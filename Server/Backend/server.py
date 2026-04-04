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
        self.event_log = []
        self.gui_api = None

    def attach_gui_api(self, gui_api):
        self.gui_api = gui_api

    def log_event(self, source, event_type, message, data=None):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "event_type": event_type,
            "message": message,
            "data": data or {},
        }
        self.event_log.append(event)

        if source == "BACKEND":
            logger.info(f"{event_type}: {message}")
        else:
            logger.event(source, f"{event_type}: {message}")

        if self.gui_api:
            asyncio.create_task(
                self.gui_api.broadcast({
                    "type": "event",
                    "payload": event,
                })
            )
            asyncio.create_task(
                self.gui_api.broadcast({
                    "type": "snapshot",
                    "payload": self.build_gui_snapshot(),
                })
            )

    def build_gui_snapshot(self):
        # ---- Devices ----
        devices = []
        for record in self.device_manager.list_devices():
            devices.append({
                "device_id": record.device_id,
                "addr": record.addr,
                "state": record.state,
                "last_seen": record.last_seen.isoformat() if record.last_seen else None,
                "firmware_version": record.firmware_version,
                "session_id": record.session_id,
            })

        # ---- Session safety ----
        if not self.session:
            return {
                "devices": devices,
                "session": None,
                "events": self.event_log[-100:],
            }

        # ---- Verification status ----
        if self.session.status == "VERIFIED_OK":
            verification_status = "PASS"
        elif self.session.status == "VERIFIED_FAIL":
            verification_status = "FAIL"
        else:
            verification_status = "PENDING"

        # ---- Derive current step (for visualization flow) ----
        current_step = "IDLE"

        if self.session.status in ["READY_WAIT"]:
            current_step = "WAITING_FOR_DEVICES"

        elif self.session.status in ["PARAMS_SENT"]:
            current_step = "PARAMS_DISTRIBUTED"

        elif self.session.status in ["EXCHANGE_STARTED"]:
            current_step = "PRIVATE_KEYS_GENERATED"

        elif self.session.status in ["COLLECTING_PUBLIC_KEYS"]:
            current_step = "PUBLIC_KEYS_COMPUTED"

        elif self.session.status in ["RELAYING_PUBLIC_KEYS"]:
            current_step = "PUBLIC_KEYS_EXCHANGED"

        elif self.session.status in ["COLLECTING_RESULTS"]:
            current_step = "SHARED_SECRET_COMPUTED"

        elif self.session.status in ["VERIFIED_OK", "VERIFIED_FAIL"]:
            current_step = "VERIFICATION_COMPLETE"

        # ---- Session ----
        session = {
            "session_id": self.session.session_id,
            "p": self.session.p,
            "g": self.session.g,
            "status": self.session.status,

            # DH data
            "public_keys": self.session.public_keys,
            "results": self.session.results,
            "devices_ready": list(self.session.devices_ready),

            # NEW fields for GUI
            "verification_status": verification_status,
            "current_step": current_step,

            # Helpful flags
            "has_all_public_keys": len(self.session.public_keys) >= 2,
            "has_all_results": len(self.session.results) >= 2,
        }

        return {
            "devices": devices,
            "session": session,
            "events": self.event_log[-100:],
        }

    async def start(self) -> None:
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
        )

        addr_list = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
        self.log_event("BACKEND", "SERVER_START", f"Listening on {addr_list}")

        asyncio.create_task(self.device_monitor())

        async with server:
            await server.serve_forever()

    async def device_monitor(self):
        while True:
            self.device_manager.print_devices()
            await asyncio.sleep(5)

    async def start_session_from_gui(self, p: int, g: int):
        if not self.device_manager.has_required_devices():
            self.log_event("BACKEND", "SESSION_START_REJECTED", "Both ESP32-A and ESP32-B must be connected")
            return

        self.session.reset_runtime_data()
        self.session.set_params(p, g)
        self.session.session_id = f"session-{int(datetime.utcnow().timestamp())}"
        self.session.status = "RESETTING"

        self.log_event(
            "BACKEND",
            "SESSION_START",
            f"Starting session {self.session.session_id}",
            {"p": p, "g": g},
        )

        # Reset boards first so they return to WAITING_PARAMS
        await self.broadcast_json({
            "type": "RESET",
            "session_id": self.session.session_id,
        })

        await asyncio.sleep(1)

        self.session.status = "PARAMS_SENT"
        await self.broadcast_json({
            "type": "SET_PARAMS",
            "session_id": self.session.session_id,
            "p": p,
            "g": g,
        })

        await asyncio.sleep(1)

        self.session.status = "EXCHANGE_STARTED"
        await self.broadcast_json({
            "type": "START_EXCHANGE",
            "session_id": self.session.session_id,
        })

    async def reset_session_from_gui(self):
        self.log_event("BACKEND", "SESSION_RESET", "Reset requested from GUI")

        await self.broadcast_json({
            "type": "RESET",
            "session_id": self.session.session_id,
        })

        self.session.reset_runtime_data()

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername")
        addr = f"{peer[0]}:{peer[1]}" if peer else "unknown"

        self.log_event("BACKEND", "CONN", f"Client connected from {addr}")

        registered_device_id: Optional[str] = None

        try:
            while True:
                raw = await reader.readline()

                if not raw:
                    self.log_event("BACKEND", "DISCONNECT", f"Client disconnected from {addr}")
                    break

                line = raw.decode(errors="replace").strip()
                if not line:
                    continue

                self.log_event("BACKEND", "RX", f"{addr} -> {line}")

                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    self.log_event("BACKEND", "MALFORMED", f"{addr}: {line}")
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
                    device_id = msg.get("device_id")
                    state = msg.get("state")
                    session_id = msg.get("session_id")

                    if registered_device_id:
                        self.device_manager.touch(registered_device_id)

                    if device_id and state:
                        self.device_manager.update_device_state(device_id, state, session_id)

                    self.log_event(
                        msg.get("device_id", "DEVICE"),
                        msg.get("event", "EVENT"),
                        f"State={msg.get('state', '-')}",
                        msg,
                    )

                else:
                    if registered_device_id:
                        self.device_manager.touch(registered_device_id)

                    self.log_event("BACKEND", "UNKNOWN_MSG", f"type={msg_type}")

        except ConnectionResetError:
            self.log_event("BACKEND", "ERROR", f"Connection reset by {addr}")
        except asyncio.IncompleteReadError:
            self.log_event("BACKEND", "ERROR", f"Incomplete read from {addr}")
        finally:
            removed = self.device_manager.unregister_by_writer(writer)
            if removed:
                self.log_event("BACKEND", "DEVICE_REMOVED", f"{removed}")
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
            self.log_event("BACKEND", "REGISTER_REJECTED", info)
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

        self.log_event("BACKEND", "REGISTER", f"{device_id} registered", {"addr": addr})
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
        if self.session.status == "IDLE":
            self.session.status = "READY_WAIT"

        return True, device_id

    async def broadcast_json(self, payload: dict) -> None:
        for record in self.device_manager.list_devices():
            await self.send_json(record.writer, payload)

    async def handle_public_key(self, msg: dict) -> None:
        device_id = msg.get("device_id")
        session_id = msg.get("session_id")
        public_key = msg.get("public_key")

        if not device_id or not session_id or public_key is None:
            self.log_event("BACKEND", "WARN", "Invalid PUBLIC_KEY message", msg)
            return

        if session_id != self.session.session_id:
            self.log_event("BACKEND", "WARN", f"Ignoring PUBLIC_KEY for stale session {session_id}")
            return

        self.session.add_public_key(device_id, public_key)
        self.session.status = "COLLECTING_PUBLIC_KEYS"

        self.log_event(device_id, "PUBLIC_KEY", f"{public_key}")

        if self.session.has_both_public_keys():
            self.session.status = "RELAYING_PUBLIC_KEYS"
            self.log_event("BACKEND", "RELAY", "Relaying public keys between devices")

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
            self.log_event("BACKEND", "WARN", "Invalid RESULT message", msg)
            return

        if session_id != self.session.session_id:
            self.log_event("BACKEND", "WARN", f"Ignoring RESULT for stale session {session_id}")
            return

        self.session.add_result(device_id, shared_secret)
        self.session.status = "COLLECTING_RESULTS"

        self.log_event(device_id, "RESULT", f"{shared_secret}")

        if self.session.has_both_results():
            if self.session.verify():
                self.session.status = "VERIFIED_OK"
                self.log_event("BACKEND", "VERIFY_OK", "Shared secret match", {
                    "secret": shared_secret
                })
            else:
                self.session.status = "VERIFIED_FAIL"
                a_secret = self.session.results.get("ESP32-A")
                b_secret = self.session.results.get("ESP32-B")
                self.log_event("BACKEND", "VERIFY_FAIL", "Secrets mismatch", {
                    "A": a_secret,
                    "B": b_secret
                })

    async def send_json(self, writer: asyncio.StreamWriter, payload: dict) -> None:
        line = json.dumps(payload) + "\n"
        writer.write(line.encode())
        await writer.drain()

        self.log_event("BACKEND", "TX", line.strip())