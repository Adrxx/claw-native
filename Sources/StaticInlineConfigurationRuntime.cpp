// Original static inline display configuration
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x425230:
        return 0;
    default:
        return -1;
    }
}

// 0x425230 Static inline display configuration. cdecl, 0 stack argument(s), returns void.
uint32_t function_425230(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t eax = 0;
    run.put(0x5370d0, 0x280);
    run.put(0x5370c8, eax);
    run.put(0x5370cc, eax);
    run.put(0x5370d4, 0x1e0);
    return eax;
}

// 0x425230. XOR defines EAX and arithmetic flags before the ordered MOVs.
uint32_t source_body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    if (function != 0x425230)
        run.fail(CLAW_FAULT_ABI, function);
    (void)receiver;
    (void)arguments;
    auto &cpu = run.source();
    cpu.eax ^= cpu.eax;
    // XOR clears CF/OF/SF; the pinned original also clears undefined AF.
    // A zero result has even parity and sets ZF. MOV and RET keep flags.
    cpu.eflags = (cpu.eflags & ~0x8d5u) | 0x46u;
    run.put(0x5370d0, 0x280);
    run.put(0x5370c8, cpu.eax);
    run.put(0x5370cc, cpu.eax);
    run.put(0x5370d4, 0x1e0);
    // The source entry wrapper consumes the existing return word exactly once.
    return cpu.eax;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x425230:
        return function_425230(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x425230:
        return {0x7ffu, 0x7ffu, 0x472u, 0u};
    default:
        return {};
    }
}
static bool source_optional(uint32_t function) {
    switch (function) {
    case 0x425230:
        return true;
    default:
        return false;
    }
}
CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_static_inline_configuration_entry, owned, source_contract, source_optional, body, source_body)
