// Level 5 town guard construction, lifetime, dispatch and strike behavior.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x496110:
    case 0x496840:
    case 0x496990:
    case 0x497040:
    case 0x497130:
    case 0x497510:
        return 1;
    case 0x496860:
    case 0x497060:
        return 0;
    default:
        return -1;
    }
}

ClawSourceContract contract(uint32_t function) {
    if (function == 0x497130)
        return {0x7ff, 0x5ff, 0x472, 0x4};
    return {};
}

// The embedded actor's resource maps are reloaded after every lookup.
uint32_t resourceMap(Run &run, uint32_t receiver, uint32_t offset) {
    return run.get(run.get(run.get(receiver + 0x12c) + 0xc) + offset);
}

uint32_t animation(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t value = run.call(0x4062e0, receiver + 0x128, {name});
    if (!value)
        value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    return value;
}

void copyRectangle(Run &run, uint32_t receiver, uint32_t rectangle) {
    // Active collision rectangle, four signed edges at +0x220.
    run.put(receiver + 0x220, run.get(receiver + rectangle));
    run.put(receiver + 0x224, run.get(receiver + rectangle + 0x4));
    run.put(receiver + 0x228, run.get(receiver + rectangle + 0x8));
    run.put(receiver + 0x22c, run.get(receiver + rectangle + 0xc));
}

// Widen a finite binary32 memory operand exactly; the x87 primitive performs
// the load or multiplication and retains the inherited status and live slots.
void floatOperand(Run &run, ClawX87State &fp, uint32_t operation, uint32_t address) {
    double value = double(run.getf(address));
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    run.x87_step(operation, fp, {uint32_t(bits), uint32_t(bits >> 32)});
}

uint32_t convert(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

void balancedCall(Run &run, ClawX87State &fp, uint32_t function, uint32_t receiver) {
    fp.popCount = 0;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    run.call_x87_exact(function, receiver, fp);
}

// 0x496110 and 0x496990. Both guards share layout and initialization order.
uint32_t construct(Run &run, uint32_t receiver, uint32_t argument, bool second) {
    uint32_t function = second ? 0x496990 : 0x496110;
    auto fp = run.x87_entry(function);
    run.call_x87_exact(0x44c000, receiver, fp, {argument});
    // Per-guard counters and clocks.
    run.put(receiver + 0x488, 0);
    run.put(receiver + 0x48c, 0);
    run.put(receiver + 0x490, 0);
    run.put(receiver + 0x494, 0);
    run.put(receiver + 0x0, second ? 0x50fb6c : 0x50fabc);
    run.call(0x4c7970, run.get(receiver + 0x12c), {second ? 0x52d450u : 0x52d204u});
    // Animation slots: advance, fast advance, strike, falls, idles, hits,
    // jump, home, lifted and thrown sequences, then alternate strike.
    run.put(receiver + 0x308, animation(run, receiver, second ? 0x52d434 : 0x52d1e8));
    run.put(receiver + 0x30c, animation(run, receiver, second ? 0x52d414 : 0x52d1c8));
    run.put(receiver + 0x310, animation(run, receiver, second ? 0x52d3f8 : 0x52d1ac));
    run.put(receiver + 0x32c, animation(run, receiver, second ? 0x52d3dc : 0x52d190));
    run.put(receiver + 0x374, animation(run, receiver, second ? 0x52d3dc : 0x52d190));
    run.put(receiver + 0x350, animation(run, receiver, second ? 0x52d3c4 : 0x52d178));
    run.put(receiver + 0x450, animation(run, receiver, second ? 0x52d3ac : 0x52d160));
    run.put(receiver + 0x334, animation(run, receiver, second ? 0x52d394 : 0x52d148));
    run.put(receiver + 0x338, animation(run, receiver, second ? 0x52d378 : 0x52d12c));
    run.put(receiver + 0x33c, animation(run, receiver, second ? 0x52d360 : 0x52d114));
    run.put(receiver + 0x340, animation(run, receiver, second ? 0x52d360 : 0x52d114));
    run.put(receiver + 0x344, animation(run, receiver, second ? 0x52d348 : 0x52d0fc));
    run.put(receiver + 0x34c, animation(run, receiver, second ? 0x52d414 : 0x52d1c8));
    run.put(receiver + 0x378, animation(run, receiver, second ? 0x52d32c : 0x52d0e0));
    run.put(receiver + 0x37c, animation(run, receiver, second ? 0x52d310 : 0x52d0c4));
    run.put(receiver + 0x380, animation(run, receiver, second ? 0x52d310 : 0x52d0c4));
    run.put(receiver + 0x36c, animation(run, receiver, second ? 0x52d2f8 : 0x52d0ac));
    run.put(receiver + 0x384, animation(run, receiver, 0x52d1ac));
    uint32_t random = run.call(0x4a3050, 0);
    uint32_t soundName = s32(random) % 100 < 50 ? 0x52d090 : 0x52d074;
    uint32_t output = run.automatic(0x4);
    run.put(output, 0);
    run.call(0x4f6286, resourceMap(run, receiver, 0x28) + 0x10, {soundName, output});
    // Sound slots.
    run.put(receiver + 0x3a4, run.get(output));
    run.put(output, 0);
    run.call(0x4f6286, resourceMap(run, receiver, 0x28) + 0x10, {second ? 0x52d2dcu : 0x52d058u, output});
    run.put(receiver + 0x410, run.get(output));
    run.put(receiver + 0x40c, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {0x52d040}));
    run.put(receiver + 0x454, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {second ? 0x52d2c0u : 0x52d024u}));
    run.put(receiver + 0x458, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {second ? 0x52d2a4u : 0x52d008u}));
    run.put(receiver + 0x45c, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {second ? 0x52d288u : 0x52cfecu}));
    run.put(receiver + 0x460, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {second ? 0x52d26cu : 0x52cfd0u}));
    run.put(receiver + 0x464, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {second ? 0x52d250u : 0x52cfb4u}));
    run.put(receiver + 0x468, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {0x52cf98}));
    run.put(receiver + 0x46c, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {second ? 0x52d234u : 0x52cf7cu}));
    run.put(receiver + 0x470, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {0x52cf60}));
    run.put(receiver + 0x474, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {0x52cf44}));
    run.put(receiver + 0x478, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {0x52cf2c}));
    run.put(receiver + 0x47c, run.call(0x4061b0, resourceMap(run, receiver, 0x28), {0x52cf14}));
    // Bitset count and storage: inline through 32 bits, indirect above it.
    if (!second || run.get(0x537964) == 5) {
        uint32_t count = run.get(receiver + 0x2fc);
        if (count > 5) {
            uint32_t bits = count <= 32 ? receiver + 0x300 : run.get(receiver + 0x300);
            run.put(bits, run.get(bits) ^ 0x20);
        }
    }
    uint32_t setRect = run.get(0x546d5c);
    // Sound/action probability.
    run.put(receiver + 0x480, second || run.get(0x537964) == 6 ? 90 : 0);
    if (second) {
        run.call(setRect, 0, {receiver + 0x230, uint32_t(-88), uint32_t(-14), uint32_t(-21), 27});
        run.call(setRect, 0, {receiver + 0x240, uint32_t(-102), 7, uint32_t(-33), 46});
    } else {
        run.call(setRect, 0, {receiver + 0x230, uint32_t(-88), uint32_t(-35), uint32_t(-20), 7});
        run.call(setRect, 0, {receiver + 0x240, uint32_t(-90), 4, uint32_t(-22), 35});
    }
    copyRectangle(run, receiver, 0x230);
    if (second)
        run.call(setRect, 0, {receiver + 0x210, uint32_t(-1), uint32_t(-1), 1, 1});
    else
        run.call(0x4296f0, receiver + 0x210, {uint32_t(-1), uint32_t(-1), 1, 1});
    run.call(0x4296f0, receiver + 0x250, {uint32_t(-20), second ? uint32_t(-40) : uint32_t(-60), 20, second ? 71u : 51u});
    run.call(0x4296f0, receiver + 0x260, {uint32_t(-20), uint32_t(-15), 20, 15});
    run.call(0x40ab80, receiver + 0x128, {uint32_t(-20), uint32_t(-50), 20, 50});
    run.call(0x40abb0, receiver + 0x128, {receiver + 0x250});
    // Behavior tuning, movement and attack bounds.
    run.put(receiver + 0x28c, 500);
    run.put(receiver + 0x290, 40);
    run.put(receiver + 0x29c, 200);
    run.put(receiver + 0x2a0, 40);
    run.put(receiver + 0x2a4, 110);
    run.put(receiver + 0x2a8, 40);
    run.put(receiver + 0x2ac, 100);
    run.put(receiver + 0x2b0, 40);
    run.put(receiver + 0x2b4, 10);
    run.put(receiver + 0x2b8, uint32_t(-10));
    run.put(receiver + 0x2bc, uint32_t(-45));
    run.put(receiver + 0x2c0, uint32_t(-20));
    run.put(receiver + 0x2c4, 20);
    run.put(receiver + 0x2c8, uint32_t(-15));
    run.put(receiver + 0x2e4, 50);
    floatOperand(run, fp, CLAW_X87_F64, 0x5262b8);
    floatOperand(run, fp, CLAW_X87_MUL_F64, 0x50fab0);
    uint32_t health = convert(run, fp);
    if (health <= 99)
        health = 99;
    run.put(receiver + 0x2e4, health);
    // Actor attack and contact damage, using the original integer conversion.
    run.put(run.get(receiver + 0xc) + 0x10c, run.get(0x537964) == 5 ? 9 : 10);
    uint32_t actor = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(actor + 0x10c)});
    floatOperand(run, fp, CLAW_X87_MUL_F64, 0x5262b4);
    uint32_t damage = convert(run, fp);
    run.put(actor + 0x10c, damage);
    run.put(run.get(receiver + 0xc) + 0x104, 10);
    actor = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(actor + 0x104)});
    floatOperand(run, fp, CLAW_X87_MUL_F64, 0x5262b0);
    damage = convert(run, fp);
    run.put(actor + 0x104, damage);
    run.put(receiver + 0x484, 0);
    balancedCall(run, fp, 0x40abf0, receiver + 0x128);
    balancedCall(run, fp, 0x497970, receiver);
    run.x87_finish(function, fp);
    return receiver;
}

// 0x496860 and 0x497060. Identical destruction of the embedded base members.
uint32_t destruct(Run &run, uint32_t receiver) {
    run.put(receiver + 0x0, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver + 0x0, 0x50b014);
    return 0;
}

// 0x496840 and 0x497040. Scalar deleting destructor wrappers.
uint32_t deletingDestruct(Run &run, uint32_t receiver, uint32_t flags) {
    destruct(run, receiver);
    if (flags & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// Source dispatch retains the physical integer machine and stack. Arithmetic
// flags are needed as input to children even though the root excludes them.
uint32_t commonFlags(uint32_t result) {
    uint32_t low = result & 0xff;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    return 2u | ((low & 1) ? 0u : 4u) | (result == 0 ? 0x40u : 0u) | (result & 0x80000000u ? 0x80u : 0u);
}

void compare(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    uint32_t result = left - right;
    cpu.eflags = commonFlags(result) | (left < right ? 1u : 0u) | ((left ^ right ^ result) & 0x10) | (((left ^ right) & (left ^ result) & 0x80000000u) ? 0x800u : 0u);
}

void addFlags(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    uint32_t result = left + right;
    cpu.eflags = commonFlags(result) | (result < left ? 1u : 0u) | ((left ^ right ^ result) & 0x10) | ((~(left ^ right) & (left ^ result) & 0x80000000u) ? 0x800u : 0u);
}

void push(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 0x4;
    run.put(cpu.esp, value);
}

void sourceCall(Run &run, ClawSourceContext &cpu, uint32_t function, uint32_t receiver, uint32_t returnPC, std::initializer_list<uint32_t> arguments, uint32_t popBytes) {
    push(run, cpu, returnPC);
    cpu.eip = function;
    auto child = cpu;
    run.source_call(function, receiver, returnPC, child, arguments, 0, popBytes);
    cpu.eax = child.eax;
    cpu.ebx = child.ebx;
    cpu.ecx = child.ecx;
    cpu.edx = child.edx;
    cpu.esi = child.esi;
    cpu.edi = child.edi;
    cpu.ebp = child.ebp;
    cpu.esp = child.esp;
    cpu.eip = child.eip;
    cpu.fsHead = child.fsHead;
}

// 0x497130. Two independent table lookups and original error continuations.
uint32_t dispatch(Run &run) {
    auto &cpu = run.source();
    push(run, cpu, cpu.ebp);
    cpu.ebp = cpu.ecx;
    cpu.ecx = run.get(0x53ca78);
    push(run, cpu, cpu.esi);
    cpu.esi = run.get(cpu.esp + 0xc);
    push(run, cpu, cpu.edi);
    compare(cpu, cpu.esi, cpu.ecx);
    run.put(0x53ca90, 0);
    bool grow = s32(cpu.esi) < s32(cpu.ecx);
    if (!grow) {
        uint32_t upper = run.get(0x53ca7c);
        compare(cpu, cpu.esi, upper);
        grow = s32(cpu.esi) > s32(upper);
    }
    if (grow) {
        push(run, cpu, 0);
        push(run, cpu, cpu.esi);
        cpu.ecx = 0x53ca70;
        sourceCall(run, cpu, 0x4db6e0, cpu.ecx, 0x497166, {cpu.esi, 0}, 0x8);
        cpu.eflags = commonFlags(cpu.eax);
        if (!cpu.eax) {
            cpu.edi = run.get(0x544b4c);
            sourceCall(run, cpu, 0x4db5f0, 0, 0x497190, {}, 0);
            cpu.ecx = run.get(0x53ca74);
            push(run, cpu, 0xc);
            push(run, cpu, cpu.edi);
            push(run, cpu, 0x53ca70);
            run.put(0x544b14, cpu.eax);
            sourceCall(run, cpu, 0x4db4d0, cpu.ecx, 0x4971a8, {0x53ca70, cpu.edi, 0xc}, 0xc);
            cpu.eax = run.get(0x53ca84);
            cpu.ecx = run.get(0x53ca78);
        } else {
            cpu.ecx = run.get(0x53ca78);
            cpu.eax = cpu.esi;
            cpu.eax -= cpu.ecx;
            cpu.edx = run.get(0x53ca80);
            cpu.eax *= run.get(0x53ca88);
            addFlags(cpu, cpu.eax, cpu.edx);
            cpu.eax += cpu.edx;
        }
    } else {
        cpu.eax = cpu.esi;
        cpu.eax -= cpu.ecx;
        cpu.edx = run.get(0x53ca80);
        cpu.eax *= run.get(0x53ca88);
        addFlags(cpu, cpu.eax, cpu.edx);
        cpu.eax += cpu.edx;
    }
    uint32_t callback = run.get(cpu.eax);
    compare(cpu, callback, 0);
    if (!callback) {
        push(run, cpu, cpu.esi);
        cpu.ecx = cpu.ebp;
        sourceCall(run, cpu, 0x44c840, cpu.ecx, 0x49723a, {cpu.esi}, 0x4);
    } else {
        compare(cpu, cpu.esi, cpu.ecx);
        run.put(0x53ca90, 0);
        grow = s32(cpu.esi) < s32(cpu.ecx);
        if (!grow) {
            uint32_t upper = run.get(0x53ca7c);
            compare(cpu, cpu.esi, upper);
            grow = s32(cpu.esi) > s32(upper);
        }
        bool failed = false;
        if (grow) {
            push(run, cpu, 0);
            push(run, cpu, cpu.esi);
            cpu.ecx = 0x53ca70;
            sourceCall(run, cpu, 0x4db6e0, cpu.ecx, 0x4971db, {cpu.esi, 0}, 0x8);
            cpu.eflags = commonFlags(cpu.eax);
            failed = !cpu.eax;
            if (!failed)
                cpu.ecx = run.get(0x53ca78);
        }
        if (failed) {
            cpu.esi = run.get(0x544b4c);
            sourceCall(run, cpu, 0x4db5f0, 0, 0x49720a, {}, 0);
            cpu.ecx = run.get(0x53ca74);
            push(run, cpu, 0xc);
            push(run, cpu, cpu.esi);
            push(run, cpu, 0x53ca70);
            run.put(0x544b14, cpu.eax);
            sourceCall(run, cpu, 0x4db4d0, cpu.ecx, 0x497222, {0x53ca70, cpu.esi, 0xc}, 0xc);
            cpu.esi = run.get(0x53ca84);
            cpu.ecx = cpu.ebp;
            sourceCall(run, cpu, run.get(cpu.esi), cpu.ecx, 0x49722c, {}, 0);
        } else {
            cpu.esi -= cpu.ecx;
            cpu.eax = run.get(0x53ca80);
            cpu.esi *= run.get(0x53ca88);
            addFlags(cpu, cpu.esi, cpu.eax);
            cpu.esi += cpu.eax;
            cpu.ecx = cpu.ebp;
            sourceCall(run, cpu, run.get(cpu.esi), cpu.ecx, 0x4971f9, {}, 0);
        }
    }
    cpu.edi = run.get(cpu.esp);
    cpu.esp += 0x4;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 0x4;
    cpu.ebp = run.get(cpu.esp);
    cpu.esp += 0x4;
    return cpu.eax;
}

// 0x497510. Input-facing action test, delayed probabilistic sound, strike map.
uint32_t updateStrike(Run &run, uint32_t receiver, uint32_t argument) {
    run.call(0x44d000, receiver, {argument});
    uint32_t input = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (run.get(input + 0x4) != 0) {
        uint32_t facing = run.get(receiver + 0x18c);
        if ((facing == 3 && run.get(input + 0x0) != 0) || (facing == 2 && run.get(input + 0x0) == 0)) {
            uint32_t action = run.get(input + 0x3c);
            if (action == 1 || action == 2 || action == 7 || action == 8) {
                uint32_t state = run.get(receiver + 0x184);
                if ((state == 3 || state == 4) && run.get(0x537210) - run.get(receiver + 0x490) >= run.get(receiver + 0x494)) {
                    int32_t probability = run.gets(receiver + 0x480);
                    if (s32(run.call(0x4a3050, 0)) % 100 < probability) {
                        uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 2);
                        uint32_t sound = run.get(receiver + 0x460 + index * 0x4);
                        run.call(0x48ce40, 0, {run.get(receiver + 0xc), sound, 0});
                        if (run.gets(receiver + 0x20) >= 2)
                            run.put(receiver + 0x14, 0x44e620);
                        uint32_t reduced = run.get(receiver + 0x480) - 30;
                        run.put(receiver + 0x480, reduced);
                        if (s32(reduced) < 0)
                            run.put(receiver + 0x480, 0);
                        run.put(receiver + 0x494, 500);
                        run.put(receiver + 0x490, run.get(0x537210));
                    }
                }
            }
        }
    }
    bool first = run.get(run.get(0x537e88) + 0xcc) == 5;
    uint32_t output = run.automatic(0x4);
    run.put(output, 0);
    copyRectangle(run, receiver, first ? 0x240 : 0x230);
    run.call(0x4f6286, resourceMap(run, receiver, 0x2c) + 0x10, {first ? 0x52d1acu : 0x52d47cu, output});
    uint32_t value = run.get(output);
    if (!value) {
        uint32_t fallback = run.automatic(-0x4);
        run.put(fallback, 0);
        run.call(0x4f6286, resourceMap(run, receiver, 0x2c) + 0x10, {0x5234b4, fallback});
        value = run.get(fallback);
    }
    run.put(receiver + 0x310, value);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x496110:
        return construct(run, receiver, arguments[0], false);
    case 0x496990:
        return construct(run, receiver, arguments[0], true);
    case 0x496840:
    case 0x497040:
        return deletingDestruct(run, receiver, arguments[0]);
    case 0x496860:
    case 0x497060:
        return destruct(run, receiver);
    case 0x497130:
        return dispatch(run);
    case 0x497510:
        return updateStrike(run, receiver, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_SOURCE_MODULE_ENTRY(claw_level_five_town_guard_core_entry, owned, contract, body)
