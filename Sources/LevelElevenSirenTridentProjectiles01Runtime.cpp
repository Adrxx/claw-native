// Level 11 siren and trident projectiles, recovered from the original entries.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4104c0:
    case 0x410580:
    case 0x412880:
    case 0x4129d0:
    case 0x412ce0:
    case 0x412e80:
        return 1;
    case 0x412cb0:
    case 0x413280:
    case 0x413470:
    case 0x4133e0:
        return 0;
    default:
        return -1;
    }
}

ClawX87State floatingState() {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    return fp;
}

uint32_t balanced(Run &run, uint32_t function, uint32_t receiver, ClawX87State &fp,
                  std::initializer_list<uint32_t> arguments = {}) {
    fp.popCount = 0;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(function, receiver, fp, arguments);
}

// 0x412880. Siren projectile constructor: +0x12c actor, +0xc descriptor,
// +0x148 resource, and actor +0x174 optional rectangle.
uint32_t sirenConstructor(Run &run, uint32_t receiver, uint32_t argument) {
    auto fp = floatingState();
    balanced(run, 0x4107c0, receiver, fp, {argument});
    run.put(receiver, 0x50b8ec);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x524394});
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    uint32_t resourceOwner = run.get(run.get(actor + 0xc) + 0x2c);
    run.call(0x4f6286, resourceOwner + 0x10, {0x52437c, local});
    run.put(receiver + 0x148, run.get(local));
    actor = run.get(receiver + 0x12c);
    uint32_t rectangle = run.get(actor + 0x174);
    if (rectangle) {
        uint32_t right = run.get(rectangle + 0x20);
        uint32_t left = run.get(rectangle + 0x18);
        run.put(actor + 0x138, right - left);
        uint32_t bottom = run.get(rectangle + 0x24);
        run.put(actor + 0x13c, bottom - run.get(rectangle + 0x1c));
        right = run.get(rectangle + 0x20);
        left = run.get(rectangle + 0x18);
        run.put(actor + 0x140, right + left - 1);
        bottom = run.get(rectangle + 0x24);
        uint32_t top = run.get(rectangle + 0x1c);
        run.put(actor + 0x144, bottom + top - 1);
    }
    run.put(run.get(receiver + 0x12c) + 0xd0, 0x40);
    run.put(run.get(receiver + 0xc) + 0xfc, 0x26bf);
    return receiver;
}

// 0x412ce0. Trident constructor: +0x150 explosion resource, +0x154 flare,
// +0x158 glitter count; +0x130 links the object-creation service.
uint32_t tridentConstructor(Run &run, uint32_t receiver, uint32_t argument) {
    auto fp = floatingState();
    balanced(run, 0x4107c0, receiver, fp, {argument});
    run.put(receiver, 0x50b924);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x5243f8});
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    uint32_t resourceOwner = run.get(run.get(actor + 0xc) + 0x2c);
    run.call(0x4f6286, resourceOwner + 0x10, {0x5243e0, local});
    run.put(receiver + 0x150, run.get(local));
    run.call(0x408050, run.get(receiver + 0x12c));
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x164, run.get(actor + 0x164) | 0x2020);
    uint32_t descriptor = run.get(receiver + 0xc);
    run.put(descriptor + 0x8, run.get(descriptor + 0x8) | 0x80000);
    if (!run.get(0x53724c) && run.get(run.get(0x5371fc) + 0x124)) {
        actor = run.get(receiver + 0x12c);
        uint32_t depth = run.get(actor + 0x64) - 1;
        uint32_t y = run.get(actor + 0x50);
        uint32_t x = run.get(actor + 0x4c);
        uint32_t service = run.get(run.get(run.get(receiver + 0x130) + 0xc) + 0x8);
        uint32_t flare = balanced(run, 0x4c8da0, service, fp, {0, x, y, depth, 0x522e24, 0x40000});
        run.put(receiver + 0x154, flare);
        run.put(receiver + 0x158, 2);
    } else {
        run.put(receiver + 0x154, 0);
        run.put(receiver + 0x158, 1);
    }
    run.put(run.get(receiver + 0x12c) + 0xd0, 0x40);
    return receiver;
}

// 0x4104c0 and 0x410580. Callback argument +0x6c is the logic record:
// +0x1c message and +0x18 published projectile.
uint32_t projectileCallback(Run &run, uint32_t argument, bool trident) {
    uint32_t record = run.get(argument + 0x6c);
    uint32_t message = run.get(record + 0x1c);
    if (message == 0) {
        run.put(record + 0x1c, 0x3e8);
        uint32_t object = run.call(0x4f63ec, 0, {trident ? 0x160u : 0x150u});
        if (object) {
            uint32_t frame = run.frame;
            run.frame = frame - 0x1c;
            object = trident ? tridentConstructor(run, object, argument) : sirenConstructor(run, object, argument);
            run.frame = frame;
        }
        run.vcall(object, 0x10);
        run.put(record + 0x18, object);
    } else if (message == 0x1d) {
        run.vcall(run.get(record + 0x18), 0x20);
    } else if (message == 0x1e) {
        run.vcall(run.get(record + 0x18), 0x1c);
    } else if (message != 0x3e8) {
        run.call(0x4dc870, 0, {run.get(record + 0x18)});
    }
    return 1;
}

uint32_t stateSlot(Run &run, uint32_t state) {
    uint32_t low = run.get(0x534bd0);
    if (s32(state) < s32(low) || s32(state) > s32(run.get(0x534bd4))) {
        uint32_t grown = run.call(0x4db6e0, 0x534bc8, {state, 0});
        if (!grown) {
            uint32_t error = run.get(0x544b4c);
            run.put(0x544b14, run.call(0x4db5f0, 0));
            run.call(0x4db4d0, run.get(0x534bcc), {0x534bc8, error, 0xc});
            return run.get(0x534bdc);
        }
        low = run.get(0x534bd0);
    }
    return (state - low) * run.get(0x534be0) + run.get(0x534bd8);
}

// 0x4129d0. Two distinct table reads, with a fallback to the base state handler.
uint32_t dispatchState(Run &run, uint32_t receiver, uint32_t state) {
    run.put(0x534be8, 0);
    uint32_t slot = stateSlot(run, state);
    if (run.get(slot)) {
        run.put(0x534be8, 0);
        slot = stateSlot(run, state);
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x473f40, receiver, {state});
    }
    return 0;
}

uint32_t tridentStateSlot(Run &run, uint32_t state) {
    uint32_t low = run.get(0x534a90);
    if (s32(state) < s32(low) || s32(state) > s32(run.get(0x534a94))) {
        uint32_t grown = run.call(0x4db6e0, 0x534a88, {state, 0});
        if (!grown) {
            uint32_t error = run.get(0x544b4c);
            run.put(0x544b14, run.call(0x4db5f0, 0));
            run.call(0x4db4d0, run.get(0x534a8c), {0x534a88, error, 0xc});
            return run.get(0x534a9c);
        }
        low = run.get(0x534a90);
    }
    return (state - low) * run.get(0x534aa0) + run.get(0x534a98);
}

// 0x412e80. Trident's signed state table is separate from the siren table.
uint32_t dispatchTridentState(Run &run, uint32_t receiver, uint32_t state) {
    run.put(0x534aa8, 0);
    uint32_t slot = tridentStateSlot(run, state);
    if (run.get(slot)) {
        run.put(0x534aa8, 0);
        slot = tridentStateSlot(run, state);
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x473f40, receiver, {state});
    }
    return 0;
}

// 0x4133e0. +0x24 saves the prior logic state and +0x134 the prior sequence;
// +0xc8 marks activation after publishing the explosion image and sequence.
uint32_t beginTridentExplosion(Run &run, uint32_t receiver) {
    uint32_t logic = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(logic + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x524418});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 0x4);
    run.put(run.get(receiver + 0x12c) + 0xd0, 0x1000000);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x524438});
    actor = run.get(receiver + 0x12c);
    uint32_t sequence = run.get(receiver + 0x150);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {sequence});
    run.put(receiver + 0xc8, 1);
    return 0;
}

// 0x412cb0. The base falling update can change the actor pointer.
uint32_t sirenFalling(Run &run, uint32_t receiver) {
    auto fp = floatingState();
    balanced(run, 0x4742f0, receiver, fp);
    uint32_t actor = run.get(receiver + 0x12c);
    if (run.get(actor + 0x1a4) && !run.get(actor + 0x19c)) {
        run.put(actor + 0x8, run.get(actor + 0x8) | 0x10000);
    }
    return 0;
}

uint32_t randomOffset(Run &run, uint32_t low, uint32_t high) {
    uint32_t span = high - low + 1;
    uint32_t value = run.call(0x4a3050, 0);
    if (!span) {
        return (value & 1) ? low : high;
    }
    int64_t remainder = int64_t(s32(value)) % int64_t(s32(span));
    return uint32_t(remainder) + low;
}

uint32_t convert(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

// 0x413280. +0x68/+0x70 are binary64 positions; descriptor +0x118..0x124
// gives signed inclusive glitter ranges. Each created object's +0x6c callback
// receives that object as one cdecl argument.
uint32_t tridentFalling(Run &run, uint32_t receiver) {
    auto fp = floatingState();
    balanced(run, 0x4742f0, receiver, fp);
    uint32_t count = 0;
    if (s32(run.get(receiver + 0x158)) > 0) {
        do {
            uint32_t xLow = run.get(receiver + 0x68);
            uint32_t xHigh = run.get(receiver + 0x6c);
            uint32_t descriptor = run.get(receiver + 0xc);
            uint32_t high = run.get(descriptor + 0x120);
            uint32_t low = run.get(descriptor + 0x118);
            uint32_t offset = randomOffset(run, low, high);
            run.x87_step(CLAW_X87_I32, fp, {offset});
            run.x87_step(CLAW_X87_ADD_F64, fp, {xLow, xHigh});
            uint32_t x = convert(run, fp);
            uint32_t yLow = run.get(receiver + 0x70);
            descriptor = run.get(receiver + 0xc);
            uint32_t yHigh = run.get(receiver + 0x74);
            high = run.get(descriptor + 0x124);
            low = run.get(descriptor + 0x11c);
            offset = randomOffset(run, low, high);
            descriptor = run.get(receiver + 0xc);
            run.x87_step(CLAW_X87_I32, fp, {offset});
            uint32_t depth = run.get(descriptor + 0x64) - 1;
            run.x87_step(CLAW_X87_ADD_F64, fp, {yLow, yHigh});
            uint32_t y = convert(run, fp);
            uint32_t service = run.get(run.get(run.get(receiver + 0x130) + 0xc) + 0x8);
            uint32_t object = balanced(run, 0x4c8da0, service, fp, {0, x, y, depth, 0x522594, 0x40000});
            uint32_t callback = run.get(run.get(object + 0x6c) + 0x10);
            run.call(callback, 0, {object});
            ++count;
        } while (s32(count) < s32(run.get(receiver + 0x158)));
    }
    uint32_t flare = run.get(receiver + 0x154);
    if (flare) {
        run.x87_step(CLAW_X87_F64, fp, {run.get(receiver + 0x68), run.get(receiver + 0x6c)});
        uint32_t x = convert(run, fp);
        run.put(flare + 0x4c, x);
        run.x87_step(CLAW_X87_F64, fp, {run.get(receiver + 0x70), run.get(receiver + 0x74)});
        uint32_t y = convert(run, fp);
        run.put(run.get(receiver + 0x154) + 0x50, y);
    }
    return 0;
}

// 0x413470. +0x15c latches the first explosion tick; actor +0x8 holds flags.
uint32_t tridentExploding(Run &run, uint32_t receiver) {
    uint32_t tick = run.get(0x5430c4);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t result = run.call(0x4c82a0, actor + 0x188, {tick});
    if (result == 1 && !run.get(receiver + 0x15c)) {
        run.put(receiver + 0x15c, 1);
        actor = run.get(receiver + 0x12c);
        run.put(actor + 0x8, run.get(actor + 0x8) & 0xffffff7f);
    }
    actor = run.get(receiver + 0x12c);
    if (run.get(actor + 0x1a4) && !run.get(actor + 0x19c)) {
        run.put(actor + 0x8, run.get(actor + 0x8) | 0x10000);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4104c0:
        return projectileCallback(run, arguments[0], false);
    case 0x410580:
        return projectileCallback(run, arguments[0], true);
    case 0x412880:
        return sirenConstructor(run, receiver, arguments[0]);
    case 0x4129d0:
        return dispatchState(run, receiver, arguments[0]);
    case 0x412cb0:
        return sirenFalling(run, receiver);
    case 0x412ce0:
        return tridentConstructor(run, receiver, arguments[0]);
    case 0x412e80:
        return dispatchTridentState(run, receiver, arguments[0]);
    case 0x413280:
        return tridentFalling(run, receiver);
    case 0x4133e0:
        return beginTridentExplosion(run, receiver);
    case 0x413470:
        return tridentExploding(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_eleven_siren_trident_projectiles_01_entry, owned, body)
