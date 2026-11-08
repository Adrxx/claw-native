#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x502301:
    case 0x50210b:
        return 0;
    case 0x4f5e89:
    case 0x4f5133:
        return 1;
    default:
        return -1;
    }
}

ClawSourceContract contract(uint32_t function) {
    return {0x7ff, 0x7ff, 0x472, uint32_t(owned(function) == 1 ? 4 : 0)};
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

void scope(Run &run, ClawSourceContext &cpu, uint32_t handler, uint32_t returnPC) {
    cpu.eax = handler;
    push(run, cpu, returnPC);
    ClawCompilerContext child{};
    child.size = sizeof(child);
    child.version = 1;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    std::memcpy(&child.eax, &cpu.eax, 11 * sizeof(uint32_t));
    child.eip = 0x4a48c0;
    child.continuation = returnPC;
    run.context_call(0x4a48c0, child);
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
}

// 0x4f5e89 and 0x4f5133. Container header, empty links and block size.
void container(Run &run, ClawSourceContext &cpu, uint32_t function) {
    cpu.eax = cpu.ecx;
    cpu.ecx = 0;
    cpu.eflags = 0x46;
    if (function == 0x4f5e89) {
        run.put(cpu.eax + 4, cpu.ecx);
        run.put(cpu.eax + 0xc, cpu.ecx);
        run.put(cpu.eax + 0x10, cpu.ecx);
        run.put(cpu.eax + 0x14, cpu.ecx);
    } else {
        run.put(cpu.eax + 0xc, cpu.ecx);
        run.put(cpu.eax + 0x10, cpu.ecx);
        run.put(cpu.eax + 8, cpu.ecx);
        run.put(cpu.eax + 4, cpu.ecx);
        run.put(cpu.eax + 0x14, cpu.ecx);
    }
    cpu.ecx = run.get(cpu.esp + 4);
    run.put(cpu.eax, function == 0x4f5e89 ? 0x510264 : 0x51000c);
    if (function == 0x4f5e89)
        run.put(cpu.eax + 8, 0x11);
    run.put(cpu.eax + 0x18, cpu.ecx);
}

void member(Run &run, ClawSourceContext &cpu, uint32_t function, uint32_t returnPC) {
    push(run, cpu, returnPC);
    cpu.eip = function;
    container(run, cpu, function);
    cpu.eip = pop(run, cpu);
    cpu.esp += 4;
}

void leave(Run &run, ClawSourceContext &cpu) {
    cpu.esp = cpu.ebp;
    cpu.ebp = pop(run, cpu);
}

// 0x50210b. Application record and its three embedded container members.
void construct(Run &run, ClawSourceContext &cpu) {
    scope(run, cpu, 0x5084ca, 0x502115);
    push(run, cpu, cpu.ecx);
    push(run, cpu, cpu.esi);
    cpu.esi = cpu.ecx;
    run.put(cpu.ebp - 0x10, cpu.esi);
    run.put(cpu.esi, 0x5101f4);
    cpu.eax = 0;
    cpu.eflags = 0x46;
    push(run, cpu, 10);
    cpu.ecx = cpu.esi + 0x30;
    run.put(cpu.ebp - 4, cpu.eax);
    run.put(cpu.esi + 8, cpu.eax);
    run.put(cpu.esi + 0xc, cpu.eax);
    member(run, cpu, 0x4f5e89, 0x502137);
    push(run, cpu, 10);
    cpu.ecx = cpu.esi + 0x4c;
    run.put8(cpu.ebp - 4, 1);
    member(run, cpu, 0x4f5e89, 0x502145);
    push(run, cpu, 10);
    cpu.ecx = cpu.esi + 0x68;
    run.put8(cpu.ebp - 4, 2);
    member(run, cpu, 0x4f5133, 0x502153);
    cpu.ecx = run.get(cpu.ebp - 0xc);
    run.put(cpu.esi, 0x510204);
    run.put(cpu.esi + 0xc, 0x54);
    run.put(cpu.esi + 0x28, 0x4f63d0);
    cpu.eax = cpu.esi;
    cpu.fsHead = cpu.ecx;
    cpu.esi = pop(run, cpu);
    leave(run, cpu);
}

uint32_t zeroCompareFlags(uint32_t value) {
    uint32_t bits = value & 255;
    bits ^= bits >> 4;
    bits ^= bits >> 2;
    bits ^= bits >> 1;
    return 2 | ((!(bits & 1)) ? 4 : 0) | (!value ? 0x40 : 0) | (value & 0x80000000 ? 0x80 : 0);
}

// 0x502301. Checked allocation followed by the owned record constructor.
void factory(Run &run, ClawSourceContext &cpu) {
    scope(run, cpu, 0x508511, 0x50230b);
    push(run, cpu, cpu.ecx);
    push(run, cpu, 0x84);
    push(run, cpu, 0x502316);
    auto child = cpu;
    child.eip = 0x502f84;
    run.source_call(0x502f84, 0, 0x502316, child, {0x84}, 0, 4);
    cpu = child;
    cpu.ecx = cpu.eax;
    run.put(cpu.ebp - 0x10, cpu.ecx);
    cpu.eax = 0;
    cpu.eflags = 0x46;
    cpu.eflags = zeroCompareFlags(cpu.ecx);
    run.put(cpu.ebp - 4, cpu.eax);
    if (cpu.ecx) {
        push(run, cpu, 0x502329);
        cpu.eip = 0x50210b;
        construct(run, cpu);
        cpu.eip = pop(run, cpu);
    }
    cpu.ecx = run.get(cpu.ebp - 0xc);
    cpu.fsHead = cpu.ecx;
    leave(run, cpu);
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    switch (function) {
    case 0x502301:
        factory(run, cpu);
        break;
    case 0x50210b:
        construct(run, cpu);
        break;
    default:
        container(run, cpu, function);
        break;
    }
    return cpu.eax;
}
}

CLAW_SOURCE_MODULE_ENTRY(claw_mfc_application_thread_record_entry, owned, contract, body)
