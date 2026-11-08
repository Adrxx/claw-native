// Level 1 Claw hit reactions and ranged helpers
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x405f80:
        return 0;
    case 0x41c9f0:
        return 3;
    case 0x41cab0:
        return 3;
    case 0x41cb80:
        return 3;
    case 0x41dd80:
        return 3;
    case 0x41e660:
        return 4;
    case 0x4207a0:
        return 0;
    default:
        return -1;
    }
}

// Spawns a named object through the object manager at [[owner + 0xc] + 8]
// (original 0x4c8da0, thiscall, six stack arguments).
uint32_t spawn(Run &run, uint32_t owner, uint32_t x, uint32_t y, uint32_t z, uint32_t name) {
    uint32_t manager = run.get(owner + 0xc);
    uint32_t receiver = run.get(manager + 0x8);
    return run.call(0x4c8da0, receiver, {0, x, y, z, name, 0x40000});
}

// 0x405f80. Returns 1 when the flag at 0x534874 is set and the global at
// 0x5349dc equals the value at +0xc of the receiver.
uint32_t function_405f80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(0x534874) == 0)
        return 0;
    uint32_t current = run.get(0x5349dc);
    uint32_t value = run.get(receiver + 0xc);
    if (current == value)
        return 1;
    return 0;
}

// 0x41c9f0. Fires a PistolBullet from owner (arg 0) using player (arg 2).
// Owner fields: +0x4c x, +0x50 y, +0x64 z. Player fields: +0x00 facing,
// +0x54 x offset, +0x58 y offset, +0x70 pistol ammo, +0xe8 owner tag.
uint32_t function_41c9f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t owner = arguments[0];
    uint32_t player = arguments[2];
    uint32_t y = run.get(player + 0x58) + run.get(owner + 0x50);
    uint32_t x = run.get(owner + 0x4c);
    uint32_t z = run.get(owner + 0x64) - 1;
    uint32_t speed = 700;
    if (run.get(player) == 0) {
        x = x - run.get(player + 0x54);
        speed = 0xfffffd44;
    } else {
        x = x + run.get(player + 0x54);
    }
    uint32_t bullet = spawn(run, owner, x, y, z, 0x522dc8);
    if (!bullet)
        return 0;
    uint32_t sub = run.get(bullet + 0x6c);
    run.put(bullet + 0xd0, 0x20);
    run.put(bullet + 0xd4, 4);
    run.put(bullet + 0x148, speed);
    run.put(bullet + 0x14c, 0);
    run.put(sub + 0xb8, run.get(player + 0xe8));
    int32_t ammo = run.gets(player + 0x70);
    if (ammo > 0)
        run.put(player + 0x70, uint32_t(ammo) - 1);
    run.put(bullet + 0x104, 8);
    run.call(0x4c7970, bullet, {0x524130});
    return 1;
}

// 0x41cab0. Fires a MagicBullet; magic ammo is at player +0x74.
uint32_t function_41cab0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t owner = arguments[0];
    uint32_t player = arguments[2];
    uint32_t y = run.get(player + 0x58) + run.get(owner + 0x50);
    uint32_t x = run.get(owner + 0x4c);
    uint32_t z = run.get(owner + 0x64) + 1;
    uint32_t speed = 700;
    if (run.get(player) == 0) {
        x = x - run.get(player + 0x54);
        speed = 0xfffffd44;
    } else {
        x = x + run.get(player + 0x54);
    }
    uint32_t bullet = spawn(run, owner, x, y, z, 0x522e00);
    if (!bullet)
        return 0;
    int32_t ammo = run.gets(player + 0x74);
    if (ammo > 0)
        run.put(player + 0x74, uint32_t(ammo) - 1);
    uint32_t flags = run.get(bullet + 0x164) | 8;
    uint32_t sub = run.get(bullet + 0x6c);
    run.put(bullet + 0xd0, 0x2000000);
    run.put(bullet + 0xd4, 4);
    run.put(bullet + 0x148, speed);
    run.put(bullet + 0x14c, 0);
    run.put(bullet + 0x164, flags);
    run.put(bullet + 0x104, 0x19);
    run.put(sub + 0xb8, run.get(player + 0xe8));
    if (run.get(player) == 0)
        run.put(bullet + 0x40, run.get(bullet + 0x40) | 2);
    return 1;
}

// 0x41cb80. Throws Dynamite; the throw strength is
// ((+0x100 - +0x104) * 200) / (+0x108 - +0x104), clamped to 0..200 and
// negated when facing left. Dynamite count is at player +0x78.
uint32_t function_41cb80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t owner = arguments[0];
    uint32_t player = arguments[2];
    uint32_t x = run.get(owner + 0x4c);
    uint32_t y = run.get(player + 0x58) + run.get(owner + 0x50);
    uint32_t z = run.get(owner + 0x64) + 1;
    uint32_t base = run.get(player + 0x104);
    uint32_t denominator = run.get(player + 0x108) - base;
    if (denominator == 0)
        denominator = 1;
    uint32_t numerator = (run.get(player + 0x100) - base) * 200;
    if (s32(denominator) == -1 && numerator == 0x80000000u)
        run.fail(CLAW_FAULT_ABI, 0x41cb80);
    int32_t strength = s32(numerator) / s32(denominator);
    if (strength <= 0)
        strength = 0;
    if (strength >= 200)
        strength = 200;
    uint32_t damage = uint32_t(strength);
    if (run.get(player) == 0) {
        x = x - run.get(player + 0x54);
        damage = 0u - damage;
    } else {
        x = x + run.get(player + 0x54);
    }
    uint32_t dynamite = spawn(run, owner, x, y, z, 0x522bec);
    if (!dynamite)
        return 0;
    run.put(player + 0x78, run.get(player + 0x78) - 1);
    run.put(dynamite + 0x158, damage);
    run.put(dynamite + 0xd0, 0x20);
    run.put(dynamite + 0xd4, 4);
    run.put(dynamite + 0x104, 0xf);
    return 1;
}

// Calls the hit reaction 0x41de90 (cdecl, four stack arguments).
void react(Run &run, const uint32_t *arguments, uint32_t code) {
    run.call(0x41de90, 0, {arguments[0], arguments[1], arguments[2], code});
}

// 0x41dd80. Chooses a hit reaction code from the attack type at arg 2 +0x30
// (1..3) and the state at arg 1 +0x1c, when arg 2 +0x4 is zero.
uint32_t function_41dd80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t hit = arguments[2];
    if (run.get(hit + 0x4) != 0)
        return 0;
    uint32_t kind = run.get(hit + 0x30);
    if (kind == 1) {
        uint32_t state = run.get(arguments[1] + 0x1c);
        if (state == 4 || state == 0x19)
            react(run, arguments, 9);
        else if (state == 0x1a)
            react(run, arguments, 0xe);
        else
            react(run, arguments, 5);
        return 0;
    }
    if (kind == 2) {
        uint32_t state = run.get(arguments[1] + 0x1c);
        if (state == 4 || state == 0x19)
            react(run, arguments, 0xa);
        else if (state == 0x1a)
            react(run, arguments, 0xf);
        else
            react(run, arguments, 6);
        return 0;
    }
    if (kind == 3) {
        uint32_t state = run.get(arguments[1] + 0x1c);
        if (state == 4 || state == 0x19)
            react(run, arguments, 0x12);
        else if (state == 0x1a)
            react(run, arguments, 0x10);
        else
            react(run, arguments, 0xc);
    }
    return 0;
}

// 0x41e660. Returns whether target (arg 3) is in melee reach of attacker
// (arg 0) given attack record arg 2 (+0x0 facing, +0x4 busy).
uint32_t function_41e660(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t attacker = arguments[0];
    uint32_t record = arguments[2];
    uint32_t target = arguments[3];
    uint32_t flags = run.get(target + 0x164);
    if ((flags & 1) == 0)
        return 0;
    if (run.get(record + 0x4) != 0)
        return 0;
    uint32_t margin = 0;
    if ((flags & 0x400) == 0)
        margin = 0x14;
    uint32_t state = run.get(attacker + 0xcc);
    if (state != 2 && state != 1)
        return 0;
    uint32_t attackerX = run.get(attacker + 0x4c);
    uint32_t targetX = run.get(target + 0x4c);
    if (s32(margin + attackerX) < s32(targetX)) {
        if (run.get(record) == 0)
            return 0;
    }
    if (s32(attackerX - margin) > s32(targetX)) {
        if (run.get(record) != 0)
            return 0;
    }
    uint32_t delta = run.get(attacker + 0x124);
    delta = delta - run.get(target + 0x50);
    delta = delta - run.get(target + 0x124);
    delta = delta + run.get(attacker + 0x50);
    uint32_t sign = uint32_t(s32(delta) >> 31);
    uint32_t magnitude = (delta ^ sign) - sign;
    if (s32(magnitude) <= 0x14)
        return 1;
    return 0;
}

// 0x4207a0. Tail-jumps to virtual method +0x94 of the receiver.
uint32_t function_4207a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.vcall(receiver, 0x94, {});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x405f80:
        return function_405f80(run, receiver, arguments);
    case 0x41c9f0:
        return function_41c9f0(run, receiver, arguments);
    case 0x41cab0:
        return function_41cab0(run, receiver, arguments);
    case 0x41cb80:
        return function_41cb80(run, receiver, arguments);
    case 0x41dd80:
        return function_41dd80(run, receiver, arguments);
    case 0x41e660:
        return function_41e660(run, receiver, arguments);
    case 0x4207a0:
        return function_4207a0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_claw_hit_ranged_01_entry, owned, body)
