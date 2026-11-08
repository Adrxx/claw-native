// Native implementation of the separately compared v1.3 death/audio profile.
#include "ClawRuntime.hpp"
#include "V13EnemyDeathSound.h"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x440130:
        return 1;
    case 0x421bb0:
        return 4;
    case 0x421c00:
        return 1;
    case 0x4cae00:
        return 2;
    default:
        return -1;
    }
}

// 0x421bb0. Resource +0x10 owns the backend, +0x14 is the last accepted
// request time and +0x18 is the minimum unsigned interval.
uint32_t playDirect(Run &run, uint32_t resource, uint32_t volume,
                    uint32_t pan, uint32_t pitch, uint32_t loop) {
    if (run.get(0x53098c) == 0)
        return 0;
    uint32_t now = run.get(0x5aafdc);
    uint32_t last = run.get(resource + 0x14);
    if (!claw_v13_sound_elapsed(now, last, run.get(resource + 0x18)))
        return 0;
    run.put(resource + 0x14, now);
    return run.call(0x4b3da0, run.get(resource + 0x10), {volume, pan, pitch, loop});
}

// 0x421c00. Manager +0x30 disables requests and +0x10 embeds its name map.
uint32_t playNamed(Run &run, uint32_t manager, uint32_t name) {
    if (run.get(manager + 0x30) != 0)
        return 0;
    uint32_t output = run.automatic(-4);
    run.put(output, 0);
    run.call(0x4fc6b4, manager + 0x10, {name, output});
    uint32_t resource = run.get(output);
    if (resource == 0)
        return 0;
    uint32_t enabled = run.get(0x53098c);
    uint32_t volume = run.get(0x530990);
    if (enabled == 0)
        return 0;
    uint32_t now = run.get(0x5aafdc);
    uint32_t last = run.get(resource + 0x14);
    if (!claw_v13_sound_elapsed(now, last, run.get(resource + 0x18)))
        return 0;
    run.put(resource + 0x14, now);
    return run.call(0x4b3da0, run.get(resource + 0x10), {volume, 0, 0, 0});
}

// 0x4cae00. The manager's +0x34 interval is sampled after loading and map
// publication; existing resources retain their copied interval.
uint32_t createSound(Run &run, uint32_t manager, const uint32_t *arguments) {
    if (run.get(manager + 0x30) != 0)
        return 0;
    uint32_t resource = run.call(0x4fcaea, 0, {0x1c});
    if (resource == 0)
        return 0;
    uint32_t identity = run.get(manager + 0x1c);
    uint32_t owner = run.get(manager + 0xc);
    run.put(resource + 0x4, identity);
    run.put(resource + 0xc, owner);
    run.put(resource + 0x8, 0);
    run.put(resource, 0x5140a8);
    run.put(resource + 0x10, 0);
    run.put(resource + 0x18, 0);
    run.put(resource + 0x14, 0);
    uint32_t savedStack = run.stackPointer;
    run.stackPointer = run.automatic(-0x14);
    uint32_t loaded = run.call(0x4c8f10, resource, {arguments[1]});
    run.stackPointer = savedStack;
    if (loaded == 0) {
        run.vcall(resource, 0x4, {1});
        return 0;
    }
    uint32_t slot = run.call(0x4fc6d6, manager + 0x10, {arguments[0]});
    run.put(slot, resource);
    run.put(resource + 0x18, run.get(manager + 0x34));
    return resource;
}

// 0x440130. Enemy +0x14 is the state record, +0x154 the sprite,
// +0x324/+0x328 the short-or-heap bitset, and +0x32c the death mode.
uint32_t enemyDeath(Run &run, uint32_t enemy, uint32_t mode) {
    run.put(enemy + 0x32c, mode);
    uint32_t record = run.get(enemy + 0x14);
    run.put(enemy + 0x30, run.get(record + 0x1c));
    uint32_t dead = run.call(0x4de970, 0x5acd00, {0x52152c});
    record = run.get(enemy + 0x14);
    run.put(record + 0x1c, dead);
    run.put(enemy + 0x2c, 1);
    uint32_t sprite = run.get(enemy + 0x154);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 0x80);
    run.call(0x43f9a0, enemy, {0});
    uint32_t state = run.get(enemy + 0x32c);
    switch (state) {
    case 0: {
        uint32_t length = run.get(enemy + 0x324);
        if (length != 0) {
            uint32_t bits = length <= 0x20 ? enemy + 0x328 : run.get(enemy + 0x328);
            run.put(bits, claw_v13_enemy_dead_bits(run.get(bits)));
        }
        uint32_t owner = run.get(enemy + 0x10);
        if (run.get(owner + 0x74) != 0x2134) {
            run.put(owner + 0x74, 0x2134);
            run.put(owner + 0x8, run.get(owner + 0x8) | 0x20000);
        }
        uint32_t random = run.call(0x4a595b, 0, {});
        if (s32(random) % 100 < 25) {
            owner = run.get(enemy + 0x10);
            uint32_t world = run.get(owner + 0x84);
            run.call(0x421650, 0, {run.get(world + 0xe8)});
        } else {
            uint32_t voice = run.get(enemy + 0x3cc);
            if (voice != 0)
                playDirect(run, voice, run.get(0x530990), 0, 0, 0);
        }
        uint32_t low = run.get(0x514538);
        uint32_t high = run.get(0x51453c);
        run.put(enemy + 0xa8, low);
        run.put(enemy + 0xac, high);
        low = run.get(0x514540);
        high = run.get(0x514544);
        run.put(enemy + 0xc0, low);
        run.put(enemy + 0xc4, high);
        low = run.get(0x514538);
        high = run.get(0x51453c);
        run.put(enemy + 0xb0, low);
        run.put(enemy + 0xb4, high);
        low = run.get(0x514540);
        high = run.get(0x514544);
        run.put(enemy + 0xc8, low);
        run.put(enemy + 0xcc, high);
        low = run.get(0x514538);
        high = run.get(0x51453c);
        run.put(enemy + 0xb8, low);
        run.put(enemy + 0xbc, high);
        low = run.get(0x514540);
        high = run.get(0x514544);
        run.put(enemy + 0xd0, low);
        run.put(enemy + 0xd4, high);
        owner = run.get(enemy + 0x10);
        run.put(owner + 0xe4, 7);
        sprite = run.get(enemy + 0x154);
        uint32_t animation = run.get(enemy + 0x39c);
        run.put(enemy + 0x15c, run.get(sprite + 0x1b4));
        run.call(0x421d10, sprite, {animation, 0});
        run.put(enemy + 0x50, 0);
        run.put(enemy + 0x54, 0x409f4000);
        uint32_t facing = run.get(enemy + 0x1b4);
        run.put(enemy + 0x60, 0);
        if (facing == 3)
            run.put(enemy + 0x64, 0x4062c000);
        else
            run.put(enemy + 0x64, 0xc062c000);
        run.put(enemy + 0x68, 0);
        run.put(enemy + 0x6c, 0xc085e000);
        run.put(enemy + 0x70, 0);
        run.put(enemy + 0x74, 0);
        if (run.get(0x535958) != 0) {
            length = run.get(enemy + 0x324);
            bool bounced = false;
            if (length > 4) {
                uint32_t bits = length <= 0x20 ? enemy + 0x328 : run.get(enemy + 0x328);
                bounced = (run.get8(bits) & 0x10) != 0;
            }
            if (bounced) {
                uint32_t current = run.get(0x535da0) + 1;
                uint32_t maximum = run.get(0x535da4);
                run.put(0x535da0, current);
                if (s32(current) > s32(maximum)) {
                    maximum = current;
                    run.put(0x535da4, maximum);
                }
                uint32_t total = run.get(0x53595c) + 1;
                uint32_t buffer = ((run.automatic(0) - 4) & 0xfffffff8) - 0x54;
                run.put(0x53595c, total);
                run.call(0x4a5b6e, 0, {buffer, 0x525484, current, maximum, total});
                run.call(0x42c780, run.get(0x535910), {buffer});
            } else {
                run.put(0x535da0, 0);
            }
        }
        break;
    }
    case 1:
    case 2: {
        uint32_t voice = run.get(enemy + (state == 1 ? 0x3d8 : 0x3d0));
        if (voice != 0)
            playDirect(run, voice, run.get(0x530990), 0, 0, 0);
        run.put(enemy + 0xf0, 1);
        sprite = run.get(enemy + 0x154);
        run.put(sprite + 0x48, 0x1e);
        run.put(sprite + 0x44, 0);
        sprite = run.get(enemy + 0x154);
        run.put(sprite + 0x40, run.get(sprite + 0x40) | 8);
        run.put(enemy + 0x404, 1000);
        run.put(enemy + 0x400, run.get(0x535928));
        break;
    }
    case 3: {
        uint32_t voice = run.get(enemy + 0x3d4);
        if (voice != 0)
            playDirect(run, voice, run.get(0x530990), 0, 0, 0);
        run.put(enemy + 0xf0, 1);
        sprite = run.get(enemy + 0x154);
        run.put(sprite + 0x8, run.get(sprite + 0x8) | 0x10000);
        break;
    }
    default:
        break;
    }
    uint32_t length = run.get(enemy + 0x324);
    if (length <= 4) {
        run.call(0x4dea70, enemy + 0x31c, {4});
        return 0;
    }
    uint32_t bits = length <= 0x20 ? enemy + 0x328 : run.get(enemy + 0x328);
    run.put(bits, run.get(bits) | 0x10);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x440130:
        return enemyDeath(run, receiver, arguments[0]);
    case 0x421bb0:
        return playDirect(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3]);
    case 0x421c00:
        return playNamed(run, receiver, arguments[0]);
    case 0x4cae00:
        return createSound(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_v13_enemy_death_sound_entry, owned, body)
