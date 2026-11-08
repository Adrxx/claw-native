// Level 11 laser state, recovered from the original v1.0 entries.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x455490:
    case 0x455600:
        return 1;
    case 0x4558b0:
    case 0x455960:
        return 0;
    default:
        return -1;
    }
}

// 0x4558b0. Reset the idle state and save the previous state/animation.
uint32_t idle(Run &run, uint32_t receiver) {
    // State +0x10 is the owner's data; data +0x1c is its state number.
    uint32_t data = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(data + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    data = run.get(receiver + 0x10);
    run.put(data + 0x1c, state);
    // State +0x2c is the owner; owner +0x188 is the animation runner.
    uint32_t owner = run.get(receiver + 0x2c);
    uint32_t animation = run.get(receiver + 0x48);
    uint32_t previous = run.get(owner + 0x190);
    run.put(receiver + 0x34, previous);
    run.call(0x4c8220, owner + 0x188, {animation});
    owner = run.get(receiver + 0x2c);
    // Owner +0x170 is the sprite resource with signed index limits.
    uint32_t sprites = run.get(owner + 0x170);
    if (sprites != 0) {
        uint32_t selected = 0;
        if (s32(run.get(sprites + 0x64)) <= 1 && s32(run.get(sprites + 0x68)) >= 1) {
            uint32_t table = run.get(sprites + 0x14);
            selected = run.get(table + 0x4);
        }
        run.put(owner + 0x174, selected);
        run.put(owner + 0x16c, 1);
    }
    owner = run.get(receiver + 0x2c);
    // Owner +0x138..+0x144 is the collision rectangle.
    run.put(owner + 0x138, 0x80000000);
    run.put(owner + 0x13c, 0);
    run.put(owner + 0x140, 0);
    run.put(owner + 0x144, 0);
    run.put(receiver + 0x54, run.get(receiver + 0x4c));
    run.put(receiver + 0x50, run.get(0x537210));
    return 0;
}

// 0x455490. Construct the base state, resources and initial idle state.
uint32_t construct(Run &run, uint32_t receiver, uint32_t owner) {
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x8, owner);
    run.put(receiver + 0xc, owner);
    uint32_t data = run.get(owner + 0x6c);
    run.put(receiver + 0x10, data);
    run.put(receiver + 0x4, 0);
    run.call(0x4c7fa0, owner, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0xc), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x28, owner);
    run.put(receiver + 0x2c, owner);
    run.put(receiver + 0x30, run.get(owner + 0x6c));
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver, 0x50e35c);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x528584});
    uint32_t currentOwner = run.get(receiver + 0x2c);
    uint32_t output = run.automatic(4);
    uint32_t context = run.get(currentOwner + 0xc);
    run.put(output, 0);
    context = run.get(context + 0x2c);
    run.call(0x4f6286, context + 0x10, {0x528570, output});
    run.put(receiver + 0x48, run.get(output));
    run.put(run.get(receiver + 0x2c) + 0xd0, 0x1000000);
    run.put(run.get(receiver + 0x2c) + 0xd4, 1);
    data = run.get(receiver + 0x10);
    run.put(receiver + 0x4c, run.get(data + 0xb8));
    idle(run, receiver);
    return receiver;
}

// 0x455600. Look up and invoke a state handler through the original table.
uint32_t dispatch(Run &run, uint32_t receiver, uint32_t index) {
    uint32_t low = run.get(0x5379d8);
    run.put(0x5379f0, 0);
    uint32_t slot = 0;
    if (s32(index) < s32(low) || s32(index) > s32(run.get(0x5379dc))) {
        uint32_t grown = run.call(0x4db6e0, 0x5379d0, {index, 0});
        if (grown == 0) {
            uint32_t message = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0, {});
            uint32_t context = run.get(0x5379d4);
            run.put(0x544b14, error);
            run.call(0x4db4d0, context, {0x5379d0, message, 0xc});
            slot = run.get(0x5379e4);
            low = run.get(0x5379d8);
        } else {
            low = run.get(0x5379d8);
            slot = (index - low) * run.get(0x5379e8) + run.get(0x5379e0);
        }
    } else {
        slot = (index - low) * run.get(0x5379e8) + run.get(0x5379e0);
    }
    if (run.get(slot) == 0) {
        run.call(0x4a36f0, 0, {receiver});
        return 0;
    }
    run.put(0x5379f0, 0);
    if (s32(index) < s32(low) || s32(index) > s32(run.get(0x5379dc))) {
        uint32_t grown = run.call(0x4db6e0, 0x5379d0, {index, 0});
        if (grown == 0) {
            uint32_t message = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0, {});
            uint32_t context = run.get(0x5379d4);
            run.put(0x544b14, error);
            run.call(0x4db4d0, context, {0x5379d0, message, 0xc});
            slot = run.get(0x5379e4);
            run.call(run.get(slot), receiver, {});
            return 0;
        }
        low = run.get(0x5379d8);
    }
    slot = (index - low) * run.get(0x5379e8) + run.get(0x5379e0);
    run.call(run.get(slot), receiver, {});
    return 0;
}

// 0x455960. Activate after the unsigned elapsed-tick threshold, then reset.
uint32_t tick(Run &run, uint32_t receiver) {
    uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x50);
    if (elapsed < run.get(receiver + 0x54)) {
        return 0;
    }
    uint32_t owner = run.get(receiver + 0x2c);
    run.put(owner + 0x138, 0xffffffec);
    run.put(owner + 0x13c, 0xffffff9c);
    run.put(owner + 0x140, 0x14);
    run.put(owner + 0x144, 0x64);
    uint32_t delta = run.get(0x5430c4);
    owner = run.get(receiver + 0x2c);
    run.call(0x4c82a0, owner + 0x188, {delta});
    owner = run.get(receiver + 0x2c);
    uint32_t runner = owner + 0x188;
    if (run.get(runner + 0x1c) != 0 && run.get(runner + 0x14) == 0) {
        idle(run, receiver);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x455490:
        return construct(run, receiver, arguments[0]);
    case 0x455600:
        return dispatch(run, receiver, arguments[0]);
    case 0x4558b0:
        return idle(run, receiver);
    case 0x455960:
        return tick(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_eleven_laser_state_01_entry, owned, body)
