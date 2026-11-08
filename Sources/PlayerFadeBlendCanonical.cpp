// Original palette blend tables, pointer-array growth and fade diagnostics
// Recovered from the hash-verified packet disassembly.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4c61f0:
        return 0;
    case 0x4c6270:
        return 0;
    case 0x4c6bd0:
        return 3;
    case 0x4c7510:
        return 1;
    case 0x4c7580:
        return 4;
    case 0x4c76d0:
        return 0;
    case 0x4c76e0:
        return 0;
    case 0x4c76f0:
        return 1;
    case 0x4c78d0:
        return 0;
    case 0x4dee30:
        return 2;
    case 0x4ec6b0:
        return 1;
    default:
        return -1;
    }
}

// All guest offsets below are byte offsets. Manager: +0x00 active,
// +0x04 array vtable, +0x08 storage, +0x0c size, +0x10 capacity.
// Table: +0x00 active, +0x04 byte count, +0x08 storage.
// Array receiver: +0x04 storage, +0x08 size, +0x0c capacity, +0x10 grow-by.

// 0x4c78d0.
uint32_t function_4c78d0(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x00)) {
        uint32_t data = run.get(receiver + 0x08);
        if (data) {
            run.call(0x4f6428, 0, {data});
            run.put(receiver + 0x08, 0);
        }
        run.put(receiver + 0x04, 0);
    }
    run.put(receiver + 0x00, 0);
    return 0;
}

// 0x4c76e0.
uint32_t function_4c76e0(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x00))
        function_4c78d0(run, receiver, nullptr);
    return 0;
}

// 0x4c6270.
uint32_t function_4c6270(Run &run, uint32_t receiver, const uint32_t *) {
    for (uint32_t i = 0; s32(i) < run.gets(receiver + 0x0c); ++i) {
        function_4c78d0(run, run.get(run.get(receiver + 0x08) + i * 4), nullptr);
        uint32_t entry = run.get(run.get(receiver + 0x08) + i * 4);
        if (entry) {
            function_4c76e0(run, entry, nullptr);
            run.call(0x4f6428, 0, {entry});
        }
    }
    uint32_t storage = run.get(receiver + 0x08);
    if (storage) {
        run.call(0x4f6428, 0, {storage});
        run.put(receiver + 0x08, 0);
    }
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x0c, 0);
    return 0;
}

// 0x4c61f0.
uint32_t function_4c61f0(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x00))
        function_4c6270(run, receiver, nullptr);
    run.put(receiver + 0x04, 0x5136e8);
    uint32_t storage = run.get(receiver + 0x08);
    if (storage)
        run.call(0x4f6428, 0, {storage});
    run.put(receiver + 0x04, 0x50becc);
    return 0;
}

// 0x4c7510.
uint32_t function_4c7510(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t count = run.get(receiver + 0x0c);
    if (s32(count) <= 0)
        return 0;
    uint32_t storage = run.get(receiver + 0x08);
    uint32_t index = 0;
    while (run.get(storage + index * 4) != arguments[0]) {
        ++index;
        if (s32(index) >= s32(count))
            return 0;
    }
    function_4c78d0(run, run.get(storage + index * 4), nullptr);
    uint32_t entry = run.get(run.get(receiver + 0x08) + index * 4);
    if (entry) {
        function_4c76e0(run, entry, nullptr);
        run.call(0x4f6428, 0, {entry});
    }
    count = run.get(receiver + 0x0c) - index - 1;
    storage = run.get(receiver + 0x08) + index * 4;
    for (uint32_t i = 0; i != count; ++i)
        run.put(storage + i * 4, run.get(storage + i * 4 + 0x04));
    run.put(receiver + 0x0c, run.get(receiver + 0x0c) - 1);
    return 0;
}

// 0x4c7580. Palette records have red/green/blue bytes and an ignored fourth byte.
uint32_t function_4c7580(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t best = 0;
    uint32_t distance = 0xffffffffu;
    for (uint32_t i = 0; i < 256; ++i) {
        uint32_t red = (arguments[1] & 255) - run.get8(arguments[0] + i * 4);
        uint32_t green = (arguments[2] & 255) - run.get8(arguments[0] + i * 4 + 0x01);
        uint32_t blue = (arguments[3] & 255) - run.get8(arguments[0] + i * 4 + 0x02);
        uint32_t candidate = red * red + green * green + blue * blue;
        if (candidate < distance) {
            distance = candidate;
            best = i;
        }
    }
    return best;
}

// 0x4c76d0.
uint32_t function_4c76d0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x00, 0);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x08, 0);
    return receiver;
}

// 0x4c76f0.
uint32_t function_4c76f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t storage = run.get(receiver + 0x08);
    if (storage)
        run.call(0x4f6428, 0, {storage});
    run.put(receiver + 0x04, arguments[0]);
    storage = run.call(0x4f63ec, 0, {arguments[0]});
    run.put(receiver + 0x08, storage);
    if (!storage)
        return 0;
    run.put(receiver + 0x00, 1);
    return 1;
}

// 0x4dee30.
uint32_t function_4dee30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (arguments[1] != 0xffffffffu)
        run.put(receiver + 0x10, arguments[1]);
    uint32_t size = arguments[0];
    uint32_t storage = run.get(receiver + 0x04);
    if (!size) {
        if (storage) {
            run.call(0x4f6428, 0, {storage});
            run.put(receiver + 0x04, 0);
        }
        run.put(receiver + 0x0c, 0);
        run.put(receiver + 0x08, 0);
        return 0;
    }
    if (!storage) {
        uint32_t bytes = size << 2;
        uint32_t data = run.call(0x4f63ec, 0, {bytes});
        run.put(receiver + 0x04, data);
        for (uint32_t i = 0; i < (bytes >> 2); ++i)
            run.put(data + i * 4, 0);
        run.put(receiver + 0x0c, size);
        run.put(receiver + 0x08, size);
        return 0;
    }
    uint32_t capacity = run.get(receiver + 0x0c);
    if (s32(size) <= s32(capacity)) {
        uint32_t old = run.get(receiver + 0x08);
        if (s32(size) > s32(old)) {
            for (uint32_t i = 0; i != size - old; ++i)
                run.put(storage + old * 4 + i * 4, 0);
        }
        run.put(receiver + 0x08, size);
        return 0;
    }
    uint32_t growth = run.get(receiver + 0x10);
    if (!growth) {
        int32_t derived = run.gets(receiver + 0x08) / 8;
        if (derived < 4)
            derived = 4;
        if (derived > 1024)
            derived = 1024;
        growth = uint32_t(derived);
    }
    uint32_t enlarged = capacity + growth;
    if (s32(size) >= s32(enlarged))
        enlarged = size;
    uint32_t data = run.call(0x4f63ec, 0, {enlarged << 2});
    uint32_t old = run.get(receiver + 0x08);
    storage = run.get(receiver + 0x04);
    for (uint32_t i = 0; i < ((old << 2) >> 2); ++i)
        run.put(data + i * 4, run.get(storage + i * 4));
    old = run.get(receiver + 0x08);
    for (uint32_t i = 0; i != size - old; ++i)
        run.put(data + old * 4 + i * 4, 0);
    run.call(0x4f6428, 0, {run.get(receiver + 0x04)});
    run.put(receiver + 0x08, size);
    run.put(receiver + 0x04, data);
    run.put(receiver + 0x0c, enlarged);
    return 0;
}

// 0x4ec6b0. CString is an inline incoming word, not a pointer to that word.
uint32_t function_4ec6b0(Run &run, uint32_t, const uint32_t *) {
    run.call(0x4f6584, run.automatic(4));
    return 0;
}

// 0x4c6c86..0x4c6cc6 round signed positive width to binary32, nearest-even.
// All other integer stores are channels <=255 and therefore exact. The reference
// interpreter retains SW exception/condition bits on these stores (including a
// rounded width); matching its published state must not synthesize hardware PE.
uint32_t roundedWidth(uint32_t width) {
    uint32_t exponent = 0;
    for (uint32_t bits = width; bits > 1; bits >>= 1)
        ++exponent;
    if (exponent <= 23)
        return width;
    uint32_t shift = exponent - 23;
    uint32_t units = width >> shift;
    uint32_t remainder = width & ((1u << shift) - 1);
    uint32_t halfway = 1u << (shift - 1);
    if (remainder > halfway || (remainder == halfway && (units & 1)))
        ++units;
    return units << shift;
}

// Exact encodings, never floating-point host arithmetic. Positive integers here
// are <=2^31 (the rounded width may be 2^31).
uint64_t integerBits(uint32_t value) {
    if (!value)
        return 0;
    uint32_t exponent = 0;
    for (uint32_t bits = value; bits > 1; bits >>= 1)
        ++exponent;
    return (uint64_t(exponent + 1023) << 52) | ((uint64_t(value) << (52 - exponent)) & 0xfffffffffffffull);
}

uint64_t binary32Bits(uint32_t value) {
    uint64_t sign = uint64_t(value >> 31) << 63;
    uint32_t exponent = (value >> 23) & 255;
    uint32_t fraction = value & 0x7fffff;
    if (exponent == 255)
        return sign | (uint64_t(2047) << 52) | (uint64_t(fraction) << 29);
    if (!exponent) {
        if (!fraction)
            return sign;
        uint32_t high = 0;
        for (uint32_t bits = fraction; bits > 1; bits >>= 1)
            ++high;
        return sign | (uint64_t(high + 874) << 52) | ((uint64_t(fraction) << (52 - high)) & 0xfffffffffffffull);
    }
    return sign | (uint64_t(exponent + 896) << 52) | (uint64_t(fraction) << 29);
}

// Every finite intermediate has precision <=53 and exponent within binary64:
// ratio is in [0,2), nonzero ratio >=2^-31; the other input is binary32 and
// channels are <=255. Thus finite nonzero results remain above 2^-202 and below
// 2^138. Arithmetic never needs a lossy store to form a memory operand.
uint64_t operandBits(Run &run, const ClawX87Value &value) {
    uint64_t sign = uint64_t(value.signExponent >> 15) << 63;
    uint32_t exponent = value.signExponent & 0x7fff;
    if (!exponent && !value.significand)
        return sign;
    if (value.significand & 0x7ff)
        run.fail(CLAW_FAULT_ABI, 0x4c6bd0);
    if (exponent == 0x7fff)
        return sign | (uint64_t(2047) << 52) | ((value.significand >> 11) & 0xfffffffffffffull);
    if (exponent < 15361 || exponent > 17406)
        run.fail(CLAW_FAULT_ABI, 0x4c6bd0);
    return sign | (uint64_t(exponent - 15360) << 52) | ((value.significand >> 11) & 0xfffffffffffffull);
}

void memoryStep(Run &run, uint32_t operation, ClawX87State &state, uint64_t bits) {
    run.x87_step(operation, state, {uint32_t(bits), uint32_t(bits >> 32)});
}

// FLD ST(i), FXCH ST(i), and the stack portion of FADDP are permutations of
// explicit logical slots. The reference interpreter preserves non-TOP SW bits
// on these instructions; the independently captured original sequence checks
// these states at all three conversion boundaries. No arithmetic is done here.
void exchange(ClawX87State &state, uint32_t index) {
    ClawX87Value value = state.slots[0];
    state.slots[0] = state.slots[index];
    state.slots[index] = value;
}

void duplicate(ClawX87State &state, uint32_t index) {
    ClawX87Value value = state.slots[index];
    for (uint32_t i = state.count; i; --i)
        state.slots[i] = state.slots[i - 1];
    state.slots[0] = value;
    ++state.count;
    state.status = (state.status & ~0x3800u) | ((((state.status >> 11) - 1) & 7) << 11);
}

// Finite FADD(a,b) is SUBR(b,CHS(a)): b-(-a), with one PC53 rounding.
// Both preserve the same lower live slots and reference-interpreter SW; only
// FADDP's stack pop remains. The other addend is always a finite target*ratio.
// Original special snapshots show a propagated quiet NaN retains its sign and
// payload when added to that finite addend, so retain that exact encoding.
void addAndPop(Run &run, ClawX87State &state, uint32_t index) {
    ClawX87Value original = state.slots[0];
    uint64_t other = operandBits(run, state.slots[index]);
    run.x87_step(CLAW_X87_CHS, state);
    memoryStep(run, CLAW_X87_SUBR_F64, state, other);
    if ((original.signExponent & 0x7fff) == 0x7fff && (original.significand & 0x7fffffffffffffffull))
        state.slots[0] = original;
    state.slots[index] = state.slots[0];
    for (uint32_t i = 1; i < state.count; ++i)
        state.slots[i - 1] = state.slots[i];
    --state.count;
    state.slots[state.count] = {};
    state.status = (state.status & ~0x3800u) | ((((state.status >> 11) + 1) & 7) << 11);
}

uint32_t convert(Run &run, ClawX87State &state) {
    state.popCount = 1;
    state.pushCount = 0;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, state);
}

// 0x4c6bd0. The arithmetic sequence follows 0x4c6cca..0x4c6d41 in order.
uint32_t function_4c6bd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t table = run.call(0x4f63ec, 0, {12});
    if (!table)
        return 0;
    function_4c76d0(run, table, nullptr);
    uint32_t allocation[] = {arguments[1] << 8};
    if (!function_4c76f0(run, table, allocation))
        return 0;
    uint32_t index = run.get(receiver + 0x0c);
    uint32_t resize[] = {index + 1, 0xffffffffu};
    function_4dee30(run, receiver + 0x04, resize);
    run.put(run.get(receiver + 0x08) + index * 4, table);
    uint32_t output = run.get(table + 0x08);
    ClawX87State state{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
    for (uint32_t row = 0; row < 256; ++row) {
        if (s32(arguments[1]) > 0) {
            uint64_t width = integerBits(roundedWidth(arguments[1]));
            uint64_t targetBlue = integerBits((arguments[2] >> 16) & 255);
            uint64_t targetGreen = integerBits((arguments[2] >> 8) & 255);
            uint64_t targetRed = integerBits(arguments[2] & 255);
            for (uint32_t column = 0; s32(column) < s32(arguments[1]); ++column) {
                memoryStep(run, CLAW_X87_F64, state, binary32Bits(run.get(0x513700)));
                run.x87_step(CLAW_X87_I32, state, {column});
                memoryStep(run, CLAW_X87_DIV_F64, state, width);
                exchange(state, 1);
                uint64_t global = operandBits(run, state.slots[0]);
                state.slots[0] = state.slots[1];
                memoryStep(run, CLAW_X87_SUBR_F64, state, global);
                run.x87_step(CLAW_X87_I32, state, {run.get8(arguments[0] + row * 4 + 0x02)});
                duplicate(state, 2);
                memoryStep(run, CLAW_X87_MUL_F64, state, targetBlue);
                exchange(state, 1);
                memoryStep(run, CLAW_X87_MUL_F64, state, operandBits(run, state.slots[2]));
                addAndPop(run, state, 1);
                uint32_t blue = convert(run, state);
                duplicate(state, 1);
                run.x87_step(CLAW_X87_I32, state, {run.get8(arguments[0] + row * 4 + 0x01)});
                exchange(state, 1);
                memoryStep(run, CLAW_X87_MUL_F64, state, targetGreen);
                exchange(state, 1);
                memoryStep(run, CLAW_X87_MUL_F64, state, operandBits(run, state.slots[2]));
                addAndPop(run, state, 1);
                uint32_t green = convert(run, state);
                run.x87_step(CLAW_X87_I32, state, {run.get8(arguments[0] + row * 4)});
                exchange(state, 2);
                memoryStep(run, CLAW_X87_MUL_F64, state, targetRed);
                exchange(state, 2);
                memoryStep(run, CLAW_X87_MUL_F64, state, operandBits(run, state.slots[1]));
                addAndPop(run, state, 2);
                exchange(state, 1);
                uint32_t red = convert(run, state);
                run.x87_step(CLAW_X87_POP, state);
                uint32_t nearest[] = {arguments[0], red, green, blue};
                uint32_t color = function_4c7580(run, 0, nearest);
                run.put8(output + column, uint8_t(color));
            }
        }
        output += arguments[1];
    }
    return table;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4c61f0:
        return function_4c61f0(run, receiver, arguments);
    case 0x4c6270:
        return function_4c6270(run, receiver, arguments);
    case 0x4c6bd0:
        return function_4c6bd0(run, receiver, arguments);
    case 0x4c7510:
        return function_4c7510(run, receiver, arguments);
    case 0x4c7580:
        return function_4c7580(run, receiver, arguments);
    case 0x4c76d0:
        return function_4c76d0(run, receiver, arguments);
    case 0x4c76e0:
        return function_4c76e0(run, receiver, arguments);
    case 0x4c76f0:
        return function_4c76f0(run, receiver, arguments);
    case 0x4c78d0:
        return function_4c78d0(run, receiver, arguments);
    case 0x4dee30:
        return function_4dee30(run, receiver, arguments);
    case 0x4ec6b0:
        return function_4ec6b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_player_fade_blend_canonical_entry, owned, body)
