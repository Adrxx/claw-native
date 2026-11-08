// Scene startup sound-controller election and readiness
//
// Recovered from the original game bodies in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4ca280:
        return 1;
    case 0x4cf7e0:
        return 0;
    default:
        return -1;
    }
}

// 0x4ca280 SoundController::initialize. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4ca280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // +0x0c parent; parent +0x20 sound manager; manager +0x78 device.
    const uint32_t parent = run.get(receiver + 0x0c);
    if (parent == 0)
        return 0;
    const uint32_t manager = run.get(parent + 0x20);
    if (arguments[0] == 0) {
        if (manager == 0)
            return 0;
        if (run.get(manager + 0x78) == 0)
            return 0;
    }
    // +0x30 normalized missing-manager flag; +0x2c selected manager.
    run.put(receiver + 0x30, manager == 0 ? 1u : 0u);
    run.put(receiver + 0x2c, manager);
    run.put(0x532c10, 100);
    return 1;
}

// 0x4cf7e0 SoundController::ready. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4cf7e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x2c) != 0)
        return 1;
    if (run.get(receiver + 0x30) != 0)
        return 1;
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4ca280:
        return function_4ca280(run, receiver, arguments);
    case 0x4cf7e0:
        return function_4cf7e0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_scene_startup_composition_canonical_entry, owned, body)
