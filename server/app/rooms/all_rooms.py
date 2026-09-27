import asyncio
import secrets
from datetime import datetime, timedelta

from ..games.player import Player, Role
from ..games.registry import GAMES
from .room import LobbyError, Room, hash_password, now

MAX_LOBBIES = 100
IDLE_LIMIT = timedelta(minutes=60)
# Same message for unknown lobby and bad password, so hidden lobby names cannot be probed.
JOIN_DENIED = "Lobby not found or wrong password"


class AllRooms:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    @staticmethod
    def _key(name: str) -> str:
        return name.casefold()

    async def create_room(
        self, name: str, password: str | None, game: str, max_players: int, display_name: str, role: Role
    ) -> tuple[Room, Player]:
        game_class = GAMES.get(game)
        if game_class is None:
            raise LobbyError(400, "Unknown game")
        if not game_class.min_players <= max_players <= game_class.max_players:
            raise LobbyError(
                400, f"{game_class.label} needs {game_class.min_players}-{game_class.max_players} players"
            )
        if self._key(name) in self._rooms:
            raise LobbyError(409, "A lobby with that name already exists")
        if len(self._rooms) >= MAX_LOBBIES:
            raise LobbyError(503, "Too many lobbies are open; try again later")

        password_hash = None
        if password:
            salt = secrets.token_bytes(16)
            password_hash = (salt, await asyncio.to_thread(hash_password, password, salt))

        # Re-check after the await; another request may have claimed the name meanwhile.
        if self._key(name) in self._rooms:
            raise LobbyError(409, "A lobby with that name already exists")
        room = Room(name, game_class(), max_players, password_hash)
        member = room.add_player(display_name, role)
        self._rooms[self._key(name)] = room
        return room, member

    async def join_room(self, name: str, password: str | None, display_name: str, role: Role) -> tuple[Room, Player]:
        room = self._rooms.get(self._key(name))
        if room is None or not await asyncio.to_thread(room.check_password, password):
            raise LobbyError(403, JOIN_DENIED)
        if self._rooms.get(self._key(name)) is not room:
            raise LobbyError(403, JOIN_DENIED)
        return room, room.add_player(display_name, role)

    def find_by_token(self, token: str) -> tuple[Room, Player] | None:
        for room in self._rooms.values():
            for member in room.members.values():
                if secrets.compare_digest(member.token, token):
                    return room, member
        return None

    def remove_room(self, room: Room) -> None:
        if self._rooms.get(self._key(room.name)) is room:
            del self._rooms[self._key(room.name)]
        room.closed = True

    def pop_expired(self, at: datetime | None = None) -> list[Room]:
        at = at or now()
        expired = [
            room
            for room in self._rooms.values()
            if at - room.last_action_at >= IDLE_LIMIT
            or (room.empty_since is not None and at - room.empty_since >= IDLE_LIMIT)
        ]
        for room in expired:
            self.remove_room(room)
        return expired