#pragma once

#include <Arduino.h>
#include <WiFi.h>

class TransportClient {
public:
    TransportClient();

    void begin();
    void update();

    bool connectToServer();
    bool isConnected();

    bool sendLine(const String& line);

    bool hasMessage() const;
    String popMessage();

private:
    WiFiClient client;
    String rxBuffer;
    String pendingMessage;

    unsigned long lastRetryAttempt;
    bool wasConnected;

    void emitEvent(const char* eventName);
    void processIncoming();
};