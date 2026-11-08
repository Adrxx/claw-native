// Tiger guard state callbacks, recovered from the original v1.0 bodies.
#include "ClawRuntime.hpp"
#include <cmath>

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4953b0:
    case 0x4955c0:
    case 0x4959e0:
    case 0x495a30:
    case 0x495a40:
        return 1;
    case 0x495280:
    case 0x4954f0:
    case 0x495710:
    case 0x4957f0:
    case 0x495940:
    case 0x495a60:
    case 0x495ac0:
    case 0x495ae0:
    case 0x495ba0:
        return 0;
    default:
        return -1;
    }
}

// FCOMP's C3 flag is set for equality and for unordered operands.
bool c3(double left, double right) {
    return left == right || std::isnan(left) || std::isnan(right);
}

// 0x4953b0/0x4955c0: orient the embedded animation view at +0x128.
void orient(Run &run, uint32_t object) {
    if (run.get(object + 0x18c) == 2) { // movement direction
        uint32_t sprite = run.get(object + 0x12c);
        if (!(run.get8(sprite + 0x40) & 2)) {
            uint32_t left = run.get(object + 0x138);
            uint32_t right = run.get(object + 0x140);
            run.put(object + 0x138, 0u - right);
            run.put(object + 0x140, 0u - left);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            run.call(0x4060b0, run.get(object + 0x12c));
        }
    } else {
        run.call(0x406310, object + 0x128);
    }
}

// 0x4953b0. Start/repeat knife attack, with repeat count in the stack argument.
uint32_t knifeStart(Run &run, uint32_t object, uint32_t count) {
    run.put(object + 0x4c4, count); // remaining knife attacks
    orient(run, object);
    uint32_t sprite = run.get(object + 0x12c);
    run.put(sprite + 0x08, run.get(sprite + 0x08) & 0xfffffffeu);
    if (run.get(object + 0x184) != 4) {
        run.call(0x44ebb0, object);
        return 0;
    }
    if (s32(run.call(0x4a3050, 0)) % 101 < 40) {
        int32_t choice = s32(run.call(0x4a3050, 0)) % 4;
        uint32_t sound = run.get(object + 0x470 + uint32_t(choice) * 4);
        run.call(0x48ce40, 0, {run.get(object + 0x0c), sound, 0});
    }
    uint32_t state = run.get(object + 0x10);
    run.put(object + 0x24, run.get(state + 0x1c));
    uint32_t next = run.call(0x4dba00, 0x537668, {0x52b3a4});
    run.put(run.get(object + 0x10) + 0x1c, next);
    sprite = run.get(object + 0x12c);
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(object + 0x310)});
    run.put(run.get(object + 0x0c) + 0x104, 15);
    uint32_t actor = run.get(object + 0x0c);
    double scaled = double(s32(run.get(actor + 0x104))) * double(run.getf(0x5262b0));
    uint32_t damage = run.call_x87(0x4a30e0, 0, scaled);
    run.put(actor + 0x104, damage);
    run.icall(0x546d5c, {object + 0x220, uint32_t(-63), uint32_t(-58), 0, uint32_t(-1)});
    return 0;
}

// 0x495280..0x4953aa, including the internal continuation at 0x495345.
uint32_t lunge(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t sprite = run.get(object + 0x12c);
    if (run.get(sprite + 0x16c) == 800) {
        run.put(object + 0x50, 0);
        run.put(object + 0x54, 0);
    } else {
        run.putd(object + 0x50, double(s32(run.get(object + 0x4cc))));
    }
    sprite = run.get(object + 0x12c);
    if (run.get(sprite + 0x16c) == 402) {
        uint32_t actor = run.get(object + 0x0c);
        run.put(actor + 0x138, run.get(object + 0x220));
        run.put(actor + 0x13c, run.get(object + 0x224));
        run.put(actor + 0x140, run.get(object + 0x228));
        run.put(actor + 0x144, run.get(object + 0x22c));
        if (run.get8(run.get(object + 0x12c) + 0x40) & 2) {
            actor = run.get(object + 0x0c);
            uint32_t right = run.get(actor + 0x140);
            uint32_t left = run.get(actor + 0x138);
            run.put(actor + 0x138, 0u - right);
            run.put(run.get(object + 0x0c) + 0x140, 0u - left);
        }
    }
    uint32_t position = run.call_x87(0x4a30e0, 0, run.getd(object + 0x68));
    uint32_t direction = run.get(object + 0x18c);
    if ((direction == 3 && s32(position) <= s32(run.get(object + 0x4c0))) ||
        (direction == 2 && s32(position) >= s32(run.get(object + 0x4c0)))) {
        run.vcall(object, 0x44);
        return 0;
    }
    if ((c3(run.getd(object + 0x68), run.getd(object + 0x80)) && direction == 3) ||
        (c3(run.getd(object + 0x68), run.getd(object + 0x98)) && direction == 2)) {
        run.vcall(object, 0x44);
        return 0;
    }
    uint32_t animation = run.get(object + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) != 0 && run.get(animation + 0x14) == 0)
        run.vcall(object, 0x44);
    return 0;
}

// 0x4954f0. Tick knife attack.
uint32_t knifeTick(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t sprite = run.get(object + 0x12c);
    if (run.get(sprite + 0x16c) == 202) {
        uint32_t actor = run.get(object + 0x0c);
        run.put(actor + 0x138, run.get(object + 0x220));
        run.put(actor + 0x13c, run.get(object + 0x224));
        run.put(actor + 0x140, run.get(object + 0x228));
        run.put(actor + 0x144, run.get(object + 0x22c));
        if (run.get8(run.get(object + 0x12c) + 0x40) & 2) {
            actor = run.get(object + 0x0c);
            uint32_t right = run.get(actor + 0x140);
            uint32_t left = run.get(actor + 0x138);
            run.put(actor + 0x138, 0u - right);
            run.put(run.get(object + 0x0c) + 0x140, 0u - left);
        }
    }
    uint32_t animation = run.get(object + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) != 0 && run.get(animation + 0x14) == 0) {
        uint32_t count = run.get(object + 0x4c4) - 1;
        run.put(object + 0x4c4, count);
        if (s32(count) > 0)
            return knifeStart(run, object, count);
        run.vcall(object, 0x44);
    }
    return 0;
}

// 0x4955c0. Start front flip.
uint32_t frontStart(Run &run, uint32_t object, uint32_t attack) {
    run.put(object + 0x4d8, attack); // knife attack after flip
    run.put(object + 0x4dc, 1); // suppress hit callback
    orient(run, object);
    run.putd(object + 0x50, run.get(object + 0x18c) == 3 ? -250.0 : 250.0);
    uint32_t position = run.call_x87(0x4a30e0, 0, run.getd(object + 0x68));
    uint32_t distance = run.get(object + 0x18c) == 3 ? uint32_t(-100) : 100;
    run.put(object + 0x4c0, position + distance);
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    uint32_t next = run.call(0x4dba00, 0x537668, {0x52ca78});
    run.put(run.get(object + 0x10) + 0x1c, next);
    uint32_t sprite = run.get(object + 0x12c);
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(object + 0x450)});
    int32_t choice = s32(run.call(0x4a3050, 0)) % 2;
    uint32_t sound = run.get(object + 0x460 + uint32_t(choice) * 4);
    if (sound && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    run.put(object + 0x4b4, 1000);
    run.put(object + 0x4b0, run.get(0x537210));
    sprite = run.get(object + 0x12c);
    run.put(sprite + 0x08, run.get(sprite + 0x08) | 1);
    return 0;
}

// 0x495710. Tick front flip.
uint32_t frontTick(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t position = run.call_x87(0x4a30e0, 0, run.getd(object + 0x68));
    uint32_t direction = run.get(object + 0x18c);
    if ((direction == 3 && s32(position) <= s32(run.get(object + 0x4c0))) ||
        (direction == 2 && s32(position) >= s32(run.get(object + 0x4c0)))) {
        if (run.get(object + 0x4d8))
            return knifeStart(run, object, 1);
        run.vcall(object, 0x44);
        return 0;
    }
    if ((direction == 3 && c3(run.getd(object + 0x68), run.getd(object + 0x80))) ||
        (direction == 2 && c3(run.getd(object + 0x68), run.getd(object + 0x98)))) {
        if (run.get(object + 0x4d8))
            knifeStart(run, object, 1);
        else
            run.vcall(object, 0x44);
    }
    uint32_t elapsed = run.get(0x537210) - run.get(object + 0x4b0);
    if (elapsed >= run.get(object + 0x4b4)) {
        if (run.get(object + 0x4d8))
            knifeStart(run, object, 1);
        run.vcall(object, 0x44);
    }
    return 0;
}

// 0x4957f0. Start back flip, or front flip at the facing collision bound.
uint32_t backStart(Run &run, uint32_t object) {
    if (run.get(object + 0x18c) == 2)
        run.call(0x4357a0, object + 0x128);
    else
        run.call(0x406310, object + 0x128);
    run.putd(object + 0x50, run.get(object + 0x18c) == 2 ? -250.0 : 250.0);
    uint32_t direction = run.get(object + 0x18c);
    uint32_t position = run.call_x87(0x4a30e0, 0, run.getd(object + 0x68));
    uint32_t distance = direction == 2 ? uint32_t(-100) : 100;
    run.put(object + 0x4c0, position + distance);
    if ((direction == 2 && c3(run.getd(object + 0x68), run.getd(object + 0x80))) ||
        (direction == 3 && c3(run.getd(object + 0x68), run.getd(object + 0x98)))) {
        frontStart(run, object, 1);
        return 0;
    }
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    uint32_t next = run.call(0x4dba00, 0x537668, {0x52ca98});
    run.put(run.get(object + 0x10) + 0x1c, next);
    uint32_t sprite = run.get(object + 0x12c);
    uint32_t stream = run.get(object + 0x454); // backflip animation stream
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {stream});
    run.put(object + 0x4b4, 1000);
    run.put(object + 0x4b0, run.get(0x537210));
    int32_t choice = s32(run.call(0x4a3050, 0)) % 2;
    uint32_t sound = run.get(object + 0x460 + uint32_t(choice) * 4);
    if (sound && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    sprite = run.get(object + 0x12c);
    run.put(sprite + 0x08, run.get(sprite + 0x08) | 1);
    return 0;
}

// 0x495940. Tick back flip.
uint32_t backTick(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t direction = run.get(object + 0x18c);
    double position = run.getd(object + 0x68);
    double target = double(s32(run.get(object + 0x4c0)));
    if ((direction == 2 && target >= position) || (direction == 3 && !(target > position))) {
        run.vcall(object, 0x44);
        return 0;
    }
    if (c3(run.getd(object + 0x68), run.getd(object + 0x80)) ||
        c3(run.getd(object + 0x68), run.getd(object + 0x98)))
        run.vcall(object, 0x44);
    uint32_t elapsed = run.get(0x537210) - run.get(object + 0x4b0);
    if (elapsed >= run.get(object + 0x4b4))
        run.vcall(object, 0x44);
    return 0;
}

// 0x495ae0. Start block.
uint32_t blockStart(Run &run, uint32_t object) {
    if (run.get(object + 0x18c) == 2) {
        uint32_t sprite = run.get(object + 0x12c);
        if (!(run.get8(sprite + 0x40) & 2)) {
            uint32_t left = run.get(object + 0x138);
            uint32_t right = run.get(object + 0x140);
            run.put(object + 0x138, 0u - right);
            run.put(object + 0x140, 0u - left);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            sprite = run.get(object + 0x12c);
            run.call(0x406120, sprite);
            run.call(0x406150, sprite);
            run.call(0x406180, sprite);
        }
    } else {
        run.call(0x406310, object + 0x128);
    }
    run.put(object + 0x50, 0);
    run.put(object + 0x54, 0);
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    uint32_t next = run.call(0x4dba00, 0x537668, {0x526a38});
    run.put(run.get(object + 0x10) + 0x1c, next);
    uint32_t sprite = run.get(object + 0x12c);
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(object + 0x458)});
    run.put(object + 0x4bc, 250);
    run.put(object + 0x4b8, run.get(0x537210));
    return 0;
}

// 0x4959e0. Mark a projectile and enter block, with optional block sound.
uint32_t blockProjectile(Run &run, uint32_t object, uint32_t projectile) {
    if (projectile)
        run.put(projectile + 0x08, run.get(projectile + 0x08) | 0x10000);
    uint32_t sound = run.get(object + 0x494);
    if (sound && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    return blockStart(run, object);
}

// 0x495a40. Forward hits unless the flip's suppression flag is set.
uint32_t hit(Run &run, uint32_t object, uint32_t argument) {
    if (!run.get(object + 0x4dc))
        run.call(0x44d460, object, {argument});
    return 0;
}

// 0x495a60. Choose lift sound, then enter the shared lifted state.
uint32_t lift(Run &run, uint32_t object) {
    uint32_t sound;
    if (s32(run.call(0x4a3050, 0)) % 101 < 10)
        sound = run.get(object + 0x46c);
    else
        sound = run.get(object + 0x468);
    run.call(0x48ce40, 0, {run.get(object + 0x0c), sound, 0});
    run.call(0x440420, object);
    return 0;
}

// 0x495ac0. Latch hit state, then tail into the unchanged base handler.
uint32_t baseHit(Run &run, uint32_t object) {
    if (!run.get(object + 0x4d0))
        run.put(object + 0x4d0, 1);
    return run.call(0x44dbb0, object);
}

// 0x495ba0. Tick block until its unsigned elapsed timer expires.
uint32_t blockTick(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t elapsed = run.get(0x537210) - run.get(object + 0x4b8);
    if (elapsed >= run.get(object + 0x4bc))
        run.vcall(object, 0x44);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x495280:
        return lunge(run, receiver);
    case 0x4953b0:
        return knifeStart(run, receiver, arguments[0]);
    case 0x4954f0:
        return knifeTick(run, receiver);
    case 0x4955c0:
        return frontStart(run, receiver, arguments[0]);
    case 0x495710:
        return frontTick(run, receiver);
    case 0x4957f0:
        return backStart(run, receiver);
    case 0x495940:
        return backTick(run, receiver);
    case 0x4959e0:
        return blockProjectile(run, receiver, arguments[0]);
    case 0x495a30:
        return blockStart(run, receiver);
    case 0x495a40:
        return hit(run, receiver, arguments[0]);
    case 0x495a60:
        return lift(run, receiver);
    case 0x495ac0:
        return baseHit(run, receiver);
    case 0x495ae0:
        return blockStart(run, receiver);
    case 0x495ba0:
        return blockTick(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_tiger_guard_states_entry, owned, body)
