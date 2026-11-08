// Level 13 Red Tail wind and spikes, recovered from original v1.0 entries.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4843d0:
    case 0x484680:
    case 0x4848d0:
    case 0x484ca0:
    case 0x484f60:
        return 1;
    case 0x484db0:
    case 0x484e10:
    case 0x484e30:
    case 0x484ea0:
    case 0x484f00:
    case 0x484fa0:
        return 0;
    default:
        return -1;
    }
}

// 0x4843d0 and 0x4848d0. Table +0x08/+0x0c are signed bounds,
// +0x10 data, +0x14 fallback, +0x18 stride and +0x20 growth extent.
uint32_t lookup(Run &run, uint32_t table, uint32_t index, uint32_t lower) {
    if (s32(index) < s32(lower) || s32(index) > s32(run.get(table + 0x0c))) {
        uint32_t grown = run.call(0x4db6e0, table, {index, 0});
        if (!grown) {
            uint32_t text = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            uint32_t handler = run.get(table + 0x04);
            run.put(0x544b14, error);
            run.call(0x4db4d0, handler, {table, text, 0x0c});
            return run.get(table + 0x14);
        }
        lower = run.get(table + 0x08);
    }
    return run.get(table + 0x10) + (index - lower) * run.get(table + 0x18);
}

uint32_t dispatchState(Run &run, uint32_t receiver, uint32_t index, uint32_t table) {
    uint32_t lower = run.get(table + 0x08);
    run.put(table + 0x20, 0);
    uint32_t slot = lookup(run, table, index, lower);
    if (run.get(slot)) {
        lower = run.get(table + 0x08);
        run.put(table + 0x20, 0);
        slot = lookup(run, table, index, lower);
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x4a36f0, 0, {receiver});
    }
    return 0;
}

// Shared constructor prefix. +0x08/+0x0c host object, +0x10 scene,
// +0x14..+0x20 state storage and +0x28..+0x30 derived references.
void initializeLogic(Run &run, uint32_t receiver, uint32_t object) {
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x08, object);
    run.put(receiver + 0x0c, object);
    uint32_t scene = run.get(object + 0x6c);
    run.put(receiver + 0x10, scene);
    run.put(receiver + 0x04, 0);
    run.call(0x4c7fa0, object, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0x0c), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x28, object);
    run.put(receiver + 0x2c, object);
    run.put(receiver + 0x30, run.get(object + 0x6c));
}

// 0x484680. Installs spikes and derives optional bounds.
uint32_t constructSpikes(Run &run, uint32_t receiver, uint32_t object) {
    initializeLogic(run, receiver, object);
    run.put(receiver, 0x50f444);
    run.put(run.get(receiver + 0x2c) + 0xd0, 4);
    run.put(run.get(receiver + 0x2c) + 0xd4, 1);
    uint32_t host = run.get(receiver + 0x2c);
    uint32_t bounds = run.get(host + 0x174);
    if (bounds) {
        run.put(host + 0x138, run.get(bounds + 0x20) - run.get(bounds + 0x18));
        run.put(host + 0x13c, run.get(bounds + 0x24) - run.get(bounds + 0x1c));
        run.put(host + 0x140, run.get(bounds + 0x20) + run.get(bounds + 0x18) - 1);
        run.put(host + 0x144, run.get(bounds + 0x24) + run.get(bounds + 0x1c) - 1);
    }
    run.put(run.get(receiver + 0x0c) + 0x104, 0x14);
    host = run.get(receiver + 0x0c);
    double duration = double(s32(run.get(host + 0x104))) * double(run.getf(0x5262b0));
    uint32_t converted = run.call_x87(0x4a30e0, 0, duration);
    run.put(host + 0x104, converted);
    run.call(0x432c20, receiver);
    return receiver;
}

// Original sound methods publish pointers to their own stack locals. Keep the
// callee's actual entry ESP so callbacks see the same guest pointers.
uint32_t soundCall(Run &run, uint32_t function, uint32_t receiver,
                   int32_t offset, std::initializer_list<uint32_t> arguments = {}) {
    uint32_t previous = run.stackPointer;
    run.stackPointer = run.automatic(offset);
    uint32_t result = run.call(function, receiver, arguments);
    run.stackPointer = previous;
    return result;
}

// 0x484db0. Enter idle and clear boss +0x4e4 request.
uint32_t enterIdle(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523604});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t sound = run.get(receiver + 0x48);
    if (sound && soundCall(run, 0x4b3e70, run.get(sound + 0x10), -0x08)) {
        sound = run.get(receiver + 0x48);
        soundCall(run, 0x4b3fe0, run.get(sound + 0x10), -0x14, {0, 0x2ee, 0});
    }
    uint32_t boss = run.get(0x53c19c);
    if (boss) {
        run.put(boss + 0x4e4, 0);
    }
    return 0;
}

// 0x484ca0. Wind +0x48 is sound; +0x4c..+0x58 clocks and intervals.
uint32_t constructWind(Run &run, uint32_t receiver, uint32_t object) {
    initializeLogic(run, receiver, object);
    run.put(receiver + 0x4c, 0);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver, 0x50f46c);
    uint32_t result = run.automatic(0x04);
    run.put(result, 0);
    uint32_t host = run.get(receiver + 0x2c);
    run.put(host + 0x40, run.get(host + 0x40) | 1);
    host = run.get(receiver + 0x2c);
    uint32_t resources = run.get(run.get(host + 0x0c) + 0x28);
    run.call(0x4f6286, resources + 0x10, {0x52bb4c, result});
    run.put(receiver + 0x48, run.get(result));
    uint32_t frame = run.frame;
    run.frame -= 0x20;
    enterIdle(run, receiver);
    run.frame = frame;
    return receiver;
}

// 0x484e30. Capture activation clock and duration before audio callbacks.
uint32_t enterBlow(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52bb28});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    run.put(receiver + 0x50, run.get(0x52b350));
    run.put(receiver + 0x4c, run.get(0x537210));
    uint32_t sound = run.get(receiver + 0x48);
    if (sound) {
        if (run.get(0x532c0c)) {
            soundCall(run, 0x4b3dc0, run.get(sound + 0x10), -0x18, {0x19, 0, 0, 1});
        }
        sound = run.get(receiver + 0x48);
        soundCall(run, 0x4b3fe0, run.get(sound + 0x10), -0x14, {0x50, 0x3e8, 0});
    }
    return 0;
}

// 0x484e10. Remain idle until boss publishes its request.
uint32_t idle(Run &run, uint32_t receiver) {
    uint32_t boss = run.get(0x53c19c);
    if (boss && run.get(boss + 0x4e4)) {
        uint32_t frame = run.frame;
        run.frame -= 0x04;
        enterBlow(run, receiver);
        run.frame = frame;
    }
    return 0;
}

// 0x484f00. Win32 takes POINT by value following RECT pointer.
uint32_t containsPlayer(Run &run) {
    uint32_t player = run.get(0x537e88);
    uint32_t bottom = run.get(0x52b360);
    uint32_t left = run.get(0x52b354);
    uint32_t x = run.get(player + 0x4c);
    uint32_t y = run.get(player + 0x50);
    uint32_t right = run.get(0x52b358);
    uint32_t top = run.get(0x52b35c);
    uint32_t rect = run.automatic(-0x10);
    run.put(rect, left);
    run.put(rect + 0x04, top);
    run.put(rect + 0x08, right);
    run.put(rect + 0x0c, bottom);
    return run.icall(0x546cd4, {rect, x, y}) ? 1 : 0;
}

// 0x484f60. Player logic +0x14 is movement, movement +0x84 is wind.
uint32_t applyWind(Run &run, uint32_t clear) {
    uint32_t player = run.get(0x537e88);
    uint32_t logic = run.get(player + 0x6c);
    uint32_t movement = run.get(logic + 0x14);
    if (movement) {
        if (clear) {
            run.put(movement + 0x84, 0);
        } else {
            run.put(movement + 0x84, run.get(0x52b34c));
        }
    }
    return movement;
}

// 0x484fa0. Create debris at original cadence and randomize motion.
void spawnDebris(Run &run, uint32_t receiver) {
    uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x54);
    if (elapsed < run.get(receiver + 0x58)) {
        return;
    }
    uint32_t x = uint32_t(s32(run.call(0x4a3050, 0)) % 0x65) + 0x93a8;
    uint32_t y = uint32_t(s32(run.call(0x4a3050, 0)) % 0xb5) + 0x780;
    uint32_t z = uint32_t(s32(run.call(0x4a3050, 0)) % 0x2711);
    uint32_t scene = run.get(receiver + 0x10);
    uint32_t factory = run.get(run.get(scene + 0x0c) + 0x08);
    uint32_t debris = run.call(0x4c8da0, factory, {0, x, y, z, 0x522a1c, 0x40000});
    if (debris) {
        uint32_t logic = run.get(debris + 0x6c);
        run.call(run.get(logic + 0x10), 0, {debris});
        uint32_t factor = uint32_t(s32(run.call(0x4a3050, 0)) % 0x65) + 0x64;
        uint32_t horizontal = uint32_t(s32(run.get(0x52b34c) * factor) / 100);
        uint32_t vertical = uint32_t(s32(run.call(0x4a3050, 0)) % 0x5b) + 0x0a;
        if (s32(run.call(0x4a3050, 0)) % 0x65 >= 0x32) {
            vertical = 0 - vertical;
        }
        logic = run.get(debris + 0x6c);
        uint32_t motion = run.get(logic + 0x18);
        run.put(motion + 0x58, 0);
        run.putd(motion + 0x50, double(s32(horizontal)));
        run.put(motion + 0x60, 0);
        run.put(motion + 0x5c, 0);
        run.put(motion + 0x64, 0);
        logic = run.get(debris + 0x6c);
        run.putd(run.get(logic + 0x18) + 0x40, double(s32(vertical)));
        logic = run.get(debris + 0x6c);
        run.put(run.get(logic + 0x18) + 0x1a0, 0x8e94);
    }
    run.put(receiver + 0x58, 0x64);
    run.put(receiver + 0x54, run.get(0x537210));
}

// 0x484ea0. Continue while both duration and boss request remain live.
uint32_t blow(Run &run, uint32_t receiver) {
    spawnDebris(run, receiver);
    uint32_t frame = run.frame;
    run.frame -= 0x08;
    uint32_t contains = containsPlayer(run);
    run.frame = frame;
    applyWind(run, contains ? 0 : 1);
    uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x4c);
    if (elapsed >= run.get(receiver + 0x50) || !run.get(run.get(0x53c19c) + 0x4e4)) {
        applyWind(run, 1);
        run.frame -= 0x08;
        enterIdle(run, receiver);
        run.frame = frame;
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4843d0:
        return dispatchState(run, receiver, arguments[0], 0x53c1d8);
    case 0x484680:
        return constructSpikes(run, receiver, arguments[0]);
    case 0x4848d0:
        return dispatchState(run, receiver, arguments[0], 0x53c208);
    case 0x484ca0:
        return constructWind(run, receiver, arguments[0]);
    case 0x484db0:
        return enterIdle(run, receiver);
    case 0x484e10:
        return idle(run, receiver);
    case 0x484e30:
        return enterBlow(run, receiver);
    case 0x484ea0:
        return blow(run, receiver);
    case 0x484f00:
        return containsPlayer(run);
    case 0x484f60:
        return applyWind(run, arguments[0]);
    case 0x484fa0:
        spawnDebris(run, receiver);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_thirteen_red_tail_wind_spikes_01_entry, owned, body)
