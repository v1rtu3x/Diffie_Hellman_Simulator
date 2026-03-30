#include "../include/transport_client.h"
#include "../include/config.h"

TransportClient::TransportClient()
    : rxBuffer(""),
      pendingMessage(""),
      lastRetryAttempt(0),
      wasConnected(false) {
}

void TransportClient::begin() {
    Serial.println("[TCP] Transport client initialized");
}

void TransportClient::update() {
    bool connectedNow = isConnected();

    if (connectedNow && !wasConnected) {
        emitEvent("SERVER_CONNECTED");
        Serial.println("[TCP] Connected to backend");
    }

    if (!connectedNow && wasConnected) {
        emitEvent("SERVER_DISCONNECTED");
        Serial.println("[TCP] Disconnected from backend");
    }

    if (!connectedNow) {
        unsigned long now = millis();

        if (now - lastRetryAttempt >= 5000) {
            lastRetryAttempt = now;
            emitEvent("SERVER_RECONNECTING");
            Serial.println("[TCP] Reconnecting to backend...");
            connectToServer();
        }
    } else {
        processIncoming();
    }

    wasConnected = connectedNow;
}

bool TransportClient::connectToServer() {
    emitEvent("SERVER_CONNECTING");

    Serial.print("[TCP] Connecting to ");
    Serial.print(Config::BACKEND_IP);
    Serial.print(":");
    Serial.println(Config::BACKEND_PORT);

    client.stop();

    if (client.connect(Config::BACKEND_IP, Config::BACKEND_PORT)) {
        return true;
    }

    Serial.println("[TCP] Connection failed");
    return false;
}

bool TransportClient::isConnected()  {
    return client.connected();
}

bool TransportClient::sendLine(const String& line) {
    if (!isConnected()) {
        Serial.println("[TCP] Send failed: not connected");
        emitEvent("MESSAGE_SEND_FAILED");
        return false;
    }

    client.print(line);
    client.print('\n');

    Serial.print("[TCP][TX] ");
    Serial.println(line);

    return true;
}

void TransportClient::processIncoming() {
    while (client.available() > 0) {
        char c = static_cast<char>(client.read());

        if (c == '\n') {
            pendingMessage = rxBuffer;
            rxBuffer = "";

            Serial.print("[TCP][RX] ");
            Serial.println(pendingMessage);
        } else if (c != '\r') {
            rxBuffer += c;
        }
    }
}

bool TransportClient::hasMessage() const {
    return pendingMessage.length() > 0;
}

String TransportClient::popMessage() {
    String msg = pendingMessage;
    pendingMessage = "";
    return msg;
}

void TransportClient::emitEvent(const char* eventName) {
    Serial.print("[TCP][EVENT] ");
    Serial.println(eventName);
}