// Level 11 fish states
// Native Fish dispatch, lifecycle, swimming, strikes and water transitions.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Fish receiver: +0xc placed data, +0x10 current logic, +0x12c render.
// Doubles +0x38/+0x40/+0x48 acceleration, +0x50/+0x58/+0x60 velocity,
// +0x68/+0x70/+0x78 position, +0x80/+0x98 swim bounds.
// +0x138/+0x140 horizontal collision limits; +0x210/+0x220 rectangles.
// +0x184 state, +0x18c direction, +0x1a0 chomp latch, +0x134 saved frame.
// +0x400/+0x404/+0x408 animations; +0x40c/+0x410/+0x414 sounds.
// +0x418 water height, +0x41c/+0x420 X limits, +0x424 target X,
// +0x428 clock and +0x42c interval. Guest integers wrap at 32 bits.

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x441d00:
        return 1;
    case 0x4420e0:
        return 1;
    case 0x4423e0:
        return 1;
    case 0x442400:
        return 0;
    case 0x442470:
        return 0;
    case 0x442640:
        return 0;
    case 0x4427d0:
        return 0;
    case 0x442b00:
        return 0;
    case 0x442cb0:
        return 0;
    case 0x442d80:
        return 0;
    case 0x442e90:
        return 0;
    case 0x442f70:
        return 0;
    case 0x4430f0:
        return 0;
    default:
        return -1;
    }
}


uint32_t function_442470(Run &run, uint32_t r, const uint32_t *);
uint32_t function_4427d0(Run &run, uint32_t r, const uint32_t *);
uint32_t function_442e90(Run &run, uint32_t r, const uint32_t *);
uint32_t function_442400(Run &run, uint32_t r, const uint32_t *);

void mirror(Run &run, uint32_t r, uint32_t lo, uint32_t hi) {
    uint32_t old = run.get(r + lo);
    run.put(r + lo, 0u - run.get(r + hi));
    run.put(r + hi, 0u - old);
}
void rectangle(Run &run, uint32_t r, uint32_t offset) {
    uint32_t dst = run.get(r + 0xc) + 0x138;
    run.put(dst, run.get(r + offset));
    run.put(dst + 0x4, run.get(r + offset + 0x4));
    run.put(dst + 0x8, run.get(r + offset + 0x8));
    run.put(dst + 0xc, run.get(r + offset + 0xc));
    if (run.get8(run.get(r + 0x12c) + 0x40) & 2) {
        uint32_t placed = run.get(r + 0xc);
        uint32_t old = run.get(placed + 0x138);
        run.put(placed + 0x138, 0u - run.get(placed + 0x140));
        run.put(run.get(r + 0xc) + 0x140, 0u - old);
    }
}
void state(Run &run, uint32_t r, uint32_t name, uint32_t animation) {
    run.put(r + 0x24, run.get(run.get(r + 0x10) + 0x1c));
    uint32_t next = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(r + 0x10) + 0x1c, next);
    uint32_t render = run.get(r + 0x12c);
    uint32_t anim = run.get(r + animation);
    run.put(r + 0x134, run.get(render + 0x190));
    run.call(0x4c8220, render + 0x188, {anim});
}
void sound(Run &run, uint32_t ptr) {
    if (ptr && run.get(0x532c0c)) {
        run.call(0x4b45f0, run.get(ptr + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
}
void chomp(Run &run, uint32_t r) {
    if (run.get(run.get(r + 0x12c) + 0x16c) == 0xca && run.get(r + 0x1a0) == 0) {
        uint32_t ptr = run.get(r + 0x3a0);
        run.put(r + 0x1a0, 1);
        sound(run, ptr);
    }
}
void water(Run &run, uint32_t r) {
    if (!(double(run.gets(r + 0x418)) >= run.getd(r + 0x70)) &&
        double(run.gets(r + 0x41c)) <= run.getd(r + 0x68) &&
        run.getd(r + 0x68) <= double(run.gets(r + 0x420))) {
        sound(run, run.get(r + 0x410));
        run.vcall(r, 0x48);
    }
}
uint32_t lookup(Run &run, uint32_t index) {
    if (s32(index) < run.gets(0x537700) || run.gets(0x537704) < s32(index)) {
        if (!run.call(0x4db6e0, 0x5376f8, {index, 0})) {
            uint32_t error = run.get(0x544b4c);
            uint32_t value = run.call(0x4db5f0, 0);
            run.put(0x544b14, value);
            run.call(0x4db4d0, run.get(0x5376fc), {0x5376f8, error, 0xc});
            return run.get(0x53770c);
        }
    }
    return (index - run.get(0x537700)) * run.get(0x537710) + run.get(0x537708);
}
// 0x441d00: dispatch a registered Fish method, falling back to enemy logic.
uint32_t function_441d00(Run &run, uint32_t r, const uint32_t *a) {
    run.put(0x537718, 0);
    uint32_t slot = lookup(run, a[0]);
    if (run.get(slot)) {
        run.put(0x537718, 0);
        slot = lookup(run, a[0]);
        run.call(run.get(slot), r);
    } else {
        run.call(0x43d490, r, {a[0]});
    }
    return 0;
}
// 0x4420e0: construct Fish state, animation and sound resources.
uint32_t function_4420e0(Run &run, uint32_t r, const uint32_t *a) {
    run.call(0x4332f0, r, {a[0]});
    run.put(r + 0x428, 0);
    run.put(r + 0x42c, 0);
    run.put(r, 0x50dc84);
    run.call(0x4c7970, run.get(r + 0x12c), {0x5273e0});
    const uint32_t names[] = {0x5273d0, 0x5273bc, 0x5273bc, 0x5273a8, 0x527398, 0x527384};
    const uint32_t fields[] = {0x400, 0x408, 0x310, 0x374, 0x364, 0x404};
    for (unsigned i = 0; i < 6; ++i) {
        uint32_t animation = run.call(0x4062e0, r + 0x128, {names[i]});
        if (!animation) {
            animation = run.call(0x4062e0, r + 0x128, {0x5234b4});
        }
        run.put(r + fields[i], animation);
    }
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    uint32_t bank = run.get(run.get(run.get(r + 0x12c) + 0xc) + 0x28);
    run.call(0x4f6286, bank + 0x10, {0x527370, local});
    run.put(r + 0x3a0, run.get(local));
    const uint32_t soundNames[] = {0x527358, 0x527344, 0x527330, 0x52731c};
    const uint32_t soundFields[] = {0x3a4, 0x40c, 0x410, 0x414};
    for (unsigned i = 0; i < 4; ++i) {
        bank = run.get(run.get(run.get(r + 0x12c) + 0xc) + 0x28);
        uint32_t ptr = run.call(0x4061b0, bank, {soundNames[i]});
        run.put(r + soundFields[i], ptr);
    }
    uint32_t count = run.get(r + 0x2fc);
    if (!count) {
        run.call(0x4dbd20, r + 0x2f4, {0});
    } else {
        uint32_t bits = count <= 0x20 ? r + 0x300 : run.get(r + 0x300);
        run.put(bits, run.get(bits) | 1);
    }
    uint32_t render = run.get(r + 0x12c);
    run.put(render + 0x8, run.get(render + 0x8) | 0x40);
    run.put(run.get(r + 0x12c) + 0xd0, 4);
    run.put(run.get(r + 0x12c) + 0xd4, 0x3000022);
    run.call(0x4061e0, run.get(r + 0x12c), {r + 0x220});
    run.call(0x4061e0, run.get(r + 0x12c), {r + 0x210});
    run.call(0x406290, run.get(r + 0x12c));
    run.call(0x406240, run.get(r + 0x12c));
    run.put(r + 0x290, 0x32);
    run.put(r + 0x2a0, 0x32);
    run.put(r + 0x2ac, 0x32);
    run.put(r + 0x2b0, 0x32);
    run.put(r + 0x28c, 0x190);
    run.put(r + 0x29c, 0x12c);
    run.put(r + 0x2a4, 0x64);
    run.put(r + 0x2a8, 0x12c);
    if (!run.get(run.get(r + 0xc) + 0x104)) {
        run.put(run.get(r + 0xc) + 0x104, 10);
    }
    run.put(r + 0x418, run.get(run.get(r + 0xc) + 0x50));
    uint32_t low = run.call_x87(0x4a30e0, 0, run.getd(r + 0x80));
    run.put(r + 0x41c, low);
    uint32_t high = run.call_x87(0x4a30e0, 0, run.getd(r + 0x98));
    run.put(r + 0x420, high);
    function_442470(run, r, nullptr);
    return r;
}
// 0x4423e0: scalar deleting destructor.
uint32_t function_4423e0(Run &run, uint32_t r, const uint32_t *a) {
    function_442400(run, r, nullptr);
    if (a[0] & 1) {
        run.call(0x4f6428, 0, {r});
    }
    return r;
}
// 0x442400: destroy the bitset and the two CString members.
uint32_t function_442400(Run &run, uint32_t r, const uint32_t *) {
    run.put(r, 0x50b16c);
    run.call(0x4dbcd0, r + 0x2f4);
    run.call(0x4f6584, r + 0x1a8);
    run.call(0x4f6584, r + 0x1a4);
    run.put(r, 0x50b014);
    return 0;
}
// 0x442470: reset the idle state and swim direction.
uint32_t function_442470(Run &run, uint32_t r, const uint32_t *) {
    run.put(run.get(r + 0xc) + 0xcc, 7);
    uint32_t speed = run.call_x87(0x4a30e0, 0, run.getd(r + 0x50));
    run.putd(r + 0x80, double(run.gets(r + 0x41c)));
    run.putd(r + 0x98, double(run.gets(r + 0x420)));
    run.put(r + 0x40, 0);
    run.put(r + 0x44, 0);
    run.put(r + 0x50, 0);
    run.put(r + 0x58, 0);
    run.put(r + 0x60, 0);
    run.put(r + 0x54, 0);
    run.put(r + 0x5c, 0);
    run.put(r + 0x64, 0);
    run.putd(r + 0x70, double(run.gets(r + 0x418)));
    bool positive = s32(speed) > 0 && (run.getd(r + 0x68) < run.getd(r + 0x98) || run.getd(r + 0x68) > run.getd(r + 0x98));
    uint32_t render = run.get(r + 0x12c);
    run.putd(r + 0x50, positive ? run.getd(0x50dc30) : -run.getd(0x50dc30));
    if (bool(run.get8(render + 0x40) & 2) != positive) {
        mirror(run, r, 0x138, 0x140);
        run.put(render + 0x40, positive ? run.get(render + 0x40) | 2 : run.get(render + 0x40) & ~2u);
        render = run.get(r + 0x12c);
        if (run.get(render + 0x118) != 0x80000000) {
            mirror(run, render, 0x118, 0x120);
        }
        if (positive) {
            run.call(0x406150, render);
        } else if (run.get(render + 0x128) != 0x80000000) {
            mirror(run, render, 0x128, 0x130);
        }
        run.call(0x406180, render);
    }
    state(run, r, 0x523604, 0x400);
    return 0;
}
// 0x442640: update the idle swim and choose a strike.
uint32_t function_442640(Run &run, uint32_t r, const uint32_t *) {
    run.call(0x4c82a0, run.get(r + 0x12c) + 0x188, {run.get(0x5430c4)});
    bool turn = false;
    bool positive = false;
    if (!(run.getd(r + 0x68) < run.getd(r + 0x80) || run.getd(r + 0x68) > run.getd(r + 0x80))) {
        run.put(r + 0x50, run.get(0x50dc30));
        run.put(r + 0x54, run.get(0x50dc34));
        positive = true;
        turn = !(run.get8(run.get(r + 0x12c) + 0x40) & 2);
    } else if (!(run.getd(r + 0x68) < run.getd(r + 0x98) || run.getd(r + 0x68) > run.getd(r + 0x98))) {
        run.putd(r + 0x50, -run.getd(0x50dc30));
        turn = run.get8(run.get(r + 0x12c) + 0x40) & 2;
    }
    if (turn) {
        mirror(run, r, 0x138, 0x140);
        uint32_t render = run.get(r + 0x12c);
        run.put(render + 0x40, positive ? run.get(render + 0x40) | 2 : run.get(render + 0x40) & ~2u);
        render = run.get(r + 0x12c);
        run.call(0x406120, render);
        run.call(0x406150, render);
        run.call(0x406180, render);
    }
    if (run.get(r + 0x184) == 3 && ((!(run.getd(r + 0x50) >= run.getd(0x50dc50)) && run.get(r + 0x18c) == 3) ||
        (run.getd(r + 0x50) > run.getd(0x50dc50) && run.get(r + 0x18c) == 2))) {
        uint32_t player = run.get(0x537e88);
        if (run.getd(r + 0x70) > double(run.gets(player + 0x50))) {
            if (s32(run.call(0x4a3050, 0)) % 101 < 80) {
                function_4427d0(run, r, nullptr);
            }
        } else if (run.gets(player + 0x4c) >= run.gets(r + 0x41c) && run.gets(player + 0x4c) <= run.gets(r + 0x420)) {
            if (s32(run.call(0x4a3050, 0)) % 101 < 90) {
                run.vcall(r, 0x58);
            }
        }
    }
    return 0;
}

// 0x4427d0: enter the jumping strike and solve its trajectory.
uint32_t function_4427d0(Run &run, uint32_t r, const uint32_t *) {
    rectangle(run, r, 0x220);
    run.put(run.get(r + 0xc) + 0xcc, 8);
    state(run, r, 0x5272e0, 0x408);
    uint32_t half = uint32_t(run.gets(r + 0x2a8) / 2);
    uint32_t height = run.get(r + 0x418) - half;
    uint32_t displacement = run.get(r + 0x18c) == 2 ? 150u : 0u - 150u;
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    auto op = [&](uint32_t operation) { return run.x87_step(operation, fp); };
    auto memory = [&](uint32_t operation, uint32_t address) {
        return run.x87_step(operation, fp, {run.get(address), run.get(address + 0x4)});
    };
    auto value = [&](uint32_t operation, uint64_t bits) {
        return run.x87_step(operation, fp, {uint32_t(bits), uint32_t(bits >> 32)});
    };
    auto write = [&](uint32_t address) {
        uint64_t bits = op(CLAW_X87_STP_F64);
        run.put(address, uint32_t(bits));
        run.put(address + 0x4, uint32_t(bits >> 32));
    };
    uint64_t dx, dy, dz, ay, az, root;
    run.x87_step(CLAW_X87_I32, fp, {height});
    run.x87_step(CLAW_X87_I32, fp, {displacement});
    memory(CLAW_X87_ADD_F64, r + 0x68);
    run.put(r + 0x80, run.get(0x513e10));
    run.put(r + 0x84, run.get(0x513e14));
    run.put(r + 0x98, run.get(0x513e18));
    run.put(r + 0x9c, run.get(0x513e1c));
    run.put(r + 0x40, 0);
    run.put(r + 0x44, 0x409f4000);
    memory(CLAW_X87_SUB_F64, r + 0x68);
    ay = uint64_t(run.get(r + 0x40)) | (uint64_t(run.get(r + 0x44)) << 32);
    az = uint64_t(run.get(r + 0x48)) | (uint64_t(run.get(r + 0x4c)) << 32);
    dx = op(CLAW_X87_STP_F64);
    memory(CLAW_X87_SUB_F64, r + 0x70);
    dy = op(CLAW_X87_STP_F64);
    memory(CLAW_X87_F64, r + 0x78);
    op(CLAW_X87_CHS);
    dz = op(CLAW_X87_STP_F64);
    memory(CLAW_X87_F64, r + 0x38);
    op(CLAW_X87_ST(CLAW_X87_LD_ST, 0));
    value(CLAW_X87_MUL_F64, dx);
    op(CLAW_X87_CHS);
    value(CLAW_X87_F64, ay);
    value(CLAW_X87_MUL_F64, dy);
    op(CLAW_X87_ST(CLAW_X87_SUBP, 1));
    value(CLAW_X87_F64, az);
    value(CLAW_X87_MUL_F64, dz);
    op(CLAW_X87_ST(CLAW_X87_SUBP, 1));
    op(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    value(CLAW_X87_F64, ay);
    value(CLAW_X87_F64, dx);
    value(CLAW_X87_F64, dy);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    op(CLAW_X87_ST(CLAW_X87_MUL_TO0, 5));
    value(CLAW_X87_F64, az);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 3));
    value(CLAW_X87_MUL_F64, ay);
    value(CLAW_X87_F64, dz);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    op(CLAW_X87_ST(CLAW_X87_ADDP, 2));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    value(CLAW_X87_MUL_F64, dx);
    op(CLAW_X87_ST(CLAW_X87_LD_ST, 5));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    value(CLAW_X87_MUL_F64, az);
    op(CLAW_X87_ST(CLAW_X87_ADDP, 2));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 4));
    value(CLAW_X87_MUL_F64, dy);
    op(CLAW_X87_ST(CLAW_X87_ADDP, 4));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    value(CLAW_X87_MUL_F64, dz);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    memory(CLAW_X87_MUL_F64, 0x50dc60);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    op(CLAW_X87_ST(CLAW_X87_ADDP, 3));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    op(CLAW_X87_ST(CLAW_X87_MUL_TO0, 2));
    memory(CLAW_X87_MUL_F64, 0x50dc58);
    op(CLAW_X87_SQRT);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    op(CLAW_X87_ST(CLAW_X87_SUBP, 1));
    memory(CLAW_X87_MUL_F64, 0x50dc68);
    op(CLAW_X87_SQRT);
    root = op(CLAW_X87_ST_F64);
    memory(CLAW_X87_COMP_F64, 0x513e20);
    if (fp.status & 0x100) {
    op(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    op(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    run.put(r + 0x50, 0);
    run.put(r + 0x58, 0);
    run.put(r + 0x60, 0);
    run.put(r + 0x54, 0);
    op(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    run.put(r + 0x5c, 0);
    run.put(r + 0x64, 0);
    } else {
    memory(CLAW_X87_MUL_F64, 0x50dc70);
    memory(CLAW_X87_F64, 0x513e20);
    op(CLAW_X87_CHS);
    op(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    op(CLAW_X87_COMPP);
    if (fp.status & 0x100) {
        goto quadratic_solution;
    }
    memory(CLAW_X87_COM_F64, 0x513e20);
        if ((fp.status & 0x4100) == 0) {
            goto quadratic_solution;
        }
    op(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    op(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    op(CLAW_X87_ST(CLAW_X87_STP_ST, 0));
    value(CLAW_X87_F64, dy);
    value(CLAW_X87_F64, dx);
    value(CLAW_X87_F64, dz);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    op(CLAW_X87_ABS);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    op(CLAW_X87_ABS);
    op(CLAW_X87_ST(CLAW_X87_ADDP, 1));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    op(CLAW_X87_ABS);
    value(CLAW_X87_F64, dx);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    op(CLAW_X87_ST(CLAW_X87_ADDP, 2));
    value(CLAW_X87_F64, dy);
    value(CLAW_X87_F64, dz);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    op(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    op(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    op(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    value(CLAW_X87_MUL_F64, root);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    value(CLAW_X87_MUL_F64, root);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    value(CLAW_X87_MUL_F64, root);
        goto trajectory_store;
quadratic_solution:
    value(CLAW_X87_F64, root);
    value(CLAW_X87_MUL_F64, root);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    op(CLAW_X87_ST(CLAW_X87_ADD_TO0, 0));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    op(CLAW_X87_ST(CLAW_X87_SUBRP, 2));
    op(CLAW_X87_ST(CLAW_X87_DIVP, 1));
    op(CLAW_X87_ST(CLAW_X87_LD_ST, 0));
    op(CLAW_X87_SQRT);
    op(CLAW_X87_ST(CLAW_X87_LD_ST, 1));
    op(CLAW_X87_ST(CLAW_X87_LD_ST, 2));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    op(CLAW_X87_ST(CLAW_X87_MUL_TO0, 4));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    op(CLAW_X87_ST(CLAW_X87_STP_ST, 4));
    value(CLAW_X87_MUL_F64, ay);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    value(CLAW_X87_MUL_F64, az);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    memory(CLAW_X87_MUL_F64, 0x50dc68);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    memory(CLAW_X87_MUL_F64, 0x50dc68);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    value(CLAW_X87_SUBR_F64, dx);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    memory(CLAW_X87_MUL_F64, 0x50dc68);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    value(CLAW_X87_SUBR_F64, dy);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    value(CLAW_X87_SUBR_F64, dz);
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    op(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    op(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 1));
    op(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
trajectory_store:
    op(CLAW_X87_ST(CLAW_X87_XCH_ST, 2));
    write(r + 0x50);
    write(r + 0x58);
    write(r + 0x60);
    op(CLAW_X87_ST(CLAW_X87_STP_ST, 0));

    }
    sound(run, run.get(r + 0x414));
    run.put(r + 0x1a0, 0);
    return 0;
}
// 0x442b00: update jumping-strike animation, hit sound and water entry.
uint32_t function_442b00(Run &run, uint32_t r, const uint32_t *) {
    run.call(0x4c82a0, run.get(r + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t render = run.get(r + 0x12c);
    if (run.get(render + 0x1a4) && !run.get(render + 0x19c)) {
        rectangle(run, r, 0x210);
    }
    if (run.get(run.get(r + 0xc) + 0xcc) == 1) {
        rectangle(run, r, 0x210);
        function_442e90(run, r, nullptr);
    }
    chomp(run, r);
    water(run, r);
    return 0;
}
// 0x442cb0: enter horizontal strike toward the player's saved X.
uint32_t function_442cb0(Run &run, uint32_t r, const uint32_t *) {
    rectangle(run, r, 0x220);
    state(run, r, 0x5272f0, 0x310);
    double speed = run.getd(0x50dc38);
    if (run.get(r + 0x18c) != 2) {
        speed = -speed;
    }
    run.put(r + 0x424, run.get(run.get(0x537e88) + 0x4c));
    run.putd(r + 0x50, speed);
    run.put(r + 0x1a0, 0);
    return 0;
}
// 0x442d80: complete the strike upon crossing the saved target.
uint32_t function_442d80(Run &run, uint32_t r, const uint32_t *) {
    run.call(0x4c82a0, run.get(r + 0x12c) + 0x188, {run.get(0x5430c4)});
    chomp(run, r);
    if ((run.getd(r + 0x50) > run.getd(0x50dc50) && double(run.gets(r + 0x424)) <= run.getd(r + 0x68)) ||
        (run.getd(r + 0x50) < run.getd(0x50dc50) && run.getd(r + 0x68) <= double(run.gets(r + 0x424)))) {
        rectangle(run, r, 0x210);
        run.vcall(r, 0x48);
    }
    return 0;
}
// 0x442e90: enter the timed out-of-water flop.
uint32_t function_442e90(Run &run, uint32_t r, const uint32_t *) {
    run.put(run.get(r + 0xc) + 0xcc, 8);
    state(run, r, 0x5272d0, 0x404);
    uint32_t x = run.call_x87(0x4a30e0, 0, run.getd(r + 0x68));
    uint32_t speed = run.call_x87(0x4a30e0, 0, run.getd(0x50dc40));
    if (s32(x) >= run.gets(r + 0x420)) {
        speed = run.call_x87(0x4a30e0, 0, -run.getd(0x50dc40));
    }
    run.putd(r + 0x50, double(s32(speed)));
    run.put(r + 0x42c, 0xfa);
    run.put(r + 0x428, run.get(0x537210));
    sound(run, run.get(r + 0x40c));
    return 0;
}
// 0x442f70: timed alternating flop and water-entry transition.
uint32_t function_442f70(Run &run, uint32_t r, const uint32_t *) {
    run.call(0x4c82a0, run.get(r + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (run.get(0x537210) - run.get(r + 0x428) >= run.get(r + 0x42c)) {
        uint32_t render = run.get(r + 0x12c);
        bool positive = !run.get(0x5272cc);
        if (bool(run.get8(render + 0x40) & 2) != positive) {
            mirror(run, r, 0x138, 0x140);
            run.put(render + 0x40, positive ? run.get(render + 0x40) | 2 : run.get(render + 0x40) & ~2u);
            render = run.get(r + 0x12c);
            run.call(0x406120, render);
            run.call(0x406150, render);
            run.call(0x406180, render);
        }
        run.put(0x5272cc, run.get(0x5272cc) == 0);
        run.put(r + 0x42c, 0xfa);
        run.put(r + 0x428, run.get(0x537210));
        sound(run, run.get(r + 0x40c));
    }
    water(run, r);
    return 0;
}
// 0x4430f0: release reverse-lookup temporaries and dispatch non-dead cleanup.
uint32_t function_4430f0(Run &run, uint32_t r, const uint32_t *) {
    uint32_t key = run.call(0x441030, 0x537698, {run.get(run.get(r + 0x10) + 0x1c)});
    uint32_t ptr = run.get(0x5376b4);
    uint32_t count = run.get(0x5376b8);
    for (uint32_t i = 0; i < count; ++i) {
        if (ptr) {
            run.call(0x4f6439, ptr);
        }
        ptr += 4;
    }
    uint32_t comparison = run.call(0x4a3810, 0, {run.get(key), 0x5234f4});
    if (comparison) {
        uint32_t object = run.get(run.get(r + 0xc) + 0x74);
        if (run.get(object + 0xd0) == 0x20) {
            run.put(object + 0x8, run.get(object + 0x8) | 0x10000);
        }
        run.vcall(r, 0x5c, {0});
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x441d00:
        return function_441d00(run, receiver, arguments);
    case 0x4420e0:
        return function_4420e0(run, receiver, arguments);
    case 0x4423e0:
        return function_4423e0(run, receiver, arguments);
    case 0x442400:
        return function_442400(run, receiver, arguments);
    case 0x442470:
        return function_442470(run, receiver, arguments);
    case 0x442640:
        return function_442640(run, receiver, arguments);
    case 0x4427d0:
        return function_4427d0(run, receiver, arguments);
    case 0x442b00:
        return function_442b00(run, receiver, arguments);
    case 0x442cb0:
        return function_442cb0(run, receiver, arguments);
    case 0x442d80:
        return function_442d80(run, receiver, arguments);
    case 0x442e90:
        return function_442e90(run, receiver, arguments);
    case 0x442f70:
        return function_442f70(run, receiver, arguments);
    case 0x4430f0:
        return function_4430f0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_eleven_fish_states_01_entry, owned, body)
