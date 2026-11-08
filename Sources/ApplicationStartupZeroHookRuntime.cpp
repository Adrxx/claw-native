// Original contextual startup zero hook
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x42a680:
        return 0;
    default:
        return -1;
    }
}

// 0x42a680. Contextual startup thiscall, no stack arguments, returns zero.
uint32_t function_42a680(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42a680:
        return function_42a680(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_application_startup_zero_hook_entry, owned, body)
