// GooVent object logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x448620:
        return 1;
    default:
        return -1;
    }
}

// 0x448620. cdecl, 1 stack argument(s), returns void.
uint32_t function_448620(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // +0x6c holds callback state; state +0x1c is the message and +0x18 the vent.
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c);
    uint32_t message = run.get(state + 0x1c);
    if (message == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t vent = run.call(0x4f63ec, 0, {0x58});
        if (vent)
            vent = run.call(0x4486e0, vent, {object});
        run.vcall(vent, 0x10);
        run.put(state + 0x18, vent);
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
    case 0x448620:
        return function_448620(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_goo_vent_entry, owned, body)
