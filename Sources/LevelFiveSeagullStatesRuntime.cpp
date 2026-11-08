// Level 5 seagull state behavior, recovered from the original v1.0.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

// Object fields: +0x0 vtable, +0xc collision owner, +0x10 state owner,
// +0x20 death flag, +0x24 saved state, +0x28 motion object; its +0x10..0x20
// acceleration, +0x28..0x38 velocity, and +0x40..0x50 position are binary64.
// Actor fields: +0x8 flags, +0x38 animation status, +0x40 facing flags,
// +0x188 animation controller, +0x190 current animation, +0x19c timer,
// +0x1a4 completion flag. Object +0x134 saves the animation; +0x138..0x144
// are patrol bounds, +0x18c direction, +0x210/+0x220 collision rectangles,
// +0x2f4 bitset, +0x3c4 dive timer, +0x408/+0x418/+0x41c/+0x420/+0x428
// animation selections, +0x38c/+0x42c/+0x430 sounds, +0x434 patrol height,
// and +0x438 dive limit. Player +0x4c/+0x50 are signed coordinates.

// Exact arithmetic follows the original binary64 stores and x87 register stack.
struct Floating {
    Run &run;
    ClawX87State state{};
    explicit Floating(Run &run) : run(run) {
        state.size = sizeof(state);
        state.version = CLAW_X87_VERSION;
        state.control = 0x023f;
    }
    Floating(Run &run, const ClawX87State &inherited) : run(run), state(inherited) {}
    uint64_t memory(uint32_t address) {
        return uint64_t(run.get(address)) | (uint64_t(run.get(address + 0x4)) << 32);
    }
    void step(uint32_t operation) {
        run.x87_step(operation, state);
    }
    void operand(uint32_t operation, uint64_t bits) {
        run.x87_step(operation, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    void load(uint64_t bits) {
        operand(CLAW_X87_F64, bits);
    }
    void integer(uint32_t word) {
        run.x87_step(CLAW_X87_I32, state, {word});
    }
    uint64_t stored(bool pop) {
        return run.x87_step(pop ? CLAW_X87_STP_F64 : CLAW_X87_ST_F64, state);
    }
    uint32_t outside(uint32_t address, std::initializer_list<uint32_t> args, uint32_t pop = 0, uint32_t receiver = 0) {
        state.popCount = pop;
        state.pushCount = 0;
        state.returned = 0;
        state.eax = 0;
        state.edx = 0;
        return run.call_x87_exact(address, receiver, state, args);
    }
};
struct Scratch {
    uint32_t words[40]{};
    uint64_t bits(uint32_t offset) const {
        return uint64_t(words[offset / 4]) | (uint64_t(words[offset / 4 + 1]) << 32);
    }
    void bits(uint32_t offset, uint64_t value) {
        words[offset / 4] = uint32_t(value);
        words[offset / 4 + 1] = uint32_t(value >> 32);
    }
};

void zeroVelocity(Run &run, uint32_t receiver) {
    run.put(receiver + 0x28, 0);
    run.put(receiver + 0x30, 0);
    run.put(receiver + 0x38, 0);
    run.put(receiver + 0x2c, 0);
    run.put(receiver + 0x34, 0);
    run.put(receiver + 0x3c, 0);
}

void animation(Run &run, uint32_t receiver, uint32_t index) {
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {index});
}
void advance(Run &run, uint32_t receiver, Floating *existing = nullptr) {
    Floating fresh(run);
    Floating &fp = existing ? *existing : fresh;
    fp.outside(0x4c82a0, {run.get(0x5430c4)}, 0, run.get(receiver + 0x12c) + 0x188);
}
void changeState(Run &run, uint32_t receiver, uint32_t name) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
}
void sound(Run &run, uint32_t receiver, uint32_t offset, int32_t entryOffset, Floating *fp = nullptr) {
    uint32_t object = run.get(receiver + offset);
    if (object && run.get(0x532c0c)) {
        // The original sound implementation exposes a stack-local status word.
        uint32_t previousStack = run.stackPointer;
        run.stackPointer = run.automatic(entryOffset);
        Floating fresh(run);
        Floating &state = fp ? *fp : fresh;
        state.outside(0x4b45f0, {run.get(0x532c10), 0, 0, 0}, 0, run.get(object + 0x10));
        run.stackPointer = previousStack;
    }
}
void rectangle(Run &run, uint32_t receiver, uint32_t offset) {
    uint32_t target = run.get(receiver + 0xc) + 0x138;
    run.put(target, run.get(receiver + offset));
    run.put(target + 0x4, run.get(receiver + offset + 0x4));
    run.put(target + 0x8, run.get(receiver + offset + 0x8));
    run.put(target + 0xc, run.get(receiver + offset + 0xc));
    if (run.get8(run.get(receiver + 0x12c) + 0x40) & 2) {
        uint32_t object = run.get(receiver + 0xc);
        uint32_t left = run.get(object + 0x138);
        run.put(object + 0x138, 0u - run.get(object + 0x140));
        run.put(run.get(receiver + 0xc) + 0x140, 0u - left);
    }
}

// 0x406da0: publish the current dispatch cursor and bind its description.
uint32_t function_406da0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // The leaf pops and restores this callsite's fixed source continuation.
    run.call(0x4db5f0, receiver);
    run.put(0x544b14, 0x406da8);
    uint32_t previousStack = run.stackPointer;
    // PUSH ESI, three arguments, and CALL place the callee entry 0x14 lower.
    run.stackPointer = run.automatic(-0x14);
    run.call(0x4db4d0, run.get(receiver + 0x4), {receiver, arguments[0], arguments[1]});
    run.stackPointer = previousStack;
    return 0;
}
// 0x467ea0: solve the initial velocity toward a selected destination.
uint32_t function_467ea0(Run &run, uint32_t receiver, const uint32_t *arguments, Floating *existing = nullptr) {
    Floating fresh(run);
    Floating &fp = existing ? *existing : fresh;
    Scratch local;
    uint32_t status = 0;
    for (uint32_t i = 0; i < 9; ++i) {
        local.words[0x38 / 4 + i] = arguments[i];
    }
    fp.load(local.bits(0x38));
    fp.load(fp.memory(0x513e20));
    fp.step(CLAW_X87_CHS);
    local.bits(0x1c, fp.stored(true));
    fp.operand(CLAW_X87_COMP_F64, local.bits(0x1c));
    status = fp.state.status;
    if (status & 0x100) {
        fp.outside(0x4c96b0, {0x529c4c, local.words[0x38 / 4], local.words[0x3c / 4]});
        return 0;
    }
    fp.load(local.bits(0x38));
    fp.operand(CLAW_X87_COMP_F64, fp.memory(0x513e20));
    status = fp.state.status;
    if (status & 0x100) {
        zeroVelocity(run, receiver);
        return 1;
    }
    fp.load(fp.memory(receiver + 0x10));
    fp.load(fp.memory(receiver + 0x18));
    fp.load(fp.memory(receiver + 0x20));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0xc, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    local.bits(0x14, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0xc));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x24, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x14));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 3));
    fp.load(local.bits(0x40));
    fp.load(local.bits(0x48));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 4));
    fp.load(local.bits(0x50));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_SUB_F64, fp.memory(receiver + 0x40));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50ec10));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_SUB_F64, fp.memory(receiver + 0x48));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_SUB_F64, fp.memory(receiver + 0x50));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    local.bits(0x2c, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 3));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    local.bits(0x48, fp.stored(false));
    fp.operand(CLAW_X87_COMP_F64, local.bits(0x1c));
    local.bits(0x1c, fp.stored(false));
    status = fp.state.status;
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x40, fp.stored(true));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    bool quadratic = (status & 0x100) != 0;
    if (!quadratic) {
        fp.load(local.bits(0x48));
        fp.operand(CLAW_X87_COMP_F64, fp.memory(0x513e20));
        status = fp.state.status;
        quadratic = (status & 0x4100) == 0;
    }
    if (!quadratic) {
        fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
        fp.load(local.bits(0x40));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.step(CLAW_X87_ABS);
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        fp.step(CLAW_X87_ABS);
        fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        fp.step(CLAW_X87_ABS);
        fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
        fp.load(local.bits(0x40));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        fp.step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        fp.step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.operand(CLAW_X87_MUL_F64, local.bits(0x38));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        fp.operand(CLAW_X87_MUL_F64, local.bits(0x38));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.operand(CLAW_X87_MUL_F64, local.bits(0x38));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        uint64_t stored1 = fp.stored(true);
        run.put(receiver + 0x28, uint32_t(stored1));
        run.put(receiver + 0x2c, uint32_t(stored1 >> 32));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        uint64_t stored2 = fp.stored(true);
        run.put(receiver + 0x30, uint32_t(stored2));
        run.put(receiver + 0x34, uint32_t(stored2 >> 32));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        uint64_t stored3 = fp.stored(true);
        run.put(receiver + 0x38, uint32_t(stored3));
        run.put(receiver + 0x3c, uint32_t(stored3 >> 32));
        fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
        return 1;
    }
    fp.load(local.bits(0xc));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 2));
    fp.load(local.bits(0x14));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 3));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 3));
    fp.load(local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 6));
    fp.load(local.bits(0x40));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5));
    fp.step(CLAW_X87_CHS);
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 5));
    fp.load(local.bits(0x38));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x40));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x40));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x38));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x48));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    local.bits(0x50, fp.stored(false));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x50));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50ec18));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 1));
    local.bits(0x38, fp.stored(true));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    fp.outside(0x4c96b0, {0x529c3c, local.words[0x38 / 4], local.words[0x3c / 4]});
    fp.load(local.bits(0x38));
    fp.load(fp.memory(0x513e20));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_CHS);
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_COMPP);
    status = fp.state.status;
    if (status & 0x100) {
        fp.step(CLAW_X87_POP);
        fp.outside(0x4c96b0, {0x529c1c, local.words[0x38 / 4], local.words[0x3c / 4]});
        return 0;
    }
    fp.operand(CLAW_X87_COM_F64, fp.memory(0x513e20));
    status = fp.state.status;
    if (status & 0x100) {
        fp.step(CLAW_X87_POP);
        fp.load(fp.memory(0x50ebf8));
    }
    fp.step(CLAW_X87_SQRT);
    fp.integer(local.words[0x58 / 4]);
    fp.load(local.bits(0x48));
    fp.step(CLAW_X87_ST(CLAW_X87_ADD_TO0, 0));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_MULP, 2));
    fp.load(local.bits(0xc));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_SUB_F64, local.bits(0x50));
    fp.load(local.bits(0x14));
    fp.load(local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.step(CLAW_X87_ST(CLAW_X87_DIVP, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    local.bits(0x48, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 0));
    fp.step(CLAW_X87_SQRT);
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    local.bits(0x38, fp.stored(true));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x48));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x48));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50ec28));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50ec28));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_SUBR_F64, local.bits(0x2c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50ec28));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_SUBR_F64, local.bits(0x1c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_SUBR_F64, local.bits(0x40));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.operand(CLAW_X87_DIV_F64, local.bits(0x38));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_DIV_F64, local.bits(0x38));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.operand(CLAW_X87_DIV_F64, local.bits(0x38));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    uint64_t stored4 = fp.stored(true);
    run.put(receiver + 0x28, uint32_t(stored4));
    run.put(receiver + 0x2c, uint32_t(stored4 >> 32));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    uint64_t stored5 = fp.stored(true);
    run.put(receiver + 0x30, uint32_t(stored5));
    run.put(receiver + 0x34, uint32_t(stored5 >> 32));
    uint64_t stored6 = fp.stored(true);
    run.put(receiver + 0x38, uint32_t(stored6));
    run.put(receiver + 0x3c, uint32_t(stored6 >> 32));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    return 1;
}
uint32_t function_487b80(Run &run, uint32_t receiver, const uint32_t *arguments, Floating *existing = nullptr);
// 0x4879a0: patrol endpoints and conditional dive.
uint32_t function_4879a0(Run &run, uint32_t receiver, const uint32_t *) {
    Floating fp(run, run.x87_entry(0x4879a0));
    fp.outside(0x4c82a0, {run.get(0x5430c4)}, 0, run.get(receiver + 0x12c) + 0x188);
    fp.load(fp.memory(receiver + 0x68));
    fp.operand(CLAW_X87_COMP_F64, fp.memory(receiver + 0x80));
    if (fp.state.status & 0x4000) {
        run.put(receiver + 0x50, run.get(0x50f550));
        run.put(receiver + 0x54, run.get(0x50f554));
        uint32_t actor = run.get(receiver + 0x12c);
        if (!(run.get8(actor + 0x40) & 2)) {
            uint32_t left = run.get(receiver + 0x138);
            uint32_t right = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0u - right);
            run.put(receiver + 0x140, 0u - left);
            run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            actor = run.get(receiver + 0x12c);
            run.call(0x406120, actor);
            run.call(0x406150, actor);
            run.call(0x406180, actor);
        }
    }
    fp.load(fp.memory(receiver + 0x68));
    fp.operand(CLAW_X87_COMP_F64, fp.memory(receiver + 0x98));
    if (fp.state.status & 0x4000) {
        fp.load(fp.memory(0x50f550));
        fp.step(CLAW_X87_CHS);
        uint64_t stored7 = fp.stored(true);
        run.put(receiver + 0x50, uint32_t(stored7));
        run.put(receiver + 0x54, uint32_t(stored7 >> 32));
        uint32_t actor = run.get(receiver + 0x12c);
        if (run.get8(actor + 0x40) & 2) {
            uint32_t left = run.get(receiver + 0x138);
            uint32_t right = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0u - right);
            run.put(receiver + 0x140, 0u - left);
            run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffdu);
            actor = run.get(receiver + 0x12c);
            run.call(0x406120, actor);
            run.call(0x406150, actor);
            run.call(0x406180, actor);
        }
    }
    uint32_t player = run.get(0x537e88);
    fp.integer(run.get(player + 0x4c));
    fp.load(fp.memory(receiver + 0x68));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBR_TO0, 1));
    uint32_t dx = fp.outside(0x4a30e0, {}, 1);
    fp.integer(run.get(player + 0x50));
    uint64_t playerY = fp.stored(true);
    fp.load(fp.memory(receiver + 0x70));
    fp.operand(CLAW_X87_SUBR_F64, playerY);
    uint32_t dy = fp.outside(0x4a30e0, {}, 1);
    dx = s32(dx) < 0 ? 0u - dx : dx;
    dy = s32(dy) < 0 ? 0u - dy : dy;
    int32_t timer = run.gets(receiver + 0x3c4);
    if (timer < 0 || timer >= 1000) {
        fp.step(CLAW_X87_POP);
        run.x87_finish(0x4879a0, fp.state);
        return 0;
    }
    fp.load(fp.memory(receiver + 0x80));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    fp.step(CLAW_X87_COMPP);
    if (fp.state.status & 0x4100) {
        fp.step(CLAW_X87_POP);
        run.x87_finish(0x4879a0, fp.state);
        return 0;
    }
    fp.load(fp.memory(receiver + 0x98));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_COMPP);
    if (!(fp.state.status & 0x100)) {
        run.x87_finish(0x4879a0, fp.state);
        return 0;
    }
    fp.load(fp.memory(receiver + 0x70));
    fp.load(playerY);
    fp.step(CLAW_X87_COMPP);
    if (fp.state.status & 0x4100) {
        run.x87_finish(0x4879a0, fp.state);
        return 0;
    }
    if (s32(dx) <= s32(dy) || s32(dy) <= 100 || s32(dy) >= 240) {
        run.x87_finish(0x4879a0, fp.state);
        return 0;
    }
    fp.load(fp.memory(receiver + 0x50));
    fp.operand(CLAW_X87_COMP_F64, fp.memory(0x50f560));
    bool dive = (fp.state.status & 0x100) && run.get(receiver + 0x18c) == 3;
    if (!dive) {
        fp.load(fp.memory(receiver + 0x50));
        fp.operand(CLAW_X87_COMP_F64, fp.memory(0x50f560));
        dive = !(fp.state.status & 0x4100) && run.get(receiver + 0x18c) == 2;
    }
    if (dive) {
        uint32_t target = run.get(run.get(receiver) + 0x58);
        if (target == 0x487b80) {
            function_487b80(run, receiver, nullptr, &fp);
        } else {
            // The finite original vtable selects the owned strike above;
            // alternate integer-only callback fixtures observe its publication.
            run.call(target, receiver);
        }
    }
    run.x87_finish(0x4879a0, fp.state);
    return 0;
}

// 0x487b80: enter strike and calculate the diving trajectory.
uint32_t function_487b80(Run &run, uint32_t receiver, const uint32_t *, Floating *existing) {
    Floating fresh(run);
    Floating &fp = existing ? *existing : fresh;
    sound(run, receiver, 0x430, existing ? -0x84 : -0x68, &fp);
    rectangle(run, receiver, 0x220);
    changeState(run, receiver, 0x52720c);
    animation(run, receiver, run.get(receiver + 0x408));
    run.put(receiver + 0x438, run.get(run.get(0x537e88) + 0x50));
    uint32_t player = run.get(0x537e88);
    uint32_t playerX = run.get(player + 0x4c);
    uint32_t playerY = run.get(player + 0x50);
    Scratch local;
    uint32_t status = 0;
    local.words[0x14 / 4] = playerX;
    local.words[0x1c / 4] = run.get(0x50f548);
    local.words[0x20 / 4] = run.get(0x50f54c);
    fp.load(fp.memory(0x513e20));
    fp.step(CLAW_X87_CHS);
    local.bits(0x34, fp.stored(true));
    fp.load(local.bits(0x1c));
    fp.operand(CLAW_X87_COMP_F64, local.bits(0x34));
    status = fp.state.status;
    if (status & 0x100) {
        fp.outside(0x4c96b0, {0x529c4c, local.words[0x1c / 4], local.words[0x20 / 4]});
        return 0;
    }
    fp.load(local.bits(0x1c));
    fp.operand(CLAW_X87_COMP_F64, fp.memory(0x513e20));
    status = fp.state.status;
    if (status & 0x100) {
        zeroVelocity(run, receiver + 0x28);
        return 0;
    }
    local.words[0xc / 4] = playerY - 0x28;
    fp.load(fp.memory(receiver + 0x38));
    fp.load(fp.memory(receiver + 0x40));
    fp.load(fp.memory(receiver + 0x48));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x24, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    local.bits(0x2c, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x3c, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x2c));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 3));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 2));
    fp.integer(local.words[0xc / 4]);
    fp.integer(local.words[0x14 / 4]);
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50f568));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.operand(CLAW_X87_SUB_F64, fp.memory(receiver + 0x68));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_SUB_F64, fp.memory(receiver + 0x70));
    fp.load(fp.memory(receiver + 0x78));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    local.bits(0xc, fp.stored(false));
    fp.operand(CLAW_X87_COMP_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.step(CLAW_X87_CHS);
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    local.bits(0x44, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x4c, fp.stored(false));
    status = fp.state.status;
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x14, fp.stored(true));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    bool quadratic = (status & 0x100) != 0;
    if (!quadratic) {
        fp.load(local.bits(0xc));
        fp.operand(CLAW_X87_COMP_F64, fp.memory(0x513e20));
        status = fp.state.status;
        quadratic = (status & 0x4100) == 0;
    }
    if (!quadratic) {
        fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
        fp.load(local.bits(0x14));
        fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 2));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.step(CLAW_X87_ABS);
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        fp.step(CLAW_X87_ABS);
        fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        fp.step(CLAW_X87_ABS);
        fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
        fp.load(local.bits(0x14));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        fp.step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        fp.step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.operand(CLAW_X87_MUL_F64, local.bits(0x1c));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        fp.operand(CLAW_X87_MUL_F64, local.bits(0x1c));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.operand(CLAW_X87_MUL_F64, local.bits(0x1c));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        uint64_t stored8 = fp.stored(true);
        run.put(receiver + 0x50, uint32_t(stored8));
        run.put(receiver + 0x54, uint32_t(stored8 >> 32));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        uint64_t stored9 = fp.stored(true);
        run.put(receiver + 0x58, uint32_t(stored9));
        run.put(receiver + 0x5c, uint32_t(stored9 >> 32));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        uint64_t stored10 = fp.stored(true);
        run.put(receiver + 0x60, uint32_t(stored10));
        run.put(receiver + 0x64, uint32_t(stored10 >> 32));
        fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
        return 0;
    }
    fp.load(local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 2));
    fp.load(local.bits(0x2c));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 3));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 3));
    fp.load(local.bits(0x3c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 6));
    fp.load(local.bits(0x14));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5));
    fp.step(CLAW_X87_CHS);
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 5));
    fp.load(local.bits(0x1c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x14));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x14));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x1c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0xc));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    local.bits(0x34, fp.stored(false));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50f570));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 1));
    local.bits(0x1c, fp.stored(true));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    fp.outside(0x4c96b0, {0x529c3c, local.words[0x1c / 4], local.words[0x20 / 4]});
    fp.load(local.bits(0x1c));
    fp.load(fp.memory(0x513e20));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_CHS);
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_COMPP);
    status = fp.state.status;
    if (status & 0x100) {
        fp.step(CLAW_X87_POP);
        fp.outside(0x4c96b0, {0x529c1c, local.words[0x1c / 4], local.words[0x20 / 4]});
        return 0;
    }
    fp.operand(CLAW_X87_COM_F64, fp.memory(0x513e20));
    status = fp.state.status;
    if (status & 0x100) {
        fp.step(CLAW_X87_POP);
        fp.load(fp.memory(0x50f560));
    }
    fp.step(CLAW_X87_SQRT);
    fp.load(local.bits(0xc));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_SUB_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_ADD_TO0, 0));
    fp.load(local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_DIVP, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    local.bits(0x24, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    fp.step(CLAW_X87_SQRT);
    fp.load(local.bits(0x2c));
    fp.load(local.bits(0x3c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x34, fp.stored(true));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50f580));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50f580));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_SUBR_F64, local.bits(0x44));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50f580));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_SUBR_F64, local.bits(0x4c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_SUBR_F64, local.bits(0x14));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_DIV_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_DIV_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_DIV_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    uint64_t stored11 = fp.stored(true);
    run.put(receiver + 0x50, uint32_t(stored11));
    run.put(receiver + 0x54, uint32_t(stored11 >> 32));
    uint64_t stored12 = fp.stored(true);
    run.put(receiver + 0x58, uint32_t(stored12));
    run.put(receiver + 0x5c, uint32_t(stored12 >> 32));
    uint64_t stored13 = fp.stored(true);
    run.put(receiver + 0x60, uint32_t(stored13));
    run.put(receiver + 0x64, uint32_t(stored13 >> 32));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    return 0;
}

// 0x487f80: withdraw to the appropriate patrol endpoint.
uint32_t function_487f80(Run &run, uint32_t object, const uint32_t *) {
    changeState(run, object, 0x52bf80);
    rectangle(run, object, 0x210);
    animation(run, object, run.get(object + 0x418));
    Floating fp(run);
    fp.load(fp.memory(object + 0x50));
    fp.operand(CLAW_X87_COMP_F64, fp.memory(0x50f560));
    if (!(fp.state.status & 0x100)) {
        fp.integer(run.get(object + 0x434));
        uint64_t targetY = fp.stored(true);
        fp.load(fp.memory(object + 0x98));
        uint64_t targetX = fp.stored(true);
        uint32_t arguments[] = {run.get(0x50f548), run.get(0x50f54c), uint32_t(targetX), uint32_t(targetX >> 32), uint32_t(targetY), uint32_t(targetY >> 32), 0, 0, 1};
        function_467ea0(run, object + 0x28, arguments, &fp);
        return 0;
    }
    uint32_t receiver = object + 0x28;
    Scratch local;
    uint32_t status = 0;
    fp.load(fp.memory(0x513e20));
    fp.load(fp.memory(0x50f548));
    local.bits(0xc, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_CHS);
    local.bits(0x34, fp.stored(true));
    fp.operand(CLAW_X87_COMP_F64, local.bits(0x34));
    fp.integer(run.get(receiver + 0x40c));
    fp.load(fp.memory(receiver + 0x58));
    local.bits(0x1c, fp.stored(true));
    status = fp.state.status;
    local.bits(0x14, fp.stored(true));
    if (status & 0x100) {
        fp.outside(0x4c96b0, {0x529c4c, local.words[0xc / 4], local.words[0x10 / 4]});
        return 0;
    }
    fp.load(local.bits(0xc));
    fp.operand(CLAW_X87_COMP_F64, fp.memory(0x513e20));
    status = fp.state.status;
    if (status & 0x100) {
        zeroVelocity(run, receiver);
        return 0;
    }
    fp.load(fp.memory(receiver + 0x10));
    fp.load(fp.memory(receiver + 0x18));
    fp.load(fp.memory(receiver + 0x20));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x24, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    local.bits(0x2c, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x3c, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x2c));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 3));
    fp.load(local.bits(0x1c));
    fp.load(local.bits(0x14));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 4));
    fp.operand(CLAW_X87_SUB_F64, fp.memory(receiver + 0x40));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_SUB_F64, fp.memory(receiver + 0x48));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50f568));
    fp.load(fp.memory(receiver + 0x50));
    fp.step(CLAW_X87_CHS);
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x44, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 3));
    local.bits(0x1c, fp.stored(false));
    fp.operand(CLAW_X87_COMP_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x4c, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x14, fp.stored(true));
    status = fp.state.status;
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    bool quadratic = (status & 0x100) != 0;
    if (!quadratic) {
        fp.load(local.bits(0x1c));
        fp.operand(CLAW_X87_COMP_F64, fp.memory(0x513e20));
        status = fp.state.status;
        quadratic = (status & 0x4100) == 0;
    }
    if (!quadratic) {
        fp.load(local.bits(0x14));
        fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 3));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.step(CLAW_X87_ABS);
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        fp.step(CLAW_X87_ABS);
        fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        fp.step(CLAW_X87_ABS);
        fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
        fp.load(local.bits(0x14));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        fp.step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        fp.step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 1));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.operand(CLAW_X87_MUL_F64, local.bits(0xc));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        fp.operand(CLAW_X87_MUL_F64, local.bits(0xc));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
        fp.operand(CLAW_X87_MUL_F64, local.bits(0xc));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
        uint64_t stored14 = fp.stored(true);
        run.put(receiver + 0x28, uint32_t(stored14));
        run.put(receiver + 0x2c, uint32_t(stored14 >> 32));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        uint64_t stored15 = fp.stored(true);
        run.put(receiver + 0x30, uint32_t(stored15));
        run.put(receiver + 0x34, uint32_t(stored15 >> 32));
        fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
        uint64_t stored16 = fp.stored(true);
        run.put(receiver + 0x38, uint32_t(stored16));
        run.put(receiver + 0x3c, uint32_t(stored16 >> 32));
        fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
        return 0;
    }
    fp.load(local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 2));
    fp.load(local.bits(0x2c));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 3));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 3));
    fp.load(local.bits(0x3c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 6));
    fp.load(local.bits(0x14));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5));
    fp.step(CLAW_X87_CHS);
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 5));
    fp.load(local.bits(0xc));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x14));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x14));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0xc));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.step(CLAW_X87_ST(CLAW_X87_ADDP, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x1c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    local.bits(0x34, fp.stored(false));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50f570));
    fp.step(CLAW_X87_ST(CLAW_X87_SUBP, 1));
    local.bits(0xc, fp.stored(true));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    fp.outside(0x4c96b0, {0x529c3c, local.words[0xc / 4], local.words[0x10 / 4]});
    fp.load(local.bits(0xc));
    fp.load(fp.memory(0x513e20));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_CHS);
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_COMPP);
    status = fp.state.status;
    if (status & 0x100) {
        fp.step(CLAW_X87_POP);
        fp.outside(0x4c96b0, {0x529c1c, local.words[0xc / 4], local.words[0x10 / 4]});
        return 0;
    }
    fp.operand(CLAW_X87_COM_F64, fp.memory(0x513e20));
    status = fp.state.status;
    if (status & 0x100) {
        fp.step(CLAW_X87_POP);
        fp.load(fp.memory(0x50f560));
    }
    fp.step(CLAW_X87_SQRT);
    fp.load(local.bits(0x1c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_SUB_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_ADD_TO0, 0));
    fp.load(local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_DIVP, 2));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    local.bits(0x24, fp.stored(false));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.step(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    fp.step(CLAW_X87_SQRT);
    fp.load(local.bits(0x2c));
    fp.load(local.bits(0x3c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    fp.step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 4));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    local.bits(0x34, fp.stored(true));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_MUL_F64, local.bits(0x24));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50f580));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50f580));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_SUBR_F64, local.bits(0x44));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_MUL_F64, fp.memory(0x50f580));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_SUBR_F64, local.bits(0x4c));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_SUBR_F64, local.bits(0x14));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_DIV_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    fp.operand(CLAW_X87_DIV_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    fp.operand(CLAW_X87_DIV_F64, local.bits(0x34));
    fp.step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    uint64_t stored17 = fp.stored(true);
    run.put(receiver + 0x28, uint32_t(stored17));
    run.put(receiver + 0x2c, uint32_t(stored17 >> 32));
    uint64_t stored18 = fp.stored(true);
    run.put(receiver + 0x30, uint32_t(stored18));
    run.put(receiver + 0x34, uint32_t(stored18 >> 32));
    uint64_t stored19 = fp.stored(true);
    run.put(receiver + 0x38, uint32_t(stored19));
    run.put(receiver + 0x3c, uint32_t(stored19 >> 32));
    fp.step(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    return 0;
}

// 0x487f20: leave the dive at its vertical or horizontal limit.
uint32_t function_487f20(Run &run, uint32_t receiver, const uint32_t *) {
    Floating fp(run);
    advance(run, receiver, &fp);
    fp.load(fp.memory(receiver + 0x70));
    fp.integer(run.get(receiver + 0x438));
    fp.step(CLAW_X87_COMPP);
    bool withdraw = (fp.state.status & 0x100) != 0;
    if (!withdraw) {
        fp.load(fp.memory(receiver + 0x68));
        fp.operand(CLAW_X87_COMP_F64, fp.memory(receiver + 0x98));
        withdraw = (fp.state.status & 0x4000) != 0;
    }
    if (!withdraw) {
        fp.load(fp.memory(receiver + 0x68));
        fp.operand(CLAW_X87_COMP_F64, fp.memory(receiver + 0x80));
        withdraw = (fp.state.status & 0x4000) != 0;
    }
    if (withdraw) {
        function_487f80(run, receiver, nullptr);
    }
    return 0;
}

// 0x488330: clamp withdrawal height and return to patrol.
uint32_t function_488330(Run &run, uint32_t receiver, const uint32_t *) {
    Floating fp(run);
    advance(run, receiver, &fp);
    fp.integer(run.get(receiver + 0x434));
    fp.load(fp.memory(receiver + 0x70));
    fp.step(CLAW_X87_ST(CLAW_X87_COMP_ST, 1));
    if (fp.state.status & 0x100) {
        uint64_t stored20 = fp.stored(true);
        run.put(receiver + 0x70, uint32_t(stored20));
        run.put(receiver + 0x74, uint32_t(stored20 >> 32));
        zeroVelocity(run, receiver + 0x28);
        run.vcall(receiver, 0x48);
    } else {
        fp.step(CLAW_X87_POP);
    }
    return 0;
}

// 0x488390: choose one of the two hit animations.
uint32_t function_488390(Run &run, uint32_t receiver, const uint32_t *) {
    changeState(run, receiver, 0x529bb8);
    sound(run, receiver, 0x42c, -0x18);
    uint32_t random = run.call(0x4a3050, 0);
    uint32_t index = run.get(receiver + (s32(random) % 100 < 50 ? 0x41c : 0x420));
    animation(run, receiver, index);
    return 0;
}

// 0x488420: restore the interrupted state after a hit animation.
uint32_t function_488420(Run &run, uint32_t receiver, const uint32_t *) {
    advance(run, receiver);
    uint32_t actor = run.get(receiver + 0x12c);
    if (!run.get(actor + 0x1a4) || run.get(actor + 0x19c)) {
        return 0;
    }
    uint32_t index = run.get(receiver + 0x24);
    run.put(0x5376b8, 0);
    uint32_t description;
    if (s32(index) < run.gets(0x5376a0) || s32(index) > run.gets(0x5376a4)) {
        uint32_t found = run.call(0x4db6e0, 0x537698, {index, 0});
        if (!found) {
            uint32_t args[] = {run.get(0x544b4c), 0xc};
            function_406da0(run, 0x537698, args);
            description = run.get(0x5376ac);
        } else {
            description = run.get(0x5376a8) + (index - run.get(0x5376a0)) * run.get(0x5376b0);
        }
    } else {
        description = run.get(0x5376a8) + (index - run.get(0x5376a0)) * run.get(0x5376b0);
    }
    uint32_t remaining = run.get(0x5376b8);
    uint32_t pending = run.get(0x5376b4);
    while (remaining) {
        if (pending) {
            run.call(0x4f6439, pending);
        }
        pending += 4;
        --remaining;
    }
    uint32_t name = run.call(0x4f6974, description, {0});
    changeState(run, receiver, name);
    uint32_t previousAnimation = run.get(receiver + 0x134);
    animation(run, receiver, previousAnimation);
    return 0;
}

// 0x488550: enter death, publish bounds, and configure the falling motion.
uint32_t function_488550(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t count = run.get(receiver + 0x2fc);
    uint32_t bits = count > 0x20 ? run.get(receiver + 0x300) : receiver + 0x300;
    bool already = count >= 5 && (run.get(bits) & 0x10);
    if (!already) {
        // Three saved registers and CALL precede the nested audible-drop path.
        uint32_t previousStack = run.stackPointer;
        run.stackPointer = run.automatic(-0x10);
        run.call(0x42df90, receiver + 0x128);
        run.stackPointer = previousStack;
    }
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 0x80);
    changeState(run, receiver, 0x5234f4);
    run.put(receiver + 0x20, 1);
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 1);
    count = run.get(receiver + 0x2fc);
    if (count) {
        bits = count > 0x20 ? run.get(receiver + 0x300) : receiver + 0x300;
        run.put(bits, run.get(bits) ^ 1);
    }
    uint32_t object = run.get(receiver + 0xc);
    if (run.get(object + 0x64) != 0x2134) {
        run.put(object + 0x64, 0x2134);
        run.put(object + 0x8, run.get(object + 0x8) | 0x20000);
    }
    run.put(receiver + 0x80, run.get(0x513e10));
    run.put(receiver + 0x84, run.get(0x513e14));
    run.put(receiver + 0x98, run.get(0x513e18));
    run.put(receiver + 0x9c, run.get(0x513e1c));
    run.put(receiver + 0x88, run.get(0x513e10));
    run.put(receiver + 0x8c, run.get(0x513e14));
    run.put(receiver + 0xa0, run.get(0x513e18));
    run.put(receiver + 0xa4, run.get(0x513e1c));
    run.put(receiver + 0x90, run.get(0x513e10));
    run.put(receiver + 0x94, run.get(0x513e14));
    run.put(receiver + 0xa8, run.get(0x513e18));
    run.put(receiver + 0xac, run.get(0x513e1c));
    run.put(run.get(receiver + 0xc) + 0xcc, 7);
    animation(run, receiver, run.get(receiver + 0x428));
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0x409f4000);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x58, 0);
    if (run.get(receiver + 0x18c) == 3) {
        run.put(receiver + 0x54, 0x40590000);
        run.put(receiver + 0x5c, 0xc0590000);
    } else {
        run.put(receiver + 0x54, 0xc0590000);
        run.put(receiver + 0x5c, 0xc0590000);
    }
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x64, 0);
    count = run.get(receiver + 0x2fc);
    if (count < 5) {
        run.call(0x4dbd20, receiver + 0x2f4, {4});
    } else {
        bits = count > 0x20 ? run.get(receiver + 0x300) : receiver + 0x300;
        run.put(bits, run.get(bits) | 0x10);
    }
    return 0;
}

// 0x488750: retire the actor once its death animation has ended.
uint32_t function_488750(Run &run, uint32_t receiver, const uint32_t *) {
    Floating fp(run);
    advance(run, receiver, &fp);
    if (run.get(run.get(receiver + 0x12c) + 0x38) == 0xffffffffu) {
        sound(run, receiver, 0x38c, -0x18, &fp);
        uint32_t actor = run.get(receiver + 0x12c);
        run.put(actor + 0x8, run.get(actor + 0x8) | 0x10000);
    }
    return 0;
}

int owned(uint32_t function) {
    switch (function) {
    case 0x406da0:
        return 2;
    case 0x467ea0:
        return 9;
    case 0x488550:
        return 1;
    case 0x4879a0:
    case 0x487b80:
    case 0x487f20:
    case 0x487f80:
    case 0x488330:
    case 0x488390:
    case 0x488420:
    case 0x488750:
        return 0;
    default:
        return -1;
    }
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x406da0:
        return function_406da0(run, receiver, arguments);
    case 0x467ea0:
        return function_467ea0(run, receiver, arguments);
    case 0x4879a0:
        return function_4879a0(run, receiver, arguments);
    case 0x487b80:
        return function_487b80(run, receiver, arguments);
    case 0x487f20:
        return function_487f20(run, receiver, arguments);
    case 0x487f80:
        return function_487f80(run, receiver, arguments);
    case 0x488330:
        return function_488330(run, receiver, arguments);
    case 0x488390:
        return function_488390(run, receiver, arguments);
    case 0x488420:
        return function_488420(run, receiver, arguments);
    case 0x488550:
        return function_488550(run, receiver, arguments);
    case 0x488750:
        return function_488750(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace
CLAW_MODULE_ENTRY(claw_level_five_seagull_states_entry, owned, body)
