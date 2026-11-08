// Static class lists, scalar records and physical message publication.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x4f709b:
    case 0x4fb15d:
    case 0x4f8371:
        return 1;
    case 0x4a13f4:
    case 0x4a141e:
    case 0x4a2e53:
    case 0x4a2e7d:
        return 2;
    case 0x4f8222:
    case 0x50254b:
    case 0x5028dc:
    case 0x502b05:
    case 0x502b52:
        return 0;
    default:
        return -1;
    }
}

void push(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 0x4;
    run.put(cpu.esp, value);
}

uint32_t pop(Run &run, ClawSourceContext &cpu) {
    uint32_t value = run.get(cpu.esp);
    cpu.esp += 0x4;
    return value;
}

void copyCPU(ClawSourceContext &to, const ClawSourceContext &from) {
    std::memcpy(&to.eax, &from.eax, 11 * sizeof(uint32_t));
}

void original(Run &run, ClawSourceContext &cpu, uint32_t target, uint32_t receiver,
              uint32_t pc, uint32_t preserve, std::initializer_list<uint32_t> args,
              uint32_t cleanup) {
    push(run, cpu, pc);
    cpu.eip = target;
    auto child = cpu;
    child.preserveMask = preserve;
    run.source_call(target, receiver, pc, child, args, 0, cleanup);
    copyCPU(cpu, child);
}

uint32_t addFlags(uint32_t left, uint32_t right) {
    uint32_t result = left + right;
    uint32_t parity = result & 0xff;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    return 0x2 | (result < left ? 0x1 : 0) | (!(parity & 1) ? 0x4 : 0)
        | ((left ^ right ^ result) & 0x10) | (!result ? 0x40 : 0)
        | (result & 0x80000000 ? 0x80 : 0)
        | ((~(left ^ right) & (left ^ result)) & 0x80000000 ? 0x800 : 0);
}

// 0x4fb15d: +0x0 vtable, +0x4 opaque scalar.
void base(Run &run, ClawSourceContext &cpu) {
    cpu.eax = cpu.ecx;
    cpu.ecx = run.get(cpu.esp + 0x4);
    run.put(cpu.eax + 0x0, 0x5119f4);
    run.put(cpu.eax + 0x4, cpu.ecx);
}

// 0x4f709b: real shared module class-list registration.
void registerRecord(Run &run, ClawSourceContext &cpu) {
    push(run, cpu, cpu.esi);
    push(run, cpu, cpu.edi);
    cpu.edi = cpu.ecx;
    original(run, cpu, 0x50228f, 0, 0x4f70a4, 0x400, {}, 0);
    push(run, cpu, 0);
    cpu.esi = cpu.eax;
    original(run, cpu, 0x502e95, 0, 0x4f70ad, 0, {0}, 0x4);
    uint32_t node = run.get(cpu.esp + 0xc);
    push(run, cpu, node);
    cpu.ecx = cpu.esi + 0x1c;
    original(run, cpu, 0x502f26, cpu.ecx, 0x4f70b9, 0x472, {node}, 0x4);
    push(run, cpu, 0);
    original(run, cpu, 0x502f05, 0, 0x4f70c0, 0, {0}, 0x4);
    cpu.eax = cpu.edi;
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
}

// Four original scalar constructor entries: +0xc/+0x10 cleared, +0x94 value.
void scalar(Run &run, ClawSourceContext &cpu, uint32_t pc, uint32_t vtable) {
    push(run, cpu, cpu.esi);
    cpu.esi = cpu.ecx;
    uint32_t first = run.get(cpu.esp + 0x8);
    push(run, cpu, first);
    push(run, cpu, pc);
    cpu.eip = 0x4fb15d;
    base(run, cpu);
    cpu.eip = pop(run, cpu);
    cpu.esp += 0x4;
    cpu.eax = run.get(cpu.esp + 0xc);
    run.put(cpu.esi + 0xc, 0);
    run.put(cpu.esi + 0x10, 0);
    cpu.eflags = 0x46;
    run.put(cpu.esi + 0x94, cpu.eax);
    run.put(cpu.esi + 0x0, vtable);
    cpu.eax = cpu.esi;
    cpu.esi = pop(run, cpu);
}

// 0x4f8371: +0x1c buffer, +0x34/+0x38 cleared scalar slots.
void buffer(Run &run, ClawSourceContext &cpu) {
    push(run, cpu, cpu.esi);
    push(run, cpu, cpu.edi);
    cpu.esi = cpu.ecx;
    original(run, cpu, 0x4f6a9a, cpu.ecx, 0x4f837a, 0x472, {}, 0);
    cpu.edi = cpu.esi + 0x1c;
    push(run, cpu, 0x20);
    push(run, cpu, 0);
    push(run, cpu, cpu.edi);
    run.put(cpu.esi + 0x0, 0x51118c);
    original(run, cpu, 0x4a4a20, 0, 0x4f838d, 0x452, {cpu.edi, 0, 0x20}, 0);
    cpu.eax = run.get(cpu.esp + 0x18);
    run.put(cpu.esi + 0x38, 0);
    run.put(cpu.esi + 0x34, 0);
    cpu.eflags = addFlags(cpu.esp, 0xc);
    cpu.esp += 0xc;
    run.put(cpu.edi + 0x0, cpu.eax);
    cpu.eax = cpu.esi;
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
}

// 0x4f8222: physical RegisterWindowMessageA publication.
void publish(Run &run, ClawSourceContext &cpu) {
    push(run, cpu, 0x511170);
    original(run, cpu, 0x546c2c, 0, 0x4f822d, 0, {0x511170}, 0x4);
    run.put(0x5406fc, cpu.eax);
}

// 0x50254b/0x5028dc/0x502b05/0x502b52 owned caller frames.
void thunk(Run &run, ClawSourceContext &cpu, uint32_t node, uint32_t receiver, uint32_t pc) {
    push(run, cpu, node);
    cpu.ecx = receiver;
    push(run, cpu, pc);
    cpu.eip = 0x4f709b;
    registerRecord(run, cpu);
    cpu.eip = pop(run, cpu);
    cpu.esp += 0x4;
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    switch (function) {
    case 0x4f709b:
        registerRecord(run, cpu);
        break;
    case 0x4fb15d:
        base(run, cpu);
        break;
    case 0x4a13f4:
        scalar(run, cpu, 0x4a1400, 0x510574);
        break;
    case 0x4a141e:
        scalar(run, cpu, 0x4a142a, 0x510594);
        break;
    case 0x4a2e53:
        scalar(run, cpu, 0x4a2e5f, 0x511a14);
        break;
    case 0x4a2e7d:
        scalar(run, cpu, 0x4a2e89, 0x511a34);
        break;
    case 0x4f8371:
        buffer(run, cpu);
        break;
    case 0x4f8222:
        publish(run, cpu);
        break;
    case 0x50254b:
        thunk(run, cpu, 0x52e490, 0x53edd8, 0x50255a);
        break;
    case 0x5028dc:
        thunk(run, cpu, 0x52e540, 0x53ede8, 0x5028eb);
        break;
    case 0x502b05:
        thunk(run, cpu, 0x52e5a8, 0x53edec, 0x502b14);
        break;
    case 0x502b52:
        thunk(run, cpu, 0x52e5e0, 0x53edf0, 0x502b61);
        break;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
    return cpu.eax;
}

uint32_t ordinary(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    if (function != 0x4fb15d)
        run.fail(CLAW_FAULT_ABI, function);
    run.put(receiver + 0x0, 0x5119f4);
    run.put(receiver + 0x4, arguments[0]);
    return receiver;
}

bool optional(uint32_t function) {
    return function == 0x4fb15d;
}

ClawSourceContract source_contract(uint32_t function) {
    return {0x7ff, 0x7ff, function == 0x4fb15d ? 0x472u : 0u,
            function == 0x4f709b || function == 0x4fb15d || function == 0x4f8371 ? 0x4u :
            owned(function) == 2 ? 0x8u : 0u};
}
}

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_static_list_records_entry, owned, source_contract, optional, ordinary, body)
