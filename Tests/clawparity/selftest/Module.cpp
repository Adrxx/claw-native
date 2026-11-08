// Native version of the synthetic self-test program. The SELFTEST_* switches
// each introduce one specific error the harness must report.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x401000:
        return 0;
    case 0x401010:
        return 2;
    case 0x401030:
        return 1;
    default:
        return -1;
    }
}

uint32_t sumAndStore(Run &run, uint32_t self) {
    uint32_t total = run.get(self) + run.get(self + 0x4);
#ifdef SELFTEST_WRONG_STORE
    run.put(self + 0xc, total);
#else
    run.put(self + 0x8, total);
#endif
    return total;
}

uint32_t scaledGlobal(Run &run, uint32_t a, uint32_t b) {
    uint32_t value = a * 3 + b;
    (void)run;
#ifndef SELFTEST_SKIP_GLOBAL
    run.put(0x402010, run.get(0x402010) + value);
#endif
#ifdef SELFTEST_WRONG_RETURN
    return value + 1;
#else
    return value;
#endif
}

uint32_t makeBuffer(Run &run, uint32_t self, uint32_t count) {
#ifdef SELFTEST_EXTRA_CALL
    run.icall(0x402000, {count});
#endif
    uint32_t buffer = run.icall(0x402000, {count});
    run.put(self, buffer);
    if (!buffer)
        return 0;
    run.call(0x401060, 0, {buffer, count});
#ifdef SELFTEST_OUT_OF_BOUNDS
    run.put8(buffer + count, 0);
#endif
    return run.get(self);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x401000:
        return sumAndStore(run, receiver);
    case 0x401010:
        return scaledGlobal(run, arguments[0], arguments[1]);
    case 0x401030:
        return makeBuffer(run, receiver, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_selftest_entry, owned, body)
