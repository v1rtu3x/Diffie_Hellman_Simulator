#pragma once

#include <Arduino.h>
#include <stdint.h>

struct DhContext {
    uint32_t p = 0;
    uint32_t g = 0;

    uint32_t privateKey = 0;
    uint32_t publicKey = 0;
    uint32_t peerPublicKey = 0;
    uint32_t sharedSecret = 0;

    bool hasParams = false;
    bool hasPrivateKey = false;
    bool hasPublicKey = false;
    bool hasPeerPublicKey = false;
    bool hasSharedSecret = false;
};

class DhEngine {
public:
    DhEngine();

    void reset();

    bool setParams(uint32_t p, uint32_t g);

    bool generatePrivateKey();
    bool computePublicKey();
    bool setPeerPublicKey(uint32_t peerPublicKey);
    bool computeSharedSecret();

    const DhContext& getContext() const;

    static uint32_t modPow(uint32_t base, uint32_t exp, uint32_t mod);

private:
    DhContext ctx;

    uint32_t generateRandomInRange(uint32_t minValue, uint32_t maxValue);
};