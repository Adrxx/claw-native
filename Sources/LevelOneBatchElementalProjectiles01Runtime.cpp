// Level 1 fire, ice and lightning sword projectiles
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x410100:
        return 1;
    case 0x4101c0:
        return 1;
    case 0x410280:
        return 1;
    case 0x410ec0:
        return 1;
    case 0x411310:
        return 0;
    case 0x411370:
        return 1;
    case 0x4117c0:
        return 0;
    case 0x411820:
        return 1;
    case 0x411c70:
        return 0;
    default:
        return -1;
    }
}

// Projectile object fields: +0x0c sprite, +0x12c animation owner, +0x130 level
// object, +0x148 loaded animation, +0x150 flare light, +0x50/+0x68/+0x70 doubles.
// State object fields: +0x18 projectile, +0x1c state. Owner object: +0x6c state.

uint32_t function_410ec0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_411370(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_411820(Run &run, uint32_t receiver, const uint32_t *arguments);

// Shared body of 0x410100, 0x4101c0 and 0x410280 (callbacks that differ only in
// the constructor they call). The original dereferences null when operator new
// returns 0; that branch is translated faithfully and faults on the read.
uint32_t stateCallback(Run &run, uint32_t constructor, uint32_t owner) {
    uint32_t state = run.get(owner + 0x6c);
    uint32_t code = run.get(state + 0x1c);
    if (code > 0x1d) {
        if (code == 0x1e) {
            uint32_t projectile = run.get(state + 0x18);
            run.vcall(projectile, 0x1c);
            return 1;
        }
        if (code == 0x3e8)
            return 1;
    } else if (code == 0x1d) {
        uint32_t projectile = run.get(state + 0x18);
        run.vcall(projectile, 0x20);
        return 1;
    } else if (code == 0) {
        run.put(state + 0x1c, 0x3e8);
        uint32_t memory = run.call(0x4f63ec, 0, {0x158});
        run.put(run.automatic(4), memory);
        uint32_t projectile = 0;
        if (memory) {
            if (constructor == 0x410ec0)
                projectile = function_410ec0(run, memory, &owner);
            else if (constructor == 0x411370)
                projectile = function_411370(run, memory, &owner);
            else
                projectile = function_411820(run, memory, &owner);
        }
        run.vcall(projectile, 0x10);
        run.put(state + 0x18, projectile);
        return 1;
    }
    run.call(0x4dc870, 0, {run.get(state + 0x18)});
    return 1;
}

// Shared body of the three projectile constructors.
uint32_t construct(Run &run, uint32_t self, uint32_t owner, uint32_t vtable, uint32_t animationName,
                   uint32_t resourceName) {
    run.call(0x4107c0, self, {owner});
    run.put(self, vtable);
    run.call(0x4c7970, run.get(self + 0x12c), {animationName});
    uint32_t outValue = run.automatic(4);
    uint32_t group = run.get(run.get(run.get(self + 0x12c) + 0xc) + 0x2c) + 0x10;
    run.put(outValue, 0);
    run.call(0x4f6286, group, {resourceName, outValue});
    uint32_t loaded = run.get(outValue);
    uint32_t sprite = run.get(self + 0xc);
    run.put(self + 0x148, loaded);
    uint32_t flags = run.get(sprite + 0x8);
    flags = flags | 0x80000;
    run.put(sprite + 0x8, flags);
    if (run.get(0x53724c) == 0 && run.get(run.get(0x5371fc) + 0x124) != 0) {
        uint32_t animation = run.get(self + 0x12c);
        uint32_t x = run.get(animation + 0x4c);
        uint32_t y = run.get(animation + 0x50);
        uint32_t z = run.get(animation + 0x64) - 1;
        uint32_t level = run.get(self + 0x130);
        uint32_t manager = run.get(run.get(level + 0xc) + 0x8);
        uint32_t light = run.call(0x4c8da0, manager, {0, x, y, z, 0x522e24, 0x40000});
        run.put(self + 0x150, light);
        return self;
    }
    run.put(self + 0x150, 0);
    return self;
}

// Shared body of the three per-frame updates: runs the base update, then moves
// the flare light to the projectile position.
uint32_t update(Run &run, uint32_t self) {
    run.call(0x4742f0, self);
    uint32_t light = run.get(self + 0x150);
    if (light == 0)
        return 0;
    double xPosition = run.getd(self + 0x50);
    double yBase = run.getd(self + 0x68);
    double limit = run.getd(0x50b7f0);
    double adjusted;
    if (xPosition > limit)
        adjusted = yBase - run.getd(0x50b7f8);
    else
        adjusted = yBase - run.getd(0x50b800);
    uint32_t converted = run.call_x87(0x4a30e0, 0, adjusted);
    run.put(light + 0x4c, converted);
    double second = run.getd(self + 0x70);
    converted = run.call_x87(0x4a30e0, 0, second);
    uint32_t current = run.get(self + 0x150);
    run.put(current + 0x50, converted);
    return 0;
}

// 0x410100. cdecl, 1 stack argument: the owner object.
uint32_t function_410100(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return stateCallback(run, 0x410ec0, arguments[0]);
}

// 0x4101c0. Same as 0x410100 with the 0x411370 constructor.
uint32_t function_4101c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return stateCallback(run, 0x411370, arguments[0]);
}

// 0x410280. Same as 0x410100 with the 0x411820 constructor.
uint32_t function_410280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return stateCallback(run, 0x411820, arguments[0]);
}

// 0x410ec0. thiscall, 1 stack argument: fire sword projectile constructor.
uint32_t function_410ec0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return construct(run, receiver, arguments[0], 0x50b7bc, 0x5241e4, 0x5241d4);
}

// 0x411310. thiscall: fire sword projectile update.
uint32_t function_411310(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return update(run, receiver);
}

// 0x411370. thiscall, 1 stack argument: ice sword projectile constructor.
uint32_t function_411370(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return construct(run, receiver, arguments[0], 0x50b80c, 0x524244, 0x524230);
}

// 0x4117c0. thiscall: ice sword projectile update.
uint32_t function_4117c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return update(run, receiver);
}

// 0x411820. thiscall, 1 stack argument: lightning sword projectile constructor.
uint32_t function_411820(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return construct(run, receiver, arguments[0], 0x50b844, 0x5242a4, 0x524294);
}

// 0x411c70. thiscall: lightning sword projectile update.
uint32_t function_411c70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return update(run, receiver);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x410100:
        return function_410100(run, receiver, arguments);
    case 0x4101c0:
        return function_4101c0(run, receiver, arguments);
    case 0x410280:
        return function_410280(run, receiver, arguments);
    case 0x410ec0:
        return function_410ec0(run, receiver, arguments);
    case 0x411310:
        return function_411310(run, receiver, arguments);
    case 0x411370:
        return function_411370(run, receiver, arguments);
    case 0x4117c0:
        return function_4117c0(run, receiver, arguments);
    case 0x411820:
        return function_411820(run, receiver, arguments);
    case 0x411c70:
        return function_411c70(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_elemental_projectiles_01_entry, owned, body)
