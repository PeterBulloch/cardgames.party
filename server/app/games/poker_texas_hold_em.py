from ..models import BoardTarget, DealCard, Fold, NewHand, NextStage, ReturnCard, SeatTarget, Unfold
from .game import ActionError, Game
from .hand_evaluator import STANDARD_DECK, best_hand, category_name
from .player import Player

BOARD_LIMIT = {"pre-flop": 0, "flop": 3, "turn": 4, "river": 5, "showdown": 5}
HAND_SIZE = 2
MAX_BURN = 3


class PokerTexasHoldEm(Game):
    key = "texas_hold_em"
    stages = ("pre-flop", "flop", "turn", "river", "showdown")
    min_players = 2
    max_players = 10

    def __init__(self) -> None:
        super().__init__()
        self.seats: list[str] = []
        self.hands: dict[str, list[str]] = {}
        self.folded: set[str] = set()
        self.board: list[str] = []
        self.burn: list[str] = []

    def add_seat(self, member_id: str) -> None:
        if len(self.seats) >= self.max_players:
            raise ActionError("The table is full")
        self.seats.append(member_id)
        self.hands[member_id] = []

    def remove_seat(self, member_id: str) -> None:
        if member_id in self.hands:
            self.seats.remove(member_id)
            del self.hands[member_id]
            self.folded.discard(member_id)

    def _pile_of(self, card: str) -> list[str] | None:
        for pile in (self.board, self.burn, *self.hands.values()):
            if card in pile:
                return pile
        return None

    def _require_seat(self, member_id: str) -> None:
        if member_id not in self.hands:
            raise ActionError("No such seat")

    def apply(self, action: object, actor: Player) -> None:
        if isinstance(action, DealCard):
            self._deal(action)
        elif isinstance(action, ReturnCard):
            self._return(action.card, actor)
        elif isinstance(action, Fold):
            self._require_seat(action.member_id)
            self.folded.add(action.member_id)
        elif isinstance(action, Unfold):
            self._require_seat(action.member_id)
            self.folded.discard(action.member_id)
        elif isinstance(action, NextStage):
            self.next_stage()
        elif isinstance(action, NewHand):
            self.stage_index = 0
            self.board.clear()
            self.burn.clear()
            self.folded.clear()
            for hand in self.hands.values():
                hand.clear()
        else:
            raise ActionError("Unsupported action for this game")

    def _deal(self, action: DealCard) -> None:
        card = action.card
        if card not in STANDARD_DECK:
            raise ActionError("That card is not used in Texas Hold'em")
        if self._pile_of(card) is not None:
            raise ActionError("That card is already on the table")
        if self.current_stage == "showdown":
            raise ActionError("Cannot deal during showdown; start a new hand")

        target = action.target
        if isinstance(target, SeatTarget):
            self._require_seat(target.member_id)
            if target.member_id in self.folded:
                raise ActionError("That player has folded")
            hand = self.hands[target.member_id]
            if len(hand) >= HAND_SIZE:
                raise ActionError("That player already has two cards")
            hand.append(card)
        elif isinstance(target, BoardTarget):
            limit = BOARD_LIMIT[self.current_stage]
            if len(self.board) >= limit:
                raise ActionError(f"The board holds {limit} cards during {self.current_stage}")
            self.board.append(card)
        else:
            if len(self.burn) >= MAX_BURN:
                raise ActionError("The burn pile is full")
            self.burn.append(card)

    def _return(self, card: str, actor: Player) -> None:
        pile = self._pile_of(card)
        # Players may only touch cards they can see, so this cannot probe hidden hands.
        visible = actor.sees_all or pile is self.board or pile is self.hands.get(actor.id)
        if pile is None or not visible:
            raise ActionError("That card is not on the table")
        pile.remove(card)

    def _showdown(self) -> dict:
        live = [seat for seat in self.seats if seat not in self.folded]
        if len(live) == 1:
            return {"complete": True, "winners": live, "results": []}

        contenders = [seat for seat in live if len(self.hands[seat]) == HAND_SIZE]
        if len(self.board) < 5 or not contenders:
            return {"complete": False, "winners": [], "results": []}

        scored = {seat: best_hand(self.hands[seat] + self.board) for seat in contenders}
        top = max(score for score, _ in scored.values())
        return {
            "complete": True,
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
                "folded": folded,
                "card_count": len(hand),
                "cards": list(hand) if visible else None,
            })
        return {
            "stage": self.current_stage,
            "stages": list(self.stages),
            "board_limit": BOARD_LIMIT[self.current_stage],
            "board": list(self.board),
            "burn": {"count": len(self.burn), "cards": list(self.burn) if viewer.sees_all else None},
            "seats": seats,
            "showdown": self._showdown() if showdown else None,
        }
