// SkullCannon object logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x48a800:
        return 1;
    default:
        return -1;
    }
}

// 0x48a800. cdecl, 1 stack argument(s), returns void.
uint32_t function_48a800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c holds callback state; state +0x1c is the message and
    // state +0x18 holds the constructed cannon instance.
    uint32_t state = run.get(object + 0x6c);
    uint32_t message = run.get(state + 0x1c);
    if (message == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x7c});
        uint32_t cannon = 0;
        if (allocation)
            cannon = run.call(0x48a8c0, allocation, {object});
        run.vcall(cannon, 0x10);
        run.put(state + 0x18, cannon);
    } else if (message == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (message == 0x1e) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (message != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48a800:
        return function_48a800(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_skull_cannon_entry, owned, body)
