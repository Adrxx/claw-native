// Whole original CRT string duplication
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
    case 0x4a56e0:
        return 1;
    default:
        return -1;
    }
}

uint32_t logical_flags(uint32_t value) {
    uint32_t parity = value & 0xffu;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    return 2u | ((parity & 1u) ? 0u : 4u) |
           (value == 0 ? 0x40u : 0u) | (value & 0x80000000u ? 0x80u : 0u);
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

void scan(Run &run, ClawSourceContext &cpu) {
    cpu.edi = cpu.esi;
    cpu.ecx = 0xffffffffu;
    cpu.eax = 0;
    cpu.eflags = logical_flags(0);
    while (cpu.ecx) {
        uint8_t value = run.get8(cpu.edi);
        ++cpu.edi;
        --cpu.ecx;
        if (value == 0)
            break;
    }
    cpu.ecx = ~cpu.ecx;
}

// 0x4a56e0 strdup. cdecl, 1 stack argument, returns u32.
uint32_t function_4a56e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &cpu = run.source();
    push(run, cpu, cpu.ebx);
    push(run, cpu, cpu.esi);
    cpu.esi = run.get(cpu.esp + 12);
    push(run, cpu, cpu.edi);
    cpu.eflags = logical_flags(cpu.esi);
    if (cpu.esi) {
        scan(run, cpu);
        push(run, cpu, cpu.ecx);
        push(run, cpu, 0x4a56fc);
        auto child = cpu;
        child.eip = 0x4a48e0;
        run.source_call(0x4a48e0, 0, 0x4a56fc, child, {cpu.ecx});
        cpu = child;
        cpu.edx = cpu.eax;
        cpu.esp += 4;
        cpu.eflags = logical_flags(cpu.edx);
        if (cpu.edx) {
            scan(run, cpu);
            cpu.edi -= cpu.ecx;
            cpu.esi = cpu.edi;
            cpu.ebx = cpu.ecx;
            cpu.edi = cpu.edx;
            cpu.eax = cpu.edi;
            cpu.ecx >>= 2;
            while (cpu.ecx) {
                run.put(cpu.edi, run.get(cpu.esi));
                cpu.edi += 4;
                cpu.esi += 4;
                --cpu.ecx;
            }
            cpu.ecx = cpu.ebx & 3u;
            cpu.eflags = logical_flags(cpu.ecx);
            while (cpu.ecx) {
                run.put8(cpu.edi, run.get8(cpu.esi));
                ++cpu.edi;
                ++cpu.esi;
                --cpu.ecx;
            }
            cpu.edi = pop(run, cpu);
            cpu.esi = pop(run, cpu);
            cpu.ebx = pop(run, cpu);
            return cpu.eax;
        }
    }
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
    cpu.eax = 0;
    cpu.eflags = logical_flags(0);
    cpu.ebx = pop(run, cpu);
    return cpu.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4a56e0:
        return function_4a56e0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4a56e0: return {2047u, 2047u, 1138u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_crt_string_duplicate_entry, owned, source_contract, body)
