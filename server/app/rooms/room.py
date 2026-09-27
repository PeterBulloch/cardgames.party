import asyncio
import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from ..games.game import ActionError, Game
from ..games.player import Player, Role
from ..models import LOBBY_ACTION_TYPES, LobbyAction, Leave, SetView

MAX_MEMBERS = 30
SCRYPT = {"n": 2**14, "r": 8, "p": 1}


class LobbyError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)


class Room:
    """A lobby: its members, one game instance, and the sockets watching it."""

    def __init__(self, name: str, game: Game, max_players: int, password_hash: tuple[bytes, bytes] | None) -> None:
        self.id = secrets.token_hex(6)
        self.name = name
        self.game = game
        self.max_players = max_players
        self._password_hash = password_hash
        self.members: dict[str, Player] = {}
        self.connections: set[Any] = set()
        self.lock = asyncio.Lock()
        self.closed = False
        self.version = 0
        self.updated_at = now()
        self.last_action_at = self.updated_at
        self.empty_since: datetime | None = self.updated_at

    @property
    def has_password(self) -> bool:
        return self._password_hash is not None

    def check_password(self, password: str | None) -> bool:
        if self._password_hash is None:
            return True
        salt, expected = self._password_hash
        return hmac.compare_digest(hash_password(password or "", salt), expected)

    def touch(self, activity: bool = True) -> None:
        self.version += 1
        self.updated_at = now()
        if activity:
            self.last_action_at = self.updated_at

    def add_player(self, name: str, role: Role) -> Player:
        if any(member.name.casefold() == name.casefold() for member in self.members.values()):
            raise LobbyError(409, "That name is already taken in this lobby")
        if len(self.members) >= MAX_MEMBERS:
            raise LobbyError(409, "This lobby is full")
        seated = sum(member.is_seated for member in self.members.values())
        if role == "player" and seated >= self.max_players:
            raise LobbyError(409, "All player seats are taken")

        member = Player(name=name, role=role)
        self.game.add_member(member)
        self.members[member.id] = member
        self.touch()
        return member

    def remove_player(self, member: Player) -> None:
        if self.members.pop(member.id, None) is not None:
            self.game.remove_member(member)
            self.touch()

    def connect(self, connection: Any) -> None:
        self.connections.add(connection)
        connection.member.connections += 1
        self.empty_since = None
        self.touch(activity=False)

    def disconnect(self, connection: Any) -> None:
        if connection in self.connections:
            self.connections.remove(connection)
            connection.member.connections -= 1
            if not self.connections:
                self.empty_since = now()
            self.touch(activity=False)

    def apply(self, member: Player, raw: dict[str, Any]) -> object:
        if raw.get("type") in LOBBY_ACTION_TYPES:
            try:
                action = LobbyAction.validate_python(raw)
            except ValidationError as error:
                raise ActionError(error.errors()[0]["msg"]) from None
        elif not member.can_act:
            raise ActionError("Observers cannot take actions")
        else:
            action = self.game.parse_action(raw)

        if isinstance(action, SetView):
            if member.role != "observer":
                raise ActionError("Only observers can change their view")
            member.hide_hands = action.hide_hands
        elif isinstance(action, Leave):
            self.remove_player(member)
            return action
        else:
            self.game.perform(action, member)
        self.touch()
        return action

    def snapshot_for(self, member: Player) -> dict:
        return {
            "type": "state",
            "version": self.version,
            "updated_at": self.updated_at.isoformat(),
            "state": {
                "lobby": {
                    "id": self.id,
                    "name": self.name,
                    "game": self.game.key,
                    "max_players": self.max_players,
                    "has_password": self.has_password,
                },
                "you": {
                    "member_id": member.id,
                    "name": member.name,
                    "role": member.role,
                    "hide_hands": member.hide_hands,
                    "can_act": member.can_act,
                },
                "members": [
                    {"member_id": m.id, "name": m.name, "role": m.role, "connected": m.connections > 0}
                    for m in self.members.values()
                ],
                "game": self.game.view_for(member),
            },
        }