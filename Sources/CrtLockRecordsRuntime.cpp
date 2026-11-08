#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x4a7b90: return 0;
    case 0x4a7bc0: return 1;
    case 0x4a7c40: return 1;
    default: return -1;
    }
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

uint32_t arithmeticFlags(uint32_t value) {
    uint32_t low = value & 0xff;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    return 2u | ((low & 1u) ? 0u : 4u) | (value == 0 ? 0x40u : 0u) | (value & 0x80000000u ? 0x80u : 0u);
}

void test(ClawSourceContext &cpu, uint32_t value) {
    cpu.eflags = arithmeticFlags(value);
}

void cleanup(ClawSourceContext &cpu) {
    uint32_t prior = cpu.esp;
    cpu.esp += 0x04;
    cpu.eflags = arithmeticFlags(cpu.esp) | (cpu.esp < prior ? 1u : 0u) | (((prior ^ 4u ^ cpu.esp) & 0x10u) ? 0x10u : 0u) | ((~(prior ^ 4u) & (prior ^ cpu.esp) & 0x80000000u) ? 0x800u : 0u);
}

void execute(Run &run, ClawSourceContext &cpu, uint32_t function);

void invoke(Run &run, ClawSourceContext &cpu, uint32_t function, uint32_t pc, uint32_t argument, bool stdcall) {
    push(run, cpu, pc);
    cpu.eip = function;
    if (owned(function) >= 0) {
        execute(run, cpu, function);
        cpu.eip = pop(run, cpu);
    } else {
        ClawSourceContext child = cpu;
        child.inputMask = 0x7ff;
        child.outputMask = 0x7ff;
        child.preserveMask = 0x472;
        run.source_call(function, 0, pc, child, {argument}, 0, stdcall ? 0x04 : 0);
        cpu = child;
    }
}

void execute(Run &run, ClawSourceContext &cpu, uint32_t function) {
    if (function == 0x4a7b90) {
        cpu.eax = run.get(0x52ed5c);
        push(run, cpu, cpu.esi);
        cpu.esi = run.get(0x546aa4);
        push(run, cpu, cpu.eax);
        invoke(run, cpu, cpu.esi, 0x4a7b9f, cpu.eax, true);
        cpu.ecx = run.get(0x52ed4c);
        push(run, cpu, cpu.ecx);
        invoke(run, cpu, cpu.esi, 0x4a7ba8, cpu.ecx, true);
        cpu.edx = run.get(0x52ed3c);
        push(run, cpu, cpu.edx);
        invoke(run, cpu, cpu.esi, 0x4a7bb1, cpu.edx, true);
        cpu.eax = run.get(0x52ed1c);
        push(run, cpu, cpu.eax);
        invoke(run, cpu, cpu.esi, 0x4a7bb9, cpu.eax, true);
        cpu.esi = pop(run, cpu);
        return;
    }
    push(run, cpu, cpu.ebp);
    cpu.ebp = cpu.esp;
    if (function == 0x4a7c40) {
        cpu.eax = run.get(cpu.ebp + 0x08);
        cpu.ecx = run.get(0x52ed18 + cpu.eax * 0x04);
        push(run, cpu, cpu.ecx);
        invoke(run, cpu, run.get(0x546a9c), 0x4a7c54, cpu.ecx, true);
        cpu.ebp = pop(run, cpu);
        return;
    }
    push(run, cpu, cpu.edi);
    cpu.edi = run.get(cpu.ebp + 0x08);
    cpu.eax = run.get(0x52ed18 + cpu.edi * 0x04);
    test(cpu, cpu.eax);
    if (!cpu.eax) {
        push(run, cpu, cpu.esi);
        push(run, cpu, 0x18);
        invoke(run, cpu, 0x4a48e0, 0x4a7bda, 0x18, false);
        cpu.esi = cpu.eax;
        cleanup(cpu);
        test(cpu, cpu.esi);
        if (!cpu.esi) {
            push(run, cpu, 0x11);
            invoke(run, cpu, 0x4a4860, 0x4a7bea, 0x11, false);
            cleanup(cpu);
        }
        push(run, cpu, 0x11);
        invoke(run, cpu, 0x4a7bc0, 0x4a7bf4, 0x11, false);
        cpu.eax = run.get(0x52ed18 + cpu.edi * 0x04);
        cleanup(cpu);
        test(cpu, cpu.eax);
        push(run, cpu, cpu.esi);
        if (!cpu.eax) {
            invoke(run, cpu, run.get(0x546aa4), 0x4a7c09, cpu.esi, true);
            run.put(0x52ed18 + cpu.edi * 0x04, cpu.esi);
        } else {
            invoke(run, cpu, 0x4a49b0, 0x4a7c17, cpu.esi, false);
            cleanup(cpu);
        }
        push(run, cpu, 0x11);
        invoke(run, cpu, 0x4a7c40, 0x4a7c21, 0x11, false);
        cleanup(cpu);
        cpu.esi = pop(run, cpu);
    }
    cpu.eax = run.get(0x52ed18 + cpu.edi * 0x04);
    push(run, cpu, cpu.eax);
    invoke(run, cpu, run.get(0x546aac), 0x4a7c33, cpu.eax, true);
    cpu.edi = pop(run, cpu);
    cpu.ebp = pop(run, cpu);
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    execute(run, cpu, function);
    return cpu.eax;
}
}

static ClawSourceContract source_contract(uint32_t function) {
    if (owned(function) >= 0) return {0x7ff, 0x7ff, 0x472, 0};
    return {};
}
CLAW_SOURCE_MODULE_ENTRY(claw_crt_lock_records_entry, owned, source_contract, body)
