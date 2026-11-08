// GroundBlower object logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x448d10:
        return 1;
    default:
        return -1;
    }
}

// 0x448d10. cdecl, 1 stack argument(s), returns void.
uint32_t function_448d10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c holds its logic record; record +0x1c is the command,
    // and +0x18 holds the constructed blower instance.
    uint32_t logic = run.get(object + 0x6c);
    uint32_t command = run.get(logic + 0x1c);
    if (command == 0) {
        run.put(logic + 0x1c, 1000);
        run.stackPointer = run.automatic(-28);
        uint32_t blower = run.call(0x4f63ec, 0, {0x50});
        if (blower)
            blower = run.call(0x4490e0, blower, {object});
        run.stackPointer = run.automatic(-24);
        run.vcall(blower, 0x10);
        run.put(logic + 0x18, blower);
    } else if (command == 0x1d) {
        run.stackPointer = run.automatic(-24);
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (command == 0x1e) {
        run.stackPointer = run.automatic(-24);
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (command != 1000) {
        run.stackPointer = run.automatic(-28);
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x448d10:
        return function_448d10(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_ground_blower_entry, owned, body)
