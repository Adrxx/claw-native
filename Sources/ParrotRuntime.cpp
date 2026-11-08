// Parrot object logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x465580:
        return 1;
    default:
        return -1;
    }
}

// 0x465580. cdecl, 1 stack argument(s), returns void.
uint32_t function_465580(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Object +0x6c is its logic context; context +0x1c is the message,
    // and +0x18 is the creature instance.
    uint32_t object = arguments[0];
    uint32_t context = run.get(object + 0x6c);
    uint32_t message = run.get(context + 0x1c);
    if (message == 0) {
        run.put(context + 0x1c, 1000);
        uint32_t creature = run.call(0x4f63ec, 0, {0x450});
        if (creature)
            creature = run.call(0x465640, creature, {object});
        run.vcall(creature, 0x10);
        run.put(context + 0x18, creature);
    } else if (message == 29) {
        run.vcall(run.get(context + 0x18), 0x20);
    } else if (message == 30) {
        run.vcall(run.get(context + 0x18), 0x1c);
    } else if (message != 1000) {
        run.call(0x4dc870, 0, {run.get(context + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x465580:
        return function_465580(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_parrot_entry, owned, body)
