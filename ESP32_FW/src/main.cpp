#include <Arduino.h>
#include "../include/wifi_manager.h"

WiFiManager wifiManager;

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println();
    Serial.println("=== ESP32 DH Simulator Boot ===");

    wifiManager.begin();
}

void loop() {
    wifiManager.update();
    delay(100);
}