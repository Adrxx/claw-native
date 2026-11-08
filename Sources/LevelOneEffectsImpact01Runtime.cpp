// Level 1 impact particle effects
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
    case 0x461a00:
        return 6;
    case 0x461a90:
        return 1;
    case 0x461bc0:
        return 1;
    case 0x461c40:
        return 4;
    default:
        return -1;
    }
}

// 0x461a00. Spawns a "HitBurst" effect object at the given position, tied to
// the hit target (arguments[5]). Fields of the target: +0x08 flags, +0x38 id.
// Fields of the effect: +0x6c logic table (method at +0x10), +0x80 target.
uint32_t function_461a00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t owner = arguments[0];
    uint32_t target = arguments[5];
    if (target == 0)
        return 0;
    if (run.get(target + 0x38) == 0xffffffff)
        return 0;
    if ((run.get(target + 0x08) & 0x10000) != 0)
        return 0;
    uint32_t manager = run.get(owner + 0x08);
    uint32_t effect = run.call(0x4c8da0, manager, {0, arguments[1], arguments[2], arguments[3], 0x522570, 0x40000});
    if (effect == 0)
        return 0;
    uint32_t name = 0x5294dc;
    if (arguments[4] != 0)
        name = 0x5294ec;
    run.call(0x4c7970, effect, {name});
    uint32_t table = run.get(effect + 0x6c);
    run.put(effect + 0x80, target);
    uint32_t method = run.get(table + 0x10);
    run.call(method, 0, {effect});
    return 1;
}

// 0x461a90. Per-frame logic of a hit burst. Fields: +0x08 flags, +0x6c logic
// table (state at +0x1c), +0x80 target, +0x158/+0x15c offset from target,
// +0x188 animation sub-object (+0x14 and +0x1c inside it), +0x4c/+0x50 position.
uint32_t function_461a90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t effect = arguments[0];
    uint32_t target = run.get(effect + 0x80);
    uint32_t table = run.get(effect + 0x6c);
    if (target == 0) {
        run.put(effect + 0x08, run.get(effect + 0x08) | 0x10000);
        return 0;
    }
    if ((run.get(target + 0x08) & 0x10000) != 0) {
        run.put(effect + 0x08, run.get(effect + 0x08) | 0x10000);
        return 0;
    }
    if (run.get(target + 0x38) == 0xffffffff) {
        run.put(effect + 0x08, run.get(effect + 0x08) | 0x10000);
        return 0;
    }
    uint32_t state = run.get(table + 0x1c);
    if (state == 0) {
        run.put(effect + 0x08, run.get(effect + 0x08) | 0x21);
        uint32_t value = run.call(0x4a3050, 0, {});
        int32_t choice = s32(value) % 3;
        uint32_t name = 0x529524;
        if (choice == 0)
            name = 0x5294fc;
        else if (choice == 1)
            name = 0x529524;
        else if (choice == 2)
            name = 0x529510;
        run.call(0x4c79e0, effect, {name, 0});
        uint32_t effectX = run.get(effect + 0x4c);
        uint32_t targetX = run.get(target + 0x4c);
        uint32_t effectY = run.get(effect + 0x50);
        run.put(effect + 0x158, effectX - targetX);
        uint32_t targetY = run.get(target + 0x50);
        run.put(effect + 0x15c, effectY - targetY);
        run.put(table + 0x1c, 5);
        return 1;
    }
    if (state != 5)
        return 1;
    uint32_t animation = effect + 0x188;
    run.call(0x4c82a0, animation, {run.get(0x5430c4)});
    if (run.get(animation + 0x1c) != 0) {
        if (run.get(animation + 0x14) == 0) {
            run.put(effect + 0x08, run.get(effect + 0x08) | 0x10000);
            return 0;
        }
    }
    uint32_t newX = run.get(target + 0x4c) + run.get(effect + 0x158);
    run.put(effect + 0x4c, newX);
    uint32_t newY = run.get(target + 0x50) + run.get(effect + 0x15c);
    run.put(effect + 0x50, newY);
    return 1;
}

// 0x461bc0. Per-frame logic of a splash effect. Same field layout as above.
uint32_t function_461bc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t effect = arguments[0];
    uint32_t table = run.get(effect + 0x6c);
    uint32_t state = run.get(table + 0x1c);
    if (state == 0) {
        run.put(effect + 0x08, run.get(effect + 0x08) | 0x21);
        run.call(0x4c79e0, effect, {0x5266ec, 0});
        run.call(0x4c7970, effect, {0x529538});
        run.put(table + 0x1c, 5);
        return 1;
    }
    if (state == 5) {
        uint32_t animation = effect + 0x188;
        run.call(0x4c82a0, animation, {run.get(0x5430c4)});
        if (run.get(animation + 0x1c) != 0) {
            if (run.get(animation + 0x14) == 0) {
                run.put(effect + 0x08, run.get(effect + 0x08) | 0x10000);
                return 0;
            }
        }
    }
    return 1;
}

// 0x461c40. Spawns a "Splash" effect through the owner's manager (+0x08).
uint32_t function_461c40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t owner = arguments[0];
    if (owner == 0)
        return 0;
    uint32_t manager = run.get(owner + 0x08);
    uint32_t effect = run.call(0x4c8da0, manager, {0, arguments[1], arguments[2], arguments[3], 0x522568, 0x40000});
    if (effect == 0)
        return 0;
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x461a00:
        return function_461a00(run, receiver, arguments);
    case 0x461a90:
        return function_461a90(run, receiver, arguments);
    case 0x461bc0:
        return function_461bc0(run, receiver, arguments);
    case 0x461c40:
        return function_461c40(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_effects_impact_01_entry, owned, body)
