// Level 13 red tail control
//
// Recovered from the original v1.0 instructions.
#include "ClawRuntime.hpp"
#include <cmath>

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x482430:
        return 0;
    case 0x482440:
        return 1;
    case 0x482460:
        return 1;
    case 0x482470:
        return 1;
    case 0x482480:
        return 1;
    case 0x4824c0:
        return 0;
    case 0x4824f0:
        return 0;
    case 0x482510:
        return 0;
    case 0x482550:
        return 1;
    case 0x482620:
        return 0;
    case 0x4827a0:
        return 1;
    default:
        return -1;
    }
}

// 0x482430. thiscall, 0 stack argument(s), returns void.
uint32_t function_482430(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x40e5b0, receiver);
    run.put(0x53c19c, 0);
    return 0;
}

// 0x482440. thiscall, 1 stack argument(s), returns void.
uint32_t function_482440(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (arguments[0]) {
        run.put(arguments[0] + 0x08, run.get(arguments[0] + 0x08) | 0x10000);
    }
    run.call(0x482090, receiver);
    return 0;
}

// 0x482460. thiscall, 1 stack argument(s), returns void.
uint32_t function_482460(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x482090, receiver);
    return 0;
}

// 0x482470. thiscall, 1 stack argument(s), returns void.
uint32_t function_482470(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // +0x20 state, +0x14 state callback.
    if (run.gets(receiver + 0x20) >= 2) {
        run.put(receiver + 0x14, 0x4817c0);
    }
    return 0;
}

// 0x482480. thiscall, 1 stack argument(s), returns void.
uint32_t function_482480(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // +0x504 repeated-hit count.
    uint32_t count = run.get(receiver + 0x504) + 1;
    run.put(receiver + 0x504, count);
    if (s32(count) < 3) {
        run.call(0x44d460, receiver, {arguments[0]});
    } else {
        uint32_t state = run.get(receiver + 0x20);
        run.put(receiver + 0x504, 0);
        if (s32(state) >= 2) {
            run.put(receiver + 0x14, 0x481790);
        }
    }
    return 0;
}

// 0x4824c0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4824c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // +0x70 vertical position; +0x0c behavior object, +0xcc behavior mode.
    double position = run.getd(receiver + 0x70);
    double boundary = double(run.gets(0x52b35c));
    if ((boundary < position || std::isnan(position)) && run.get(run.get(receiver + 0x0c) + 0xcc) == 1) {
        return 1;
    }
    return 0;
}

// 0x4824f0. cdecl, 0 stack argument(s), returns u32.
uint32_t function_4824f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    (void)receiver;
    // Global player +0x50 integer horizontal position.
    uint32_t position = run.get(run.get(0x537e88) + 0x50);
    return s32(position) > run.gets(0x52b35c) ? 1 : 0;
}

// 0x482510. thiscall, 0 stack argument(s), returns u32.
uint32_t function_482510(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (function_4824f0(run, 0, nullptr) && function_4824c0(run, receiver, nullptr)) {
        return 1;
    }
    if (!function_4824f0(run, 0, nullptr) && !function_4824c0(run, receiver, nullptr)) {
        return 1;
    }
    return 0;
}

// 0x482550. thiscall, 1 stack argument(s), returns u32.
uint32_t function_482550(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // +0x18c facing; +0x128 sprite controller; +0x12c sprite.
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t sprite = run.get(receiver + 0x12c);
        if (!(run.get8(sprite + 0x40) & 2)) {
            uint32_t left = run.get(receiver + 0x138);
            uint32_t right = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0u - right);
            run.put(receiver + 0x140, 0u - left);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            sprite = run.get(receiver + 0x12c);
            run.call(0x406120, sprite);
            run.call(0x406150, sprite);
            run.call(0x406180, sprite);
        }
    } else {
        run.call(0x406310, receiver + 0x128);
    }
    // +0x460 pending action; +0x404 integer speed; +0x50 horizontal velocity.
    run.put(receiver + 0x460, arguments[0]);
    uint32_t speed = run.get(receiver + 0x404);
    if (run.get(receiver + 0x18c) == 3) {
        speed = 0u - speed;
    }
    run.putd(receiver + 0x50, double(s32(speed)));
    // +0x10 animation object, +0x24 saved animation; animation +0x1c selection.
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t selection = run.call(0x4dba00, 0x537668, {0x527d84});
    run.put(run.get(receiver + 0x10) + 0x1c, selection);
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t advance = run.get(receiver + 0x30c);
    // +0x134 saved sprite clock; sprite +0x190 clock, +0x188 timer.
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {advance});
    return 0;
}

// 0x482620. thiscall, 0 stack argument(s), returns u32.
uint32_t function_482620(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // +0x68 current position, +0x80 and +0x98 limits.
    double position = run.getd(receiver + 0x68);
    double boundary = run.getd(receiver + 0x80);
    bool atFirst = position == boundary || std::isnan(position) || std::isnan(boundary);
    bool change = atFirst && run.get(receiver + 0x18c) == 3;
    if (!change) {
        position = run.getd(receiver + 0x68);
        boundary = run.getd(receiver + 0x98);
        bool atSecond = position == boundary || std::isnan(position) || std::isnan(boundary);
        change = atSecond && run.get(receiver + 0x18c) == 2;
    }
    if (change) {
        run.call(0x481810, receiver, {run.get(receiver + 0x460)});
    }
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t sprite = run.get(receiver + 0x12c);
        if (!(run.get8(sprite + 0x40) & 2)) {
            uint32_t left = run.get(receiver + 0x138);
            uint32_t right = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0u - right);
            run.put(receiver + 0x140, 0u - left);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            sprite = run.get(receiver + 0x12c);
            run.call(0x406120, sprite);
            run.call(0x406150, sprite);
            run.call(0x406180, sprite);
        }
    } else {
        uint32_t sprite = run.get(receiver + 0x12c);
        if (run.get8(sprite + 0x40) & 2) {
            uint32_t left = run.get(receiver + 0x138);
            uint32_t right = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0u - right);
            run.put(receiver + 0x140, 0u - left);
            run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffdu);
            run.call(0x4060b0, run.get(receiver + 0x12c));
        }
    }
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    // +0x184 action state.
    uint32_t action = run.get(receiver + 0x184);
    if (action == 4) {
        run.call(0x481810, receiver, {run.get(receiver + 0x460)});
        return 0;
    }
    if (action == 6) {
        run.call(0x44edd0, receiver);
        return 0;
    }
    if (action > 5) {
        return 0;
    }
    uint32_t speed = run.get(receiver + 0x404);
    if (run.get(receiver + 0x18c) == 3) {
        speed = 0u - speed;
    }
    run.putd(receiver + 0x50, double(s32(speed)));
    return 0;
}

// 0x4827a0. thiscall, 1 stack argument(s), returns void.
uint32_t function_4827a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x44d000, receiver, {arguments[0]});
    double position = run.getd(receiver + 0x70);
    double boundary = run.getd(0x50f358);
    if (position > boundary) {
        run.put(receiver + 0x70, 0);
        run.put(receiver + 0x74, 0x40a04a00);
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x60, 0);
        run.put(receiver + 0x54, 0);
        run.put(receiver + 0x5c, 0);
        run.put(receiver + 0x64, 0);
        // +0x38 through +0x44 movement accumulators.
        run.put(receiver + 0x38, 0);
        run.put(receiver + 0x3c, 0);
        run.put(receiver + 0x40, 0);
        run.put(receiver + 0x44, 0);
        run.put(run.get(receiver + 0x0c) + 0xcc, 7);
        run.vcall(receiver, 0x24);
        run.put(receiver + 0x40, 0);
        run.put(receiver + 0x44, 0x409f4000);
        run.put(run.get(receiver + 0x0c) + 0xcc, 8);
        run.vcall(receiver, 0x44);
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x482430:
        return function_482430(run, receiver, arguments);
    case 0x482440:
        return function_482440(run, receiver, arguments);
    case 0x482460:
        return function_482460(run, receiver, arguments);
    case 0x482470:
        return function_482470(run, receiver, arguments);
    case 0x482480:
        return function_482480(run, receiver, arguments);
    case 0x4824c0:
        return function_4824c0(run, receiver, arguments);
    case 0x4824f0:
        return function_4824f0(run, receiver, arguments);
    case 0x482510:
        return function_482510(run, receiver, arguments);
    case 0x482550:
        return function_482550(run, receiver, arguments);
    case 0x482620:
        return function_482620(run, receiver, arguments);
    case 0x4827a0:
        return function_4827a0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_thirteen_red_tail_control_01_entry, owned, body)
