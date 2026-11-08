// Original single-player cheat display steps and previous-level search.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x42a260:
    case 0x42a350:
    case 0x429cb0:
        return 0;
    case 0x4bce30:
        return 3;
    case 0x4bce80:
    case 0x4bcf00:
        return 4;
    default:
        return -1;
    }
}

// 0x4bce30. Display owner +0x3f8 is the signed mode count; +0x3f4
// points to descriptors with height +0x08, width +0x0c and depth +0x54.
uint32_t findMode(Run &run, uint32_t receiver, uint32_t width, uint32_t height, uint32_t depth) {
    uint32_t count = run.get(receiver + 0x3f8);
    if (s32(count) <= 0)
        return 0xffffffffu;
    uint32_t cursor = run.get(receiver + 0x3f4);
    for (uint32_t index = 0; s32(index) < s32(count); ++index) {
        uint32_t mode = run.get(cursor);
        if (run.get(mode + 0x0c) == width && run.get(mode + 0x08) == height && run.get(mode + 0x54) == depth)
            return index;
        cursor += 4;
    }
    return 0xffffffffu;
}

// 0x4bce80. Publish the next same-depth mode, or a pair of -1 values.
uint32_t nextMode(Run &run, uint32_t receiver, uint32_t output, uint32_t width, uint32_t height, uint32_t depth) {
    uint32_t index = findMode(run, receiver, width, height, depth);
    if (index != 0xffffffffu) {
        uint32_t count = run.get(receiver + 0x3f8);
        if (s32(index) < s32(count)) {
            ++index;
            if (s32(index) < s32(count)) {
                uint32_t cursor = run.get(receiver + 0x3f4) + index * 4;
                do {
                    uint32_t mode = run.get(cursor);
                    if (run.get(mode + 0x54) == depth) {
                        uint32_t resultWidth = run.get(mode + 0x0c);
                        uint32_t resultHeight = run.get(mode + 0x08);
                        run.put(output, resultWidth);
                        run.put(output + 0x04, resultHeight);
                        return output;
                    }
                    ++index;
                    cursor += 4;
                } while (s32(index) < s32(count));
            }
        }
    }
    run.put(output, 0xffffffffu);
    run.put(output + 0x04, 0xffffffffu);
    return output;
}

// 0x4bcf00. Publish the previous same-depth mode.
uint32_t previousMode(Run &run, uint32_t receiver, uint32_t output, uint32_t width, uint32_t height, uint32_t depth) {
    uint32_t index = findMode(run, receiver, width, height, depth);
    if (index != 0xffffffffu && s32(index) < s32(run.get(receiver + 0x3f8))) {
        --index;
        if (s32(index) >= 0) {
            uint32_t cursor = run.get(receiver + 0x3f4) + index * 4;
            do {
                uint32_t mode = run.get(cursor);
                if (run.get(mode + 0x54) == depth) {
                    uint32_t resultWidth = run.get(mode + 0x0c);
                    uint32_t resultHeight = run.get(mode + 0x08);
                    run.put(output, resultWidth);
                    run.put(output + 0x04, resultHeight);
                    return output;
                }
                --index;
                cursor -= 4;
            } while (s32(index) >= 0);
        }
    }
    run.put(output, 0xffffffffu);
    run.put(output + 0x04, 0xffffffffu);
    return output;
}

void refreshDisplay(Run &run, uint32_t receiver) {
    run.stackPointer = run.frame - 0x18;
    // Command owner +0x30 holds display services; +0x04 selects surfaces.
    uint32_t surfaces = run.get(run.get(receiver + 0x30) + 0x04);
    uint32_t primary = run.get(surfaces + 0x14);
    run.call(0x4b97c0, run.get(primary + 0x2c), {0});
    uint32_t secondary = run.get(surfaces + 0x10);
    run.call(0x4b98b0, run.get(secondary + 0x2c), {0});
    surfaces = run.get(run.get(receiver + 0x30) + 0x04);
    primary = run.get(surfaces + 0x14);
    run.call(0x4b97c0, run.get(primary + 0x2c), {0});
    secondary = run.get(surfaces + 0x10);
    run.call(0x4b98b0, run.get(secondary + 0x2c), {0});
    run.call(0x429eb0, receiver, {0});
}

// 0x42a260. Owner +0x2c is game state; +0x78 depth, +0x7c width,
// +0x80 height. The output pair occupies the original eight stack bytes.
uint32_t increaseVideo(Run &run, uint32_t receiver) {
    if (run.vcall(run.get(receiver + 0x2c), 0x10) != 3)
        return 1;
    uint32_t depth = run.get(receiver + 0x78);
    uint32_t height = run.get(receiver + 0x80);
    uint32_t width = run.get(receiver + 0x7c);
    uint32_t display = run.get(run.get(receiver + 0x30) + 0x1c);
    uint32_t output = nextMode(run, display, run.automatic(-8), width, height, depth);
    width = run.get(output);
    height = run.get(output + 0x04);
    if (s32(width) > 0x514)
        return 1;
    if (width != 0xffffffffu && height != 0xffffffffu) {
        run.stackPointer = run.frame - 0x1c;
        if (!run.call(0x42a060, receiver, {width, height})) {
            if (!run.call(0x42a060, receiver, {0x280, 0x1e0})) {
                run.call(0x429e10, receiver, {0x8008, 0x404});
                return 0;
            }
        }
    }
    refreshDisplay(run, receiver);
    return 1;
}

// 0x42a350. Decrease accepts game states 3 and 4 and minimum 320x200.
uint32_t decreaseVideo(Run &run, uint32_t receiver) {
    if (run.vcall(run.get(receiver + 0x2c), 0x10) != 3) {
        if (run.vcall(run.get(receiver + 0x2c), 0x10) != 4)
            return 1;
    }
    uint32_t depth = run.get(receiver + 0x78);
    uint32_t height = run.get(receiver + 0x80);
    uint32_t width = run.get(receiver + 0x7c);
    uint32_t display = run.get(run.get(receiver + 0x30) + 0x1c);
    uint32_t output = previousMode(run, display, run.automatic(-8), width, height, depth);
    width = run.get(output);
    height = run.get(output + 0x04);
    if (width != 0xffffffffu && height != 0xffffffffu && s32(width) >= 0x140 && s32(height) >= 0xc8) {
        run.stackPointer = run.frame - 0x1c;
        if (!run.call(0x42a060, receiver, {width, height})) {
            if (!run.call(0x42a060, receiver, {0x280, 0x1e0})) {
                run.call(0x429e10, receiver, {0x8008, 0x405});
                return 0;
            }
        }
    }
    refreshDisplay(run, receiver);
    return 1;
}

// 0x429cb0. Try at most twenty prior levels, wrapping nonpositive to 20.
uint32_t mulder(Run &run, uint32_t receiver) {
    if (run.vcall(run.get(receiver + 0x2c), 0x10) != 3)
        return 0;
    run.stackPointer = run.frame - 0x18;
    // +0xc0 is the command owner's retained level-name CString.
    run.call(0x4f650f, receiver + 0xc0);
    uint32_t state = run.get(receiver + 0x2c);
    uint32_t remaining = 0x13;
    uint32_t level = run.get(state + 0x14) - 1;
    for (;;) {
        if (s32(level) <= 0)
            level = 0x14;
        uint32_t table = run.get(state);
        run.stackPointer = run.frame - 0x18;
        uint32_t kind = run.call(run.get(table + 0x10), state);
        run.stackPointer = run.frame - 0x1c;
        run.call(run.get(table + 0x28), state, {kind});
        run.stackPointer = run.frame - 0x20;
        if (run.call(0x46aeb0, state, {level, 1})) {
            table = run.get(state);
            run.stackPointer = run.frame - 0x18;
            kind = run.call(run.get(table + 0x10), state);
            run.stackPointer = run.frame - 0x1c;
            run.call(run.get(table + 0x24), state, {kind});
            return 1;
        }
        --level;
        uint32_t before = remaining;
        --remaining;
        if (s32(before) <= 0)
            break;
    }
    run.stackPointer = run.frame - 0x20;
    run.call(0x429e10, receiver, {0x8007, 0x402});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42a260:
        return increaseVideo(run, receiver);
    case 0x42a350:
        return decreaseVideo(run, receiver);
    case 0x4bce30:
        return findMode(run, receiver, arguments[0], arguments[1], arguments[2]);
    case 0x4bce80:
        return nextMode(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3]);
    case 0x4bcf00:
        return previousMode(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3]);
    case 0x429cb0:
        return mulder(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_cheat_video_mulder_entry, owned, body)
