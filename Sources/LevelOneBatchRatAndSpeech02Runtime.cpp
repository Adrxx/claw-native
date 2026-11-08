// Level 1 Rat states, batch 2
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
    case 0x47d150:
        return 0;
    case 0x47d1b0:
        return 0;
    case 0x47d2f0:
        return 0;
    case 0x47d470:
        return 0;
    case 0x47d490:
        return 0;
    case 0x47d660:
        return 0;
    default:
        return -1;
    }
}

uint32_t function_47d2f0(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x47d150. Rat state entry: clears +0x50/+0x54, saves the animation id at
// +0x24 from the current animation record (+0x10 -> +0x1c), looks up the
// "LS_HOME" animation and stores it, then optionally starts a sound.
uint32_t function_47d150(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    run.put(self + 0x50, 0);
    run.put(self + 0x54, 0);
    uint32_t record = run.get(self + 0x10);
    uint32_t saved = run.get(record + 0x1c);
    run.put(self + 0x24, saved);
    uint32_t animation = run.call(0x4dba00, 0x537668, {0x5234ec});
    uint32_t record2 = run.get(self + 0x10);
    run.put(record2 + 0x1c, animation);
    uint32_t sound = run.get(self + 0x400);
    if (sound == 0)
        return 0;
    uint32_t enabled = run.get(0x532c0c);
    uint32_t cue = run.get(0x532c10);
    if (enabled == 0)
        return 0;
    uint32_t target = run.get(sound + 0x10);
    run.call(0x4b45f0, target, {cue, 0, 0, 0});
    return 0;
}

// 0x47d1b0. Rat state update: refreshes the logic at +0x12c + 0x188; if bit 2
// of the flag set at +0x300 (inline when the count at +0x2fc is 3..0x20,
// otherwise through the pointer at +0x300) is set, tries 0x47d2f0. Otherwise
// looks up the animation named by +0x24 and picks the virtual method +0x70
// when its name equals "LS_MOVINGRIGHT", +0x6c when it does not.
uint32_t function_47d1b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t level = run.get(0x5430c4);
    uint32_t logic = run.get(self + 0x12c);
    run.call(0x4c82a0, logic + 0x188, {level});
    uint32_t count = run.get(self + 0x2fc);
    uint32_t flag;
    if (count <= 2) {
        flag = 0;
    } else {
        uint32_t address;
        if (count <= 0x20)
            address = self + 0x300;
        else
            address = run.get(self + 0x300);
        flag = (run.get(address) >> 2) & 1;
    }
    if (flag != 0) {
        function_47d2f0(run, self, nullptr);
        return 0;
    }
    uint32_t id = run.get(self + 0x24);
    uint32_t low = run.get(0x5376a0);
    run.put(0x5376b8, 0);
    uint32_t entry;
    if (s32(id) < s32(low)) {
        goto lookup;
    }
    if (s32(id) > s32(run.get(0x5376a4))) {
        goto lookup;
    }
    {
        uint32_t base = run.get(0x5376a8);
        uint32_t stride = run.get(0x5376b0);
        entry = (id - low) * stride + base;
        goto found;
    }
lookup:
    {
        uint32_t result = run.call(0x4db6e0, 0x537698, {id, 0});
        if (result == 0) {
            uint32_t name = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            uint32_t table = run.get(0x53769c);
            run.call(0x4db4d0, table, {0x537698, name, 0xc});
            entry = run.get(0x5376ac);
        } else {
            uint32_t low2 = run.get(0x5376a0);
            uint32_t base2 = run.get(0x5376a8);
            uint32_t stride2 = run.get(0x5376b0);
            entry = (id - low2) * stride2 + base2;
        }
    }
found:
    uint32_t remaining = run.get(0x5376b8);
    uint32_t cursor = run.get(0x5376b4);
    while (remaining != 0) {
        if (cursor != 0)
            run.call(0x4f6439, cursor);
        cursor += 4;
        remaining -= 1;
    }
    uint32_t name2 = run.get(entry);
    uint32_t compare = run.call(0x4a3810, 0, {name2, 0x5271e4});
    if (compare == 0) {
        run.vcall(self, 0x70, {0x3c});
        return 0;
    }
    run.vcall(self, 0x6c, {0x3c});
    return 0;
}

// 0x47d2f0. Returns 1 when the Rat reacts to the player: the player-in-range
// test (0x4cda10) holds, the player's y is within 0x32 of the target's y and
// the target's +0x38 is not -1. Then it calls one of the virtual actions
// +0xb0 / +0xac (timer gated) or +0xa8 (random gated), else returns 0.
uint32_t function_47d2f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t part = self + 0x128;
    bool near = false;
    if (run.get(0x534eac) != 0x26b7) {
        uint32_t player = run.get(0x537e88);
        uint32_t target = run.get(part + 0x6c);
        uint32_t playerX = run.get(player + 0x4c);
        uint32_t targetY = run.get(target + 0x50);
        uint32_t targetX = run.get(target + 0x4c);
        uint32_t owner = run.get(part + 0x68);
        uint32_t ownerInfo = run.get(owner + 0xc);
        uint32_t region = run.get(ownerInfo + 0x24);
        uint32_t hit = run.call(0x4cda10, region, {targetX, targetY, playerX, 0x20});
        if (hit != 0) {
            uint32_t target2 = run.get(part + 0x6c);
            uint32_t player2 = run.get(0x537e88);
            uint32_t targetY2 = run.get(target2 + 0x50);
            uint32_t playerY = run.get(player2 + 0x50);
            uint32_t upper = targetY2 + 0x32;
            if (s32(playerY) < s32(upper)) {
                uint32_t lower = targetY2 - 0x32;
                if (s32(playerY) > s32(lower)) {
                    if (run.get(target2 + 0x38) != 0xffffffff)
                        near = true;
                }
            }
        }
    }
    if (!near)
        return 0;
    uint32_t mode = run.get(self + 0x18c);
    if (mode == 2)
        run.call(0x4357a0, part);
    else
        run.call(0x406310, part);
    uint32_t player3 = run.get(0x537e88);
    double speedY = run.getd(self + 0x70);
    uint32_t playerY3 = run.get(player3 + 0x50);
    uint32_t rounded = run.call_x87(0x4a30e0, 0, speedY);
    uint32_t delta = rounded - playerY3;
    uint32_t sign = (delta >> 31) ? 0xffffffffu : 0;
    uint32_t distance = (delta ^ sign) - sign;
    if (s32(distance) < 0x32) {
        uint32_t clock = run.get(0x537210);
        uint32_t last = run.get(self + 0x418);
        uint32_t interval = run.get(self + 0x41c);
        uint32_t elapsed = clock - last;
        if (elapsed >= interval) {
            run.put(self + 0x41c, 0x3e8);
            uint32_t clock2 = run.get(0x537210);
            run.put(self + 0x418, clock2);
            uint32_t mode2 = run.get(self + 0x18c);
            if (mode2 == 2) {
                run.vcall(self, 0xb0);
                return 1;
            }
            run.vcall(self, 0xac);
            return 1;
        }
    }
    double speedX = run.getd(self + 0x68);
    uint32_t roundedX = run.call_x87(0x4a30e0, 0, speedX);
    uint32_t deltaX = roundedX - run.get(player3 + 0x4c);
    uint32_t signX = (deltaX >> 31) ? 0xffffffffu : 0;
    uint32_t distanceX = (deltaX ^ signX) - signX;
    if (s32(distanceX) >= 0x28)
        return 0;
    double speedY2 = run.getd(self + 0x70);
    if (!(double(s32(playerY3)) > speedY2))
        return 0;
    uint32_t disabled = run.get(0x541334);
    uint32_t chance = run.get(self + 0x2e4);
    bool roll;
    if (disabled == 0) {
        uint32_t value = run.call(0x4a3050, 0);
        int32_t remainder = s32(value) % 100;
        roll = remainder < s32(chance);
    } else {
        roll = false;
    }
    if (!roll)
        return 0;
    run.vcall(self, 0xa8);
    return 1;
}

// 0x47d470. Calls 0x47d2f0; when it returns 0, runs LS_MOVINGLEFT (0x43fd10).
uint32_t function_47d470(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t result = function_47d2f0(run, receiver, nullptr);
    if (result == 0)
        run.call(0x43fd10, receiver);
    return 0;
}

// 0x47d490. Calls 0x47d2f0; when it returns 0, runs LS_MOVINGRIGHT (0x43fdc0).
uint32_t function_47d490(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t result = function_47d2f0(run, receiver, nullptr);
    if (result == 0)
        run.call(0x43fdc0, receiver);
    return 0;
}

// 0x47d660. Rat bomb throw: when the logic update (0x4c82a0) returns 1 and the
// throw counter at +0x1a0 is zero, spawns a "RatBomb" object (0x4c8da0), sets
// its velocity fields from +0x404/+0x408/+0x40c, then bumps the counter. Then
// calls virtual +0x44 once the logic's +0x1a4 is set and +0x19c is clear.
uint32_t function_47d660(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t level = run.get(0x5430c4);
    uint32_t logic = run.get(self + 0x12c);
    uint32_t status = run.call(0x4c82a0, logic + 0x188, {level});
    if (status == 1) {
        if (run.get(self + 0x1a0) == 0) {
            uint32_t world = run.get(self + 0x12c);
            uint32_t offsetY = run.get(self + 0x414);
            uint32_t depth = run.get(world + 0x64);
            uint32_t worldY = run.get(world + 0x50);
            uint32_t spawnY = offsetY + worldY;
            uint32_t offsetX = run.get(self + 0x410);
            uint32_t worldX = run.get(world + 0x4c);
            uint32_t spawnX = offsetX + worldX;
            uint32_t holder = run.get(self + 0x130);
            uint32_t holderInfo = run.get(holder + 0xc);
            uint32_t factory = run.get(holderInfo + 0x8);
            uint32_t bomb = run.call(0x4c8da0, factory, {0, spawnX, spawnY, depth - 1, 0x522d1c, 0x40000});
            uint32_t bombLogic = run.get(bomb + 0x6c);
            uint32_t initializer = run.get(bombLogic + 0x10);
            run.call(initializer, 0, {bomb});
            uint32_t logic1 = run.get(bomb + 0x6c);
            int32_t speedX = run.gets(self + 0x404);
            uint32_t part1 = run.get(logic1 + 0x18);
            run.putd(part1 + 0x50, double(speedX));
            uint32_t logic2 = run.get(bomb + 0x6c);
            int32_t speedY = run.gets(self + 0x408);
            uint32_t part2 = run.get(logic2 + 0x18);
            run.putd(part2 + 0x58, double(speedY));
            uint32_t logic3 = run.get(bomb + 0x6c);
            int32_t speedZ = run.gets(self + 0x40c);
            uint32_t part3 = run.get(logic3 + 0x18);
            run.putd(part3 + 0x40, double(speedZ));
            if (run.get(self + 0x404) != 0) {
                uint32_t logic4 = run.get(bomb + 0x6c);
                uint32_t part4 = run.get(logic4 + 0x18);
                uint32_t extra = run.get(part4 + 0x12c);
                uint32_t flags = run.get(extra + 0x164);
                flags |= 0x2020;
                run.put(extra + 0x164, flags);
                uint32_t bombFlags = run.get(bomb + 0x8);
                bombFlags &= 0xffffff7f;
                run.put(bomb + 0x8, bombFlags);
            }
            uint32_t logic5 = run.get(bomb + 0x6c);
            uint32_t part5 = run.get(logic5 + 0x18);
            run.vcall(part5, 0x28);
        }
        uint32_t counter = run.get(self + 0x1a0);
        run.put(self + 0x1a0, counter + 1);
    }
    uint32_t logic6 = run.get(self + 0x12c);
    uint32_t block = logic6 + 0x188;
    if (run.get(block + 0x1c) != 0) {
        if (run.get(block + 0x14) == 0)
            run.vcall(self, 0x44);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x47d150:
        return function_47d150(run, receiver, arguments);
    case 0x47d1b0:
        return function_47d1b0(run, receiver, arguments);
    case 0x47d2f0:
        return function_47d2f0(run, receiver, arguments);
    case 0x47d470:
        return function_47d470(run, receiver, arguments);
    case 0x47d490:
        return function_47d490(run, receiver, arguments);
    case 0x47d660:
        return function_47d660(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_rat_and_speech_02_entry, owned, body)
