// Original CRT cleanup callback registry
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
    case 0x4a3610:
        return 0;
    case 0x4a3560:
        return 1;
    case 0x4a35f0:
        return 1;
    case 0x4a5860:
        return 0;
    case 0x4a5870:
        return 0;
    default:
        return -1;
    }
}

// Arithmetic status and physical stack operations retain complete source state.
uint32_t status(uint32_t value) {
    uint32_t byte = value & 0xff;
    byte ^= byte >> 4;
    byte ^= byte >> 2;
    byte ^= byte >> 1;
    return 2u | ((byte & 1u) ? 0u : 4u) | (value == 0 ? 0x40u : 0u) | (value & 0x80000000u ? 0x80u : 0u);
}
uint32_t add(ClawSourceContext &cpu, uint32_t a, uint32_t b) {
    uint32_t value = a + b;
    cpu.eflags = status(value) | (value < a ? 1u : 0u) | ((a ^ b ^ value) & 0x10u) | ((~(a ^ b) & (a ^ value) & 0x80000000u) ? 0x800u : 0u);
    return value;
}
uint32_t subtract(ClawSourceContext &cpu, uint32_t a, uint32_t b) {
    uint32_t value = a - b;
    cpu.eflags = status(value) | (a < b ? 1u : 0u) | ((a ^ b ^ value) & 0x10u) | (((a ^ b) & (a ^ value) & 0x80000000u) ? 0x800u : 0u);
    return value;
}
void push(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 0x04;
    run.put(cpu.esp, value);
}
uint32_t pop(Run &run, ClawSourceContext &cpu) {
    uint32_t value = run.get(cpu.esp);
    cpu.esp += 0x04;
    return value;
}
void execute(Run &run, uint32_t function, ClawSourceContext &cpu);
void call(Run &run, ClawSourceContext &cpu, uint32_t function, uint32_t returnPC, std::initializer_list<uint32_t> arguments = {}) {
    push(run, cpu, returnPC);
    cpu.eip = function;
    if (owned(function) >= 0) {
        execute(run, function, cpu);
        cpu.eip = pop(run, cpu);
    } else {
        auto child = cpu;
        run.source_call(function, 0, returnPC, child, arguments);
        cpu = child;
    }
}

// 0x4a3610, 0x4a3560, 0x4a35f0, 0x4a5860 and 0x4a5870.
void execute(Run &run, uint32_t function, ClawSourceContext &cpu) {
    if (function == 0x4a5860 || function == 0x4a5870) {
        push(run, cpu, 0x0d);
        call(run, cpu, function == 0x4a5860 ? 0x4a7bc0 : 0x4a7c40, function == 0x4a5860 ? 0x4a5867 : 0x4a5877, {0x0d});
        cpu.esp = add(cpu, cpu.esp, 0x04);
        return;
    }
    if (function == 0x4a3610) {
        push(run, cpu, 0x80);
        call(run, cpu, 0x4a48e0, 0x4a361a, {0x80});
        cpu.esp = add(cpu, cpu.esp, 0x04);
        run.put(0x545fd4, cpu.eax);
        cpu.eflags = status(cpu.eax);
        if (!cpu.eax) {
            push(run, cpu, 0x18);
            call(run, cpu, 0x4a4860, 0x4a362d, {0x18});
            run.fail(CLAW_FAULT_ABI, 0x4a362d);
        }
        run.put(cpu.eax, 0);
        cpu.eax = run.get(0x545fd4);
        run.put(0x545fd0, cpu.eax);
        return;
    }
    if (function == 0x4a35f0) {
        cpu.eax = run.get(cpu.esp + 0x04);
        push(run, cpu, cpu.eax);
        call(run, cpu, 0x4a3560, 0x4a35fa, {cpu.eax});
        cpu.esp = add(cpu, cpu.esp, 0x04);
        cpu.eax = subtract(cpu, 0, cpu.eax);
        uint32_t carry = cpu.eflags & 1u;
        uint32_t prior = cpu.eax;
        cpu.eax = 0u - carry;
        cpu.eflags = status(cpu.eax) | carry | ((prior ^ prior ^ cpu.eax) & 0x10u);
        cpu.eax = subtract(cpu, 0, cpu.eax);
        carry = cpu.eflags & 1u;
        cpu.eax = subtract(cpu, cpu.eax, 1);
        cpu.eflags = (cpu.eflags & ~1u) | carry;
        return;
    }
    if (function != 0x4a3560) {
        run.fail(CLAW_FAULT_ABI, function);
    }
    push(run, cpu, cpu.esi);
    call(run, cpu, 0x4a5860, 0x4a3566);
    cpu.eax = run.get(0x545fd4);
    push(run, cpu, cpu.eax);
    call(run, cpu, 0x4a6560, 0x4a3571, {cpu.eax});
    cpu.ecx = run.get(0x545fd0);
    cpu.edx = run.get(0x545fd4);
    cpu.esi = cpu.ecx;
    cpu.esp = add(cpu, cpu.esp, 0x04);
    cpu.esi = subtract(cpu, cpu.esi, cpu.edx);
    cpu.esi = add(cpu, cpu.esi, 0x04);
    subtract(cpu, cpu.eax, cpu.esi);
    if (cpu.eax < cpu.esi) {
        push(run, cpu, cpu.edx);
        call(run, cpu, 0x4a6560, 0x4a3591, {cpu.edx});
        cpu.ecx = run.get(0x545fd4);
        cpu.esp = add(cpu, cpu.esp, 0x04);
        cpu.eax = add(cpu, cpu.eax, 0x10);
        push(run, cpu, cpu.eax);
        push(run, cpu, cpu.ecx);
        call(run, cpu, 0x4a9070, 0x4a35a4, {cpu.ecx, cpu.eax});
        cpu.esp = add(cpu, cpu.esp, 0x08);
        cpu.eflags = status(cpu.eax);
        if (!cpu.eax) {
            call(run, cpu, 0x4a5870, 0x4a35b0);
            cpu.eax = 0;
            cpu.eflags = status(0);
            cpu.esi = pop(run, cpu);
            return;
        }
        cpu.edx = run.get(0x545fd0);
        cpu.esi = run.get(0x545fd4);
        cpu.edx = subtract(cpu, cpu.edx, cpu.esi);
        run.put(0x545fd4, cpu.eax);
        uint32_t beforeShift = cpu.edx;
        cpu.edx = uint32_t(s32(cpu.edx) >> 2);
        cpu.eflags = status(cpu.edx) | ((beforeShift >> 1) & 1u);
        cpu.ecx = cpu.eax + cpu.edx * 0x04;
        run.put(0x545fd0, cpu.ecx);
    }
    cpu.esi = run.get(cpu.esp + 0x08);
    run.put(cpu.ecx, cpu.esi);
    cpu.eax = run.get(0x545fd0);
    cpu.eax = add(cpu, cpu.eax, 0x04);
    run.put(0x545fd0, cpu.eax);
    call(run, cpu, 0x4a5870, 0x4a35eb);
    cpu.eax = cpu.esi;
    cpu.esi = pop(run, cpu);
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    execute(run, function, cpu);
    return cpu.eax;
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4a3610: return {2047u, 2047u, 1138u, 0u};
    case 0x4a3560: return {2047u, 2047u, 1138u, 0u};
    case 0x4a35f0: return {2047u, 2047u, 1138u, 0u};
    case 0x4a5860: return {2047u, 2047u, 1138u, 0u};
    case 0x4a5870: return {2047u, 2047u, 1138u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_crt_exit_registry_entry, owned, source_contract, body)
