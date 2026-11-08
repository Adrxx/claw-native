// CannonSwitch object logic
//
// Recovered from the original v1.0 disassembly.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x415350:
        return 1;
    default:
        return -1;
    }
}

// 0x415350. cdecl, 1 stack argument(s), returns void.
uint32_t function_415350(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // +0x6c: switch state object; state +0x1c: command, +0x18: cannon.
    uint32_t state = run.get(object + 0x6c);
    uint32_t command = run.get(state + 0x1c);
    if (command == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x54});
        uint32_t cannon = 0;
        if (allocation != 0)
            cannon = run.call(0x415840, allocation, {object});
        run.vcall(cannon, 0x10);
        run.put(state + 0x18, cannon);
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
    case 0x415350:
        return function_415350(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_cannon_switch_entry, owned, body)
