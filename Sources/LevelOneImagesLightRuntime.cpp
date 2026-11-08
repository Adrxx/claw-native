// Level 1 closure: surface color converters, restore handler and light palette helpers
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b9fa0:
        return 3;
    case 0x4ba150:
        return 2;
    case 0x4ba3f0:
        return 2;
    case 0x4ba890:
        return 3;
    case 0x4bd0a0:
        return 0;
    case 0x4c68e0:
        return 5;
    default:
        return -1;
    }
}

// Surface wrapper fields used by the converters: +0x08 surface COM object,
// +0x14 height (signed), +0x18 width (signed), +0x1c pitch in bytes.
void unlockSurface(Run &run, uint32_t surface) {
    uint32_t interface = run.get(surface + 0x08);
    uint32_t method = run.get(run.get(interface) + 0x80);
    run.call(method, 0, {interface, 0});
}

// Shift counts are the low byte of a global, masked to five bits like x86.
uint32_t shiftCount(Run &run, uint32_t global) {
    return run.get8(global) & 31u;
}

// Visits every pixel of the locked surface. Bottom-up reads the height once
// and counts rows down to zero; top-down re-reads the height after each row.
// The width is re-read after every pixel in both orders.
template <typename Pixel>
void walkSurface(Run &run, uint32_t surface, uint32_t lock, bool bottomUp, Pixel pixel) {
    if (bottomUp) {
        uint32_t row = run.get(surface + 0x14) - 1;
        while (s32(row) >= 0) {
            uint32_t base = row * run.get(surface + 0x1c) + lock;
            uint32_t width = run.get(surface + 0x18);
            if (s32(width) > 0) {
                uint32_t x = 0;
                do {
                    pixel(base, x);
                    ++x;
                } while (s32(x) < s32(run.get(surface + 0x18)));
            }
            --row;
        }
        return;
    }
    uint32_t height = run.get(surface + 0x14);
    if (s32(height) <= 0)
        return;
    uint32_t row = 0;
    do {
        uint32_t base = row * run.get(surface + 0x1c) + lock;
        uint32_t width = run.get(surface + 0x18);
        if (s32(width) > 0) {
            uint32_t x = 0;
            do {
                pixel(base, x);
                ++x;
            } while (s32(x) < s32(run.get(surface + 0x18)));
        }
        ++row;
        height = run.get(surface + 0x14);
    } while (s32(row) < s32(height));
}

// Packs three bytes into the 16-bit pixel: a and b are shifted down and then
// left into place, c is only shifted down.
uint16_t packPixel(Run &run, uint32_t a, uint32_t b, uint32_t c) {
    uint32_t down0 = shiftCount(run, 0x541368);
    uint32_t down1 = shiftCount(run, 0x54136c);
    uint32_t down2 = shiftCount(run, 0x541370);
    uint32_t up0 = shiftCount(run, 0x54135c);
    uint32_t up1 = shiftCount(run, 0x541360);
    uint32_t word0 = (a >> down0) << up0;
    uint32_t word1 = (b >> down1) << up1;
    uint32_t word2 = c >> down2;
    return uint16_t(word0 | word1 | word2);
}

// 0x4b9fa0. Palette image (one index byte per pixel) to a 16-bit surface.
// Arguments: source, palette, mode (2 = bottom-up rows).
uint32_t function_4b9fa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[0];
    uint32_t palette = arguments[1];
    uint32_t mode = arguments[2];
    if (!palette)
        return 0;
    uint32_t lock = run.call(0x4b9730, receiver, {0});
    if (!lock)
        return 0;
    walkSurface(run, receiver, lock, mode == 2, [&](uint32_t base, uint32_t x) {
        uint32_t entry = palette + run.get8(source) * 4;
        ++source;
        uint32_t p0 = run.get8(entry);
        uint32_t p1 = run.get8(entry + 1);
        uint32_t p2 = run.get8(entry + 2);
        uint16_t word = packPixel(run, p0, p1, p2);
        run.put16(base + x * 2, word);
    });
    unlockSurface(run, receiver);
    return 1;
}

// 0x4ba150. 24-bit image to a 16-bit surface. Mode 2 reads the source as BGR,
// so components 0 and 2 swap; any other mode reads it as RGB.
uint32_t function_4ba150(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[0];
    uint32_t mode = arguments[1];
    uint32_t lock = run.call(0x4b9730, receiver, {0});
    if (!lock)
        return 0;
    walkSurface(run, receiver, lock, mode == 2, [&](uint32_t base, uint32_t x) {
        uint32_t s0 = run.get8(source);
        uint32_t s1 = run.get8(source + 1);
        uint32_t s2 = run.get8(source + 2);
        source += 3;
        uint16_t word = mode == 2 ? packPixel(run, s2, s1, s0) : packPixel(run, s0, s1, s2);
        run.put16(base + x * 2, word);
    });
    unlockSurface(run, receiver);
    return 1;
}

// 0x4ba3f0. 16-bit image to three 16-bit words per pixel.
uint32_t function_4ba3f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[0];
    uint32_t mode = arguments[1];
    uint32_t lock = run.call(0x4b9730, receiver, {0});
    if (!lock)
        return 0;
    walkSurface(run, receiver, lock, mode == 2, [&](uint32_t base, uint32_t x) {
        uint32_t value = run.get16(source);
        source += 2;
        uint32_t up0 = shiftCount(run, 0x541368);
        uint32_t up1 = shiftCount(run, 0x54136c);
        uint32_t up2 = shiftCount(run, 0x541370);
        uint32_t down0 = shiftCount(run, 0x54135c);
        uint32_t down1 = shiftCount(run, 0x541360);
        uint32_t word0 = uint8_t(((value >> down0) & 0xff) << up0);
        uint32_t word1 = uint8_t(((value >> down1) & 0xff) << up1);
        uint32_t word2 = uint8_t((value & 0xff) << up2);
        uint32_t dest = base + x * 6;
        run.put16(dest, uint16_t(word0));
        run.put16(dest + 2, uint16_t(word1));
        run.put16(dest + 4, uint16_t(word2));
    });
    unlockSurface(run, receiver);
    return 1;
}

// 0x4ba890. 16-bit image to palette indices, nearest colour.
// Arguments: source, palette, mode (2 = bottom-up rows).
uint32_t function_4ba890(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[0];
    uint32_t palette = arguments[1];
    uint32_t mode = arguments[2];
    if (!palette)
        return 0;
    uint32_t lock = run.call(0x4b9730, receiver, {0});
    if (!lock)
        return 0;
    walkSurface(run, receiver, lock, mode == 2, [&](uint32_t base, uint32_t x) {
        uint32_t value = run.get16(source);
        source += 2;
        uint32_t up0 = shiftCount(run, 0x541368);
        uint32_t up1 = shiftCount(run, 0x54136c);
        uint32_t up2 = shiftCount(run, 0x541370);
        uint32_t down0 = shiftCount(run, 0x54135c);
        uint32_t down1 = shiftCount(run, 0x541360);
        int32_t a = uint8_t(((value >> down0) & 0xff) << up0);
        int32_t b = uint8_t(((value >> down1) & 0xff) << up1);
        int32_t c = uint8_t((value & 0xff) << up2);
        int32_t da = a - int32_t(run.get8(palette));
        int32_t db = b - int32_t(run.get8(palette + 1));
        int32_t dc = c - int32_t(run.get8(palette + 2));
        int32_t bestDistance = da * da + db * db + dc * dc;
        uint32_t best = 0;
        for (uint32_t index = 1; index < 0x100; ++index) {
            uint32_t entry = palette + index * 4;
            int32_t ea = a - int32_t(run.get8(entry));
            int32_t eb = b - int32_t(run.get8(entry + 1));
            int32_t ec = c - int32_t(run.get8(entry + 2));
            int32_t distance = ea * ea + eb * eb + ec * ec;
            if (distance >= bestDistance)
                continue;
            best = index;
            bestDistance = distance;
            if (distance == 0)
                break;
        }
        run.put8(base + x, uint8_t(best));
    });
    unlockSurface(run, receiver);
    return 1;
}

// 0x4bd0a0. Tail jump through the function pointer at 0x54138c, or a no-op
// call and zero when the pointer is empty.
uint32_t function_4bd0a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t target = run.get(0x54138c);
    if (target)
        return run.call(target, 0, {});
    run.call(0x4bc110, 0, {0x532540});
    return 0;
}

float floatFromBits(uint32_t bits) {
    float value;
    std::memcpy(&value, &bits, 4);
    return value;
}

uint32_t doubleLow(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    return uint32_t(bits);
}

uint32_t doubleHigh(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    return uint32_t(bits >> 32);
}

// The x87 stack of the light table builder. The original leaves the compare
// condition bits (C0..C3 of the status word) untouched by loads, arithmetic
// and conversions, so they are carried across every operation here.
struct Fpu {
    Run &run;
    ClawX87State state{};
    uint32_t condition = 0;

    explicit Fpu(Run &r) : run(r) {
        state.size = sizeof(state);
        state.version = CLAW_X87_VERSION;
        state.control = 0x023f;
    }

    void restoreCondition() {
        state.status = (state.status & ~0x4700u) | condition;
    }

    uint64_t step(uint32_t operation, std::initializer_list<uint32_t> operands = {}) {
        restoreCondition();
        uint64_t bits = run.x87_step(operation, state, operands);
        if (operation == CLAW_X87_COMP_F64)
            condition = state.status & 0x4700;
        restoreCondition();
        return bits;
    }

    void arithmetic(uint32_t operation, double operand) {
        step(operation, {doubleLow(operand), doubleHigh(operand)});
    }

    void push(double value) {
        step(CLAW_X87_F64, {doubleLow(value), doubleHigh(value)});
    }

    // Original __ftol: one value in, none out. Returns EAX.
    uint32_t truncate() {
        restoreCondition();
        state.popCount = 1;
        state.pushCount = 0;
        state.returned = 0;
        state.eax = 0;
        state.edx = 0;
        uint32_t result = run.call_x87_exact(0x4a30e0, 0, state);
        condition = state.status & 0x4700;
        return result;
    }

    // Original power runtime: ST(0) = exponent, ST(1) = base, one result.
    void power() {
        restoreCondition();
        state.popCount = 2;
        state.pushCount = 1;
        state.returned = 0;
        state.eax = 0;
        state.edx = 0;
        run.call_x87_exact(0x4f1b30, 0, state);
        condition = state.status & 0x4700;
    }
};

// Converts one channel of the light table: ST(0) holds E + channel on entry.
// Multiplies by the float factor, clamps at 255.0 like the original, and
// truncates through the original __ftol. Returns the converted value.
uint32_t convertChannel(Fpu &fpu, uint32_t sum, double factor) {
    fpu.arithmetic(CLAW_X87_MUL_F64, factor);
    fpu.arithmetic(CLAW_X87_COMP_F64, 255.0);
    if (fpu.condition & 0x100) {
        fpu.step(CLAW_X87_I32, {sum});
        fpu.arithmetic(CLAW_X87_MUL_F64, factor);
    } else {
        fpu.push(255.0);
    }
    return fpu.truncate();
}

// 0x4c68e0. Builds a 256 x count nearest-colour light table.
// Arguments: palette, count, a3, a4, a5.
uint32_t function_4c68e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t palette = arguments[0];
    uint32_t count = arguments[1];
    uint32_t a3 = arguments[2];
    uint32_t a4 = arguments[3];
    uint32_t a5 = arguments[4];
    uint32_t block = run.call(0x4f63ec, 0, {0xc});
    uint32_t object = 0;
    if (block)
        object = run.call(0x4c76d0, block, {});
    if (!object)
        return 0;
    if (!run.call(0x4c76f0, object, {count << 8}))
        return 0;
    // Container: +0x0c element count, +0x08 data pointer (re-read after growth).
    uint32_t index = run.get(receiver + 0x0c);
    run.call(0x4dee30, receiver + 4, {index + 1, 0xffffffffu});
    uint32_t data = run.get(receiver + 0x08);
    run.put(data + index * 4, object);
    uint32_t destination = run.get(object + 0x08);
    uint32_t entry = palette;
    Fpu fpu(run);
    const double constant0 = floatFromBits(0x3f160000);
    const double constant1 = floatFromBits(0x3e980000);
    const double constant2 = floatFromBits(0x3de00000);
    const double scale = floatFromBits(0x3b808081);
    const double hundredth = floatFromBits(0x3c23d70a);
    const double negativeOne = -1.0;
    for (uint32_t row = 0; row < 0x100; ++row) {
        if (s32(count) > 0) {
            float offsetFactor = float(s32(a3 - 100));
            float countFloat = float(s32(count));
            uint32_t extra = a5 & 0xff;
            for (uint32_t column = 0; s32(column) < s32(count); ++column) {
                uint32_t p0 = run.get8(entry);
                uint32_t p1 = run.get8(entry + 1);
                uint32_t p2 = run.get8(entry + 2);
                // L = trunc((p0 * C0 + p1 * C1) + p2 * C2)
                fpu.step(CLAW_X87_I32, {p1});
                fpu.step(CLAW_X87_I32, {p0});
                fpu.arithmetic(CLAW_X87_MUL_F64, constant0);
                fpu.step(CLAW_X87_I32, {p2});
                fpu.step(CLAW_X87_XCH_ST + 2);
                fpu.arithmetic(CLAW_X87_MUL_F64, constant1);
                fpu.step(CLAW_X87_XCH_ST + 2);
                fpu.arithmetic(CLAW_X87_MUL_F64, constant2);
                fpu.step(CLAW_X87_XCH_ST + 2);
                fpu.step(CLAW_X87_ADDP + 1);
                fpu.step(CLAW_X87_XCH_ST + 1);
                fpu.step(CLAW_X87_ADDP + 1);
                uint32_t light = fpu.truncate() & 0xff;
                // Q = 1 / (L / 255 + 1), D = a4, P = pow(Q, D)
                fpu.step(CLAW_X87_I32, {a4});
                fpu.step(CLAW_X87_I32, {light});
                fpu.arithmetic(CLAW_X87_MUL_F64, scale);
                fpu.arithmetic(CLAW_X87_SUB_F64, negativeOne);
                fpu.push(1.0);
                fpu.step(CLAW_X87_DIV_TO0 + 1);
                fpu.step(CLAW_X87_XCH_ST + 1);
                fpu.step(CLAW_X87_POP);
                fpu.step(CLAW_X87_XCH_ST + 1);
                fpu.power();
                // M = (float)(J * ((P * a3') * 0.01) + 1), J = column / count
                fpu.step(CLAW_X87_I32, {column});
                fpu.arithmetic(CLAW_X87_DIV_F64, countFloat);
                fpu.step(CLAW_X87_XCH_ST + 1);
                fpu.arithmetic(CLAW_X87_MUL_F64, offsetFactor);
                fpu.step(CLAW_X87_I32, {extra + p0});
                fpu.step(CLAW_X87_XCH_ST + 1);
                fpu.arithmetic(CLAW_X87_MUL_F64, hundredth);
                fpu.step(CLAW_X87_MULP + 2);
                fpu.step(CLAW_X87_XCH_ST + 1);
                fpu.arithmetic(CLAW_X87_SUB_F64, negativeOne);
                uint64_t stored = fpu.step(CLAW_X87_STP_F64);
                double storedValue;
                std::memcpy(&storedValue, &stored, 8);
                double factor = float(storedValue);
                uint32_t r0 = convertChannel(fpu, extra + p0, factor);
                fpu.step(CLAW_X87_I32, {extra + p1});
                uint32_t r1 = convertChannel(fpu, extra + p1, factor);
                fpu.step(CLAW_X87_I32, {extra + p2});
                uint32_t r2 = convertChannel(fpu, extra + p2, factor);
                uint32_t found = run.call(0x4c7580, 0, {palette, r0 & 0xff, r1 & 0xff, r2});
                run.put8(destination + column, uint8_t(found));
            }
        }
        destination += count;
        entry += 4;
    }
    return object;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b9fa0:
        return function_4b9fa0(run, receiver, arguments);
    case 0x4ba150:
        return function_4ba150(run, receiver, arguments);
    case 0x4ba3f0:
        return function_4ba3f0(run, receiver, arguments);
    case 0x4ba890:
        return function_4ba890(run, receiver, arguments);
    case 0x4bd0a0:
        return function_4bd0a0(run, receiver, arguments);
    case 0x4c68e0:
        return function_4c68e0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_images_light_entry, owned, body)
