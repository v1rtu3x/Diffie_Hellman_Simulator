#pragma once

#include <Arduino.h>
#include "types.h"

class EventReporter {
public:
    static String buildEvent(
        const char* deviceId,
        const String& sessionId,
        uint32_t seq,
        const char* state,
        const char* eventType,
        const String& data = ""
    );
};