// Level 12 Aquatis dynamite
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
    case 0x406ef0:
        return 1;
    case 0x4071a0:
        return 1;
    case 0x4072f0:
        return 0;
    case 0x407310:
        return 0;
    case 0x407360:
        return 0;
    default:
        return -1;
    }
}

uint32_t function_407360(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4072f0(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x406ef0. Dispatches the dynamite state's registered callback.
uint32_t function_406ef0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t index = arguments[0];
    uint32_t lower = run.get(0x5348c0);
    run.put(0x5348d8, 0);
    uint32_t slot;
    bool found = true;
    if (s32(index) < s32(lower) || s32(index) > s32(run.get(0x5348c4))) {
        found = run.call(0x4db6e0, 0x5348b8, {index, 0}) != 0;
        if (found)
            lower = run.get(0x5348c0);
    }
    if (found) {
        slot = (index - lower) * run.get(0x5348d0) + run.get(0x5348c8);
    } else {
        const uint32_t error = run.get(0x544b4c);
        const uint32_t code = run.call(0x4db5f0, 0, {});
        const uint32_t handler = run.get(0x5348bc);
        run.put(0x544b14, code);
        run.call(0x4db4d0, handler, {0x5348b8, error, 0xc});
        slot = run.get(0x5348cc);
        lower = run.get(0x5348c0);
    }
    if (run.get(slot) == 0) {
        run.call(0x4a36f0, 0, {receiver});
        return 0;
    }
    run.put(0x5348d8, 0);
    found = true;
    if (s32(index) < s32(lower) || s32(index) > s32(run.get(0x5348c4))) {
        found = run.call(0x4db6e0, 0x5348b8, {index, 0}) != 0;
        if (found)
            lower = run.get(0x5348c0);
    }
    if (found) {
        slot = (index - lower) * run.get(0x5348d0) + run.get(0x5348c8);
    } else {
        const uint32_t error = run.get(0x544b4c);
        const uint32_t code = run.call(0x4db5f0, 0, {});
        const uint32_t handler = run.get(0x5348bc);
        run.put(0x544b14, code);
        run.call(0x4db4d0, handler, {0x5348b8, error, 0xc});
        slot = run.get(0x5348cc);
    }
    run.call(run.get(slot), receiver, {});
    return 0;
}

// 0x4071a0. Constructs the dynamite state and starts its initial attack.
uint32_t function_4071a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t owner = arguments[0];
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x8, owner); // Base owner.
    run.put(receiver + 0xc, owner); // Game object.
    const uint32_t context = run.get(owner + 0x6c); // Object level context.
    run.put(receiver + 0x10, context); // Base context.
    run.put(receiver + 0x4, 0); // State flags.
    run.call(0x4c7fa0, owner, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0xc), {0x522d48});
    run.put(receiver + 0x14, 0); // Base state storage.
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9); // State identifier.
    run.put(receiver + 0x20, 2); // State mode.
    run.put(receiver + 0x28, owner); // Derived owner.
    run.put(receiver + 0x2c, owner); // Sprite object.
    run.put(receiver + 0x30, run.get(owner + 0x6c)); // Derived level context.
    run.put(receiver + 0x4c, 0); // Last attack tick.
    run.put(receiver + 0x50, 0); // Attack interval.
    run.put(receiver, 0x50b244);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x5235d0});
    uint32_t object = run.get(receiver + 0x2c);
    run.put(object + 0x40, run.get(object + 0x40) | 1); // Sprite flags.
    run.put(run.get(receiver + 0x2c) + 0xd0, 1); // Object property.
    run.put(run.get(receiver + 0x2c) + 0xd4, 0x1000000); // Object mask.
    object = run.get(receiver + 0xc);
    run.put(object + 0x8, run.get(object + 0x8) | 2); // Object flags.
    run.put(run.get(receiver + 0xc) + 0x128, run.get(run.get(receiver + 0x10) + 0x2c)); // Rectangle left.
    run.put(run.get(receiver + 0xc) + 0x12c, run.get(run.get(receiver + 0x10) + 0x34)); // Rectangle top.
    run.put(run.get(receiver + 0xc) + 0x130, run.get(run.get(receiver + 0x10) + 0x30)); // Rectangle right.
    run.put(run.get(receiver + 0xc) + 0x134, run.get(run.get(receiver + 0x10) + 0x38)); // Rectangle bottom.
    run.put(receiver + 0x48, 0); // Saved player health.
    const uint32_t player = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (player != 0)
        run.put(receiver + 0x48, run.get(player + 0x78));
    function_4072f0(run, receiver, nullptr);
    return receiver;
}

// 0x4072f0. Initial attack and base state initialization.
uint32_t function_4072f0(Run &run, uint32_t receiver, const uint32_t *) {
    function_407360(run, receiver, nullptr);
    run.call(0x465450, receiver, {});
    return 0;
}

// 0x407310. Timed attack update.
uint32_t function_407310(Run &run, uint32_t receiver, const uint32_t *) {
    const uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x4c);
    if (elapsed >= run.get(receiver + 0x50)) {
        const uint32_t boss = run.get(0x534874);
        if (boss != 0 && run.get(boss + 0x4b8) != 0 && run.get(boss + 0x4c8) == 0)
            function_407360(run, receiver, nullptr);
        run.put(receiver + 0x50, 0x2ee);
        run.put(receiver + 0x4c, run.get(0x537210));
    }
    return 0;
}

// 0x407360. Spawn dynamite unless the player's health has increased.
uint32_t function_407360(Run &run, uint32_t receiver, const uint32_t *) {
    const uint32_t player = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (player != 0) {
        const uint32_t health = run.get(player + 0x78); // Current player health.
        if (s32(health) > s32(run.get(receiver + 0x48)))
            return 0;
        run.put(receiver + 0x48, health);
    }
    const uint32_t boss = run.get(0x534874);
    if (boss != 0)
        run.put(boss + 0x4c8, 1); // Attack active flag.
    const uint32_t object = run.get(receiver + 0xc);
    const uint32_t context = run.get(receiver + 0x30);
    const uint32_t y = run.get(object + 0x50); // Object Y coordinate.
    const uint32_t x = run.get(object + 0x4c); // Object X coordinate.
    const uint32_t factory = run.get(run.get(context + 0xc) + 0x8);
    const uint32_t spawned = run.call(0x4c8da0, factory, {0, x, y, 0x3e8, 0x522894, 0x40000});
    if (spawned != 0) {
        run.call(0x4c7970, spawned, {0x5235d0});
        run.put(spawned + 0x108, 1); // Spawned object dynamite flag.
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x406ef0:
        return function_406ef0(run, receiver, arguments);
    case 0x4071a0:
        return function_4071a0(run, receiver, arguments);
    case 0x4072f0:
        return function_4072f0(run, receiver, arguments);
    case 0x407310:
        return function_407310(run, receiver, arguments);
    case 0x407360:
        return function_407360(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_twelve_aquatis_dynamite_01_entry, owned, body)
