from datetime import datetime
from typing import Dict, Optional, Set


class DHSession:
    def __init__(self, session_id: str, p: int, g: int):
        self.session_id: str = session_id
        self.p: int = p
        self.g: int = g

        self.devices_ready: Set[str] = set()
        self.public_keys: Dict[str, int] = {}
        self.results: Dict[str, int] = {}

        self.status: str = "IDLE"

        self.started_at: Optional[datetime] = None
        self.last_progress_at: Optional[datetime] = None
        self.failure_reason: Optional[str] = None

        # Prevent duplicate relay / verify actions
        self.relay_sent: bool = False
        self.verification_done: bool = False

    def mark_ready(self, device_id: str) -> None:
        self.devices_ready.add(device_id)
        self.touch_progress()

    def add_public_key(self, device_id: str, key: int) -> None:
        self.public_keys[device_id] = key
        self.touch_progress()

    def add_result(self, device_id: str, secret: int) -> None:
        self.results[device_id] = secret
        self.touch_progress()

    def is_ready(self) -> bool:
        return len(self.devices_ready) == 2

    def has_both_public_keys(self) -> bool:
        return len(self.public_keys) == 2

    def has_both_results(self) -> bool:
        return len(self.results) == 2

    def verify(self) -> bool:
        values = list(self.results.values())
        return len(values) == 2 and values[0] == values[1]

    def set_params(self, p: int, g: int) -> None:
        self.p = p
        self.g = g

    def touch_progress(self) -> None:
        self.last_progress_at = datetime.utcnow()

    def start(self) -> None:
        now = datetime.utcnow()
        self.started_at = now
        self.last_progress_at = now
        self.failure_reason = None
        self.relay_sent = False
        self.verification_done = False

    def fail(self, reason: str) -> None:
        self.status = "VERIFIED_FAIL"
        self.failure_reason = reason
        self.touch_progress()

    def reset_runtime_data(self) -> None:
        self.devices_ready.clear()
        self.public_keys.clear()
        self.results.clear()

        self.status = "IDLE"
        self.started_at = None
        self.last_progress_at = None
        self.failure_reason = None
        self.relay_sent = False
        self.verification_done = False