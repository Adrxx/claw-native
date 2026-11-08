// Application viewport size accelerator commands
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x429e30:
        return 0;
    case 0x429e70:
        return 0;
    case 0x42afd0:
        return 0;
    default:
        return -1;
    }
}

// Application fields used here: +0x0c flag, +0x2c and +0x30 required objects,
// +0x68 viewport size step (1 through 10).

// 0x429e30. Decreases the viewport size step and applies it.
uint32_t function_429e30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x2c) == 0)
        return 0;
    if (run.get(receiver + 0x30) == 0)
        return 0;
    uint32_t ready = run.call(0x42a630, receiver);
    if (ready == 0)
        return 0;
    if (s32(run.get(receiver + 0x68)) <= 1)
        return 0;
    uint32_t size = run.get(receiver + 0x68) - 1;
    run.put(receiver + 0x68, size);
    run.stackPointer = run.frame - 0x14;
    run.call(0x429ed0, receiver, {size, 1, 1});
    return 0;
}

// 0x429e70. Increases the viewport size step and applies it.
uint32_t function_429e70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x2c) == 0)
        return 0;
    if (run.get(receiver + 0x30) == 0)
        return 0;
    uint32_t ready = run.call(0x42a630, receiver);
    if (ready == 0)
        return 0;
    if (s32(run.get(receiver + 0x68)) >= 10)
        return 0;
    uint32_t size = run.get(receiver + 0x68) + 1;
    run.put(receiver + 0x68, size);
    run.stackPointer = run.frame - 0x14;
    run.call(0x429ed0, receiver, {size, 1, 1});
    return 0;
}

// 0x42afd0. True when the object exists, is ready and the +0x0c flag is clear.
uint32_t function_42afd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x2c) == 0)
        return 0;
    uint32_t ready = run.call(0x42a630, receiver);
    if (ready == 0)
        return ready;
    return run.get(receiver + 0xc) == 0 ? 1 : 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x429e30:
        return function_429e30(run, receiver, arguments);
    case 0x429e70:
        return function_429e70(run, receiver, arguments);
    case 0x42afd0:
        return function_42afd0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_application_viewport_accelerators_entry, owned, body)
