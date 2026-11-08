#include "ClawRuntime.hpp"

namespace {
int rawImageArguments(uint32_t function) {
    return function == 0x4d32e0 ? 2 : -1;
}

// 0x4d32e0: the unconditional unflipped compressed helper. Projection remains
// the existing 0x4c96d0 dependency; this entry does not repeat dispatcher flags.
uint32_t rawImageEntry(claw::Run &run, uint32_t, uint32_t image, const uint32_t *args) {
    const uint32_t actor = args[0];
    const uint32_t target = args[1];
    const uint32_t xLocal = run.automatic(4); // Original reuses the incoming actor slot.
    const uint32_t yLocal = run.automatic(-0x50);
    const uint32_t destination = run.automatic(-0x40);
    const uint32_t worldSource = run.automatic(-0x30);
    const uint32_t worldClip = run.automatic(-0x20);
    const uint32_t source = run.automatic(-0x10);

    // Actor displacement/position and image offsets/half extents are captured
    // before projection. Image dimensions and the actor flag are read after it.
    uint32_t x = run.get(actor + 0x10) + run.get(actor + 0x4c) + run.get(image + 0x20) - run.get(image + 0x18);
    uint32_t y = run.get(actor + 0x14) + run.get(actor + 0x50) + run.get(image + 0x24) - run.get(image + 0x1c);
    const uint32_t flags = run.get(actor + 8);
    run.put(run.automatic(-0x44), image);
    run.put(xLocal, x);
    run.put(yLocal, y);
    // Canonical arguments are values; also materialize the incoming target slot
    // that the original reloads after its callbacks.
    run.put(run.automatic(8), target);
    if (flags & 0x40000) {
        const uint32_t holder = run.get(actor + 0x3c);
        const uint32_t plane = run.get(holder + 0x5c);
        run.stackPointer = run.automatic(-0x6c);
        run.call(0x4c96d0, plane, {xLocal, yLocal});
        x = run.get(xLocal);
        y = run.get(yLocal);
    }
    const uint32_t right = x + run.get(image + 0x10) - 1;
    const bool world = (run.get8(actor + 0xa) & 4) != 0;
    const uint32_t bottom = y + run.get(image + 0x14) - 1;
    run.put(run.automatic(-0x4c), right);
    run.put(destination + 8, right);
    run.put(run.automatic(-0x48), bottom);
    run.put(destination, x);
    run.put(destination + 4, y);
    run.put(destination + 12, bottom);

    if (world) {
        const uint32_t parent = run.get(image + 0xc);
        const uint32_t clip = run.get(parent + 0x24) + 0x10;
        for (uint32_t offset = 0; offset != 16; offset += 4)
            run.put(worldSource + offset, run.get(clip + offset));
        run.stackPointer = run.automatic(-0x6c);
        run.icall(0x546d58, {worldClip, worldSource});
        x = run.get(xLocal);
        y = run.get(yLocal);
        if (claw::s32(x) < run.gets(worldClip))
            run.put(destination, run.get(destination) + run.get(worldClip) - x);
        if (claw::s32(run.get(run.automatic(-0x4c))) > run.gets(worldClip + 8))
            run.put(destination + 8, run.get(destination + 8) + run.get(worldClip + 8) - run.get(run.automatic(-0x4c)));
        if (claw::s32(y) < run.gets(worldClip + 4))
            run.put(destination + 4, run.get(destination + 4) + run.get(worldClip + 4) - y);
        if (claw::s32(bottom) > run.gets(worldClip + 12))
            run.put(destination + 12, run.get(destination + 12) + run.get(worldClip + 12) - bottom);
    } else {
        const uint32_t leftClip = run.get(actor + 0x54);
        if (leftClip == 0x80000000) {
            if (claw::s32(x) < 0)
                run.put(destination, 0);
            const uint32_t width = run.get(run.get(run.automatic(8)) + 0x10);
            if (claw::s32(right) >= claw::s32(width))
                run.put(destination + 8, width - 1);
            if (claw::s32(y) < 0)
                run.put(destination + 4, 0);
            const uint32_t height = run.get(run.get(run.automatic(8)) + 0x14);
            if (claw::s32(bottom) >= claw::s32(height))
                run.put(destination + 12, height - 1);
        } else {
            if (claw::s32(x) < claw::s32(leftClip))
                run.put(destination, leftClip);
            if (claw::s32(right) > run.gets(actor + 0x5c))
                run.put(destination + 8, run.get(actor + 0x5c));
            if (claw::s32(y) < run.gets(actor + 0x58))
                run.put(destination + 4, run.get(actor + 0x58));
            if (claw::s32(bottom) > run.gets(actor + 0x60))
                run.put(destination + 12, run.get(actor + 0x60));
        }
    }
    const uint32_t width = run.get(destination + 8) - run.get(destination) + 1;
    const uint32_t height = run.get(destination + 12) - run.get(destination + 4) + 1;
    if (claw::s32(width) <= 0 || claw::s32(height) <= 0) {
        run.put(actor + 0x38, 0xffffffff);
        return 0;
    }
    const uint32_t sx = run.get(destination) - x;
    const uint32_t sy = run.get(destination + 4) - y;
    run.put(source + 4, sy);
    run.put(source + 8, sx + width - 1);
    run.put(source + 12, sy + height - 1);
    const uint32_t surface = run.get(run.get(run.automatic(8)) + 0x2c);
    const uint32_t compressed = run.get(run.get(run.automatic(-0x44)) + 0x30);
    run.put(source, sx);
    run.stackPointer = run.automatic(-0x78);
    run.call(0x4bffa0, compressed, {destination, surface, source, 0, 0});

    // The returned EAX is ignored. Callback writes to the destination are
    // observed, while the clipped width/height stay held across the call.
    x = run.get(destination);
    y = run.get(destination + 4);
    run.put(actor + 0x18, x);
    run.put(actor + 0x1c, y);
    run.put(actor + 0x30, width);
    run.put(actor + 0x20, x);
    const uint32_t drawnRight = run.get(destination + 8);
    run.put(actor + 0x34, height);
    run.put(actor + 0x38, 0);
    run.put(actor + 0x24, y);
    const uint32_t drawnBottom = run.get(destination + 12);
    run.put(actor + 0x28, drawnRight);
    run.put(actor + 0x2c, drawnBottom);
    return 0;
}
} // namespace

CLAW_MODULE_ENTRY(claw_game_image_raw_entry, rawImageArguments, rawImageEntry)
