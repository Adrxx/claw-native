// End-of-level elevator entries
//
// Recovered from the decompile and the disassembly of 0x49e060, 0x49e1c0 and
// 0x49e2a0.
#include "ClawRuntime.hpp"
#include <cstdint>
#include <climits>

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x49e060:
        return 2;
    case 0x49e1c0:
        return 3;
    case 0x49e2a0:
        return 1;
    default:
        return -1;
    }
}

// Signed 32-bit division with the faults of idiv.
uint32_t signedDivide(Run &run, uint32_t dividend, uint32_t divisor, uint32_t address) {
    int32_t a = s32(dividend);
    int32_t b = s32(divisor);
    if (b == 0)
        run.fail(CLAW_FAULT_HALT, address);
    if (b == -1 && a == INT32_MIN)
        run.fail(CLAW_FAULT_HALT, address);
    return uint32_t(a / b);
}

// Copies a 16-byte rectangle word by word.
void copyRect(Run &run, uint32_t source, uint32_t target) {
    uint32_t word = run.get(source);
    run.put(target, word);
    word = run.get(source + 0x4);
    run.put(target + 0x4, word);
    word = run.get(source + 0x8);
    run.put(target + 0x8, word);
    word = run.get(source + 0xc);
    run.put(target + 0xc, word);
}

// 0x49e060. cdecl, 2 stack argument(s), returns void.
// actor = param_1, state = param_2. State fields: +0xc8/+0xcc extents,
// +0x2c/+0x30 x range, +0x34/+0x38 y range, +0x3c/+0x40 spans,
// +0x44/+0x48 phase offsets, +0x4c/+0x50 periods. Actor fields: +0x4c/+0x50
// position, +0x110 direction, +0x148/+0x14c speeds, +0x158/+0x15c deltas.
uint32_t function_49e060(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t state = arguments[1];
    uint32_t extent = run.get(state + 0xc8);
    if (s32(extent) > 0) {
        uint32_t half = uint32_t(s32(extent) >> 1);
        uint32_t x = run.get(actor + 0x4c);
        run.put(state + 0x2c, x - half);
        x = run.get(actor + 0x4c);
        run.put(state + 0x30, half + x);
    }
    extent = run.get(state + 0xcc);
    if (s32(extent) > 0) {
        uint32_t half = uint32_t(s32(extent) >> 1);
        uint32_t y = run.get(actor + 0x50);
        run.put(state + 0x34, y - half);
        y = run.get(actor + 0x50);
        run.put(state + 0x38, half + y);
    }
    uint32_t right = run.get(state + 0x30);
    uint32_t left = run.get(state + 0x2c);
    uint32_t top = run.get(state + 0x34);
    uint32_t width = right - left + 1;
    uint32_t bottom = run.get(state + 0x38);
    uint32_t height = bottom - top + 1;
    run.put(state + 0x3c, width);
    run.put(state + 0x40, height);
    if (s32(width) < 2)
        run.put(state + 0x3c, 0);
    if (s32(height) < 2)
        run.put(state + 0x40, 0);
    width = run.get(state + 0x3c);
    height = run.get(state + 0x40);
    run.put(state + 0x4c, width << 1);
    run.put(state + 0x50, height << 1);
    if (run.get(actor + 0x148) == 0)
        run.put(actor + 0x148, 0x7d);
    if (run.get(actor + 0x14c) == 0)
        run.put(actor + 0x14c, 0x7d);
    run.put(actor + 0x158, 0);
    run.put(actor + 0x15c, 0);
    uint32_t dx = run.get(actor + 0x4c) - run.get(state + 0x2c);
    uint32_t dy = run.get(actor + 0x50) - run.get(state + 0x34);
    run.put(state + 0x44, dx);
    run.put(state + 0x48, dy);
    if (s32(dx) < 0)
        run.put(state + 0x44, 0);
    uint32_t spanX = run.get(state + 0x3c);
    uint32_t phaseX = run.get(state + 0x44);
    if (s32(phaseX) > s32(spanX))
        run.put(state + 0x44, spanX);
    if (s32(run.get(state + 0x48)) < 0)
        run.put(state + 0x48, 0);
    uint32_t spanY = run.get(state + 0x40);
    uint32_t phaseY = run.get(state + 0x48);
    if (s32(phaseY) > s32(spanY))
        run.put(state + 0x48, spanY);
    uint32_t direction = run.get(actor + 0x110);
    if (direction == 7 || direction == 4 || direction == 1)
        run.put(state + 0x44, run.get(state + 0x44) + spanX);
    direction = run.get(actor + 0x110);
    if (direction == 7 || direction == 8 || direction == 9)
        run.put(state + 0x48, run.get(state + 0x48) + spanY);
    uint32_t scaledX = run.get(state + 0x44) * 1000;
    run.put(state + 0x44, signedDivide(run, scaledX, run.get(actor + 0x148), 0x49e192));
    uint32_t scaledY = run.get(state + 0x48) * 1000;
    run.put(state + 0x48, signedDivide(run, scaledY, run.get(actor + 0x14c), 0x49e1ab));
    return 0;
}

// Quotient remainder of 0x4a4630 as the caller sees it in EDX: the idiv
// remainder, moved into the divisor's sign when the dividend is negative.
uint32_t floorRemainder(uint32_t dividend, uint32_t divisor) {
    int32_t a = s32(dividend);
    int32_t b = s32(divisor);
    int32_t remainder = a % b;
    if (a < 0 && remainder > 0)
        remainder -= b;
    return uint32_t(remainder);
}

// 0x49e1c0. cdecl, 3 stack argument(s), returns void.
// Moves the actor along both axes by the position implied by the tick.
uint32_t function_49e1c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t state = arguments[1];
    uint32_t tick = arguments[2];
    uint32_t speed = run.get(actor + 0x148);
    if (s32(speed) > 0) {
        uint32_t period = run.get(state + 0x4c);
        if (s32(period) > 0) {
            uint32_t phase = run.get(state + 0x44);
            uint32_t old = run.get(actor + 0x4c);
            uint32_t product = (phase + tick) * speed;
            uint32_t scaled = product / 1000;
            run.call(0x4a4630, 0, {scaled, period});
            uint32_t remainder = floorRemainder(scaled, period);
            uint32_t span = run.get(state + 0x3c);
            if (s32(remainder) > s32(span)) {
                uint32_t high = run.get(state + 0x30);
                run.put(actor + 0x4c, high - remainder + span);
            } else {
                uint32_t low = run.get(state + 0x2c);
                run.put(actor + 0x4c, low + remainder);
            }
            uint32_t now = run.get(actor + 0x4c);
            run.put(actor + 0x158, now - old);
        }
    }
    uint32_t speedY = run.get(actor + 0x14c);
    if (s32(speedY) > 0) {
        uint32_t period = run.get(state + 0x50);
        if (s32(period) > 0) {
            uint32_t phase = run.get(state + 0x48);
            uint32_t product = (phase + tick) * speedY;
            uint32_t old = run.get(actor + 0x50);
            uint32_t scaled = product / 1000;
            run.call(0x4a4630, 0, {scaled, period});
            uint32_t remainder = floorRemainder(scaled, period);
            uint32_t span = run.get(state + 0x40);
            uint32_t now;
            if (s32(remainder) > s32(span)) {
                uint32_t high = run.get(state + 0x38);
                now = high - remainder + span;
            } else {
                uint32_t low = run.get(state + 0x34);
                now = low + remainder;
            }
            run.put(actor + 0x50, now);
            run.put(actor + 0x15c, now - old);
        }
    }
    return 0;
}

// 0x49e2a0. cdecl, 1 stack argument(s), returns u32.
// actor = param_1; actor+0x6c is the elevator state, whose +0x1c is the phase.
uint32_t function_49e2a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t state = run.get(actor + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase == 1) {
        uint32_t tick = run.get(0x537210);
        const uint32_t stepArguments[3] = {actor, state, tick};
        function_49e1c0(run, 0, stepArguments);
        return 1;
    }
    if (phase != 0)
        return 1;
    const uint32_t setupArguments[2] = {actor, state};
    function_49e060(run, 0, setupArguments);
    uint32_t flags = run.get(actor + 0x8);
    uint32_t image = run.get(actor + 0x174);
    flags |= 1;
    run.put(actor + 0xd0, 0x80);
    run.put(actor + 0x8, flags);
    if (image != 0) {
        uint32_t right = run.get(image + 0x20);
        uint32_t left = run.get(image + 0x18);
        run.put(actor + 0x118, right - left);
        uint32_t bottom = run.get(image + 0x24);
        run.put(actor + 0x11c, bottom - run.get(image + 0x1c));
        left = run.get(image + 0x18);
        right = run.get(image + 0x20);
        run.put(actor + 0x120, left + right - 1);
        bottom = run.get(image + 0x24);
        uint32_t top = run.get(image + 0x1c);
        run.put(actor + 0x124, bottom + top - 1);
    }
    uint32_t rectangle = actor + 0x128;
    copyRect(run, run.get(0x537960) + 0x68, rectangle);
    uint32_t level = run.get(run.get(0x5371fc) + 0x2c);
    if (run.get(level + 0x14) == 10) {
        uint32_t scene = run.get(actor + 0xc);
        uint32_t original = run.get(actor + 0x170);
        uint32_t found = run.automatic(0x4);
        run.put(found, 0);
        uint32_t registry = run.get(scene + 0x10);
        run.call(0x4f6286, registry + 0x10, {0x528a4c, found});
        if (original == run.get(found))
            copyRect(run, run.get(0x537960) + 0x98, rectangle);
    }
    if (run.get(state + 0x10) == 0x49e810)
        copyRect(run, run.get(0x537960) + 0x88, rectangle);
    uint32_t scene = run.get(actor + 0xc);
    uint32_t original = run.get(actor + 0x170);
    uint32_t found = run.automatic(0x4);
    run.put(found, 0);
    uint32_t registry = run.get(scene + 0x10);
    run.call(0x4f6286, registry + 0x10, {0x52dd68, found});
    if (original == run.get(found))
        copyRect(run, run.get(0x537960) + 0x88, rectangle);
    uint32_t bottomEdge = run.get(actor + 0x134) + 0x20;
    uint32_t life = run.get(actor + 0x64);
    run.put(actor + 0x134, bottomEdge);
    if (life == 0) {
        uint32_t current = run.get(actor + 0x8);
        run.put(actor + 0x64, 0x7d0);
        run.put(actor + 0x8, current | 0x20000);
    }
    run.put(state + 0x1c, 1);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49e060:
        return function_49e060(run, receiver, arguments);
    case 0x49e1c0:
        return function_49e1c0(run, receiver, arguments);
    case 0x49e2a0:
        return function_49e2a0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_end_of_level_elevator_entry, owned, body)
