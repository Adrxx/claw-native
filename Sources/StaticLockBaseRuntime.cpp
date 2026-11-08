// Complete original embedded lock base constructor with physical RET4
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4a2f62:
        return 1;
    default:
        return -1;
    }
}

// 0x4a2f62 OriginalEmbeddedLockBaseConstructor. thiscall, 1 stack argument(s), returns void.
uint32_t function_4a2f62(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eax = context.ecx;
    // +0x04 is the base lock field; +0x00 is its initial vtable.
    uint32_t value = run.get(context.eax + 0x04);
    run.put(context.eax + 0x04, value & 0u);
    context.eflags = 0x46u;
    run.put(context.eax + 0x00, 0x511e34u);
    return context.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4a2f62:
        return function_4a2f62(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4a2f62: return {2047u, 2047u, 0u, 4u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_static_lock_base_entry, owned, source_contract, body)
