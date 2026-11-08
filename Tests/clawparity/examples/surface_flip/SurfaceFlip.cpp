// Reference example of a canonical module: one original function, recovered
// against Sources/ClawRuntime.hpp.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b99d0:
        return 0;
    default:
        return -1;
    }
}

// Surface fields used here: +0x08 DirectDraw surface interface, +0x14 height
// (signed), +0x18 width, +0x1c pitch in bytes.
void unlock(Run &run, uint32_t surface) {
    uint32_t interface = run.get(surface + 0x08);
    uint32_t method = run.get(run.get(interface) + 0x80);
    run.call(method, 0, {interface, 0});
}

// 0x4b99d0. Flips a surface top to bottom in place, one row at a time through
// a scratch row. Copies `width` bytes per row whatever the pixel depth, and
// re-reads the pitch from the surface before each of the three row copies.
uint32_t flipVertical(Run &run, uint32_t surface) {
    if (s32(run.get(surface + 0x14)) <= 1)
        return 0;
    uint32_t pixels = run.call(0x4b9730, surface, {0});
    if (!pixels)
        return 0;
    uint32_t scratch = run.call(0x4f63ec, 0, {run.get(surface + 0x18)});
    if (!scratch) {
        unlock(run, surface);
        return 0;
    }
    uint32_t height = run.get(surface + 0x14);
    uint32_t width = run.get(surface + 0x18);
    uint32_t half = uint32_t(s32(height) / 2);
    for (uint32_t row = 0; s32(row) < s32(half); ++row) {
        uint32_t top = row * run.get(surface + 0x1c);
        for (uint32_t x = 0; s32(x) < s32(width); ++x)
            run.put8(scratch + x, run.get8(pixels + top + x));
        uint32_t pitch = run.get(surface + 0x1c);
        uint32_t oppositeRow = height - row - 1;
        top = row * pitch;
        uint32_t bottom = oppositeRow * pitch;
        for (uint32_t x = 0; s32(x) < s32(width); ++x)
            run.put8(pixels + top + x, run.get8(pixels + bottom + x));
        bottom = oppositeRow * run.get(surface + 0x1c);
        for (uint32_t x = 0; s32(x) < s32(width); ++x)
            run.put8(pixels + bottom + x, run.get8(scratch + x));
    }
    unlock(run, surface);
    run.call(0x4f6428, 0, {scratch});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *) {
    switch (function) {
    case 0x4b99d0:
        return flipVertical(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_example_surface_flip_entry, owned, body)
