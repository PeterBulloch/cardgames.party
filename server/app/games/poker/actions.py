from typing import Annotated, Literal, Union

from pydantic import Field, TypeAdapter

from ...models import CardCode, MemberId, Strict


class StartHand(Strict):
    type: Literal["start_hand"]


class DealCard(Strict):
    """The server decides where the card goes: the next seat, the burn pile or the board."""

    type: Literal["deal_card"]
    card: CardCode


class BettingAction(Strict):
    """A betting decision for the player whose turn it is; any acting member may submit it."""

    type: Literal["fold", "check", "call", "bet", "raise"]
    member_id: MemberId


TexasHoldEmAction = TypeAdapter(
    Annotated[Union[StartHand, DealCard, BettingAction], Field(discriminator="type")]
)
