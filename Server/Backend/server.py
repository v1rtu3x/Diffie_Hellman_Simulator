import asyncio
import json
from datetime import datetime
from typing import Optional

from device_manager import DeviceManager
import logger


class BackendServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.device_manager = DeviceManager()

    async def start(self) -> None:
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
        )

        addr_list = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
        logger.info(f"Server listening on {addr_list}")

        # Periodic device monitor
        asyncio.create_task(self.device_monitor())

        async with server:
            await server.serve_forever()

    async def device_monitor(self):
        while True:
            self.device_manager.print_devices()
            await asyncio.sleep(5)

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername")
        addr = f"{peer[0]}:{peer[1]}" if peer else "unknown"

        logger.event("CONN", f"Client connected from {addr}")

        registered_device_id: Optional[str] = None

        try:
            while True:
                raw = await reader.readline()

                if not raw:
                    logger.event("DISCONNECT", f"Client disconnected from {addr}")
                    break

                line = raw.decode(errors="replace").strip()
                if not line:
                    continue

                logger.event("RX", f"{addr} -> {line}")

                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    logger.warn(f"Malformed message from {addr}: {line}")
                    await self.send_json(
                        writer,
                        {
                            "type": "ERROR",
                            "error_code": "INVALID_JSON",
                            "message": "Malformed JSON",
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    continue

                msg_type = msg.get("type")

                if msg_type == "REGISTER":
                    ok, registered_device_id = await self.handle_register(msg, writer, addr)
                    if not ok:
                        break
                else:
                    if registered_device_id:
                        self.device_manager.touch(registered_device_id)

                    logger.warn(f"Unhandled message type: {msg_type}")

        except ConnectionResetError:
            logger.warn(f"Connection reset by {addr}")
        except asyncio.IncompleteReadError:
            logger.warn(f"Incomplete read from {addr}")
        finally:
            removed = self.device_manager.unregister_by_writer(writer)
            if removed:
                logger.event("DISCONNECT", f"Device removed: {removed}")
                self.device_manager.print_devices()

            writer.close()
            await writer.wait_closed()

    async def handle_register(
        self,
        msg: dict,
        writer: asyncio.StreamWriter,
        addr: str,
    ) -> tuple[bool, Optional[str]]:
        device_id = msg.get("device_id")
        firmware_version = msg.get("firmware_version")
        seq = msg.get("seq", 0)

        if not device_id:
            await self.send_json(
                writer,
                {
                    "type": "ERROR",
                    "error_code": "MISSING_DEVICE_ID",
                    "message": "REGISTER missing device_id",
                    "seq": seq,
                },
            )
            return False, None

        ok, info = self.device_manager.register_device(
            device_id=device_id,
            writer=writer,
            addr=addr,
            firmware_version=firmware_version,
        )

        if not ok:
            logger.warn(f"Registration rejected: {info}")

            await self.send_json(
                writer,
                {
                    "type": "ERROR",
                    "error_code": "DUPLICATE_DEVICE_ID",
                    "message": info,
                    "device_id": device_id,
                    "seq": seq,
                },
            )

            writer.close()
            return False, None

        logger.event("REGISTER", f"{device_id} registered ({addr})")

        self.device_manager.print_devices()

        await self.send_json(
            writer,
            {
                "type": "REGISTER_ACK",
                "device_id": device_id,
                "seq": seq,
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        return True, device_id

    async def send_json(self, writer: asyncio.StreamWriter, payload: dict) -> None:
        line = json.dumps(payload) + "\n"
        writer.write(line.encode())
        await writer.drain()

        logger.event("TX", line.strip())