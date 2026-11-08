// Test-only synthetic entries. Registered only in the temporary host-test
// header generated under work/, never in the application's canonical registry.
#include "ClawRuntime.hpp"

namespace {
ClawHost *observedHost = nullptr; // borrowed while the Swift test owner is alive
uint32_t restoredAfterFault = 0;
constexpr uint32_t graph = 0x7f001000u, leaf = 0x7f001010u, bounds = 0x7f001020u;
int owned(uint32_t function) { return function == graph || function == leaf || function == bounds ? 4 : -1; }
uint32_t body(claw::Run &run, uint32_t function, uint32_t, const uint32_t *args) {
    observedHost = &run.host;
    if (run.frame != run.host.entryStackPointer || run.stackPointer)
        run.fail(CLAW_FAULT_HOST, function);
    for (uint32_t i = 0; i < 4; ++i) {
        if (run.get(run.automatic(4 + 4 * int32_t(i))) != args[i])
            run.fail(CLAW_FAULT_HOST, function);
    }
    if (function == bounds) {
        if (args[2]) {
            // Expose the active frame to a synchronous dependency. It may
            // inspect aliases, add a conflicting mapping, or fail deliberately.
            return run.call(args[2], 0, {run.frame});
        }
        for (uint32_t i = 0; i < args[1]; ++i)
            run.put8(args[0] + i, uint8_t(i + 1));
        return args[1] ? run.get8(args[0] + args[1] - 1) : run.frame;
    }
    uint32_t local = run.automatic(-4);
    run.put(local, 0xabc00000u + args[1]);
    run.put(args[0] + args[1] * 4, run.frame);
    if (args[3])
        run.put(args[3], run.get(args[3]) + 1);
    if (args[2] == 8 && args[1] == 0)
        run.fail(CLAW_FAULT_MEMORY, 0x0badf00d);
    if (function == graph && args[1]) {
        run.stackPointer = run.frame - 32;
        switch (args[2]) {
        case 1: run.stackPointer = 0; break;
        case 2: run.stackPointer = run.frame; break;
        case 3: run.stackPointer = run.frame + 4; break;
        case 4: run.stackPointer = run.frame - 16; break;
        case 5: run.stackPointer = CLAW_STACK_BASE - 4; break;
        case 6: run.stackPointer = 0xfffffffcu; break;
        case 7: run.stackPointer = run.frame - 33; break;
        default: break;
        }
        try {
            run.call(graph, 0, {args[0], args[1] - 1, args[2], local});
            if (run.host.entryStackPointer != run.frame)
                run.fail(CLAW_FAULT_HOST, function);
            run.call(leaf, 0, {args[0], 0, 0, local});
            if (run.host.entryStackPointer != run.frame)
                run.fail(CLAW_FAULT_HOST, function);
        } catch (claw::Failure &) {
            restoredAfterFault = run.host.entryStackPointer == run.frame;
            throw;
        }
    }
    return run.get(local);
}
}
CLAW_MODULE_ENTRY(claw_frame_test_entry, owned, body)

// These probes are test-only. The borrowed host must remain alive when read.
extern "C" uint32_t claw_frame_test_scope_state() {
    return observedHost ? (observedHost->entryStackPointer == 0 ? 1u : 0u) |
        (observedHost->remainingOperations == nullptr ? 2u : 0u) : 0;
}
extern "C" uint32_t claw_frame_test_restored_after_fault() { return restoredAfterFault; }
