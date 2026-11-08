// Level 1 player dynamite and dynamite states
//
#include "ClawRuntime.hpp"
#include <cstring>

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4084b0:
        return 1;
    case 0x4089d0:
        return 0;
    case 0x43a850:
        return 1;
    case 0x43a910:
        return 1;
    case 0x43b290:
        return 0;
    case 0x43b320:
        return 0;
    case 0x486e70:
        return 1;
    default:
        return -1;
    }
}

uint64_t qword(Run &run, uint32_t address) {
    uint32_t low = run.get(address);
    uint32_t high = run.get(address + 4);
    return uint64_t(low) | (uint64_t(high) << 32);
}

void storeQword(Run &run, uint32_t address, uint64_t bits) {
    run.put(address, uint32_t(bits));
    run.put(address + 4, uint32_t(bits >> 32));
}

// The original x87 register stack, driven one instruction at a time. Control
// word 0x023f is the startup state of the game.
struct Fpu {
    Run &run;
    ClawX87State state;

    explicit Fpu(Run &r) : run(r), state{} {
        state.size = sizeof(state);
        state.version = CLAW_X87_VERSION;
        state.control = 0x023f;
    }

    // fnstsw ah; test ah, 1
    bool c0() const {
        return ((state.status >> 8) & 1) != 0;
    }
    // fnstsw ah; test ah, 0x40
    bool c3() const {
        return ((state.status >> 14) & 1) != 0;
    }
    // fld qword ptr [mem]
    void load(uint64_t bits) {
        run.x87_step(CLAW_X87_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    // fild dword ptr [mem]
    void loadInt(uint32_t word) {
        run.x87_step(CLAW_X87_I32, state, {word});
    }
    // fld st(i)
    void dup(uint32_t i) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, i), state);
    }
    // fxch st(i)
    void exchange(uint32_t i) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, i), state);
    }
    // fst qword ptr [mem]
    uint64_t store() {
        return run.x87_step(CLAW_X87_ST_F64, state);
    }
    // fstp qword ptr [mem]
    uint64_t storePop() {
        return run.x87_step(CLAW_X87_STP_F64, state);
    }
    // fstp st(0)
    void discard() {
        run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), state);
    }
    void negate() {
        run.x87_step(CLAW_X87_CHS, state);
    }
    void absolute() {
        run.x87_step(CLAW_X87_ABS, state);
    }
    void squareRoot() {
        run.x87_step(CLAW_X87_SQRT, state);
    }
    // fadd qword ptr [mem]
    void add(uint64_t bits) {
        run.x87_step(CLAW_X87_ADD_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    // fsub qword ptr [mem]: ST(0) = ST(0) - operand
    void sub(uint64_t bits) {
        run.x87_step(CLAW_X87_SUB_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    // fsubr qword ptr [mem]: ST(0) = operand - ST(0)
    void subReverse(uint64_t bits) {
        run.x87_step(CLAW_X87_SUBR_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    // fmul qword ptr [mem]
    void mul(uint64_t bits) {
        run.x87_step(CLAW_X87_MUL_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    // fcom qword ptr [mem]
    void compare(uint64_t bits) {
        run.x87_step(CLAW_X87_COM_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    // fcomp qword ptr [mem]
    void comparePop(uint64_t bits) {
        run.x87_step(CLAW_X87_COMP_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    // fcomp st(i)
    void compareStPop(uint32_t i) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_COMP_ST, i), state);
    }
    // fcompp
    void comparePopPop() {
        run.x87_step(CLAW_X87_COMPP, state);
    }
    // fadd st(0), st(0)
    void doubleTop() {
        run.x87_step(CLAW_X87_ST(CLAW_X87_ADD_TOI, 0), state);
    }
    // fdiv st(0), st(i)
    void divBySt(uint32_t i) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, i), state);
    }
    // faddp st(i), st(0)
    void addPop(uint32_t i) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, i), state);
    }
    // fmulp st(i), st(0)
    void mulPop(uint32_t i) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_MULP, i), state);
    }
    // fsubp st(i), st(0): ST(i) = ST(i) - ST(0)
    void subPop(uint32_t i) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, i), state);
    }
    // fdivp st(i), st(0): ST(i) = ST(i) / ST(0)
    void divPop(uint32_t i) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_DIVP, i), state);
    }
};

// 0x486e70. Raises the global high-water mark 0x53c260 to the argument plus
// the base in 0x541328 when it is not already above it (unsigned).
uint32_t raiseMaximum(Run &run, uint32_t amount) {
    uint32_t reach = amount + run.get(0x541328);
    uint32_t current = run.get(0x53c260);
    if (current > reach)
        return 0;
    run.put(0x53c260, reach);
    return 0;
}

// 0x4084b0. Base constructor. Object fields: +0x0c owner, +0x12c actor
// record (flags at +0x08), +0x150 +0x154 +0x158 +0x15c +0x160 +0x164 +0x168
// dynamite state.
uint32_t constructBase(Run &run, uint32_t self, uint32_t owner) {
    run.call(0x473c50, self, {owner});
    run.put(self + 0x160, 0);
    run.put(self + 0x164, 0);
    run.put(self, 0x50b2d4);
    uint32_t actor = run.get(self + 0x12c);
    uint32_t flags = run.get(actor + 0x08);
    run.put(actor + 0x08, flags | 0x40);
    run.put(self + 0x150, 0);
    run.put(self + 0x158, 0);
    run.put(self + 0x15c, 0);
    run.put(self + 0x168, 0x4e2);
    run.put(self + 0x154, 0);
    return self;
}

// 0x43a910. Dynamite constructor.
uint32_t construct(Run &run, uint32_t self, uint32_t owner) {
    constructBase(run, self, owner);
    run.put(self, 0x50da04);
    run.call(0x4c7970, run.get(self + 0x12c), {0x526f78});
    // The owner argument slot is reused as the out-parameter of the lookups.
    uint32_t slot = run.automatic(4);
    uint32_t actor = run.get(self + 0x12c);
    uint32_t level = run.get(actor + 0x0c);
    run.put(slot, 0);
    uint32_t registry = run.get(level + 0x2c) + 0x10;
    run.call(0x4f6286, registry, {0x526f78, slot});
    run.put(self + 0x150, run.get(slot));
    actor = run.get(self + 0x12c);
    level = run.get(actor + 0x0c);
    run.put(slot, 0);
    registry = run.get(level + 0x2c) + 0x10;
    run.call(0x4f6286, registry, {0x526f64, slot});
    run.put(self + 0x178, run.get(slot));
    actor = run.get(self + 0x12c);
    level = run.get(actor + 0x0c);
    run.put(slot, 0);
    registry = run.get(level + 0x2c) + 0x10;
    run.call(0x4f6286, registry, {0x526f50, slot});
    run.put(self + 0x174, run.get(slot));
    actor = run.get(self + 0x12c);
    level = run.get(actor + 0x0c);
    uint32_t sounds = run.get(level + 0x28);
    uint32_t boom = run.call(0x4061b0, sounds, {0x526f40});
    run.put(self + 0x17c, boom);
    run.put(self + 0x180, 0);
    run.call(0x40fe90, run.get(self + 0x12c), {0xffffffce, 0xffffffce, 0x32, 0x32});
    run.call(0x406290, run.get(self + 0x12c));
    actor = run.get(self + 0x12c);
    run.put(actor + 0xd0, 4);
    actor = run.get(self + 0x12c);
    uint32_t flags = run.get(actor + 0x08);
    run.put(actor + 0x08, flags | 0x80);
    run.call(0x406240, run.get(self + 0x12c));
    uint32_t state = run.get(self + 0x0c);
    if (run.get(state + 0x64) == 0) {
        uint32_t priority = run.get(state + 0x64);
        if (priority != 0x137e) {
            run.put(state + 0x64, 0x137e);
            uint32_t stateFlags = run.get(state + 0x08);
            run.put(state + 0x08, stateFlags | 0x20000);
        }
    }
    run.put(self + 0x124, 8);
    run.put(self + 0x15c, 2);
    run.put(self + 0x168, 0x4e2);
    run.put(self + 0x40, 0);
    run.put(self + 0x44, 0x409f4000);
    // Launch velocity solve. Doubles: +0x38 +0x40 +0x48 direction, +0x68
    // +0x70 +0x78 position, results +0x50 +0x58 +0x60.
    uint32_t spare = run.get(self + 0x0c);
    Fpu fp(run);
    fp.load(qword(run, self + 0x68));
    fp.loadInt(run.get(spare + 0x158));
    fp.load(qword(run, self + 0x70));
    fp.exchange(1);
    fp.addPop(2);
    fp.exchange(1);
    uint64_t local48 = fp.store();
    fp.sub(qword(run, self + 0x68));
    fp.load(qword(run, self + 0x38));
    fp.load(qword(run, self + 0x40));
    fp.exchange(3);
    fp.sub(qword(run, self + 0x70));
    fp.load(qword(run, self + 0x78));
    fp.load(qword(run, self + 0x48));
    fp.exchange(4);
    uint64_t local10 = fp.store();
    fp.exchange(2);
    uint64_t local18 = fp.store();
    fp.exchange(1);
    fp.negate();
    uint64_t local20 = fp.store();
    fp.exchange(3);
    uint64_t local28 = fp.store();
    fp.exchange(5);
    uint64_t local30 = fp.store();
    fp.exchange(4);
    uint64_t local38 = fp.store();
    fp.load(local28);
    fp.mul(local10);
    fp.negate();
    fp.load(local30);
    fp.mul(local18);
    fp.subPop(1);
    fp.load(local38);
    fp.mul(local20);
    fp.subPop(1);
    local48 = fp.storePop();
    fp.exchange(5);
    fp.mul(local28);
    fp.load(local48);
    fp.exchange(5);
    fp.mul(local30);
    fp.addPop(1);
    fp.exchange(5);
    fp.mul(local38);
    fp.addPop(5);
    fp.exchange(1);
    fp.mul(local10);
    fp.exchange(4);
    uint64_t local40 = fp.storePop();
    fp.mul(local18);
    fp.exchange(1);
    fp.mul(local20);
    fp.exchange(1);
    fp.addPop(3);
    fp.exchange(1);
    fp.mul(qword(run, 0x50d9e0));
    fp.exchange(1);
    fp.addPop(2);
    fp.exchange(1);
    fp.mul(local40);
    fp.mul(qword(run, 0x50d9d8));
    fp.squareRoot();
    fp.exchange(1);
    fp.subPop(1);
    fp.mul(qword(run, 0x50d9e8));
    fp.squareRoot();
    uint64_t local08 = fp.store();
    fp.comparePop(qword(run, 0x513e20));
    if (fp.c0()) {
        run.put(self + 0x50, 0);
        run.put(self + 0x58, 0);
        run.put(self + 0x60, 0);
        run.put(self + 0x54, 0);
        run.put(self + 0x5c, 0);
        run.put(self + 0x64, 0);
    } else {
        fp.load(local40);
        fp.mul(qword(run, 0x50d9f0));
        fp.load(qword(run, 0x513e20));
        fp.negate();
        fp.dup(1);
        fp.comparePopPop();
        bool outside = fp.c0();
        if (!outside) {
            fp.compare(qword(run, 0x513e20));
            outside = !(fp.c0() || fp.c3());
        }
        if (!outside) {
            fp.discard();
            fp.load(local18);
            fp.load(local10);
            fp.load(local20);
            fp.exchange(2);
            fp.absolute();
            fp.exchange(1);
            fp.absolute();
            fp.addPop(1);
            fp.exchange(1);
            fp.absolute();
            fp.load(local10);
            fp.exchange(1);
            fp.addPop(2);
            fp.load(local18);
            fp.load(local20);
            fp.exchange(2);
            fp.divBySt(3);
            fp.exchange(1);
            fp.divBySt(3);
            fp.exchange(2);
            fp.divBySt(3);
            fp.exchange(1);
            fp.mul(local08);
            fp.exchange(2);
            fp.mul(local08);
            fp.exchange(1);
            fp.mul(local08);
            fp.exchange(2);
            uint64_t x = fp.storePop();
            storeQword(run, self + 0x50, x);
        } else {
            fp.load(local08);
            fp.mul(local08);
            fp.exchange(1);
            fp.doubleTop();
            fp.exchange(1);
            fp.sub(local48);
            fp.exchange(1);
            fp.divPop(1);
            fp.dup(0);
            fp.squareRoot();
            fp.dup(1);
            fp.dup(2);
            fp.exchange(1);
            fp.mul(local28);
            fp.exchange(2);
            fp.exchange(3);
            fp.exchange(1);
            fp.mul(local30);
            fp.exchange(1);
            fp.mul(local38);
            fp.exchange(2);
            fp.mul(qword(run, 0x50d9e8));
            fp.exchange(1);
            fp.mul(qword(run, 0x50d9e8));
            fp.exchange(1);
            fp.subReverse(local10);
            fp.exchange(2);
            fp.mul(qword(run, 0x50d9e8));
            fp.exchange(1);
            fp.subReverse(local18);
            fp.exchange(1);
            fp.subReverse(local20);
            fp.exchange(2);
            fp.divBySt(3);
            fp.exchange(1);
            fp.divBySt(3);
            fp.exchange(2);
            fp.divBySt(3);
            fp.exchange(1);
            uint64_t x = fp.storePop();
            storeQword(run, self + 0x50, x);
            fp.exchange(1);
        }
        uint64_t y = fp.storePop();
        storeQword(run, self + 0x58, y);
        uint64_t z = fp.storePop();
        storeQword(run, self + 0x60, z);
        fp.discard();
    }
    uint32_t tail = run.get(self + 0x0c);
    fp.load(qword(run, self + 0x58));
    uint32_t doubled = run.get(tail + 0x158) << 1;
    uint32_t sign = uint32_t(s32(doubled) >> 31);
    uint32_t magnitude = (doubled ^ sign) - sign;
    fp.loadInt(magnitude);
    fp.subPop(1);
    uint64_t adjusted = fp.storePop();
    storeQword(run, self + 0x58, adjusted);
    run.put(self + 0x170, 1);
    return self;
}

// 0x43a850. State callback on the owner object: the state record is the
// owner's +0x6c, its command at +0x1c and its object at +0x18.
uint32_t callback(Run &run, uint32_t owner) {
    uint32_t state = run.get(owner + 0x6c);
    uint32_t command = run.get(state + 0x1c);
    if (command > 0x1d) {
        if (command == 0x1e) {
            run.vcall(run.get(state + 0x18), 0x1c);
            return 1;
        }
        if (command == 0x3e8)
            return 1;
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    if (command == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
        return 1;
    }
    if (command != 0) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    run.put(state + 0x1c, 0x3e8);
    uint32_t memory = run.call(0x4f63ec, 0, {0x188});
    uint32_t object = 0;
    if (memory)
        object = construct(run, memory, owner);
    run.vcall(object, 0x10);
    run.put(state + 0x18, object);
    return 1;
}

// 0x43b290.
uint32_t arm(Run &run, uint32_t self) {
    uint32_t actor = run.get(self + 0x12c);
    uint32_t flags = run.get(actor + 0x08);
    run.put(actor + 0x08, flags | 0x80);
    uint32_t step = run.get(0x5430c4);
    uint32_t result = run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {step});
    if (result == 1) {
        if (run.get(self + 0x180) == 0) {
            run.put(self + 0x180, 1);
            raiseMaximum(run, 0x1f4);
            actor = run.get(self + 0x12c);
            flags = run.get(actor + 0x08);
            run.put(actor + 0x08, flags & 0xffffff7f);
        }
    }
    uint32_t record = run.get(self + 0x12c);
    if (run.get(record + 0x1a4) != 0) {
        if (run.get(record + 0x19c) == 0) {
            uint32_t recordFlags = run.get(record + 0x08);
            run.put(record + 0x08, recordFlags | 0x10000);
        }
    }
    return 0;
}

// 0x4089d0. Per-frame update: +0x12c actor record, +0x154 lit fuse object,
// +0x158 and +0x15c fuse counters, +0x160 start time, +0x164 window.
uint32_t update(Run &run, uint32_t self) {
    uint32_t step = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {step});
    uint32_t clock = run.get(0x537210);
    uint32_t started = run.get(self + 0x160);
    uint32_t window = run.get(self + 0x164);
    if (clock - started >= window)
        run.vcall(self, 0x38);
    uint32_t state = run.get(self + 0x0c);
    if (run.get(state + 0xcc) != 1)
        return 0;
    run.vcall(self, 0x34);
    uint32_t lit = run.get(self + 0x154);
    uint32_t litFlag = run.get(0x532c0c);
    uint32_t litValue = run.get(0x532c10);
    if (lit != 0) {
        if (litFlag != 0)
            run.call(0x4b45f0, run.get(lit + 0x10), {litValue, 0, 0, 0});
    }
    uint32_t count = run.get(self + 0x158);
    uint32_t limit = run.get(self + 0x15c);
    if (count == limit) {
        run.put(self + 0xc8, 1);
        run.vcall(self, 0x30);
        return 0;
    }
    uint32_t owner = run.get(self + 0x0c);
    count = count + 1;
    run.put(self + 0x158, count);
    run.put(owner + 0xcc, 8);
    Fpu fp(run);
    fp.load(qword(run, self + 0x70));
    fp.sub(qword(run, 0x50b318));
    fp.dup(0);
    fp.load(qword(run, self + 0x40));
    fp.comparePop(qword(run, 0x50b320));
    if (fp.c3()) {
        fp.discard();
        fp.load(qword(run, self + 0x58));
    } else {
        fp.sub(qword(run, self + 0x70));
        fp.load(qword(run, self + 0x58));
        fp.exchange(1);
        fp.mul(qword(run, self + 0x40));
        fp.dup(1);
        fp.mulPop(2);
        fp.load(qword(run, 0x50b320));
        fp.exchange(1);
        fp.mul(qword(run, 0x50b328));
        fp.subPop(2);
        fp.compareStPop(1);
        if (!(fp.c0() || fp.c3())) {
            fp.discard();
            fp.load(qword(run, 0x50b320));
        }
        fp.squareRoot();
        fp.load(qword(run, self + 0x58));
        fp.comparePop(qword(run, 0x50b320));
        if (fp.c0() || fp.c3())
            fp.negate();
    }
    uint64_t velocity = fp.storePop();
    storeQword(run, self + 0x58, velocity);
    run.put(self + 0xb8, 0);
    run.put(self + 0xbc, 0xbff00000);
    uint64_t height = fp.storePop();
    storeQword(run, self + 0x70, height);
    fp.load(qword(run, self + 0x50));
    fp.load(qword(run, self + 0x58));
    fp.mul(qword(run, 0x50b338));
    fp.exchange(1);
    fp.mul(qword(run, 0x50b330));
    fp.exchange(1);
    uint64_t scaledVelocity = fp.storePop();
    storeQword(run, self + 0x58, scaledVelocity);
    run.put(self + 0x60, 0);
    run.put(self + 0x64, 0);
    uint64_t scaledHorizontal = fp.storePop();
    storeQword(run, self + 0x50, scaledHorizontal);
    return 0;
}

// 0x4a30e0 (C runtime __ftol): truncates ST(0) toward zero to 64 bits and
// returns the low word. NaN and values outside the 64-bit range give the
// integer indefinite 0x8000000000000000, whose low word is zero.
uint32_t truncateLow(uint64_t bits) {
    double value;
    std::memcpy(&value, &bits, 8);
    if (!(value > -9223372036854775809.0 && value < 9223372036854775808.0))
        return 0;
    int64_t whole = int64_t(value);
    return uint32_t(whole);
}

// Random value in [low, high] as the original draws it; a zero span (the
// wrapped count) picks one end by the low bit.
uint32_t draw(Run &run, uint32_t low, uint32_t high) {
    uint32_t span = (high - low) + 1;
    if (span == 0) {
        uint32_t bit = run.call(0x4a3050, 0);
        if (bit & 1)
            return low;
        return high;
    }
    uint32_t value = run.call(0x4a3050, 0);
    int64_t remainder = int64_t(s32(value)) % int64_t(s32(span));
    return uint32_t(remainder) + low;
}

// 0x43b320. Fuse: runs the update, then spawns +0x170 sparkle objects at a
// random place inside the owner's rectangle (+0x118 +0x11c +0x120 +0x124).
uint32_t fuse(Run &run, uint32_t self) {
    update(run, self);
    uint32_t index = 0;
    if (s32(run.get(self + 0x170)) <= 0)
        return 0;
    do {
        uint32_t xLow = run.get(self + 0x68);
        uint32_t xHigh = run.get(self + 0x6c);
        uint64_t xBase = uint64_t(xLow) | (uint64_t(xHigh) << 32);
        uint32_t owner = run.get(self + 0x0c);
        uint32_t xValue = draw(run, run.get(owner + 0x118), run.get(owner + 0x120));
        Fpu fx(run);
        fx.loadInt(xValue);
        fx.add(xBase);
        uint64_t xBits = fx.storePop();
        uint32_t x = truncateLow(xBits);
        uint32_t yLow = run.get(self + 0x70);
        uint32_t yHigh = run.get(self + 0x74);
        uint64_t yBase = uint64_t(yLow) | (uint64_t(yHigh) << 32);
        owner = run.get(self + 0x0c);
        uint32_t yValue = draw(run, run.get(owner + 0x11c), run.get(owner + 0x124));
        owner = run.get(self + 0x0c);
        uint32_t depth = run.get(owner + 0x64) - 1;
        Fpu fy(run);
        fy.loadInt(yValue);
        fy.add(yBase);
        uint64_t yBits = fy.storePop();
        uint32_t y = truncateLow(yBits);
        uint32_t service = run.get(run.get(run.get(self + 0x130) + 0x0c) + 0x08);
        uint32_t object = run.call(0x4c8da0, service, {0, x, y, depth, 0x522594, 0x40000});
        uint32_t method = run.get(run.get(object + 0x6c) + 0x10);
        run.call(method, 0, {object});
        index = index + 1;
    } while (s32(index) < s32(run.get(self + 0x170)));
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4084b0:
        return constructBase(run, receiver, arguments[0]);
    case 0x4089d0:
        return update(run, receiver);
    case 0x43a850:
        return callback(run, arguments[0]);
    case 0x43a910:
        return construct(run, receiver, arguments[0]);
    case 0x43b290:
        return arm(run, receiver);
    case 0x43b320:
        return fuse(run, receiver);
    case 0x486e70:
        return raiseMaximum(run, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_dynamite_01_entry, owned, body)
