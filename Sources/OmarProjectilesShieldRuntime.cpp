// Omar projectile and elemental shield game behavior.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x410400:
    case 0x412330:
    case 0x412460:
    case 0x464f20:
    case 0x464fe0:
    case 0x4651a0:
    case 0x465480:
        return 1;
    case 0x412740:
    case 0x465550:
        return 0;
    default:
        return -1;
    }
}

// 0x412330. Projectile +0x12c is its actor; +0x148 is the animation
// resource and +0x150 is the number of falling glitter particles.
uint32_t bulletConstructor(Run &run, uint32_t receiver, uint32_t actor) {
    run.call(0x4107c0, receiver, {actor});
    run.put(receiver, 0x50b8b4);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x52433c});
    const uint32_t output = run.automatic(4);
    run.put(output, 0);
    const uint32_t world = run.get(run.get(receiver + 0x12c) + 0xc);
    run.call(0x4f6286, run.get(world + 0x2c) + 0x10, {0x52417c, output});
    run.put(receiver + 0x148, run.get(output));
    if (run.get(0x53724c) == 0 && run.get(run.get(0x5371fc) + 0x124) != 0) {
        run.put(receiver + 0x150, 2);
    } else {
        run.put(receiver + 0x150, 1);
    }
    run.put(run.get(receiver + 0x12c) + 0xd0, 0x40);
    return receiver;
}

// 0x464fe0. Shield +0xc/+0x2c retain the actor; +0x10/+0x30 retain
// its logic record, and +0x34 saves the selected animation frame.
uint32_t shieldConstructor(Run &run, uint32_t receiver, uint32_t actor) {
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x8, actor);
    run.put(receiver + 0xc, actor);
    run.put(receiver + 0x10, run.get(actor + 0x6c));
    run.put(receiver + 0x4, 0);
    run.call(0x4c7fa0, actor, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0xc), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x28, actor);
    run.put(receiver + 0x2c, actor);
    run.put(receiver + 0x30, run.get(actor + 0x6c));
    run.put(receiver, 0x50ebb4);
    run.put(run.get(receiver + 0x2c) + 0xd0, 4);
    run.put(run.get(receiver + 0x2c) + 0xd4, 0x3000032);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x529a8c});
    uint32_t currentActor = run.get(receiver + 0x2c);
    run.put(receiver + 0x34, run.get(currentActor + 0x190));
    run.call(0x4c79e0, currentActor, {0x529a8c, 0});
    currentActor = run.get(receiver + 0xc);
    if (run.get(currentActor + 0x64) == 0 && run.get(currentActor + 0x64) != 5000) {
        run.put(currentActor + 0x64, 5000);
        run.put(currentActor + 0x8, run.get(currentActor + 0x8) | 0x20000);
    }
    currentActor = run.get(receiver + 0x2c);
    run.put(currentActor + 0x128, 0xfffffff2);
    run.put(currentActor + 0x12c, 0xfffffffa);
    run.put(currentActor + 0x130, 0xc);
    run.put(currentActor + 0x134, 0x15);
    currentActor = run.get(receiver + 0x2c);
    run.put(currentActor + 0x144, 0x15);
    run.put(currentActor + 0x138, 0xfffffff2);
    run.put(currentActor + 0x13c, 0xfffffffa);
    run.put(currentActor + 0x140, 0xc);
    run.call(0x465450, receiver);
    return receiver;
}

// 0x410400 and 0x464f20. Actor +0x6c points to command record;
// record +0x1c is the command and +0x18 receives the behavior instance.
uint32_t factory(Run &run, uint32_t actor, bool shield) {
    const uint32_t logic = run.get(actor + 0x6c);
    const uint32_t command = run.get(logic + 0x1c);
    if (command == 0) {
        run.put(logic + 0x1c, 1000);
        uint32_t behavior = run.call(0x4f63ec, 0, {shield ? 0x48u : 0x158u});
        if (behavior != 0) {
            const uint32_t frame = run.frame;
            run.frame = frame - 0x1c;
            if (shield) {
                behavior = shieldConstructor(run, behavior, actor);
            } else {
                behavior = bulletConstructor(run, behavior, actor);
            }
            run.frame = frame;
        }
        run.vcall(behavior, 0x10);
        run.put(logic + 0x18, behavior);
    } else if (command == 0x1d) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (command == 0x1e) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (command != 1000) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}

// 0x412460 and 0x4651a0. Registry +0x8/+0xc are signed bounds,
// +0x10 is its cell buffer, +0x18 its stride and +0x20 lookup scratch.
uint32_t lookupCell(Run &run, uint32_t registry, uint32_t index) {
    uint32_t lower = run.get(registry + 0x8);
    if (s32(index) < s32(lower) || s32(index) > s32(run.get(registry + 0xc))) {
        if (run.call(0x4db6e0, registry, {index, 0}) == 0) {
            const uint32_t message = run.get(0x544b4c);
            const uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            run.call(0x4db4d0, run.get(registry + 0x4), {registry, message, 0xc});
            return run.get(registry + 0x14);
        }
        lower = run.get(registry + 0x8);
    }
    return (index - lower) * run.get(registry + 0x18) + run.get(registry + 0x10);
}

void dispatch(Run &run, uint32_t receiver, uint32_t index, bool shield) {
    const uint32_t registry = shield ? 0x537c00u : 0x534b28u;
    run.put(registry + 0x20, 0);
    const uint32_t first = lookupCell(run, registry, index);
    if (run.get(first) != 0) {
        run.put(registry + 0x20, 0);
        const uint32_t second = lookupCell(run, registry, index);
        run.call(run.get(second), receiver);
    } else if (shield) {
        run.call(0x4a36f0, 0, {receiver});
    } else {
        run.call(0x473f40, receiver, {index});
    }
}

void clearX87Receipt(ClawX87State &state, uint32_t pop, uint32_t push) {
    state.popCount = pop;
    state.pushCount = push;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
}

uint32_t randomCoordinate(Run &run, uint32_t minimum, uint32_t maximum) {
    const uint32_t divisor = maximum - minimum + 1;
    const uint32_t random = run.call(0x4a3050, 0);
    if (divisor == 0) {
        return (random & 1) != 0 ? minimum : maximum;
    }
    const int64_t remainder = int64_t(s32(random)) % int64_t(s32(divisor));
    return uint32_t(remainder) + minimum;
}

uint32_t coordinateInteger(Run &run, ClawX87State &state, uint32_t integer,
                           uint32_t low, uint32_t high) {
    run.x87_step(CLAW_X87_I32, state, {integer});
    run.x87_step(CLAW_X87_ADD_F64, state, {low, high});
    clearX87Receipt(state, 1, 0);
    return run.call_x87_exact(0x4a30e0, 0, state);
}

// 0x412740. Base falling updates projectile state; each particle uses
// +0x68/+0x70 binary64 position and actor rectangle +0x118 through +0x124.
uint32_t falling(Run &run, uint32_t receiver) {
    auto state = run.x87_entry(0x412740);
    clearX87Receipt(state, 0, 0);
    run.call_x87_exact(0x4742f0, receiver, state);
    uint32_t count = 0;
    if (s32(run.get(receiver + 0x150)) > 0) {
        do {
            const uint32_t xLow = run.get(receiver + 0x68);
            const uint32_t xHigh = run.get(receiver + 0x6c);
            uint32_t actor = run.get(receiver + 0xc);
            const uint32_t xMaximum = run.get(actor + 0x120);
            const uint32_t xMinimum = run.get(actor + 0x118);
            const uint32_t x = coordinateInteger(run, state,
                randomCoordinate(run, xMinimum, xMaximum), xLow, xHigh);
            const uint32_t yLow = run.get(receiver + 0x70);
            actor = run.get(receiver + 0xc);
            const uint32_t yHigh = run.get(receiver + 0x74);
            const uint32_t yMaximum = run.get(actor + 0x124);
            const uint32_t yMinimum = run.get(actor + 0x11c);
            const uint32_t yOffset = randomCoordinate(run, yMinimum, yMaximum);
            actor = run.get(receiver + 0xc);
            const uint32_t depth = run.get(actor + 0x64) - 1;
            const uint32_t y = coordinateInteger(run, state, yOffset, yLow, yHigh);
            const uint32_t source = run.get(receiver + 0x130);
            const uint32_t creator = run.get(run.get(source + 0xc) + 0x8);
            const uint32_t created = run.call(0x4c8da0, creator, {0, x, y, depth, 0x522594, 0x40000});
            const uint32_t callback = run.get(run.get(created + 0x6c) + 0x10);
            run.call(callback, 0, {created});
            ++count;
        } while (s32(count) < s32(run.get(receiver + 0x150)));
    }
    run.x87_finish(0x412740, state);
    return 0;
}

// 0x465480. Select elemental animation only if actor +0x170 resource
// differs; the lookup output aliases the incoming selection slot.
void selectShield(Run &run, uint32_t receiver, uint32_t selection) {
    if (selection != 0 && selection != 1) {
        return;
    }
    const uint32_t key = selection == 0 ? 0x529a8cu : 0x529aa0u;
    const uint32_t output = run.automatic(4);
    run.put(output, 0);
    const uint32_t previous = run.get(run.get(receiver + 0x2c) + 0x170);
    const uint32_t world = run.get(run.get(receiver + 0xc) + 0xc);
    run.call(0x4f6286, run.get(world + 0x10) + 0x10, {key, output});
    if (previous != run.get(output)) {
        run.call(0x4c7970, run.get(receiver + 0x2c), {key});
        const uint32_t actor = run.get(receiver + 0x2c);
        run.put(receiver + 0x34, run.get(actor + 0x190));
        run.call(0x4c79e0, actor, {key, 0});
    }
}

// 0x465550. Actor +0x74 is attack target; target +0xd0 is its type
// and target +0x8 holds flags marked for fire or ice projectile hits.
uint32_t attack(Run &run, uint32_t receiver) {
    const uint32_t target = run.get(run.get(receiver + 0xc) + 0x74);
    const uint32_t type = run.get(target + 0xd0);
    if (type == 0x20 || type == 0x2000000) {
        run.put(target + 0x8, run.get(target + 0x8) | 0x10000);
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x410400:
        return factory(run, arguments[0], false);
    case 0x412330:
        return bulletConstructor(run, receiver, arguments[0]);
    case 0x412460:
        dispatch(run, receiver, arguments[0], false);
        return 0;
    case 0x412740:
        return falling(run, receiver);
    case 0x464f20:
        return factory(run, arguments[0], true);
    case 0x464fe0:
        return shieldConstructor(run, receiver, arguments[0]);
    case 0x4651a0:
        dispatch(run, receiver, arguments[0], true);
        return 0;
    case 0x465480:
        selectShield(run, receiver, arguments[0]);
        return 0;
    case 0x465550:
        return attack(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_omar_projectiles_shield_entry, owned, body)
