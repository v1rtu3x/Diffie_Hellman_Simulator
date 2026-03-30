#pragma once

#ifndef DEVICE_ID
#define DEVICE_ID "ESP32-A"
#endif

#define FIRMWARE_VERSION "1.0.0"
#include <Arduino.h>
#include "secrets.h"

namespace Config {
    static const char* WIFI_SSID = S_WIFI_SSID;
    static const char* WIFI_PASSWORD = S_WIFI_PASSWORD;
    static const char* BACKEND_IP = "172.20.10.9";
    static const uint16_t BACKEND_PORT = 5050;
}