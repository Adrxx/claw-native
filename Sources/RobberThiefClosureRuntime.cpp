// Robber thief Level 3 closure, recovered from original v1.0.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x485330:
    case 0x485870:
    case 0x485960:
        return 1;
    case 0x485890:
    case 0x485d60:
    case 0x485d90:
    case 0x485ec0:
    case 0x485f00:
    case 0x486090:
        return 0;
    default:
        return -1;
    }
}

// +0x12c is the sprite; its +0xc owns resource maps at +0x28/+0x2c.
uint32_t resourceMap(Run &run, uint32_t object, uint32_t offset) {
    return run.get(run.get(run.get(object + 0x12c) + 0xc) + offset);
}

// 0x485d60. +0x460 holds four idle resources; +0x420 is selected idle.
uint32_t chooseIdle(Run &run, uint32_t object) {
    uint32_t random = run.call(0x4a3050, 0);
    uint32_t index = uint32_t(s32(random) % 4);
    run.put(object + 0x420, run.get(object + 0x460 + index * 4));
    run.call(0x44f1b0, object);
    return 0;
}

uint32_t convertProduct(Run &run, ClawX87State &state, double left, double right) {
    uint64_t bits;
    std::memcpy(&bits, &left, sizeof(bits));
    run.x87_step(CLAW_X87_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    std::memcpy(&bits, &right, sizeof(bits));
    run.x87_step(CLAW_X87_MUL_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    state.popCount = 1;
    state.pushCount = 0;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, state);
}

uint32_t lookupAnimation(Run &run, uint32_t object, uint32_t name) {
    uint32_t value = run.call(0x4062e0, object + 0x128, {name});
    if (!value) {
        value = run.call(0x4062e0, object + 0x128, {0x5234b4});
    }
    return value;
}

// 0x485330. Initializes resources, rectangles, combat settings and idle state.
uint32_t construct(Run &run, uint32_t object, uint32_t argument) {
    ClawX87State state{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
    run.call_x87_exact(0x44c000, object, state, {argument});
    run.put(object + 0x470, 0);
    run.put(object + 0x474, 0);
    run.put(object, 0x50f49c);
    run.call(0x4c7970, run.get(object + 0x12c), {0x52bdac});
    uint32_t capacity = run.get(object + 0x2fc);
    if (capacity <= 8) {
        run.call(0x4dbd20, object + 0x2f4, {8});
    } else {
        uint32_t word = capacity > 0x20 ? run.get(object + 0x300) : object + 0x300;
        run.put(word, run.get(word) | 0x100);
    }
    run.put(object + 0x30c, lookupAnimation(run, object, 0x52bd8c));
    run.put(object + 0x310, lookupAnimation(run, object, 0x52bd70));
    run.put(object + 0x370, lookupAnimation(run, object, 0x52bd70));
    run.put(object + 0x32c, lookupAnimation(run, object, 0x52bd58));
    run.put(object + 0x374, lookupAnimation(run, object, 0x52bd58));
    run.put(object + 0x334, lookupAnimation(run, object, 0x52bd3c));
    run.put(object + 0x338, lookupAnimation(run, object, 0x52bd20));
    run.put(object + 0x344, lookupAnimation(run, object, 0x52bd08));
    run.put(object + 0x34c, lookupAnimation(run, object, 0x52bd8c));
    run.put(object + 0x350, lookupAnimation(run, object, 0x52bcf0));
    run.put(object + 0x378, lookupAnimation(run, object, 0x52bcd4));
    run.put(object + 0x37c, lookupAnimation(run, object, 0x52bcb8));
    run.put(object + 0x33c, lookupAnimation(run, object, 0x52bca0));
    run.put(object + 0x380, lookupAnimation(run, object, 0x52bcb8));
    run.put(object + 0x36c, lookupAnimation(run, object, 0x52bc84));
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    run.call(0x4f6286, resourceMap(run, object, 0x28) + 0x10, {0x52bc68, local});
    run.put(object + 0x3a4, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, resourceMap(run, object, 0x28) + 0x10, {0x52bc4c, local});
    run.put(object + 0x410, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, resourceMap(run, object, 0x28) + 0x10, {0x52bc30, local});
    run.put(object + 0x3b4, run.get(local));
    run.put(object + 0x460, run.call(0x4061b0, resourceMap(run, object, 0x28), {0x52bc14}));
    run.put(object + 0x464, run.call(0x4061b0, resourceMap(run, object, 0x28), {0x52bbf8}));
    run.put(object + 0x468, run.call(0x4061b0, resourceMap(run, object, 0x28), {0x52bbdc}));
    run.put(object + 0x46c, run.call(0x4061b0, resourceMap(run, object, 0x28), {0x52bbc0}));
    run.put(object + 0x45c, run.call(0x4061b0, resourceMap(run, object, 0x28), {0x52bba4}));
    run.icall(0x546d5c, {object + 0x220, uint32_t(-75), 0, 0, 27});
    run.icall(0x546d5c, {object + 0x210, uint32_t(-1), uint32_t(-1), 1, 1});
    run.icall(0x546d5c, {object + 0x250, uint32_t(-15), uint32_t(-30), 15, 55});
    run.icall(0x546d5c, {object + 0x260, uint32_t(-30), uint32_t(-50), 31, 8});
    run.put(object + 0x28c, 400);
    run.put(object + 0x290, 50);
    run.put(object + 0x29c, 200);
    run.put(object + 0x2a0, 50);
    run.put(object + 0x2a4, 100);
    run.put(object + 0x2a8, 50);
    run.put(object + 0x2ac, 50);
    run.put(object + 0x2b0, 50);
    run.put(object + 0x2b4, 0);
    run.put(object + 0x2b8, 0);
    run.put(object + 0x2bc, uint32_t(-50));
    run.put(object + 0x2c0, uint32_t(-20));
    run.put(object + 0x2c4, 20);
    run.put(object + 0x2c8, uint32_t(-15));
    run.put(object + 0x2e4, 25);
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    uint32_t chance = convertProduct(run, state, double(run.getf(0x5262b8)), double(run.getf(0x50f490)));
    if (chance <= 99) {
        chance = 99;
    }
    run.put(object + 0x2e4, chance);
    run.put(run.get(object + 0xc) + 0x10c, 7);
    uint32_t value = convertProduct(run, state, double(run.gets(run.get(object + 0xc) + 0x10c)), double(run.getf(0x5262b4)));
    run.put(run.get(object + 0xc) + 0x10c, value);
    run.put(run.get(object + 0xc) + 0x104, 10);
    value = convertProduct(run, state, double(run.gets(run.get(object + 0xc) + 0x104)), double(run.getf(0x5262b0)));
    run.put(run.get(object + 0xc) + 0x104, value);
    run.call(0x40f6c0, run.get(object + 0x12c), {run.get(object + 0x250), run.get(object + 0x254), run.get(object + 0x258), run.get(object + 0x25c)});
    run.call(0x40ab80, object + 0x128, {uint32_t(-20), uint32_t(-50), 20, 50});
    run.call(0x40abf0, object + 0x128);
    chooseIdle(run, object);
    return object;
}

// 0x485890. Tears down bit storage and two reference strings.
uint32_t destroy(Run &run, uint32_t object) {
    run.put(object, 0x50b16c);
    run.call(0x4dbcd0, object + 0x2f4);
    run.call(0x4f6584, object + 0x1a8);
    run.call(0x4f6584, object + 0x1a4);
    run.put(object, 0x50b014);
    return 0;
}

// 0x485870. Optional deleting destructor.
uint32_t deletingDestructor(Run &run, uint32_t object, uint32_t flags) {
    destroy(run, object);
    if (flags & 1) {
        run.call(0x4f6428, 0, {object});
    }
    return object;
}

uint32_t stateSlot(Run &run, uint32_t state) {
    uint32_t minimum = run.get(0x53c240);
    run.put(0x53c258, 0);
    if (s32(state) < s32(minimum) || s32(state) > run.gets(0x53c244)) {
        uint32_t ok = run.call(0x4db6e0, 0x53c238, {state, 0});
        if (!ok) {
            uint32_t diagnostic = run.get(0x544b4c);
            uint32_t value = run.call(0x4db5f0, 0);
            run.put(0x544b14, value);
            run.call(0x4db4d0, run.get(0x53c23c), {0x53c238, diagnostic, 12});
            return run.get(0x53c24c);
        }
        minimum = run.get(0x53c240);
    }
    return (state - minimum) * run.get(0x53c250) + run.get(0x53c248);
}

// 0x485960. State table dispatch, with generic actor fallback.
uint32_t dispatchState(Run &run, uint32_t object, uint32_t state) {
    uint32_t slot = stateSlot(run, state);
    if (run.get(slot)) {
        slot = stateSlot(run, state);
        run.call(run.get(slot), object);
    } else {
        run.call(0x44c840, object, {state});
    }
    return 0;
}

// 0x485d90. Keep facing in sync, then decide whether the player can be attacked.
uint32_t considerAttack(Run &run, uint32_t object) {
    uint32_t sprite = run.get(object + 0x12c);
    bool left = run.get(object + 0x18c) == 2;
    if (left != bool(run.get8(sprite + 0x40) & 2)) {
        uint32_t first = run.get(object + 0x138);
        run.put(object + 0x138, 0u - run.get(object + 0x140));
        run.put(object + 0x140, 0u - first);
        uint32_t flags = run.get(sprite + 0x40);
        run.put(sprite + 0x40, left ? flags | 2 : flags & 0xfffffffd);
        sprite = run.get(object + 0x12c);
        run.call(0x406120, sprite);
        run.call(0x406150, sprite);
        run.call(0x406180, sprite);
    }
    bool attack = false;
    if (run.get(0x534eac) != 0x26b7) {
        uint32_t player = run.get(0x537e88);
        uint32_t data = run.get(object + 0x194);
        uint32_t sight = run.call(0x4cda10, run.get(run.get(run.get(object + 0x190) + 0xc) + 0x24), {run.get(data + 0x4c), run.get(data + 0x50), run.get(player + 0x4c), 0x20});
        if (sight) {
            data = run.get(object + 0x194);
            uint32_t y = run.get(data + 0x50);
            uint32_t playerY = run.get(run.get(0x537e88) + 0x50);
            attack = s32(playerY) < s32(y + 50) && s32(playerY) > s32(y - 50) && run.get(data + 0x38) != 0xffffffff;
        }
    }
    if (!attack) {
        run.vcall(object, 0x48);
        return 0;
    }
    uint32_t chance = run.get(object + 0x2e4);
    uint32_t random = run.call(0x4a3050, 0);
    if (s32(random) % 100 < s32(chance)) {
        run.vcall(object, 0xa4);
    }
    return 0;
}

// 0x485f00. +0x450/+0x454 set projectile offset; +0x458 is signed velocity.
uint32_t beginFire(Run &run, uint32_t object) {
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    uint32_t value = run.call(0x4dba00, 0x537668, {0x524548});
    run.put(run.get(object + 0x10) + 0x1c, value);
    bool high = run.get(run.get(0x537e88) + 0xcc) == 5;
    uint32_t local = run.automatic(-4);
    run.put(local, 0);
    run.call(0x4f6286, resourceMap(run, object, 0x28) + 0x10, {high ? 0x52bc30u : 0x52bdd0u, local});
    run.put(object + 0x3b4, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, resourceMap(run, object, 0x2c) + 0x10, {high ? 0x52bdecu : 0x52bd70u, local});
    value = run.get(local);
    if (!value) {
        value = high ? run.call(0x4062e0, object + 0x128, {0x5234b4}) : run.call(0x4061b0, resourceMap(run, object, 0x2c), {0x5234b4});
    }
    run.put(object + 0x370, value);
    run.put(object + 0x454, high ? 20u : uint32_t(-15));
    if (run.get8(run.get(object + 0x12c) + 0x40) & 2) {
        run.put(object + 0x450, 65);
        run.put(object + 0x458, 400);
    } else {
        run.put(object + 0x450, uint32_t(-65));
        run.put(object + 0x458, uint32_t(-400));
    }
    uint32_t sprite = run.get(object + 0x12c);
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(object + 0x370)});
    run.put(object + 0x1a0, 0);
    return 0;
}

// 0x485ec0. Unsigned elapsed-time cooldown.
uint32_t timedFire(Run &run, uint32_t object) {
    if (run.get(0x537210) - run.get(object + 0x470) >= run.get(object + 0x474)) {
        uint32_t savedFrame = run.frame;
        run.frame -= 8;
        beginFire(run, object);
        run.frame = savedFrame;
        run.put(object + 0x474, 1500);
        run.put(object + 0x470, run.get(0x537210));
    }
    return 0;
}

// 0x486090. Spawn one projectile at the firing frame and return when animation ends.
uint32_t updateFire(Run &run, uint32_t object) {
    uint32_t result = run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (result == 1 && !run.get(object + 0x1a0)) {
        uint32_t vertical = run.get(object + 0x454);
        run.put(object + 0x1a0, 1);
        uint32_t sprite = run.get(object + 0x12c);
        uint32_t projectile = run.call(0x4c8da0, run.get(run.get(run.get(object + 0x130) + 0xc) + 8), {0, run.get(object + 0x450) + run.get(sprite + 0x4c), vertical + run.get(sprite + 0x50), run.get(sprite + 0x64) - 1, 0x522e0c, 0x40000});
        run.call(0x4c7970, projectile, {0x52be08});
        uint32_t callbacks = run.get(projectile + 0x6c);
        run.put(projectile + 0x104, 10);
        run.put(projectile + 0xd0, 0x40);
        run.call(run.get(callbacks + 0x10), 0, {projectile});
        uint32_t body = run.get(run.get(projectile + 0x6c) + 0x18);
        run.putd(body + 0x50, double(run.gets(object + 0x458)));
        body = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(body + 0x58, 0);
        run.put(body + 0x5c, 0);
        body = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(body + 0x40, 0);
        run.put(body + 0x44, 0);
        if (run.gets(object + 0x458) < 0) {
            body = run.get(run.get(projectile + 0x6c) + 0x18);
            sprite = run.get(body + 0x12c);
            if (!(run.get8(sprite + 0x40) & 2)) {
                uint32_t first = run.get(body + 0x138);
                run.put(body + 0x138, 0u - run.get(body + 0x140));
                run.put(body + 0x140, 0u - first);
                run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
                sprite = run.get(body + 0x12c);
                first = run.get(sprite + 0x118);
                if (first != 0x80000000) {
                    run.put(sprite + 0x118, 0u - run.get(sprite + 0x120));
                    run.put(sprite + 0x120, 0u - first);
                }
                first = run.get(sprite + 0x128);
                if (first != 0x80000000) {
                    run.put(sprite + 0x128, 0u - run.get(sprite + 0x130));
                    run.put(sprite + 0x130, 0u - first);
                }
                run.call(0x406180, sprite);
            }
        }
        uint32_t sound = run.get(object + 0x3b4);
        if (sound && run.get(0x532c0c)) {
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
        }
    }
    uint32_t animation = run.get(object + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14)) {
        run.vcall(object, 0x44);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x485330:
        return construct(run, receiver, arguments[0]);
    case 0x485870:
        return deletingDestructor(run, receiver, arguments[0]);
    case 0x485890:
        return destroy(run, receiver);
    case 0x485960:
        return dispatchState(run, receiver, arguments[0]);
    case 0x485d60:
        return chooseIdle(run, receiver);
    case 0x485d90:
        return considerAttack(run, receiver);
    case 0x485ec0:
        return timedFire(run, receiver);
    case 0x485f00:
        return beginFire(run, receiver);
    case 0x486090:
        return updateFire(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_robber_thief_closure_entry, owned, body)
