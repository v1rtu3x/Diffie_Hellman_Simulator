import asyncio
import json
from datetime import datetime
from typing import Optional

from device_manager import DeviceManager
from dhsession import DHSession
import logger


class BackendServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.device_manager = DeviceManager()
        self.session = DHSession("test-session", 23, 5)

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

                elif msg_type == "PUBLIC_KEY":
                    if registered_device_id:
                        self.device_manager.touch(registered_device_id)
                    await self.handle_public_key(msg)

                elif msg_type == "RESULT":
                    if registered_device_id:
                        self.device_manager.touch(registered_device_id)
                    await self.handle_result(msg)

                elif msg_type == "EVENT":
                    if registered_device_id:
                        self.device_manager.touch(registered_device_id)
                    logger.event("EVENT", f"{addr} -> {line}")

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
                self.session.reset_runtime_data()

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

        self.session.mark_ready(device_id)
        self.session.status = "READY_WAIT"

        await self.maybe_start_test_session()

        return True, device_id
    
    async def maybe_start_test_session(self) -> None:
        if self.session.status != "READY_WAIT":
            return

        if not self.device_manager.has_required_devices():
            return

        if not self.session.is_ready():
            return

        logger.info("Both ESP32-A and ESP32-B are connected. Starting test session.")

        self.session.status = "PARAMS_SENT"

        await self.broadcast_json(
            {
                "type": "SET_PARAMS",
                "session_id": self.session.session_id,
                "p": self.session.p,
                "g": self.session.g,
            }
        )

        await asyncio.sleep(1)

        self.session.status = "EXCHANGE_STARTED"

        await self.broadcast_json(
            {
                "type": "START_EXCHANGE",
                "session_id": self.session.session_id,
            }
        )

    async def broadcast_json(self, payload: dict) -> None:
        for record in self.device_manager.list_devices():
            await self.send_json(record.writer, payload)

    async def handle_public_key(self, msg: dict) -> None:
        device_id = msg.get("device_id")
        session_id = msg.get("session_id")
        public_key = msg.get("public_key")

        if not device_id or not session_id or public_key is None:
            logger.warn(f"Invalid PUBLIC_KEY message: {msg}")
            return

        if session_id != self.session.session_id:
            logger.warn(f"Ignoring PUBLIC_KEY for stale session: {session_id}")
            return

        self.session.add_public_key(device_id, public_key)
        self.session.status = "COLLECTING_PUBLIC_KEYS"

        logger.event("PUBLIC_KEY", f"{device_id} -> {public_key}")

        if self.session.has_both_public_keys():
            logger.info("Both public keys received. Relaying peer keys.")
            self.session.status = "RELaying_PUBLIC_KEYS"

            dev_a = self.device_manager.get_device("ESP32-A")
            dev_b = self.device_manager.get_device("ESP32-B")

            if dev_a and dev_b:
                await self.send_json(
                    dev_a.writer,
                    {
                        "type": "PEER_PUBLIC_KEY",
                        "session_id": self.session.session_id,
                        "peer_device_id": "ESP32-B",
                        "public_key": self.session.public_keys["ESP32-B"],
                    },
                )

                await self.send_json(
                    dev_b.writer,
                    {
                        "type": "PEER_PUBLIC_KEY",
                        "session_id": self.session.session_id,
                        "peer_device_id": "ESP32-A",
                        "public_key": self.session.public_keys["ESP32-A"],
                    },
                )

    async def handle_result(self, msg: dict) -> None:
        device_id = msg.get("device_id")
        session_id = msg.get("session_id")
        shared_secret = msg.get("shared_secret")

        if not device_id or not session_id or shared_secret is None:
            logger.warn(f"Invalid RESULT message: {msg}")
            return

        if session_id != self.session.session_id:
            logger.warn(f"Ignoring RESULT for stale session: {session_id}")
            return

        self.session.add_result(device_id, shared_secret)
        self.session.status = "COLLECTING_RESULTS"

        logger.event("RESULT", f"{device_id} -> {shared_secret}")

        if self.session.has_both_results():
            if self.session.verify():
                self.session.status = "VERIFIED_OK"
                logger.info(f"Shared secret match: {shared_secret}")
            else:
                self.session.status = "VERIFIED_FAIL"
                a_secret = self.session.results.get("ESP32-A")
                b_secret = self.session.results.get("ESP32-B")
                logger.error(f"Shared secret mismatch: A={a_secret}, B={b_secret}")

    async def send_json(self, writer: asyncio.StreamWriter, payload: dict) -> None:
        line = json.dumps(payload) + "\n"
        writer.write(line.encode())
        await writer.drain()

        logger.event("TX", line.strip())
        