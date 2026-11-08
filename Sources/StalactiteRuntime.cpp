// Stalactite object logic
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
    case 0x48e4a0:
        return 1;
    default:
        return -1;
    }
}

// 0x48e4a0. Object logic callback. Object +0x6c is the state block: +0x18
// the logic helper object, +0x1c the state (0 start, 0x1d, 0x1e, 0x3e8 idle).
uint32_t function_48e4a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t block = run.get(object + 0x6c);
    uint32_t state = run.get(block + 0x1c);
    if (state == 0x1d) {
        uint32_t helper = run.get(block + 0x18);
        run.vcall(helper, 0x20);
    } else if (state == 0x1e) {
        uint32_t helper = run.get(block + 0x18);
        run.vcall(helper, 0x1c);
    } else if (state == 0) {
        run.put(block + 0x1c, 0x3e8);
        uint32_t memory = run.call(0x4f63ec, 0, {0x1c8});
        uint32_t created = 0;
        if (memory)
            created = run.call(0x48e990, memory, {object});
        // The original dereferences the result without a null check.
        run.vcall(created, 0x10);
        run.put(block + 0x18, created);
    } else if (state != 0x3e8) {
        uint32_t helper = run.get(block + 0x18);
        run.call(0x4dc870, 0, {helper});
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48e4a0:
        return function_48e4a0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_stalactite_entry, owned, body)
