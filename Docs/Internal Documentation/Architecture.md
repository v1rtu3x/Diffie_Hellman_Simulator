# 🧱 Architecture

## Overview

ESP32-A and ESP32-B communicate through backend, visualized in GUI.

```
ESP32-A ─┐
         ├── TCP ─► Backend ─► WebSocket ─► GUI
ESP32-B ─┘
```

---

## Message Flow

### Backend → ESP32

* RESET
* SET_PARAMS
* START_EXCHANGE
* PEER_PUBLIC_KEY

### ESP32 → Backend

* REGISTERED
* PUBLIC_KEY
* RESULT
* HEARTBEAT

---

## States

### ESP32

WAITING_PARAMS → READY → GENERATING → DONE

### Backend

READY_WAIT → EXCHANGE → VERIFIED

---

## Delays

Backend enforces:

* Step delay (2s)
* Relay delay (1s)

Purpose:

* Clear visualization
* Avoid race conditions
