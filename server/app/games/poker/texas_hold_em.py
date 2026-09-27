from typing import Literal

from ..cards import STANDARD_DECK
from ..game import ActionError, Game
from ..player import Player
from .actions import (
    AwardPots, BettingAction, DealCard, SetBlinds, SetChips, SetPot, SizedBet, StartHand, TexasHoldEmAction,
)
from .hand_evaluator import best_hand, category_name
from .pots import Pot, build_pots, split

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
        self.stacks: dict[str, int] = {}
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

        self.small_blind_amount = 0
        self.big_blind_amount = 0
        self.auto_double = False
        self.double_every = 10
        self.hands_at_level = 0

        self.contributions: dict[str, int] = {}
        self.pot_adjustments: dict[int, int] = {}
        self.awarded = False
        self.street_bets: dict[str, int] = {}
        self.current_bet = 0
        self.min_raise = 0
        # Players who have acted since the last full raise; they may not re-raise an incomplete one.
        self.acted: set[str] = set()
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
        self.stacks[member_id] = 0

    def remove_seat(self, member_id: str) -> None:
        if member_id not in self.hands:
            return
        if self.hand_active and member_id in self.live:
            self._fold(member_id)
        # Chips already bet stay in the pot; the rest of the stack leaves with the player.
        self.muck.extend(self.hands.pop(member_id))
        self.stacks.pop(member_id)
        if member_id in self.in_hand:
            self.in_hand.remove(member_id)
        self.folded.discard(member_id)
        if self.button == member_id:
            # Hand the button back one seat so the next rotation lands where it would have.
            index = self.seats.index(member_id)
            self.button = self.seats[index - 1] if len(self.seats) > 1 else None
        self.seats.remove(member_id)

    # --- helpers ----------------------------------------------------------

    @property
    def hand_active(self) -> bool:
        return self.phase in ("dealing", "betting")

    @property
    def live(self) -> list[str]:
        return [seat for seat in self.in_hand if seat not in self.folded]

    def _clockwise_after(self, anchor: str | None, pool: list[str] | set[str]) -> list[str]:
        start = self.seats.index(anchor) + 1 if anchor in self.seats else 0
        ordered = self.seats[start:] + self.seats[:start]
        return [seat for seat in ordered if seat in pool]

    def _cards_in_play(self) -> set[str]:
        return {*self.board, *self.burn, *self.muck, *(card for hand in self.hands.values() for card in hand)}

    def _can_bet(self, seat: str) -> bool:
        return self.stacks.get(seat, 0) > 0

    def _put_in(self, seat: str, amount: int) -> None:
        amount = min(amount, self.stacks[seat])
        self.stacks[seat] -= amount
        self.street_bets[seat] = self.street_bets.get(seat, 0) + amount
        self.contributions[seat] = self.contributions.get(seat, 0) + amount

    @property
    def _min_bet(self) -> int:
        return max(self.big_blind_amount, 1)

    def pots(self) -> list[Pot]:
        live = self.live
        pots = build_pots(self.contributions, live, {seat for seat in live if not self._can_bet(seat)})
        if not pots and 0 in self.pot_adjustments:
            pots = [Pot(0, live)]
        for index, pot in enumerate(pots):
            pot.amount = max(0, pot.amount + self.pot_adjustments.get(index, 0))
        return pots

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

    def legal_bets(self) -> list[dict]:
        if self.phase != "betting" or self.to_act is None:
            return []
        seat = self.to_act
        stack = self.stacks[seat]
        owed = self.current_bet - self.street_bets.get(seat, 0)
        options: list[dict] = [{"type": "fold"}]
        options.append({"type": "call", "amount": min(owed, stack)} if owed > 0 else {"type": "check"})
        if seat not in self.acted and stack > max(owed, 0):
            most = self.street_bets.get(seat, 0) + stack
            if self.current_bet == 0:
                options.append({"type": "bet", "min": min(self._min_bet, most), "max": most})
            else:
                options.append({"type": "raise", "min": min(self.current_bet + self.min_raise, most), "max": most})
        return options

    # --- actions ----------------------------------------------------------

    def apply(self, action: object, actor: Player) -> None:
        if isinstance(action, StartHand):
            self._start_hand()
        elif isinstance(action, DealCard):
            self._deal(action.card)
        elif isinstance(action, (BettingAction, SizedBet)):
            self._bet(action)
        elif isinstance(action, SetChips):
            if action.member_id not in self.stacks:
                raise ActionError("No such player")
            self.stacks[action.member_id] = action.chips
        elif isinstance(action, SetPot):
            self._set_pot(action)
        elif isinstance(action, SetBlinds):
            self._set_blinds(action)
        elif isinstance(action, AwardPots):
            self._award()
        else:
            raise ActionError("Unsupported action for this game")

    def _set_blinds(self, action: SetBlinds) -> None:
        if self.hand_active:
            raise ActionError("Blinds can only be changed between hands")
        if action.big < action.small:
            raise ActionError("The big blind cannot be smaller than the small blind")
        self.small_blind_amount = action.small
        self.big_blind_amount = action.big
        self.auto_double = action.auto_double
        self.double_every = action.double_every
        self.hands_at_level = 0

    def _set_pot(self, action: SetPot) -> None:
        if self.phase == "waiting":
            raise ActionError("There is no pot before the first hand")
        if self.awarded:
            raise ActionError("The pot has already been awarded")
        pots = self.pots()
        if action.index > max(len(pots) - 1, 0):
            raise ActionError("No such pot")
        current = pots[action.index].amount if pots else 0
        self.pot_adjustments[action.index] = self.pot_adjustments.get(action.index, 0) + action.amount - current

    def _start_hand(self) -> None:
        if self.hand_active:
            raise ActionError("A hand is already in progress")
        if self.phase == "complete" and not self.awarded and any(pot.amount for pot in self.pots()):
            raise ActionError("Award the pot before starting the next hand")
        if len(self.seats) < self.min_players:
            raise ActionError(f"At least {self.min_players} players are needed")

        if self.auto_double and self.hands_at_level >= self.double_every:
            self.small_blind_amount *= 2
            self.big_blind_amount *= 2
            self.hands_at_level = 0
        self.hands_at_level += 1

        self.button = self._clockwise_after(self.button, self.seats)[0] if self.button else self.seats[0]
        self.in_hand = list(self.seats)
        if len(self.in_hand) == 2:
            # Heads-up: the button posts the small blind.
            small, big = self.button, self._clockwise_after(self.button, self.in_hand)[0]
        else:
            small, big = self._clockwise_after(self.button, self.in_hand)[:2]
        self.small_blind, self.big_blind = small, big

        for hand in self.hands.values():
            hand.clear()
        self.board.clear()
        self.burn.clear()
        self.muck.clear()
        self.folded.clear()
        self.contributions = {}
        self.pot_adjustments = {}
        self.awarded = False
        self.stage_index = 0
        self.phase = "dealing"
        self.hand_number += 1
        self._reset_street()

        self._put_in(small, self.small_blind_amount)
        self._put_in(big, self.big_blind_amount)
        # A short big blind still sets the full amount others must call.
        self.current_bet = self.big_blind_amount

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

    def _bet(self, action: BettingAction | SizedBet) -> None:
        if self.phase != "betting":
            raise ActionError("No betting round is open")
        if action.member_id != self.to_act:
            raise ActionError("It is not that player's turn")
        option = next((o for o in self.legal_bets() if o["type"] == action.type), None)
        if option is None:
            raise ActionError(f"Cannot {action.type} right now")

        seat = action.member_id
        if action.type == "fold":
            self._fold(seat)
            return
        if action.type == "call":
            self._put_in(seat, option["amount"])
        elif isinstance(action, SizedBet):
            if not option["min"] <= action.amount <= option["max"]:
                raise ActionError(f"The {action.type} must be between {option['min']} and {option['max']}")
            self._raise_to(seat, action.amount)
        self.acted.add(seat)
        self.needs_to_act.discard(seat)
        self._advance_from(seat)

    def _raise_to(self, seat: str, total: int) -> None:
        self._put_in(seat, total - self.street_bets.get(seat, 0))
        increase = total - self.current_bet
        if increase >= self.min_raise:
            self.min_raise = increase
            self.acted = set()
            self.needs_to_act = {s for s in self.live if s != seat}
        else:
            # An all-in short of a full raise only obliges those now facing more to respond.
            self.needs_to_act |= {s for s in self.live if s != seat and self.street_bets.get(s, 0) < total}
        self.current_bet = total

    def _award(self) -> None:
        if self.phase != "complete":
            raise ActionError("The hand is not over yet")
        if self.awarded:
            raise ActionError("The pot has already been awarded")
        for pot in self._pot_results():
            if not pot["winners"]:
                continue
            for seat, share in split(pot["amount"], pot["winners"]).items():
                if seat in self.stacks:
                    self.stacks[seat] += share
        self.awarded = True

    # --- flow -------------------------------------------------------------

    def _reset_street(self) -> None:
        self.street_bets = {}
        self.current_bet = 0
        self.min_raise = self._min_bet
        self.acted = set()
        self.needs_to_act = set()
        self.to_act = None

    def _open_betting(self) -> None:
        self.phase = "betting"
        self.acted = set()
        self.needs_to_act = {seat for seat in self.live if self._can_bet(seat)}
        anchor = self.big_blind if self.current_stage == "pre-flop" else self.button
        order = [seat for seat in self._clockwise_after(anchor, self.live) if seat in self.needs_to_act]
        # Nobody left to bet against: run the remaining cards out.
        if not order or (len(order) == 1 and self.street_bets.get(order[0], 0) >= self.current_bet):
            self._close_round()
            return
        self.to_act = order[0]

    def _advance_from(self, seat: str) -> None:
        self.needs_to_act = {s for s in self.needs_to_act if self._can_bet(s)}
        if not self.needs_to_act:
            self._close_round()
            return
        self.to_act = next(s for s in self._clockwise_after(seat, self.live) if s in self.needs_to_act)

    def _close_round(self) -> None:
        self._reset_street()
        self.next_stage()
        if self.current_stage == "showdown":
            self.phase = "complete"
        else:
            self.phase = "dealing"

    def _fold(self, seat: str) -> None:
        self.folded.add(seat)
        self.needs_to_act.discard(seat)
        if len(self.live) <= 1:
            self.street_bets = {}
            self.needs_to_act = set()
            self.to_act = None
            self.phase = "complete"
        elif self.phase == "betting" and self.to_act == seat:
            self._advance_from(seat)
        elif self.phase == "dealing" and self.next_deal() is None:
            self._open_betting()

    # --- results ----------------------------------------------------------

    def _scores(self) -> dict[str, tuple]:
        if len(self.live) <= 1 or self.current_stage != "showdown":
            return {}
        return {seat: best_hand(self.hands[seat] + self.board) for seat in self.live}

    def _pot_results(self) -> list[dict]:
        scores = self._scores()
        order = self._clockwise_after(self.button, self.live)
        results = []
        for pot in self.pots():
            if len(pot.eligible) <= 1 or not scores:
                winners = list(pot.eligible)
            else:
                top = max(scores[seat][0] for seat in pot.eligible)
                winners = [seat for seat in order if seat in pot.eligible and scores[seat][0] == top]
            results.append({"amount": pot.amount, "eligible": pot.eligible, "winners": winners})
        return results

    def _result(self) -> dict | None:
        if self.phase != "complete":
            return None
        scores = self._scores()
        pots = self._pot_results()
        if pots:
            winners = pots[0]["winners"]
        else:
            winners = self.live if len(self.live) == 1 else []
        return {
            "uncontested": len(self.live) <= 1,
            "winners": winners,
            "results": [
                {"member_id": seat, "hand_name": category_name(score), "best_cards": cards}
                for seat, (score, cards) in scores.items()
            ],
        }

    # --- view -------------------------------------------------------------

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
                "chips": self.stacks[seat],
                "street_bet": self.street_bets.get(seat, 0),
                "all_in": self.hand_active and seat in self.live and self.stacks[seat] == 0,
                "card_count": len(hand),
                "cards": list(hand) if visible else None,
            })

        if self.dedicated_dealers:
            dealer = {"member_id": self.dedicated_dealers[0], "dedicated": True}
        elif self.button:
            dealer = {"member_id": self.button, "dedicated": False}
        else:
            dealer = None

        pots = self._pot_results() if self.phase == "complete" else [
            {"amount": pot.amount, "eligible": pot.eligible, "winners": []} for pot in self.pots()
        ]
        return {
            "phase": self.phase,
            "stage": self.current_stage,
            "stages": list(self.stages),
            "hand_number": self.hand_number,
            "button": self.button,
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "dealer": dealer,
            "blinds": {
                "small": self.small_blind_amount,
                "big": self.big_blind_amount,
                "auto_double": self.auto_double,
                "double_every": self.double_every,
                "hands_until_double": max(self.double_every - self.hands_at_level, 0) if self.auto_double else None,
            },
            "to_act": self.to_act,
            "current_bet": self.current_bet,
            "legal_bets": self.legal_bets(),
            "next_deal": self.next_deal(),
            "pots": [] if self.awarded else pots,
            "awarded": self.awarded,
            "can_award": self.phase == "complete" and not self.awarded,
            "can_start_hand": not self.hand_active and len(self.seats) >= self.min_players
            and (self.phase != "complete" or self.awarded or not any(p["amount"] for p in pots)),
            "can_set_blinds": not self.hand_active,
            "can_undo": self.can_undo,
            "board": list(self.board),
            "burn": {"count": len(self.burn), "cards": list(self.burn) if viewer.sees_all else None},
            "seats": seats,
            "result": self._result(),
        }
