// Original application factory and constructor
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x423450:
        return 0;
    case 0x4254a0:
        return 0;
    default:
        return -1;
    }
}

uint32_t flags(uint32_t old, uint32_t a, uint32_t b, uint32_t result, bool add) {
    uint32_t low = result & 0xff;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    uint32_t value = 2u | (result & 0x80000000u ? 0x80u : 0u) | (result == 0 ? 0x40u : 0u) | (!(low & 1) ? 4u : 0u);
    if (add) {
        value |= result < a ? 1u : 0u;
        value |= (a ^ b ^ result) & 0x10u;
        value |= ((~(a ^ b) & (a ^ result)) >> 20) & 0x800u;
    } else {
        value |= old & 0x10u;
    }
    return value;
}

void push(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}

void addStack(ClawSourceContext &cpu, uint32_t count) {
    uint32_t previous = cpu.esp;
    cpu.esp += count;
    cpu.eflags = flags(cpu.eflags, previous, count, cpu.esp, true);
}

void child(Run &run, ClawSourceContext &cpu, uint32_t function, uint32_t receiver, uint32_t returnPC, uint32_t preserve, bool allocation = false) {
    push(run, cpu, returnPC);
    ClawSourceContext next = cpu;
    next.eip = function;
    next.preserveMask = preserve;
    if (allocation) {
        run.source_call(function, receiver, returnPC, next, {0x134});
    } else {
        run.source_call(function, receiver, returnPC, next);
    }
    std::memcpy(&cpu.eax, &next.eax, 11 * sizeof(uint32_t));
}

// 0x4254a0.
uint32_t construct(Run &run, ClawSourceContext &cpu) {
    push(run, cpu, 0xffffffffu);
    push(run, cpu, 0x504df0);
    cpu.eax = cpu.fsHead;
    push(run, cpu, cpu.eax);
    cpu.fsHead = cpu.esp;
    push(run, cpu, cpu.ecx);
    push(run, cpu, cpu.ebx);
    push(run, cpu, cpu.esi);
    cpu.esi = cpu.ecx;
    push(run, cpu, cpu.edi);
    run.put(cpu.esp + 0xc, cpu.esi);
    child(run, cpu, 0x4b8240, cpu.ecx, 0x4254c4, 0);
    cpu.edi = 0;
    cpu.eflags = flags(cpu.eflags, 0, 0, 0, false);
    cpu.ecx = cpu.esi + 0xc0;
    run.put(cpu.esp + 0x18, cpu.edi);
    child(run, cpu, 0x4f6439, cpu.ecx, 0x4254d5, 1138);
    cpu.ebx = 1;
    cpu.ecx = cpu.esi + 0xdc;
    run.put8(cpu.esp + 0x18, uint8_t(cpu.ebx));
    child(run, cpu, 0x4f54ea, cpu.ecx, 0x4254e9, 1138);
    cpu.ecx = cpu.esi + 0xf8;
    run.put8(cpu.esp + 0x18, 2);
    child(run, cpu, 0x4f6439, cpu.ecx, 0x4254f9, 1138);
    cpu.ecx = cpu.esi + 0xfc;
    run.put8(cpu.esp + 0x18, 3);
    child(run, cpu, 0x4f6439, cpu.ecx, 0x425509, 1138);
    cpu.ecx = cpu.esi + 0x100;
    run.put8(cpu.esp + 0x18, 4);
    child(run, cpu, 0x4f6439, cpu.ecx, 0x425519, 1138);
    run.put(cpu.esi + 0x0, 0x50bee4);
    run.put(cpu.esi + 0x2c, cpu.edi);
    run.put(cpu.esi + 0x30, cpu.edi);
    run.put(cpu.esi + 0x34, cpu.edi);
    run.put(cpu.esi + 0x38, cpu.edi);
    run.put(cpu.esi + 0x3c, cpu.edi);
    run.put(cpu.esi + 0x40, cpu.edi);
    run.put(cpu.esi + 0x44, cpu.edi);
    run.put(cpu.esi + 0x48, cpu.edi);
    run.put(cpu.esi + 0x4c, cpu.edi);
    run.put(cpu.esi + 0x50, cpu.edi);
    run.put(cpu.esi + 0x54, cpu.edi);
    run.put(cpu.esi + 0x60, cpu.edi);
    run.put(cpu.esi + 0x58, cpu.edi);
    run.put(cpu.esi + 0x64, cpu.edi);
    run.put(cpu.esi + 0x8c, cpu.edi);
    run.put(cpu.esi + 0xb8, cpu.edi);
    run.put(cpu.esi + 0x5c, cpu.edi);
    run.put(cpu.esi + 0x90, cpu.ebx);
    run.put(cpu.esi + 0x9c, cpu.edi);
    run.put(cpu.esi + 0x94, cpu.edi);
    run.put(cpu.esi + 0x98, cpu.edi);
    run.put(cpu.esi + 0xa0, cpu.edi);
    run.put(cpu.esi + 0xa4, cpu.edi);
    run.put(cpu.esi + 0xa8, cpu.edi);
    run.put(cpu.esi + 0xac, cpu.edi);
    run.put(cpu.esi + 0xb0, cpu.edi);
    run.put(cpu.esi + 0xb4, cpu.edi);
    run.put(cpu.esi + 0xbc, cpu.edi);
    run.put(cpu.esi + 0x68, 2);
    run.put(cpu.esi + 0x6c, cpu.edi);
    run.put(cpu.esi + 0x70, cpu.edi);
    run.put(cpu.esi + 0x74, cpu.edi);
    run.put(cpu.esi + 0xc4, cpu.edi);
    run.put(cpu.esi + 0xc8, 0x1e);
    run.put(cpu.esi + 0x7c, cpu.edi);
    run.put(cpu.esi + 0x80, cpu.edi);
    run.put(cpu.esi + 0x78, 8);
    run.put(cpu.esi + 0xf4, cpu.edi);
    run.put(cpu.esi + 0xf0, cpu.edi);
    run.put(cpu.esi + 0x108, cpu.ebx);
    run.put(cpu.esi + 0x104, cpu.edi);
    run.put(cpu.esi + 0x10c, cpu.edi);
    run.put(cpu.esi + 0x110, cpu.edi);
    run.put(cpu.esi + 0x114, cpu.edi);
    run.put(cpu.esi + 0x14, cpu.ebx);
    run.put(cpu.esi + 0x10, cpu.ebx);
    run.put(cpu.esi + 0x118, cpu.ebx);
    run.put(cpu.esi + 0x11c, cpu.ebx);
    run.put(cpu.esi + 0x120, cpu.edi);
    run.put(cpu.esi + 0x124, cpu.ebx);
    run.put(cpu.esi + 0x128, cpu.ebx);
    run.put(cpu.esi + 0x130, cpu.edi);
    cpu.ecx = run.get(cpu.esp + 0x10);
    cpu.eax = cpu.esi;
    cpu.edi = run.get(cpu.esp);
    cpu.esp += 4;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 4;
    cpu.fsHead = cpu.ecx;
    cpu.ebx = run.get(cpu.esp);
    cpu.esp += 4;
    addStack(cpu, 0x10);
    return cpu.eax;
}

uint32_t function_4254a0(Run &run, uint32_t, const uint32_t *) {
    return construct(run, run.source());
}

// 0x423450.
uint32_t function_423450(Run &run, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    push(run, cpu, 0xffffffffu);
    push(run, cpu, 0x504b4b);
    cpu.eax = cpu.fsHead;
    push(run, cpu, cpu.eax);
    cpu.fsHead = cpu.esp;
    push(run, cpu, cpu.ecx);
    push(run, cpu, 0x134);
    child(run, cpu, 0x4f63ec, 0, 0x423470, 0, true);
    addStack(cpu, 4);
    run.put(cpu.esp + 0x0, cpu.eax);
    cpu.eflags = flags(cpu.eflags, cpu.eax, cpu.eax, cpu.eax, false);
    run.put(cpu.esp + 0xc, 0);
    if (cpu.eax) {
        cpu.ecx = cpu.eax;
        push(run, cpu, 0x42348a);
        construct(run, cpu);
        cpu.eip = run.get(cpu.esp);
        cpu.esp += 4;
        cpu.ecx = run.get(cpu.esp + 0x4);
    } else {
        cpu.ecx = run.get(cpu.esp + 0x4);
        cpu.eax = 0;
        cpu.eflags = flags(cpu.eflags, 0, 0, 0, false);
    }
    cpu.fsHead = cpu.ecx;
    addStack(cpu, 0x10);
    return cpu.eax;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x423450:
        return function_423450(run, receiver, arguments);
    case 0x4254a0:
        return function_4254a0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x423450: return {2047u, 2047u, 0u, 0u};
    case 0x4254a0: return {2047u, 2047u, 0u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_application_construction_entry, owned, source_contract, body)
