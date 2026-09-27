import asyncio
import contextlib
import json
from dataclasses import dataclass

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from .games.game import ActionError
from .games.player import Player
from .models import ClientMessage, Hello, Leave
from .rooms.all_rooms import AllRooms
from .rooms.room import Room

HELLO_TIMEOUT_S = 10
MAX_MESSAGE_BYTES = 4096
CLOSE_POLICY = 1008
CLOSE_GONE = 4404


@dataclass(eq=False)
class Connection:
    websocket: WebSocket
    member: Player
    last_seq: int = 0

    async def send(self, payload: dict) -> None:
        with contextlib.suppress(Exception):
            await self.websocket.send_json(payload)

    async def close(self, code: int, reason: str = "") -> None:
        with contextlib.suppress(Exception):
            await self.websocket.close(code=code, reason=reason)


async def broadcast(room: Room) -> None:
    await asyncio.gather(*(conn.send(room.snapshot_for(conn.member)) for conn in list(room.connections)))


async def close_room(room: Room, reason: str) -> None:
    await asyncio.gather(*(conn.close(CLOSE_GONE, reason) for conn in list(room.connections)))


async def _receive_text(websocket: WebSocket) -> str:
    message = await websocket.receive()
    if message["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(message.get("code", 1000))
    text = message.get("text")
    if text is None:
        raise ValueError("Only text frames are accepted")
    return text


async def _authenticate(websocket: WebSocket, rooms: AllRooms) -> tuple[Room, Player] | None:
    try:
        raw = await asyncio.wait_for(_receive_text(websocket), HELLO_TIMEOUT_S)
        hello = Hello.model_validate_json(raw)
    except (asyncio.TimeoutError, ValueError, ValidationError):
        await websocket.close(code=CLOSE_POLICY, reason="Expected hello")
        return None
    found = rooms.find_by_token(hello.token)
    if found is None:
        await websocket.close(code=CLOSE_GONE, reason="Unknown or expired session")
    return found


async def handle_socket(websocket: WebSocket, rooms: AllRooms) -> None:
    await websocket.accept()
    found = await _authenticate(websocket, rooms)
    if found is None:
        return
    room, member = found
    conn = Connection(websocket, member)

    async with room.lock:
        room.connect(conn)
        await broadcast(room)

    try:
        while True:
            try:
                raw = await _receive_text(websocket)
            except ValueError as error:
                await conn.send({"type": "error", "seq": None, "message": str(error)})
                continue
            if room.closed or member.id not in room.members:
                break
            if len(raw) > MAX_MESSAGE_BYTES:
                await conn.send({"type": "error", "seq": None, "message": "Message too large"})
                continue
            await _handle_message(room, conn, raw)
            if member.id not in room.members:
                break
    except WebSocketDisconnect:
        pass
    finally:
        async with room.lock:
            room.disconnect(conn)
            if not room.closed:
                await broadcast(room)
        await conn.close(CLOSE_GONE if member.id not in room.members else 1000)


async def _handle_message(room: Room, conn: Connection, raw: str) -> None:
    try:
        message = ClientMessage.model_validate_json(raw)
    except ValidationError as error:
        seq = None
        with contextlib.suppress(Exception):
            seq = json.loads(raw).get("seq")
        await conn.send({"type": "error", "seq": seq if isinstance(seq, int) else None,
                         "message": error.errors()[0]["msg"]})
        return

    if message.lobby != room.id or message.player != conn.member.id:
        await conn.send({"type": "error", "seq": message.seq, "message": "Lobby or player does not match session"})
        return
    # WebSocket frames arrive in order, so a non-increasing seq is a replay or duplicate.
    if message.seq <= conn.last_seq:
        await conn.send({"type": "error", "seq": message.seq, "message": "Stale or duplicate message ignored"})
        return
    conn.last_seq = message.seq

    async with room.lock:
        try:
            action = room.apply(conn.member, message.action)
        except ActionError as error:
            await conn.send({"type": "error", "seq": message.seq, "message": str(error)})
            return
        await conn.send({"type": "ack", "seq": message.seq, "version": room.version})
        if isinstance(action, Leave):
            await asyncio.gather(*(
                other.close(CLOSE_GONE, "Left lobby")
                for other in list(room.connections)
                if other.member is conn.member and other is not conn
            ))
        await broadcast(room)
