// ConveyorBelt object logic
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
    case 0x431320:
        return 1;
    default:
        return -1;
    }
}

// 0x431320. Object-logic callback; `object` is the argument. Fields: object+0x6c
// state block; state+0x18 the belt component, state+0x1c the phase.
// Phase 0 builds the component (0x58 bytes) and then parks the phase at 1000.
// Phase 0x1d and 0x1e call a component method, 1000 does nothing, any other
// phase calls the generic updater. The original returns 1.
uint32_t function_431320(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase == 0x1d) {
        uint32_t component = run.get(state + 0x18);
        run.vcall(component, 0x20);
        return 1;
    }
    if (phase == 0) {
        run.put(state + 0x1c, 0x3e8);
        uint32_t memory = run.call(0x4f63ec, 0, {0x58});
        uint32_t component = 0;
        if (memory)
            component = run.call(0x431810, memory, {object});
        run.vcall(component, 0x10);
        run.put(state + 0x18, component);
        return 1;
    }
    if (phase == 0x1e) {
        uint32_t component = run.get(state + 0x18);
        run.vcall(component, 0x1c);
        return 1;
    }
    if (phase == 0x3e8)
        return 1;
    run.call(0x4dc870, 0, {run.get(state + 0x18)});
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x431320:
        return function_431320(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_conveyor_belt_entry, owned, body)
