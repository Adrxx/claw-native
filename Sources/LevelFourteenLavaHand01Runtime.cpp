// Level 14 lava hand state and construction behavior.
#include "ClawRuntime.hpp"
namespace {
using claw::Run;
using claw::s32;
int owned(uint32_t function) {
    switch (function) {
    case 0x4562e0:
    case 0x4566b0:
        return 1;
    case 0x456840:
    case 0x456880:
    case 0x4568b0:
    case 0x456a10:
        return 0;
    default:
        return -1;
    }
}
uint32_t continuation(Run &run, uint32_t receiver, uint32_t pc) {
    ClawCompilerContext context{};
    context.size = sizeof(context);
    context.version = CLAW_CONTEXT_VERSION;
    context.inputMask = 0x5c1;
    context.outputMask = 0x5c1;
    context.ebp = receiver;
    context.esp = run.frame - 0x10;
    context.eip = 0x4db5f0;
    context.fsHead = 0xffffffff;
    context.continuation = pc;
    run.put(context.esp, pc);
    return run.context_call(0x4db5f0, context);
}
// 0x4562e0. Global table signed bounds and byte stride.
uint32_t dispatchState(Run &run, uint32_t receiver, uint32_t index) {
    uint32_t low = run.get(0x537a38);
    run.put(0x537a50, 0);
    uint32_t slot;
    if ((s32(index) < s32(low) || s32(index) > s32(run.get(0x537a3c))) &&
        !run.call(0x4db6e0, 0x537a30, {index, 0})) {
        const uint32_t message = run.get(0x544b4c);
        const uint32_t pc = continuation(run, receiver, 0x456340);
        run.put(0x544b14, pc);
        run.call(0x4db4d0, run.get(0x537a34), {0x537a30, message, 0xc});
        slot = run.get(0x537a44);
        low = run.get(0x537a38);
    } else {
        low = run.get(0x537a38);
        slot = (index - low) * run.get(0x537a48) + run.get(0x537a40);
    }
    if (!run.get(slot)) {
        run.call(0x4a36f0, 0, {receiver});
        return 0;
    }
    run.put(0x537a50, 0);
    if ((s32(index) < s32(low) || s32(index) > s32(run.get(0x537a3c))) &&
        !run.call(0x4db6e0, 0x537a30, {index, 0})) {
        const uint32_t message = run.get(0x544b4c);
        const uint32_t pc = continuation(run, receiver, 0x4563ba);
        run.put(0x544b14, pc);
        run.call(0x4db4d0, run.get(0x537a34), {0x537a30, message, 0xc});
        slot = run.get(0x537a44);
    } else {
        low = run.get(0x537a38);
        slot = (index - low) * run.get(0x537a48) + run.get(0x537a40);
    }
    run.call(run.get(slot), receiver, {});
    return 0;
}
// 0x456840. +0x2c actor, +0x10 logic, +0x24 saved state.
uint32_t enterIdle(Run &run, uint32_t receiver) {
    const uint32_t actor = run.get(receiver + 0x2c);
    run.put(actor + 0x08, run.get(actor + 0x08) & 0xfffffffe);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    const uint32_t state = run.call(0x4dba00, 0x537668, {0x523604});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    run.put(receiver + 0xac, 0);
    return 0;
}
// 0x4568b0. +0x8c direction, +0x38/+0x40 horizontal bounds.
uint32_t enterThrow(Run &run, uint32_t receiver) {
    const uint32_t sourceActor = run.get(receiver + 0x0c);
    if (s32(run.get(sourceActor + 0x4c)) <= s32(run.get(run.get(0x537e88) + 0x4c)))
        run.put(receiver + 0x8c, 2);
    if (s32(run.get(sourceActor + 0x4c)) > s32(run.get(run.get(0x537e88) + 0x4c)))
        run.put(receiver + 0x8c, 3);
    uint32_t actor = run.get(receiver + 0x2c);
    const bool right = run.get(receiver + 0x8c) == 2;
    const bool facing = (run.get8(actor + 0x40) & 2) != 0;
    if (right != facing) {
        const uint32_t left = run.get(receiver + 0x38);
        const uint32_t mirroredLeft = 0u - run.get(receiver + 0x40);
        run.put(receiver + 0x38, mirroredLeft);
        run.put(receiver + 0x40, 0u - left);
        const uint32_t flags = run.get(actor + 0x40);
        run.put(actor + 0x40, right ? flags | 2u : flags & 0xfffffffdu);
        actor = run.get(receiver + 0x2c);
        const uint32_t firstLeft = run.get(actor + 0x118);
        if (firstLeft != 0x80000000) {
            const uint32_t firstRight = run.get(actor + 0x120);
            run.put(actor + 0x118, 0u - firstRight);
            run.put(actor + 0x120, 0u - firstLeft);
        }
        const uint32_t secondLeft = run.get(actor + 0x128);
        if (secondLeft != 0x80000000) {
            const uint32_t secondRight = run.get(actor + 0x130);
            run.put(actor + 0x128, 0u - secondRight);
            run.put(actor + 0x130, 0u - secondLeft);
        }
        run.call(0x406180, actor, {});
    }
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    const uint32_t state = run.call(0x4dba00, 0x537668, {0x5285d0});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    actor = run.get(receiver + 0x2c);
    const uint32_t animation = run.get(receiver + 0xa4);
    run.put(receiver + 0x34, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    run.put(receiver + 0xb4, 0);
    return 0;
}
// 0x456880. +0x9c timer origin, +0xa0 unsigned duration.
uint32_t updateIdle(Run &run, uint32_t receiver) {
    const uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x9c);
    if (elapsed >= run.get(receiver + 0xa0)) {
        const uint32_t actor = run.get(receiver + 0x2c);
        run.put(actor + 0x08, run.get(actor + 0x08) | 1u);
        enterThrow(run, receiver);
    }
    return 0;
}
// 0x4566b0. +0xa4 throw animation, +0xa8 idle delay, +0xb0 shot limit.
uint32_t construct(Run &run, uint32_t receiver, uint32_t actor) {
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x08, actor);
    run.put(receiver + 0x0c, actor);
    const uint32_t logic = run.get(actor + 0x6c);
    run.put(receiver + 0x10, logic);
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
    run.put(receiver, 0x50e4dc);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x5285f8});
    uint32_t target = run.get(receiver + 0x2c);
    run.put(target + 0x08, run.get(target + 0x08) | 4u);
    run.put(run.get(receiver + 0x2c) + 0xd0, 1);
    run.put(run.get(receiver + 0x2c) + 0xd8, 2);
    const uint32_t scene = run.get(run.get(receiver + 0x2c) + 0x0c);
    uint32_t animation = run.call(0x4061b0, run.get(scene + 0x2c), {0x5285f8});
    if (!animation)
        animation = run.call(0x4062e0, receiver + 0x28, {0x5234b4});
    run.put(receiver + 0xa4, animation);
    const uint32_t sourceActor = run.get(receiver + 0x0c);
    const uint32_t y = run.get(sourceActor + 0x50);
    const uint32_t x = run.get(sourceActor + 0x4c);
    const uint32_t rect = run.get(receiver + 0x10);
    const uint32_t bottom = run.get(rect + 0x38) - y;
    const uint32_t top = run.get(rect + 0x34) - y;
    const uint32_t right = run.get(rect + 0x30) - x;
    const uint32_t left = run.get(rect + 0x2c) - x;
    target = run.get(receiver + 0x2c);
    run.put(target + 0x138, left);
    run.put(target + 0x13c, top);
    run.put(target + 0x140, right);
    run.put(target + 0x144, bottom);
    const uint32_t delay = run.get(run.get(receiver + 0x10) + 0xbc);
    run.put(receiver + 0xac, 0);
    run.put(receiver + 0xa8, delay);
    uint32_t limit = run.get(run.get(receiver + 0x0c) + 0x108);
    if (s32(limit) <= 0)
        limit = 1;
    run.put(receiver + 0xb0, limit);
    enterIdle(run, receiver);
    return receiver;
}
// 0x456a10. +0xb4 prevents duplicate spawn; +0xac counts shots.
uint32_t updateThrow(Run &run, uint32_t receiver) {
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    uint32_t actor = run.get(receiver + 0x2c);
    if (run.get(actor + 0x16c) == 10 && !run.get(receiver + 0xb4)) {
        run.put(receiver + 0xb4, 1);
        actor = run.get(receiver + 0x2c);
        const uint32_t depth = run.get(actor + 0x64) - 1;
        const uint32_t y = run.get(actor + 0x50);
        const uint32_t x = run.get(actor + 0x4c);
        const uint32_t factory = run.get(run.get(run.get(receiver + 0x30) + 0x0c) + 0x08);
        const uint32_t projectile = run.call(0x4c8da0, factory, {0, x, y, depth, 0x522a48, 0x40000});
        if (projectile) {
            const uint32_t definition = run.get(projectile + 0x6c);
            run.call(run.get(definition + 0x10), 0, {projectile});
            const uint32_t speed = run.get(receiver + 0x8c) == 3 ? 0xffffff6a : 0x96;
            const uint32_t motion = run.get(run.get(projectile + 0x6c) + 0x18);
            run.call(0x4571a0, motion, {speed});
        }
        run.put(receiver + 0xac, run.get(receiver + 0xac) + 1);
    }
    actor = run.get(receiver + 0x2c);
    if (run.get(actor + 0x1a4) && !run.get(actor + 0x19c)) {
        if (run.get(receiver + 0xac) == run.get(receiver + 0xb0)) {
            run.put(receiver + 0xa0, run.get(receiver + 0xa8));
            run.put(receiver + 0x9c, run.get(0x537210));
            enterIdle(run, receiver);
        } else {
            enterThrow(run, receiver);
        }
    }
    return 0;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4562e0:
        return dispatchState(run, receiver, arguments[0]);
    case 0x4566b0:
        return construct(run, receiver, arguments[0]);
    case 0x456840:
        return enterIdle(run, receiver);
    case 0x456880:
        return updateIdle(run, receiver);
    case 0x4568b0:
        return enterThrow(run, receiver);
    case 0x456a10:
        return updateThrow(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace
CLAW_MODULE_ENTRY(claw_level_fourteen_lava_hand_01_entry, owned, body)
