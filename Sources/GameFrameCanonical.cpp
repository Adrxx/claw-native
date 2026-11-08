// Original outer game-frame runtime.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x428b60:
    case 0x46ac30:
    case 0x475dc0:
        return 0;
    default:
        return -1;
    }
}

// 0x428b60 GameManager::frame. Timing is evaluated even while paused.
uint32_t function_428b60(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4b82f0, receiver);
    uint32_t clock = run.get(0x541328);
    uint32_t accumulated = run.get(0x537210);
    run.put(0x537208, clock);
    uint32_t delta = run.get(0x54132c);
    accumulated += delta;
    run.put(0x53720c, delta);
    run.put(0x537210, accumulated);
    // Manager +0xb0 pause, +0x2c active state, +0x6c signed countdown.
    if (run.get(receiver + 0xb0) != 0)
        return 0;
    uint32_t state = run.get(receiver + 0x2c);
    run.vcall(state, 0x14);
    uint32_t countdown = run.get(receiver + 0x6c);
    if (s32(countdown) > 0) {
        run.put(receiver + 0x6c, countdown - 1);
    }
    return 1;
}

// 0x46ac30 GameState::frame.
uint32_t function_46ac30(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t delta = run.get(0x53720c);
    if (delta <= 0x12 || delta >= 0x64) {
        run.call(0x46ace0, receiver);
    } else {
        run.call(0x46ad70, receiver);
    }
    // State +0xc scene, +0x4 application; scene +0x24 world.
    uint32_t scene = run.get(receiver + 0x0c);
    uint32_t world = run.get(scene + 0x24);
    // World +0x5c plane; plane +0x84/+0x88 audio coordinates.
    uint32_t plane = run.get(world + 0x5c);
    uint32_t application = run.get(receiver + 0x04);
    uint32_t y = run.get(plane + 0x88);
    uint32_t x = run.get(plane + 0x84);
    // Application +0x5c audio controller.
    uint32_t audio = run.get(application + 0x5c);
    run.call(0x4025c0, audio, {x, y});
    scene = run.get(receiver + 0x0c);
    // Scene +0x8 actor list, +0x4 display context.
    uint32_t actors = run.get(scene + 0x08);
    uint32_t display = run.get(scene + 0x04);
    // Display +0x14 render target, +0x18 second renderer argument.
    uint32_t target = run.get(display + 0x14);
    world = run.get(scene + 0x24);
    run.call(0x4cb9b0, world, {target, actors});
    scene = run.get(receiver + 0x0c);
    // Scene +0xc renderer with vtable +0x34 draw method.
    uint32_t renderer = run.get(scene + 0x0c);
    display = run.get(scene + 0x04);
    uint32_t second = run.get(display + 0x18);
    target = run.get(display + 0x14);
    run.vcall(renderer, 0x34, {target, second});
    run.call(0x46c2c0, receiver);
    scene = run.get(receiver + 0x0c);
    display = run.get(scene + 0x04);
    // Display +0x10 presentation context; context +0x2c surface.
    uint32_t presentation = run.get(display + 0x10);
    uint32_t surface = run.get(presentation + 0x2c);
    run.call(0x4b98b0, surface, {0});
    scene = run.get(receiver + 0x0c);
    world = run.get(scene + 0x24);
    plane = run.get(world + 0x5c);
    if (plane != 0) {
        run.call(0x4d2000, plane);
    }
    return 1;
}

// 0x475dc0 MultiplayerState::frame.
uint32_t function_475dc0(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4774f0, receiver);
    run.call(0x477840, receiver);
    run.call(0x478290, receiver, {0});
    uint32_t delta = run.get(0x53720c);
    if (delta <= 0x12 || delta >= 0x64) {
        run.call(0x46ace0, receiver);
    } else {
        run.call(0x46ad70, receiver);
    }
    uint32_t scene = run.get(receiver + 0x0c);
    uint32_t world = run.get(scene + 0x24);
    uint32_t plane = run.get(world + 0x5c);
    uint32_t application = run.get(receiver + 0x04);
    uint32_t y = run.get(plane + 0x88);
    uint32_t x = run.get(plane + 0x84);
    uint32_t audio = run.get(application + 0x5c);
    run.call(0x4025c0, audio, {x, y});
    scene = run.get(receiver + 0x0c);
    uint32_t actors = run.get(scene + 0x08);
    uint32_t display = run.get(scene + 0x04);
    uint32_t target = run.get(display + 0x14);
    world = run.get(scene + 0x24);
    run.call(0x4cb9b0, world, {target, actors});
    scene = run.get(receiver + 0x0c);
    uint32_t renderer = run.get(scene + 0x0c);
    display = run.get(scene + 0x04);
    uint32_t second = run.get(display + 0x18);
    target = run.get(display + 0x14);
    run.vcall(renderer, 0x34, {target, second});
    delta = run.get(0x53720c);
    application = run.get(receiver + 0x04);
    // Application +0x4c message/chat controller.
    uint32_t chat = run.get(application + 0x4c);
    run.call(0x4224f0, chat, {delta});
    run.call(0x46c2c0, receiver);
    scene = run.get(receiver + 0x0c);
    display = run.get(scene + 0x04);
    uint32_t presentation = run.get(display + 0x10);
    uint32_t surface = run.get(presentation + 0x2c);
    run.call(0x4b98b0, surface, {0});
    scene = run.get(receiver + 0x0c);
    world = run.get(scene + 0x24);
    plane = run.get(world + 0x5c);
    if (plane != 0) {
        run.call(0x4d2000, plane);
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x428b60:
        return function_428b60(run, receiver, arguments);
    case 0x46ac30:
        return function_46ac30(run, receiver, arguments);
    case 0x475dc0:
        return function_475dc0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_game_frame_canonical_entry, owned, body)
