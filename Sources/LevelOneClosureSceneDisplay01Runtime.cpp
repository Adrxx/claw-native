// Level 1 closure: Scene display helpers
//
// Nine thiscall functions of the bitmap surface wrapper: row copy, clear,
// the BMP/PCX/PID/resource loaders and the loader that picks one by extension.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b9b00:
        return 2;
    case 0x4b9bd0:
        return 1;
    case 0x4bc960:
        return 5;
    case 0x4bdad0:
        return 4;
    case 0x4bdc40:
        return 3;
    case 0x4be050:
        return 3;
    case 0x4bea60:
        return 3;
    case 0x4bf540:
        return 4;
    case 0x4bfa70:
        return 4;
    default:
        return -1;
    }
}

// Wrapper fields used here: +0x08 DirectDraw surface interface, +0x14 height
// (signed), +0x1c pitch in bytes, +0xa8 bytes per row to copy.
// Globals: 0x541390 module handle, 0x5413b0 palette table (256 entries of 4 bytes).

// Records the callee-entry ESP of the next outside call: this function's entry
// ESP minus `bytes` (its pushes, the pushed arguments and the return word).
void atDepth(Run &run, uint32_t bytes) {
    run.stackPointer = run.frame - bytes;
}

// 0x4b9b00. thiscall, 2 stack arguments: source pixels, mode. Copies the source
// into the locked surface one row at a time, bottom row first when mode is 2.
// Returns 1, or 0 when the surface cannot be locked.
uint32_t copyRows(Run &run, uint32_t receiver, uint32_t source, uint32_t mode) {
    atDepth(run, 0x10);
    uint32_t pixels = run.call(0x4b9730, receiver, {0});
    if (!pixels)
        return 0;
    if (mode == 2) {
        int32_t row = s32(run.get(receiver + 0x14)) - 1;
        while (row >= 0) {
            uint32_t destination = uint32_t(row) * run.get(receiver + 0x1c) + pixels;
            int32_t count = s32(run.get(receiver + 0xa8));
            uint32_t from = source;
            while (count > 0) {
                run.put8(destination, run.get8(from));
                destination += 1;
                from += 1;
                count -= 1;
            }
            source += run.get(receiver + 0xa8);
            row -= 1;
        }
    } else {
        uint32_t row = 0;
        if (s32(run.get(receiver + 0x14)) > 0) {
            do {
                uint32_t destination = row * run.get(receiver + 0x1c) + pixels;
                int32_t count = s32(run.get(receiver + 0xa8));
                uint32_t from = source;
                while (count > 0) {
                    run.put8(destination, run.get8(from));
                    destination += 1;
                    from += 1;
                    count -= 1;
                }
                source += run.get(receiver + 0xa8);
                row += 1;
            } while (s32(row) < s32(run.get(receiver + 0x14)));
        }
    }
    uint32_t interface = run.get(receiver + 0x08);
    uint32_t method = run.get(run.get(interface) + 0x80);
    atDepth(run, 0x20);
    run.call(method, 0, {interface, 0});
    return 1;
}

// 0x4b9bd0. thiscall, 1 stack argument: flag. Fills the surface through Blt
// with a colour-fill descriptor, then sets the colour key to 0xff or 0.
void clearSurface(Run &run, uint32_t receiver, uint32_t flag) {
    uint32_t descriptor = run.automatic(-0x64);
    for (uint32_t i = 0; i < 0x19; ++i)
        run.put(descriptor + i * 4, 0);
    uint32_t fill = 0;
    if (flag)
        fill = 0xff0020;
    run.put(descriptor + 0x8, fill + 0x42);
    run.put(descriptor + 0x0, 0x64);
    uint32_t interface = run.get(receiver + 0x08);
    uint32_t method = run.get(run.get(interface) + 0x14);
    atDepth(run, 0x88);
    uint32_t result = run.call(method, 0, {interface, 0, 0, 0, 0x1020000, descriptor});
    if (result) {
        if (flag) {
            atDepth(run, 0x74);
            run.call(0x4b97c0, receiver, {0xff});
            return;
        }
        atDepth(run, 0x74);
        run.call(0x4b97c0, receiver, {0});
    }
}

// 0x4bc960. thiscall, 5 stack arguments. Forwards to 0x4bc670 with 0x840 or-ed
// into the fourth argument.
void createWithFlags(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t flags = arguments[3] | 0x840;
    atDepth(run, 0x18);
    run.call(0x4bc670, receiver, {arguments[0], arguments[1], arguments[2], flags, arguments[4]});
}

// 0x4bdad0. thiscall, 4 stack arguments: target object, BMP image, size (unused),
// extra. Image fields: +0x0a pixel data offset, +0x12 width, +0x16 height,
// +0x1c bits per pixel. Target fields: +0x474 depth, +0x478 palette, +0x878 palette flag.
uint32_t bitmapFromImage(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t target = arguments[0];
    uint32_t image = arguments[1];
    uint32_t extra = arguments[3];
    uint32_t depth = run.get16(image + 0x1c);
    uint32_t width = run.get(image + 0x12);
    uint32_t height = run.get(image + 0x16);
    if (depth != 8 && depth != 0x18)
        return 0;
    uint32_t differs = 0;
    uint32_t targetDepth = run.get(target + 0x474);
    if (targetDepth != depth)
        differs = 1;
    if (differs && targetDepth == 8) {
        if (run.get(target + 0x878) == 0)
            return 0;
    }
    uint32_t palette = 0;
    if (differs) {
        if (depth == 8) {
            uint32_t table = 0x5413b0;
            uint32_t entry = image + 0x37;
            do {
                run.put8(table, run.get8(entry + 1));
                run.put8(table + 1, run.get8(entry));
                run.put8(table + 2, run.get8(entry - 1));
                run.put8(table + 3, 0);
                entry += 4;
                table += 4;
            } while (s32(table) < s32(0x5417b0));
            palette = 0x5413b0;
        } else if (targetDepth == 8) {
            if (run.get(target + 0x878) != 0)
                palette = target + 0x478;
            else
                palette = 0;
        }
    }
    atDepth(run, 0x38);
    uint32_t created = run.call(0x4b9180, receiver, {target, width, height, 0, extra});
    if (!created)
        return 0;
    uint32_t pixels = run.get(image + 0xa) + image;
    if (differs) {
        atDepth(run, 0x34);
        uint32_t converted = run.call(0x4b9e90, receiver, {pixels, depth, palette, 2});
        if (!converted)
            return 0;
    } else {
        uint32_t entry = run.frame;
        run.frame = entry - 0x2c;
        uint32_t copied = copyRows(run, receiver, pixels, 2);
        run.frame = entry;
        if (!copied)
            return 0;
    }
    return 1;
}

// 0x4bdc40. thiscall, 3 stack arguments: target, BMP file name, extra. Reads the
// whole file into a buffer and hands it to 0x4bdad0.
uint32_t loadBitmapFile(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // The file reader object is the local at entry ESP - 0x1c.
    uint32_t reader = run.automatic(-0x1c);
    atDepth(run, 0x2c);
    run.call(0x4f72c9, reader);
    atDepth(run, 0x38);
    uint32_t opened = run.call(0x4f7448, reader, {arguments[1], 0, 0});
    if (!opened) {
        atDepth(run, 0x2c);
        run.call(0x4f7369, reader);
        return 0;
    }
    atDepth(run, 0x2c);
    uint32_t size = run.call(0x4f774d, reader);
    if (!size) {
        atDepth(run, 0x2c);
        run.call(0x4f7369, reader);
        return 0;
    }
    atDepth(run, 0x30);
    uint32_t buffer = run.call(0x4f63ec, 0, {size});
    if (!buffer) {
        atDepth(run, 0x2c);
        run.call(0x4f7369, reader);
        return 0;
    }
    atDepth(run, 0x34);
    uint32_t count = run.call(0x4f7570, reader, {buffer, size});
    if (count != size) {
        atDepth(run, 0x30);
        run.call(0x4f6428, 0, {buffer});
        atDepth(run, 0x2c);
        run.call(0x4f7369, reader);
        return 0;
    }
    uint32_t inner[4] = {arguments[0], buffer, size, arguments[2]};
    uint32_t entry = run.frame;
    run.frame = entry - 0x3c;
    uint32_t result = bitmapFromImage(run, receiver, inner);
    run.frame = entry;
    atDepth(run, 0x30);
    run.call(0x4f6428, 0, {buffer});
    atDepth(run, 0x2c);
    run.call(0x4f7369, reader);
    return result;
}

// 0x4be050. thiscall, 3 stack arguments: target, resource name, extra. Loads an
// 8-bit bitmap resource of type 2 (RT_BITMAP) from the module and copies it.
// Resource fields: +0x00 pixel offset, +0x04 width, +0x08 height, +0x0e bits per pixel.
uint32_t loadBitmapResource(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t name = arguments[1];
    uint32_t module = run.get(0x541390);
    atDepth(run, 0x20);
    uint32_t found = run.icall(0x546ac8, {module, name, 2});
    if (!found)
        return 0;
    module = run.get(0x541390);
    atDepth(run, 0x1c);
    uint32_t loaded = run.icall(0x546acc, {module, found});
    if (!loaded)
        return 0;
    atDepth(run, 0x18);
    uint32_t resource = run.icall(0x546ac4, {loaded});
    if (!resource)
        return 0;
    uint32_t height = run.get(resource + 0x8);
    uint32_t depth = run.get16(resource + 0xe);
    uint32_t width = run.get(resource + 0x4);
    if (depth != 8)
        return 0;
    // Surface description: 0x6c bytes at +0x0c.
    for (uint32_t i = 0; i < 0x1b; ++i)
        run.put(receiver + 0xc + i * 4, 0);
    run.put(receiver + 0xc, 0x6c);
    run.put(receiver + 0x74, arguments[2] | 0x40);
    run.put(receiver + 0x10, 7);
    run.put(receiver + 0x18, width);
    run.put(receiver + 0x14, height);
    atDepth(run, 0x1c);
    uint32_t created = run.call(0x4b9150, receiver, {arguments[0], 0});
    if (!created)
        return 0;
    uint32_t pixels = run.get(resource) + resource + 0x400;
    uint32_t entry = run.frame;
    run.frame = entry - 0x1c;
    copyRows(run, receiver, pixels, 2);
    run.frame = entry;
    return 1;
}

// 0x4bea60. thiscall, 3 stack arguments: target, PCX file name, output pointer.
// Same shape as the BMP loader, handing the buffer to 0x4be810.
uint32_t loadPcxFile(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t reader = run.automatic(-0x1c);
    atDepth(run, 0x2c);
    run.call(0x4f72c9, reader);
    atDepth(run, 0x38);
    uint32_t opened = run.call(0x4f7448, reader, {arguments[1], 0, 0});
    if (!opened) {
        atDepth(run, 0x2c);
        run.call(0x4f7369, reader);
        return 0;
    }
    atDepth(run, 0x2c);
    uint32_t size = run.call(0x4f774d, reader);
    if (!size) {
        atDepth(run, 0x2c);
        run.call(0x4f7369, reader);
        return 0;
    }
    atDepth(run, 0x30);
    uint32_t buffer = run.call(0x4f63ec, 0, {size});
    if (!buffer) {
        atDepth(run, 0x2c);
        run.call(0x4f7369, reader);
        return 0;
    }
    atDepth(run, 0x34);
    uint32_t count = run.call(0x4f7570, reader, {buffer, size});
    if (count != size) {
        atDepth(run, 0x30);
        run.call(0x4f6428, 0, {buffer});
        atDepth(run, 0x2c);
        run.call(0x4f7369, reader);
        return 0;
    }
    atDepth(run, 0x3c);
    uint32_t result = run.call(0x4be810, receiver, {arguments[0], buffer, size, arguments[2]});
    atDepth(run, 0x30);
    run.call(0x4f6428, 0, {buffer});
    atDepth(run, 0x2c);
    run.call(0x4f7369, reader);
    return result;
}

// 0x4bf540. thiscall, 4 stack arguments: target, PID file name, flags, extra.
// Unlike the other file loaders it does not reject an empty file.
uint32_t loadPidFile(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t reader = run.automatic(-0x1c);
    atDepth(run, 0x2c);
    run.call(0x4f72c9, reader);
    atDepth(run, 0x38);
    uint32_t opened = run.call(0x4f7448, reader, {arguments[1], 0, 0});
    if (!opened) {
        atDepth(run, 0x2c);
        run.call(0x4f7369, reader);
        return 0;
    }
    atDepth(run, 0x2c);
    uint32_t size = run.call(0x4f774d, reader);
    atDepth(run, 0x30);
    uint32_t buffer = run.call(0x4f63ec, 0, {size});
    if (!buffer) {
        atDepth(run, 0x2c);
        run.call(0x4f7369, reader);
        return 0;
    }
    atDepth(run, 0x34);
    uint32_t count = run.call(0x4f7570, reader, {buffer, size});
    if (count != size) {
        atDepth(run, 0x30);
        run.call(0x4f6428, 0, {buffer});
        atDepth(run, 0x2c);
        run.call(0x4f7369, reader);
        return 0;
    }
    atDepth(run, 0x40);
    uint32_t result = run.call(0x4bf310, receiver, {arguments[0], buffer, size, arguments[2], arguments[3]});
    atDepth(run, 0x30);
    run.call(0x4f6428, 0, {buffer});
    atDepth(run, 0x2c);
    run.call(0x4f7369, reader);
    return result;
}

// 0x4bfa70. thiscall, 4 stack arguments: target, file name, flags, palette slot
// (-1 for none). Chooses the loader from the file extension (compare against
// the strings at 0x5324f8, 0x5324f0, 0x5324e8), falling back to the resource
// loader, then applies the palette slot through 0x4b9990 unless the PID loader ran.
uint32_t loadByExtension(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t entry = run.frame;
    uint32_t target = arguments[0];
    uint32_t name = arguments[1];
    uint32_t flags = arguments[2] | 0x40;
    uint32_t slot = arguments[3];
    uint32_t applyPalette = 1;
    atDepth(run, 0x1c);
    uint32_t extension = run.call(0x4ad460, 0, {name, 0x2e});
    bool fallback = false;
    if (!extension) {
        fallback = true;
    atDepth(run, 0x1c);
    } else if (run.call(0x4a3cf0, 0, {extension, 0x5324f8}) == 0) {
        uint32_t inner[3] = {target, name, flags};
        run.frame = entry - 0x20;
        uint32_t loaded = loadBitmapFile(run, receiver, inner);
        run.frame = entry;
        if (!loaded)
            return 0;
    atDepth(run, 0x1c);
    } else if (run.call(0x4a3cf0, 0, {extension, 0x5324f0}) == 0) {
        uint32_t inner[3] = {target, name, flags};
        run.frame = entry - 0x20;
        uint32_t loaded = loadPcxFile(run, receiver, inner);
        run.frame = entry;
        if (!loaded)
            return 0;
    atDepth(run, 0x1c);
    } else if (run.call(0x4a3cf0, 0, {extension, 0x5324e8}) != 0) {
        fallback = true;
    } else {
        uint32_t inner[4] = {target, name, flags, slot};
        run.frame = entry - 0x24;
        uint32_t loaded = loadPidFile(run, receiver, inner);
        run.frame = entry;
        if (!loaded)
            return 0;
        applyPalette = 0;
    }
    if (fallback) {
        uint32_t inner[3] = {target, name, flags};
        uint32_t loaded = loadBitmapResource(run, receiver, inner);
        if (!loaded)
            return 0;
    }
    if (slot != 0xffffffffu && applyPalette) {
        atDepth(run, 0x18);
        run.call(0x4b9990, receiver, {slot});
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b9b00:
        return copyRows(run, receiver, arguments[0], arguments[1]);
    case 0x4b9bd0:
        clearSurface(run, receiver, arguments[0]);
        return 0;
    case 0x4bc960:
        createWithFlags(run, receiver, arguments);
        return 0;
    case 0x4bdad0:
        return bitmapFromImage(run, receiver, arguments);
    case 0x4bdc40:
        return loadBitmapFile(run, receiver, arguments);
    case 0x4be050:
        return loadBitmapResource(run, receiver, arguments);
    case 0x4bea60:
        return loadPcxFile(run, receiver, arguments);
    case 0x4bf540:
        return loadPidFile(run, receiver, arguments);
    case 0x4bfa70:
        return loadByExtension(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_closure_scene_display_01_entry, owned, body)
