// Level 1 closure: Scene actor and world object helpers
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
    case 0x4c7a90:
        return 2;
    case 0x4c7ae0:
        return 3;
    case 0x4c7cd0:
        return 3;
    case 0x4c80a0:
        return 0;
    case 0x4c80b0:
        return 0;
    case 0x4c81b0:
        return 0;
    case 0x4c97c0:
        return 1;
    case 0x4c97e0:
        return 0;
    case 0x4c9810:
        return 0;
    case 0x4c9890:
        return 0;
    case 0x4c9bc0:
        return 0;
    case 0x4c9d80:
        return 0;
    case 0x4cf080:
        return 0;
    case 0x4d56c0:
        return 3;
    default:
        return -1;
    }
}

// Actor fields used here: +0x04 and +0x38 (-1 when unset), +0x18/+0x1c position,
// +0x20/+0x24 rectangle origin, +0x30/+0x34 size, +0xa4 saved copy of the nine
// dwords at +0x18, +0xac saved rectangle, +0xbc/+0xc0 saved size, +0xc4 saved
// flag (-1 when unset).
// Surface owner objects hold their surface at +0x2c.

// 0x4d56c0. stdcall, 3 stack arguments, empty body.
void emptyService(uint32_t a, uint32_t b, uint32_t c) {
    (void)a;
    (void)b;
    (void)c;
}

// Writes the rectangle {left, top, right, bottom} to the local at entry-0x10 and
// calls the wrapper 0x4b9ce0 with it twice (source and destination rectangle).
void blitRect(Run &run, uint32_t destination, uint32_t source, uint32_t left, uint32_t top, uint32_t right, uint32_t bottom) {
    uint32_t rect = run.automatic(-0x10);
    run.put(rect, left);
    run.put(rect + 4, top);
    run.put(rect + 8, right);
    run.put(rect + 12, bottom);
    uint32_t target = run.get(destination + 0x2c);
    uint32_t origin = run.get(source + 0x2c);
    run.call(0x4b9ce0, target, {rect, origin, rect, 0x1000000, 0});
}

// Blits the current rectangle: left/top from +0x18/+0x1c, extent from +0x30/+0x34.
void blitCurrent(Run &run, uint32_t actor, uint32_t destination, uint32_t source) {
    uint32_t left = run.get(actor + 0x18);
    uint32_t top = run.get(actor + 0x1c);
    uint32_t right = left + run.get(actor + 0x30);
    uint32_t bottom = top + run.get(actor + 0x34);
    blitRect(run, destination, source, left, top, right, bottom);
}

// Blits the saved rectangle: left/top from +0xa4/+0xa8, extent from +0xbc/+0xc0.
void blitSaved(Run &run, uint32_t actor, uint32_t destination, uint32_t source) {
    uint32_t left = run.get(actor + 0xa4);
    uint32_t top = run.get(actor + 0xa8);
    uint32_t right = left + run.get(actor + 0xbc);
    uint32_t bottom = top + run.get(actor + 0xc0);
    blitRect(run, destination, source, left, top, right, bottom);
}

// 0x4c7a90. Saves the nine dwords at +0x18 to +0xa4; when +0x38 was set, calls
// 0x4b9d80 on the destination surface and clears +0x38 to -1.
uint32_t function_4c7a90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t flag = run.get(receiver + 0x38);
    for (uint32_t i = 0; i < 9; ++i) {
        uint32_t value = run.get(receiver + 0x18 + 4 * i);
        run.put(receiver + 0xa4 + 4 * i, value);
    }
    if (flag != 0xffffffff) {
        uint32_t destination = run.get(arguments[1] + 0x2c);
        uint32_t x = run.get(receiver + 0x20);
        uint32_t y = run.get(receiver + 0x24);
        uint32_t target = run.get(arguments[0] + 0x2c);
        run.call(0x4b9d80, target, {x, y, destination, receiver + 0x20, 0x10});
        run.put(receiver + 0x38, 0xffffffff);
    }
    return 0;
}

// 0x4c7ae0. Redraws the dirty area of the actor: union when the current and
// saved rectangles intersect, otherwise each separately.
uint32_t function_4c7ae0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t destination = arguments[0];
    uint32_t source = arguments[1];
    uint32_t current = run.get(receiver + 0x38);
    if (current != 0xffffffff) {
        if (run.get(receiver + 0xc4) != 0xffffffff) {
            uint32_t out = run.automatic(-0x20);
            uint32_t hit = run.call(0x546ce0, 0, {out, receiver + 0x20, receiver + 0xac});
            if (hit != 0) {
                run.call(0x546d94, 0, {out, receiver + 0x20, receiver + 0xac});
                uint32_t left = run.get(out);
                uint32_t top = run.get(out + 4);
                uint32_t right = run.get(out + 8);
                uint32_t bottom = run.get(out + 12);
                uint32_t farRight = (right - left + 1) + left;
                uint32_t farBottom = (bottom - top + 1) + top;
                blitRect(run, destination, source, left, top, farRight, farBottom);
                return 0;
            }
            blitCurrent(run, receiver, destination, source);
            blitSaved(run, receiver, destination, source);
            return 0;
        }
        blitCurrent(run, receiver, destination, source);
        return 0;
    }
    if (run.get(receiver + 0xc4) != 0xffffffff)
        blitSaved(run, receiver, destination, source);
    return 0;
}

// 0x4c7cd0. Same branching as 0x4c7ae0 but only calls the empty service 0x4d56c0.
// The disassembly takes three stack arguments (ret 0xc), not the decompile's none.
uint32_t function_4c7cd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t first = arguments[0];
    uint32_t second = arguments[1];
    uint32_t current = run.get(receiver + 0x38);
    if (current != 0xffffffff) {
        if (run.get(receiver + 0xc4) != 0xffffffff) {
            uint32_t out = run.automatic(-0x10);
            uint32_t hit = run.call(0x546ce0, 0, {out, receiver + 0x20, receiver + 0xac});
            if (hit != 0) {
                run.call(0x546d94, 0, {out, receiver + 0x20, receiver + 0xac});
                uint32_t left = run.get(out);
                uint32_t top = run.get(out + 4);
                uint32_t right = run.get(out + 8);
                uint32_t bottom = run.get(out + 12);
                uint32_t width = right - left;
                uint32_t height = bottom - top;
                run.put(run.automatic(-0x18), left);
                width = width + 1;
                run.put(run.automatic(-0x14), top);
                height = height + 1;
                run.put(run.automatic(-0x20), width);
                run.put(run.automatic(-0x1c), height);
                emptyService(second, run.automatic(-0x18), run.automatic(-0x20));
                return 0;
            }
            emptyService(second, receiver + 0x18, receiver + 0x30);
            emptyService(second, receiver + 0xa4, receiver + 0xbc);
            return 0;
        }
        emptyService(second, receiver + 0x18, receiver + 0x30);
        return 0;
    }
    (void)first;
    if (run.get(receiver + 0xc4) != 0xffffffff)
        emptyService(second, receiver + 0xa4, receiver + 0xbc);
    return 0;
}

// 0x4c80a0. True when +0x10 is non-zero.
uint32_t function_4c80a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return run.get(receiver + 0x10) != 0 ? 1 : 0;
}

// 0x4c80b0. Returns the constant 9.
uint32_t function_4c80b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 9;
}

// 0x4c81b0. Clears +0x10, frees and clears the buffer at +0x14, and deletes the
// object at +0x18 through its first virtual method with argument 1.
uint32_t function_4c81b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t buffer = run.get(receiver + 0x14);
    run.put(receiver + 0x10, 0);
    if (buffer != 0) {
        run.call(0x4f6428, 0, {buffer});
        run.put(receiver + 0x14, 0);
    }
    uint32_t object = run.get(receiver + 0x18);
    if (object != 0) {
        run.vcall(object, 0, {1});
        run.put(receiver + 0x18, 0);
    }
    return 0;
}

// 0x4c97e0. Resets the base fields; +0x00 receives the vtable 0x50becc.
uint32_t function_4c97e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    run.put(receiver + 0x04, 0xffffffff);
    run.put(receiver + 0x00, 0x50becc);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    return 0;
}

// 0x4c97c0. Scalar deleting destructor: resets, then frees when bit 0 is set.
uint32_t function_4c97c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4c97e0(run, receiver, nullptr);
    if ((arguments[0] & 1) != 0)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4c9810.
uint32_t function_4c9810(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    return 0;
}

// 0x4c9890. True when +0x6c, +0x68 and +0xc are non-zero and +0x04 is not -1.
uint32_t function_4c9890(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x6c) == 0)
        return 0;
    if (run.get(receiver + 0x68) == 0)
        return 0;
    if (run.get(receiver + 0x0c) == 0)
        return 0;
    if (run.get(receiver + 0x04) == 0xffffffff)
        return 0;
    return 1;
}

// 0x4c9bc0. True when +0x180 is non-zero.
uint32_t function_4c9bc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return run.get(receiver + 0x180) != 0 ? 1 : 0;
}

// 0x4c9d80. Resets state and deletes the owned objects at +0x6c, +0x70 and +0x78
// through virtual slot +4 with argument 1.
uint32_t function_4c9d80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x168, 0xffffffff);
    run.put(receiver + 0x16c, 0xffffffff);
    run.put(receiver + 0x174, 0);
    run.put(receiver + 0x170, 0);
    uint32_t first = run.get(receiver + 0x6c);
    if (first != 0) {
        run.vcall(first, 4, {1});
        run.put(receiver + 0x6c, 0);
    }
    uint32_t second = run.get(receiver + 0x70);
    if (second != 0) {
        run.vcall(second, 4, {1});
        run.put(receiver + 0x70, 0);
    }
    uint32_t third = run.get(receiver + 0x78);
    if (third != 0) {
        run.vcall(third, 4, {1});
        run.put(receiver + 0x78, 0);
    }
    run.put(receiver + 0xc4, 0xffffffff);
    run.put(receiver + 0xac, 0x80000000);
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    return 0;
}

// 0x4cf080. True when +0x0c is non-zero and +0x04 is not -1.
uint32_t function_4cf080(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x0c) == 0)
        return 0;
    if (run.get(receiver + 0x04) == 0xffffffff)
        return 0;
    return 1;
}

// 0x4d56c0. stdcall, 3 stack arguments, does nothing.
uint32_t function_4d56c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    emptyService(arguments[0], arguments[1], arguments[2]);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4c7a90:
        return function_4c7a90(run, receiver, arguments);
    case 0x4c7ae0:
        return function_4c7ae0(run, receiver, arguments);
    case 0x4c7cd0:
        return function_4c7cd0(run, receiver, arguments);
    case 0x4c80a0:
        return function_4c80a0(run, receiver, arguments);
    case 0x4c80b0:
        return function_4c80b0(run, receiver, arguments);
    case 0x4c81b0:
        return function_4c81b0(run, receiver, arguments);
    case 0x4c97c0:
        return function_4c97c0(run, receiver, arguments);
    case 0x4c97e0:
        return function_4c97e0(run, receiver, arguments);
    case 0x4c9810:
        return function_4c9810(run, receiver, arguments);
    case 0x4c9890:
        return function_4c9890(run, receiver, arguments);
    case 0x4c9bc0:
        return function_4c9bc0(run, receiver, arguments);
    case 0x4c9d80:
        return function_4c9d80(run, receiver, arguments);
    case 0x4cf080:
        return function_4cf080(run, receiver, arguments);
    case 0x4d56c0:
        return function_4d56c0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_closure_scene_actor_01_entry, owned, body)
