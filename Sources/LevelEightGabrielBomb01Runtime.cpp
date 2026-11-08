// Level 8 Gabriel bomb closure
//
// Gabriel's bomb object: the logic state machine, state dispatch, the
// constructor, the throw trajectory, and the fall and explosion updates.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4459d0:
        return 1;
    case 0x445af0:
        return 1;
    case 0x445ef0:
        return 1;
    case 0x446130:
        return 1;
    case 0x446340:
        return 0;
    case 0x4463f0:
        return 0;
    case 0x446490:
        return 0;
    default:
        return -1;
    }
}

// Explicit x87 register-stack sequence at the startup control word.
struct Fpu {
    Run &run;
    ClawX87State state;

    explicit Fpu(Run &r) : run(r), state{} {
        state.size = sizeof(state);
        state.version = CLAW_X87_VERSION;
        state.control = 0x023f;
        state.status = 0;
    }

    uint64_t bits(uint32_t address) {
        uint64_t low = run.get(address);
        uint64_t high = run.get(address + 4);
        return low | (high << 32);
    }

    // Memory-operand form: the operand is a binary64 as low and high words.
    uint64_t stepBits(uint32_t operation, uint64_t operand) {
        uint32_t low = uint32_t(operand);
        uint32_t high = uint32_t(operand >> 32);
        return run.x87_step(operation, state, {low, high});
    }

    void ld(uint64_t operand) {
        stepBits(CLAW_X87_F64, operand);
    }

    void fild(uint32_t word) {
        run.x87_step(CLAW_X87_I32, state, {word});
    }

    void sub(uint64_t operand) {
        stepBits(CLAW_X87_SUB_F64, operand);
    }

    void subr(uint64_t operand) {
        stepBits(CLAW_X87_SUBR_F64, operand);
    }

    void mul(uint64_t operand) {
        stepBits(CLAW_X87_MUL_F64, operand);
    }

    void reg(uint32_t form, uint32_t index) {
        run.x87_step(CLAW_X87_ST(form, index), state);
    }

    void xch(uint32_t index) {
        reg(CLAW_X87_XCH_ST, index);
    }

    void plain(uint32_t operation) {
        run.x87_step(operation, state);
    }

    uint64_t fst() {
        return run.x87_step(CLAW_X87_ST_F64, state);
    }

    uint64_t fstp() {
        return run.x87_step(CLAW_X87_STP_F64, state);
    }

    // The condition-code byte of the status word (AH after FNSTSW AX).
    uint32_t conditions() const {
        return (state.status >> 8) & 0xff;
    }
};

void storePair(Run &run, uint32_t address, uint64_t value) {
    run.put(address, uint32_t(value));
    run.put(address + 4, uint32_t(value >> 32));
}

// 0x445ef0. thiscall, one argument. Builds the bomb: base constructor,
// vtable, resource lookups and the fixed starting field values.
uint32_t construct(Run &run, uint32_t self, uint32_t argument) {
    run.call(0x4084b0, self, {argument});
    // +0x00 vtable
    run.put(self, 0x50ded4);
    // +0x12c sprite holder
    uint32_t holder = run.get(self + 0x12c);
    if (run.get(holder + 0x170) == 0)
        run.call(0x4c7970, holder, {0x527878});
    // the out value of each lookup lives in the first argument slot
    uint32_t slot = run.automatic(4);
    uint32_t table = 0;
    holder = run.get(self + 0x12c);
    table = run.get(run.get(holder + 0xc) + 0x2c);
    run.put(slot, 0);
    run.call(0x4f6286, table + 0x10, {0x527860, slot});
    run.put(self + 0x150, run.get(slot));
    holder = run.get(self + 0x12c);
    table = run.get(run.get(holder + 0xc) + 0x2c);
    run.put(slot, 0);
    run.call(0x4f6286, table + 0x10, {0x527860, slot});
    run.put(self + 0x148, run.get(slot));
    holder = run.get(self + 0x12c);
    table = run.get(run.get(holder + 0xc) + 0x2c);
    run.put(slot, 0);
    run.call(0x4f6286, table + 0x10, {0x527844, slot});
    run.put(self + 0x170, run.get(slot));
    holder = run.get(self + 0x12c);
    table = run.get(run.get(holder + 0xc) + 0x28);
    run.put(slot, 0);
    run.call(0x4f6286, table + 0x10, {0x527824, slot});
    run.put(self + 0x174, run.get(slot));
    holder = run.get(self + 0x12c);
    table = run.get(run.get(holder + 0xc) + 0x28);
    run.put(slot, 0);
    run.call(0x4f6286, table + 0x10, {0x527804, slot});
    run.put(self + 0x178, run.get(slot));
    uint32_t sound = run.get(self + 0x12c);
    sound = run.get(run.get(sound + 0xc) + 0x28);
    run.put(self + 0x17c, run.call(0x4061b0, sound, {0x5277e4}));
    sound = run.get(self + 0x12c);
    sound = run.get(run.get(sound + 0xc) + 0x28);
    run.put(self + 0x180, run.call(0x4061b0, sound, {0x5277c4}));
    sound = run.get(self + 0x12c);
    sound = run.get(run.get(sound + 0xc) + 0x28);
    run.put(self + 0x184, run.call(0x4061b0, sound, {0x5277c4}));
    sound = run.get(self + 0x12c);
    sound = run.get(run.get(sound + 0xc) + 0x28);
    run.put(self + 0x188, run.call(0x4061b0, sound, {0x5277c4}));
    run.put(self + 0x18c, 0);
    holder = run.get(self + 0x12c);
    run.call(0x40fe90, holder, {0xffffffce, 0xffffffce, 0x32, 0x32});
    holder = run.get(self + 0x12c);
    run.put(holder + 0xd0, 0x40);
    holder = run.get(self + 0x12c);
    run.call(0x406290, holder);
    uint32_t owner = run.get(self + 0xc);
    if (run.get(owner + 0x104) == 0)
        run.put(owner + 0x104, 0xf);
    holder = run.get(self + 0x12c);
    uint32_t flags = run.get(holder + 0x164);
    flags |= 0x2020;
    run.put(holder + 0x164, flags);
    owner = run.get(self + 0xc);
    run.put(self + 0x15c, 0);
    run.put(self + 0x168, 0x2710);
    run.put(owner + 0xcc, 7);
    run.put(self + 0x190, 0);
    return self;
}

uint32_t function_445ef0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return construct(run, receiver, arguments[0]);
}

// 0x4459d0. cdecl, one argument: the owning actor. Runs one logic step of
// the bomb held in the actor's state record, creating the bomb on the first.
uint32_t function_4459d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    // +0x6c state record; +0x1c state number, +0x18 the bomb object.
    uint32_t record = run.get(actor + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state > 0x1d) {
        if (state == 0x1e) {
            uint32_t bomb = run.get(record + 0x18);
            run.vcall(bomb, 0x1c);
            return 1;
        }
        if (state == 0x3e8)
            return 1;
        run.call(0x4dc870, 0, {run.get(record + 0x18)});
        return 1;
    }
    if (state == 0x1d) {
        uint32_t bomb = run.get(record + 0x18);
        run.vcall(bomb, 0x20);
        return 1;
    }
    if (state != 0) {
        run.call(0x4dc870, 0, {run.get(record + 0x18)});
        return 1;
    }
    run.put(record + 0x1c, 0x3e8);
    uint32_t memory = run.call(0x4f63ec, 0, {0x198});
    uint32_t bomb = 0;
    if (memory) {
        // The constructor is entered with its own return word and argument
        // pushed below this function's saved registers: entry minus 28.
        uint32_t saved = run.frame;
        run.frame = saved - 28;
        bomb = construct(run, memory, actor);
        run.frame = saved;
    }
    run.vcall(bomb, 0x10);
    run.put(record + 0x18, bomb);
    return 1;
}

// Handler slot for `state`: (state - lowest key) * entry size + entries base.
// Globals: 0x537768 entries, 0x537770 entry size.
uint32_t entryAddress(Run &run, uint32_t state, uint32_t low) {
    uint32_t base = run.get(0x537768);
    uint32_t size = run.get(0x537770);
    uint32_t offset = (state - low) * size;
    return offset + base;
}

// 0x445af0. thiscall, one argument. Calls the handler registered for the
// state number, or the generic handler at 0x408580 when its slot is empty.
uint32_t function_445af0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t state = arguments[0];
    uint32_t low = run.get(0x537760);
    run.put(0x537778, 0);
    uint32_t entry = 0;
    bool inRange = !(s32(state) < s32(low));
    if (inRange)
        inRange = !(s32(state) > s32(run.get(0x537764)));
    if (inRange) {
        entry = entryAddress(run, state, low);
    } else {
        uint32_t found = run.call(0x4db6e0, 0x537758, {state, 0});
        if (found) {
            low = run.get(0x537760);
            entry = entryAddress(run, state, low);
        } else {
            uint32_t reason = run.get(0x544b4c);
            uint32_t value = run.call(0x4db5f0, 0);
            uint32_t owner = run.get(0x53775c);
            run.put(0x544b14, value);
            run.call(0x4db4d0, owner, {0x537758, reason, 0xc});
            entry = run.get(0x53776c);
            low = run.get(0x537760);
        }
    }
    if (run.get(entry) == 0) {
        run.call(0x408580, receiver, {state});
        return 0;
    }
    run.put(0x537778, 0);
    inRange = !(s32(state) < s32(low));
    if (inRange)
        inRange = !(s32(state) > s32(run.get(0x537764)));
    if (!inRange) {
        uint32_t found = run.call(0x4db6e0, 0x537758, {state, 0});
        if (!found) {
            uint32_t reason = run.get(0x544b4c);
            uint32_t value = run.call(0x4db5f0, 0);
            uint32_t owner = run.get(0x53775c);
            run.put(0x544b14, value);
            run.call(0x4db4d0, owner, {0x537758, reason, 0xc});
            entry = run.get(0x53776c);
            run.call(run.get(entry), receiver);
            return 0;
        }
        low = run.get(0x537760);
    }
    entry = entryAddress(run, state, low);
    run.call(run.get(entry), receiver);
    return 0;
}

// 0x446130. thiscall, one argument: an integer added to and removed again
// from the x coordinate. Solves the launch velocity (+0x50, +0x58, +0x60)
// for a throw toward the aim offset, in the original x87 order.
// Fields: +0x38 and +0x48 gravity terms, +0x40 launch speed (2000.0),
// +0x68 x, +0x70 y, +0x78 z.
uint32_t function_446130(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    run.put(self + 0x40, 0);
    run.put(self + 0x44, 0x409f4000);
    Fpu fpu(run);
    fpu.ld(fpu.bits(self + 0x68));
    fpu.ld(fpu.bits(self + 0x70));
    fpu.fild(arguments[0]);
    fpu.reg(CLAW_X87_ADDP, 2);
    fpu.ld(fpu.bits(self + 0x38));
    fpu.xch(2);
    fpu.sub(fpu.bits(self + 0x68));
    fpu.ld(fpu.bits(self + 0x40));
    fpu.xch(2);
    fpu.sub(fpu.bits(self + 0x70));
    fpu.ld(fpu.bits(self + 0x78));
    fpu.ld(fpu.bits(self + 0x48));
    fpu.xch(3);
    uint64_t local8 = fpu.fst();
    fpu.xch(2);
    uint64_t local10 = fpu.fst();
    fpu.xch(1);
    fpu.plain(CLAW_X87_CHS);
    uint64_t local18 = fpu.fst();
    fpu.xch(5);
    uint64_t local20 = fpu.fst();
    fpu.xch(4);
    uint64_t local28 = fpu.fst();
    fpu.xch(3);
    uint64_t local30 = fpu.fst();
    fpu.ld(local20);
    fpu.mul(local8);
    fpu.plain(CLAW_X87_CHS);
    fpu.ld(local28);
    fpu.mul(local10);
    fpu.reg(CLAW_X87_SUBP, 1);
    fpu.ld(local30);
    fpu.mul(local18);
    fpu.reg(CLAW_X87_SUBP, 1);
    uint64_t local40 = fpu.fstp();
    fpu.xch(4);
    fpu.mul(local20);
    fpu.ld(local40);
    fpu.xch(4);
    fpu.mul(local28);
    fpu.reg(CLAW_X87_ADDP, 1);
    fpu.xch(4);
    fpu.mul(local30);
    fpu.reg(CLAW_X87_ADDP, 4);
    fpu.xch(1);
    fpu.mul(local8);
    fpu.xch(3);
    uint64_t local38 = fpu.fstp();
    fpu.mul(local10);
    fpu.xch(3);
    fpu.mul(local18);
    fpu.xch(3);
    fpu.reg(CLAW_X87_ADDP, 2);
    fpu.mul(fpu.bits(0x50df20));
    fpu.xch(2);
    fpu.reg(CLAW_X87_ADDP, 1);
    fpu.mul(local38);
    fpu.mul(fpu.bits(0x50df18));
    fpu.plain(CLAW_X87_SQRT);
    fpu.xch(1);
    fpu.reg(CLAW_X87_SUBP, 1);
    fpu.mul(fpu.bits(0x50df28));
    fpu.plain(CLAW_X87_SQRT);
    uint64_t local0 = fpu.fst();
    fpu.stepBits(CLAW_X87_COMP_F64, fpu.bits(0x513e20));
    // fnstsw ax; test ah, 1: below the threshold
    if (fpu.conditions() & 0x01) {
        run.put(self + 0x50, 0);
        run.put(self + 0x58, 0);
        run.put(self + 0x60, 0);
        run.put(self + 0x54, 0);
        run.put(self + 0x5c, 0);
        run.put(self + 0x64, 0);
        return 0;
    }
    fpu.ld(local38);
    fpu.mul(fpu.bits(0x50df30));
    fpu.ld(fpu.bits(0x513e20));
    fpu.plain(CLAW_X87_CHS);
    fpu.reg(CLAW_X87_LD_ST, 1);
    fpu.plain(CLAW_X87_COMPP);
    bool general = (fpu.conditions() & 0x01) != 0;
    if (!general) {
        fpu.stepBits(CLAW_X87_COM_F64, fpu.bits(0x513e20));
        general = (fpu.conditions() & 0x41) == 0;
    }
    if (!general) {
        fpu.reg(CLAW_X87_STP_ST, 0);
        fpu.ld(local8);
        fpu.ld(local18);
        fpu.ld(local10);
        fpu.xch(2);
        fpu.plain(CLAW_X87_ABS);
        fpu.xch(1);
        fpu.plain(CLAW_X87_ABS);
        fpu.reg(CLAW_X87_ADDP, 1);
        fpu.xch(1);
        fpu.plain(CLAW_X87_ABS);
        fpu.ld(local8);
        fpu.xch(1);
        fpu.reg(CLAW_X87_ADDP, 2);
        fpu.ld(local10);
        fpu.ld(local18);
        fpu.xch(2);
        fpu.reg(CLAW_X87_DIV_TO0, 3);
        fpu.xch(1);
        fpu.reg(CLAW_X87_DIV_TO0, 3);
        fpu.xch(2);
        fpu.reg(CLAW_X87_DIV_TO0, 3);
        fpu.xch(1);
        fpu.mul(local0);
        fpu.xch(2);
        fpu.mul(local0);
        fpu.xch(1);
        fpu.mul(local0);
        fpu.xch(2);
        storePair(run, self + 0x50, fpu.fstp());
        storePair(run, self + 0x58, fpu.fstp());
        storePair(run, self + 0x60, fpu.fstp());
        fpu.reg(CLAW_X87_STP_ST, 0);
        return 0;
    }
    fpu.ld(local0);
    fpu.mul(local0);
    fpu.xch(1);
    fpu.reg(CLAW_X87_ADD_TOI, 0);
    fpu.xch(1);
    fpu.sub(local40);
    fpu.xch(1);
    fpu.reg(CLAW_X87_DIVP, 1);
    fpu.reg(CLAW_X87_LD_ST, 0);
    fpu.plain(CLAW_X87_SQRT);
    fpu.reg(CLAW_X87_LD_ST, 1);
    fpu.reg(CLAW_X87_LD_ST, 2);
    fpu.xch(1);
    fpu.mul(local20);
    fpu.xch(2);
    fpu.xch(3);
    fpu.xch(1);
    fpu.mul(local28);
    fpu.xch(1);
    fpu.mul(local30);
    fpu.xch(2);
    fpu.mul(fpu.bits(0x50df28));
    fpu.xch(1);
    fpu.mul(fpu.bits(0x50df28));
    fpu.xch(1);
    fpu.subr(local8);
    fpu.xch(2);
    fpu.mul(fpu.bits(0x50df28));
    fpu.xch(1);
    fpu.subr(local10);
    fpu.xch(1);
    fpu.subr(local18);
    fpu.xch(2);
    fpu.reg(CLAW_X87_DIV_TO0, 3);
    fpu.xch(1);
    fpu.reg(CLAW_X87_DIV_TO0, 3);
    fpu.xch(2);
    fpu.reg(CLAW_X87_DIV_TO0, 3);
    fpu.xch(1);
    storePair(run, self + 0x50, fpu.fstp());
    fpu.xch(1);
    storePair(run, self + 0x58, fpu.fstp());
    storePair(run, self + 0x60, fpu.fstp());
    fpu.reg(CLAW_X87_STP_ST, 0);
    return 0;
}

// 0x446340. thiscall, no arguments. Starts the explosion: swaps in the
// exploding state, sets flags, starts the animation and plays a random
// one of three explosion sounds.
uint32_t function_446340(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t record = run.get(self + 0x10);
    uint32_t previous = run.get(record + 0x1c);
    run.put(self + 0x24, previous);
    uint32_t exploding = run.call(0x4dba00, 0x537668, {0x524418});
    record = run.get(self + 0x10);
    run.put(record + 0x1c, exploding);
    uint32_t holder = run.get(self + 0x12c);
    uint32_t flags = run.get(holder + 0x8);
    flags |= 4;
    run.put(holder + 0x8, flags);
    holder = run.get(self + 0x12c);
    run.put(holder + 0xd0, 0x1000000);
    holder = run.get(self + 0x12c);
    uint32_t sequence = run.get(self + 0x170);
    uint32_t frame = run.get(holder + 0x190);
    run.put(self + 0x134, frame);
    run.call(0x4c8220, holder + 0x188, {sequence});
    run.put(self + 0xc8, 1);
    uint32_t random = run.call(0x4a3050, 0);
    uint32_t pick = uint32_t(s32(random) % 3);
    uint32_t sound = run.get(self + pick * 4 + 0x174);
    if (sound == 0)
        return 0;
    uint32_t lit = run.get(0x532c0c);
    uint32_t value = run.get(0x532c10);
    if (lit == 0)
        return 0;
    uint32_t channel = run.get(sound + 0x10);
    run.call(0x4b45f0, channel, {value, 0, 0, 0});
    return 0;
}

// 0x4463f0. thiscall, no arguments. Waits out the explosion animation, then
// lets the owner finish.
uint32_t function_4463f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t game = run.get(0x53774c);
    if (game != 0) {
        if (run.get(game + 0x520) != 0) {
            uint32_t holder = run.get(self + 0x12c);
            uint32_t flags = run.get(holder + 0x8);
            flags |= 0x80;
            run.put(holder + 0x8, flags);
            holder = run.get(self + 0x12c);
            flags = run.get(holder + 0x8);
            flags |= 0x10000;
            run.put(holder + 0x8, flags);
            return 0;
        }
    }
    uint32_t step = run.get(0x5430c4);
    uint32_t holder = run.get(self + 0x12c);
    uint32_t done = run.call(0x4c82a0, holder + 0x188, {step});
    if (done == 1) {
        if (run.get(self + 0x18c) == 0) {
            run.put(self + 0x18c, 1);
            holder = run.get(self + 0x12c);
            uint32_t flags = run.get(holder + 0x8);
            flags &= 0xffffff7f;
            run.put(holder + 0x8, flags);
        }
    }
    holder = run.get(self + 0x12c);
    if (run.get(holder + 0x1a4) != 0) {
        if (run.get(holder + 0x19c) == 0) {
            uint32_t flags = run.get(holder + 0x8);
            flags |= 0x10000;
            run.put(holder + 0x8, flags);
        }
    }
    return 0;
}

// 0x446490. thiscall, no arguments. Falling bomb: plays a whistle once,
// then explodes (virtual +0x2c) once the target height is reached.
uint32_t function_446490(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    if (run.get(self + 0x190) == 0) {
        run.put(self + 0x190, 1);
        uint32_t random = run.call(0x4a3050, 0);
        uint32_t pick = uint32_t(s32(random) % 3);
        uint32_t sound = run.get(self + pick * 4 + 0x180);
        if (sound != 0) {
            uint32_t lit = run.get(0x532c0c);
            uint32_t value = run.get(0x532c10);
            if (lit != 0) {
                uint32_t channel = run.get(sound + 0x10);
                run.call(0x4b45f0, channel, {value, 0, 0, 0});
            }
        }
    }
    uint32_t game = run.get(0x53774c);
    if (game == 0)
        return 0;
    if (run.get(game + 0x520) != 0) {
        uint32_t holder = run.get(self + 0x12c);
        uint32_t flags = run.get(holder + 0x8);
        flags |= 0x80;
        run.put(holder + 0x8, flags);
        holder = run.get(self + 0x12c);
        flags = run.get(holder + 0x8);
        flags |= 0x10000;
        run.put(holder + 0x8, flags);
        return 0;
    }
    uint32_t step = run.get(0x5430c4);
    uint32_t holder = run.get(self + 0x12c);
    run.call(0x4c82a0, holder + 0x188, {step});
    game = run.get(0x53774c);
    Fpu fpu(run);
    fpu.ld(fpu.bits(self + 0x70));
    fpu.fild(run.get(game + 0x530));
    fpu.plain(CLAW_X87_COMPP);
    // test ah, 0x41: the integer is not greater than the coordinate
    if (fpu.conditions() & 0x41)
        run.vcall(self, 0x2c);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4459d0:
        return function_4459d0(run, receiver, arguments);
    case 0x445af0:
        return function_445af0(run, receiver, arguments);
    case 0x445ef0:
        return function_445ef0(run, receiver, arguments);
    case 0x446130:
        return function_446130(run, receiver, arguments);
    case 0x446340:
        return function_446340(run, receiver, arguments);
    case 0x4463f0:
        return function_4463f0(run, receiver, arguments);
    case 0x446490:
        return function_446490(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_eight_gabriel_bomb_01_entry, owned, body)
