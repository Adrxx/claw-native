// Level 10 Marrow combat, recovered from the v1.0 instruction bodies.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x459d60:
    case 0x459ee0:
        return 1;
    case 0x459b70:
    case 0x459c80:
    case 0x459f10:
    case 0x459f90:
    case 0x45a0b0:
    case 0x45a260:
        return 0;
    default:
        return -1;
    }
}

// 0x459b70. +0x12c sprite, +0x190 world, +0x194 actor;
// +0x470/+0x474 idle clock and delay, +0x420 idle sound.
uint32_t updateIdle(Run &run, uint32_t self) {
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (run.get(0x534eac) != 0x26b7) {
        uint32_t player = run.get(0x537e88);
        uint32_t actor = run.get(self + 0x194);
        uint32_t playerX = run.get(player + 0x4c);
        uint32_t y = run.get(actor + 0x50);
        uint32_t x = run.get(actor + 0x4c);
        uint32_t world = run.get(run.get(run.get(self + 0x190) + 0x0c) + 0x24);
        if (run.call(0x4cda10, world, {x, y, playerX, 0x20})) {
            actor = run.get(self + 0x194);
            player = run.get(0x537e88);
            y = run.get(actor + 0x50);
            uint32_t playerY = run.get(player + 0x50);
            if (s32(playerY) < s32(y + 0x32) && s32(playerY) > s32(y - 0x32) && run.get(actor + 0x38) != 0xffffffff) {
                run.vcall(self, 0x44);
                return 0;
            }
        }
    }
    if (run.get(0x537210) - run.get(self + 0x470) >= run.get(self + 0x474) && !run.get(0x541334)) {
        if (s32(run.call(0x4a3050, 0)) % 100 < 5) {
            if (s32(run.call(0x4a3050, 0)) % 100 < 25) {
                uint32_t sound = run.get(self + 0x420);
                run.call(0x48ce40, 0, {run.get(self + 0x0c), sound, 0});
            }
            run.call(0x44edd0, self);
        }
    }
    return 0;
}

// 0x459c80. +0x80/+0x84 and +0x98/+0x9c combat bounds;
// +0x0c logic data, +0x128 subordinate, +0x4b4..+0x4bc combat flags.
uint32_t initializeCombat(Run &run, uint32_t self) {
    run.call(0x40e560, self);
    uint32_t low = run.get(0x513e10);
    uint32_t high = run.get(0x513e14);
    run.put(self + 0x80, low);
    run.put(self + 0x84, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(self + 0x98, low);
    run.put(self + 0x9c, high);
    run.put(run.get(self + 0x0c) + 0xcc, 7);
    run.vcall(self, 0x24);
    run.put(run.get(self + 0x0c) + 0xcc, 1);
    uint32_t sprite = run.get(self + 0x12c);
    run.put(sprite + 0x50, run.get(sprite + 0x50) - 0x20);
    uint32_t subordinate = run.get(self + 0x128);
    run.call(0x4cd800, run.get(run.get(subordinate + 0x0c) + 0x24), {subordinate, 0});
    run.put(run.get(self + 0x128) + 0xcc, 1);
    run.put(run.get(self + 0x0c) + 0x10c, 100);
    uint32_t data = run.get(self + 0x0c);
    // FILD i32; FMUL m32. This product fits binary64 without rounding.
    double product = double(s32(run.get(data + 0x10c))) * double(run.getf(0x5262b4));
    uint32_t health = run.call_x87(0x4a30e0, 0, product);
    run.put(data + 0x10c, health);
    run.put(self + 0x4b4, 1);
    run.put(self + 0x4b8, 0);
    run.put(self + 0x4bc, 0);
    return 0;
}

// 0x459d60. +0x10 state holder, +0x3c4 elapsed state time,
// +0x4c0 prior health, +0x490 signed-indexed hit states, +0x3bc state.
uint32_t takeHit(Run &run, uint32_t self, uint32_t hit) {
    run.call(0x43e9c0, self, {0x12c});
    uint32_t state = run.call(0x406020, 0x537698, {run.get(run.get(self + 0x10) + 0x1c)});
    if (!run.call(0x4a3810, 0, {run.get(state), 0x523204})) {
        run.vcall(self, 0x44);
        return 0;
    }
    state = run.call(0x406020, 0x537698, {run.get(run.get(self + 0x10) + 0x1c)});
    if (!run.call(0x4a3810, 0, {run.get(state), 0x523210})) {
        run.vcall(self, 0x44);
        return 0;
    }
    uint32_t elapsed = run.get(self + 0x3c4);
    if ((s32(elapsed) < 0 || s32(elapsed) >= 400) && s32(run.get(run.get(self + 0x0c) + 0x10c)) > s32(run.get(self + 0x4c0) - 25)) {
        uint32_t playerData = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
        if (run.get(playerData + 0x14)) {
            run.call(0x44f510, self);
        } else {
            run.call(0x44f3c0, self);
        }
        run.vcall(self, 0x28, {hit});
        run.call(0x440e20, self, {hit});
        uint32_t player = run.get(0x537e88);
        playerData = run.get(run.get(player + 0x6c) + 0x14);
        uint32_t mode = run.get(playerData + 0x3c);
        if ((mode == 1 || mode == 2 || mode == 7 || mode == 8) && run.get(player + 0xcc) == 5) {
            run.vcall(self, 0x58);
        }
        return 0;
    }
    uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 2);
    run.put(self + 0x3bc, run.get(self + index * 4 + 0x490));
    run.vcall(self, 0x9c);
    elapsed = run.get(self + 0x3c4);
    if (s32(elapsed) >= 300 && s32(elapsed) < 400) {
        uint32_t sound = run.get(self + 0x48c);
        run.call(0x48ce40, 0, {run.get(self + 0x0c), sound, 0});
    }
    return 0;
}

// 0x459ee0. Incoming hit +0x08 flags; +0x3bc current state.
uint32_t clearHit(Run &run, uint32_t self, uint32_t hit) {
    run.put(hit + 0x08, run.get(hit + 0x08) | 0x10000);
    uint32_t table = run.get(self);
    run.put(self + 0x3bc, 0);
    run.call(run.get(table + 0x9c), self);
    return 0;
}

// 0x459f90. +0x24 saved state, +0x18c facing;
// +0x138/+0x140 horizontal bounds; +0x4c4/+0x4c8 projectile offsets,
// +0x4cc projectile velocity, +0x134 saved animation, +0x1a0 fired flag.
uint32_t beginFire(Run &run, uint32_t self) {
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x524548});
    run.put(run.get(self + 0x10) + 0x1c, state);
    bool facing = run.get(self + 0x18c) == 2;
    uint32_t sprite = run.get(self + 0x12c);
    if (facing != bool(run.get8(sprite + 0x40) & 2)) {
        uint32_t left = run.get(self + 0x138);
        uint32_t right = run.get(self + 0x140);
        run.put(self + 0x138, 0u - right);
        run.put(self + 0x140, 0u - left);
        uint32_t flags = run.get(sprite + 0x40);
        run.put(sprite + 0x40, facing ? flags | 2 : flags & 0xfffffffd);
        sprite = run.get(self + 0x12c);
        run.call(0x406120, sprite);
        run.call(0x406150, sprite);
        run.call(0x406180, sprite);
    }
    sprite = run.get(self + 0x12c);
    if (run.get8(sprite + 0x40) & 2) {
        run.put(self + 0x4c4, 0x41);
        run.put(self + 0x4cc, 600);
    } else {
        run.put(self + 0x4c4, 0xffffffbf);
        run.put(self + 0x4cc, 0xfffffda8);
    }
    uint32_t animation = run.get(self + 0x4a0);
    run.put(self + 0x4c8, 0xffffffe8);
    sprite = run.get(self + 0x12c);
    run.put(self + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    run.put(self + 0x1a0, 0);
    return 0;
}

// 0x459f10. +0x478/+0x47c fire clock and delay, +0x498 fire sound.
uint32_t updateFireTimer(Run &run, uint32_t self) {
    if (run.get(0x537210) - run.get(self + 0x478) >= run.get(self + 0x47c)) {
        beginFire(run, self);
        uint32_t delay = (uint32_t(s32(run.call(0x4a3050, 0)) % 4) + 1) * 1000;
        run.put(self + 0x47c, delay);
        run.put(self + 0x478, run.get(0x537210));
        uint32_t elapsed = run.get(self + 0x3c4);
        if (s32(elapsed) >= 0 && s32(elapsed) < 100) {
            uint32_t sound = run.get(self + 0x498);
            run.call(0x48ce40, 0, {run.get(self + 0x0c), sound, 0});
        }
    }
    return 0;
}

// 0x45a0b0. +0x130 world owner, +0x480 sound handle.
uint32_t updateFire(Run &run, uint32_t self) {
    uint32_t advanced = run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (advanced == 1 && run.get(self + 0x1a0) == 0) {
        uint32_t offsetY = run.get(self + 0x4c8);
        run.put(self + 0x1a0, 1);
        uint32_t sprite = run.get(self + 0x12c);
        uint32_t layer = run.get(sprite + 0x64) - 1;
        uint32_t y = offsetY + run.get(sprite + 0x50);
        uint32_t spriteX = run.get(sprite + 0x4c);
        uint32_t offsetX = run.get(self + 0x4c4);
        uint32_t owner = run.get(self + 0x130);
        uint32_t bullet = run.call(0x4c8da0, run.get(run.get(owner + 0x0c) + 0x08), {0, offsetX + spriteX, y, layer, 0x522e0c, 0x40000});
        run.call(0x4c7970, bullet, {0x524130});
        uint32_t callbackTable = run.get(bullet + 0x6c);
        run.put(bullet + 0x104, 0x14);
        run.put(bullet + 0xd0, 0x40);
        run.call(run.get(callbackTable + 0x10), 0, {bullet});
        uint32_t interface = run.get(bullet + 0x6c);
        double velocity = double(s32(run.get(self + 0x4cc)));
        uint32_t data = run.get(interface + 0x18);
        run.putd(data + 0x50, velocity);
        data = run.get(run.get(bullet + 0x6c) + 0x18);
        run.put(data + 0x58, 0);
        run.put(data + 0x5c, 0);
        data = run.get(run.get(bullet + 0x6c) + 0x18);
        run.put(data + 0x40, 0);
        run.put(data + 0x44, 0);
        if (s32(run.get(self + 0x4cc)) < 0) {
            data = run.get(run.get(bullet + 0x6c) + 0x18);
            sprite = run.get(data + 0x12c);
            if (!(run.get8(sprite + 0x40) & 2)) {
                uint32_t left = run.get(data + 0x138);
                uint32_t right = run.get(data + 0x140);
                run.put(data + 0x138, 0u - right);
                run.put(data + 0x140, 0u - left);
                run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
                sprite = run.get(data + 0x12c);
                left = run.get(sprite + 0x118);
                if (left != 0x80000000) {
                    right = run.get(sprite + 0x120);
                    run.put(sprite + 0x118, 0u - right);
                    run.put(sprite + 0x120, 0u - left);
                }
                left = run.get(sprite + 0x128);
                if (left != 0x80000000) {
                    right = run.get(sprite + 0x130);
                    run.put(sprite + 0x128, 0u - right);
                    run.put(sprite + 0x130, 0u - left);
                }
                run.call(0x406180, sprite);
            }
        }
        uint32_t sound = run.get(self + 0x480);
        if (sound) {
            uint32_t enabled = run.get(0x532c0c);
            uint32_t value = run.get(0x532c10);
            if (enabled) {
                // 0x45a230: three saved registers, four arguments and CALL.
                uint32_t previousStack = run.stackPointer;
                run.stackPointer = run.frame - 0x20;
                run.call(0x4b45f0, run.get(sound + 0x10), {value, 0, 0, 0});
                run.stackPointer = previousStack;
            }
        }
    }
    uint32_t animation = run.get(self + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14)) {
        run.vcall(self, 0x44);
    }
    return 0;
}

// 0x45a260. +0x2f4 state table; +0x1a8/+0x1a4 CString members.
// The ordinary destructor's compiler EH registration has no observable heap effect.
uint32_t destroy(Run &run, uint32_t self) {
    run.put(0x537b14, 0);
    run.put(self + 0x00, 0x50b16c);
    run.call(0x4dbcd0, self + 0x2f4);
    run.call(0x4f6584, self + 0x1a8);
    run.call(0x4f6584, self + 0x1a4);
    run.put(self + 0x00, 0x50b014);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x459b70:
        return updateIdle(run, receiver);
    case 0x459c80:
        return initializeCombat(run, receiver);
    case 0x459d60:
        return takeHit(run, receiver, arguments[0]);
    case 0x459ee0:
        return clearHit(run, receiver, arguments[0]);
    case 0x459f10:
        return updateFireTimer(run, receiver);
    case 0x459f90:
        return beginFire(run, receiver);
    case 0x45a0b0:
        return updateFire(run, receiver);
    case 0x45a260:
        return destroy(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_ten_marrow_combat_01_entry, owned, body)
