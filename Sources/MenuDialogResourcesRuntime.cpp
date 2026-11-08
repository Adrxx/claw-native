// Original popup dialog resource parsing and geometry.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4e1b20: return 2;
    case 0x4e2090: return 1;
    case 0x4e2160: return 1;
    case 0x4e21a0: return 1;
    case 0x4e25e0: return 0;
    case 0x4e2670: return 1;
    default: return -1;
    }
}

struct Frame {
    Run &run;
    uint32_t savedFrame;
    uint32_t savedStack;
    Frame(Run &run, uint32_t entry) : run(run), savedFrame(run.frame), savedStack(run.stackPointer) {
        run.frame = entry;
    }
    ~Frame() {
        run.frame = savedFrame;
        run.stackPointer = savedStack;
    }
};

uint32_t outside(Run &run, uint32_t base, uint32_t function, uint32_t receiver,
                 std::initializer_list<uint32_t> arguments = {}) {
    run.stackPointer = base - 4 - uint32_t(arguments.size()) * 4;
    return run.call(function, receiver, arguments);
}

void copyBytes(Run &run, uint32_t destination, uint32_t source, uint32_t size) {
    uint32_t index = 0;
    for (; index + 4 <= size; index += 4) {
        run.put(destination + index, run.get(source + index));
    }
    for (; index < size; ++index) {
        run.put8(destination + index, run.get8(source + index));
    }
}

// 0x4e2160. UTF16 word termination, low-byte narrowing, allocated return.
uint32_t function_4e2160(Run &run, uint32_t source) {
    uint32_t count = 0;
    while (run.get16(source + count * 2) != 0) {
        ++count;
    }
    uint32_t result = outside(run, run.frame - 4, 0x4f63ec, 0, {count + 1});
    count = 0;
    while (run.get16(source) != 0) {
        uint8_t value = run.get8(source);
        source += 2;
        run.put8(result + count, value);
        ++count;
    }
    run.put8(result + count, 0);
    return result;
}

uint32_t narrowAt(Run &run, uint32_t base, uint32_t source) {
    Frame frame(run, base - 8);
    return function_4e2160(run, source);
}

// 0x4e1b20. Embedded GDI/CDC/font objects and NONCLIENTMETRICS.
uint32_t function_4e1b20(Run &run, uint32_t receiver, uint32_t first, uint32_t second) {
    uint32_t base = run.frame - 0x1c;
    run.put(receiver + 0xd0, 0);
    run.put(receiver + 0xcc, 0x5141a8);
    outside(run, base, 0x4fcf35, receiver + 0xd4);
    run.put(receiver + 0xe8, 0);
    run.put(receiver + 0xe4, 0x5141a8);
    outside(run, base, 0x4fcf35, receiver + 0xec);
    run.put(receiver + 0x108, 0);
    run.put(receiver + 0x104, 0x5141a8);
    run.put(receiver + 0x110, 0);
    run.put(receiver + 0x10c, 0x514190);
    run.put(receiver + 0x118, 0);
    run.put(receiver + 0x114, 0x514190);
    run.put(receiver + 0x0, 0x513fc8);
    run.put(receiver + 0x4, 0);
    run.put(receiver + 0x8, first);
    run.put(receiver + 0xc, 0);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put16(receiver + 0x1c, 0);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x24, 0);
    run.put(receiver + 0x28, 0);
    run.put(receiver + 0x2c, 0);
    run.put(receiver + 0x30, 0);
    run.put16(receiver + 0x34, 0);
    run.put(receiver + 0x38, 0);
    run.put(receiver + 0x3c, 0);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0);
    run.put(receiver + 0x48, 0);
    run.put(receiver + 0x4c, 0);
    run.put(receiver + 0x50, second);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x5c, 0);
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x64, 0);
    run.put(receiver + 0x68, 0);
    outside(run, base, 0x546cdc, 0, {receiver + 0xbc});
    run.put(receiver + 0xfc, 0);
    run.put(receiver + 0x100, 0);
    run.put(receiver + 0x11c, 0);
    for (uint32_t offset = 0; offset < 0x154; offset += 4) {
        run.put(receiver + 0x120 + offset, 0);
    }
    run.put(receiver + 0x120, 0x154);
    outside(run, base, 0x546d04, 0, {0x29, 0, receiver + 0x120, 0});
    run.put(receiver + 0x274, 0);
    return receiver;
}

// 0x4e25e0. Font wrappers at +0x10c/+0x114, face at +0x38.
uint32_t function_4e25e0(Run &run, uint32_t receiver) {
    uint32_t base = run.frame - 0x10;
    outside(run, base, 0x4fd732, receiver + 0x10c);
    outside(run, base, 0x4fd732, receiver + 0x114);
    uint32_t stock = (run.get(receiver + 0xc) & 8) ? 0x10 : 0xd;
    uint32_t handle = outside(run, base, 0x5468bc, 0, {stock});
    run.put(receiver + 0x110, handle);
    if (!handle) {
        return 0;
    }
    uint32_t face = run.get(receiver + 0x38);
    if (face) {
        if (!outside(run, base, 0x4ff973, receiver + 0x114, {run.get16(receiver + 0x34) * 10u, face, 0})) {
            return 0;
        }
    } else {
        handle = outside(run, base, 0x5468bc, 0, {stock});
        run.put(receiver + 0x118, handle);
        if (!handle) {
            return 0;
        }
    }
    return 1;
}

// Encode a signed integer exactly as binary64, without host floating arithmetic.
uint64_t integerBits(int32_t value) {
    uint64_t magnitude = value < 0 ? uint64_t(-int64_t(value)) : uint64_t(value);
    if (!magnitude) return 0;
    uint32_t leading = 0;
    for (uint64_t n = magnitude; n >>= 1;) ++leading;
    return (uint64_t(value < 0) << 63) | (uint64_t(1023 + leading) << 52) |
           ((magnitude << (52 - leading)) & 0xfffffffffffffu);
}

// ROUND_F64 has already performed the architectural store rounding. Re-encode
// its reloaded value as memory bits; this does not round or evaluate arithmetic.
void storeRounded(Run &run, ClawX87State &fp, uint32_t address) {
    run.x87_step(CLAW_X87_ROUND_F64, fp);
    const auto &value = fp.slots[0];
    uint64_t bits = uint64_t(value.signExponent >> 15) << 63;
    uint32_t exponent = value.signExponent & 0x7fff;
    if (exponent == 0x7fff) {
        bits |= 0x7ff0000000000000ull | ((value.significand >> 11) & 0xfffffffffffffu);
    } else if (value.significand) {
        int32_t biased = int32_t(exponent) - 16383 + 1023;
        if (biased > 0) {
            bits |= (uint64_t(biased) << 52) | ((value.significand >> 11) & 0xfffffffffffffu);
        } else {
            uint32_t shift = uint32_t(12 - biased);
            if (shift < 64) bits |= value.significand >> shift;
        }
    }
    run.store<uint64_t>(address, bits);
    run.x87_step(CLAW_X87_POP, fp);
}

// 0x4e2670. Local CDialog uses the original aligned frame. Arithmetic retains
// the extended live y operand through the first two original __ftol calls.
uint32_t function_4e2670(Run &run, uint32_t receiver, uint32_t resource) {
    uint32_t base = ((run.frame - 4) & ~7u) - 0xa4;
    uint32_t dialog = base + 0x3c;
    outside(run, base, 0x4f7ad2, dialog);
    uint32_t parent = outside(run, base, 0x4fb7d8, 0);
    if (parent) {
        parent = outside(run, base, 0x4fb7d8, 0);
        parent = outside(run, base, run.get(run.get(parent) + 0x7c), parent);
    }
    if (!outside(run, base, 0x4f7b4e, dialog, {resource, parent, 0})) {
        outside(run, base, 0x4f7b10, dialog);
        return 0;
    }
    outside(run, base, 0x546cc0, 0, {run.get(dialog + 0x1c), receiver + 0x6c});
    uint32_t dy = 0u - run.get(receiver + 0x70);
    uint32_t dx = 0u - run.get(receiver + 0x6c);
    outside(run, base, 0x546b7c, 0, {receiver + 0x6c, dx, dy});
    outside(run, base, 0x4f8f44, dialog);
    uint32_t style = run.get(receiver + 0xc);
    uint32_t metric = run.get(0x546c44);
    uint32_t horizontal = outside(run, base, metric, 0, {7});
    run.put(base + 0x1c, horizontal);
    uint32_t vertical = outside(run, base, metric, 0, {8});
    if (style & 0xc00000) {
        run.put(base + 0x10, vertical);
        uint32_t caption = outside(run, base, metric, 0, {4});
        vertical = run.get(base + 0x10) + caption;
    } else {
        metric = run.get(0x546c44);
    }
    run.put(base + 0x20, vertical);
    uint32_t width = run.get(receiver + 0x74) - 2u * run.get(base + 0x1c) - run.get(receiver + 0x6c);
    run.put(base + 0x14, width);
    uint32_t bottomBorder = outside(run, base, metric, 0, {8});
    uint32_t height = run.get(receiver + 0x78) - run.get(receiver + 0x70) - run.get(base + 0x20) - bottomBorder;
    ClawX87State fp{};
    fp.size = sizeof(fp); fp.version = CLAW_X87_VERSION; fp.control = 0x023f;
    auto signedWord = [&](uint32_t address) {
        uint32_t word = run.get16(address);
        return (word & 0x8000) ? word | 0xffff0000u : word;
    };
    auto memory = [&](uint32_t op, uint32_t address) {
        run.x87_step(op, fp, {run.get(address), run.get(address + 4)});
    };
    auto scale = [&](uint32_t numerator, uint32_t dimension, uint32_t address) {
        run.x87_step(CLAW_X87_I32, fp, {numerator});
        uint64_t divisor = integerBits(s32(dimension));
        run.x87_step(CLAW_X87_DIV_F64, fp, {uint32_t(divisor), uint32_t(divisor >> 32)});
        storeRounded(run, fp, address);
    };
    auto convert = [&](uint32_t pushed) {
        fp.popCount = 1; fp.pushCount = 0; fp.returned = fp.eax = fp.edx = 0;
        run.stackPointer = base - pushed - 4;
        return run.call_x87_exact(0x4a30e0, 0, fp);
    };
    run.put(base + 0x18, height);
    scale(width, signedWord(receiver + 0x1a), base + 0x34);
    scale(height, signedWord(receiver + 0x1c), base + 0x24);
    run.put(base + 0x10, 0);
    if (run.get16(receiver + 0x14)) {
        uint32_t offset = 0;
        do {
            uint32_t record = run.get(receiver + 0x3c) + offset;
            run.put(base + 0x14, signedWord(record + 0xa));
            run.x87_step(CLAW_X87_I32, fp, {run.get(base + 0x14)});
            memory(CLAW_X87_MUL_F64, base + 0x24);
            run.put(base + 0x14, signedWord(record + 8));
            run.x87_step(CLAW_X87_I32, fp, {run.get(base + 0x14)});
            run.put(base + 0x14, signedWord(record + 0xe));
            memory(CLAW_X87_MUL_F64, base + 0x34);
            storeRounded(run, fp, base + 0x2c);
            run.x87_step(CLAW_X87_I32, fp, {run.get(base + 0x14)});
            memory(CLAW_X87_MUL_F64, base + 0x24);
            run.x87_step(CLAW_X87_ADD_ST1, fp);
            uint32_t bottom = convert(0);
            run.put(base - 4, bottom);
            run.put(base + 0x14, signedWord(record + 0xc));
            run.x87_step(CLAW_X87_I32, fp, {run.get(base + 0x14)});
            memory(CLAW_X87_MUL_F64, base + 0x34);
            memory(CLAW_X87_ADD_F64, base + 0x2c);
            uint32_t right = convert(4);
            run.put(base - 8, right);
            uint32_t top = convert(8);
            memory(CLAW_X87_F64, base + 0x2c);
            run.put(base - 12, top);
            uint32_t left = convert(12);
            outside(run, base, 0x546d5c, 0, {record + 0x28, left, top, right, bottom});
            outside(run, base, 0x546b7c, 0, {run.get(receiver + 0x3c) + offset + 0x28,
                                           run.get(base + 0x1c), run.get(base + 0x20)});
            uint32_t index = run.get(base + 0x10) + 1;
            offset += 0x5c;
            run.put(base + 0x10, index);
        } while (s32(run.get(base + 0x10)) < int32_t(run.get16(receiver + 0x14)));
        metric = run.get(0x546c44);
    }
    uint32_t captionTop = outside(run, base, metric, 0, {8});
    run.put(base + 0x14, captionTop);
    uint32_t captionLeft = outside(run, base, metric, 0, {7});
    run.put(base + 0x10, captionLeft);
    uint32_t windowWidth = run.get(receiver + 0x74) - run.get(receiver + 0x6c);
    uint32_t captionHeight = outside(run, base, metric, 0, {4});
    captionTop = run.get(base + 0x14);
    captionLeft = run.get(base + 0x10);
    outside(run, base, 0x546d5c, 0, {receiver + 0x7c, captionLeft, captionTop, windowWidth - captionLeft, captionHeight + captionTop});
    uint32_t buttonWidth = run.get(receiver + 0x130);
    uint32_t x = run.get(receiver + 0x84) - buttonWidth - 1;
    uint32_t y = run.get(receiver + 0x80) + 2;
    uint32_t buttonHeight = run.get(receiver + 0x134);
    run.put(base + 0x14, x);
    outside(run, base, 0x546d5c, 0, {receiver + 0x8c, x, y, x + buttonWidth - 1, y + buttonHeight - 4});
    x = run.get(base + 0x14) + run.get(receiver + 0x8c) - run.get(receiver + 0x94) - 2;
    uint32_t bottom = run.get(receiver + 0x98) - run.get(receiver + 0x90) + y;
    uint32_t right = run.get(receiver + 0x94) - run.get(receiver + 0x8c) + x;
    run.put(base + 0x14, x);
    outside(run, base, 0x546d5c, 0, {receiver + 0xac, x, y, right, bottom});
    x = run.get(base + 0x14) + run.get(receiver + 0x8c) - run.get(receiver + 0x94);
    bottom = run.get(receiver + 0x98) - run.get(receiver + 0x90) + y;
    right = run.get(receiver + 0x94) - run.get(receiver + 0x8c) + x;
    outside(run, base, 0x546d5c, 0, {receiver + 0x9c, x, y, right, bottom});
    outside(run, base, 0x4f7b10, dialog);
    return 1;
}

// 0x4e21a0. Standard dialog template and 0x5c-byte control records.
uint32_t function_4e21a0(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t base = run.frame - 0x28;
    run.put(receiver + 0x64, 0);
    uint32_t info = outside(run, base, 0x546ac8, 0, {0, name, 5});
    if (!info) {
        return 0;
    }
    uint32_t loaded = outside(run, base, 0x546acc, 0, {0, info});
    if (!loaded) {
        return 0;
    }
    uint32_t source = outside(run, base, 0x546ac4, 0, {loaded});
    if (!source) {
        return 0;
    }
    uint32_t size = outside(run, base, 0x546a54, 0, {0, info});
    uint32_t copy = outside(run, base, 0x4f63ec, 0, {size});
    copyBytes(run, copy, source, size);
    if (run.get16(copy) == 0xffff) {
        outside(run, base, 0x4f6428, 0, {copy});
        return 0;
    }
    copyBytes(run, receiver + 0xc, source, 0x12);
    uint32_t cursor = source + 0x12;
    uint32_t strlenFunction;
    if (run.get16(cursor) == 0xffff) {
        run.put(receiver + 0x20, run.get16(cursor + 2));
        cursor += 4;
        strlenFunction = run.get(0x5469e4);
    } else if (!run.get16(cursor)) {
        cursor += 2;
        strlenFunction = run.get(0x5469e4);
    } else {
        uint32_t text = narrowAt(run, base, cursor);
        strlenFunction = run.get(0x5469e4);
        run.put(receiver + 0x24, text);
        cursor += outside(run, base, strlenFunction, 0, {text}) * 2 + 2;
    }
    if (run.get16(cursor) == 0xffff) {
        run.put(receiver + 0x28, run.get16(cursor + 2));
        cursor += 4;
    } else if (!run.get16(cursor)) {
        cursor += 2;
    } else {
        uint32_t text = narrowAt(run, base, cursor);
        run.put(receiver + 0x2c, text);
        cursor += outside(run, base, strlenFunction, 0, {text}) * 2 + 2;
    }
    if (run.get16(cursor)) {
        uint32_t text = narrowAt(run, base, cursor);
        run.put(receiver + 0x30, text);
        cursor += outside(run, base, strlenFunction, 0, {text}) * 2 + 2;
    } else {
        cursor += 2;
    }
    if (run.get8(receiver + 0xc) & 0x40) {
        run.put16(receiver + 0x34, run.get16(cursor));
        cursor += 2;
        uint32_t text = narrowAt(run, base, cursor);
        run.put(receiver + 0x38, text);
        cursor += outside(run, base, strlenFunction, 0, {text}) * 2 + 2;
    }
    uint32_t count = run.get16(receiver + 0x14);
    uint32_t array = outside(run, base, 0x4f63ec, 0, {count * 0x5c});
    if (array) {
        for (uint32_t index = 0; index < count; ++index) {
            uint32_t record = array + index * 0x5c;
            run.put(record + 0x0, 0);
            run.put(record + 0x4, 0);
            run.put(record + 0x8, 0);
            run.put(record + 0xc, 0);
            run.put16(record + 0x10, 0);
            run.put16(record + 0x12, 0);
            run.put(record + 0x14, 0);
            run.put16(record + 0x18, 0);
            run.put(record + 0x1c, 0);
            run.put(record + 0x20, 0);
            run.put(record + 0x24, 0);
            outside(run, base, 0x546cdc, 0, {record + 0x28});
            run.put(record + 0x38, 0);
            run.put(record + 0x3c, 0);
            for (uint32_t offset = 0x40; offset < 0x5c; offset += 4) {
                run.put(record + offset, 0);
            }
        }
    }
    run.put(receiver + 0x3c, array);
    uint32_t offset = 0;
    uint32_t index = 0;
    if (run.get16(receiver + 0x14)) {
        do {
            cursor = (cursor + 3) & ~3u;
            copyBytes(run, run.get(receiver + 0x3c) + offset, cursor, 0x12);
            cursor = (cursor + 0x13) & ~1u;
            if (run.get16(cursor) == 0xffff) {
                run.put16(run.get(receiver + 0x3c) + offset + 0x12, run.get16(cursor + 2));
                cursor += 4;
            } else {
                uint32_t text = narrowAt(run, base, cursor);
                run.put(run.get(receiver + 0x3c) + offset + 0x14, text);
                text = run.get(run.get(receiver + 0x3c) + offset + 0x14);
                cursor += outside(run, base, 0x5469e4, 0, {text}) * 2 + 2;
            }
            cursor = (cursor + 1) & ~1u;
            if (run.get16(cursor) == 0xffff) {
                run.put16(run.get(receiver + 0x3c) + offset + 0x18, run.get16(cursor + 2));
                cursor += 4;
            } else {
                uint32_t text = narrowAt(run, base, cursor);
                run.put(run.get(receiver + 0x3c) + offset + 0x1c, text);
                text = run.get(run.get(receiver + 0x3c) + offset + 0x1c);
                cursor += outside(run, base, 0x5469e4, 0, {text}) * 2 + 2;
            }
            uint32_t extra = run.get16(cursor);
            if (extra) {
                run.put(run.get(receiver + 0x3c) + offset + 0x20, extra);
                extra = run.get(run.get(receiver + 0x3c) + offset + 0x20);
                uint32_t data = outside(run, base, 0x4f63ec, 0, {extra - 2});
                cursor += 2;
                run.put(run.get(receiver + 0x3c) + offset + 0x24, data);
                uint32_t record = run.get(receiver + 0x3c) + offset;
                uint32_t bytes = run.get(record + 0x20) - 2;
                copyBytes(run, run.get(record + 0x24), cursor, bytes);
                cursor += run.get(run.get(receiver + 0x3c) + offset + 0x20) - 2;
            } else {
                cursor += 2;
            }
            run.put(run.get(receiver + 0x3c) + offset + 0x38, index);
            count = run.get16(receiver + 0x14);
            ++index;
            offset += 0x5c;
        } while (s32(index) < s32(count));
    }
    run.put(copy, run.get(copy) & 0xefffffff);
    uint32_t measured;
    {
        Frame frame(run, base - 8);
        measured = function_4e2670(run, receiver, copy);
    }
    outside(run, base, 0x4f6428, 0, {copy});
    if (!measured) {
        return 0;
    }
    count = run.get16(receiver + 0x14);
    array = run.get(receiver + 0x3c);
    for (index = 0; index < count; ++index) {
        uint32_t record = array + index * 0x5c;
        uint32_t type = run.get16(record + 0x12);
        if ((type == 0x80 && (run.get(record) & 0xf) != 7) || type == 0x81 || type == 0x83 || type == 0x85) {
            run.put(record + 0x3c, run.get(record + 0x3c) | 4);
            run.put(receiver + 0x68, run.get(receiver + 0x3c) + index * 0x5c);
            break;
        }
    }
    return 1;
}

// 0x4e2090. Every failed stage returns its zero result; success sets +0x4.
uint32_t function_4e2090(Run &run, uint32_t receiver, uint32_t resource) {
    uint32_t base = run.frame - 4;
    {
        Frame frame(run, base - 8);
        if (!function_4e21a0(run, receiver, resource)) {
            return 0;
        }
    }
    {
        Frame frame(run, base - 4);
        if (!function_4e25e0(run, receiver)) {
            return 0;
        }
    }
    if (!outside(run, base, 0x4e29a0, receiver)) {
        return 0;
    }
    if (!outside(run, base, 0x4e2f70, receiver)) {
        return 0;
    }
    if (!outside(run, base, 0x4e3090, receiver)) {
        return 0;
    }
    if (run.get(receiver + 0x50) && !outside(run, base, 0x4e31f0, receiver)) {
        return 0;
    }
    run.put(receiver + 0x4, 1);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4e1b20: return function_4e1b20(run, receiver, arguments[0], arguments[1]);
    case 0x4e2090: return function_4e2090(run, receiver, arguments[0]);
    case 0x4e2160: return function_4e2160(run, arguments[0]);
    case 0x4e21a0: return function_4e21a0(run, receiver, arguments[0]);
    case 0x4e25e0: return function_4e25e0(run, receiver);
    case 0x4e2670: return function_4e2670(run, receiver, arguments[0]);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_menu_dialog_resources_entry, owned, body)
