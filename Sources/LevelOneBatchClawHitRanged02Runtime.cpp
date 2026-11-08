// Level 1 Claw hit reset and ranged attack
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
    case 0x417b00:
        return 4;
    case 0x41cc60:
        return 3;
    default:
        return -1;
    }
}

// 0x417b00. cdecl, 4 stack arguments (actor, owner, state, flag), returns void.
// Actor fields: +0x08 flags, +0x64 animation id, +0xcc, +0x10c, +0x148, +0x14c.
// State fields: +0x04, +0x20, +0x3c, +0x40, +0x124, +0x12c (attached object).
uint32_t function_417b00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t owner = arguments[1];
    uint32_t state = arguments[2];
    uint32_t flag = arguments[3];
    uint32_t world = run.get(0x537204);
    uint32_t value = run.get(world + 0x0c);
    value = value & 0xfdffffff;
    run.put(world + 0x0c, value);
    world = run.get(0x537204);
    value = run.get(world + 0x0c);
    value = value & 0xfeffffff;
    run.put(world + 0x0c, value);
    uint32_t attached = run.get(state + 0x12c);
    if (attached != 0) {
        uint32_t inner = run.get(attached + 0x6c);
        uint32_t object = run.get(inner + 0x18);
        run.call(0x421010, object, {0x4207a0, 1});
        run.call(0x420fc0, object + 0x2f4, {0});
        run.put(state + 0x12c, 0);
    }
    uint32_t pending = run.get(state + 0x04);
    run.put(state + 0x3c, 0);
    run.put(state + 0x20, 1);
    if (pending != 0) {
        uint32_t extra = run.get(state + 0x124);
        run.put(state + 0x04, 0);
        run.call(0x4c8220, actor + 0x188, {extra});
        uint32_t flags = run.get(actor + 0x08);
        flags = flags | 0x80;
        run.put(actor + 0x08, flags);
    }
    run.put(owner + 0x1c, 0x138c);
    run.put(owner + 0x20, 0x2ee);
    run.call(0x4c79e0, actor, {0x5246e8, 1});
    uint32_t flags = run.get(actor + 0x08);
    uint32_t animation = run.get(actor + 0x64);
    flags = flags & 0xffffffef;
    flags = flags | 5;
    run.put(actor + 0xcc, 4);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(actor + 0x08, flags);
    if (animation != 0x2134) {
        flags = flags | 0x20000;
        run.put(actor + 0x64, 0x2134);
        run.put(actor + 0x08, flags);
    }
    run.put(actor + 0x10c, 0);
    run.put(state + 0x40, 0);
    run.put(0x534de8, 0);
    run.put(0x534dec, 0);
    run.put(0x534dd0, 0);
    run.put(0x534dd4, 0x40a19400);
    if (flag != 0)
        run.call(0x41ebd0, 0, {});
    uint32_t manager = run.get(0x5371fc);
    run.call(0x4b7aa0, manager, {0});
    run.call(0x41f990, 0, {actor, owner, state, 0, 0});
    return 0;
}

// 0x41cc60. cdecl, 3 stack arguments (actor, unused, state), returns u32.
// Spawns the bullet for the current weapon (global 0x534eac: 0x26b8 fire,
// 0x26b9 lightning, 0x26ba ice) and initializes it. State fields: +0x00
// direction flag, +0x54 x offset, +0x58 y offset, +0xe8 value copied to the
// bullet's +0x6c object.
uint32_t function_41cc60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t state = arguments[2];
    uint32_t facing = run.get(state + 0x00);
    uint32_t y = run.get(state + 0x58) + run.get(actor + 0x50);
    uint32_t z = run.get(actor + 0x64) + 1;
    uint32_t velocity = 0x2bc;
    run.put(run.automatic(12), velocity);
    uint32_t xOffset = run.get(state + 0x54);
    uint32_t x = run.get(actor + 0x4c);
    if (facing == 0) {
        x = x - xOffset;
        velocity = 0xfffffd44;
        run.put(run.automatic(12), velocity);
    } else {
        x = x + xOffset;
    }
    uint32_t bullet = 0;
    uint32_t weapon = run.get(0x534eac);
    uint32_t bulletName = 0;
    uint32_t swordName = 0;
    uint32_t bulletFlag = 0;
    if (weapon == 0x26b8) {
        bulletName = 0x522df4;
        swordName = 0x5247b0;
        bulletFlag = 0x40000;
    } else if (weapon == 0x26b9) {
        bulletName = 0x522de4;
        swordName = 0x5247c0;
        bulletFlag = 0x100000;
    } else if (weapon == 0x26ba) {
        bulletName = 0x522dd8;
        swordName = 0x5247d0;
        bulletFlag = 0x80000;
    } else {
        return 0;
    }
    uint32_t spawner = run.get(run.get(actor + 0x0c) + 0x08);
    bullet = run.call(0x4c8da0, spawner, {0, x, y, z, bulletName, 0x40000});
    uint32_t bulletFlags = run.get(bullet + 0x164);
    bulletFlags = bulletFlags | bulletFlag;
    run.put(bullet + 0x164, bulletFlags);
    uint32_t table = run.get(run.get(actor + 0x0c) + 0x28);
    uint32_t existing = run.get(table + 0x30);
    if (existing == 0) {
        run.put(run.automatic(4), 0);
        run.call(0x4f6286, table + 0x10, {swordName, run.automatic(4)});
        uint32_t sword = run.get(run.automatic(4));
        if (sword != 0)
            run.call(0x4208e0, sword, {run.get(0x532c10), 0, 0, 0});
    }
    if (bullet == 0)
        return 0;
    // Slot 0x14 of the stack argument block was reused as the velocity local.
    velocity = run.get(run.automatic(12));
    run.put(bullet + 0xd0, 0x2000000);
    run.put(bullet + 0xd4, 4);
    run.put(bullet + 0x148, velocity);
    run.put(bullet + 0x14c, 0);
    bulletFlags = run.get(bullet + 0x164);
    bulletFlags = bulletFlags | 8;
    run.put(bullet + 0x164, bulletFlags);
    run.put(bullet + 0x104, 0x19);
    uint32_t inner = run.get(bullet + 0x6c);
    uint32_t value = run.get(state + 0xe8);
    run.put(inner + 0xb8, value);
    facing = run.get(state + 0x00);
    if (facing == 0) {
        uint32_t flags = run.get(bullet + 0x40);
        flags = flags | 2;
        run.put(bullet + 0x40, flags);
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x417b00:
        return function_417b00(run, receiver, arguments);
    case 0x41cc60:
        return function_41cc60(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_claw_hit_ranged_02_entry, owned, body)
