// Canonical translation of the original v1.0 end gem entries.
#include "ClawRuntime.hpp"
namespace {
using claw::Run;
using claw::s32;
struct Floating {
    Run &run;
    ClawX87State state{};
    explicit Floating(Run &run) : run(run) {
        state.size = sizeof(state);
        state.version = CLAW_X87_VERSION;
        state.control = 0x023f;
    }
    void op(uint32_t operation) {
        run.x87_step(operation, state);
    }
    void load(uint64_t bits) {
        run.x87_step(CLAW_X87_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    void integer(uint32_t value) {
        run.x87_step(CLAW_X87_I32, state, {value});
    }
    void mem(uint32_t operation, uint64_t bits) {
        run.x87_step(operation, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    uint64_t save(bool pop = false) {
        return run.x87_step(pop ? CLAW_X87_STP_F64 : CLAW_X87_ST_F64, state);
    }
};
uint64_t bits(Run &run, uint32_t address) {
    return run.load<uint64_t>(address);
}
uint64_t doubleBits(double value) {
    uint64_t result;
    std::memcpy(&result, &value, sizeof(result));
    return result;
}
// 0x4205b0: restore the player after the gem's special state.
uint32_t resetPlayer(Run &run) {
    uint32_t player = run.get(0x537e88);
    if (!player)
        return 0;
    uint32_t state = run.get(player + 0x6c);
    if (!state || run.get(state + 0x1c) != 0x1392)
        return 0;
    uint32_t data = run.get(state + 0x14);
    uint32_t manager = run.get(0x537204);
    run.put(manager + 0xc, run.get(manager + 0xc) & 0xfdffffff);
    manager = run.get(0x537204);
    run.put(manager + 0xc, run.get(manager + 0xc) & 0xfeffffff);
    uint32_t child = run.get(data + 0x12c);
    if (child) {
        uint32_t behavior = run.get(run.get(child + 0x6c) + 0x18);
        run.call(0x421010, behavior, {0x4207a0, 1});
        run.call(0x420fc0, behavior + 0x2f4, {0});
        run.put(data + 0x12c, 0);
    }
    run.put(data + 0x3c, 0);
    run.put(data + 0x20, 1);
    if (run.get(data + 0x4)) {
        uint32_t animation = run.get(data + 0x124);
        run.put(data + 0x4, 0);
        run.call(0x4c8220, player + 0x188, {animation});
        run.put(player + 0x8, run.get(player + 0x8) | 0x80);
    }
    run.put(state + 0x1c, 0x18);
    run.call(0x4c79e0, player, {0x5246d0, 1});
    uint32_t flags = run.get(player + 0x8);
    run.put(player + 0xcc, 1);
    run.put(player + 0x148, 0);
    run.put(player + 0x14c, 0);
    run.put(player + 0x104, 0);
    run.put(player + 0x8, flags | 0x80);
    if (run.get(data) == 0) {
        run.put(player + 0x128, 0xfffffff1);
        run.put(player + 0x12c, 0xffffffd3);
        run.put(player + 0x130, 0x16);
    } else {
        run.put(player + 0x128, 0xffffffea);
        run.put(player + 0x12c, 0xffffffd3);
        run.put(player + 0x130, 0xf);
    }
    run.put(player + 0x134, 0x34);
    if (run.get(data) == 0) {
        run.call(0x40f6c0, player, {0xfffffff0, 0xffffffcc, 0x10, 0x3c});
    } else {
        run.put(player + 0x118, 0xfffffff0);
        run.put(player + 0x11c, 0xffffffcc);
        run.put(player + 0x120, 0x10);
        run.put(player + 0x124, 0x3c);
    }
    run.put(data + 0xfc, 0x28a);
    run.put(data + 0x114, 0x5dc);
    run.put(data + 0x120, 0x3a98);
    run.put(data + 0x118, 0);
    run.put(0x534e60, 0);
    run.put(0x534e64, 0);
    run.put(0x534e68, 0);
    run.put(0x534e6c, 0);
    run.put(0x534e70, 0);
    run.put(0x534e74, 0);
    run.put(player + 0x1b0, 0x3f800000);
    return 0;
}
// 0x43d0f0: preserve the original x87 operation order and local rounding.
void aim(Run &run, uint32_t gem, uint32_t x, uint32_t y) {
    if (x == 0 && y == 0) {
        resetPlayer(run);
        run.call(0x473660, 0, {run.get(gem + 0x8), 0x1f});
    }
    uint32_t motion = gem + 0x28;
    Floating fp(run);
    uint64_t local[11]{};
    fp.integer(y);
    fp.integer(x);
    run.put(gem + 0x148, x);
    run.put(gem + 0x14c, y);
    fp.mem(CLAW_X87_SUB_F64, bits(run, motion + 0x40));
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_SUB_F64, bits(run, motion + 0x48));
    fp.load(bits(run, motion + 0x10));
    fp.load(bits(run, motion + 0x18));
    fp.load(bits(run, motion + 0x50));
    fp.load(bits(run, motion + 0x20));
    fp.op(CLAW_X87_XCH_ST | 5);
    local[1] = fp.save(false);
    fp.op(CLAW_X87_XCH_ST | 4);
    local[2] = fp.save(false);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_CHS);
    local[3] = fp.save(false);
    fp.op(CLAW_X87_XCH_ST | 3);
    local[4] = fp.save(false);
    fp.op(CLAW_X87_XCH_ST | 2);
    local[5] = fp.save(false);
    fp.op(CLAW_X87_XCH_ST | 5);
    local[6] = fp.save(false);
    fp.load(local[4]);
    fp.mem(CLAW_X87_MUL_F64, local[1]);
    fp.op(CLAW_X87_CHS);
    fp.load(local[5]);
    fp.mem(CLAW_X87_MUL_F64, local[2]);
    fp.op(CLAW_X87_SUBP | 1);
    fp.load(local[6]);
    fp.mem(CLAW_X87_MUL_F64, local[3]);
    fp.op(CLAW_X87_SUBP | 1);
    local[8] = fp.save(true);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.mem(CLAW_X87_MUL_F64, local[4]);
    fp.load(local[8]);
    fp.op(CLAW_X87_XCH_ST | 6);
    fp.mem(CLAW_X87_MUL_F64, local[5]);
    fp.op(CLAW_X87_ADDP | 1);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.mem(CLAW_X87_MUL_F64, local[6]);
    fp.op(CLAW_X87_ADDP | 2);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.mem(CLAW_X87_MUL_F64, local[1]);
    fp.op(CLAW_X87_XCH_ST | 1);
    local[7] = fp.save(true);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.mem(CLAW_X87_MUL_F64, local[2]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_MUL_F64, local[3]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ADDP | 2);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.mem(CLAW_X87_MUL_F64, bits(run, 0x50db70));
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_ADDP | 1);
    fp.mem(CLAW_X87_MUL_F64, local[7]);
    fp.mem(CLAW_X87_MUL_F64, bits(run, 0x50db68));
    fp.op(CLAW_X87_SQRT);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_SUBP | 1);
    fp.mem(CLAW_X87_MUL_F64, bits(run, 0x50db78));
    fp.op(CLAW_X87_SQRT);
    local[0] = fp.save(false);
    fp.mem(CLAW_X87_COMP_F64, bits(run, 0x513e20));
    if (fp.state.status & 0x100) {
        run.put(gem + 0x50, 0);
        run.put(gem + 0x58, 0);
        run.put(gem + 0x60, 0);
        run.put(gem + 0x54, 0);
        run.put(gem + 0x5c, 0);
        run.put(gem + 0x64, 0);
        return;
    }
    fp.load(local[7]);
    fp.mem(CLAW_X87_MUL_F64, bits(run, 0x50db80));
    fp.load(bits(run, 0x513e20));
    fp.op(CLAW_X87_CHS);
    fp.op(CLAW_X87_LD_ST | 1);
    fp.op(CLAW_X87_COMPP);
    if (fp.state.status & 0x100) goto accelerated;
    fp.mem(CLAW_X87_COM_F64, bits(run, 0x513e20));
    if (!(fp.state.status & 0x4100)) goto accelerated;
    fp.op(CLAW_X87_POP);
    fp.load(local[1]);
    fp.load(local[2]);
    fp.load(local[3]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_ABS);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ABS);
    fp.op(CLAW_X87_ADDP | 1);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ABS);
    fp.load(local[1]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ADDP | 2);
    fp.load(local[2]);
    fp.load(local[3]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_DIV_TO0 | 3);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_DIV_TO0 | 3);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_DIV_TO0 | 3);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_MUL_F64, local[0]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.mem(CLAW_X87_MUL_F64, local[0]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_MUL_F64, local[0]);
    fp.op(CLAW_X87_XCH_ST | 2);
    {
        uint64_t value = fp.save(true);
        run.put(motion + 0x28, uint32_t(value));
        run.put(motion + 0x2c, uint32_t(value >> 32));
    }
    {
        uint64_t value = fp.save(true);
        run.put(motion + 0x30, uint32_t(value));
        run.put(motion + 0x34, uint32_t(value >> 32));
    }
    {
        uint64_t value = fp.save(true);
        run.put(motion + 0x38, uint32_t(value));
        run.put(motion + 0x3c, uint32_t(value >> 32));
    }
    fp.op(CLAW_X87_POP);
    return;
accelerated:
    fp.load(local[0]);
    fp.mem(CLAW_X87_MUL_F64, local[0]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_ADD_TOI | 0);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_SUB_F64, local[8]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_DIVP | 1);
    fp.op(CLAW_X87_LD_ST | 0);
    fp.op(CLAW_X87_SQRT);
    fp.op(CLAW_X87_LD_ST | 1);
    fp.op(CLAW_X87_LD_ST | 2);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_MUL_F64, local[4]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_XCH_ST | 3);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_MUL_F64, local[5]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_MUL_F64, local[6]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.mem(CLAW_X87_MUL_F64, bits(run, 0x50db78));
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_MUL_F64, bits(run, 0x50db78));
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_SUBR_F64, local[1]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.mem(CLAW_X87_MUL_F64, bits(run, 0x50db78));
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_SUBR_F64, local[2]);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.mem(CLAW_X87_SUBR_F64, local[3]);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_DIV_TO0 | 3);
    fp.op(CLAW_X87_XCH_ST | 1);
    fp.op(CLAW_X87_DIV_TO0 | 3);
    fp.op(CLAW_X87_XCH_ST | 2);
    fp.op(CLAW_X87_DIV_TO0 | 3);
    fp.op(CLAW_X87_XCH_ST | 1);
    {
        uint64_t value = fp.save(true);
        run.put(motion + 0x28, uint32_t(value));
        run.put(motion + 0x2c, uint32_t(value >> 32));
    }
    fp.op(CLAW_X87_XCH_ST | 1);
    {
        uint64_t value = fp.save(true);
        run.put(motion + 0x30, uint32_t(value));
        run.put(motion + 0x34, uint32_t(value >> 32));
    }
    {
        uint64_t value = fp.save(true);
        run.put(motion + 0x38, uint32_t(value));
        run.put(motion + 0x3c, uint32_t(value >> 32));
    }
    fp.op(CLAW_X87_POP);
}
// 0x43cb20: +0xc is the owner, +0x10 its state; +0x28 begins motion.
uint32_t construct(Run &run, uint32_t gem, uint32_t owner) {
    run.call(0x4082f0, gem, {owner});
    run.call(0x4080a0, gem + 0x28);
    run.put(gem, 0x50b2a4);
    uint32_t value0 = run.get(run.get(gem + 0x10) + 0x2c);
    if (value0 == 0) {
        uint32_t low = run.get(0x513e10);
        uint32_t high = run.get(0x513e14);
        run.put(gem + 0x80, low);
        run.put(gem + 0x84, high);
    } else {
        run.putd(gem + 0x80, double(s32(value0)));
    }
    uint32_t value1 = run.get(run.get(gem + 0x10) + 0x34);
    if (value1 == 0) {
        uint32_t low = run.get(0x513e10);
        uint32_t high = run.get(0x513e14);
        run.put(gem + 0x88, low);
        run.put(gem + 0x8c, high);
    } else {
        run.putd(gem + 0x88, double(s32(value1)));
    }
    uint32_t value2 = run.get(run.get(gem + 0x10) + 0x30);
    if (value2 == 0) {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(gem + 0x98, low);
        run.put(gem + 0x9c, high);
    } else {
        run.putd(gem + 0x98, double(s32(value2)));
    }
    uint32_t value3 = run.get(run.get(gem + 0x10) + 0x38);
    if (value3 == 0) {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(gem + 0xa0, low);
        run.put(gem + 0xa4, high);
    } else {
        run.putd(gem + 0xa0, double(s32(value3)));
    }
    Floating fp(run);
    // Unsigned global count was widened to a positive signed qword by the original.
    fp.load(doubleBits(double(run.get(0x537210))));
    fp.mem(CLAW_X87_MUL_F64, bits(run, 0x50db58));
    uint64_t scale = fp.save(true);
    uint32_t actor = run.get(gem + 0xc);
    uint64_t yVelocity = doubleBits(double(run.gets(actor + 0x14c)));
    uint64_t xVelocity = doubleBits(double(run.gets(actor + 0x148)));
    uint64_t y = doubleBits(double(run.gets(actor + 0x50)));
    uint64_t x = doubleBits(double(run.gets(actor + 0x4c)));
    run.call(0x408220, gem + 0x28, {uint32_t(x), uint32_t(x >> 32), uint32_t(y), uint32_t(y >> 32), 0, 0,
        uint32_t(xVelocity), uint32_t(xVelocity >> 32), uint32_t(yVelocity), uint32_t(yVelocity >> 32),
        0, 0, 0, 0, 0, 0, 0, 0, uint32_t(scale), uint32_t(scale >> 32), 0, 0});
    double magnitude = double(run.get(0x513e40));
    run.putd(gem + 0xe8, magnitude);
    run.putd(gem + 0xf0, magnitude);
    run.putd(gem + 0xf8, magnitude);
    run.put(gem + 0x120, 0);
    run.put(gem + 0x124, 0);
    run.put(run.get(gem + 0xc) + 0xcc, 7);
    run.call(0x4dca10, gem);
    run.put(gem + 0x128, owner);
    run.put(gem + 0x12c, owner);
    run.put(gem + 0x130, run.get(owner + 0x6c));
    run.put(gem, 0x50db2c);
    uint32_t animation = run.call(0x473630, 0, {0x1f});
    run.call(0x4c7970, run.get(gem + 0x12c), {animation});
    uint32_t target = run.get(gem + 0x12c);
    run.put(target + 0x8, run.get(target + 0x8) | 3);
    run.put(gem + 0x40, 0);
    run.put(gem + 0x44, 0x40590000);
    run.put(gem + 0x24, run.get(run.get(gem + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(gem + 0x10) + 0x1c, state);
    return gem;
}
// 0x43ca60: dispatch the owner object's state.
uint32_t logic(Run &run, uint32_t owner) {
    uint32_t state = run.get(owner + 0x6c);
    uint32_t code = run.get(state + 0x1c);
    if (code == 0) {
        run.put(state + 0x1c, 0x3e8);
        uint32_t gem = run.call(0x4f63ec, 0, {0x150});
        if (gem)
            gem = construct(run, gem, owner);
        run.vcall(gem, 0x10);
        run.put(state + 0x18, gem);
    } else if (code == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (code == 0x1e) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (code != 0x3e8) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}
// 0x43cdc0: the registered state table at 0x537608.
uint32_t tableSlot(Run &run, uint32_t code) {
    uint32_t lower = run.get(0x537610);
    if (s32(code) < s32(lower) || s32(code) > run.gets(0x537614)) {
        if (!run.call(0x4db6e0, 0x537608, {code, 0})) {
            uint32_t diagnostic = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            run.call(0x4db4d0, run.get(0x53760c), {0x537608, diagnostic, 0xc});
            return run.get(0x53761c);
        }
        lower = run.get(0x537610);
    }
    return (code - lower) * run.get(0x537620) + run.get(0x537618);
}
void dispatchState(Run &run, uint32_t gem, uint32_t code) {
    run.put(0x537628, 0);
    uint32_t slot = tableSlot(run, code);
    if (run.get(slot)) {
        run.put(0x537628, 0);
        slot = tableSlot(run, code);
        run.call(run.get(slot), gem);
    } else {
        run.call(0x4a36f0, 0, {gem});
    }
}
// 0x43d070: publish the motion coordinates and check arrival.
uint32_t tick(Run &run, uint32_t gem) {
    Floating fp(run);
    fp.load(bits(run, gem + 0x70));
    fp.load(bits(run, gem + 0x68));
    fp.state.popCount = 1;
    fp.state.pushCount = 0;
    fp.state.returned = 0;
    fp.state.eax = 0;
    fp.state.edx = 0;
    uint32_t x = run.call_x87_exact(0x4a30e0, 0, fp.state);
    run.put(0x52be14, x);
    fp.state.returned = 0;
    fp.state.eax = 0;
    fp.state.edx = 0;
    uint32_t y = run.call_x87_exact(0x4a30e0, 0, fp.state);
    run.put(0x52be18, y);
    fp.load(bits(run, gem + 0x58));
    fp.mem(CLAW_X87_COMP_F64, bits(run, 0x50db60));
    if (!(fp.state.status & 0x4100)) {
        fp.load(bits(run, gem + 0x70));
        fp.integer(run.get(gem + 0x14c));
        fp.op(CLAW_X87_COMPP);
        if (fp.state.status & 0x100) {
            run.put(gem + 0xc8, 1);
            uint32_t owner = run.get(gem + 0x12c);
            run.put(owner + 0x8, run.get(owner + 0x8) & 0xfffffffe);
            resetPlayer(run);
            run.call(0x473660, 0, {run.get(gem + 0x8), 0x1f});
            run.put(0x52be14, 0xffffffff);
            run.put(0x52be18, 0xffffffff);
        }
    }
    return 0;
}
// 0x40e5c0: +0x45c latches creation; +0x458 selects optional sound.
void createGem(Run &run, uint32_t actor) {
    if (run.get(actor + 0x45c))
        return;
    run.put(actor + 0x45c, 1);
    uint32_t owner = run.get(actor + 0x12c);
    uint32_t z = run.get(owner + 0x64) + 1;
    uint32_t y = run.get(owner + 0x50);
    uint32_t x = run.get(owner + 0x4c);
    uint32_t manager = run.get(run.get(run.get(actor + 0x130) + 0xc) + 0x8);
    uint32_t gem = run.call(0x4c8da0, manager, {0, x, y, z, 0x522aac, 0x40000});
    run.call(run.get(run.get(gem + 0x6c) + 0x10), 0, {gem});
    uint32_t player = run.get(actor + 0xc);
    uint32_t targetY = run.get(player + 0x14c);
    uint32_t targetX = run.get(player + 0x148);
    aim(run, run.get(run.get(gem + 0x6c) + 0x18), targetX, targetY);
    uint32_t sound = run.get(actor + 0x458);
    if (sound && run.get(0x532c0c)) {
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
}
// 0x4701b0: initialize the collectible level gem and its optional glitter.
uint32_t levelGem(Run &run, uint32_t owner) {
    uint32_t state = run.get(owner + 0x6c);
    uint32_t code = run.get(state + 0x1c);
    if (code) {
        if (code == 5) {
            run.call(0x4c82a0, owner + 0x188, {run.get(0x5430c4)});
        } else if (code == 0x1d) {
            uint32_t glitter = run.get(owner + 0xc8);
            if (glitter) {
                run.put(glitter + 0x8, run.get(glitter + 0x8) | 0x10000);
            }
        }
        return 1;
    }
    run.put(state + 0x168, 0);
    if (!run.get(owner + 0x190)) {
        run.call(0x4c79e0, owner, {0x52a198, 0});
    }
    run.call(0x4c7970, owner, {0x52a1e0});
    if (!run.get(owner + 0x64)) {
        uint32_t flags = run.get(owner + 0x8);
        run.put(owner + 0x64, 1000);
        run.put(owner + 0x8, flags | 0x20000);
    }
    uint32_t settings = run.get(run.get(0x5371fc) + 0x2c);
    uint32_t mode = run.vcall(settings, 0x10);
    if (mode == 4 || run.get(run.get(run.get(0x5371fc) + 0xc0) - 0x8)) {
        run.call(0x4c7970, owner, {0x52a1cc});
    } else {
        run.call(0x4c7970, owner, {(run.get8(settings + 0x14) & 1) ? 0x524d1cu : 0x52a1e0u});
        if (run.get(settings + 0x14) == 0xd) {
            run.call(0x4c7970, owner, {0x52a1e0});
        }
    }
    uint32_t rect = run.get(owner + 0x174);
    if (rect) {
        run.put(owner + 0x138, run.get(rect + 0x20) - run.get(rect + 0x18));
        run.put(owner + 0x13c, run.get(rect + 0x24) - run.get(rect + 0x1c));
        run.put(owner + 0x140, run.get(rect + 0x18) + run.get(rect + 0x20) - 1);
        run.put(owner + 0x144, run.get(rect + 0x24) + run.get(rect + 0x1c) - 1);
    }
    run.put(owner + 0x8, run.get(owner + 0x8) | 0x80000);
    if (!run.get(0x538418)) {
        run.call(0x4719e0, 0, {run.get(owner + 0xc)});
    }
    uint32_t count = run.get(0x52a190);
    uint32_t type = run.get(owner + 0x170);
    uint32_t i = 0;
    for (; s32(i) < s32(count); ++i) {
        if (run.get(0x537ec8 + i * 4) == type)
            break;
    }
    if (s32(i) < s32(count)) {
        run.put(owner + 0x4, i);
        if (!i) {
            run.put(owner + 0x4, 0x21);
        }
        uint32_t value = run.get(0x537fd0 + i * 4);
        uint32_t currentState = run.get(owner + 0x6c);
        run.put(owner + 0xfc, value);
        run.put(currentState + 0x168, run.get(0x538310 + i * 4));
        if (run.get(owner + 0xd0) == 1) {
            run.put(owner + 0xd0, run.get(0x5380d8 + i * 4));
        }
    } else {
        uint32_t currentState = run.get(owner + 0x6c);
        run.put(owner + 0x4, 0);
        run.put(owner + 0xfc, 100);
        run.put(currentState + 0x168, 0);
    }
    run.put(owner + 0xfc, 0x26ad);
    run.put(owner + 0xd0, 0x100);
    uint32_t glitter = 0;
    if (run.get(run.get(0x5371fc) + 0x124)) {
        uint32_t z = run.get(owner + 0x64) + 1;
        uint32_t y = run.get(owner + 0x50);
        uint32_t x = run.get(owner + 0x4c);
        glitter = run.call(0x4c8da0, run.get(run.get(owner + 0xc) + 0x8), {1, x, y, z, 0x522950, 0x240000});
    }
    if (glitter) {
        run.call(0x4c79e0, glitter, {0x52417c, 0});
        run.call(0x4c7970, glitter, {0x52a1b8});
    }
    run.put(owner + 0xc8, glitter);
    run.put(state + 0x1c, 5);
    return 1;
}
int owned(uint32_t function) {
    switch (function) {
    case 0x40e5c0:
    case 0x4205b0:
    case 0x43d070:
        return 0;
    case 0x43ca60:
    case 0x43cb20:
    case 0x43cdc0:
    case 0x4701b0:
        return 1;
    case 0x43d0f0:
        return 2;
    default:
        return -1;
    }
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *args) {
    switch (function) {
    case 0x40e5c0:
        createGem(run, receiver);
        return 0;
    case 0x4205b0:
        return resetPlayer(run);
    case 0x43ca60:
        return logic(run, args[0]);
    case 0x43cb20:
        return construct(run, receiver, args[0]);
    case 0x43cdc0:
        dispatchState(run, receiver, args[0]);
        return 0;
    case 0x43d070:
        return tick(run, receiver);
    case 0x43d0f0:
        aim(run, receiver, args[0], args[1]);
        return 0;
    case 0x4701b0:
        return levelGem(run, args[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_end_level_gem_closure_entry, owned, body)
