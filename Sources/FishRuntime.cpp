// Fish object callback: creates its creature, dispatches lifecycle messages,
// and forwards other messages to the original creature update routine.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x441be0:
        return 1;
    default:
        return -1;
    }
}

// 0x441be0. Object +0x6c is its logic record; record +0x18 holds the
// creature and +0x1c holds the callback message. Message 1000 is idle.
uint32_t function_441be0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t record = run.get(object + 0x6c);
    uint32_t message = run.get(record + 0x1c);
    if (message == 0) {
        run.put(record + 0x1c, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x430});
        uint32_t creature = 0;
        if (allocation)
            creature = run.call(0x4420e0, allocation, {object});
        run.vcall(creature, 0x10);
        run.put(record + 0x18, creature);
    } else if (message == 29) {
        run.vcall(run.get(record + 0x18), 0x20);
    } else if (message == 30) {
        run.vcall(run.get(record + 0x18), 0x1c);
    } else if (message != 1000) {
        run.call(0x4dc870, 0, {run.get(record + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x441be0:
        return function_441be0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_fish_entry, owned, body)
