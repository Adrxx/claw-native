// Level 1 pistol and magic bullets and enemy bullet logic
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
    case 0x40ff80:
        return 1;
    case 0x410040:
        return 1;
    case 0x410870:
        return 1;
    case 0x410900:
        return 1;
    case 0x410d60:
        return 0;
    case 0x4107c0:
        return 1;
    case 0x40fec0:
        return 1;
    default:
        return -1;
    }
}

uint32_t function_4107c0(Run &run, uint32_t receiver, uint32_t argument);

// Owner object fields used here: +0x0c scene, +0x6c logic state, +0x12c
// registry owner, +0x130 effect source. State fields: +0x18 object, +0x1c phase.
// Shared by the three logic callbacks (0x40fec0, 0x40ff80, 0x410040), which
// differ only in the allocation size and the constructor they run.
// Phase 0 builds the object, 0x1d and 0x1e call object methods, 0x3e8 does
// nothing and any other phase frees the object through 0x4dc870.
uint32_t function_410870(Run &run, uint32_t receiver, uint32_t argument);
uint32_t function_410900(Run &run, uint32_t receiver, uint32_t argument);

uint32_t construct(Run &run, uint32_t kind, uint32_t object, uint32_t owner) {
    switch (kind) {
    case 0x4107c0:
        return function_4107c0(run, object, owner);
    case 0x410870:
        return function_410870(run, object, owner);
    default:
        return function_410900(run, object, owner);
    }
}

uint32_t logicCallback(Run &run, uint32_t owner, uint32_t size, uint32_t kind) {
    uint32_t state = run.get(owner + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase > 0x1d) {
        if (phase == 0x1e) {
            uint32_t target = run.get(state + 0x18);
            run.vcall(target, 0x1c);
            return 1;
        }
        if (phase == 0x3e8)
            return 1;
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    if (phase == 0x1d) {
        uint32_t target = run.get(state + 0x18);
        run.vcall(target, 0x20);
        return 1;
    }
    if (phase != 0) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    run.put(state + 0x1c, 0x3e8);
    uint32_t memory = run.call(0x4f63ec, 0, {size});
    uint32_t built = 0;
    if (memory)
        built = construct(run, kind, memory, owner);
    run.vcall(built, 0x10);
    run.put(state + 0x18, built);
    return 1;
}

// 0x40ff80. cdecl, 1 stack argument, returns 1. Builds a 0x410870 object.
uint32_t function_40ff80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return logicCallback(run, arguments[0], 0x150, 0x410870);
}

// 0x410040. cdecl, 1 stack argument, returns 1. Builds a 0x410900 object.
uint32_t function_410040(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return logicCallback(run, arguments[0], 0x158, 0x410900);
}

// 0x40fec0. cdecl, 1 stack argument, returns 1. Builds a 0x4107c0 object.
uint32_t function_40fec0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return logicCallback(run, arguments[0], 0x150, 0x4107c0);
}

// Looks up the "GAME_BULLETS" entry: stores the current index at +0x16c and
// the indexed table entry (or 0 when out of range) at +0x174 of the registry
// owner at +0x12c. Shared tail of 0x4107c0 and 0x410870.
void selectBullet(Run &run, uint32_t object) {
    uint32_t owner = run.get(object + 0x12c);
    uint32_t table = run.get(owner + 0x170);
    if (!table)
        return;
    uint32_t index = run.get(table + 0x64);
    run.put(owner + 0x16c, index);
    uint32_t low = run.get(table + 0x64);
    uint32_t entry = 0;
    bool outside = s32(index) < s32(low);
    if (!outside)
        outside = s32(index) > s32(run.get(table + 0x68));
    if (!outside)
        entry = run.get(run.get(table + 0x14) + index * 4);
    run.put(owner + 0x174, entry);
}

// 0x4107c0. thiscall, 1 stack argument; returns the object.
uint32_t function_4107c0(Run &run, uint32_t receiver, uint32_t argument) {
    run.call(0x473c50, receiver, {argument});
    run.put(receiver, 0x50b714);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0);
    uint32_t owner = run.get(receiver + 0x12c);
    if (run.get(owner + 0x170) == 0) {
        run.call(0x4c7970, owner, {0x524130});
        selectBullet(run, receiver);
    }
    return receiver;
}

// 0x410870. thiscall, 1 stack argument; returns the object.
uint32_t function_410870(Run &run, uint32_t receiver, uint32_t argument) {
    function_4107c0(run, receiver, argument);
    run.put(receiver, 0x50b74c);
    uint32_t owner = run.get(receiver + 0x12c);
    run.call(0x4c7970, owner, {0x524130});
    selectBullet(run, receiver);
    return receiver;
}

// 0x410900. thiscall, 1 stack argument; returns the object. The incoming
// argument slot is reused as a local that receives the cycle value.
uint32_t function_410900(Run &run, uint32_t receiver, uint32_t argument) {
    function_4107c0(run, receiver, argument);
    run.put(receiver, 0x50b784);
    uint32_t owner = run.get(receiver + 0x12c);
    run.call(0x4c7970, owner, {0x52418c});
    uint32_t registry = run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x2c);
    uint32_t slot = run.automatic(4);
    run.put(slot, 0);
    run.call(0x4f6286, registry + 0x10, {0x52417c, slot});
    uint32_t cycle = run.get(slot);
    uint32_t scene = run.get(receiver + 0xc);
    run.put(receiver + 0x148, cycle);
    uint32_t flags = run.get(scene + 0x8);
    flags |= 0x80000;
    run.put(scene + 0x8, flags);
    if (run.get(0x53724c) == 0) {
        uint32_t world = run.get(0x5371fc);
        if (run.get(world + 0x124) != 0) {
            uint32_t source = run.get(receiver + 0x12c);
            uint32_t height = run.get(source + 0x64) - 1;
            uint32_t second = run.get(source + 0x50);
            uint32_t first = run.get(source + 0x4c);
            uint32_t factory = run.get(run.get(run.get(receiver + 0x130) + 0xc) + 0x8);
            uint32_t effect = run.call(0x4c8da0, factory, {0, first, second, height, 0x522e24, 0x40000});
            run.put(receiver + 0x154, effect);
            run.put(receiver + 0x150, 2);
            return receiver;
        }
    }
    run.put(receiver + 0x154, 0);
    run.put(receiver + 0x150, 1);
    return receiver;
}

// A random integer in [low, high] the way the original draws it: when the
// span wraps to zero a single bit of the draw picks an end.
uint32_t randomBetween(Run &run, uint32_t low, uint32_t high) {
    uint32_t span = high - low + 1;
    uint32_t draw = run.call(0x4a3050, 0);
    if (span == 0) {
        if (draw & 1)
            return low;
        return high;
    }
    if (span == 0xffffffffu)
        return low;
    int32_t remainder = s32(draw) % s32(span);
    return uint32_t(remainder) + low;
}

// 0x410d60. thiscall, no arguments, returns 0. Spawns +0x150 scatter effects
// around the point at +0x68/+0x70 (doubles) and then moves the effect at
// +0x154 there.
uint32_t function_410d60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x4742f0, receiver);
    uint32_t counter = 0;
    if (s32(run.get(receiver + 0x150)) > 0) {
        do {
            double originX = run.getd(receiver + 0x68);
            uint32_t scene = run.get(receiver + 0xc);
            uint32_t offsetX = randomBetween(run, run.get(scene + 0x118), run.get(scene + 0x120));
            double pointX = double(s32(offsetX)) + originX;
            uint32_t resultX = run.call_x87(0x4a30e0, 0, pointX);
            double originY = run.getd(receiver + 0x70);
            scene = run.get(receiver + 0xc);
            uint32_t offsetY = randomBetween(run, run.get(scene + 0x11c), run.get(scene + 0x124));
            scene = run.get(receiver + 0xc);
            double pointY = double(s32(offsetY)) + originY;
            uint32_t height = run.get(scene + 0x64) - 1;
            uint32_t resultY = run.call_x87(0x4a30e0, 0, pointY);
            uint32_t factory = run.get(run.get(run.get(receiver + 0x130) + 0xc) + 0x8);
            uint32_t effect = run.call(0x4c8da0, factory, {0, resultX, resultY, height, 0x522594, 0x40000});
            uint32_t method = run.get(run.get(effect + 0x6c) + 0x10);
            run.call(method, 0, {effect});
            counter += 1;
        } while (s32(counter) < s32(run.get(receiver + 0x150)));
    }
    uint32_t mover = run.get(receiver + 0x154);
    if (mover) {
        uint32_t movedX = run.call_x87(0x4a30e0, 0, run.getd(receiver + 0x68));
        run.put(mover + 0x4c, movedX);
        uint32_t movedY = run.call_x87(0x4a30e0, 0, run.getd(receiver + 0x70));
        uint32_t again = run.get(receiver + 0x154);
        run.put(again + 0x50, movedY);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40ff80:
        return function_40ff80(run, receiver, arguments);
    case 0x410040:
        return function_410040(run, receiver, arguments);
    case 0x410870:
        return function_410870(run, receiver, arguments[0]);
    case 0x410900:
        return function_410900(run, receiver, arguments[0]);
    case 0x410d60:
        return function_410d60(run, receiver, arguments);
    case 0x4107c0:
        return function_4107c0(run, receiver, arguments[0]);
    case 0x40fec0:
        return function_40fec0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_projectiles_01_entry, owned, body)
