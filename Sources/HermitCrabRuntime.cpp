// HermitCrab object logic
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x449c40:
        return 1;
    default:
        return -1;
    }
}

// 0x449c40. cdecl, 1 stack argument(s), returns void.
uint32_t function_449c40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c is its logic record; record +0x1c is the state and
    // +0x18 holds the creature instance.
    uint32_t record = run.get(object + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state == 0) {
        run.put(record + 0x1c, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x438});
        uint32_t creature = 0;
        if (allocation)
            creature = run.call(0x44a380, allocation, {object});
        run.vcall(creature, 0x10);
        run.put(record + 0x18, creature);
    } else if (state == 29) {
        run.vcall(run.get(record + 0x18), 0x20);
    } else if (state == 30) {
        run.vcall(run.get(record + 0x18), 0x1c);
    } else if (state != 1000) {
        run.call(0x4dc870, 0, {run.get(record + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x449c40:
        return function_449c40(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_hermit_crab_entry, owned, body)
