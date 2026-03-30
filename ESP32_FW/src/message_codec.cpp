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