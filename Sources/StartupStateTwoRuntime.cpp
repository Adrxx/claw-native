// Original startup state 2 lifecycle
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
    case 0x408b30:
        return 3;
    case 0x408bf0:
        return 0;
    case 0x408c20:
        return 1;
    case 0x408d30:
        return 1;
    case 0x408e20:
        return 0;
    case 0x408f50:
        return 0;
    case 0x408fa0:
        return 0;
    case 0x4293f0:
        return 1;
    case 0x429410:
        return 0;
    default:
        return -1;
    }
}

// 0x408b30. thiscall, 3 stack argument(s), returns u32.
uint32_t function_408b30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x408b30);
}

// 0x408bf0. thiscall, 0 stack argument(s), returns void.
uint32_t function_408bf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x408bf0);
}

// 0x408c20. thiscall, 1 stack argument(s), returns u32.
uint32_t function_408c20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x408c20);
}

// 0x408d30. thiscall, 1 stack argument(s), returns u32.
uint32_t function_408d30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x408d30);
}

// 0x408e20. thiscall, 0 stack argument(s), returns u32.
uint32_t function_408e20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x408e20);
}

// 0x408f50. thiscall, 0 stack argument(s), returns void.
uint32_t function_408f50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x408f50);
}

// 0x408fa0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_408fa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x408fa0);
}

// 0x4293f0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4293f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x4293f0);
}

// 0x429410. thiscall, 0 stack argument(s), returns void.
uint32_t function_429410(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x429410);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x408b30:
        return function_408b30(run, receiver, arguments);
    case 0x408bf0:
        return function_408bf0(run, receiver, arguments);
    case 0x408c20:
        return function_408c20(run, receiver, arguments);
    case 0x408d30:
        return function_408d30(run, receiver, arguments);
    case 0x408e20:
        return function_408e20(run, receiver, arguments);
    case 0x408f50:
        return function_408f50(run, receiver, arguments);
    case 0x408fa0:
        return function_408fa0(run, receiver, arguments);
    case 0x4293f0:
        return function_4293f0(run, receiver, arguments);
    case 0x429410:
        return function_429410(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_startup_state_two_entry, owned, body)
