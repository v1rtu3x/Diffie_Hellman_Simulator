#pragma once

#include <Arduino.h>

class MessageCodec {
public:
    static String makeRegisterMessage(const char* deviceId,
                                      const char* firmwareVersion,
                                      uint32_t seq);
};
