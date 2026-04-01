#pragma once

#include <Arduino.h>
#include "types.h"

class MessageCodec {
public:
    static String makeRegisterMessage(const char* deviceId,
                                      const char* firmwareVersion,
                                      uint32_t seq);

    static ParsedMessage parseMessage(const String& raw);

private:
    static bool extractStringField(const String& raw, const String& key, String& value);
    static bool extractUIntField(const String& raw, const String& key, uint32_t& value);
};