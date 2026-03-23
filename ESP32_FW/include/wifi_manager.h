#pragma once

#include <Arduino.h>
#include <WiFi.h>

class WiFiManager {
public:
    WiFiManager();

    void begin();
    void update();

    bool isConnected() const;
    String getIpAddress() const;
    wl_status_t getStatus() const;

private:
    unsigned long lastRetryAttempt;
    bool wasConnected;

    void connectToWiFi();
    void emitEvent(const char* eventName);
};