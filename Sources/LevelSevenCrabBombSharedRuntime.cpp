// Original Level 7 crab bomb and shared player-state behavior.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t f) {
    switch (f) {
    case 0x431cd0:
    case 0x431df0:
    case 0x4320d0:
    case 0x432250:
        return 1;
    case 0x41fce0:
    case 0x41fe80:
    case 0x432460:
    case 0x4324e0:
    case 0x432550:
    case 0x432560:
        return 0;
    default:
        return -1;
    }
}

void clearGlobals(Run &run) {
    run.put(0x534e60, 0);
    run.put(0x534e64, 0);
    run.put(0x534e68, 0);
    run.put(0x534e6c, 0);
    run.put(0x534e70, 0);
    run.put(0x534e74, 0);
}

void geometry(Run &run, uint32_t player, uint32_t detail) {
    if (run.get(detail) != 0) {
        run.put(player + 0x128, 0xffffffea);
        run.put(player + 0x12c, 0xffffffd3);
        run.put(player + 0x130, 0xf);
    } else {
        run.put(player + 0x128, 0xfffffff1);
        run.put(player + 0x12c, 0xffffffd3);
        run.put(player + 0x130, 0x16);
    }
    run.put(player + 0x134, 0x34);
}

void bounds(Run &run, uint32_t player) {
    run.put(player + 0x118, 0xfffffff0);
    run.put(player + 0x11c, 0xffffffcc);
    run.put(player + 0x120, 0x10);
    run.put(player + 0x124, 0x3c);
}

// 0x41fce0 and 0x41fe80: enter/leave the shared player state.
uint32_t playerState(Run &run, bool leaving) {
    uint32_t p = run.get(0x537e88);
    if (!p)
        return 0;
    uint32_t state = run.get(p + 0x6c);
    if (leaving && (!state || run.get(state + 0x1c) != 0x1390))
        return 0;
    uint32_t d = run.get(state + 0x14);
    uint32_t flags = run.get(0x537204);
    run.put(flags + 0xc, run.get(flags + 0xc) & 0xfdffffff);
    flags = run.get(0x537204);
    run.put(flags + 0xc, run.get(flags + 0xc) & 0xfeffffff);
    uint32_t other = run.get(d + 0x12c);
    if (other) {
        uint32_t controller = run.get(run.get(other + 0x6c) + 0x18);
        if (leaving) {
            run.call(0x421010, controller, {0x4207a0, 1});
        } else if (run.gets(controller + 0x20) >= 1) {
            run.put(controller + 0x14, 0x4207a0);
        }
        run.call(0x420fc0, controller + 0x2f4, {0});
        run.put(d + 0x12c, 0);
    }
    uint32_t active = run.get(d + 0x4);
    run.put(d + 0x3c, 0);
    run.put(d + 0x20, 1);
    if (active) {
        uint32_t value = run.get(d + 0x124);
        run.put(d + 0x4, 0);
        if (leaving)
            run.call(0x4c8220, p + 0x188, {value});
        else
            run.call(0x420a10, p, {value, 0});
        run.put(p + 0x8, run.get(p + 0x8) | 0x80);
    }
    run.put(state + 0x1c, leaving ? 0x18 : 0x1390);
    if (leaving)
        run.call(0x4c79e0, p, {0x5246d0, 1});
    uint32_t bits = run.get(p + 0x8) | 0x80;
    run.put(p + 0xcc, leaving ? 1 : 7);
    run.put(p + 0x148, 0);
    run.put(p + 0x14c, 0);
    run.put(p + 0x104, 0);
    run.put(p + 0x8, bits);
    geometry(run, p, d);
    if (leaving && !run.get(d))
        run.call(0x40f6c0, p, {0xfffffff0, 0xffffffcc, 0x10, 0x3c});
    else
        bounds(run, p);
    run.put(d + 0xfc, 0x28a);
    run.put(d + 0x114, 0x5dc);
    if (leaving) {
        run.put(d + 0x120, 15000);
    }
    run.put(d + 0x118, 0);
    clearGlobals(run);
    if (leaving) {
        run.put(p + 0x1b0, 0x3f800000);
    }
    return 0;
}

// 0x4320d0: construct the bomb controller from the world object.
uint32_t construct(Run &run, uint32_t r, uint32_t world) {
    run.call(0x4084b0, r, {world});
    run.put(r, 0x50c6e4);
    uint32_t w = run.get(r + 0x12c);
    if (!run.get(w + 0x170))
        run.call(0x4c7970, w, {0x52664c});
    uint32_t scratch = run.automatic(0x4);
    run.put(scratch, 0);
    uint32_t map = run.get(run.get(run.get(r + 0x12c) + 0xc) + 0x2c) + 0x10;
    run.call(0x4f6286, map, {0x526638, scratch});
    run.put(r + 0x150, run.get(scratch));
    run.put(scratch, 0);
    map = run.get(run.get(run.get(r + 0x12c) + 0xc) + 0x2c) + 0x10;
    run.call(0x4f6286, map, {0x526638, scratch});
    run.put(r + 0x148, run.get(scratch));
    run.put(scratch, 0);
    map = run.get(run.get(run.get(r + 0x12c) + 0xc) + 0x2c) + 0x10;
    run.call(0x4f6286, map, {0x526620, scratch});
    uint32_t value = run.get(scratch);
    run.put(r + 0x174, 0);
    run.put(r + 0x170, value);
    w = run.get(r + 0x12c);
    run.put(w + 0x138, 0xffffffce);
    run.put(w + 0x13c, 0xffffffce);
    run.put(w + 0x140, 0x32);
    run.put(w + 0x144, 0x32);
    run.put(run.get(r + 0x12c) + 0xd0, 0x40);
    run.call(0x406290, run.get(r + 0x12c));
    uint32_t owner = run.get(r + 0xc);
    if (!run.get(owner + 0x104)) {
        run.put(owner + 0x104, 5);
    }
    w = run.get(r + 0x12c);
    run.put(w + 0x164, run.get(w + 0x164) | 0x2020);
    run.put(r + 0x15c, 2);
    run.put(r + 0x168, 1000);
    return r;
}

// 0x431cd0: dispatch the bomb's current state.
uint32_t dispatch(Run &run, uint32_t object) {
    uint32_t state = run.get(object + 0x6c);
    uint32_t value = run.get(state + 0x1c);
    if (value == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t r = run.call(0x4f63ec, 0, {0x178});
        if (r) {
            uint32_t oldFrame = run.frame;
            run.frame -= 0x1c;
            r = construct(run, r, object);
            run.frame = oldFrame;
        }
        run.vcall(r, 0x10);
        run.put(state + 0x18, r);
    } else if (value == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (value == 0x1e) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (value != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}

uint32_t tableSlot(Run &run, uint32_t input) {
    uint32_t lower = run.get(0x5372b0);
    if (s32(input) < s32(lower) || s32(input) > run.gets(0x5372b4)) {
        uint32_t result = run.call(0x4db6e0, 0x5372a8, {input, 0});
        if (!result) {
            uint32_t message = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            uint32_t handler = run.get(0x5372ac);
            run.put(0x544b14, error);
            run.call(0x4db4d0, handler, {0x5372a8, message, 0xc});
            return run.get(0x5372bc);
        }
        lower = run.get(0x5372b0);
    }
    return (input - lower) * run.get(0x5372c0) + run.get(0x5372b8);
}

// 0x431df0: two-stage state callback table lookup.
uint32_t stateCallback(Run &run, uint32_t r, uint32_t input) {
    run.put(0x5372c8, 0);
    uint32_t slot = tableSlot(run, input);
    if (run.get(slot)) {
        run.put(0x5372c8, 0);
        slot = tableSlot(run, input);
        run.call(run.get(slot), r);
    } else {
        run.call(0x408580, r, {input});
    }
    return 0;
}

// 0x432460: begin explosion and select the explosion animation.
uint32_t explode(Run &run, uint32_t r) {
    run.put(r + 0x24, run.get(run.get(r + 0x10) + 0x1c));
    uint32_t animation = run.call(0x4dba00, 0x537668, {0x524418});
    run.put(run.get(r + 0x10) + 0x1c, animation);
    uint32_t w = run.get(r + 0x12c);
    run.put(w + 0x8, run.get(w + 0x8) | 4);
    run.put(run.get(r + 0x12c) + 0xd0, 0x1000000);
    w = run.get(r + 0x12c);
    uint32_t selected = run.get(r + 0x170);
    run.put(r + 0x134, run.get(w + 0x190));
    run.call(0x4c8220, w + 0x188, {selected});
    run.put(r + 0xc8, 1);
    return 0;
}

// 0x4324e0: advance the explosion and collision flags.
uint32_t exploding(Run &run, uint32_t r) {
    uint32_t result = run.call(0x4c82a0, run.get(r + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (result == 1 && !run.get(r + 0x174)) {
        run.put(r + 0x174, 1);
        uint32_t w = run.get(r + 0x12c);
        run.put(w + 0x8, run.get(w + 0x8) & 0xffffff7f);
    }
    uint32_t w = run.get(r + 0x12c);
    if (run.get(w + 0x1a4) && !run.get(w + 0x19c)) {
        run.put(w + 0x8, run.get(w + 0x8) | 0x10000);
    }
    return 0;
}

// 0x432250: ballistic calculation, preserving the original x87 operation order.
uint32_t ballistic(Run &run, uint32_t r, uint32_t argument) {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    uint32_t local = run.automatic(-0x48);
    run.put(r + 0x40, 0);
    run.put(r + 0x44, 0x409f4000);
    run.put(local + 0x4c, argument);
    run.x87_step(CLAW_X87_F64, fp, {run.get(r + 0x68), run.get(r + 0x6c)});
    run.x87_step(CLAW_X87_F64, fp, {run.get(r + 0x70), run.get(r + 0x74)});
    run.x87_step(CLAW_X87_I32, fp, {run.get(local + 0x4c)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), fp);
    run.x87_step(CLAW_X87_F64, fp, {run.get(r + 0x38), run.get(r + 0x3c)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(r + 0x68), run.get(r + 0x6c)});
    run.x87_step(CLAW_X87_F64, fp, {run.get(r + 0x40), run.get(r + 0x44)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(r + 0x70), run.get(r + 0x74)});
    run.x87_step(CLAW_X87_F64, fp, {run.get(r + 0x78), run.get(r + 0x7c)});
    run.x87_step(CLAW_X87_F64, fp, {run.get(r + 0x48), run.get(r + 0x4c)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_ST_F64, fp);
        run.put(local + 0x8, uint32_t(bits));
        run.put(local + 0xc, uint32_t(bits >> 32));
    }
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_ST_F64, fp);
        run.put(local + 0x10, uint32_t(bits));
        run.put(local + 0x14, uint32_t(bits >> 32));
    }
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_CHS, fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_ST_F64, fp);
        run.put(local + 0x18, uint32_t(bits));
        run.put(local + 0x1c, uint32_t(bits >> 32));
    }
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5), fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_ST_F64, fp);
        run.put(local + 0x20, uint32_t(bits));
        run.put(local + 0x24, uint32_t(bits >> 32));
    }
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_ST_F64, fp);
        run.put(local + 0x28, uint32_t(bits));
        run.put(local + 0x2c, uint32_t(bits >> 32));
    }
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_ST_F64, fp);
        run.put(local + 0x30, uint32_t(bits));
        run.put(local + 0x34, uint32_t(bits >> 32));
    }
    run.x87_step(CLAW_X87_F64, fp, {run.get(local + 0x20), run.get(local + 0x24)});
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x8), run.get(local + 0xc)});
    run.x87_step(CLAW_X87_CHS, fp);
    run.x87_step(CLAW_X87_F64, fp, {run.get(local + 0x28), run.get(local + 0x2c)});
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x10), run.get(local + 0x14)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
    run.x87_step(CLAW_X87_F64, fp, {run.get(local + 0x30), run.get(local + 0x34)});
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x18), run.get(local + 0x1c)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
        run.put(local + 0x40, uint32_t(bits));
        run.put(local + 0x44, uint32_t(bits >> 32));
    }
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x20), run.get(local + 0x24)});
    run.x87_step(CLAW_X87_F64, fp, {run.get(local + 0x40), run.get(local + 0x44)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x28), run.get(local + 0x2c)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x30), run.get(local + 0x34)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 4), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x8), run.get(local + 0xc)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
        run.put(local + 0x38, uint32_t(bits));
        run.put(local + 0x3c, uint32_t(bits >> 32));
    }
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x10), run.get(local + 0x14)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x18), run.get(local + 0x1c)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50c730), run.get(0x50c730 + 0x4)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x38), run.get(local + 0x3c)});
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50c728), run.get(0x50c728 + 0x4)});
    run.x87_step(CLAW_X87_SQRT, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50c738), run.get(0x50c738 + 0x4)});
    run.x87_step(CLAW_X87_SQRT, fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_ST_F64, fp);
        run.put(local, uint32_t(bits));
        run.put(local + 0x4, uint32_t(bits >> 32));
    }
    run.x87_step(CLAW_X87_COMP_F64, fp, {run.get(0x513e20), run.get(0x513e20 + 0x4)});
    if (!(fp.status & 0x100)) goto math_00432347;
    run.put(r + 0x50, 0);
    run.put(r + 0x58, 0);
    run.put(r + 0x60, 0);
    run.put(r + 0x54, 0);
    run.put(r + 0x5c, 0);
    run.put(r + 0x64, 0);
    goto math_0043243b;
math_00432347:
    run.x87_step(CLAW_X87_F64, fp, {run.get(local + 0x38), run.get(local + 0x3c)});
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50c740), run.get(0x50c740 + 0x4)});
    run.x87_step(CLAW_X87_F64, fp, {run.get(0x513e20), run.get(0x513e20 + 0x4)});
    run.x87_step(CLAW_X87_CHS, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), fp);
    run.x87_step(CLAW_X87_COMPP, fp);
    if (fp.status & 0x100) goto math_004323c2;
    run.x87_step(CLAW_X87_COM_F64, fp, {run.get(0x513e20), run.get(0x513e20 + 0x4)});
    if (!(fp.status & 0x4100)) goto math_004323c2;
    run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), fp);
    run.x87_step(CLAW_X87_F64, fp, {run.get(local + 0x8), run.get(local + 0xc)});
    run.x87_step(CLAW_X87_F64, fp, {run.get(local + 0x10), run.get(local + 0x14)});
    run.x87_step(CLAW_X87_F64, fp, {run.get(local + 0x18), run.get(local + 0x1c)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ABS, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ABS, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ABS, fp);
    run.x87_step(CLAW_X87_F64, fp, {run.get(local + 0x8), run.get(local + 0xc)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), fp);
    run.x87_step(CLAW_X87_F64, fp, {run.get(local + 0x10), run.get(local + 0x14)});
    run.x87_step(CLAW_X87_F64, fp, {run.get(local + 0x18), run.get(local + 0x1c)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local), run.get(local + 0x4)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local), run.get(local + 0x4)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local), run.get(local + 0x4)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
        run.put(r + 0x50, uint32_t(bits));
        run.put(r + 0x54, uint32_t(bits >> 32));
    }
    goto math_00432433;
math_004323c2:
    run.x87_step(CLAW_X87_F64, fp, {run.get(local), run.get(local + 0x4)});
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local), run.get(local + 0x4)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADD_TO0, 0), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(local + 0x40), run.get(local + 0x44)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIVP, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), fp);
    run.x87_step(CLAW_X87_SQRT, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x20), run.get(local + 0x24)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x28), run.get(local + 0x2c)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(local + 0x30), run.get(local + 0x34)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50c738), run.get(0x50c738 + 0x4)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50c738), run.get(0x50c738 + 0x4)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_SUBR_F64, fp, {run.get(local + 0x8), run.get(local + 0xc)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50c738), run.get(0x50c738 + 0x4)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_SUBR_F64, fp, {run.get(local + 0x10), run.get(local + 0x14)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_SUBR_F64, fp, {run.get(local + 0x18), run.get(local + 0x1c)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
        run.put(r + 0x50, uint32_t(bits));
        run.put(r + 0x54, uint32_t(bits >> 32));
    }
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
math_00432433:
    {
        uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
        run.put(r + 0x58, uint32_t(bits));
        run.put(r + 0x5c, uint32_t(bits >> 32));
    }
    {
        uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
        run.put(r + 0x60, uint32_t(bits));
        run.put(r + 0x64, uint32_t(bits >> 32));
    }
    run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), fp);
math_0043243b:
    {
        uint32_t doubled = argument + argument;
        uint32_t sign = s32(doubled) < 0 ? 0xffffffff : 0;
        run.put(local + 0x4c, (doubled ^ sign) - sign);
    }
    run.x87_step(CLAW_X87_F64, fp, {run.get(r + 0x58), run.get(r + 0x5c)});
    run.x87_step(CLAW_X87_I32, fp, {run.get(local + 0x4c)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
    {
        uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
        run.put(r + 0x58, uint32_t(bits));
        run.put(r + 0x5c, uint32_t(bits >> 32));
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x41fce0:
        return playerState(run, false);
    case 0x41fe80:
        return playerState(run, true);
    case 0x431cd0:
        return dispatch(run, arguments[0]);
    case 0x431df0:
        return stateCallback(run, receiver, arguments[0]);
    case 0x4320d0:
        return construct(run, receiver, arguments[0]);
    case 0x432250:
        return ballistic(run, receiver, arguments[0]);
    case 0x432460:
        return explode(run, receiver);
    case 0x4324e0:
        return exploding(run, receiver);
    case 0x432550:
        run.put(receiver + 0xc8, 1);
        return 0;
    case 0x432560:
        run.put(receiver + 0xc8, 1);
        return run.vcall(receiver, 0x2c);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace
CLAW_MODULE_ENTRY(claw_level_seven_crab_bomb_shared_entry, owned, body)
