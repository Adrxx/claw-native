// Level 6 Wolvington state transitions, recovered from the original entries.
#include "ClawRuntime.hpp"
#include <cmath>

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4a0960: case 0x4a0a90: case 0x4a0ae0: case 0x4a0b30:
    case 0x4a0c10: case 0x4a0cf0: case 0x4a0ec0: case 0x4a0f40:
    case 0x4a0fd0: case 0x4a1020: case 0x4a10b0: case 0x4a10f0:
    case 0x4a1250:
        return 0;
    default:
        return -1;
    }
}

// Receiver +0x10 is the state controller; +0x24 saves its previous state.
void changeState(Run &run, uint32_t self, uint32_t name) {
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t next = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(self + 0x10) + 0x1c, next);
}

// Receiver +0x12c is the sprite, +0x138/+0x140 its horizontal bounds.
void faceLeft(Run &run, uint32_t self) {
    if (run.get(self + 0x18c) == 2) {
        uint32_t sprite = run.get(self + 0x12c);
        if (!(run.get8(sprite + 0x40) & 2)) {
            uint32_t left = run.get(self + 0x138);
            uint32_t right = run.get(self + 0x140);
            run.put(self + 0x138, 0u - right);
            run.put(self + 0x140, 0u - left);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            run.call(0x4060b0, run.get(self + 0x12c));
        }
    } else {
        run.call(0x406310, self + 0x128);
    }
}

// 0x4a0a90. +0x460 enables repeated magic; +0x464 counts repetitions.
uint32_t beginRepeatedMagic(Run &run, uint32_t self) {
    changeState(run, self, 0x52e0e0);
    run.put(self + 0x50, 0);
    run.put(self + 0x54, 0);
    run.put(self + 0x460, 1);
    uint32_t random = run.call(0x4a3050, 0);
    run.put(self + 0x464, uint32_t(s32(random) % 11));
    return 0;
}

// 0x4a0b30 and 0x4a0c10. +0x468/+0x46c are projectile offsets,
// +0x470 is projectile velocity, +0x1a0 marks an already fired projectile.
uint32_t beginMagic(Run &run, uint32_t self, bool high) {
    changeState(run, self, 0x52e0d4);
    uint32_t sprite = run.get(self + 0x12c);
    run.put(self + 0x134, run.get(sprite + 0x190));
    run.call(0x4c79e0, sprite, {high ? 0x52e148u : 0x52e114u, 0});
    uint32_t local = run.automatic(-4);
    uint32_t resource = run.get(run.get(run.get(self + 0x12c) + 0x0c) + 0x28) + 0x10;
    run.put(local, 0);
    run.call(0x4f6286, resource, {high ? 0x52e130u : 0x52e0f8u, local});
    uint32_t sound = run.get(local);
    if (sound && run.get(0x532c0c)) {
        uint32_t context = run.get(0x532c10);
        run.call(0x4b45f0, run.get(sound + 0x10), {context, 0, 0, 0});
    }
    if (run.get8(run.get(self + 0x12c) + 0x40) & 2) {
        run.put(self + 0x468, 0x41);
        run.put(self + 0x470, 300);
    } else {
        run.put(self + 0x468, 0xffffffbf);
        run.put(self + 0x470, 0xfffffed4);
    }
    run.put(self + 0x46c, high ? 0xffffffecu : 10u);
    run.put(self + 0x1a0, 0);
    return 0;
}

// 0x4a0ae0.
uint32_t advanceMagicAttack(Run &run, uint32_t self) {
    if (run.get(self + 0x464) == 10) {
        run.vcall(self, 0x44);
        run.put(self + 0x460, 0);
    }
    uint32_t previous = run.get(self + 0x464);
    run.put(self + 0x464, previous + 1);
    uint32_t frame = run.frame;
    run.frame -= 8;
    beginMagic(run, self, !(previous & 1));
    run.frame = frame;
    return 0;
}

// 0x4a0ec0. +0x474 is the optional uppercut sound resource.
uint32_t beginUppercut(Run &run, uint32_t self) {
    uint32_t sound = run.get(self + 0x474);
    if (sound && run.get(0x532c0c)) {
        uint32_t context = run.get(0x532c10);
        run.call(0x4b45f0, run.get(sound + 0x10), {context, 0, 0, 0});
    }
    changeState(run, self, 0x52e0c4);
    uint32_t sprite = run.get(self + 0x12c);
    run.put(self + 0x134, run.get(sprite + 0x190));
    run.call(0x4c79e0, sprite, {0x52e164, 0});
    run.put(self + 0x50, 0);
    run.put(self + 0x54, 0);
    return 0;
}

// 0x4a0fd0.
uint32_t beginSwordAttack(Run &run, uint32_t self) {
    changeState(run, self, 0x52e0b4);
    uint32_t sprite = run.get(self + 0x12c);
    run.put(self + 0x134, run.get(sprite + 0x190));
    run.call(0x4c79e0, sprite, {0x52df84, 0});
    return 0;
}

// 0x4a10b0.
uint32_t beginRunningUppercut(Run &run, uint32_t self) {
    run.call(0x44ebb0, self);
    changeState(run, self, 0x52e0a4);
    run.put(run.get(self + 0x12c) + 0x1b0, 0x3e800000);
    return 0;
}

// 0x4a0960. +0x184 is contact classification; +0x3c4 is decision value.
uint32_t chooseState(Run &run, uint32_t self) {
    faceLeft(run, self);
    switch (run.get(self + 0x184)) {
    case 0: case 1: case 2:
        if (s32(run.get(self + 0x3c4)) >= 0 && s32(run.get(self + 0x3c4)) < 300)
            beginRepeatedMagic(run, self);
        if (s32(run.get(self + 0x3c4)) >= 300 && s32(run.get(self + 0x3c4)) < 400)
            beginRunningUppercut(run, self);
        if (s32(run.get(self + 0x3c4)) >= 400 && s32(run.get(self + 0x3c4)) < 1000)
            run.call(0x4a1180, self);
        break;
    case 3: case 4:
        if (s32(run.get(self + 0x3c4)) >= 0 && s32(run.get(self + 0x3c4)) < 500) {
            if (run.get(run.get(0x537e88) + 0xcc) == 5)
                beginSwordAttack(run, self);
            else
                beginUppercut(run, self);
        } else {
            run.vcall(self, 0x64);
        }
        break;
    case 5: case 6:
        run.call(0x44edd0, self);
        break;
    }
    return 0;
}

// 0x4a0cf0. Projectile +0x6c points at its class, whose +0x18 is logic.
uint32_t updateMagic(Run &run, uint32_t self) {
    if (run.get(self + 0x18c) == 2)
        run.call(0x4357a0, self + 0x128);
    else
        run.call(0x406310, self + 0x128);
    uint32_t frame = run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (frame == 1 && run.get(self + 0x1a0) == 0) {
        run.put(self + 0x1a0, 1);
        uint32_t sprite = run.get(self + 0x12c);
        uint32_t y = run.get(self + 0x46c) + run.get(sprite + 0x50);
        uint32_t x = run.get(self + 0x468) + run.get(sprite + 0x4c);
        uint32_t z = run.get(sprite + 0x64) - 1;
        uint32_t manager = run.get(run.get(run.get(self + 0x130) + 0x0c) + 0x08);
        uint32_t projectile = run.call(0x4c8da0, manager, {0, x, y, z, 0x522da8, 0x40000});
        uint32_t klass = run.get(projectile + 0x6c);
        run.put(projectile + 0x104, 15);
        run.put(projectile + 0xd0, 0x40);
        run.call(run.get(klass + 0x10), 0, {projectile});
        uint32_t logic = run.get(run.get(projectile + 0x6c) + 0x18);
        run.putd(logic + 0x50, double(s32(run.get(self + 0x470))));
        logic = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(logic + 0x58, 0);
        run.put(logic + 0x5c, 0);
        logic = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(logic + 0x40, 0);
        run.put(logic + 0x44, 0);
        if (s32(run.get(self + 0x470)) < 0) {
            logic = run.get(run.get(projectile + 0x6c) + 0x18);
            uint32_t childSprite = run.get(logic + 0x12c);
            if (!(run.get8(childSprite + 0x40) & 2)) {
                uint32_t left = run.get(logic + 0x138);
                uint32_t right = run.get(logic + 0x140);
                run.put(logic + 0x138, 0u - right);
                run.put(logic + 0x140, 0u - left);
                run.put(childSprite + 0x40, run.get(childSprite + 0x40) | 2);
                childSprite = run.get(logic + 0x12c);
                for (uint32_t offset : {0x118u, 0x128u, 0x138u}) {
                    left = run.get(childSprite + offset);
                    if (left != 0x80000000) {
                        right = run.get(childSprite + offset + 0x08);
                        run.put(childSprite + offset, 0u - right);
                        run.put(childSprite + offset + 0x08, 0u - left);
                    }
                }
            }
        }
    }
    uint32_t animation = run.get(self + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14)) {
        if (run.get(self + 0x460))
            beginRepeatedMagic(run, self);
        else
            run.vcall(self, 0x44);
    }
    return 0;
}

// 0x4a0f40 and 0x4a1020. +0x0c points at the collision owner.
uint32_t updateMelee(Run &run, uint32_t self, bool sword) {
    if (run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)}) == 1) {
        run.icall(0x546d5c, {run.get(self + 0x0c) + 0x138,
            sword ? 0xffffffa1u : 0xffffffc5u, sword ? 1u : 0xffffffc1u,
            sword ? 0xffffffe8u : 0xffffffdcu, sword ? 42u : 0xfffffff8u});
        if (run.get8(run.get(self + 0x12c) + 0x40) & 2) {
            uint32_t collision = run.get(self + 0x0c);
            uint32_t right = run.get(collision + 0x140);
            uint32_t left = run.get(collision + 0x138);
            run.put(collision + 0x138, 0u - right);
            run.put(run.get(self + 0x0c) + 0x140, 0u - left);
        }
    }
    uint32_t animation = run.get(self + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14))
        run.vcall(self, 0x44);
    return 0;
}

// 0x4a10f0. +0x404 holds running speed before the fourfold scale.
uint32_t updateRunningUppercut(Run &run, uint32_t self) {
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
    switch (run.get(self + 0x184)) {
    case 0: case 1: case 2: case 5:
        break;
    case 3: case 4:
        beginUppercut(run, self);
        return 0;
    default:
        return 0;
    }
    uint32_t speed = run.get(self + 0x404);
    if (run.get(self + 0x18c) == 3)
        speed = 0u - speed;
    run.putd(self + 0x50, double(s32(speed << 2)));
    return 0;
}

// 0x4a1250. The x87 C3 test treats unordered comparisons as matching too.
uint32_t updateAdvance(Run &run, uint32_t self) {
    double position = run.getd(self + 0x68);
    double first = run.getd(self + 0x80);
    bool atEdge = position == first || std::isnan(position) || std::isnan(first);
    if (!atEdge) {
        position = run.getd(self + 0x68);
        double second = run.getd(self + 0x98);
        atEdge = position == second || std::isnan(position) || std::isnan(second);
    }
    if (atEdge)
        run.vcall(self, 0x48);
    faceLeft(run, self);
    uint32_t speed = run.get(self + 0x400);
    if (run.get(self + 0x18c) == 3)
        speed = 0u - speed;
    run.putd(self + 0x50, double(s32(speed)));
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
    switch (run.get(self + 0x184)) {
    case 0:
        run.call(0x44ebb0, self);
        break;
    case 1: case 2:
        if (s32(run.get(self + 0x3c4)) >= 0 && s32(run.get(self + 0x3c4)) < 10)
            beginRepeatedMagic(run, self);
        if (s32(run.get(self + 0x3c4)) >= 10 && s32(run.get(self + 0x3c4)) < 20)
            beginRunningUppercut(run, self);
        break;
    case 3: case 4: case 5: case 6:
        run.vcall(self, 0x44);
        break;
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t self, const uint32_t *) {
    switch (function) {
    case 0x4a0960: return chooseState(run, self);
    case 0x4a0a90: return beginRepeatedMagic(run, self);
    case 0x4a0ae0: return advanceMagicAttack(run, self);
    case 0x4a0b30: return beginMagic(run, self, false);
    case 0x4a0c10: return beginMagic(run, self, true);
    case 0x4a0cf0: return updateMagic(run, self);
    case 0x4a0ec0: return beginUppercut(run, self);
    case 0x4a0f40: return updateMelee(run, self, false);
    case 0x4a0fd0: return beginSwordAttack(run, self);
    case 0x4a1020: return updateMelee(run, self, true);
    case 0x4a10b0: return beginRunningUppercut(run, self);
    case 0x4a10f0: return updateRunningUppercut(run, self);
    case 0x4a1250: return updateAdvance(run, self);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace
CLAW_MODULE_ENTRY(claw_level_six_wolvington_states_01_entry, owned, body)
