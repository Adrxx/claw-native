// PegLeg object logic
//
// Original v1.0 callback dispatches the object state to its creature.
// Unowned construction and update functions run through the shared runtime.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4689b0:
        return 1;
    default:
        return -1;
    }
}

// 0x4689b0. cdecl, one object argument; EAX is 1 (declared void).
// Object +0x6c holds callback data; data +0x18 holds the creature and
// +0x1c holds the unsigned callback state.
uint32_t function_4689b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    constexpr uint32_t callbackDataOffset = 0x6c;
    constexpr uint32_t creatureOffset = 0x18;
    constexpr uint32_t stateOffset = 0x1c;
    uint32_t object = arguments[0];
    uint32_t data = run.get(object + callbackDataOffset);
    uint32_t state = run.get(data + stateOffset);
    if (state == 0) {
        run.put(data + stateOffset, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x4e8});
        uint32_t creature = 0;
        if (allocation != 0)
            creature = run.call(0x468eb0, allocation, {object});
        run.vcall(creature, 0x10);
        run.put(data + creatureOffset, creature);
    } else if (state == 29) {
        run.vcall(run.get(data + creatureOffset), 0x20);
    } else if (state == 30) {
        run.vcall(run.get(data + creatureOffset), 0x1c);
    } else if (state != 1000) {
        run.call(0x4dc870, 0, {run.get(data + creatureOffset)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4689b0:
        return function_4689b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_peg_leg_entry, owned, body)
