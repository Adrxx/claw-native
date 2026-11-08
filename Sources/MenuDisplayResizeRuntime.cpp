// Menu primary and auxiliary display resize.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4d5720:
    case 0x4d4280:
        return 3;
    case 0x4c9bd0:
        return 0;
    default:
        return -1;
    }
}

// +0x10/+0x14/+0x18 hold width/height/depth; +0x1c..+0x28 hold the rectangle.
bool validSize(uint32_t width, uint32_t height, uint32_t depth) {
    return s32(width) > 0 && s32(height) > 0 &&
        (depth == 8 || depth == 16 || depth == 24 || depth == 32);
}

// 0x4d5720. Primary resize; +0xc is parent and +0x2c is surface.
uint32_t primary(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t width = arguments[0];
    uint32_t height = arguments[1];
    uint32_t depth = arguments[2];
    if (run.get(receiver + 0x10) == width &&
        run.get(receiver + 0x14) == height &&
        run.get(receiver + 0x18) == depth)
        return 1;
    // Parent +0x1c is graphics manager; +0x34 bit 2 selects surface kind.
    uint32_t graphics = run.get(run.get(receiver + 0xc) + 0x1c);
    if (!graphics)
        return 0;
    run.stackPointer = run.automatic(-0x18);
    run.call(0x4bc4f0, graphics, {run.get(receiver + 0x2c)});
    run.put(receiver + 0x2c, 0);
    run.stackPointer = run.automatic(-0x20);
    if (run.call(0x4bd1c0, graphics, {width, height, depth}) != 0)
        return 0;
    uint32_t kind = (run.get8(run.get(receiver + 0xc) + 0x34) & 2) ? 2 : 1;
    run.stackPointer = run.automatic(-0x18);
    uint32_t surface = run.call(0x4bc890, graphics, {kind});
    run.put(receiver + 0x2c, surface);
    if (!surface)
        return 0;
    run.stackPointer = run.automatic(-0x14);
    if (!run.vcall(surface, 0x14))
        return 0;
    if (!validSize(width, height, depth))
        return 0;
    run.put(receiver + 0x18, depth);
    run.put(receiver + 0x10, width);
    run.put(receiver + 0x14, height);
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x24, width);
    run.put(receiver + 0x28, height);
    return 1;
}

// 0x4d4280. Auxiliary +0x4 selects attached (1) or offscreen surface.
uint32_t auxiliary(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t width = arguments[0];
    uint32_t height = arguments[1];
    uint32_t depth = arguments[2];
    if (run.get(receiver + 0x10) == width &&
        run.get(receiver + 0x14) == height &&
        run.get(receiver + 0x18) == depth)
        return 1;
    uint32_t parent = run.get(receiver + 0xc);
    uint32_t oldSurface = run.get(receiver + 0x2c);
    run.stackPointer = run.automatic(-0x18);
    run.call(0x4bc4f0, run.get(parent + 0x1c), {oldSurface});
    uint32_t mode = run.get(receiver + 0x4);
    run.put(receiver + 0x2c, 0);
    if (mode == 1) {
        parent = run.get(receiver + 0xc);
        // Parent +0x4 controller, controller +0x10 primary wrapper.
        uint32_t controller = run.get(parent + 0x4);
        uint32_t wrapper = run.get(controller + 0x10);
        uint32_t source = run.get(wrapper + 0x2c);
        run.stackPointer = run.automatic(-0x1c);
        uint32_t surface = run.call(0x4bcf80, run.get(parent + 0x1c), {source, 4});
        run.put(receiver + 0x2c, surface);
        if (!surface)
            return 0;
        mode = run.get(receiver + 0x4);
    }
    if (mode != 1) {
        parent = run.get(receiver + 0xc);
        run.stackPointer = run.automatic(-0x28);
        uint32_t surface = run.call(0x4bc670, run.get(parent + 0x1c), {width, height, depth, 0, 0xffffffff});
        run.put(receiver + 0x2c, surface);
        if (!surface)
            return 0;
    }
    if (!validSize(width, height, depth))
        return 0;
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x10, width);
    run.put(receiver + 0x14, height);
    run.put(receiver + 0x18, depth);
    run.put(receiver + 0x24, width);
    run.put(receiver + 0x28, height);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4d5720:
        return primary(run, receiver, arguments);
    case 0x4d4280:
        return auxiliary(run, receiver, arguments);
    // 0x4c9bd0. Menu state type query.
    case 0x4c9bd0:
        return 5;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_menu_display_resize_entry, owned, body)
