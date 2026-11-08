// Synthetic import identity probes, independent of original game code.
#include "ClawRuntime.hpp"
namespace {
int owned(uint32_t function) { return function >= 0x401000 && function <= 0x401030 ? 1 : -1; }
uint32_t body(claw::Run &run, uint32_t function, uint32_t, const uint32_t *arguments) {
    const uint32_t slot = function == 0x401030 ? 0x402004 : 0x402000;
    const uint32_t target = run.get(slot);
    run.stackPointer = run.frame - 8;
    if (function == 0x401010)
        return run.call(target, 0, {});
    if (function == 0x401020)
        return run.call(target, 123, {arguments[0]});
    return run.call(target, 0, {arguments[0]});
}
}
CLAW_MODULE_ENTRY(claw_cached_import_selftest_entry, owned, body)
