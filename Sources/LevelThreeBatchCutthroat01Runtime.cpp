#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x437a90:
    case 0x438010:
    case 0x438100:
        return 1;
    case 0x438030:
    case 0x4384f0:
    case 0x4385b0:
    case 0x4386d0:
    case 0x4388a0:
    case 0x438900:
    case 0x438a90:
        return 0;
    default:
        return -1;
    }
}

uint32_t worldMap(Run &run, uint32_t self, uint32_t offset) {
    return run.get(run.get(run.get(self + 0x12c) + 0x0c) + offset);
}

// +0x134 saved animation; +0x12c primary actor; actor +0x188 animation state.
void selectAnimation(Run &run, uint32_t self, uint32_t animation, bool advance) {
    uint32_t actor = run.get(self + 0x12c);
    run.put(self + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    if (advance)
        run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
}

// 0x4384f0. +0x50 velocity, +0x24 previous state, +0x474/+0x478 pacing timer.
uint32_t enterIdle(Run &run, uint32_t self) {
    if (s32(run.call(0x4a3050, 0)) % 100 < 33) {
        uint32_t voice = uint32_t(s32(run.call(0x4a3050, 0)) % 2);
        uint32_t sound = run.get(self + 0x460 + voice * 4);
        if (run.get(run.get(self + 0x12c) + 0x38) != 0xffffffffu)
            run.call(0x48ce40, 0, {run.get(self + 0x0c), sound, 0});
    }
    run.put(self + 0x50, 0);
    run.put(self + 0x54, 0);
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(self + 0x10) + 0x1c, state);
    selectAnimation(run, self, run.get(self + 0x318), true);
    run.put(self + 0x478, 4000);
    run.put(self + 0x474, run.get(0x537210));
    return 0;
}

// 0x4385b0. +0x46c/+0x470 idle animation timer, +0x184 mode.
uint32_t updateIdle(Run &run, uint32_t self) {
    if (run.get(0x537210) - run.get(self + 0x46c) >= run.get(self + 0x470)) {
        run.put(self + 0x470, 1000);
        run.put(self + 0x46c, run.get(0x537210));
        uint32_t choice = uint32_t(s32(run.call(0x4a3050, 0)) % 4);
        if (choice <= 3)
            selectAnimation(run, self, run.get(self + 0x318 + choice * 4), true);
    }
    uint32_t mode = run.get(self + 0x184);
    if (mode <= 4)
        run.vcall(self, 0x44);
    else if (mode <= 6 && run.get(0x537210) - run.get(self + 0x474) >= run.get(self + 0x478)) {
        if (s32(run.call(0x4a3050, 0)) % 100 < 20)
            run.call(0x44edd0, self);
    }
    return 0;
}

// +0x190 collision-context actor, +0x194 position actor.
bool visible(Run &run, uint32_t self) {
    if (run.get(0x534eac) == 0x26b7)
        return false;
    uint32_t actor = run.get(self + 0x194);
    uint32_t playerX = run.get(run.get(0x537e88) + 0x4c);
    uint32_t y = run.get(actor + 0x50);
    uint32_t x = run.get(actor + 0x4c);
    uint32_t collision = run.get(run.get(run.get(self + 0x190) + 0x0c) + 0x24);
    if (!run.call(0x4cda10, collision, {x, y, playerX, 0x20}))
        return false;
    actor = run.get(self + 0x194);
    y = run.get(actor + 0x50);
    uint32_t playerY = run.get(run.get(0x537e88) + 0x50);
    return s32(playerY) < s32(y + 50) && s32(playerY) > s32(y - 50) && run.get(actor + 0x38) != 0xffffffffu;
}

// 0x4386d0. +0x18c facing mode; +0x138/+0x140 horizontal bounds.
uint32_t updateHome(Run &run, uint32_t self) {
    if (run.get(self + 0x18c) == 2) {
        uint32_t actor = run.get(self + 0x12c);
        if (!(run.get8(actor + 0x40) & 2)) {
            uint32_t left = run.get(self + 0x138);
            run.put(self + 0x138, 0u - run.get(self + 0x140));
            run.put(self + 0x140, 0u - left);
            run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            actor = run.get(self + 0x12c);
            run.call(0x406120, actor);
            run.call(0x406150, actor);
            run.call(0x406180, actor);
        }
    } else {
        run.call(0x406310, self + 0x128);
    }
    int32_t random = s32(run.call(0x4a3050, 0)) % 121;
    uint32_t mode = run.get(self + 0x184);
    if (mode <= 2) {
        if (!visible(run, self))
            run.vcall(self, 0x48);
        if (!run.get(self + 0x468)) {
            if (run.get(run.get(self + 0x12c) + 0x38) != 0xffffffffu)
                run.call(0x48ce40, 0, {run.get(self + 0x0c), run.get(self + 0x45c), 0});
            run.put(self + 0x468, 1);
        }
    } else if (mode <= 4 && random < s32(run.get(self + 0x2e4))) {
        run.vcall(self, 0x58);
    }
    if (visible(run, self))
        run.vcall(self, 0xa4);
    else
        run.call(0x44da20, self);
    return 0;
}

// 0x438900. +0x3b4 throw sound; +0x370 firing animation; +0x450/454/458 projectile parameters.
uint32_t enterFiring(Run &run, uint32_t self) {
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x524548});
    run.put(run.get(self + 0x10) + 0x1c, state);
    bool low = run.get(run.get(0x537e88) + 0xcc) == 5;
    uint32_t scratch = run.automatic(-4);
    run.put(scratch, 0);
    run.call(0x4f6286, worldMap(run, self, 0x28) + 0x10, {low ? 0x526d68u : 0x526b78u, scratch});
    run.put(self + 0x3b4, run.get(scratch));
    run.put(scratch, 0);
    run.call(0x4f6286, worldMap(run, self, 0x2c) + 0x10, {low ? 0x526d50u : 0x526cecu, scratch});
    uint32_t animation = run.get(scratch);
    if (!animation) {
        if (low)
            animation = run.call(0x4062e0, self + 0x128, {0x5234b4});
        else
            animation = run.call(0x4061b0, worldMap(run, self, 0x2c), {0x5234b4});
    }
    run.put(self + 0x370, animation);
    run.put(self + 0x454, low ? 20 : 0xfffffff1u);
    bool flipped = run.get8(run.get(self + 0x12c) + 0x40) & 2;
    run.put(self + 0x450, flipped ? 65 : 0xffffffbfu);
    run.put(self + 0x458, flipped ? 400 : 0xfffffe70u);
    selectAnimation(run, self, run.get(self + 0x370), false);
    run.put(self + 0x1a0, 0);
    return 0;
}

// 0x4388a0.
uint32_t tryFire(Run &run, uint32_t self) {
    if (run.get(0x537210) - run.get(self + 0x46c) >= run.get(self + 0x470)) {
        uint32_t frame = run.frame;
        run.frame -= 8;
        enterFiring(run, self);
        run.frame = frame;
        run.put(self + 0x470, run.get(0x537964) == 3 ? 2000 : 1500);
        run.put(self + 0x46c, run.get(0x537210));
    }
    return 0;
}

// 0x438a90. +0x1a0 projectile latch, projectile +0x6c logic and logic +0x18 movement.
uint32_t updateFiring(Run &run, uint32_t self) {
    uint32_t advanced = run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (advanced == 1 && !run.get(self + 0x1a0)) {
        uint32_t dy = run.get(self + 0x454);
        run.put(self + 0x1a0, 1);
        uint32_t actor = run.get(self + 0x12c);
        uint32_t projectile = run.call(0x4c8da0, run.get(run.get(run.get(self + 0x130) + 0x0c) + 0x08), {0, run.get(self + 0x450) + run.get(actor + 0x4c), dy + run.get(actor + 0x50), run.get(actor + 0x64) - 1, 0x522e0c, 0x40000});
        run.call(0x4c7970, projectile, {0x526d84});
        uint32_t logic = run.get(projectile + 0x6c);
        run.put(projectile + 0x104, 10);
        run.put(projectile + 0xd0, 0x40);
        run.call(run.get(logic + 0x10), 0, {projectile});
        uint32_t movement = run.get(run.get(projectile + 0x6c) + 0x18);
        run.putd(movement + 0x50, double(s32(run.get(self + 0x458))));
        movement = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(movement + 0x58, 0);
        run.put(movement + 0x5c, 0);
        movement = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(movement + 0x40, 0);
        run.put(movement + 0x44, 0);
        if (s32(run.get(self + 0x458)) < 0) {
            movement = run.get(run.get(projectile + 0x6c) + 0x18);
            actor = run.get(movement + 0x12c);
            if (!(run.get8(actor + 0x40) & 2)) {
                uint32_t left = run.get(movement + 0x138);
                run.put(movement + 0x138, 0u - run.get(movement + 0x140));
                run.put(movement + 0x140, 0u - left);
                run.put(actor + 0x40, run.get(actor + 0x40) | 2);
                actor = run.get(movement + 0x12c);
                left = run.get(actor + 0x118);
                if (left != 0x80000000u) {
                    run.put(actor + 0x118, 0u - run.get(actor + 0x120));
                    run.put(actor + 0x120, 0u - left);
                }
                left = run.get(actor + 0x128);
                if (left != 0x80000000u) {
                    run.put(actor + 0x128, 0u - run.get(actor + 0x130));
                    run.put(actor + 0x130, 0u - left);
                }
                run.call(0x406180, actor);
            }
        }
        uint32_t sound = run.get(self + 0x3b4);
        if (sound && run.get(0x532c0c))
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
    uint32_t animation = run.get(self + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14))
        run.vcall(self, 0x44);
    return 0;
}

// 0x438030. +0x2f4 bitset, +0x1a8/+0x1a4 CStrings.
void destruct(Run &run, uint32_t self) {
    run.put(self, 0x50b16c);
    run.call(0x4dbcd0, self + 0x2f4);
    run.call(0x4f6584, self + 0x1a8);
    run.call(0x4f6584, self + 0x1a4);
    run.put(self, 0x50b014);
}

// 0x437a90.
uint32_t construct(Run &run, uint32_t self, uint32_t actor) {
    run.call(0x44c000, self, {actor});
    run.put(self + 0x46c, 0);
    run.put(self + 0x470, 0);
    run.put(self + 0x474, 0);
    run.put(self + 0x478, 0);
    run.put(self, 0x50c934);
    run.call(0x4c7970, run.get(self + 0x12c), {0x526d34});
    uint32_t count = run.get(self + 0x2fc);
    if (count <= 8) {
        run.call(0x4dbd20, self + 0x2f4, {8});
    } else {
        uint32_t bits = count <= 32 ? self + 0x300 : run.get(self + 0x300);
        run.put(bits, run.get(bits) | 0x100);
    }
    uint32_t value;
    value = run.call(0x4062e0, self + 0x128, {0x526d1c});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x30c, value);
    value = run.call(0x4062e0, self + 0x128, {0x526d04});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x310, value);
    value = run.call(0x4062e0, self + 0x128, {0x526cec});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x370, value);
    value = run.call(0x4062e0, self + 0x128, {0x526cd4});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x32c, value);
    value = run.call(0x4062e0, self + 0x128, {0x526cd4});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x374, value);
    value = run.call(0x4062e0, self + 0x128, {0x526cbc});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x334, value);
    value = run.call(0x4062e0, self + 0x128, {0x526ca4});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x338, value);
    value = run.call(0x4062e0, self + 0x128, {0x526c8c});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x344, value);
    value = run.call(0x4062e0, self + 0x128, {0x526d1c});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x34c, value);
    value = run.call(0x4062e0, self + 0x128, {0x526c74});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x378, value);
    value = run.call(0x4062e0, self + 0x128, {0x526c5c});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x37c, value);
    value = run.call(0x4062e0, self + 0x128, {0x526c44});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x318, value);
    value = run.call(0x4062e0, self + 0x128, {0x526c2c});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x31c, value);
    value = run.call(0x4062e0, self + 0x128, {0x526c14});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x320, value);
    value = run.call(0x4062e0, self + 0x128, {0x526bfc});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x324, value);
    value = run.call(0x4062e0, self + 0x128, {0x526be4});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x33c, value);
    value = run.call(0x4062e0, self + 0x128, {0x526c5c});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x380, value);
    value = run.call(0x4062e0, self + 0x128, {0x526bcc});
    if (!value)
        value = run.call(0x4062e0, self + 0x128, {0x5234b4});
    run.put(self + 0x36c, value);
    uint32_t scratch = run.automatic(4);
    run.put(scratch, 0);
    run.call(0x4f6286, worldMap(run, self, 0x28) + 0x10, {0x526bb0, scratch});
    run.put(self + 0x3a4, run.get(scratch));
    run.put(scratch, 0);
    run.call(0x4f6286, worldMap(run, self, 0x28) + 0x10, {0x526b94, scratch});
    run.put(self + 0x410, run.get(scratch));
    value = run.call(0x4061b0, worldMap(run, self, 0x28), {0x526b78});
    run.put(self + 0x3b4, value);
    value = run.call(0x4061b0, worldMap(run, self, 0x28), {0x526b5c});
    run.put(self + 0x460, value);
    value = run.call(0x4061b0, worldMap(run, self, 0x28), {0x526b40});
    run.put(self + 0x464, value);
    value = run.call(0x4061b0, worldMap(run, self, 0x28), {0x526b24});
    run.put(self + 0x45c, value);
    uint32_t setRect = run.get(0x546d5c);
    run.call(setRect, 0, {self + 0x220, 0xffffffb5, 0, 0, 27});
    run.call(setRect, 0, {self + 0x210, 0xffffffff, 0xffffffff, 1, 1});
    run.call(setRect, 0, {self + 0x250, 0xfffffff1, 0xffffffe2, 15, 55});
    run.call(setRect, 0, {self + 0x260, 0xffffffd2, 0xffffffec, 46, 14});
    run.put(self + 0x28c, 400);
    run.put(self + 0x290, 50);
    run.put(self + 0x294, 300);
    run.put(self + 0x298, 50);
    run.put(self + 0x29c, 200);
    run.put(self + 0x2a0, 50);
    run.put(self + 0x2a4, 75);
    run.put(self + 0x2a8, 50);
    run.put(self + 0x2ac, 50);
    run.put(self + 0x2b0, 50);
    run.put(self + 0x2b4, 0);
    run.put(self + 0x2b8, 0);
    run.put(self + 0x2bc, 0xffffffe2);
    run.put(self + 0x2c0, 0xffffffec);
    run.put(self + 0x2c4, 20);
    run.put(self + 0x2c8, 0xfffffff1);
    run.put(self + 0x2e4, 50);
    value = run.call_x87(0x4a30e0, 0, double(run.getf(0x5262b8)) * double(run.getf(0x50c928)));
    run.put(self + 0x2e4, value > 99 ? value : 99);
    run.put(run.get(self + 0x0c) + 0x10c, run.get(0x537964) == 3 ? 7 : 9);
    value = run.call_x87(0x4a30e0, 0, double(s32(run.get(run.get(self + 0x0c) + 0x10c))) * double(run.getf(0x5262b4)));
    run.put(run.get(self + 0x0c) + 0x10c, value);
    run.put(run.get(self + 0x0c) + 0x104, 10);
    value = run.call_x87(0x4a30e0, 0, double(s32(run.get(run.get(self + 0x0c) + 0x104))) * double(run.getf(0x5262b0)));
    run.put(run.get(self + 0x0c) + 0x104, value);
    run.call(0x40f6c0, run.get(self + 0x12c), {run.get(self + 0x250), run.get(self + 0x254), run.get(self + 0x258), run.get(self + 0x25c)});
    run.call(0x4208b0, run.get(self + 0x12c), {0xffffffec, 0xffffffce, 20, 50});
    run.call(0x40abf0, self + 0x128);
    enterIdle(run, self);
    return self;
}

uint32_t dispatchOrdinary(Run &run, uint32_t self, uint32_t state) {
    run.put(0x5375b8, 0);
    uint32_t slot;
    bool outside = s32(state) < s32(run.get(0x5375a0)) || s32(state) > s32(run.get(0x5375a4));
    if (outside && !run.call(0x4db6e0, 0x537598, {state, 0})) {
        uint32_t message = run.get(0x544b4c);
        uint32_t pc = run.call(0x4db5f0, 0);
        run.put(0x544b14, pc);
        run.call(0x4db4d0, run.get(0x53759c), {0x537598, message, 12});
        slot = run.get(0x5375ac);
    } else {
        slot = (state - run.get(0x5375a0)) * run.get(0x5375b0) + run.get(0x5375a8);
    }
    if (!run.get(slot))
        return run.call(0x44c840, self, {state});
    run.put(0x5375b8, 0);
    outside = s32(state) < s32(run.get(0x5375a0)) || s32(state) > s32(run.get(0x5375a4));
    if (outside && !run.call(0x4db6e0, 0x537598, {state, 0})) {
        uint32_t message = run.get(0x544b4c);
        uint32_t pc = run.call(0x4db5f0, 0);
        run.put(0x544b14, pc);
        run.call(0x4db4d0, run.get(0x53759c), {0x537598, message, 12});
        slot = run.get(0x5375ac);
    } else {
        slot = (state - run.get(0x5375a0)) * run.get(0x5375b0) + run.get(0x5375a8);
    }
    return run.call(run.get(slot), self);
}

uint32_t arithmeticFlags(uint32_t old, uint32_t a, uint32_t b, bool subtract) {
    uint32_t result = subtract ? a - b : a + b;
    uint32_t flags = old & ~0x8d5u;
    flags |= result == 0 ? 0x40 : 0;
    flags |= result & 0x80000000u ? 0x80 : 0;
    flags |= (__builtin_parity(result & 0xff) == 0) ? 4 : 0;
    flags |= (a ^ b ^ result) & 0x10;
    flags |= subtract ? uint32_t(a < b) : uint32_t(uint64_t(a) + b > 0xffffffffu);
    flags |= ((subtract ? (a ^ b) : ~(a ^ b)) & (a ^ result) & 0x80000000u) ? 0x800 : 0;
    return flags;
}

void push(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}

uint32_t sourceCall(Run &run, ClawSourceContext &cpu, uint32_t function, uint32_t receiver, uint32_t pc, std::initializer_list<uint32_t> args, uint32_t pop) {
    push(run, cpu, pc);
    cpu.eip = function;
    auto child = cpu;
    child.outputMask = 0x7ff;
    run.source_call(function, receiver, pc, child, args, 0, pop);
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
    return cpu.eax;
}

// 0x438100. Explicit source frame for original diagnostic return addresses.
uint32_t dispatchSource(Run &run, uint32_t, uint32_t state) {
    auto &cpu = run.source();
    push(run, cpu, cpu.ebp);
    cpu.ebp = cpu.ecx;
    cpu.ecx = run.get(0x5375a0);
    push(run, cpu, cpu.esi);
    cpu.esi = state;
    push(run, cpu, cpu.edi);
    cpu.eflags = arithmeticFlags(cpu.eflags, cpu.esi, cpu.ecx, true);
    run.put(0x5375b8, 0);
    bool outside = s32(cpu.esi) < s32(cpu.ecx);
    if (!outside) {
        cpu.eflags = arithmeticFlags(cpu.eflags, cpu.esi, run.get(0x5375a4), true);
        outside = s32(cpu.esi) > s32(run.get(0x5375a4));
    }
    bool failed = false;
    if (outside) {
        push(run, cpu, 0);
        push(run, cpu, cpu.esi);
        cpu.ecx = 0x537598;
        sourceCall(run, cpu, 0x4db6e0, cpu.ecx, 0x438136, {cpu.esi, 0}, 8);
        cpu.eflags = (cpu.eflags & ~0x8d5u) | (cpu.eax == 0 ? 0x40 : 0) | (cpu.eax & 0x80000000u ? 0x80 : 0) | (__builtin_parity(cpu.eax & 0xff) == 0 ? 4 : 0);
        failed = cpu.eax == 0;
        if (!failed)
            cpu.ecx = run.get(0x5375a0);
    }
    if (failed) {
        cpu.edi = run.get(0x544b4c);
        sourceCall(run, cpu, 0x4db5f0, 0, 0x438160, {}, 0);
        cpu.ecx = run.get(0x53759c);
        push(run, cpu, 12);
        push(run, cpu, cpu.edi);
        push(run, cpu, 0x537598);
        run.put(0x544b14, cpu.eax);
        sourceCall(run, cpu, 0x4db4d0, cpu.ecx, 0x438178, {0x537598, cpu.edi, 12}, 12);
        cpu.eax = run.get(0x5375ac);
        cpu.ecx = run.get(0x5375a0);
    } else {
        cpu.eax = cpu.esi;
        cpu.eflags = arithmeticFlags(cpu.eflags, cpu.eax, cpu.ecx, true);
        cpu.eax -= cpu.ecx;
        cpu.edx = run.get(0x5375a8);
        cpu.eax *= run.get(0x5375b0);
        cpu.eflags = arithmeticFlags(cpu.eflags, cpu.eax, cpu.edx, false);
        cpu.eax += cpu.edx;
    }
    cpu.eflags = arithmeticFlags(cpu.eflags, run.get(cpu.eax), 0, true);
    if (!run.get(cpu.eax)) {
        push(run, cpu, cpu.esi);
        cpu.ecx = cpu.ebp;
        sourceCall(run, cpu, 0x44c840, cpu.ecx, 0x43820a, {cpu.esi}, 4);
    } else {
        cpu.eflags = arithmeticFlags(cpu.eflags, cpu.esi, cpu.ecx, true);
        run.put(0x5375b8, 0);
        outside = s32(cpu.esi) < s32(cpu.ecx);
        if (!outside) {
            cpu.eflags = arithmeticFlags(cpu.eflags, cpu.esi, run.get(0x5375a4), true);
            outside = s32(cpu.esi) > s32(run.get(0x5375a4));
        }
        failed = false;
        if (outside) {
            push(run, cpu, 0);
            push(run, cpu, cpu.esi);
            cpu.ecx = 0x537598;
            sourceCall(run, cpu, 0x4db6e0, cpu.ecx, 0x4381ab, {cpu.esi, 0}, 8);
            cpu.eflags = (cpu.eflags & ~0x8d5u) | (cpu.eax == 0 ? 0x40 : 0) | (cpu.eax & 0x80000000u ? 0x80 : 0) | (__builtin_parity(cpu.eax & 0xff) == 0 ? 4 : 0);
            failed = cpu.eax == 0;
            if (!failed)
                cpu.ecx = run.get(0x5375a0);
        }
        uint32_t pc;
        if (failed) {
            cpu.esi = run.get(0x544b4c);
            sourceCall(run, cpu, 0x4db5f0, 0, 0x4381da, {}, 0);
            cpu.ecx = run.get(0x53759c);
            push(run, cpu, 12);
            push(run, cpu, cpu.esi);
            push(run, cpu, 0x537598);
            run.put(0x544b14, cpu.eax);
            sourceCall(run, cpu, 0x4db4d0, cpu.ecx, 0x4381f2, {0x537598, cpu.esi, 12}, 12);
            cpu.esi = run.get(0x5375ac);
            pc = 0x4381fc;
        } else {
            cpu.eflags = arithmeticFlags(cpu.eflags, cpu.esi, cpu.ecx, true);
            cpu.esi -= cpu.ecx;
            cpu.eax = run.get(0x5375a8);
            cpu.esi *= run.get(0x5375b0);
            cpu.eflags = arithmeticFlags(cpu.eflags, cpu.esi, cpu.eax, false);
            cpu.esi += cpu.eax;
            pc = 0x4381c9;
        }
        cpu.ecx = cpu.ebp;
        sourceCall(run, cpu, run.get(cpu.esi), cpu.ecx, pc, {}, 0);
    }
    cpu.edi = run.get(cpu.esp);
    cpu.esp += 4;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 4;
    cpu.ebp = run.get(cpu.esp);
    cpu.esp += 4;
    return cpu.eax;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x437a90:
        return construct(run, receiver, arguments[0]);
    case 0x438010:
        destruct(run, receiver);
        if (arguments[0] & 1)
            run.call(0x4f6428, 0, {receiver});
        return receiver;
    case 0x438030:
        destruct(run, receiver);
        return 0;
    case 0x438100:
        return dispatchOrdinary(run, receiver, arguments[0]);
    case 0x4384f0:
        return enterIdle(run, receiver);
    case 0x4385b0:
        return updateIdle(run, receiver);
    case 0x4386d0:
        return updateHome(run, receiver);
    case 0x4388a0:
        return tryFire(run, receiver);
    case 0x438900:
        return enterFiring(run, receiver);
    case 0x438a90:
        return updateFiring(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

ClawSourceContract contract(uint32_t function) {
    if (function == 0x438100)
        return {0x7ff, 0x5f3, 0x472, 4};
    return {};
}

bool optional(uint32_t function) {
    return function == 0x438100;
}

uint32_t sourceBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    if (function == 0x438100)
        return dispatchSource(run, receiver, arguments[0]);
    return body(run, function, receiver, arguments);
}
} // namespace

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_level_three_batch_cutthroat_01_entry, owned, contract, optional, body, sourceBody)
