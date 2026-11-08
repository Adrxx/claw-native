// Level 9 PegLeg roll and collision helpers
//
// Recovered behavior from the original v1.0 packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x46a000:
        return 0;
    case 0x46a040:
        return 0;
    case 0x46a1c0:
        return 0;
    case 0x46a280:
        return 0;
    case 0x46a420:
        return 1;
    case 0x46a430:
        return 1;
    case 0x46a5b0:
        return 0;
    case 0x46a610:
        return 0;
    case 0x46a650:
        return 0;
    case 0x46a690:
        return 1;
    default:
        return -1;
    }
}

// Registry global fields: +0x08/+0x0c index bounds, +0x10 data,
// +0x14 fallback, +0x18 stride, +0x1c temporary string slots, +0x20 count.
void releaseRegistrySlots(Run &run) {
    uint32_t count = run.get(0x5376b8);
    uint32_t slot = run.get(0x5376b4);
    while (count != 0) {
        if (slot)
            run.call(0x4f6439, slot);
        slot += 4;
        --count;
    }
}

uint32_t stateName(Run &run, uint32_t receiver, bool second) {
    uint32_t state = run.get(run.get(receiver + 0x10) + 0x1c);
    uint32_t low = run.get(0x5376a0);
    run.put(0x5376b8, 0);
    uint32_t entry;
    if (s32(state) >= s32(low) && s32(state) <= run.gets(0x5376a4)) {
        entry = (state - low) * run.get(0x5376b0) + run.get(0x5376a8);
    } else {
        uint32_t found = run.call(0x4db6e0, 0x537698, {state, 0});
        if (found) {
            uint32_t base = run.get(0x5376a0);
            uint32_t data = run.get(0x5376a8);
            entry = (state - base) * run.get(0x5376b0) + data;
        } else {
            uint32_t message = run.get(0x544b4c);
            if (!second) {
                run.call(0x406da0, 0x537698, {message, 0xc});
            } else {
                uint32_t result = run.call(0x4db5f0, 0);
                uint32_t handler = run.get(0x53769c);
                run.put(0x544b14, result);
                run.call(0x4db4d0, handler, {0x537698, message, 0xc});
            }
            entry = run.get(0x5376ac);
        }
    }
    releaseRegistrySlots(run);
    return entry;
}

// Actor fields: +0x0c scene, +0x10 state holder, +0x50 horizontal velocity,
// +0x68 horizontal position, +0x80/+0x98 endpoints, +0x128 sprite view,
// +0x12c sprite, +0x18c direction, +0x49c/+0x4a0 cooldown origin/duration.
// 0x46a000. thiscall, 0 stack argument(s), returns u32.
uint32_t function_46a000(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x128, 0xffffffec);
    run.put(sprite + 0x12c, 0xffffffce);
    run.put(sprite + 0x130, 0x14);
    run.put(sprite + 0x134, 0x32);
    return 0;
}

// 0x46a040. thiscall, 0 stack argument(s), returns u32.
uint32_t function_46a040(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(0x537210) - run.get(receiver + 0x49c) < run.get(receiver + 0x4a0)) {
        run.vcall(receiver, 0x44);
        return 0;
    }
    uint32_t view = receiver + 0x128;
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t sprite = run.get(view + 0x4);
        if ((run.get8(sprite + 0x40) & 2) == 0) {
            uint32_t left = run.get(view + 0x10);
            uint32_t right = run.get(view + 0x18);
            run.put(view + 0x10, 0u - right);
            run.put(view + 0x18, 0u - left);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            run.call(0x4060b0, run.get(view + 0x4));
        }
    } else {
        run.call(0x406310, view);
    }
    run.putd(receiver + 0x50, run.get(receiver + 0x18c) == 2 ? -250.0 : 250.0);
    uint32_t direction = run.get(receiver + 0x18c);
    uint32_t position = run.call_x87(0x4a30e0, 0, run.getd(receiver + 0x68));
    run.put(receiver + 0x4bc, position + (direction == 2 ? 0xffffff6au : 150u));
    bool endpoint = false;
    if (direction == 2) {
        double x = run.getd(receiver + 0x68);
        double end = run.getd(receiver + 0x80);
        endpoint = !(x < end || x > end);
    }
    if (!endpoint && direction == 3) {
        double x = run.getd(receiver + 0x68);
        double end = run.getd(receiver + 0x98);
        endpoint = !(x < end || x > end);
    }
    if (endpoint) {
        run.vcall(receiver, 0x58);
        return 0;
    }
    uint32_t sound = run.get(receiver + 0x490);
    if (sound && run.get(0x532c0c)) {
        uint32_t message = run.get(0x532c10);
        run.call(0x4b45f0, run.get(sound + 0x10), {message, 0, 0, 0});
    }
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x529c6c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(view + 0x4);
    uint32_t animation = run.get(receiver + 0x454);
    run.put(view + 0xc, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    run.put(receiver + 0x4b8, 0x5dc);
    run.put(receiver + 0x4b4, run.get(0x537210));
    return 0;
}

// 0x46a1c0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_46a1c0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t delta = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {delta});
    run.putd(receiver + 0x50, run.get(receiver + 0x18c) == 2 ? -250.0 : 250.0);
    uint32_t direction = run.get(receiver + 0x18c);
    bool stop = false;
    if (direction == 2) {
        double position = run.getd(receiver + 0x68);
        double limit = double(run.gets(receiver + 0x4bc));
        stop = limit >= position;
    }
    if (!stop && direction == 3) {
        double position = run.getd(receiver + 0x68);
        double limit = double(run.gets(receiver + 0x4bc));
        stop = !(limit > position);
    }
    if (!stop) {
        double position = run.getd(receiver + 0x68);
        double end = run.getd(receiver + 0x80);
        bool endpoint = !(position < end || position > end);
        if (!endpoint) {
            position = run.getd(receiver + 0x68);
            end = run.getd(receiver + 0x98);
            endpoint = !(position < end || position > end);
        }
        if (endpoint)
            run.vcall(receiver, 0x58);
        stop = run.get(0x537210) - run.get(receiver + 0x4b4) >= run.get(receiver + 0x4b8);
    }
    if (stop)
        run.vcall(receiver, 0x58);
    return 0;
}

// 0x46a280. thiscall, 0 stack argument(s), returns u32.
uint32_t function_46a280(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t name = stateName(run, receiver, false);
    if (run.call(0x4a3810, 0, {run.get(name), 0x529c7c}) == 0)
        return 0;
    name = stateName(run, receiver, true);
    if (run.call(0x4a3810, 0, {run.get(name), 0x529c6c}) == 0)
        return 0;
    return run.call(0x44df60, receiver);
}

// 0x46a420. thiscall, 1 stack argument(s), returns void.
uint32_t function_46a420(Run &run, uint32_t receiver, const uint32_t *) {
    return run.call(0x469c40, receiver);
}

uint32_t function_46a5b0(Run &run, uint32_t receiver, const uint32_t *);

// 0x46a430. thiscall, 1 stack argument(s), returns void.
uint32_t function_46a430(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x43e9c0, receiver, {0x12c});
    uint32_t name = run.call(0x441030, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
    releaseRegistrySlots(run);
    bool hit = run.call(0x4a3810, 0, {run.get(name), 0x523204}) == 0;
    if (!hit) {
        name = run.call(0x441030, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
        releaseRegistrySlots(run);
        hit = run.call(0x4a3810, 0, {run.get(name), 0x523210}) == 0;
    }
    if (hit) {
        run.vcall(receiver, 0x44);
        return 0;
    }
    uint32_t player = run.get(0x537e88);
    uint32_t actor = run.get(player + 0x6c);
    uint32_t attack = run.get(run.get(actor + 0x14) + 0x3c);
    switch (attack) {
    case 7:
        function_46a5b0(run, receiver, nullptr);
        return 0;
    case 1:
    case 2:
    case 3:
    case 4:
    case 8:
    case 13: {
        int32_t chance = s32(run.call(0x4a3050, 0)) % 101;
        if (chance >= 50 && run.get(0x537210) - run.get(receiver + 0x49c) >= run.get(receiver + 0x4a0))
            return 0;
        run.call(0x44f510, receiver);
        run.vcall(receiver, 0x28, {arguments[0]});
        run.call(0x440e20, receiver, {arguments[0]});
        return 0;
    }
    default:
        run.call(0x44d460, receiver, {arguments[0]});
        return 0;
    }
}

// 0x46a5b0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_46a5b0(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(0x537210) - run.get(receiver + 0x49c) < run.get(receiver + 0x4a0))
        return 0;
    uint32_t result = run.call(0x44f3c0, receiver);
    run.put(receiver + 0x4a0, 0x7d0);
    run.put(receiver + 0x49c, run.get(0x537210));
    uint32_t scene = run.get(receiver + 0xc);
    uint32_t target = run.get(scene + 0x74);
    run.vcall(receiver, 0x28, {target});
    run.call(0x440e20, receiver, {target});
    return result;
}

// 0x46a610. thiscall, 0 stack argument(s), returns u32.
uint32_t function_46a610(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t random = run.call(0x4a3050, 0);
    uint32_t scene = run.get(receiver + 0xc);
    uint32_t index = uint32_t(s32(random) % 4);
    uint32_t animation = run.get(receiver + 0x460 + index * 4);
    run.call(0x48ce40, 0, {scene, animation, 0});
    function_46a000(run, receiver, nullptr);
    run.call(0x440420, receiver);
    return 0;
}

// 0x46a650. thiscall, 0 stack argument(s), returns void.
uint32_t function_46a650(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x4d8) == 0) {
        run.put(receiver + 0x4d8, 1);
        run.put(receiver + 0x260, run.get(receiver + 0x270));
        run.put(receiver + 0x264, run.get(receiver + 0x274));
        run.put(receiver + 0x268, run.get(receiver + 0x278));
        run.put(receiver + 0x26c, run.get(receiver + 0x27c));
    }
    return run.call(0x44dbb0, receiver);
}

// 0x46a690. thiscall, 1 stack argument(s), returns void.
uint32_t function_46a690(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t target = arguments[0];
    if (target && run.get(target + 0xd0) != 0x20) {
        uint32_t scene = run.get(receiver + 0xc);
        uint32_t health = run.get(scene + 0x10c);
        if (s32(health) > 0)
            run.put(scene + 0x10c, health - run.get(target + 0x104));
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x46a000:
        return function_46a000(run, receiver, arguments);
    case 0x46a040:
        return function_46a040(run, receiver, arguments);
    case 0x46a1c0:
        return function_46a1c0(run, receiver, arguments);
    case 0x46a280:
        return function_46a280(run, receiver, arguments);
    case 0x46a420:
        return function_46a420(run, receiver, arguments);
    case 0x46a430:
        return function_46a430(run, receiver, arguments);
    case 0x46a5b0:
        return function_46a5b0(run, receiver, arguments);
    case 0x46a610:
        return function_46a610(run, receiver, arguments);
    case 0x46a650:
        return function_46a650(run, receiver, arguments);
    case 0x46a690:
        return function_46a690(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_nine_peg_leg_roll_01_entry, owned, body)
