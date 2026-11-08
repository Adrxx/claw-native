// Original sound-trigger and ambient actors
// Canonical game owners translated from the original packet.
#include "ClawRuntime.hpp"
#include <cmath>

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x402240:
        return 2;
    case 0x402270:
        return 0;
    case 0x4022a0:
        return 0;
    case 0x4022d0:
        return 1;
    case 0x4022f0:
        return 5;
    case 0x402370:
        return 5;
    case 0x4023f0:
        return 0;
    case 0x402400:
        return 9;
    case 0x4024e0:
        return 1;
    case 0x402520:
        return 0;
    case 0x402570:
        return 0;
    case 0x4025c0:
        return 2;
    case 0x402610:
        return 5;
    case 0x4026a0:
        return 1;
    case 0x402720:
        return 3;
    case 0x402840:
        return 3;
    case 0x4028c0:
        return 3;
    case 0x402a60:
        return 5;
    case 0x402ac0:
        return 3;
    case 0x402f10:
        return 3;
    case 0x48c4d0:
        return 2;
    case 0x48cb00:
        return 2;
    default:
        return -1;
    }
}

// Ambient fields: +0x04 voice, +0x08 percentage, +0x0c master,
// +0x10 scale, +0x14 active, +0x18/+0x28 rectangles, +0x38 pan.
uint32_t clamp(uint32_t value) {
    if (s32(value) < 0)
        return 0;
    if (s32(value) > 100)
        return 100;
    return value;
}
uint32_t volume(Run &run, uint32_t object, uint32_t percentage, uint32_t master) {
    if (s32(master) > 5)
        master -= 15;
    uint32_t value = uint32_t(s32(master * percentage) / 100);
    uint32_t scale = run.get(object + 0x10);
    if (s32(scale) > 0)
        value = uint32_t(s32(value * scale) / 100);
    return clamp(value);
}
bool enabled(Run &run) {
    uint32_t app = run.get(0x5371fc);
    if (!run.get(app + 0x10))
        return false;
    return run.get(run.get(app + 0x5c) + 0x24) != 0;
}
bool rectangle(Run &run, uint32_t rect, uint32_t x, uint32_t y) {
    return s32(x) > run.gets(rect) && s32(x) < run.gets(rect + 0x08) &&
        s32(y) > run.gets(rect + 0x04) && s32(y) < run.gets(rect + 0x0c);
}
bool inside(Run &run, uint32_t object, uint32_t x, uint32_t y) {
    if (rectangle(run, object + 0x18, x, y))
        return true;
    return run.get(object + 0x28) != 0x80000000 && rectangle(run, object + 0x28, x, y);
}
uint32_t interval(Run &run, uint32_t low, uint32_t high) {
    uint32_t width = high - low + 1;
    uint32_t random = run.call(0x4a3050, 0, {});
    if (!width)
        return (random & 1) ? low : high;
    return uint32_t(int64_t(s32(random)) % int64_t(s32(width))) + low;
}

// 0x402240. Manager initialization.
uint32_t function_402240(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!arguments[0])
        return 0;
    run.put(receiver, arguments[0]);
    run.put(receiver + 0x04, arguments[1]);
    run.put(receiver + 0x24, 1);
    run.put(receiver + 0x28, 0);
    run.put(receiver + 0x2c, 0);
    return 1;
}
// 0x4022a0. Delete objects, with next cached before each callback.
uint32_t function_4022a0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t node = run.get(receiver + 0x0c);
    while (node) {
        uint32_t current = node;
        node = run.get(node);
        uint32_t object = run.get(current + 0x08);
        if (object)
            run.vcall(object, 0, {1});
    }
    run.call(0x4f5172, receiver + 0x08, {});
    return 0;
}
// 0x402270. Manager cleanup.
uint32_t function_402270(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t app = run.get(receiver);
    if (app) {
        uint32_t controller = run.get(app + 0x2c);
        if (controller)
            run.call(0x4b4c10, controller, {});
    }
    function_4022a0(run, receiver, nullptr);
    run.put(receiver, 0);
    return 0;
}
// 0x4023f0. Base destruction preserves the other ambient state.
uint32_t function_4023f0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x50b014);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x3c, 0);
    return 0;
}
// 0x4022d0. Scalar deleting destructor.
uint32_t function_4022d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4023f0(run, receiver, nullptr);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}
// 0x402610. Base initializer copies rectangle words sequentially.
uint32_t function_402610(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!arguments[0])
        return 0;
    run.put(receiver + 0x04, arguments[0]);
    run.put(receiver + 0x08, arguments[1]);
    run.put(receiver + 0x10, arguments[4]);
    run.put(receiver + 0x0c, arguments[2]);
    run.put(receiver + 0x38, 0);
    run.put(receiver + 0x14, 0);
    if (arguments[3]) {
        run.put(receiver + 0x18, run.get(arguments[3]));
        run.put(receiver + 0x1c, run.get(arguments[3] + 0x04));
        run.put(receiver + 0x20, run.get(arguments[3] + 0x08));
        run.put(receiver + 0x24, run.get(arguments[3] + 0x0c));
    } else {
        run.put(receiver + 0x18, 0x80000000);
    }
    if (!run.get(receiver + 0x18) && !run.get(receiver + 0x1c) &&
        !run.get(receiver + 0x20) && !run.get(receiver + 0x24))
        run.put(receiver + 0x18, 0x80000000);
    run.put(receiver + 0x28, 0x80000000);
    return 1;
}
// 0x402a60. Spatial initializer.
uint32_t function_402a60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!arguments[0] || !arguments[3])
        return 0;
    run.put(receiver + 0x04, arguments[0]);
    run.put(receiver + 0x08, arguments[1]);
    run.put(receiver + 0x0c, arguments[2]);
    run.put(receiver + 0x38, 0);
    run.put(receiver + 0x10, arguments[4]);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x40, run.get(arguments[3]));
    run.put(receiver + 0x44, run.get(arguments[3] + 0x04));
    return 1;
}
uint32_t factory(Run &run, uint32_t receiver, const uint32_t *arguments, uint32_t type) {
    uint32_t size = type == 0 ? 0x40 : (type == 1 ? 0x48 : 0x58);
    uint32_t object = run.call(0x4f63ec, 0, {size});
    if (!object)
        return 0;
    if (!type)
        run.put(object, 0x50b004);
    run.put(object + 0x04, 0);
    run.put(object + 0x08, 100);
    run.put(object + 0x14, 0);
    run.put(object + 0x3c, 0);
    if (type)
        run.put(object, type == 1 ? 0x50b01c : 0x50b02c);
    uint32_t args[] = {arguments[0], arguments[1], run.get(receiver + 0x04), arguments[2], arguments[3]};
    uint32_t result = type == 1 ? function_402a60(run, object, args) : function_402610(run, object, args);
    if (!result) {
        run.vcall(object, 0, {1});
        return 0;
    }
    if (type == 2) {
        run.put(object + 0x40, arguments[4]);
        run.put(object + 0x44, arguments[5]);
        run.put(object + 0x48, arguments[6]);
        run.put(object + 0x4c, arguments[7]);
        uint32_t timer = interval(run, arguments[6], arguments[7]);
        run.put(object + 0x50, timer);
        run.put(object + 0x54, 1);
    }
    uint32_t position = run.call(0x4f51c5, receiver + 0x08, {object});
    run.put(object + 0x3c, position);
    return object;
}
// 0x4022f0.
uint32_t function_4022f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return factory(run, receiver, arguments, 0);
}
// 0x402370.
uint32_t function_402370(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return factory(run, receiver, arguments, 1);
}
// 0x402400.
uint32_t function_402400(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return factory(run, receiver, arguments, 2);
}
// 0x4026a0. Unchanged master exits without effects.
uint32_t function_4026a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (run.get(receiver + 0x0c) == arguments[0])
        return 0;
    uint32_t percentage = run.get(receiver + 0x08);
    run.put(receiver + 0x0c, arguments[0]);
    uint32_t value = volume(run, receiver, percentage, arguments[0]);
    run.call(0x4b3f40, run.get(receiver + 0x04), {value});
    return 0;
}
// 0x4024e0. Publish master before cleanup, then traverse its resulting head.
uint32_t function_4024e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t app = run.get(receiver);
    run.put(receiver + 0x04, arguments[0]);
    uint32_t controller = run.get(app + 0x2c);
    if (controller) {
        run.stackPointer = run.frame - 0x0c;
        run.call(0x4b4c10, controller, {});
    }
    uint32_t node = run.get(receiver + 0x0c);
    while (node) {
        uint32_t current = node;
        node = run.get(node);
        uint32_t object = run.get(current + 0x08);
        if (object)
            function_4026a0(run, object, arguments);
    }
    return 0;
}
// 0x402520. Stop all voices.
uint32_t function_402520(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t app = run.get(receiver);
    if (app) {
        uint32_t controller = run.get(app + 0x2c);
        if (controller) {
            run.stackPointer = run.frame - 0x10;
            run.call(0x4b4c10, controller, {});
        }
    }
    uint32_t node = run.get(receiver + 0x0c);
    while (node) {
        uint32_t current = node;
        node = run.get(node);
        uint32_t object = run.get(current + 0x08);
        if (object) {
            uint32_t voice = run.get(object + 0x04);
            if (voice) {
                run.call(0x4b3e30, voice, {});
                run.put(object + 0x14, 0);
            }
        }
    }
    return 0;
}
// 0x402570. Reset and force update.
uint32_t function_402570(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t node = run.get(receiver + 0x0c);
    while (node) {
        uint32_t current = node;
        node = run.get(node);
        uint32_t object = run.get(current + 0x08);
        if (object) {
            uint32_t method = run.get(run.get(object) + 0x04);
            run.put(object + 0x14, 0);
            uint32_t y = run.get(receiver + 0x2c);
            uint32_t x = run.get(receiver + 0x28);
            run.call(method, object, {x, y, 1});
        }
    }
    uint32_t controller = run.get(run.get(receiver) + 0x2c);
    if (controller)
        run.call(0x4b4b80, controller, {});
    return 0;
}
// 0x4025c0. Position update.
uint32_t function_4025c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x28, arguments[0]);
    run.put(receiver + 0x2c, arguments[1]);
    uint32_t node = run.get(receiver + 0x0c);
    while (node) {
        uint32_t current = node;
        node = run.get(node);
        uint32_t object = run.get(current + 0x08);
        if (object)
            run.vcall(object, 0x04, {arguments[0], arguments[1], 0});
    }
    uint32_t controller = run.get(run.get(receiver) + 0x2c);
    if (controller)
        run.call(0x4b4b80, controller, {});
    return 0;
}
// 0x402840. Percentage publication precedes backend volume/fade.
uint32_t function_402840(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t master = run.get(receiver + 0x0c);
    run.put(receiver + 0x08, arguments[0]);
    uint32_t value = volume(run, receiver, arguments[0], master);
    uint32_t voice = run.get(receiver + 0x04);
    if (!arguments[1])
        run.call(0x4b3f40, voice, {value});
    else {
        run.stackPointer = run.frame - 0x14;
        run.call(0x4b3fe0, voice, {value, arguments[1], arguments[2]});
    }
    return 0;
}
// 0x4028c0. Start/stop with optional fade.
uint32_t function_4028c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t voice = run.get(receiver + 0x04);
    if (!voice)
        return 0;
    uint32_t active = run.get(receiver + 0x14);
    if (!arguments[0]) {
        if (!active)
            return 0;
        if (!arguments[2])
            run.call(0x4b3e30, voice, {});
        else {
            run.put(receiver + 0x08, 0);
            run.stackPointer = run.frame - 0x1c;
            run.call(0x4b3fe0, voice, {0, arguments[2], 1});
        }
        run.put(receiver + 0x14, 0);
        return 0;
    }
    if (active || !enabled(run))
        return 0;
    run.call(0x4b3dc0, voice, {1, run.get(receiver + 0x38), 0, 1});
    uint32_t master = run.get(receiver + 0x0c);
    run.put(receiver + 0x08, arguments[1]);
    uint32_t value = volume(run, receiver, arguments[1], master);
    if (!arguments[2])
        run.call(0x4b3f40, run.get(receiver + 0x04), {value});
    else {
        run.stackPointer = run.frame - 0x1c;
        run.call(0x4b3fe0, run.get(receiver + 0x04), {value, arguments[2], 0});
    }
    run.put(receiver + 0x08, arguments[1]);
    run.put(receiver + 0x14, 1);
    return 0;
}
// 0x402720. Rectangle ambient actor.
uint32_t function_402720(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (run.get(receiver + 0x18) == 0x80000000) {
        if (run.get(receiver + 0x14))
            return 0;
        uint32_t voice = run.get(receiver + 0x04);
        uint32_t percentage = run.get(receiver + 0x08);
        if (!voice || !percentage || !enabled(run))
            return 0;
        run.call(0x4b3dc0, voice, {1, run.get(receiver + 0x38), 0, 1});
    } else {
        bool in = inside(run, receiver, arguments[0], arguments[1]);
        if (run.get(receiver + 0x14)) {
            if (!in) {
                uint32_t args[] = {0, 0, 1000};
                uint32_t parentFrame = run.frame;
                run.frame -= 0x14;
                function_4028c0(run, receiver, args);
                run.frame = parentFrame;
            }
            return 0;
        }
        if (!in || !enabled(run))
            return 0;
        if (!arguments[2]) {
            uint32_t args[] = {1, 100, 1000};
            uint32_t parentFrame = run.frame;
            run.frame -= 0x14;
            function_4028c0(run, receiver, args);
            run.frame = parentFrame;
            return 0;
        }
        uint32_t voice = run.get(receiver + 0x04);
        if (!voice)
            return 0;
        run.call(0x4b3dc0, voice, {1, run.get(receiver + 0x38), 0, 1});
    }
    uint32_t args[] = {100, 0, 0};
    function_402840(run, receiver, args);
    run.put(receiver + 0x08, 100);
    run.put(receiver + 0x14, 1);
    return 0;
}
// 0x402ac0. Spatial attenuation, pan and start/stop policy.
uint32_t function_402ac0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t sourceX = run.get(receiver + 0x40);
    uint32_t dx = sourceX - arguments[0];
    uint32_t dy = run.get(receiver + 0x44) - arguments[1];
    if (s32(dx) < 0)
        dx = 0u - dx;
    if (s32(dy) < 0)
        dy = 0u - dy;
    uint32_t squares = dx * dx + dy * dy;
    if (s32(dx) > 640 || s32(dy) > 640) {
        uint32_t voice = run.get(receiver + 0x04);
        if (voice && run.get(receiver + 0x14)) {
            run.call(0x4b3e30, voice, {});
            run.put(receiver + 0x14, 0);
        }
        return 0;
    }
    double distance = std::sqrt(double(s32(squares)));
    uint32_t integral = run.call_x87(0x4a30e0, 0, distance, {});
    uint32_t percentage = clamp(100u - uint32_t(s32(integral) / 12));
    uint32_t pan = clamp(uint32_t(s32(dx) / 4));
    if (s32(sourceX) < s32(arguments[0]))
        pan = 0u - pan;
    uint32_t master = run.get(receiver + 0x0c);
    run.put(receiver + 0x08, percentage);
    uint32_t value = volume(run, receiver, percentage, master);
    run.call(0x4b3f40, run.get(receiver + 0x04), {value});
    uint32_t voice = run.get(receiver + 0x04);
    run.put(receiver + 0x38, pan);
    run.call(0x4b4110, voice, {pan});
    if (run.get(receiver + 0x14))
        return 0;
    voice = run.get(receiver + 0x04);
    if (!voice || !enabled(run))
        return 0;
    run.call(0x4b3dc0, voice, {1, run.get(receiver + 0x38), 0, 1});
    master = run.get(receiver + 0x0c);
    run.put(receiver + 0x08, percentage);
    value = volume(run, receiver, percentage, master);
    run.call(0x4b3f40, run.get(receiver + 0x04), {value});
    run.put(receiver + 0x08, percentage);
    run.put(receiver + 0x14, 1);
    return 0;
}
// 0x402f10. Periodic actor countdown uses unsigned elapsed comparison.
uint32_t function_402f10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    bool in = run.get(receiver + 0x18) == 0x80000000 || inside(run, receiver, arguments[0], arguments[1]);
    if (!in) {
        if (run.get(receiver + 0x14) && run.get(receiver + 0x04)) {
            uint32_t args[] = {0, 1000, 1};
            uint32_t parentFrame = run.frame;
            run.frame -= 0x20;
            function_402840(run, receiver, args);
            run.frame = parentFrame;
            run.put(receiver + 0x14, 0);
        }
        run.put(receiver + 0x54, 0);
        return 0;
    }
    if (arguments[2] && run.get(receiver + 0x54)) {
        uint32_t voice = run.get(receiver + 0x04);
        if (!voice || run.get(receiver + 0x14) || !enabled(run))
            return 0;
        run.call(0x4b3dc0, voice, {1, run.get(receiver + 0x38), 0, 1});
        uint32_t args[] = {100, 0, 0};
        function_402840(run, receiver, args);
        run.put(receiver + 0x08, 100);
        run.put(receiver + 0x14, 1);
        return 0;
    }
    uint32_t remaining = run.get(receiver + 0x50);
    uint32_t elapsed = run.get(0x53720c);
    run.put(receiver + 0x50, elapsed < remaining ? remaining - elapsed : 0);
    if (run.get(receiver + 0x50))
        return 0;
    uint32_t phase = run.get(receiver + 0x54) ^ 1u;
    run.put(receiver + 0x54, phase);
    uint32_t high = run.get(receiver + (phase ? 0x44 : 0x4c));
    uint32_t low = run.get(receiver + (phase ? 0x40 : 0x48));
    uint32_t timer = interval(run, low, high);
    run.put(receiver + 0x50, timer);
    uint32_t args[] = {phase ? 1u : 0u, 100, 1000};
    uint32_t parentFrame = run.frame;
    run.frame -= 0x20;
    function_4028c0(run, receiver, args);
    run.frame = parentFrame;
    return 0;
}
uint32_t bounds(Run &run, const uint32_t *arguments, uint32_t base) {
    uint32_t identity = run.get(arguments[1] + 0x10);
    uint32_t x = 64;
    uint32_t y = 64;
    if (identity == base)
        x = y = 128;
    else if (identity == base + 0x20)
        x = y = 32;
    else if (identity == base + 0x40)
        x = y = 256;
    else if (identity == base + 0x60)
        x = y = 16;
    else if (identity == base + 0x80) {
        x = 32;
        y = 100;
    } else if (identity == base + 0xa0) {
        x = 100;
        y = 32;
    }
    uint32_t object = arguments[0];
    run.put(object + 0x128, 0u - x);
    run.put(object + 0x12c, 0u - y);
    run.put(object + 0x130, x);
    run.put(object + 0x134, y);
    return object;
}
// 0x48c4d0.
uint32_t function_48c4d0(Run &run, uint32_t, const uint32_t *arguments) {
    return bounds(run, arguments, 0x48c410);
}
// 0x48cb00.
uint32_t function_48cb00(Run &run, uint32_t, const uint32_t *arguments) {
    return bounds(run, arguments, 0x48ca40);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x402240:
        return function_402240(run, receiver, arguments);
    case 0x402270:
        return function_402270(run, receiver, arguments);
    case 0x4022a0:
        return function_4022a0(run, receiver, arguments);
    case 0x4022d0:
        return function_4022d0(run, receiver, arguments);
    case 0x4022f0:
        return function_4022f0(run, receiver, arguments);
    case 0x402370:
        return function_402370(run, receiver, arguments);
    case 0x4023f0:
        return function_4023f0(run, receiver, arguments);
    case 0x402400:
        return function_402400(run, receiver, arguments);
    case 0x4024e0:
        return function_4024e0(run, receiver, arguments);
    case 0x402520:
        return function_402520(run, receiver, arguments);
    case 0x402570:
        return function_402570(run, receiver, arguments);
    case 0x4025c0:
        return function_4025c0(run, receiver, arguments);
    case 0x402610:
        return function_402610(run, receiver, arguments);
    case 0x4026a0:
        return function_4026a0(run, receiver, arguments);
    case 0x402720:
        return function_402720(run, receiver, arguments);
    case 0x402840:
        return function_402840(run, receiver, arguments);
    case 0x4028c0:
        return function_4028c0(run, receiver, arguments);
    case 0x402a60:
        return function_402a60(run, receiver, arguments);
    case 0x402ac0:
        return function_402ac0(run, receiver, arguments);
    case 0x402f10:
        return function_402f10(run, receiver, arguments);
    case 0x48c4d0:
        return function_48c4d0(run, receiver, arguments);
    case 0x48cb00:
        return function_48cb00(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_sound_trigger_logic_entry, owned, body)
