// Level 1 Officer and Soldier state callbacks, batch 1
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
    case 0x463020:
        return 0;
    case 0x48b4b0:
        return 0;
    case 0x48ba00:
        return 0;
    default:
        return -1;
    }
}

// Actor fields used below: +0x00 vtable, +0x0c owner, +0x12c sprite record,
// +0x138 and +0x140 sprite edge values, +0x184 state, +0x18c mode,
// +0x190 and +0x194 collaborating objects. Sprite record +0x38 frame, +0x40 flags.

// Mirrors the sprite edge pair and flag bit 2 as the originals do inline.
void mirrorOn(Run &run, uint32_t actor, uint32_t sprite) {
    uint32_t first = run.get(actor + 0x138);
    uint32_t second = run.get(actor + 0x140);
    run.put(actor + 0x138, 0u - second);
    run.put(actor + 0x140, 0u - first);
    run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
}

// 0x463020. State callback: mirrors the sprite to the facing, then continues.
uint32_t function_463020(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t actor = receiver;
    uint32_t sprite = run.get(actor + 0x12c);
    uint32_t flags = run.get8(sprite + 0x40);
    if (s32(run.get(actor + 0x18c)) == 2) {
        if ((flags & 2) == 0) {
            mirrorOn(run, actor, sprite);
            uint32_t again = run.get(actor + 0x12c);
            run.call(0x406120, again);
            run.call(0x406150, again);
            run.call(0x406180, again);
        }
    } else {
        if ((flags & 2) != 0) {
            uint32_t first = run.get(actor + 0x138);
            uint32_t second = run.get(actor + 0x140);
            run.put(actor + 0x138, 0u - second);
            run.put(actor + 0x140, 0u - first);
            run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffdu);
            run.call(0x4060b0, run.get(actor + 0x12c));
        }
    }
    run.call(0x4a3050, 0);
    int32_t state = s32(run.get(actor + 0x184));
    if (state >= 0 && state <= 4) {
        uint32_t draw = run.call(0x4a3050, 0);
        if (s32(draw) % 100 < 0x21) {
            if (run.get(run.get(actor + 0x12c) + 0x38) != 0xffffffffu)
                run.call(0x48ceb0, 0, {run.get(actor + 0xc), 0x529888, 0});
        }
        run.vcall(actor, 0x58);
        return 0;
    }
    run.call(0x44edd0, actor);
    return 0;
}

// The player-overlap test the 0x48b4b0 callback performs twice.
bool playerInRange(Run &run, uint32_t actor) {
    if (run.get(0x534eac) == 0x26b7)
        return false;
    uint32_t player = run.get(0x537e88);
    uint32_t target = run.get(actor + 0x194);
    uint32_t x = run.get(target + 0x4c);
    uint32_t y = run.get(target + 0x50);
    uint32_t playerX = run.get(player + 0x4c);
    uint32_t region = run.get(run.get(run.get(actor + 0x190) + 0xc) + 0x24);
    uint32_t hit = run.call(0x4cda10, region, {x, y, playerX, 0x20});
    if (hit == 0)
        return false;
    uint32_t other = run.get(actor + 0x194);
    uint32_t top = run.get(other + 0x50);
    uint32_t playerY = run.get(run.get(0x537e88) + 0x50);
    if (s32(playerY) >= s32(top + 0x32))
        return false;
    if (s32(playerY) <= s32(top - 0x32))
        return false;
    if (run.get(other + 0x38) == 0xffffffffu)
        return false;
    return true;
}

// 0x48b4b0. State callback with a proximity test against the player.
uint32_t function_48b4b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t actor = receiver;
    uint32_t record = actor + 0x128;
    if (s32(run.get(actor + 0x18c)) == 2) {
        uint32_t sprite = run.get(record + 0x4);
        if ((run.get8(sprite + 0x40) & 2) == 0) {
            mirrorOn(run, actor, sprite);
            uint32_t again = run.get(record + 0x4);
            run.call(0x406120, again);
            run.call(0x406150, again);
            run.call(0x406180, again);
        }
    } else {
        run.call(0x406310, record);
    }
    run.call(0x4a3050, 0);
    uint32_t state = run.get(actor + 0x184);
    if (state <= 4) {
        if (state >= 3) {
            run.vcall(actor, 0x58);
            return 0;
        }
        if (!playerInRange(run, actor))
            run.vcall(actor, 0x48);
        if (run.get(actor + 0x450) == 0) {
            uint32_t sprite = run.get(actor + 0x12c);
            uint32_t sound = run.get(actor + 0x460);
            if (run.get(sprite + 0x38) != 0xffffffffu)
                run.call(0x48ce40, 0, {run.get(actor + 0xc), sound, 0});
            run.put(actor + 0x450, 1);
        }
    }
    if (playerInRange(run, actor)) {
        run.vcall(actor, 0xa4);
        return 0;
    }
    run.call(0x44da20, actor);
    return 0;
}

// Mirrors an edge pair at +0x118/+0x120 or +0x128/+0x130 unless it holds the
// 0x80000000 sentinel.
void mirrorPair(Run &run, uint32_t sprite, uint32_t low, uint32_t high) {
    uint32_t first = run.get(sprite + low);
    if (first == 0x80000000u)
        return;
    uint32_t second = run.get(sprite + high);
    run.put(sprite + low, 0u - second);
    run.put(sprite + high, 0u - first);
}

// 0x48ba00. Fires a musket ball when the shooting animation reaches its frame.
uint32_t function_48ba00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t actor = receiver;
    uint32_t phase = run.get(0x5430c4);
    uint32_t result = run.call(0x4c82a0, run.get(actor + 0x12c) + 0x188, {phase});
    if (result == 1 && run.get(actor + 0x1a0) == 0) {
        uint32_t offsetY = run.get(actor + 0x458);
        run.put(actor + 0x1a0, 1);
        uint32_t sprite = run.get(actor + 0x12c);
        uint32_t layer = run.get(sprite + 0x64) - 1;
        uint32_t y = offsetY + run.get(sprite + 0x50);
        uint32_t x = run.get(actor + 0x454) + run.get(sprite + 0x4c);
        uint32_t factory = run.get(run.get(run.get(actor + 0x130) + 0xc) + 0x8);
        uint32_t ball = run.call(0x4c8da0, factory, {0, x, y, layer, 0x522e0c, 0x40000});
        run.call(0x4c7970, ball, {0x52c4a0});
        run.put(ball + 0x104, 0xa);
        run.put(ball + 0xd0, 0x40);
        uint32_t ballSprite = run.get(ball + 0x6c);
        run.call(run.get(ballSprite + 0x10), 0, {ball});
        uint32_t velocity = run.get(run.get(ball + 0x6c) + 0x18);
        run.putd(velocity + 0x50, double(s32(run.get(actor + 0x45c))));
        uint32_t motion = run.get(run.get(ball + 0x6c) + 0x18);
        run.put(motion + 0x58, 0);
        run.put(motion + 0x5c, 0);
        uint32_t body = run.get(run.get(ball + 0x6c) + 0x18);
        run.put(body + 0x40, 0);
        run.put(body + 0x44, 0);
        if (s32(run.get(actor + 0x45c)) < 0) {
            uint32_t shot = run.get(run.get(ball + 0x6c) + 0x18);
            uint32_t flagsRecord = run.get(shot + 0x12c);
            if ((run.get8(flagsRecord + 0x40) & 2) == 0) {
                uint32_t first = run.get(shot + 0x138);
                uint32_t second = run.get(shot + 0x140);
                run.put(shot + 0x138, 0u - second);
                run.put(shot + 0x140, 0u - first);
                run.put(flagsRecord + 0x40, run.get(flagsRecord + 0x40) | 2);
                uint32_t edges = run.get(shot + 0x12c);
                mirrorPair(run, edges, 0x118, 0x120);
                mirrorPair(run, edges, 0x128, 0x130);
                run.call(0x406180, edges);
            }
        }
        uint32_t effect = run.get(actor + 0x3b4);
        if (effect != 0 && run.get(0x532c0c) != 0)
            run.call(0x4b45f0, run.get(effect + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
    uint32_t anim = run.get(actor + 0x12c) + 0x188;
    if (run.get(anim + 0x1c) != 0 && run.get(anim + 0x14) == 0)
        run.vcall(actor, 0x44);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x463020:
        return function_463020(run, receiver, arguments);
    case 0x48b4b0:
        return function_48b4b0(run, receiver, arguments);
    case 0x48ba00:
        return function_48ba00(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_officer_soldier_01_entry, owned, body)
