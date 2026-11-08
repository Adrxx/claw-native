// Level 1 shared enemy state callbacks, batch 2
//
// Recovered from the decompile and the disassembly of each owned function.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x43f980:
        return 0;
    case 0x43fc20:
        return 0;
    case 0x43ff60:
        return 0;
    case 0x440070:
        return 0;
    case 0x440260:
        return 0;
    case 0x4405b0:
        return 0;
    case 0x440870:
        return 0;
    case 0x440a50:
        return 0;
    case 0x440be0:
        return 0;
    case 0x440d50:
        return 0;
    default:
        return -1;
    }
}

// Globals used below: 0x5430c4 animation time step, 0x537210 clock,
// 0x537e88 game state, 0x50dba0 / 0x50dbc8 / 0x50dbd0 double constants.
// Enemy fields: +0x0c target object, +0x12c scale object (animation at +0x188).

// x87 compare of ST(0) = left against right: C0 is set when left is below right
// or unordered, C3 when they are equal or unordered.
bool compareC0(double left, double right) {
    return !(left >= right);
}

bool compareC3(double left, double right) {
    return !(left < right || left > right);
}

// Steps the animation object at scale + 0x188 (0x4c82a0) with the time step.
uint32_t stepAnimation(Run &run, uint32_t enemy) {
    uint32_t timeStep = run.get(0x5430c4);
    uint32_t scale = run.get(enemy + 0x12c);
    return run.call(0x4c82a0, scale + 0x188, {timeStep});
}

// Negates and swaps a left/right pair of fields, as the three flip helpers do.
void flipScaleFields(Run &run, uint32_t scale) {
    run.call(0x406120, scale);
    run.call(0x406150, scale);
    run.call(0x406180, scale);
}

// Shared by 0x43f980 and 0x43fc20: calls virtual method +0x44 when the
// vertical position has crossed the limit.
uint32_t chaseLimit(Run &run, uint32_t enemy) {
    stepAnimation(run, enemy);
    bool callMethod = false;
    double zero = run.getd(0x50dba0);
    if (compareC0(run.getd(enemy + 0x50), zero)) {
        double bound = double(s32(run.get(enemy + 0x280)));
        double position = run.getd(enemy + 0x68);
        if (!compareC0(bound, position))
            callMethod = true;
    }
    if (!callMethod) {
        bool below = compareC0(run.getd(enemy + 0x50), run.getd(0x50dba0));
        if (!below) {
            double position = run.getd(enemy + 0x68);
            double bound = double(s32(run.get(enemy + 0x280)));
            if (compareC0(bound, position) || compareC3(bound, position))
                callMethod = true;
        }
    }
    if (!callMethod) {
        if (run.get(enemy + 0x120) & 0x10000) {
            callMethod = true;
        } else {
            double target = double(s32(run.get(enemy + 0x118)));
            double position = run.getd(enemy + 0x68);
            if (compareC3(position, target))
                callMethod = true;
        }
    }
    if (callMethod)
        run.vcall(enemy, 0x44);
    return 0;
}

// 0x43f980.
uint32_t function_43f980(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return chaseLimit(run, receiver);
}

// 0x43fc20.
uint32_t function_43fc20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return chaseLimit(run, receiver);
}

// 0x43ff60. Calls virtual method +0x78 when the target's state (+0xcc) is 1.
uint32_t function_43ff60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    stepAnimation(run, receiver);
    uint32_t target = run.get(receiver + 0xc);
    if (run.get(target + 0xcc) == 1)
        run.vcall(receiver, 0x78);
    return 0;
}

// 0x440070.
uint32_t function_440070(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t result = stepAnimation(run, receiver);
    if (result == 1 && run.get(receiver + 0x1a0) == 0) {
        uint32_t target = run.get(receiver + 0xc);
        uint32_t destination = target + 0x138;
        uint32_t source = receiver + 0x220;
        run.put(receiver + 0x1a0, 1);
        run.put(destination + 0x0, run.get(source + 0x0));
        run.put(destination + 0x4, run.get(source + 0x4));
        run.put(destination + 0x8, run.get(source + 0x8));
        run.put(destination + 0xc, run.get(source + 0xc));
        uint32_t scale = run.get(receiver + 0x12c);
        if (run.get8(scale + 0x40) & 2) {
            uint32_t object = run.get(receiver + 0xc);
            uint32_t second = run.get(object + 0x140);
            uint32_t first = run.get(object + 0x138);
            run.put(object + 0x138, 0u - second);
            object = run.get(receiver + 0xc);
            run.put(object + 0x140, 0u - first);
        }
    }
    uint32_t scale = run.get(receiver + 0x12c);
    if (run.get(scale + 0x1a4) != 0 && run.get(scale + 0x19c) == 0) {
        run.put(scale + 0x8, run.get(scale + 0x8) | 0x10000);
    }
    return 0;
}

// Copies the saved box at enemy + 0x270 into the scale object (+0x118..+0x124)
// and adds the height difference to the target (+0x50).
void restoreBox(Run &run, uint32_t enemy) {
    uint32_t box = enemy + 0x270;
    uint32_t left = run.get(box + 0x0);
    uint32_t target = run.get(enemy + 0xc);
    uint32_t top = run.get(box + 0x4);
    uint32_t oldBottom = run.get(target + 0x124);
    uint32_t right = run.get(box + 0x8);
    uint32_t bottom = run.get(box + 0xc);
    uint32_t difference = oldBottom - bottom;
    run.put(target + 0x50, run.get(target + 0x50) + difference);
    uint32_t scale = run.get(enemy + 0x12c);
    run.put(scale + 0x118, left);
    run.put(scale + 0x11c, top);
    run.put(scale + 0x120, right);
    run.put(scale + 0x124, bottom);
}

// 0x440260.
uint32_t function_440260(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    stepAnimation(run, receiver);
    uint32_t target = run.get(receiver + 0xc);
    if (run.get(target + 0xcc) == 1) {
        run.put(receiver + 0x20, 2);
        uint32_t scale = run.get(receiver + 0x12c);
        uint32_t flags = run.get(scale + 0x8) & 0xfffffffd;
        run.put(scale + 0x8, flags);
        scale = run.get(receiver + 0x12c);
        uint32_t animation = run.get(receiver + 0x380);
        uint32_t frame = run.get(scale + 0x190);
        run.put(receiver + 0x134, frame);
        run.call(0x4c8220, scale + 0x188, {animation});
        stepAnimation(run, receiver);
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x54, 0);
        restoreBox(run, receiver);
        scale = run.get(receiver + 0x12c);
        run.put(scale + 0xd0, 4);
        scale = run.get(receiver + 0x12c);
        run.put(scale + 0x8, run.get(scale + 0x8) & 0xfffffffb);
        run.vcall(receiver, 0x44);
    }
    return 0;
}

// 0x4405b0.
uint32_t function_4405b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t state = run.get(0x537e88);
    if (run.get(state + 0x16c) == 0x2a) {
        uint32_t scale = run.get(receiver + 0x12c);
        uint32_t animation = run.get(receiver + 0x378);
        uint32_t frame = run.get(scale + 0x190);
        run.put(receiver + 0x134, frame);
        run.call(0x4c8220, scale + 0x188, {animation});
        run.call(0x4c82a0, scale + 0x188, {run.get(0x5430c4)});
        state = run.get(0x537e88);
        uint32_t flag = run.get(run.get(run.get(state + 0x6c) + 0x14));
        scale = run.get(receiver + 0x12c);
        uint32_t x = 0;
        if (flag == 0) {
            if (!(run.get8(scale + 0x40) & 2)) {
                uint32_t first = run.get(receiver + 0x138);
                uint32_t second = run.get(receiver + 0x140);
                run.put(receiver + 0x138, 0u - second);
                run.put(receiver + 0x140, 0u - first);
                run.put(scale + 0x40, run.get(scale + 0x40) | 2);
                scale = run.get(receiver + 0x12c);
                flipScaleFields(run, scale);
            }
            state = run.get(0x537e88);
            x = run.get(receiver + 0x2c0) + run.get(state + 0x4c);
        } else {
            if (run.get8(scale + 0x40) & 2) {
                uint32_t first = run.get(receiver + 0x138);
                uint32_t second = run.get(receiver + 0x140);
                run.put(receiver + 0x138, 0u - second);
                run.put(receiver + 0x140, 0u - first);
                run.put(scale + 0x40, run.get(scale + 0x40) & 0xfffffffd);
                scale = run.get(receiver + 0x12c);
                flipScaleFields(run, scale);
            }
            state = run.get(0x537e88);
            x = run.get(receiver + 0x2c4) + run.get(state + 0x4c);
        }
        run.putd(receiver + 0x68, double(s32(x)));
        state = run.get(0x537e88);
        uint32_t y = run.get(receiver + 0x2c8) + run.get(state + 0x50);
        run.putd(receiver + 0x70, double(s32(y)));
    }
    state = run.get(0x537e88);
    if (run.get(state + 0x16c) == 0x2b)
        run.vcall(receiver, 0x8c);
    return 0;
}

// 0x440870.
uint32_t function_440870(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    stepAnimation(run, receiver);
    uint32_t state = run.get(0x537e88);
    uint32_t flag = run.get(run.get(run.get(state + 0x6c) + 0x14));
    uint32_t scale = run.get(receiver + 0x12c);
    bool flip = false;
    uint32_t flags = 0;
    if (flag == 0) {
        if (!(run.get8(scale + 0x40) & 2)) {
            flip = true;
            flags = 2;
        }
    } else {
        if (run.get8(scale + 0x40) & 2)
            flip = true;
    }
    if (flip) {
        uint32_t first = run.get(receiver + 0x138);
        uint32_t second = run.get(receiver + 0x140);
        run.put(receiver + 0x138, 0u - second);
        run.put(receiver + 0x140, 0u - first);
        if (flag == 0) {
            run.put(scale + 0x40, run.get(scale + 0x40) | flags);
        } else {
            run.put(scale + 0x40, run.get(scale + 0x40) & 0xfffffffd);
        }
        scale = run.get(receiver + 0x12c);
        flipScaleFields(run, scale);
        state = run.get(0x537e88);
    }
    flag = run.get(run.get(run.get(state + 0x6c) + 0x14));
    uint32_t mirrored = run.get(receiver + 0x2cc);
    uint32_t x = 0;
    if (flag == 0) {
        uint32_t offset = run.get(state + 0x4c);
        uint32_t base = run.get(receiver + 0x2b4);
        if (mirrored != 0)
            x = base + offset + 4;
        else
            x = base + offset;
    } else {
        uint32_t base = run.get(receiver + 0x2b8);
        if (mirrored != 0) {
            uint32_t offset = run.get(state + 0x4c);
            x = base + offset - 4;
        } else {
            x = base + run.get(state + 0x4c);
        }
    }
    run.putd(receiver + 0x68, double(s32(x)));
    if (run.get(receiver + 0x2cc) != 0) {
        uint32_t globalState = run.get(0x537e88);
        uint32_t base = run.get(receiver + 0x2bc);
        uint32_t offset = run.get(globalState + 0x50);
        uint32_t y = base + offset + 5;
        run.putd(receiver + 0x70, double(s32(y)));
        return 0;
    }
    uint32_t globalState = run.get(0x537e88);
    uint32_t y = run.get(receiver + 0x2bc) + run.get(globalState + 0x50);
    run.putd(receiver + 0x70, double(s32(y)));
    return 0;
}

// 0x440a50. After the timer (+0x3f0 start, +0x3f4 duration) expires, restores
// the saved box, calls virtual method +0x44 and returns to state 2.
uint32_t function_440a50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    stepAnimation(run, receiver);
    uint32_t target = run.get(receiver + 0xc);
    if (run.get(target + 0xcc) == 1) {
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x54, 0);
    }
    uint32_t clock = run.get(0x537210);
    uint32_t start = run.get(receiver + 0x3f0);
    uint32_t duration = run.get(receiver + 0x3f4);
    if (clock - start >= duration) {
        uint32_t scale = run.get(receiver + 0x12c);
        run.put(scale + 0x8, run.get(scale + 0x8) & 0xfffffffd);
        restoreBox(run, receiver);
        scale = run.get(receiver + 0x12c);
        run.put(scale + 0x8, run.get(scale + 0x8) & 0xfffffffb);
        run.vcall(receiver, 0x44);
        scale = run.get(receiver + 0x12c);
        run.put(scale + 0x8, run.get(scale + 0x8) & 0xfffffffe);
        run.put(receiver + 0x20, 2);
    }
    return 0;
}

// Shared by 0x440be0 and 0x440d50: slows the vertical speed (+0x50), or leaves
// the state when the scale object signals completion.
uint32_t slowDown(Run &run, uint32_t enemy) {
    stepAnimation(run, enemy);
    uint32_t scale = run.get(enemy + 0x12c);
    if (run.get(scale + 0x1a4) != 0 && run.get(scale + 0x19c) == 0) {
        run.put(scale + 0x8, run.get(scale + 0x8) & 0xfffffffb);
        run.vcall(enemy, 0x44);
        run.put(enemy + 0x20, 2);
        return 0;
    }
    double speed = run.getd(enemy + 0x50);
    if (!compareC3(speed, run.getd(0x50dba0))) {
        uint32_t mode = run.get(enemy + 0x18c);
        speed = run.getd(enemy + 0x50);
        if (mode == 3) {
            run.putd(enemy + 0x50, speed - run.getd(0x50dbc8));
            return 0;
        }
        run.putd(enemy + 0x50, speed - run.getd(0x50dbd0));
    }
    return 0;
}

// 0x440be0.
uint32_t function_440be0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return slowDown(run, receiver);
}

// 0x440d50.
uint32_t function_440d50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return slowDown(run, receiver);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x43f980:
        return function_43f980(run, receiver, arguments);
    case 0x43fc20:
        return function_43fc20(run, receiver, arguments);
    case 0x43ff60:
        return function_43ff60(run, receiver, arguments);
    case 0x440070:
        return function_440070(run, receiver, arguments);
    case 0x440260:
        return function_440260(run, receiver, arguments);
    case 0x4405b0:
        return function_4405b0(run, receiver, arguments);
    case 0x440870:
        return function_440870(run, receiver, arguments);
    case 0x440a50:
        return function_440a50(run, receiver, arguments);
    case 0x440be0:
        return function_440be0(run, receiver, arguments);
    case 0x440d50:
        return function_440d50(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_enemy_states_02_entry, owned, body)
