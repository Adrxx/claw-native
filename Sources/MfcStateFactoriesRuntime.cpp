// Whole original MFC factories with explicit source register/frame ownership.
// Physical allocation failures retain their genuine nonreturning prefix;
// source exception dispatch and cleanup remain separate dependencies.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
int owned(uint32_t function) {
    switch (function) {
    case 0x502335:
    case 0x502369:
        return 0;
    default:
        return -1;
    }
}
ClawSourceContract source_contract(uint32_t) { return {0x7ff, 0x7ff, 0x472, 0}; }
void push(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}
void registers(ClawSourceContext &cpu, const ClawCompilerContext &child) {
    cpu.eax = child.eax;
    cpu.ebx = child.ebx;
    cpu.ecx = child.ecx;
    cpu.edx = child.edx;
    cpu.esi = child.esi;
    cpu.edi = child.edi;
    cpu.ebp = child.ebp;
    cpu.esp = child.esp;
    cpu.eip = child.eip;
    cpu.eflags = child.eflags;
    cpu.fsHead = child.fsHead;
}
void scope(Run &run, ClawSourceContext &cpu, uint32_t handler, uint32_t continuation) {
    cpu.eax = handler;
    push(run, cpu, continuation);
    ClawCompilerContext child{72, 1, 0x7ff, 0x7ff, cpu.eax, cpu.ebx, cpu.ecx, cpu.edx,
                             cpu.esi, cpu.edi, cpu.ebp, cpu.esp, 0x4a48c0, cpu.eflags,
                             cpu.fsHead, continuation, 0, 0};
    run.context_call(0x4a48c0, child);
    registers(cpu, child);
}
uint32_t outward(Run &run, ClawSourceContext &cpu, uint32_t target, uint32_t receiver,
                 uint32_t continuation, std::initializer_list<uint32_t> arguments = {}, uint32_t pops = 0) {
    push(run, cpu, continuation);
    ClawSourceContext child = cpu;
    child.eip = target;
    uint32_t value = run.source_call(target, receiver, continuation, child, arguments, 0, pops);
    cpu = child;
    return value;
}
uint32_t compare_zero(uint32_t value) {
    uint32_t flags = 2;
    if (!value)
        flags |= 0x40;
    if (value & 0x80000000u)
        flags |= 0x80;
    uint32_t parity = value & 0xff;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    if (!(parity & 1))
        flags |= 4;
    return flags;
}
void leave(Run &run, ClawSourceContext &cpu) {
    cpu.ecx = run.get(cpu.ebp - 12);
    cpu.fsHead = cpu.ecx;
    cpu.esp = cpu.ebp;
    cpu.ebp = run.get(cpu.esp);
    cpu.esp += 4;
}
uint32_t function_502335(Run &run) {
    auto &cpu = run.source();
    scope(run, cpu, 0x508525, 0x50233f);
    push(run, cpu, cpu.ecx);
    push(run, cpu, 0x118);
    uint32_t allocation = outward(run, cpu, 0x502f84, 0, 0x50234a, {0x118}, 4);
    cpu.ecx = allocation;
    run.put(cpu.ebp - 16, cpu.ecx);
    cpu.eax = 0;
    cpu.eflags = compare_zero(cpu.ecx);
    run.put(cpu.ebp - 4, 0);
    if (cpu.ecx != 0) {
        cpu.eax = outward(run, cpu, 0x501f01, cpu.ecx, 0x50235d);
    }
    uint32_t value = cpu.eax;
    leave(run, cpu);
    return value;
}
uint32_t function_502369(Run &run) {
    auto &cpu = run.source();
    scope(run, cpu, 0x508539, 0x502373);
    push(run, cpu, cpu.ecx);
    push(run, cpu, cpu.esi);
    push(run, cpu, 0x1074);
    uint32_t allocation = outward(run, cpu, 0x502f84, 0, 0x50237f, {0x1074}, 4);
    cpu.esi = allocation;
    run.put(cpu.ebp - 16, cpu.esi);
    cpu.eax = 0;
    cpu.eflags = compare_zero(cpu.esi);
    run.put(cpu.ebp - 4, 0);
    if (cpu.esi != 0) {
        push(run, cpu, 1);
        cpu.ecx = cpu.esi;
        outward(run, cpu, 0x501fde, cpu.ecx, 0x502396, {1}, 4);
        run.put(cpu.esi, 0x51020c);
        cpu.eax = cpu.esi;
    }
    uint32_t value = cpu.eax;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 4;
    leave(run, cpu);
    return value;
}
uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    switch (function) {
    case 0x502335:
        return function_502335(run);
    case 0x502369:
        return function_502369(run);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_SOURCE_MODULE_ENTRY(claw_mfc_state_factories_entry, owned, source_contract, body)
