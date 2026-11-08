// Level 9 projectile construction and firing states, recovered from v1.0.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x462330:
    case 0x48a8c0:
    case 0x497f70:
    case 0x4981c0:
        return 1;
    case 0x498580:
    case 0x498590:
    case 0x4985f0:
    case 0x498690:
    case 0x4988b0:
    case 0x4988f0:
        return 0;
    default:
        return -1;
    }
}

// 0x462330: select the fourth saw blade timing, then run its common logic.
uint32_t sawBlade4(Run &run, uint32_t object) {
    run.put(0x537b90, 4);
    return run.call(0x462040, 0, {object});
}

// 0x48a8c0: skull cannon constructor; +0x48/+0x4c are home/firing resources.
uint32_t skullCannon(Run &run, uint32_t receiver, uint32_t object) {
    run.call(0x414030, receiver, {object});
    run.put(receiver, 0x50f744);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x52c260});
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    uint32_t manager = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x2c);
    run.call(0x4f6286, manager + 0x10, {0x52c244, local});
    run.put(receiver + 0x4c, run.get(local));
    run.put(local, 0);
    manager = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x2c);
    run.call(0x4f6286, manager + 0x10, {0x52c22c, local});
    run.put(receiver + 0x48, run.get(local));
    run.call(0x4145b0, receiver);
    return receiver;
}

// Refresh +0x174 animation frame and +0x16c animation index from +0x170.
void firstFrame(Run &run, uint32_t object) {
    uint32_t animation = run.get(object + 0x170);
    if (animation) {
        uint32_t frame = 0;
        if (s32(run.get(animation + 0x64)) <= 0 && s32(run.get(animation + 0x68)) >= 0) {
            frame = run.get(run.get(animation + 0x14));
        }
        run.put(object + 0x174, frame);
        run.put(object + 0x16c, 0);
    }
}

// 0x497f70: projectile launcher constructor. +0x10/+0x30 are logic contexts.
uint32_t projectileConstructor(Run &run, uint32_t receiver, uint32_t object) {
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x08, object);
    run.put(receiver + 0x0c, object);
    run.put(receiver + 0x10, run.get(object + 0x6c));
    run.put(receiver + 0x04, 0);
    run.call(0x4c7fa0, object, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0x0c), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x28, object);
    run.put(receiver + 0x2c, object);
    run.put(receiver + 0x30, run.get(object + 0x6c));
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x5c, 0);
    uint32_t actor = run.get(receiver + 0x0c);
    run.put(receiver, 0x50fc1c);
    if (run.get(actor + 0x64) == 0) {
        run.put(actor + 0x64, 0xfaa);
        run.put(actor + 0x08, run.get(actor + 0x08) | 0x20000);
    }
    run.put(receiver + 0x48, run.get(run.get(receiver + 0x2c) + 0x190));
    actor = run.get(receiver + 0x2c);
    run.put(actor + 0x08, run.get(actor + 0x08) | 4);
    run.put(run.get(receiver + 0x2c) + 0xd0, 1);
    run.put(run.get(receiver + 0x2c) + 0xd8, 2);
    actor = run.get(receiver + 0x0c);
    if (run.get(actor + 0x148) == 0) {
        run.put(actor + 0x148, 0x64);
    }
    actor = run.get(receiver + 0x0c);
    if (run.get(actor + 0x14c) == 0) {
        run.put(actor + 0x14c, 0x64);
    }
    uint32_t context = run.get(receiver + 0x10);
    if (run.get(context + 0xbc) == 0) {
        run.put(context + 0xbc, 0x1f4);
    }
    actor = run.get(receiver + 0x0c);
    if (run.get(actor + 0x108) == 0) {
        run.put(actor + 0x108, 0);
    }
    actor = run.get(receiver + 0x0c);
    if (run.get(actor + 0x110) == 0) {
        run.put(actor + 0x110, 4);
    }
    run.put(run.get(receiver + 0x0c) + 0x104, 5);
    actor = run.get(receiver + 0x0c);
    uint32_t y = run.get(actor + 0x50);
    uint32_t x = run.get(actor + 0x4c);
    context = run.get(receiver + 0x10);
    uint32_t bottom = run.get(context + 0x38) - y;
    uint32_t top = run.get(context + 0x34) - y;
    uint32_t right = run.get(context + 0x30) - x;
    uint32_t left = run.get(context + 0x2c) - x;
    actor = run.get(receiver + 0x2c);
    run.put(actor + 0x138, left);
    run.put(actor + 0x13c, top);
    run.put(actor + 0x140, right);
    run.put(actor + 0x144, bottom);
    firstFrame(run, run.get(receiver + 0x2c));
    run.put(receiver + 0x60, 1);
    run.call(0x465450, receiver);
    return receiver;
}

uint32_t tableEntry(Run &run, uint32_t index) {
    if (s32(index) < s32(run.get(0x53caa8)) || s32(index) > s32(run.get(0x53caac))) {
        if (!run.call(0x4db6e0, 0x53caa0, {index, 0})) {
            uint32_t message = run.get(0x544b4c);
            run.put(0x544b14, run.call(0x4db5f0, 0));
            run.call(0x4db4d0, run.get(0x53caa4), {0x53caa0, message, 0x0c});
            return run.get(0x53cab4);
        }
    }
    return (index - run.get(0x53caa8)) * run.get(0x53cab8) + run.get(0x53cab0);
}

// 0x4981c0: state-table dispatch or object free for an empty entry.
uint32_t projectileDispatch(Run &run, uint32_t receiver, uint32_t index) {
    run.put(0x53cac0, 0);
    uint32_t slot = tableEntry(run, index);
    if (run.get(slot)) {
        run.put(0x53cac0, 0);
        slot = tableEntry(run, index);
        return run.call(run.get(slot), receiver);
    }
    return run.call(0x4a36f0, 0, {receiver});
}

// 0x498590: enter firing state; +0x24 preserves the former state.
uint32_t firingStart(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x524548});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    run.put(receiver + 0x34, run.get(run.get(receiver + 0x2c) + 0x190));
    run.call(0x4c8220, run.get(receiver + 0x2c) + 0x188, {run.get(receiver + 0x48)});
    if (run.get(receiver + 0x60)) {
        run.put(run.get(receiver + 0x30) + 0x20, run.get(run.get(receiver + 0x0c) + 0x108));
        run.put(receiver + 0x60, 0);
    }
    run.put(receiver + 0x4c, 0);
    return 0;
}

// 0x498580: mark the actor active before entering firing.
uint32_t activate(Run &run, uint32_t receiver) {
    uint32_t actor = run.get(receiver + 0x2c);
    run.put(actor + 0x08, run.get(actor + 0x08) | 1);
    firingStart(run, receiver);
    return 0;
}

// 0x498690: create and initialize a projectile, with direction-specific speed.
uint32_t fireProjectile(Run &run, uint32_t receiver) {
    uint32_t actor = run.get(receiver + 0x2c);
    uint32_t level = run.get(run.get(run.get(receiver + 0x30) + 0x0c) + 0x08);
    uint32_t projectile = run.call(0x4c8da0, level, {0, run.get(actor + 0x4c), run.get(actor + 0x50), run.get(actor + 0x64) - 1, 0x522e0c, 0x40000});
    if (run.get(run.get(receiver + 0x10) + 0x68)) {
        uint32_t text = run.automatic(-0x10);
        run.call(0x4f6439, text);
        run.call(0x4f4f58, 0, {text, 0x52d4c8, run.get(run.get(receiver + 0x10) + 0x68)});
        uint32_t resource = run.call(0x4f6974, text, {0});
        run.call(0x4c7970, projectile, {resource});
        uint32_t logic = run.get(projectile + 0x6c);
        uint32_t damage = run.get(run.get(receiver + 0x0c) + 0x104);
        run.put(projectile + 0xd0, 0x40);
        run.put(projectile + 0x104, damage);
        run.call(run.get(logic + 0x10), 0, {projectile});
        uint32_t manager = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x2c);
        uint32_t cycle = run.call(0x4061b0, manager, {0x5240d8});
        logic = run.get(projectile + 0x6c);
        run.put(run.get(logic + 0x18) + 0x148, cycle);
        uint32_t motion = run.get(run.get(projectile + 0x6c) + 0x18);
        run.vcall(motion, 0x28);
        run.call(0x4f6584, text);
    } else {
        run.call(0x4c7970, projectile, {0x52d4b4});
        uint32_t animation = run.get(projectile + 0x170);
        uint32_t index = run.get(run.get(receiver + 0x10) + 0x64);
        if (animation) {
            uint32_t frame = run.call(0x40f680, animation, {index});
            run.put(projectile + 0x174, frame);
            run.put(projectile + 0x16c, index);
        }
        uint32_t logic = run.get(projectile + 0x6c);
        uint32_t damage = run.get(run.get(receiver + 0x0c) + 0x104);
        run.put(projectile + 0xd0, 0x40);
        run.put(projectile + 0x104, damage);
        run.call(run.get(logic + 0x10), 0, {projectile});
    }
    actor = run.get(receiver + 0x0c);
    uint32_t direction = run.get(actor + 0x110);
    if (direction == 4) {
        uint32_t speed = 0 - run.get(actor + 0x148);
        run.putd(run.get(run.get(projectile + 0x6c) + 0x18) + 0x50, double(s32(speed)));
        uint32_t motion = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(motion + 0x58, 0);
        run.put(motion + 0x5c, 0);
    } else if (direction == 6) {
        run.putd(run.get(run.get(projectile + 0x6c) + 0x18) + 0x50, double(s32(run.get(actor + 0x148))));
        uint32_t motion = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(motion + 0x58, 0);
        run.put(motion + 0x5c, 0);
    } else if (direction == 2) {
        run.putd(run.get(run.get(projectile + 0x6c) + 0x18) + 0x58, double(s32(run.get(actor + 0x14c))));
        uint32_t motion = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(motion + 0x50, 0);
        run.put(motion + 0x54, 0);
    } else if (direction == 8) {
        uint32_t speed = 0 - run.get(actor + 0x14c);
        run.putd(run.get(run.get(projectile + 0x6c) + 0x18) + 0x58, double(s32(speed)));
        uint32_t motion = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(motion + 0x50, 0);
        run.put(motion + 0x54, 0);
    }
    uint32_t motion = run.get(run.get(projectile + 0x6c) + 0x18);
    run.put(motion + 0x40, 0);
    run.put(motion + 0x44, 0);
    return 0;
}

// 0x4988b0: enter waiting, remembering the timestamp and configured delay.
uint32_t waitStart(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x529a48});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    run.put(receiver + 0x54, run.get(run.get(receiver + 0x10) + 0xbc));
    run.put(receiver + 0x50, run.get(0x537210));
    return 0;
}

void nestedFire(Run &run, uint32_t receiver) {
    uint32_t outerFrame = run.frame;
    run.frame -= 8;
    fireProjectile(run, receiver);
    run.frame = outerFrame;
}

// 0x4985f0: advance firing animation, emit once, then enter waiting.
uint32_t firingUpdate(Run &run, uint32_t receiver) {
    uint32_t result = run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    if (result == 1 && run.get(receiver + 0x4c) == 0) {
        nestedFire(run, receiver);
        run.put(receiver + 0x4c, 1);
    }
    uint32_t animation = run.get(receiver + 0x2c) + 0x188;
    if (run.get(animation + 0x1c) && run.get(animation + 0x14) == 0) {
        if (run.get(receiver + 0x4c) == 0) {
            nestedFire(run, receiver);
        }
        firstFrame(run, run.get(receiver + 0x2c));
        waitStart(run, receiver);
    }
    return 0;
}

// 0x4988f0: unsigned elapsed time clears the actor's active bit at expiry.
uint32_t waitingUpdate(Run &run, uint32_t receiver) {
    uint32_t actor = run.get(receiver + 0x2c);
    if ((run.get8(actor + 0x08) & 1) == 0) {
        run.put(receiver + 0x60, 1);
    }
    uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x50);
    if (elapsed >= run.get(receiver + 0x54)) {
        actor = run.get(receiver + 0x2c);
        run.put(actor + 0x08, run.get(actor + 0x08) & 0xfffffffe);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x462330:
        return sawBlade4(run, arguments[0]);
    case 0x48a8c0:
        return skullCannon(run, receiver, arguments[0]);
    case 0x497f70:
        return projectileConstructor(run, receiver, arguments[0]);
    case 0x4981c0:
        return projectileDispatch(run, receiver, arguments[0]);
    case 0x498580:
        return activate(run, receiver);
    case 0x498590:
        return firingStart(run, receiver);
    case 0x4985f0:
        return firingUpdate(run, receiver);
    case 0x498690:
        return fireProjectile(run, receiver);
    case 0x4988b0:
        return waitStart(run, receiver);
    case 0x4988f0:
        return waitingUpdate(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_nine_projectile_hazards_01_entry, owned, body)
