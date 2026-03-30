#include <Arduino.h>
#include "../include/wifi_manager.h"
#include "../include/transport_client.h"
#include "../include/message_codec.h"
#include "../include/config.h"

WiFiManager wifiManager;
TransportClient transportClient;

static uint32_t g_seq = 1;
static bool registerSent = false;

void handleIncomingMessage(const String& msg) {
    Serial.print("[APP][RX] ");
    Serial.println(msg);

    if (msg.indexOf("\"type\":\"REGISTER_ACK\"") >= 0) {
        Serial.println("[APP] REGISTER_ACK received");
    }
}

void sendRegisterIfNeeded() {
    if (!transportClient.isConnected()) {
        registerSent = false;
        return;
    }

    if (!registerSent) {
        String registerMsg = MessageCodec::makeRegisterMessage(
            DEVICE_ID,
            FIRMWARE_VERSION,
            g_seq++
        );

        Serial.println("[APP] Sending REGISTER...");
        if (transportClient.sendLine(registerMsg)) {
            Serial.println("[APP] REGISTER sent successfully");
            registerSent = true;
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

    wifiManager.begin();
    transportClient.begin();
}

void loop() {
    wifiManager.update();

    if (wifiManager.isConnected()) {
        transportClient.update();
        sendRegisterIfNeeded();

        while (transportClient.hasMessage()) {
            String msg = transportClient.popMessage();
            handleIncomingMessage(msg);
        }
    } else {
        registerSent = false;
    }

    delay(100);
}