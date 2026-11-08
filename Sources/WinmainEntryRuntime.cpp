// Original application entry
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
    case 0x49f8d0:
        return 4;
    default:
        return -1;
    }
}

// 0x49f8d0. stdcall, 4 stack argument(s), returns u32.
uint32_t function_49f8d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x49f8d0);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49f8d0:
        return function_49f8d0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x49f8d0: return {2047u, 2047u, 0u, 16u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_winmain_entry_entry, owned, source_contract, body)
