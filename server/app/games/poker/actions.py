from typing import Annotated, Literal, Union

from pydantic import Field, TypeAdapter

from ...models import CardCode, MemberId, Strict


class SeatTarget(Strict):
    kind: Literal["seat"]
    member_id: MemberId


class BoardTarget(Strict):
    kind: Literal["board"]


class BurnTarget(Strict):
    kind: Literal["burn"]


Target = Annotated[Union[SeatTarget, BoardTarget, BurnTarget], Field(discriminator="kind")]


class DealCard(Strict):
    type: Literal["deal_card"]
    card: CardCode
    target: Target


class ReturnCard(Strict):
    type: Literal["return_card"]
    card: CardCode


class Fold(Strict):
    type: Literal["fold"]
    member_id: MemberId


class Unfold(Strict):
    type: Literal["unfold"]
    member_id: MemberId


class NextStage(Strict):
    type: Literal["next_stage"]


class NewHand(Strict):
    type: Literal["new_hand"]


TexasHoldEmAction = TypeAdapter(
    Annotated[
        Union[DealCard, ReturnCard, Fold, Unfold, NextStage, NewHand],
        Field(discriminator="type"),
    ]
)
