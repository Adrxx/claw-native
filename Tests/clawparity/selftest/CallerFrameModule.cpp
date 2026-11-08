// Synthetic caller-frame probes, independent of original game code.
// 0x401000 and 0x401020 call the original 0x401050, which reads the caller's EBP.
#include "ClawRuntime.hpp"
namespace {
int owned(uint32_t function) { return function == 0x401000 || function == 0x401020 ? 1 : -1; }
uint32_t body(claw::Run &run, uint32_t function, uint32_t, const uint32_t *arguments) {
    if (function == 0x401020) {
        run.call(0x401050, 0, {arguments[0]});
        return run.call(0x401050, 0, {arguments[0]});
    }
    if (arguments[0] == 0xBAD)
        return run.call(0x401050, 0, {arguments[0], arguments[0]});
    if (arguments[0] == 0xBAE)
        return run.call(0x401050, 7, {arguments[0]});
    return run.call(0x401050, 0, {arguments[0]});
}
}
CLAW_MODULE_ENTRY(claw_caller_frame_selftest_entry, owned, body)
