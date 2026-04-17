import asyncio
import json
from datetime import datetime
from typing import Optional

from device_manager import DeviceManager
from dhsession import DHSession
import logger


DEBUG_LEVEL = 2
STEP_DELAY_SECONDS = 2.0
RELAY_DELAY_SECONDS = 2.0
SESSION_TIMEOUT_SECONDS = 20


class BackendServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.device_manager = DeviceManager()

        self.session_seq = 0
        self.session = DHSession("session-0000", 23, 5)

        self.event_log = []
        self.current_run_events = []
        self.event_archives = []

        self.gui_api = None

    def attach_gui_api(self, gui_api):
        self.gui_api = gui_api

    def _should_print_event(self, event_type: str) -> bool:
        if DEBUG_LEVEL <= 0:
            return event_type in {
                "ERROR",
                "VERIFY_FAIL",
                "SESSION_TIMEOUT",
                "REGISTER_REJECTED",
                "SESSION_START_REJECTED",
                "MALFORMED",
                "WARN",
                "SESSION_FAIL",
            }

        if DEBUG_LEVEL == 1:
            return event_type not in {"RX", "TX", "HEARTBEAT"}

        return True

    def _archive_current_run(self):
        if self.current_run_events:
            self.event_archives.append({
                "archived_at": datetime.utcnow().isoformat(),
                "session_id": self.session.session_id,
                "events": self.current_run_events[-200:],
            })
            self.current_run_events = []

    def _broadcast_snapshot(self):
        if self.gui_api:
            asyncio.create_task(
                self.gui_api.broadcast({
                    "type": "snapshot",
                    "payload": self.build_gui_snapshot(),
                })
            )

    def log_event(self, source, event_type, message, data=None):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "event_type": event_type,
            "message": message,
            "data": data or {},
        }
        self.event_log.append(event)
        self.current_run_events.append(event)

        self.event_log = self.event_log[-1000:]
        self.current_run_events = self.current_run_events[-300:]

        if self._should_print_event(event_type):
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
            self._broadcast_snapshot()

    def _compute_verification_status(self):
        if self.session.status == "VERIFIED_OK":
            return "PASS"
        if self.session.status == "VERIFIED_FAIL":
            return "FAIL"
        return "PENDING"

    def _compute_current_step(self):
        if self.session.status == "READY_WAIT":
            return "WAITING_FOR_DEVICES"
        if self.session.status == "RESETTING":
            return "RESETTING"
        if self.session.status == "PARAMS_SENT":
            return "PARAMS_DISTRIBUTED"
        if self.session.status == "EXCHANGE_STARTED":
            return "PRIVATE_KEYS_GENERATED"
        if self.session.status == "COLLECTING_PUBLIC_KEYS":
            return "PUBLIC_KEYS_COMPUTED"
        if self.session.status == "RELAYING_PUBLIC_KEYS":
            return "PUBLIC_KEYS_EXCHANGED"
        if self.session.status == "COLLECTING_RESULTS":
            return "SHARED_SECRET_COMPUTED"
        if self.session.status in {"VERIFIED_OK", "VERIFIED_FAIL"}:
            return "VERIFICATION_COMPLETE"
        return "IDLE"

    def _device_heartbeat_health(self, record):
        if not record.last_seen:
            return "offline"

        age = (datetime.utcnow() - record.last_seen).total_seconds()
        if age <= 5:
            return "healthy"
        if age <= 10:
            return "stale"
        return "offline"

    def _ready_to_start(self):
        if not self.device_manager.has_required_devices():
            return False

        required = {"ESP32-A", "ESP32-B"}
        seen = set()

        for record in self.device_manager.list_devices():
            if record.device_id in required:
                health = self._device_heartbeat_health(record)
                if health == "offline":
                    return False
                seen.add(record.device_id)

        return seen == required

    def build_gui_snapshot(self):
        devices = []
        for record in self.device_manager.list_devices():
            devices.append({
                "device_id": record.device_id,
                "addr": record.addr,
                "state": record.state,
                "last_seen": record.last_seen.isoformat() if record.last_seen else None,
                "firmware_version": record.firmware_version,
                "session_id": record.session_id,
                "heartbeat_health": self._device_heartbeat_health(record),
            })

        verification_status = self._compute_verification_status()
        current_step = self._compute_current_step()

        session = {
            "session_id": self.session.session_id,
            "p": self.session.p,
            "g": self.session.g,
            "status": self.session.status,
            "public_keys": self.session.public_keys,
            "results": self.session.results,
            "devices_ready": list(self.session.devices_ready),
            "verification_status": verification_status,
            "current_step": current_step,
            "has_all_public_keys": len(self.session.public_keys) >= 2,
            "has_all_results": len(self.session.results) >= 2,
            "failure_reason": self.session.failure_reason,
            "started_at": self.session.started_at.isoformat() if self.session.started_at else None,
            "last_progress_at": self.session.last_progress_at.isoformat() if self.session.last_progress_at else None,
            "ready_to_start": self._ready_to_start(),
            "exchange_complete": self.session.status in {"VERIFIED_OK", "VERIFIED_FAIL"},
            "archive_count": len(self.event_archives),
        }

        return {
            "devices": devices,
            "session": session,
            "events": self.current_run_events[-100:],
            "archive_count": len(self.event_archives),
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
        asyncio.create_task(self.session_watchdog())

        async with server:
            await server.serve_forever()

    async def device_monitor(self):
        while True:
            self.device_manager.print_devices()
            self._broadcast_snapshot()
            await asyncio.sleep(2)

    async def session_watchdog(self):
        while True:
            await asyncio.sleep(1)

            if not self.session or not self.session.last_progress_at:
                continue

            if self.session.status in {"IDLE", "READY_WAIT", "VERIFIED_OK", "VERIFIED_FAIL"}:
                continue

            elapsed = (datetime.utcnow() - self.session.last_progress_at).total_seconds()
            if elapsed >= SESSION_TIMEOUT_SECONDS:
                self.session.fail("DEVICE_RESPONSE_TIMEOUT")
                self.log_event(
                    "BACKEND",
                    "SESSION_TIMEOUT",
                    f"No device progress for {SESSION_TIMEOUT_SECONDS}s",
                    {"error_code": "DEVICE_RESPONSE_TIMEOUT"},
                )

    def _next_session_id(self):
        self.session_seq += 1
        return f"session-{self.session_seq:04d}"

    async def start_session_from_gui(self, p: int, g: int):
        if not self._ready_to_start():
            self.log_event(
                "BACKEND",
                "SESSION_START_REJECTED",
                "Devices are not ready to start",
                {"error_code": "DEVICES_NOT_READY"},
            )
            return

        self._archive_current_run()

        self.session.reset_runtime_data()
        self.session.set_params(p, g)
        self.session.session_id = self._next_session_id()
        self.session.status = "RESETTING"
        self.session.start()

        self.log_event(
            "BACKEND",
            "SESSION_START",
            f"Starting session {self.session.session_id}",
            {"p": p, "g": g},
        )

        await self.broadcast_json({
            "type": "RESET",
            "session_id": self.session.session_id,
        })

        self.log_event("BACKEND", "STEP_DELAY", f"Waiting {STEP_DELAY_SECONDS}s after RESET")
        await asyncio.sleep(STEP_DELAY_SECONDS)

        self.session.status = "PARAMS_SENT"
        self.session.touch_progress()

        await self.broadcast_json({
            "type": "SET_PARAMS",
            "session_id": self.session.session_id,
            "p": p,
            "g": g,
        })

        self.log_event("BACKEND", "STEP_DELAY", f"Waiting {STEP_DELAY_SECONDS}s after SET_PARAMS")
        await asyncio.sleep(STEP_DELAY_SECONDS)

        self.session.status = "EXCHANGE_STARTED"
        self.session.touch_progress()

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

        self._archive_current_run()
        self.session.reset_runtime_data()

    async def _relay_public_keys_with_delay(self):
        if self.session.relay_sent:
            return

        dev_a = self.device_manager.get_device("ESP32-A")
        dev_b = self.device_manager.get_device("ESP32-B")

        if not dev_a or not dev_b:
            self.session.fail("MISSING_DEVICE")
            self.log_event(
                "BACKEND",
                "SESSION_FAIL",
                "Cannot relay public keys because a device is missing",
                {"error_code": "MISSING_DEVICE"},
            )
            return

        self.session.relay_sent = True
        self.session.status = "RELAYING_PUBLIC_KEYS"
        self.session.touch_progress()

        self.log_event("BACKEND", "RELAY_DELAY", f"Waiting {RELAY_DELAY_SECONDS}s before relaying peer keys")
        await asyncio.sleep(RELAY_DELAY_SECONDS)

        self.log_event("BACKEND", "RELAY", "Relaying public keys between devices")

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

        self.session.status = "COLLECTING_RESULTS"
        self.session.touch_progress()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
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
                    self.log_event(
                        "BACKEND",
                        "MALFORMED",
                        f"{addr}: {line}",
                        {"error_code": "INVALID_JSON"},
                    )
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

                    self.log_event(
                        "BACKEND",
                        "UNKNOWN_MSG",
                        f"type={msg_type}",
                        {"error_code": "UNKNOWN_MESSAGE_TYPE"},
                    )

        except ConnectionResetError:
            self.log_event(
                "BACKEND",
                "ERROR",
                f"Connection reset by {addr}",
                {"error_code": "BOARD_DISCONNECTED"},
            )
        except asyncio.IncompleteReadError:
            self.log_event(
                "BACKEND",
                "ERROR",
                f"Incomplete read from {addr}",
                {"error_code": "BOARD_DISCONNECTED"},
            )
        finally:
            removed = self.device_manager.unregister_by_writer(writer)
            if removed:
                self.log_event(
                    "BACKEND",
                    "DEVICE_REMOVED",
                    f"{removed}",
                    {"error_code": "BOARD_DISCONNECTED"},
                )

                if self.session and self.session.status not in {"IDLE", "READY_WAIT", "VERIFIED_OK", "VERIFIED_FAIL"}:
                    self.session.fail("BOARD_DISCONNECTED")
                    self.log_event(
                        "BACKEND",
                        "SESSION_FAIL",
                        f"{removed} disconnected during active exchange",
                        {"error_code": "BOARD_DISCONNECTED"},
                    )

                self.device_manager.print_devices()

            writer.close()
            await writer.wait_closed()

    async def handle_register(self, msg: dict, writer: asyncio.StreamWriter, addr: str) -> tuple[bool, Optional[str]]:
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
            self.log_event(
                "BACKEND",
                "REGISTER_REJECTED",
                info,
                {"error_code": "DUPLICATE_DEVICE_ID"},
            )
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
            self.log_event(
                "BACKEND",
                "WARN",
                "Invalid PUBLIC_KEY message",
                {"error_code": "MISSING_PUBLIC_KEY", "raw": msg},
            )
            return

        if session_id != self.session.session_id:
            self.log_event(
                "BACKEND",
                "WARN",
                f"Ignoring PUBLIC_KEY for stale session {session_id}",
                {"error_code": "SESSION_MISMATCH"},
            )
            return

        self.session.add_public_key(device_id, public_key)
        self.session.status = "COLLECTING_PUBLIC_KEYS"

        self.log_event(device_id, "PUBLIC_KEY", f"{public_key}")

        if self.session.has_both_public_keys() and not self.session.relay_sent:
            asyncio.create_task(self._relay_public_keys_with_delay())

    async def handle_result(self, msg: dict) -> None:
        device_id = msg.get("device_id")
        session_id = msg.get("session_id")
        shared_secret = msg.get("shared_secret")

        if not device_id or not session_id or shared_secret is None:
            self.log_event(
                "BACKEND",
                "WARN",
                "Invalid RESULT message",
                {"error_code": "MISSING_RESULT", "raw": msg},
            )
            return

        if session_id != self.session.session_id:
            self.log_event(
                "BACKEND",
                "WARN",
                f"Ignoring RESULT for stale session {session_id}",
                {"error_code": "SESSION_MISMATCH"},
            )
            return

        self.session.add_result(device_id, shared_secret)
        self.session.status = "COLLECTING_RESULTS"

        self.log_event(device_id, "RESULT", f"{shared_secret}")

        if self.session.has_both_results() and not self.session.verification_done:
            self.session.verification_done = True

            if self.session.verify():
                self.session.status = "VERIFIED_OK"
                self.session.failure_reason = None
                self.log_event(
                    "BACKEND",
                    "VERIFY_OK",
                    "Shared secret match",
                    {"secret": shared_secret},
                )
            else:
                self.session.fail("VERIFICATION_MISMATCH")
                a_secret = self.session.results.get("ESP32-A")
                b_secret = self.session.results.get("ESP32-B")
                self.log_event(
                    "BACKEND",
                    "VERIFY_FAIL",
                    "Secrets mismatch",
                    {
                        "error_code": "VERIFICATION_MISMATCH",
                        "A": a_secret,
                        "B": b_secret,
                    },
                )

    async def send_json(self, writer: asyncio.StreamWriter, payload: dict) -> None:
        line = json.dumps(payload) + "\n"
        writer.write(line.encode())
        await writer.drain()

        self.log_event("BACKEND", "TX", line.strip())