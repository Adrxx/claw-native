// Lava hand projectile, recovered from the original v1.0 instructions.
#include "ClawRuntime.hpp"
namespace {
using claw::Run;
using claw::s32;
int owned(uint32_t function) {
    switch (function) {
    case 0x456b00:
    case 0x456c20:
    case 0x457020:
    case 0x4571a0:
        return 1;
    case 0x4573b0:
    case 0x457460:
    case 0x4574e0:
        return 0;
    default:
        return -1;
    }
}
ClawX87State floatingState() {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    return fp;
}
void fpMemory(Run &run, ClawX87State &fp, uint32_t op, uint32_t address) {
    run.x87_step(op, fp, {run.get(address), run.get(address + 0x4)});
}
void fpBits(Run &run, ClawX87State &fp, uint32_t op, uint64_t bits) {
    run.x87_step(op, fp, {uint32_t(bits), uint32_t(bits >> 32)});
}
void fpStore(Run &run, ClawX87State &fp, uint32_t address) {
    uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(address, uint32_t(bits));
    run.put(address + 0x4, uint32_t(bits >> 32));
}
// 0x457020. +0x12c entity, +0x148/+0x150 images, +0x170 explosion image,
// +0x174 sound, +0x178 one-shot flag. Output is the incoming entity argument slot.
uint32_t construct(Run &run, uint32_t receiver, uint32_t entity, uint32_t output) {
    run.call(0x4084b0, receiver, {entity});
    run.put(receiver + 0x0, 0x50e504);
    if (!run.get(run.get(receiver + 0x12c) + 0x170))
        run.call(0x4c7970, run.get(receiver + 0x12c), {0x528644});
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x2c) + 0x10, {0x528644, output});
    run.put(receiver + 0x150, run.get(output));
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x2c) + 0x10, {0x528644, output});
    run.put(receiver + 0x148, run.get(output));
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x2c) + 0x10, {0x526f50, output});
    run.put(receiver + 0x170, run.get(output));
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28) + 0x10, {0x526f40, output});
    uint32_t sound = run.get(output);
    run.put(receiver + 0x178, 0);
    run.put(receiver + 0x174, sound);
    run.call(0x408050, run.get(receiver + 0x12c));
    run.put(run.get(receiver + 0x12c) + 0xd0, 0x40);
    run.call(0x406290, run.get(receiver + 0x12c));
    entity = run.get(receiver + 0xc);
    if (!run.get(entity + 0x104))
        run.put(entity + 0x104, 0xa);
    entity = run.get(receiver + 0x12c);
    run.put(entity + 0x164, run.get(entity + 0x164) | 0x2020);
    run.put(receiver + 0x15c, 0);
    run.put(receiver + 0x168, 0x3e8);
    return receiver;
}
// 0x456b00. Entity +0x6c descriptor; descriptor +0x1c state, +0x18 controller.
uint32_t logic(Run &run, uint32_t entity) {
    uint32_t descriptor = run.get(entity + 0x6c);
    uint32_t state = run.get(descriptor + 0x1c);
    if (!state) {
        run.put(descriptor + 0x1c, 0x3e8);
        uint32_t controller = run.call(0x4f63ec, 0, {0x180});
        if (controller)
            controller = construct(run, controller, entity, run.automatic(-24));
        run.vcall(controller, 0x10);
        run.put(descriptor + 0x18, controller);
    } else if (state == 0x1d) {
        run.vcall(run.get(descriptor + 0x18), 0x20);
    } else if (state == 0x1e) {
        run.vcall(run.get(descriptor + 0x18), 0x1c);
    } else if (state != 0x3e8) {
        run.call(0x4dc870, 0, {run.get(descriptor + 0x18)});
    }
    return 1;
}
uint32_t stateCell(Run &run, uint32_t state) {
    if (s32(state) < s32(run.get(0x537a68)) || s32(state) > s32(run.get(0x537a6c))) {
        if (!run.call(0x4db6e0, 0x537a60, {state, 0})) {
            uint32_t error = run.get(0x544b4c);
            uint32_t pc = run.call(0x4db5f0, 0);
            run.put(0x544b14, pc);
            run.call(0x4db4d0, run.get(0x537a64), {0x537a60, error, 0xc});
            return run.get(0x537a74);
        }
    }
    return (state - run.get(0x537a68)) * run.get(0x537a78) + run.get(0x537a70);
}
// 0x456c20. Registry +0x20 is per-lookup scratch.
uint32_t dispatchState(Run &run, uint32_t receiver, uint32_t state) {
    run.put(0x537a80, 0);
    uint32_t cell = stateCell(run, state);
    if (!run.get(cell)) {
        run.call(0x408580, receiver, {state});
    } else {
        run.put(0x537a80, 0);
        cell = stateCell(run, state);
        run.call(run.get(cell), receiver);
    }
    return 0;
}
// 0x4571a0. Exact x87 instruction sequence, including binary64 store points.
uint32_t aim(Run &run, uint32_t receiver, uint32_t displacement) {
    auto fp = floatingState();
    uint64_t local[9]{};
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0x409f4000);
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x68);
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x70);
    run.x87_step(CLAW_X87_I32, fp, {displacement});
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), fp);
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x38);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    fpMemory(run, fp, CLAW_X87_SUB_F64, receiver + 0x68);
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x40);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    fpMemory(run, fp, CLAW_X87_SUB_F64, receiver + 0x70);
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x78);
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x48);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    local[1] = run.x87_step(CLAW_X87_ST_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    local[2] = run.x87_step(CLAW_X87_ST_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_CHS, fp);
    local[3] = run.x87_step(CLAW_X87_ST_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5), fp);
    local[4] = run.x87_step(CLAW_X87_ST_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
    local[5] = run.x87_step(CLAW_X87_ST_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    local[6] = run.x87_step(CLAW_X87_ST_F64, fp);
    fpBits(run, fp, CLAW_X87_F64, local[4]);
    fpBits(run, fp, CLAW_X87_MUL_F64, local[1]);
    run.x87_step(CLAW_X87_CHS, fp);
    fpBits(run, fp, CLAW_X87_F64, local[5]);
    fpBits(run, fp, CLAW_X87_MUL_F64, local[2]);
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
    fpBits(run, fp, CLAW_X87_F64, local[6]);
    fpBits(run, fp, CLAW_X87_MUL_F64, local[3]);
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
    local[8] = run.x87_step(CLAW_X87_STP_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, local[4]);
    fpBits(run, fp, CLAW_X87_F64, local[8]);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, local[5]);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, local[6]);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 4), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, local[1]);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    local[7] = run.x87_step(CLAW_X87_STP_F64, fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, local[2]);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, local[3]);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), fp);
    fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50e550);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, local[7]);
    fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50e548);
    run.x87_step(CLAW_X87_SQRT, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
    fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50e558);
    run.x87_step(CLAW_X87_SQRT, fp);
    local[0] = run.x87_step(CLAW_X87_ST_F64, fp);
    fpMemory(run, fp, CLAW_X87_COMP_F64, 0x513e20);
    if (fp.status & 0x100) {
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x60, 0);
        run.put(receiver + 0x54, 0);
        run.put(receiver + 0x5c, 0);
        run.put(receiver + 0x64, 0);
    } else {
        fpBits(run, fp, CLAW_X87_F64, local[7]);
        fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50e560);
        fpMemory(run, fp, CLAW_X87_F64, 0x513e20);
        run.x87_step(CLAW_X87_CHS, fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), fp);
        run.x87_step(CLAW_X87_COMPP, fp);
        bool quadratic = (fp.status & 0x100) != 0;
        if (!quadratic) {
            fpMemory(run, fp, CLAW_X87_COM_F64, 0x513e20);
            quadratic = (fp.status & 0x4100) == 0;
        }
        if (!quadratic) {
            run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), fp);
            fpBits(run, fp, CLAW_X87_F64, local[2]);
            fpBits(run, fp, CLAW_X87_F64, local[1]);
            fpBits(run, fp, CLAW_X87_F64, local[3]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
            run.x87_step(CLAW_X87_ABS, fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            run.x87_step(CLAW_X87_ABS, fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            run.x87_step(CLAW_X87_ABS, fp);
            fpBits(run, fp, CLAW_X87_F64, local[1]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), fp);
            fpBits(run, fp, CLAW_X87_F64, local[2]);
            fpBits(run, fp, CLAW_X87_F64, local[3]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            fpBits(run, fp, CLAW_X87_MUL_F64, local[0]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
            fpBits(run, fp, CLAW_X87_MUL_F64, local[0]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            fpBits(run, fp, CLAW_X87_MUL_F64, local[0]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
            fpStore(run, fp, receiver + 0x50);
        } else {
            fpBits(run, fp, CLAW_X87_F64, local[0]);
            fpBits(run, fp, CLAW_X87_MUL_F64, local[0]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_ADD_TOI, 0), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            fpBits(run, fp, CLAW_X87_SUB_F64, local[8]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_DIVP, 1), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), fp);
            run.x87_step(CLAW_X87_SQRT, fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 2), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            fpBits(run, fp, CLAW_X87_MUL_F64, local[4]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            fpBits(run, fp, CLAW_X87_MUL_F64, local[5]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            fpBits(run, fp, CLAW_X87_MUL_F64, local[6]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
            fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50e558);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50e558);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            fpBits(run, fp, CLAW_X87_SUBR_F64, local[1]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
            fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50e558);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            fpBits(run, fp, CLAW_X87_SUBR_F64, local[2]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            fpBits(run, fp, CLAW_X87_SUBR_F64, local[3]);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
            fpStore(run, fp, receiver + 0x50);
            run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        }
        fpStore(run, fp, receiver + 0x58);
        fpStore(run, fp, receiver + 0x60);
        run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), fp);
    }
    uint32_t doubled = displacement + displacement;
    uint32_t sign = s32(doubled) < 0 ? 0xffffffff : 0;
    uint32_t magnitude = (doubled ^ sign) - sign;
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x58);
    run.x87_step(CLAW_X87_I32, fp, {magnitude});
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
    fpStore(run, fp, receiver + 0x58);
    return 0;
}
// 0x4573b0. +0x24 saved state, +0x134 saved animation, +0xc8 active flag.
uint32_t beginExplosion(Run &run, uint32_t receiver) {
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x526f50});
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x524418});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t entity = run.get(receiver + 0x12c);
    run.put(entity + 0x8, run.get(entity + 0x8) | 0x4);
    run.put(run.get(receiver + 0x12c) + 0xd0, 0x1000000);
    entity = run.get(receiver + 0x12c);
    uint32_t image = run.get(receiver + 0x170);
    run.put(receiver + 0x134, run.get(entity + 0x190));
    run.call(0x4c8220, entity + 0x188, {image});
    run.put(receiver + 0xc8, 1);
    uint32_t sound = run.get(receiver + 0x174);
    if (sound) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t volume = run.get(0x532c10);
        if (enabled)
            run.call(0x4b45f0, run.get(sound + 0x10), {volume, 0, 0, 0});
    }
    return 0;
}
// 0x457460. Entity +0x8 flags, +0x1a4 completion, +0x19c current frame.
uint32_t advanceExplosion(Run &run, uint32_t receiver) {
    uint32_t entity = run.get(receiver + 0x12c);
    run.put(entity + 0x8, run.get(entity + 0x8) | 0x80);
    uint32_t tick = run.get(0x5430c4);
    uint32_t result = run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {tick});
    if (result == 1 && !run.get(receiver + 0x178)) {
        run.put(receiver + 0x178, 1);
        entity = run.get(receiver + 0x12c);
        run.put(entity + 0x8, run.get(entity + 0x8) & 0xffffff7f);
    }
    entity = run.get(receiver + 0x12c);
    if (run.get(entity + 0x1a4) && !run.get(entity + 0x19c))
        run.put(entity + 0x8, run.get(entity + 0x8) | 0x10000);
    return 0;
}
uint32_t randomCoordinate(Run &run, uint32_t lower, uint32_t upper) {
    uint32_t width = upper - lower + 1;
    uint32_t random = run.call(0x4a3050, 0);
    if (!width)
        return random & 1 ? lower : upper;
    int64_t remainder = int64_t(s32(random)) % int64_t(s32(width));
    return uint32_t(remainder) + lower;
}
uint32_t convertPosition(Run &run, ClawX87State &fp, uint32_t coordinate, uint32_t low, uint32_t high) {
    run.x87_step(CLAW_X87_I32, fp, {coordinate});
    run.x87_step(CLAW_X87_ADD_F64, fp, {low, high});
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}
// 0x4574e0. Entity +0x118/+0x120 X bounds, +0x11c/+0x124 Y bounds.
uint32_t updateTrail(Run &run, uint32_t receiver) {
    run.call(0x4089d0, receiver);
    uint32_t count = run.get(run.get(0x5371fc) + 0x124) ? 2 : 1;
    auto fp = floatingState();
    do {
        uint32_t xHigh = run.get(receiver + 0x6c);
        uint32_t xLow = run.get(receiver + 0x68);
        uint32_t entity = run.get(receiver + 0xc);
        uint32_t upper = run.get(entity + 0x120);
        uint32_t lower = run.get(entity + 0x118);
        uint32_t selected = randomCoordinate(run, lower, upper);
        uint32_t x = convertPosition(run, fp, selected, xLow, xHigh);
        uint32_t yHigh = run.get(receiver + 0x74);
        entity = run.get(receiver + 0xc);
        uint32_t yLow = run.get(receiver + 0x70);
        upper = run.get(entity + 0x124);
        lower = run.get(entity + 0x11c);
        selected = randomCoordinate(run, lower, upper);
        entity = run.get(receiver + 0xc);
        uint32_t z = run.get(entity + 0x64) - 1;
        uint32_t y = convertPosition(run, fp, selected, yLow, yHigh);
        uint32_t descriptor = run.get(receiver + 0x130);
        uint32_t factory = run.get(run.get(descriptor + 0xc) + 0x8);
        uint32_t created = run.call(0x4c8da0, factory, {0, x, y, z, 0x522594, 0x40000});
        run.call(run.get(run.get(created + 0x6c) + 0x10), 0, {created});
        --count;
    } while (count);
    return 0;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x456b00:
        return logic(run, arguments[0]);
    case 0x456c20:
        return dispatchState(run, receiver, arguments[0]);
    case 0x457020:
        return construct(run, receiver, arguments[0], run.automatic(4));
    case 0x4571a0:
        return aim(run, receiver, arguments[0]);
    case 0x4573b0:
        return beginExplosion(run, receiver);
    case 0x457460:
        return advanceExplosion(run, receiver);
    case 0x4574e0:
        return updateTrail(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace
CLAW_MODULE_ENTRY(claw_lava_hand_projectile_entry, owned, body)
