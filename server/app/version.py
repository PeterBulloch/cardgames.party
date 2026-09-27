import os
from pathlib import Path

_HERE = Path(__file__).resolve()
# VERSION sits at the repo root in development and beside app/ in the container image.
_CANDIDATES = (_HERE.parents[1] / "VERSION", _HERE.parents[2] / "VERSION")


def _read_version() -> str:
    if override := os.getenv("CARDS_VERSION"):
        return override
    for path in _CANDIDATES:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    return "unknown"


__version__ = _read_version()
