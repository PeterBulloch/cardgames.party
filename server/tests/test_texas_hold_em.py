import pytest

from app.games.game import ActionError
from app.games.player import Player
from app.games.poker.texas_hold_em import TexasHoldEm

HOLE_CARDS = ["SPADE_ACE", "CLUB_TWO", "CLUB_KING", "HEART_ACE", "DIAMOND_SEVEN", "CLUB_QUEEN"]


class Table:
    def __init__(self, *names: str) -> None:
        self.game = TexasHoldEm()
        self.players = {name: Player(name, "player") for name in names}
        for player in self.players.values():
            self.game.add_member(player)
        self.anyone = next(iter(self.players.values()))

    def __getitem__(self, name: str) -> Player:
        return self.players[name]

    def act(self, action: dict, actor: Player | None = None) -> None:
        self.game.perform(self.game.parse_action(action), actor or self.anyone)

    def start(self) -> None:
        self.act({"type": "start_hand"})

    def deal(self, *cards: str) -> None:
        for card in cards:
            self.act({"type": "deal_card", "card": f"CARD_{card}"})

    def bet(self, kind: str, name: str) -> None:
        self.act({"type": kind, "member_id": self[name].id})

    def name_of(self, member_id: str | None) -> str | None:
        return next((n for n, p in self.players.items() if p.id == member_id), None)

    @property
    def to_act(self) -> str | None:
        return self.name_of(self.game.to_act)

    def next_deal(self) -> str | None:
        target = self.game.next_deal()
        if target is None:
            return None
        return self.name_of(target["member_id"]) if target["kind"] == "seat" else target["kind"]


def cards_of(view: dict, player: Player) -> list[str] | None:
    return next(s["cards"] for s in view["seats"] if s["member_id"] == player.id)


def test_button_and_blinds_rotate() -> None:
    t = Table("a", "b", "c")
    t.start()
    assert [t.name_of(x) for x in (t.game.button, t.game.small_blind, t.game.big_blind)] == ["a", "b", "c"]
    with pytest.raises(ActionError, match="already in progress"):
        t.start()
    t.deal(*HOLE_CARDS)
    t.bet("fold", "a")
    t.bet("fold", "b")
    assert t.game.phase == "complete"
    t.start()
    assert [t.name_of(x) for x in (t.game.button, t.game.small_blind, t.game.big_blind)] == ["b", "c", "a"]


def test_heads_up_button_is_small_blind_and_acts_first_preflop() -> None:
    t = Table("a", "b")
    t.start()
    assert (t.name_of(t.game.small_blind), t.name_of(t.game.big_blind)) == ("a", "b")
    assert t.next_deal() == "b"
    t.deal("SPADE_ACE", "HEART_ACE", "CLUB_TWO", "CLUB_THREE")
    assert t.to_act == "a"


def test_deal_order_and_burns_are_enforced() -> None:
    t = Table("a", "b", "c")
    t.start()
    order = []
    for card in HOLE_CARDS:
        order.append(t.next_deal())
        t.deal(card)
    assert order == ["b", "c", "a", "b", "c", "a"]
    assert t.game.hands[t["b"].id] == ["CARD_SPADE_ACE", "CARD_HEART_ACE"]

    with pytest.raises(ActionError, match="already on the table"):
        t.deal("SPADE_ACE")
    with pytest.raises(ActionError, match="No card is due"):
        t.deal("SPADE_TWO")

    t.bet("call", "a")
    t.bet("call", "b")
    t.bet("check", "c")
    assert t.next_deal() == "burn"
    t.deal("SPADE_TWO")
    assert t.next_deal() == "board"
    t.deal("SPADE_THREE", "SPADE_FOUR", "SPADE_FIVE")
    assert t.game.phase == "betting" and t.game.board == ["CARD_SPADE_THREE", "CARD_SPADE_FOUR", "CARD_SPADE_FIVE"]


def test_betting_turns_are_enforced() -> None:
    t = Table("a", "b", "c")
    t.start()
    t.deal(*HOLE_CARDS)
    assert t.to_act == "a"
    with pytest.raises(ActionError, match="not that player's turn"):
        t.bet("fold", "b")
    with pytest.raises(ActionError, match="Cannot check"):
        t.bet("check", "a")
    # Any acting member may submit the move for the player on turn.
    t.act({"type": "call", "member_id": t["a"].id}, actor=t["c"])
    t.bet("call", "b")
    assert t.to_act == "c" and t.game.legal_bets() == ["fold", "check", "raise"]
    t.bet("raise", "c")
    assert t.to_act == "a" and t.game.legal_bets() == ["fold", "call", "raise"]
    t.bet("call", "a")
    t.bet("call", "b")
    assert t.game.phase == "dealing" and t.game.current_stage == "flop"


def test_postflop_action_starts_left_of_button() -> None:
    t = Table("a", "b", "c")
    t.start()
    t.deal(*HOLE_CARDS)
    t.bet("call", "a")
    t.bet("call", "b")
    t.bet("check", "c")
    t.deal("SPADE_TWO", "SPADE_THREE", "SPADE_FOUR", "SPADE_FIVE")
    assert t.to_act == "b" and t.game.legal_bets() == ["fold", "check", "bet"]


def play_to_showdown(t: Table) -> None:
    t.start()
    t.deal(*HOLE_CARDS)
    t.bet("fold", "a")
    t.bet("call", "b")
    t.bet("check", "c")
    for street in (["HEART_TWO", "SPADE_NINE", "HEART_FOUR", "CLUB_JACK"], ["HEART_THREE", "DIAMOND_THREE"],
                   ["HEART_FIVE", "SPADE_EIGHT"]):
        t.deal(*street)
        t.bet("check", "b")
        t.bet("check", "c")


def test_showdown_reveals_live_hands_and_picks_winner() -> None:
    t = Table("a", "b", "c")
    play_to_showdown(t)
    assert t.game.phase == "complete" and t.game.current_stage == "showdown"

    view = t.game.view_for(t["c"])
    assert cards_of(view, t["b"]) == ["CARD_SPADE_ACE", "CARD_HEART_ACE"]
    assert cards_of(view, t["a"]) is None
    assert view["result"]["winners"] == [t["b"].id]
    assert view["legal_bets"] == [] and view["can_start_hand"]


def test_fold_to_one_player_ends_hand_without_reveal() -> None:
    t = Table("a", "b", "c")
    t.start()
    t.deal(*HOLE_CARDS)
    t.bet("fold", "a")
    t.bet("fold", "b")
    view = t.game.view_for(t["a"])
    assert view["result"] == {"uncontested": True, "winners": [t["c"].id], "results": []}
    assert cards_of(view, t["c"]) is None


def test_undo_restores_previous_states() -> None:
    t = Table("a", "b", "c")
    t.start()
    t.deal(*HOLE_CARDS)
    t.bet("call", "a")
    t.bet("fold", "b")
    t.act({"type": "undo"})
    assert t.to_act == "b" and t["b"].id not in t.game.folded
    t.act({"type": "undo"})
    t.act({"type": "undo"})
    assert t.game.phase == "dealing" and t.next_deal() == "a" and len(t.game.hands[t["a"].id]) == 1


def test_players_joining_sit_out_and_leavers_fold() -> None:
    t = Table("a", "b", "c")
    t.start()
    t.deal(*HOLE_CARDS)
    late = Player("late", "player")
    t.game.add_member(late)
    t.players["late"] = late
    assert not t.game.can_undo
    assert t.game.view_for(late)["seats"][-1]["in_hand"] is False

    t.game.remove_member(t["a"])
    assert t.to_act == "b" and t["a"].id not in t.game.seats
    # The leaver's cards stay out of play.
    with pytest.raises(ActionError, match="already on the table"):
        t.deal("CLUB_KING")


def test_dealer_is_dedicated_member_when_present() -> None:
    t = Table("a", "b")
    t.start()
    assert t.game.view_for(t["a"])["dealer"] == {"member_id": t["a"].id, "dedicated": False}
    croupier = Player("croupier", "dealer")
    t.game.add_member(croupier)
    view = t.game.view_for(croupier)
    assert view["dealer"] == {"member_id": croupier.id, "dedicated": True}
    assert view["button"] == t["a"].id


def test_visibility_by_role() -> None:
    t = Table("a", "b")
    observer, dealer = Player("obs", "observer"), Player("d", "dealer")
    t.start()
    t.deal("SPADE_ACE", "HEART_ACE", "CLUB_TWO", "CLUB_THREE")
    b_cards = ["CARD_SPADE_ACE", "CARD_CLUB_TWO"]

    view = t.game.view_for(t["a"])
    assert cards_of(view, t["a"]) == ["CARD_HEART_ACE", "CARD_CLUB_THREE"]
    assert cards_of(view, t["b"]) is None
    assert cards_of(t.game.view_for(observer), t["b"]) == b_cards
    observer.hide_hands = True
    assert cards_of(t.game.view_for(observer), t["b"]) is None
    assert cards_of(t.game.view_for(dealer), t["b"]) == b_cards
