// Level 4 Katherine states
//
// Recovered from the original state and animation entry points.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Actor +0x0 vtable, +0xc owner, +0x10 state record, +0x20 motion state,
// +0x24 previous state, +0x38/+0x40/+0x48 acceleration, +0x50..0x64 velocity,
// +0x68/+0x70/+0x78 position, +0x128 entity, +0x12c sprite,
// +0x134 animation origin, +0x138/+0x140 horizontal bounds,
// +0x184 behavior, +0x18c facing, +0x350/+0x464/+0x468 animation clocks,
// +0x3a0 stab resource, +0x3c4 target distance.
// Sprite +0x8 flags, +0xc scene, +0x38 sound enable, +0x40 mirroring,
// +0x118/+0x120, +0x128/+0x130, +0x138/+0x140 optional rectangle bounds,
// +0x188 animation timer, +0x190 origin, +0x19c progress, +0x1a4 active.


// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x454a10:
        return 0;
    case 0x454b90:
        return 0;
    case 0x454c20:
        return 0;
    case 0x454cb0:
        return 0;
    case 0x4550e0:
        return 0;
    case 0x455230:
        return 0;
    case 0x455280:
        return 0;
    case 0x4552d0:
        return 0;
    case 0x455360:
        return 2;
    case 0x4553a0:
        return 1;
    default:
        return -1;
    }
}

uint32_t function_4550e0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_455280(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_455360(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4553a0(Run &run, uint32_t receiver, const uint32_t *arguments);


ClawX87State arithmeticState() {
    ClawX87State state{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
    return state;
}

uint64_t readDoubleBits(Run &run, uint32_t address) {
    return uint64_t(run.get(address)) | (uint64_t(run.get(address + 0x4)) << 32);
}

void operand(Run &run, ClawX87State &state, uint32_t operation, uint64_t bits) {
    run.x87_step(operation, state, {uint32_t(bits), uint32_t(bits >> 32)});
}

void storeDoubleBits(Run &run, uint32_t address, uint64_t bits) {
    run.put(address, uint32_t(bits));
    run.put(address + 0x4, uint32_t(bits >> 32));
}

// Ballistic velocity calculation uses the original binary64 spills and x87 order.
void leftwardVelocity(Run &run, uint32_t receiver, uint32_t target) {
    ClawX87State state = arithmeticState();
    uint64_t local[11]{};
    operand(run, state, CLAW_X87_F64, readDoubleBits(run, receiver + 0x70));
    run.x87_step(CLAW_X87_I32, state, {target});
    operand(run, state, CLAW_X87_F64, readDoubleBits(run, receiver + 0x38));
    operand(run, state, CLAW_X87_F64, readDoubleBits(run, receiver + 0x40));
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    operand(run, state, CLAW_X87_SUB_F64, readDoubleBits(run, receiver + 0x68));
    run.x87_step(CLAW_X87_XCH_ST | 3u, state);
    operand(run, state, CLAW_X87_SUB_F64, readDoubleBits(run, receiver + 0x70));
    operand(run, state, CLAW_X87_F64, readDoubleBits(run, receiver + 0x78));
    operand(run, state, CLAW_X87_F64, readDoubleBits(run, receiver + 0x48));
    run.x87_step(CLAW_X87_XCH_ST | 5u, state);
    local[3] = run.x87_step(CLAW_X87_ST_F64, state);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    local[4] = run.x87_step(CLAW_X87_ST_F64, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    run.x87_step(CLAW_X87_CHS, state);
    local[5] = run.x87_step(CLAW_X87_ST_F64, state);
    run.x87_step(CLAW_X87_XCH_ST | 3u, state);
    local[6] = run.x87_step(CLAW_X87_ST_F64, state);
    run.x87_step(CLAW_X87_XCH_ST | 4u, state);
    local[7] = run.x87_step(CLAW_X87_ST_F64, state);
    run.x87_step(CLAW_X87_XCH_ST | 5u, state);
    local[8] = run.x87_step(CLAW_X87_ST_F64, state);
    operand(run, state, CLAW_X87_F64, local[6]);
    operand(run, state, CLAW_X87_MUL_F64, local[3]);
    run.x87_step(CLAW_X87_CHS, state);
    operand(run, state, CLAW_X87_F64, local[7]);
    operand(run, state, CLAW_X87_MUL_F64, local[4]);
    run.x87_step(CLAW_X87_SUBP | 1u, state);
    operand(run, state, CLAW_X87_F64, local[8]);
    operand(run, state, CLAW_X87_MUL_F64, local[5]);
    run.x87_step(CLAW_X87_SUBP | 1u, state);
    local[10] = run.x87_step(CLAW_X87_STP_F64, state);
    run.x87_step(CLAW_X87_XCH_ST | 4u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[6]);
    operand(run, state, CLAW_X87_F64, local[10]);
    run.x87_step(CLAW_X87_XCH_ST | 6u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[7]);
    run.x87_step(CLAW_X87_ADDP | 1u, state);
    run.x87_step(CLAW_X87_XCH_ST | 4u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[8]);
    run.x87_step(CLAW_X87_ADDP | 4u, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[3]);
    run.x87_step(CLAW_X87_XCH_ST | 3u, state);
    local[9] = run.x87_step(CLAW_X87_STP_F64, state);
    operand(run, state, CLAW_X87_MUL_F64, local[4]);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[5]);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    run.x87_step(CLAW_X87_ADDP | 2u, state);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    operand(run, state, CLAW_X87_MUL_F64, readDoubleBits(run, 0x50e278));
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    run.x87_step(CLAW_X87_ADDP | 1u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[9]);
    operand(run, state, CLAW_X87_MUL_F64, readDoubleBits(run, 0x50e270));
    run.x87_step(CLAW_X87_SQRT, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    run.x87_step(CLAW_X87_SUBP | 1u, state);
    operand(run, state, CLAW_X87_MUL_F64, readDoubleBits(run, 0x50e280));
    run.x87_step(CLAW_X87_SQRT, state);
    local[2] = run.x87_step(CLAW_X87_ST_F64, state);
    operand(run, state, CLAW_X87_COMP_F64, readDoubleBits(run, 0x513e20));
    if (state.status & 0x100) {
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x60, 0);
        run.put(receiver + 0x54, 0);
        run.put(receiver + 0x5c, 0);
        run.put(receiver + 0x64, 0);
        return;
    }
    operand(run, state, CLAW_X87_F64, local[9]);
    operand(run, state, CLAW_X87_MUL_F64, readDoubleBits(run, 0x50e288));
    operand(run, state, CLAW_X87_F64, readDoubleBits(run, 0x513e20));
    run.x87_step(CLAW_X87_CHS, state);
    run.x87_step(CLAW_X87_LD_ST | 1u, state);
    run.x87_step(CLAW_X87_COMPP, state);
    bool nonzero = (state.status & 0x100) != 0;
    if (!nonzero) {
    operand(run, state, CLAW_X87_COM_F64, readDoubleBits(run, 0x513e20));
        nonzero = (state.status & 0x4100) == 0;
    }
    if (nonzero) {
    operand(run, state, CLAW_X87_F64, local[2]);
    operand(run, state, CLAW_X87_MUL_F64, local[2]);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    run.x87_step(CLAW_X87_ADD_TO0 | 0u, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_SUB_F64, local[10]);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    run.x87_step(CLAW_X87_DIVP | 1u, state);
    run.x87_step(CLAW_X87_LD_ST | 0u, state);
    run.x87_step(CLAW_X87_SQRT, state);
    run.x87_step(CLAW_X87_LD_ST | 1u, state);
    run.x87_step(CLAW_X87_LD_ST | 2u, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[6]);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    run.x87_step(CLAW_X87_XCH_ST | 3u, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[7]);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[8]);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    operand(run, state, CLAW_X87_MUL_F64, readDoubleBits(run, 0x50e280));
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_MUL_F64, readDoubleBits(run, 0x50e280));
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_SUBR_F64, local[3]);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    operand(run, state, CLAW_X87_MUL_F64, readDoubleBits(run, 0x50e280));
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_SUBR_F64, local[4]);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_SUBR_F64, local[5]);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    run.x87_step(CLAW_X87_DIV_TO0 | 3u, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    run.x87_step(CLAW_X87_DIV_TO0 | 3u, state);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    run.x87_step(CLAW_X87_DIV_TO0 | 3u, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    storeDoubleBits(run, receiver + 0x50, run.x87_step(CLAW_X87_STP_F64, state));
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    storeDoubleBits(run, receiver + 0x58, run.x87_step(CLAW_X87_STP_F64, state));
    storeDoubleBits(run, receiver + 0x60, run.x87_step(CLAW_X87_STP_F64, state));
    } else {
    run.x87_step(CLAW_X87_STP_ST | 0u, state);
    operand(run, state, CLAW_X87_F64, local[3]);
    operand(run, state, CLAW_X87_F64, local[5]);
    operand(run, state, CLAW_X87_F64, local[4]);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    run.x87_step(CLAW_X87_ABS, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    run.x87_step(CLAW_X87_ABS, state);
    run.x87_step(CLAW_X87_ADDP | 1u, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    run.x87_step(CLAW_X87_ABS, state);
    operand(run, state, CLAW_X87_F64, local[3]);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    run.x87_step(CLAW_X87_ADDP | 2u, state);
    operand(run, state, CLAW_X87_F64, local[4]);
    operand(run, state, CLAW_X87_F64, local[5]);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    run.x87_step(CLAW_X87_DIV_TO0 | 3u, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    run.x87_step(CLAW_X87_DIV_TO0 | 3u, state);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    run.x87_step(CLAW_X87_DIV_TO0 | 3u, state);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[2]);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[2]);
    run.x87_step(CLAW_X87_XCH_ST | 1u, state);
    operand(run, state, CLAW_X87_MUL_F64, local[2]);
    run.x87_step(CLAW_X87_XCH_ST | 2u, state);
    storeDoubleBits(run, receiver + 0x50, run.x87_step(CLAW_X87_STP_F64, state));
    storeDoubleBits(run, receiver + 0x58, run.x87_step(CLAW_X87_STP_F64, state));
    storeDoubleBits(run, receiver + 0x60, run.x87_step(CLAW_X87_STP_F64, state));
    }
}

// 0x454a10. thiscall, 0 stack argument(s), returns u32.
uint32_t function_454a10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(run.get(receiver + 0x18c) == 2 ? 0x4357a0 : 0x406310, receiver + 0x128);
    int32_t state = run.gets(receiver + 0x184);
    if (state <= 0 || state > 4) {
        run.call(0x44da20, receiver);
        return 0;
    }
    if (state == 4) {
        if (s32(run.call(0x4a3050, 0)) % 100 < 50) {
            run.vcall(receiver, 0x64);
            return 0;
        }
        uint32_t key = s32(run.call(0x4a3050, 0)) % 100 < 50 ? 0x528510 : 0x528504;
        uint32_t local = run.automatic(-4);
        run.put(local, 0);
        run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28) + 0x10, {key, local});
        run.put(receiver + 0x3a0, run.get(local));
        run.vcall(receiver, 0x54, {0x5284ec, 0x5379b8});
        return 0;
    }
    int32_t distance = run.gets(receiver + 0x3c4);
    if (distance < 0 || distance >= 600)
        return 0;
    if (distance >= 400) {
        run.vcall(receiver, 0x60);
        return 0;
    }
    uint32_t key = s32(run.call(0x4a3050, 0)) % 100 < 50 ? 0x5284d0 : 0x5284b4;
    if (run.get(run.get(receiver + 0x12c) + 0x38) != 0xffffffff)
        run.call(0x48ceb0, 0, {run.get(receiver + 0xc), key, 0});
    run.vcall(receiver, 0x50, {0x528414, 0x5379a8, 0x52849c});
    return 0;
}

// 0x454b90. thiscall, 0 stack argument(s), returns u32.
uint32_t function_454b90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    if (run.get(run.get(receiver + 0x12c) + 0x38) != 0xffffffff)
        run.call(0x48ceb0, 0, {run.get(receiver + 0xc), 0x52851c, 0});
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(receiver + 0x350)});
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    return 0;
}

// 0x454c20. thiscall, 0 stack argument(s), returns u32.
uint32_t function_454c20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t state = run.get(receiver + 0x184);
    if (state <= 4)
        run.vcall(receiver, 0x44);
    else if (state <= 6 && run.get(0x541334) == 0 && s32(run.call(0x4a3050, 0)) % 100 < 5)
        run.call(0x44edd0, receiver);
    return 0;
}

// 0x454cb0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_454cb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t distance = uint32_t(s32(run.call(0x4a3050, 0)) % 201) + 200;
    bool left = run.get(receiver + 0x18c) == 3;
    uint32_t target = left ? run.get(run.get(0x537e88) + 0x4c) - distance : run.get(run.get(0x537e88) + 0x4c) + distance;
    ClawX87State conversion = arithmeticState();
    operand(run, conversion, CLAW_X87_F64, readDoubleBits(run, receiver + 0x70));
    conversion.returned = 0;
    conversion.eax = 0;
    conversion.edx = 0;
    conversion.popCount = 1;
    conversion.pushCount = 0;
    uint32_t y = run.call_x87_exact(0x4a30e0, 0, conversion);
    operand(run, conversion, CLAW_X87_F64, readDoubleBits(run, receiver + 0x68));
    conversion.returned = 0;
    conversion.eax = 0;
    conversion.edx = 0;
    conversion.popCount = 1;
    conversion.pushCount = 0;
    uint32_t x = run.call_x87_exact(0x4a30e0, 0, conversion);
    uint32_t object = run.get(receiver + 0x128);
    uint32_t world = run.get(run.get(object + 0xc) + 0x24);
    if (run.call(0x4cda10, world, {x, y, target, 0x20}) == 0)
        return 0;
    target = left ? run.get(run.get(0x537e88) + 0x4c) - distance : run.get(run.get(0x537e88) + 0x4c) + distance;
    object = run.get(receiver + 0x128);
    y = run.get(object + 0x50) + run.get(object + 0x124) + 1;
    auto tile = [&](uint32_t row) {
        uint32_t current = run.get(receiver + 0x128);
        return run.call(0x4207f0, run.get(run.get(current + 0xc) + 0x24), {target, row});
    };
    if (tile(y) != 1 && tile(y) != 2 && tile(y) != 3)
        return 0;
    if (tile(y - 1) != 0)
        return 0;
    target = left ? run.get(run.get(0x537e88) + 0x4c) - distance : run.get(run.get(0x537e88) + 0x4c) + distance;
    if (left) {
        leftwardVelocity(run, receiver, target);
    } else {
        ClawX87State result = conversion;
        operand(run, result, CLAW_X87_F64, readDoubleBits(run, receiver + 0x70));
        uint64_t yBits = run.x87_step(CLAW_X87_STP_F64, result);
        run.x87_step(CLAW_X87_I32, result, {target});
        uint64_t targetBits = run.x87_step(CLAW_X87_STP_F64, result);
        result.returned = 0;
        result.eax = 0;
        result.edx = 0;
        result.popCount = 0;
        result.pushCount = 1;
        run.call_x87_exact(0x420dd0, receiver + 0x28, result, {uint32_t(targetBits), uint32_t(targetBits >> 32), uint32_t(yBits), uint32_t(yBits >> 32), 0, 0});
        run.x87_step(CLAW_X87_POP, result);
    }
    run.put(receiver + 0x20, 1);
    function_4550e0(run, receiver, nullptr);
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 4);
    uint32_t stateArgument[] = {0x527204};
    function_4553a0(run, receiver, stateArgument);
    run.put(run.get(receiver + 0xc) + 0xcc, 8);
    uint32_t animationArguments[] = {run.get(receiver + 0x464), 0};
    function_455360(run, receiver + 0x128, animationArguments);
    uint32_t animation = run.call(0x40f780, receiver + 0x128, {0x528354});
    if (animation != 0) {
        // Entry minus 0x48 locals, four saved registers, four arguments,
        // and the return word gives the original sound callee's frame.
        uint32_t previousStack = run.stackPointer;
        run.stackPointer = run.automatic(-0x6c);
        run.call(0x4208e0, animation, {run.get(0x532c10), 0, 0, 0});
        run.stackPointer = previousStack;
    }
    return 0;
}

// 0x4550e0. thiscall, 0 stack argument(s), returns void.
uint32_t function_4550e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t sprite = run.get(receiver + 0x12c);
    bool flip = run.get(receiver + 0x18c) == 2;
    if (((run.get8(sprite + 0x40) & 2) != 0) == flip)
        return 0;
    uint32_t first = run.get(receiver + 0x138);
    uint32_t second = run.get(receiver + 0x140);
    run.put(receiver + 0x138, 0u - second);
    run.put(receiver + 0x140, 0u - first);
    run.put(sprite + 0x40, flip ? run.get(sprite + 0x40) | 2 : run.get(sprite + 0x40) & 0xfffffffd);
    sprite = run.get(receiver + 0x12c);
    for (uint32_t offset : {0x118u, 0x128u, 0x138u}) {
        first = run.get(sprite + offset);
        if (first != 0x80000000) {
            second = run.get(sprite + offset + 0x8);
            run.put(sprite + offset, 0u - second);
            run.put(sprite + offset + 0x8, 0u - first);
        }
    }
    return 0;
}

// 0x455230. thiscall, 0 stack argument(s), returns u32.
uint32_t function_455230(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (run.get(run.get(receiver + 0xc) + 0xcc) == 1) {
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x60, 0);
        run.put(receiver + 0x54, 0);
        run.put(receiver + 0x5c, 0);
        run.put(receiver + 0x64, 0);
        function_455280(run, receiver, nullptr);
    }
    return 0;
}

// 0x455280. thiscall, 0 stack argument(s), returns u32.
uint32_t function_455280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x528454});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(receiver + 0x468)});
    return 0;
}

// 0x4552d0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4552d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t sprite = run.get(receiver + 0x12c);
    if (run.get(sprite + 0x1a4) != 0 && run.get(sprite + 0x19c) == 0) {
        run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xfffffffb);
        if (s32(run.call(0x4a3050, 0)) % 100 < 10 && run.get(run.get(receiver + 0x12c) + 0x38) != 0xffffffff)
            run.call(0x48ceb0, 0, {run.get(receiver + 0xc), 0x528538, 0});
        run.put(receiver + 0x20, 2);
        run.vcall(receiver, 0x44);
    }
    return 0;
}

// 0x455360. thiscall, 2 stack argument(s), returns void.
uint32_t function_455360(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t sprite = run.get(receiver + 0x4);
    uint32_t timer = sprite + 0x188;
    run.put(receiver + 0xc, run.get(sprite + 0x190));
    run.call(0x4c8220, timer, {arguments[0]});
    if (arguments[1] != 0)
        run.call(0x4c82a0, timer, {run.get(0x5430c4)});
    return 0;
}

// 0x4553a0. thiscall, 1 stack argument(s), returns void.
uint32_t function_4553a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {arguments[0]});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x454a10:
        return function_454a10(run, receiver, arguments);
    case 0x454b90:
        return function_454b90(run, receiver, arguments);
    case 0x454c20:
        return function_454c20(run, receiver, arguments);
    case 0x454cb0:
        return function_454cb0(run, receiver, arguments);
    case 0x4550e0:
        return function_4550e0(run, receiver, arguments);
    case 0x455230:
        return function_455230(run, receiver, arguments);
    case 0x455280:
        return function_455280(run, receiver, arguments);
    case 0x4552d0:
        return function_4552d0(run, receiver, arguments);
    case 0x455360:
        return function_455360(run, receiver, arguments);
    case 0x4553a0:
        return function_4553a0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_four_katherine_states_01_entry, owned, body)
