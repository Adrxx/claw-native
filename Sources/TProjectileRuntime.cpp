// TProjectile object logic
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
    case 0x497eb0:
        return 1;
    default:
        return -1;
    }
}

// 0x497eb0. Projectile object logic. Object +0x6c is the logic state; state
// +0x18 is the helper object, state +0x1c is the phase.
uint32_t function_497eb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase > 0x1d) {
        if (phase == 0x1e) {
            uint32_t helper = run.get(state + 0x18);
            run.call(run.get(run.get(helper) + 0x1c), helper, {});
        } else if (phase != 0x3e8) {
            run.call(0x4dc870, 0, {run.get(state + 0x18)});
        }
    } else if (phase == 0x1d) {
        uint32_t helper = run.get(state + 0x18);
        run.call(run.get(run.get(helper) + 0x20), helper, {});
    } else if (phase == 0) {
        run.put(state + 0x1c, 0x3e8);
        uint32_t memory = run.call(0x4f63ec, 0, {0x64});
        uint32_t created = 0;
        if (memory)
            created = run.call(0x497f70, memory, {object});
        run.call(run.get(run.get(created) + 0x10), created, {});
        run.put(state + 0x18, created);
    } else {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x497eb0:
        return function_497eb0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_t_projectile_entry, owned, body)
