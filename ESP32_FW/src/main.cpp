#include <Arduino.h>
#include "../include/wifi_manager.h"
#include "../include/transport_client.h"
#include "../include/message_codec.h"
#include "../include/config.h"
#include "../include/state_machine.h"
#include "../include/app_context.h"
#include "../include/event_reporter.h"
#include "../include/dh_engine.h"

WiFiManager wifiManager;
TransportClient transportClient;
StateMachine stateMachine;
AppContext app;
DhEngine dhEngine;

unsigned long waitingForPeerKeySinceMs = 0;
const unsigned long PEER_KEY_TIMEOUT_MS = 10000;

unsigned long lastHeartbeatMs = 0;
const unsigned long HEARTBEAT_INTERVAL_MS = 3000;

void sendEvent(const char* eventType, const String& data = "") {
    if (!transportClient.isConnected()) {
        return;
    }

    String msg = EventReporter::buildEvent(
        DEVICE_ID,
        app.currentSessionId,
        app.seq++,
        stateMachine.getStateName(),
        eventType,
        data
    );

    transportClient.sendLine(msg);

    Serial.print("[APP][EVENT] ");
    Serial.println(msg);
}

void sendHeartbeatIfNeeded() {
    if (!transportClient.isConnected()) return;

    unsigned long now = millis();
    if (now - lastHeartbeatMs < HEARTBEAT_INTERVAL_MS) return;

    lastHeartbeatMs = now;
    sendEvent("HEARTBEAT");
}

void handleRegisterAck(const ParsedMessage& msg) {
    (void)msg;

    Serial.println("[APP] REGISTER_ACK received");

    app.registrationBlocked = false;

    if (stateMachine.getState() == DeviceState::SERVER_CONNECTING ||
        stateMachine.getState() == DeviceState::ERROR) {
        stateMachine.transitionTo(DeviceState::WAITING_PARAMS);
    }

    sendEvent("REGISTERED");
}

void handleSetParams(const ParsedMessage& msg) {
    if (stateMachine.getState() != DeviceState::WAITING_PARAMS &&
        stateMachine.getState() != DeviceState::DONE) {
        Serial.println("[APP][ERROR] SET_PARAMS invalid state");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"INVALID_STATE\",\"detail\":\"SET_PARAMS invalid state\"}");
        return;
    }

    if (!msg.hasP || !msg.hasG || msg.sessionId.length() == 0) {
        Serial.println("[APP][ERROR] SET_PARAMS missing required fields");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"MISSING_PARAMS\",\"detail\":\"SET_PARAMS missing fields\"}");
        return;
    }

    if (!dhEngine.setParams(msg.p, msg.g)) {
        Serial.println("[APP][ERROR] Failed to set DH params");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"INVALID_PARAMS\",\"detail\":\"invalid DH params\"}");
        return;
    }

    app.currentSessionId = msg.sessionId;
    app.p = msg.p;
    app.g = msg.g;
    app.hasParams = true;

    Serial.print("[APP] Session set: ");
    Serial.println(app.currentSessionId);
    Serial.print("[APP] p = ");
    Serial.println(app.p);
    Serial.print("[APP] g = ");
    Serial.println(app.g);

    stateMachine.transitionTo(DeviceState::READY);
    sendEvent("PARAMS_RECEIVED");
}

void handleStartExchange(const ParsedMessage& msg) {
    if (stateMachine.getState() != DeviceState::READY) {
        Serial.println("[APP][ERROR] START_EXCHANGE invalid state");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"INVALID_STATE\",\"detail\":\"START_EXCHANGE invalid state\"}");
        return;
    }

    if (!app.hasParams) {
        Serial.println("[APP][ERROR] START_EXCHANGE missing params");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"MISSING_PARAMS\",\"detail\":\"params not set\"}");
        return;
    }

    if (msg.sessionId.length() == 0 || msg.sessionId != app.currentSessionId) {
        Serial.println("[APP][ERROR] START_EXCHANGE session mismatch");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"SESSION_MISMATCH\",\"detail\":\"START_EXCHANGE session mismatch\"}");
        return;
    }

    Serial.println("[APP] START_EXCHANGE received");

    stateMachine.transitionTo(DeviceState::GENERATING_PRIVATE);
    sendEvent("GENERATING_PRIVATE");

    if (!dhEngine.generatePrivateKey()) {
        Serial.println("[APP][ERROR] Failed to generate private key");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"PRIVATE_KEY_FAILED\",\"detail\":\"private key generation failed\"}");
        return;
    }

    if (!dhEngine.computePublicKey()) {
        Serial.println("[APP][ERROR] Failed to compute public key");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"PUBLIC_KEY_FAILED\",\"detail\":\"public key computation failed\"}");
        return;
    }

    const DhContext& ctx = dhEngine.getContext();

    Serial.print("[APP] Private key: ");
    Serial.println(ctx.privateKey);
    Serial.print("[APP] Public key: ");
    Serial.println(ctx.publicKey);

    stateMachine.transitionTo(DeviceState::COMPUTED_PUBLIC);
    sendEvent("PUBLIC_KEY_COMPUTED", "{\"public_key\":" + String(ctx.publicKey) + "}");

    String msgOut = "{";
    msgOut += "\"type\":\"PUBLIC_KEY\",";
    msgOut += "\"device_id\":\"";
    msgOut += DEVICE_ID;
    msgOut += "\",";
    msgOut += "\"session_id\":\"";
    msgOut += app.currentSessionId;
    msgOut += "\",";
    msgOut += "\"seq\":";
    msgOut += String(app.seq++);
    msgOut += ",";
    msgOut += "\"public_key\":";
    msgOut += String(ctx.publicKey);
    msgOut += "}";

    transportClient.sendLine(msgOut);

    stateMachine.transitionTo(DeviceState::WAITING_PEER_PUBLIC);
    sendEvent("WAITING_PEER_PUBLIC");
    waitingForPeerKeySinceMs = millis();
}

void handlePeerPublicKey(const ParsedMessage& msg) {
    if (stateMachine.getState() != DeviceState::WAITING_PEER_PUBLIC) {
        Serial.println("[APP][ERROR] PEER_PUBLIC_KEY invalid state");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"INVALID_STATE\",\"detail\":\"PEER_PUBLIC_KEY invalid state\"}");
        return;
    }

    if (msg.sessionId.length() == 0 || msg.sessionId != app.currentSessionId) {
        Serial.println("[APP][ERROR] PEER_PUBLIC_KEY session mismatch");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"SESSION_MISMATCH\",\"detail\":\"PEER_PUBLIC_KEY session mismatch\"}");
        return;
    }

    if (!msg.hasPublicKey) {
        Serial.println("[APP][ERROR] PEER_PUBLIC_KEY missing public_key");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"MISSING_PEER_KEY\",\"detail\":\"PEER_PUBLIC_KEY missing public_key\"}");
        return;
    }

    if (!dhEngine.setPeerPublicKey(msg.publicKey)) {
        Serial.println("[APP][ERROR] Invalid peer public key");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"INVALID_PEER_KEY\",\"detail\":\"invalid peer public key\"}");
        return;
    }

    if (!dhEngine.computeSharedSecret()) {
        Serial.println("[APP][ERROR] Failed to compute shared secret");
        stateMachine.transitionTo(DeviceState::ERROR);
        sendEvent("ERROR", "{\"reason\":\"SHARED_SECRET_FAILED\",\"detail\":\"shared secret computation failed\"}");
        return;
    }

    waitingForPeerKeySinceMs = 0;

    const DhContext& ctx = dhEngine.getContext();

    Serial.print("[APP] Peer public key received: ");
    Serial.println(ctx.peerPublicKey);
    Serial.print("[APP] Shared secret: ");
    Serial.println(ctx.sharedSecret);

    stateMachine.transitionTo(DeviceState::COMPUTED_SHARED_SECRET);
    sendEvent("SHARED_SECRET_COMPUTED", "{\"shared_secret\":" + String(ctx.sharedSecret) + "}");

    String resultMsg = "{";
    resultMsg += "\"type\":\"RESULT\",";
    resultMsg += "\"device_id\":\"";
    resultMsg += DEVICE_ID;
    resultMsg += "\",";
    resultMsg += "\"session_id\":\"";
    resultMsg += app.currentSessionId;
    resultMsg += "\",";
    resultMsg += "\"seq\":";
    resultMsg += String(app.seq++);
    resultMsg += ",";
    resultMsg += "\"shared_secret\":";
    resultMsg += String(ctx.sharedSecret);
    resultMsg += "}";

    transportClient.sendLine(resultMsg);

    stateMachine.transitionTo(DeviceState::DONE);
    sendEvent("DONE");
}

void handleReset(const ParsedMessage& msg) {
    (void)msg;

    Serial.println("[APP] RESET received");

    app.resetSession();
    app.registrationBlocked = false;
    dhEngine.reset();
    waitingForPeerKeySinceMs = 0;

    stateMachine.transitionTo(DeviceState::WAITING_PARAMS);
    sendEvent("RESET_DONE");
}

void handleError(const ParsedMessage& msg) {
    Serial.println("[APP] ERROR received from backend");

    if (msg.errorCode == "DUPLICATE_DEVICE_ID") {
        Serial.println("[APP] Duplicate device ID detected. Blocking re-registration.");
        app.registrationBlocked = true;
        sendEvent("ERROR", "{\"reason\":\"DUPLICATE_DEVICE_ID\"}");
        return;
    }

    stateMachine.transitionTo(DeviceState::ERROR);
    sendEvent("ERROR", "{\"reason\":\"BACKEND_ERROR\",\"detail\":\"backend error\"}");
}

void dispatchCommand(const ParsedMessage& msg) {
    switch (msg.type) {
        case CommandType::SET_PARAMS:
            handleSetParams(msg);
            break;
        case CommandType::START_EXCHANGE:
            handleStartExchange(msg);
            break;
        case CommandType::PEER_PUBLIC_KEY:
            handlePeerPublicKey(msg);
            break;
        case CommandType::RESET:
            handleReset(msg);
            break;
        case CommandType::REGISTER_ACK:
            handleRegisterAck(msg);
            break;
        case CommandType::ERROR_MSG:
            handleError(msg);
            break;
        case CommandType::UNKNOWN:
        default:
            Serial.println("[APP][WARN] Unknown command");
            sendEvent("ERROR", "{\"reason\":\"UNKNOWN_COMMAND\"}");
            break;
    }
}

void handleIncomingMessage(const String& raw) {
    Serial.print("[APP][RX] ");
    Serial.println(raw);

    ParsedMessage msg = MessageCodec::parseMessage(raw);

    if (!msg.parseOk) {
        Serial.print("[APP][ERROR] Malformed message: ");
        Serial.println(msg.parseError);
        sendEvent("ERROR", "{\"reason\":\"INVALID_JSON\"}");
        return;
    }

    dispatchCommand(msg);
}

void sendRegisterIfNeeded() {
    if (!transportClient.isConnected()) {
        app.registerSent = false;
        return;
    }

    if (app.registrationBlocked) {
        return;
    }

    if (!app.registerSent) {
        String registerMsg = MessageCodec::makeRegisterMessage(
            DEVICE_ID,
            FIRMWARE_VERSION,
            app.seq++
        );

        Serial.println("[APP] Sending REGISTER...");
        if (transportClient.sendLine(registerMsg)) {
            Serial.println("[APP] REGISTER sent successfully");
            app.registerSent = true;
        } else {
            Serial.println("[APP] REGISTER send failed");
        }
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println();
    Serial.println("=== ESP32 DH Simulator Boot ===");

    stateMachine.transitionTo(DeviceState::WIFI_CONNECTING);

    wifiManager.begin();
    transportClient.begin();
}

void loop() {
    wifiManager.update();

    if (wifiManager.isConnected()) {
        if (stateMachine.getState() == DeviceState::WIFI_CONNECTING) {
            stateMachine.transitionTo(DeviceState::SERVER_CONNECTING);
        }

        transportClient.update();

        if (!transportClient.isConnected()) {
            if (stateMachine.getState() != DeviceState::SERVER_CONNECTING &&
                stateMachine.getState() != DeviceState::WIFI_CONNECTING) {

                Serial.println("[APP][WARN] Backend disconnected during session, resetting local DH state");
                sendEvent("ERROR", "{\"reason\":\"BACKEND_DISCONNECTED\"}");

                app.resetSession();
                dhEngine.reset();
                waitingForPeerKeySinceMs = 0;
                app.registerSent = false;
                stateMachine.transitionTo(DeviceState::SERVER_CONNECTING);
            }
        }

        sendRegisterIfNeeded();

        while (transportClient.hasMessage()) {
            String msg = transportClient.popMessage();
            handleIncomingMessage(msg);
        }

        sendHeartbeatIfNeeded();

        if (stateMachine.getState() == DeviceState::WAITING_PEER_PUBLIC) {
            unsigned long now = millis();
            if (waitingForPeerKeySinceMs != 0 &&
                now - waitingForPeerKeySinceMs >= PEER_KEY_TIMEOUT_MS) {

                Serial.println("[APP][ERROR] Timed out waiting for peer public key");
                sendEvent("ERROR", "{\"reason\":\"PEER_KEY_TIMEOUT\"}");

                app.resetSession();
                dhEngine.reset();
                waitingForPeerKeySinceMs = 0;
                stateMachine.transitionTo(DeviceState::WAITING_PARAMS);
            }
        }
    } else {
        app.registerSent = false;
        app.registrationBlocked = false;
        app.resetSession();
        dhEngine.reset();
        waitingForPeerKeySinceMs = 0;

        if (stateMachine.getState() != DeviceState::WIFI_CONNECTING) {
            stateMachine.transitionTo(DeviceState::WIFI_CONNECTING);
        }
    }

    delay(1);
}