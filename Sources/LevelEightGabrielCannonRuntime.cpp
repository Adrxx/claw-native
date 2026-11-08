// Level 8 Gabriel cannon controller, recovered from the v1.0 packet.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x446550:
    case 0x446670:
    case 0x446a70:
        return 1;
    case 0x446c20:
    case 0x446ca0:
    case 0x446d70:
    case 0x446e10:
    case 0x446eb0:
        return 0;
    default:
        return -1;
    }
}

// 0x446c20. +0x8c pending, +0x90 raised; +0x2c sprite object.
uint32_t reset(Run &run, uint32_t receiver) {
    run.put(receiver + 0x8c, 0);
    run.put(receiver + 0x90, 0);
    uint32_t boss = run.get(0x53774c);
    if (boss) {
        run.put(boss + 0x518, 0);
        boss = run.get(0x53774c);
        run.put(boss + 0x51c, 0);
        boss = run.get(0x53774c);
        run.put(boss + 0x534, run.get(boss + 0x534) & 0xfffffffe);
    }
    uint32_t object = run.get(receiver + 0x2c);
    uint32_t sprite = run.get(object + 0x170);
    if (sprite) {
        uint32_t frame = 0;
        if (run.gets(sprite + 0x64) <= 1 && run.gets(sprite + 0x68) >= 1) {
            frame = run.get(run.get(sprite + 0x14) + 0x04);
        }
        run.put(object + 0x174, frame);
        run.put(object + 0x16c, 1);
    }
    run.call(0x4145b0, receiver);
    return 0;
}

// Original constructor resource lookup sequence. Output aliases its argument word.
uint32_t lookupResource(Run &run, uint32_t receiver, uint32_t name, uint32_t dictionaryOffset, uint32_t output, bool clearOutput) {
    uint32_t object = run.get(receiver + 0x2c);
    uint32_t manager = run.get(object + 0x0c);
    if (clearOutput) {
        run.put(output, 0);
    }
    uint32_t dictionary = run.get(manager + dictionaryOffset);
    run.call(0x4f6286, dictionary + 0x10, {name, output});
    return run.get(output);
}

// 0x446a70. +0x4c/+0x50 fire animations, +0x7c/+0x80 rise/rest,
// +0x84/+0x88 rise/drop sounds, +0x54 firing sound.
uint32_t construct(Run &run, uint32_t receiver, uint32_t object) {
    run.call(0x414030, receiver, {object});
    run.put(receiver + 0x00, 0x50df44);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x5279a4});
    uint32_t output = run.automatic(0x04);
    uint32_t resource = lookupResource(run, receiver, 0x527984, 0x2c, output, true);
    run.put(receiver + 0x4c, resource);
    resource = lookupResource(run, receiver, 0x527964, 0x2c, output, true);
    run.put(receiver + 0x50, resource);
    resource = lookupResource(run, receiver, 0x527948, 0x2c, output, true);
    run.put(receiver + 0x7c, resource);
    resource = lookupResource(run, receiver, 0x52792c, 0x2c, output, true);
    run.put(receiver + 0x80, resource);
    resource = lookupResource(run, receiver, 0x52790c, 0x28, output, true);
    run.put(receiver + 0x84, resource);
    resource = lookupResource(run, receiver, 0x5278ec, 0x28, output, true);
    run.put(output, 0);
    run.put(receiver + 0x88, resource);
    resource = lookupResource(run, receiver, 0x5278d0, 0x28, output, false);
    run.put(receiver + 0x5c, 0x32);
    run.put(receiver + 0x54, resource);
    run.put(receiver + 0x60, 0x36);
    run.put(receiver + 0x64, 0xffffffe6);
    run.put(receiver + 0x68, 0xfffffff6);
    if (run.get8(run.get(receiver + 0x2c) + 0x40) & 2) {
        run.put(receiver + 0x5c, 0xffffffce);
        run.put(receiver + 0x64, 0x1a);
    }
    reset(run, receiver);
    return receiver;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

uint32_t callMethod(Run &run, uint32_t target, uint32_t receiver, uint32_t frameSize) {
    if (owned(target) == 0) {
        uint32_t previousFrame = run.frame;
        run.frame -= frameSize;
        uint32_t result = body(run, target, receiver, nullptr);
        run.frame = previousFrame;
        return result;
    }
    return run.call(target, receiver);
}

void logicVirtualCall(Run &run, uint32_t controller, uint32_t offset) {
    uint32_t target = run.get(run.get(controller) + offset);
    callMethod(run, target, controller, 0x18);
}

// 0x446550. +0x6c logic state; state +0x18 controller, +0x1c id.
uint32_t logic(Run &run, uint32_t object) {
    uint32_t state = run.get(object + 0x6c);
    uint32_t id = run.get(state + 0x1c);
    if (id == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t controller = run.call(0x4f63ec, 0, {0x98});
        if (controller) {
            uint32_t previousFrame = run.frame;
            run.frame -= 0x1c;
            controller = construct(run, controller, object);
            run.frame = previousFrame;
        }
        logicVirtualCall(run, controller, 0x10);
        run.put(state + 0x18, controller);
    } else if (id == 29) {
        logicVirtualCall(run, run.get(state + 0x18), 0x20);
    } else if (id == 30) {
        logicVirtualCall(run, run.get(state + 0x18), 0x1c);
    } else if (id != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}

// 0x446670. Registry +0x08/+0x0c signed bounds, +0x10 table,
// +0x14 fallback, +0x18 stride, +0x20 insertion count.
uint32_t dispatchSlot(Run &run, uint32_t id, uint32_t low, uint32_t returnPC) {
    if (s32(id) < s32(low) || s32(id) > run.gets(0x537794)) {
        uint32_t grown = run.call(0x4db6e0, 0x537788, {id, 0});
        if (!grown) {
            uint32_t text = run.get(0x544b4c);
            run.call(0x4db5f0, 0);
            uint32_t handler = run.get(0x53778c);
            // The original POP/PUSH/RET helper returns this CALL's return PC.
            run.put(0x544b14, returnPC);
            run.call(0x4db4d0, handler, {0x537788, text, 0x0c});
            return run.get(0x53779c);
        }
        low = run.get(0x537790);
    }
    uint32_t table = run.get(0x537798);
    uint32_t stride = run.get(0x5377a0);
    return table + (id - low) * stride;
}

uint32_t dispatch(Run &run, uint32_t receiver, uint32_t id) {
    uint32_t low = run.get(0x537790);
    run.put(0x5377a8, 0);
    uint32_t slot = dispatchSlot(run, id, low, 0x4466d0);
    low = run.get(0x537790);
    if (!run.get(slot)) {
        return run.call(0x4141f0, receiver, {id});
    }
    run.put(0x5377a8, 0);
    slot = dispatchSlot(run, id, low, 0x44674a);
    return callMethod(run, run.get(slot), receiver, 0x10);
}

// 0x446d70. +0x24 prior state, +0x34 prior animation,
// +0x0c moving object, +0x94 progress, +0x70 orientation.
uint32_t rise(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52788c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t object = run.get(receiver + 0x2c);
    uint32_t animation = run.get(receiver + 0x7c);
    run.put(receiver + 0x34, run.get(object + 0x190));
    run.call(0x4c8220, object + 0x188, {animation});
    run.put(run.get(receiver + 0x0c) + 0x148, 0);
    run.put(run.get(receiver + 0x0c) + 0x14c, 0xfffffe0c);
    run.put(receiver + 0x94, 0);
    run.put(receiver + 0x90, 1);
    run.put(receiver + 0x70, 1);
    uint32_t sound = run.get(receiver + 0x84);
    if (sound) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t volume = run.get(0x532c10);
        if (enabled) {
            run.call(0x4b45f0, run.get(sound + 0x10), {volume, 0, 0, 0});
        }
    }
    return 0;
}

// 0x446e10.
uint32_t drop(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52788c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t object = run.get(receiver + 0x2c);
    uint32_t animation = run.get(receiver + 0x80);
    run.put(receiver + 0x34, run.get(object + 0x190));
    run.call(0x4c8220, object + 0x188, {animation});
    run.put(run.get(receiver + 0x0c) + 0x148, 0xfffffe0c);
    run.put(run.get(receiver + 0x0c) + 0x14c, 0);
    run.put(receiver + 0x94, 0);
    uint32_t boss = run.get(0x53774c);
    if (boss) {
        run.put(boss + 0x51c, 0);
    }
    run.put(receiver + 0x90, 0);
    run.put(receiver + 0x70, 0);
    uint32_t sound = run.get(receiver + 0x88);
    if (sound) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t volume = run.get(0x532c10);
        if (enabled) {
            run.call(0x4b45f0, run.get(sound + 0x10), {volume, 0, 0, 0});
        }
    }
    return 0;
}

// 0x446ca0. Boss +0x520 busy, +0x534 reset, +0x51c rise, +0x518 fire.
uint32_t update(Run &run, uint32_t receiver) {
    uint32_t boss = run.get(0x53774c);
    if (!boss || run.get(boss + 0x520)) {
        return 0;
    }
    if (run.get8(boss + 0x534) & 1) {
        return reset(run, receiver);
    }
    uint32_t ticks = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {ticks});
    if (run.get(receiver + 0x8c) && run.get(receiver + 0x90)) {
        run.put(receiver + 0x8c, 0);
        return drop(run, receiver);
    }
    boss = run.get(0x53774c);
    if (run.get(boss + 0x51c) && !run.get(receiver + 0x90)) {
        run.put(receiver + 0x8c, 0);
        return rise(run, receiver);
    }
    if (run.get(boss + 0x518)) {
        run.call(0x414640, receiver);
        boss = run.get(0x53774c);
        run.put(boss + 0x518, 0);
        run.put(receiver + 0x8c, 1);
    }
    return 0;
}

// 0x446eb0. Animation +0x1c completed, +0x14 remaining delay.
uint32_t rotateUpdate(Run &run, uint32_t receiver) {
    uint32_t ticks = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {ticks});
    uint32_t animation = run.get(receiver + 0x2c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14)) {
        run.call(0x4145b0, receiver);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x446550:
        return logic(run, arguments[0]);
    case 0x446670:
        return dispatch(run, receiver, arguments[0]);
    case 0x446a70:
        return construct(run, receiver, arguments[0]);
    case 0x446c20:
        return reset(run, receiver);
    case 0x446ca0:
        return update(run, receiver);
    case 0x446d70:
        return rise(run, receiver);
    case 0x446e10:
        return drop(run, receiver);
    case 0x446eb0:
        return rotateUpdate(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_eight_gabriel_cannon_entry, owned, body)
