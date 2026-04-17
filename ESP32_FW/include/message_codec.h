#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include "types.h"

class MessageCodec {
public:
    static ParsedMessage parseMessage(const String& jsonStr);
    static String makeRegisterMessage(const char* deviceId, const char* firmwareVersion, uint32_t seq);
};