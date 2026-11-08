// Level 2 cannon objects, recovered from the hash-checked v1.0 instructions.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4145b0:
    case 0x4145f0:
    case 0x414640:
    case 0x414660:
    case 0x4146b0:
    case 0x414860:
    case 0x4148b0:
    case 0x414a60:
        return 0;
    case 0x4493c0:
    case 0x449480:
    case 0x449590:
        return 1;
    default:
        return -1;
    }
}

// 0x4145b0 / 0x414660 / 0x414860. +0x10 state, +0x24 previous state,
// +0x2c sprite, +0x34 previous animation, +0x48/4c/50 animation handles.
uint32_t setup(Run &run, uint32_t receiver, uint32_t name, uint32_t animation, bool firing) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(receiver + 0x2c);
    uint32_t selected = run.get(receiver + animation);
    uint32_t previous = run.get(sprite + 0x190);
    run.put(receiver + 0x34, previous);
    run.call(0x4c8220, sprite + 0x188, {selected});
    if (firing)
        run.put(receiver + 0x58, 0);
    return 0;
}

// 0x414640. +0x70 selects the vertical firing animation.
uint32_t selectFiring(Run &run, uint32_t receiver) {
    if (run.get(receiver + 0x70) != 0)
        return setup(run, receiver, 0x524538, 0x50, true);
    return setup(run, receiver, 0x524548, 0x4c, true);
}

// 0x4145f0. +0x74 last tick, +0x78 timeout, unsigned tick arithmetic.
uint32_t homeTick(Run &run, uint32_t receiver) {
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    if (run.get(0x537210) - run.get(receiver + 0x74) >= run.get(receiver + 0x78)) {
        run.put(receiver + 0x78, 3000);
        run.put(receiver + 0x74, run.get(0x537210));
        selectFiring(run, receiver);
    }
    return 0;
}

// Optional sprite collision rectangles: +0x118/120, +0x128/130, +0x138/140.
void flipRectangles(Run &run, uint32_t sprite) {
    uint32_t left = run.get(sprite + 0x118);
    if (left != 0x80000000u) {
        uint32_t right = run.get(sprite + 0x120);
        run.put(sprite + 0x118, 0u - right);
        run.put(sprite + 0x120, 0u - left);
    }
    left = run.get(sprite + 0x128);
    if (left != 0x80000000u) {
        uint32_t right = run.get(sprite + 0x130);
        run.put(sprite + 0x128, 0u - right);
        run.put(sprite + 0x130, 0u - left);
    }
    left = run.get(sprite + 0x138);
    if (left != 0x80000000u) {
        uint32_t right = run.get(sprite + 0x140);
        run.put(sprite + 0x138, 0u - right);
        run.put(sprite + 0x140, 0u - left);
    }
}

// 0x4146b0 / 0x4148b0. +0x58 one-shot latch; +0x5c/60 horizontal
// muzzle offsets, +0x64/68 vertical offsets, +0x30 creation manager.
uint32_t firingTick(Run &run, uint32_t receiver, bool vertical) {
    uint32_t advanced = run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    if (advanced == 1 && run.get(receiver + 0x58) == 0) {
        uint32_t yOffset = run.get(receiver + (vertical ? 0x68 : 0x60));
        run.put(receiver + 0x58, 1);
        uint32_t sprite = run.get(receiver + 0x2c);
        uint32_t layer = run.get(sprite + 0x64) - 1;
        uint32_t y = yOffset + run.get(sprite + 0x50);
        uint32_t x = run.get(receiver + (vertical ? 0x64 : 0x5c)) + run.get(sprite + 0x4c);
        uint32_t manager = run.get(run.get(run.get(receiver + 0x30) + 0x0c) + 0x08);
        uint32_t ball = run.call(0x4c8da0, manager, {0, x, y, layer, 0x522dbc, 0x40000});
        uint32_t control = run.get(ball + 0x6c);
        run.call(run.get(control + 0x10), 0, {ball});
        uint32_t object = run.get(receiver + 0x0c);
        control = run.get(ball + 0x6c);
        double vx = double(s32(run.get(object + 0x148)));
        run.putd(run.get(control + 0x18) + 0x50, vx);
        object = run.get(receiver + 0x0c);
        control = run.get(ball + 0x6c);
        double vy = double(s32(run.get(object + 0x14c)));
        run.putd(run.get(control + 0x18) + 0x58, vy);
        uint32_t runtime = run.get(run.get(ball + 0x6c) + 0x18);
        run.put(runtime + 0x40, 0);
        run.put(runtime + 0x44, 0);
        uint32_t sound = run.get(receiver + 0x54);
        if (sound != 0 && run.get(0x532c0c) != 0)
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
        if (s32(run.get(run.get(receiver + 0x0c) + 0x148)) < 0) {
            runtime = run.get(run.get(ball + 0x6c) + 0x18);
            uint32_t target = run.get(runtime + 0x12c);
            uint32_t flip = runtime + 0x128;
            if ((run.get8(target + 0x40) & 2) == 0) {
                uint32_t left = run.get(flip + 0x10);
                uint32_t right = run.get(flip + 0x18);
                run.put(flip + 0x10, 0u - right);
                run.put(flip + 0x18, 0u - left);
                run.put(target + 0x40, run.get(target + 0x40) | 2);
                flipRectangles(run, run.get(flip + 0x04));
            }
        }
    }
    uint32_t animator = run.get(receiver + 0x2c) + 0x188;
    if (run.get(animator + 0x1c) != 0 && run.get(animator + 0x14) == 0)
        setup(run, receiver, 0x5234ec, 0x48, false);
    return 0;
}

// 0x414a60. +0x38/40 local extents, sprite +0x40 mirrored flag;
// object +0x148 horizontal velocity, +0x5c/64 horizontal muzzle offsets.
uint32_t mirror(Run &run, uint32_t receiver) {
    uint32_t sprite = run.get(receiver + 0x2c);
    if ((run.get8(sprite + 0x40) & 2) == 0) {
        uint32_t left = run.get(receiver + 0x38);
        uint32_t right = run.get(receiver + 0x40);
        run.put(receiver + 0x38, 0u - right);
        run.put(receiver + 0x40, 0u - left);
        run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
        flipRectangles(run, run.get(receiver + 0x2c));
    }
    uint32_t object = run.get(receiver + 0x0c);
    uint32_t velocity = run.get(object + 0x148);
    if (s32(velocity) > 0) {
        run.put(object + 0x148, 0u - velocity);
        uint32_t horizontal = run.get(receiver + 0x5c);
        uint32_t vertical = run.get(receiver + 0x64);
        run.put(receiver + 0x5c, 0u - horizontal);
        run.put(receiver + 0x64, 0u - vertical);
    }
    return 0;
}

// 0x449480. Original constructor reuses its argument slot as lookup output.
uint32_t construct(Run &run, uint32_t receiver, uint32_t sprite) {
    run.call(0x414030, receiver, {sprite});
    run.put(receiver, 0x50dfd4);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x527b14});
    uint32_t output = run.automatic(0x04);
    run.put(output, 0);
    uint32_t table = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x2c) + 0x10;
    run.call(0x4f6286, table, {0x527b00, output});
    run.put(receiver + 0x4c, run.get(output));
    run.put(output, 0);
    table = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x2c) + 0x10;
    run.call(0x4f6286, table, {0x527aec, output});
    run.put(receiver + 0x48, run.get(output));
    return receiver;
}

// 0x4493c0. Sprite +0x6c control, control +0x1c selector/+0x18 child.
uint32_t dispatchObject(Run &run, uint32_t sprite) {
    uint32_t state = run.get(sprite + 0x6c);
    uint32_t selector = run.get(state + 0x1c);
    if (selector <= 0x1d) {
        if (selector == 0x1d)
            run.vcall(run.get(state + 0x18), 0x20);
        else if (selector == 0) {
            run.put(state + 0x1c, 1000);
            uint32_t child = run.call(0x4f63ec, 0, {0x7c});
            if (child != 0)
                child = construct(run, child, sprite);
            run.vcall(child, 0x10);
            run.put(state + 0x18, child);
        } else
            run.call(0x4dc870, 0, {run.get(state + 0x18)});
    } else if (selector == 0x1e)
        run.vcall(run.get(state + 0x18), 0x1c);
    else if (selector != 1000)
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    return 1;
}

// 0x449590. Global dynamic dispatch table, signed selector bounds.
uint32_t dispatchRow(Run &run, uint32_t selector) {
    uint32_t low = run.get(0x537820);
    run.put(0x537838, 0);
    if (s32(selector) < s32(low) || s32(selector) > s32(run.get(0x537824))) {
        uint32_t grown = run.call(0x4db6e0, 0x537818, {selector, 0});
        if (grown == 0) {
            uint32_t text = run.get(0x544b4c);
            uint32_t site = run.call(0x4db5f0, 0);
            run.put(0x544b14, site);
            run.call(0x4db4d0, run.get(0x53781c), {0x537818, text, 0x0c});
            return run.get(0x53782c);
        }
        low = run.get(0x537820);
    }
    return (selector - low) * run.get(0x537830) + run.get(0x537828);
}

uint32_t dispatchState(Run &run, uint32_t receiver, uint32_t selector) {
    uint32_t row = dispatchRow(run, selector);
    if (run.get(row) != 0) {
        row = dispatchRow(run, selector);
        run.call(run.get(row), receiver);
    } else
        run.call(0x4141f0, receiver, {selector});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4145b0:
        return setup(run, receiver, 0x5234ec, 0x48, false);
    case 0x4145f0:
        return homeTick(run, receiver);
    case 0x414640:
        return selectFiring(run, receiver);
    case 0x414660:
        return setup(run, receiver, 0x524548, 0x4c, true);
    case 0x4146b0:
        return firingTick(run, receiver, false);
    case 0x414860:
        return setup(run, receiver, 0x524538, 0x50, true);
    case 0x4148b0:
        return firingTick(run, receiver, true);
    case 0x414a60:
        return mirror(run, receiver);
    case 0x4493c0:
        return dispatchObject(run, arguments[0]);
    case 0x449480:
        return construct(run, receiver, arguments[0]);
    case 0x449590:
        return dispatchState(run, receiver, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_level_two_cannon_objects_01_entry, owned, body)
