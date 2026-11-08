// Crab Nest core and hatch states
//
// Recovered from the original v1.0 instructions in the family packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x432690:
        return 1;
    case 0x432a60:
        return 1;
    case 0x432c20:
        return 0;
    case 0x432c50:
        return 0;
    case 0x432d00:
        return 0;
    case 0x432d50:
        return 0;
    case 0x432dd0:
        return 0;
    default:
        return -1;
    }
}

uint32_t function_432c20(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_432d00(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_432dd0(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x432690. Dispatch the indexed state callback or query RTTI.
uint32_t function_432690(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[0];
    uint32_t slot = 0;
    for (uint32_t lookup = 0; lookup < 2; ++lookup) {
        uint32_t low = run.get(0x5372e0);
        run.put(0x5372f8, 0);
        if ((s32(index) < s32(low) || s32(index) > run.gets(0x5372e4)) &&
            !run.call(0x4db6e0, 0x5372d8, {index, 0})) {
            uint32_t error = run.get(0x544b4c);
            uint32_t code = run.call(0x4db5f0, 0);
            uint32_t callback = run.get(0x5372dc);
            run.put(0x544b14, code);
            run.call(0x4db4d0, callback, {0x5372d8, error, 0xc});
            slot = run.get(0x5372ec);
        } else {
            slot = (index - run.get(0x5372e0)) * run.get(0x5372f0) + run.get(0x5372e8);
        }
        if (!lookup && !run.get(slot)) {
            run.call(0x4a36f0, 0, {receiver});
            return 0;
        }
    }
    run.call(run.get(slot), receiver);
    return 0;
}

// 0x432a60. Owner pointers +0x08/+0x0c/+0x28/+0x2c and logic pointers
// +0x10/+0x30; +0x4c hatch animation, +0x48 sound, +0x50 triggered and
// +0x54 offspring published. Logic +0x2c/+0x30/+0x34/+0x38 are the nest
// rectangle and +0x64 is the signed crab count. Owner +0x4c/+0x50 are its
// position, +0x64 its level, +0x6c its logic, +0xd0/+0xd4 its display mode.
uint32_t function_432a60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t owner = arguments[0];
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x08, owner);
    run.put(receiver + 0x0c, owner);
    uint32_t logic = run.get(owner + 0x6c);
    run.put(receiver + 0x10, logic);
    run.put(receiver + 0x04, 0);
    run.call(0x4c7fa0, owner, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0x0c), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x28, owner);
    run.put(receiver + 0x2c, owner);
    run.put(receiver + 0x30, run.get(owner + 0x6c));
    run.put(receiver, 0x50c754);
    uint32_t output = run.automatic(0x04);
    uint32_t map = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x2c) + 0x10;
    run.put(output, 0);
    run.call(0x4f6286, map, {0x52668c, output});
    run.put(receiver + 0x4c, run.get(output));
    map = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x28) + 0x10;
    run.put(output, 0);
    run.call(0x4f6286, map, {0x526680, output});
    uint32_t sound = run.get(output);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x48, sound);
    logic = run.get(receiver + 0x10);
    run.put(receiver + 0x54, 0);
    if (!run.get(logic + 0x2c) && !run.get(logic + 0x34) && !run.get(logic + 0x30) && !run.get(logic + 0x38)) {
        uint32_t rect = run.automatic(-0x1c);
        run.call(0x4061e0, run.get(receiver + 0x2c), {rect});
        run.put(run.get(receiver + 0x10) + 0x2c, run.get(rect) + run.get(run.get(receiver + 0x0c) + 0x4c));
        run.put(run.get(receiver + 0x10) + 0x30, run.get(rect + 0x08) + run.get(run.get(receiver + 0x0c) + 0x4c));
        run.put(run.get(receiver + 0x10) + 0x34, run.get(rect + 0x04) + run.get(run.get(receiver + 0x0c) + 0x50));
        run.put(run.get(receiver + 0x10) + 0x38, run.get(rect + 0x0c) + run.get(run.get(receiver + 0x0c) + 0x50));
    }
    logic = run.get(receiver + 0x10);
    uint32_t count = run.get(logic + 0x64);
    if (!count) {
        run.put(logic + 0x64, 3);
    } else if (s32(count) > 9) {
        run.put(logic + 0x64, 9);
    }
    run.put(run.get(receiver + 0x2c) + 0xd0, 1);
    run.put(run.get(receiver + 0x2c) + 0xd4, 0x3000072);
    owner = run.get(receiver + 0x0c);
    if (!run.get(owner + 0x64)) {
        uint32_t flags = run.get(owner + 0x08);
        run.put(owner + 0x64, 1);
        run.put(owner + 0x08, flags | 0x20000);
    }
    function_432c20(run, receiver, nullptr);
    return receiver;
}

// 0x432c20. Save state at +0x24 and select idle.
uint32_t function_432c20(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523604});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    return 0;
}

// 0x432c50. Start hatching on eligible player overlap.
uint32_t function_432c50(Run &run, uint32_t receiver, const uint32_t *) {
    if (!run.get(receiver + 0x50)) {
        uint32_t player = run.get(0x537e88);
        uint32_t bottom = run.get(player + 0x124) + run.get(player + 0x50);
        uint32_t top = run.get(player + 0x11c) + run.get(player + 0x50);
        uint32_t right = run.get(player + 0x120) + run.get(player + 0x4c);
        uint32_t left = run.get(player + 0x118) + run.get(player + 0x4c);
        uint32_t rect = run.automatic(-0x20);
        run.put(rect + 0x0c, bottom);
        run.put(rect, left);
        run.put(rect + 0x04, top);
        run.put(rect + 0x08, right);
        uint32_t logic = run.get(receiver + 0x10);
        uint32_t nest = run.automatic(-0x10);
        run.put(nest + 0x04, run.get(logic + 0x34));
        run.put(nest, run.get(logic + 0x2c));
        run.put(nest + 0x08, run.get(logic + 0x30));
        run.put(nest + 0x0c, run.get(logic + 0x38));
        uint32_t mode = run.get(player + 0xcc);
        if (mode == 1 || mode == 2) {
            if (run.icall(0x546ce0, {rect, rect, nest}))
                function_432d00(run, receiver, nullptr);
        }
    }
    return 0;
}

// 0x432d00. Save state and animation, select hatch state and animation.
uint32_t function_432d00(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t logic = run.get(receiver + 0x10);
    run.put(receiver + 0x50, 1);
    run.put(receiver + 0x24, run.get(logic + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52665c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t owner = run.get(receiver + 0x2c);
    uint32_t animation = run.get(receiver + 0x4c);
    run.put(receiver + 0x34, run.get(owner + 0x190));
    run.call(0x4c8220, owner + 0x188, {animation});
    return 0;
}

// 0x432d50. Tick hatch animation and publish offspring once at frame two.
uint32_t function_432d50(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    if (run.get(run.get(receiver + 0x2c) + 0x16c) == 2 && !run.get(receiver + 0x54)) {
        uint32_t sound = run.get(receiver + 0x48);
        if (sound && run.get(0x532c0c))
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
        function_432dd0(run, receiver, nullptr);
        run.put(receiver + 0x54, 1);
    }
    uint32_t animation = run.get(receiver + 0x2c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14))
        function_432c20(run, receiver, nullptr);
    return 0;
}

// 0x432dd0. Hatch crabs and distribute treasure in original slot order.
uint32_t function_432dd0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t treasure[9];
    treasure[0] = run.get(run.get(receiver + 0x0c) + 0x100);
    uint32_t logic = run.get(receiver + 0x10);
    treasure[1] = run.get(logic + 0xf0);
    treasure[2] = run.get(logic + 0xf8);
    treasure[3] = run.get(logic + 0xf4);
    treasure[4] = run.get(logic + 0xfc);
    treasure[5] = run.get(logic + 0x100);
    treasure[6] = run.get(logic + 0x108);
    treasure[7] = run.get(logic + 0x104);
    treasure[8] = run.get(logic + 0x10c);
    uint32_t remaining = 0;
    for (uint32_t value : treasure)
        remaining += value != 0;
    uint32_t crabs = run.get(logic + 0x64);
    uint32_t loops = s32(remaining) > s32(crabs) ? remaining : crabs;
    uint32_t cursor = 0;
    uint32_t speed = uint32_t(s32(loops * uint32_t(-50)) / 2);
    while (s32(loops) > 0) {
        uint32_t vertical = 0u - (uint32_t(s32(run.call(0x4a3050, 0)) % 201) + 200u);
        if (s32(crabs) > 0 && !run.get(run.get(receiver + 0x10) + 0x68)) {
            uint32_t owner = run.get(receiver + 0x2c);
            uint32_t scene = run.get(run.get(receiver + 0x30) + 0x0c);
            uint32_t crab = run.call(0x4c8da0, run.get(scene + 0x08), {0, run.get(owner + 0x4c), run.get(owner + 0x50), run.get(owner + 0x64) - 1, 0x522bac, 0x40000});
            run.call(run.get(run.get(crab + 0x6c) + 0x10), 0, {crab});
            uint32_t direction = s32(run.call(0x4a3050, 0)) % 100 < 50;
            uint32_t horizontal = speed;
            if (crabs == 1)
                horizontal = uint32_t(s32(run.call(0x4a3050, 0)) % 401) - 200u;
            run.putd(run.get(run.get(crab + 0x6c) + 0x18) + 0x50, double(s32(horizontal)));
            run.putd(run.get(run.get(crab + 0x6c) + 0x18) + 0x58, double(s32(vertical)));
            uint32_t state = run.get(run.get(crab + 0x6c) + 0x18);
            run.put(state + 0x40, 0);
            run.put(state + 0x44, 0x40890000);
            run.vcall(run.get(run.get(crab + 0x6c) + 0x18), 0x4c);
            run.call(0x44acd0, run.get(run.get(crab + 0x6c) + 0x18), {direction});
            if (s32(remaining) > 0 && s32(cursor) < 9) {
                run.put(crab + 0x100, treasure[cursor]);
                ++cursor;
                --remaining;
            }
            --crabs;
        } else if (s32(remaining) > 0 && s32(cursor) < 9) {
            uint32_t value = treasure[cursor++];
            uint32_t owner = run.get(receiver + 0x0c);
            run.call(0x40f450, 0, {run.get(owner + 0x0c), value, run.get(owner + 0x4c), run.get(owner + 0x50), run.get(owner + 0x64), speed, vertical});
            --remaining;
        }
        speed += 50;
        --loops;
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x432690:
        return function_432690(run, receiver, arguments);
    case 0x432a60:
        return function_432a60(run, receiver, arguments);
    case 0x432c20:
        return function_432c20(run, receiver, arguments);
    case 0x432c50:
        return function_432c50(run, receiver, arguments);
    case 0x432d00:
        return function_432d00(run, receiver, arguments);
    case 0x432d50:
        return function_432d50(run, receiver, arguments);
    case 0x432dd0:
        return function_432dd0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_crab_nest_core_entry, owned, body)
