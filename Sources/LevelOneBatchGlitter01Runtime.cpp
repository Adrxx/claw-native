// Level 1 glitter mother and baby logic
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
    case 0x448440:
        return 1;
    case 0x4485a0:
        return 1;
    default:
        return -1;
    }
}

// Picks a random value in [low, high] the way 0x448440 does: when the span
// (high - low + 1) is zero the low bit of rand chooses an end, otherwise a
// signed remainder is added to low.
uint32_t randomInRange(Run &run, uint32_t low, uint32_t high) {
    uint32_t span = high - low + 1;
    if (span == 0) {
        uint32_t value = run.call(0x4a3050, 0, {});
        if ((value & 1) != 0)
            return low;
        return high;
    }
    int32_t value = s32(run.call(0x4a3050, 0, {}));
    int32_t divisor = s32(span);
    int32_t remainder = 0;
    if (divisor != -1)
        remainder = value % divisor;
    return uint32_t(remainder) + low;
}

// 0x448440. cdecl, 1 stack argument(s), returns void (EAX is always 1).
// Object fields: +0x08 and +0x40 flags, +0x0c owner, +0x6c state block.
// State block: +0x1c state, +0x20 next state, +0x170 parent object.
// Parent fields: +0x4c/+0x50 origin x/y, +0x64 height, +0x118/+0x120 x range,
// +0x11c/+0x124 y range.
uint32_t function_448440(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t block = run.get(object + 0x6c);
    uint32_t state = run.get(block + 0x1c);
    if (state == 0) {
        uint32_t parent = run.get(block + 0x170);
        if (parent == 0)
            return 1;
        run.put(block + 0x1c, 10);
        uint32_t flags = run.get(object + 0x08);
        uint32_t other = run.get(object + 0x40);
        run.put(object + 0x08, flags | 1);
        run.put(object + 0x40, other | 1);
        return 1;
    }
    if (state != 10)
        return 1;
    uint32_t count = 2;
    uint32_t global = run.get(0x5371fc);
    if (run.get(global + 0x124) == 0)
        count = 1;
    while (s32(count) > 0) {
        uint32_t parent = run.get(block + 0x170);
        uint32_t xHigh = run.get(parent + 0x120);
        uint32_t xOrigin = run.get(parent + 0x4c);
        uint32_t xLow = run.get(parent + 0x118);
        uint32_t x = randomInRange(run, xLow, xHigh);
        parent = run.get(block + 0x170);
        x = x + xOrigin;
        uint32_t yHigh = run.get(parent + 0x124);
        uint32_t yLow = run.get(parent + 0x11c);
        uint32_t yOrigin = run.get(parent + 0x50);
        uint32_t y = randomInRange(run, yLow, yHigh);
        parent = run.get(block + 0x170);
        uint32_t height = run.get(parent + 0x64) + 1;
        y = y + yOrigin;
        uint32_t receiverObject = run.get(run.get(object + 0x0c) + 0x08);
        run.call(0x4c8da0, receiverObject, {1, x, y, height, 0x522594, 0x240020});
        count = count - 1;
    }
    run.put(block + 0x20, 0x0f);
    return 1;
}

// 0x4485a0. cdecl, 1 stack argument(s), returns void (EAX is always 1).
// Object fields: +0x08 flags, +0x6c state block (+0x1c state), +0x188 timer
// sub-object (+0x14 and +0x1c checked after update).
uint32_t function_4485a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t block = run.get(object + 0x6c);
    uint32_t state = run.get(block + 0x1c);
    if (state == 0) {
        uint32_t flags = run.get(object + 0x08);
        run.put(object + 0x08, flags | 0x21);
        run.call(0x4c7970, object, {0x527a50});
        run.call(0x4c79e0, object, {0x527a40, 0});
        run.put(block + 0x1c, 5);
        return 1;
    }
    if (state != 5)
        return 1;
    uint32_t sub = object + 0x188;
    uint32_t argument = run.get(0x5430c4);
    run.call(0x4c82a0, sub, {argument});
    if (run.get(sub + 0x1c) == 0)
        return 1;
    if (run.get(sub + 0x14) != 0)
        return 1;
    uint32_t flags = run.get(object + 0x08);
    run.put(object + 0x08, flags | 0x10000);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x448440:
        return function_448440(run, receiver, arguments);
    case 0x4485a0:
        return function_4485a0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_glitter_01_entry, owned, body)
