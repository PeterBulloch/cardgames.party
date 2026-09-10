import os
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import ScanIn, ScanOut
from .store import ScanStore

DIST_DIR = Path(
    os.getenv("CARDS_DIST_DIR", Path(__file__).resolve().parents[2] / "web" / "dist")
)

# Matches the Vite dev server on localhost or on a dashed local-ip.sh host.
DEV_ORIGIN_REGEX = (
    r"^https?://(localhost|127\.0\.0\.1|"
    r"(?:\d{1,3}-){3}\d{1,3}\.local-ip\.sh):5173$"
)

app = FastAPI(title="Cards NFC Scanner")
store = ScanStore()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=DEV_ORIGIN_REGEX,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


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


# Mounted last so the API routes above take precedence over the catch-all.
if DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="spa")
