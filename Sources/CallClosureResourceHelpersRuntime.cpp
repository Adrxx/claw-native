// Call closure archive image surface helpers
// Recovered from the hash-checked v1.0 instruction bodies.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b7550:
        return 0;
    case 0x4b76b0:
        return 0;
    case 0x4bdda0:
        return 3;
    case 0x4bfd80:
        return 1;
    case 0x4bc740:
        return 3;
    case 0x4b99d0:
        return 0;
    default:
        return -1;
    }
}

// Calls that expose stack locals retain the original callee-entry stack slot.
uint32_t callAt(Run &run, int32_t offset, uint32_t function, uint32_t receiver,
                std::initializer_list<uint32_t> arguments = {}) {
    uint32_t previous = run.stackPointer;
    run.stackPointer = run.automatic(offset);
    uint32_t result = run.call(function, receiver, arguments);
    run.stackPointer = previous;
    return result;
}

uint32_t length(Run &run, uint32_t text) {
    uint32_t count = 0;
    while (run.get8(text + count) != 0) {
        ++count;
    }
    return count;
}

void copyString(Run &run, uint32_t destination, uint32_t source) {
    uint32_t count = length(run, source) + 1;
    for (uint32_t i = 0; i < count; ++i) {
        run.put8(destination + i, run.get8(source + i));
    }
}

void appendString(Run &run, uint32_t destination, uint32_t source) {
    copyString(run, destination + length(run, destination), source);
}

// 0x4b7550. Archive +0x20 read-only flag; +0x24 directory tree.
uint32_t function_4b7550(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x20) != 0) {
        return 0;
    }
    uint32_t oldLength = run.get(receiver + 0x1c);
    callAt(run, -0xc8, 0x4b6bd0, run.get(receiver + 0x24), {receiver + 0x10, receiver + 0x14});
    uint32_t header = run.automatic(-0xa8);
    run.put8(header, 13);
    run.put8(header + 0x3e, 13);
    run.put8(header + 0x7c, 13);
    run.put8(header + 0x01, 10);
    run.put8(header + 0x3f, 10);
    run.put8(header + 0x7d, 10);
    run.put8(header + 0x7e, 0x1a);
    for (uint32_t i = 0; i < 0x3c; i += 4) {
        run.put(header + 0x02 + i, 0x20202020);
    }
    copyString(run, header + 0x02, 0x532480);
    uint32_t treeLength = run.get(receiver + 0x14);
    run.put8(header + 0x02 + length(run, header + 0x02), 0x20);
    for (uint32_t i = 0; i < 0x3c; i += 4) {
        run.put(header + 0x40 + i, 0x20202020);
    }
    run.put(header + 0x87, treeLength);
    run.put(header + 0x83, run.get(receiver + 0x10));
    run.put(header + 0x93, run.get(receiver + 0x28));
    run.put(header + 0x8f, oldLength);
    run.put(header + 0x8b, run.get(receiver + 0x18));
    run.put(header + 0x9f, run.get(receiver + 0x3c));
    run.put(header + 0x9b, run.get(receiver + 0x38));
    run.put(header + 0x97, run.get(receiver + 0x34));
    run.put8(header + 0xa7, run.get8(receiver + 0x04));
    run.put(header + 0x7f, 1);
    run.put(header + 0xa3, run.get(receiver + 0x40));
    callAt(run, -0xcc, 0x4b7b40, receiver, {0, 0xa8, header});
    callAt(run, -0xc0, 0x4b7c80, receiver);
    return 1;
}

// 0x4b76b0. Archive +0x04 mode and +0x44 original pathname.
uint32_t function_4b76b0(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x04) != 0) {
        return 1;
    }
    uint32_t original = callAt(run, -0x384, 0x4f63ec, 0, {length(run, run.get(receiver + 0x44) + 1)});
    copyString(run, original, run.get(receiver + 0x44));
    uint32_t drive = run.automatic(-0x36c);
    uint32_t directory = run.automatic(-0x318);
    uint32_t name = run.automatic(-0x214);
    uint32_t extension = run.automatic(-0x110);
    callAt(run, -0x394, 0x4a6a90, 0, {run.get(receiver + 0x44), drive, directory, name, extension});
    uint32_t temporary = callAt(run, -0x384, 0x4f63ec, 0, {length(run, run.get(receiver + 0x44)) + 16});
    copyString(run, temporary, drive);
    appendString(run, temporary, directory);
    appendString(run, temporary, 0x5324bc);
    uint32_t backup = callAt(run, -0x384, 0x4f63ec, 0, {length(run, run.get(receiver + 0x44)) + 16});
    copyString(run, backup, drive);
    appendString(run, backup, directory);
    appendString(run, backup, name);
    appendString(run, backup, 0x5324b4);
    uint32_t archive = run.automatic(-0x360);
    callAt(run, -0x380, 0x4b7210, archive);
    callAt(run, -0x38c, 0x4b72e0, archive, {temporary, 0, 1});
    callAt(run, -0x388, 0x4b7950, receiver, {run.get(archive + 0x24), run.get(receiver + 0x24)});
    run.put(archive + 0x04, 1);
    callAt(run, -0x384, 0x4b74d0, archive, {0});
    if (callAt(run, -0x380, 0x4b7c40, receiver) != 0) {
        callAt(run, -0x384, 0x4f1df0, 0, {backup});
        callAt(run, -0x388, 0x4f1db0, 0, {original, backup});
        callAt(run, -0x388, 0x4f1db0, 0, {temporary, original});
        callAt(run, -0x384, 0x4f6428, 0, {temporary});
        callAt(run, -0x384, 0x4f6428, 0, {original});
        callAt(run, -0x384, 0x4f6428, 0, {backup});
    }
    callAt(run, -0x380, 0x4b7250, archive);
    return 0;
}

// 0x4bdda0. Surface +0x18 width, +0x14 height; bitmap BGR palette.
uint32_t function_4bdda0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t context = arguments[0];
    uint32_t bitmap = arguments[1];
    uint32_t depth = run.get16(bitmap + 0x1c);
    if (run.get(receiver + 0x18) != run.get(bitmap + 0x12) ||
        run.get(receiver + 0x14) != run.get(bitmap + 0x16) || (depth != 8 && depth != 24)) {
        return 0;
    }
    uint32_t contextDepth = run.get(context + 0x474);
    bool conversion = contextDepth != depth;
    if (conversion && contextDepth == 8 && run.get(context + 0x878) == 0) {
        return 0;
    }
    uint32_t palette = 0;
    if (conversion) {
        if (depth == 8) {
            for (uint32_t i = 0; i < 0x400; i += 4) {
                run.put8(0x5417b0 + i, run.get8(bitmap + 0x38 + i));
                run.put8(0x5417b1 + i, run.get8(bitmap + 0x37 + i));
                run.put8(0x5417b2 + i, run.get8(bitmap + 0x36 + i));
                run.put8(0x5417b3 + i, 0);
            }
            palette = 0x5417b0;
        } else if (contextDepth == 8 && run.get(context + 0x878) != 0) {
            palette = context + 0x478;
        }
    }
    uint32_t pixels = bitmap + run.get(bitmap + 0x0a);
    uint32_t result = conversion ? callAt(run, -0x2c, 0x4b9e90, receiver, {pixels, depth, palette, 2})
                                 : callAt(run, -0x24, 0x4b9b00, receiver, {pixels, 2});
    return result != 0 ? 1 : 0;
}

uint32_t shiftByteRight(uint32_t value, uint32_t count) {
    return (value & 0xff) >> (count & 31);
}

uint32_t shiftByteLeft(uint32_t value, uint32_t count) {
    return ((value & 0xff) << (count & 31)) & 0xff;
}

void appendByte(Run &run, uint32_t array, uint32_t value) {
    callAt(run, -0x58, 0x4f5c49, array, {run.get(array + 0x08), value});
}

// 0x4bfd80. Converts run tokens with the original byte-register shifts.
uint32_t function_4bfd80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t array = run.automatic(-0x20);
    callAt(run, -0x50, 0x4f5ade, array);
    uint32_t horizontal = 0;
    uint32_t row = 0;
    uint32_t offset = 0;
    while (s32(row) < s32(run.get(receiver + 0x08))) {
        uint32_t tokenAddress = arguments[0] + offset;
        uint32_t token = run.get8(tokenAddress);
        appendByte(run, array, token);
        if ((token & 0x80) != 0) {
            horizontal += run.get8(run.get(receiver + 0x0c) + offset) - 0x80;
            ++offset;
        } else {
            for (uint32_t index = 0; s32(index) < int32_t(run.get8(tokenAddress)); ++index) {
                uint32_t paletteOffset = uint32_t(run.get8(tokenAddress + index)) * 4;
                uint32_t palette = run.get(receiver + 0x20) + paletteOffset;
                uint32_t red = shiftByteRight(run.get8(palette), run.get8(0x541368));
                red = shiftByteLeft(red, run.get(0x54135c));
                uint32_t green = shiftByteRight(run.get8(palette + 0x01), run.get8(0x54136c));
                green = shiftByteLeft(green, run.get(0x541360));
                uint32_t blue = shiftByteRight(run.get8(palette + 0x02), run.get8(0x541370));
                appendByte(run, array, red | green | blue);
                palette = run.get(receiver + 0x20) + paletteOffset;
                green = shiftByteRight(run.get8(palette + 0x01), run.get8(0x54136c));
                green <<= run.get(0x541360) & 31;
                uint32_t greenHigh = (green >> 8) & 0xff;
                red = shiftByteRight(run.get8(palette), run.get8(0x541368));
                red <<= run.get(0x54135c) & 31;
                appendByte(run, array, greenHigh | ((red >> 8) & 0xff));
            }
            uint32_t runLength = run.get8(run.get(receiver + 0x0c) + offset);
            horizontal += runLength;
            offset += runLength + 1;
        }
        if (s32(horizontal) >= s32(run.get(receiver + 0x04) - 1)) {
            horizontal = 0;
            ++row;
        }
    }
    uint32_t output = callAt(run, -0x54, 0x4f63ec, 0, {run.get(array + 0x08)});
    for (uint32_t index = 0; s32(index) < s32(run.get(array + 0x08)); ++index) {
        run.put8(output + index, run.get8(run.get(array + 0x04) + index));
    }
    callAt(run, -0x50, 0x4f5b11, array);
    return output;
}

// 0x4bc740. Image-manager factory; image +0x90 embedded CPtrList.
uint32_t function_4bc740(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t image = callAt(run, -0x24, 0x4f63ec, 0, {0xbc});
    if (image != 0) {
        callAt(run, -0x20, 0x4f54ea, image + 0x90);
        run.put(image + 0x08, 0);
        run.put(image + 0x04, 0);
        run.put(image + 0x78, 0);
        run.put(image + 0xa4, 0);
        run.put(image + 0xb4, 0);
        run.put(image, 0x513690);
    }
    uint32_t method = run.get(run.get(image) + 0x28);
    uint32_t success = callAt(run, -0x30, method, image, {receiver, arguments[0], arguments[1], arguments[2]});
    if (success == 0) {
        if (image != 0) {
            callAt(run, -0x24, run.get(run.get(image)), image, {1});
        }
        return 0;
    }
    callAt(run, -0x24, 0x4bc490, receiver, {image});
    return image;
}

void unlock(Run &run, uint32_t receiver) {
    uint32_t surface = run.get(receiver + 0x08);
    callAt(run, -0x30, run.get(run.get(surface) + 0x80), 0, {surface, 0});
}

// 0x4b99d0. Surface +0x14 signed height, +0x18 row bytes, +0x1c pitch.
uint32_t function_4b99d0(Run &run, uint32_t receiver, const uint32_t *) {
    if (s32(run.get(receiver + 0x14)) <= 1) {
        return 0;
    }
    uint32_t pixels = callAt(run, -0x2c, 0x4b9730, receiver, {0});
    if (pixels == 0) {
        return 0;
    }
    uint32_t scratch = callAt(run, -0x2c, 0x4f63ec, 0, {run.get(receiver + 0x18)});
    if (scratch == 0) {
        unlock(run, receiver);
        return 0;
    }
    uint32_t height = run.get(receiver + 0x14);
    uint32_t width = run.get(receiver + 0x18);
    uint32_t half = uint32_t(s32(height) / 2);
    for (uint32_t row = 0; s32(row) < s32(half); ++row) {
        uint32_t top = pixels + row * run.get(receiver + 0x1c);
        for (uint32_t x = 0; s32(x) < s32(width); ++x) {
            run.put8(scratch + x, run.get8(top + x));
        }
        uint32_t pitch = run.get(receiver + 0x1c);
        uint32_t opposite = height - row - 1;
        top = pixels + row * pitch;
        uint32_t bottom = pixels + opposite * pitch;
        for (uint32_t x = 0; s32(x) < s32(width); ++x) {
            run.put8(top + x, run.get8(bottom + x));
        }
        bottom = pixels + opposite * run.get(receiver + 0x1c);
        for (uint32_t x = 0; s32(x) < s32(width); ++x) {
            run.put8(bottom + x, run.get8(scratch + x));
        }
    }
    unlock(run, receiver);
    callAt(run, -0x2c, 0x4f6428, 0, {scratch});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b7550:
        return function_4b7550(run, receiver, arguments);
    case 0x4b76b0:
        return function_4b76b0(run, receiver, arguments);
    case 0x4bdda0:
        return function_4bdda0(run, receiver, arguments);
    case 0x4bfd80:
        return function_4bfd80(run, receiver, arguments);
    case 0x4bc740:
        return function_4bc740(run, receiver, arguments);
    case 0x4b99d0:
        return function_4b99d0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_call_closure_resource_helpers_entry, owned, body)
