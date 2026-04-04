#include "../include/message_codec.h"

String MessageCodec::makeRegisterMessage(const char* deviceId,
                                         const char* firmwareVersion,
                                         uint32_t seq) {
    String msg = "{";
    msg += "\"type\":\"REGISTER\",";
    msg += "\"device_id\":\"";
    msg += deviceId;
    msg += "\",";
    msg += "\"seq\":";
    msg += String(seq);
    msg += ",";
    msg += "\"firmware_version\":\"";
    msg += firmwareVersion;
    msg += "\"";
    msg += "}";
    return msg;
}

ParsedMessage MessageCodec::parseMessage(const String& raw) {
    ParsedMessage msg;
    String typeStr;

    extractStringField(raw, "type", typeStr);
    extractStringField(raw, "session_id", msg.sessionId);
    extractStringField(raw, "error_code", msg.errorCode);
    extractStringField(raw, "device_id", msg.deviceId);
    extractStringField(raw, "peer_device_id", msg.peerDeviceId);
    extractUIntField(raw, "seq", msg.seq);
    msg.hasP = extractUIntField(raw, "p", msg.p);
    msg.hasG = extractUIntField(raw, "g", msg.g);
    msg.hasPublicKey = extractUIntField(raw, "public_key", msg.publicKey);

    if (typeStr == "REGISTER_ACK") msg.type = CommandType::REGISTER_ACK;
    else if (typeStr == "SET_PARAMS") msg.type = CommandType::SET_PARAMS;
    else if (typeStr == "START_EXCHANGE") msg.type = CommandType::START_EXCHANGE;
    else if (typeStr == "PEER_PUBLIC_KEY") msg.type = CommandType::PEER_PUBLIC_KEY;
    else if (typeStr == "RESET") msg.type = CommandType::RESET;
    else if (typeStr == "ERROR") msg.type = CommandType::ERROR_MSG;
    else msg.type = CommandType::UNKNOWN;

    return msg;
}

bool MessageCodec::extractStringField(const String& raw, const String& key, String& value) {
    String pattern = "\"" + key + "\"";
    int keyPos = raw.indexOf(pattern);
    if (keyPos < 0) return false;

    int colonPos = raw.indexOf(':', keyPos + pattern.length());
    if (colonPos < 0) return false;

    int start = colonPos + 1;
    while (start < raw.length() && isspace(raw[start])) {
        start++;
    }

    if (start >= raw.length() || raw[start] != '"') {
        return false;
    }

    start++;  // move past opening quote
    int end = raw.indexOf('"', start);
    if (end < 0) return false;

    value = raw.substring(start, end);
    return true;
}

bool MessageCodec::extractUIntField(const String& raw, const String& key, uint32_t& value) {
    String pattern = "\"" + key + "\"";
    int keyPos = raw.indexOf(pattern);
    if (keyPos < 0) return false;

    int colonPos = raw.indexOf(':', keyPos + pattern.length());
    if (colonPos < 0) return false;

    int start = colonPos + 1;
    while (start < raw.length() && isspace(raw[start])) {
        start++;
    }

    int end = start;
    while (end < raw.length() && isDigit(raw[end])) {
        end++;
    }

    if (end == start) return false;

    value = raw.substring(start, end).toInt();
    return true;
}