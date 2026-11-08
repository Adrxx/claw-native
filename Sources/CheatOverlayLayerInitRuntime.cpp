// Debug overlay layer initializer 0x4d0800 (MPLITH/MPLOGO/MPMONOLITH/NOLITH)
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
    case 0x4d0800:
        return 8;
    default:
        return -1;
    }
}

// Signed division by two, truncating toward zero (cdq, sub, sar).
uint32_t halve(uint32_t value) {
    return uint32_t(s32(value) / 2);
}

// Recomputes the +0x70 width, +0x74 height and their halves from the
// rectangle at +0x50..+0x5c.
void sizeFromRect(Run &run, uint32_t layer) {
    uint32_t width = run.get(layer + 0x58) - run.get(layer + 0x50) + 1;
    uint32_t height = run.get(layer + 0x5c) - run.get(layer + 0x54) + 1;
    run.put(layer + 0x70, width);
    run.put(layer + 0x74, height);
    run.put(layer + 0x78, halve(width));
    run.put(layer + 0x7c, halve(height));
}

// 0x4d0800. thiscall, 8 stack arguments: width, height, tile width, tile
// height, scale x, scale y, rectangle pointer, name pointer. Returns 1.
uint32_t function_4d0800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t layer = receiver;
    uint32_t width = arguments[0];
    uint32_t height = arguments[1];
    uint32_t tileWidth = arguments[2];
    uint32_t tileHeight = arguments[3];
    uint32_t scaleX = arguments[4];
    uint32_t scaleY = arguments[5];
    uint32_t rect = arguments[6];
    uint32_t name = arguments[7];
    run.put(layer + 0x28, width);
    run.put(layer + 0x2c, height);
    run.put(layer + 0x38, tileWidth);
    run.put(layer + 0x3c, tileHeight);
    run.put(layer + 0x50, run.get(rect + 0x0));
    run.put(layer + 0x54, run.get(rect + 0x4));
    run.put(layer + 0x58, run.get(rect + 0x8));
    run.put(layer + 0x5c, run.get(rect + 0xc));
    run.put(layer + 0x94, scaleX);
    run.put(layer + 0x98, scaleY);
    run.put(layer + 0x60, 0);
    run.put(layer + 0x64, 0);
    run.put(layer + 0x6c, tileHeight);
    run.put(layer + 0x30, tileWidth * width);
    run.put(layer + 0x34, tileHeight * height);
    run.put(layer + 0x68, tileWidth);
    sizeFromRect(run, layer);
    // Base-two logarithm of the tile width, stored twice.
    run.put(layer + 0x8c, 0);
    uint32_t log = 0;
    for (uint32_t value = tileWidth; s32(value) > 1; value = uint32_t(s32(value) >> 1)) {
        ++log;
        run.put(layer + 0x8c, log);
    }
    run.put(layer + 0x90, 0);
    log = 0;
    for (uint32_t value = tileWidth; s32(value) > 1; value = uint32_t(s32(value) >> 1)) {
        ++log;
        run.put(layer + 0x90, log);
    }
    if (name != 0) {
        uint32_t count = 0;
        while (run.get8(name + count) != 0)
            ++count;
        ++count;
        uint32_t destination = layer + 0xb4;
        uint32_t offset = 0;
        for (uint32_t words = count >> 2; words != 0; --words) {
            run.put(destination + offset, run.get(name + offset));
            offset += 4;
        }
        for (uint32_t rest = count & 3; rest != 0; --rest) {
            run.put8(destination + offset, run.get8(name + offset));
            ++offset;
        }
    }
    if (run.get(rect) != 0x80000000u) {
        uint32_t copy = run.automatic(-0x10);
        run.icall(0x546d58, {copy, rect});
        run.put(layer + 0x50, run.get(copy + 0x0));
        run.put(layer + 0x54, run.get(copy + 0x4));
        run.put(layer + 0x58, run.get(copy + 0x8));
        run.put(layer + 0x5c, run.get(copy + 0xc));
        sizeFromRect(run, layer);
        run.call(0x4d0a60, layer);
    }
    double factor = double(run.getf(0x513d70));
    run.putf(layer + 0x18, float(double(s32(run.get(layer + 0x94))) * factor));
    run.putf(layer + 0x1c, float(double(s32(run.get(layer + 0x98))) * factor));
    uint32_t cells = run.get(layer + 0x28) * run.get(layer + 0x2c);
    run.put(layer + 0x20, run.call(0x4f63ec, 0, {cells << 2}));
    run.put(layer + 0x24, run.call(0x4f63ec, 0, {run.get(layer + 0x2c) << 2}));
    uint32_t row = 0;
    if (s32(run.get(layer + 0x2c)) > 0) {
        do {
            uint32_t rowStart = row * run.get(layer + 0x28);
            run.put(run.get(layer + 0x24) + row * 4, rowStart);
            ++row;
        } while (s32(row) < s32(run.get(layer + 0x2c)));
    }
    run.put(layer + 0x10, 0);
    run.put(layer + 0x14, 0);
    run.call(0x4d0a60, layer);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4d0800:
        return function_4d0800(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_cheat_overlay_layer_init_entry, owned, body)
