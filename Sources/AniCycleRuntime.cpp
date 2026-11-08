// AniCycle object logic (also AniCycleNormal)
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
    case 0x4918b0:
        return 1;
    default:
        return -1;
    }
}

// 0x4918b0. cdecl, 1 stack argument (the object), returns void (EAX is 1).
// Object fields: +0x08 flags, +0x6c state block, +0x188 cycle sub-object,
// +0x190 cycle name. State block: +0x1c phase.
uint32_t function_4918b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase == 0) {
        run.put(object + 0x08, run.get(object + 0x08) | 1);
        if (run.get(object + 0x190) == 0)
            run.call(0x4c79e0, object, {0x5240d8, 0});
        run.put(state + 0x1c, 5);
    } else if (phase == 5) {
        run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4918b0:
        return function_4918b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_ani_cycle_entry, owned, body)
