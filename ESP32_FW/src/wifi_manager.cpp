#include "../include/wifi_manager.h"
#include "../include/config.h"

WiFiManager::WiFiManager()
    : lastRetryAttempt(0), wasConnected(false) {
}

void WiFiManager::begin() {
    Serial.println("[WiFi] Initializing Wi-Fi...");

    WiFi.mode(WIFI_STA);
    WiFi.disconnect(true, true);
    delay(200);

    connectToWiFi();
}

void WiFiManager::update() {
    bool connectedNow = isConnected();

    if (connectedNow && !wasConnected) {
        emitEvent("WIFI_CONNECTED");
        Serial.print("[WiFi] Connected. IP: ");
        Serial.println(getIpAddress());
    }

    if (!connectedNow && wasConnected) {
        emitEvent("WIFI_DISCONNECTED");
        Serial.println("[WiFi] Disconnected from hotspot");
    }

    if (!connectedNow) {
        unsigned long now = millis();

        if (now - lastRetryAttempt >= 5000) {
            lastRetryAttempt = now;
            emitEvent("WIFI_RECONNECTING");
            Serial.println("[WiFi] Reconnecting...");
            connectToWiFi();
        }
    }

    wasConnected = connectedNow;
}

bool WiFiManager::isConnected() const {
    return WiFi.status() == WL_CONNECTED;
}

String WiFiManager::getIpAddress() const {
    if (!isConnected()) {
        return "0.0.0.0";
    }
    return WiFi.localIP().toString();
}

wl_status_t WiFiManager::getStatus() const {
    return WiFi.status();
}

void WiFiManager::connectToWiFi() {
    emitEvent("WIFI_CONNECTING");
    Serial.print("[WiFi] Connecting to SSID: ");
    Serial.println(Config::WIFI_SSID);

    WiFi.begin(Config::WIFI_SSID, Config::WIFI_PASSWORD);
}

void WiFiManager::emitEvent(const char* eventName) {
    Serial.print("[WiFi][EVENT] ");
    Serial.println(eventName);
}