// Scene camera mode helpers called by 0x486240: look up/down, climb, reset and shake
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
    case 0x486620:
        return 3;
    case 0x486650:
        return 3;
    case 0x4868e0:
        return 3;
    case 0x486910:
        return 3;
    case 0x486a00:
        return 3;
    default:
        return -1;
    }
}

// Player actor pointer is the global at 0x537e88; its +0x4c is x and +0x50 is y.
// Camera state record: +0x00 x, +0x04 y, +0x08 target x, +0x0c target y, +0x10 shake timer.
// Logic record: +0x1c mode. Global 0x5430c4 is the frame delta, 0x52be14/0x52be18 an override target.

// 0x486620. Look mode 0x18: target is the player position.
uint32_t function_486620(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t logic = arguments[1];
    uint32_t state = arguments[2];
    run.put(logic + 0x1c, 0x18);
    run.put(state + 0x8, run.get(run.get(0x537e88) + 0x4c));
    run.put(state + 0xc, run.get(run.get(0x537e88) + 0x50));
    return 0;
}

// Moves state x toward the target at rate/1000 of the frame delta per step, clamped on overshoot.
void approachX(Run &run, uint32_t state, uint32_t target, uint32_t rate) {
    uint32_t current = run.get(state + 0x0);
    if (s32(current) < s32(target)) {
        uint32_t moved = run.get(0x5430c4) * rate / 1000u + current;
        run.put(state + 0x0, moved);
        if (s32(moved) > s32(target))
            run.put(state + 0x0, target);
    } else if (s32(current) > s32(target)) {
        uint32_t moved = current - run.get(0x5430c4) * rate / 1000u;
        run.put(state + 0x0, moved);
        if (s32(moved) < s32(target))
            run.put(state + 0x0, target);
    }
}

// The same for state y; the delta is read again here, as in the original.
void approachY(Run &run, uint32_t state, uint32_t target, uint32_t rate) {
    uint32_t current = run.get(state + 0x4);
    if (s32(current) < s32(target)) {
        uint32_t moved = run.get(0x5430c4) * rate / 1000u + current;
        run.put(state + 0x4, moved);
        if (s32(moved) > s32(target))
            run.put(state + 0x4, target);
    } else if (s32(current) > s32(target)) {
        uint32_t moved = current - run.get(0x5430c4) * rate / 1000u;
        run.put(state + 0x4, moved);
        if (s32(moved) < s32(target))
            run.put(state + 0x4, target);
    }
}

uint32_t absolute(uint32_t value) {
    uint32_t sign = uint32_t(s32(value) >> 31);
    return (value ^ sign) - sign;
}

// 0x486650. Camera follow: snaps when far (over 500) from the target, then eases
// toward it by player mode (+0xcc): 3 and 4 at rate 4000, 8 at 99999, else 0x486940.
uint32_t function_486650(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t state = arguments[2];
    run.put(state + 0x8, run.get(run.get(0x537e88) + 0x4c));
    run.put(state + 0xc, run.get(run.get(0x537e88) + 0x50));
    uint32_t override = run.get(0x52be14);
    if (override != 0xffffffffu) {
        run.put(state + 0x8, override);
        run.put(state + 0xc, run.get(0x52be18));
        override = run.get(0x52be14);
    }
    uint32_t targetY = run.get(state + 0xc);
    uint32_t y = run.get(state + 0x4);
    uint32_t targetX = run.get(state + 0x8);
    uint32_t distanceY = absolute(targetY - y);
    uint32_t x = run.get(state + 0x0);
    uint32_t distanceX = absolute(targetX - x);
    if (s32(distanceX) > 500 || s32(distanceY) > 500) {
        run.put(state + 0x0, targetX);
        run.put(state + 0x4, targetY);
        override = run.get(0x52be14);
    }
    uint32_t mode = run.get(run.get(0x537e88) + 0xcc);
    if (mode == 3 || mode == 4) {
        if (override != 0xffffffffu) {
            run.put(state + 0x8, override);
            run.put(state + 0xc, run.get(0x52be18));
        }
        approachX(run, state, run.get(state + 0x8), 4000);
        approachY(run, state, run.get(state + 0xc), 4000);
        return 0;
    }
    if (mode == 8) {
        if (override != 0xffffffffu) {
            run.put(state + 0x8, override);
            run.put(state + 0xc, run.get(0x52be18));
        }
        approachX(run, state, run.get(state + 0x8), 99999);
        approachY(run, state, run.get(state + 0xc), 99999);
        return 0;
    }
    run.call(0x486940, 0, {arguments[0], arguments[1], state, 500, 500});
    return 0;
}

// 0x4868e0. Look mode 0x1a: target is the player position, 200 lower.
uint32_t function_4868e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t logic = arguments[1];
    uint32_t state = arguments[2];
    run.put(logic + 0x1c, 0x1a);
    run.put(state + 0x8, run.get(run.get(0x537e88) + 0x4c));
    run.put(state + 0xc, run.get(run.get(0x537e88) + 0x50) + 0xc8);
    return 0;
}

// 0x486910. Look mode 0x138b: target is the player position, 200 higher.
uint32_t function_486910(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t logic = arguments[1];
    uint32_t state = arguments[2];
    run.put(logic + 0x1c, 0x138b);
    run.put(state + 0x8, run.get(run.get(0x537e88) + 0x4c));
    run.put(state + 0xc, run.get(run.get(0x537e88) + 0x50) - 0xc8);
    return 0;
}

// 0x486a00. Shake: while the timer (+0x10) is below the frame delta, reseed it and
// jitter x and y by -6..6 with three rand calls; otherwise count the timer down.
uint32_t function_486a00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t state = arguments[2];
    uint32_t delta = run.get(0x5430c4);
    uint32_t timer = run.get(state + 0x10);
    if (delta <= timer) {
        run.put(state + 0x10, timer - delta);
        return 0;
    }
    uint32_t first = run.call(0x4a3050, 0);
    run.put(state + 0x10, uint32_t(s32(first) % 0x24));
    uint32_t second = run.call(0x4a3050, 0);
    uint32_t jitterX = uint32_t(s32(second) % 0xd) - 6;
    uint32_t third = run.call(0x4a3050, 0);
    uint32_t jitterY = uint32_t(s32(third) % 0xd) - 6;
    uint32_t x = run.get(state + 0x0);
    uint32_t y = run.get(state + 0x4);
    run.put(state + 0x0, x + jitterX);
    run.put(state + 0x4, y + jitterY);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x486620:
        return function_486620(run, receiver, arguments);
    case 0x486650:
        return function_486650(run, receiver, arguments);
    case 0x4868e0:
        return function_4868e0(run, receiver, arguments);
    case 0x486910:
        return function_486910(run, receiver, arguments);
    case 0x486a00:
        return function_486a00(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_scene_camera_helpers_entry, owned, body)
