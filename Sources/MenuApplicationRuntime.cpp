// Menu application readiness, display sizing, viewport and camera policy.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x425640:
    case 0x42ae70:
        return 0;
    case 0x429eb0:
    case 0x42a000:
        return 1;
    case 0x429e10:
    case 0x42a060:
        return 2;
    case 0x429ed0:
        return 3;
    default:
        return -1;
    }
}

// Retain the original entry-relative locations of address-taken locals when
// an owned caller enters another owned function directly.
struct Frame {
    Run &run;
    uint32_t saved;
    Frame(Run &run, uint32_t displacement) : run(run), saved(run.frame) {
        run.frame -= displacement;
    }
    ~Frame() {
        run.frame = saved;
    }
};

// Shared original clear/present pair. Scene +0x04 is its display manager;
// manager +0x14/+0x10 are back/front, wrapper +0x2c is the actual surface.
void clearPair(Run &run, uint32_t app, uint32_t localBytes) {
    uint32_t savedStack = run.stackPointer;
    run.stackPointer = run.frame - localBytes - 0x08;
    uint32_t manager = run.get(run.get(app + 0x30) + 0x04);
    run.call(0x4b97c0, run.get(run.get(manager + 0x14) + 0x2c), {0});
    run.call(0x4b98b0, run.get(run.get(manager + 0x10) + 0x2c), {0});
    run.stackPointer = savedStack;
}

// 0x425640. Application +0x30 scene and +0x2c state are readiness tokens.
uint32_t function_425640(Run &run, uint32_t app) {
    if (!run.get(app + 0x30))
        return 0;
    return run.get(app + 0x2c) ? 1 : 0;
}

// 0x429e10. Application +0x08 is the diagnostic receiver.
void function_429e10(Run &run, uint32_t app, uint32_t code, uint32_t detail) {
    uint32_t target = run.get(app + 0x08);
    if (target)
        run.vcall(target, 0x1c, {code, detail});
}

// 0x429ed0. Application +0x68 is layout, +0x6c is redraw state;
// front surface +0x10/+0x14 are signed width and height.
void function_429ed0(Run &run, uint32_t app, uint32_t layout, uint32_t force, uint32_t present) {
    if (s32(layout) >= 10)
        layout = 10;
    if (s32(layout) <= 1)
        layout = 1;
    if (layout == run.get(app + 0x68) && !force)
        return;
    uint32_t scene = run.get(app + 0x30);
    run.put(app + 0x68, layout);
    uint32_t front = run.get(run.get(scene + 0x04) + 0x10);
    uint32_t height = run.get(front + 0x14);
    uint32_t width = run.get(front + 0x10);
    // Each multiplication rounds to binary64, matching x87 CW 0x023f.
    double scaled = double(10 - layout) * double(run.getf(0x50c34c));
    double product = scaled * double(s32(height));
    uint32_t inset = run.call_x87(0x4a30e0, 0, product);
    uint32_t rectangle = run.automatic(-0x10);
    run.put(rectangle + 0x00, 0);
    run.put(rectangle + 0x04, inset);
    run.put(rectangle + 0x08, width - 1);
    run.put(rectangle + 0x0c, height - inset - 1);
    if (s32(layout) >= 10)
        run.icall(0x546d5c, {rectangle, 0, 0, width - 1, height - 1});
    run.call(0x4cb960, run.get(run.get(app + 0x30) + 0x24), {rectangle});
    uint32_t left = run.get(rectangle + 0x00);
    uint32_t top = run.get(rectangle + 0x04);
    uint32_t right = run.get(rectangle + 0x08);
    run.put(0x5370c8, left);
    uint32_t bottom = run.get(rectangle + 0x0c);
    run.put(0x5370cc, top);
    run.put(0x5370d4, bottom);
    run.put(0x5370d0, right);
    if (present) {
        clearPair(run, app, 0x20);
        clearPair(run, app, 0x20);
    }
    run.put(app + 0x6c, 2);
}

// 0x429eb0.
void function_429eb0(Run &run, uint32_t app, uint32_t deferred) {
    run.put(app + 0x6c, 2);
    if (!deferred) {
        uint32_t layout = run.get(app + 0x68);
        Frame frame(run, 0x10);
        function_429ed0(run, app, layout, 1, 1);
    }
}

// 0x42ae70. World +0xc8..+0xdc stores three camera threshold pairs.
void function_42ae70(Run &run, uint32_t app) {
    uint32_t scene = run.get(app + 0x30);
    if (!scene)
        return;
    uint32_t manager = run.get(scene + 0x04);
    uint32_t world = run.get(scene + 0x24);
    uint32_t front = run.get(manager + 0x10);
    uint32_t width = run.get(front + 0x10);
    uint32_t height = run.get(front + 0x14);
    float roundedWidth = float(s32(width));
    uint32_t x = run.call_x87(0x4a30e0, 0, double(s32(width)) * double(run.getf(0x50c350)));
    run.put(world + 0xc8, x);
    float roundedHeight = float(s32(height));
    uint32_t y = run.call_x87(0x4a30e0, 0, double(s32(height)) * double(run.getf(0x50c350)));
    run.put(world + 0xcc, y);
    run.call(0x4cdca0, world);
    for (uint32_t pair = 0; pair < 2; ++pair) {
        scene = run.get(app + 0x30);
        double productX = double(roundedWidth) * double(run.getf(0x50c354 + pair * 4));
        world = run.get(scene + 0x24);
        x = run.call_x87(0x4a30e0, 0, productX);
        double productY = double(roundedHeight) * double(run.getf(0x50c354 + pair * 4));
        run.put(world + 0xd0 + pair * 8, x);
        y = run.call_x87(0x4a30e0, 0, productY);
        run.put(world + 0xd4 + pair * 8, y);
        run.call(0x4cdca0, world);
    }
}

// 0x42a060. Scene +0x18 owns image slot +0x64; image +0x10 is palette.
// Application +0x78 depth, +0x7c/+0x80 display size, +0x84/+0x88 gameplay size.
uint32_t function_42a060(Run &run, uint32_t app, uint32_t width, uint32_t height) {
    uint32_t scene = run.get(app + 0x30);
    if (!scene)
        return 0;
    uint32_t image = run.get(run.get(scene + 0x18) + 0x64);
    if (image) {
        run.call(0x4bb870, run.get(image + 0x10));
        run.call(0x42d590, run.get(image + 0x10), {0, 0, 0, 250});
        clearPair(run, app, 0x94);
        clearPair(run, app, 0x94);
    }
    scene = run.get(app + 0x30);
    uint32_t front = run.get(run.get(scene + 0x04) + 0x10);
    bool changed = width != run.get(front + 0x10);
    if (height != run.get(front + 0x14))
        changed = true;
    uint32_t result = run.call(0x4cf020, scene, {width, height, run.get(app + 0x78)});
    if (!result) {
        if (image) {
            uint32_t palette = run.get(image + 0x10);
            run.call(0x4bbd90, palette, {0, 256, run.get(palette + 0x10), 250});
        }
        return 0;
    }
    if (image) {
        run.put(run.get(run.get(app + 0x30) + 0x18) + 0x64, image);
        run.vcall(image, 0x34);
        run.call(0x4bb8c0, run.get(image + 0x10), {0});
    }
    uint32_t state = run.get(app + 0x2c);
    run.put(app + 0x7c, width);
    run.put(app + 0x80, height);
    uint32_t type = run.vcall(state, 0x10);
    if (type == 3 || run.vcall(run.get(app + 0x2c), 0x10) == 4) {
        run.put(app + 0x84, width);
        run.put(app + 0x88, height);
    }
    if (changed) {
        clearPair(run, app, 0x94);
        clearPair(run, app, 0x94);
        Frame frame(run, 0x9c);
        function_429eb0(run, app, 0);
    }
    function_42ae70(run, app);
    run.call(0x42abf0, app);
    if (run.get(0x537268)) {
        run.put(0x537268, 0);
        uint32_t depth = run.get(app + 0x78);
        uint32_t liveHeight = run.get(app + 0x80);
        uint32_t liveWidth = run.get(app + 0x7c);
        uint32_t buffer = run.automatic(-0x80);
        run.call(0x4a3920, 0, {buffer, 0x525e1c, liveWidth, liveHeight, depth});
        run.call(0x42af70, app, {buffer});
    }
    return 1;
}

// 0x42a000.
uint32_t function_42a000(Run &run, uint32_t app, uint32_t force) {
    if (force || run.get(app + 0x7c) != 0x280 || run.get(app + 0x80) != 0x1e0) {
        uint32_t result;
        {
            Frame frame(run, 0x10);
            result = function_42a060(run, app, 0x280, 0x1e0);
        }
        if (!result) {
            function_429e10(run, app, 0x8008, 0x403);
            return 0;
        }
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x425640:
        return function_425640(run, receiver);
    case 0x429e10:
        function_429e10(run, receiver, arguments[0], arguments[1]);
        return 0;
    case 0x429eb0:
        function_429eb0(run, receiver, arguments[0]);
        return 0;
    case 0x429ed0:
        function_429ed0(run, receiver, arguments[0], arguments[1], arguments[2]);
        return 0;
    case 0x42a000:
        return function_42a000(run, receiver, arguments[0]);
    case 0x42a060:
        return function_42a060(run, receiver, arguments[0], arguments[1]);
    case 0x42ae70:
        function_42ae70(run, receiver);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_menu_application_entry, owned, body)
