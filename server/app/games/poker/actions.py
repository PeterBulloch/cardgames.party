from typing import Annotated, Literal, Union

from pydantic import Field, TypeAdapter

from ...models import CardCode, MemberId, Strict

Chips = Annotated[int, Field(ge=0, le=1_000_000_000)]


class StartHand(Strict):
    type: Literal["start_hand"]


class DealCard(Strict):
    """The server decides where the card goes: the next seat, the burn pile or the board."""

    type: Literal["deal_card"]
    card: CardCode


class BettingAction(Strict):
    """A betting decision for the player whose turn it is; any acting member may submit it."""

    type: Literal["fold", "check", "call"]
    member_id: MemberId


class SizedBet(Strict):
    type: Literal["bet", "raise"]
    member_id: MemberId
    # Total the player will have in front of them this street, not the increment.
    amount: Chips


class SetChips(Strict):
    type: Literal["set_chips"]
    member_id: MemberId
    chips: Chips


class SetPot(Strict):
    type: Literal["set_pot"]
    index: int = Field(ge=0, le=20)
    amount: Chips


class SetBlinds(Strict):
    type: Literal["set_blinds"]
    small: Chips
    big: Chips
    auto_double: bool = False
    double_every: int = Field(default=10, ge=1, le=1000)


class AwardPots(Strict):
    type: Literal["award_pots"]


TexasHoldEmAction = TypeAdapter(
    Annotated[
        Union[StartHand, DealCard, BettingAction, SizedBet, SetChips, SetPot, SetBlinds, AwardPots],
        Field(discriminator="type"),
    ]
)
