// Level 12 shake state, recovered from the original v1.0 instructions.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x488870:
    case 0x4889e0:
        return 1;
    case 0x488c90:
    case 0x488cd0:
    case 0x488cf0:
        return 0;
    default:
        return -1;
    }
}

// 0x488870. Construct the Shake state and make its rectangle object-relative.
uint32_t function_488870(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x08, object); // Base owner and resource owner.
    run.put(receiver + 0x0c, object);
    uint32_t owner = run.get(object + 0x6c);
    run.put(receiver + 0x10, owner); // State-bearing owner.
    run.put(receiver + 0x04, 0);
    run.call(0x4c7fa0, object, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0x0c), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x28, object);
    run.put(receiver + 0x2c, object); // Placed object.
    run.put(receiver + 0x30, run.get(object + 0x6c));
    run.put(receiver + 0x4c, 0); // Timer origin and duration.
    run.put(receiver + 0x50, 0);
    run.put(receiver, 0x50f63c);
    uint32_t placed = run.get(receiver + 0x2c);
    run.put(placed + 0x08, run.get(placed + 0x08) | 4);
    run.put(run.get(receiver + 0x2c) + 0xd0, 1);
    run.put(run.get(receiver + 0x2c) + 0xd8, 2);
    uint32_t source = run.get(receiver + 0x0c);
    uint32_t x = run.get(source + 0x4c);
    uint32_t right = run.get(source + 0x140);
    uint32_t y = run.get(source + 0x50);
    uint32_t bottom = run.get(source + 0x144);
    right -= x;
    uint32_t top = run.get(source + 0x13c);
    uint32_t left = run.get(source + 0x138);
    bottom -= y;
    top -= y;
    left -= x;
    placed = run.get(receiver + 0x2c);
    run.put(placed + 0x138, left);
    run.put(placed + 0x13c, top);
    run.put(placed + 0x140, right);
    run.put(placed + 0x144, bottom);
    run.put(receiver + 0x48, 0); // Selected earthquake sound resource.
    return receiver;
}

// 0x4889e0. Resolve the callback slot, growing the original table as needed.
uint32_t function_4889e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[0];
    uint32_t lower = run.get(0x53c2a8);
    run.put(0x53c2c0, 0);
    uint32_t slot;
    if (s32(index) < s32(lower) || s32(index) > s32(run.get(0x53c2ac))) {
        uint32_t grown = run.call(0x4db6e0, 0x53c2a0, {index, 0});
        if (!grown) {
            uint32_t context = run.get(0x544b4c);
            uint32_t location = run.call(0x4db5f0, 0);
            uint32_t error = run.get(0x53c2a4);
            run.put(0x544b14, location);
            run.call(0x4db4d0, error, {0x53c2a0, context, 0x0c});
            slot = run.get(0x53c2b4);
            lower = run.get(0x53c2a8);
        } else {
            lower = run.get(0x53c2a8);
            slot = (index - lower) * run.get(0x53c2b8) + run.get(0x53c2b0);
        }
    } else {
        slot = (index - lower) * run.get(0x53c2b8) + run.get(0x53c2b0);
    }
    if (!run.get(slot)) {
        run.call(0x4a36f0, 0, {receiver});
        return 0;
    }
    run.put(0x53c2c0, 0);
    if (s32(index) < s32(lower) || s32(index) > s32(run.get(0x53c2ac))) {
        uint32_t grown = run.call(0x4db6e0, 0x53c2a0, {index, 0});
        if (!grown) {
            uint32_t context = run.get(0x544b4c);
            uint32_t location = run.call(0x4db5f0, 0);
            uint32_t error = run.get(0x53c2a4);
            run.put(0x544b14, location);
            run.call(0x4db4d0, error, {0x53c2a0, context, 0x0c});
            slot = run.get(0x53c2b4);
            run.call(run.get(slot), receiver);
            return 0;
        }
        lower = run.get(0x53c2a8);
    }
    slot = (index - lower) * run.get(0x53c2b8) + run.get(0x53c2b0);
    run.call(run.get(slot), receiver);
    return 0;
}

// 0x488c90. Save the current state and enter LS_WAIT for seven seconds.
uint32_t function_488c90(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t owner = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(owner + 0x1c)); // Previous state.
    uint32_t state = run.call(0x4dba00, 0x537668, {0x529a48});
    owner = run.get(receiver + 0x10);
    run.put(owner + 0x1c, state);
    run.put(receiver + 0x50, 0x1b58);
    run.put(receiver + 0x4c, run.get(0x537210));
    return 0;
}

// 0x488cd0. Clear the active bit once the unsigned elapsed time expires.
uint32_t function_488cd0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x4c);
    if (elapsed >= run.get(receiver + 0x50)) {
        uint32_t placed = run.get(receiver + 0x2c);
        run.put(placed + 0x08, run.get(placed + 0x08) & 0xfffffffeu);
    }
    return 0;
}

// 0x488cf0. Activate shake, enter wait, and optionally play an earthquake.
uint32_t function_488cf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t placed = run.get(receiver + 0x2c);
    run.put(placed + 0x08, run.get(placed + 0x08) | 1);
    run.call(0x486e70, 0, {0x1388});
    function_488c90(run, receiver, arguments);
    int32_t selection = s32(run.call(0x4a3050, 0)) % 6;
    uint32_t name = 0;
    switch (selection) {
    case 1:
        name = 0x523574;
        break;
    case 2:
        name = 0x523560;
        break;
    case 3:
        name = 0x52354c;
        break;
    case 4:
        name = 0x523538;
        break;
    case 5:
        name = 0x523524;
        break;
    default:
        break;
    }
    if (name) {
        placed = run.get(receiver + 0x2c);
        uint32_t owner = run.get(placed + 0x0c);
        uint32_t local = run.automatic(-4);
        run.put(local, 0);
        uint32_t map = run.get(owner + 0x28) + 0x10;
        run.call(0x4f6286, map, {name, local});
        run.put(receiver + 0x48, run.get(local));
    }
    uint32_t sound = run.get(receiver + 0x48);
    if (sound) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t audioArgument = run.get(0x532c10);
        if (enabled)
            run.call(0x4b45f0, run.get(sound + 0x10), {audioArgument, 0, 0, 0});
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x488870:
        return function_488870(run, receiver, arguments);
    case 0x4889e0:
        return function_4889e0(run, receiver, arguments);
    case 0x488c90:
        return function_488c90(run, receiver, arguments);
    case 0x488cd0:
        return function_488cd0(run, receiver, arguments);
    case 0x488cf0:
        return function_488cf0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_twelve_shake_state_entry, owned, body)
