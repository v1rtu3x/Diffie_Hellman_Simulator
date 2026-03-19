# Protocol Reference
1. Overview

- communication model (ESP32 ↔ backend only)
- transport (TCP)
- format (JSON + newline-delimited)
- role of backend as orchestrator
2. Message structure

Common message format:
```
{
  "type": "...",
  "device_id": "...",
  "session_id": "...",
  "seq": 0,
  "timestamp": "...",
  "data": {}
}
```

3. Message categories

Sample messages for each type
Backend → ESP32
```
SET_PARAMS
{
  "type": "SET_PARAMS",
  "device_id": "ESP32-A",
  "session_id": "sess-001",
  "seq": 1,
  "p": 23,
  "g": 5
}

START_EXCHANGE
{
  "type": "START_EXCHANGE",
  "device_id": "ESP32-A",
  "session_id": "sess-001",
  "seq": 2
}

PEER_PUBLIC_KEY
{
  "type": "PEER_PUBLIC_KEY",
  "device_id": "ESP32-A",
  "session_id": "sess-001",
  "seq": 3,
  "peer_device_id": "ESP32-B",
  "public_key": 19
}

RESET
{
  "type": "RESET",
  "device_id": "ESP32-A",
  "session_id": "sess-001",
  "seq": 4
}
```

ESP32 → Backend
```
REGISTER
{
  "type": "REGISTER",
  "device_id": "ESP32-A",
  "seq": 1,
  "firmware_version": "1.0.0"
}

EVENT
{
  "type": "EVENT",
  "device_id": "ESP32-A",
  "session_id": "sess-001",
  "seq": 10,
  "state": "READY",
  "severity": "info",
  "event": "PARAMS_SET",
  "data": {
    "p": 23,
    "g": 5
  }
}

PUBLIC_KEY
{
  "type": "PUBLIC_KEY",
  "device_id": "ESP32-A",
  "session_id": "sess-001",
  "seq": 11,
  "public_key": 8
}

RESULT
{
  "type": "RESULT",
  "device_id": "ESP32-A",
  "session_id": "sess-001",
  "seq": 12,
  "shared_secret": 2
}

ERROR
{
  "type": "ERROR",
  "device_id": "ESP32-A",
  "session_id": "sess-001",
  "seq": 13,
  "error_code": "INVALID_STATE",
  "message": "START_EXCHANGE received before params"
}

HEARTBEAT
{
  "type": "HEARTBEAT",
  "device_id": "ESP32-A",
  "seq": 20,
  "state": "WAITING_PARAMS"
}
```
State transition examples
ESP32 state flow (normal case)

BOOT
 - WIFI_CONNECTING
 - SERVER_CONNECTING
 - WAITING_PARAMS
 - READY
 - GENERATING_PRIVATE
 - WAITING_PEER_PUBLIC
 - COMPUTED_SHARED_SECRET
 - DONE

Example: Normal exchange flow

WAITING_PARAMS
 - (SET_PARAMS)

READY
 
 - (START_EXCHANGE)

GENERATING_PRIVATE

 - PUBLIC_KEY_COMPUTED

WAITING_PEER_PUBLIC

 - (PEER_PUBLIC_KEY)

COMPUTED_SHARED_SECRET

 - RESULT_SENT

DONE

Example: Reset flow

ANY_STATE
 - (RESET)

WAITING_PARAMS

Example: Invalid transition

WAITING_PARAMS

 - (START_EXCHANGE)

ERROR

 - (RESET)

WAITING_PARAMS

Rules 
- ESP32 must not start exchange without parameters
- ESP32 must ignore stale session_id
- backend is the only orchestrator
- all important actions must emit events
- messages must always be valid JSON
- each message must end with newline (\n)
- acts as contract between all components