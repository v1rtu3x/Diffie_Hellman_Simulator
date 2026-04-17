#include "../include/message_codec.h"

static CommandType parseCommandType(const String& typeStr) {
    if (typeStr == "REGISTER_ACK") return CommandType::REGISTER_ACK;
    if (typeStr == "SET_PARAMS") return CommandType::SET_PARAMS;
    if (typeStr == "START_EXCHANGE") return CommandType::START_EXCHANGE;
    if (typeStr == "PEER_PUBLIC_KEY") return CommandType::PEER_PUBLIC_KEY;
    if (typeStr == "RESET") return CommandType::RESET;
    if (typeStr == "ERROR") return CommandType::ERROR_MSG;
    return CommandType::UNKNOWN;
}

ParsedMessage MessageCodec::parseMessage(const String& jsonStr) {
    ParsedMessage msg;
    msg.parseOk = false;
    msg.parseError = "";

    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, jsonStr);

    if (err) {
        msg.parseError = String("JSON_PARSE_ERROR: ") + err.c_str();
        return msg;
    }

    msg.rawType = doc["type"] | "";
    msg.type = parseCommandType(msg.rawType);

    msg.deviceId = doc["device_id"] | "";
    msg.sessionId = doc["session_id"] | "";
    msg.peerDeviceId = doc["peer_device_id"] | "";
    msg.errorCode = doc["error_code"] | "";
    msg.seq = doc["seq"] | 0;

    if (!doc["p"].isNull()) {
        msg.p = doc["p"] | 0;
        msg.hasP = true;
    }

    if (!doc["g"].isNull()) {
        msg.g = doc["g"] | 0;
        msg.hasG = true;
    }

    if (!doc["public_key"].isNull()) {
        msg.publicKey = doc["public_key"] | 0;
        msg.hasPublicKey = true;
    }

    if (msg.rawType.length() == 0) {
        msg.parseError = "MISSING_TYPE";
        return msg;
    }

    msg.parseOk = true;
    return msg;
}

String MessageCodec::makeRegisterMessage(const char* deviceId, const char* firmwareVersion, uint32_t seq) {
    StaticJsonDocument<256> doc;
    doc["type"] = "REGISTER";
    doc["device_id"] = deviceId;
    doc["seq"] = seq;
    doc["firmware_version"] = firmwareVersion;

    String out;
    serializeJson(doc, out);
    return out;
}