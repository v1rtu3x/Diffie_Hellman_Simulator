#pragma once

#ifndef DEVICE_ID
#define DEVICE_ID "ESP32-A"
#endif

#define FIRMWARE_VERSION "1.0.0"

namespace Config {
    static const char* WIFI_SSID = "YourLaptopHotspot";
    static const char* WIFI_PASSWORD = "YourHotspotPassword";
    static const char* BACKEND_IP = "192.168.137.1";
    static const uint16_t BACKEND_PORT = 5000;
}