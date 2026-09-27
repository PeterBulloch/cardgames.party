import pytest

from app.games.game import ActionError
from app.games.player import Player
from app.games.poker.actions import BoardTarget, BurnTarget, DealCard, Fold, NextStage, ReturnCard, SeatTarget
from app.games.poker.texas_hold_em import TexasHoldEm


@pytest.fixture
def table() -> tuple[TexasHoldEm, Player, Player, Player, Player]:
    game = TexasHoldEm()
    alice, bob = Player("alice", "player"), Player("bob", "player")
    dealer, observer = Player("dealer", "dealer"), Player("obs", "observer")
    game.add_seat(alice.id)
    game.add_seat(bob.id)
    return game, alice, bob, dealer, observer


def deal(game: TexasHoldEm, actor: Player, card: str, target) -> None:
    game.apply(DealCard(type="deal_card", card=f"CARD_{card}", target=target), actor)


def seat(player: Player) -> SeatTarget:
    return SeatTarget(kind="seat", member_id=player.id)


def cards_of(view: dict, player: Player) -> list[str] | None:
    return next(s["cards"] for s in view["seats"] if s["member_id"] == player.id)


def test_players_only_see_own_hand(table) -> None:
    game, alice, bob, dealer, observer = table
    deal(game, dealer, "SPADE_ACE", seat(alice))
    deal(game, dealer, "HEART_ACE", seat(bob))
    deal(game, dealer, "CLUB_TWO", BurnTarget(kind="burn"))

    view = game.view_for(alice)
    assert cards_of(view, alice) == ["CARD_SPADE_ACE"]
    assert cards_of(view, bob) is None
    assert view["burn"] == {"count": 1, "cards": None}

    assert cards_of(game.view_for(observer), bob) == ["CARD_HEART_ACE"]
    observer.hide_hands = True
    assert cards_of(game.view_for(observer), bob) is None
    assert cards_of(game.view_for(dealer), bob) == ["CARD_HEART_ACE"]


def test_validation(table) -> None:
    game, alice, bob, dealer, _ = table
    deal(game, alice, "SPADE_ACE", seat(bob))
    with pytest.raises(ActionError):
        deal(game, alice, "SPADE_ACE", seat(alice))
    with pytest.raises(ActionError):
        deal(game, alice, "CLUB_KING", BoardTarget(kind="board"))
    with pytest.raises(ActionError):
        deal(game, alice, "JOKER", seat(alice))
    deal(game, alice, "SPADE_TWO", seat(bob))
    with pytest.raises(ActionError):
        deal(game, alice, "SPADE_THREE", seat(bob))
    # Alice cannot see Bob's card, so she cannot return it either.
    with pytest.raises(ActionError):
        game.apply(ReturnCard(type="return_card", card="CARD_SPADE_ACE"), alice)
    game.apply(ReturnCard(type="return_card", card="CARD_SPADE_ACE"), dealer)


def test_showdown_reveals_live_hands_and_picks_winner(table) -> None:
    game, alice, bob, dealer, _ = table
    carol = Player("carol", "player")
    game.add_seat(carol.id)
    for card, target in [
        ("SPADE_ACE", seat(alice)), ("HEART_ACE", seat(alice)),
        ("CLUB_TWO", seat(bob)), ("DIAMOND_SEVEN", seat(bob)),
        ("CLUB_KING", seat(carol)), ("CLUB_QUEEN", seat(carol)),
    ]:
        deal(game, dealer, card, target)
    game.apply(Fold(type="fold", member_id=carol.id), bob)

    for stage_cards in (["SPADE_NINE", "HEART_FOUR", "CLUB_JACK"], ["DIAMOND_THREE"], ["SPADE_EIGHT"]):
        game.apply(NextStage(type="next_stage"), dealer)
        for card in stage_cards:
            deal(game, dealer, card, BoardTarget(kind="board"))
    game.apply(NextStage(type="next_stage"), dealer)

    view = game.view_for(bob)
    assert cards_of(view, alice) == ["CARD_SPADE_ACE", "CARD_HEART_ACE"]
    assert cards_of(view, carol) is None
    assert view["showdown"]["winners"] == [alice.id]
    assert {r["member_id"] for r in view["showdown"]["results"]} == {alice.id, bob.id}
