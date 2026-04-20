# 🔐 Diffie-Hellman Simulator (ESP32 + Backend + GUI)

A real-time system demonstrating Diffie-Hellman key exchange using:

* 📡 ESP32 hardware
* 🧠 Python backend
* 🖥️ React GUI

---

## 🚀 Quick Start

### Backend

```bash
cd Server
python -m venv .venv
.venv\Scripts\activate
pip install aiohttp
python Backend/main.py
```

### Firmware

```bash
pio run -t upload -e esp32_a
pio run -t upload -e esp32_b
```

### GUI

```bash
cd GUI
npm install
npm run dev
```

Open:
http://localhost:5173

---

## 🎮 Demo Workflow

1. Power ESP32s
2. Wait for heartbeat = healthy
3. Set p=23, g=5
4. Start session
5. Observe exchange
6. Verify PASS
7. Reset and repeat

---

## 🔍 Diffie-Hellman

* A = g^a mod p
* B = g^b mod p
* Shared = B^a mod p = A^b mod p

---

## 🧪 Features

* Real hardware exchange
* Live visualization
* Error handling
* Repeatable sessions
* Heartbeat monitoring

---

## 🏁 Status

✅ Demo-ready system
