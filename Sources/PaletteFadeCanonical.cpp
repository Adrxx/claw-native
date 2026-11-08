// Original palette fade and clock bodies.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4bb8c0:
        return 1;
    case 0x4bbb70:
    case 0x4bbd20:
        return 0;
    case 0x4bbd90:
        return 4;
    default:
        return -1;
    }
}

// Fields: +0x04 palette interface, +0x0c current buffer, +0x10 saved buffer,
// +0x14 target buffer, +0x18 fade source, +0x1c packed target RGB,
// +0x20 duration, +0x24 start tick, +0x28 previous elapsed,
// +0x2c first index, +0x30 count, +0x34 active flag.

// 0x4bb8c0 Palette::restoreSaved.
uint32_t restoreSaved(Run &run, uint32_t receiver) {
    uint32_t saved = run.get(receiver + 0x10);
    if (!saved)
        return 0;
    for (uint32_t offset = 0; offset < 0x400; offset += 4) {
        uint32_t destination = run.get(receiver + 0x0c);
        uint32_t value = run.get(saved + offset);
        run.put(destination + offset, value);
    }
    uint32_t holder = run.get(0x541374);
    if (holder) {
        uint32_t display = run.get(holder);
        uint32_t method = run.get(run.get(display) + 0x58);
        run.call(method, 0, {display, 1, 0});
    }
    uint32_t palette = run.get(receiver + 0x04);
    uint32_t method = run.get(run.get(palette) + 0x18);
    run.call(method, 0, {palette, 0, 0, 0x100, saved});
    return 0;
}

// 0x4bbd20 Palette::finishFade.
uint32_t finishFade(Run &run, uint32_t receiver) {
    if (!run.get(receiver + 0x34))
        return 0;
    uint32_t target = run.get(receiver + 0x14);
    run.put(receiver + 0x34, 0);
    if (target) {
        uint32_t start = run.get(receiver + 0x2c);
        uint32_t count = run.get(receiver + 0x30);
        run.call(0x4bb800, receiver, {start, count, target, 0});
        run.put(receiver + 0x14, 0);
    } else {
        uint32_t color = run.get(receiver + 0x1c);
        uint32_t count = run.get(receiver + 0x30);
        uint32_t start = run.get(receiver + 0x2c);
        run.call(0x4bb910, receiver, {start, count, color, color >> 8, color >> 16, 0});
    }
    return 0;
}

uint32_t interpolate(uint32_t source, uint32_t target, uint32_t elapsed, uint32_t duration) {
    uint32_t numerator = (target - source) * elapsed;
    // Widen signed division to avoid C++ overflow for the IDIV overflow pair.
    return uint32_t(int64_t(s32(numerator)) / int64_t(s32(duration)));
}

// 0x4bbb70 Palette::advanceFade.
uint32_t advanceFade(Run &run, uint32_t receiver) {
    if (!run.get(receiver + 0x34))
        return 0;
    uint32_t clock = run.icall(0x546df0, {});
    uint32_t elapsed = clock - run.get(receiver + 0x24);
    if (elapsed >= run.get(receiver + 0x20)) {
        finishFade(run, receiver);
        return 0;
    }
    bool paletteTarget = run.get(receiver + 0x14) != 0;
    if (elapsed != run.get(receiver + 0x28)) {
        uint32_t index = run.get(receiver + 0x2c);
        uint32_t end = index + run.get(receiver + 0x30);
        while (s32(index) < s32(end)) {
            for (uint32_t channel = 0; channel < 3; ++channel) {
                uint32_t sourceAddress = run.get(receiver + 0x18) + index * 4 + channel;
                uint32_t targetAddress = paletteTarget ? run.get(receiver + 0x14) + index * 4 + channel : receiver + 0x1c + channel;
                uint32_t source = run.get8(sourceAddress);
                uint32_t target = run.get8(targetAddress);
                uint32_t value = interpolate(source, target, elapsed, run.get(receiver + 0x20)) + source;
                uint32_t destination = run.get(receiver + 0x0c);
                run.put8(destination + index * 4 + channel, value);
            }
            end = run.get(receiver + 0x2c) + run.get(receiver + 0x30);
            ++index;
        }
        uint32_t start = run.get(receiver + 0x2c);
        uint32_t buffer = run.get(receiver + 0x0c) + start * 4;
        uint32_t palette = run.get(receiver + 0x04);
        uint32_t method = run.get(run.get(palette) + 0x18);
        uint32_t count = run.get(receiver + 0x30);
        run.call(method, 0, {palette, 0, start, count, buffer});
    }
    run.put(receiver + 0x28, elapsed);
    return 1;
}

// 0x4bbd90 Palette::fadeBlocking.
uint32_t fadeBlocking(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t start = arguments[0];
    uint32_t count = arguments[1];
    uint32_t target = arguments[2];
    uint32_t duration = arguments[3];
    uint32_t buffer = run.get(receiver + 0x0c);
    uint32_t palette = run.get(receiver + 0x04);
    uint32_t method = run.get(run.get(palette) + 0x10);
    uint32_t error = run.call(method, 0, {palette, 0, 0, 0x100, buffer});
    if (error)
        run.call(0x4bd260, 0, {0x532500, 0x41b, error});
    uint32_t snapshot = run.call(0x4f63ec, 0, {0x400});
    for (uint32_t offset = 0; offset < 0x400; offset += 4) {
        uint32_t source = run.get(receiver + 0x0c);
        uint32_t value = run.get(source + offset);
        run.put(snapshot + offset, value);
    }
    uint32_t baseline = run.icall(0x546df0, {});
    uint32_t elapsed = 10;
    uint32_t previous = 9;
    while (elapsed < duration) {
        if (elapsed != previous) {
            uint32_t end = start + count;
            if (s32(start) < s32(end)) {
                uint32_t remaining = end - start;
                uint32_t offset = start * 4;
                do {
                    for (uint32_t channel = 0; channel < 3; ++channel) {
                        uint32_t source = run.get8(snapshot + offset + channel);
                        uint32_t targetByte = run.get8(target + offset + channel);
                        uint32_t value = interpolate(source, targetByte, elapsed, duration);
                        value += run.get8(snapshot + offset + channel);
                        uint32_t destination = run.get(receiver + 0x0c);
                        run.put8(destination + offset + channel, value);
                    }
                    offset += 4;
                    --remaining;
                } while (remaining);
            }
            palette = run.get(receiver + 0x04);
            buffer = run.get(receiver + 0x0c) + start * 4;
            method = run.get(run.get(palette) + 0x18);
            run.call(method, 0, {palette, 0, start, count, buffer});
        }
        previous = elapsed;
        elapsed = run.icall(0x546df0, {}) - baseline;
    }
    run.call(0x4bb800, receiver, {start, count, target, 0});
    run.call(0x4f6428, 0, {snapshot});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4bb8c0:
        return restoreSaved(run, receiver);
    case 0x4bbb70:
        return advanceFade(run, receiver);
    case 0x4bbd20:
        return finishFade(run, receiver);
    case 0x4bbd90:
        return fadeBlocking(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_palette_fade_canonical_entry, owned, body)
