// Flipped game image actor drawing helpers
// Coordinates and rectangle edges use wrapping arithmetic and signed clipping.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4d3790:
        return 2;
    case 0x4d3550:
        return 2;
    case 0x4d3a00:
        return 2;
    case 0x4d2bb0:
        return 2;
    case 0x4d2e10:
        return 2;
    case 0x4d3080:
        return 2;
    default:
        return -1;
    }
}

// 0x4d3790. Image offsets +0x18/+0x1c, image placement +0x20/+0x24;
// actor offsets +0x10/+0x14, position +0x4c/+0x50, flags +0x08.
uint32_t function_4d3790(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t actor = arguments[0];
    const uint32_t target = arguments[1];
    const uint32_t xp = run.automatic(0x4);
    const uint32_t yp = run.automatic(-0x50);
    const uint32_t destination = run.automatic(-0x40);
    const uint32_t clipInput = run.automatic(-0x30);
    const uint32_t clip = run.automatic(-0x20);
    const uint32_t source = run.automatic(-0x10);
    uint32_t x = run.get(actor + 0x4c) - run.get(receiver + 0x20) - run.get(receiver + 0x18) - run.get(actor + 0x10);
    uint32_t y = run.get(actor + 0x50) + run.get(actor + 0x14) + run.get(receiver + 0x24) - run.get(receiver + 0x1c);
    run.put(xp, x);
    run.put(yp, y);
    if (run.get(actor + 0x08) & 0x40000) {
        // Actor world +0x3c, world transform +0x5c.
        const uint32_t transform = run.get(run.get(actor + 0x3c) + 0x5c);
        run.call(0x4c96d0, transform, {xp, yp});
        x = run.get(xp);
        y = run.get(yp);
    }
    // Image dimensions +0x10/+0x14 are reloaded after transformation.
    const uint32_t right = run.get(receiver + 0x10) + x - 1;
    const uint32_t bottom = run.get(receiver + 0x14) + y - 1;
    run.put(destination + 0x00, x);
    run.put(destination + 0x04, y);
    run.put(destination + 0x08, right);
    run.put(destination + 0x0c, bottom);
    uint32_t clippedBottom = bottom;
    if ((run.get8(actor + 0x0a) & 0x04)) {
        // Image owner +0x0c, owner viewport +0x24, viewport RECT +0x10.
        const uint32_t viewport = run.get(run.get(receiver + 0x0c) + 0x24);
        run.put(clipInput + 0x00, run.get(viewport + 0x10));
        run.put(clipInput + 0x04, run.get(viewport + 0x14));
        run.put(clipInput + 0x08, run.get(viewport + 0x18));
        run.put(clipInput + 0x0c, run.get(viewport + 0x1c));
        run.icall(0x546d58, {clip, clipInput});
        x = run.get(xp);
        uint32_t edge = run.get(clip + 0x00);
        if (s32(x) < s32(edge)) {
            run.put(destination + 0x00, run.get(destination + 0x00) + edge - x);
        }
        edge = run.get(clip + 0x08);
        if (s32(right) > s32(edge)) {
            run.put(destination + 0x08, run.get(destination + 0x08) + edge - right);
        }
        y = run.get(yp);
        edge = run.get(clip + 0x04);
        if (s32(y) < s32(edge)) {
            run.put(destination + 0x04, run.get(destination + 0x04) + edge - y);
        }
        edge = run.get(clip + 0x0c);
        if (s32(bottom) > s32(edge)) {
            run.put(destination + 0x0c, run.get(destination + 0x0c) + edge - bottom);
        }
    } else {
        // Actor explicit clip +0x54/+0x58/+0x5c/+0x60, or target dimensions.
        uint32_t edge = run.get(actor + 0x54);
        if (edge == 0x80000000) {
            if (s32(x) < 0) {
                run.put(destination + 0x00, 0);
            }
            edge = run.get(target + 0x10);
            if (s32(right) >= s32(edge)) {
                run.put(destination + 0x08, edge - 1);
            }
            if (s32(y) < 0) {
                run.put(destination + 0x04, 0);
            }
            edge = run.get(target + 0x14);
            if (s32(bottom) >= s32(edge)) {
                run.put(destination + 0x0c, edge - 1);
            }
        } else {
            if (s32(x) < s32(edge)) {
                run.put(destination + 0x00, edge);
            }
            edge = run.get(actor + 0x5c);
            if (s32(right) > s32(edge)) {
                run.put(destination + 0x08, edge);
            }
            edge = run.get(actor + 0x58);
            if (s32(y) < s32(edge)) {
                run.put(destination + 0x04, edge);
            }
            edge = run.get(actor + 0x60);
            if (s32(bottom) > s32(edge)) {
                run.put(destination + 0x0c, edge);
            }
        }
    }
    clippedBottom = run.get(destination + 0x0c);
    const uint32_t left = run.get(destination + 0x00);
    const uint32_t top = run.get(destination + 0x04);
    const uint32_t clippedRight = run.get(destination + 0x08);
    const uint32_t width = clippedRight - left + 1;
    const uint32_t height = clippedBottom - top + 1;
    // Actor status +0x38 is the only output for an empty rectangle.
    if (s32(width) <= 0 || s32(height) <= 0) {
        run.put(actor + 0x38, 0xffffffff);
        return 0;
    }
    const uint32_t sourceLeft = left - x;
    const uint32_t sourceTop = top - y;
    run.put(source + 0x00, sourceLeft);
    run.put(source + 0x04, sourceTop);
    run.put(source + 0x08, sourceLeft + width - 1);
    run.put(source + 0x0c, sourceTop + height - 1);
    // Software descriptor +0x30, target surface wrapper +0x2c.
    const uint32_t targetSurface = run.get(target + 0x2c);
    const uint32_t descriptor = run.get(receiver + 0x30);
    run.call(0x4bffa0, descriptor, {destination, targetSurface, source, 1, 0});
    // Reload the rectangle after drawing; retain the pre-call dimensions.
    const uint32_t outputLeft = run.get(destination + 0x00);
    const uint32_t outputTop = run.get(destination + 0x04);
    run.put(actor + 0x18, outputLeft);
    run.put(actor + 0x1c, outputTop);
    run.put(actor + 0x30, width);
    run.put(actor + 0x20, outputLeft);
    const uint32_t outputRight = run.get(destination + 0x08);
    run.put(actor + 0x34, height);
    run.put(actor + 0x38, 0);
    run.put(actor + 0x24, outputTop);
    const uint32_t outputBottom = run.get(destination + 0x0c);
    run.put(actor + 0x28, outputRight);
    run.put(actor + 0x2c, outputBottom);
    return 0;
}

// 0x4d3550. Image offsets +0x18/+0x1c, image placement +0x20/+0x24;
// actor offsets +0x10/+0x14, position +0x4c/+0x50, flags +0x08.
uint32_t function_4d3550(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t actor = arguments[0];
    const uint32_t target = arguments[1];
    const uint32_t xp = run.automatic(0x4);
    const uint32_t yp = run.automatic(-0x4c);
    const uint32_t destination = run.automatic(-0x40);
    const uint32_t clipInput = run.automatic(-0x30);
    const uint32_t clip = run.automatic(-0x20);
    const uint32_t source = run.automatic(-0x10);
    uint32_t x = run.get(actor + 0x4c) - run.get(receiver + 0x18) - run.get(actor + 0x10) - run.get(receiver + 0x20);
    uint32_t y = run.get(actor + 0x50) - run.get(actor + 0x14) - run.get(receiver + 0x1c) - run.get(receiver + 0x24);
    run.put(xp, x);
    run.put(yp, y);
    if (run.get(actor + 0x08) & 0x40000) {
        // Actor world +0x3c, world transform +0x5c.
        const uint32_t transform = run.get(run.get(actor + 0x3c) + 0x5c);
        run.call(0x4c96d0, transform, {xp, yp});
        x = run.get(xp);
        y = run.get(yp);
    }
    // Image dimensions +0x10/+0x14 are reloaded after transformation.
    const uint32_t right = run.get(receiver + 0x10) + x - 1;
    const uint32_t bottom = run.get(receiver + 0x14) + y - 1;
    run.put(destination + 0x00, x);
    run.put(destination + 0x04, y);
    run.put(destination + 0x08, right);
    run.put(destination + 0x0c, bottom);
    uint32_t clippedBottom = bottom;
    if ((run.get(actor + 0x08) & 0x40000)) {
        // Image owner +0x0c, owner viewport +0x24, viewport RECT +0x10.
        const uint32_t viewport = run.get(run.get(receiver + 0x0c) + 0x24);
        run.put(clipInput + 0x00, run.get(viewport + 0x10));
        run.put(clipInput + 0x04, run.get(viewport + 0x14));
        run.put(clipInput + 0x08, run.get(viewport + 0x18));
        run.put(clipInput + 0x0c, run.get(viewport + 0x1c));
        run.icall(0x546d58, {clip, clipInput});
        x = run.get(xp);
        uint32_t edge = run.get(clip + 0x00);
        if (s32(x) < s32(edge)) {
            run.put(destination + 0x00, run.get(destination + 0x00) + edge - x);
        }
        edge = run.get(clip + 0x08);
        if (s32(right) > s32(edge)) {
            run.put(destination + 0x08, run.get(destination + 0x08) + edge - right);
        }
        y = run.get(yp);
        edge = run.get(clip + 0x04);
        if (s32(y) < s32(edge)) {
            run.put(destination + 0x04, run.get(destination + 0x04) + edge - y);
        }
        edge = run.get(clip + 0x0c);
        if (s32(bottom) > s32(edge)) {
            run.put(destination + 0x0c, run.get(destination + 0x0c) + edge - bottom);
        }
    } else {
        // Actor explicit clip +0x54/+0x58/+0x5c/+0x60, or target dimensions.
        uint32_t edge = run.get(actor + 0x54);
        if (edge == 0x80000000) {
            if (s32(x) < 0) {
                run.put(destination + 0x00, 0);
            }
            edge = run.get(target + 0x10);
            if (s32(right) >= s32(edge)) {
                run.put(destination + 0x08, edge - 1);
            }
            if (s32(y) < 0) {
                run.put(destination + 0x04, 0);
            }
            edge = run.get(target + 0x14);
            if (s32(bottom) >= s32(edge)) {
                run.put(destination + 0x0c, edge - 1);
            }
        } else {
            if (s32(x) < s32(edge)) {
                run.put(destination + 0x00, edge);
            }
            edge = run.get(actor + 0x5c);
            if (s32(right) > s32(edge)) {
                run.put(destination + 0x08, edge);
            }
            edge = run.get(actor + 0x58);
            if (s32(y) < s32(edge)) {
                run.put(destination + 0x04, edge);
            }
            edge = run.get(actor + 0x60);
            if (s32(bottom) > s32(edge)) {
                run.put(destination + 0x0c, edge);
            }
        }
    }
    clippedBottom = run.get(destination + 0x0c);
    const uint32_t left = run.get(destination + 0x00);
    const uint32_t top = run.get(destination + 0x04);
    const uint32_t clippedRight = run.get(destination + 0x08);
    const uint32_t width = clippedRight - left + 1;
    const uint32_t height = clippedBottom - top + 1;
    // Actor status +0x38 is the only output for an empty rectangle.
    if (s32(width) <= 0 || s32(height) <= 0) {
        run.put(actor + 0x38, 0xffffffff);
        return 0;
    }
    const uint32_t sourceLeft = right - clippedRight;
    const uint32_t sourceTop = bottom - clippedBottom;
    run.put(source + 0x00, sourceLeft);
    run.put(source + 0x04, sourceTop);
    run.put(source + 0x08, sourceLeft + width - 1);
    run.put(source + 0x0c, sourceTop + height - 1);
    // Software descriptor +0x30, target surface wrapper +0x2c.
    const uint32_t targetSurface = run.get(target + 0x2c);
    const uint32_t descriptor = run.get(receiver + 0x30);
    run.call(0x4bffa0, descriptor, {destination, targetSurface, source, 1, 1});
    // Reload the rectangle after drawing; retain the pre-call dimensions.
    const uint32_t outputLeft = run.get(destination + 0x00);
    const uint32_t outputTop = run.get(destination + 0x04);
    run.put(actor + 0x18, outputLeft);
    run.put(actor + 0x1c, outputTop);
    run.put(actor + 0x30, width);
    run.put(actor + 0x20, outputLeft);
    const uint32_t outputRight = run.get(destination + 0x08);
    run.put(actor + 0x34, height);
    run.put(actor + 0x38, 0);
    run.put(actor + 0x24, outputTop);
    const uint32_t outputBottom = run.get(destination + 0x0c);
    run.put(actor + 0x28, outputRight);
    run.put(actor + 0x2c, outputBottom);
    return 0;
}

// 0x4d3a00. Image offsets +0x18/+0x1c, image placement +0x20/+0x24;
// actor offsets +0x10/+0x14, position +0x4c/+0x50, flags +0x08.
uint32_t function_4d3a00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t actor = arguments[0];
    const uint32_t target = arguments[1];
    const uint32_t xp = run.automatic(0x4);
    const uint32_t yp = run.automatic(-0x44);
    const uint32_t destination = run.automatic(-0x40);
    const uint32_t clipInput = run.automatic(-0x30);
    const uint32_t clip = run.automatic(-0x20);
    const uint32_t source = run.automatic(-0x10);
    uint32_t x = run.get(receiver + 0x20) - run.get(receiver + 0x18) + run.get(actor + 0x10) + run.get(actor + 0x4c);
    uint32_t y = run.get(actor + 0x50) - run.get(actor + 0x14) - run.get(receiver + 0x1c) - run.get(receiver + 0x24);
    run.put(xp, x);
    run.put(yp, y);
    if (run.get(actor + 0x08) & 0x40000) {
        // Actor world +0x3c, world transform +0x5c.
        const uint32_t transform = run.get(run.get(actor + 0x3c) + 0x5c);
        run.call(0x4c96d0, transform, {xp, yp});
        x = run.get(xp);
        y = run.get(yp);
    }
    // Image dimensions +0x10/+0x14 are reloaded after transformation.
    const uint32_t right = run.get(receiver + 0x10) + x - 1;
    const uint32_t bottom = run.get(receiver + 0x14) + y - 1;
    run.put(destination + 0x00, x);
    run.put(destination + 0x04, y);
    run.put(destination + 0x08, right);
    run.put(destination + 0x0c, bottom);
    uint32_t clippedBottom = bottom;
    if ((run.get8(actor + 0x0a) & 0x04)) {
        // Image owner +0x0c, owner viewport +0x24, viewport RECT +0x10.
        const uint32_t viewport = run.get(run.get(receiver + 0x0c) + 0x24);
        run.put(clipInput + 0x00, run.get(viewport + 0x10));
        run.put(clipInput + 0x04, run.get(viewport + 0x14));
        run.put(clipInput + 0x08, run.get(viewport + 0x18));
        run.put(clipInput + 0x0c, run.get(viewport + 0x1c));
        run.icall(0x546d58, {clip, clipInput});
        x = run.get(xp);
        uint32_t edge = run.get(clip + 0x00);
        if (s32(x) < s32(edge)) {
            run.put(destination + 0x00, run.get(destination + 0x00) + edge - x);
        }
        edge = run.get(clip + 0x08);
        if (s32(right) > s32(edge)) {
            run.put(destination + 0x08, run.get(destination + 0x08) + edge - right);
        }
        y = run.get(yp);
        edge = run.get(clip + 0x04);
        if (s32(y) < s32(edge)) {
            run.put(destination + 0x04, run.get(destination + 0x04) + edge - y);
        }
        edge = run.get(clip + 0x0c);
        if (s32(bottom) > s32(edge)) {
            run.put(destination + 0x0c, run.get(destination + 0x0c) + edge - bottom);
        }
    } else {
        // Actor explicit clip +0x54/+0x58/+0x5c/+0x60, or target dimensions.
        uint32_t edge = run.get(actor + 0x54);
        if (edge == 0x80000000) {
            if (s32(x) < 0) {
                run.put(destination + 0x00, 0);
            }
            edge = run.get(target + 0x10);
            if (s32(right) >= s32(edge)) {
                run.put(destination + 0x08, edge - 1);
            }
            if (s32(y) < 0) {
                run.put(destination + 0x04, 0);
            }
            edge = run.get(target + 0x14);
            if (s32(bottom) >= s32(edge)) {
                run.put(destination + 0x0c, edge - 1);
            }
        } else {
            if (s32(x) < s32(edge)) {
                run.put(destination + 0x00, edge);
            }
            edge = run.get(actor + 0x5c);
            if (s32(right) > s32(edge)) {
                run.put(destination + 0x08, edge);
            }
            edge = run.get(actor + 0x58);
            if (s32(y) < s32(edge)) {
                run.put(destination + 0x04, edge);
            }
            edge = run.get(actor + 0x60);
            if (s32(bottom) > s32(edge)) {
                run.put(destination + 0x0c, edge);
            }
        }
    }
    clippedBottom = run.get(destination + 0x0c);
    const uint32_t left = run.get(destination + 0x00);
    const uint32_t top = run.get(destination + 0x04);
    const uint32_t clippedRight = run.get(destination + 0x08);
    const uint32_t width = clippedRight - left + 1;
    const uint32_t height = clippedBottom - top + 1;
    // Actor status +0x38 is the only output for an empty rectangle.
    if (s32(width) <= 0 || s32(height) <= 0) {
        run.put(actor + 0x38, 0xffffffff);
        return 0;
    }
    const uint32_t sourceLeft = left - x;
    const uint32_t sourceTop = bottom - clippedBottom;
    run.put(source + 0x00, sourceLeft);
    run.put(source + 0x04, sourceTop);
    run.put(source + 0x08, sourceLeft + width - 1);
    run.put(source + 0x0c, sourceTop + height - 1);
    // Software descriptor +0x30, target surface wrapper +0x2c.
    const uint32_t targetSurface = run.get(target + 0x2c);
    const uint32_t descriptor = run.get(receiver + 0x30);
    run.call(0x4bffa0, descriptor, {destination, targetSurface, source, 0, 1});
    // Reload the rectangle after drawing; retain the pre-call dimensions.
    const uint32_t outputLeft = run.get(destination + 0x00);
    const uint32_t outputTop = run.get(destination + 0x04);
    run.put(actor + 0x30, width);
    run.put(actor + 0x18, outputLeft);
    run.put(actor + 0x1c, outputTop);
    run.put(actor + 0x34, height);
    const uint32_t outputRight = run.get(destination + 0x08);
    run.put(actor + 0x20, outputLeft);
    run.put(actor + 0x38, 0);
    run.put(actor + 0x24, outputTop);
    const uint32_t outputBottom = run.get(destination + 0x0c);
    run.put(actor + 0x28, outputRight);
    run.put(actor + 0x2c, outputBottom);
    return 0;
}

// 0x4d2bb0. Image offsets +0x18/+0x1c, image placement +0x20/+0x24;
// actor offsets +0x10/+0x14, position +0x4c/+0x50, flags +0x08.
uint32_t function_4d2bb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t actor = arguments[0];
    const uint32_t target = arguments[1];
    const uint32_t xp = run.automatic(0x4);
    const uint32_t yp = run.automatic(-0x4c);
    const uint32_t destination = run.automatic(-0x40);
    const uint32_t clipInput = run.automatic(-0x30);
    const uint32_t clip = run.automatic(-0x20);
    const uint32_t source = run.automatic(-0x10);
    uint32_t x = run.get(actor + 0x4c) - run.get(receiver + 0x18) - run.get(actor + 0x10) - run.get(receiver + 0x20);
    uint32_t y = run.get(actor + 0x50) - run.get(receiver + 0x1c) - run.get(actor + 0x14) - run.get(receiver + 0x24);
    run.put(xp, x);
    run.put(yp, y);
    if (run.get(actor + 0x08) & 0x40000) {
        // Actor world +0x3c, world transform +0x5c.
        const uint32_t transform = run.get(run.get(actor + 0x3c) + 0x5c);
        run.call(0x4c96d0, transform, {xp, yp});
        x = run.get(xp);
        y = run.get(yp);
    }
    // Image dimensions +0x10/+0x14 are reloaded after transformation.
    const uint32_t right = run.get(receiver + 0x10) + x - 1;
    const uint32_t bottom = run.get(receiver + 0x14) + y - 1;
    run.put(destination + 0x00, x);
    run.put(destination + 0x04, y);
    run.put(destination + 0x08, right);
    run.put(destination + 0x0c, bottom);
    uint32_t clippedBottom = bottom;
    if ((run.get8(actor + 0x0a) & 0x04)) {
        // Image owner +0x0c, owner viewport +0x24, viewport RECT +0x10.
        const uint32_t viewport = run.get(run.get(receiver + 0x0c) + 0x24);
        run.put(clipInput + 0x00, run.get(viewport + 0x10));
        run.put(clipInput + 0x04, run.get(viewport + 0x14));
        run.put(clipInput + 0x08, run.get(viewport + 0x18));
        run.put(clipInput + 0x0c, run.get(viewport + 0x1c));
        run.icall(0x546d58, {clip, clipInput});
        x = run.get(xp);
        uint32_t edge = run.get(clip + 0x00);
        if (s32(x) < s32(edge)) {
            run.put(destination + 0x00, run.get(destination + 0x00) + edge - x);
        }
        edge = run.get(clip + 0x08);
        if (s32(right) > s32(edge)) {
            run.put(destination + 0x08, run.get(destination + 0x08) + edge - right);
        }
        y = run.get(yp);
        edge = run.get(clip + 0x04);
        if (s32(y) < s32(edge)) {
            run.put(destination + 0x04, run.get(destination + 0x04) + edge - y);
        }
        edge = run.get(clip + 0x0c);
        if (s32(bottom) > s32(edge)) {
            clippedBottom = run.get(destination + 0x0c) + edge - bottom;
        }
    } else {
        // Actor explicit clip +0x54/+0x58/+0x5c/+0x60, or target dimensions.
        uint32_t edge = run.get(actor + 0x54);
        if (edge == 0x80000000) {
            if (s32(x) < 0) {
                run.put(destination + 0x00, 0);
            }
            edge = run.get(target + 0x10);
            if (s32(right) >= s32(edge)) {
                run.put(destination + 0x08, edge - 1);
            }
            if (s32(y) < 0) {
                run.put(destination + 0x04, 0);
            }
            edge = run.get(target + 0x14);
            if (s32(bottom) >= s32(edge)) {
                clippedBottom = edge - 1;
            }
        } else {
            if (s32(x) < s32(edge)) {
                run.put(destination + 0x00, edge);
            }
            edge = run.get(actor + 0x5c);
            if (s32(right) > s32(edge)) {
                run.put(destination + 0x08, edge);
            }
            edge = run.get(actor + 0x58);
            if (s32(y) < s32(edge)) {
                run.put(destination + 0x04, edge);
            }
            edge = run.get(actor + 0x60);
            if (s32(bottom) > s32(edge)) {
                clippedBottom = edge;
            }
        }
    }
    const uint32_t left = run.get(destination + 0x00);
    const uint32_t top = run.get(destination + 0x04);
    const uint32_t clippedRight = run.get(destination + 0x08);
    const uint32_t width = clippedRight - left + 1;
    const uint32_t height = clippedBottom - top + 1;
    // Actor status +0x38 is the only output for an empty rectangle.
    if (s32(width) <= 0 || s32(height) <= 0) {
        run.put(actor + 0x38, 0xffffffff);
        return 0;
    }
    const uint32_t sourceLeft = right - clippedRight;
    const uint32_t sourceTop = bottom - clippedBottom;
    run.put(source + 0x00, sourceLeft);
    run.put(source + 0x04, sourceTop);
    run.put(source + 0x08, sourceLeft + width);
    run.put(source + 0x0c, sourceTop + height);
    run.put(destination + 0x08, clippedRight + 1);
    run.put(destination + 0x0c, clippedBottom + 1);
    run.put(0x54310c, 6);
    // Surface wrappers at image/target +0x2c; the original Blt is retained.
    const uint32_t sourceSurface = run.get(receiver + 0x2c);
    const uint32_t targetSurface = run.get(target + 0x2c);
    run.call(0x4b9ce0, targetSurface, {destination, sourceSurface, source, 0x8800, 0x543108});
    // Reload the rectangle after drawing; retain the pre-call dimensions.
    const uint32_t outputLeft = run.get(destination + 0x00);
    const uint32_t outputTop = run.get(destination + 0x04);
    const uint32_t outputRight = run.get(destination + 0x08) - 1;
    run.put(actor + 0x30, width);
    const uint32_t outputBottom = run.get(destination + 0x0c) - 1;
    run.put(actor + 0x20, outputLeft);
    run.put(actor + 0x18, outputLeft);
    run.put(actor + 0x1c, outputTop);
    run.put(actor + 0x34, height);
    run.put(actor + 0x24, outputTop);
    run.put(actor + 0x38, 0);
    run.put(actor + 0x28, outputRight);
    run.put(actor + 0x2c, outputBottom);
    return 0;
}

// 0x4d2e10. Image offsets +0x18/+0x1c, image placement +0x20/+0x24;
// actor offsets +0x10/+0x14, position +0x4c/+0x50, flags +0x08.
uint32_t function_4d2e10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t actor = arguments[0];
    const uint32_t target = arguments[1];
    const uint32_t xp = run.automatic(-0x4c);
    const uint32_t yp = run.automatic(-0x48);
    const uint32_t destination = run.automatic(-0x40);
    const uint32_t clipInput = run.automatic(-0x30);
    const uint32_t clip = run.automatic(-0x20);
    const uint32_t source = run.automatic(-0x10);
    uint32_t x = run.get(actor + 0x4c) - run.get(receiver + 0x20) - run.get(receiver + 0x18) - run.get(actor + 0x10);
    uint32_t y = run.get(actor + 0x50) + run.get(actor + 0x14) + run.get(receiver + 0x24) - run.get(receiver + 0x1c);
    run.put(xp, x);
    run.put(yp, y);
    if (run.get(actor + 0x08) & 0x40000) {
        // Actor world +0x3c, world transform +0x5c.
        const uint32_t transform = run.get(run.get(actor + 0x3c) + 0x5c);
        run.call(0x4c96d0, transform, {xp, yp});
        x = run.get(xp);
        y = run.get(yp);
    }
    // Image dimensions +0x10/+0x14 are reloaded after transformation.
    const uint32_t right = run.get(receiver + 0x10) + x - 1;
    const uint32_t bottom = run.get(receiver + 0x14) + y - 1;
    run.put(destination + 0x00, x);
    run.put(destination + 0x04, y);
    run.put(destination + 0x08, right);
    run.put(destination + 0x0c, bottom);
    uint32_t clippedBottom = bottom;
    if ((run.get(actor + 0x08) & 0x40000)) {
        // Image owner +0x0c, owner viewport +0x24, viewport RECT +0x10.
        const uint32_t viewport = run.get(run.get(receiver + 0x0c) + 0x24);
        run.put(clipInput + 0x00, run.get(viewport + 0x10));
        run.put(clipInput + 0x04, run.get(viewport + 0x14));
        run.put(clipInput + 0x08, run.get(viewport + 0x18));
        run.put(clipInput + 0x0c, run.get(viewport + 0x1c));
        run.icall(0x546d58, {clip, clipInput});
        x = run.get(xp);
        uint32_t edge = run.get(clip + 0x00);
        if (s32(x) < s32(edge)) {
            run.put(destination + 0x00, run.get(destination + 0x00) + edge - x);
        }
        edge = run.get(clip + 0x08);
        if (s32(right) > s32(edge)) {
            run.put(destination + 0x08, run.get(destination + 0x08) + edge - right);
        }
        y = run.get(yp);
        edge = run.get(clip + 0x04);
        if (s32(y) < s32(edge)) {
            run.put(destination + 0x04, run.get(destination + 0x04) + edge - y);
        }
        edge = run.get(clip + 0x0c);
        if (s32(bottom) > s32(edge)) {
            run.put(destination + 0x0c, run.get(destination + 0x0c) + edge - bottom);
        }
    } else {
        // Actor explicit clip +0x54/+0x58/+0x5c/+0x60, or target dimensions.
        uint32_t edge = run.get(actor + 0x54);
        if (edge == 0x80000000) {
            if (s32(x) < 0) {
                run.put(destination + 0x00, 0);
            }
            edge = run.get(target + 0x10);
            if (s32(right) >= s32(edge)) {
                run.put(destination + 0x08, edge - 1);
            }
            if (s32(y) < 0) {
                run.put(destination + 0x04, 0);
            }
            edge = run.get(target + 0x14);
            if (s32(bottom) >= s32(edge)) {
                run.put(destination + 0x0c, edge - 1);
            }
        } else {
            if (s32(x) < s32(edge)) {
                run.put(destination + 0x00, edge);
            }
            edge = run.get(actor + 0x5c);
            if (s32(right) > s32(edge)) {
                run.put(destination + 0x08, edge);
            }
            edge = run.get(actor + 0x58);
            if (s32(y) < s32(edge)) {
                run.put(destination + 0x04, edge);
            }
            edge = run.get(actor + 0x60);
            if (s32(bottom) > s32(edge)) {
                run.put(destination + 0x0c, edge);
            }
        }
    }
    clippedBottom = run.get(destination + 0x0c);
    const uint32_t left = run.get(destination + 0x00);
    const uint32_t top = run.get(destination + 0x04);
    const uint32_t clippedRight = run.get(destination + 0x08);
    const uint32_t width = clippedRight - left + 1;
    const uint32_t height = clippedBottom - top + 1;
    // Actor status +0x38 is the only output for an empty rectangle.
    if (s32(width) <= 0 || s32(height) <= 0) {
        run.put(actor + 0x38, 0xffffffff);
        return 0;
    }
    const uint32_t sourceLeft = right - clippedRight;
    const uint32_t sourceTop = top - y;
    run.put(source + 0x00, sourceLeft);
    run.put(source + 0x04, sourceTop);
    run.put(source + 0x08, sourceLeft + width);
    run.put(source + 0x0c, sourceTop + height);
    run.put(destination + 0x08, clippedRight + 1);
    run.put(destination + 0x0c, clippedBottom + 1);
    run.put(0x54310c, 2);
    // Surface wrappers at image/target +0x2c; the original Blt is retained.
    const uint32_t sourceSurface = run.get(receiver + 0x2c);
    const uint32_t targetSurface = run.get(target + 0x2c);
    run.call(0x4b9ce0, targetSurface, {destination, sourceSurface, source, 0x8800, 0x543108});
    // Reload the rectangle after drawing; retain the pre-call dimensions.
    const uint32_t outputLeft = run.get(destination + 0x00);
    const uint32_t outputTop = run.get(destination + 0x04);
    const uint32_t outputRight = run.get(destination + 0x08) - 1;
    run.put(actor + 0x30, width);
    const uint32_t outputBottom = run.get(destination + 0x0c) - 1;
    run.put(actor + 0x20, outputLeft);
    run.put(actor + 0x18, outputLeft);
    run.put(actor + 0x1c, outputTop);
    run.put(actor + 0x34, height);
    run.put(actor + 0x24, outputTop);
    run.put(actor + 0x38, 0);
    run.put(actor + 0x28, outputRight);
    run.put(actor + 0x2c, outputBottom);
    return 0;
}

// 0x4d3080. Image offsets +0x18/+0x1c, image placement +0x20/+0x24;
// actor offsets +0x10/+0x14, position +0x4c/+0x50, flags +0x08.
uint32_t function_4d3080(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t actor = arguments[0];
    const uint32_t target = arguments[1];
    const uint32_t xp = run.automatic(0x4);
    const uint32_t yp = run.automatic(-0x48);
    const uint32_t destination = run.automatic(-0x40);
    const uint32_t clipInput = run.automatic(-0x30);
    const uint32_t clip = run.automatic(-0x20);
    const uint32_t source = run.automatic(-0x10);
    uint32_t x = run.get(receiver + 0x20) + run.get(actor + 0x10) + run.get(actor + 0x4c) - run.get(receiver + 0x18);
    uint32_t y = run.get(actor + 0x50) - run.get(receiver + 0x1c) - run.get(actor + 0x14) - run.get(receiver + 0x24);
    run.put(xp, x);
    run.put(yp, y);
    if (run.get(actor + 0x08) & 0x40000) {
        // Actor world +0x3c, world transform +0x5c.
        const uint32_t transform = run.get(run.get(actor + 0x3c) + 0x5c);
        run.call(0x4c96d0, transform, {xp, yp});
        x = run.get(xp);
        y = run.get(yp);
    }
    // Image dimensions +0x10/+0x14 are reloaded after transformation.
    const uint32_t right = run.get(receiver + 0x10) + x - 1;
    const uint32_t bottom = run.get(receiver + 0x14) + y - 1;
    run.put(destination + 0x00, x);
    run.put(destination + 0x04, y);
    run.put(destination + 0x08, right);
    run.put(destination + 0x0c, bottom);
    uint32_t clippedBottom = bottom;
    if ((run.get8(actor + 0x0a) & 0x04)) {
        // Image owner +0x0c, owner viewport +0x24, viewport RECT +0x10.
        const uint32_t viewport = run.get(run.get(receiver + 0x0c) + 0x24);
        run.put(clipInput + 0x00, run.get(viewport + 0x10));
        run.put(clipInput + 0x04, run.get(viewport + 0x14));
        run.put(clipInput + 0x08, run.get(viewport + 0x18));
        run.put(clipInput + 0x0c, run.get(viewport + 0x1c));
        run.icall(0x546d58, {clip, clipInput});
        x = run.get(xp);
        uint32_t edge = run.get(clip + 0x00);
        if (s32(x) < s32(edge)) {
            run.put(destination + 0x00, run.get(destination + 0x00) + edge - x);
        }
        edge = run.get(clip + 0x08);
        if (s32(right) > s32(edge)) {
            run.put(destination + 0x08, run.get(destination + 0x08) + edge - right);
        }
        y = run.get(yp);
        edge = run.get(clip + 0x04);
        if (s32(y) < s32(edge)) {
            run.put(destination + 0x04, run.get(destination + 0x04) + edge - y);
        }
        edge = run.get(clip + 0x0c);
        if (s32(bottom) > s32(edge)) {
            run.put(destination + 0x0c, run.get(destination + 0x0c) + edge - bottom);
        }
    } else {
        // Actor explicit clip +0x54/+0x58/+0x5c/+0x60, or target dimensions.
        uint32_t edge = run.get(actor + 0x54);
        if (edge == 0x80000000) {
            if (s32(x) < 0) {
                run.put(destination + 0x00, 0);
            }
            edge = run.get(target + 0x10);
            if (s32(right) >= s32(edge)) {
                run.put(destination + 0x08, edge - 1);
            }
            if (s32(y) < 0) {
                run.put(destination + 0x04, 0);
            }
            edge = run.get(target + 0x14);
            if (s32(bottom) >= s32(edge)) {
                run.put(destination + 0x0c, edge - 1);
            }
        } else {
            if (s32(x) < s32(edge)) {
                run.put(destination + 0x00, edge);
            }
            edge = run.get(actor + 0x5c);
            if (s32(right) > s32(edge)) {
                run.put(destination + 0x08, edge);
            }
            edge = run.get(actor + 0x58);
            if (s32(y) < s32(edge)) {
                run.put(destination + 0x04, edge);
            }
            edge = run.get(actor + 0x60);
            if (s32(bottom) > s32(edge)) {
                run.put(destination + 0x0c, edge);
            }
        }
    }
    clippedBottom = run.get(destination + 0x0c);
    const uint32_t left = run.get(destination + 0x00);
    const uint32_t top = run.get(destination + 0x04);
    const uint32_t clippedRight = run.get(destination + 0x08);
    const uint32_t width = clippedRight - left + 1;
    const uint32_t height = clippedBottom - top + 1;
    // Actor status +0x38 is the only output for an empty rectangle.
    if (s32(width) <= 0 || s32(height) <= 0) {
        run.put(actor + 0x38, 0xffffffff);
        return 0;
    }
    const uint32_t sourceLeft = left - x;
    const uint32_t sourceTop = bottom - clippedBottom;
    run.put(source + 0x00, sourceLeft);
    run.put(source + 0x04, sourceTop);
    run.put(source + 0x08, sourceLeft + width);
    run.put(source + 0x0c, sourceTop + height);
    run.put(destination + 0x08, clippedRight + 1);
    run.put(destination + 0x0c, clippedBottom + 1);
    run.put(0x54310c, 4);
    // Surface wrappers at image/target +0x2c; the original Blt is retained.
    const uint32_t sourceSurface = run.get(receiver + 0x2c);
    const uint32_t targetSurface = run.get(target + 0x2c);
    run.call(0x4b9ce0, targetSurface, {destination, sourceSurface, source, 0x8800, 0x543108});
    // Reload the rectangle after drawing; retain the pre-call dimensions.
    const uint32_t outputLeft = run.get(destination + 0x00);
    const uint32_t outputTop = run.get(destination + 0x04);
    const uint32_t outputRight = run.get(destination + 0x08) - 1;
    run.put(actor + 0x30, width);
    const uint32_t outputBottom = run.get(destination + 0x0c) - 1;
    run.put(actor + 0x20, outputLeft);
    run.put(actor + 0x18, outputLeft);
    run.put(actor + 0x1c, outputTop);
    run.put(actor + 0x34, height);
    run.put(actor + 0x24, outputTop);
    run.put(actor + 0x38, 0);
    run.put(actor + 0x28, outputRight);
    run.put(actor + 0x2c, outputBottom);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4d3790:
        return function_4d3790(run, receiver, arguments);
    case 0x4d3550:
        return function_4d3550(run, receiver, arguments);
    case 0x4d3a00:
        return function_4d3a00(run, receiver, arguments);
    case 0x4d2bb0:
        return function_4d2bb0(run, receiver, arguments);
    case 0x4d2e10:
        return function_4d2e10(run, receiver, arguments);
    case 0x4d3080:
        return function_4d3080(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_game_image_flips_entry, owned, body)
