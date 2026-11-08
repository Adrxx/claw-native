// RedTailPirate object logic
// Implements the original object callback through the canonical runtime.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x482820:
        return 1;
    default:
        return -1;
    }
}

// 0x482820. cdecl, 1 stack argument(s), returns void.
uint32_t function_482820(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c points to callback state; state +0x1c is the event code
    // and state +0x18 holds the constructed pirate creature.
    constexpr uint32_t callbackStateOffset = 0x6c;
    constexpr uint32_t eventOffset = 0x1c;
    constexpr uint32_t creatureOffset = 0x18;
    uint32_t state = run.get(object + callbackStateOffset);
    uint32_t event = run.get(state + eventOffset);
    if (event == 0) {
        run.put(state + eventOffset, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x4b8});
        uint32_t creature = 0;
        if (allocation)
            creature = run.call(0x4828e0, allocation, {object});
        run.vcall(creature, 0x10);
        run.put(state + creatureOffset, creature);
    } else if (event == 29) {
        run.vcall(run.get(state + creatureOffset), 0x20);
    } else if (event == 30) {
        run.vcall(run.get(state + creatureOffset), 0x1c);
    } else if (event != 1000) {
        run.call(0x4dc870, 0, {run.get(state + creatureOffset)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x482820:
        return function_482820(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_red_tail_pirate_entry, owned, body)
