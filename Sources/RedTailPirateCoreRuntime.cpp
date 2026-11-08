// Red tail pirate construction and state behavior, recovered from v1.0.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4828e0:
    case 0x483090:
    case 0x483180:
    case 0x483560:
    case 0x483e10:
        return 1;
    case 0x4830b0:
    case 0x4837b0:
    case 0x483ae0:
    case 0x483d20:
    case 0x483f30:
    case 0x484210:
    case 0x484240:
    case 0x484260:
        return 0;
    default:
        return -1;
    }
}

// +0x12c is the animated actor, whose +0x0c owns resource banks.
uint32_t bank(Run &run, uint32_t receiver, uint32_t offset) {
    return run.get(run.get(run.get(receiver + 0x12c) + 0x0c) + offset);
}

uint32_t animation(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t value = run.call(0x4062e0, receiver + 0x128, {name});
    if (!value)
        value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    return value;
}

void copyRect(Run &run, uint32_t destination, uint32_t source) {
    run.put(destination + 0x00, run.get(source + 0x00));
    run.put(destination + 0x04, run.get(source + 0x04));
    run.put(destination + 0x08, run.get(source + 0x08));
    run.put(destination + 0x0c, run.get(source + 0x0c));
}

ClawX87State emptyFP() {
    ClawX87State state{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
    return state;
}

void fpBits(Run &run, ClawX87State &fp, uint32_t operation, uint64_t bits) {
    run.x87_step(operation, fp, {uint32_t(bits), uint32_t(bits >> 32)});
}

void fpMemory(Run &run, ClawX87State &fp, uint32_t operation, uint32_t address) {
    run.x87_step(operation, fp, {run.get(address), run.get(address + 0x04)});
}

void fpFloat(Run &run, ClawX87State &fp, uint32_t operation, uint32_t address) {
    double value = run.getf(address);
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    fpBits(run, fp, operation, bits);
}

uint32_t convert(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

void balancedCall(Run &run, ClawX87State &fp, uint32_t function, uint32_t receiver) {
    fp.popCount = 0;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    run.call_x87_exact(function, receiver, fp);
}

// 0x4828e0. Construction; animation handles and encounter-specific defaults.
uint32_t construct(Run &run, uint32_t receiver, uint32_t actor) {
    auto fp = run.x87_entry(0x4828e0);
    run.call_x87_exact(0x44c000, receiver, fp, {actor});
    run.put(receiver + 0x494, 0);
    run.put(receiver + 0x498, 0);
    run.put(receiver + 0x49c, 0);
    run.put(receiver + 0x4a0, 0);
    run.put(receiver + 0x4a4, 0);
    run.put(receiver + 0x4a8, 0);
    run.put(receiver + 0x00, 0x50f394);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x52ba74});
    run.put(receiver + 0x308, animation(run, receiver, 0x52ba58));
    run.put(receiver + 0x30c, animation(run, receiver, 0x52ba38));
    run.put(receiver + 0x338, animation(run, receiver, 0x52ba1c));
    run.put(receiver + 0x334, animation(run, receiver, 0x52ba00));
    run.put(receiver + 0x350, animation(run, receiver, 0x52b9e4));
    run.put(receiver + 0x34c, animation(run, receiver, 0x52ba38));
    run.put(receiver + 0x33c, animation(run, receiver, 0x52b9c8));
    run.put(receiver + 0x340, animation(run, receiver, 0x52b9c8));
    run.put(receiver + 0x32c, animation(run, receiver, 0x52b9a8));
    run.put(receiver + 0x374, animation(run, receiver, 0x52b9a8));
    run.put(receiver + 0x378, animation(run, receiver, 0x52b98c));
    run.put(receiver + 0x37c, animation(run, receiver, 0x52b970));
    run.put(receiver + 0x310, animation(run, receiver, 0x52b954));
    run.put(receiver + 0x380, animation(run, receiver, 0x52b938));
    run.put(receiver + 0x36c, animation(run, receiver, 0x52b938));
    run.put(receiver + 0x384, animation(run, receiver, 0x52b91c));
    run.put(receiver + 0x388, animation(run, receiver, 0x52b91c));
    run.put(receiver + 0x344, animation(run, receiver, 0x52b900));
    run.put(receiver + 0x34c, animation(run, receiver, 0x52ba58));
    run.put(receiver + 0x454, animation(run, receiver, 0x52b8e0));
    uint32_t local = run.automatic(0x04);
    run.put(local, 0);
    run.call(0x4f6286, bank(run, receiver, 0x28) + 0x10, {0x52b8c0, local});
    run.put(receiver + 0x3a4, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, bank(run, receiver, 0x28) + 0x10, {0x52b8a0, local});
    run.put(receiver + 0x458, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, bank(run, receiver, 0x28) + 0x10, {0x52b880, local});
    run.put(receiver + 0x45c, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, bank(run, receiver, 0x28) + 0x10, {0x52b860, local});
    run.put(receiver + 0x460, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, bank(run, receiver, 0x28) + 0x10, {0x52b840, local});
    run.put(receiver + 0x464, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, bank(run, receiver, 0x28) + 0x10, {0x52b820, local});
    run.put(receiver + 0x468, run.get(local));
    run.put(receiver + 0x46c, run.call(0x4061b0, bank(run, receiver, 0x28), {0x52b800}));
    run.put(receiver + 0x470, run.call(0x4061b0, bank(run, receiver, 0x28), {0x52b7e0}));
    run.put(receiver + 0x474, run.call(0x4061b0, bank(run, receiver, 0x28), {0x52b7c0}));
    run.put(receiver + 0x478, run.call(0x4061b0, bank(run, receiver, 0x28), {0x52b7a0}));
    run.put(receiver + 0x47c, run.call(0x4061b0, bank(run, receiver, 0x28), {0x52b780}));
    run.put(receiver + 0x480, run.call(0x4061b0, bank(run, receiver, 0x28), {0x52b760}));
    run.put(receiver + 0x484, run.call(0x4061b0, bank(run, receiver, 0x28), {0x52b740}));
    run.put(receiver + 0x488, run.call(0x4061b0, bank(run, receiver, 0x28), {0x52b720}));
    run.put(receiver + 0x48c, run.call(0x4061b0, bank(run, receiver, 0x28), {0x52b704}));
    run.put(receiver + 0x490, run.call(0x4061b0, bank(run, receiver, 0x28), {0x52b6e8}));
    uint32_t setRect = run.get(0x546d5c);
    run.call(setRect, 0, {receiver + 0x240, 0xffffffa0, 0x1d, 4, 0x4a});
    run.call(setRect, 0, {receiver + 0x230, 0xffffffa0, 0xffffffce, 0xffffffec, 0x32});
    copyRect(run, receiver + 0x220, receiver + 0x230);
    run.call(setRect, 0, {receiver + 0x210, 0xffffffff, 0xffffffff, 1, 1});
    run.call(setRect, 0, {receiver + 0x250, 0xffffffec, 0xffffffc4, 0x14, 0x3d});
    run.call(setRect, 0, {receiver + 0x260, 0xffffffec, 0xfffffff1, 0x14, 0x0f});
    run.call(0x4208b0, run.get(receiver + 0x12c), {0xffffffec, 0xffffffce, 0x14, 0x32});
    run.call(0x40f6c0, run.get(receiver + 0x12c), {run.get(receiver + 0x250), run.get(receiver + 0x254), run.get(receiver + 0x258), run.get(receiver + 0x25c)});
    uint32_t encounter = run.get(0x53774c);
    if (encounter && !run.get(encounter + 0x520)) {
        for (uint32_t i = 0; s32(i) < run.gets(receiver + 0x14c); ++i)
            run.put(receiver + 0x154 + i * 4, 0);
        uint32_t animated = run.get(receiver + 0x12c);
        run.put(animated + 0x164, run.get(animated + 0x164) | 0x2000);
        animated = run.get(receiver + 0x12c);
        run.put(animated + 0x08, run.get(animated + 0x08) | 2);
        run.put(receiver + 0x28c, 10000);
        run.put(receiver + 0x290, 10000);
        run.put(receiver + 0x294, 5000);
        run.put(receiver + 0x298, 5000);
    } else {
        run.put(receiver + 0x28c, 500);
        run.put(receiver + 0x290, 0x28);
        run.put(receiver + 0x294, 200);
        run.put(receiver + 0x298, 0x28);
    }
    run.put(receiver + 0x29c, 200);
    run.put(receiver + 0x2a0, 0x28);
    run.put(receiver + 0x2a4, 100);
    run.put(receiver + 0x2a8, 0x28);
    run.put(receiver + 0x2ac, 0x3c);
    run.put(receiver + 0x2b0, 0x28);
    run.put(receiver + 0x4ac, 0);
    run.put(receiver + 0x4b0, 0);
    run.put(receiver + 0x404, 0xf0);
    run.put(receiver + 0x400, 0x78);
    run.put(receiver + 0x450, 0x5a);
    run.put(receiver + 0x2b4, 10);
    run.put(receiver + 0x2b8, 0xfffffff6);
    run.put(receiver + 0x2bc, 0xffffffd3);
    run.put(receiver + 0x2c0, 0xffffffec);
    run.put(receiver + 0x2c4, 0x14);
    run.put(receiver + 0x2c8, 0xfffffff1);
    run.put(receiver + 0x2e4, 0x32);
    fpFloat(run, fp, CLAW_X87_F64, 0x5262b8);
    fpFloat(run, fp, CLAW_X87_MUL_F64, 0x50f360);
    uint32_t chance = convert(run, fp);
    if (chance <= 99)
        chance = 99;
    run.put(receiver + 0x2e4, chance);
    run.put(run.get(receiver + 0x0c) + 0x10c, 10);
    actor = run.get(receiver + 0x0c);
    run.x87_step(CLAW_X87_I32, fp, {run.get(actor + 0x10c)});
    fpFloat(run, fp, CLAW_X87_MUL_F64, 0x5262b4);
    run.put(actor + 0x10c, convert(run, fp));
    run.put(run.get(receiver + 0x0c) + 0x104, 10);
    actor = run.get(receiver + 0x0c);
    run.x87_step(CLAW_X87_I32, fp, {run.get(actor + 0x104)});
    fpFloat(run, fp, CLAW_X87_MUL_F64, 0x5262b0);
    run.put(actor + 0x104, convert(run, fp));
    balancedCall(run, fp, 0x40abf0, receiver + 0x128);
    run.call(0x44f1b0, receiver);
    run.x87_finish(0x4828e0, fp);
    return receiver;
}

// 0x4830b0. Embedded container and string destruction.
uint32_t destroy(Run &run, uint32_t receiver) {
    run.put(receiver + 0x00, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver + 0x00, 0x50b014);
    return 0;
}

// 0x483090. Scalar deleting destructor.
uint32_t deleteObject(Run &run, uint32_t receiver, uint32_t flag) {
    destroy(run, receiver);
    if (flag & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

uint32_t registrySlot(Run &run, uint32_t key, uint32_t returnPC) {
    uint32_t lower = run.get(0x53c1b0);
    run.put(0x53c1c8, 0);
    if (s32(key) < s32(lower) || s32(key) > run.gets(0x53c1b4)) {
        if (!run.call(0x4db6e0, 0x53c1a8, {key, 0})) {
            uint32_t message = run.get(0x544b4c);
            // The manifest exempts this unreachable original allocation-error
            // block. Ordinary bridging cannot transport its original CALL PC.
            (void)returnPC;
            uint32_t pc = run.call(0x4db5f0, 0);
            run.put(0x544b14, pc);
            run.call(0x4db4d0, run.get(0x53c1ac), {0x53c1a8, message, 0x0c});
            return run.get(0x53c1bc);
        }
        lower = run.get(0x53c1b0);
    }
    return (key - lower) * run.get(0x53c1c0) + run.get(0x53c1b8);
}

// 0x483180. Registry state dispatch, falling back to the base transition.
uint32_t dispatchState(Run &run, uint32_t receiver, uint32_t key) {
    uint32_t slot = registrySlot(run, key, 0x4831e0);
    if (run.get(slot)) {
        slot = registrySlot(run, key, 0x48325a);
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x44c840, receiver, {key});
    }
    return 0;
}

// 0x483560. Update, counterattack chance, and current strike resource.
uint32_t update(Run &run, uint32_t receiver, uint32_t argument) {
    uint32_t encounter = run.get(0x53774c);
    if (encounter) {
        if (run.get(encounter + 0x520)) {
            run.vcall(receiver, 0x5c, {1});
            return 0;
        }
        uint32_t name = run.call(0x406020, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
        if (!run.call(0x4a3810, 0, {run.get(name), 0x52ba88}))
            return 0;
        name = run.call(0x406020, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
        if (!run.call(0x4a3810, 0, {run.get(name), 0x527204}))
            return 0;
    }
    run.call(0x44d000, receiver, {argument});
    uint32_t detail = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    uint32_t facing = run.get(receiver + 0x18c);
    uint32_t state = run.get(receiver + 0x184);
    if (run.get(detail + 0x04) && ((facing == 3 && run.get(detail)) || (facing == 2 && !run.get(detail))) &&
        (state == 3 || state == 4) && run.get(0x537210) - run.get(receiver + 0x4a4) >= run.get(receiver + 0x4a8)) {
        uint32_t chance = run.get(receiver + 0x450);
        if (s32(run.call(0x4a3050, 0)) % 100 < s32(chance)) {
            if (run.gets(receiver + 0x20) >= 2)
                run.put(receiver + 0x14, 0x44e620);
            chance = run.get(receiver + 0x450) - 0x1e;
            run.put(receiver + 0x450, chance);
            if (s32(chance) < 0)
                run.put(receiver + 0x450, 0);
            run.put(receiver + 0x4a8, 500);
            run.put(receiver + 0x4a4, run.get(0x537210));
        }
    }
    bool second = run.get(run.get(0x537e88) + 0xcc) == 5;
    uint32_t output = run.automatic(0x04);
    run.put(output, 0);
    copyRect(run, receiver + 0x220, receiver + (second ? 0x240 : 0x230));
    run.call(0x4f6286, bank(run, receiver, 0x2c) + 0x10, {second ? 0x52baacU : 0x52b954U, output});
    uint32_t value = run.get(output);
    if (!value) {
        output = run.automatic(-0x04);
        run.put(output, 0);
        run.call(0x4f6286, bank(run, receiver, 0x2c) + 0x10, {0x5234b4, output});
        value = run.get(output);
    }
    run.put(receiver + 0x310, value);
    return 0;
}

bool nearby(Run &run, uint32_t receiver) {
    if (run.get(0x534eac) == 0x26b7)
        return false;
    uint32_t target = run.get(receiver + 0x194);
    uint32_t collision = run.get(run.get(run.get(receiver + 0x190) + 0x0c) + 0x24);
    if (!run.call(0x4cda10, collision, {run.get(target + 0x4c), run.get(target + 0x50), run.get(run.get(0x537e88) + 0x4c), 0x20}))
        return false;
    target = run.get(receiver + 0x194);
    uint32_t y = run.get(target + 0x50);
    uint32_t playerY = run.get(run.get(0x537e88) + 0x50);
    return s32(playerY) < s32(y + 0x32) && s32(playerY) > s32(y - 0x32) && run.get(target + 0x38) != 0xffffffff;
}

void faceTarget(Run &run, uint32_t receiver) {
    run.call(run.get(receiver + 0x18c) == 2 ? 0x4357a0 : 0x406310, receiver + 0x128);
}

// 0x4837b0. Idle/combat choices and proximity sound latches.
uint32_t think(Run &run, uint32_t receiver) {
    if (!run.get(receiver + 0x4ac)) {
        if (!run.get(receiver + 0x4b0) && nearby(run, receiver)) {
            if (s32(run.call(0x4a3050, 0)) % 101 < 50) {
                uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 2);
                run.call(0x48ce40, 0, {run.get(receiver + 0x0c), run.get(receiver + 0x47c + index * 4), 0});
            }
            run.put(receiver + 0x4b0, 1);
        }
    }
    if (run.get(receiver + 0x4ac) && nearby(run, receiver)) {
        uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 2);
        run.call(0x48ce40, 0, {run.get(receiver + 0x0c), run.get(receiver + 0x484 + index * 4), 0});
        run.put(receiver + 0x4ac, 0);
    }
    faceTarget(run, receiver);
    int32_t choice = s32(run.call(0x4a3050, 0)) % 121;
    switch (run.get(receiver + 0x184)) {
    case 0:
        run.call(0x44ebb0, receiver);
        return 0;
    case 1:
    case 2:
        if (run.get(0x537210) - run.get(receiver + 0x494) >= run.get(receiver + 0x498) && choice < 60) {
            copyRect(run, receiver + 0x220, receiver + 0x230);
            run.put(receiver + 0x310, animation(run, receiver, 0x52b954));
            run.vcall(receiver, 0x58);
            run.put(receiver + 0x498, 2000);
            run.put(receiver + 0x494, run.get(0x537210));
        } else {
            run.call(0x4a1180, receiver);
        }
        return 0;
    case 3: {
        uint32_t threshold = run.get(receiver + 0x2e4);
        if (choice >= s32(threshold) || run.get(0x537210) - run.get(receiver + 0x494) < run.get(receiver + 0x498)) {
            if (choice < s32(threshold + 0x1e))
                run.vcall(receiver, 0x68);
            return 0;
        }
        break;
    }
    case 4:
        if (s32(run.call(0x4a3050, 0)) % 100 < 50) {
            run.vcall(receiver, 0x64);
            return 0;
        }
        if (run.get(0x537210) - run.get(receiver + 0x494) < run.get(receiver + 0x498))
            return 0;
        break;
    case 5:
    case 6:
        run.put(receiver + 0x450, 0x5a);
        run.call(0x44edd0, receiver);
        return 0;
    default:
        return 0;
    }
    run.vcall(receiver, 0x58);
    run.put(receiver + 0x498, 0xfa);
    run.put(receiver + 0x494, run.get(0x537210));
    return 0;
}

void blockSound(Run &run, uint32_t receiver) {
    uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 2);
    uint32_t sound = run.get(receiver + 0x48c + index * 4);
    if (sound && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
}

// 0x483d20. Enter block state and select the quick-block animation.
uint32_t block(Run &run, uint32_t receiver) {
    run.put(receiver + 0x20, 1);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x526a38});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {run.get(receiver + 0x454)});
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x08, run.get(actor + 0x08) | 4);
    blockSound(run, receiver);
    return 0;
}

// 0x483ae0. Hit response: block, reverse dodge, or base damage reaction.
uint32_t hit(Run &run, uint32_t receiver) {
    uint32_t detail = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (run.get(detail + 0xe8) == run.get(receiver + 0x19c))
        return 0;
    uint32_t object = run.get(run.get(receiver + 0x0c) + 0x74);
    int32_t choice = s32(run.call(0x4a3050, 0)) % 101;
    uint32_t level = run.get(0x537964);
    detail = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    uint32_t state = run.get(detail + 0x3c);
    if ((state == 1 || state == 2 || state == 7 || state == 8) && run.get(object + 0xd0) == 2 &&
        ((level == 8 && choice < 25) || (level == 13 && choice < 50))) {
        faceTarget(run, receiver);
        blockSound(run, receiver);
        run.vcall(receiver, 0x98);
        return 1;
    }
    if (run.get(object + 0xd0) == 0x20 && ((level == 8 && choice < 25) || (level == 13 && choice < 75))) {
        run.put(object + 0x08, run.get(object + 0x08) | 0x10000);
        if (run.get(receiver + 0x18c) == 2) {
            uint32_t actor = run.get(receiver + 0x12c);
            if (!(run.get8(actor + 0x40) & 2)) {
                uint32_t left = run.get(receiver + 0x138);
                uint32_t right = run.get(receiver + 0x140);
                run.put(receiver + 0x138, 0u - right);
                run.put(receiver + 0x140, 0u - left);
                run.put(actor + 0x40, run.get(actor + 0x40) | 2);
                run.call(0x4060b0, run.get(receiver + 0x12c));
            }
        } else {
            run.call(0x406310, receiver + 0x128);
        }
        block(run, receiver);
        return 1;
    }
    run.put(receiver + 0x414, 0);
    run.put(receiver + 0x418, 0);
    if (s32(run.call(0x4a3050, 0)) % 101 <= 10) {
        uint32_t output = run.automatic(-0x04);
        run.put(output, 0);
        run.call(0x4f6286, bank(run, receiver, 0x28) + 0x10, {0x52bae8, output});
        run.put(receiver + 0x414, run.get(output));
        run.put(output, 0);
        run.call(0x4f6286, bank(run, receiver, 0x28) + 0x10, {0x52bac8, output});
        run.put(receiver + 0x418, run.get(output));
    }
    return run.call(0x44df60, receiver);
}

// 0x483e10. Encounter count and base death handling.
uint32_t die(Run &run, uint32_t receiver, uint32_t argument) {
    uint32_t encounter = run.get(0x53774c);
    if (encounter && !run.get(encounter + 0x520))
        run.put(encounter + 0x524, run.get(encounter + 0x524) - 1);
    run.call(0x44e0c0, receiver, {argument});
    return 0;
}

// 0x483f30. Projectile intercept solver. Every x87 operation and binary64
// spill follows the original order; C0/C3 also retain unordered branches.
uint32_t aim(Run &run, uint32_t receiver) {
    if (!run.get(0x53774c))
        return 0;
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    auto fp = emptyFP();
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x68);
    run.x87_step(CLAW_X87_I32, fp, {run.get(run.get(0x53774c) + 0x528)});
    run.x87_step(CLAW_X87_COMPP, fp);
    if (fp.status & 0x0100)
        return 0;
    fpMemory(run, fp, CLAW_X87_F64, 0x513e10);
    uint64_t initial = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(receiver + 0x80, uint32_t(initial));
    run.put(receiver + 0x84, uint32_t(initial >> 32));
    run.put(receiver + 0x98, run.get(0x513e18));
    run.put(receiver + 0x9c, run.get(0x513e1c));
    run.put(receiver + 0x88, run.get(0x513e10));
    run.put(receiver + 0x8c, run.get(0x513e14));
    run.put(receiver + 0xa0, run.get(0x513e18));
    run.put(receiver + 0xa4, run.get(0x513e1c));
    run.put(receiver + 0x90, run.get(0x513e10));
    run.put(receiver + 0x94, run.get(0x513e14));
    run.put(receiver + 0xa8, run.get(0x513e18));
    run.put(receiver + 0xac, run.get(0x513e1c));
    run.vcall(receiver, 0x60);
    uint32_t encounter = run.get(0x53774c);
    uint32_t targetY = run.get(encounter + 0x530) - 0x190;
    uint64_t spill_08 = 0;
    uint64_t spill_10 = 0;
    uint64_t spill_18 = 0;
    uint64_t spill_20 = 0;
    uint64_t spill_28 = 0;
    uint64_t spill_30 = 0;
    uint64_t spill_38 = 0;
    uint64_t spill_40 = 0;
    uint64_t spill_48 = 0;
    run.x87_step(CLAW_X87_I32, fp, {run.get(encounter + 0x52c)});
    run.x87_step(CLAW_X87_I32, fp, {targetY});
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpMemory(run, fp, CLAW_X87_SUB_F64, receiver + 0x68);
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x38);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    fpMemory(run, fp, CLAW_X87_SUB_F64, receiver + 0x70);
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x40);
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x78);
    fpMemory(run, fp, CLAW_X87_F64, receiver + 0x48);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
    spill_10 = run.x87_step(CLAW_X87_ST_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    spill_18 = run.x87_step(CLAW_X87_ST_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_CHS, fp);
    spill_20 = run.x87_step(CLAW_X87_ST_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5), fp);
    spill_28 = run.x87_step(CLAW_X87_ST_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    spill_30 = run.x87_step(CLAW_X87_ST_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
    spill_38 = run.x87_step(CLAW_X87_ST_F64, fp);
    fpBits(run, fp, CLAW_X87_F64, spill_28);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_10);
    run.x87_step(CLAW_X87_CHS, fp);
    fpBits(run, fp, CLAW_X87_F64, spill_30);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_18);
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
    fpBits(run, fp, CLAW_X87_F64, spill_38);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_20);
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
    spill_48 = run.x87_step(CLAW_X87_STP_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_28);
    fpBits(run, fp, CLAW_X87_F64, spill_48);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_30);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_38);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_10);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    spill_40 = run.x87_step(CLAW_X87_STP_F64, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_18);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_20);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50f370);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_40);
    fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50f368);
    run.x87_step(CLAW_X87_SQRT, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
    fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50f378);
    run.x87_step(CLAW_X87_SQRT, fp);
    spill_08 = run.x87_step(CLAW_X87_ST_F64, fp);
    fpMemory(run, fp, CLAW_X87_COMP_F64, 0x513e20);
    if (fp.status & 0x0100) {
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x60, 0);
        run.put(receiver + 0x54, 0);
        run.put(receiver + 0x5c, 0);
        run.put(receiver + 0x64, 0);
        return 0;
    }
    fpBits(run, fp, CLAW_X87_F64, spill_40);
    fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50f380);
    fpMemory(run, fp, CLAW_X87_F64, 0x513e20);
    run.x87_step(CLAW_X87_CHS, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), fp);
    run.x87_step(CLAW_X87_COMPP, fp);
    bool quadratic = fp.status & 0x0100;
    if (!quadratic) {
        fpMemory(run, fp, CLAW_X87_COM_F64, 0x513e20);
        quadratic = !(fp.status & 0x4100);
    }
    if (!quadratic) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), fp);
        fpBits(run, fp, CLAW_X87_F64, spill_10);
        fpBits(run, fp, CLAW_X87_F64, spill_20);
        fpBits(run, fp, CLAW_X87_F64, spill_18);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
        run.x87_step(CLAW_X87_ABS, fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_ABS, fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_ABS, fp);
        fpBits(run, fp, CLAW_X87_F64, spill_10);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), fp);
        fpBits(run, fp, CLAW_X87_F64, spill_18);
        fpBits(run, fp, CLAW_X87_F64, spill_20);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        fpBits(run, fp, CLAW_X87_MUL_F64, spill_08);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
        fpBits(run, fp, CLAW_X87_MUL_F64, spill_08);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        fpBits(run, fp, CLAW_X87_MUL_F64, spill_08);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
        uint64_t value_484179 = run.x87_step(CLAW_X87_STP_F64, fp);
        run.put(receiver + 0x50, uint32_t(value_484179));
        run.put(receiver + 0x50 + 0x04, uint32_t(value_484179 >> 32));
        uint64_t value_48417c = run.x87_step(CLAW_X87_STP_F64, fp);
        run.put(receiver + 0x58, uint32_t(value_48417c));
        run.put(receiver + 0x58 + 0x04, uint32_t(value_48417c >> 32));
        uint64_t value_48417f = run.x87_step(CLAW_X87_STP_F64, fp);
        run.put(receiver + 0x60, uint32_t(value_48417f));
        run.put(receiver + 0x60 + 0x04, uint32_t(value_48417f >> 32));
        run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), fp);
        return 0;
    }
    fpBits(run, fp, CLAW_X87_F64, spill_08);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_08);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADD_TOI, 0), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpBits(run, fp, CLAW_X87_SUB_F64, spill_48);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIVP, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), fp);
    run.x87_step(CLAW_X87_SQRT, fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_28);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_30);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpBits(run, fp, CLAW_X87_MUL_F64, spill_38);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50f378);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50f378);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpBits(run, fp, CLAW_X87_SUBR_F64, spill_10);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    fpMemory(run, fp, CLAW_X87_MUL_F64, 0x50f378);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpBits(run, fp, CLAW_X87_SUBR_F64, spill_18);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    fpBits(run, fp, CLAW_X87_SUBR_F64, spill_20);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    uint64_t value_4841f6 = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(receiver + 0x50, uint32_t(value_4841f6));
    run.put(receiver + 0x50 + 0x04, uint32_t(value_4841f6 >> 32));
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    uint64_t value_4841fb = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(receiver + 0x58, uint32_t(value_4841fb));
    run.put(receiver + 0x58 + 0x04, uint32_t(value_4841fb >> 32));
    uint64_t value_4841fe = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(receiver + 0x60, uint32_t(value_4841fe));
    run.put(receiver + 0x60 + 0x04, uint32_t(value_4841fe >> 32));
    run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), fp);
    return 0;
}

// 0x484210. Death sound and base death-state behavior.
uint32_t deathSound(Run &run, uint32_t receiver) {
    uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 5);
    run.call(0x48ce40, 0, {run.get(receiver + 0x0c), run.get(receiver + 0x458 + index * 4), 0});
    run.call(0x44df10, receiver);
    return 0;
}

// 0x484240. Arm the proximity latch before the base transition.
uint32_t arm(Run &run, uint32_t receiver) {
    if (!run.get(receiver + 0x4ac))
        run.put(receiver + 0x4ac, 1);
    run.call(0x44dbb0, receiver);
    return 0;
}

// 0x484260. Optional reaction sound and base response.
uint32_t reaction(Run &run, uint32_t receiver) {
    if (s32(run.call(0x4a3050, 0)) % 101 < 25) {
        uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 4);
        run.call(0x48ce40, 0, {run.get(receiver + 0x0c), run.get(receiver + 0x46c + index * 4), 0});
    }
    run.call(0x43efe0, receiver);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4828e0:
        return construct(run, receiver, arguments[0]);
    case 0x483090:
        return deleteObject(run, receiver, arguments[0]);
    case 0x4830b0:
        return destroy(run, receiver);
    case 0x483180:
        return dispatchState(run, receiver, arguments[0]);
    case 0x483560:
        return update(run, receiver, arguments[0]);
    case 0x4837b0:
        return think(run, receiver);
    case 0x483ae0:
        return hit(run, receiver);
    case 0x483d20:
        return block(run, receiver);
    case 0x483e10:
        return die(run, receiver, arguments[0]);
    case 0x483f30:
        return aim(run, receiver);
    case 0x484210:
        return deathSound(run, receiver);
    case 0x484240:
        return arm(run, receiver);
    case 0x484260:
        return reaction(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_red_tail_pirate_core_entry, owned, body)
