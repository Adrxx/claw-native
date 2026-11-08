// TownGuard1 object logic
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
    case 0x496050:
        return 1;
    default:
        return -1;
    }
}

// 0x496050. Object logic callback. The object's +0x6c points to a state block:
// +0x18 is the helper object and +0x1c is the state number.
// State 0 builds the helper (0x498 bytes) and enters state 1000. State 0x1d and
// 0x1e call virtual methods 0x20 and 0x1c of the helper. State 1000 does nothing.
// Any other state passes the helper to 0x4dc870.
uint32_t function_496050(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t block = run.get(object + 0x6c);
    uint32_t state = run.get(block + 0x1c);
    if (state > 0x1d) {
        if (state == 0x1e) {
            uint32_t helper = run.get(block + 0x18);
            run.vcall(helper, 0x1c);
            return 1;
        }
        if (state == 0x3e8)
            return 1;
    } else {
        if (state == 0x1d) {
            uint32_t helper = run.get(block + 0x18);
            run.vcall(helper, 0x20);
            return 1;
        }
        if (state == 0) {
            run.put(block + 0x1c, 0x3e8);
            uint32_t memory = run.call(0x4f63ec, 0, {0x498});
            uint32_t helper = 0;
            if (memory)
                helper = run.call(0x496110, memory, {object});
            run.vcall(helper, 0x10);
            run.put(block + 0x18, helper);
            return 1;
        }
    }
    uint32_t helper = run.get(block + 0x18);
    run.call(0x4dc870, 0, {helper});
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x496050:
        return function_496050(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_town_guard1_entry, owned, body)
