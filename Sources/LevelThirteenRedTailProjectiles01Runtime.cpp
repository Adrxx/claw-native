// Red Tail knife and bullet creation, state dispatch and lifetime behavior.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x410640:
    case 0x410700:
    case 0x4134e0:
    case 0x413660:
    case 0x4139c0:
    case 0x413b80:
        return 1;
    case 0x413940:
    case 0x413960:
    case 0x413f80:
        return 0;
    default:
        return -1;
    }
}

// 0x4134e0: construct the knife behavior on the common projectile base.
uint32_t knifeConstructor(Run &run, uint32_t receiver, uint32_t object) {
    run.call(0x4107c0, receiver, {object});
    run.put(receiver + 0x150, 0); // Creation tick.
    run.put(receiver + 0x154, 0); // Lifetime.
    run.put(receiver, 0x50b95c);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x524474});
    const uint32_t output = run.automatic(4);
    run.put(output, 0);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t resources = run.get(run.get(actor + 0xc) + 0x2c);
    run.call(0x4f6286, resources + 0x10, {0x52417c, output});
    run.put(receiver + 0x148, run.get(output)); // Cycle animation.
    actor = run.get(receiver + 0x12c);
    const uint32_t image = run.get(actor + 0x174);
    if (image != 0) {
        run.put(actor + 0x138, run.get(image + 0x20) - run.get(image + 0x18));
        run.put(actor + 0x13c, run.get(image + 0x24) - run.get(image + 0x1c));
        run.put(actor + 0x140, run.get(image + 0x20) + run.get(image + 0x18) - 1);
        run.put(actor + 0x144, run.get(image + 0x1c) + run.get(image + 0x24) - 1);
    }
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0xd0, 0x40);
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x164, run.get(actor + 0x164) | 0x2000);
    run.put(receiver + 0x154, 0x2710);
    run.put(receiver + 0x150, run.get(0x537210));
    return receiver;
}

// 0x4139c0: construct the bullet behavior and optional visual flare.
uint32_t bulletConstructor(Run &run, uint32_t receiver, uint32_t object) {
    run.call(0x4107c0, receiver, {object});
    run.put(receiver, 0x50b994);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x5244d8});
    const uint32_t output = run.automatic(4);
    run.put(output, 0);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t resources = run.get(run.get(actor + 0xc) + 0x2c);
    run.call(0x4f6286, resources + 0x10, {0x52417c, output});
    run.put(receiver + 0x148, run.get(output));
    run.put(output, 0);
    actor = run.get(receiver + 0x12c);
    resources = run.get(run.get(actor + 0xc) + 0x2c);
    run.call(0x4f6286, resources + 0x10, {0x5244b8, output});
    run.put(receiver + 0x150, run.get(output)); // Explosion animation.
    run.call(0x408050, run.get(receiver + 0x12c));
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x164, run.get(actor + 0x164) | 0x2020);
    uint32_t owner = run.get(receiver + 0xc);
    run.put(owner + 0x8, run.get(owner + 0x8) | 0x80000);
    if (run.get(0x53724c) == 0 && run.get(run.get(0x5371fc) + 0x124) != 0) {
        actor = run.get(receiver + 0x12c);
        const uint32_t layer = run.get(run.get(run.get(receiver + 0x130) + 0xc) + 0x8);
        const uint32_t flare = run.call(0x4c8da0, layer,
            {0, run.get(actor + 0x4c), run.get(actor + 0x50), run.get(actor + 0x64) - 1, 0x522e24, 0x40000});
        run.put(receiver + 0x154, flare);
        run.put(receiver + 0x158, 2);
    } else {
        run.put(receiver + 0x154, 0);
        run.put(receiver + 0x158, 1);
    }
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0xd0, 0x40);
    return receiver;
}

// 0x410640 and 0x410700: object-logic notifications for the two projectiles.
uint32_t projectileLogic(Run &run, uint32_t object, bool bullet) {
    const uint32_t logic = run.get(object + 0x6c);
    const uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        run.put(logic + 0x1c, 0x3e8);
        uint32_t behavior = run.call(0x4f63ec, 0, {bullet ? 0x160u : 0x158u});
        run.put(run.automatic(4), behavior);
        if (behavior != 0) {
            const uint32_t previousFrame = run.frame;
            run.frame -= 0x1c;
            behavior = bullet ? bulletConstructor(run, behavior, object) : knifeConstructor(run, behavior, object);
            run.frame = previousFrame;
        }
        run.vcall(behavior, 0x10);
        run.put(logic + 0x18, behavior);
    } else if (state == 0x1d) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (state == 0x1e) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (state != 0x3e8) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}

// 0x413660 and 0x413b80: dispatch through the independently registered tables.
uint32_t dispatchState(Run &run, uint32_t receiver, uint32_t state, uint32_t table) {
    uint32_t lower = run.get(table + 0x8);
    run.put(table + 0x20, 0);
    uint32_t slot;
    if (s32(state) >= s32(lower) && s32(state) <= run.gets(table + 0xc)) {
        slot = (state - lower) * run.get(table + 0x18) + run.get(table + 0x10);
    } else if (run.call(0x4db6e0, table, {state, 0}) != 0) {
        lower = run.get(table + 0x8);
        slot = (state - lower) * run.get(table + 0x18) + run.get(table + 0x10);
    } else {
        const uint32_t diagnostic = run.get(0x544b4c);
        const uint32_t sequence = run.call(0x4db5f0, 0);
        run.put(0x544b14, sequence);
        run.call(0x4db4d0, run.get(table + 0x4), {table, diagnostic, 0xc});
        slot = run.get(table + 0x14);
        lower = run.get(table + 0x8);
    }
    if (run.get(slot) == 0) {
        run.call(0x473f40, receiver, {state});
        return 0;
    }
    run.put(table + 0x20, 0);
    if (s32(state) >= s32(lower) && s32(state) <= run.gets(table + 0xc)) {
        slot = (state - lower) * run.get(table + 0x18) + run.get(table + 0x10);
    } else if (run.call(0x4db6e0, table, {state, 0}) != 0) {
        lower = run.get(table + 0x8);
        slot = (state - lower) * run.get(table + 0x18) + run.get(table + 0x10);
    } else {
        const uint32_t diagnostic = run.get(0x544b4c);
        const uint32_t sequence = run.call(0x4db5f0, 0);
        run.put(0x544b14, sequence);
        run.call(0x4db4d0, run.get(table + 0x4), {table, diagnostic, 0xc});
        slot = run.get(table + 0x14);
    }
    run.call(run.get(slot), receiver);
    return 0;
}

// 0x413940: enter the knife's falling state after the common transition.
uint32_t knifeFalling(Run &run, uint32_t receiver) {
    run.call(0x474290, receiver);
    run.put(run.get(receiver + 0xc) + 0xcc, 7);
    return 0;
}

// 0x413960: advance the animation and retire an expired or low knife.
uint32_t knifeTick(Run &run, uint32_t receiver) {
    if (run.get(receiver + 0x148) != 0) {
        run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    }
    const uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x150);
    if (elapsed >= run.get(receiver + 0x154) || !(double(run.gets(0x52b360)) >= run.getd(receiver + 0x70))) {
        const uint32_t actor = run.get(receiver + 0x12c);
        run.put(actor + 0x8, run.get(actor + 0x8) | 0x10000);
    }
    return 0;
}

// 0x413f80: select the explosion state, animation and collision flags.
uint32_t bulletExplosion(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    const uint32_t state = run.call(0x4dba00, 0x537668, {0x524418});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 0x4);
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0xd0, 0x1000000);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x5244fc});
    actor = run.get(receiver + 0x12c);
    const uint32_t animation = run.get(receiver + 0x150);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    run.put(receiver + 0xc8, 1);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x410640:
        return projectileLogic(run, arguments[0], false);
    case 0x410700:
        return projectileLogic(run, arguments[0], true);
    case 0x4134e0:
        return knifeConstructor(run, receiver, arguments[0]);
    case 0x413660:
        return dispatchState(run, receiver, arguments[0], 0x534b78);
    case 0x413940:
        return knifeFalling(run, receiver);
    case 0x413960:
        return knifeTick(run, receiver);
    case 0x4139c0:
        return bulletConstructor(run, receiver, arguments[0]);
    case 0x413b80:
        return dispatchState(run, receiver, arguments[0], 0x534b50);
    case 0x413f80:
        return bulletExplosion(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_thirteen_red_tail_projectiles_01_entry, owned, body)
