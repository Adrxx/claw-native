// Independently authored counterpart of the synthetic x86 stack-input controls.
#include "ClawRuntime.hpp"

namespace {
int owned(uint32_t function) {
    if (function == 0x401000) return 1;
    if (function == 0x401040) return 0;
    return -1;
}

uint32_t body(claw::Run &run, uint32_t function, uint32_t receiver, const uint32_t *) {
    if (function == 0x401000) {
        uint32_t value = run.get(run.automatic(-16));
        value ^= run.get(run.automatic(4));
        value ^= run.get(run.automatic(0));
        run.put(receiver, value);
        return value;
    }
    (void)receiver;
#ifndef INITIAL_STACK_OMIT_INITIALIZER
    run.put(run.automatic(-16), 0);
#endif
    run.stackPointer = run.automatic(-24);
    run.icall(0x402000, {run.automatic(-16)});
    return run.get(run.automatic(-16));
}
}
CLAW_MODULE_ENTRY(claw_initial_stack_entry, owned, body)
