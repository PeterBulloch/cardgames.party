import pytest

from app.games.game import ActionError
from app.games.player import Player
from app.games.poker.texas_hold_em import TexasHoldEm

HOLE_CARDS = ["SPADE_ACE", "CLUB_TWO", "CLUB_KING", "HEART_ACE", "DIAMOND_SEVEN", "CLUB_QUEEN"]


class Table:
    def __init__(self, *names: str, chips: int | dict[str, int] = 100, blinds: tuple[int, int] = (1, 2)) -> None:
        self.game = TexasHoldEm()
        self.players = {name: Player(name, "player") for name in names}
        for player in self.players.values():
            self.game.add_member(player)
        self.anyone = next(iter(self.players.values()))
        self.act({"type": "set_blinds", "small": blinds[0], "big": blinds[1]})
        for name in names:
            stack = chips if isinstance(chips, int) else chips[name]
            self.act({"type": "set_chips", "member_id": self[name].id, "chips": stack})

    def __getitem__(self, name: str) -> Player:
        return self.players[name]

    def act(self, action: dict, actor: Player | None = None) -> None:
        self.game.perform(self.game.parse_action(action), actor or self.anyone)

    def start(self) -> None:
        self.act({"type": "start_hand"})

    def deal(self, *cards: str) -> None:
        for card in cards:
            self.act({"type": "deal_card", "card": f"CARD_{card}"})

    def bet(self, kind: str, name: str, amount: int | None = None) -> None:
        action = {"type": kind, "member_id": self[name].id}
        if amount is not None:
            action["amount"] = amount
        self.act(action)

    def chips(self, name: str) -> int:
        return self.game.stacks[self[name].id]

    def legal(self) -> list[str]:
        return [option["type"] for option in self.game.legal_bets()]

    def pots(self) -> list[tuple[int, list[str]]]:
        return [(pot.amount, [self.name_of(s) for s in pot.eligible]) for pot in self.game.pots()]

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
    with pytest.raises(ActionError, match="Award the pot"):
        t.start()
    t.act({"type": "award_pots"})
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
    assert t.to_act == "c" and t.legal() == ["fold", "check", "raise"]
    t.bet("raise", "c", 6)
    assert t.to_act == "a" and t.legal() == ["fold", "call", "raise"]
    t.bet("call", "a")
    t.bet("call", "b")
    assert t.game.phase == "dealing" and t.game.current_stage == "flop"
    assert t.pots() == [(18, ["a", "b", "c"])] and t.chips("a") == 94


def test_postflop_action_starts_left_of_button() -> None:
    t = Table("a", "b", "c")
    t.start()
    t.deal(*HOLE_CARDS)
    t.bet("call", "a")
    t.bet("call", "b")
    t.bet("check", "c")
    t.deal("SPADE_TWO", "SPADE_THREE", "SPADE_FOUR", "SPADE_FIVE")
    assert t.to_act == "b" and t.legal() == ["fold", "check", "bet"]


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
    assert view["legal_bets"] == [] and view["can_award"] and not view["can_start_hand"]
    t.act({"type": "award_pots"})
    assert t.game.view_for(t["c"])["can_start_hand"] and t.chips("b") == 102


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


BURNS_AND_BOARD = ["HEART_TWO", "SPADE_NINE", "HEART_FOUR", "CLUB_JACK", "HEART_THREE", "DIAMOND_THREE",
                   "HEART_FIVE", "SPADE_EIGHT"]


def test_blinds_are_posted_from_stacks() -> None:
    t = Table("a", "b", "c")
    t.start()
    assert (t.chips("a"), t.chips("b"), t.chips("c")) == (100, 99, 98)
    assert t.pots() == [(3, ["a", "b", "c"])] and t.game.current_bet == 2


def test_no_limit_bet_sizes() -> None:
    t = Table("a", "b", "c")
    t.start()
    t.deal(*HOLE_CARDS)
    with pytest.raises(ActionError, match="between 4 and 100"):
        t.bet("raise", "a", 3)
    t.bet("raise", "a", 10)
    raise_option = t.game.legal_bets()[2]
    assert raise_option == {"type": "raise", "min": 18, "max": 100}
    with pytest.raises(ActionError):
        t.bet("bet", "b", 20)


def test_side_pots_are_built_and_awarded() -> None:
    t = Table("a", "b", "c", chips={"a": 100, "b": 30, "c": 60})
    t.start()
    t.deal(*HOLE_CARDS)
    t.bet("raise", "a", 100)
    t.bet("call", "b")
    t.bet("call", "c")
    # Everyone is all-in, so the board runs out with no more betting.
    assert t.game.phase == "dealing"
    t.deal(*BURNS_AND_BOARD)
    assert t.game.phase == "complete"
    assert t.pots() == [(90, ["a", "b", "c"]), (60, ["a", "c"]), (40, ["a"])]

    t.act({"type": "award_pots"})
    assert (t.chips("a"), t.chips("b"), t.chips("c")) == (100, 90, 0)
    with pytest.raises(ActionError, match="already been awarded"):
        t.act({"type": "award_pots"})


def test_split_pot_gives_odd_chip_left_of_button() -> None:
    t = Table("a", "b")
    t.start()
    t.deal("CLUB_TWO", "CLUB_THREE", "DIAMOND_TWO", "DIAMOND_THREE")
    t.bet("call", "a")
    t.bet("check", "b")
    for street in (["HEART_TWO", "SPADE_ACE", "SPADE_KING", "SPADE_QUEEN"], ["HEART_THREE", "SPADE_JACK"],
                   ["HEART_FOUR", "SPADE_TEN"]):
        t.deal(*street)
        t.bet("check", "b")
        t.bet("check", "a")
    t.act({"type": "set_pot", "index": 0, "amount": 5})
    t.act({"type": "award_pots"})
    assert (t.chips("a"), t.chips("b")) == (100, 101)


def test_chips_and_pot_can_be_edited_mid_hand_and_undone() -> None:
    t = Table("a", "b", "c")
    t.start()
    t.act({"type": "set_chips", "member_id": t["b"].id, "chips": 500})
    t.act({"type": "set_pot", "index": 0, "amount": 50})
    assert t.chips("b") == 500 and t.pots()[0][0] == 50
    t.act({"type": "undo"})
    t.act({"type": "undo"})
    assert t.chips("b") == 99 and t.pots()[0][0] == 3


def test_blinds_change_between_hands_and_can_double() -> None:
    t = Table("a", "b")
    t.act({"type": "set_blinds", "small": 1, "big": 2, "auto_double": True, "double_every": 2})

    def play_hand() -> None:
        t.start()
        t.deal("CLUB_TWO", "CLUB_THREE", "DIAMOND_TWO", "DIAMOND_THREE")
        t.bet("fold", t.to_act)
        t.act({"type": "award_pots"})

    play_hand()
    t.start()
    with pytest.raises(ActionError, match="between hands"):
        t.act({"type": "set_blinds", "small": 5, "big": 10})
    t.act({"type": "undo"})
    play_hand()
    t.start()
    assert (t.game.small_blind_amount, t.game.big_blind_amount) == (2, 4)


def test_players_without_chips_are_dealt_in_but_skip_betting() -> None:
    t = Table("a", "b", "c", chips=0)
    t.start()
    t.deal(*HOLE_CARDS)
    assert t.game.phase == "dealing" and t.next_deal() == "burn"
