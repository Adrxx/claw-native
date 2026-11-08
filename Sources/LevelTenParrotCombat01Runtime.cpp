// Level 10 parrot combat, recovered from original v1.0 functions.
#include "ClawRuntime.hpp"
namespace {
using claw::Run;
using claw::s32;
uint64_t bits(Run &run, uint32_t address) {
    return uint64_t(run.get(address)) | (uint64_t(run.get(address + 4)) << 32);
}
void writeBits(Run &run, uint32_t address, uint64_t value) {
    run.put(address, uint32_t(value));
    run.put(address + 4, uint32_t(value >> 32));
}
struct FP {
    Run &run;
    ClawX87State &state;
    FP(Run &run, ClawX87State &state) : run(run), state(state) {}
    uint32_t call(uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}, uint32_t push = 0) {
        state.popCount = 0;
        state.pushCount = push;
        state.returned = 0;
        state.eax = 0;
        state.edx = 0;
        return run.call_x87_exact(function, receiver, state, arguments);
    }
    void op(uint32_t operation) {
        run.x87_step(operation, state);
    }
    void memory(uint32_t operation, uint64_t value) {
        run.x87_step(operation, state, {uint32_t(value), uint32_t(value >> 32)});
    }
    void load(uint64_t value) {
        memory(CLAW_X87_F64, value);
    }
    void integer(uint32_t value) {
        run.x87_step(CLAW_X87_I32, state, {value});
    }
    uint64_t store(bool pop = true) {
        return run.x87_step(pop ? CLAW_X87_STP_F64 : CLAW_X87_ST_F64, state);
    }
    uint32_t status() const {
        return state.status;
    }
};
uint32_t compare(Run &run, FP &fp, uint32_t a, uint32_t b) {
    fp.load(bits(run, a));
    fp.memory(CLAW_X87_COMP_F64, bits(run, b));
    return fp.status();
}
uint32_t compareInteger(Run &run, FP &fp, uint32_t integer, uint32_t value) {
    fp.load(bits(run, value));
    fp.integer(integer);
    fp.op(CLAW_X87_COMPP);
    return fp.status();
}
uint64_t subtract(Run &run, FP &fp, uint32_t a, uint32_t b) {
    fp.load(bits(run, a));
    fp.memory(CLAW_X87_SUB_F64, bits(run, b));
    return fp.store();
}
void negateGlobal(Run &run, FP &fp, uint32_t destination, uint32_t source) {
    fp.load(bits(run, source));
    fp.op(CLAW_X87_CHS);
    writeBits(run, destination, fp.store());
}
// +0xc scene object, +0x10 state holder, +0x12c sprite,
// +0x134 saved animation, +0x138/+0x140 horizontal collision extents.
void flipOwn(Run &run, uint32_t p) {
    uint32_t left = run.get(p + 0x138);
    uint32_t right = run.get(p + 0x140);
    run.put(p + 0x138, 0u - right);
    run.put(p + 0x140, 0u - left);
}
void flipSpriteBounds(Run &run, uint32_t sprite, uint32_t offset) {
    uint32_t left = run.get(sprite + offset);
    if (left != 0x80000000u) {
        uint32_t right = run.get(sprite + offset + 8);
        run.put(sprite + offset, 0u - right);
        run.put(sprite + offset + 8, 0u - left);
    }
}
void initialFacing(Run &run, uint32_t p) {
    if (run.get(p + 0x18c) == 2) {
        uint32_t sprite = run.get(p + 0x12c);
        if (!(run.get8(sprite + 0x40) & 2)) {
            flipOwn(run, p);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            run.call(0x4060b0, run.get(p + 0x12c));
        }
    } else {
        run.call(0x406310, p + 0x128);
    }
}
void setState(Run &run, uint32_t p, uint32_t name) {
    run.put(p + 0x24, run.get(run.get(p + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(p + 0x10) + 0x1c, state);
}
void setAnimation(Run &run, uint32_t p, uint32_t animationOffset) {
    uint32_t sprite = run.get(p + 0x12c);
    uint32_t animation = run.get(p + animationOffset);
    run.put(p + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
}
void updateAnimation(Run &run, FP &fp, uint32_t p, bool flyAbout = false) {
    fp.call(0x4c82a0, run.get(p + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t sprite = run.get(p + 0x12c);
    if (run.get(sprite + 0x1a4) && !run.get(sprite + 0x19c)) {
        if (flyAbout) {
            uint32_t animation = run.get(p + 0x410);
            sprite = run.get(p + 0x12c);
            run.put(p + 0x134, run.get(sprite + 0x190));
            fp.call(0x420a10, sprite, {animation, 0});
        } else {
            setAnimation(run, p, 0x410);
        }
    }
}
void copyBounds(Run &run, uint32_t p, uint32_t sourceOffset) {
    uint32_t object = run.get(p + 0xc);
    run.put(object + 0x138, run.get(p + sourceOffset));
    run.put(object + 0x13c, run.get(p + sourceOffset + 4));
    run.put(object + 0x140, run.get(p + sourceOffset + 8));
    run.put(object + 0x144, run.get(p + sourceOffset + 12));
    if (run.get8(run.get(p + 0x12c) + 0x40) & 2) {
        object = run.get(p + 0xc);
        uint32_t right = run.get(object + 0x140);
        uint32_t left = run.get(object + 0x138);
        run.put(object + 0x138, 0u - right);
        run.put(run.get(p + 0xc) + 0x140, 0u - left);
    }
}
void faceTarget(Run &run, uint32_t p, bool targetGreater, bool secondBounds, bool callFirst) {
    uint32_t sprite = run.get(p + 0x12c);
    bool facing = (run.get8(sprite + 0x40) & 2) != 0;
    if (facing == targetGreater)
        return;
    flipOwn(run, p);
    uint32_t flags = run.get(sprite + 0x40);
    run.put(sprite + 0x40, targetGreater ? flags | 2 : flags & 0xfffffffd);
    sprite = run.get(p + 0x12c);
    if (callFirst) {
        run.call(0x406120, sprite);
    } else {
        flipSpriteBounds(run, sprite, 0x118);
    }
    if (secondBounds) {
        flipSpriteBounds(run, sprite, 0x128);
    } else {
        run.call(0x406150, sprite);
    }
    run.call(0x406180, sprite);
}
void moveTo(Run &run, FP &fp, uint32_t p, uint64_t x, uint64_t y) {
    (void)run;
    fp.call(0x420dd0, p + 0x28,
            {uint32_t(x), uint32_t(x >> 32), uint32_t(y), uint32_t(y >> 32), 0, 0}, 1);
}
uint32_t function_466a80(Run &run, FP &fp, uint32_t p);
uint32_t function_4677b0(Run &run, FP &fp, uint32_t p);
// 0x466790. LS_FLYABOUT.
uint32_t function_466790(Run &run, FP &fp, uint32_t p) {
    updateAnimation(run, fp, p, true);
    if (s32(run.call(0x4a3050, 0)) % 100 < 1 &&
        run.get(0x537210) - run.get(p + 0x400) >= run.get(p + 0x404) &&
        run.get(0x53c9c0) == 2) {
        uint32_t value = run.call(0x4a3050, 0);
        uint32_t sign = s32(value) < 0 ? 0xffffffffu : 0;
        uint32_t index = ((((value ^ sign) - sign) & 1) ^ sign) - sign;
        run.call(0x48ce40, 0, {run.get(p + 0xc), run.get(p + 0x424 + index * 4), 0});
        run.put(p + 0x404, 15000);
        run.put(p + 0x400, run.get(0x537210));
    }
    if (!(compare(run, fp, p + 0x70, p + 0x88) & 0x4000))
        return 0;
    uint32_t playerX = run.get(run.get(0x537e88) + 0x4c);
    run.put(p + 0x58, 0);
    run.put(p + 0x5c, 0);
    if (compare(run, fp, p + 0x50, 0x50ebf8) & 0x4000) {
        bool left = (compare(run, fp, p + 0x68, 0x50ebf0) & 0x4100) != 0;
        if (left) {
            run.put(p + 0x50, run.get(0x50ebe0));
            run.put(p + 0x54, run.get(0x50ebe4));
        } else {
            negateGlobal(run, fp, p + 0x50, 0x50ebe0);
        }
        faceTarget(run, p, left, false, true);
    }
    if (compare(run, fp, p + 0x68, p + 0x80) & 0x4000) {
        run.put(p + 0x50, run.get(0x50ebe0));
        run.put(p + 0x54, run.get(0x50ebe4));
        faceTarget(run, p, true, false, true);
        if (s32(playerX) >= 0x9f68 && s32(run.call(0x4a3050, 0)) % 100 < 75)
            function_466a80(run, fp, p);
    }
    if (compare(run, fp, p + 0x68, p + 0x98) & 0x4000) {
        negateGlobal(run, fp, p + 0x50, 0x50ebe0);
        faceTarget(run, p, false, false, false);
        if (s32(playerX) <= 0x9f68 && s32(run.call(0x4a3050, 0)) % 100 < 75)
            function_466a80(run, fp, p);
    }
    return 0;
}
// 0x466a80: ballistic arithmetic with each original rounding point.
void setupVelocity(Run &run, FP &fp, uint32_t p, uint64_t x, uint64_t y) {
    uint64_t local[24]{};
    local[0xc / 4] = bits(run, 0x50ebd8);
    local[0x34 / 4] = x;
    local[0x1c / 4] = y;
    fp.load(bits(run, 0x513e20));
    fp.op(CLAW_X87_CHS);
    local[0x14 / 4] = fp.store();
    fp.load(local[0xc / 4]);
    fp.memory(CLAW_X87_COMP_F64, local[0x14 / 4]);
    if (fp.status() & 0x100) {
        uint64_t speed = local[0xc / 4];
        run.call(0x4c96b0, 0, {0x529c4c, uint32_t(speed), uint32_t(speed >> 32)});
        return;
    }
    fp.load(local[0xc / 4]);
    fp.memory(CLAW_X87_COMP_F64, bits(run, 0x513e20));
    if (fp.status() & 0x100) {
        run.put(p + 0x50, 0);
        run.put(p + 0x58, 0);
        run.put(p + 0x60, 0);
        run.put(p + 0x54, 0);
        run.put(p + 0x5c, 0);
        run.put(p + 0x64, 0);
        return;
    }
    fp.load(bits(run, p + 0x38));
    fp.load(bits(run, p + 0x40));
    fp.load(bits(run, p + 0x48));
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x24 / 4] = fp.store(false);
    fp.op(CLAW_X87_XCH_ST | 1);
    local[0x2c / 4] = fp.store(false);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, local[0x24 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x3c / 4] = fp.store(false);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, local[0x2c / 4]);
    fp.op(CLAW_X87_LD_ST | 1);
    fp.op(CLAW_X87_MUL_TO0 | 2);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ADDP | 3);
    fp.load(local[0x34 / 4]);
    fp.load(local[0x1c / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_ADDP | 4);
    fp.memory(CLAW_X87_SUB_F64, bits(run, p + 0x68));
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_SUB_F64, bits(run, p + 0x70));
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.memory(CLAW_X87_MUL_F64, bits(run, 0x50ec10));
    fp.load(bits(run, p + 0x78));
    fp.op(CLAW_X87_CHS);
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x44 / 4] = fp.store(false);
    fp.op(CLAW_X87_STP_ST | 3);
    local[0x1c / 4] = fp.store(false);
    fp.memory(CLAW_X87_COMP_F64, local[0x14 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x4c / 4] = fp.store(false);
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x14 / 4] = fp.store(true);
    fp.op(CLAW_X87_XCH_ST | 1);
    bool accelerated = (fp.status() & 0x100) != 0;
    if (!accelerated) {
    fp.load(local[0x1c / 4]);
    fp.memory(CLAW_X87_COMP_F64, bits(run, 0x513e20));
    accelerated = !(fp.status() & 0x4100);
    }
    if (!accelerated) {
    fp.op(CLAW_X87_LD_ST | 1);
    fp.load(local[0x14 / 4]);
    fp.op(CLAW_X87_LD_ST | 2);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_ABS);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ABS);
    fp.op(CLAW_X87_ADDP | 1);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ABS);
    fp.op(CLAW_X87_ADDP | 1);
    fp.load(local[0x14 / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.op(CLAW_X87_DIV_TO0 | 1);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_DIV_TO0 | 1);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.op(CLAW_X87_DIV_TO0 | 1);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_MUL_F64, local[0xc / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.memory(CLAW_X87_MUL_F64, local[0xc / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_MUL_F64, local[0xc / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    writeBits(run, p + 0x50, fp.store(true));
    fp.op(CLAW_X87_XCH_ST | 1);
    writeBits(run, p + 0x58, fp.store(true));
    fp.op(CLAW_X87_XCH_ST | 1);
    writeBits(run, p + 0x60, fp.store(true));
    fp.op(CLAW_X87_STP_ST | 0);
    return;
    }
    fp.load(local[0x24 / 4]);
    fp.op(CLAW_X87_MUL_TO0 | 2);
    fp.load(local[0x2c / 4]);
    fp.op(CLAW_X87_MUL_TO0 | 2);
    fp.op(CLAW_X87_LD_ST | 3);
    fp.op(CLAW_X87_LD_ST | 3);
    fp.load(local[0x3c / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_MUL_TO0 | 6);
    fp.load(local[0x14 / 4]);
    fp.op(CLAW_X87_XCH_ST | 5);
    fp.op(CLAW_X87_CHS);
    fp.op(CLAW_X87_XCH_ST | 4);
    fp.op(CLAW_X87_SUBP | 4);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_MUL_TO0 | 5);
    fp.load(local[0xc / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.memory(CLAW_X87_MUL_F64, local[0x14 / 4]);
    fp.op(CLAW_X87_SUBP | 4);
    fp.op(CLAW_X87_XCH_ST | 4);
    fp.memory(CLAW_X87_MUL_F64, local[0x14 / 4]);
    fp.op(CLAW_X87_XCH_ST | 4);
    fp.op(CLAW_X87_ADDP | 1);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, local[0xc / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.op(CLAW_X87_ADDP | 1);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_SUBP | 1);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, local[0x1c / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    local[0x34 / 4] = fp.store(false);
    fp.memory(CLAW_X87_MUL_F64, local[0x34 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, bits(run, 0x50ec18));
    fp.op(CLAW_X87_SUBP | 1);
    local[0xc / 4] = fp.store(true);
    fp.op(CLAW_X87_STP_ST | 0);
    fp.op(CLAW_X87_STP_ST | 0);
    uint64_t discriminant = local[0xc / 4];
    run.call(0x4c96b0, 0, {0x529c3c, uint32_t(discriminant), uint32_t(discriminant >> 32)});
    fp.load(local[0xc / 4]);
    fp.load(bits(run, 0x513e20));
    fp.op(CLAW_X87_LD_ST | 1);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_CHS);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_COMPP);
    if (fp.status() & 0x100) {
    fp.op(CLAW_X87_POP);
    run.call(0x4c96b0, 0, {0x529c1c, uint32_t(discriminant), uint32_t(discriminant >> 32)});
    return;
    }
    fp.memory(CLAW_X87_COM_F64, bits(run, 0x513e20));
    if (fp.status() & 0x100) {
    fp.op(CLAW_X87_STP_ST | 0);
    fp.load(bits(run, 0x50ebf8));
    }
    fp.op(CLAW_X87_SQRT);
    fp.load(local[0x1c / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_SUB_F64, local[0x34 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ADD_TOI | 0);
    fp.load(local[0x24 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_DIVP | 2);
    fp.op(CLAW_X87_XCH_ST | 1);
    local[0x24 / 4] = fp.store(false);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_LD_ST | 1);
    fp.op(CLAW_X87_SQRT);
    fp.load(local[0x2c / 4]);
    fp.load(local[0x3c / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.op(CLAW_X87_MUL_TO0 | 4);
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x34 / 4] = fp.store(true);
    fp.memory(CLAW_X87_MUL_F64, local[0x24 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_MUL_F64, local[0x24 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, bits(run, 0x50ec28));
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_MUL_F64, bits(run, 0x50ec28));
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_SUBR_F64, local[0x44 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, bits(run, 0x50ec28));
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_SUBR_F64, local[0x4c / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_SUBR_F64, local[0x14 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_DIV_F64, local[0x34 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_DIV_F64, local[0x34 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_DIV_F64, local[0x34 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    writeBits(run, p + 0x50, fp.store(true));
    writeBits(run, p + 0x58, fp.store(true));
    writeBits(run, p + 0x60, fp.store(true));
    fp.op(CLAW_X87_STP_ST | 0);
}
// 0x466ea0: ballistic arithmetic with each original rounding point.
void strikeVelocity(Run &run, FP &fp, uint32_t p, uint64_t x, uint64_t y) {
    uint64_t local[24]{};
    local[0x10 / 4] = bits(run, 0x50ebd8);
    local[0x38 / 4] = y;
    local[0x20 / 4] = x;
    fp.load(bits(run, 0x513e20));
    fp.op(CLAW_X87_CHS);
    local[0x18 / 4] = fp.store();
    fp.load(local[0x10 / 4]);
    fp.memory(CLAW_X87_COMP_F64, local[0x18 / 4]);
    if (fp.status() & 0x100) {
        uint64_t speed = local[0x10 / 4];
        run.call(0x4c96b0, 0, {0x529c4c, uint32_t(speed), uint32_t(speed >> 32)});
        return;
    }
    fp.load(local[0x10 / 4]);
    fp.memory(CLAW_X87_COMP_F64, bits(run, 0x513e20));
    if (fp.status() & 0x100) {
        run.put(p + 0x50, 0);
        run.put(p + 0x58, 0);
        run.put(p + 0x60, 0);
        run.put(p + 0x54, 0);
        run.put(p + 0x5c, 0);
        run.put(p + 0x64, 0);
        return;
    }
    fp.load(bits(run, p + 0x38));
    fp.load(bits(run, p + 0x40));
    fp.load(bits(run, p + 0x48));
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x28 / 4] = fp.store(false);
    fp.op(CLAW_X87_XCH_ST | 1);
    local[0x30 / 4] = fp.store(false);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, local[0x28 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x40 / 4] = fp.store(false);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, local[0x30 / 4]);
    fp.op(CLAW_X87_LD_ST | 1);
    fp.op(CLAW_X87_MUL_TO0 | 2);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ADDP | 3);
    fp.load(local[0x20 / 4]);
    fp.load(local[0x38 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_ADDP | 4);
    fp.memory(CLAW_X87_SUB_F64, bits(run, p + 0x68));
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_SUB_F64, bits(run, p + 0x70));
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.memory(CLAW_X87_MUL_F64, bits(run, 0x50ec10));
    fp.load(bits(run, p + 0x78));
    fp.op(CLAW_X87_CHS);
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x48 / 4] = fp.store(false);
    fp.op(CLAW_X87_STP_ST | 3);
    local[0x20 / 4] = fp.store(false);
    fp.memory(CLAW_X87_COMP_F64, local[0x18 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x50 / 4] = fp.store(false);
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x18 / 4] = fp.store(true);
    fp.op(CLAW_X87_XCH_ST | 1);
    bool accelerated = (fp.status() & 0x100) != 0;
    if (!accelerated) {
    fp.load(local[0x20 / 4]);
    fp.memory(CLAW_X87_COMP_F64, bits(run, 0x513e20));
    accelerated = !(fp.status() & 0x4100);
    }
    if (!accelerated) {
    fp.op(CLAW_X87_LD_ST | 0);
    fp.op(CLAW_X87_LD_ST | 2);
    fp.load(local[0x18 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_ABS);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ABS);
    fp.op(CLAW_X87_ADDP | 1);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ABS);
    fp.op(CLAW_X87_ADDP | 1);
    fp.load(local[0x18 / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.op(CLAW_X87_DIV_TO0 | 1);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_DIV_TO0 | 1);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.op(CLAW_X87_DIV_TO0 | 1);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_MUL_F64, local[0x10 / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.memory(CLAW_X87_MUL_F64, local[0x10 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_MUL_F64, local[0x10 / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    writeBits(run, p + 0x50, fp.store(true));
    fp.op(CLAW_X87_XCH_ST | 1);
    writeBits(run, p + 0x58, fp.store(true));
    fp.op(CLAW_X87_XCH_ST | 1);
    writeBits(run, p + 0x60, fp.store());
    fp.op(CLAW_X87_POP);
    return;
    }
    fp.load(local[0x28 / 4]);
    fp.op(CLAW_X87_MUL_TO0 | 2);
    fp.load(local[0x30 / 4]);
    fp.op(CLAW_X87_MUL_TO0 | 2);
    fp.op(CLAW_X87_LD_ST | 3);
    fp.op(CLAW_X87_LD_ST | 3);
    fp.load(local[0x40 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_MUL_TO0 | 6);
    fp.load(local[0x18 / 4]);
    fp.op(CLAW_X87_XCH_ST | 5);
    fp.op(CLAW_X87_CHS);
    fp.op(CLAW_X87_XCH_ST | 4);
    fp.op(CLAW_X87_SUBP | 4);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_MUL_TO0 | 5);
    fp.load(local[0x10 / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.memory(CLAW_X87_MUL_F64, local[0x18 / 4]);
    fp.op(CLAW_X87_SUBP | 4);
    fp.op(CLAW_X87_XCH_ST | 4);
    fp.memory(CLAW_X87_MUL_F64, local[0x18 / 4]);
    fp.op(CLAW_X87_XCH_ST | 4);
    fp.op(CLAW_X87_ADDP | 1);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, local[0x10 / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.op(CLAW_X87_ADDP | 1);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_SUBP | 1);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, local[0x20 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    local[0x38 / 4] = fp.store(false);
    fp.memory(CLAW_X87_MUL_F64, local[0x38 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, bits(run, 0x50ec18));
    fp.op(CLAW_X87_SUBP | 1);
    local[0x10 / 4] = fp.store(true);
    fp.op(CLAW_X87_STP_ST | 0);
    fp.op(CLAW_X87_STP_ST | 0);
    uint64_t discriminant = local[0x10 / 4];
    run.call(0x4c96b0, 0, {0x529c3c, uint32_t(discriminant), uint32_t(discriminant >> 32)});
    fp.load(local[0x10 / 4]);
    fp.load(bits(run, 0x513e20));
    fp.op(CLAW_X87_LD_ST | 1);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_CHS);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_COMPP);
    if (fp.status() & 0x100) {
    fp.op(CLAW_X87_POP);
    run.call(0x4c96b0, 0, {0x529c1c, uint32_t(discriminant), uint32_t(discriminant >> 32)});
    return;
    }
    fp.memory(CLAW_X87_COM_F64, bits(run, 0x513e20));
    if (fp.status() & 0x100) {
    fp.op(CLAW_X87_STP_ST | 0);
    fp.load(bits(run, 0x50ebf8));
    }
    fp.op(CLAW_X87_SQRT);
    fp.load(local[0x20 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_SUB_F64, local[0x38 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ADD_TOI | 0);
    fp.load(local[0x28 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_DIVP | 2);
    fp.op(CLAW_X87_XCH_ST | 1);
    local[0x28 / 4] = fp.store(false);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_LD_ST | 1);
    fp.op(CLAW_X87_SQRT);
    fp.load(local[0x30 / 4]);
    fp.load(local[0x40 / 4]);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.op(CLAW_X87_MUL_TO0 | 4);
    fp.op(CLAW_X87_XCH_ST | 2);
    local[0x38 / 4] = fp.store(true);
    fp.memory(CLAW_X87_MUL_F64, local[0x28 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_MUL_F64, local[0x28 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, bits(run, 0x50ec28));
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_MUL_F64, bits(run, 0x50ec28));
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_SUBR_F64, local[0x48 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_MUL_F64, bits(run, 0x50ec28));
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_SUBR_F64, local[0x50 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_SUBR_F64, local[0x18 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_DIV_F64, local[0x38 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.memory(CLAW_X87_DIV_F64, local[0x38 / 4]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.memory(CLAW_X87_DIV_F64, local[0x38 / 4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    writeBits(run, p + 0x50, fp.store(true));
    writeBits(run, p + 0x58, fp.store(true));
    writeBits(run, p + 0x60, fp.store(true));
    fp.op(CLAW_X87_STP_ST | 0);
}
// 0x466a80. Begin a strike setup.
uint32_t function_466a80(Run &run, FP &fp, uint32_t p) {
    initialFacing(run, p);
    if (run.get(0x53c9c0) != 2 || !run.get(0x537b14))
        return 0;
    uint64_t x;
    if (s32(run.get(run.get(0x537e88) + 0x4c)) <= 0x9f68)
        x = subtract(run, fp, p + 0x98, 0x50ec00);
    else
        x = subtract(run, fp, p + 0x80, 0x50ec08);
    writeBits(run, p + 0x440, x);
    setState(run, p, 0x529bf8);
    setAnimation(run, p, 0x410);
    uint32_t playerY = run.get(run.get(0x537e88) + 0x50);
    uint32_t random = run.call(0x4a3050, 0);
    fp.integer(playerY - uint32_t(s32(random) % 31));
    uint64_t y = fp.store();
    writeBits(run, p + 0x448, y);
    setupVelocity(run, fp, p, bits(run, p + 0x440), y);
    return 0;
}
// 0x466e40. LS_STRIKESETUP.
uint32_t function_466e40(Run &run, FP &fp, uint32_t p) {
    fp.call(0x4c82a0, run.get(p + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (!(compare(run, fp, p + 0x70, p + 0x448) & 0x4100) ||
        (compare(run, fp, p + 0x68, p + 0x98) & 0x4000) ||
        (compare(run, fp, p + 0x68, p + 0x80) & 0x4000))
        run.vcall(p, 0x58);
    return 0;
}
// 0x466ea0. Begin a strike.
uint32_t function_466ea0(Run &run, FP &fp, uint32_t p) {
    initialFacing(run, p);
    copyBounds(run, p, 0x220);
    setState(run, p, 0x52720c);
    setAnimation(run, p, 0x408);
    uint32_t sprite = run.get(p + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xfffffffe);
    uint64_t y = bits(run, p + 0x448);
    fp.integer(run.get(run.get(0x537e88) + 0x4c));
    uint64_t x = fp.store();
    writeBits(run, p + 0x440, x);
    strikeVelocity(run, fp, p, x, y);
    uint32_t sound = run.get(p + 0x41c);
    if (sound && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    return 0;
}
// 0x467280. LS_STRIKE.
uint32_t function_467280(Run &run, FP &fp, uint32_t p) {
    fp.call(0x4c82a0, run.get(p + 0x12c) + 0x188, {run.get(0x5430c4)});
    if ((compare(run, fp, p + 0x68, p + 0x98) & 0x4000) ||
        (compare(run, fp, p + 0x68, p + 0x80) & 0x4000))
        fp.call(0x466580, p);
    return 0;
}
// 0x4672d0. Begin returning to idle.
uint32_t function_4672d0(Run &run, FP &fp, uint32_t p) {
    setState(run, p, 0x529be8);
    copyBounds(run, p, 0x210);
    setAnimation(run, p, 0x410);
    uint32_t orientationStatus = compareInteger(run, fp, run.get(p + 0x434), p + 0x68);
    bool targetGreater = !(orientationStatus & 0x4100);
    faceTarget(run, p, targetGreater, false, false);
    run.put(p + 0x40, 0);
    run.put(p + 0x44, 0x408f4000);
    fp.integer(run.get(p + 0x438));
    uint64_t y = fp.store();
    fp.integer(run.get(p + 0x434));
    uint64_t x = fp.store();
    moveTo(run, fp, p, x, y);
    fp.op(CLAW_X87_POP);
    return 0;
}
// 0x467470. LS_FLYTOIDLE.
uint32_t function_467470(Run &run, FP &fp, uint32_t p) {
    updateAnimation(run, fp, p);
    uint32_t velocity = compare(run, fp, p + 0x50, 0x50ebf8);
    bool reached = false;
    if (!(velocity & 0x4100))
        reached = (compareInteger(run, fp, run.get(p + 0x434), p + 0x68) & 0x4100) != 0;
    if (!reached && (compare(run, fp, p + 0x50, 0x50ebf8) & 0x100))
        reached = !(compareInteger(run, fp, run.get(p + 0x434), p + 0x68) & 0x4100);
    if (reached) {
        run.put(p + 0x40, 0);
        run.put(p + 0x44, 0);
        run.vcall(p, 0x48);
    }
    return 0;
}
// 0x467530. Begin flying to Marrow.
uint32_t function_467530(Run &run, FP &fp, uint32_t p) {
    setState(run, p, 0x529bd8);
    setAnimation(run, p, 0x410);
    uint32_t marrow = run.get(0x537b14);
    uint64_t y = subtract(run, fp, marrow + 0x70, 0x50ec30);
    fp.integer(run.get(marrow + 0x4d0));
    fp.memory(CLAW_X87_ADD_F64, bits(run, marrow + 0x68));
    uint64_t x = fp.store();
    fp.load(bits(run, p + 0x68));
    fp.memory(CLAW_X87_COMP_F64, x);
    bool targetGreater = (fp.status() & 0x100) != 0;
    faceTarget(run, p, targetGreater, true, false);
    fp.call(0x467ea0, p + 0x28,
             {run.get(0x50ebe0), run.get(0x50ebe4), uint32_t(x), uint32_t(x >> 32),
              uint32_t(y), uint32_t(y >> 32), 0, 0, 1});
    run.put(p + 0x440, uint32_t(x));
    run.put(p + 0x448, uint32_t(y));
    run.put(p + 0x444, uint32_t(x >> 32));
    run.put(p + 0x44c, uint32_t(y >> 32));
    return 0;
}
bool reachedTarget(Run &run, FP &fp, uint32_t p) {
    if (!(compare(run, fp, p + 0x50, 0x50ebf8) & 0x4100) &&
        !(compare(run, fp, p + 0x68, p + 0x440) & 0x100))
        return true;
    if (compare(run, fp, p + 0x50, 0x50ebf8) & 0x100)
        return (compare(run, fp, p + 0x68, p + 0x440) & 0x100) != 0;
    return false;
}
// 0x467700. LS_FLYTOMARROW.
uint32_t function_467700(Run &run, FP &fp, uint32_t p) {
    updateAnimation(run, fp, p);
    if (reachedTarget(run, fp, p)) {
        run.put(p + 0x40, 0);
        run.put(p + 0x44, 0);
        function_4677b0(run, fp, p);
    }
    return 0;
}
// 0x4677b0. Begin carrying Marrow.
uint32_t function_4677b0(Run &run, FP &fp, uint32_t p) {
    setState(run, p, 0x529bc8);
    setAnimation(run, p, 0x410);
    uint32_t marrow = run.get(0x537b14);
    uint32_t high;
    if (s32(run.get(run.get(0x537e88) + 0x4c)) < 0x9f68) {
        run.put(marrow + 0x98, run.get(0x513e18));
        run.put(marrow + 0x9c, run.get(0x513e1c));
        high = 0x40e40ce0;
    } else {
        run.put(marrow + 0x80, run.get(0x513e10));
        run.put(marrow + 0x84, run.get(0x513e14));
        high = 0x40e3cd20;
    }
    uint64_t x = uint64_t(high) << 32;
    fp.load(bits(run, marrow + 0x70));
    fp.load(bits(run, p + 0x68));
    fp.memory(CLAW_X87_COMP_F64, x);
    bool targetGreater = (fp.status() & 0x100) != 0;
    fp.memory(CLAW_X87_SUB_F64, bits(run, 0x50ec48));
    uint64_t y = fp.store();
    uint32_t sprite = run.get(p + 0x12c);
    if (((run.get8(sprite + 0x40) & 2) != 0) != targetGreater) {
        flipOwn(run, p);
        uint32_t flags = run.get(sprite + 0x40);
        run.put(sprite + 0x40, targetGreater ? flags | 2 : flags & 0xfffffffd);
        sprite = run.get(p + 0x12c);
        if (targetGreater)
            flipSpriteBounds(run, sprite, 0x118);
        else
            run.call(0x406120, sprite);
        run.call(0x406150, sprite);
        run.call(0x406180, sprite);
    }
    run.put(p + 0x40, 0);
    run.put(p + 0x44, 0x40690000);
    moveTo(run, fp, p, x, y);
    run.put(p + 0x440, 0);
    run.put(p + 0x448, uint32_t(y));
    run.put(p + 0x444, high);
    run.put(p + 0x44c, uint32_t(y >> 32));
    marrow = run.get(0x537b14);
    fp.op(CLAW_X87_POP);
    uint32_t sound = run.get(marrow + 0x484);
    run.put(marrow + 0x4b4, 1);
    run.call(0x48ce40, 0, {run.get(marrow + 0xc), sound, 0});
    return 0;
}
// 0x4679a0. LS_CARRYMARROW.
uint32_t function_4679a0(Run &run, FP &fp, uint32_t p) {
    updateAnimation(run, fp, p);
    if (reachedTarget(run, fp, p)) {
        run.put(p + 0x40, 0);
        run.put(p + 0x44, 0);
        fp.call(0x466580, p);
        uint32_t marrow = run.get(0x537b14);
        run.put(marrow + 0x40, 0);
        run.put(marrow + 0x44, 0x409f4000);
        uint32_t sprite = run.get(marrow + 0x12c);
        run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xfffffffb);
        sprite = run.get(marrow + 0x12c);
        run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xffffff7f);
        uint32_t object = run.get(marrow + 0xc);
        run.put(marrow + 0x20, 2);
        run.put(object + 0xcc, 8);
        sprite = run.get(marrow + 0x12c);
        run.put(sprite + 0x50, run.get(sprite + 0x50) - 0x20);
        uint32_t binding = run.get(marrow + 0x128);
        run.call(0x4cd800, run.get(run.get(binding + 0xc) + 0x24), {binding, 0});
        run.put(run.get(marrow + 0x128) + 0xcc, 1);
        uint32_t next = run.get(run.get(marrow + 0xc) + 0x10c);
        uint32_t method = run.get(run.get(marrow) + 0x44);
        run.put(marrow + 0x4b8, 0);
        run.put(marrow + 0x4c0, next);
        run.call(method, marrow);
    }
    return 0;
}
int owned(uint32_t function) {
    switch (function) {
    case 0x466790:
    case 0x466a80:
    case 0x466e40:
    case 0x466ea0:
    case 0x467280:
    case 0x4672d0:
    case 0x467470:
    case 0x467530:
    case 0x467700:
    case 0x4677b0:
    case 0x4679a0:
        return 0;
    default:
        return -1;
    }
}
uint32_t dispatch(Run &run, FP &fp, uint32_t function, uint32_t p) {
    switch (function) {
    case 0x466790:
        return function_466790(run, fp, p);
    case 0x466a80:
        return function_466a80(run, fp, p);
    case 0x466e40:
        return function_466e40(run, fp, p);
    case 0x466ea0:
        return function_466ea0(run, fp, p);
    case 0x467280:
        return function_467280(run, fp, p);
    case 0x4672d0:
        return function_4672d0(run, fp, p);
    case 0x467470:
        return function_467470(run, fp, p);
    case 0x467530:
        return function_467530(run, fp, p);
    case 0x467700:
        return function_467700(run, fp, p);
    case 0x4677b0:
        return function_4677b0(run, fp, p);
    case 0x4679a0:
        return function_4679a0(run, fp, p);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
uint32_t body(Run &run, uint32_t function, uint32_t p, const uint32_t *) {
    auto state = run.x87_entry(function);
    FP fp(run, state);
    uint32_t result = dispatch(run, fp, function, p);
    run.x87_finish(function, state);
    return result;
}

}
CLAW_MODULE_ENTRY(claw_level_ten_parrot_combat_01_entry, owned, body)
