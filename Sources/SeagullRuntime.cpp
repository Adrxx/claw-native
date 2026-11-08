// Seagull object logic
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
    case 0x486e90:
        return 1;
    default:
        return -1;
    }
}

// 0x486e90. Object-logic callback: drives a state machine kept in the
// object's state record. Object +0x6c is the record; record +0x18 is the
// helper object and record +0x1c is the state.
uint32_t function_486e90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t record = run.get(object + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state == 0x1d) {
        uint32_t helper = run.get(record + 0x18);
        run.call(run.get(run.get(helper) + 0x20), helper);
        return 1;
    }
    if (state == 0x1e) {
        uint32_t helper = run.get(record + 0x18);
        run.call(run.get(run.get(helper) + 0x1c), helper);
        return 1;
    }
    if (state == 0x3e8)
        return 1;
    if (state == 0) {
        run.put(record + 0x1c, 0x3e8);
        uint32_t memory = run.call(0x4f63ec, 0, {0x440});
        uint32_t created = 0;
        if (memory)
            created = run.call(0x486f50, memory, {object});
        run.call(run.get(run.get(created) + 0x10), created);
        run.put(record + 0x18, created);
        return 1;
    }
    run.call(0x4dc870, 0, {run.get(record + 0x18)});
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x486e90:
        return function_486e90(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_seagull_entry, owned, body)
