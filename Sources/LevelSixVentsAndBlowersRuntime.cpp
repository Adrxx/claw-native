#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4486e0: return 1;
    case 0x448850: return 1;
    case 0x448b00: return 0;
    case 0x448b50: return 0;
    case 0x448e30: return 1;
    case 0x4490e0: return 1;
    case 0x449270: return 0;
    case 0x4492c0: return 0;
    default: return -1;
    }
}

// Common base initialization in 0x4486e0 and 0x4490e0. +0x08/+0x0c
// retain the actor; +0x10 is its logic data; +0x28/+0x2c repeat the actor.
void initializeBase(Run &run, uint32_t receiver, uint32_t actor) {
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x08, actor);
    run.put(receiver + 0x0c, actor);
    uint32_t logic = run.get(actor + 0x6c);
    run.put(receiver + 0x10, logic);
    run.put(receiver + 0x04, 0);
    run.call(0x4c7fa0, actor, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0x0c), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x28, actor);
    run.put(receiver + 0x2c, actor);
    run.put(receiver + 0x30, run.get(actor + 0x6c));
}

// 0x448b00. Save the previous state and animation, select idle, reset the timer.
uint32_t ventIdle(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x2c);
    uint32_t animation = run.get(receiver + 0x48);
    uint32_t previous = run.get(actor + 0x190);
    run.put(receiver + 0x34, previous);
    run.call(0x4c8220, actor + 0x188, {animation});
    run.put(receiver + 0x54, run.get(receiver + 0x4c));
    run.put(receiver + 0x50, run.get(0x537210));
    return 0;
}

// 0x4486e0. Build the vent and load its registered animation resource.
uint32_t constructVent(Run &run, uint32_t receiver, uint32_t actor) {
    initializeBase(run, receiver, actor);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver, 0x50df84);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x527a90});
    uint32_t output = run.automatic(4);
    uint32_t owner = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x2c) + 0x10;
    run.put(output, 0);
    run.call(0x4f6286, owner, {0x527a78, output});
    run.put(receiver + 0x48, run.get(output));
    run.put(run.get(receiver + 0x2c) + 0xd0, 0x1000000);
    run.put(run.get(receiver + 0x2c) + 0xd4, 1);
    run.put(receiver + 0x4c, run.get(run.get(receiver + 0x10) + 0xb8));
    ventIdle(run, receiver);
    return receiver;
}

// 0x448850 and 0x448e30. Read the class state table twice, because table
// growth and the error callback may change its range or backing storage.
void dispatchState(Run &run, uint32_t receiver, uint32_t state, uint32_t table) {
    uint32_t low = run.get(table + 0x08);
    run.put(table + 0x20, 0);
    uint32_t slot;
    if (s32(state) < s32(low) || s32(state) > run.gets(table + 0x0c)) {
        uint32_t grown = run.call(0x4db6e0, table, {state, 0});
        if (!grown) {
            uint32_t context = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            run.call(0x4db4d0, run.get(table + 0x04), {table, context, 0x0c});
            slot = run.get(table + 0x14);
            low = run.get(table + 0x08);
        } else {
            low = run.get(table + 0x08);
            slot = (state - low) * run.get(table + 0x18) + run.get(table + 0x10);
        }
    } else {
        slot = (state - low) * run.get(table + 0x18) + run.get(table + 0x10);
    }
    if (!run.get(slot)) {
        run.call(0x4a36f0, 0, {receiver});
        return;
    }
    run.put(table + 0x20, 0);
    if (s32(state) < s32(low) || s32(state) > run.gets(table + 0x0c)) {
        uint32_t grown = run.call(0x4db6e0, table, {state, 0});
        if (!grown) {
            uint32_t context = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            run.call(0x4db4d0, run.get(table + 0x04), {table, context, 0x0c});
            slot = run.get(table + 0x14);
        } else {
            low = run.get(table + 0x08);
            slot = (state - low) * run.get(table + 0x18) + run.get(table + 0x10);
        }
    } else {
        slot = (state - low) * run.get(table + 0x18) + run.get(table + 0x10);
    }
    run.call(run.get(slot), receiver);
}

// 0x448b50. On timer expiry publish the collision rectangle for this frame.
uint32_t tickVent(Run &run, uint32_t receiver) {
    if (run.get(0x537210) - run.get(receiver + 0x50) < run.get(receiver + 0x54))
        return 0;
    uint32_t actor = run.get(receiver + 0x2c);
    switch (run.get(actor + 0x16c)) {
    case 1:
    case 2:
    case 3:
        run.put(actor + 0x138, 0x80000000);
        run.put(actor + 0x13c, 0);
        run.put(actor + 0x140, 0);
        run.put(actor + 0x144, 0);
        break;
    case 4:
        run.put(actor + 0x138, 0xffffffd8);
        run.put(actor + 0x13c, 0xfffffff4);
        run.put(actor + 0x140, 0x28);
        run.put(actor + 0x144, 7);
        break;
    case 5:
        run.put(actor + 0x138, 0xffffffce);
        run.put(actor + 0x13c, 0xfffffff4);
        run.put(actor + 0x140, 0x32);
        run.put(actor + 0x144, 8);
        break;
    case 6:
        run.put(actor + 0x138, 0xffffffc4);
        run.put(actor + 0x13c, 0xfffffff4);
        run.put(actor + 0x140, 0x3c);
        run.put(actor + 0x144, 0x0a);
        break;
    case 7:
        run.put(actor + 0x138, 0xffffffbf);
        run.put(actor + 0x13c, 0xfffffff4);
        run.put(actor + 0x140, 0x41);
        run.put(actor + 0x144, 0x0b);
        break;
    case 8:
        run.put(actor + 0x138, 0xffffffba);
        run.put(actor + 0x13c, 0xfffffff4);
        run.put(actor + 0x140, 0x46);
        run.put(actor + 0x144, 0x0c);
        break;
    case 9:
        run.put(actor + 0x138, 0xffffffb5);
        run.put(actor + 0x13c, 0xfffffff4);
        run.put(actor + 0x140, 0x4b);
        run.put(actor + 0x144, 0x0d);
        break;
    default:
        break;
    }
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    actor = run.get(receiver + 0x2c) + 0x188;
    if (run.get(actor + 0x1c) && !run.get(actor + 0x14))
        ventIdle(run, receiver);
    return 0;
}

// 0x449270. Save the previous state and animation, select idle, then animate.
uint32_t blowerIdle(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523604});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x2c);
    uint32_t animation = run.get(receiver + 0x4c);
    uint32_t previous = run.get(actor + 0x190);
    run.put(receiver + 0x34, previous);
    uint32_t sequence = actor + 0x188;
    run.call(0x4c8220, sequence, {animation});
    run.call(0x4c82a0, sequence, {run.get(0x5430c4)});
    return 0;
}

// 0x4490e0. Build the blower and supply its default collision rectangle.
uint32_t constructBlower(Run &run, uint32_t receiver, uint32_t actor) {
    initializeBase(run, receiver, actor);
    run.put(receiver, 0x50dfac);
    uint32_t output = run.automatic(4);
    uint32_t owner = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x2c) + 0x10;
    run.put(output, 0);
    run.call(0x4f6286, owner, {0x527abc, output});
    run.put(receiver + 0x4c, run.get(output));
    uint32_t rectangle = run.automatic(-0x1c);
    run.icall(0x546d58, {rectangle, run.get(receiver + 0x0c) + 0x118});
    bool empty = !run.get(rectangle) && !run.get(rectangle + 0x08) && !run.get(rectangle + 0x04) && !run.get(rectangle + 0x0c);
    if (empty || run.icall(0x546d4c, {rectangle})) {
        run.call(0x406290, run.get(receiver + 0x2c));
        uint32_t object = run.get(receiver + 0x0c);
        run.put(object + 0x11c, run.get(object + 0x11c) - 0x0a);
        object = run.get(receiver + 0x0c);
        run.put(object + 0x124, run.get(object + 0x124) + 0x0a);
        object = run.get(receiver + 0x0c);
        run.put(object + 0x118, run.get(object + 0x118) - 5);
        object = run.get(receiver + 0x0c);
        run.put(object + 0x120, run.get(object + 0x120) + 0x19);
    }
    run.put(run.get(receiver + 0x2c) + 0xd0, 1);
    run.put(run.get(receiver + 0x2c) + 0xd4, 0x3000072);
    uint32_t object = run.get(receiver + 0x0c);
    if (!run.get(object + 0x64)) {
        uint32_t flags = run.get(object + 0x08);
        run.put(object + 0x64, 1);
        run.put(object + 0x08, flags | 0x20000);
    }
    blowerIdle(run, receiver);
    return receiver;
}

// 0x4492c0. Advance animation; intersect actor and player bounds at frame one.
uint32_t tickBlower(Run &run, uint32_t receiver) {
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    if (run.get(run.get(receiver + 0x2c) + 0x16c) != 1)
        return 0;
    uint32_t player = run.get(0x537e88);
    uint32_t vertical = run.get(player + 0x50);
    uint32_t horizontal = run.get(player + 0x4c);
    uint32_t bottom = run.get(player + 0x124) + vertical;
    uint32_t right = run.get(player + 0x120) + horizontal;
    uint32_t top = run.get(player + 0x11c) + vertical;
    uint32_t left = run.get(player + 0x118) + horizontal;
    uint32_t first = run.automatic(-0x20);
    uint32_t second = run.automatic(-0x10);
    run.put(first, left);
    uint32_t actor = run.get(receiver + 0x0c);
    run.put(first + 0x04, top);
    run.put(first + 0x08, right);
    run.put(first + 0x0c, bottom);
    vertical = run.get(actor + 0x50);
    bottom = run.get(actor + 0x124) + vertical;
    horizontal = run.get(actor + 0x4c);
    right = run.get(actor + 0x120) + horizontal;
    top = run.get(actor + 0x11c) + vertical;
    left = run.get(actor + 0x118) + horizontal;
    run.put(second + 0x0c, bottom);
    run.put(second + 0x08, right);
    run.put(second, left);
    run.put(second + 0x04, top);
    if (run.icall(0x546ce0, {first, first, second})) {
        uint32_t force = run.get(run.get(receiver + 0x10) + 0x38);
        if (s32(force) > 0) {
            run.call(0x41e810, 0, {run.get(0x537e88), force});
            return 0;
        }
        run.call(0x41e810, 0, {run.get(0x537e88), 0x1c2});
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4486e0: return constructVent(run, receiver, arguments[0]);
    case 0x448850:
        dispatchState(run, receiver, arguments[0], 0x5377b8);
        return 0;
    case 0x448b00: return ventIdle(run, receiver);
    case 0x448b50: return tickVent(run, receiver);
    case 0x448e30:
        dispatchState(run, receiver, arguments[0], 0x5377e8);
        return 0;
    case 0x4490e0: return constructBlower(run, receiver, arguments[0]);
    case 0x449270: return blowerIdle(run, receiver);
    case 0x4492c0: return tickBlower(run, receiver);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_six_vents_and_blowers_entry, owned, body)
