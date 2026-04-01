#include "../include/event_reporter.h"

String EventReporter::buildEvent(
    const char* deviceId,
    const String& sessionId,
    uint32_t seq,
    const char* state,
    const char* eventType,
    const String& data
) {
    String msg = "{";

    msg += "\"type\":\"EVENT\",";
    msg += "\"device_id\":\""; msg += deviceId; msg += "\",";

    if (sessionId.length() > 0) {
        msg += "\"session_id\":\""; msg += sessionId; msg += "\",";
    }

    msg += "\"seq\":"; msg += String(seq); msg += ",";
    msg += "\"state\":\""; msg += state; msg += "\",";
    msg += "\"event\":\""; msg += eventType; msg += "\"";

    if (data.length() > 0) {
        msg += ",\"data\":"; msg += data;
    }

    msg += "}";

    return msg;
}