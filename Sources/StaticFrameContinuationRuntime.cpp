// Original caller-frame continuation leaf
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4dc680:
        return 0;
    default:
        return -1;
    }
}

// 0x4dc680. cdecl, 0 stack argument(s), returns u32.
uint32_t function_4dc680(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    // The inherited EBP is opaque; only the checked read grants access.
    context.eax = run.get(context.ebp + 0x04);
    context.eip = 0x4dc683;
    return context.eax;
}

ClawSourceContract contract(uint32_t function) {
    if (function == 0x4dc680)
        return {0x7ff, 0x7ff, 0x472, 0};
    return {};
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4dc680:
        return function_4dc680(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_SOURCE_MODULE_ENTRY(claw_static_frame_continuation_entry, owned, contract, body)
