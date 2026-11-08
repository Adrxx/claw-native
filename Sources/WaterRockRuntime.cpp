// WaterRock object logic
//
// Canonical state-machine implementation.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x49de10:
        return 1;
    default:
        return -1;
    }
}

// 0x49de10. cdecl, 1 stack argument(s), returns void.
uint32_t function_49de10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c holds state data; state +0x1c is the current phase.
    uint32_t data = run.get(object + 0x6c);
    uint32_t phase = run.get(data + 0x1c);
    if (phase == 0) {
        run.call(0x4c79e0, object, {0x52dd50, 0});
        // Object +8 flags, +0x164 behavior flags, +0x64 delay.
        uint32_t flags = run.get(object + 8) | 1;
        uint32_t behavior = run.get(object + 0x164) | 0x10040;
        uint32_t delay = run.get(object + 0x64);
        // Object +0x128..+0x134 collision rectangle, +0xd0 collision mode.
        run.put(object + 0x128, 0xffffffe7);
        run.put(object + 0x12c, 0x5a);
        run.put(object + 0x130, 0x19);
        run.put(object + 0x134, 0xac);
        run.put(object + 0xd0, 0x80);
        run.put(object + 8, flags);
        run.put(object + 0x164, behavior);
        // Object +0x158 and +0x15c reset motion values.
        run.put(object + 0x158, 0);
        run.put(object + 0x15c, 0);
        if (delay == 0) {
            run.put(object + 0x64, 2000);
            run.put(object + 8, flags | 0x20000);
        }
        // State +0xbc is the default timing value.
        if (run.get(data + 0xbc) == 0)
            run.put(data + 0xbc, 0x4b0);
        run.put(data + 0x1c, 5);
        return 1;
    }
    if (phase == 5) {
        // Object +0x188 is the animation controller.
        run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
        uint32_t player = run.get(0x537e88);
        // Player +8 contact flags, +0x80 supporting object.
        if (!(run.get8(player + 8) & 0x10))
            return 1;
        if (run.get(player + 0x80) != object)
            return 1;
        run.call(0x4c79e0, object, {0x52dd38, 0});
        // State +0x20 phase timer, +0x64 pending impulse.
        run.put(data + 0x20, 0xfa);
        run.put(data + 0x1c, 6);
        run.put(data + 0x64, 1);
        return 1;
    }
    if (phase == 0x457) {
        run.call(0x4c79e0, object, {0x52dd38, 0});
        run.put(data + 0x20, 0xfa);
        run.put(data + 0x1c, 0x3f0);
        run.put(data + 0x64, 1);
        return 1;
    }
    if (phase != 6 && phase != 0x3f0)
        return 1;
    uint32_t advanced = run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
    if (advanced == 1 && run.get(data + 0x64) == 1) {
        if (phase == 0x3f0) {
            run.put(object + 0x164, run.get(object + 0x164) | 0x20000);
        } else {
            uint32_t player = run.get(0x537e88);
            if ((run.get8(player + 8) & 0x10) && run.get(player + 0x80) == object) {
                // State +0x38 is the configured impulse strength.
                uint32_t strength = run.get(data + 0x38);
                if (s32(strength) <= 0)
                    strength = 0x1c2;
                run.call(0x41e810, 0, {player, strength});
            }
        }
        run.put(data + 0x64, 0);
    }
    // Animation +0x1c completion indicator and +0x14 active frame state.
    if (run.get(object + 0x1a4) == 0)
        return 1;
    if (run.get(object + 0x19c) != 0)
        return 1;
    if (phase == 0x3f0)
        run.put(object + 0x164, run.get(object + 0x164) & 0xfffdffff);
    run.call(0x4c79e0, object, {0x52dd50, 0});
    run.put(data + 0x1c, 5);
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49de10:
        return function_49de10(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_water_rock_entry, owned, body)
