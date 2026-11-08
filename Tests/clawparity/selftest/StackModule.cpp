// Hand-written synthetic callers for stack backing and bridge tests. No game code.
#include "ClawRuntime.hpp"

namespace {
int owned(uint32_t function) {
    return function == 0x401000 || function == 0x401010 ? 4 : -1;
}

uint32_t body(claw::Run &run, uint32_t function, uint32_t, const uint32_t *args) {
    if (function == 0x401010) {
        uint32_t sum = 0;
        for (uint32_t i = 0; i < args[1]; ++i) {
            run.put8(args[0] + i, uint8_t(i));
            sum += run.get8(args[0] + i);
        }
        return sum;
    }
    uint32_t local = run.automatic(-4);
    run.put(local, 0x13579bdf);
    run.stackPointer = args[3];
    uint32_t result = run.call(args[0], 0, {args[1], args[2], local});
    // The original nested callee updated a low stack local. Read it after the
    // bridge copied memory back, then check the outer escaped local separately.
    run.put(args[2] + 16, run.get(run.get(args[2])));
    run.put(args[2] + 20, run.get(local));
    return result;
}
}

CLAW_MODULE_ENTRY(claw_stack_selftest_entry, owned, body)
