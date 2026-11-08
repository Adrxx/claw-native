// Level 8 cannon controls closure.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x414de0:
    case 0x415090:
    case 0x415470:
    case 0x415840:
        return 1;
    case 0x415210:
    case 0x415250:
    case 0x4152e0:
    case 0x4159b0:
    case 0x4159f0:
    case 0x415a60:
        return 0;
    default:
        return -1;
    }
}

// 0x414de0 and 0x415470. State tables contain signed bounds, element width,
// storage, a fallback slot and a scratch field at +0x20.
uint32_t dispatchSlot(Run &run, uint32_t table, uint32_t index) {
    uint32_t lower = run.get(table + 0x08);
    if (s32(index) < s32(lower) || s32(index) > run.gets(table + 0x0c)) {
        uint32_t grown = run.call(0x4db6e0, table, {index, 0});
        if (!grown) {
            uint32_t text = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            run.call(0x4db4d0, run.get(table + 0x04), {table, text, 0x0c});
            return run.get(table + 0x14);
        }
        lower = run.get(table + 0x08);
    }
    return (index - lower) * run.get(table + 0x18) + run.get(table + 0x10);
}

uint32_t dispatch(Run &run, uint32_t receiver, uint32_t index, uint32_t table) {
    run.put(table + 0x20, 0);
    uint32_t slot = dispatchSlot(run, table, index);
    if (!run.get(slot)) {
        run.call(0x4a36f0, 0, {receiver});
        return 0;
    }
    run.put(table + 0x20, 0);
    slot = dispatchSlot(run, table, index);
    run.call(run.get(slot), receiver);
    return 0;
}

// 0x415210. Save the animation and state, then enter button idle.
uint32_t buttonIdle(Run &run, uint32_t receiver) {
    uint32_t object = run.get(receiver + 0x2c);
    uint32_t definition = run.get(receiver + 0x4c);
    run.put(receiver + 0x34, run.get(object + 0x190));
    run.call(0x4c8220, object + 0x188, {definition});
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    return 0;
}

// 0x415090 and 0x415840. The lookup output occupies the incoming argument slot.
uint32_t construct(Run &run, uint32_t receiver, uint32_t object, bool button) {
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
    run.put(receiver, button ? 0x50ba3c : 0x50ba64);
    run.call(0x4c7970, run.get(receiver + 0x2c), {button ? 0x5245f0u : 0x524664u});
    uint32_t output = run.automatic(4);
    uint32_t manager = run.get(run.get(receiver + 0x2c) + 0x0c);
    uint32_t table = run.get(manager + 0x2c);
    run.put(output, 0);
    run.call(0x4f6286, table + 0x10, {button ? 0x5245d8u : 0x524648u, output});
    run.put(receiver + 0x4c, run.get(output));
    manager = run.get(run.get(receiver + 0x2c) + 0x0c);
    table = run.get(manager + 0x28);
    run.put(output, 0);
    run.call(0x4f6286, table + 0x10, {button ? 0x5245bcu : 0x52462cu, output});
    if (button) {
        run.put(receiver + 0x48, run.get(output));
        run.put(run.get(receiver + 0x2c) + 0xd0, 4);
        run.put(run.get(receiver + 0x2c) + 0xd4, 2);
    } else {
        run.put(receiver + 0x50, run.get(output));
    }
    object = run.get(receiver + 0x2c);
    run.put(object + 0x138, 0x80000000);
    run.put(object + 0x13c, 0);
    run.put(object + 0x140, 0);
    run.put(object + 0x144, 0);
    object = run.get(receiver + 0x2c);
    uint32_t frame = run.get(object + 0x174);
    if (frame) {
        run.put(object + 0x128, run.get(frame + 0x20) - run.get(frame + 0x18));
        run.put(object + 0x12c, run.get(frame + 0x24) - run.get(frame + 0x1c));
        run.put(object + 0x130, run.get(frame + 0x20) + run.get(frame + 0x18) - 1);
        run.put(object + 0x134, run.get(frame + 0x24) + run.get(frame + 0x1c) - 1);
    }
    if (button) {
        buttonIdle(run, receiver);
    } else {
        run.call(0x465450, receiver);
    }
    return receiver;
}

// 0x415250. Boss activation selects sprite frame two; inactive resets the latch.
uint32_t buttonTick(Run &run, uint32_t receiver) {
    uint32_t boss = run.get(0x53774c);
    if (!boss || run.get(boss + 0x520) || !run.get(boss + 0x51c)) {
        run.put(receiver + 0x50, 0);
        uint32_t delta = run.get(0x5430c4);
        run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {delta});
        return 0;
    }
    uint32_t object = run.get(receiver + 0x2c);
    uint32_t sprite = run.get(object + 0x170);
    if (sprite) {
        uint32_t frame = 0;
        if (run.gets(sprite + 0x64) <= 2 && run.gets(sprite + 0x68) >= 2) {
            frame = run.get(run.get(sprite + 0x14) + 0x08);
        }
        run.put(object + 0x16c, 2);
        run.put(object + 0x174, frame);
    }
    return 0;
}

// 0x4152e0. First activation plays sound and latches the button.
uint32_t buttonPress(Run &run, uint32_t receiver) {
    if (run.get(run.get(receiver + 0x2c) + 0x16c) == 2) {
        return 0;
    }
    uint32_t boss = run.get(0x53774c);
    if (!boss || run.get(boss + 0x520)) {
        return 0;
    }
    if (!run.get(receiver + 0x50)) {
        uint32_t sound = run.get(receiver + 0x48);
        if (sound && run.get(0x532c0c)) {
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
        }
        run.put(receiver + 0x50, 1);
        boss = run.get(0x53774c);
    }
    run.put(boss + 0x51c, 1);
    return 0;
}

// 0x4159f0. Enter switch state before replacing its animation and playing sound.
uint32_t switchActivate(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x524604});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t object = run.get(receiver + 0x2c);
    uint32_t definition = run.get(receiver + 0x4c);
    run.put(receiver + 0x34, run.get(object + 0x190));
    run.call(0x4c8220, object + 0x188, {definition});
    uint32_t sound = run.get(receiver + 0x50);
    if (sound && run.get(0x532c0c)) {
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
    return 0;
}

// 0x4159b0. Animate, then consume the boss's switch activation flag.
uint32_t switchIdle(Run &run, uint32_t receiver) {
    uint32_t delta = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {delta});
    uint32_t boss = run.get(0x53774c);
    if (boss && !run.get(boss + 0x520) && run.get(boss + 0x518)) {
        switchActivate(run, receiver);
    }
    return 0;
}

// 0x415a60. Completed animation with no delay returns to idle.
uint32_t switchTick(Run &run, uint32_t receiver) {
    uint32_t delta = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {delta});
    uint32_t player = run.get(receiver + 0x2c) + 0x188;
    if (run.get(player + 0x1c) && !run.get(player + 0x14)) {
        run.call(0x465450, receiver);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x414de0:
        return dispatch(run, receiver, arguments[0], 0x534c28);
    case 0x415090:
        return construct(run, receiver, arguments[0], true);
    case 0x415210:
        return buttonIdle(run, receiver);
    case 0x415250:
        return buttonTick(run, receiver);
    case 0x4152e0:
        return buttonPress(run, receiver);
    case 0x415470:
        return dispatch(run, receiver, arguments[0], 0x534c58);
    case 0x415840:
        return construct(run, receiver, arguments[0], false);
    case 0x4159b0:
        return switchIdle(run, receiver);
    case 0x4159f0:
        return switchActivate(run, receiver);
    case 0x415a60:
        return switchTick(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_level_eight_cannon_controls_entry, owned, body)
