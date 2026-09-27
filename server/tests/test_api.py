import pytest
from fastapi.testclient import TestClient

from app.main import app, rooms


@pytest.fixture
def client():
    rooms._rooms.clear()
    with TestClient(app) as client:
        yield client


def create(client: TestClient, **overrides) -> dict:
    body = {"name": "Table", "password": "secret", "max_players": 2, "display_name": "dealer", "role": "dealer"}
    response = client.post("/api/lobbies", json=body | overrides)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_validates_against_game(client: TestClient) -> None:
    base = {"name": "T", "max_players": 4, "display_name": "d", "role": "dealer"}
    assert client.post("/api/lobbies", json=base | {"game": "go_fish"}).status_code == 400
    assert client.post("/api/lobbies", json=base | {"max_players": 11}).status_code == 400


def join(client: TestClient, name: str, role: str = "player", password: str = "secret"):
    return client.post("/api/lobbies/join", json={
        "name": "table", "password": password, "display_name": name, "role": role,
    })


def test_join_rules(client: TestClient) -> None:
    create(client)
    assert join(client, "a", password="wrong").status_code == 403
    assert client.post("/api/lobbies/join", json={
        "name": "nope", "password": "secret", "display_name": "a", "role": "player",
    }).json() == join(client, "x", password="wrong").json()
    assert join(client, "a").status_code == 200
    assert join(client, "A").status_code == 409
    assert join(client, "b").status_code == 200
    assert join(client, "c").status_code == 409
    assert join(client, "c", role="observer").status_code == 200


def test_socket_flow(client: TestClient) -> None:
    dealer = create(client)
    alice = join(client, "alice").json()
    bob = join(client, "bob").json()

    with client.websocket_connect("/api/ws") as dealer_ws, client.websocket_connect("/api/ws") as alice_ws:
        dealer_ws.send_json({"type": "hello", "token": dealer["token"]})
        first = dealer_ws.receive_json()
        assert first["type"] == "state"
        alice_ws.send_json({"type": "hello", "token": alice["token"]})
        alice_ws.receive_json()
        dealer_ws.receive_json()

        def act(ws, who, seq, action):
            ws.send_json({"lobby": who["lobby_id"], "player": who["member_id"], "seq": seq, "action": action})

        act(dealer_ws, dealer, 1, {"type": "start_hand"})
        assert dealer_ws.receive_json()["type"] == "ack"
        dealer_ws.receive_json()
        alice_ws.receive_json()

        # Heads-up, Alice has the button, so the first card goes to Bob.
        act(dealer_ws, dealer, 2, {"type": "deal_card", "card": "CARD_SPADE_ACE"})
        assert dealer_ws.receive_json()["type"] == "ack"
        dealer_state = dealer_ws.receive_json()
        alice_state = alice_ws.receive_json()
        assert dealer_state["version"] == alice_state["version"] > first["version"]

        def bob_cards(message):
            return next(s for s in message["state"]["game"]["seats"] if s["member_id"] == bob["member_id"])

        assert bob_cards(dealer_state)["cards"] == ["CARD_SPADE_ACE"]
        assert bob_cards(alice_state)["cards"] is None
        assert bob_cards(alice_state)["card_count"] == 1

        act(dealer_ws, dealer, 2, {"type": "undo"})
        error = dealer_ws.receive_json()
        assert error == {"type": "error", "seq": 2, "message": "Stale or duplicate message ignored"}

        act(alice_ws, dealer, 1, {"type": "undo"})
        assert alice_ws.receive_json()["type"] == "error"


def test_observer_cannot_act(client: TestClient) -> None:
    create(client)
    obs = join(client, "obs", role="observer").json()
    with client.websocket_connect("/api/ws") as ws:
        ws.send_json({"type": "hello", "token": obs["token"]})
        ws.receive_json()
        ws.send_json({"lobby": obs["lobby_id"], "player": obs["member_id"], "seq": 1,
                      "action": {"type": "next_stage"}})
        assert ws.receive_json()["message"] == "Observers cannot take actions"
