#pragma once

#include <Arduino.h>

enum class DeviceState {
    BOOT,
    WIFI_CONNECTING,
    SERVER_CONNECTING,
    WAITING_PARAMS,
    READY,
    GENERATING_PRIVATE,
    COMPUTED_PUBLIC,
    WAITING_PEER_PUBLIC,
    COMPUTED_SHARED_SECRET,
    DONE,
    ERROR
};

enum class CommandType {
    UNKNOWN,
    REGISTER_ACK,
    SET_PARAMS,
    START_EXCHANGE,
    PEER_PUBLIC_KEY,
    RESET,
    ERROR_MSG
};

struct ParsedMessage {
    CommandType type = CommandType::UNKNOWN;
    String sessionId = "";
    String errorCode = "";
    String deviceId = "";
    uint32_t seq = 0;

    bool hasP = false;
    bool hasG = false;
    uint32_t p = 0;
    uint32_t g = 0;

    bool hasPublicKey = false;
    uint32_t publicKey = 0;
    String peerDeviceId = "";
};