// Level 14 Omar constructor and ring construction.
#include "ClawRuntime.hpp"
namespace {
using claw::Run;
int owned(uint32_t function) {
    switch (function) {
    case 0x463460: return 1;
    case 0x464010: return 1;
    case 0x464110: return 0;
    default: return -1;
    }
}
ClawX87State emptyFP() {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    return fp;
}
void loadDouble(Run &run, ClawX87State &fp, uint32_t address) {
    run.x87_step(CLAW_X87_F64, fp, {run.get(address), run.get(address + 4)});
}
void mulDouble(Run &run, ClawX87State &fp, uint32_t address) {
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(address), run.get(address + 4)});
}
void loadFloat(Run &run, ClawX87State &fp, uint32_t address) {
    const double value = double(run.getf(address));
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    run.x87_step(CLAW_X87_F64, fp, {uint32_t(bits), uint32_t(bits >> 32)});
}
void mulFloat(Run &run, ClawX87State &fp, uint32_t address) {
    const double value = double(run.getf(address));
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(bits), uint32_t(bits >> 32)});
}
uint32_t ftol(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}
// 0x464110. Render +0x12c; world +0xc; slots +0x484;
// records +0x4a8 with stride 0xf0 and angle +0x40.
void createRings(Run &run, uint32_t receiver, ClawX87State &fp) {
    uint32_t render = run.get(receiver + 0x12c);
    run.put(render + 0x8, run.get(render + 0x8) & 0xfffffffbu);
    render = run.get(receiver + 0x12c);
    run.put(render + 0x40, run.get(render + 0x40) & 0xfffffff7u);
    run.put(receiver + 0xd20, 1);
    run.put(receiver + 0xd1c, 1);
    run.call(0x464eb0, receiver, {0xa50a});
    run.call(0x464ec0, receiver, {0x9ab});
    run.vcall(receiver, 0x48);
    run.put(receiver + 0xd18, 0);
    for (uint32_t index = 0; index < 9; ++index) {
        const uint32_t record = receiver + 0x4f0 + index * 0xf0;
        run.x87_step(CLAW_X87_I32, fp, {index * 0x21});
        run.put(record, 0);
        run.put(record + 0x8, 0);
        run.put(record - 0x20, 0);
        const uint64_t angle = run.x87_step(CLAW_X87_STP_F64, fp);
        run.put(record - 0x8, uint32_t(angle));
        run.put(record - 0x4, uint32_t(angle >> 32));
        run.put(record - 0x18, 0);
        run.put(record - 0x10, 0);
        run.put(record - 0x38, 0);
        run.put(record - 0x30, 0);
        run.put(record - 0x28, 0);
        run.put(record - 0x48, 0);
        run.put(record - 0x40, 0);
        run.put(record + 0x4, 0);
        run.put(record + 0xc, 0);
        run.put(record - 0x1c, 0xc06f4000);
        run.put(record - 0x14, 0);
        run.put(record - 0xc, 0);
        run.put(record - 0x34, 0);
        run.put(record - 0x2c, 0);
        run.put(record - 0x24, 0);
        run.put(record - 0x44, 0);
        run.put(record - 0x3c, 0);
        const uint32_t slot = receiver + 0x484 + index * 4;
        const uint32_t existing = run.get(slot);
        loadDouble(run, fp, record - 0x8);
        mulDouble(run, fp, 0x50eab8);
        mulDouble(run, fp, 0x50eac8);
        if (!existing) {
            run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), fp);
            run.x87_step(CLAW_X87_SIN, fp);
            render = run.get(receiver + 0x12c);
            const uint32_t serial = run.get(render + 0x64) + 1;
            mulDouble(run, fp, 0x50ead0);
            const uint32_t sine = ftol(run, fp);
            run.x87_step(CLAW_X87_COS, fp);
            const uint32_t y = run.get(render + 0x50) - sine;
            mulDouble(run, fp, 0x50ead0);
            const uint32_t cosine = ftol(run, fp);
            const uint32_t x = run.get(render + 0x4c) - cosine;
            const uint32_t context = run.get(run.get(run.get(receiver + 0x130) + 0xc) + 0x8);
            const uint32_t ring = run.call(0x4c8da0, context, {0, x, y, serial, 0x522c40, 0x40000});
            run.put(slot, ring);
            run.put(ring + 0x8, run.get(ring + 0x8) | 2);
            const uint32_t published = run.get(slot);
            run.call(run.get(run.get(published + 0x6c) + 0x10), 0, {published});
        } else {
            run.x87_step(CLAW_X87_POP, fp);
        }
    }
    run.put(run.get(receiver + 0xc) + 0x10c, 100);
    const uint32_t world = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(world + 0x10c)});
    mulFloat(run, fp, 0x5262b4);
    const uint32_t health = ftol(run, fp);
    run.put(world + 0x10c, health);
}
// 0x464010. World signed coordinates +0x4c/+0x50; ring logic +0x6c.
uint32_t positionRings(Run &run, uint32_t receiver, const uint32_t *arguments) {
    auto fp = emptyFP();
    fp.popCount = 0;
    fp.pushCount = 0;
    run.call_x87_exact(0x44d000, receiver, fp, {arguments[0]});
    if (!run.get(receiver + 0x484))
        return 0;
    for (uint32_t index = 0; index < 9; ++index) {
        const uint32_t slot = receiver + 0x484 + index * 4;
        loadDouble(run, fp, receiver + 0x4e8 + index * 0xf0);
        uint32_t world = run.get(receiver + 0xc);
        mulDouble(run, fp, 0x50eab8);
        mulDouble(run, fp, 0x50eac8);
        run.x87_step(CLAW_X87_I32, fp, {run.get(world + 0x4c)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), fp);
        run.x87_step(CLAW_X87_COS, fp);
        mulDouble(run, fp, 0x50ead0);
        run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
        const uint32_t x = ftol(run, fp);
        run.put(run.get(slot) + 0x4c, x);
        world = run.get(receiver + 0xc);
        run.x87_step(CLAW_X87_I32, fp, {run.get(world + 0x50)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_SIN, fp);
        mulDouble(run, fp, 0x50ead0);
        run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
        const uint32_t y = ftol(run, fp);
        run.put(run.get(slot) + 0x50, y);
        const uint32_t ring = run.get(slot);
        const uint32_t mode = run.get(receiver + 0xd18);
        const uint32_t logic = run.get(run.get(ring + 0x6c) + 0x18);
        run.call(0x465480, logic, {mode});
    }
    return 0;
}
uint32_t resourceManager(Run &run, uint32_t receiver, uint32_t offset) {
    return run.get(run.get(run.get(receiver + 0x12c) + 0xc) + offset);
}
// 0x463460. Establish resources, combat state and all nine rings.
uint32_t construct(Run &run, uint32_t receiver, const uint32_t *arguments) {
    auto fp = emptyFP();
    fp.popCount = 0;
    fp.pushCount = 0;
    run.call_x87_exact(0x40e0d0, receiver, fp, {arguments[0]});
    run.call(0x4a4590, 0, {receiver + 0x4a8, 0xf0, 9, 0x4080a0, 0x4c96b0});
    run.put(receiver + 0xd30, 0);
    run.put(receiver + 0xd34, 0);
    run.put(receiver, 0x50eafc);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x529a18});
    uint32_t value = run.call(0x4061b0, resourceManager(run, receiver, 0x2c), {0x529a04});
    if (!value)
        value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    run.put(receiver + 0x338, value);
    const uint32_t names[] = {0x5299f0, 0x5299e0, 0x5299cc, 0x5299b4, 0x5299a0, 0x52998c, 0x52998c};
    const uint32_t fields[] = {0x334, 0x350, 0x32c, 0x460, 0x310, 0x384, 0x388};
    for (uint32_t index = 0; index < 7; ++index) {
        value = run.call(0x4062e0, receiver + 0x128, {names[index]});
        if (!value)
            value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + fields[index], value);
    }
    const uint32_t soundNames[] = {0x529978, 0x529964, 0x529950, 0x52993c, 0x529924, 0x529910};
    const uint32_t soundFields[] = {0x464, 0x468, 0x46c, 0x470, 0x474, 0x3a4};
    const uint32_t local = run.automatic(4);
    for (uint32_t index = 0; index < 6; ++index) {
        run.put(local, 0);
        run.call(0x4f6286, resourceManager(run, receiver, 0x28) + 0x10, {soundNames[index], local});
        run.put(receiver + soundFields[index], run.get(local));
    }
    value = run.call(0x4061b0, resourceManager(run, receiver, 0x28), {0x5298f8});
    run.put(receiver + 0x478, value);
    value = run.call(0x4061b0, resourceManager(run, receiver, 0x28), {0x5298e0});
    run.put(receiver + 0x47c, value);
    value = run.call(0x4061b0, resourceManager(run, receiver, 0x28), {0x5298cc});
    run.put(receiver + 0x480, value);
    run.icall(0x546d5c, {receiver + 0x210, 0xffffffff, 0xffffffff, 1, 1});
    run.icall(0x546d5c, {receiver + 0x250, 0xfffffff5, 0xffffffd1, 0x17, 0x3d});
    run.icall(0x546d5c, {receiver + 0x260, 0xfffffff5, 0xffffffd1, 0x17, 0x3d});
    run.call(0x4208b0, run.get(receiver + 0x12c), {0xfffffff5, 0xffffffd1, 0x17, 0x3d});
    run.call(0x40f6c0, run.get(receiver + 0x12c), {run.get(receiver + 0x250), run.get(receiver + 0x254), run.get(receiver + 0x258), run.get(receiver + 0x25c)});
    run.put(receiver + 0x2b4, 10);
    run.put(receiver + 0x2b8, 0xfffffff6);
    run.put(receiver + 0x2bc, 0xffffffd3);
    run.put(receiver + 0x2c0, 0xffffffec);
    run.put(receiver + 0x2c4, 0x14);
    run.put(receiver + 0x2c8, 0xfffffff1);
    run.put(receiver + 0x28c, 500);
    run.put(receiver + 0x290, 0x28);
    run.put(receiver + 0x294, 300);
    run.put(receiver + 0x298, 0x28);
    run.put(receiver + 0x29c, 200);
    run.put(receiver + 0x2a0, 0x28);
    run.put(receiver + 0x2a4, 0x38);
    run.put(receiver + 0x2a8, 0x28);
    run.put(receiver + 0x2ac, 0x38);
    run.put(receiver + 0x2b0, 0x28);
    run.put(receiver + 0x2e4, 0x32);
    loadFloat(run, fp, 0x5262b8);
    mulFloat(run, fp, 0x50eac0);
    value = ftol(run, fp);
    if (value <= 99)
        value = 99;
    uint32_t world = run.get(receiver + 0xc);
    run.put(receiver + 0x2e4, value);
    run.put(world + 0x10c, 100);
    world = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(world + 0x10c)});
    mulFloat(run, fp, 0x5262b4);
    value = ftol(run, fp);
    run.put(world + 0x10c, value);
    run.put(run.get(receiver + 0xc) + 0x104, 0x1e);
    world = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(world + 0x104)});
    mulFloat(run, fp, 0x5262b0);
    value = ftol(run, fp);
    run.put(world + 0x104, value);
    const uint32_t bits = run.get(receiver + 0x2fc);
    if (bits > 9) {
        const uint32_t storage = bits > 0x20 ? run.get(receiver + 0x300) : receiver + 0x300;
        run.put(storage, run.get(storage) ^ 0x200);
    }
    run.put(receiver + 0xd18, 0);
    run.put(receiver + 0xd1c, 1);
    run.put(receiver + 0xd20, 1);
    run.put(receiver + 0xd40, 0);
    for (uint32_t index = 0; index < 9; ++index)
        run.put(receiver + 0x484 + index * 4, 0);
    for (uint32_t index = 0; index < 3; ++index) {
        const uint32_t low = run.get(0x513e10);
        const uint32_t high = run.get(0x513e14);
        run.put(receiver + 0x80 + index * 8, low);
        run.put(receiver + 0x84 + index * 8, high);
        const uint32_t otherLow = run.get(0x513e18);
        const uint32_t otherHigh = run.get(0x513e1c);
        run.put(receiver + 0x98 + index * 8, otherLow);
        run.put(receiver + 0x9c + index * 8, otherHigh);
    }
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x5c, 0);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0);
    uint32_t render = run.get(receiver + 0x12c);
    run.put(render + 0x8, run.get(render + 0x8) & 0xfffffffbu);
    world = run.get(receiver + 0xc);
    if (run.get(world + 0x64) != 0x1005) {
        run.put(world + 0x64, 0x1005);
        run.put(world + 0x8, run.get(world + 0x8) | 0x20000);
    }
    createRings(run, receiver, fp);
    render = run.get(receiver + 0x12c);
    run.put(render + 0x50, run.get(render + 0x50) - 0x20);
    const uint32_t resource = run.get(receiver + 0x128);
    run.call(0x4cd800, run.get(run.get(resource + 0xc) + 0x24), {resource, 0});
    run.put(run.get(receiver + 0x128) + 0xcc, 1);
    run.call(0x405060, receiver);
    return receiver;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x463460: return construct(run, receiver, arguments);
    case 0x464010: return positionRings(run, receiver, arguments);
    case 0x464110: {
        auto fp = emptyFP();
        createRings(run, receiver, fp);
        return 0;
    }
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_level_fourteen_omar_ring_construction_01_entry, owned, body)
