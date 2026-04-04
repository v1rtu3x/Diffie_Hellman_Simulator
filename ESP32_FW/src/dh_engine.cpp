#include "../include/dh_engine.h"

DhEngine::DhEngine() {
    reset();
}

void DhEngine::reset() {
    ctx = DhContext{};
}

bool DhEngine::setParams(uint32_t p, uint32_t g) {
    if (p < 3 || g < 2 || g >= p) {
        return false;
    }

    ctx.p = p;
    ctx.g = g;

    ctx.privateKey = 0;
    ctx.publicKey = 0;
    ctx.peerPublicKey = 0;
    ctx.sharedSecret = 0;

    ctx.hasParams = true;
    ctx.hasPrivateKey = false;
    ctx.hasPublicKey = false;
    ctx.hasPeerPublicKey = false;
    ctx.hasSharedSecret = false;

    return true;
}

bool DhEngine::generatePrivateKey() {
    if (!ctx.hasParams) {
        return false;
    }

    // Simple demo range: [2, p-2]
    if (ctx.p <= 4) {
        return false;
    }

    ctx.privateKey = generateRandomInRange(2, ctx.p - 2);
    ctx.hasPrivateKey = true;
    return true;
}

bool DhEngine::computePublicKey() {
    if (!ctx.hasParams || !ctx.hasPrivateKey) {
        return false;
    }

    ctx.publicKey = modPow(ctx.g, ctx.privateKey, ctx.p);
    ctx.hasPublicKey = true;
    return true;
}

bool DhEngine::setPeerPublicKey(uint32_t peerPublicKey) {
    if (!ctx.hasParams) {
        return false;
    }

    if (peerPublicKey == 0 || peerPublicKey >= ctx.p) {
        return false;
    }

    ctx.peerPublicKey = peerPublicKey;
    ctx.hasPeerPublicKey = true;
    return true;
}

bool DhEngine::computeSharedSecret() {
    if (!ctx.hasParams || !ctx.hasPrivateKey || !ctx.hasPeerPublicKey) {
        return false;
    }

    ctx.sharedSecret = modPow(ctx.peerPublicKey, ctx.privateKey, ctx.p);
    ctx.hasSharedSecret = true;
    return true;
}

const DhContext& DhEngine::getContext() const {
    return ctx;
}

uint32_t DhEngine::modPow(uint32_t base, uint32_t exp, uint32_t mod) {
    if (mod == 0) {
        return 0;
    }

    uint64_t result = 1;
    uint64_t b = base % mod;

    while (exp > 0) {
        if (exp & 1U) {
            result = (result * b) % mod;
        }

        b = (b * b) % mod;
        exp >>= 1U;
    }

    return static_cast<uint32_t>(result);
}

uint32_t DhEngine::generateRandomInRange(uint32_t minValue, uint32_t maxValue) {
    if (maxValue <= minValue) {
        return minValue;
    }

    uint32_t span = maxValue - minValue + 1;
    uint32_t r = static_cast<uint32_t>(esp_random());
    return minValue + (r % span);
}