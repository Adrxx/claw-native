// Level 1 Claw lift and throw states
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
    case 0x41a850:
        return 3;
    case 0x41b1f0:
        return 3;
    case 0x41b280:
        return 3;
    case 0x41dc50:
        return 4;
    case 0x421010:
        return 2;
    case 0x4dbd20:
        return 1;
    case 0x4dc6d0:
        return 1;
    default:
        return -1;
    }
}

// The x87 register stack of the lift, driven one original instruction at a time.
struct Fp {
    Run &run;
    ClawX87State state;
    explicit Fp(Run &r) : run(r), state{} {
        state.size = sizeof(state);
        state.version = CLAW_X87_VERSION;
        state.control = 0x023f;
    }
    // fld qword ptr [address]
    void load(uint32_t address) {
        uint32_t low = run.get(address);
        uint32_t high = run.get(address + 4);
        run.x87_step(CLAW_X87_F64, state, {low, high});
    }
    void multiply(uint32_t address) {
        uint32_t low = run.get(address);
        uint32_t high = run.get(address + 4);
        run.x87_step(CLAW_X87_MUL_F64, state, {low, high});
    }
    void add(uint32_t address) {
        uint32_t low = run.get(address);
        uint32_t high = run.get(address + 4);
        run.x87_step(CLAW_X87_ADD_F64, state, {low, high});
    }
    // fsubr qword ptr [address]: memory minus ST(0)
    void subtractFrom(uint32_t address) {
        uint32_t low = run.get(address);
        uint32_t high = run.get(address + 4);
        run.x87_step(CLAW_X87_SUBR_F64, state, {low, high});
    }
    // fsub qword ptr [local]: ST(0) minus the local's two words
    void subtractWords(uint32_t low, uint32_t high) {
        run.x87_step(CLAW_X87_SUB_F64, state, {low, high});
    }
    // fcomp qword ptr [address]; returns the status word
    uint32_t compare(uint32_t address) {
        uint32_t low = run.get(address);
        uint32_t high = run.get(address + 4);
        run.x87_step(CLAW_X87_COMP_F64, state, {low, high});
        return state.status;
    }
    // fstp qword ptr [address]
    void storePop(uint32_t address) {
        uint64_t bits = run.x87_step(CLAW_X87_STP_F64, state);
        run.put(address, uint32_t(bits));
        run.put(address + 4, uint32_t(bits >> 32));
    }
    // fst qword ptr [address]
    void store(uint32_t address) {
        uint64_t bits = run.x87_step(CLAW_X87_ST_F64, state);
        run.put(address, uint32_t(bits));
        run.put(address + 4, uint32_t(bits >> 32));
    }
    void reg(uint32_t form, uint32_t index) {
        run.x87_step(CLAW_X87_ST(form, index), state);
    }
    uint32_t compareReg(uint32_t index) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_COMP_ST, index), state);
        return state.status;
    }
    void negate() {
        run.x87_step(CLAW_X87_CHS, state);
    }
    void loadInt(uint32_t value) {
        run.x87_step(CLAW_X87_I32, state, {value});
    }
    // fstp qword ptr [esp] followed by the thiscall: pops ST(0) as the two stack words
    // and leaves the helper's ST(0) result.
    void callWithTop(uint32_t function) {
        uint64_t bits = run.x87_step(CLAW_X87_STP_F64, state);
        callWithWords(function, uint32_t(bits), uint32_t(bits >> 32));
    }
    void callWithWords(uint32_t function, uint32_t low, uint32_t high) {
        state.popCount = 0;
        state.pushCount = 1;
        state.returned = 0;
        state.eax = 0;
        state.edx = 0;
        run.call_x87_exact(function, 0x534db8, state, {low, high});
    }
    // call 0x4a30e0 (__ftol): consumes ST(0), returns the low word
    uint32_t truncate() {
        state.popCount = 1;
        state.pushCount = 0;
        state.returned = 0;
        state.eax = 0;
        state.edx = 0;
        return run.call_x87_exact(0x4a30e0, 0, state);
    }
};

// One axis of the lift's motion integration (0x41a9d2 onwards for x, then y and z).
void integrateAxis(Run &run, Fp &fp, uint32_t velocity, uint32_t position, uint32_t limit, uint32_t delta,
                   uint32_t low, uint32_t high, uint32_t clampTo, uint32_t acceleration, uint32_t helper,
                   bool firstAxis, bool accelerationFirst) {
    if (firstAxis) {
        fp.reg(CLAW_X87_LD_ST, 0);
        fp.multiply(acceleration);
        fp.multiply(0x50bb00);
        fp.subtractFrom(velocity);
        fp.reg(CLAW_X87_MUL_TO0, 1);
        fp.storePop(delta);
        fp.reg(CLAW_X87_STP_ST, 0);
        fp.load(delta);
    } else {
        if (!accelerationFirst) {
            fp.load(0x534dc0);
            fp.multiply(acceleration);
        } else {
            fp.load(acceleration);
            fp.multiply(0x534dc0);
        }
        fp.multiply(0x50bb00);
        fp.subtractFrom(velocity);
        fp.multiply(0x534dc0);
        fp.store(delta);
    }
    uint32_t status = fp.compare(limit);
    if ((status & 0x4100) == 0) {
        fp.load(position);
        fp.add(limit);
        fp.load(limit);
        fp.storePop(delta);
        fp.callWithTop(helper);
        fp.storePop(velocity);
    } else {
        fp.load(delta);
        fp.load(limit);
        fp.negate();
        fp.reg(CLAW_X87_XCH_ST, 1);
        status = fp.compareReg(1);
        if ((status & 0x100) != 0) {
            fp.load(position);
            fp.reg(CLAW_X87_XCH_ST, 1);
            fp.storePop(delta);
            fp.add(delta);
            fp.callWithTop(helper);
            fp.storePop(velocity);
        } else {
            fp.reg(CLAW_X87_STP_ST, 0);
        }
    }
    fp.load(position);
    fp.add(delta);
    uint32_t oldLow = run.get(position);
    uint32_t oldHigh = run.get(position + 4);
    fp.store(position);
    status = fp.compare(high);
    if ((status & 0x4100) == 0) {
        fp.callWithWords(helper, run.get(high), run.get(high + 4));
        fp.load(high);
        fp.subtractWords(oldLow, oldHigh);
        fp.load(high);
        fp.reg(CLAW_X87_XCH_ST, 2);
        fp.storePop(velocity);
        fp.reg(CLAW_X87_XCH_ST, 1);
        fp.storePop(position);
        fp.storePop(delta);
    } else {
        fp.load(position);
        status = fp.compare(low);
        if ((status & 0x100) != 0) {
            fp.callWithWords(helper, run.get(low), run.get(low + 4));
            fp.load(low);
            fp.subtractWords(oldLow, oldHigh);
            fp.load(low);
            fp.reg(CLAW_X87_XCH_ST, 2);
            fp.storePop(velocity);
            fp.reg(CLAW_X87_XCH_ST, 1);
            fp.storePop(position);
            fp.storePop(delta);
        } else {
            if (accelerationFirst) {
                fp.load(acceleration);
                fp.multiply(0x534dc0);
            } else {
                fp.load(0x534dc0);
                fp.multiply(acceleration);
            }
            fp.add(velocity);
            fp.storePop(velocity);
        }
    }
    fp.load(velocity);
    status = fp.compare(clampTo);
    if ((status & 0x4100) == 0) {
        uint32_t clampLow = run.get(clampTo);
        uint32_t clampHigh = run.get(clampTo + 4);
        run.put(velocity, clampLow);
        run.put(velocity + 4, clampHigh);
    }
}

void copyStateWords(Run &run, uint32_t actor, uint32_t state) {
    run.put(actor + 0x118, run.get(state + 0xd8));
    run.put(actor + 0x11c, run.get(state + 0xdc));
    run.put(actor + 0x120, run.get(state + 0xe0));
    run.put(actor + 0x124, run.get(state + 0xe4));
}

uint32_t function_41b1f0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_421010(Run &run, uint32_t receiver, const uint32_t *arguments);
void setFirstBit(Run &run, uint32_t body);

// 0x41a850. cdecl, 3 stack arguments (actor, frame, state), returns void.
// Carrying the held object, lift phase: walks, integrates the held object's motion
// with exact x87 arithmetic, then drops, throws or finishes the lift.
uint32_t function_41a850(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t frame = arguments[1];
    uint32_t state = arguments[2];
    uint32_t x = run.get(actor + 0x4c);
    uint32_t y = run.get(actor + 0x50);
    uint32_t input = run.get(run.get(0x537204) + 0x8);
    Fp fp(run);
    if ((input & 0x1000000) != 0 && run.get(state + 0x8) != 0) {
        if (run.get(state) != 0) {
            run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            run.call(0x4060b0, actor);
            run.put(state, 0);
            run.put(state + 0x114, 0x5dc);
        }
        bool walk = run.get(state + 0xc) != 0;
        if (!walk) {
            fp.load(0x534de0);
            uint32_t status = fp.compare(0x50baf0);
            walk = (status & 0x4000) != 0;
        }
        if (walk) {
            run.call(0x4c79e0, actor, {0x524758, 0});
            run.put(0x534de0, 0);
            run.put(0x534de4, 0xc03e0000);
            run.put(state + 0xc, 0);
        }
    } else if ((input & 0x2000000) != 0 && run.get(state + 0x8) != 0) {
        if (run.get(state) == 0) {
            run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffd);
            run.call(0x406120, actor);
            run.call(0x406150, actor);
            run.call(0x406180, actor);
            run.put(state, 1);
            run.put(state + 0x114, 0x5dc);
        }
        bool walk = run.get(state + 0xc) != 0;
        if (!walk) {
            fp.load(0x534de0);
            uint32_t status = fp.compare(0x50baf8);
            walk = (status & 0x4000) != 0;
        }
        if (walk) {
            run.call(0x4c79e0, actor, {0x524758, 0});
            run.put(0x534de0, 0);
            run.put(0x534de4, 0x403e0000);
            run.put(state + 0xc, 0);
        }
    } else {
        run.put(0x534de0, 0);
        run.put(0x534de4, 0);
    }
    uint32_t stepped = run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    if (stepped != 1) {
        // fild qword of the 32-bit count (high word zero), scaled by the frame constant
        double count = double(run.get(0x53720c));
        uint64_t countBits;
        std::memcpy(&countBits, &count, 8);
        run.x87_step(CLAW_X87_F64, fp.state, {uint32_t(countBits), uint32_t(countBits >> 32)});
        fp.multiply(0x50bab0);
        fp.reg(CLAW_X87_LD_ST, 0);
        fp.add(0x534db8);
        fp.reg(CLAW_X87_LD_ST, 1);
        fp.storePop(0x534dc0);
        fp.storePop(0x534db8);
        if (run.get(0x534e58) != 0) {
            fp.reg(CLAW_X87_STP_ST, 0);
        } else {
            integrateAxis(run, fp, 0x534de0, 0x534df8, 0x534e78, 0x534e40, 0x534e10, 0x534e28, 0x534e90,
                          0x534dc8, 0x420af0, true, false);
            integrateAxis(run, fp, 0x534de8, 0x534e00, 0x534e80, 0x534e48, 0x534e18, 0x534e30, 0x534e98,
                          0x534dd0, 0x420b60, false, false);
            integrateAxis(run, fp, 0x534df0, 0x534e08, 0x534e88, 0x534e50, 0x534e20, 0x534e38, 0x534ea0,
                          0x534dd8, 0x420bd0, false, true);
        }
        if (run.get(0x534e58) == 0) {
            fp.load(0x534e40);
            uint32_t whole = fp.truncate();
            fp.loadInt(whole);
            fp.subtractFrom(0x534e40);
            fp.add(0x534e60);
            fp.reg(CLAW_X87_LD_ST, 0);
            fp.add(0x534e40);
            uint32_t moved = fp.truncate();
            fp.reg(CLAW_X87_LD_ST, 0);
            run.put(0x544e8c, moved);
            uint32_t rest = fp.truncate();
            fp.loadInt(rest);
            fp.reg(CLAW_X87_SUBR_TO0, 1);
            fp.storePop(0x534e60);
            fp.reg(CLAW_X87_STP_ST, 0);
            x = x + moved;
        }
    }
    uint32_t parent = 0;
    if ((run.get8(actor + 0x8) & 0x10) != 0)
        parent = run.get(actor + 0x80);
    if (parent != 0) {
        x = x + run.get(parent + 0x158);
        y = y + run.get(parent + 0x15c);
    }
    run.call(0x4cbb60, run.get(run.get(actor + 0xc) + 0x24), {actor, x, y, 0x18});
    if (run.get(actor + 0xcc) == 4) {
        uint32_t body = run.get(run.get(run.get(state + 0x12c) + 0x6c) + 0x18);
        if (s32(run.get(body + 0x20)) >= 1)
            run.put(body + 0x14, 0x4207a0);
        fp.load(0x534de0);
        uint32_t status = fp.compare(0x50ba88);
        if ((status & 0x4100) == 0) {
            run.put(body + 0x50, 0);
            run.put(body + 0x54, 0x406c2000);
        } else {
            fp.load(0x534de0);
            run.put(body + 0x50, 0);
            status = fp.compare(0x50ba88);
            if ((status & 0x100) != 0)
                run.put(body + 0x54, 0xc06c2000);
            else
                run.put(body + 0x54, 0);
        }
        setFirstBit(run, body);
        run.put(state + 0x12c, 0);
        copyStateWords(run, actor, state);
        uint32_t kind = run.get(state + 0x3c);
        if (kind == 8 || kind == 9 || kind == 10 || kind == 0x12) {
            uint32_t found = run.call(0x4061b0, run.get(run.get(actor + 0xc) + 0x2c), {0x5246dc});
            run.put(state + 0x124, found);
        } else {
            run.call(0x41c4e0, 0, {actor, frame, state});
            run.call(0x4c79e0, actor, {0x5246dc, 0});
        }
        run.put(frame + 0x1c, 0x19);
        uint32_t flags = run.get(actor + 0x8) & 0xffffffef;
        run.put(actor + 0xcc, 4);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(actor + 0x8, flags);
        run.call(0x417050, 0, {actor, state});
        run.call(0x4170b0, 0, {actor, state});
        run.put(state + 0x40, 0);
        run.put(0x534de8, 0);
        run.put(0x534dec, 0);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0x40a19400);
        return 0;
    }
    bool lift2 = false;
    if (run.get(actor + 0x1a4) != 0 && run.get(actor + 0x19c) == 0 && run.get(state + 0x8) == 0) {
        lift2 = true;
    } else if (run.get(state + 0x8) != 0) {
        fp.load(0x534de0);
        uint32_t status = fp.compare(0x50ba88);
        if ((status & 0x4000) != 0) {
            lift2 = true;
        } else if (run.get(state + 0xc) == 0) {
            fp.load(0x534de0);
            status = fp.compare(0x50ba88);
            if ((status & 0x4000) != 0)
                lift2 = true;
        }
    }
    if (lift2) {
        run.call(0x4c79e0, actor, {0x52474c, 0});
        run.put(state + 0x8, 1);
        run.put(state + 0xc, 1);
    }
    if (run.get(state + 0x8) != 0 && (run.get8(run.get(0x537204) + 0x4) & 0x22) != 0) {
        copyStateWords(run, actor, state);
        const uint32_t throwArguments[3] = {actor, frame, state};
        function_41b1f0(run, 0, throwArguments);
    }
    uint32_t timer = run.get(state + 0xf0);
    uint32_t dt = run.get(0x5430c4);
    if (dt < timer) {
        run.put(state + 0xf0, timer - dt);
        return 0;
    }
    uint32_t body = run.get(run.get(run.get(state + 0x12c) + 0x6c) + 0x18);
    const uint32_t callbackArguments[2] = {0x4207a0, 1};
    function_421010(run, body, callbackArguments);
    run.call(0x420fc0, body + 0x2f4, {0});
    run.put(state + 0x12c, 0);
    copyStateWords(run, actor, state);
    run.call(0x4171d0, 0, {actor, frame, state});
    return 0;
}

// 0x41b1f0. cdecl, 3 stack arguments (actor, frame, state), returns void.
// Starts the throw: sets the throw animation, copies the held-object link and
// calls the held body's virtual method at +0xa0.
uint32_t function_41b1f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t frame = arguments[1];
    uint32_t state = arguments[2];
    run.put(frame + 0x1c, 0x1389);
    run.call(0x4c79e0, actor, {0x524774, 0});
    uint32_t link = run.get(actor + 0x170);
    run.put(actor + 0xcc, 1);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    if (link != 0) {
        uint32_t value = 0;
        if (s32(run.get(link + 0x64)) <= 0x2c) {
            if (s32(run.get(link + 0x68)) >= 0x2c)
                value = run.get(run.get(link + 0x14) + 0xb0);
        }
        run.put(actor + 0x174, value);
        run.put(actor + 0x16c, 0x2c);
    }
    uint32_t holder = run.get(state + 0x12c);
    uint32_t body = run.get(run.get(holder + 0x6c) + 0x18);
    run.vcall(body, 0xa0);
    return 0;
}

// Held-body bit set: +8 bit count, +0xc inline word (up to 32 bits) or pointer to the words.
uint32_t bitWordAddress(Run &run, uint32_t bits) {
    if (run.get(bits + 0x8) > 0x20)
        return run.get(bits + 0xc);
    return bits + 0xc;
}

// 0x4dc6d0. thiscall, 1 stack argument, returns 1 on success and 0 when the allocation fails.
// Grows the bit set to hold `bitCount` bits.
uint32_t growBits(Run &run, uint32_t bits, uint32_t bitCount) {
    uint32_t words = ((bitCount & 0x1f) != 0 ? 1u : 0u) + (bitCount >> 5);
    uint32_t block = 0;
    if (run.get(bits + 0x8) <= 0x20) {
        block = run.call(0x4a48e0, 0, {words * 4});
        if (block != 0) {
            for (uint32_t i = 0; i < words; ++i)
                run.put(block + i * 4, 0);
            run.call(0x4a5290, 0, {block, bits + 0xc, 4});
        }
    } else {
        block = run.call(0x4a9070, 0, {run.get(bits + 0xc), words * 4});
        if (block != 0) {
            uint32_t oldWords = run.get(bits + 0x8) >> 5;
            uint32_t count = (words - oldWords) & 0x3fffffff;
            for (uint32_t i = 0; i < count; ++i)
                run.put(block + (oldWords + i) * 4, 0);
        }
    }
    if (block == 0) {
        // The original helper 0x4dc680 returns [ebp + 4] of this frame, and EBP is the word count here.
        uint32_t message = run.get(0x544b4c);
        uint32_t code = run.get(words + 4);
        run.put(0x544b14, code);
        run.call(0x4db4d0, run.get(bits + 0x4), {bits, message, 0xc});
        return 0;
    }
    run.put(bits + 0xc, block);
    run.put(bits + 0x8, words << 5);
    return 1;
}

uint32_t function_4dc6d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return growBits(run, receiver, arguments[0]);
}

// 0x4dbd20. thiscall, 1 stack argument, returns this. Sets one bit, growing the set first.
uint32_t function_4dbd20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t bit = arguments[0];
    if (growBits(run, receiver, bit + 1) != 0) {
        uint32_t word = bitWordAddress(run, receiver) + (bit >> 5) * 4;
        run.put(word, run.get(word) | (1u << (bit & 0x1f)));
    }
    return receiver;
}

// 0x421010. thiscall, 2 stack arguments (callback, limit), returns void.
uint32_t function_421010(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (s32(arguments[1]) <= s32(run.get(receiver + 0x20)))
        run.put(receiver + 0x14, arguments[0]);
    return 0;
}

// Sets bit 0 of the held body's bit set, the way 0x41b280 and 0x41a850 do inline.
void setFirstBit(Run &run, uint32_t body) {
    uint32_t count = run.get(body + 0x2fc);
    uint32_t bits = body + 0x2f4;
    if (count == 0) {
        const uint32_t zero[1] = {0};
        function_4dbd20(run, bits, zero);
        return;
    }
    uint32_t word = bitWordAddress(run, bits);
    run.put(word, run.get(word) | 1);
}

void clearSixWords(Run &run) {
    run.put(0x534e60, 0);
    run.put(0x534e64, 0);
    run.put(0x534e68, 0);
    run.put(0x534e6c, 0);
    run.put(0x534e70, 0);
    run.put(0x534e74, 0);
}

// 0x41b280. cdecl, 3 stack arguments (actor, frame, state), returns void.
// Carrying the held object: turns on direction input, drops or throws it, falls.
uint32_t function_41b280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t frame = arguments[1];
    uint32_t state = arguments[2];
    uint32_t x = run.get(actor + 0x4c);
    uint32_t y = run.get(actor + 0x50);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    if ((run.get8(actor + 0x8) & 0x10) != 0) {
        uint32_t parent = run.get(actor + 0x80);
        if (parent != 0) {
            x = x + run.get(parent + 0x158);
            y = y + run.get(parent + 0x15c);
        }
    }
    uint32_t input = run.get(run.get(0x537204) + 0x8);
    bool directionChanged = false;
    if ((input & 0x1000000) != 0 && run.get(state) != 0) {
        run.put(actor + 0x40, run.get(actor + 0x40) | 2);
        run.call(0x406120, actor);
        run.call(0x406150, actor);
        run.call(0x406180, actor);
        run.put(state, 0);
        directionChanged = true;
    } else if ((input & 0x2000000) != 0 && run.get(state) == 0) {
        run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffd);
        run.call(0x406120, actor);
        run.call(0x406150, actor);
        run.call(0x406180, actor);
        run.put(state, 1);
        directionChanged = true;
    }
    if (directionChanged)
        run.put(state + 0x114, 0x5dc);
    run.call(0x4cbb60, run.get(run.get(actor + 0xc) + 0x24), {actor, x, y, 0x18});
    if (run.get(actor + 0xcc) == 4) {
        uint32_t kind = run.get(state + 0x3c);
        run.put(state + 0x12c, 0);
        if (kind == 8 || kind == 9 || kind == 10 || kind == 0x12) {
            run.put(run.automatic(8), 0);
            run.call(0x4f6286, run.get(run.get(actor + 0xc) + 0x2c) + 0x10, {0x5246dc, run.automatic(8)});
            run.put(state + 0x124, run.get(run.automatic(8)));
        } else {
            run.call(0x41c4e0, 0, {actor, frame, state});
            run.call(0x4c79e0, actor, {0x5246dc, 0});
        }
        run.put(frame + 0x1c, 0x19);
        uint32_t flags = run.get(actor + 0x8) & 0xffffffef;
        run.put(actor + 0xcc, 4);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(actor + 0x8, flags);
        run.call(0x417050, 0, {actor, state});
        run.call(0x4170b0, 0, {actor, state});
        run.put(state + 0x40, 0);
        run.put(0x534de8, 0);
        run.put(0x534dec, 0);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0x40a19400);
        return 0;
    }
    if ((run.get8(run.get(0x537204) + 0x8) & 0x22) != 0) {
        uint32_t timer = run.get(state + 0xf4);
        if (timer < 0xbb8) {
            run.put(state + 0xf4, run.get(0x5430c4) + timer);
            return 0;
        }
    }
    uint32_t stepped = run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    if (stepped == 1 && run.get(state + 0x12c) != 0) {
        uint32_t holder = run.get(state + 0x12c);
        uint32_t body = run.get(run.get(holder + 0x6c) + 0x18);
        uint32_t timer = run.get(state + 0xf4);
        uint32_t scaled = uint32_t((uint64_t(timer * 100) * 0x57619f1) >> 38);
        setFirstBit(run, body);
        run.vcall(body, 0x80, {scaled});
        run.vcall(body, 0x84);
        run.put(state + 0x12c, 0);
        uint32_t scene = run.get(run.get(actor + 0xc) + 0x28);
        if (run.get(scene + 0x30) == 0) {
            run.put(run.automatic(4), 0);
            run.call(0x4f6286, scene + 0x10, {0x524780, run.automatic(4)});
            uint32_t found = run.get(run.automatic(4));
            if (found != 0) {
                uint32_t sound = run.get(0x532c0c);
                uint32_t sample = run.get(0x532c10);
                if (sound != 0)
                    run.call(0x4b45f0, run.get(found + 0x10), {sample, 0, 0, 0});
            }
        }
    }
    if (run.get(actor + 0x1a4) != 0 && run.get(actor + 0x19c) == 0) {
        run.put(state + 0x12c, 0);
        run.call(0x41c4e0, 0, {actor, frame, state});
        run.put(frame + 0x1c, 0x18);
        run.call(0x4c79e0, actor, {0x5246d0, 1});
        uint32_t flags = run.get(actor + 0x8) | 0x80;
        run.put(actor + 0xcc, 1);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(actor + 0x104, 0);
        run.put(actor + 0x8, flags);
        if (run.get(state) != 0)
            run.call(0x4208b0, actor, {0xffffffea, 0xffffffd3, 0xf, 0x34});
        else
            run.call(0x4208b0, actor, {0xfffffff1, 0xffffffd3, 0x16, 0x34});
        run.call(0x4170b0, 0, {actor, state});
        run.put(state + 0xfc, 0x28a);
        run.put(state + 0x114, 0x5dc);
        run.put(state + 0x120, 0x3a98);
        run.put(state + 0x118, 0);
        clearSixWords(run);
        run.put(actor + 0x1b0, 0x3f800000);
    }
    return 0;
}

// 0x41dc50. cdecl, 4 stack arguments (actor, frame, state, player), returns void.
// Picks up the held object.
uint32_t function_41dc50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t frame = arguments[1];
    uint32_t state = arguments[2];
    uint32_t player = arguments[3];
    run.put(frame + 0x1c, 0x1388);
    uint32_t name = 0x52487c;
    if ((run.get8(player + 0x164) & 4) != 0)
        name = 0x524888;
    run.call(0x4c79e0, actor, {name, 0});
    run.put(actor + 0xcc, 1);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(state + 0x8, 0);
    run.put(state + 0xc, 0);
    run.put(state + 0x12c, player);
    run.put(state + 0xf0, 100000);
    run.put(state + 0xf4, 0);
    uint32_t body = run.get(run.get(player + 0x6c) + 0x18);
    uint32_t count = run.get(body + 0x2fc);
    if (count != 0) {
        uint32_t word = body + 0x300;
        if (count > 0x20)
            word = run.get(body + 0x300);
        run.put(word, run.get(word) ^ 1);
    }
    uint32_t link = run.get(body + 0xc);
    uint32_t level = run.get(actor + 0x64) + 1;
    if (run.get(link + 0x64) != level) {
        run.put(link + 0x64, level);
        run.put(link + 0x8, run.get(link + 0x8) | 0x20000);
    }
    run.vcall(body, 0x88);
    run.put(state + 0xd8, run.get(actor + 0x118));
    run.put(state + 0xdc, run.get(actor + 0x11c));
    run.put(state + 0xe0, run.get(actor + 0x120));
    run.put(state + 0xe4, run.get(actor + 0x124));
    run.put(actor + 0x11c, run.get(actor + 0x11c) - 0x19);
    clearSixWords(run);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x41a850:
        return function_41a850(run, receiver, arguments);
    case 0x41b1f0:
        return function_41b1f0(run, receiver, arguments);
    case 0x41b280:
        return function_41b280(run, receiver, arguments);
    case 0x41dc50:
        return function_41dc50(run, receiver, arguments);
    case 0x421010:
        return function_421010(run, receiver, arguments);
    case 0x4dbd20:
        return function_4dbd20(run, receiver, arguments);
    case 0x4dc6d0:
        return function_4dc6d0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_claw_lift_throw_01_entry, owned, body)
