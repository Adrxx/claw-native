// Break and single plank logic, translated from the original v1.0 bodies.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x40f870:
    case 0x40fb30:
    case 0x488e30:
    case 0x488ef0:
    case 0x4890f0:
        return 1;
    case 0x40fde0:
    case 0x40fe20:
    case 0x4894b0:
    case 0x489530:
    case 0x4895b0:
    case 0x489600:
    case 0x489640:
    case 0x489680:
        return 0;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

uint32_t invoke(Run &run, uint32_t function, uint32_t receiver) {
    if (owned(function) == 0)
        return body(run, function, receiver, nullptr);
    return run.call(function, receiver);
}

uint32_t sar(uint32_t value, uint32_t count) {
    return uint32_t(s32(value) >> (count & 0x1f));
}

// D+0xc world, world+0x24 level, level+0x5c grid.
uint32_t gridFor(Run &run, uint32_t data) {
    return run.get(run.get(run.get(data + 0xc) + 0x24) + 0x5c);
}

// Grid +0x20 tile words, +0x24 row offsets, +0x8c/+0x90 shifts.
uint32_t tileAt(Run &run, uint32_t grid, uint32_t actor) {
    uint32_t y = run.get(run.get(0x537960) + 0xac) + run.get(actor + 0x50);
    uint32_t x = run.get(actor + 0x4c);
    uint32_t row = sar(y, run.get(grid + 0x90));
    uint32_t column = sar(x, run.get(grid + 0x8c));
    uint32_t index = run.get(run.get(grid + 0x24) + row * 4) + column;
    return run.get(grid + 0x20) + index * 4;
}

// 0x4894b0. Receiver +0x10 data, +0x2c actor, +0x4c idle animation.
uint32_t function_4894b0(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x2c);
    uint32_t animation = actor + 0x188;
    run.put(receiver + 0x34, run.get(actor + 0x190));
    run.call(0x4c8220, animation, {run.get(receiver + 0x4c)});
    run.call(0x4c82a0, animation, {run.get(0x5430c4)});
    run.put(receiver + 0x68, 0);
    actor = run.get(receiver + 0x2c);
    run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffe);
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    return 0;
}

// 0x4895b0. +0x68 armed, +0x58 configured delay, +0x60 start, +0x64 delay.
uint32_t function_4895b0(Run &run, uint32_t receiver) {
    if (run.get(receiver + 0x68) == 0) {
        uint32_t data = run.get(receiver + 0x10);
        run.put(receiver + 0x68, 1);
        run.put(receiver + 0x24, run.get(data + 0x1c));
        uint32_t state = run.call(0x4dba00, 0x537668, {0x529a48});
        run.put(run.get(receiver + 0x10) + 0x1c, state);
        run.put(receiver + 0x64, run.get(receiver + 0x58));
        run.put(receiver + 0x60, run.get(0x537210));
    }
    return 0;
}

// 0x489640. +0x48 crumble animation, +0x34 saved animation frame.
uint32_t function_489640(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52c024});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x2c);
    run.put(receiver + 0x34, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {run.get(receiver + 0x48)});
    return 0;
}

// 0x489600. +0x50 next, +0x54 previous; elapsed time is unsigned.
uint32_t function_489600(Run &run, uint32_t receiver) {
    if (run.get(0x537210) - run.get(receiver + 0x60) >= run.get(receiver + 0x64)) {
        uint32_t next = run.get(receiver + 0x50);
        if (next)
            function_4895b0(run, next);
        uint32_t previous = run.get(receiver + 0x54);
        if (previous)
            function_4895b0(run, previous);
        function_489640(run, receiver);
    }
    return 0;
}

// 0x489530. Actor +0x4c/+0x50 position, +0x118..+0x124 collision bounds.
uint32_t function_489530(Run &run, uint32_t receiver) {
    uint32_t player = run.get(0x537e88);
    uint32_t mode = run.get(player + 0xcc);
    if (mode != 1 && mode != 2)
        return 0;
    uint32_t actor = run.get(receiver + 0xc);
    uint32_t bottom = run.get(player + 0x50) + run.get(player + 0x124);
    uint32_t y = run.get(actor + 0x50);
    if (s32(bottom) <= s32(run.get(actor + 0x11c) + y))
        return 0;
    if (s32(bottom) >= s32(run.get(actor + 0x124) + y))
        return 0;
    uint32_t x = run.get(actor + 0x4c);
    uint32_t px = run.get(player + 0x4c);
    if (s32(run.get(player + 0x118) + px) <= s32(run.get(actor + 0x118) + x))
        return 0;
    if (s32(run.get(player + 0x120) + px) >= s32(run.get(actor + 0x120) + x))
        return 0;
    function_4895b0(run, receiver);
    return 0;
}

// 0x489680. +0x170 sprite descriptor, +0x16c current frame.
uint32_t function_489680(Run &run, uint32_t receiver) {
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    uint32_t actor = run.get(receiver + 0x2c);
    uint32_t sprite = run.get(actor + 0x170);
    uint32_t sum = run.get(sprite + 0x64) + run.get(sprite + 0x68);
    uint32_t sign = s32(sum) < 0 ? 0xffffffff : 0;
    uint32_t midpoint = sar(sum - sign, 1);
    if (run.get(actor + 0x16c) == midpoint) {
        uint32_t grid = gridFor(run, run.get(receiver + 0x10));
        uint32_t tile = tileAt(run, grid, run.get(receiver + 0xc));
        run.put(tile, 0xffffffff);
    }
    actor = run.get(receiver + 0x2c);
    if (run.get(actor + 0x1a4) && !run.get(actor + 0x19c))
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
    return 0;
}

// 0x40fe20. +0xa0 chain head; each node +0x5c saved tile.
uint32_t function_40fe20(Run &run, uint32_t receiver) {
    uint32_t data = run.get(receiver + 0x10);
    uint32_t node = run.get(receiver + 0xa0);
    uint32_t grid = gridFor(run, data);
    while (node) {
        uint32_t tile = tileAt(run, grid, run.get(node + 0xc));
        run.put(tile, run.get(node + 0x5c));
        function_4894b0(run, node);
        node = run.get(node + 0x50);
    }
    return 0;
}

// 0x40fde0. +0x9c cached checkpoint.
uint32_t function_40fde0(Run &run, uint32_t receiver) {
    uint32_t checkpoint = run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0x80);
    if (run.get(receiver + 0x9c) != checkpoint) {
        function_40fe20(run, receiver);
        checkpoint = run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0x80);
        run.put(receiver + 0x9c, checkpoint);
    }
    return 0;
}

// 0x40fb30 and 0x4890f0. Registry +0x8 low, +0xc high, +0x10 table,
// +0x14 fallback, +0x18 stride, +0x20 scratch.
uint32_t dispatchState(Run &run, uint32_t registry, uint32_t receiver, uint32_t index) {
    uint32_t low = run.get(registry + 0x8);
    run.put(registry + 0x20, 0);
    uint32_t slot;
    if ((s32(index) < s32(low) || s32(index) > s32(run.get(registry + 0xc))) &&
        !run.call(0x4db6e0, registry, {index, 0})) {
        uint32_t diagnostic = run.get(0x544b4c);
        uint32_t pc = run.call(0x4db5f0, 0);
        run.put(0x544b14, pc);
        run.call(0x4db4d0, run.get(registry + 0x4), {registry, diagnostic, 0xc});
        slot = run.get(registry + 0x14);
    } else {
        slot = (index - run.get(registry + 0x8)) * run.get(registry + 0x18) + run.get(registry + 0x10);
    }
    low = run.get(registry + 0x8);
    if (!run.get(slot)) {
        run.call(0x4a36f0, 0, {receiver});
        return 0;
    }
    run.put(registry + 0x20, 0);
    if ((s32(index) < s32(low) || s32(index) > s32(run.get(registry + 0xc))) &&
        !run.call(0x4db6e0, registry, {index, 0})) {
        uint32_t diagnostic = run.get(0x544b4c);
        uint32_t pc = run.call(0x4db5f0, 0);
        run.put(0x544b14, pc);
        run.call(0x4db4d0, run.get(registry + 0x4), {registry, diagnostic, 0xc});
        slot = run.get(registry + 0x14);
    } else {
        slot = (index - run.get(registry + 0x8)) * run.get(registry + 0x18) + run.get(registry + 0x10);
    }
    invoke(run, run.get(slot), receiver);
    return 0;
}

// Shared base constructor stores, in the order used by 0x40f870/0x488ef0.
void base(Run &run, uint32_t receiver, uint32_t actor) {
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
}

// 0x488ef0. +0x28/+0x2c actor, +0x30 data, +0x48/+0x4c animations.
uint32_t function_488ef0(Run &run, uint32_t receiver, uint32_t actor) {
    base(run, receiver, actor);
    run.put(receiver + 0x28, actor);
    run.put(receiver + 0x2c, actor);
    run.put(receiver + 0x30, run.get(actor + 0x6c));
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x64, 0);
    run.put(receiver, 0x50f664);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x52c010});
    uint32_t out = run.automatic(4);
    run.put(out, 0);
    uint32_t world = run.get(run.get(receiver + 0x2c) + 0xc);
    run.call(0x4f6286, run.get(world + 0x2c) + 0x10, {0x52bff4, out});
    run.put(receiver + 0x48, run.get(out));
    run.put(out, 0);
    world = run.get(run.get(receiver + 0x2c) + 0xc);
    run.call(0x4f6286, run.get(world + 0x2c) + 0x10, {0x52bfdc, out});
    run.put(receiver + 0x4c, run.get(out));
    run.call(0x406290, run.get(receiver + 0x2c));
    actor = run.get(receiver + 0x2c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 1);
    run.put(run.get(receiver + 0x2c) + 0xd0, 1);
    run.put(run.get(receiver + 0x2c) + 0xd4, 0x3000072);
    actor = run.get(receiver + 0xc);
    if (!run.get(actor + 0x64)) {
        run.put(actor + 0x64, 1);
        run.put(actor + 0x8, run.get(actor + 0x8) | 0x20000);
    }
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    uint32_t grid = gridFor(run, run.get(receiver + 0x10));
    run.put(receiver + 0x5c, run.get(tileAt(run, grid, run.get(receiver + 0xc))));
    function_4894b0(run, receiver);
    return receiver;
}

// 0x488e30. Actor +0x6c data; data +0x1c state, +0x18 state object.
uint32_t function_488e30(Run &run, uint32_t actor) {
    uint32_t data = run.get(actor + 0x6c);
    uint32_t state = run.get(data + 0x1c);
    if (state == 0) {
        run.put(data + 0x1c, 0x3e8);
        uint32_t object = run.call(0x4f63ec, 0, {0x6c});
        if (object)
            object = function_488ef0(run, object, actor);
        invoke(run, run.get(run.get(object) + 0x10), object);
        run.put(data + 0x18, object);
    } else if (state == 29) {
        uint32_t object = run.get(data + 0x18);
        invoke(run, run.get(run.get(object) + 0x20), object);
    } else if (state == 30) {
        uint32_t object = run.get(data + 0x18);
        invoke(run, run.get(run.get(object) + 0x1c), object);
    } else if (state != 1000) {
        run.call(0x4dc870, 0, {run.get(data + 0x18)});
    }
    return 1;
}

// 0x40f870. +0x90/+0x94 actor, +0x98 data, +0xa0 child-chain head.
uint32_t function_40f870(Run &run, uint32_t receiver, uint32_t actor) {
    base(run, receiver, actor);
    run.call(0x408370, receiver + 0x28, {actor});
    run.put(receiver + 0x90, actor);
    run.put(receiver + 0x94, actor);
    run.put(receiver + 0x98, run.get(actor + 0x6c));
    run.put(receiver, 0x50b6ec);
    actor = run.get(receiver + 0x2c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 1);
    actor = run.get(receiver + 0x2c);
    run.put(actor + 0x40, run.get(actor + 0x40) | 1);
    run.call(0x40fe90, run.get(receiver + 0x2c), {0x80000000, 0, 0, 0});
    actor = run.get(receiver + 0x2c);
    uint32_t manager = run.get(run.get(run.get(receiver + 0x30) + 0xc) + 0x8);
    uint32_t child = run.call(0x4c8da0, manager, {0, run.get(actor + 0x4c), run.get(actor + 0x50), run.get(actor + 0x64) + 1, 0x522bd4, 0x40000});
    uint32_t callback = run.get(run.get(child + 0x6c) + 0x10);
    if (callback == 0x488e30)
        function_488e30(run, child);
    else
        run.call(callback, 0, {child});
    run.put(receiver + 0xa0, run.get(run.get(child + 0x6c) + 0x18));
    run.put(run.get(run.get(child + 0x6c) + 0x18) + 0x4, receiver);
    run.put(run.get(run.get(child + 0x6c) + 0x18) + 0x54, 0);
    run.put(run.get(run.get(child + 0x6c) + 0x18) + 0x58, run.get(run.get(receiver + 0x10) + 0xb8));
    uint32_t index = 1;
    while (s32(index) < s32(run.get(run.get(receiver + 0x10) + 0xc8))) {
        actor = run.get(receiver + 0x2c);
        uint32_t x = run.get(run.get(0x537960) + 0xa8) * index + run.get(actor + 0x4c);
        manager = run.get(run.get(run.get(receiver + 0x30) + 0xc) + 0x8);
        uint32_t next = run.call(0x4c8da0, manager, {0, x, run.get(actor + 0x50), run.get(actor + 0x64) + 1, 0x522bd4, 0x40000});
        callback = run.get(run.get(next + 0x6c) + 0x10);
        if (callback == 0x488e30)
            function_488e30(run, next);
        else
            run.call(callback, 0, {next});
        run.put(run.get(run.get(next + 0x6c) + 0x18) + 0x4, receiver);
        run.put(run.get(run.get(next + 0x6c) + 0x18) + 0x54, run.get(run.get(child + 0x6c) + 0x18));
        run.put(run.get(run.get(next + 0x6c) + 0x18) + 0x58, run.get(run.get(receiver + 0x10) + 0xb8));
        run.put(run.get(run.get(child + 0x6c) + 0x18) + 0x50, run.get(run.get(next + 0x6c) + 0x18));
        child = next;
        ++index;
    }
    run.put(run.get(run.get(child + 0x6c) + 0x18) + 0x50, 0);
    run.put(receiver + 0x9c, run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0x80));
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    return receiver;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40f870:
        return function_40f870(run, receiver, arguments[0]);
    case 0x40fb30:
        return dispatchState(run, 0x534a10, receiver, arguments[0]);
    case 0x40fde0:
        return function_40fde0(run, receiver);
    case 0x40fe20:
        return function_40fe20(run, receiver);
    case 0x488e30:
        return function_488e30(run, arguments[0]);
    case 0x488ef0:
        return function_488ef0(run, receiver, arguments[0]);
    case 0x4890f0:
        return dispatchState(run, 0x53c2c8, receiver, arguments[0]);
    case 0x4894b0:
        return function_4894b0(run, receiver);
    case 0x489530:
        return function_489530(run, receiver);
    case 0x4895b0:
        return function_4895b0(run, receiver);
    case 0x489600:
        return function_489600(run, receiver);
    case 0x489640:
        return function_489640(run, receiver);
    case 0x489680:
        return function_489680(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_break_single_plank_entry, owned, body)
