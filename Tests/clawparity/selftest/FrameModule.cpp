// Synthetic frame transport probes only; no original game implementation.
#include "ClawRuntime.hpp"

namespace {
int owned(uint32_t function) { return function == 0x401000 ? 2 : -1; }
uint32_t body(claw::Run &run, uint32_t, uint32_t, const uint32_t *args) {
    uint32_t local = run.automatic(-4);
    run.put(local, args[1]);
    run.put(run.automatic(8), args[1] ^ 0x55u);
    run.stackPointer = run.automatic(-16);
    run.call(0x401100, 0, {local, args[0]});
    run.put(args[0], run.get(local));
    run.put(args[0] + 4, local);
    uint32_t result = run.get(run.automatic(8));
    run.put(args[0] + 8, result);
    return result;
}
}
CLAW_MODULE_ENTRY(claw_frame_selftest_entry, owned, body)

namespace {
int argumentOwned(uint32_t function) { return function == 0x401060 ? 2 : -1; }
uint32_t argumentBody(claw::Run &run, uint32_t, uint32_t, const uint32_t *args) {
    const uint32_t destination = run.get(run.automatic(4));
    run.put8(destination, uint8_t(args[1]));
    return run.get(run.automatic(4));
}
}
CLAW_MODULE_ENTRY(claw_frame_arguments_selftest_entry, argumentOwned, argumentBody)

extern "C" uint32_t claw_frame_runtime_selftest() {
    ClawHost host{};
    host.maximumOperations = 1;
    claw::Run first(host), second(host);
    first.tick();
    second.tick(); // A NULL graph budget preserves independent legacy limits.
    if (first.frame != CLAW_STACK_TOP || first.stackPointer || first.operations != 1 || second.operations != 1)
        return 0;
    uint64_t remaining = 1;
    host.remainingOperations = &remaining;
    host.entryStackPointer = CLAW_STACK_TOP - 128;
    claw::Run third(host), fourth(host);
    third.tick();
    try {
        fourth.tick();
        return 0;
    } catch (claw::Failure &) {
        if (remaining || host.fault != CLAW_FAULT_BUDGET || fourth.operations ||
            third.frame != host.entryStackPointer || third.stackPointer)
            return 0;
    }
    // Existing explicit manual frame changes still work without rewriting ESP.
    third.frame -= 64;
    if (third.automatic(-4) != host.entryStackPointer - 68 || third.stackPointer)
        return 0;
    host.fault = 0;
    host.remainingOperations = nullptr;
    host.maximumOperations = 0xffffffffu;
    claw::Run last(host);
    last.operations = 0xffffffffu;
    try {
        last.tick();
        return 0;
    } catch (claw::Failure &) {
        if (host.fault != CLAW_FAULT_BUDGET || last.operations != 0xffffffffu)
            return 0;
    }
    host.fault = 0;
    last.frame = CLAW_STACK_TOP;
    try {
        last.automatic(0x7fffffff);
        return 0;
    } catch (claw::Failure &) {
        return host.fault == CLAW_FAULT_MEMORY;
    }
}
