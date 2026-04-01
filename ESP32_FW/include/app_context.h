#pragma once

#include <Arduino.h>

struct AppContext {
    String currentSessionId = "";
    bool registerSent = false;
    bool registrationBlocked = false;
    uint32_t seq = 1;

    bool hasParams = false;
    uint32_t p = 0;
    uint32_t g = 0;

    void resetSession() {
        currentSessionId = "";
        hasParams = false;
        p = 0;
        g = 0;
    }
};