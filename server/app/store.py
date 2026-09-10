import asyncio
from collections import deque
from datetime import datetime, timezone
from itertools import count

from .models import ScanIn, ScanOut

MAX_SCANS = 500


class ScanStore:
    """In-memory ring of recent scans. Bounded so an unattended page cannot grow the process."""

    def __init__(self, maxlen: int = MAX_SCANS) -> None:
        self._scans: deque[ScanOut] = deque(maxlen=maxlen)
        self._lock = asyncio.Lock()
        self._ids = count(1)

    async def add(self, scan: ScanIn) -> ScanOut:
        async with self._lock:
            record = ScanOut(
                id=next(self._ids),
                serialNumber=scan.serialNumber,
                records=scan.records,
                receivedAt=datetime.now(timezone.utc),
            )
            self._scans.append(record)
            return record

    async def list(self) -> list[ScanOut]:
        async with self._lock:
            return list(self._scans)

    async def clear(self) -> None:
        async with self._lock:
            self._scans.clear()
