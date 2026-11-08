// Level 13 Red Tail jump and death
//
// Canonical guest-memory translation of the owned Red Tail state handlers.
#include "ClawRuntime.hpp"
#include <cmath>

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x481880:
        return 1;
    case 0x481c10:
        return 0;
    case 0x481c90:
        return 1;
    case 0x481f70:
        return 0;
    case 0x481fe0:
        return 0;
    case 0x482090:
        return 0;
    case 0x482180:
        return 0;
    case 0x4821c0:
        return 1;
    case 0x482260:
        return 0;
    case 0x482380:
        return 0;
    default:
        return -1;
    }
}

// Object fields: +0x0c actor, +0x10 logic, +0x18 callback, +0x20 state,
// +0x38/40/48 acceleration, +0x50/58/60 velocity, +0x68/70/78 position,
// +0x12c sprite, +0x134 saved frame, +0x138/140 mirrored bounds,
// +0x460 continuation, +0x4e8/4ec death progress, +0x4e0 defeated.
uint32_t function_481fe0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_481c90(Run &run, uint32_t receiver, const uint32_t *arguments);

void sound(Run &run, uint32_t receiver, uint32_t offset) {
    uint32_t handle = run.get(receiver + offset);
    if (handle && run.get(0x532c0c)) {
        run.call(0x4b45f0, run.get(handle + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
}

void animation(Run &run, uint32_t receiver, uint32_t name, uint32_t field) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t value = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(receiver + 0x10) + 0x1c, value);
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t speed = run.get(receiver + field);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {speed});
}

void mirror(Run &run, uint32_t receiver, uint32_t sprite, bool set) {
    uint32_t previous = run.get(receiver + 0x138);
    uint32_t opposite = run.get(receiver + 0x140);
    run.put(receiver + 0x138, 0u - opposite);
    run.put(receiver + 0x140, 0u - previous);
    uint32_t flags = run.get(sprite + 0x40);
    run.put(sprite + 0x40, set ? flags | 2u : flags & ~2u);
}

void trajectory(Run &run, uint32_t receiver, double x, double y, bool down) {
    double dx = x - run.getd(receiver + 0x68);
    double dy = y - run.getd(receiver + 0x70);
    double ax = run.getd(receiver + 0x38);
    double ay = run.getd(receiver + 0x40);
    double dz = -run.getd(receiver + 0x78);
    double az = run.getd(receiver + 0x48);
    double dot = (-ax * dx - ay * dy) - az * dz;
    double square = (ax * ax + ay * ay) + az * az;
    double distance = (dx * dx + dy * dy) + dz * dz;
    double speed = std::sqrt((std::sqrt((distance * square) * run.getd(0x50f320)) - dot * run.getd(0x50f328)) * run.getd(0x50f330));
    double epsilon = run.getd(0x513e20);
    if (!(speed >= epsilon)) {
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x60, 0);
        run.put(receiver + 0x54, 0);
        run.put(receiver + 0x5c, 0);
        run.put(receiver + 0x64, 0);
        return;
    }
    double q = square * run.getd(0x50f338);
    double vx;
    double vy;
    double vz;
    if (q < -epsilon || q > epsilon || std::isnan(q)) {
        double time = (speed * speed - dot) / (q + q);
        double root = std::sqrt(time);
        double scale = run.getd(0x50f330);
        vx = (dx - (time * ax) * scale) / root;
        vy = (dy - (time * ay) * scale) / root;
        vz = (dz - (time * az) * scale) / root;
    } else {
        double magnitude = down ? (std::fabs(dx) + std::fabs(dz)) + std::fabs(dy) : (std::fabs(dy) + std::fabs(dx)) + std::fabs(dz);
        vx = (dx / magnitude) * speed;
        vy = (dy / magnitude) * speed;
        vz = (dz / magnitude) * speed;
    }
    run.putd(receiver + 0x50, vx);
    run.putd(receiver + 0x58, vy);
    run.putd(receiver + 0x60, vz);
}

// 0x481880.
uint32_t function_481880(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!run.call(0x4824c0, receiver)) {
        run.call(0x481810, receiver, {arguments[0]});
        return 0;
    }
    run.put(receiver + 0x460, arguments[0]);
    uint32_t target = run.get(0x52b35c) - 0x96;
    if (run.get(run.get(receiver + 0x0c) + 0xcc) != 1) {
        return 0;
    }
    run.put(receiver + 0x18, 0x481fe0);
    run.put(receiver + 0x20, 1);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x5c, 0xc082c000);
    run.put(receiver + 0x64, 0);
    run.put(run.get(receiver + 0x0c) + 0xcc, 7);
    animation(run, receiver, 0x52b3c0, 0x33c);
    trajectory(run, receiver, run.getd(0x50f318), double(s32(target)), false);
    double x = run.getd(receiver + 0x68);
    double targetX = run.getd(0x50f318);
    bool flip = false;
    bool set = false;
    uint32_t sprite = 0;
    if ((targetX < x || std::isnan(targetX) || std::isnan(x)) && run.get(receiver + 0x18c) == 2) {
        sprite = run.get(receiver + 0x12c);
        flip = (run.get8(sprite + 0x40) & 2) != 0;
    } else if (targetX > x && run.get(receiver + 0x18c) == 3) {
        sprite = run.get(receiver + 0x12c);
        flip = (run.get8(sprite + 0x40) & 2) == 0;
        set = true;
    }
    if (flip) {
        mirror(run, receiver, sprite, set);
        sprite = run.get(receiver + 0x12c);
        run.call(0x406120, sprite);
        run.call(0x406150, sprite);
        run.call(0x406180, sprite);
    }
    sound(run, receiver, 0x40c);
    return 0;
}

// 0x481c10.
uint32_t function_481c10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t actor = run.get(receiver + 0x0c);
    if (run.get(actor + 0xcc) == 7 && double(s32(run.get(0x52b35c) - 0x4b)) > run.getd(receiver + 0x70)) {
        run.put(actor + 0xcc, 8);
    }
    if (run.get(run.get(receiver + 0x0c) + 0xcc) == 1) {
        function_481fe0(run, receiver, arguments);
        run.call(0x481810, receiver, {run.get(receiver + 0x460)});
    }
    return 0;
}

// 0x481c90.
uint32_t function_481c90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (run.call(0x4824c0, receiver)) {
        run.call(0x481810, receiver, {arguments[0]});
        return 0;
    }
    run.put(receiver + 0x460, arguments[0]);
    uint32_t target = uint32_t(s32(run.call(0x4a3050, 0)) % 0x12d) + 0x91e6;
    if (run.get(run.get(receiver + 0x0c) + 0xcc) != 1) {
        return 0;
    }
    run.put(receiver + 0x18, 0x481fe0);
    run.put(receiver + 0x20, 1);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x5c, 0x406f4000);
    run.put(receiver + 0x64, 0);
    run.put(run.get(receiver + 0x0c) + 0xcc, 7);
    animation(run, receiver, 0x52b3b4, 0x33c);
    trajectory(run, receiver, double(s32(target)), run.getd(0x50f348), true);
    sound(run, receiver, 0x40c);
    return 0;
}

// 0x481f70.
uint32_t function_481f70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t actor = run.get(receiver + 0x0c);
    if (run.get(actor + 0xcc) == 7 && run.getd(receiver + 0x70) > run.getd(0x50f350)) {
        run.put(actor + 0xcc, 8);
    }
    if (run.get(run.get(receiver + 0x0c) + 0xcc) == 1) {
        function_481fe0(run, receiver, arguments);
        run.call(0x481810, receiver, {run.get(receiver + 0x460)});
    }
    return 0;
}

// 0x481fe0.
uint32_t function_481fe0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x5c, 0);
    run.putd(receiver + 0x80, double(run.gets(0x52b354)));
    run.putd(receiver + 0x98, double(run.gets(0x52b358)));
    run.putd(receiver + 0xa0, double(run.gets(0x52b360)));
    uint32_t actor = run.get(receiver + 0x0c);
    if (run.get(actor + 0xcc) == 7) {
        run.put(actor + 0xcc, 8);
    }
    double floor = double(s32(run.get(0x52b360) - 0x37));
    if (run.getd(receiver + 0x70) > floor) {
        run.putd(receiver + 0x70, floor);
    }
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x08, run.get(sprite + 0x08) & ~1u);
    sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x08, run.get(sprite + 0x08) & ~4u);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x4bc, 0x2ee);
    run.put(receiver + 0x4b8, run.get(0x537210));
    return 0;
}

// 0x482090.
uint32_t function_482090(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t sprite = run.get(receiver + 0x12c);
        if (!(run.get8(sprite + 0x40) & 2)) {
            mirror(run, receiver, sprite, true);
            run.call(0x4060b0, run.get(receiver + 0x12c));
        }
    } else {
        run.call(0x406310, receiver + 0x128);
    }
    animation(run, receiver, 0x526a38, 0x47c);
    sound(run, receiver, 0x4a4);
    if (s32(run.call(0x4a3050, 0)) % 0x65 < 0x21) {
        uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 3);
        uint32_t actor = run.get(receiver + 0x0c);
        run.call(0x48ce40, 0, {actor, run.get(receiver + index * 4 + 0x49c), 0});
    }
    return 0;
}

// 0x482180.
uint32_t function_482180(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t sprite = run.get(receiver + 0x12c);
    if (run.get(sprite + 0x1a4) && !run.get(sprite + 0x19c)) {
        run.vcall(receiver, 0x44);
    }
    return 0;
}

// 0x4821c0.
uint32_t function_4821c0(Run &run, uint32_t receiver, const uint32_t *) {
    if (!run.call(0x4824c0, receiver)) {
        const uint32_t arguments[] = {6};
        function_481c90(run, receiver, arguments);
        return 0;
    }
    animation(run, receiver, 0x5234f4, 0x374);
    run.put(receiver + 0x20, 1);
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x08, run.get(sprite + 0x08) | 0x80);
    sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x08, run.get(sprite + 0x08) | 4);
    run.put(receiver + 0x4e8, 0);
    run.put(receiver + 0x4ec, 0);
    return 0;
}

// 0x482260.
uint32_t function_482260(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (!run.get(receiver + 0x4e8)) {
        if (!run.call(0x48cf90, 0, {run.get(receiver + 0x0c)})) {
            run.call(0x48ce40, 0, {run.get(receiver + 0x0c), run.get(receiver + 0x3a4), 0});
            run.put(receiver + 0x4e8, 1);
        }
    }
    uint32_t sprite = run.get(receiver + 0x12c);
    if (run.get(sprite + 0x1a4) && !run.get(sprite + 0x19c) && !run.get(receiver + 0x4ec) && run.get(receiver + 0x4e8)) {
        if (!run.call(0x48cf90, 0, {run.get(receiver + 0x0c)})) {
            run.put(receiver + 0x4ec, run.get(receiver + 0x4ec) + 1);
            if (run.gets(run.get(0x537e88) + 0x10c) > 0) {
                uint32_t length = run.get(receiver + 0x2fc);
                if (length < 5) {
                    run.call(0x4dbd20, receiver + 0x2f4, {4});
                } else {
                    uint32_t data = length <= 0x20 ? receiver + 0x300 : run.get(receiver + 0x300);
                    run.put(data, run.get(data) | 0x10);
                }
                run.call(0x420590, 0);
                run.call(0x40e5c0, receiver);
                run.call(0x48cf50, 0, {run.get(receiver + 0x0c)});
                run.put(receiver + 0xc8, 1);
                run.put(receiver + 0x4e0, 1);
            }
        }
    }
    return 0;
}

// 0x482380.
uint32_t function_482380(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x4e0)) {
        return run.vcall(receiver, 0x44);
    }
    run.put(run.get(receiver + 0x0c) + 0xcc, 7);
    run.call(0x40e560, receiver);
    run.vcall(receiver, 0x24);
    run.put(run.get(receiver + 0x0c) + 0xcc, 8);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x5c, 0);
    run.put(receiver + 0x64, 0);
    run.put(receiver + 0x38, 0);
    run.put(receiver + 0x3c, 0);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0x409f4000);
    run.put(run.get(receiver + 0x0c) + 0x10c, 100);
    uint32_t actor = run.get(receiver + 0x0c);
    double health = double(run.gets(actor + 0x10c));
    double scaled = health * double(run.getf(0x5262b4));
    uint32_t value = run.call_x87(0x4a30e0, 0, scaled);
    run.put(actor + 0x10c, value);
    uint32_t method = run.get(run.get(receiver) + 0x44);
    run.put(receiver + 0x4e4, 0);
    run.put(receiver + 0x4ec, 0);
    run.put(receiver + 0x504, 0);
    return run.call(method, receiver);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x481880:
        return function_481880(run, receiver, arguments);
    case 0x481c10:
        return function_481c10(run, receiver, arguments);
    case 0x481c90:
        return function_481c90(run, receiver, arguments);
    case 0x481f70:
        return function_481f70(run, receiver, arguments);
    case 0x481fe0:
        return function_481fe0(run, receiver, arguments);
    case 0x482090:
        return function_482090(run, receiver, arguments);
    case 0x482180:
        return function_482180(run, receiver, arguments);
    case 0x4821c0:
        return function_4821c0(run, receiver, arguments);
    case 0x482260:
        return function_482260(run, receiver, arguments);
    case 0x482380:
        return function_482380(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_thirteen_red_tail_jump_death_01_entry, owned, body)
