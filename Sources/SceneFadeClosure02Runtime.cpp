// Level 1 closure: scene fade and paper transition helpers
//
// Recovered from the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"
#include <cmath>

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4ed060:
        return 0;
    case 0x4ed080:
        return 1;
    case 0x4ed0a0:
        return 0;
    case 0x4ed0b0:
        return 1;
    case 0x4ed1a0:
        return 1;
    case 0x4ed5d0:
        return 0;
    case 0x4efb00:
        return 4;
    case 0x4efc40:
        return 1;
    case 0x4c62e0:
        return 5;
    case 0x4c7180:
        return 1;
    case 0x4c7780:
        return 1;
    default:
        return -1;
    }
}

// ---- Shared helpers ------------------------------------------------------------------------

// Original float constants: 0x513700, 0x513704, 0x513708 (palette), 0x51423c, 0x514240, 0x514244 (fade).

// operator new, cdecl, one argument.
uint32_t allocate(Run &run, uint32_t size) {
    return run.call(0x4f63ec, 0, {size});
}

// operator delete, cdecl, one argument.
void release(Run &run, uint32_t block) {
    run.call(0x4f6428, 0, {block});
}

// rand, cdecl, no arguments.
uint32_t callRand(Run &run) {
    return run.call(0x4a3050, 0);
}

// idiv remainder (CDQ then IDIV). The original traps on a zero divisor or overflow.
int32_t signedRemainder(Run &run, int32_t dividend, int32_t divisor) {
    if (divisor == 0)
        run.fail(CLAW_FAULT_ABI, 0);
    if (divisor == -1)
        return 0;
    return dividend % divisor;
}

// rep stosd of zero, then rep stosb of zero.
void zeroFill(Run &run, uint32_t destination, uint32_t bytes) {
    uint32_t words = bytes >> 2;
    uint32_t tail = bytes & 3;
    for (uint32_t i = 0; i < words; ++i) {
        run.put(destination, 0);
        destination += 4;
    }
    for (uint32_t i = 0; i < tail; ++i) {
        run.put8(destination, 0);
        destination += 1;
    }
}

// rep stosd of zero for a dword count.
void zeroWords(Run &run, uint32_t destination, uint32_t words) {
    for (uint32_t i = 0; i < words; ++i) {
        run.put(destination, 0);
        destination += 4;
    }
}

// rep movsd of a dword count.
void copyWords(Run &run, uint32_t destination, uint32_t source, uint32_t words) {
    for (uint32_t i = 0; i < words; ++i) {
        run.put(destination, run.get(source));
        destination += 4;
        source += 4;
    }
}

// Byte copy loop.
void copyBytes(Run &run, uint32_t destination, uint32_t source, uint32_t count) {
    for (uint32_t i = 0; i < count; ++i) {
        run.put8(destination + i, run.get8(source + i));
    }
}

// Signed division by 100 through the compiler's multiply by 0x51eb851f.
int32_t divideByHundred(uint32_t value) {
    int64_t product = int64_t(int32_t(0x51eb851f)) * int64_t(s32(value));
    int32_t high = int32_t(product >> 32);
    int32_t shifted = high >> 5;
    uint32_t sign = uint32_t(shifted) >> 31;
    return shifted + int32_t(sign);
}

// Growable pointer array shared by 0x4c62e0 and 0x4c7180: data +0x8, count +0xc,
// capacity +0x10, growth step +0x14. Adds one slot and stores `item` at the old count.
void appendPointer(Run &run, uint32_t manager, uint32_t item) {
    uint32_t count = run.get(manager + 0xc);
    uint32_t data = run.get(manager + 0x8);
    uint32_t wanted = count + 1;
    if (wanted == 0) {
        if (data != 0) {
            release(run, data);
            run.put(manager + 0x8, 0);
        }
        run.put(manager + 0x10, 0);
        run.put(manager + 0xc, 0);
    } else if (data == 0) {
        uint32_t created = allocate(run, wanted * 4);
        run.put(manager + 0x8, created);
        zeroFill(run, created, wanted * 4);
        run.put(manager + 0x10, wanted);
        run.put(manager + 0xc, wanted);
    } else {
        uint32_t capacity = run.get(manager + 0x10);
        if (s32(wanted) <= s32(capacity)) {
            if (s32(wanted) > s32(count)) {
                zeroWords(run, data + count * 4, wanted - count);
            }
            run.put(manager + 0xc, wanted);
        } else {
            uint32_t step = run.get(manager + 0x14);
            if (step == 0) {
                uint32_t bias = uint32_t(s32(count) >> 31) & 7;
                int32_t eighth = (s32(count + bias)) >> 3;
                if (eighth < 4) {
                    eighth = 4;
                } else if (eighth > 0x400) {
                    eighth = 0x400;
                }
                step = uint32_t(eighth);
            }
            uint32_t grown = step + capacity;
            if (!(s32(wanted) < s32(grown))) {
                grown = wanted;
            }
            uint32_t buffer = allocate(run, grown * 4);
            uint32_t oldCount = run.get(manager + 0xc);
            uint32_t oldData = run.get(manager + 0x8);
            uint32_t oldBytes = oldCount << 2;
            copyWords(run, buffer, oldData, oldBytes >> 2);
            uint32_t filled = run.get(manager + 0xc);
            zeroWords(run, buffer + filled * 4, wanted - filled);
            release(run, run.get(manager + 0x8));
            run.put(manager + 0x8, buffer);
            run.put(manager + 0xc, wanted);
            run.put(manager + 0x10, grown);
        }
    }
    uint32_t table = run.get(manager + 0x8);
    run.put(table + count * 4, item);
}

// ---- x87 helper ------------------------------------------------------------------------------

uint32_t lowWord(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    return uint32_t(bits);
}

uint32_t highWord(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    return uint32_t(bits >> 32);
}

// The x87 stack of an owned function, evolved only through the runtime's primitives.
struct Fpu {
    Run &run;
    ClawX87State state;

    explicit Fpu(Run &owner) : run(owner), state{} {
        state.size = sizeof(state);
        state.version = CLAW_X87_VERSION;
        state.control = 0x023f;
        state.status = 0;
    }

    uint64_t step(uint32_t operation, std::initializer_list<uint32_t> operands = {}) {
        return run.x87_step(operation, state, operands);
    }

    // FILD m32.
    void fild(uint32_t value) {
        step(CLAW_X87_I32, {value});
    }
    // FLD m64 (and FLD m32, whose operand widens exactly).
    void fld(double value) {
        step(CLAW_X87_F64, {lowWord(value), highWord(value)});
    }
    void fldSt(uint32_t index) {
        step(CLAW_X87_ST(CLAW_X87_LD_ST, index));
    }
    void xchSt(uint32_t index) {
        step(CLAW_X87_ST(CLAW_X87_XCH_ST, index));
    }
    void stpSt(uint32_t index) {
        step(CLAW_X87_ST(CLAW_X87_STP_ST, index));
    }
    void comSt(uint32_t index) {
        step(CLAW_X87_ST(CLAW_X87_COM_ST, index));
    }
    void mulTo0(uint32_t index) {
        step(CLAW_X87_ST(CLAW_X87_MUL_TO0, index));
    }
    void subTo0(uint32_t index) {
        step(CLAW_X87_ST(CLAW_X87_SUB_TO0, index));
    }
    void addToI(uint32_t index) {
        step(CLAW_X87_ST(CLAW_X87_ADD_TOI, index));
    }
    void addP(uint32_t index) {
        step(CLAW_X87_ST(CLAW_X87_ADDP, index));
    }
    void mulP(uint32_t index) {
        step(CLAW_X87_ST(CLAW_X87_MULP, index));
    }
    void divP(uint32_t index) {
        step(CLAW_X87_ST(CLAW_X87_DIVP, index));
    }
    // FMUL, FDIV, FADD, FSUBR with a float operand.
    void fmul(float value) {
        double wide = value;
        step(CLAW_X87_MUL_F64, {lowWord(wide), highWord(wide)});
    }
    void fdiv(float value) {
        double wide = value;
        step(CLAW_X87_DIV_F64, {lowWord(wide), highWord(wide)});
    }
    void fadd(float value) {
        double wide = value;
        step(CLAW_X87_ADD_F64, {lowWord(wide), highWord(wide)});
    }
    void fsubr(float value) {
        double wide = value;
        step(CLAW_X87_SUBR_F64, {lowWord(wide), highWord(wide)});
    }
    // FCOMP m32: compares ST(0) with the operand and pops.
    void fcomp(float value) {
        double wide = value;
        step(CLAW_X87_COMP_F64, {lowWord(wide), highWord(wide)});
    }
    // FSTP m32: stores ST(0) as a float and pops.
    float fstp32() {
        uint64_t bits = step(CLAW_X87_STP_F64);
        double wide;
        std::memcpy(&wide, &bits, 8);
        return float(wide);
    }
    // FSIN: the stored binary64 value goes through the C library and comes back.
    void fsin() {
        uint64_t bits = step(CLAW_X87_STP_F64);
        double wide;
        std::memcpy(&wide, &bits, 8);
        fld(std::sin(wide));
    }
    // FNSTSW AX, then TEST AH, 1: the C0 condition bit.
    bool below() const {
        return (state.status & 0x100) != 0;
    }
    // CALL 0x4a30e0: the original float to integer conversion consumes ST(0).
    uint32_t ftol() {
        state.popCount = 1;
        state.pushCount = 0;
        state.returned = 0;
        state.eax = 0;
        state.edx = 0;
        return run.call_x87_exact(0x4a30e0, 0, state);
    }
};

// ---- 0x4ed060 -----------------------------------------------------------------------------------

// 0x4ed060. thiscall, 0 stack arguments. Fade object constructor.
uint32_t function_4ed060(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x4ec8d0, receiver);
    // +0x0 vtable, +0x4c height, +0x50 width
    run.put(receiver + 0x0, 0x514228);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x4c, 0);
    return receiver;
}

// 0x4ed0a0. thiscall, 0 stack arguments. Destructor body; ends in a jump to 0x4ec920.
uint32_t function_4ed0a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x0, 0x514228);
    return run.call(0x4ec920, receiver);
}

// 0x4ed080. thiscall, 1 stack argument. Scalar deleting destructor.
uint32_t function_4ed080(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4ed0a0(run, receiver, nullptr);
    if ((arguments[0] & 1) != 0) {
        release(run, receiver);
    }
    return receiver;
}

// 0x4ed5d0. thiscall, 0 stack arguments. Rows plus span.
uint32_t function_4ed5d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t span = run.get(receiver + 0x54);
    uint32_t height = run.get(receiver + 0x4c);
    return span + height;
}

// ---- 0x4efc40 and 0x4efb00 -------------------------------------------------------------------------

// 0x4efc40. cdecl, 1 stack argument. Primality by trial division; anything below 3 counts as prime.
uint32_t function_4efc40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    int32_t value = s32(arguments[0]);
    int32_t divisor = 2;
    if (value <= divisor) {
        return 1;
    }
    do {
        if (value % divisor == 0) {
            return 0;
        }
        divisor += 1;
    } while (divisor < value);
    return 1;
}

// 0x4efb00. cdecl, 4 stack arguments (output, low, high, generator). Writes a scrambled order of
// the span low..high into `output`, using a multiplicative generator modulo a prime.
uint32_t function_4efb00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t output = arguments[0];
    int32_t low = s32(arguments[1]);
    int32_t high = s32(arguments[2]);
    int32_t generator = s32(arguments[3]);
    if (low > high || low == high) {
        return 0;
    }
    int32_t span = high - low;
    int32_t modulus = generator;
    int32_t candidate = span;
    while (candidate < 100000) {
        uint32_t probe[1] = {uint32_t(candidate)};
        if (function_4efc40(run, 0, probe) != 0) {
            modulus = candidate;
            break;
        }
        candidate += 1;
    }
    uint32_t table = allocate(run, uint32_t(modulus) * 4);
    if (table == 0) {
        return 0;
    }
    uint32_t multiplier = table;
    int32_t limit = modulus - 1;
    int32_t trial = 1;
    if (limit > trial) {
        do {
            bool unique = true;
            if (modulus > 0) {
                for (int32_t i = 0; i < modulus; ++i) {
                    run.put(table + uint32_t(i) * 4, 0);
                }
            }
            int32_t used = 0;
            int32_t current = generator;
            if (limit > 0) {
                do {
                    int32_t product = s32(uint32_t(trial) * uint32_t(current));
                    current = signedRemainder(run, product, modulus);
                    uint32_t slot = table + uint32_t(current) * 4 - 4;
                    if (run.get(slot) != 0) {
                        unique = false;
                        break;
                    }
                    used += 1;
                    run.put(slot, 1);
                } while (used < limit);
            }
            if (unique) {
                multiplier = uint32_t(trial);
                break;
            }
            trial += 1;
        } while (trial < limit);
    }
    if (modulus > 0) {
        int32_t current = generator;
        uint32_t cursor = output;
        int32_t remaining = modulus;
        do {
            int32_t product = s32(multiplier * uint32_t(current));
            current = signedRemainder(run, product, modulus);
            if (current - 1 <= span) {
                int32_t value = current + low - 1;
                int32_t clamped = value;
                if (!(value < high)) {
                    clamped = high;
                }
                if (clamped < 0) {
                    value = 0;
                } else if (!(value < high)) {
                    value = high;
                }
                run.put(cursor, uint32_t(value));
                cursor += 4;
            }
            remaining -= 1;
        } while (remaining != 0);
    }
    release(run, table);
    return 0;
}

// ---- 0x4ed0b0 -------------------------------------------------------------------------------------

// 0x4ed0b0. thiscall, 1 stack argument (descriptor). Prepares the fade from its descriptor.
// Fade object: +0x20 step, +0x24 and +0x28 default surfaces, +0x38 and +0x3c surfaces,
// +0x40 flag, +0x4c height, +0x50 width, +0x54 span, +0x58 percent.
// Descriptor: +0x4 first surface, +0x8 second surface, +0xc flag, +0x10 percent.
uint32_t function_4ed0b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t descriptor = arguments[0];
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x40, run.get(descriptor + 0xc));
    uint32_t first = run.get(descriptor + 0x4);
    if (first == 0) {
        run.put(receiver + 0x38, run.get(receiver + 0x24));
    } else {
        run.put(receiver + 0x38, first);
    }
    uint32_t second = run.get(descriptor + 0x8);
    if (second == 0) {
        second = run.get(receiver + 0x28);
    }
    run.put(receiver + 0x3c, second);
    uint32_t surface = run.get(receiver + 0x38);
    if (surface == 0) {
        return 0;
    }
    if (run.get(receiver + 0x3c) == 0) {
        run.put(receiver + 0x40, 1);
    }
    // Surface +0x14 height, +0x18 width.
    run.put(receiver + 0x50, run.get(surface + 0x18));
    uint32_t height = run.get(surface + 0x14);
    run.put(receiver + 0x4c, height);
    uint32_t percent = run.get(descriptor + 0x10);
    if (s32(percent) < 0) {
        return 0;
    }
    if (s32(percent) > 0x64) {
        return 0;
    }
    Fpu fpu(run);
    fpu.fild(percent);
    run.put(receiver + 0x58, percent);
    fpu.fmul(run.getf(0x51423c));
    fpu.fild(height);
    fpu.mulP(1);
    uint32_t span = fpu.ftol();
    run.put(receiver + 0x54, span);
    uint32_t cell = receiver + 0x3edc;
    uint32_t count = 0x7d0;
    do {
        run.put(cell - 0x3e80, 0);
        run.put(cell, 0);
        run.put(cell + 0x1f40, 0);
        uint32_t width = run.get(receiver + 0x50);
        uint32_t value = callRand(run);
        cell += 4;
        count -= 1;
        int32_t remains = signedRemainder(run, s32(value), s32(width));
        run.put(cell - 0x1f44, uint32_t(remains));
    } while (count != 0);
    uint32_t order[4] = {receiver + 0x5e1c, 0, run.get(receiver + 0x50), 1};
    function_4efb00(run, 0, order);
    return 1;
}

// ---- 0x4ed1a0 -------------------------------------------------------------------------------------

// Carry of one row: converts the scaled step into whole cells, advances the fraction at `cell`
// and returns the whole part in `whole` and the extra part from the fraction in `extra`.
void rowCarry(Run &run, Fpu &fpu, uint32_t cell, uint32_t delta, float ratio, uint32_t &whole,
              uint32_t &extra) {
    extra = 0;
    fpu.fild(delta);
    fpu.fmul(ratio);
    fpu.fldSt(0);
    whole = fpu.ftol();
    fpu.fild(whole);
    fpu.comSt(1);
    if (fpu.below()) {
        fpu.xchSt(1);
        fpu.subTo0(1);
        fpu.fadd(run.getf(cell));
        run.putf(cell, fpu.fstp32());
    } else {
        fpu.stpSt(0);
    }
    fpu.stpSt(0);
    fpu.fld(run.getf(cell));
    fpu.fcomp(run.getf(0x514244));
    if (!fpu.below()) {
        fpu.fld(run.getf(cell));
        extra = fpu.ftol();
        fpu.fild(extra);
        fpu.fsubr(run.getf(cell));
        run.putf(cell, fpu.fstp32());
    }
}

// 0x4ed1a0. thiscall, 1 stack argument (step). Advances the fade to `step`.
// +0x44 and +0x48 hold the locked pixel pointers of the two surfaces; surface +0x1c is the pitch,
// +0xac the bytes per pixel, +0x8 the DirectDraw interface.
uint32_t function_4ed1a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t amount = arguments[0];
    if (amount == 0) {
        return 0;
    }
    if (run.get(receiver + 0x38) != 0) {
        uint32_t pixels = run.call(0x4b9730, run.get(receiver + 0x38), {0});
        run.put(receiver + 0x44, pixels);
    }
    if (run.get(receiver + 0x3c) != 0) {
        uint32_t pixels = run.call(0x4b9730, run.get(receiver + 0x3c), {0});
        run.put(receiver + 0x48, pixels);
    }
    uint32_t span = run.get(receiver + 0x54);
    uint32_t firstSurface = run.get(receiver + 0x38);
    Fpu fpu(run);
    fpu.fild(run.get(receiver + 0x50));
    uint32_t height = run.get(receiver + 0x4c);
    uint32_t bytesPerPixel = run.get(firstSurface + 0xac);
    uint32_t divisor = span;
    uint32_t row = height - amount;
    uint32_t limit = height - amount + span;
    fpu.fild(divisor);
    fpu.divP(1);
    float ratio = fpu.fstp32();
    if (s32(row) < s32(limit)) {
        uint32_t cell = receiver + row * 4 + 0x3edc;
        do {
            if (s32(row) >= 0 && s32(row) < s32(height)) {
                uint32_t surface = run.get(receiver + 0x38);
                uint32_t pitch = run.get(surface + 0x1c);
                uint32_t pixels = run.get(receiver + 0x44);
                uint32_t destination = pitch * row + pixels;
                uint32_t progress = row + amount - height;
                // FILD qword of a zero-extended value.
                fpu.fld(double(progress));
                fpu.fild(divisor);
                fpu.divP(1);
                fpu.fmul(run.getf(0x514240));
                fpu.fsin();
                fpu.fild(run.get(receiver + 0x50));
                fpu.mulP(1);
                fpu.fdiv(ratio);
                uint32_t target = fpu.ftol();
                uint32_t offset = run.get(cell - 0x3e80);
                uint32_t delta = target - offset;
                uint32_t whole = 0;
                uint32_t extra = 0;
                if (run.get(receiver + 0x40) != 0) {
                    rowCarry(run, fpu, cell, delta, ratio, whole, extra);
                    uint32_t total = extra + whole;
                    if (s32(total) > 0) {
                        uint32_t remaining = total;
                        do {
                            uint32_t counter = run.get(cell - 0x1f40) + 1;
                            run.put(cell - 0x1f40, counter);
                            if (s32(counter) > s32(run.get(receiver + 0x50))) {
                                run.put(cell - 0x1f40, 0);
                            }
                            uint32_t slot = run.get(cell - 0x1f40);
                            uint32_t column = run.get(receiver + slot * 4 + 0x5e1c);
                            if (s32(bytesPerPixel) > 0) {
                                zeroFill(run, column * bytesPerPixel + destination, bytesPerPixel);
                            }
                            remaining -= 1;
                        } while (remaining != 0);
                    }
                    fpu.fld(ratio);
                    uint32_t held = run.get(cell - 0x3e80);
                    fpu.addToI(0);
                    run.put(cell - 0x3e80, held + delta);
                    uint32_t randoms = fpu.ftol();
                    if (s32(randoms) > 0) {
                        do {
                            uint32_t width = run.get(receiver + 0x50);
                            uint32_t value = callRand(run);
                            int32_t column = signedRemainder(run, s32(value), s32(width));
                            if (s32(bytesPerPixel) > 0) {
                                zeroFill(run, uint32_t(column) * bytesPerPixel + destination, bytesPerPixel);
                            }
                            randoms -= 1;
                        } while (randoms != 0);
                    }
                } else {
                    uint32_t otherSurface = run.get(receiver + 0x3c);
                    uint32_t otherPixels = run.get(receiver + 0x48);
                    uint32_t otherPitch = run.get(otherSurface + 0x1c);
                    uint32_t source = otherPitch * row + otherPixels;
                    rowCarry(run, fpu, cell, delta, ratio, whole, extra);
                    uint32_t total = extra + whole;
                    if (s32(total) > 0) {
                        uint32_t remaining = total;
                        do {
                            uint32_t counter = run.get(cell - 0x1f40) + 1;
                            run.put(cell - 0x1f40, counter);
                            if (s32(counter) > s32(run.get(receiver + 0x50))) {
                                run.put(cell - 0x1f40, 0);
                            }
                            uint32_t slot = run.get(cell - 0x1f40);
                            uint32_t column = run.get(receiver + slot * 4 + 0x5e1c);
                            if (s32(bytesPerPixel) > 0) {
                                uint32_t offsetInRow = column * bytesPerPixel;
                                copyBytes(run, offsetInRow + destination, source + offsetInRow, bytesPerPixel);
                            }
                            remaining -= 1;
                        } while (remaining != 0);
                    }
                    fpu.fld(ratio);
                    uint32_t held = run.get(cell - 0x3e80);
                    fpu.addToI(0);
                    run.put(cell - 0x3e80, held + delta);
                    uint32_t randoms = fpu.ftol();
                    if (s32(randoms) > 0) {
                        do {
                            uint32_t width = run.get(receiver + 0x50);
                            uint32_t value = callRand(run);
                            int32_t column = signedRemainder(run, s32(value), s32(width));
                            if (s32(bytesPerPixel) > 0) {
                                uint32_t offsetInRow = uint32_t(column) * bytesPerPixel;
                                copyBytes(run, offsetInRow + destination, source + offsetInRow, bytesPerPixel);
                            }
                            randoms -= 1;
                        } while (randoms != 0);
                    }
                }
            }
            height = run.get(receiver + 0x4c);
            divisor = run.get(receiver + 0x54);
            limit = height - amount + divisor;
            row += 1;
            cell += 4;
        } while (s32(row) < s32(limit));
    }
    for (uint32_t previous = run.get(receiver + 0x20); s32(previous) < s32(amount); ++previous) {
        uint32_t spanNow = run.get(receiver + 0x54);
        uint32_t heightNow = run.get(receiver + 0x4c);
        uint32_t line = spanNow - previous + heightNow - 1;
        if (s32(line) < 0 || s32(line) >= s32(heightNow)) {
            continue;
        }
        if (run.get(receiver + 0x40) != 0) {
            uint32_t surface = run.get(receiver + 0x38);
            uint32_t count = bytesPerPixel * run.get(receiver + 0x50);
            uint32_t start = run.get(surface + 0x1c) * line + run.get(receiver + 0x44);
            if (s32(count) > 0) {
                zeroFill(run, start, count);
            }
        } else {
            uint32_t other = run.get(receiver + 0x3c);
            uint32_t count = bytesPerPixel * run.get(receiver + 0x50);
            uint32_t source = run.get(other + 0x1c) * line + run.get(receiver + 0x48);
            uint32_t destination = run.get(run.get(receiver + 0x38) + 0x1c) * line + run.get(receiver + 0x44);
            if (s32(count) > 0) {
                copyBytes(run, destination, source, count);
            }
        }
    }
    run.put(receiver + 0x20, amount);
    uint32_t first = run.get(receiver + 0x38);
    if (first != 0) {
        uint32_t interface = run.get(first + 0x8);
        uint32_t method = run.get(run.get(interface) + 0x80);
        run.call(method, 0, {interface, 0});
    }
    uint32_t second = run.get(receiver + 0x3c);
    if (second != 0) {
        uint32_t interface = run.get(second + 0x8);
        uint32_t method = run.get(run.get(interface) + 0x80);
        run.call(method, 0, {interface, 0});
    }
    return 0;
}

// ---- 0x4c7780 and 0x4c7180 --------------------------------------------------------------------------

// 0x4c7780. thiscall, 1 stack argument (a CString passed by value). Loads a file into a list item.
// Locals: the CFile object at entry-0x1c.
uint32_t function_4c7780(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t file = run.automatic(-0x1c);
    uint32_t name = run.automatic(0x4);
    run.call(0x4f72c9, file);
    uint32_t opened = run.call(0x4f7448, file, {run.get(name), 0, 0});
    if (opened == 0) {
        run.call(0x4f7369, file);
        run.call(0x4f6584, name);
        return 0;
    }
    uint32_t result = run.call(0x4c7730, receiver, {file});
    run.call(0x4f766e, file);
    run.put(receiver + 0x0, result);
    run.call(0x4f7369, file);
    run.call(0x4f6584, name);
    return result;
}

// 0x4c7180. thiscall, 1 stack argument (a CString passed by value). Appends a new loaded list item.
// Locals: the copied CString at entry-0x30, passed by value to 0x4c7780.
uint32_t function_4c7180(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t created = allocate(run, 0xc);
    uint32_t item = 0;
    if (created != 0) {
        item = run.call(0x4c76d0, created);
    }
    appendPointer(run, receiver, item);
    uint32_t copy = run.automatic(-0x30);
    run.call(0x4f6449, copy, {run.automatic(0x4)});
    // The callee's entry frame sits below the pushed copy and the return word.
    uint32_t saved = run.frame;
    run.frame = copy - 4;
    uint32_t loaded = function_4c7780(run, item, nullptr);
    run.frame = saved;
    if (loaded == 0) {
        run.call(0x4c7510, receiver, {item});
        run.call(0x4f6584, run.automatic(0x4));
        return 0;
    }
    run.call(0x4f6584, run.automatic(0x4));
    return item;
}

// ---- 0x4c62e0 -----------------------------------------------------------------------------------------

// One colour of the first pass: scale a palette byte by percent, blend with the running ratio and
// convert. `last` selects the ending of the third colour. The x87 stack on entry is (u, t).
uint32_t blendFirstPass(Run &run, Fpu &fpu, uint32_t palette, uint32_t percent, bool last) {
    uint32_t sample = run.get8(palette);
    int32_t quotient = divideByHundred(percent * sample);
    fpu.fild(uint32_t(quotient));
    fpu.mulTo0(1);
    fpu.fild(sample);
    fpu.mulTo0(3);
    fpu.addP(1);
    fpu.fcomp(run.getf(0x513704));
    if (!fpu.below()) {
        if (last) {
            fpu.stpSt(0);
            fpu.stpSt(0);
        }
        fpu.fld(run.getf(0x513704));
    } else {
        uint32_t again = sample;
        if (!last) {
            again = run.get8(palette);
        }
        int32_t second = divideByHundred(percent * again);
        fpu.fild(uint32_t(second));
        fpu.mulTo0(1);
        fpu.fild(again);
        fpu.mulTo0(3);
        fpu.addP(1);
        if (last) {
            fpu.stpSt(2);
            fpu.stpSt(0);
        }
    }
    return fpu.ftol();
}

// One colour of the second pass. The x87 stack on entry is (w, s). `last` is the third colour.
uint32_t blendSecondPass(Run &run, Fpu &fpu, uint32_t palette, float scale, uint32_t colour) {
    uint32_t sample = run.get8(palette);
    float sampleFloat = 0;
    if (colour == 0) {
        fpu.fild(sample);
        fpu.fld(scale);
        fpu.fld(run.getf(0x513700));
        fpu.subTo0(3);
        fpu.xchSt(2);
        sampleFloat = fpu.fstp32();
        fpu.fmul(sampleFloat);
        fpu.fmul(run.getf(0x513708));
        fpu.fldSt(1);
        fpu.fmul(sampleFloat);
        fpu.xchSt(1);
        fpu.mulTo0(3);
        fpu.xchSt(1);
        fpu.addP(1);
    } else {
        fpu.fild(sample);
        fpu.fld(scale);
        fpu.fldSt(2);
        fpu.xchSt(1);
        fpu.mulTo0(2);
        fpu.xchSt(1);
        fpu.mulTo0(2);
        fpu.xchSt(1);
        fpu.fmul(run.getf(0x513708));
        fpu.mulTo0(4);
        fpu.xchSt(1);
        fpu.addP(1);
    }
    fpu.fcomp(run.getf(0x513704));
    if (colour != 0) {
        fpu.stpSt(0);
    }
    if (!fpu.below()) {
        if (colour == 2) {
            fpu.stpSt(0);
            fpu.stpSt(0);
        }
        fpu.fld(run.getf(0x513704));
    } else if (colour == 2) {
        fpu.fild(sample);
        fpu.fldSt(0);
        fpu.fmul(scale);
        fpu.xchSt(1);
        fpu.mulTo0(2);
        fpu.xchSt(1);
        fpu.fmul(run.getf(0x513708));
        fpu.mulP(3);
        fpu.addP(2);
        fpu.stpSt(0);
    } else {
        uint32_t again = run.get8(palette);
        fpu.fild(again);
        fpu.fldSt(0);
        fpu.fmul(scale);
        fpu.xchSt(1);
        fpu.mulTo0(2);
        fpu.xchSt(1);
        fpu.fmul(run.getf(0x513708));
        fpu.mulTo0(3);
        fpu.xchSt(1);
        fpu.addP(1);
    }
    return fpu.ftol();
}

// 0x4c62e0. thiscall, 5 stack arguments (palette, columns, rows, percent, shade). Builds a
// 256 step shade table from a 4 byte per entry palette and appends it to the receiver's list.
uint32_t function_4c62e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t palette = arguments[0];
    uint32_t columns = arguments[1];
    uint32_t rows = arguments[2];
    uint32_t percent = arguments[3];
    uint32_t shade = arguments[4];
    uint32_t created = allocate(run, 0xc);
    uint32_t item = 0;
    if (created != 0) {
        item = run.call(0x4c76d0, created);
    }
    if (item == 0) {
        return 0;
    }
    uint32_t total = rows + columns;
    uint32_t reserved = run.call(0x4c76f0, item, {total << 8});
    if (reserved == 0) {
        return 0;
    }
    appendPointer(run, receiver, item);
    // Item +0x8 holds the shade bytes.
    uint32_t output = run.get(item + 0x8);
    uint32_t cursor = palette + 2;
    uint32_t outer = 0x100;
    Fpu fpu(run);
    do {
        uint32_t index = 0;
        if (s32(columns) > 0) {
            float columnsFloat;
            fpu.fild(columns);
            columnsFloat = fpu.fstp32();
            do {
                fpu.fild(index);
                fpu.fdiv(columnsFloat);
                fpu.fld(run.getf(0x513700));
                fpu.subTo0(1);
                uint32_t first = blendFirstPass(run, fpu, cursor - 2, percent, false);
                uint32_t second = blendFirstPass(run, fpu, cursor - 1, percent, false);
                uint32_t third = blendFirstPass(run, fpu, cursor, percent, true);
                uint32_t value = run.call(0x4c7580, 0, {palette, first & 0xff, second & 0xff, third});
                run.put8(output + index, uint8_t(value));
                index += 1;
            } while (s32(index) < s32(columns));
        }
        // Brighten the three palette bytes around the cursor.
        uint32_t brighter = run.get8(cursor - 2) + 0x10;
        if (!(s32(brighter) < 0xff)) {
            brighter = 0xff;
        }
        run.put8(cursor - 2, uint8_t(brighter));
        brighter = run.get8(cursor - 1) + 0x10;
        if (!(s32(brighter) < 0xff)) {
            brighter = 0xff;
        }
        run.put8(cursor - 1, uint8_t(brighter));
        brighter = run.get8(cursor) + 0x10;
        if (!(s32(brighter) < 0xff)) {
            brighter = 0xff;
        }
        run.put8(cursor, uint8_t(brighter));
        uint32_t pixel = columns;
        if (s32(pixel) < s32(total)) {
            fpu.fild(shade);
            fpu.fild(rows);
            float rowsFloat = fpu.fstp32();
            float shadeFloat = fpu.fstp32();
            do {
                uint32_t distance = pixel - columns;
                fpu.fild(distance);
                fpu.fdiv(rowsFloat);
                uint32_t first = blendSecondPass(run, fpu, cursor - 2, shadeFloat, 0);
                uint32_t second = blendSecondPass(run, fpu, cursor - 1, shadeFloat, 1);
                uint32_t third = blendSecondPass(run, fpu, cursor, shadeFloat, 2);
                uint32_t value = run.call(0x4c7580, 0, {palette, first & 0xff, second & 0xff, third});
                run.put8(output + pixel, uint8_t(value));
                pixel += 1;
            } while (s32(pixel) < s32(total));
        }
        output += total;
        cursor += 4;
        outer -= 1;
    } while (outer != 0);
    return item;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4ed060:
        return function_4ed060(run, receiver, arguments);
    case 0x4ed080:
        return function_4ed080(run, receiver, arguments);
    case 0x4ed0a0:
        return function_4ed0a0(run, receiver, arguments);
    case 0x4ed0b0:
        return function_4ed0b0(run, receiver, arguments);
    case 0x4ed1a0:
        return function_4ed1a0(run, receiver, arguments);
    case 0x4ed5d0:
        return function_4ed5d0(run, receiver, arguments);
    case 0x4efb00:
        return function_4efb00(run, receiver, arguments);
    case 0x4efc40:
        return function_4efc40(run, receiver, arguments);
    case 0x4c62e0:
        return function_4c62e0(run, receiver, arguments);
    case 0x4c7180:
        return function_4c7180(run, receiver, arguments);
    case 0x4c7780:
        return function_4c7780(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_scene_fade_closure_02_entry, owned, body)
