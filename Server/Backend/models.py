from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import asyncio


@dataclass
class DeviceRecord:
    device_id: str
    writer: asyncio.StreamWriter
    addr: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    state: str = "CONNECTED"
    session_id: Optional[str] = None
    firmware_version: Optional[str] = None

    def touch(self) -> None:
        self.last_seen = datetime.utcnow()