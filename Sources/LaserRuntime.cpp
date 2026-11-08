// Laser object logic
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4553d0:
        return 1;
    default:
        return -1;
    }
}

// 0x4553d0. cdecl, 1 stack argument(s), returns void.
uint32_t function_4553d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t owner = arguments[0];
    // Owner +0x6c is the state pointer; state +0x1c is its numeric state.
    uint32_t state = run.get(owner + 0x6c);
    uint32_t number = run.get(state + 0x1c);
    if (number <= 29) {
        if (number == 29) {
            // State +0x18 holds the creature pointer.
            run.vcall(run.get(state + 0x18), 0x20);
        } else if (number == 0) {
            run.put(state + 0x1c, 1000);
            uint32_t allocated = run.call(0x4f63ec, 0, {0x58});
            uint32_t creature = 0;
            if (allocated)
                creature = run.call(0x455490, allocated, {owner});
            run.vcall(creature, 0x10);
            run.put(state + 0x18, creature);
        } else {
            run.call(0x4dc870, 0, {run.get(state + 0x18)});
        }
    } else if (number == 30) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (number != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4553d0:
        return function_4553d0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_laser_entry, owned, body)
