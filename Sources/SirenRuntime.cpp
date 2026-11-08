// Siren object logic
//
// Original v1.0 callback translated through the canonical runtime.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

constexpr uint32_t objectState = 0x6c; // Object's callback state pointer.
constexpr uint32_t stateCreature = 0x18; // Callback state's creature pointer.
constexpr uint32_t stateEvent = 0x1c; // Callback state's event code.

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x489730:
        return 1;
    default:
        return -1;
    }
}

// 0x489730. cdecl, 1 stack argument(s), returns void.
uint32_t function_489730(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + objectState);
    uint32_t event = run.get(state + stateEvent);
    if (event == 0) {
        run.put(state + stateEvent, 1000);
        uint32_t creature = run.call(0x4f63ec, 0, {0x4b0});
        if (creature != 0)
            creature = run.call(0x489c50, creature, {object});
        run.vcall(creature, 0x10);
        run.put(state + stateCreature, creature);
    } else if (event == 29) {
        run.vcall(run.get(state + stateCreature), 0x20);
    } else if (event == 30) {
        run.vcall(run.get(state + stateCreature), 0x1c);
    } else if (event != 1000) {
        run.call(0x4dc870, 0, {run.get(state + stateCreature)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x489730:
        return function_489730(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_siren_entry, owned, body)
