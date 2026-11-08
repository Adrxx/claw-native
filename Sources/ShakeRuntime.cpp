// Shake object callback: creates its controller on initialization, dispatches
// start/stop events through virtual methods, and forwards other events to the
// original controller update routine.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4887b0:
        return 1;
    default:
        return -1;
    }
}

// 0x4887b0. cdecl, 1 stack argument(s), returns void.
uint32_t function_4887b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c: callback state; state +0x1c: event code.
    uint32_t state = run.get(object + 0x6c);
    uint32_t event = run.get(state + 0x1c);
    // State +0x18: shake controller.
    if (event == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x54});
        uint32_t controller = 0;
        if (allocation != 0)
            controller = run.call(0x488870, allocation, {object});
        run.vcall(controller, 0x10);
        run.put(state + 0x18, controller);
    } else if (event == 29) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (event == 30) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (event != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4887b0:
        return function_4887b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_shake_entry, owned, body)
