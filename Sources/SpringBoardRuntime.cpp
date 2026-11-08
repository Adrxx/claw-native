// SpringBoard object logic
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
    case 0x49db90:
        return 1;
    default:
        return -1;
    }
}

// Globals: 0x537960 table of animation records, 0x537e88 player object,
// 0x5430c4 timer argument. Object fields: +0x08 flags, +0x64 counter,
// +0x6c logic record (+0x1c state, +0x20, +0x38, +0x64 phase, +0xbc timer),
// +0x128..+0x137 copied vector, +0xd0, +0x134, +0x158, +0x15c, +0x164 flags,
// +0x188 sub-object (+0x14, +0x1c flags).
void playAnimation(Run &run, uint32_t object, uint32_t offset) {
    uint32_t table = run.get(0x537960);
    run.call(0x4c79e0, object, {table + offset, 0});
}

bool playerHoldsObject(Run &run, uint32_t object) {
    uint32_t player = run.get(0x537e88);
    if ((run.get8(player + 8) & 0x10) == 0)
        return false;
    return run.get(player + 0x80) == object;
}

// 0x49db90. Registered object-logic callback; always returns 1.
uint32_t function_49db90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t logic = run.get(object + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        playAnimation(run, object, 4);
        uint32_t table = run.get(0x537960);
        uint32_t flags = run.get(object + 8);
        run.put(object + 0x128, run.get(table + 0x48));
        run.put(object + 0x12c, run.get(table + 0x4c));
        run.put(object + 0x130, run.get(table + 0x50));
        uint32_t last = run.get(table + 0x54);
        run.put(object + 0xd0, 0x80);
        run.put(object + 0x134, last);
        uint32_t y = run.get(object + 0x134) + 0x20;
        uint32_t other = run.get(object + 0x164) | 0x10040;
        run.put(object + 0x134, y);
        flags |= 1;
        run.put(object + 8, flags);
        run.put(object + 0x164, other);
        run.put(object + 0x158, 0);
        run.put(object + 0x15c, 0);
        if (run.get(object + 0x64) == 0) {
            run.put(object + 0x64, 2000);
            run.put(object + 8, flags | 0x20000);
        }
        if (run.get(logic + 0xbc) == 0)
            run.put(logic + 0xbc, 0x4b0);
        run.put(logic + 0x1c, 5);
        return 1;
    }
    if (state == 5) {
        run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
        if (!playerHoldsObject(run, object))
            return 1;
        playAnimation(run, object, 0x24);
        run.put(logic + 0x20, 0xfa);
        run.put(logic + 0x1c, 6);
        run.put(logic + 0x64, 1);
        return 1;
    }
    if (state == 6) {
        uint32_t sub = object + 0x188;
        uint32_t result = run.call(0x4c82a0, sub, {run.get(0x5430c4)});
        if (result == 1 && run.get(logic + 0x64) == 1) {
            if (playerHoldsObject(run, object)) {
                uint32_t player = run.get(0x537e88);
                uint32_t value = run.get(logic + 0x38);
                if (s32(value) <= 0)
                    value = 0x1c2;
                run.call(0x41e810, 0, {player, value});
            }
            run.put(logic + 0x64, 0);
        }
        if (run.get(sub + 0x1c) == 0)
            return 1;
        if (run.get(sub + 0x14) != 0)
            return 1;
        playAnimation(run, object, 4);
        run.put(logic + 0x1c, 5);
        return 1;
    }
    if (state == 0x3f0) {
        uint32_t sub = object + 0x188;
        uint32_t result = run.call(0x4c82a0, sub, {run.get(0x5430c4)});
        if (result == 1 && run.get(logic + 0x64) == 1) {
            run.put(object + 0x164, run.get(object + 0x164) | 0x20000);
            run.put(logic + 0x64, 0);
        }
        if (run.get(sub + 0x1c) == 0)
            return 1;
        if (run.get(sub + 0x14) != 0)
            return 1;
        run.put(object + 0x164, run.get(object + 0x164) & 0xfffdffffu);
        playAnimation(run, object, 4);
        run.put(logic + 0x1c, 5);
        return 1;
    }
    if (state == 0x457) {
        playAnimation(run, object, 0x24);
        run.put(logic + 0x20, 0xfa);
        run.put(logic + 0x1c, 0x3f0);
        run.put(logic + 0x64, 1);
        return 1;
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49db90:
        return function_49db90(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_spring_board_entry, owned, body)
