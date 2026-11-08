// Omar object logic
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4633a0:
        return 1;
    default:
        return -1;
    }
}

// 0x4633a0. cdecl, 1 stack argument(s), returns void.
uint32_t function_4633a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c is its logic record; record +0x1c is the dispatch state.
    uint32_t logic = run.get(object + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        run.put(logic + 0x1c, 1000);
        uint32_t allocated = run.call(0x4f63ec, 0, {0xd48});
        uint32_t creature = 0;
        if (allocated)
            creature = run.call(0x463460, allocated, {object});
        run.vcall(creature, 0x10);
        // Record +0x18 holds the constructed creature.
        run.put(logic + 0x18, creature);
    } else if (state == 0x1d) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (state == 0x1e) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (state != 1000) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4633a0:
        return function_4633a0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_omar_entry, owned, body)
