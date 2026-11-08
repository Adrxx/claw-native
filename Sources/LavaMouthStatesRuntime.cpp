// Original LavaMouth runtime dispatch and states.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x457740:
    case 0x457b10:
        return 1;
    case 0x457cd0:
    case 0x457d60:
    case 0x457d80:
    case 0x457de0:
        return 0;
    default:
        return -1;
    }
}

// 0x457740. Global table bounds, base, fallback slot and entry stride.
uint32_t function_00457740(Run &run, uint32_t receiver, uint32_t state) {
    uint32_t lower = run.get(0x537a98);
    run.put(0x537ab0, 0);
    uint32_t slot;
    if ((s32(state) >= s32(lower) && s32(state) <= s32(run.get(0x537a9c))) ||
        run.call(0x4db6e0, 0x537a90, {state, 0}) != 0) {
        lower = run.get(0x537a98);
        slot = (state - lower) * run.get(0x537aa8) + run.get(0x537aa0);
    } else {
        uint32_t message = run.get(0x544b4c);
        uint32_t value = run.call(0x4db5f0, 0);
        uint32_t context = run.get(0x537a94);
        run.put(0x544b14, value);
        run.call(0x4db4d0, context, {0x537a90, message, 0xc});
        slot = run.get(0x537aa4);
        lower = run.get(0x537a98);
    }
    if (run.get(slot) != 0) {
        run.put(0x537ab0, 0);
        if ((s32(state) >= s32(lower) && s32(state) <= s32(run.get(0x537a9c))) ||
            run.call(0x4db6e0, 0x537a90, {state, 0}) != 0) {
            lower = run.get(0x537a98);
            slot = (state - lower) * run.get(0x537aa8) + run.get(0x537aa0);
        } else {
            uint32_t message = run.get(0x544b4c);
            uint32_t value = run.call(0x4db5f0, 0);
            uint32_t context = run.get(0x537a94);
            run.put(0x544b14, value);
            run.call(0x4db4d0, context, {0x537a90, message, 0xc});
            slot = run.get(0x537aa4);
        }
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x4a36f0, 0, {receiver});
    }
    return 0;
}

// 0x457cd0. +0x10 data, +0x24 previous command, +0x2c actor;
// +0x9c/+0xa0 idle timestamp and interval.
uint32_t function_00457cd0(Run &run, uint32_t receiver) {
    uint32_t data = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(data + 0x1c));
    uint32_t command = run.call(0x4dba00, 0x537668, {0x523604});
    data = run.get(receiver + 0x10);
    run.put(data + 0x1c, command);
    uint32_t actor = run.get(receiver + 0x2c);
    uint32_t frames = run.get(actor + 0x170);
    if (frames != 0) {
        uint32_t frame = 0;
        if (s32(run.get(frames + 0x64)) <= 1 && s32(run.get(frames + 0x68)) >= 1) {
            frame = run.get(run.get(frames + 0x14) + 0x4);
        }
        run.put(actor + 0x174, frame);
        run.put(actor + 0x16c, 1);
    }
    data = run.get(receiver + 0x10);
    run.put(receiver + 0xa0, run.get(data + 0xbc));
    run.put(receiver + 0x9c, run.get(0x537210));
    uint32_t playerData = run.get(run.get(0x537e88) + 0x6c);
    data = run.get(receiver + 0x10);
    uint32_t playerState = run.get(playerData + 0x14);
    run.put(data + 0x64, run.get(playerState + 0x80));
    return 0;
}

// 0x457d80. +0xac falling animation, +0x34 previous animation value.
uint32_t function_00457d80(Run &run, uint32_t receiver) {
    uint32_t delta = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {delta});
    uint32_t data = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(data + 0x1c));
    uint32_t command = run.call(0x4dba00, 0x537668, {0x5235f8});
    data = run.get(receiver + 0x10);
    run.put(data + 0x1c, command);
    uint32_t actor = run.get(receiver + 0x2c);
    uint32_t animation = run.get(receiver + 0xac);
    run.put(receiver + 0x34, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    return 0;
}

// 0x457d60. Unsigned elapsed-time comparison includes clock wrapping.
uint32_t function_00457d60(Run &run, uint32_t receiver) {
    uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x9c);
    if (elapsed >= run.get(receiver + 0xa0)) {
        function_00457d80(run, receiver);
    }
    return 0;
}

// 0x457de0. +0xc object, +0xa4/+0xa8 sound clock and interval,
// +0xb0/+0xb4 sound resources; rectangle records contain four words.
uint32_t function_00457de0(Run &run, uint32_t receiver) {
    uint32_t delta = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {delta});
    uint32_t index = run.get(run.get(receiver + 0x2c) + 0x16c) - 1;
    if (s32(index) >= 0 && s32(index) < 0x16) {
        uint32_t object = run.get(receiver + 0xc);
        uint32_t record = 0x50e570 + (index << 4);
        run.put(object + 0x138, run.get(record));
        run.put(object + 0x13c, run.get(record + 0x4));
        run.put(object + 0x140, run.get(record + 0x8));
        run.put(object + 0x144, run.get(record + 0xc));
    }
    uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0xa4);
    if (elapsed >= run.get(receiver + 0xa8)) {
        if (index == 1) {
            uint32_t sound = run.get(receiver + 0xb0);
            if (sound != 0) {
                uint32_t enabled = run.get(0x532c0c);
                uint32_t volume = run.get(0x532c10);
                if (enabled != 0) {
                    // Original 0x457e78/0x457ebe: ESI/EDI, four arguments, return word.
                    uint32_t savedStack = run.stackPointer;
                    run.stackPointer = run.automatic(-0x1c);
                    run.call(0x4b45f0, run.get(sound + 0x10), {volume, 0, 0, 0});
                    run.stackPointer = savedStack;
                }
            }
            run.put(receiver + 0xa8, 0xfa);
            run.put(receiver + 0xa4, run.get(0x537210));
        } else if (index == 0x12) {
            uint32_t sound = run.get(receiver + 0xb4);
            if (sound != 0) {
                uint32_t enabled = run.get(0x532c0c);
                uint32_t volume = run.get(0x532c10);
                if (enabled != 0) {
                    // Original 0x457e78/0x457ebe: ESI/EDI, four arguments, return word.
                    uint32_t savedStack = run.stackPointer;
                    run.stackPointer = run.automatic(-0x1c);
                    run.call(0x4b45f0, run.get(sound + 0x10), {volume, 0, 0, 0});
                    run.stackPointer = savedStack;
                }
            }
            run.put(receiver + 0xa8, 0xfa);
            run.put(receiver + 0xa4, run.get(0x537210));
        }
    }
    uint32_t playerData = run.get(run.get(0x537e88) + 0x6c);
    uint32_t data = run.get(receiver + 0x10);
    uint32_t playerState = run.get(playerData + 0x14);
    if (run.get(data + 0x64) != run.get(playerState + 0x80)) {
        function_00457cd0(run, receiver);
    }
    return 0;
}

// 0x457b10. +0x28 embedded base; +0x90..0x98 retained object/data.
uint32_t function_00457b10(Run &run, uint32_t receiver, uint32_t object) {
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x8, object);
    run.put(receiver + 0xc, object);
    uint32_t data = run.get(object + 0x6c);
    run.put(receiver + 0x10, data);
    run.put(receiver + 0x4, 0);
    run.call(0x4c7fa0, object, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0xc), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    uint32_t base = receiver + 0x28;
    run.call(0x408370, base, {object});
    run.put(base + 0x68, object);
    run.put(base + 0x6c, object);
    run.put(base + 0x70, run.get(object + 0x6c));
    run.put(receiver + 0x9c, 0);
    run.put(receiver + 0xa0, 0);
    run.put(receiver + 0xa4, 0);
    run.put(receiver + 0xa8, 0);
    run.put(receiver, 0x50e6d4);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x5286a4});
    uint32_t actor = run.get(receiver + 0x2c);
    run.put(actor + 0xd0, 4);
    uint32_t out = run.automatic(4);
    run.put(out, 0);
    actor = run.get(receiver + 0x2c);
    run.put(actor + 0xd4, 1);
    uint32_t resources = run.get(run.get(run.get(base + 0x4) + 0xc) + 0x2c) + 0x10;
    run.call(0x4f6286, resources, {0x52417c, out});
    uint32_t animation = run.get(out);
    if (animation == 0) {
        uint32_t fallback = run.automatic(-0x14);
        run.put(fallback, 0);
        resources = run.get(run.get(run.get(base + 0x4) + 0xc) + 0x2c) + 0x10;
        run.call(0x4f6286, resources, {0x5234b4, fallback});
        animation = run.get(fallback);
    }
    run.put(receiver + 0xac, animation);
    actor = run.get(receiver + 0x2c);
    run.put(out, 0);
    resources = run.get(run.get(actor + 0xc) + 0x28) + 0x10;
    run.call(0x4f6286, resources, {0x528690, out});
    run.put(receiver + 0xb0, run.get(out));
    actor = run.get(receiver + 0x2c);
    run.put(out, 0);
    resources = run.get(run.get(actor + 0xc) + 0x28) + 0x10;
    run.call(0x4f6286, resources, {0x52867c, out});
    uint32_t sound = run.get(out);
    object = run.get(receiver + 0xc);
    run.put(receiver + 0xb4, sound);
    run.put(object + 0x104, 0xa);
    object = run.get(receiver + 0xc);
    double scaled = double(run.gets(object + 0x104)) * double(run.getf(0x5262b0));
    uint32_t converted = run.call_x87(0x4a30e0, 0, scaled);
    run.put(object + 0x104, converted);
    function_00457cd0(run, receiver);
    return receiver;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x457740:
        return function_00457740(run, receiver, arguments[0]);
    case 0x457b10:
        return function_00457b10(run, receiver, arguments[0]);
    case 0x457cd0:
        return function_00457cd0(run, receiver);
    case 0x457d60:
        return function_00457d60(run, receiver);
    case 0x457d80:
        return function_00457d80(run, receiver);
    case 0x457de0:
        return function_00457de0(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_lava_mouth_states_entry, owned, body)
