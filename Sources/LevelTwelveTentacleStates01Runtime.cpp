// Level 12 tentacle states, recovered from the original v1.0 entries.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x492ec0:
    case 0x493030:
    case 0x493200:
    case 0x493550:
    case 0x493600:
    case 0x493680:
    case 0x493830:
    case 0x493890:
    case 0x493920:
    case 0x4939a0:
    case 0x493be0:
        return 0;
    default:
        return -1;
    }
}

// Keep stack-local addresses exported by original callees at their real CALL frames.
uint32_t original(Run &run, uint32_t target, uint32_t receiver, uint32_t frameBytes,
                  std::initializer_list<uint32_t> arguments = {}) {
    uint32_t previous = run.stackPointer;
    run.stackPointer = run.frame - frameBytes;
    uint32_t result = run.call(target, receiver, arguments);
    run.stackPointer = previous;
    return result;
}

// S+0xc is the scene object, +0x12c the sprite; +0x210/+0x220 are hit rectangles.
// Copy in original word order, including when the source and destination alias.
void rectangle(Run &run, uint32_t s, uint32_t source) {
    uint32_t destination = run.get(s + 0xc) + 0x138;
    run.put(destination, run.get(source));
    run.put(destination + 0x4, run.get(source + 0x4));
    run.put(destination + 0x8, run.get(source + 0x8));
    run.put(destination + 0xc, run.get(source + 0xc));
    if (run.get8(run.get(s + 0x12c) + 0x40) & 2) {
        uint32_t object = run.get(s + 0xc);
        uint32_t right = run.get(object + 0x140);
        uint32_t left = run.get(object + 0x138);
        run.put(object + 0x138, 0u - right);
        run.put(run.get(s + 0xc) + 0x140, 0u - left);
    }
}

void frameRectangle(Run &run, uint32_t s) {
    if (run.get(run.get(s + 0x12c) + 0x16c) == 0x12d) {
        rectangle(run, s, s + 0x220);
    } else {
        rectangle(run, s, s + 0x210);
    }
}

// The embedded animation at sprite+0x188 stores completion +0x1c and remaining +0x14.
bool completed(Run &run, uint32_t s) {
    uint32_t animation = run.get(s + 0x12c) + 0x188;
    return run.get(animation + 0x1c) != 0 && run.get(animation + 0x14) == 0;
}

// S+0x10 is its logic state; +0x24 saves its token and +0x134 saves animation identity.
void enterState(Run &run, uint32_t s, uint32_t name, uint32_t animationOffset) {
    run.put(s + 0x24, run.get(run.get(s + 0x10) + 0x1c));
    uint32_t token = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(s + 0x10) + 0x1c, token);
    uint32_t sprite = run.get(s + 0x12c);
    uint32_t animation = run.get(s + animationOffset);
    uint32_t identity = run.get(sprite + 0x190);
    run.put(s + 0x134, identity);
    run.call(0x4c8220, sprite + 0x188, {animation});
}

// 0x492ec0. Idle updates and attack readiness.
uint32_t function_492ec0(Run &run, uint32_t s) {
    uint32_t boss = run.get(0x534874);
    if (!boss || !run.call(0x405f80, boss)) {
        return 0;
    }
    if (!run.get(run.get(0x534874) + 0x4b8)) {
        run.call(0x493450, s);
    }
    run.call(0x4c82a0, run.get(s + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (run.get(run.get(0x534874) + 0x4b4)) {
        run.call(0x493110, s);
    }
    uint32_t state = run.get(s + 0x184);
    if (state && s32(state) > 2 && s32(state) <= 4) {
        if (run.getd(s + 0x68) >= double(s32(run.get(run.get(0x537e88) + 0x4c)))) {
            if (run.get(0x537210) - run.get(s + 0x41c) >= run.get(s + 0x420)) {
                run.call(0x492f70, s);
            }
        }
    }
    return 0;
}

// 0x493030. Attack animation and its hit rectangle.
uint32_t function_493030(Run &run, uint32_t s) {
    run.call(0x4c82a0, run.get(s + 0x12c) + 0x188, {run.get(0x5430c4)});
    frameRectangle(run, s);
    if (completed(run, s)) {
        run.vcall(s, 0x48);
    }
    return 0;
}

// 0x493200. Timed reversal and attack completion.
uint32_t function_493200(Run &run, uint32_t s) {
    uint32_t boss = run.get(0x534874);
    if (!boss || !run.call(0x405f80, boss)) {
        return 0;
    }
    if (run.get(0x537210) - run.get(s + 0x43c) < run.get(s + 0x440)) {
        return 0;
    }
    run.call(0x4c82a0, run.get(s + 0x12c) + 0x188, {run.get(0x5430c4)});
    frameRectangle(run, s);
    uint32_t sprite = run.get(s + 0x12c);
    uint32_t animation = sprite + 0x188;
    if (run.get(sprite + 0x1a4) && !run.get(animation + 0x14)) {
        if (animation) {
            run.call(0x4c8260, animation, {1});
        }
        sprite = run.get(s + 0x12c);
        bool facing = (run.get8(sprite + 0x40) & 2) != 0;
        uint32_t left = run.get(s + 0x138);
        uint32_t right = run.get(s + 0x140);
        run.put(s + 0x138, 0u - right);
        run.put(s + 0x140, 0u - left);
        if (facing) {
            run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffdu);
        } else {
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
        }
        sprite = run.get(s + 0x12c);
        uint32_t spriteLeft = run.get(sprite + 0x118);
        if (spriteLeft != 0x80000000u) {
            uint32_t spriteRight = run.get(sprite + 0x120);
            run.put(sprite + 0x118, 0u - spriteRight);
            run.put(sprite + 0x120, 0u - spriteLeft);
        }
        run.call(0x406150, sprite);
        run.call(0x406180, sprite);
    }
    if (!run.get(run.get(0x534874) + 0x4b4)) {
        rectangle(run, s, s + 0x210);
        run.vcall(s, 0x48);
    }
    return 0;
}

// 0x493600. Respawn state entry.
uint32_t function_493600(Run &run, uint32_t s) {
    uint32_t sound = run.get(s + 0x444);
    if (sound && run.get(0x532c0c)) {
        original(run, 0x4b45f0, run.get(sound + 0x10), 0x18, {run.get(0x532c10), 0, 0, 0});
    }
    enterState(run, s, 0x52c8f4, 0x40c);
    uint32_t sprite = run.get(s + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xffffff7fu);
    return 0;
}

// 0x493550. Splash once, then enter respawn when the boss permits it.
uint32_t function_493550(Run &run, uint32_t s) {
    uint32_t boss = run.get(0x534874);
    if (!boss || !run.call(0x405f80, boss)) {
        return 0;
    }
    run.call(0x4c82a0, run.get(s + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (!run.get(s + 0x458)) {
        uint32_t object = run.get(s + 0xc);
        run.put(s + 0x458, 1);
        uint32_t z = run.get(object + 0x64) + 2;
        uint32_t y = run.get(object + 0x124);
        uint32_t x = run.get(object + 0x4c);
        uint32_t scene = run.get(object + 0xc);
        run.call(0x461c40, 0, {scene, x, y, z});
    }
    boss = run.get(0x534874);
    if (run.get(boss + 0x4b8)) {
        if (run.get(boss + 0x4b4) || run.get(0x537210) - run.get(s + 0x414) >= run.get(s + 0x418)) {
            run.frame -= 0x8;
            function_493600(run, s);
            run.frame += 0x8;
        }
    }
    return 0;
}

// 0x493680. Respawn animation completion.
uint32_t function_493680(Run &run, uint32_t s) {
    if (run.get(0x534874)) {
        run.call(0x4c82a0, run.get(s + 0x12c) + 0x188, {run.get(0x5430c4)});
        if (completed(run, s)) {
            run.vcall(s, 0x48);
        }
    }
    return 0;
}

// 0x493830. Begin grabbing Claw.
uint32_t function_493830(Run &run, uint32_t s) {
    enterState(run, s, 0x52c8e4, 0x408);
    run.call(0x41fce0, 0);
    run.put(0x53ca2c, 1);
    return 0;
}

// 0x493920. Enter squeeze and initialize its clocks and counters.
uint32_t function_493920(Run &run, uint32_t s) {
    enterState(run, s, 0x52c8d8, 0x410);
    uint32_t state = run.get(s + 0x10);
    run.put(s + 0x18, 0x493be0);
    uint32_t token = run.get(state + 0x1c);
    run.put(s + 0x1c, token);
    run.put(s + 0x438, 0xbb8);
    run.put(s + 0x434, run.get(0x537210));
    run.put(s + 0x44c, 0);
    run.put(s + 0x450, 0);
    return 0;
}

// Explicit FLD/FSUB/FTOL sequence: preserve extended operands and conversion status.
uint32_t coordinate(Run &run, ClawX87State &fp, uint32_t value, uint32_t offset) {
    run.x87_step(CLAW_X87_F64, fp, {run.get(value), run.get(value + 0x4)});
    run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(offset), run.get(offset + 0x4)});
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

// 0x493890. Finish grab, place Claw relative to the tentacle and start squeeze.
uint32_t function_493890(Run &run, uint32_t s) {
    run.call(0x4c82a0, run.get(s + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (completed(run, s)) {
        uint32_t player = run.get(0x537e88);
        uint32_t state = run.get(player + 0x6c);
        run.call(0x418120, 0, {player, state, run.get(state + 0x14)});
        ClawX87State fp{};
        fp.size = sizeof(fp);
        fp.version = CLAW_X87_VERSION;
        fp.control = 0x023f;
        player = run.get(0x537e88);
        uint32_t x = coordinate(run, fp, s + 0x68, 0x50f998);
        run.put(player + 0x4c, x);
        player = run.get(0x537e88);
        uint32_t y = coordinate(run, fp, s + 0x70, 0x50f9a0);
        run.put(player + 0x50, y);
        run.frame -= 0xc;
        function_493920(run, s);
        run.frame += 0xc;
    }
    return 0;
}

// 0x4939a0. Squeeze input escape, damage pulses and corresponding player frames.
uint32_t function_4939a0(Run &run, uint32_t s) {
    uint32_t input = run.get(0x537204);
    if (!input) {
        return 0;
    }
    if (run.get(input + 0x4) & 0x0f000fffu) {
        run.put(s + 0x450, run.get(s + 0x450) + 1);
    }
    uint32_t player = run.get(0x537e88);
    uint32_t state = run.get(player + 0x6c);
    if (run.get(state + 0x1c) != 0x1390 || run.get(0x537210) - run.get(s + 0x434) >= run.get(s + 0x438) || s32(run.get(s + 0x450)) >= 10) {
        original(run, 0x41fe80, 0, 0xc);
        run.put(0x53ca2c, 0);
        run.vcall(s, 0x48);
        return 0;
    }
    uint32_t now = run.get(0x537210);
    if (now - run.get(s + 0x42c) >= run.get(s + 0x430)) {
        if (run.get(0x534eac) != 0x26bd) {
            run.put(player + 0x10c, run.get(player + 0x10c) - 1);
        }
        uint32_t count = run.get(s + 0x44c) + 1;
        run.put(s + 0x44c, count);
        player = run.get(0x537e88);
        if (s32(run.get(player + 0x10c)) <= 0) {
            original(run, 0x41fe80, 0, 0xc);
            run.put(0x53ca2c, 0);
            run.vcall(s, 0x48);
            player = run.get(0x537e88);
            state = run.get(player + 0x6c);
            original(run, 0x417b00, 0, 0x1c, {player, state, run.get(state + 0x14), 1});
        } else if (s32(count) >= 20) {
            original(run, 0x41fe80, 0, 0xc);
            player = run.get(0x537e88);
            run.put(0x53ca2c, 0);
            state = run.get(player + 0x6c);
            original(run, 0x417930, 0, 0x1c, {player, state, run.get(state + 0x14), 0});
        }
        run.put(s + 0x430, 100);
        run.put(s + 0x42c, run.get(0x537210));
    }
    run.call(0x4c82a0, run.get(s + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t frame = run.get(run.get(s + 0x12c) + 0x16c);
    uint32_t requested;
    if (frame == 0x12e) {
        requested = 0x1c2;
    } else if (frame == 0x12f) {
        requested = 0x1c3;
    } else if (frame == 0x130) {
        requested = 0x1c4;
    } else {
        return 0;
    }
    player = run.get(0x537e88);
    uint32_t table = run.get(player + 0x170);
    if (!table) {
        return 0;
    }
    if (s32(run.get(table + 0x64)) <= s32(requested) && s32(run.get(table + 0x68)) >= s32(requested)) {
        uint32_t data = run.get(table + 0x14);
        run.put(player + 0x174, run.get(data + requested * 4));
        run.put(player + 0x16c, requested);
    } else {
        run.put(player + 0x174, 0);
        run.put(player + 0x16c, requested);
    }
    return 0;
}

// 0x493be0. Squeeze state's cleanup callback.
uint32_t function_493be0(Run &run) {
    run.call(0x41fe80, 0);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *) {
    switch (function) {
    case 0x492ec0: return function_492ec0(run, receiver);
    case 0x493030: return function_493030(run, receiver);
    case 0x493200: return function_493200(run, receiver);
    case 0x493550: return function_493550(run, receiver);
    case 0x493600: return function_493600(run, receiver);
    case 0x493680: return function_493680(run, receiver);
    case 0x493830: return function_493830(run, receiver);
    case 0x493890: return function_493890(run, receiver);
    case 0x493920: return function_493920(run, receiver);
    case 0x4939a0: return function_4939a0(run, receiver);
    case 0x493be0: return function_493be0(run);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_twelve_tentacle_states_01_entry, owned, body)
