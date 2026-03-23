
## 1. Overview
This document describes the firmware architecture and connectivity implementation for the ESP32 nodes in the Diffie-Hellman simulation system. The system consists of two ESP32 devices (ESP32-A and ESP32-B) and a laptop acting as a Wi-Fi hotspot and backend relay server.

This document focuses exclusively on the ESP32 firmware design, including connectivity, communication, and internal architecture.

---

## 2. System Role of ESP32 Devices

Each ESP32 acts as an independent client node that:
- Connects to the laptop Wi-Fi hotspot
- Establishes a TCP connection to the backend server
- Participates in the Diffie-Hellman key exchange
- Sends and receives protocol messages via the laptop relay
- Reports events and status updates

Both ESP32-A and ESP32-B run identical firmware, differing only by a compile-time `DEVICE_ID`.

---

## 3. Firmware Architecture

### 3.1 Design Principles
- Single shared codebase for both devices
- Modular architecture for maintainability
- Clear separation of responsibilities
- Event-driven state machine
- Robust reconnection handling

### 3.2 High-Level Modules

#### 1. App Controller
Coordinates all subsystems and drives the main application flow.

#### 2. Wi-Fi Manager
Handles:
- Connecting to the laptop hotspot
- Monitoring connection state
- Automatic reconnection

#### 3. Transport Client
Responsible for:
- TCP socket connection to backend
- Sending and receiving raw data
- Connection retry logic

#### 4. Message Codec
- Encodes outgoing messages (JSON)
- Decodes incoming messages
- Validates protocol structure

#### 5. State Machine
Controls the device lifecycle:

- Initialization
- Registration
- Key exchange phases
- Completion

#### 6. Event Reporter
- Sends structured event messages to backend
- Logs internal state transitions
- Supports debugging and GUI visualization
---
## 4. Firmware Project Structure

```
firmware/
├── src/
│ ├── main.cpp
│ ├── app_controller.cpp
│ ├── wifi_manager.cpp
│ ├── transport_client.cpp
│ ├── message_codec.cpp
│ ├── state_machine.cpp
│ └── event_reporter.cpp
├── include/
│ ├── config.h
│ ├── protocol.h
│ ├── types.h
│ ├── wifi_manager.h
│ ├── transport_client.h
│ ├── message_codec.h
│ ├── state_machine.h
│ └── event_reporter.h
├── platformio.ini
└── README.md
```
---

## 5. Configuration

All configuration is centralized in `config.h`.
### 5.1 Parameters
- `DEVICE_ID` – unique identifier for ESP32-A or ESP32-B
- `WIFI_SSID` – laptop hotspot SSID
- `WIFI_PASSWORD` – hotspot password
- `BACKEND_IP` – laptop IP address
- `BACKEND_PORT` – backend TCP port

### 5.2 Compile-Time Identity
Each device is built with a different `DEVICE_ID`:
- ESP32-A → `DEVICE_ID = "A"`
- ESP32-B → `DEVICE_ID = "B"`

---

## 6. Connectivity Flow

### 6.1 Boot Sequence
1. Device powers on
2. Initializes serial and modules
3. Starts Wi-Fi connection

### 6.2 Wi-Fi Connection
- Connect to configured hotspot
- Wait until `WL_CONNECTED`
- Retry on failure

### 6.3 Backend Connection

- Open TCP socket to backend
- Maintain persistent connection
- Reconnect if connection drops

### 6.4 Registration
Once connected:
- Send a `REGISTER` message
- Include `DEVICE_ID`
- Wait for acknowledgment from backend

---

## 7. Message Transport
### 7.1 Protocol Transport
- TCP-based communication
- Laptop acts as relay (no direct ESP-to-ESP communication)

### 7.2 Message Format
Messages are encoded in JSON.
Example:
```
{
"type": "REGISTER",
"device": "A"
}
```

### 7.3 Message Types
Defined in `protocol.h`, including:
- REGISTER
- PUBLIC_KEY
- SHARED_SECRET
- EVENT

---

## 8. State Machine

### 8.1 States
- INIT
- WIFI_CONNECTED
- BACKEND_CONNECTED
- REGISTERED
- KEY_EXCHANGE
- COMPLETE
### 8.2 Transitions
State transitions are triggered by:

- Wi-Fi connection events
- Backend connection status
- Incoming messages
---
## 9. Reliability Considerations

### 9.1 Wi-Fi Reliability
- Automatic reconnection
- Connection status monitoring

### 9.2 TCP Reliability
- Persistent socket
- Reconnect on failure
- Graceful handling of disconnects

### 9.3 Error Handling
- Invalid message detection
- Timeout handling
- Retry mechanisms
---
## 10. Event Reporting
Each ESP32 reports events to the backend for visualization:

- Connection events
- State transitions
- Key exchange steps

Example event:
```
{
"type": "EVENT",
"event": "WIFI_CONNECTED",
"device": "A"
}
```
---

## 11. Summary
The ESP32 firmware is designed as a modular, shared codebase that enables both devices to:
- Connect reliably to the laptop hotspot
- Communicate through a TCP relay
- Execute a synchronized Diffie-Hellman exchange
- Provide real-time event feedback

This architecture ensures consistency, scalability, and ease of debugging across both ESP32 nodes.