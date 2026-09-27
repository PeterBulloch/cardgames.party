from datetime import datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter

from .games.player import Role


class NdefRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recordType: str = Field(max_length=64)
    mediaType: str | None = Field(default=None, max_length=128)
    text: str | None = Field(default=None, max_length=2048)


class ScanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    serialNumber: str = Field(min_length=1, max_length=64)
    records: list[NdefRecord] = Field(default_factory=list, max_length=16)


class ScanOut(ScanIn):
    id: int
    receivedAt: datetime


LobbyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=24)]
Password = Annotated[str, StringConstraints(max_length=128)]
CardCode = Annotated[str, StringConstraints(pattern=r"^CARD_[A-Z]+(_[A-Z]+)?$", max_length=32)]
MemberId = Annotated[str, StringConstraints(max_length=32)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateLobbyIn(Strict):
    name: LobbyName
    password: Password | None = None
    game: str = Field(default="texas_hold_em", max_length=32)
    max_players: int = Field(ge=1, le=64)
    display_name: DisplayName
    role: Role


class JoinLobbyIn(Strict):
    name: LobbyName
    password: Password | None = None
    display_name: DisplayName
    role: Role


class JoinOut(BaseModel):
    lobby_id: str
    member_id: str
    token: str


class SetView(Strict):
    type: Literal["set_view"]
    hide_hands: bool


class Leave(Strict):
    type: Literal["leave"]


LobbyAction = TypeAdapter(Annotated[Union[SetView, Leave], Field(discriminator="type")])
LOBBY_ACTION_TYPES = frozenset({"set_view", "leave"})


class Hello(Strict):
    type: Literal["hello"]
    token: Annotated[str, StringConstraints(max_length=128)]


class ClientMessage(Strict):
    lobby: str = Field(max_length=32)
    player: MemberId
    seq: int = Field(ge=1)
    sent_at: datetime | None = None
    # Validated later by the lobby or by the lobby's game, which owns its own action schema.
    action: dict[str, Any]
