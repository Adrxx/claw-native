// CrabNest object logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x432570:
        return 1;
    default:
        return -1;
    }
}

// 0x432570. cdecl, 1 stack argument(s), returns void.
uint32_t function_432570(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c); // Object state record.
    uint32_t action = run.get(state + 0x1c); // Pending action code.
    if (action == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t creature = run.call(0x4f63ec, 0, {0x58});
        if (creature)
            creature = run.call(0x432a60, creature, {object});
        run.vcall(creature, 0x10);
        run.put(state + 0x18, creature); // Created creature pointer.
    } else if (action == 29) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (action == 30) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (action != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x432570:
        return function_432570(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_crab_nest_entry, owned, body)
