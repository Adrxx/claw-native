// Independent transport probes, not game code.
#include "ClawRuntime.hpp"
#include <utility>

namespace {
template<size_t... I>
uint32_t send(claw::Run &run, uint32_t target, std::index_sequence<I...>) {
    return run.call(target, 0, {uint32_t(0x81230000u + I * 0x10203u)...});
}
template<size_t... I>
uint32_t sourceSend(claw::Run &run, ClawSourceContext &context, uint32_t pops,
                    std::index_sequence<I...>) {
    return run.source_call(context.eip, 0, 0x401f00, context,
                          {uint32_t(0x81230000u + I * 0x10203u)...}, 0, pops);
}
int owned(uint32_t f) { return f == 0x401000 ? 3 : -1; }
uint32_t body(claw::Run &run, uint32_t, uint32_t, const uint32_t *a) {
    const auto n = a[0], target = a[1];
    run.stackPointer = run.frame - 4 * (n + 1);
    if (a[2]) {
        ClawCall raw{};
        raw.function = target; raw.argumentCount = n;
        if (a[2] == 2) raw.x87ArgumentCount = CLAW_X87_EXACT;
        if (a[2] == 3) raw.sourceContext = reinterpret_cast<ClawSourceContext *>(uintptr_t(1));
        if (a[2] == 4) raw.compilerContext = reinterpret_cast<ClawCompilerContext *>(uintptr_t(1));
        for (uint32_t i = 0; i < CLAW_CALL_ARGUMENT_CAPACITY; ++i)
            raw.arguments[i] = 0x81230000u + i * 0x10203u;
        return run.host.call(run.host.user, &raw);
    }
    switch (n) {
#define SEND(N) case N: return send(run, target, std::make_index_sequence<N>{});
    SEND(0) SEND(15) SEND(16) SEND(17) SEND(31) SEND(32) SEND(33)
#undef SEND
    default: run.fail(CLAW_FAULT_ABI, target);
    }
}
}
CLAW_MODULE_ENTRY(claw_wide_call_entry, owned, body)

extern "C" uint32_t claw_wide_source(ClawHost *host, ClawSourceContext *context,
                                      uint32_t count, uint32_t pops) {
    try {
        claw::Run run(*host);
        switch (count) {
#define SEND(N) case N: sourceSend(run, *context, pops, std::make_index_sequence<N>{}); break;
        SEND(0) SEND(15) SEND(16) SEND(17) SEND(31) SEND(32) SEND(33)
#undef SEND
        default: run.fail(CLAW_FAULT_ABI);
        }
        return 1;
    } catch (claw::Failure &) { return 0; }
}
