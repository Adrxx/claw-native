// Level 1 enemies: shared enemy base virtual slots, batch 2
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
    case 0x43ed70:
        return 0;
    case 0x43eee0:
        return 3;
    case 0x43ee10:
        return 2;
    case 0x43efe0:
        return 0;
    case 0x43fa10:
        return 0;
    case 0x44e0c0:
        return 1;
    case 0x40a440:
        return 0;
    case 0x40aaf0:
        return 1;
    case 0x40e5b0:
        return 0;
    case 0x40e1b0:
        return 0;
    default:
        return -1;
    }
}

uint32_t function_44e0c0(Run &run, uint32_t receiver, const uint32_t *arguments);

// Enemy fields used here: +0x0c object, +0x10 animation holder (+0x1c current
// sequence), +0x20 flag, +0x24 saved sequence, +0x12c state holder (+0x188
// animation player, +0x190 frame), +0x134 current frame.
// Looks up an animation sequence by name.
uint32_t lookupSequence(Run &run, uint32_t name) {
    return run.call(0x4dba00, 0x537668, {name});
}

// 0x43ed70. Falling animation start.
uint32_t function_43ed70(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t holder = run.get(receiver + 0x12c);
    uint32_t argument = run.get(receiver + 0x32c);
    uint32_t frame = run.get(holder + 0x190);
    run.put(receiver + 0x134, frame);
    run.call(0x4c8220, holder + 0x188, {argument});
    uint32_t animation = run.get(receiver + 0x10);
    uint32_t saved = run.get(animation + 0x1c);
    run.put(receiver + 0x24, saved);
    uint32_t sequence = lookupSequence(run, 0x5236fc);
    uint32_t animation2 = run.get(receiver + 0x10);
    run.put(animation2 + 0x1c, sequence);
    uint32_t object = run.get(receiver + 0xc);
    run.put(object + 0xcc, 8);
    return 0;
}

// Common body of 0x43ee10 and 0x43eee0 up to the 0x310 store and animation
// start. `slot` is the entry-relative offset of the GAME_NULL fallback local.
uint32_t strikeStart(Run &run, uint32_t receiver, uint32_t nameKey, uint32_t source, uint32_t slotA, uint32_t slotB) {
    run.put(receiver + 0x20, 1);
    uint32_t animation = run.get(receiver + 0x10);
    uint32_t saved = run.get(animation + 0x1c);
    run.put(receiver + 0x24, saved);
    uint32_t sequence = lookupSequence(run, 0x52720c);
    uint32_t animation2 = run.get(receiver + 0x10);
    run.put(slotB, 0);
    run.put(animation2 + 0x1c, sequence);
    uint32_t word0 = run.get(source);
    run.put(receiver + 0x220, word0);
    uint32_t word1 = run.get(source + 4);
    run.put(receiver + 0x224, word1);
    uint32_t word2 = run.get(source + 8);
    run.put(receiver + 0x228, word2);
    uint32_t word3 = run.get(source + 0xc);
    run.put(receiver + 0x22c, word3);
    uint32_t holder = run.get(receiver + 0x12c);
    uint32_t table = run.get(holder + 0xc);
    uint32_t map = run.get(table + 0x2c);
    run.call(0x4f6286, map + 0x10, {nameKey, slotB});
    uint32_t found = run.get(slotB);
    if (found == 0) {
        uint32_t holder2 = run.get(receiver + 0x12c);
        run.put(slotA, found);
        uint32_t table2 = run.get(holder2 + 0xc);
        uint32_t map2 = run.get(table2 + 0x2c);
        run.call(0x4f6286, map2 + 0x10, {0x5234b4, slotA});
        found = run.get(slotA);
    }
    run.put(receiver + 0x310, found);
    uint32_t holder3 = run.get(receiver + 0x12c);
    uint32_t frame = run.get(holder3 + 0x190);
    run.put(receiver + 0x134, frame);
    run.call(0x4c8220, holder3 + 0x188, {found});
    return 0;
}

// 0x43eee0. Strike start with a second lookup stored at +0x3a0.
uint32_t function_43eee0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    strikeStart(run, receiver, arguments[0], arguments[1], run.automatic(4), run.automatic(8));
    uint32_t holder = run.get(receiver + 0x12c);
    uint32_t slot = run.automatic(8);
    run.put(slot, 0);
    uint32_t table = run.get(holder + 0xc);
    uint32_t map = run.get(table + 0x28);
    run.call(0x4f6286, map + 0x10, {arguments[2], slot});
    uint32_t result = run.get(slot);
    run.put(receiver + 0x3a0, result);
    return 0;
}

// 0x43ee10. Strike start.
uint32_t function_43ee10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return strikeStart(run, receiver, arguments[0], arguments[1], run.automatic(4), run.automatic(8));
}

// 0x43efe0. Strike animation restart using the stored +0x310 value.
uint32_t function_43efe0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x20, 1);
    uint32_t animation = run.get(receiver + 0x10);
    uint32_t saved = run.get(animation + 0x1c);
    run.put(receiver + 0x24, saved);
    uint32_t sequence = lookupSequence(run, 0x52720c);
    uint32_t animation2 = run.get(receiver + 0x10);
    run.put(animation2 + 0x1c, sequence);
    uint32_t holder = run.get(receiver + 0x12c);
    uint32_t argument = run.get(receiver + 0x310);
    uint32_t frame = run.get(holder + 0x190);
    run.put(receiver + 0x134, frame);
    run.call(0x4c8220, holder + 0x188, {argument});
    return 0;
}

// Calls 0x4207f0 on the tile map of the object held at +0x128.
uint32_t tileProbe(Run &run, uint32_t objectHolder, uint32_t x, uint32_t y) {
    uint32_t object = run.get(objectHolder);
    uint32_t table = run.get(object + 0xc);
    uint32_t map = run.get(table + 0x24);
    return run.call(0x4207f0, map, {x, y});
}

// 0x43fa10. Picks a target x at random, checks the tile map, starts moving.
uint32_t function_43fa10(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t direction = run.get(receiver + 0x18c);
    uint32_t base = run.get(0x537e88);
    uint32_t x;
    uint32_t velocityHigh;
    uint32_t anchor = run.get(base + 0x4c);
    uint32_t random = run.call(0x4a3050, 0);
    uint32_t offset = uint32_t(s32(random) % 0x29) + 0x28;
    if (direction == 3) {
        x = offset + anchor;
        velocityHigh = 0xc062c000;
        run.put(receiver + 0x280, x);
        double limit = run.getd(receiver + 0x80);
        double value = double(s32(x));
        if (limit > value)
            return 0;
    } else {
        x = anchor - offset;
        velocityHigh = 0x4062c000;
        run.put(receiver + 0x280, x);
        double limit = run.getd(receiver + 0x98);
        double value = double(s32(x));
        if (limit < value || limit != limit)
            return 0;
    }
    uint32_t holderObject = run.get(receiver + 0x128);
    uint32_t row = run.get(holderObject + 0x124);
    uint32_t extra = run.get(holderObject + 0x50);
    uint32_t y = row + extra + 1;
    uint32_t table = run.get(holderObject + 0xc);
    uint32_t map = run.get(table + 0x24);
    uint32_t hit = run.call(0x4207f0, map, {x, y});
    if (hit != 1) {
        hit = tileProbe(run, receiver + 0x128, x, y);
        if (hit != 2) {
            hit = tileProbe(run, receiver + 0x128, x, y);
            if (hit != 3)
                return 0;
        }
    }
    uint32_t below = tileProbe(run, receiver + 0x128, x, y - 1);
    if (below != 0)
        return 0;
    run.put(receiver + 0x50, below);
    run.put(receiver + 0x54, velocityHigh);
    run.put(receiver + 0x58, below);
    run.put(receiver + 0x5c, below);
    run.put(receiver + 0x60, below);
    run.put(receiver + 0x64, below);
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t state = run.get(receiver + 0x12c);
        uint32_t flags = run.get8(state + 0x40);
        if ((flags & 2) == 0) {
            uint32_t first = run.get(receiver + 0x138);
            uint32_t second = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0u - second);
            run.put(receiver + 0x140, 0u - first);
            uint32_t word = run.get(state + 0x40);
            run.put(state + 0x40, word | 2);
            uint32_t state2 = run.get(receiver + 0x12c);
            run.call(0x4060b0, state2);
        }
    } else {
        run.call(0x406310, receiver + 0x128);
    }
    uint32_t animation = run.get(receiver + 0x10);
    uint32_t saved = run.get(animation + 0x1c);
    run.put(receiver + 0x24, saved);
    uint32_t sequence = lookupSequence(run, 0x527198);
    uint32_t animation2 = run.get(receiver + 0x10);
    run.put(animation2 + 0x1c, sequence);
    uint32_t holder = run.get(receiver + 0x12c);
    uint32_t argument = run.get(receiver + 0x308);
    uint32_t frame = run.get(holder + 0x190);
    run.put(receiver + 0x134, frame);
    run.call(0x4c8220, holder + 0x188, {argument});
    return 0;
}

// 0x44e0c0. Stores the argument at +0x304, conditionally resets the +0x128
// holder (bit 4 of a small/large bitset at +0x2fc/+0x300), then 0x43f120.
uint32_t function_44e0c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t argument = arguments[0];
    run.put(receiver + 0x304, argument);
    uint32_t count = run.get(receiver + 0x2fc);
    uint32_t bit;
    if (count <= 4) {
        bit = 0;
    } else {
        uint32_t address;
        if (count <= 0x20)
            address = receiver + 0x300;
        else
            address = run.get(receiver + 0x300);
        uint32_t word = run.get(address);
        bit = (word >> 4) & 1;
    }
    if (bit == 0)
        run.call(0x42df90, receiver + 0x128);
    run.call(0x43f120, receiver, {argument});
    return 0;
}

// 0x40a440. Maybe plays a random sound, then 0x44f1b0.
uint32_t function_40a440(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x184) != 6) {
        uint32_t random = run.call(0x4a3050, 0);
        if (s32(random) % 100 < 0x3c) {
            uint32_t random2 = run.call(0x4a3050, 0);
            uint32_t index = uint32_t(s32(random2) % 3);
            uint32_t object = run.get(receiver + 0xc);
            uint32_t sound = run.get(receiver + index * 4 + 0x470);
            run.call(0x48ce40, 0, {object, sound, 0});
        }
    }
    run.call(0x44f1b0, receiver);
    return 0;
}

// 0x40aaf0. Calls 0x41fe80 when the current level record is 0x1390, then 0x44e0c0.
uint32_t function_40aaf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t base = run.get(0x537e88);
    uint32_t record = run.get(base + 0x6c);
    if (run.get(record + 0x1c) == 0x1390)
        run.call(0x41fe80, record);
    function_44e0c0(run, receiver, arguments);
    return 0;
}

// 0x40e5b0. Runs 0x44cfd0, then clears a global.
uint32_t function_40e5b0(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x44cfd0, receiver);
    run.put(0x5349dc, 0);
    return 0;
}

// 0x40e1b0. Copies +0x210..+0x21c into the object at +0xc (+0x138..), mirrors
// when bit 1 of the state flags is set, copies +0x3a4 to +0x3b0.
uint32_t function_40e1b0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t object = run.get(receiver + 0xc);
    uint32_t destination = object + 0x138;
    uint32_t source = receiver + 0x210;
    uint32_t word0 = run.get(source);
    run.put(destination, word0);
    uint32_t word1 = run.get(source + 4);
    run.put(destination + 4, word1);
    uint32_t word2 = run.get(source + 8);
    run.put(destination + 8, word2);
    uint32_t word3 = run.get(source + 0xc);
    run.put(destination + 0xc, word3);
    uint32_t state = run.get(receiver + 0x12c);
    if ((run.get8(state + 0x40) & 2) != 0) {
        uint32_t object2 = run.get(receiver + 0xc);
        uint32_t second = run.get(object2 + 0x140);
        uint32_t first = run.get(object2 + 0x138);
        run.put(object2 + 0x138, 0u - second);
        uint32_t object3 = run.get(receiver + 0xc);
        run.put(object3 + 0x140, 0u - first);
    }
    uint32_t value = run.get(receiver + 0x3a4);
    run.put(receiver + 0x3b0, value);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x43ed70:
        return function_43ed70(run, receiver, arguments);
    case 0x43eee0:
        return function_43eee0(run, receiver, arguments);
    case 0x43ee10:
        return function_43ee10(run, receiver, arguments);
    case 0x43efe0:
        return function_43efe0(run, receiver, arguments);
    case 0x43fa10:
        return function_43fa10(run, receiver, arguments);
    case 0x44e0c0:
        return function_44e0c0(run, receiver, arguments);
    case 0x40a440:
        return function_40a440(run, receiver, arguments);
    case 0x40aaf0:
        return function_40aaf0(run, receiver, arguments);
    case 0x40e5b0:
        return function_40e5b0(run, receiver, arguments);
    case 0x40e1b0:
        return function_40e1b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_enemy_base_virtuals_02_entry, owned, body)
