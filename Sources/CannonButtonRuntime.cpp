// CannonButton object logic
//
// Recovered from the original v1.0 instructions.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x414cc0:
        return 1;
    default:
        return -1;
    }
}

// 0x414cc0. cdecl, 1 stack argument(s), returns void.
uint32_t function_414cc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c); // Object's logic-state pointer.
    uint32_t command = run.get(state + 0x1c); // Logic command.
    if (command == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t allocated = run.call(0x4f63ec, 0, {0x54});
        uint32_t button = 0;
        if (allocated)
            button = run.call(0x415090, allocated, {object});
        run.vcall(button, 0x10);
        run.put(state + 0x18, button); // Logic's constructed button pointer.
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
    case 0x414cc0:
        return function_414cc0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_cannon_button_entry, owned, body)
