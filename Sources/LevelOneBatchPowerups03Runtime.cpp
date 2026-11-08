// Level 1 claw pickup hit handler
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x41ee60:
        return 4;
    default:
        return -1;
    }
}

// Import slot of PostMessageA.
const uint32_t kPostMessageSlot = 0x546d50;
// Global at 0x5371fc: game object. +0x04 -> window holder (+0x04 window handle), +0x2c -> level object.
const uint32_t kGameGlobal = 0x5371fc;

// Posts a command message to the main window (call dword ptr [0x546d50]).
void postCommand(Run &run, uint32_t wparam) {
    uint32_t game = run.get(kGameGlobal);
    uint32_t holder = run.get(game + 0x04);
    uint32_t window = run.get(holder + 0x04);
    run.icall(kPostMessageSlot, {window, 0x111, wparam, 0});
}

// Marks the pickup (item) as finished: item flags +0x08 |= 0x10000.
void markDone(Run &run, uint32_t item) {
    uint32_t flags = run.get(item + 0x08);
    flags = flags | 0x10000;
    run.put(item + 0x08, flags);
}

// Timed power-up shared by 0x26b8, 0x26b9 and 0x26ba. Skips the grant when the
// same kind is already active and the item repeats.
void timedPowerup(Run &run, uint32_t actor, uint32_t second, uint32_t player, uint32_t item, uint32_t kind) {
    uint32_t duration = 0x7530;
    uint32_t configured = run.get(item + 0x108);
    if (s32(configured) > 0)
        duration = configured;
    bool skip = false;
    if (run.get(item + 0x104) != 0) {
        if (run.get(0x534eac) == kind)
            skip = true;
    }
    if (!skip) {
        run.call(0x41f990, 0, {actor, second, player, kind, duration});
        run.call(0x41d6f0, 0, {item});
    }
    uint32_t again = run.get(item + 0x104);
    if (s32(again) <= 0) {
        markDone(run, item);
        return;
    }
    run.put(0x534ea8, duration);
}

// Plain timed power-up used by 0x26b7 and 0x26bd.
void plainPowerup(Run &run, uint32_t actor, uint32_t second, uint32_t player, uint32_t item, uint32_t kind) {
    uint32_t duration = 0x7530;
    uint32_t configured = run.get(item + 0x108);
    if (s32(configured) > 0)
        duration = configured;
    run.call(0x41f990, 0, {actor, second, player, kind, duration});
    run.call(0x41d6f0, 0, {item});
    markDone(run, item);
}

// 0x26ad: map piece pickup.
void mapPiece(Run &run, uint32_t actor, uint32_t second, uint32_t item) {
    postCommand(run, 0x800e);
    uint32_t slot = run.automatic(0xc);
    run.put(slot, 0);
    run.put(second + 0x24, 2);
    uint32_t owner = run.get(actor + 0x0c);
    uint32_t table = run.get(owner + 0x28);
    run.call(0x4f6286, table + 0x10, {0x524d1c, slot});
    uint32_t found = run.get(slot);
    if (found != 0) {
        uint32_t flag = run.get(0x532c0c);
        uint32_t value = run.get(0x532c10);
        if (flag != 0) {
            uint32_t target = run.get(found + 0x10);
            run.call(0x4b45f0, target, {value, 0, 0, 0});
        }
        uint32_t inner = run.get(found + 0x10);
        uint32_t delay = run.get(inner + 0x28);
        run.call(0x4b8960, 0, {delay});
    }
    uint32_t game = run.get(kGameGlobal);
    uint32_t level = run.get(game + 0x2c);
    uint32_t method = run.get(run.get(level) + 0x10);
    uint32_t result = run.call(method, level, {});
    if (result == 4) {
        if (run.get(level + 0xbcc) == 1) {
            uint32_t score = run.get(actor + 0xf8);
            score = score + 0x13ba;
            run.put(actor + 0xf8, score);
            markDone(run, item);
            return;
        }
    }
    markDone(run, item);
}

// 0x26ae: life/warp style pickup that restores the claw and posts a message.
void restoreClaw(Run &run, uint32_t actor, uint32_t second, uint32_t player, uint32_t item) {
    uint32_t savedA = run.get(item + 0x148);
    uint32_t savedB = run.get(item + 0x14c);
    run.put(run.automatic(0x10), savedA);
    run.put(run.automatic(-4), savedB);
    if (run.get(second + 0x1c) == 4) {
        uint32_t state = run.get(player + 0x3c);
        if (state == 8 || state == 9 || state == 0xa || state == 0x12) {
            uint32_t slot = run.automatic(0xc);
            run.put(slot, 0);
            uint32_t owner = run.get(actor + 0x0c);
            uint32_t table = run.get(owner + 0x2c);
            run.call(0x4f6286, table + 0x10, {0x5246dc, slot});
            uint32_t made = run.get(slot);
            run.put(player + 0x124, made);
        } else {
            run.call(0x41c4e0, 0, {actor, second, player});
            run.call(0x4c79e0, actor, {0x5246dc, 0});
        }
        run.put(second + 0x1c, 0x19);
        uint32_t flags = run.get(actor + 0x08);
        flags = flags & 0xffffffef;
        run.put(actor + 0xcc, 4);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(actor + 0x08, flags);
        run.call(0x417050, 0, {actor, player});
        run.call(0x4170b0, 0, {actor, player});
        savedA = run.get(run.automatic(0x10));
        savedB = run.get(run.automatic(-4));
        run.put(player + 0x40, 0);
        run.put(0x534de8, 0);
        run.put(0x534dec, 0);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0x40a19400);
    }
    if (s32(savedA) > 0) {
        if (s32(savedB) > 0) {
            run.put(0x529fa0, savedA);
            run.put(0x529fa4, savedB);
            postCommand(run, 0x805c);
        }
    }
    if (run.get(item + 0x108) != 0)
        return;
    uint32_t done = run.get(item + 0x08);
    done = done | 0x10000;
    run.put(item + 0x08, done);
}

// 0x26af: grab/swing pickup.
void swing(Run &run, uint32_t actor, uint32_t second, uint32_t player, uint32_t item) {
    if (run.get(player + 0x11c) != 0) {
        if (run.get(player + 0x134) == item)
            return;
    }
    uint32_t mode = run.get(actor + 0xcc);
    if (mode != 3 && mode != 4)
        return;
    uint32_t object = run.get(item + 0x6c);
    uint32_t y = run.call(0x403ac0, run.get(object + 0x18), {});
    uint32_t diff = run.get(actor + 0x50) - y - 0x10;
    uint32_t sign = uint32_t(s32(diff) >> 31);
    uint32_t magnitude = (diff ^ sign) - sign;
    if (s32(magnitude) >= 0x30)
        return;
    run.call(0x41c4e0, 0, {actor, second, player});
    run.put(second + 0x1c, 0x138f);
    run.call(0x4c79e0, actor, {0x524d2c, 0});
    run.put(actor + 0xcc, 8);
    uint32_t facing = run.get(player);
    run.put(player + 0x134, item);
    run.put(player + 0xf8, 0);
    uint32_t held;
    if (facing != 0) {
        uint32_t x = run.call(0x403ab0, run.get(run.get(item + 0x6c) + 0x18), {});
        run.put(actor + 0x4c, x + 8);
        held = run.get(player + 0x134);
    } else {
        uint32_t x = run.call(0x403ab0, run.get(run.get(item + 0x6c) + 0x18), {});
        run.put(actor + 0x4c, x - 8);
        held = run.get(player + 0x134);
    }
    uint32_t heldObject = run.get(held + 0x6c);
    uint32_t top = run.call(0x403ac0, run.get(heldObject + 0x18), {});
    run.put(actor + 0x50, top + 0x14);
    run.put(0x534e60, 0);
    run.put(0x534e64, 0);
    run.put(0x534e68, 0);
    run.put(0x534e6c, 0);
    run.put(0x534e70, 0);
    run.put(0x534e74, 0);
}

// 0x26b0: coin-style pickup adding to a capped counter.
void counterPickup(Run &run, uint32_t player, uint32_t item) {
    uint32_t amount = 5;
    uint32_t configured = run.get(item + 0x108);
    if (s32(configured) > 0)
        amount = configured;
    uint32_t total = run.get(player + 0x78) + amount;
    run.put(player + 0x78, total);
    if (s32(total) > 0x63)
        run.put(player + 0x78, 0x63);
    run.call(0x41d6f0, 0, {item});
    markDone(run, item);
    uint32_t holder = run.get(0x534874);
    if (holder == 0)
        return;
    uint32_t hit = run.call(0x405f80, holder, {});
    if (hit == 0)
        return;
    uint32_t again = run.get(0x534874);
    run.put(again + 0x4c8, 0);
}

// 0x41ee60. Handles the player touching a pickup item. Dispatches on the item
// type at +0xfc (0x26ad to 0x26be).
uint32_t function_41ee60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t second = arguments[1];
    uint32_t player = arguments[2];
    uint32_t item = arguments[3];
    if (item == 0)
        return 0;
    uint32_t type = run.get(item + 0xfc);
    switch (type) {
    case 0x26ad:
        mapPiece(run, actor, second, item);
        return 0;
    case 0x26ae:
        restoreClaw(run, actor, second, player, item);
        return 0;
    case 0x26af:
        swing(run, actor, second, player, item);
        return 0;
    case 0x26b0:
        counterPickup(run, player, item);
        return 0;
    case 0x26b1:
    case 0x26b2:
    case 0x26b3:
    case 0x26b4:
    case 0x26b5:
    case 0x26b6: {
        uint32_t game = run.get(kGameGlobal);
        uint32_t level = run.get(game + 0x2c);
        if (level != 0) {
            uint32_t result = run.vcall(level, 0x58, {item});
            if (result != 0) {
                run.call(0x41d6f0, 0, {item});
                markDone(run, item);
                return 0;
            }
        }
        markDone(run, item);
        return 0;
    }
    case 0x26b7:
        plainPowerup(run, actor, second, player, item, 0x26b7);
        return 0;
    case 0x26b8:
    case 0x26b9:
    case 0x26ba:
        timedPowerup(run, actor, second, player, item, type);
        return 0;
    case 0x26bd:
        plainPowerup(run, actor, second, player, item, 0x26bd);
        return 0;
    case 0x26be: {
        uint32_t count = run.get(player + 0x7c);
        if (s32(count) < 10) {
            count = count + 1;
            run.put(player + 0x7c, count);
            run.call(0x41d6f0, 0, {item});
        }
        uint32_t result = run.call(0x473ae0, 0, {item});
        if (result != 0)
            return 0;
        markDone(run, item);
        return 0;
    }
    default:
        return 0;
    }
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x41ee60:
        return function_41ee60(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_powerups_03_entry, owned, body)
