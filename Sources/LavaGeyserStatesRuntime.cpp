// Lava geyser state closure, translated from the original v1.0 bodies.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x455b00:
    case 0x455ed0:
        return 1;
    case 0x456040:
    case 0x4560a0:
    case 0x4560c0:
    case 0x456120:
        return 0;
    default:
        return -1;
    }
}

// The global dispatch table has signed lower/upper bounds, data and stride.
uint32_t dispatchSlot(Run &run, uint32_t index) {
    uint32_t lower = run.get(0x537a08);
    run.put(0x537a20, 0);
    if (s32(index) < s32(lower) || s32(index) > s32(run.get(0x537a0c))) {
        if (!run.call(0x4db6e0, 0x537a00, {index, 0})) {
            uint32_t message = run.get(0x544b4c);
            uint32_t site = run.call(0x4db5f0, 0);
            uint32_t context = run.get(0x537a04);
            run.put(0x544b14, site);
            run.call(0x4db4d0, context, {0x537a00, message, 0xc});
            return run.get(0x537a14);
        }
        lower = run.get(0x537a08);
    }
    return (index - lower) * run.get(0x537a18) + run.get(0x537a10);
}

// 0x455b00. Invoke the selected state handler, or destroy an unhandled object.
uint32_t function_455b00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[0];
    uint32_t slot = dispatchSlot(run, index);
    if (run.get(slot)) {
        slot = dispatchSlot(run, index);
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x4a36f0, 0, {receiver});
    }
    return 0;
}

// 0x456040. +0x10 is the world object; +0x24 saves its preceding state.
uint32_t function_456040(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t idle = run.call(0x4dba00, 0x537668, {0x523604});
    run.put(run.get(receiver + 0x10) + 0x1c, idle);
    // +0xa0 is the wait duration and +0x9c the starting clock.
    run.put(receiver + 0xa0, run.get(run.get(receiver + 0x10) + 0xbc));
    run.put(receiver + 0x9c, run.get(0x537210));
    uint32_t clock = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    run.put(run.get(receiver + 0x10) + 0x64, run.get(clock + 0x80));
    return 0;
}

// 0x4560c0. +0x2c is the actor and +0xa4 the selected eruption animation.
uint32_t function_4560c0(Run &run, uint32_t receiver) {
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t erupting = run.call(0x4dba00, 0x537668, {0x528590});
    run.put(run.get(receiver + 0x10) + 0x1c, erupting);
    uint32_t actor = run.get(receiver + 0x2c);
    uint32_t animation = run.get(receiver + 0xa4);
    // +0x34 saves the previous animation token.
    run.put(receiver + 0x34, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    return 0;
}

// 0x455ed0. Construct the state controller and its embedded actor helper.
uint32_t function_455ed0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x08, actor);
    run.put(receiver + 0x0c, actor);
    run.put(receiver + 0x10, run.get(actor + 0x6c));
    run.put(receiver + 0x04, 0);
    run.call(0x4c7fa0, actor, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0x0c), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.call(0x408370, receiver + 0x28, {actor});
    run.put(receiver + 0x90, actor);
    run.put(receiver + 0x94, actor);
    run.put(receiver + 0x98, run.get(actor + 0x6c));
    run.put(receiver + 0x9c, 0);
    run.put(receiver + 0xa0, 0);
    run.put(receiver, 0x50e4b4);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x5285bc});
    run.put(run.get(receiver + 0x2c) + 0xd0, 4);
    uint32_t primaryOut = run.automatic(4);
    run.put(primaryOut, 0);
    run.put(run.get(receiver + 0x2c) + 0xd4, 1);
    uint32_t resources = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x2c);
    run.call(0x4f6286, resources + 0x10, {0x5285bc, primaryOut});
    uint32_t selected = run.get(primaryOut);
    if (!selected) {
        uint32_t fallbackOut = run.automatic(-0x14);
        run.put(fallbackOut, 0);
        resources = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x2c);
        run.call(0x4f6286, resources + 0x10, {0x5234b4, fallbackOut});
        selected = run.get(fallbackOut);
    }
    run.put(receiver + 0xa4, selected);
    run.put(run.get(receiver + 0x0c) + 0x104, 10);
    uint32_t object = run.get(receiver + 0x0c);
    double duration = double(run.gets(object + 0x104)) * double(run.getf(0x5262b0));
    uint32_t ticks = run.call_x87(0x4a30e0, 0, duration);
    run.put(object + 0x104, ticks);
    function_456040(run, receiver);
    return receiver;
}

// 0x4560a0. Elapsed clock arithmetic and comparison are unsigned.
uint32_t function_4560a0(Run &run, uint32_t receiver) {
    uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x9c);
    if (elapsed >= run.get(receiver + 0xa0)) {
        function_4560c0(run, receiver);
    }
    return 0;
}

// 0x456120. Update the eruption rectangle and react to animation/clock changes.
uint32_t function_456120(Run &run, uint32_t receiver) {
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    uint32_t frame = run.get(run.get(receiver + 0x2c) + 0x16c) - 1;
    if (s32(frame) >= 0 && s32(frame) < 0x13) {
        uint32_t source = 0x50e380 + (frame << 4);
        uint32_t destination = run.get(receiver + 0x0c) + 0x138;
        run.put(destination, run.get(source));
        run.put(destination + 0x04, run.get(source + 0x04));
        run.put(destination + 0x08, run.get(source + 0x08));
        run.put(destination + 0x0c, run.get(source + 0x0c));
    }
    uint32_t animation = run.get(receiver + 0x2c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14)) {
        function_4560c0(run, receiver);
    }
    uint32_t clock = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (run.get(run.get(receiver + 0x10) + 0x64) != run.get(clock + 0x80)) {
        function_456040(run, receiver);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x455b00:
        return function_455b00(run, receiver, arguments);
    case 0x455ed0:
        return function_455ed0(run, receiver, arguments);
    case 0x456040:
        return function_456040(run, receiver);
    case 0x4560a0:
        return function_4560a0(run, receiver);
    case 0x4560c0:
        return function_4560c0(run, receiver);
    case 0x456120:
        return function_456120(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_lava_geyser_states_entry, owned, body)
