// BossStagerAttack contact callback
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x48e430:
        return 1;
    default:
        return -1;
    }
}

// 0x48e430. cdecl, one actor argument, returns whether contact was accepted.
uint32_t function_48e430(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t player = run.get(0x537e88);
    uint32_t primary = run.get(actor + 0x6c); // Captured primary record.
    uint32_t mode = run.get(player + 0xcc); // Player mode.
    if (mode != 2 && mode != 1)
        return 0;
    uint32_t manager = run.get(0x5371fc);
    uint32_t x = run.get(player + 0x4c); // Player X coordinate.
    uint32_t coordinates = run.get(manager + 0x2c); // Coordinate record.
    run.put(coordinates + 0x44, x); // Target X coordinate.
    manager = run.get(0x5371fc);
    player = run.get(0x537e88);
    coordinates = run.get(manager + 0x2c);
    uint32_t y = run.get(player + 0x50); // Player Y coordinate.
    run.put(coordinates + 0x48, y); // Target Y coordinate.
    run.put(0x53c9f8, run.get(0x53c9f8) + 0x1d4c0); // Contact timer.
    run.put(actor + 0x08, run.get(actor + 0x08) | 1); // Actor flags.
    run.put(primary + 0x1c, 0x1f43); // Primary record state.
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48e430:
        return function_48e430(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_boss_stager_attack_entry, owned, body)
