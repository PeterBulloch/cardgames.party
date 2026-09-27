from typing import Literal

from ..cards import STANDARD_DECK
from ..game import ActionError, Game
from ..player import Player
from .actions import BettingAction, DealCard, StartHand, TexasHoldEmAction
from .hand_evaluator import best_hand, category_name

Phase = Literal["waiting", "dealing", "betting", "complete"]

BOARD_LIMIT = {"pre-flop": 0, "flop": 3, "turn": 4, "river": 5, "showdown": 5}
HAND_SIZE = 2


class TexasHoldEm(Game):
    key = "texas_hold_em"
    label = "Texas Hold'em"
    stages = ("pre-flop", "flop", "turn", "river", "showdown")
    min_players = 2
    max_players = 10
    actions = TexasHoldEmAction

    def __init__(self) -> None:
        super().__init__()
        self.seats: list[str] = []
        self.dedicated_dealers: list[str] = []
        self.hands: dict[str, list[str]] = {}
        self.board: list[str] = []
        self.burn: list[str] = []
        self.muck: list[str] = []
        self.phase: Phase = "waiting"
        self.hand_number = 0
        self.in_hand: list[str] = []
        self.folded: set[str] = set()
        self.button: str | None = None
        self.small_blind: str | None = None
        self.big_blind: str | None = None
        # Betting has no chips, so "level" counts bets/raises and each player records the level they matched.
        self.level = 0
        self.matched: dict[str, int] = {}
        self.needs_to_act: set[str] = set()
        self.to_act: str | None = None

    # --- membership -------------------------------------------------------

    def add_member(self, member: Player) -> None:
        super().add_member(member)
        if member.role == "dealer":
            self.dedicated_dealers.append(member.id)

    def remove_member(self, member: Player) -> None:
        if member.id in self.dedicated_dealers:
            self.dedicated_dealers.remove(member.id)
        super().remove_member(member)

    def add_seat(self, member_id: str) -> None:
        if len(self.seats) >= self.max_players:
            raise ActionError("The table is full")
        self.seats.append(member_id)
        self.hands[member_id] = []

    def remove_seat(self, member_id: str) -> None:
        if member_id not in self.hands:
            return
        if self.phase in ("dealing", "betting") and member_id in self.live:
            self._fold(member_id)
        self.muck.extend(self.hands.pop(member_id))
        if member_id in self.in_hand:
            self.in_hand.remove(member_id)
        self.folded.discard(member_id)
        self.matched.pop(member_id, None)
        if self.button == member_id:
            # Hand the button back one seat so the next rotation lands where it would have.
            index = self.seats.index(member_id)
            self.button = self.seats[index - 1] if len(self.seats) > 1 else None
        self.seats.remove(member_id)

    # --- helpers ----------------------------------------------------------

    @property
    def live(self) -> list[str]:
        return [seat for seat in self.in_hand if seat not in self.folded]

    def _clockwise_after(self, anchor: str | None, pool: list[str]) -> list[str]:
        start = self.seats.index(anchor) + 1 if anchor in self.seats else 0
        ordered = self.seats[start:] + self.seats[:start]
        return [seat for seat in ordered if seat in pool]

    def _cards_in_play(self) -> set[str]:
        return {*self.board, *self.burn, *self.muck, *(card for hand in self.hands.values() for card in hand)}

    def next_deal(self) -> dict | None:
        if self.phase != "dealing":
            return None
        if self.current_stage == "pre-flop":
            order = self._clockwise_after(self.button, self.live)
            for round_index in range(HAND_SIZE):
                for seat in order:
                    if len(self.hands[seat]) == round_index:
                        return {"kind": "seat", "member_id": seat}
            return None
        if len(self.burn) < self.stage_index:
            return {"kind": "burn"}
        if len(self.board) < BOARD_LIMIT[self.current_stage]:
            return {"kind": "board"}
        return None

    def legal_bets(self) -> list[str]:
        if self.phase != "betting" or self.to_act is None:
            return []
        owes = self.matched.get(self.to_act, 0) < self.level
        return ["fold", "call" if owes else "check", "raise" if self.level else "bet"]

    # --- actions ----------------------------------------------------------

    def apply(self, action: object, actor: Player) -> None:
        if isinstance(action, StartHand):
            self._start_hand()
        elif isinstance(action, DealCard):
            self._deal(action.card)
        elif isinstance(action, BettingAction):
            self._bet(action)
        else:
            raise ActionError("Unsupported action for this game")

    def _start_hand(self) -> None:
        if self.phase in ("dealing", "betting"):
            raise ActionError("A hand is already in progress")
        if len(self.seats) < self.min_players:
            raise ActionError(f"At least {self.min_players} players are needed")

        self.button = self._clockwise_after(self.button, self.seats)[0] if self.button else self.seats[0]
        self.in_hand = list(self.seats)
        if len(self.in_hand) == 2:
            # Heads-up: the button posts the small blind.
            self.small_blind = self.button
            self.big_blind = self._clockwise_after(self.button, self.in_hand)[0]
        else:
            self.small_blind, self.big_blind = self._clockwise_after(self.button, self.in_hand)[:2]

        for hand in self.hands.values():
            hand.clear()
        self.board.clear()
        self.burn.clear()
        self.muck.clear()
        self.folded.clear()
        self.stage_index = 0
        self.phase = "dealing"
        self.hand_number += 1
        self._reset_betting()

    def _deal(self, card: str) -> None:
        if card not in STANDARD_DECK:
            raise ActionError("That card is not used in Texas Hold'em")
        if card in self._cards_in_play():
            raise ActionError("That card is already on the table")
        target = self.next_deal()
        if target is None:
            raise ActionError("No card is due to be dealt right now")

        if target["kind"] == "seat":
            self.hands[target["member_id"]].append(card)
        else:
            (self.burn if target["kind"] == "burn" else self.board).append(card)

        if self.next_deal() is None:
            self._open_betting()

    def _bet(self, action: BettingAction) -> None:
        if self.phase != "betting":
            raise ActionError("No betting round is open")
        if action.member_id != self.to_act:
            raise ActionError("It is not that player's turn")
        if action.type not in self.legal_bets():
            raise ActionError(f"Cannot {action.type} right now")

        seat = action.member_id
        if action.type == "fold":
            self._fold(seat)
            return
        if action.type in ("bet", "raise"):
            self.level += 1
            self.needs_to_act = set(self.live)
        self.matched[seat] = self.level
        self.needs_to_act.discard(seat)
        self._advance_from(seat)

    # --- flow -------------------------------------------------------------

    def _reset_betting(self) -> None:
        self.level = 0
        self.matched = {}
        self.needs_to_act = set()
        self.to_act = None

    def _open_betting(self) -> None:
        live = self.live
        self.phase = "betting"
        self.needs_to_act = set(live)
        self.matched = {seat: 0 for seat in live}
        if self.current_stage == "pre-flop":
            # The big blind counts as the opening bet, so the big blind still gets an option.
            self.level = 1
            if self.big_blind in self.matched:
                self.matched[self.big_blind] = 1
            self.to_act = self._clockwise_after(self.big_blind, live)[0]
        else:
            self.level = 0
            self.to_act = self._clockwise_after(self.button, live)[0]

    def _advance_from(self, seat: str) -> None:
        if not self.needs_to_act:
            self._close_round()
            return
        self.to_act = next(s for s in self._clockwise_after(seat, self.live) if s in self.needs_to_act)

    def _close_round(self) -> None:
        self._reset_betting()
        self.next_stage()
        self.phase = "complete" if self.current_stage == "showdown" else "dealing"

    def _fold(self, seat: str) -> None:
        self.folded.add(seat)
        self.needs_to_act.discard(seat)
        if len(self.live) <= 1:
            self._reset_betting()
            self.phase = "complete"
        elif self.phase == "betting" and self.to_act == seat:
            self._advance_from(seat)
        elif self.phase == "dealing" and self.next_deal() is None:
            self._open_betting()

    # --- view -------------------------------------------------------------

    def _result(self) -> dict | None:
        if self.phase != "complete":
            return None
        live = self.live
        if len(live) <= 1:
            return {"uncontested": True, "winners": live, "results": []}

        scored = {seat: best_hand(self.hands[seat] + self.board) for seat in live}
        top = max(score for score, _ in scored.values())
        return {
            "uncontested": False,
            "winners": [seat for seat, (score, _) in scored.items() if score == top],
            "results": [
                {"member_id": seat, "hand_name": category_name(score), "best_cards": cards}
                for seat, (score, cards) in scored.items()
            ],
        }

    def view_for(self, viewer: Player) -> dict:
        showdown = self.current_stage == "showdown"
        seats = []
        for seat in self.seats:
            hand = self.hands[seat]
            folded = seat in self.folded
            visible = viewer.sees_all or seat == viewer.id or (showdown and not folded)
            seats.append({
                "member_id": seat,
                "in_hand": seat in self.in_hand,
                "folded": folded,
                "card_count": len(hand),
                "cards": list(hand) if visible else None,
            })

        if self.dedicated_dealers:
            dealer = {"member_id": self.dedicated_dealers[0], "dedicated": True}
        elif self.button:
            dealer = {"member_id": self.button, "dedicated": False}
        else:
            dealer = None

        return {
            "phase": self.phase,
            "stage": self.current_stage,
            "stages": list(self.stages),
            "hand_number": self.hand_number,
            "button": self.button,
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "dealer": dealer,
            "to_act": self.to_act,
            "legal_bets": self.legal_bets(),
            "next_deal": self.next_deal(),
            "can_start_hand": self.phase in ("waiting", "complete") and len(self.seats) >= self.min_players,
            "can_undo": self.can_undo,
            "board": list(self.board),
            "burn": {"count": len(self.burn), "cards": list(self.burn) if viewer.sees_all else None},
            "seats": seats,
            "result": self._result(),
        }
