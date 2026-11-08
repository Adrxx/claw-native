#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x431440:
    case 0x431810:
    case 0x431c90:
        return 1;
    case 0x431a70:
    case 0x431b10:
    case 0x431b40:
    case 0x431b70:
    case 0x431bd0:
        return 0;
    default:
        return -1;
    }
}

// Registry: bounds +0x08/+0x0c, data +0x10, fallback +0x14, stride +0x18.
uint32_t registrySlot(Run &run, uint32_t index, uint32_t lower) {
    if (s32(index) < s32(lower) || s32(index) > run.gets(0x537284)) {
        if (!run.call(0x4db6e0, 0x537278, {index, 0})) {
            uint32_t file = run.get(0x544b4c);
            uint32_t line = run.call(0x4db5f0, 0);
            uint32_t handler = run.get(0x53727c);
            run.put(0x544b14, line);
            run.call(0x4db4d0, handler, {0x537278, file, 0xc});
            return run.get(0x53728c);
        }
        lower = run.get(0x537280);
    }
    return (index - lower) * run.get(0x537290) + run.get(0x537288);
}

// 0x431440. Invoke the indexed state handler or the original fallback.
uint32_t function_431440(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t lower = run.get(0x537280);
    run.put(0x537298, 0);
    uint32_t slot = registrySlot(run, arguments[0], lower);
    lower = run.get(0x537280);
    if (run.get(slot)) {
        run.put(0x537298, 0);
        slot = registrySlot(run, arguments[0], lower);
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x4a36f0, 0, {receiver});
    }
    return 0;
}

// 0x431a70. +0x10 settings, +0x1c state, +0xbc speed, +0x48..54 cycles.
uint32_t function_431a70(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523604});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    int32_t speed = run.gets(run.get(receiver + 0x10) + 0xbc);
    uint32_t cycle;
    if (speed <= -300 || speed >= 300) {
        cycle = run.get(receiver + 0x48);
    } else if (speed <= -225 || speed >= 225 || speed <= -150 || speed >= 150) {
        cycle = run.get(receiver + 0x4c);
    } else if (speed <= -75 || speed >= 75) {
        cycle = run.get(receiver + 0x50);
    } else {
        cycle = run.get(receiver + 0x54);
    }
    uint32_t object = run.get(receiver + 0x2c);
    run.put(receiver + 0x34, run.get(object + 0x190));
    run.call(0x4c8220, object + 0x188, {cycle});
    uint32_t time = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {time});
    return 0;
}

// 0x431b40. Save the current state and select ES_MOVE.
uint32_t function_431b40(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x526544});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    return 0;
}

// 0x431bd0. +0x4c/+0x50 position, +0x118..124 collision bounds.
uint32_t function_431bd0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t player = run.get(0x537e88);
    uint32_t bottom = run.get(player + 0x124);
    uint32_t x = run.get(player + 0x4c);
    uint32_t right = run.get(player + 0x120);
    uint32_t left = run.get(player + 0x118);
    uint32_t y = run.get(player + 0x50);
    uint32_t first = run.automatic(-0x20);
    uint32_t second = run.automatic(-0x10);
    run.put(first + 0xc, bottom + y);
    uint32_t object = run.get(receiver + 0xc);
    run.put(first + 0x4, y);
    run.put(first + 0x0, left + x);
    run.put(first + 0x8, right + x);
    y = run.get(object + 0x50);
    x = run.get(object + 0x4c);
    bottom = run.get(object + 0x124);
    right = run.get(object + 0x120);
    uint32_t top = run.get(object + 0x11c);
    left = run.get(object + 0x118);
    run.put(second + 0x0, left + x);
    run.put(second + 0x4, top + y);
    run.put(second + 0x8, right + x);
    run.put(second + 0xc, bottom + y);
    if (run.get(player + 0xcc) == 3) {
        return 0;
    }
    return run.icall(0x546ce0, {first, first, second}) ? 1 : 0;
}

// 0x431c90. +0x6c player settings, +0x14 controller, +0x84 carried speed.
uint32_t function_431c90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t controller = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (controller) {
        if (arguments[0]) {
            run.put(controller + 0x84, 0);
        } else {
            run.put(controller + 0x84, run.get(run.get(receiver + 0x10) + 0xbc));
        }
    }
    return 0;
}

// 0x431b10. Advance the cycle and enter the moving state on overlap.
uint32_t function_431b10(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t time = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {time});
    uint32_t frame = run.frame;
    run.frame = frame - 0x8;
    uint32_t overlaps = function_431bd0(run, receiver, nullptr);
    run.frame = frame;
    if (overlaps) {
        function_431b40(run, receiver, nullptr);
    }
    return 0;
}

// 0x431b70. Carry on overlap; otherwise clear the speed and return to idle.
uint32_t function_431b70(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t time = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {time});
    if (run.get(run.get(0x537e88) + 0xcc) != 3) {
        uint32_t frame = run.frame;
        run.frame = frame - 0x8;
        uint32_t overlaps = function_431bd0(run, receiver, nullptr);
        run.frame = frame;
        uint32_t clear = overlaps ? 0 : 1;
        function_431c90(run, receiver, &clear);
        if (!overlaps) {
            function_431a70(run, receiver, nullptr);
        }
    }
    return 0;
}

// +0x2c object, +0x0c parent, whose +0x2c is the cycle registry.
uint32_t cycleRegistry(Run &run, uint32_t receiver) {
    return run.get(run.get(run.get(receiver + 0x2c) + 0xc) + 0x2c);
}

// 0x431810. Construct and load direction-specific cycles.
uint32_t function_431810(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    run.put(receiver + 0x0, 0x50b064);
    run.put(receiver + 0x8, object);
    run.put(receiver + 0xc, object);
    uint32_t settings = run.get(object + 0x6c);
    run.put(receiver + 0x10, settings);
    run.put(receiver + 0x4, 0);
    run.call(0x4c7fa0, object, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0xc), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x28, object);
    run.put(receiver + 0x2c, object);
    run.put(receiver + 0x30, run.get(object + 0x6c));
    settings = run.get(receiver + 0x10);
    run.put(receiver + 0x0, 0x50c6bc);
    int32_t speed = run.gets(settings + 0xbc);
    if (speed > 300) {
        run.put(settings + 0xbc, 300);
    } else if (speed < -300) {
        run.put(settings + 0xbc, 0xfffffed4);
    }
    uint32_t lastName;
    if (run.gets(run.get(receiver + 0x10) + 0xbc) < 0) {
        uint32_t output = run.automatic(0x4);
        run.put(output, 0);
        run.call(0x4f6286, cycleRegistry(run, receiver) + 0x10, {0x52417c, output});
        run.put(receiver + 0x48, run.get(output));
        run.put(output, 0);
        run.call(0x4f6286, cycleRegistry(run, receiver) + 0x10, {0x5240d8, output});
        run.put(receiver + 0x4c, run.get(output));
        run.put(output, 0);
        run.call(0x4f6286, cycleRegistry(run, receiver) + 0x10, {0x5265ec, output});
        run.put(receiver + 0x50, run.get(output));
        lastName = 0x5265dc;
    } else {
        uint32_t value = run.call(0x4061b0, cycleRegistry(run, receiver), {0x5265c8});
        run.put(receiver + 0x48, value);
        value = run.call(0x4061b0, cycleRegistry(run, receiver), {0x5265b0});
        run.put(receiver + 0x4c, value);
        value = run.call(0x4061b0, cycleRegistry(run, receiver), {0x526598});
        run.put(receiver + 0x50, value);
        lastName = 0x526580;
    }
    uint32_t value = run.call(0x4061b0, cycleRegistry(run, receiver), {lastName});
    run.put(receiver + 0x54, value);
    run.call(0x406290, run.get(receiver + 0x2c));
    uint32_t name = run.get(run.get(receiver + 0x2c) + 0x170) + 0x24;
    uint32_t string = run.automatic(-0x14);
    run.call(0x4f65f2, string, {name});
    if (!run.call(0x4a3dc0, 0, {run.get(string), 0x52656c})) {
        uint32_t target = run.get(receiver + 0xc);
        uint32_t left = run.get(target + 0x118);
        uint32_t difference = run.get(target + 0x120) - left;
        run.put(target + 0x120, uint32_t(s32(difference) / 2) + left);
    }
    run.put(run.get(receiver + 0x2c) + 0xd0, 1);
    run.put(run.get(receiver + 0x2c) + 0xd4, 0x3000072);
    uint32_t target = run.get(receiver + 0xc);
    if (!run.get(target + 0x64)) {
        uint32_t flags = run.get(target + 0x8);
        run.put(target + 0x64, 1);
        run.put(target + 0x8, flags | 0x20000);
    }
    function_431a70(run, receiver, nullptr);
    run.call(0x4f6584, string);
    return receiver;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x431440:
        return function_431440(run, receiver, arguments);
    case 0x431810:
        return function_431810(run, receiver, arguments);
    case 0x431a70:
        return function_431a70(run, receiver, arguments);
    case 0x431b10:
        return function_431b10(run, receiver, arguments);
    case 0x431b40:
        return function_431b40(run, receiver, arguments);
    case 0x431b70:
        return function_431b70(run, receiver, arguments);
    case 0x431bd0:
        return function_431bd0(run, receiver, arguments);
    case 0x431c90:
        return function_431c90(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level9_conveyor_entry, owned, body)
