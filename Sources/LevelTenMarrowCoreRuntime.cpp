// Level 10 Marrow behavior recovered from the original v1.0 packet.
#include "ClawRuntime.hpp"
#include <cmath>

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4587a0:
    case 0x458d40:
    case 0x4593d0:
    case 0x459470:
        return 1;
    case 0x4593f0:
    case 0x459440:
    case 0x459660:
    case 0x4596a0:
    case 0x4599b0:
    case 0x459ad0:
        return 0;
    default:
        return -1;
    }
}

uint32_t dispatchSlot(Run &run, uint32_t index, uint32_t returnPC) {
    if (s32(index) < run.gets(0x537af8) || s32(index) > run.gets(0x537afc)) {
        if (!run.call(0x4db6e0, 0x537af0, {index, 0})) {
            uint32_t error = run.get(0x544b4c);
            run.call(0x4db5f0, 0);
            run.put(0x544b14, returnPC);
            run.call(0x4db4d0, run.get(0x537af4), {0x537af0, error, 0xc});
            return run.get(0x537b04);
        }
    }
    return (index - run.get(0x537af8)) * run.get(0x537b08) + run.get(0x537b00);
}

// 0x4587a0. Global state callback dispatch; +0x20 is table scratch.
uint32_t dispatch(Run &run, uint32_t actor, uint32_t index) {
    run.put(0x537b10, 0);
    uint32_t slot = dispatchSlot(run, index, 0x458800);
    if (run.get(slot)) {
        run.put(0x537b10, 0);
        slot = dispatchSlot(run, index, 0x45887a);
        run.call(run.get(slot), actor);
    } else {
        run.call(0x40e280, actor, {index});
    }
    return 0;
}

// 0x4593f0. +0x10 logic, +0x24 prior state, +0x12c sprite,
// +0x134 prior animation, +0x344 startup animation.
uint32_t startup(Run &run, uint32_t actor) {
    run.put(actor + 0x24, run.get(run.get(actor + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523268});
    run.put(run.get(actor + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(actor + 0x12c);
    uint32_t animation = run.get(actor + 0x344);
    run.put(actor + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    return 0;
}

uint32_t resource(Run &run, uint32_t actor, uint32_t name) {
    uint32_t result = run.call(0x4062e0, actor + 0x128, {name});
    if (!result) {
        result = run.call(0x4062e0, actor + 0x128, {0x5234b4});
    }
    return result;
}

uint32_t world(Run &run, uint32_t actor) {
    return run.get(run.get(run.get(actor + 0x12c) + 0xc) + 0x28);
}

// 0x458d40. +0xc entity, +0x2fc bit count, +0x300 bit storage;
// +0x308..0x4b0 animation and sound handles, rectangles at +0x210..0x260.
uint32_t construct(Run &run, uint32_t actor, uint32_t entity) {
    run.call(0x40e0d0, actor, {entity});
    run.put(actor + 0x460, 0);
    run.put(actor + 0x464, 0);
    run.put(actor + 0x468, 0);
    run.put(actor + 0x46c, 0);
    run.put(actor + 0x470, 0);
    run.put(actor + 0x474, 0);
    run.put(actor + 0x478, 0);
    run.put(actor + 0x47c, 0);
    run.put(actor + 0x0, 0x50e7ac);
    run.put(0x537b14, actor);
    run.call(0x4c7970, run.get(actor + 0x12c), {0x5289e0});
    run.put(actor + 0x308, resource(run, actor, 0x5289c8));
    run.put(actor + 0x30c, resource(run, actor, 0x5289ac));
    run.put(actor + 0x4a0, resource(run, actor, 0x528994));
    uint32_t value = resource(run, actor, 0x52897c);
    run.put(actor + 0x49c, value);
    run.put(actor + 0x310, value);
    run.put(actor + 0x318, 0);
    run.put(actor + 0x31c, 0);
    run.put(actor + 0x320, 0);
    run.put(actor + 0x32c, resource(run, actor, 0x528968));
    run.put(actor + 0x374, resource(run, actor, 0x528950));
    run.put(actor + 0x334, resource(run, actor, 0x52893c));
    run.put(actor + 0x338, resource(run, actor, 0x528924));
    run.put(actor + 0x33c, resource(run, actor, 0x528910));
    run.put(actor + 0x340, resource(run, actor, 0x528910));
    run.put(actor + 0x344, resource(run, actor, 0x5288fc));
    run.put(actor + 0x348, resource(run, actor, 0x5288e8));
    run.put(actor + 0x34c, resource(run, actor, 0x5289ac));
    run.put(actor + 0x4a4, resource(run, actor, 0x5288d4));
    run.put(actor + 0x4a8, resource(run, actor, 0x5288c0));
    run.put(actor + 0x4ac, resource(run, actor, 0x5288ac));
    run.put(actor + 0x4b0, resource(run, actor, 0x528898));
    run.put(actor + 0x378, resource(run, actor, 0x528884));
    run.put(actor + 0x37c, resource(run, actor, 0x528884));
    run.put(actor + 0x380, resource(run, actor, 0x528884));
    run.put(actor + 0x36c, resource(run, actor, 0x528884));
    run.put(actor + 0x384, resource(run, actor, 0x528870));
    run.put(actor + 0x388, resource(run, actor, 0x528870));
    uint32_t scratch = run.automatic(4);
    run.put(scratch, 0);
    run.call(0x4f6286, world(run, actor) + 0x10, {0x528858, scratch});
    run.put(actor + 0x420, run.get(scratch));
    run.put(scratch, 0);
    run.call(0x4f6286, world(run, actor) + 0x10, {0x528840, scratch});
    run.put(actor + 0x3a4, run.get(scratch));
    run.put(actor + 0x480, run.call(0x4061b0, world(run, actor), {0x52882c}));
    run.put(actor + 0x484, run.call(0x4061b0, world(run, actor), {0x528814}));
    run.put(actor + 0x488, run.call(0x4061b0, world(run, actor), {0x5287fc}));
    run.put(actor + 0x48c, run.call(0x4061b0, world(run, actor), {0x5287e4}));
    run.put(actor + 0x3a0, run.call(0x4061b0, world(run, actor), {0x5287d0}));
    run.put(actor + 0x490, run.call(0x4061b0, world(run, actor), {0x5287bc}));
    run.put(actor + 0x494, run.call(0x4061b0, world(run, actor), {0x5287a8}));
    run.put(actor + 0x498, run.call(0x4061b0, world(run, actor), {0x528790}));
    run.icall(0x546d5c, {actor + 0x220, 0xffffff8b, 0xfffffffc, 0xffffffe2, 0x15});
    run.icall(0x546d5c, {actor + 0x210, 0xffffffff, 0xffffffff, 1, 1});
    run.icall(0x546d5c, {actor + 0x250, 0xfffffff1, 0xffffffc4, 0xf, 0x34});
    run.icall(0x546d5c, {actor + 0x260, 0xfffffff1, 0xffffffc4, 0xf, 0x34});
    run.put(actor + 0x28c, 500);
    run.put(actor + 0x290, 20);
    run.put(actor + 0x29c, 300);
    run.put(actor + 0x2a0, 20);
    run.put(actor + 0x2a4, 150);
    run.put(actor + 0x2a8, 20);
    run.put(actor + 0x2ac, 100);
    run.put(actor + 0x2b0, 20);
    run.put(actor + 0x2b4, 0);
    run.put(actor + 0x2b8, 0);
    run.put(actor + 0x2bc, 0xffffffc4);
    run.put(actor + 0x2c0, 0xffffffec);
    run.put(actor + 0x2c4, 20);
    run.put(actor + 0x2c8, 0xfffffff1);
    run.put(actor + 0x2e4, 100);
    value = run.call_x87(0x4a30e0, 0, double(run.getf(0x5262b8)) * double(run.getf(0x50e770)));
    if (value <= 99) {
        value = 99;
    }
    run.put(actor + 0x2e4, value);
    run.put(run.get(actor + 0xc) + 0x10c, 100);
    value = run.call_x87(0x4a30e0, 0, double(run.gets(run.get(actor + 0xc) + 0x10c)) * double(run.getf(0x5262b4)));
    run.put(run.get(actor + 0xc) + 0x10c, value);
    run.put(run.get(actor + 0xc) + 0x104, 10);
    value = run.call_x87(0x4a30e0, 0, double(run.gets(run.get(actor + 0xc) + 0x104)) * double(run.getf(0x5262b0)));
    run.put(run.get(actor + 0xc) + 0x104, value);
    uint32_t count = run.get(actor + 0x2fc);
    if (count > 9) {
        uint32_t bits = count <= 32 ? actor + 0x300 : run.get(actor + 0x300);
        run.put(bits, run.get(bits) ^ 0x200);
    }
    run.call(0x420fc0, actor + 0x2f4, {8});
    run.call(0x40abb0, actor + 0x128, {actor + 0x250});
    run.call(0x40ab80, actor + 0x128, {0, 0xffffffc4, 20, 35});
    run.call(0x459c80, actor);
    run.call(0x40abf0, actor + 0x128);
    startup(run, actor);
    return actor;
}

// 0x4593d0.
uint32_t deletingDestructor(Run &run, uint32_t actor, uint32_t flags) {
    run.call(0x45a260, actor);
    if (flags & 1) {
        run.call(0x4f6428, 0, {actor});
    }
    return actor;
}

// 0x459440.
uint32_t startupTick(Run &run, uint32_t actor) {
    run.call(0x4c82a0, run.get(actor + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (run.get(0x53c9c0) == 2) {
        run.vcall(actor, 0x44);
    }
    return 0;
}

// 0x459470. +0x70 elapsed, +0x454 deadline, +0x4c0 health snapshot,
// +0x184 behavior, +0x18c direction, +0x3c4 distance, +0x14 next handler.
uint32_t evaluate(Run &run, uint32_t actor, uint32_t argument) {
    run.call(0x44d000, actor, {argument});
    double elapsed = run.getd(actor + 0x70);
    if (!(double(run.gets(actor + 0x454)) >= elapsed)) {
        uint32_t name = run.call(0x406020, 0x537698, {run.get(run.get(actor + 0x10) + 0x1c)});
        if (run.call(0x4a3810, 0, {run.get(name), 0x5234f4})) {
            run.putd(actor + 0x70, double(s32(run.get(actor + 0x454) - 10)));
            run.put(actor + 0x50, 0);
            run.put(actor + 0x58, 0);
            run.put(actor + 0x60, 0);
            run.put(actor + 0x54, 0);
            run.put(actor + 0x5c, 0);
            run.put(actor + 0x64, 0);
            run.put(actor + 0x38, 0);
            run.put(actor + 0x3c, 0);
            run.put(actor + 0x40, 0);
            run.put(actor + 0x44, 0);
            run.put(run.get(actor + 0xc) + 0xcc, 7);
            run.vcall(actor, 0x24);
            run.put(actor + 0x40, 0);
            run.put(actor + 0x44, 0x409f4000);
            run.put(run.get(actor + 0xc) + 0xcc, 8);
            run.vcall(actor, 0x44);
        }
    }
    if (run.gets(run.get(actor + 0xc) + 0x10c) <= s32(run.get(actor + 0x4c0) - 25)) {
        if (run.gets(actor + 0x20) >= 2) {
            run.put(actor + 0x14, 0x459830);
        }
        return 0;
    }
    uint32_t input = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (!run.get(input + 0x4)) {
        return 0;
    }
    uint32_t direction = run.get(actor + 0x18c);
    if (!((direction == 3 && run.get(input)) || (direction == 2 && !run.get(input)))) {
        return 0;
    }
    uint32_t behavior = run.get(actor + 0x184);
    if (behavior != 3 && behavior != 4) {
        return 0;
    }
    uint32_t name = run.call(0x441030, 0x537698, {run.get(run.get(actor + 0x10) + 0x1c)});
    uint32_t element = run.get(0x5376b4);
    uint32_t count = run.get(0x5376b8);
    while (count) {
        if (element) {
            run.call(0x4f6439, element);
        }
        element += 4;
        --count;
    }
    if (!run.call(0x4a3810, 0, {run.get(name), 0x528758})) {
        return 0;
    }
    int32_t threshold = run.gets(actor + 0x2e4);
    int32_t random = s32(run.call(0x4a3050, 0)) % 100;
    if (random >= threshold) {
        return 0;
    }
    int32_t distance = run.gets(actor + 0x3c4);
    if (distance < 0) {
        return 0;
    }
    if (distance < 200) {
        if (run.gets(actor + 0x20) >= 2) {
            run.put(actor + 0x14, 0x44e620);
        }
    } else if (distance < 600 && run.gets(actor + 0x20) >= 2) {
        run.put(actor + 0x14, 0x455350);
    }
    return 0;
}

// 0x459660.
uint32_t home(Run &run, uint32_t actor) {
    if (run.get(0x53c9c0) == 2) {
        run.put(actor + 0x50, 0);
        run.put(actor + 0x54, 0);
        run.put(actor + 0x24, run.get(run.get(actor + 0x10) + 0x1c));
        uint32_t state = run.call(0x4dba00, 0x537668, {0x5234ec});
        run.put(run.get(actor + 0x10) + 0x1c, state);
    }
    return 0;
}

// 0x4596a0. +0x138/+0x140 facing bounds, sprite +0x40 flip flags,
// +0x190 world entity, +0x194 position entity.
uint32_t homeTick(Run &run, uint32_t actor) {
    uint32_t sprite = run.get(actor + 0x12c);
    bool facingLeft = run.get(actor + 0x18c) == 2;
    bool flipped = (run.get8(sprite + 0x40) & 2) != 0;
    if (facingLeft != flipped) {
        uint32_t left = run.get(actor + 0x138);
        run.put(actor + 0x138, 0u - run.get(actor + 0x140));
        run.put(actor + 0x140, 0u - left);
        if (facingLeft) {
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            sprite = run.get(actor + 0x12c);
            run.call(0x406120, sprite);
            run.call(0x406150, sprite);
            run.call(0x406180, sprite);
        } else {
            run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffd);
            run.call(0x4060b0, run.get(actor + 0x12c));
        }
    }
    int32_t random = s32(run.call(0x4a3050, 0)) % 121;
    uint32_t behavior = run.get(actor + 0x184);
    if (behavior == 2 || behavior == 3) {
        uint32_t threshold = run.get(actor + 0x2e4);
        if (random < s32(threshold)) {
            run.vcall(actor, 0x58);
        } else if (random < s32(threshold + 20)) {
            run.vcall(actor, 0x68);
        }
    } else if (behavior == 4) {
        random = s32(run.call(0x4a3050, 0)) % 100;
        run.vcall(actor, random >= 40 ? 0x58 : 0x64);
    } else if (behavior == 6) {
        run.vcall(actor, 0xa4);
        return 0;
    }
    bool sight = false;
    if (run.get(0x534eac) != 0x26b7) {
        uint32_t playerX = run.get(run.get(0x537e88) + 0x4c);
        uint32_t position = run.get(actor + 0x194);
        uint32_t y = run.get(position + 0x50);
        uint32_t x = run.get(position + 0x4c);
        uint32_t grid = run.get(run.get(run.get(actor + 0x190) + 0xc) + 0x24);
        if (run.call(0x4cda10, grid, {x, y, playerX, 0x20})) {
            position = run.get(actor + 0x194);
            y = run.get(position + 0x50);
            int32_t playerY = run.gets(run.get(0x537e88) + 0x50);
            sight = playerY < s32(y + 50) && playerY > s32(y - 50) && run.get(position + 0x38) != 0xffffffff;
        }
    }
    if (sight) {
        run.vcall(actor, 0xa4);
    } else {
        run.call(0x44da20, actor);
    }
    return 0;
}

// 0x4599b0. +0x1a0 event latch, +0x4b8 active flag,
// +0x468 start clock, +0x46c duration.
uint32_t waitForParrotTick(Run &run, uint32_t actor) {
    run.call(0x4c82a0, run.get(actor + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t sprite = run.get(actor + 0x12c);
    if (run.get(sprite + 0x1a4) && !run.get(sprite + 0x19c) && !run.get(actor + 0x1a0)) {
        uint32_t sound = run.get(actor + 0x488);
        uint32_t entity = run.get(actor + 0xc);
        run.put(actor + 0x1a0, 1);
        run.put(actor + 0x4b8, 1);
        run.call(0x48ce40, 0, {entity, sound, 0});
        run.put(actor + 0x50, 0);
        run.put(actor + 0x58, 0);
        run.put(actor + 0x60, 0);
        run.put(actor + 0x54, 0);
        run.put(actor + 0x5c, 0);
        run.put(actor + 0x64, 0);
    }
    if (run.get(0x537210) - run.get(actor + 0x468) >= run.get(actor + 0x46c)) {
        run.put(actor + 0x40, 0);
        run.put(actor + 0x44, 0x409f4000);
        sprite = run.get(actor + 0x12c);
        run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xfffffffb);
        sprite = run.get(actor + 0x12c);
        run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xffffff7f);
        uint32_t entity = run.get(actor + 0xc);
        run.put(actor + 0x20, 2);
        run.put(entity + 0xcc, 8);
        sprite = run.get(actor + 0x12c);
        run.put(sprite + 0x50, run.get(sprite + 0x50) - 0x20);
        entity = run.get(actor + 0x128);
        run.call(0x4cd800, run.get(run.get(entity + 0xc) + 0x24), {entity, 0});
        run.put(run.get(actor + 0x128) + 0xcc, 1);
        run.put(actor + 0x4c0, run.get(run.get(actor + 0xc) + 0x10c));
        run.put(actor + 0x4b8, 0);
        run.vcall(actor, 0x44);
    }
    return 0;
}

// 0x459ad0. +0x350 idle animation, +0x470 timer start, +0x474 duration.
uint32_t idle(Run &run, uint32_t actor) {
    run.put(actor + 0x50, 0);
    run.put(actor + 0x54, 0);
    run.put(actor + 0x24, run.get(run.get(actor + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(actor + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(actor + 0x12c);
    uint32_t animation = run.get(actor + 0x350);
    run.put(actor + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    int32_t distance = run.gets(actor + 0x3c4);
    if (distance >= 0 && distance < 500) {
        run.call(0x48ceb0, 0, {run.get(actor + 0xc), 0x5289f0, 0});
    }
    run.put(actor + 0x474, 1000);
    run.put(actor + 0x470, run.get(0x537210));
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4587a0:
        return dispatch(run, receiver, arguments[0]);
    case 0x458d40:
        return construct(run, receiver, arguments[0]);
    case 0x4593d0:
        return deletingDestructor(run, receiver, arguments[0]);
    case 0x4593f0:
        return startup(run, receiver);
    case 0x459440:
        return startupTick(run, receiver);
    case 0x459470:
        return evaluate(run, receiver, arguments[0]);
    case 0x459660:
        return home(run, receiver);
    case 0x4596a0:
        return homeTick(run, receiver);
    case 0x4599b0:
        return waitForParrotTick(run, receiver);
    case 0x459ad0:
        return idle(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_level_ten_marrow_core_entry, owned, body)
