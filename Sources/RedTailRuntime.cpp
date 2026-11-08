// RedTail object logic
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x47f6e0:
        return 1;
    default:
        return -1;
    }
}

// 0x47f6e0. cdecl, 1 stack argument(s), returns void.
uint32_t function_47f6e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t parent = arguments[0];
    uint32_t state = run.get(parent + 0x6c); // Parent's logic-state pointer.
    uint32_t command = run.get(state + 0x1c); // Requested logic command.
    if (command == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t object = run.call(0x4f63ec, 0, {0x508});
        if (object != 0)
            object = run.call(0x47ff90, object, {parent});
        run.vcall(object, 0x10);
        run.put(state + 0x18, object); // Active RedTail object.
    } else if (command == 29) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (command == 30) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (command != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x47f6e0:
        return function_47f6e0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_red_tail_entry, owned, body)
