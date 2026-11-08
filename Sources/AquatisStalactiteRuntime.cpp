// AquatisStalactite object logic
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4073e0:
        return 1;
    default:
        return -1;
    }
}

// 0x4073e0. cdecl, 1 stack argument(s), returns void.
uint32_t function_4073e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c holds logic data; logic +0x1c is the command and +0x18 the creature.
    uint32_t logic = run.get(object + 0x6c);
    uint32_t command = run.get(logic + 0x1c);
    if (command == 0) {
        run.put(logic + 0x1c, 1000);
        uint32_t creature = run.call(0x4f63ec, 0, {0x1b8});
        if (creature)
            creature = run.call(0x4078b0, creature, {object});
        run.vcall(creature, 0x10);
        run.put(logic + 0x18, creature);
    } else if (command == 0x1d) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (command == 0x1e) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (command != 1000) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4073e0:
        return function_4073e0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_aquatis_stalactite_entry, owned, body)
