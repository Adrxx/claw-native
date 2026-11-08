// Observed Level 1 player actions batch 3
//
// Native implementation of the owned functions, recovered from the decompile
// and disassembly in the task packet.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

#include <cmath>
#include <cstring>

namespace {

using claw::Run;
using claw::s32;
using claw::recovered::v10::ActorFields;
using claw::recovered::v10::LogicHolderFields;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x41b630:
        return 3;
    case 0x41c4e0:
        return 3;
    case 0x41c5a0:
        return 3;
    case 0x41ce80:
        return 1;
    case 0x41d6f0:
        return 1;
    case 0x41d750:
        return 4;
    case 0x41d850:
        return 3;
    case 0x41de90:
        return 4;
    case 0x41e710:
        return 1;
    case 0x41f850:
        return 2;
    case 0x41fc30:
        return 4;
    default:
        return -1;
    }
}

// Low and high 32-bit words of a binary64 value, as pushed on the stack.
uint32_t lowWord(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return uint32_t(bits);
}

uint32_t highWord(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return uint32_t(bits >> 32);
}

// 0x4a30e0 (__ftol): truncates ST(0) to a 64-bit integer and returns the low
// word. Values outside the 64-bit range and NaN give the integer indefinite,
// whose low word is zero.
uint32_t truncateToInt(double value) {
    if (!(value > -9223372036854775808.0 && value < 9223372036854775808.0))
        return 0;
    int64_t whole = int64_t(value);
    return uint32_t(whole);
}

// Clears bit 0x2000000 and then bit 0x1000000 of the dword at [[0x537204]+0xc].
// The global is read again before the second mask, as the original does.
void clearInputFlags(Run &run) {
    uint32_t input = run.get(0x537204);
    uint32_t value = run.get(input + 0xc);
    value = value & 0xfdffffff;
    run.put(input + 0xc, value);
    input = run.get(0x537204);
    value = run.get(input + 0xc);
    value = value & 0xfeffffff;
    run.put(input + 0xc, value);
}

// Detaches the held object of a state record: state+0x12c holds the object.
// Used by 0x41c4e0 and the default case of 0x41de90.
void detachHeldObject(Run &run, uint32_t state) {
    uint32_t held = run.get(state + 0x12c);
    if (held == 0)
        return;
    ActorFields detachedActorFields{run, held};
    uint32_t block = detachedActorFields.holder();
    LogicHolderFields detachedHolderFields{run, block};
    uint32_t logic = detachedHolderFields.logic();
    uint32_t mode = run.get(logic + 0x20);
    if (s32(mode) >= 1)
        run.put(logic + 0x14, 0x4207a0);
    uint32_t list = logic + 0x2f4;
    uint32_t count = run.get(logic + 0x2fc);
    if (count == 0) {
        run.call(0x4dbd20, list, {0});
    } else {
        uint32_t cell = list + 0xc;
        if (count > 0x20)
            cell = run.get(list + 0xc);
        uint32_t word = run.get(cell);
        word = word | 1;
        run.put(cell, word);
    }
    run.put(state + 0x12c, 0);
}

// Releases the held object through the two list helpers 0x421010 and 0x420fc0.
// Used by 0x41c5a0 and the damage tail of 0x41ce80.
void releaseHeldObject(Run &run, uint32_t state) {
    uint32_t held = run.get(state + 0x12c);
    if (held == 0)
        return;
    ActorFields releasedActorFields{run, held};
    uint32_t block = releasedActorFields.holder();
    LogicHolderFields releasedHolderFields{run, block};
    uint32_t logic = releasedHolderFields.logic();
    run.call(0x421010, logic, {0x4207a0, 1});
    run.call(0x420fc0, logic + 0x2f4, {0});
    run.put(state + 0x12c, 0);
}

// 0x41c4e0. cdecl, 3 arguments: actor, record, state. Drops the held object
// and ends the current attack state.
void dropAttack(Run &run, uint32_t actor, uint32_t state) {
    clearInputFlags(run);
    detachHeldObject(run, state);
    run.put(state + 0x3c, 0);
    run.put(state + 0x20, 1);
    uint32_t active = run.get(state + 4);
    if (active == 0)
        return;
    uint32_t animation = run.get(state + 0x124);
    run.put(state + 4, 0);
    run.call(0x4c8220, actor + 0x188, {animation});
    uint32_t flags = run.get(actor + 8);
    flags = flags | 0x80;
    run.put(actor + 8, flags);
}

uint32_t dropAttackEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    dropAttack(run, arguments[0], arguments[2]);
    return 0;
}

// Spawns a projectile through 0x4c8da0 on the scene object at [[actor+0xc]+8].
uint32_t spawnProjectile(Run &run, uint32_t actor, uint32_t x, uint32_t y, uint32_t z, uint32_t name) {
    uint32_t owner = run.get(actor + 0xc);
    uint32_t scene = run.get(owner + 8);
    return run.call(0x4c8da0, scene, {0, x, y, z, name, 0x40000});
}

// 0x41c5a0. cdecl, 3 arguments: actor, record, state. Advances the attack
// animation and fires the weapon on the frames that ask for it.
void advanceAttack(Run &run, uint32_t actor, uint32_t record, uint32_t state) {
    uint32_t clock = run.get(0x5430c4);
    uint32_t pose = actor + 0x188;
    uint32_t phase = run.call(0x4c82a0, pose, {clock});
    uint32_t finished = run.get(pose + 0x1c);
    uint32_t looping = run.get(pose + 0x14);
    if (finished != 0 && looping == 0) {
        clearInputFlags(run);
        releaseHeldObject(run, state);
        run.put(state + 0x3c, 0);
        run.put(state + 0x20, 1);
        uint32_t active = run.get(state + 4);
        if (active == 0)
            return;
        uint32_t animation = run.get(state + 0x124);
        run.put(state + 4, 0);
        run.call(0x4c8220, pose, {animation});
        uint32_t flags = run.get(actor + 8);
        flags = flags | 0x80;
        run.put(actor + 8, flags);
        return;
    }
    uint32_t pending = run.get(state + 0x1c);
    if (pending != 0)
        run.put(state + 0x20, 1);
    uint32_t flags = run.get(actor + 8);
    flags = flags | 0x80;
    run.put(actor + 8, flags);
    switch (phase) {
    case 1:
        flags = flags & 0xffffff7f;
        run.put(actor + 8, flags);
        run.put(state + 0x1c, 1);
        return;
    case 2: {
        uint32_t fired = run.get(state + 0x10);
        run.put(state + 0x1c, 1);
        if (fired != 0)
            return;
        uint32_t weapon = run.get(state + 0x30);
        run.put(state + 0x10, 1);
        if (weapon == 1) {
            uint32_t y = run.get(state + 0x58) + run.get(actor + 0x50);
            uint32_t z = run.get(actor + 0x64) - 1;
            uint32_t x = run.get(actor + 0x4c);
            uint32_t speed = 0x2bc;
            uint32_t facing = run.get(state);
            if (facing == 0) {
                x = x - run.get(state + 0x54);
                speed = 0xfffffd44;
            } else {
                x = x + run.get(state + 0x54);
            }
            uint32_t bullet = spawnProjectile(run, actor, x, y, z, 0x522dc8);
            if (bullet == 0)
                return;
            ActorFields pistolBulletFields{run, bullet};
            uint32_t bulletBlock = pistolBulletFields.holder();
            run.put(bullet + 0xd0, 0x20);
            run.put(bullet + 0xd4, 4);
            run.put(bullet + 0x148, speed);
            run.put(bullet + 0x14c, 0);
            uint32_t owner = run.get(state + 0xe8);
            run.put(bulletBlock + 0xb8, owner);
            uint32_t ammo = run.get(state + 0x70);
            if (s32(ammo) > 0)
                run.put(state + 0x70, ammo - 1);
            run.put(bullet + 0x104, 8);
            run.call(0x4c7970, bullet, {0x524130});
            return;
        }
        if (weapon == 2) {
            uint32_t y = run.get(state + 0x58) + run.get(actor + 0x50);
            uint32_t z = run.get(actor + 0x64) + 1;
            uint32_t x = run.get(actor + 0x4c);
            uint32_t speed = 0x2bc;
            uint32_t facing = run.get(state);
            if (facing == 0) {
                x = x - run.get(state + 0x54);
                speed = 0xfffffd44;
            } else {
                x = x + run.get(state + 0x54);
            }
            uint32_t bullet = spawnProjectile(run, actor, x, y, z, 0x522e00);
            if (bullet == 0)
                return;
            uint32_t ammo = run.get(state + 0x74);
            if (s32(ammo) > 0)
                run.put(state + 0x74, ammo - 1);
            uint32_t bulletFlags = run.get(bullet + 0x164);
            bulletFlags = bulletFlags | 8;
            ActorFields magicBulletFields{run, bullet};
            uint32_t bulletBlock = magicBulletFields.holder();
            run.put(bullet + 0xd0, 0x2000000);
            run.put(bullet + 0xd4, 4);
            run.put(bullet + 0x148, speed);
            run.put(bullet + 0x14c, 0);
            run.put(bullet + 0x164, bulletFlags);
            run.put(bullet + 0x104, 0x19);
            uint32_t owner = run.get(state + 0xe8);
            run.put(bulletBlock + 0xb8, owner);
            uint32_t facing2 = run.get(state);
            if (facing2 != 0)
                return;
            uint32_t motion = run.get(bullet + 0x40);
            motion = motion | 2;
            run.put(bullet + 0x40, motion);
            return;
        }
        if (weapon == 3) {
            uint32_t x = run.get(actor + 0x4c);
            uint32_t y = run.get(state + 0x58) + run.get(actor + 0x50);
            uint32_t low = run.get(state + 0x104);
            uint32_t span = run.get(state + 0x108) - low;
            uint32_t z = run.get(actor + 0x64) + 1;
            uint32_t divisor = span;
            if (divisor == 0)
                divisor = 1;
            uint32_t charge = run.get(state + 0x100) - low;
            uint32_t scaled = charge * 200;
            int32_t power = int32_t(int64_t(s32(scaled)) / int64_t(s32(divisor)));
            if (power <= 0)
                power = 0;
            if (power >= 200)
                power = 200;
            uint32_t facing = run.get(state);
            if (facing == 0) {
                x = x - run.get(state + 0x54);
                power = -power;
            } else {
                x = x + run.get(state + 0x54);
            }
            uint32_t bomb = spawnProjectile(run, actor, x, y, z, 0x522bec);
            if (bomb == 0)
                return;
            uint32_t remaining = run.get(state + 0x78);
            run.put(state + 0x78, remaining - 1);
            run.put(bomb + 0xd0, 0x20);
            run.put(bomb + 0xd4, 4);
            run.put(bomb + 0x158, uint32_t(power));
            run.put(bomb + 0x104, 0xf);
            return;
        }
        return;
    }
    case 3: {
        uint32_t input = run.get(0x537204);
        uint32_t keys = run.get(input + 4);
        uint32_t weapon = run.get(state + 0x30);
        bool pressed = false;
        if ((keys & 4) != 0) {
            pressed = true;
        } else {
            if (weapon == 1 && (keys & 0x40) != 0)
                pressed = true;
            else if (weapon == 2 && (keys & 0x80) != 0)
                pressed = true;
        }
        if (!pressed)
            return;
        if (weapon == 1) {
            uint32_t ammo = run.get(state + 0x70);
            if (s32(ammo) <= 0)
                return;
        }
        uint32_t counter = run.get(state + 0xe8);
        uint32_t block = run.get(state + 0x6c);
        run.put(state + 0xe8, counter + 1);
        run.put(state + 0x10, 0);
        run.call(0x420970, pose, {block});
        return;
    }
    case 4: {
        uint32_t input = run.get(0x537204);
        uint32_t keys = run.get(input + 8);
        if ((keys & 4) == 0 && (keys & 0x100) == 0) {
            uint32_t charge = run.get(state + 0x104);
            uint32_t current = run.get(state + 0x100);
            if (current > charge)
                charge = current;
            run.put(state + 0x100, charge);
            uint32_t sequence = run.get(state + 0x128);
            run.call(0x420a10, actor, {sequence, 0});
            return;
        }
        uint32_t step = run.get(0x53720c);
        uint32_t charge = run.get(state + 0x100);
        uint32_t limit = run.get(state + 0x108);
        charge = charge + step;
        run.put(state + 0x100, charge);
        if (charge < limit)
            return;
        uint32_t sequence = run.get(state + 0x128);
        run.put(state + 0x100, limit);
        run.call(0x420a10, actor, {sequence, 0});
        return;
    }
    case 5:
        run.put(state + 0x1c, 1);
        run.call(0x41cc60, 0, {actor, record, state});
        return;
    default:
        return;
    }
}

uint32_t advanceAttackEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    advanceAttack(run, arguments[0], arguments[1], arguments[2]);
    return 0;
}

// 0x41d6f0. cdecl, 1 argument: an object. Starts the sound named by the
// object's logic block when it changed since the last call.
void refreshSound(Run &run, uint32_t object) {
    ActorFields soundActorFields{run, object};
    uint32_t block = soundActorFields.holder();
    uint32_t sound = run.get(block + 0x168);
    uint32_t stamp = run.get(0x537210);
    uint32_t lastStamp = run.get(0x534ec0);
    if (lastStamp == stamp) {
        uint32_t lastSound = run.get(0x534ec4);
        if (sound == lastSound)
            return;
    }
    run.put(0x534ec0, stamp);
    run.put(0x534ec4, sound);
    if (sound == 0)
        return;
    uint32_t enabled = run.get(0x532c0c);
    uint32_t volume = run.get(0x532c10);
    if (enabled == 0)
        return;
    uint32_t channel = run.get(sound + 0x10);
    run.call(0x4b45f0, channel, {volume, 0, 0, 0});
}

uint32_t refreshSoundEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    refreshSound(run, arguments[0]);
    return 0;
}

// 0x41d750. cdecl, 4 arguments: actor, record (unused), mode pointer, output
// pointer. Finds the nearest item in the actor's scene list that is within 100
// rows, and returns its horizontal distance; the item goes to *output.
uint32_t nearestItem(Run &run, uint32_t actor, uint32_t facingPointer, uint32_t outputPointer) {
    uint32_t actorX = run.get(actor + 0x4c);
    uint32_t leftEdge = run.get(actor + 0x128) + actorX;
    uint32_t rightEdge = run.get(actor + 0x130) + actorX;
    uint32_t found = 0;
    uint32_t best = 0xf423f;
    uint32_t owner = run.get(actor + 0xc);
    uint32_t scene = run.get(owner + 8);
    uint32_t node = run.get(scene + 0x14);
    while (node != 0) {
        uint32_t item = run.get(node + 8);
        node = run.get(node);
        uint32_t kind = run.get(item + 0xd0);
        if (kind != 4 && kind != 0x200)
            continue;
        uint32_t itemFlags = run.get(item + 0x164);
        uint32_t margin = 0x30;
        if ((itemFlags & 0x400) != 0)
            margin = 0;
        uint32_t rowGap = run.get(item + 0x50) - run.get(actor + 0x50);
        uint32_t rowSign = uint32_t(s32(rowGap) >> 31);
        uint32_t rowDistance = (rowGap ^ rowSign) - rowSign;
        if (s32(rowDistance) >= 0x64)
            continue;
        uint32_t facing = run.get(facingPointer);
        if (facing != 0) {
            uint32_t itemX = run.get(item + 0x4c);
            uint32_t edge = run.get(item + 0x128) + itemX + margin;
            uint32_t here = run.get(actor + 0x4c);
            if (s32(edge) <= s32(here))
                continue;
            uint32_t distance = edge - rightEdge;
            if (s32(distance) >= s32(best))
                continue;
            found = item;
            best = distance;
        } else {
            uint32_t itemX = run.get(item + 0x4c);
            uint32_t edge = run.get(item + 0x130) + itemX - margin;
            uint32_t here = run.get(actor + 0x4c);
            if (s32(here) <= s32(edge))
                continue;
            uint32_t distance = leftEdge - edge;
            if (s32(distance) >= s32(best))
                continue;
            found = item;
            best = distance;
        }
    }
    if (outputPointer != 0)
        run.put(outputPointer, found);
    return best;
}

uint32_t nearestItemEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return nearestItem(run, arguments[0], arguments[2], arguments[3]);
}

// 0x41e710. cdecl, 1 argument: an actor. True when the ground probe finds
// support at the first column and none at the sampled later columns, including
// the final column. This predicate does not infer the actor's facing direction.
uint32_t hasTrailingGroundGap(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t flags = run.get(actor + 8);
    if ((flags & 0x10) != 0)
        return 0;
    uint32_t owner = run.get(actor + 0xc);
    uint32_t map = run.get(owner + 0x24);
    uint32_t first = run.get(actor + 0x118);
    uint32_t probe = run.call(0x4cd1c0, map, {actor, first});
    if (probe == 0)
        return 0;
    uint32_t column = run.get(actor + 0x118);
    uint32_t last = run.get(actor + 0x120);
    column = column + 0xc;
    if (s32(column) >= s32(last))
        return 0;
    do {
        uint32_t hit = run.call(0x4cd1c0, map, {actor, column});
        if (hit != 0)
            return 0;
        column = column + 4;
    } while (s32(column) < s32(last));
    uint32_t edge = run.call(0x4cd1c0, map, {actor, last});
    if (edge == 0)
        return 1;
    return 0;
}

// 0x41f850. cdecl, 2 arguments: a pickup record and a counter block. Maps
// record+0x4 to a collection category and increments both counter tables.
void countCollectedItem(Run &run, uint32_t record, uint32_t counters) {
    uint32_t kind = run.get(record + 4);
    int32_t slot = -1;
    switch (kind) {
    case 1:
        slot = 1;
        break;
    case 2:
    case 3:
    case 4:
    case 5:
        slot = 2;
        break;
    case 7:
    case 8:
    case 9:
    case 10:
        slot = 4;
        break;
    case 0xb:
    case 0xc:
    case 0xd:
    case 0xe:
        slot = 5;
        break;
    case 0xf:
    case 0x10:
    case 0x11:
    case 0x12:
        slot = 6;
        break;
    case 0x21:
        slot = 0;
        break;
    case 0x29:
    case 0x2a:
    case 0x2b:
    case 0x2c:
        slot = 3;
        break;
    case 0x2d:
    case 0x2e:
    case 0x2f:
    case 0x30:
        slot = 7;
        break;
    case 0x31:
    case 0x32:
    case 0x33:
    case 0x34:
        slot = 8;
        break;
    default:
        break;
    }
    if (slot < 0 || slot >= 10)
        return;
    uint32_t first = run.get(counters + uint32_t(slot) * 4 + 0x88);
    run.put(counters + uint32_t(slot) * 4 + 0x88, first + 1);
    uint32_t second = run.get(counters + uint32_t(slot) * 4 + 0xb0);
    run.put(counters + uint32_t(slot) * 4 + 0xb0, second + 1);
}

uint32_t countCollectedItemEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    countCollectedItem(run, arguments[0], arguments[1]);
    return 0;
}

// 0x41fc30. cdecl, 4 arguments. Counts the power-up timer at 0x534ea8 down by
// the elapsed time and acts on the power-up kind at 0x534eac.
uint32_t updatePowerUpTimer(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t record = arguments[1];
    uint32_t state = arguments[2];
    uint32_t elapsed = arguments[3];
    uint32_t timer = run.get(0x534ea8);
    if (elapsed < timer)
        timer = timer - elapsed;
    else
        timer = 0;
    run.put(0x534ea8, timer);
    uint32_t kind = run.get(0x534eac);
    if (timer == 0 && kind != 0) {
        run.put(0x534eb8, 1);
        run.call(0x41f990, 0, {actor, record, state, 0, 0});
        uint32_t manager = run.get(0x5371fc);
        run.call(0x4bc110, manager);
        return 0;
    }
    if (kind == 0x26b7) {
        uint32_t child = run.get(actor + 0x174);
        if (child == 0)
            return 0;
        uint32_t link = run.get(child + 0x30);
        if (link == 0)
            return 0;
        run.call(0x4c6130, link, {2, 0});
        return 0;
    }
    if (kind == 0x26bd) {
        run.call(0x420070, 0, {actor, elapsed});
        uint32_t flags = run.get(actor + 0xd4);
        flags = flags & 0xfeffffbb;
        run.put(actor + 0xd4, flags);
    }
    return 0;
}

// Plays the sound called `name` from the actor's sound table when the table is
// not muted. Lookup goes through 0x4061b0.
void playNamedSound(Run &run, uint32_t actor, uint32_t name) {
    uint32_t owner = run.get(actor + 0xc);
    uint32_t table = run.get(owner + 0x28);
    uint32_t muted = run.get(table + 0x30);
    if (muted != 0)
        return;
    uint32_t sound = run.call(0x4061b0, table, {name});
    if (sound == 0)
        return;
    uint32_t volume = run.get(0x532c10);
    run.call(0x4208e0, sound, {volume, 0, 0, 0});
}

// The same through the out-parameter lookup 0x4f6286; `slot` is a stack local
// of the caller that receives the sound.
void playNamedSoundOut(Run &run, uint32_t actor, uint32_t name, uint32_t slot) {
    uint32_t owner = run.get(actor + 0xc);
    uint32_t table = run.get(owner + 0x28);
    uint32_t muted = run.get(table + 0x30);
    if (muted != 0)
        return;
    run.put(slot, 0);
    run.call(0x4f6286, table + 0x10, {name, slot});
    uint32_t sound = run.get(slot);
    if (sound == 0)
        return;
    uint32_t volume = run.get(0x532c10);
    run.call(0x4208e0, sound, {volume, 0, 0, 0});
}

// Maps a random value to 0..3 the way the original does, with the sign
// handling of its abs-and-mask sequence. Values above 3 select nothing.
uint32_t randomChoice(uint32_t value) {
    uint32_t sign = uint32_t(s32(value) >> 31);
    uint32_t magnitude = (value ^ sign) - sign;
    uint32_t masked = magnitude & 3;
    return (masked ^ sign) - sign;
}

// The hit reaction shared by the item kinds 0x10, 0x40 and 0x1000000 in
// 0x41ce80. Returns the damage to apply.
uint32_t hitReaction(Run &run, uint32_t actor, uint32_t block, uint32_t target) {
    uint32_t slot = run.automatic(-4);
    run.put(block + 0x130, 0x352);
    run.put(actor + 0x48, 0x21);
    run.put(actor + 0x44, 0);
    playNamedSound(run, actor, 0x524800);
    uint32_t choice = randomChoice(run.call(0x4a3050, 0));
    switch (choice) {
    case 0:
        playNamedSound(run, actor, 0x524870);
        break;
    case 1:
        playNamedSound(run, actor, 0x524864);
        break;
    case 2:
        playNamedSound(run, actor, 0x524858);
        break;
    case 3:
        playNamedSoundOut(run, actor, 0x52484c, slot);
        break;
    default:
        break;
    }
    choice = randomChoice(run.call(0x4a3050, 0));
    switch (choice) {
    case 0:
        playNamedSoundOut(run, actor, 0x52483c, slot);
        break;
    case 1:
        playNamedSoundOut(run, actor, 0x52482c, slot);
        break;
    case 2:
        playNamedSoundOut(run, actor, 0x52481c, slot);
        break;
    case 3:
        playNamedSoundOut(run, actor, 0x52480c, slot);
        break;
    default:
        break;
    }
    uint32_t motion = run.get(actor + 0xd4);
    motion = motion & 0xfefffffb;
    run.put(actor + 0xd4, motion);
    uint32_t damage = run.get(target + 0x104);
    if (damage == 0)
        damage = 1;
    uint32_t targetFlags = run.get(target + 0x164);
    if ((targetFlags & 0x20) != 0) {
        ActorFields hitTargetFields{run, target};
        uint32_t targetBlock = hitTargetFields.holder();
        LogicHolderFields hitTargetHolderFields{run, targetBlock};
        uint32_t logic = hitTargetHolderFields.logic();
        run.vcall(logic, 0x2c);
        return damage;
    }
    uint32_t targetKind = run.get(target + 0xd0);
    if (targetKind != 0x1000000) {
        uint32_t flags = run.get(target + 8);
        flags = flags | 0x10000;
        run.put(target + 8, flags);
    }
    return damage;
}

// The pickup reaction: marks the item as consumed.
void consumeItem(Run &run, uint32_t target) {
    uint32_t flags = run.get(target + 8);
    flags = flags | 0x10000;
    run.put(target + 8, flags);
}

// The damage tail of 0x41ce80 (label 0x41d46a). Returns 1.
uint32_t applyDamage(Run &run, uint32_t actor, uint32_t block, uint32_t state, uint32_t target, uint32_t damage) {
    if (s32(damage) <= 0)
        return 1;
    uint32_t health = run.get(actor + 0x10c);
    health = health - damage;
    run.put(actor + 0x10c, health);
    if (s32(health) <= 0) {
        run.call(0x417b00, 0, {actor, block, state, 1});
        return 1;
    }
    uint32_t phase = run.get(block + 0x1c);
    if (phase == 0x1f)
        return 1;
    clearInputFlags(run);
    releaseHeldObject(run, state);
    run.put(state + 0x3c, 0);
    run.put(state + 0x20, 1);
    uint32_t active = run.get(state + 4);
    if (active != 0) {
        uint32_t animation = run.get(state + 0x124);
        run.put(state + 4, 0);
        run.call(0x420a10, actor, {animation, 0});
        uint32_t flags = run.get(actor + 8);
        flags = flags | 0x80;
        run.put(actor + 8, flags);
    }
    run.put(block + 0x1c, 0x1f);
    uint32_t pick = run.call(0x4a3050, 0);
    int32_t remainder = s32(pick) % 100;
    uint32_t reaction = 0x5247e0;
    if (remainder < 0x32)
        reaction = 0x5247f0;
    run.call(0x4c79e0, actor, {reaction, 0});
    uint32_t x = run.get(actor + 0x4c);
    uint32_t y = run.get(actor + 0x50);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    uint32_t form = run.get(actor + 0xcc);
    uint32_t targetY = y;
    if (form == 1 || form == 5 || form == 2) {
        uint32_t targetX = run.get(target + 0x4c);
        if (s32(x) > s32(targetX)) {
            run.put(actor + 0x148, 0xc8);
            x = x - 4;
        } else {
            run.put(actor + 0x148, 0xffffff38);
            x = x + 4;
        }
    }
    uint32_t reach = run.get(target + 0x138);
    if (reach != 0x80000000) {
        uint32_t sum = run.get(target + 0x13c) + run.get(target + 0x144);
        uint32_t sign = uint32_t(s32(sum) >> 31);
        uint32_t rounded = sum - sign;
        int32_t half = s32(rounded) >> 1;
        uint32_t middle = uint32_t(half) + run.get(target + 0x50);
        uint32_t lower = run.get(actor + 0x12c) + y;
        if (!(s32(middle) > s32(lower)))
            middle = lower;
        uint32_t upper = run.get(actor + 0x134) + y;
        if (!(s32(middle) < s32(upper)))
            middle = upper;
        targetY = middle;
    }
    uint32_t depth = run.get(actor + 0x64);
    uint32_t firstRandom = run.call(0x4a3050, 0);
    int32_t jitterY = s32(firstRandom) % 9;
    jitterY = jitterY - 4;
    uint32_t secondRandom = run.call(0x4a3050, 0);
    int32_t jitterX = s32(secondRandom) % 9;
    jitterX = jitterX - 4;
    uint32_t spawnY = targetY + uint32_t(jitterY);
    uint32_t spawnX = x + uint32_t(jitterX);
    uint32_t owner = run.get(actor + 0xc);
    run.call(0x461a00, 0, {owner, spawnX, spawnY, depth + 1, 1, actor});
    uint32_t after = run.get(actor + 0xcc);
    if (after == 4 || after == 3 || after == 8) {
        uint32_t flags = run.get(actor + 8);
        uint32_t next = 4;
        if ((flags & 0x10) != 0)
            next = 1;
        run.put(actor + 0xcc, next);
        return 1;
    }
    run.put(actor + 0xcc, 1);
    return 1;
}

// 0x41ce80. cdecl, 1 argument: an actor. Reacts to the item it touches.
uint32_t reactToTouchedItem(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    ActorFields contactActorFields{run, actor};
    uint32_t block = contactActorFields.holder();
    uint32_t target = run.get(actor + 0x74);
    uint32_t state = run.get(block + 0x14);
    if (target == 0)
        return 0;
    uint32_t kind = run.get(target + 0xd0);
    uint32_t damage = 0;
    if (kind > 0x10) {
        if (kind <= 0x100) {
            if (kind == 0x100) {
                run.call(0x41ee60, 0, {actor, block, state, target});
            } else if (kind == 0x40) {
                uint32_t value = run.get(target + 0xfc);
                if (value == 0x26bf) {
                    uint32_t manager = run.get(0x5371fc);
                    uint32_t boss = run.get(manager + 0x2c);
                    if (boss != 0) {
                        playNamedSound(run, actor, 0x524800);
                        run.put(boss + 0x764, 0x7d0);
                    }
                    consumeItem(run, target);
                } else {
                    damage = hitReaction(run, actor, block, target);
                }
            }
        } else if (kind > 0x40000) {
            if (kind <= 0x200000) {
                if (kind == 0x200000) {
                    uint32_t gain = run.get(target + 0xfc);
                    uint32_t health = run.get(actor + 0x10c) + gain;
                    run.put(actor + 0x10c, health);
                    if (s32(health) > 0x64)
                        run.put(actor + 0x10c, 0x64);
                    refreshSound(run, target);
                    consumeItem(run, target);
                } else if (kind == 0x100000) {
                    uint32_t gain = run.get(target + 0xfc);
                    uint32_t lives = run.get(state + 0x74) + gain;
                    run.put(state + 0x74, lives);
                    if (s32(lives) > 0x63)
                        run.put(state + 0x74, 0x63);
                    refreshSound(run, target);
                    consumeItem(run, target);
                }
            } else if (kind == 0x800000) {
                uint32_t gain = run.get(target + 0xfc);
                uint32_t ammo = run.get(state + 0x70) + gain;
                run.put(state + 0x70, ammo);
                if (s32(ammo) > 0x63)
                    run.put(state + 0x70, 0x63);
                refreshSound(run, target);
                consumeItem(run, target);
            } else if (kind == 0x1000000) {
                damage = hitReaction(run, actor, block, target);
            }
        } else if (kind == 0x40000) {
            uint32_t gain = run.get(target + 0xfc);
            uint32_t score = run.get(actor + 0xf8) + gain;
            run.put(actor + 0xf8, score);
            refreshSound(run, target);
            countCollectedItem(run, target, state);
            uint32_t seen = run.call(0x473ae0, 0, {target});
            if (seen == 0)
                consumeItem(run, target);
        } else if (kind == 0x10000) {
            uint32_t value = run.get(target + 0xfc);
            if (s32(value) > 0x64) {
                uint32_t bonus = run.get(target + 0x108);
                if (s32(bonus) > 0)
                    value = bonus;
                run.call(0x41f990, 0, {actor, block, state, 0x26bc, value});
                refreshSound(run, target);
                consumeItem(run, target);
            } else {
                uint32_t health = run.get(actor + 0x10c);
                if (s32(health) < 0x64) {
                    health = value + health;
                    run.put(actor + 0x10c, health);
                    if (s32(health) > 0x64)
                        run.put(actor + 0x10c, 0x64);
                    refreshSound(run, target);
                    consumeItem(run, target);
                }
            }
        }
    } else if (kind == 0x10) {
        damage = hitReaction(run, actor, block, target);
    } else if (kind == 4) {
        uint32_t targetFlags = run.get(target + 0x164);
        uint32_t held = run.get(state + 0x12c);
        if ((targetFlags & 0x10) == 0 && held != target) {
            run.put(block + 0x130, 0x352);
            run.put(actor + 0x48, 0x21);
            run.put(actor + 0x44, 0);
            uint32_t choice = randomChoice(run.call(0x4a3050, 0));
            switch (choice) {
            case 0:
                playNamedSound(run, actor, 0x524870);
                break;
            case 1:
                playNamedSound(run, actor, 0x524864);
                break;
            case 2:
                playNamedSound(run, actor, 0x524858);
                break;
            case 3:
                playNamedSound(run, actor, 0x52484c);
                break;
            default:
                break;
            }
            choice = randomChoice(run.call(0x4a3050, 0));
            switch (choice) {
            case 0:
                playNamedSound(run, actor, 0x52483c);
                break;
            case 1:
                playNamedSound(run, actor, 0x52482c);
                break;
            case 2:
                playNamedSound(run, actor, 0x52481c);
                break;
            case 3:
                playNamedSound(run, actor, 0x52480c);
                break;
            default:
                break;
            }
            uint32_t motion = run.get(actor + 0xd4);
            motion = motion & 0xfffffffb;
            run.put(actor + 0xd4, motion);
            damage = run.get(target + 0x104);
            if (damage == 0)
                damage = 1;
        }
    }
    return applyDamage(run, actor, block, state, target, damage);
}

// Sets the weapon-swipe hitbox; the damage values depend on the power-up kind
// at 0x534eac and the cheat flag at 0x53725c.
bool isSwipePowerUp(uint32_t kind) {
    return kind == 0x26b8 || kind == 0x26b9 || kind == 0x26ba || kind == 0x26bb;
}

void setMeleeBox(Run &run, uint32_t actor, int32_t left, int32_t top, int32_t right, int32_t bottom) {
    run.put(actor + 0x138, uint32_t(left));
    run.put(actor + 0x13c, uint32_t(top));
    run.put(actor + 0x140, uint32_t(right));
    run.put(actor + 0x144, uint32_t(bottom));
}

// 0x41de90. cdecl, 4 arguments: actor, record, state, attack kind. Starts an
// attack animation and fills in the state record for it.
void startAttack(Run &run, uint32_t actor, uint32_t record, uint32_t state, uint32_t mode) {
    (void)record;
    uint32_t counter = run.get(state + 0xe8);
    counter = counter + 1;
    run.put(state + 0xe8, counter);
    run.put(state + 4, 1);
    run.put(state + 0x1c, 0);
    run.put(state + 0x20, 0);
    uint32_t animation = run.get(actor + 0x190);
    run.put(state + 0x120, 0x3a98);
    run.put(state + 0x124, animation);
    run.put(state + 0x3c, mode);
    switch (mode) {
    case 0xb: {
        uint32_t slot = run.automatic(0xc);
        run.put(state + 4, 0);
        run.put(state + 0x3c, 0);
        run.put(slot, 0);
        uint32_t distance = nearestItem(run, actor, state, slot);
        if (s32(distance) >= 0x40)
            break;
        uint32_t item = run.get(slot);
        if (item == 0)
            break;
        uint32_t itemFlags = run.get(item + 0x164);
        if ((itemFlags & 1) == 0)
            break;
        uint32_t reachable = run.call(0x41e660, 0, {actor, record, state, item});
        if (reachable == 0)
            break;
        uint32_t grabbed = run.get(slot);
        run.call(0x41dc50, 0, {actor, record, state, grabbed});
        break;
    }
    case 7: {
        run.call(0x4c79e0, actor, {0x524abc, 0});
        setMeleeBox(run, actor, 0x1e, 0x13, 0x69, 0x25);
        run.put(actor + 0x104, 2);
        uint32_t kind = run.get(0x534eac);
        if (isSwipePowerUp(kind)) {
            run.call(0x4c79e0, actor, {0x524aa4, 0});
            kind = run.get(0x534eac);
        }
        if (kind == 0x26bc)
            run.put(actor + 0x104, 4);
        uint32_t cheat = run.get(0x53725c);
        if (cheat != 0)
            run.put(actor + 0x104, 0xa);
        run.put(state + 0x14, 0);
        run.put(state + 0x54, 0x5f);
        run.put(state + 0x58, 0x19);
        break;
    }
    case 1: {
        run.call(0x4c79e0, actor, {0x524a98, 0});
        setMeleeBox(run, actor, 0x1e, -2, 0x70, 0x13);
        run.put(actor + 0x104, 5);
        uint32_t kind = run.get(0x534eac);
        if (isSwipePowerUp(kind)) {
            run.call(0x4c79e0, actor, {0x524a84, 0});
            kind = run.get(0x534eac);
        }
        if (kind == 0x26bc)
            run.put(actor + 0x104, 0xa);
        uint32_t cheat = run.get(0x53725c);
        if (cheat != 0)
            run.put(actor + 0x104, 0x14);
        run.put(state + 0x14, 0);
        run.put(state + 0x54, 0x5f);
        run.put(state + 0x58, 0xf);
        break;
    }
    case 8: {
        run.call(0x4c79e0, actor, {0x524a74, 0});
        setMeleeBox(run, actor, 0x1e, -2, 0x70, 0x13);
        run.put(actor + 0x104, 5);
        uint32_t kind = run.get(0x534eac);
        if (isSwipePowerUp(kind)) {
            run.call(0x4c79e0, actor, {0x524a5c, 0});
            kind = run.get(0x534eac);
        }
        if (kind == 0x26bc)
            run.put(actor + 0x104, 0xa);
        uint32_t cheat = run.get(0x53725c);
        if (cheat != 0)
            run.put(actor + 0x104, 0x14);
        run.put(state + 0x14, 0);
        run.put(state + 0x54, 0x4b);
        run.put(state + 0x58, 0xa);
        break;
    }
    case 5: {
        uint32_t ammo = run.get(state + 0x70);
        uint32_t name = 0x524a30;
        if (s32(ammo) > 0) {
            uint32_t pick = run.call(0x4a3050, 0);
            int32_t remainder = s32(pick) % 100;
            if (remainder < 0x1e)
                run.call(0x48c8a0, 0, {0x524a50, 0});
            name = 0x524a44;
        }
        run.call(0x4c79e0, actor, {name, 0});
        run.put(state + 0x10, 0);
        run.put(state + 0x54, 0x47);
        run.put(state + 0x58, 0xffffffeb);
        run.put(state + 0x6c, 2);
        run.put(state + 0x14, 0);
        break;
    }
    case 0xe: {
        uint32_t ammo = run.get(state + 0x70);
        uint32_t name = 0x524a08;
        if (s32(ammo) > 0)
            name = 0x524a20;
        run.call(0x4c79e0, actor, {name, 0});
        run.put(state + 0x10, 0);
        run.put(state + 0x54, 0x47);
        run.put(state + 0x58, 0x17);
        run.put(state + 0x6c, 2);
        run.put(state + 0x14, 0);
        break;
    }
    case 9: {
        uint32_t ammo = run.get(state + 0x70);
        uint32_t name = 0x5249e0;
        if (s32(ammo) > 0)
            name = 0x5249f8;
        run.call(0x4c79e0, actor, {name, 0});
        run.put(state + 0x10, 0);
        run.put(state + 0x54, 0x47);
        run.put(state + 0x58, 0xffffffeb);
        run.put(state + 0x6c, 1);
        run.put(state + 0x14, 0);
        break;
    }
    case 0xf: {
        uint32_t magic = run.get(state + 0x74);
        uint32_t name = 0x5249bc;
        if (s32(magic) > 0)
            name = 0x5249d0;
        run.call(0x4c79e0, actor, {name, 0});
        run.put(state + 0x10, 0);
        run.put(state + 0x54, 0x44);
        run.put(state + 0x58, 0x18);
        run.put(state + 0x6c, 0);
        run.put(state + 0x14, 0);
        break;
    }
    case 6: {
        uint32_t magic = run.get(state + 0x74);
        uint32_t name = 0x5249a0;
        if (s32(magic) > 0)
            name = 0x5249b0;
        run.call(0x4c79e0, actor, {name, 0});
        run.put(state + 0x10, 0);
        run.put(state + 0x54, 0x36);
        run.put(state + 0x58, 0xfffffff8);
        run.put(state + 0x6c, 1);
        run.put(state + 0x14, 0);
        break;
    }
    case 0xa: {
        uint32_t magic = run.get(state + 0x74);
        uint32_t name = 0x52497c;
        if (s32(magic) > 0)
            name = 0x524990;
        run.call(0x4c79e0, actor, {name, 0});
        run.put(state + 0x10, 0);
        run.put(state + 0x54, 0x4b);
        run.put(state + 0x58, 0xfffffff8);
        run.put(state + 0x6c, 1);
        run.put(state + 0x14, 0);
        break;
    }
    case 0x10: {
        uint32_t slot = run.automatic(0xc);
        uint32_t dynamite = run.get(state + 0x78);
        uint32_t name = 0x524940;
        if (s32(dynamite) > 0) {
            uint32_t pick = run.call(0x4a3050, 0);
            int32_t remainder = s32(pick) % 100;
            if (remainder < 0x23)
                run.call(0x48c8a0, 0, {0x524970, 0});
            name = 0x524958;
        }
        run.call(0x4c79e0, actor, {name, 0});
        run.put(state + 0x10, 0);
        run.put(state + 0x54, 0x3c);
        run.put(state + 0x58, 0xc);
        run.put(state + 0x6c, 1);
        run.put(state + 0x14, 0);
        run.put(state + 0x100, 0);
        run.put(state + 0x104, 0x32);
        run.put(state + 0x108, 0x7d0);
        uint32_t owner = run.get(actor + 0xc);
        uint32_t table = run.get(owner + 0x2c);
        run.put(slot, 0);
        run.call(0x4f6286, table + 0x10, {0x524928, slot});
        uint32_t sound = run.get(slot);
        run.put(state + 0x1c, 1);
        run.put(state + 0x128, sound);
        break;
    }
    case 0xc: {
        uint32_t slot = run.automatic(0xc);
        uint32_t dynamite = run.get(state + 0x78);
        uint32_t name = 0x524900;
        if (s32(dynamite) > 0) {
            uint32_t pick = run.call(0x4a3050, 0);
            int32_t remainder = s32(pick) % 100;
            if (remainder < 0x19)
                run.call(0x48c8a0, 0, {0x524970, 0});
            name = 0x524914;
        }
        run.call(0x4c79e0, actor, {name, 0});
        run.put(state + 0x10, 0);
        run.put(state + 0x54, 0x3c);
        run.put(state + 0x58, 0xfffffff8);
        run.put(state + 0x6c, 1);
        run.put(state + 0x14, 0);
        run.put(state + 0x100, 0);
        run.put(state + 0x104, 0x32);
        run.put(state + 0x108, 0x7d0);
        uint32_t owner = run.get(actor + 0xc);
        uint32_t table = run.get(owner + 0x2c);
        run.put(slot, 0);
        run.call(0x4f6286, table + 0x10, {0x5248ec, slot});
        uint32_t sound = run.get(slot);
        run.put(state + 0x1c, 1);
        run.put(state + 0x128, sound);
        break;
    }
    case 0x12: {
        uint32_t dynamite = run.get(state + 0x78);
        uint32_t name = 0x5248c0;
        if (s32(dynamite) > 0)
            name = 0x5248d8;
        run.call(0x4c79e0, actor, {name, 0});
        run.put(state + 0x10, 0);
        run.put(state + 0x54, 0x3c);
        run.put(state + 0x58, 0xfffffff0);
        run.put(state + 0x6c, 1);
        run.put(state + 0x14, 0);
        run.put(state + 0x100, 0x1f4);
        run.put(state + 0x104, 0x32);
        run.put(state + 0x108, 0x7d0);
        break;
    }
    case 4: {
        run.call(0x4c79e0, actor, {0x5248b0, 0});
        setMeleeBox(run, actor, 0, -0x13, 0x38, 0x13);
        run.put(actor + 0x104, 5);
        uint32_t kind = run.get(0x534eac);
        if (kind == 0x26bc)
            run.put(actor + 0x104, 0xa);
        uint32_t cheat = run.get(0x53725c);
        if (cheat != 0)
            run.put(actor + 0x104, 0x14);
        run.put(state + 0x14, 1);
        break;
    }
    case 3:
    case 0xd: {
        uint32_t name = 0x5248a4;
        if (mode == 0xd)
            name = 0x524898;
        run.call(0x4c79e0, actor, {name, 0});
        setMeleeBox(run, actor, 0, -2, 0x38, 0x13);
        run.put(actor + 0x104, 5);
        uint32_t kind = run.get(0x534eac);
        if (kind == 0x26bc)
            run.put(actor + 0x104, 0xa);
        uint32_t cheat = run.get(0x53725c);
        if (cheat != 0)
            run.put(actor + 0x104, 0x14);
        run.put(state + 0x14, 0);
        break;
    }
    default: {
        clearInputFlags(run);
        detachHeldObject(run, state);
        run.put(state + 0x3c, 0);
        run.put(state + 0x20, 1);
        uint32_t active = run.get(state + 4);
        if (active != 0) {
            uint32_t sequence = run.get(state + 0x124);
            run.put(state + 4, 0);
            run.call(0x4c8220, actor + 0x188, {sequence});
            uint32_t flags = run.get(actor + 8);
            flags = flags | 0x80;
            run.put(actor + 8, flags);
        }
        break;
    }
    }
    uint32_t facing = run.get(state);
    if (facing == 0) {
        uint32_t left = run.get(actor + 0x138);
        if (left != 0x80000000) {
            uint32_t right = run.get(actor + 0x140);
            run.put(actor + 0x138, uint32_t(-s32(right)));
            run.put(actor + 0x140, uint32_t(-s32(left)));
        }
    }
    uint32_t swipeCheat = run.get(0x537218);
    if (swipeCheat != 0) {
        run.put(actor + 0x104, 100);
        return;
    }
    uint32_t noDamage = run.get(0x537228);
    if (noDamage != 0)
        run.put(actor + 0x104, 0);
}

uint32_t startAttackEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    startAttack(run, arguments[0], arguments[1], arguments[2], arguments[3]);
    return 0;
}

// 0x41d850. cdecl, 3 arguments: actor, record, state. Chooses and starts the
// attack the held keys ask for. Returns whether an attack is running.
uint32_t selectAttackFromInput(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t record = arguments[1];
    uint32_t state = arguments[2];
    LogicHolderFields attackRecordFields{run, record};
    uint32_t running = run.get(state + 4);
    if (running != 0)
        return 0;
    uint32_t input = run.get(0x537204);
    uint32_t keys = run.get(input + 4);
    if ((keys & 2) != 0) {
        uint32_t form = attackRecordFields.state();
        if (form == 0x19 || form == 4) {
            startAttack(run, actor, record, state, 8);
            return run.get(state + 4);
        }
        if (form == 0x1a) {
            startAttack(run, actor, record, state, 7);
            return run.get(state + 4);
        }
        uint32_t power = run.get(0x534eac);
        if (isSwipePowerUp(power)) {
            startAttack(run, actor, record, state, 1);
            return run.get(state + 4);
        }
        uint32_t slot = run.automatic(8);
        run.put(slot, 0);
        uint32_t distance = nearestItem(run, actor, state, slot);
        uint32_t pick = run.call(0x4207b0, 0, {0, 3});
        uint32_t item = run.get(slot);
        if (s32(distance) > 0x96) {
            item = 0;
            run.put(slot, 0);
        }
        if (pick == 0 || pick == 3) {
            pick = run.call(0x4207b0, 0, {0, 3});
            item = run.get(slot);
        }
        uint32_t held = run.get(run.get(0x537204) + 8);
        if ((held & 0x4000000) != 0 && (held & 0x3000000) == 0) {
            if (s32(distance) >= 0x40)
                return run.get(state + 4);
            if (item == 0)
                return run.get(state + 4);
            uint32_t itemFlags = run.get(item + 0x164);
            if ((itemFlags & 1) == 0)
                return run.get(state + 4);
            uint32_t reachable = run.call(0x41e660, 0, {actor, record, state, item});
            if (reachable == 0)
                return run.get(state + 4);
            uint32_t grabbed = run.get(slot);
            run.call(0x41dc50, 0, {actor, record, state, grabbed});
            return run.get(state + 4);
        }
        bool lowItem = true;
        if (item != 0) {
            uint32_t itemFlags = run.get(item + 0x164);
            if ((itemFlags & 0x400) == 0)
                lowItem = false;
        }
        if (lowItem) {
            if (s32(distance) < 0x20)
                pick = run.call(0x4207b0, 0, {1, 3});
            else if (s32(distance) < 0x96)
                pick = 0;
        } else {
            pick = 0;
        }
        switch (pick) {
        case 0:
            startAttack(run, actor, record, state, 1);
            break;
        case 1:
            startAttack(run, actor, record, state, 4);
            break;
        case 2:
            startAttack(run, actor, record, state, 3);
            break;
        case 3:
            startAttack(run, actor, record, state, 0xd);
            break;
        default:
            break;
        }
        return run.get(state + 4);
    }
    if ((keys & 4) != 0) {
        uint32_t weapon = run.get(state + 0x30);
        uint32_t form = attackRecordFields.state();
        uint32_t mode;
        if (weapon == 1) {
            if (form == 4 || form == 0x19)
                mode = 9;
            else if (form == 0x1a)
                mode = 0xe;
            else
                mode = 5;
        } else if (weapon == 2) {
            if (form == 4 || form == 0x19)
                mode = 0xa;
            else if (form == 0x1a)
                mode = 0xf;
            else
                mode = 6;
        } else if (weapon == 3) {
            if (form == 4 || form == 0x19)
                mode = 0x12;
            else if (form == 0x1a)
                mode = 0x10;
            else
                mode = 0xc;
        } else {
            return run.get(state + 4);
        }
        startAttack(run, actor, record, state, mode);
        return run.get(state + 4);
    }
    if ((keys & 0x40) != 0) {
        run.put(state + 0x30, 1);
        run.call(0x41dd80, 0, {actor, record, state});
        return run.get(state + 4);
    }
    if ((keys & 0x80) != 0) {
        run.put(state + 0x30, 2);
        run.call(0x41dd80, 0, {actor, record, state});
        return run.get(state + 4);
    }
    if ((keys & 0x100) != 0) {
        run.put(state + 0x30, 3);
        run.call(0x41dd80, 0, {actor, record, state});
        return run.get(state + 4);
    }
    if ((keys & 0x20) == 0)
        return 0;
    uint32_t form = run.get(actor + 0xcc);
    if (form != 1)
        return 0;
    uint32_t slot = run.automatic(4);
    run.put(slot, 0);
    uint32_t distance = nearestItem(run, actor, state, slot);
    if (s32(distance) >= 0x40)
        return 0;
    uint32_t item = run.get(slot);
    if (item == 0)
        return 0;
    uint32_t itemFlags = run.get(item + 0x164);
    if ((itemFlags & 1) == 0)
        return 0;
    uint32_t reachable = run.call(0x41e660, 0, {actor, record, state, item});
    if (reachable == 0)
        return 0;
    uint32_t grabbed = run.get(slot);
    run.call(0x41dc50, 0, {actor, record, state, grabbed});
    return 1;
}

// 0x41b630. cdecl, 3 arguments: actor, record, state. Per-frame update of the
// player's jump and fall: counts down the jump timer, integrates the vertical
// motion through the physics object at 0x534db8, moves the actor and then
// hands over to the attack update or to the landing.
void updateJumpAndFall(Run &run, uint32_t actor, uint32_t record, uint32_t state) {
    LogicHolderFields motionRecordFields{run, record};
    uint32_t input = run.get(0x537204);
    uint32_t y = run.get(actor + 0x50);
    uint32_t x = run.get(actor + 0x4c);
    uint32_t inputFlags = run.get8(input + 8);
    if ((inputFlags & 1) != 0) {
        uint32_t timer = run.get(state + 0x118);
        if (timer != 0) {
            uint32_t clock = run.get(0x5430c4);
            if (clock < timer)
                run.put(state + 0x118, timer - clock);
            else
                run.put(state + 0x118, 0);
            uint32_t factorAddress = 0x50bb08;
            uint32_t holdBaseAddress = 0x41b6a4;
            uint32_t boost = run.get(0x537220);
            if (boost != 0) {
                run.put(actor + 0x14c, 0xfffffd12);
            } else {
                uint32_t power = run.get(0x534eac);
                if (power == 0x26bc) {
                    run.put(actor + 0x14c, 0xfffffe0c);
                    holdBaseAddress = 0x41b6de;
                } else {
                    uint32_t mode = run.get(state + 0x114);
                    if (mode == 0) {
                        run.put(actor + 0x14c, 0xfffffe0c);
                        factorAddress = 0x50bb0c;
                        holdBaseAddress = 0x41b714;
                    } else {
                        run.put(actor + 0x14c, 0xfffffe57);
                        factorAddress = 0x50bb10;
                        holdBaseAddress = 0x41b750;
                    }
                }
            }
            uint32_t left = run.get(state + 0x118);
            double base = double(s32(run.get(state + 0x60)));
            // Keep unsigned subtraction before binary64 conversion, including wrap.
            uint32_t span = run.get(holdBaseAddress) - left;
            double spanValue = double(span);
            double factor = double(run.getf(factorAddress));
            double product = spanValue * factor;
            double lifted = base - product;
            uint32_t reach = truncateToInt(lifted);
            uint32_t ceiling = run.get(state + 0x64);
            if (!(s32(ceiling) >= s32(reach)))
                reach = ceiling;
            run.put(state + 0x64, reach);
            double stored = double(s32(run.get(state + 0x64)));
            uint32_t originHigh = run.get(0x534dfc);
            uint32_t originLow = run.get(0x534df8);
            run.call(0x420dd0, 0x534db8, {originLow, originHigh, lowWord(stored), highWord(stored), 0, 0});
        }
    } else {
        run.put(state + 0x118, 0);
    }
    uint32_t held = run.get(run.get(0x537204) + 8);
    if ((held & 0x2000000) != 0) {
        uint32_t facing = run.get(state);
        if (facing == 0) {
            uint32_t motion = run.get(actor + 0x40);
            motion = motion & 0xfffffffd;
            run.put(actor + 0x40, motion);
            run.call(0x4060b0, actor);
            run.put(state, 1);
            run.put(state + 0x114, 0x5dc);
        }
        run.put(actor + 0x148, run.get(0x41b7e6));
    } else if ((held & 0x1000000) != 0) {
        uint32_t facing = run.get(state);
        if (facing != 0) {
            uint32_t motion = run.get(actor + 0x40);
            motion = motion | 2;
            run.put(actor + 0x40, motion);
            run.call(0x4060b0, actor);
            run.put(state, 0);
            run.put(state + 0x114, 0x5dc);
        }
        run.put(actor + 0x148, run.get(0x41b818));
    } else {
        run.put(actor + 0x148, 0);
    }
    uint32_t drift = run.get(state + 0x84);
    uint32_t velocity = run.get(actor + 0x148) + drift;
    run.put(actor + 0x148, velocity);
    uint32_t frame = run.get(0x53720c);
    double velocityValue = double(s32(velocity));
    run.putd(0x534de0, velocityValue);
    double frameValue = double(frame);
    double frameScale = run.getd(0x50bab0);
    double step = frameValue * frameScale;
    run.call(0x403b40, 0x534db8, {lowWord(step), highWord(step)});
    uint32_t smoothing = run.get(0x534e58);
    uint32_t shiftX = 0;
    uint32_t shiftY = 0;
    if (smoothing == 0) {
        double positionX = run.getd(0x534e40);
        uint32_t wholeX = truncateToInt(positionX);
        double wholeXValue = double(s32(wholeX));
        double fractionX = positionX - wholeXValue;
        double carryX = run.getd(0x534e60);
        double totalX = fractionX + carryX;
        double offsetBaseX = run.getd(0x534e40);
        double probeX = totalX + offsetBaseX;
        shiftX = truncateToInt(probeX);
        run.put(0x544e8c, shiftX);
        uint32_t wholeTotalX = truncateToInt(totalX);
        double wholeTotalValueX = double(s32(wholeTotalX));
        double remainderX = totalX - wholeTotalValueX;
        run.putd(0x534e60, remainderX);
    }
    x = x + shiftX;
    if (smoothing == 0) {
        double positionY = run.getd(0x534e48);
        uint32_t wholeY = truncateToInt(positionY);
        double wholeYValue = double(s32(wholeY));
        double fractionY = positionY - wholeYValue;
        double carryY = run.getd(0x534e68);
        double totalY = fractionY + carryY;
        double offsetBaseY = run.getd(0x534e48);
        double probeY = totalY + offsetBaseY;
        shiftY = truncateToInt(probeY);
        run.put(0x544e88, shiftY);
        uint32_t wholeTotalY = truncateToInt(totalY);
        double wholeTotalValueY = double(s32(wholeTotalY));
        double remainderY = totalY - wholeTotalValueY;
        run.putd(0x534e68, remainderY);
    }
    y = y + shiftY;
    uint32_t distance = run.get(state + 0x10c);
    uint32_t tick = run.get(0x53720c);
    run.put(state + 0x10c, distance + tick);
    double speed = run.getd(0x534de8);
    double zero = run.getd(0x50ba88);
    if (speed >= zero) {
        double target = double(s32(run.get(state + 0x64)));
        double rate = run.getd(0x534dd0);
        double oldSpeed = run.getd(0x534de8);
        double newSpeed = oldSpeed;
        if (rate < zero || rate > zero) {
            double origin = run.getd(0x534e00);
            double delta = target - origin;
            double scaled = delta * rate;
            double square = oldSpeed * oldSpeed;
            double constant = run.getd(0x50bac8);
            double scaledAgain = scaled * constant;
            double radicand = square - scaledAgain;
            if (zero > radicand)
                radicand = zero;
            double root = std::sqrt(radicand);
            if (!(oldSpeed > zero))
                root = -root;
            newSpeed = root;
        }
        double origin2 = run.getd(0x534e00);
        double gap = origin2 - target;
        run.putd(0x534de8, newSpeed);
        double drag = run.getd(0x534e48);
        double newDrag = drag - gap;
        run.putd(0x534e00, target);
        run.putd(0x534e48, newDrag);
        y = run.get(state + 0x64);
    }
    uint32_t drawFlags = 0;
    uint32_t input2 = run.get(0x537204);
    uint32_t held2 = run.get(input2 + 8);
    if ((held2 & 0x4000000) != 0)
        drawFlags = 0x11;
    uint32_t ceiling = run.get(state + 0x64);
    uint32_t oldY = run.get(actor + 0x50);
    if (!(s32(y) >= s32(ceiling)))
        y = ceiling;
    uint32_t owner = run.get(actor + 0xc);
    uint32_t grid = run.get(owner + 0x24);
    run.call(0x4cbb60, grid, {actor, x, y, drawFlags});
    uint32_t newY = run.get(actor + 0x50);
    uint32_t travelled = run.get(state + 0x5c);
    travelled = travelled + (oldY - newY);
    run.put(state + 0x5c, travelled);
    uint32_t form = run.get(actor + 0xcc);
    if (form == 4) {
        uint32_t kind = run.get(state + 0x3c);
        if (kind == 8 || kind == 9 || kind == 0xa || kind == 0x12) {
            uint32_t sounds = run.get(run.get(actor + 0xc) + 0x2c);
            uint32_t found = run.call(0x4061b0, sounds, {0x5246dc});
            run.put(state + 0x124, found);
        } else {
            dropAttack(run, actor, state);
            run.call(0x4c79e0, actor, {0x5246dc, 0});
        }
        motionRecordFields.state(0x19);
        uint32_t flags = run.get(actor + 8);
        flags = flags & 0xffffffef;
        run.put(actor + 0xcc, 4);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(actor + 8, flags);
        run.call(0x417050, 0, {actor, state});
        run.call(0x4170b0, 0, {actor, state});
        run.put(state + 0x40, 0);
        run.put(0x534de8, 0);
        run.put(0x534dec, 0);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0x40a19400);
        return;
    }
    if (form == 6) {
        dropAttack(run, actor, state);
        motionRecordFields.state(0x1b);
        run.call(0x4c79e0, actor, {0x5246c4, 0});
        uint32_t flags = run.get(actor + 8);
        run.put(actor + 0xcc, 6);
        flags = flags & 0xffffffef;
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(actor + 8, flags);
        run.put(state + 0x2c, 0);
        run.put(state + 0x68, 0);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0);
        return;
    }
    uint32_t attacking = run.get(state + 4);
    if (attacking != 0) {
        advanceAttack(run, actor, record, state);
    } else {
        uint32_t clock = run.get(0x5430c4);
        run.call(0x4c82a0, actor + 0x188, {clock});
    }
    uint32_t finalY = run.get(actor + 0x50);
    uint32_t floorY = run.get(state + 0x64);
    if (s32(finalY) <= s32(floorY))
        run.call(0x417930, 0, {actor, record, state, 1});
}

uint32_t updateJumpAndFallEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    updateJumpAndFall(run, arguments[0], arguments[1], arguments[2]);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x41b630:
        return updateJumpAndFallEntry(run, receiver, arguments);
    case 0x41c4e0:
        return dropAttackEntry(run, receiver, arguments);
    case 0x41c5a0:
        return advanceAttackEntry(run, receiver, arguments);
    case 0x41ce80:
        return reactToTouchedItem(run, receiver, arguments);
    case 0x41d6f0:
        return refreshSoundEntry(run, receiver, arguments);
    case 0x41d750:
        return nearestItemEntry(run, receiver, arguments);
    case 0x41d850:
        return selectAttackFromInput(run, receiver, arguments);
    case 0x41de90:
        return startAttackEntry(run, receiver, arguments);
    case 0x41e710:
        return hasTrailingGroundGap(run, receiver, arguments);
    case 0x41f850:
        return countCollectedItemEntry(run, receiver, arguments);
    case 0x41fc30:
        return updatePowerUpTimer(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_player_actions_03_entry, owned, body)
