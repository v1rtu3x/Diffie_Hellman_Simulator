#pragma once

#include <Arduino.h>
#include "types.h"

class StateMachine {
public:
    StateMachine();

    DeviceState getState() const;
    const char* getStateName() const;

    bool transitionTo(DeviceState newState);
    bool canTransitionTo(DeviceState newState) const;

private:
    DeviceState currentState;

    const char* stateToString(DeviceState state) const;
    void emitStateChange(DeviceState oldState, DeviceState newState) const;
};