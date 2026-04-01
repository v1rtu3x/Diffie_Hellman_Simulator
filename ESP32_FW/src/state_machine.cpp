#include "../include/state_machine.h"

StateMachine::StateMachine()
    : currentState(DeviceState::BOOT) {
}

DeviceState StateMachine::getState() const {
    return currentState;
}

const char* StateMachine::getStateName() const {
    return stateToString(currentState);
}

bool StateMachine::transitionTo(DeviceState newState) {
    if (!canTransitionTo(newState)) {
        Serial.print("[STATE][ERROR] Invalid transition: ");
        Serial.print(stateToString(currentState));
        Serial.print(" -> ");
        Serial.println(stateToString(newState));
        return false;
    }

    DeviceState oldState = currentState;
    currentState = newState;
    emitStateChange(oldState, newState);
    return true;
}

bool StateMachine::canTransitionTo(DeviceState newState) const {
    switch (currentState) {
        case DeviceState::BOOT:
            return newState == DeviceState::WIFI_CONNECTING;

        case DeviceState::WIFI_CONNECTING:
            return newState == DeviceState::SERVER_CONNECTING ||
                   newState == DeviceState::ERROR;

        case DeviceState::SERVER_CONNECTING:
            return newState == DeviceState::WAITING_PARAMS ||
                   newState == DeviceState::ERROR;

        case DeviceState::WAITING_PARAMS:
            return newState == DeviceState::READY ||
                   newState == DeviceState::ERROR;

        case DeviceState::READY:
            return newState == DeviceState::GENERATING_PRIVATE ||
                   newState == DeviceState::WAITING_PARAMS ||
                   newState == DeviceState::ERROR;

        case DeviceState::GENERATING_PRIVATE:
            return newState == DeviceState::COMPUTED_PUBLIC ||
                   newState == DeviceState::ERROR;

        case DeviceState::COMPUTED_PUBLIC:
            return newState == DeviceState::WAITING_PEER_PUBLIC ||
                   newState == DeviceState::ERROR;

        case DeviceState::WAITING_PEER_PUBLIC:
            return newState == DeviceState::COMPUTED_SHARED_SECRET ||
                   newState == DeviceState::ERROR;

        case DeviceState::COMPUTED_SHARED_SECRET:
            return newState == DeviceState::DONE ||
                   newState == DeviceState::ERROR;

        case DeviceState::DONE:
            return newState == DeviceState::WAITING_PARAMS ||
                   newState == DeviceState::ERROR;

        case DeviceState::ERROR:
            return newState == DeviceState::WAITING_PARAMS ||
                   newState == DeviceState::WIFI_CONNECTING ||
                   newState == DeviceState::SERVER_CONNECTING;

        default:
            return false;
    }
}

const char* StateMachine::stateToString(DeviceState state) const {
    switch (state) {
        case DeviceState::BOOT: return "BOOT";
        case DeviceState::WIFI_CONNECTING: return "WIFI_CONNECTING";
        case DeviceState::SERVER_CONNECTING: return "SERVER_CONNECTING";
        case DeviceState::WAITING_PARAMS: return "WAITING_PARAMS";
        case DeviceState::READY: return "READY";
        case DeviceState::GENERATING_PRIVATE: return "GENERATING_PRIVATE";
        case DeviceState::COMPUTED_PUBLIC: return "COMPUTED_PUBLIC";
        case DeviceState::WAITING_PEER_PUBLIC: return "WAITING_PEER_PUBLIC";
        case DeviceState::COMPUTED_SHARED_SECRET: return "COMPUTED_SHARED_SECRET";
        case DeviceState::DONE: return "DONE";
        case DeviceState::ERROR: return "ERROR";
        default: return "UNKNOWN";
    }
}

void StateMachine::emitStateChange(DeviceState oldState, DeviceState newState) const {
    Serial.print("[STATE] ");
    Serial.print(stateToString(oldState));
    Serial.print(" -> ");
    Serial.println(stateToString(newState));
}