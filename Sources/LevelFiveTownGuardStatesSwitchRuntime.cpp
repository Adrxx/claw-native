// Level 5 town guard states and switch, recovered from the original entries.
#include "ClawRuntime.hpp"
namespace {
using claw::Run;
using claw::s32;
int owned(uint32_t f) {
    switch (f) {
    case 0x453bd0: case 0x497ab0: case 0x497b00: case 0x497c50: return 1;
    case 0x483dc0: case 0x497750: case 0x497970: case 0x4979b0: case 0x497a50: case 0x497dc0: return 0;
    default: return -1;
    }
}
uint32_t randomValue(Run &run) {
    return run.call(0x4a3050, 0);
}
uint32_t randomIndex(Run &run) {
    return uint32_t(s32(randomValue(run)) % 2) * 4u;
}
void sound(Run &run, uint32_t entry) {
    if (entry && run.get(0x532c0c)) {
        uint32_t channel = run.get(0x532c10);
        run.call(0x4b45f0, run.get(entry + 0x10), {channel, 0, 0, 0});
    }
}
// Actor facing +0x18c; collision bounds +0x138/+0x140; sprite +0x12c.
void face(Run &run, uint32_t self) {
    uint32_t actor = run.get(self + 0x12c);
    bool right = run.get(self + 0x18c) == 2;
    if (right == bool(run.get8(actor + 0x40) & 2)) return;
    uint32_t old = run.get(self + 0x138);
    uint32_t other = run.get(self + 0x140);
    run.put(self + 0x138, 0u - other);
    run.put(self + 0x140, 0u - old);
    uint32_t flags = run.get(actor + 0x40);
    run.put(actor + 0x40, right ? flags | 2u : flags & 0xfffffffdu);
    actor = run.get(self + 0x12c);
    run.call(0x406120, actor);
    run.call(0x406150, actor);
    run.call(0x406180, actor);
}
bool blockable(uint32_t state) {
    return state == 1 || state == 2 || state == 7 || state == 8;
}
// 0x497dc0. Enter block; save current state and animation.
uint32_t block(Run &run, uint32_t self) {
    uint32_t state = run.get(self + 0x10);
    run.put(self + 0x20, 1);
    run.put(self + 0x24, run.get(state + 0x1c));
    uint32_t next = run.call(0x4dba00, 0x537668, {0x526a38});
    run.put(run.get(self + 0x10) + 0x1c, next);
    uint32_t actor = run.get(self + 0x12c);
    uint32_t animation = run.get(self + 0x384);
    run.put(self + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    actor = run.get(self + 0x12c);
    run.put(actor + 0x08, run.get(actor + 0x08) | 4u);
    sound(run, run.get(self + 0x478 + randomIndex(run)));
    if (s32(randomValue(run)) % 100 < 40) {
        sound(run, run.get(self + 0x460 + randomIndex(run)));
    }
    return 0;
}
// 0x453bd0. Switch construction; +0x08/+0x0c and +0x28/+0x2c actors.
uint32_t construct(Run &run, uint32_t self, uint32_t actor) {
    run.put(self, 0x50b064);
    run.put(self + 0x08, actor);
    run.put(self + 0x0c, actor);
    run.put(self + 0x10, run.get(actor + 0x6c));
    run.put(self + 0x04, 0);
    run.call(0x4c7fa0, actor, {0x522d54});
    run.call(0x4c8060, run.get(self + 0x0c), {0x522d48});
    run.put(self + 0x14, 0);
    run.put(self + 0x18, 0);
    run.put(self + 0x1c, 0x3e9);
    run.put(self + 0x20, 2);
    run.put(self + 0x28, actor);
    run.put(self + 0x2c, actor);
    run.put(self + 0x30, run.get(actor + 0x6c));
    run.put(self, 0x50e244);
    uint32_t target = run.get(self + 0x2c);
    run.put(target + 0x138, 0xfffffffbu);
    run.put(target + 0x13c, 0xfffffffbu);
    run.put(target + 0x140, 5);
    run.put(target + 0x144, 5);
    run.put(run.get(self + 0x2c) + 0xd0, 0x1000);
    run.put(run.get(self + 0x2c) + 0xd4, 1);
    return self;
}
// 0x483dc0. Finish blocking when the current animation completes.
uint32_t blockTick(Run &run, uint32_t self) {
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t actor = run.get(self + 0x12c);
    if (run.get(actor + 0x1a4) && !run.get(actor + 0x19c)) {
        run.put(actor + 0x08, run.get(actor + 0x08) & 0xfffffffbu);
        run.vcall(self, 0x44);
        run.put(self + 0x20, 2);
    }
    return 0;
}
// 0x497750. Home state: spot player, face, and choose the next action.
uint32_t home(Run &run, uint32_t self) {
    if (!run.get(self + 0x484)) {
        bool spotted = false;
        if (run.get(0x534eac) != 0x26b7) {
            uint32_t player = run.get(0x537e88);
            uint32_t object = run.get(self + 0x194);
            uint32_t world = run.get(run.get(self + 0x190) + 0x0c);
            uint32_t visible = run.call(0x4cda10, run.get(world + 0x24), {run.get(object + 0x4c), run.get(object + 0x50), run.get(player + 0x4c), 0x20});
            if (visible) {
                object = run.get(self + 0x194);
                player = run.get(0x537e88);
                uint32_t y = run.get(object + 0x50);
                uint32_t py = run.get(player + 0x50);
                spotted = s32(py) < s32(y + 0x32) && s32(py) > s32(y - 0x32) && run.get(object + 0x38) != 0xffffffffu;
            }
        }
        if (spotted) {
            if (s32(randomValue(run)) % 100 < 70) {
                uint32_t entry = run.get(self + 0x458 + randomIndex(run));
                run.call(0x48ce40, 0, {run.get(self + 0x0c), entry, 0});
            }
            run.put(self + 0x484, 1);
        }
    }
    if (run.get(self + 0x18c) == 2) {
        uint32_t actor = run.get(self + 0x12c);
        if (!(run.get8(actor + 0x40) & 2)) {
            uint32_t old = run.get(self + 0x138);
            uint32_t other = run.get(self + 0x140);
            run.put(self + 0x138, 0u - other);
            run.put(self + 0x140, 0u - old);
            run.put(actor + 0x40, run.get(actor + 0x40) | 2u);
            run.call(0x4060b0, run.get(self + 0x12c));
        }
    } else {
        run.call(0x406310, self + 0x128);
    }
    int32_t choice = s32(randomValue(run)) % 121;
    switch (run.get(self + 0x184)) {
    case 3: {
        uint32_t threshold = run.get(self + 0x2e4);
        if (choice < s32(threshold)) {
            uint32_t value = run.get(self + 0x470 + randomIndex(run));
            run.put(self + 0x3a0, value);
            run.vcall(self, 0x58);
        } else if (choice < s32(threshold + 0x14)) {
            run.vcall(self, 0x68);
        }
        break;
    }
    case 4:
        if (s32(randomValue(run)) % 100 < 50) {
            run.vcall(self, 0x64);
        } else {
            uint32_t index = randomIndex(run);
            uint32_t method = run.get(run.get(self) + 0x58);
            uint32_t value = run.get(self + 0x470 + index);
            run.put(self + 0x3a0, value);
            run.call(method, self);
        }
        break;
    case 5: case 6:
        run.put(self + 0x480, 0x5a);
        run.call(0x44edd0, self);
        break;
    default: break;
    }
    run.call(0x44da20, self);
    return 0;
}
// 0x497970. Enter idle with an optional vocalization.
uint32_t enterIdle(Run &run, uint32_t self) {
    if (run.get(self + 0x184) != 6 && s32(randomValue(run)) % 100 < 20) {
        run.call(0x48ce40, 0, {run.get(self + 0x0c), run.get(self + 0x454), 0});
    }
    run.call(0x44f1b0, self);
    return 0;
}
// 0x4979b0. Idle animation completion starts the timed second idle.
uint32_t idle(Run &run, uint32_t self) {
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t actor = run.get(self + 0x12c);
    if (run.get(actor + 0x1a4) && !run.get(actor + 0x19c)) {
        uint32_t nextAnimation = run.get(self + 0x450);
        run.put(self + 0x134, run.get(actor + 0x190));
        run.call(0x4c8220, actor + 0x188, {nextAnimation});
        run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
        uint32_t state = run.call(0x4dba00, 0x537668, {0x52d464});
        run.put(run.get(self + 0x10) + 0x1c, state);
        uint32_t delay = uint32_t(s32(randomValue(run)) % 2001);
        run.put(self + 0x48c, delay);
        run.put(self + 0x488, run.get(0x537210));
    }
    return 0;
}
// 0x497a50. Unsigned elapsed-time check, including timer wrap.
uint32_t idle2(Run &run, uint32_t self) {
    if (run.get(0x537210) - run.get(self + 0x488) >= run.get(self + 0x48c)) {
        run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
        uint32_t actor = run.get(self + 0x12c);
        if (run.get(actor + 0x1a4) && !run.get(actor + 0x19c)) {
            run.call(0x44edd0, self);
        }
    }
    return 0;
}
// 0x497ab0. Hit fallback with randomized sound.
uint32_t hit(Run &run, uint32_t self, uint32_t arg) {
    sound(run, run.get(self + 0x468 + randomIndex(run)));
    return run.call(0x44d460, self, {arg});
}
// 0x497b00. Difficulty-six hit response can enter block.
uint32_t hitBlock(Run &run, uint32_t self, uint32_t arg) {
    if (run.get(0x537964) == 6 && s32(randomValue(run)) % 100 < 25) {
        uint32_t player = run.get(0x537e88);
        uint32_t state = run.get(run.get(run.get(player + 0x6c) + 0x14) + 0x3c);
        if (blockable(state) && run.get(player + 0xcc) == 1) {
            face(run, self);
            return block(run, self);
        }
    }
    return hit(run, self, arg);
}
// 0x497c50. Difficulty-five/six reaction with exact original return.
uint32_t reaction(Run &run, uint32_t self, uint32_t arg) {
    uint32_t player = run.get(0x537e88);
    uint32_t state = run.get(run.get(run.get(player + 0x6c) + 0x14) + 0x3c);
    if (blockable(state)) {
        uint32_t mode = run.get(player + 0xcc);
        if (mode == 1 || mode == 5) {
            bool chosen = false;
            if (run.get(0x537964) == 5) {
                chosen = s32(randomValue(run)) % 100 < 25;
            }
            if (!chosen && run.get(0x537964) == 6) {
                chosen = s32(randomValue(run)) % 100 < 50;
            }
            if (chosen) {
                face(run, self);
                return block(run, self);
            }
        }
    }
    return hit(run, self, arg);
}
uint32_t body(Run &run, uint32_t f, uint32_t self, const uint32_t *args) {
    switch (f) {
    case 0x453bd0: return construct(run, self, args[0]);
    case 0x483dc0: return blockTick(run, self);
    case 0x497750: return home(run, self);
    case 0x497970: return enterIdle(run, self);
    case 0x4979b0: return idle(run, self);
    case 0x497a50: return idle2(run, self);
    case 0x497ab0: return hit(run, self, args[0]);
    case 0x497b00: return hitBlock(run, self, args[0]);
    case 0x497c50: return reaction(run, self, args[0]);
    case 0x497dc0: return block(run, self);
    default: run.fail(CLAW_FAULT_ABI, f);
    }
}
// Integer CPU transport at the four registered TownGuard state targets.
uint32_t flags(uint32_t value) {
    uint32_t low = value & 0xff;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    return 2u | ((low & 1) ? 0u : 4u) | (value ? 0u : 0x40u) | (value & 0x80000000u ? 0x80u : 0u);
}
void logic(ClawSourceContext &cpu, uint32_t value) {
    cpu.eflags = flags(value);
}
uint32_t subtract(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    uint32_t value = left - right;
    cpu.eflags = flags(value) | (left < right ? 1u : 0u) | ((left ^ right ^ value) & 0x10u) |
        (((left ^ right) & (left ^ value) & 0x80000000u) ? 0x800u : 0u);
    return value;
}
uint32_t add(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    uint32_t value = left + right;
    cpu.eflags = flags(value) | (value < left ? 1u : 0u) | ((left ^ right ^ value) & 0x10u) |
        (((~(left ^ right)) & (left ^ value) & 0x80000000u) ? 0x800u : 0u);
    return value;
}
void push(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}
uint32_t pop(Run &run, ClawSourceContext &cpu) {
    uint32_t value = run.get(cpu.esp);
    cpu.esp += 4;
    return value;
}
ClawSourceContext childFrame(Run &run, ClawSourceContext &cpu, uint32_t target, uint32_t continuation) {
    push(run, cpu, continuation);
    auto child = cpu;
    child.eip = target;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0x472;
    return child;
}
void adopt(ClawSourceContext &cpu, const ClawSourceContext &child) {
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
}
void sourceRandom(Run &run, ClawSourceContext &cpu, uint32_t continuation) {
    auto child = childFrame(run, cpu, 0x4a3050, continuation);
    run.source_call(0x4a3050, 0, continuation, child);
    adopt(cpu, child);
}
void divide(ClawSourceContext &cpu) {
    int32_t dividend = s32(cpu.eax);
    cpu.edx = uint32_t(dividend % int32_t(cpu.ecx));
    cpu.eax = uint32_t(dividend / int32_t(cpu.ecx));
}
// 0x483dc0, 0x4979b0 and 0x497a50. Each physical PUSH and continuation
// remains visible to the original descendants and to the caller's stack.
uint32_t sourceTick(Run &run, uint32_t function) {
    auto &cpu = run.source();
    cpu.eax = run.get(function == 0x497a50 ? 0x537210 : 0x5430c4);
    push(run, cpu, cpu.esi);
    cpu.esi = cpu.ecx;
    if (function == 0x497a50) {
        cpu.edx = run.get(cpu.esi + 0x488);
        cpu.ecx = run.get(cpu.esi + 0x48c);
        cpu.eax = subtract(cpu, cpu.eax, cpu.edx);
        subtract(cpu, cpu.eax, cpu.ecx);
        if (cpu.eax < cpu.ecx)
            goto tickDone;
        cpu.ecx = run.get(0x5430c4);
        push(run, cpu, cpu.ecx);
    } else {
        push(run, cpu, cpu.eax);
    }
    cpu.ecx = run.get(cpu.esi + 0x12c);
    cpu.ecx = add(cpu, cpu.ecx, 0x188);
    {
        uint32_t continuation = function == 0x483dc0 ? 0x483dda : function == 0x4979b0 ? 0x4979ca : 0x497a82;
        auto child = childFrame(run, cpu, 0x4c82a0, continuation);
        run.source_call(0x4c82a0, cpu.ecx, continuation, child, {run.get(cpu.esp + 0x4)}, 0, 4);
        adopt(cpu, child);
    }
    cpu.eax = run.get(cpu.esi + 0x12c);
    if (function != 0x483dc0)
        cpu.eax = add(cpu, cpu.eax, 0x188);
    cpu.ecx = run.get(cpu.eax + (function == 0x483dc0 ? 0x1a4 : 0x1c));
    logic(cpu, cpu.ecx);
    if (!cpu.ecx)
        goto tickDone;
    cpu.ecx = run.get(cpu.eax + (function == 0x483dc0 ? 0x19c : 0x14));
    logic(cpu, cpu.ecx);
    if (cpu.ecx)
        goto tickDone;
    if (function == 0x483dc0) {
        cpu.ecx = run.get(cpu.eax + 0x8);
        cpu.ecx &= 0xfffffffbu;
        logic(cpu, cpu.ecx);
        run.put(cpu.eax + 0x8, cpu.ecx);
        cpu.edx = run.get(cpu.esi);
        cpu.ecx = cpu.esi;
        uint32_t target = run.get(cpu.edx + 0x44);
        auto child = childFrame(run, cpu, target, 0x483e04);
        run.source_call(target, cpu.ecx, 0x483e04, child);
        adopt(cpu, child);
        run.put(cpu.esi + 0x20, 2);
    } else if (function == 0x497a50) {
        cpu.ecx = cpu.esi;
        auto child = childFrame(run, cpu, 0x44edd0, 0x497aa2);
        run.source_call(0x44edd0, cpu.ecx, 0x497aa2, child);
        adopt(cpu, child);
    } else {
        cpu.eax = run.get(cpu.esi + 0x12c);
        cpu.ecx = run.get(cpu.esi + 0x450);
        push(run, cpu, cpu.ecx);
        cpu.edx = run.get(cpu.eax + 0x190);
        cpu.ecx = cpu.eax + 0x188;
        run.put(cpu.esi + 0x134, cpu.edx);
        auto child = childFrame(run, cpu, 0x4c8220, 0x497a07);
        run.source_call(0x4c8220, cpu.ecx, 0x497a07, child, {run.get(cpu.esp + 0x4)}, 0, 4);
        adopt(cpu, child);
        cpu.eax = run.get(cpu.esi + 0x10);
        push(run, cpu, 0x52d464);
        cpu.ecx = run.get(cpu.eax + 0x1c);
        run.put(cpu.esi + 0x24, cpu.ecx);
        cpu.ecx = 0x537668;
        child = childFrame(run, cpu, 0x4dba00, 0x497a1f);
        run.source_call(0x4dba00, cpu.ecx, 0x497a1f, child, {0x52d464}, 0, 4);
        adopt(cpu, child);
        cpu.edx = run.get(cpu.esi + 0x10);
        run.put(cpu.edx + 0x1c, cpu.eax);
        sourceRandom(run, cpu, 0x497a2a);
        cpu.edx = s32(cpu.eax) < 0 ? 0xffffffffu : 0;
        cpu.ecx = 0x7d1;
        divide(cpu);
        run.put(cpu.esi + 0x48c, cpu.edx);
        cpu.edx = run.get(0x537210);
        run.put(cpu.esi + 0x488, cpu.edx);
    }
tickDone:
    cpu.eax = 0;
    logic(cpu, cpu.eax);
    cpu.esi = pop(run, cpu);
    return cpu.eax;
}
// 0x497750. Home state's CPU and frame, including signed random choices.
uint32_t sourceHome(Run &run) {
    auto &cpu = run.source();
    push(run, cpu, cpu.esi);
    cpu.esi = cpu.ecx;
    push(run, cpu, cpu.edi);
    cpu.eax = run.get(cpu.esi + 0x484);
    logic(cpu, cpu.eax);
    if (!cpu.eax) {
        uint32_t spotted;
        subtract(cpu, run.get(0x534eac), 0x26b7);
        if (run.get(0x534eac) == 0x26b7)
            goto notSpotted;
        cpu.ecx = run.get(0x537e88);
        cpu.eax = run.get(cpu.esi + 0x194);
        push(run, cpu, 0x20);
        cpu.edx = run.get(cpu.ecx + 0x4c);
        cpu.ecx = run.get(cpu.eax + 0x50);
        push(run, cpu, cpu.edx);
        cpu.edx = run.get(cpu.eax + 0x4c);
        cpu.eax = run.get(cpu.esi + 0x190);
        push(run, cpu, cpu.ecx);
        push(run, cpu, cpu.edx);
        cpu.ecx = run.get(cpu.eax + 0xc);
        cpu.ecx = run.get(cpu.ecx + 0x24);
        {
            auto child = childFrame(run, cpu, 0x4cda10, 0x497799);
            run.source_call(0x4cda10, cpu.ecx, 0x497799, child,
                {run.get(cpu.esp + 0x4), run.get(cpu.esp + 0x8), run.get(cpu.esp + 0xc), run.get(cpu.esp + 0x10)}, 0, 16);
            adopt(cpu, child);
        }
        logic(cpu, cpu.eax);
        if (!cpu.eax)
            goto notSpotted;
        cpu.edx = run.get(cpu.esi + 0x194);
        cpu.ecx = run.get(0x537e88);
        cpu.eax = run.get(cpu.edx + 0x50);
        cpu.ecx = run.get(cpu.ecx + 0x50);
        cpu.edi = cpu.eax + 0x32;
        subtract(cpu, cpu.ecx, cpu.edi);
        if (s32(cpu.ecx) >= s32(cpu.edi))
            goto notSpotted;
        cpu.eax = add(cpu, cpu.eax, 0xffffffceu);
        subtract(cpu, cpu.ecx, cpu.eax);
        if (s32(cpu.ecx) <= s32(cpu.eax))
            goto notSpotted;
        spotted = run.get(cpu.edx + 0x38);
        subtract(cpu, spotted, 0xffffffffu);
        if (spotted == 0xffffffffu)
            goto notSpotted;
        cpu.eax = 1;
        goto spotTest;
notSpotted:
        cpu.eax = 0;
        logic(cpu, cpu.eax);
spotTest:
        logic(cpu, cpu.eax);
        if (cpu.eax) {
            sourceRandom(run, cpu, 0x4977d5);
            cpu.edx = s32(cpu.eax) < 0 ? 0xffffffffu : 0;
            cpu.ecx = 0x64;
            divide(cpu);
            subtract(cpu, cpu.edx, 0x46);
            if (s32(cpu.edx) < 70) {
                sourceRandom(run, cpu, 0x4977e7);
                cpu.edx = s32(cpu.eax) < 0 ? 0xffffffffu : 0;
                cpu.eax ^= cpu.edx;
                logic(cpu, cpu.eax);
                push(run, cpu, 0);
                cpu.eax = subtract(cpu, cpu.eax, cpu.edx);
                cpu.eax &= 1;
                logic(cpu, cpu.eax);
                cpu.eax ^= cpu.edx;
                logic(cpu, cpu.eax);
                cpu.eax = subtract(cpu, cpu.eax, cpu.edx);
                cpu.edx = run.get(cpu.esi + cpu.eax * 4 + 0x458);
                cpu.eax = run.get(cpu.esi + 0xc);
                push(run, cpu, cpu.edx);
                push(run, cpu, cpu.eax);
                auto child = childFrame(run, cpu, 0x48ce40, 0x497806);
                run.source_call(0x48ce40, 0, 0x497806, child,
                    {run.get(cpu.esp + 0x4), run.get(cpu.esp + 0x8), run.get(cpu.esp + 0xc)});
                adopt(cpu, child);
                cpu.esp = add(cpu, cpu.esp, 0xc);
            }
            run.put(cpu.esi + 0x484, 1);
        }
    }
    cpu.eax = run.get(cpu.esi + 0x18c);
    cpu.edx = 2;
    subtract(cpu, cpu.eax, cpu.edx);
    if (cpu.eax == cpu.edx) {
        cpu.ecx = run.get(cpu.esi + 0x12c);
        uint32_t bits = run.get8(cpu.ecx + 0x40) & (cpu.edx & 0xff);
        logic(cpu, bits);
        if (!bits) {
            cpu.eax = run.get(cpu.esi + 0x138);
            cpu.edi = run.get(cpu.esi + 0x140);
            cpu.edi = subtract(cpu, 0, cpu.edi);
            cpu.eax = subtract(cpu, 0, cpu.eax);
            run.put(cpu.esi + 0x138, cpu.edi);
            run.put(cpu.esi + 0x140, cpu.eax);
            cpu.eax = run.get(cpu.ecx + 0x40);
            cpu.eax |= cpu.edx;
            logic(cpu, cpu.eax);
            run.put(cpu.ecx + 0x40, cpu.eax);
            cpu.ecx = run.get(cpu.esi + 0x12c);
            auto child = childFrame(run, cpu, 0x4060b0, 0x49785c);
            run.source_call(0x4060b0, cpu.ecx, 0x49785c, child);
            adopt(cpu, child);
        }
    } else {
        cpu.ecx = cpu.esi + 0x128;
        auto child = childFrame(run, cpu, 0x406310, 0x497869);
        run.source_call(0x406310, cpu.ecx, 0x497869, child);
        adopt(cpu, child);
    }
    sourceRandom(run, cpu, 0x49786e);
    cpu.edx = s32(cpu.eax) < 0 ? 0xffffffffu : 0;
    cpu.ecx = 0x79;
    divide(cpu);
    cpu.eax = run.get(cpu.esi + 0x184);
    cpu.eax = add(cpu, cpu.eax, 0xfffffffdu);
    subtract(cpu, cpu.eax, 3);
    if (cpu.eax > 3)
        goto homeFinal;
    if (cpu.eax >= 2) {
        cpu.ecx = cpu.esi;
        run.put(cpu.esi + 0x480, 0x5a);
        auto child = childFrame(run, cpu, 0x44edd0, 0x4978a0);
        run.source_call(0x44edd0, cpu.ecx, 0x4978a0, child);
        adopt(cpu, child);
        cpu.ecx = cpu.esi;
        child = childFrame(run, cpu, 0x44da20, 0x4978a7);
        run.source_call(0x44da20, cpu.ecx, 0x4978a7, child);
        adopt(cpu, child);
        goto homeDone;
    }
    if (!cpu.eax) {
        cpu.eax = run.get(cpu.esi + 0x2e4);
        subtract(cpu, cpu.edx, cpu.eax);
        if (s32(cpu.edx) < s32(cpu.eax)) {
            sourceRandom(run, cpu, 0x4978bb);
            cpu.edx = s32(cpu.eax) < 0 ? 0xffffffffu : 0;
            cpu.eax ^= cpu.edx;
            logic(cpu, cpu.eax);
            cpu.ecx = cpu.esi;
            cpu.eax = subtract(cpu, cpu.eax, cpu.edx);
            cpu.eax &= 1;
            logic(cpu, cpu.eax);
            cpu.eax ^= cpu.edx;
            logic(cpu, cpu.eax);
            cpu.eax = subtract(cpu, cpu.eax, cpu.edx);
            cpu.edx = run.get(cpu.esi + cpu.eax * 4 + 0x470);
            cpu.eax = run.get(cpu.esi);
            run.put(cpu.esi + 0x3a0, cpu.edx);
            uint32_t target = run.get(cpu.eax + 0x58);
            auto child = childFrame(run, cpu, target, 0x4978db);
            run.source_call(target, cpu.ecx, 0x4978db, child);
            adopt(cpu, child);
            cpu.ecx = cpu.esi;
            child = childFrame(run, cpu, 0x44da20, 0x4978e2);
            run.source_call(0x44da20, cpu.ecx, 0x4978e2, child);
            adopt(cpu, child);
            goto homeDone;
        }
        cpu.eax = add(cpu, cpu.eax, 0x14);
        subtract(cpu, cpu.edx, cpu.eax);
        if (s32(cpu.edx) >= s32(cpu.eax))
            goto homeFinal;
        cpu.edx = run.get(cpu.esi);
        cpu.ecx = cpu.esi;
        {
            uint32_t target = run.get(cpu.edx + 0x68);
            auto child = childFrame(run, cpu, target, 0x4978f5);
            run.source_call(target, cpu.ecx, 0x4978f5, child);
            adopt(cpu, child);
            cpu.ecx = cpu.esi;
            child = childFrame(run, cpu, 0x44da20, 0x4978fc);
            run.source_call(0x44da20, cpu.ecx, 0x4978fc, child);
            adopt(cpu, child);
        }
        goto homeDone;
    }
    sourceRandom(run, cpu, 0x497906);
    cpu.edx = s32(cpu.eax) < 0 ? 0xffffffffu : 0;
    cpu.ecx = 0x64;
    divide(cpu);
    subtract(cpu, cpu.edx, 0x32);
    if (s32(cpu.edx) < 50) {
        cpu.edx = run.get(cpu.esi);
        cpu.ecx = cpu.esi;
        uint32_t target = run.get(cpu.edx + 0x64);
        auto child = childFrame(run, cpu, target, 0x49791a);
        run.source_call(target, cpu.ecx, 0x49791a, child);
        adopt(cpu, child);
        cpu.ecx = cpu.esi;
        child = childFrame(run, cpu, 0x44da20, 0x497921);
        run.source_call(0x44da20, cpu.ecx, 0x497921, child);
        adopt(cpu, child);
        goto homeDone;
    }
    sourceRandom(run, cpu, 0x49792b);
    cpu.edx = s32(cpu.eax) < 0 ? 0xffffffffu : 0;
    cpu.eax ^= cpu.edx;
    logic(cpu, cpu.eax);
    cpu.ecx = cpu.esi;
    cpu.eax = subtract(cpu, cpu.eax, cpu.edx);
    cpu.eax &= 1;
    logic(cpu, cpu.eax);
    cpu.eax ^= cpu.edx;
    logic(cpu, cpu.eax);
    cpu.eax = subtract(cpu, cpu.eax, cpu.edx);
    cpu.edx = run.get(cpu.esi);
    cpu.eax = run.get(cpu.esi + cpu.eax * 4 + 0x470);
    run.put(cpu.esi + 0x3a0, cpu.eax);
    {
        uint32_t target = run.get(cpu.edx + 0x58);
        auto child = childFrame(run, cpu, target, 0x49794b);
        run.source_call(target, cpu.ecx, 0x49794b, child);
        adopt(cpu, child);
    }
homeFinal:
    cpu.ecx = cpu.esi;
    {
        auto child = childFrame(run, cpu, 0x44da20, 0x497952);
        run.source_call(0x44da20, cpu.ecx, 0x497952, child);
        adopt(cpu, child);
    }
homeDone:
    cpu.eax = 0;
    logic(cpu, cpu.eax);
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
    return cpu.eax;
}
ClawSourceContract sourceContract(uint32_t function) {
    switch (function) {
    case 0x483dc0:
    case 0x497750:
    case 0x4979b0:
    case 0x497a50:
        return {0x7ff, 0x5ff, 0x472, 0};
    default:
        return {};
    }
}
bool optionalSource(uint32_t function) {
    return sourceContract(function).inputMask != 0;
}
uint32_t sourceBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    if (function == 0x497750)
        return sourceHome(run);
    if (optionalSource(function))
        return sourceTick(run, function);
    return body(run, function, receiver, arguments);
}

}
CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_level_five_town_guard_states_switch_entry, owned, sourceContract, optionalSource, body, sourceBody)
