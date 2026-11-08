#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x443220:
    case 0x4872d0:
    case 0x487830:
        return 0;
    case 0x443170:
    case 0x443200:
    case 0x486f50:
    case 0x4872b0:
    case 0x4873a0:
    case 0x4877a0:
    case 0x4877d0:
    case 0x487800:
        return 1;
    default:
        return -1;
    }
}

ClawSourceContract contract(uint32_t function) {
    if (function == 0x4873a0)
        return {0x7ff, 0x5f3, 0x472, 4};
    return {};
}

// Expand an m32 operand without rounding or quieting its NaN payload.
uint64_t widen(uint32_t bits) {
    uint64_t sign = uint64_t(bits & 0x80000000u) << 32;
    uint32_t exponent = (bits >> 23) & 0xff;
    uint32_t fraction = bits & 0x7fffff;
    if (exponent == 0xff)
        return sign | (uint64_t(0x7ff) << 52) | (uint64_t(fraction) << 29);
    if (exponent)
        return sign | (uint64_t(exponent + 896) << 52) | (uint64_t(fraction) << 29);
    if (!fraction)
        return sign;
    uint32_t biased = 897;
    while (!(fraction & 0x800000)) {
        fraction <<= 1;
        --biased;
    }
    return sign | (uint64_t(biased) << 52) | (uint64_t(fraction & 0x7fffff) << 29);
}

void floatOperand(Run &run, ClawX87State &state, uint32_t operation, uint32_t address) {
    uint64_t bits = widen(run.get(address));
    run.x87_step(operation, state, {uint32_t(bits), uint32_t(bits >> 32)});
}

uint32_t convert(Run &run, ClawX87State &state) {
    state.popCount = 1;
    state.pushCount = 0;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, state);
}

// 0x443170. Base initialization and actor classification.
uint32_t constructBase(Run &run, uint32_t receiver, uint32_t argument, ClawX87State &state) {
    state.popCount = 0;
    state.pushCount = 0;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    run.call_x87_exact(0x4332f0, receiver, state, {argument});
    run.put(receiver, 0x50dd34);
    uint32_t low = run.get(0x513e10);
    uint32_t high = run.get(0x513e14);
    run.put(receiver + 0x88, low);
    run.put(receiver + 0x8c, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(receiver + 0xa0, low);
    run.put(receiver + 0xa4, high);
    run.put(run.get(receiver + 0x0c) + 0xcc, 7);
    uint32_t object = run.get(receiver + 0x12c);
    run.put(object + 0x08, run.get(object + 0x08) | 0x40);
    run.put(run.get(receiver + 0x12c) + 0xd0, 4);
    run.put(run.get(receiver + 0x12c) + 0xd4, 0x3000032);
    return receiver;
}

// 0x443220 and 0x4872d0. Identical member destruction sequences.
void destruct(Run &run, uint32_t receiver) {
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
}

// 0x487830. Direction, reflected rectangles, idle state and animation.
uint32_t idle(Run &run, uint32_t receiver, ClawX87State &state) {
    run.x87_step(CLAW_X87_F64, state, {run.get(receiver + 0x68), run.get(receiver + 0x6c)});
    run.x87_step(CLAW_X87_COMP_F64, state, {run.get(receiver + 0x98), run.get(receiver + 0x9c)});
    bool negative = (state.status & 0x4000) != 0;
    if (negative) {
        run.x87_step(CLAW_X87_F64, state, {run.get(0x50f550), run.get(0x50f554)});
        run.x87_step(CLAW_X87_CHS, state);
        uint64_t bits = run.x87_step(CLAW_X87_STP_F64, state);
        run.put(receiver + 0x50, uint32_t(bits));
        run.put(receiver + 0x54, uint32_t(bits >> 32));
    } else {
        uint32_t low = run.get(0x50f550);
        uint32_t high = run.get(0x50f554);
        run.put(receiver + 0x50, low);
        run.put(receiver + 0x54, high);
    }
    uint32_t object = run.get(receiver + 0x12c);
    bool flipped = (run.get8(object + 0x40) & 2) != 0;
    if (negative == flipped) {
        uint32_t left = run.get(receiver + 0x138);
        uint32_t right = run.get(receiver + 0x140);
        run.put(receiver + 0x138, 0u - right);
        run.put(receiver + 0x140, 0u - left);
        uint32_t flags = run.get(object + 0x40);
        run.put(object + 0x40, negative ? flags & 0xfffffffdu : flags | 2);
        object = run.get(receiver + 0x12c);
        left = run.get(object + 0x118);
        if (left != 0x80000000) {
            right = run.get(object + 0x120);
            run.put(object + 0x118, 0u - right);
            run.put(object + 0x120, 0u - left);
        }
        if (negative) {
            run.call(0x406150, object);
        } else {
            left = run.get(object + 0x128);
            if (left != 0x80000000) {
                right = run.get(object + 0x130);
                run.put(object + 0x128, 0u - right);
                run.put(object + 0x130, 0u - left);
            }
        }
        run.call(0x406180, object);
    }
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t value = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(receiver + 0x10) + 0x1c, value);
    object = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x418);
    run.put(receiver + 0x134, run.get(object + 0x190));
    run.call(0x4c8220, object + 0x188, {animation});
    return 0;
}

// 0x486f50. Seagull resource lookup and scaled combat fields.
uint32_t construct(Run &run, uint32_t receiver, uint32_t argument, ClawX87State &state) {
    uint32_t frame = run.frame;
    run.frame = frame - 0x24;
    constructBase(run, receiver, argument, state);
    run.frame = frame;
    run.put(receiver, 0x50f58c);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x52bf70});
    const uint32_t names[] = {0x52bf5c, 0x52bf48, 0x52bf34, 0x52bf20, 0x52bf00, 0x52bee4, 0x52becc, 0x52beb4, 0x52be9c, 0x52be88, 0x52be70};
    for (uint32_t index = 0; index < 11; ++index) {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {names[index]});
        if (!value)
            value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x400 + index * 4, value);
    }
    uint32_t output = run.automatic(4);
    run.put(output, 0);
    uint32_t map = run.get(run.get(run.get(receiver + 0x12c) + 0x0c) + 0x28);
    run.call(0x4f6286, map + 0x10, {0x52be54, output});
    run.put(receiver + 0x42c, run.get(output));
    map = run.get(run.get(run.get(receiver + 0x12c) + 0x0c) + 0x28);
    uint32_t value = run.call(0x4061b0, map, {0x52be38});
    uint32_t setRect = run.get(0x546d5c);
    run.put(receiver + 0x430, value);
    run.call(setRect, 0, {receiver + 0x220, 0xffffffe6, 0xfffffffb, 0xfffffffb, 0x16});
    run.call(setRect, 0, {receiver + 0x210, 0x80000000, 0, 0, 0});
    run.call(0x406290, run.get(receiver + 0x12c));
    run.call(0x4208b0, run.get(receiver + 0x12c), {0xffffffe2, 0xffffffe2, 0x1e, 0x1e});
    run.put(receiver + 0x28c, 0x1f4);
    run.put(receiver + 0x290, 0x28);
    run.put(receiver + 0x2a0, 0x28);
    run.put(receiver + 0x2a8, 0x28);
    run.put(receiver + 0x2b0, 0x28);
    uint32_t object = run.get(receiver + 0x0c);
    run.put(receiver + 0x29c, 0xc8);
    run.put(receiver + 0x2a4, 0x96);
    run.put(receiver + 0x2ac, 0x64);
    if (!run.get(object + 0x64)) {
        if (run.get(object + 0x64) != 0x2134) {
            run.put(object + 0x64, 0x2134);
            run.put(object + 0x08, run.get(object + 0x08) | 0x20000);
        }
    }
    run.put(receiver + 0x2e4, 0x32);
    floatOperand(run, state, CLAW_X87_F64, 0x5262b8);
    floatOperand(run, state, CLAW_X87_MUL_F64, 0x50f558);
    value = convert(run, state);
    if (value <= 99)
        value = 99;
    object = run.get(receiver + 0x0c);
    run.put(receiver + 0x2e4, value);
    run.put(object + 0x10c, 1);
    object = run.get(receiver + 0x0c);
    run.x87_step(CLAW_X87_I32, state, {run.get(object + 0x10c)});
    floatOperand(run, state, CLAW_X87_MUL_F64, 0x5262b4);
    value = convert(run, state);
    run.put(object + 0x10c, value);
    run.put(run.get(receiver + 0x0c) + 0x104, 10);
    object = run.get(receiver + 0x0c);
    run.x87_step(CLAW_X87_I32, state, {run.get(object + 0x104)});
    floatOperand(run, state, CLAW_X87_MUL_F64, 0x5262b0);
    value = convert(run, state);
    run.put(object + 0x104, value);
    run.put(receiver + 0x434, run.get(run.get(receiver + 0x0c) + 0x50));
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0);
    run.frame = frame - 0x20;
    idle(run, receiver, state);
    run.frame = frame;
    return receiver;
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

uint32_t sourceCall(Run &run, ClawSourceContext &cpu, uint32_t target, uint32_t pc, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}, uint32_t popBytes = 0) {
    push(run, cpu, pc);
    auto child = cpu;
    child.inputMask = target == 0x4db5f0 ? 0x5c1 : 0x7ff;
    child.outputMask = target == 0x4db5f0 ? 0x5c1 : 0x5f3;
    child.preserveMask = target == 0x4db5f0 ? 0x440 : 0x472;
    child.eip = target;
    run.source_call(target, receiver, pc, child, arguments, 0, popBytes);
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
    return cpu.eax;
}

uint32_t resultFlags(uint32_t value) {
    uint32_t byte = value & 0xff;
    byte ^= byte >> 4;
    byte ^= byte >> 2;
    byte ^= byte >> 1;
    return 2 | (value & 0x80000000 ? 0x80 : 0) | (value == 0 ? 0x40 : 0) | (!(byte & 1) ? 4 : 0);
}

uint32_t subtract(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    uint32_t value = left - right;
    cpu.eflags = resultFlags(value) | (left < right ? 1 : 0) | ((left ^ right ^ value) & 0x10) | (((left ^ right) & (left ^ value) & 0x80000000) ? 0x800 : 0);
    return value;
}

uint32_t add(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    uint32_t value = left + right;
    cpu.eflags = resultFlags(value) | (value < left ? 1 : 0) | ((left ^ right ^ value) & 0x10) | ((~(left ^ right) & (left ^ value) & 0x80000000) ? 0x800 : 0);
    return value;
}

bool outside(Run &run, ClawSourceContext &cpu) {
    subtract(cpu, cpu.esi, cpu.ecx);
    if (s32(cpu.esi) < s32(cpu.ecx))
        return true;
    uint32_t maximum = run.get(0x53c27c);
    subtract(cpu, cpu.esi, maximum);
    return s32(cpu.esi) > s32(maximum);
}

// 0x4873a0. Physical source frames retain real return-address observations.
uint32_t dispatch(Run &run, uint32_t receiver, uint32_t argument) {
    auto &cpu = run.source();
    push(run, cpu, cpu.ebp);
    cpu.ebp = receiver;
    cpu.ecx = run.get(0x53c278);
    push(run, cpu, cpu.esi);
    cpu.esi = argument;
    push(run, cpu, cpu.edi);
    run.put(0x53c290, 0);
    bool out = outside(run, cpu);
    if (out) {
        push(run, cpu, 0);
        push(run, cpu, cpu.esi);
        cpu.ecx = 0x53c270;
        sourceCall(run, cpu, 0x4db6e0, 0x4873d6, cpu.ecx, {cpu.esi, 0}, 8);
        cpu.eflags = resultFlags(cpu.eax);
        if (!cpu.eax) {
            cpu.edi = run.get(0x544b4c);
            sourceCall(run, cpu, 0x4db5f0, 0x487400, 0);
            cpu.ecx = run.get(0x53c274);
            push(run, cpu, 0x0c);
            push(run, cpu, cpu.edi);
            push(run, cpu, 0x53c270);
            run.put(0x544b14, cpu.eax);
            sourceCall(run, cpu, 0x4db4d0, 0x487418, cpu.ecx, {0x53c270, cpu.edi, 0x0c}, 12);
            cpu.eax = run.get(0x53c284);
            cpu.ecx = run.get(0x53c278);
        } else {
            cpu.ecx = run.get(0x53c278);
            cpu.eax = subtract(cpu, cpu.esi, cpu.ecx);
            cpu.edx = run.get(0x53c280);
            cpu.eax *= run.get(0x53c288);
            cpu.eax = add(cpu, cpu.eax, cpu.edx);
        }
    } else {
        cpu.eax = subtract(cpu, cpu.esi, cpu.ecx);
        cpu.edx = run.get(0x53c280);
        cpu.eax *= run.get(0x53c288);
        cpu.eax = add(cpu, cpu.eax, cpu.edx);
    }
    uint32_t callback = run.get(cpu.eax);
    subtract(cpu, callback, 0);
    if (!callback) {
        push(run, cpu, cpu.esi);
        cpu.ecx = cpu.ebp;
        sourceCall(run, cpu, 0x43d490, 0x4874aa, cpu.ecx, {cpu.esi}, 4);
    } else {
        run.put(0x53c290, 0);
        out = outside(run, cpu);
        bool failed = false;
        if (out) {
            push(run, cpu, 0);
            push(run, cpu, cpu.esi);
            cpu.ecx = 0x53c270;
            sourceCall(run, cpu, 0x4db6e0, 0x48744b, cpu.ecx, {cpu.esi, 0}, 8);
            cpu.eflags = resultFlags(cpu.eax);
            failed = cpu.eax == 0;
            if (!failed)
                cpu.ecx = run.get(0x53c278);
        }
        if (failed) {
            cpu.esi = run.get(0x544b4c);
            sourceCall(run, cpu, 0x4db5f0, 0x48747a, 0);
            cpu.ecx = run.get(0x53c274);
            push(run, cpu, 0x0c);
            push(run, cpu, cpu.esi);
            push(run, cpu, 0x53c270);
            run.put(0x544b14, cpu.eax);
            sourceCall(run, cpu, 0x4db4d0, 0x487492, cpu.ecx, {0x53c270, cpu.esi, 0x0c}, 12);
            cpu.esi = run.get(0x53c284);
        } else {
            cpu.esi = subtract(cpu, cpu.esi, cpu.ecx);
            cpu.eax = run.get(0x53c280);
            cpu.esi *= run.get(0x53c288);
            cpu.esi = add(cpu, cpu.esi, cpu.eax);
        }
        cpu.ecx = cpu.ebp;
        sourceCall(run, cpu, run.get(cpu.esi), failed ? 0x48749c : 0x487469, cpu.ecx);
    }
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
    cpu.ebp = pop(run, cpu);
    return cpu.eax;
}

// 0x4877a0, 0x4877d0, 0x487800. Collision response variants.
uint32_t hit(Run &run, uint32_t receiver, uint32_t argument, uint32_t function) {
    run.vcall(receiver, 0x28, {argument});
    run.call(0x440e20, receiver, {argument});
    if (function == 0x4877d0)
        run.put(argument + 0x08, run.get(argument + 0x08) | 0x10000);
    if (function == 0x487800)
        run.call(0x43e9c0, receiver, {2000});
    run.call(0x488390, receiver);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x443170: {
        auto state = run.x87_entry(function);
        uint32_t result = constructBase(run, receiver, arguments[0], state);
        run.x87_finish(function, state);
        return result;
    }
    case 0x443200:
    case 0x4872b0:
        destruct(run, receiver);
        if (arguments[0] & 1)
            run.call(0x4f6428, 0, {receiver});
        return receiver;
    case 0x443220:
    case 0x4872d0:
        destruct(run, receiver);
        return 0;
    case 0x486f50: {
        auto state = run.x87_entry(function);
        uint32_t result = construct(run, receiver, arguments[0], state);
        run.x87_finish(function, state);
        return result;
    }
    case 0x4873a0:
        return dispatch(run, receiver, arguments[0]);
    case 0x4877a0:
    case 0x4877d0:
    case 0x487800:
        return hit(run, receiver, arguments[0], function);
    case 0x487830: {
        auto state = run.x87_entry(function);
        uint32_t result = idle(run, receiver, state);
        run.x87_finish(function, state);
        return result;
    }
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_SOURCE_MODULE_ENTRY(claw_level_five_seagull_core_entry, owned, contract, body)
