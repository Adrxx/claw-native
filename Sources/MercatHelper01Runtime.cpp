// Mercat helper object, recovered against the original v1.0 game bodies.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x45ffc0:
    case 0x460620:
    case 0x460710:
    case 0x460af0:
    case 0x461020:
    case 0x461170:
        return 1;
    case 0x460640:
    case 0x460bf0:
    case 0x460e20:
    case 0x4612c0:
        return 0;
    default:
        return -1;
    }
}

// Finite binary32 values widen exactly. Keep NaN payload bits for the x87
// load/arithmetic primitive rather than letting host floating arithmetic run.
uint64_t wideFloat(uint32_t bits) {
    uint64_t sign = uint64_t(bits >> 31) << 63;
    uint32_t exponent = (bits >> 23) & 0xff;
    uint32_t fraction = bits & 0x7fffff;
    if (exponent == 0xff)
        return sign | (uint64_t(0x7ff) << 52) | (uint64_t(fraction) << 29);
    if (!exponent) {
        if (!fraction)
            return sign;
        uint32_t shift = 0;
        while (!(fraction & 0x800000)) {
            fraction <<= 1;
            ++shift;
        }
        return sign | (uint64_t(897 - shift) << 52) | (uint64_t(fraction & 0x7fffff) << 29);
    }
    return sign | (uint64_t(exponent + 896) << 52) | (uint64_t(fraction) << 29);
}

void floatStep(Run &run, ClawX87State &fp, uint32_t operation, uint32_t address) {
    uint64_t bits = wideFloat(run.get(address));
    run.x87_step(operation, fp, {uint32_t(bits), uint32_t(bits >> 32)});
}

uint32_t exactCall(Run &run, ClawX87State &fp, uint32_t target, uint32_t receiver,
                   uint32_t pop = 0, std::initializer_list<uint32_t> arguments = {}) {
    fp.popCount = pop;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(target, receiver, fp, arguments);
}

uint32_t innerBody(Run &run, uint32_t function, uint32_t receiver,
                   const uint32_t *arguments, ClawX87State &fp);

// 0x460e20. Selects idle state and animation and starts its timer.
uint32_t idle(Run &run, uint32_t object, ClawX87State &fp) {
    run.put(object + 0x50, 0);
    run.put(object + 0x54, 0);
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(object + 0x10) + 0x1c, state);
    uint32_t animation = run.get(object + 0x12c) + 0x188;
    uint32_t value = run.get(object + 0x4bc);
    run.put(object + 0x134, run.get(run.get(object + 0x12c) + 0x190));
    run.call(0x4c8220, animation, {value});
    exactCall(run, fp, 0x4c82a0, animation, 0, {run.get(0x5430c4)});
    run.put(object + 0x4b0, 2000);
    run.put(object + 0x4ac, run.get(0x537210));
    return 0;
}

// 0x4612c0. Publishes the blocking state and plays a selected sound.
uint32_t block(Run &run, uint32_t object) {
    run.put(object + 0x20, 1);
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x526a38});
    run.put(run.get(object + 0x10) + 0x1c, state);
    uint32_t animation = run.get(object + 0x12c) + 0x188;
    uint32_t value = run.get(object + 0x384);
    run.put(object + 0x134, run.get(run.get(object + 0x12c) + 0x190));
    run.call(0x4c8220, animation, {value});
    uint32_t sprite = run.get(object + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 4);
    int32_t selection = s32(run.call(0x4a3050, 0)) % 2;
    uint32_t sound = run.get(object + 0x47c + uint32_t(selection) * 4);
    if (sound && run.get(0x532c0c)) {
        uint32_t channel = run.get(0x532c10);
        run.call(0x4b45f0, run.get(sound + 0x10), {channel, 0, 0, 0});
    }
    return 0;
}

// Both defensive callbacks reflect the actor and sprite bounds when needed.
void face(Run &run, uint32_t object) {
    uint32_t sprite = run.get(object + 0x12c);
    bool right = run.get(object + 0x18c) == 2;
    bool reflected = (run.get8(sprite + 0x40) & 2) != 0;
    if (right == reflected)
        return;
    uint32_t oldLeft = run.get(object + 0x138);
    uint32_t oldRight = run.get(object + 0x140);
    run.put(object + 0x138, 0u - oldRight);
    run.put(object + 0x140, 0u - oldLeft);
    if (right) {
        run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
    } else {
        run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffdu);
    }
    sprite = run.get(object + 0x12c);
    oldLeft = run.get(sprite + 0x118);
    if (oldLeft != 0x80000000u) {
        run.put(sprite + 0x118, 0u - run.get(sprite + 0x120));
        run.put(sprite + 0x120, 0u - oldLeft);
    }
    run.call(0x406150, sprite);
    run.call(0x406180, sprite);
}

void hurtSound(Run &run, uint32_t object) {
    int32_t selection = s32(run.call(0x4a3050, 0)) % 2;
    uint32_t sound = run.get(object + 0x470 + uint32_t(selection) * 4);
    run.call(0x48ce40, 0, {run.get(object + 0xc), sound, 0});
}

uint32_t resourceManager(Run &run, uint32_t object) {
    return run.get(run.get(run.get(object + 0x12c) + 0xc) + 0x28);
}

// 0x45ffc0. Initializes the Mercat's resources, geometry, combat and idle state.
uint32_t construct(Run &run, uint32_t object, uint32_t source, ClawX87State &fp) {
    exactCall(run, fp, 0x44c000, object, 0, {source});
    run.put(object + 0x484, 0);
    run.put(object + 0x488, 0);
    run.put(object + 0x48c, 0);
    run.put(object + 0x490, 0);
    run.put(object + 0x494, 0);
    run.put(object + 0x498, 0);
    run.put(object + 0x49c, 0);
    run.put(object + 0x4a0, 0);
    run.put(object + 0x4a4, 0);
    run.put(object + 0x4a8, 0);
    run.put(object + 0x4ac, 0);
    run.put(object + 0x4b0, 0);
    run.put(object + 0x4b4, 0);
    run.put(object + 0x4b8, 0);
    run.put(object, 0x50e954);
    run.call(0x4c7970, run.get(object + 0x12c), {0x5294c4});
    const uint32_t names[] = {0x5294ac, 0x529490, 0x529478, 0x529464, 0x529450,
        0x52943c, 0x529428, 0x529414, 0x529490, 0x529400, 0x529400,
        0x5293e8, 0x5293e8, 0x5293d0, 0x5293b8, 0x5293a0, 0x52938c,
        0x52938c, 0x529378, 0x529364};
    const uint32_t offsets[] = {0x308, 0x30c, 0x338, 0x334, 0x4bc, 0x4c0,
        0x4c4, 0x4c8, 0x34c, 0x33c, 0x340, 0x32c, 0x374, 0x378,
        0x37c, 0x310, 0x380, 0x36c, 0x344, 0x384};
    for (uint32_t index = 0; index < 20; ++index) {
        uint32_t animation = run.call(0x4062e0, object + 0x128, {names[index]});
        if (!animation)
            animation = run.call(0x4062e0, object + 0x128, {0x5234b4});
        run.put(object + offsets[index], animation);
    }
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    run.call(0x4f6286, resourceManager(run, object) + 0x10, {0x52934c, local});
    run.put(object + 0x450, run.get(local));
    run.put(local, 0);
    run.call(0x4f6286, resourceManager(run, object) + 0x10, {0x529334, local});
    run.put(object + 0x454, run.get(local));
    const uint32_t soundNames[] = {0x52931c, 0x529304, 0x5292ec, 0x5292d4,
        0x5292bc, 0x5292a4, 0x52928c, 0x529274, 0x529260, 0x52924c,
        0x529234, 0x529220};
    const uint32_t soundOffsets[] = {0x458, 0x45c, 0x460, 0x464, 0x468,
        0x46c, 0x470, 0x474, 0x47c, 0x480, 0x478, 0x3a0};
    for (uint32_t index = 0; index < 12; ++index) {
        uint32_t sound = run.call(0x4061b0, resourceManager(run, object), {soundNames[index]});
        run.put(object + soundOffsets[index], sound);
    }
    int32_t choice = s32(run.call(0x4a3050, 0)) % 100;
    uint32_t name = choice < 50 ? 0x529208 : 0x5291f0;
    uint32_t sound = run.call(0x4061b0, resourceManager(run, object), {name});
    run.put(object + 0x3a4, sound);
    run.icall(0x546d5c, {object + 0x220, uint32_t(-111), uint32_t(-5), uint32_t(-22), 22});
    run.call(0x4296f0, object + 0x210, {0xffffffffu, 0xffffffffu, 1, 1});
    run.call(0x40ab80, object + 0x128, {uint32_t(-20), uint32_t(-50), 20, 50});
    run.call(0x406290, run.get(object + 0x12c));
    run.put(object + 0x404, 300);
    run.put(object + 0x400, 150);
    run.call(0x420fc0, object + 0x2f4, {8});
    run.put(object + 0x4d8, 90);
    run.put(object + 0x2e4, 50);
    floatStep(run, fp, CLAW_X87_F64, 0x5262b8);
    floatStep(run, fp, CLAW_X87_MUL_F64, 0x50e948);
    uint32_t health = exactCall(run, fp, 0x4a30e0, 0, 1);
    if (health <= 99)
        health = 99;
    run.put(object + 0x2e4, health);
    uint32_t actor = run.get(object + 0xc);
    run.put(actor + 0x10c, run.get(0x537964) == 11 ? 9 : 15);
    actor = run.get(object + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(actor + 0x10c)});
    floatStep(run, fp, CLAW_X87_MUL_F64, 0x5262b4);
    uint32_t damage = exactCall(run, fp, 0x4a30e0, 0, 1);
    run.put(actor + 0x10c, damage);
    actor = run.get(object + 0xc);
    run.put(actor + 0x104, 10);
    actor = run.get(object + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(actor + 0x104)});
    floatStep(run, fp, CLAW_X87_MUL_F64, 0x5262b0);
    damage = exactCall(run, fp, 0x4a30e0, 0, 1);
    run.put(actor + 0x104, damage);
    run.call(0x40abf0, object + 0x128);
    idle(run, object, fp);
    return object;
}

// 0x460640. Releases the embedded table and reference-counted strings.
uint32_t destroy(Run &run, uint32_t object) {
    run.put(object, 0x50b16c);
    run.call(0x4dbcd0, object + 0x2f4);
    run.call(0x4f6584, object + 0x1a8);
    run.call(0x4f6584, object + 0x1a4);
    run.put(object, 0x50b014);
    return 0;
}

// 0x460620. Scalar deleting destructor.
uint32_t deletingDestroy(Run &run, uint32_t object, uint32_t flags) {
    destroy(run, object);
    if (flags & 1)
        run.call(0x4f6428, 0, {object});
    return object;
}

// 0x460710. Dispatches the state table or delegates to the base class.
uint32_t dispatchState(Run &run, uint32_t object, uint32_t state, ClawX87State &fp) {
    run.put(0x537b88, 0);
    uint32_t low = run.get(0x537b70);
    uint32_t slot;
    if ((s32(state) < s32(low) || s32(state) > run.gets(0x537b74)) &&
        !run.call(0x4db6e0, 0x537b68, {state, 0})) {
        uint32_t message = run.get(0x544b4c);
        uint32_t error = run.call(0x4db5f0, 0);
        run.put(0x544b14, error);
        run.call(0x4db4d0, run.get(0x537b6c), {0x537b68, message, 12});
        slot = run.get(0x537b7c);
        low = run.get(0x537b70);
    } else {
        low = run.get(0x537b70);
        slot = (state - low) * run.get(0x537b80) + run.get(0x537b78);
    }
    if (!run.get(slot)) {
        exactCall(run, fp, 0x44c840, object, 0, {state});
        return 0;
    }
    run.put(0x537b88, 0);
    if ((s32(state) < s32(low) || s32(state) > run.gets(0x537b74)) &&
        !run.call(0x4db6e0, 0x537b68, {state, 0})) {
        uint32_t message = run.get(0x544b4c);
        uint32_t error = run.call(0x4db5f0, 0);
        run.put(0x544b14, error);
        run.call(0x4db4d0, run.get(0x537b6c), {0x537b68, message, 12});
        slot = run.get(0x537b7c);
    } else {
        low = run.get(0x537b70);
        slot = (state - low) * run.get(0x537b80) + run.get(0x537b78);
    }
    uint32_t target = run.get(slot);
    if (owned(target) == 0) {
        innerBody(run, target, object, nullptr, fp);
    } else if (target == 0x460ea0 || target == 0x460c50 || target == 0x4614c0 || target == 0x483dc0) {
        exactCall(run, fp, target, object);
    } else {
        run.call(target, object);
    }
    return 0;
}

// 0x460af0. Updates the base actor and occasionally emits an attack sound.
uint32_t update(Run &run, uint32_t object, uint32_t argument, ClawX87State &fp) {
    exactCall(run, fp, 0x44d000, object, 0, {argument});
    uint32_t player = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (!run.get(player + 0x4))
        return 0;
    uint32_t direction = run.get(object + 0x18c);
    if (!((direction == 3 && run.get(player)) || (direction == 2 && !run.get(player))))
        return 0;
    uint32_t state = run.get(object + 0x184);
    if (state != 3 && state != 4)
        return 0;
    if (run.get(0x537210) - run.get(object + 0x49c) < run.get(object + 0x4a0))
        return 0;
    int32_t chance = run.gets(object + 0x4d8);
    if (s32(run.call(0x4a3050, 0)) % 100 >= chance)
        return 0;
    int32_t selection = s32(run.call(0x4a3050, 0)) % 2;
    uint32_t sound = run.get(object + 0x468 + uint32_t(selection) * 4);
    run.call(0x48ce40, 0, {run.get(object + 0xc), sound, 0});
    if (run.gets(object + 0x20) >= 2)
        run.put(object + 0x14, 0x44e620);
    uint32_t reduced = run.get(object + 0x4d8) - 30;
    run.put(object + 0x4d8, reduced);
    if (s32(reduced) < 0)
        run.put(object + 0x4d8, 0);
    run.put(object + 0x4a0, 500);
    run.put(object + 0x49c, run.get(0x537210));
    return 0;
}

// 0x460bf0. Enters home state and starts a randomized timer.
uint32_t home(Run &run, uint32_t object) {
    run.call(0x44d9f0, object);
    uint32_t sprite = run.get(object + 0x12c);
    uint32_t animation = run.get(object + 0x344);
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    int32_t duration = s32(run.call(0x4a3050, 0)) % 1001;
    run.put(object + 0x4a8, uint32_t(duration) + 1000);
    run.put(object + 0x4a4, run.get(0x537210));
    return 0;
}

// 0x461020. Chooses a level-dependent block instead of the base hit response.
uint32_t projectileHit(Run &run, uint32_t object, uint32_t argument, ClawX87State &fp) {
    int32_t chance = s32(run.call(0x4a3050, 0)) % 101;
    uint32_t level = run.get(0x537964);
    if ((level == 11 && chance < 25) || (level == 12 && chance < 50)) {
        run.put(argument + 0x8, run.get(argument + 0x8) | 0x10000);
        face(run, object);
        return block(run, object);
    }
    hurtSound(run, object);
    exactCall(run, fp, 0x44d570, object, 0, {argument});
    return 0;
}

// 0x461170. Blocks selected player attacks in mode five.
uint32_t meleeHit(Run &run, uint32_t object, uint32_t argument, ClawX87State &fp) {
    uint32_t player = run.get(0x537e88);
    uint32_t attack = run.get(run.get(run.get(player + 0x6c) + 0x14) + 0x3c);
    if ((attack == 1 || attack == 2 || attack == 7 || attack == 8) && run.get(player + 0xcc) == 5) {
        face(run, object);
        return block(run, object);
    }
    hurtSound(run, object);
    exactCall(run, fp, 0x44d460, object, 0, {argument});
    return 0;
}

uint32_t innerBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments, ClawX87State &fp) {
    switch (function) {
    case 0x45ffc0:
        return construct(run, receiver, arguments[0], fp);
    case 0x460620:
        return deletingDestroy(run, receiver, arguments[0]);
    case 0x460640:
        return destroy(run, receiver);
    case 0x460710:
        return dispatchState(run, receiver, arguments[0], fp);
    case 0x460af0:
        return update(run, receiver, arguments[0], fp);
    case 0x460bf0:
        return home(run, receiver);
    case 0x460e20:
        return idle(run, receiver, fp);
    case 0x461020:
        return projectileHit(run, receiver, arguments[0], fp);
    case 0x461170:
        return meleeHit(run, receiver, arguments[0], fp);
    case 0x4612c0:
        return block(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    auto fp = run.x87_entry(function);
    uint32_t result = innerBody(run, function, receiver, arguments, fp);
    run.x87_finish(function, fp);
    return result;
}
} // namespace

CLAW_MODULE_ENTRY(claw_mercat_helper_01_entry, owned, body)
