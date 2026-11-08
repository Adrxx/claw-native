// Palette filename and embedded-resource loader chain, translated from v1.0.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x4d6560:
    case 0x4bca40:
        return 2;
    case 0x4bb180:
    case 0x4bb740:
    case 0x4bb2f0:
    case 0x4bb470:
    case 0x4bb620:
        return 3;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// Each physical CALL descends below the caller's saves, locals and arguments.
struct Frame {
    Run &run;
    uint32_t parent;
    uint32_t outgoing;
    Frame(Run &run, uint32_t entry) : run(run), parent(run.frame), outgoing(run.stackPointer) {
        run.frame = entry;
    }
    ~Frame() {
        run.frame = parent;
        run.stackPointer = outgoing;
    }
};

uint32_t original(Run &run, int32_t offset, uint32_t function, uint32_t receiver,
                  std::initializer_list<uint32_t> arguments = {}) {
    run.stackPointer = run.automatic(offset);
    return run.call(function, receiver, arguments);
}

uint32_t nested(Run &run, int32_t offset, uint32_t returnPC, uint32_t function,
                uint32_t receiver, std::initializer_list<uint32_t> arguments) {
    Frame frame(run, run.automatic(offset));
    run.put(run.frame, returnPC);
    uint32_t index = 0;
    uint32_t values[3]{};
    for (uint32_t argument : arguments) {
        values[index++] = argument;
    }
    return body(run, function, receiver, values);
}

// The original loops load and store channels in this order, including aliases.
void expandRGB(Run &run, uint32_t source, uint32_t destination) {
    for (uint32_t index = 0; index < 0x100; ++index) {
        uint8_t red = run.get8(source++);
        run.put8(destination, red);
        uint8_t green = run.get8(source++);
        run.put8(destination + 0x01, green);
        uint8_t blue = run.get8(source++);
        run.put8(destination + 0x02, blue);
        run.put8(destination + 0x03, 0);
        destination += 0x04;
    }
}

// 0x4d6560. Resource +0xc context, +0x10 backend, +0x08 flags.
uint32_t loadNamed(Run &run, uint32_t receiver) {
    uint32_t name = run.get(run.automatic(0x04));
    uint32_t manager = run.get(run.get(receiver + 0x0c) + 0x1c);
    uint32_t palette = nested(run, -0x10, 0x4d6575, 0x4bca40, manager, {name, 0x44});
    run.put(receiver + 0x10, palette);
    if (!palette) {
        return 0;
    }
    if (run.get8(run.automatic(0x08)) & 1) {
        run.put(receiver + 0x08, run.get(receiver + 0x08) | 1);
        original(run, -0x08, 0x4bbf60, palette);
    }
    return 1;
}

// 0x4bca40. Manager +0x00 holds DirectDraw; preserve uninitialized palette gaps.
uint32_t createNamed(Run &run, uint32_t receiver) {
    uint32_t palette = original(run, -0x14, 0x4f63ec, 0, {0x38});
    if (palette) {
        run.put(palette + 0x04, 0);
        run.put(palette + 0x00, 0);
        run.put(palette + 0x08, 0);
        run.put(palette + 0x0c, 0);
        run.put(palette + 0x10, 0);
        run.put(palette + 0x34, 0);
        run.put(palette + 0x18, 0);
        run.put(palette + 0x14, 0);
        run.put(palette + 0x2c, 0);
        run.put(palette + 0x30, 0);
    }
    uint32_t flags = run.get(run.automatic(0x08));
    uint32_t name = run.get(run.automatic(0x04));
    uint32_t directDraw = run.get(receiver + 0x00);
    uint32_t result = nested(run, -0x1c, 0x4bca8c, 0x4bb180, palette, {directDraw, name, flags});
    if (!result) {
        if (palette) {
            original(run, -0x10, 0x4bb2a0, palette);
            original(run, -0x14, 0x4f6428, 0, {palette});
        }
        return 0;
    }
    original(run, -0x14, 0x4bc9b0, receiver, {palette});
    return palette;
}

// 0x4bb180. strrchr and all extension comparisons remain physical originals.
uint32_t loadByExtension(Run &run, uint32_t receiver) {
    uint32_t name = run.get(run.automatic(0x08));
    uint32_t extension = original(run, -0x18, 0x4ad460, 0, {name, 0x2e});
    uint32_t loader = 0x4bb740;
    uint32_t returnPC = 0x4bb236;
    if (extension) {
        if (!original(run, -0x18, 0x4a3cf0, 0, {extension, 0x5324f8})) {
            loader = 0x4bb2f0;
            returnPC = 0x4bb1c2;
        } else if (!original(run, -0x18, 0x4a3cf0, 0, {extension, 0x5324f0})) {
            loader = 0x4bb470;
            returnPC = 0x4bb1f0;
        } else if (!original(run, -0x18, 0x4a3cf0, 0, {extension, 0x53250c})) {
            loader = 0x4bb620;
            returnPC = 0x4bb21e;
        }
    }
    uint32_t flags = run.get(run.automatic(0x0c));
    uint32_t directDraw = run.get(run.automatic(0x04));
    return nested(run, -0x1c, returnPC, loader, receiver, {directDraw, name, flags});
}

// 0x4bb740. RGB0 local occupies entry-0x400 through entry-1.
uint32_t loadEmbedded(Run &run, uint32_t receiver) {
    uint32_t name = run.get(run.automatic(0x08));
    uint32_t found = original(run, -0x41c, 0x546ac8, 0, {run.get(0x541390), name, 0x532514});
    if (!found) {
        return 0;
    }
    uint32_t loaded = original(run, -0x418, 0x546acc, 0, {run.get(0x541390), found});
    if (!loaded) {
        return 0;
    }
    uint32_t source = original(run, -0x414, 0x546ac4, 0, {loaded});
    if (!source) {
        return 0;
    }
    uint32_t converted = run.automatic(-0x400);
    expandRGB(run, source, converted);
    uint32_t flags = run.get(run.automatic(0x0c));
    uint32_t directDraw = run.get(run.automatic(0x04));
    return original(run, -0x41c, 0x4bb100, receiver, {directDraw, converted, flags});
}

// 0x4bb2f0. The 0x428-byte second read overlaps the third read buffer.
uint32_t loadBMP(Run &run, uint32_t receiver) {
    uint32_t file = run.automatic(-0x854);
    original(run, -0x860, 0x4f72c9, file);
    uint32_t name = run.get(run.automatic(0x08));
    run.put(run.automatic(-0x04), 0);
    uint32_t result = 0;
    if (original(run, -0x86c, 0x4f7448, file, {name, 0, 0}) &&
        original(run, -0x868, 0x4f7570, file, {run.automatic(-0x844), 0x0e}) == 0x0e &&
        original(run, -0x868, 0x4f7570, file, {run.automatic(-0x434), 0x428}) == 0x428 &&
        original(run, -0x868, 0x4f7570, file, {run.automatic(-0x40c), 0x400}) == 0x400) {
        uint32_t source = run.automatic(-0x40c);
        uint32_t converted = run.automatic(-0x834);
        for (uint32_t index = 0; index < 0x400; index += 0x04) {
            uint8_t red = run.get8(source + index + 0x02);
            uint8_t green = run.get8(source + index + 0x01);
            run.put8(converted + index, red);
            uint8_t blue = run.get8(source + index);
            run.put8(converted + index + 0x01, green);
            run.put8(converted + index + 0x02, blue);
            run.put8(converted + index + 0x03, 0);
        }
        uint32_t flags = run.get(run.automatic(0x0c));
        uint32_t directDraw = run.get(run.automatic(0x04));
        result = original(run, -0x86c, 0x4bb100, receiver, {directDraw, converted, flags});
    }
    run.put(run.automatic(-0x04), 0xffffffff);
    original(run, -0x860, 0x4f7369, file);
    return result;
}

// 0x4bb470 and 0x4bb620. Physical CFile calls, with PCX's ignored seek result.
uint32_t loadTriplets(Run &run, uint32_t receiver, bool pcx) {
    uint32_t file = run.automatic(-0x71c);
    original(run, -0x72c, 0x4f72c9, file);
    uint32_t name = run.get(run.automatic(0x08));
    run.put(run.automatic(-0x04), 0);
    uint32_t result = 0;
    if (original(run, -0x738, 0x4f7448, file, {name, 0, 0})) {
        if (pcx) {
            original(run, -0x734, 0x4f75f5, file, {0xfffffd00, 2});
        }
        uint32_t source = run.automatic(-0x70c);
        if (original(run, -0x734, 0x4f7570, file, {source, 0x300}) == 0x300) {
            uint32_t converted = run.automatic(-0x40c);
            expandRGB(run, source, converted);
            uint32_t flags = run.get(run.automatic(0x0c));
            uint32_t directDraw = run.get(run.automatic(0x04));
            result = original(run, -0x738, 0x4bb100, receiver, {directDraw, converted, flags});
        }
    }
    run.put(run.automatic(-0x04), 0xffffffff);
    original(run, -0x72c, 0x4f7369, file);
    return result;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    for (int index = 0; index < owned(function); ++index) {
        run.put(run.automatic(0x04 + 4 * index), arguments[index]);
    }
    switch (function) {
    case 0x4d6560:
        return loadNamed(run, receiver);
    case 0x4bca40:
        return createNamed(run, receiver);
    case 0x4bb180:
        return loadByExtension(run, receiver);
    case 0x4bb740:
        return loadEmbedded(run, receiver);
    case 0x4bb2f0:
        return loadBMP(run, receiver);
    case 0x4bb470:
        return loadTriplets(run, receiver, true);
    case 0x4bb620:
        return loadTriplets(run, receiver, false);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_palette_named_loader_entry, owned, body)
