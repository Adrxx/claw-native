// AquatisCrack object logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x406400:
        return 1;
    default:
        return -1;
    }
}

// 0x406400. cdecl, 1 stack argument(s), returns void.
uint32_t function_406400(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c is the logic state; state +0x1c is the command and
    // state +0x18 is the associated crack controller.
    uint32_t state = run.get(object + 0x6c);
    uint32_t command = run.get(state + 0x1c);
    if (command == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t controller = run.call(0x4f63ec, 0, {0x70});
        if (controller)
            controller = run.call(0x4068f0, controller, {object});
        run.vcall(controller, 0x10);
        run.put(state + 0x18, controller);
    } else if (command == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (command == 0x1e) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (command != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x406400:
        return function_406400(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_aquatis_crack_entry, owned, body)
