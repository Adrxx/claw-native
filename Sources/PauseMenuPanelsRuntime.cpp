// Pause menu panel build and draw
//
// Recovered from the decompile and the disassembly of 0x451680, 0x4520f0 and
// 0x452290.
#include "ClawRuntime.hpp"

#include <cmath>

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x451680:
        return 1;
    case 0x4520f0:
        return 2;
    case 0x452290:
        return 2;
    default:
        return -1;
    }
}

uint32_t function_4520f0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_452290(Run &run, uint32_t receiver, const uint32_t *arguments);

// Sets the callee-entry ESP for the next outside call. `below` is the byte
// distance under this function's entry frame, including the return word.
void enter(Run &run, uint32_t below) {
    run.stackPointer = run.frame - below;
}

// Runs an owned function with the frame it has when called from here. The
// original pushes the arguments and the return address before the call.
uint32_t owned_call(Run &run, uint32_t below, uint32_t returnAddress,
                    uint32_t (*function)(Run &, uint32_t, const uint32_t *), uint32_t receiver,
                    uint32_t first, uint32_t second) {
    uint32_t saved = run.frame;
    run.frame = saved - below;
    run.put(run.frame, returnAddress);
    run.put(run.frame + 4, first);
    run.put(run.frame + 8, second);
    uint32_t arguments[2] = {first, second};
    uint32_t result = function(run, receiver, arguments);
    run.frame = saved;
    return result;
}

// The __ftol at 0x4a30e0: truncates toward zero through a 64-bit store and
// returns the low word (an out-of-range value stores the integer indefinite).
uint32_t truncate(double value) {
    if (std::isnan(value))
        return 0;
    if (value >= 9223372036854775808.0 || value < -9223372036854775808.0)
        return 0;
    return uint32_t(uint64_t(int64_t(value)));
}

// 0x4f6286 click lookup shared by all three functions: when the sound
// owner's +0x30 is zero, plays the GAME_CLICK sound if it resolves.
// `slot` is the guest address of the out word the lookup fills.
void click(Run &run, uint32_t owner, uint32_t slot, uint32_t below, uint32_t pushed) {
    enter(run, below);
    run.call(0x4f6286, owner + 0x10, {0x524678, slot});
    uint32_t sound = run.get(slot);
    if (sound != 0) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t volume = run.get(0x532c10);
        if (enabled != 0) {
            enter(run, pushed);
            run.call(0x4b45f0, run.get(sound + 0x10), {volume, 0, 0, 0});
        }
    }
}

// 0x451680. Positions the arrow buttons for the selected panel, then rebuilds
// it. +0x0c owner, +0x154 panel list, +0x258/+0x25c arrow widgets
// (+0x4c x, +0x50 y), +0x278/+0x280 anchors, +0x298 current panel.
uint32_t function_451680(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t panel = arguments[0];
    enter(run, 0x1c);
    run.call(0x451770, receiver, {panel});
    uint32_t list = receiver + 0x154;
    uint32_t owner = run.get(receiver + 0x0c);
    uint32_t group = run.get(owner + 0x04);
    uint32_t holder = run.get(group + 0x14);
    uint32_t key = run.get(holder + 0x2c);
    enter(run, 0x1c);
    run.call(0x4dd270, list, {key});
    enter(run, 0x18);
    uint32_t iterator = run.call(0x4dd480, list);
    enter(run, 0x1c);
    uint32_t node = run.call(0x4dd450, list, {iterator});
    if (node != 0) {
        // local_8 at entry-8 is x, local_4 at entry-4 is y
        enter(run, 0x1c);
        run.call(0x4ded20, node, {run.automatic(-8)});
        uint32_t left = run.get(receiver + 0x278);
        uint32_t widget = run.get(receiver + 0x258);
        run.put(widget + 0x4c, left - 0x1e);
        uint32_t y = run.get(run.automatic(-4));
        widget = run.get(receiver + 0x258);
        run.put(widget + 0x50, y + 0x11);
        uint32_t right = run.get(receiver + 0x280);
        widget = run.get(receiver + 0x25c);
        run.put(widget + 0x4c, right + 0x1e);
        y = run.get(run.automatic(-4));
        widget = run.get(receiver + 0x25c);
        run.put(widget + 0x50, y + 0x11);
    }
    enter(run, 0x1c);
    run.call(0x451900, receiver, {panel});
    if (panel == 0x59db) {
        owned_call(run, 0x20, 0x45172d, function_452290, receiver, 0, 0x5aa1);
        owned_call(run, 0x20, 0x45173b, function_452290, receiver, 0, 0x5aa4);
        run.put(receiver + 0x298, panel);
        return 0;
    }
    if (panel == 0x59da)
        owned_call(run, 0x20, 0x451760, function_4520f0, receiver, 0, 0x5b06);
    run.put(receiver + 0x298, panel);
    return 0;
}

// 0x4520f0. Steps the level slider (panel item 0x5b06): param_1 is the step
// (1 up, 2 down, other none), param_2 the item id. Stack slots: entry+4
// param_1, entry+8 param_2.
uint32_t function_4520f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t step = arguments[0];
    uint32_t item = arguments[1];
    // table of ten x offsets at entry-0x28
    run.put(run.automatic(-0x28), 0x15c);
    run.put(run.automatic(-0x24), 0x16e);
    run.put(run.automatic(-0x20), 0x182);
    run.put(run.automatic(-0x1c), 0x196);
    run.put(run.automatic(-0x18), 0x1aa);
    run.put(run.automatic(-0x14), 0x1be);
    run.put(run.automatic(-0x10), 0x1d2);
    run.put(run.automatic(-0x0c), 0x1e6);
    run.put(run.automatic(-0x08), 0x1fa);
    run.put(run.automatic(-0x04), 0x20e);
    enter(run, 0x4c);
    uint32_t found = run.call(0x4dd020, receiver + 0x154, {item});
    if (found == 0)
        return 0;
    // local_38 at entry-0x38 is x, local_34 at entry-0x34 is y
    enter(run, 0x4c);
    run.call(0x4ded40, found + 0x3c, {run.automatic(-0x38)});
    if (item != 0x5b06)
        return 0;
    uint32_t delta;
    if (step == 2)
        delta = 0xffffffffu;
    else
        delta = (step == 1) ? 1 : 0;
    uint32_t current = run.get(run.get(receiver + 0x04) + 0x68);
    uint32_t level = delta + current;
    if (s32(level) < 1)
        level = 1;
    else if (s32(level) > 10)
        level = 10;
    run.put(run.automatic(8), level);
    uint32_t changed = 0;
    if (level != current) {
        enter(run, 0x54);
        run.call(0x429ed0, run.get(receiver + 0x04), {level, 1, 0});
        uint32_t owner = run.get(run.get(receiver + 0x0c) + 0x28);
        if (run.get(owner + 0x30) == 0) {
            run.put(run.automatic(4), 0);
            click(run, owner, run.automatic(4), 0x50, 0x58);
        }
        changed = 1;
    }
    double scaled = double(s32(run.get(run.automatic(8)))) * run.getd(0x50e220);
    uint32_t y = run.get(run.automatic(-0x34));
    uint32_t index = truncate(scaled);
    uint32_t entry = run.get(run.automatic(-0x28) - index * 4);
    uint32_t x = run.get(run.automatic(-0x38));
    uint32_t widget = run.get(receiver + 0x26c);
    run.put(widget + 0x4c, entry + x);
    widget = run.get(receiver + 0x26c);
    run.put(widget + 0x50, y + 0x0e);
    if (changed != 0) {
        uint32_t effect = run.get(0x53c9fc);
        if (effect != 0) {
            enter(run, 0x48);
            run.call(0x4d3ef0, effect);
        }
        uint32_t owner = run.get(receiver + 0x0c);
        uint32_t group = run.get(owner + 0x04);
        uint32_t holder = run.get(group + 0x14);
        enter(run, 0x4c);
        run.call(0x4b97c0, run.get(holder + 0x2c), {0});
        enter(run, 0x48);
        run.call(0x450380, receiver);
    }
    return 0;
}

// 0x452290. Steps the volume slider of item 0x5aa1 (music) or 0x5aa4
// (effects). Table of eleven x offsets at entry-0x2c; local_3c x, local_38 y.
uint32_t function_452290(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t step = arguments[0];
    uint32_t item = arguments[1];
    if (run.get(receiver + 0x264) == 0)
        return 0;
    if (run.get(receiver + 0x268) == 0)
        return 0;
    if (run.get(receiver + 0x04) == 0)
        return 0;
    if (run.get(receiver + 0x0c) == 0)
        return 0;
    run.put(run.automatic(-0x2c), 0x148);
    run.put(run.automatic(-0x28), 0x15a);
    run.put(run.automatic(-0x24), 0x16e);
    run.put(run.automatic(-0x20), 0x182);
    run.put(run.automatic(-0x1c), 0x196);
    run.put(run.automatic(-0x18), 0x1aa);
    run.put(run.automatic(-0x14), 0x1be);
    run.put(run.automatic(-0x10), 0x1d2);
    run.put(run.automatic(-0x0c), 0x1e6);
    run.put(run.automatic(-0x08), 0x1fa);
    run.put(run.automatic(-0x04), 0x20c);
    enter(run, 0x50);
    uint32_t found = run.call(0x4dd020, receiver + 0x154, {item});
    if (found == 0)
        return 0;
    enter(run, 0x50);
    run.call(0x4ded40, found + 0x3c, {run.automatic(-0x3c)});
    if (item == 0x5aa1) {
        if (step != 0) {
            uint32_t object = run.get(receiver + 0x04);
            if (run.get(object + 0x10) == 0)
                return 0;
        }
        uint32_t delta;
        if (step == 2)
            delta = 0xfffffff8u;
        else
            delta = ((step != 1) ? 0xfffffff8u : 0u) + 8;
        uint32_t sound = run.get(run.get(receiver + 0x0c) + 0x28);
        if (sound == 0)
            return 0;
        uint32_t volume = run.get(0x532c10);
        uint32_t level = volume + delta;
        run.put(run.automatic(4), level);
        if (s32(level) < 0) {
            level = 0;
            run.put(run.automatic(4), level);
        } else if (s32(level) > 0x50) {
            level = 0x50;
            run.put(run.automatic(4), level);
        }
        if (level != volume) {
            enter(run, 0x50);
            run.call(0x42cdc0, run.get(receiver + 0x04), {level});
            if (run.get(sound + 0x30) == 0) {
                run.put(run.automatic(8), 0);
                click(run, sound, run.automatic(8), 0x54, 0x5c);
            }
        }
        double scaled = double(s32(run.get(run.automatic(4)))) * run.getd(0x50e230);
        uint32_t y = run.get(run.automatic(-0x38));
        uint32_t index = truncate(scaled);
        uint32_t entry = run.get(run.automatic(-0x2c) - index * 4);
        uint32_t x = run.get(run.automatic(-0x3c));
        uint32_t widget = run.get(receiver + 0x264);
        run.put(widget + 0x4c, entry + x);
        widget = run.get(receiver + 0x264);
        run.put(widget + 0x50, y + 0x0e);
        return 0;
    }
    if (item != 0x5aa4)
        return 0;
    if (step != 0) {
        uint32_t object = run.get(receiver + 0x04);
        if (run.get(object + 0x14) == 0)
            return 0;
    }
    uint32_t object = run.get(receiver + 0x04);
    uint32_t meter = run.get(object + 0x50);
    if (meter == 0)
        return 0;
    enter(run, 0x4c);
    uint32_t raw = run.call(0x4b5650, meter);
    run.put(run.automatic(4), raw);
    double ratio = double(s32(raw)) * run.getd(0x50e228);
    int32_t remainder = s32(raw) % 10;
    double rounded;
    if (remainder < 5)
        rounded = std::floor(ratio);
    else
        rounded = std::ceil(ratio);
    uint32_t tens = truncate(rounded) * 10;
    uint32_t delta;
    if (step == 2)
        delta = 0xfffffff6u;
    else
        delta = ((step != 1) ? 0xfffffff6u : 0u) + 10;
    uint32_t level = delta + tens;
    run.put(run.automatic(4), level);
    if (s32(level) < 0) {
        level = 0;
        run.put(run.automatic(4), level);
    } else if (s32(level) > 100) {
        level = 100;
        run.put(run.automatic(4), level);
    }
    if (level != tens) {
        uint32_t sound = run.get(run.get(receiver + 0x0c) + 0x28);
        if (run.get(sound + 0x30) == 0) {
            run.put(run.automatic(8), 0);
            click(run, sound, run.automatic(8), 0x54, 0x5c);
        }
        enter(run, 0x50);
        run.call(0x4b55e0, meter, {level});
    }
    double scaled = double(s32(run.get(run.automatic(4)))) * run.getd(0x50e228);
    double upper = std::ceil(scaled);
    uint32_t index = truncate(upper);
    uint32_t y = run.get(run.automatic(-0x38));
    uint32_t entry = run.get(run.automatic(-0x2c) + index * 4);
    uint32_t x = run.get(run.automatic(-0x3c));
    uint32_t widget = run.get(receiver + 0x268);
    run.put(widget + 0x4c, entry + x - 8);
    widget = run.get(receiver + 0x268);
    run.put(widget + 0x50, y + 0x0e);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x451680:
        return function_451680(run, receiver, arguments);
    case 0x4520f0:
        return function_4520f0(run, receiver, arguments);
    case 0x452290:
        return function_452290(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_pause_menu_panels_entry, owned, body)
