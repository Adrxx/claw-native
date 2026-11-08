// Aquatis state callbacks recovered from the original v1.0 entries.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4051a0:
    case 0x405440:
    case 0x405540:
    case 0x405640:
    case 0x4057a0:
    case 0x4059e0:
    case 0x405a60:
    case 0x405d50:
    case 0x405df0:
    case 0x405ed0:
    case 0x405fa0:
        return 0;
    default:
        return -1;
    }
}

// +0x12c sprite, whose +0x188 is the animation controller.
void animate(Run &run, uint32_t receiver) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
}

// +0x1a4 animation finished, +0x19c animation delay.
bool finished(Run &run, uint32_t receiver) {
    uint32_t sprite = run.get(receiver + 0x12c);
    return run.get(sprite + 0x1a4) != 0 && run.get(sprite + 0x19c) == 0;
}

// 0x4051a0. Idle state: +0x4b8 live, +0x4ec startup delay,
// +0x184 phase, +0x4cc/+0x4d0 idle clock and duration.
uint32_t idle(Run &run, uint32_t receiver) {
    if (run.get(receiver + 0x4b8) == 0 || run.get(receiver + 0x4ec) != 0)
        return 0;
    animate(run, receiver);
    if (run.get(receiver + 0x4c0) != 0)
        run.call(0x4053d0, receiver);
    uint32_t phase = run.get(receiver + 0x184);
    if (phase != 0 && s32(phase) > 1 && s32(phase) <= 4 &&
        run.get(0x537210) - run.get(receiver + 0x4cc) >= run.get(receiver + 0x4d0)) {
        run.call(0x405240, receiver);
        return 0;
    }
    if (finished(run, receiver))
        run.vcall(receiver, 0x48);
    return 0;
}

// 0x405440. Scared state's first-entry flag is +0x4a0; +0x49c sound.
uint32_t scared(Run &run, uint32_t receiver) {
    animate(run, receiver);
    if (run.get(receiver + 0x4a0) == 0) {
        uint32_t sound = run.get(receiver + 0x49c);
        run.put(receiver + 0x4a0, 1);
        run.call(0x405f60, receiver, {sound});
    }
    if (run.get(0x537210) - run.get(receiver + 0x4d4) >= run.get(receiver + 0x4d8) &&
        run.get(receiver + 0x4c0) == 0 && run.get(receiver + 0x4c4) == 0)
        run.vcall(receiver, 0x48);
    return 0;
}

// 0x405540. Frenzy timer +0x4dc/+0x4e0, active flag +0x4b4.
uint32_t frenzy(Run &run, uint32_t receiver) {
    animate(run, receiver);
    if (run.get(receiver + 0x4a0) == 0) {
        uint32_t sound = run.get(receiver + 0x498);
        run.put(receiver + 0x4a0, 1);
        run.call(0x405f60, receiver, {sound});
    }
    if (run.get(0x537210) - run.get(receiver + 0x4dc) >= run.get(receiver + 0x4e0)) {
        uint32_t method = run.get(run.get(receiver) + 0x48);
        run.put(receiver + 0x4b4, 0);
        run.call(method, receiver);
        return 0;
    }
    if (run.get(0x534878) == 0)
        run.call(0x4055e0, receiver);
    else
        run.call(0x405740, receiver);
    run.put(0x534878, run.get(0x534878) == 0 ? 1u : 0u);
    return 0;
}

// +0x10 points at state object; +0x24 remembers its old +0x1c state.
void returnFromPunch(Run &run, uint32_t receiver) {
    if (!finished(run, receiver))
        return;
    if (run.get(receiver + 0x4b4) != 0) {
        run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
        uint32_t state = run.call(0x4dba00, 0x537668, {0x52323c});
        run.put(run.get(receiver + 0x10) + 0x1c, state);
        return;
    }
    run.vcall(receiver, 0x48);
}

// 0x405640. High punch sound +0x490; sprite frame +0x16c,
// facing byte +0x40. Descriptor +0xc owns its attack RECT at +0x138.
uint32_t highPunch(Run &run, uint32_t receiver) {
    animate(run, receiver);
    if (run.get(receiver + 0x4a0) == 0) {
        uint32_t sound = run.get(receiver + 0x490);
        run.put(receiver + 0x4a0, 1);
        if (sound != 0 && run.get(0x532c0c) != 0)
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
    if (run.get(run.get(receiver + 0x12c) + 0x16c) == 0xcc) {
        run.icall(0x546d5c, {run.get(receiver + 0xc) + 0x138, 0xffffff8a, 0xffffffb4, 0, 10});
        if ((run.get8(run.get(receiver + 0x12c) + 0x40) & 2) != 0) {
            uint32_t descriptor = run.get(receiver + 0xc);
            uint32_t right = run.get(descriptor + 0x140);
            uint32_t left = run.get(descriptor + 0x138);
            run.put(descriptor + 0x138, 0u - right);
            run.put(run.get(receiver + 0xc) + 0x140, 0u - left);
        }
    }
    returnFromPunch(run, receiver);
    return 0;
}

// 0x4057a0. Low punch sound +0x494 and frame 0xcf.
uint32_t lowPunch(Run &run, uint32_t receiver) {
    animate(run, receiver);
    if (run.get(receiver + 0x4a0) == 0) {
        uint32_t sound = run.get(receiver + 0x494);
        run.put(receiver + 0x4a0, 1);
        if (sound != 0 && run.get(0x532c0c) != 0)
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
    if (run.get(run.get(receiver + 0x12c) + 0x16c) == 0xcf) {
        run.icall(0x546d5c, {run.get(receiver + 0xc) + 0x138, 0xffffff7e, 10, 0, 60});
        if ((run.get8(run.get(receiver + 0x12c) + 0x40) & 2) != 0) {
            uint32_t descriptor = run.get(receiver + 0xc);
            uint32_t right = run.get(descriptor + 0x140);
            uint32_t left = run.get(descriptor + 0x138);
            run.put(descriptor + 0x138, 0u - right);
            run.put(run.get(receiver + 0xc) + 0x140, 0u - left);
        }
    }
    returnFromPunch(run, receiver);
    return 0;
}

// 0x4059e0. Stalactite hit: +0x488 sound, +0x4a4 completion latch.
uint32_t stalactiteHit(Run &run, uint32_t receiver) {
    animate(run, receiver);
    if (run.get(receiver + 0x4a0) == 0) {
        uint32_t sound = run.get(receiver + 0x488);
        run.put(receiver + 0x4a0, 1);
        run.call(0x405f60, receiver, {sound});
    }
    if (finished(run, receiver) && run.get(receiver + 0x4a4) == 0) {
        run.put(receiver + 0x4a4, 1);
        run.call(0x4054c0, receiver);
    }
    return 0;
}

// 0x405a60. High hit: +0x4ac is the hit counter.
uint32_t hitHigh(Run &run, uint32_t receiver) {
    animate(run, receiver);
    if (!finished(run, receiver))
        return 0;
    uint32_t count = run.get(receiver + 0x4ac) + 1u;
    run.put(receiver + 0x4ac, count);
    if (count == 3) {
        run.put(receiver + 0x4ac, 0);
        run.call(0x4053d0, receiver);
        return 0;
    }
    uint32_t random = run.call(0x4a3050, 0);
    if (s32(random) % 101 < 85)
        run.call(0x405240, receiver);
    else
        run.vcall(receiver, 0x48);
    return 0;
}

// 0x405d50. Enter death: +0x374 death animation, +0x134 saved animation;
// +0x220 and +0x210 are disabled collision rectangles.
uint32_t enterDeath(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x5231f8});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x374);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 0x80);
    run.icall(0x546d5c, {receiver + 0x220, 0x80000000, 0, 0, 0});
    run.icall(0x546d5c, {receiver + 0x210, 0x80000000, 0, 0, 0});
    run.put(receiver + 0x4a0, 0);
    run.put(receiver + 0x4a4, 0);
    return 0;
}

// 0x405df0. Death animation: +0x48c sound and +0x2f4 bit-array.
uint32_t death(Run &run, uint32_t receiver) {
    animate(run, receiver);
    if (run.get(receiver + 0x4a0) == 0) {
        uint32_t sound = run.get(receiver + 0x48c);
        run.put(receiver + 0x4a0, 1);
        run.call(0x405f60, receiver, {sound});
    }
    if (!finished(run, receiver) || run.get(receiver + 0x4a4) != 0)
        return 0;
    run.put(receiver + 0x4a4, 1);
    if (s32(run.get(run.get(0x537e88) + 0x10c)) <= 0)
        return 0;
    run.call(0x420590, 0);
    run.call(0x40e5c0, receiver);
    run.call(0x48cf50, 0, {run.get(receiver + 0xc)});
    run.put(receiver + 0x4b8, 0);
    uint32_t size = run.get(receiver + 0x2fc);
    if (size <= 4) {
        run.call(0x4dbd20, receiver + 0x2f4, {4});
        return 0;
    }
    if (size > 32) {
        uint32_t bits = run.get(receiver + 0x300);
        run.put(bits, run.get(bits) | 0x10);
        return 0;
    }
    run.put(receiver + 0x300, run.get(receiver + 0x300) | 0x10);
    return 0;
}

// 0x405ed0. Reset Aquatis health and transient combat flags.
uint32_t reset(Run &run, uint32_t receiver) {
    if (run.get(receiver + 0x4b8) == 0)
        return 0;
    run.put(run.get(receiver + 0xc) + 0x10c, 100);
    uint32_t descriptor = run.get(receiver + 0xc);
    double health = double(s32(run.get(descriptor + 0x10c)));
    double scale = double(run.getf(0x5262b4));
    uint32_t converted = run.call_x87(0x4a30e0, 0, health * scale);
    run.put(descriptor + 0x10c, converted);
    descriptor = run.get(receiver + 0xc);
    uint32_t method = run.get(run.get(receiver) + 0x48);
    run.put(receiver + 0x4a0, 0);
    run.put(receiver + 0x4a4, 0);
    run.put(receiver + 0x4a8, 0);
    run.put(receiver + 0x4ac, 0);
    run.put(receiver + 0x4b0, run.get(descriptor + 0x50) - 50u);
    run.put(receiver + 0x4b4, 0);
    run.put(receiver + 0x4bc, 0);
    run.put(receiver + 0x4c0, 0);
    run.put(receiver + 0x4c4, 0);
    run.put(receiver + 0x4c8, 0);
    run.put(receiver + 0x4ec, 0x3fe);
    run.call(method, receiver);
    return 0;
}

// 0x405fa0. Normal destructor path; exception registration is scaffolding.
uint32_t destroy(Run &run, uint32_t receiver) {
    run.put(0x534874, 0);
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *) {
    switch (function) {
    case 0x4051a0: return idle(run, receiver);
    case 0x405440: return scared(run, receiver);
    case 0x405540: return frenzy(run, receiver);
    case 0x405640: return highPunch(run, receiver);
    case 0x4057a0: return lowPunch(run, receiver);
    case 0x4059e0: return stalactiteHit(run, receiver);
    case 0x405a60: return hitHigh(run, receiver);
    case 0x405d50: return enterDeath(run, receiver);
    case 0x405df0: return death(run, receiver);
    case 0x405ed0: return reset(run, receiver);
    case 0x405fa0: return destroy(run, receiver);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_level_twelve_aquatis_states_01_entry, owned, body)
