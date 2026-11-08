// Level 9 crazy hook closure, translated from the v1.0 instruction packet.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x434250: case 0x434860: case 0x434950: case 0x434d30:
    case 0x435140: case 0x4353a0:
        return 1;
    case 0x434880: case 0x434eb0: case 0x4350e0: case 0x4354e0:
    case 0x4355a0: case 0x435600: case 0x435700: case 0x435720: case 0x435740:
        return 0;
    default:
        return -1;
    }
}

uint32_t animation(Run &run, uint32_t self, uint32_t name) {
    uint32_t value = run.call(0x4062e0, self + 0x128, {name});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    return value;
}

uint32_t resourceMap(Run &run, uint32_t self, uint32_t offset) {
    return run.get(run.get(run.get(self + 0x12c) + 0x0c) + offset);
}

uint32_t stateString(Run &run, uint32_t self) {
    uint32_t result = run.call(0x441030, 0x537698, {run.get(run.get(self + 0x10) + 0x1c)});
    uint32_t entry = run.get(0x5376b4);
    uint32_t count = run.get(0x5376b8);
    while (count) {
        if (entry)
            run.call(0x4f6439, entry);
        entry += 4;
        --count;
    }
    return run.get(result);
}

// Preserve the instruction-derived sound CALL frame: nested COM calls expose
// their real stack output addresses to physical services.
void sound(Run &run, uint32_t value, uint32_t entryESP) {
    if (value && run.get(0x532c0c)) {
        uint32_t saved = run.stackPointer;
        run.stackPointer = entryESP;
        run.call(0x4b45f0, run.get(value + 0x10), {run.get(0x532c10), 0, 0, 0});
        run.stackPointer = saved;
    }
}

uint32_t random(Run &run) {
    return run.call(0x4a3050, 0);
}

uint32_t signedPair(uint32_t value) {
    return uint32_t(s32(value) % 2);
}

void copyRect(Run &run, uint32_t destination, uint32_t source) {
    run.put(destination, run.get(source));
    run.put(destination + 0x04, run.get(source + 0x04));
    run.put(destination + 0x08, run.get(source + 0x08));
    run.put(destination + 0x0c, run.get(source + 0x0c));
}

void facing(Run &run, uint32_t self) {
    run.call(run.get(self + 0x18c) == 2 ? 0x4357a0 : 0x406310, self + 0x128);
}

// 0x4350e0. Reset the home state with its occasional spoken cue.
uint32_t home(Run &run, uint32_t self) {
    if (run.get(self + 0x184) != 6 && s32(random(run)) % 100 < 20) {
        uint32_t index = signedPair(random(run));
        run.call(0x48ce40, 0, {run.get(self + 0x0c), run.get(self + 0x458 + index * 4), 0});
    }
    run.call(0x44f1b0, self);
    return 0;
}

void fpDouble(Run &run, ClawX87State &fp, double value, uint32_t operation) {
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    run.x87_step(operation, fp, {uint32_t(bits), uint32_t(bits >> 32)});
}

uint32_t fpInteger(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

// 0x434250. Constructor. Animation pointers occupy +0x308 through +0x488;
// +0x12c is the actor, +0x0c its controller, +0x48c/+0x490 the attack clock.
uint32_t construct(Run &run, uint32_t self, uint32_t argument) {
    auto fp = run.x87_entry(0x434250);
    fp.popCount = 0;
    fp.pushCount = 0;
    run.call_x87_exact(0x44c000, self, fp, {argument});
    run.put(self + 0x48c, 0);
    run.put(self + 0x490, 0);
    run.put(self, 0x50c85c);
    run.call(0x4c7970, run.get(self + 0x12c), {0x526a1c});
    run.put(self + 0x308, animation(run, self, 0x526a04));
    run.put(self + 0x30c, animation(run, self, 0x5269e8));
    run.put(self + 0x338, animation(run, self, 0x5269d0));
    run.put(self + 0x334, animation(run, self, 0x5269b8));
    run.put(self + 0x350, animation(run, self, 0x5269a0));
    run.put(self + 0x33c, animation(run, self, 0x526988));
    run.put(self + 0x32c, animation(run, self, 0x52696c));
    run.put(self + 0x374, animation(run, self, 0x52696c));
    run.put(self + 0x378, animation(run, self, 0x526954));
    run.put(self + 0x37c, animation(run, self, 0x52693c));
    run.put(self + 0x484, animation(run, self, 0x526924));
    run.put(self + 0x488, animation(run, self, 0x52690c));
    run.put(self + 0x380, animation(run, self, 0x5268f4));
    run.put(self + 0x36c, animation(run, self, 0x5268f4));
    run.put(self + 0x384, animation(run, self, 0x5268dc));
    run.put(self + 0x388, animation(run, self, 0x5268dc));
    run.put(self + 0x34c, animation(run, self, 0x5269e8));
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    run.call(0x4f6286, resourceMap(run, self, 0x28) + 0x10, {0x5268c0, local});
    run.put(self + 0x3a4, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, resourceMap(run, self, 0x28) + 0x10, {0x5268a4, local});
    run.put(self + 0x450, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, resourceMap(run, self, 0x28) + 0x10, {0x526888, local});
    run.put(self + 0x454, run.get(local));
    run.put(self + 0x458, run.call(0x4061b0, resourceMap(run, self, 0x28), {0x52686c}));
    run.put(self + 0x45c, run.call(0x4061b0, resourceMap(run, self, 0x28), {0x526850}));
    run.put(self + 0x464, run.call(0x4061b0, resourceMap(run, self, 0x28), {0x526834}));
    run.put(self + 0x468, run.call(0x4061b0, resourceMap(run, self, 0x28), {0x526818}));
    run.put(self + 0x460, run.call(0x4061b0, resourceMap(run, self, 0x28), {0x5267fc}));
    run.put(self + 0x46c, run.call(0x4061b0, resourceMap(run, self, 0x28), {0x5267e0}));
    run.put(self + 0x470, run.call(0x4061b0, resourceMap(run, self, 0x28), {0x5267c4}));
    run.put(self + 0x474, run.call(0x4061b0, resourceMap(run, self, 0x28), {0x5267ac}));
    run.put(self + 0x478, run.call(0x4061b0, resourceMap(run, self, 0x28), {0x526794}));
    run.put(self + 0x47c, run.call(0x4061b0, resourceMap(run, self, 0x28), {0x526778}));
    uint32_t value = run.call(0x4061b0, resourceMap(run, self, 0x28), {0x52675c});
    uint32_t setRect = run.get(0x546d5c);
    run.put(self + 0x480, value);
    run.call(setRect, 0, {self + 0x230, uint32_t(-67), uint32_t(-46), uint32_t(-18), 26});
    run.call(setRect, 0, {self + 0x240, uint32_t(-80), 10, uint32_t(-30), 34});
    copyRect(run, self + 0x220, self + 0x230);
    run.call(setRect, 0, {self + 0x210, 0xffffffff, 0xffffffff, 1, 1});
    run.call(0x4296f0, self + 0x250, {uint32_t(-20), uint32_t(-60), 20, 61});
    run.call(0x4296f0, self + 0x260, {uint32_t(-20), uint32_t(-15), 20, 15});
    run.call(0x40ab80, self + 0x128, {uint32_t(-20), uint32_t(-50), 20, 50});
    run.call(0x40abb0, self + 0x128, {self + 0x250});
    run.put(self + 0x28c, 500);
    run.put(self + 0x290, 40);
    run.put(self + 0x29c, 200);
    run.put(self + 0x2a0, 40);
    run.put(self + 0x2a4, 100);
    run.put(self + 0x2a8, 40);
    run.put(self + 0x2ac, 100);
    run.put(self + 0x2b0, 40);
    run.put(self + 0x2b4, 10);
    run.put(self + 0x2b8, uint32_t(-10));
    run.put(self + 0x2bc, uint32_t(-45));
    run.put(self + 0x2c0, uint32_t(-20));
    run.put(self + 0x2c4, 20);
    run.put(self + 0x2c8, uint32_t(-15));
    run.put(self + 0x2e4, 50);
    fpDouble(run, fp, double(run.getf(0x5262b8)), CLAW_X87_F64);
    fpDouble(run, fp, double(run.getf(0x50c850)), CLAW_X87_MUL_F64);
    value = fpInteger(run, fp);
    run.put(self + 0x2e4, value > 99 ? value : 99);
    run.put(run.get(self + 0x0c) + 0x10c, 10);
    uint32_t controller = run.get(self + 0x0c);
    run.x87_step(CLAW_X87_I32, fp, {run.get(controller + 0x10c)});
    fpDouble(run, fp, double(run.getf(0x5262b4)), CLAW_X87_MUL_F64);
    run.put(controller + 0x10c, fpInteger(run, fp));
    run.put(run.get(self + 0x0c) + 0x104, 10);
    controller = run.get(self + 0x0c);
    run.x87_step(CLAW_X87_I32, fp, {run.get(controller + 0x104)});
    fpDouble(run, fp, double(run.getf(0x5262b0)), CLAW_X87_MUL_F64);
    run.put(controller + 0x104, fpInteger(run, fp));
    run.put(self + 0x494, 0);
    run.call(0x40abf0, self + 0x128);
    home(run, self);
    run.x87_finish(0x434250, fp);
    return self;
}

// 0x434880. Destructor, including string and table members.
void destruct(Run &run, uint32_t self) {
    run.put(self, 0x50b16c);
    run.call(0x4dbcd0, self + 0x2f4);
    run.call(0x4f6584, self + 0x1a8);
    run.call(0x4f6584, self + 0x1a4);
    run.put(self, 0x50b014);
}

uint32_t dispatchSlot(Run &run, uint32_t id) {
    run.put(0x537358, 0);
    if (s32(id) < run.gets(0x537340) || s32(id) > run.gets(0x537344)) {
        if (!run.call(0x4db6e0, 0x537338, {id, 0})) {
            uint32_t context = run.get(0x544b4c);
            uint32_t result = run.call(0x4db5f0, 0);
            run.put(0x544b14, result);
            run.call(0x4db4d0, run.get(0x53733c), {0x537338, context, 12});
            return run.get(0x53734c);
        }
    }
    return (id - run.get(0x537340)) * run.get(0x537350) + run.get(0x537348);
}

// 0x434950. Dispatch a registered state, otherwise use the actor base callback.
void dispatchState(Run &run, uint32_t self, uint32_t id) {
    uint32_t slot = dispatchSlot(run, id);
    if (run.get(slot)) {
        slot = dispatchSlot(run, id);
        run.call(run.get(slot), self);
    } else {
        run.call(0x44c840, self, {id});
    }
}

// 0x434d30. Select the attack rectangle, animation and spoken state.
uint32_t attack(Run &run, uint32_t self, uint32_t argument) {
    run.call(0x44d000, self, {argument});
    uint32_t state = run.get(self + 0x184);
    if (state >= 1 && state <= 4) {
        uint32_t local = run.automatic(4);
        run.put(local, 0);
        copyRect(run, self + 0x220, self + (state <= 2 ? 0x230 : 0x240));
        run.call(0x4f6286, resourceMap(run, self, 0x2c) + 0x10, {state <= 2 ? 0x526924u : 0x52690cu, local});
        uint32_t value = run.get(local);
        if (!value) {
            uint32_t fallback = run.automatic(-4);
            run.put(fallback, 0);
            run.call(0x4f6286, resourceMap(run, self, 0x2c) + 0x10, {0x5234b4, fallback});
            value = run.get(fallback);
        }
        uint32_t cue = run.get(self + (state <= 2 ? 0x470 : 0x46c));
        run.put(self + 0x310, value);
        run.put(self + 0x3a0, cue);
    }
    uint32_t roll = random(run);
    uint32_t result = uint32_t(s32(roll) / 100);
    if (s32(roll) % 100 < 20) {
        uint32_t actor = run.get(self + 0x12c);
        result = run.get(actor + 0x164) & 0xfffffffe;
        run.put(actor + 0x164, result);
    }
    return result;
}

// 0x4355a0. Enter the hook-holding state.
uint32_t hold(Run &run, uint32_t self) {
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x526a2c});
    run.put(run.get(self + 0x10) + 0x1c, state);
    uint32_t actor = run.get(self + 0x12c);
    run.put(self + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {run.get(self + 0x384)});
    run.put(self + 0x490, 1000);
    run.put(self + 0x48c, run.get(0x537210));
    return 0;
}

// 0x4354e0. Enter the blocking state and select its sound.
uint32_t block(Run &run, uint32_t self) {
    run.put(self + 0x20, 1);
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x526a38});
    run.put(run.get(self + 0x10) + 0x1c, state);
    uint32_t actor = run.get(self + 0x12c);
    run.put(self + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {run.get(self + 0x384)});
    actor = run.get(self + 0x12c);
    run.put(actor + 0x08, run.get(actor + 0x08) | 4);
    // Saved ESI, four operands and the CALL return word.
    sound(run, run.get(self + 0x474 + signedPair(random(run)) * 4), run.automatic(-0x18));
    if (s32(random(run)) % 100 < 40)
        run.call(0x48ce40, 0, {run.get(self + 0x0c), run.get(self + 0x460), 0});
    return 0;
}

// 0x434eb0. Home-state decision, cooldown and proximity cue.
uint32_t updateHome(Run &run, uint32_t self) {
    if (!run.get(self + 0x494)) {
        bool nearby = false;
        if (run.get(0x534eac) != 0x26b7) {
            uint32_t position = run.get(self + 0x194);
            uint32_t world = run.get(run.get(run.get(self + 0x190) + 0x0c) + 0x24);
            uint32_t player = run.get(0x537e88);
            if (run.call(0x4cda10, world, {run.get(position + 0x4c), run.get(position + 0x50), run.get(player + 0x4c), 32})) {
                position = run.get(self + 0x194);
                player = run.get(0x537e88);
                uint32_t y = run.get(position + 0x50);
                nearby = run.gets(player + 0x50) < s32(y + 50) && run.gets(player + 0x50) > s32(y - 50) && run.get(position + 0x38) != 0xffffffff;
            }
        }
        if (nearby) {
            if (s32(random(run)) % 100 < 70) {
                uint32_t cue = run.get(self + 0x450 + signedPair(random(run)) * 4);
                run.call(0x48ce40, 0, {run.get(self + 0x0c), cue, 0});
            }
            run.put(self + 0x494, 1);
        }
    }
    facing(run, self);
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
    int32_t roll = s32(random(run)) % 121;
    uint32_t state = run.get(self + 0x184);
    switch (state) {
    case 0:
        run.call(0x44ebb0, self);
        return 0;
    case 1: case 2:
        if (run.get(0x537210) - run.get(self + 0x48c) >= run.get(self + 0x490) && roll < 60) {
            if (run.get(0x537964) == 9 && roll < 30)
                hold(run, self);
            else
                run.vcall(self, 0x58);
            run.put(self + 0x490, 2000);
            run.put(self + 0x48c, run.get(0x537210));
            return 0;
        }
        if (roll < s32(run.get(self + 0x2e4) + 30))
            run.call(state == 1 ? 0x44ebb0 : 0x4a1180, self);
        return 0;
    case 3:
        if (roll >= run.gets(self + 0x2e4))
            return 0;
        break;
    case 4:
        break;
    case 5: case 6:
        run.call(0x44edd0, self);
        return 0;
    default:
        return 0;
    }
    if (run.get(0x537210) - run.get(self + 0x48c) >= run.get(self + 0x490)) {
        run.vcall(self, 0x58);
        run.put(self + 0x490, 1000);
        run.put(self + 0x48c, run.get(0x537210));
    }
    return 0;
}

// 0x435700 and 0x435720. Complete the selected strike and stop motion.
void finishStrike(Run &run, uint32_t self, bool high) {
    run.call(high ? 0x44f510 : 0x44f3c0, self);
    run.put(self + 0x50, 0);
    run.put(self + 0x54, 0);
}

// 0x435140. Attack response with Level 9 hook/block special handling.
void hit(Run &run, uint32_t self, uint32_t argument) {
    if (run.get(0x537964) == 9) {
        uint32_t player = run.get(0x537e88);
        uint32_t mode = run.get(run.get(run.get(player + 0x6c) + 0x14) + 0x3c);
        if ((mode == 1 || mode == 2 || mode == 7 || mode == 8) && run.get(player + 0xcc) == 1) {
            facing(run, self);
            uint32_t parentFrame = run.frame;
            run.frame -= 0x18;
            block(run, self);
            run.frame = parentFrame;
            return;
        }
    }
    run.vcall(self, 0x28, {argument});
    run.call(0x440e20, self, {argument});
    run.call(0x43e9c0, self, {300});
    if (!run.call(0x4a3810, 0, {stateString(run, self), 0x523204})) {
        run.vcall(self, 0x44);
        return;
    }
    if (!run.call(0x4a3810, 0, {stateString(run, self), 0x523210})) {
        run.vcall(self, 0x44);
        return;
    }
    // One local, four saved registers, four operands and the return word.
    sound(run, run.get(self + 0x47c + signedPair(random(run)) * 4), run.automatic(-0x28));
    uint32_t player = run.get(0x537e88);
    bool high = run.get(run.get(run.get(player + 0x6c) + 0x14) + 0x14) != 0;
    finishStrike(run, self, high);
    if (run.gets(run.get(self + 0x0c) + 0x10c) <= 0)
        return;
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    copyRect(run, self + 0x220, self + 0x230);
    run.call(0x4f6286, resourceMap(run, self, 0x2c) + 0x10, {0x526924, local});
    uint32_t value = run.get(local);
    if (!value) {
        uint32_t fallback = run.automatic(-4);
        run.put(fallback, 0);
        run.call(0x4f6286, resourceMap(run, self, 0x2c) + 0x10, {0x5234b4, fallback});
        value = run.get(fallback);
    }
    run.put(self + 0x310, value);
    run.vcall(self, 0x58);
}

// 0x4353a0. The held hook blocks; other states take the normal hit.
void heldHit(Run &run, uint32_t self, uint32_t argument) {
    if (run.call(0x4a3810, 0, {stateString(run, self), 0x526a2c})) {
        // Four saved registers, four operands and the return word.
        sound(run, run.get(self + 0x47c + signedPair(random(run)) * 4), run.automatic(-0x24));
        run.call(0x44d570, self, {argument});
        return;
    }
    uint32_t actor = run.get(self + 0x12c);
    bool left = run.get(self + 0x18c) == 2;
    if (left != bool(run.get8(actor + 0x40) & 2)) {
        uint32_t old = run.get(self + 0x138);
        uint32_t opposite = run.get(self + 0x140);
        run.put(self + 0x138, 0u - opposite);
        run.put(self + 0x140, 0u - old);
        uint32_t flags = run.get(actor + 0x40);
        run.put(actor + 0x40, left ? flags | 2 : flags & 0xfffffffd);
        actor = run.get(self + 0x12c);
        run.call(0x406120, actor);
        run.call(0x406150, actor);
        run.call(0x406180, actor);
    }
    uint32_t parentFrame = run.frame;
    run.frame -= 0x14;
    block(run, self);
    run.frame = parentFrame;
}

// 0x435600. Publish the hook rectangle and leave when its clock expires.
uint32_t updateHold(Run &run, uint32_t self) {
    uint32_t actor = run.get(self + 0x12c);
    uint32_t frame = run.get(actor + 0x174);
    if (frame) {
        run.put(self + 0x220, run.get(frame + 0x20) - run.get(frame + 0x18));
        frame = run.get(actor + 0x174);
        run.put(self + 0x224, run.get(frame + 0x24) - run.get(frame + 0x1c));
        frame = run.get(actor + 0x174);
        run.put(self + 0x228, run.get(frame + 0x20) + run.get(frame + 0x18) - 1);
        frame = run.get(actor + 0x174);
        run.put(self + 0x22c, run.get(frame + 0x24) + run.get(frame + 0x1c) - 1);
    }
    uint32_t controller = run.get(self + 0x0c);
    copyRect(run, controller + 0x138, self + 0x220);
    if (run.get8(run.get(self + 0x12c) + 0x40) & 2) {
        controller = run.get(self + 0x0c);
        uint32_t old = run.get(controller + 0x138);
        run.put(controller + 0x138, 0u - run.get(controller + 0x140));
        run.put(run.get(self + 0x0c) + 0x140, 0u - old);
    }
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (run.get(0x537210) - run.get(self + 0x48c) >= run.get(self + 0x490))
        run.vcall(self, 0x44);
    return 0;
}

// 0x435740. Release the hook and select its cue.
uint32_t release(Run &run, uint32_t self) {
    run.call(0x48cf50, 0, {run.get(self + 0x0c)});
    bool rare = s32(random(run)) % 100 < 35;
    run.call(0x48ce40, 0, {run.get(self + 0x0c), run.get(self + (rare ? 0x468 : 0x464)), 0});
    run.call(0x440420, self);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t self, const uint32_t *arguments) {
    switch (function) {
    case 0x434250:
        return construct(run, self, arguments[0]);
    case 0x434860:
        destruct(run, self);
        if (arguments[0] & 1)
            run.call(0x4f6428, 0, {self});
        return self;
    case 0x434880:
        destruct(run, self);
        return 0;
    case 0x434950:
        dispatchState(run, self, arguments[0]);
        return 0;
    case 0x434d30:
        return attack(run, self, arguments[0]);
    case 0x434eb0:
        return updateHome(run, self);
    case 0x4350e0:
        return home(run, self);
    case 0x435140:
        hit(run, self, arguments[0]);
        return 0;
    case 0x4353a0:
        heldHit(run, self, arguments[0]);
        return 0;
    case 0x4354e0:
        return block(run, self);
    case 0x4355a0:
        return hold(run, self);
    case 0x435600:
        return updateHold(run, self);
    case 0x435700:
        finishStrike(run, self, true);
        return 0;
    case 0x435720:
        finishStrike(run, self, false);
        return 0;
    case 0x435740:
        return release(run, self);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_level_nine_crazy_hook_01_entry, owned, body)
