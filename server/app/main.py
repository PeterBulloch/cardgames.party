import asyncio
import contextlib
import os
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .controller import close_room, handle_socket
from .models import CreateLobbyIn, JoinLobbyIn, JoinOut, ScanIn, ScanOut
from .rooms.all_rooms import AllRooms
from .rooms.room import LobbyError
from .store import ScanStore

DIST_DIR = Path(
    os.getenv("CARDS_DIST_DIR", Path(__file__).resolve().parents[2] / "web" / "dist")
)
CLEANUP_INTERVAL_S = 60

# Matches the Vite dev server on localhost or on a dashed local-ip.sh host.
DEV_ORIGIN_REGEX = (
    r"^https?://(localhost|127\.0\.0\.1|"
    r"(?:\d{1,3}-){3}\d{1,3}\.local-ip\.sh):5173$"
)

store = ScanStore()
rooms = AllRooms()


async def _expire_rooms() -> None:
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_S)
        for room in rooms.pop_expired():
            await close_room(room, "Lobby expired")


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_expire_rooms())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="Cards", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=DEV_ORIGIN_REGEX,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/lobbies", response_model=JoinOut, status_code=201)
async def create_lobby(body: CreateLobbyIn) -> JoinOut:
    try:
        room, member = await rooms.create_room(
            body.name, body.password, body.game, body.max_players, body.display_name, body.role
        )
    except LobbyError as error:
        raise HTTPException(error.status, error.message) from None
    return JoinOut(lobby_id=room.id, member_id=member.id, token=member.token)


@app.post("/api/lobbies/join", response_model=JoinOut)
async def join_lobby(body: JoinLobbyIn) -> JoinOut:
    try:
        room, member = await rooms.join_room(body.name, body.password, body.display_name, body.role)
    except LobbyError as error:
        raise HTTPException(error.status, error.message) from None
    return JoinOut(lobby_id=room.id, member_id=member.id, token=member.token)


@app.websocket("/api/ws")
async def lobby_socket(websocket: WebSocket) -> None:
    await handle_socket(websocket, rooms)


@app.get("/api/scans", response_model=list[ScanOut])
async def list_scans() -> list[ScanOut]:
    return await store.list()


@app.post("/api/scans", response_model=ScanOut, status_code=201)
async def create_scan(scan: ScanIn) -> ScanOut:
    return await store.add(scan)


@app.delete("/api/scans", status_code=204)
async def clear_scans() -> Response:
    await store.clear()
    return Response(status_code=204)


class SpaStaticFiles(StaticFiles):
    """Serves index.html for unknown paths so client-side routes like /scanner survive a reload."""

    async def get_response(self, path: str, scope):  # type: ignore[override]
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as error:
            if error.status_code != 404 or path.startswith("api"):
                raise
            return await super().get_response("index.html", scope)


# Mounted last so the API routes above take precedence over the catch-all.
if DIST_DIR.is_dir():
    app.mount("/", SpaStaticFiles(directory=DIST_DIR, html=True), name="spa")
