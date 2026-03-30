from datetime import datetime
from typing import Dict, Optional
import asyncio

from models import DeviceRecord


class DeviceManager:
    def __init__(self) -> None:
        self.devices: Dict[str, DeviceRecord] = {}

    def register_device(
        self,
        device_id: str,
        writer: asyncio.StreamWriter,
        addr: str,
        firmware_version: Optional[str] = None,
    ) -> tuple[bool, str]:
        existing = self.devices.get(device_id)

        if existing is not None:
            # Reject duplicate if old connection is still active
            if not existing.writer.is_closing():
                return False, f"Device ID '{device_id}' is already connected"

        record = DeviceRecord(
            device_id=device_id,
            writer=writer,
            addr=addr,
            firmware_version=firmware_version,
            connected_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            state="CONNECTED",
        )

        self.devices[device_id] = record
        return True, f"Registered {device_id}"

    def unregister_by_writer(self, writer: asyncio.StreamWriter) -> Optional[str]:
        for device_id, record in list(self.devices.items()):
            if record.writer is writer:
                del self.devices[device_id]
                return device_id
        return None

    def touch(self, device_id: str) -> None:
        record = self.devices.get(device_id)
        if record:
            record.touch()

    def get_device(self, device_id: str) -> Optional[DeviceRecord]:
        return self.devices.get(device_id)

    def list_devices(self) -> list[DeviceRecord]:
        return list(self.devices.values())

    def print_devices(self) -> None:
        print("\n[DeviceManager] Connected devices:")
        if not self.devices:
            print("  (none)")
            return

        for record in self.devices.values():
            print(
                f"  - {record.device_id} | {record.addr} | "
                f"state={record.state} | last_seen={record.last_seen.isoformat()} | "
                f"firmware={record.firmware_version}"
            )