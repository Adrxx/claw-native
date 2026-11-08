// Cheat debug overlay toggles and resource closure
//
// Canonical implementation of the original v1.0 game entries.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x42c2d0:
        return 0;
    case 0x42c460:
        return 0;
    case 0x42c5c0:
        return 3;
    case 0x42c6f0:
        return 0;
    case 0x42c7d0:
        return 0;
    case 0x42c8e0:
        return 0;
    case 0x4cb880:
        return 7;
    case 0x4cbb00:
        return 1;
    case 0x4ce800:
        return 1;
    case 0x4d2710:
        return 1;
    default:
        return -1;
    }
}

// Controller +0x2c is the active state; +0x30 is the level context.
// Context +0x10 holds image resources, +0x24 layers, +0x28 sound resources.
bool inLevel(Run &run, uint32_t receiver) {
    uint32_t state = run.get(receiver + 0x2c);
    if (!state)
        return false;
    if (run.vcall(state, 0x10) != 3)
        return false;
    return run.get(receiver + 0x30) != 0;
}

uint32_t imageMap(Run &run, uint32_t receiver) {
    return run.get(run.get(receiver + 0x30) + 0x10) + 0x10;
}

uint32_t lookup(Run &run, uint32_t map, uint32_t name, uint32_t local) {
    run.put(local, 0);
    run.call(0x4f6286, map, {name, local});
    return run.get(local);
}

// Resource +0x14 holds frames, +0x64 and +0x68 are inclusive frame bounds.
uint32_t firstFrame(Run &run, uint32_t resource) {
    uint32_t index = run.get(resource + 0x64);
    uint32_t frames = run.get(resource + 0x14);
    return run.get(frames + index * 4);
}

void minorSound(Run &run, uint32_t receiver, uint32_t local) {
    uint32_t sounds = run.get(run.get(receiver + 0x30) + 0x28);
    if (run.get(sounds + 0x30))
        return;
    uint32_t resource = lookup(run, sounds + 0x10, 0x525b68, local);
    if (resource && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(resource + 0x10), {run.get(0x532c10), 0, 0, 0});
}

// 0x4d2710. Surface +0x2c is the raster, +0x30 an effect descriptor.
uint32_t function_4d2710(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[0];
    if (!source || run.get(source + 0x30))
        return 0;
    uint32_t raster = run.get(receiver + 0x2c);
    if (!raster || run.get(receiver + 0x30))
        return 0;
    if (run.get(receiver + 0x10) != run.get(source + 0x10))
        return 0;
    if (run.get(receiver + 0x14) != run.get(source + 0x14))
        return 0;
    uint32_t parentStack = run.stackPointer;
    run.stackPointer = run.frame - 0x10;
    run.call(0x4b97c0, raster, {0});
    run.stackPointer = parentStack;
    return run.call(0x4b9c50, run.get(receiver + 0x2c), {run.get(source + 0x2c)}) != 0;
}

// 0x4ce800. Effect +0x18 holds the selected color.
uint32_t function_4ce800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = run.get(receiver + 0x64);
    uint32_t end = run.get(receiver + 0x68);
    uint32_t count = 0;
    while (s32(index) <= s32(end)) {
        uint32_t frame = 0;
        if (s32(index) >= run.gets(receiver + 0x64) && s32(index) <= s32(end))
            frame = run.get(run.get(receiver + 0x14) + index * 4);
        if (frame) {
            uint32_t effect = run.get(frame + 0x30);
            if (effect) {
                run.put(effect + 0x18, arguments[0]);
                ++count;
            }
        }
        end = run.get(receiver + 0x68);
        ++index;
    }
    return count;
}

// 0x4cbb00. Layer manager +0x38 is its array and +0x3c the count.
// Layer +0xb4 contains the inline name.
uint32_t function_4cbb00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t count = run.get(receiver + 0x3c);
    uint32_t index = 0;
    if (s32(count) <= 0)
        return 0;
    do {
        uint32_t layer = 0;
        if (s32(index) >= 0 && s32(index) < s32(count))
            layer = run.get(run.get(receiver + 0x38) + index * 4);
        if (!run.call(0x4a3cf0, 0, {arguments[0], layer + 0xb4}))
            return layer;
        count = run.get(receiver + 0x3c);
        ++index;
    } while (s32(index) < s32(count));
    return 0;
}

// 0x4cb880. Manager +0x0c is the renderer; +0x34 its layer array.
// +0x5c/+0x60 track the active layer and its index.
uint32_t function_4cb880(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t allocation = run.call(0x4f63ec, 0, {0x158});
    uint32_t layer = 0;
    if (allocation) {
        uint32_t count = run.get(receiver + 0x3c);
        uint32_t renderer = run.get(receiver + 0x0c);
        uint32_t parentStack = run.stackPointer;
        run.stackPointer = run.frame - 0x28;
        layer = run.call(0x4d03b0, allocation, {renderer, count, 0});
        run.stackPointer = parentStack;
    }
    uint32_t parentStack = run.stackPointer;
    run.stackPointer = run.frame - 0x3c;
    uint32_t initialized = run.vcall(layer, 0x24, {arguments[0], arguments[1], arguments[2], arguments[3], arguments[4], arguments[5], receiver + 0x10, arguments[6]});
    run.stackPointer = parentStack;
    if (!initialized) {
        if (layer)
            run.vcall(layer, 0x04, {1});
        return 0;
    }
    run.call(0x4f582f, receiver + 0x34, {run.get(receiver + 0x3c), layer});
    if (run.get8(layer + 0x08) & 1) {
        run.put(receiver + 0x5c, layer);
        run.put(receiver + 0x60, run.get(receiver + 0x3c) - 1);
    }
    return layer;
}

// 0x42c5c0. The first argument slot doubles as the lookup output.
uint32_t function_42c5c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[0];
    if (!source || !arguments[1])
        return 0;
    uint32_t resource = lookup(run, imageMap(run, receiver), arguments[1], run.automatic(0x04));
    if (!resource)
        return 0;
    uint32_t target = firstFrame(run, resource);
    if (!target)
        return 0;
    uint32_t index = arguments[2];
    if (s32(index) < run.gets(source + 0x64) || s32(index) > run.gets(source + 0x68))
        return 0;
    uint32_t frame = run.get(run.get(source + 0x14) + index * 4);
    if (!frame)
        return 0;
    uint32_t copyArgs[] = {frame};
    uint32_t parentFrame = run.frame;
    run.frame -= 0x0c;
    function_4d2710(run, target, copyArgs);
    run.frame = parentFrame;
    return 1;
}

// 0x42c2d0. New layers use +0x20 cells, +0x24 row offsets,
// +0x28/+0x2c grid dimensions, +0x80 update rate, +0x9c resources.
uint32_t function_42c2d0(Run &run, uint32_t receiver, const uint32_t *) {
    if (!inLevel(run, receiver))
        return 0;
    uint32_t resource = lookup(run, imageMap(run, receiver), 0x525968, run.automatic(-0x08));
    if (!resource)
        return 0;
    uint32_t index = run.get(resource + 0x64);
    run.put(run.automatic(-0x04), index);
    uint32_t frame = run.get(run.get(resource + 0x14) + index * 4);
    if (!frame)
        return 0;
    uint32_t width = run.get(frame + 0x10);
    uint32_t height = run.get(frame + 0x14);
    uint32_t findArgs[] = {0x525948};
    uint32_t layer = function_4cbb00(run, run.get(run.get(receiver + 0x30) + 0x24), findArgs);
    if (layer) {
        uint32_t flags = run.get(layer + 0x08);
        if (!(flags & 2)) {
            run.put(layer + 0x08, flags | 2);
            run.put(0x537260, 0);
            return 1;
        }
        run.put(layer + 0x08, flags & ~2u);
    } else {
        uint32_t createArgs[] = {0x20, 0x20, width, height, 0xffffffe7, 0xffffffe7, 0x525948};
        uint32_t parentFrame = run.frame;
        run.frame -= 0x38;
        layer = function_4cb880(run, run.get(run.get(receiver + 0x30) + 0x24), createArgs);
        run.frame = parentFrame;
        if (!layer)
            return 0;
        run.call(0x4f582f, layer + 0x9c, {0, resource});
        uint32_t flags = run.get(layer + 0x08);
        uint32_t rows = run.get(layer + 0x2c);
        run.put(layer + 0x08, flags | 0x0c);
        run.put(layer + 0x80, 0x56ce);
        uint32_t parity = 1;
        for (uint32_t row = 0; s32(row) < s32(rows); ++row) {
            uint32_t columns = run.get(layer + 0x28);
            for (uint32_t column = 0; s32(column) < s32(columns); ++column) {
                uint32_t value = parity ? run.get(run.automatic(-0x04)) : 0xffffffff;
                uint32_t rowArray = run.get(layer + 0x24);
                uint32_t cells = run.get(layer + 0x20);
                uint32_t cell = run.get(rowArray + row * 4) + column;
                parity ^= 1;
                run.put(cells + cell * 4, value);
                columns = run.get(layer + 0x28);
            }
            rows = run.get(layer + 0x2c);
            parity ^= 1;
        }
    }
    run.put(0x537260, 1);
    return 1;
}

// 0x42c460. Every treasure replacement receives the same source resource.
uint32_t function_42c460(Run &run, uint32_t receiver, const uint32_t *) {
    if (!inLevel(run, receiver))
        return 0;
    uint32_t resource = lookup(run, imageMap(run, receiver), 0x52615c, run.automatic(-0x04));
    if (!resource)
        return 0;
    constexpr uint32_t names[] = {0x526140, 0x526124, 0x526108, 0x5260ec, 0x5260d0, 0x5260b0, 0x526094, 0x526074, 0x526058, 0x52603c, 0x526020, 0x526000, 0x525fe4, 0x525fc4, 0x525fa8, 0x525f88};
    for (uint32_t i = 0; i < 16; ++i) {
        uint32_t args[] = {resource, names[i], i < 8 ? 0u : (i < 12 ? 1u : 2u)};
        uint32_t parentFrame = run.frame;
        run.frame -= 0x1c;
        function_42c5c0(run, receiver, args);
        run.frame = parentFrame;
    }
    return 1;
}

// 0x42c6f0. Effect +0x14 selects the render mode.
uint32_t function_42c6f0(Run &run, uint32_t receiver, const uint32_t *) {
    if (!inLevel(run, receiver))
        return 0;
    uint32_t local = run.automatic(-0x04);
    uint32_t resource = lookup(run, imageMap(run, receiver), 0x523734, local);
    if (!resource)
        return 0;
    uint32_t frame = firstFrame(run, resource);
    if (!frame)
        return 0;
    uint32_t effect = run.get(frame + 0x30);
    if (!effect)
        return 0;
    bool off = run.get(effect + 0x14) == 2;
    run.call(0x4ce7b0, resource, {off ? 1u : 2u});
    run.call(0x42af70, receiver, {off ? 0x52616cu : 0x526180u});
    minorSound(run, receiver, local);
    return 0;
}

// 0x42c7d0. The signed remainder follows CDQ/XOR/SUB exactly.
uint32_t function_42c7d0(Run &run, uint32_t receiver, const uint32_t *) {
    if (!inLevel(run, receiver))
        return 0;
    uint32_t local = run.automatic(-0x04);
    uint32_t resource = lookup(run, imageMap(run, receiver), 0x523734, local);
    if (!resource)
        return 0;
    uint32_t frame = firstFrame(run, resource);
    if (!frame)
        return 0;
    uint32_t effect = run.get(frame + 0x30);
    if (!effect)
        return 0;
    bool off = run.get(effect + 0x14) == 4;
    run.call(0x4ce7b0, resource, {off ? 1u : 4u});
    if (!off) {
        uint32_t random = run.call(0x4a3050, 0);
        uint32_t sign = s32(random) < 0 ? 0xffffffff : 0;
        uint32_t color = (((random ^ sign) - sign) & 0xff) ^ sign;
        color -= sign;
        uint32_t colorArgs[] = {color};
        function_4ce800(run, resource, colorArgs);
    }
    run.call(0x42af70, receiver, {off ? 0x526198u : 0x5261b0u});
    minorSound(run, receiver, local);
    return 0;
}

// 0x42c8e0. The last eligible resource determines the final message.
uint32_t function_42c8e0(Run &run, uint32_t receiver, const uint32_t *) {
    if (!inLevel(run, receiver))
        return 0;
    uint32_t local = run.automatic(-0x18);
    uint32_t excluded = lookup(run, imageMap(run, receiver), 0x523734, local);
    if (!excluded)
        return 0;
    uint32_t map = imageMap(run, receiver);
    if (!map)
        return 0;
    uint32_t position = run.automatic(-0x10);
    uint32_t key = run.automatic(-0x14);
    run.put(position, run.get(map + 0x0c) ? 0xffffffff : 0);
    bool enabled = false;
    while (run.get(position)) {
        run.call(0x4f6439, key);
        run.put(local, 0);
        run.call(0x4f5e1e, map, {position, key, local});
        uint32_t resource = run.get(local);
        if (resource && resource != excluded) {
            uint32_t frame = firstFrame(run, resource);
            if (frame) {
                uint32_t effect = run.get(frame + 0x30);
                if (effect) {
                    enabled = run.get(effect + 0x14) != 2;
                    run.call(0x4ce7b0, resource, {enabled ? 2u : 1u});
                }
            }
        }
        run.call(0x4f6584, key);
    }
    run.call(0x42af70, receiver, {enabled ? 0x5261e8u : 0x5261c0u});
    minorSound(run, receiver, key);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42c2d0:
        return function_42c2d0(run, receiver, arguments);
    case 0x42c460:
        return function_42c460(run, receiver, arguments);
    case 0x42c5c0:
        return function_42c5c0(run, receiver, arguments);
    case 0x42c6f0:
        return function_42c6f0(run, receiver, arguments);
    case 0x42c7d0:
        return function_42c7d0(run, receiver, arguments);
    case 0x42c8e0:
        return function_42c8e0(run, receiver, arguments);
    case 0x4cb880:
        return function_4cb880(run, receiver, arguments);
    case 0x4cbb00:
        return function_4cbb00(run, receiver, arguments);
    case 0x4ce800:
        return function_4ce800(run, receiver, arguments);
    case 0x4d2710:
        return function_4d2710(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_cheat_debug_overlays_entry, owned, body)
