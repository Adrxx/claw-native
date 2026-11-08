#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    return function == 0x4f65f2 ? 1 : -1;
}

uint32_t ordinary(Run &run, uint32_t, uint32_t receiver, const uint32_t *arguments) {
    run.stackPointer = run.frame - 0x10;
    uint32_t slot = run.call(0x4f6433, 0);
    uint32_t token = arguments[0];
    run.put(receiver + 0x00, run.get(slot));
    if (token && !(token >> 16)) {
        run.stackPointer = run.frame - 0x14;
        run.call(0x4fb253, receiver, {token & 0xffff});
        return receiver;
    }
    uint32_t length = 0;
    if (token) {
        run.stackPointer = run.frame - 0x14;
        length = run.icall(0x5469e4, {token});
    }
    if (length) {
        run.stackPointer = run.frame - 0x14;
        run.call(0x4f6480, receiver, {length});
        uint32_t destination = run.get(receiver + 0x00);
        run.stackPointer = run.frame - 0x1c;
        run.call(0x4a4a80, 0, {destination, token, length});
    }
    return receiver;
}

uint32_t parity(uint32_t value) {
    value ^= value >> 4;
    return ((0x9669u >> (value & 15)) & 1) << 2;
}

void logical(ClawSourceContext &cpu, uint32_t value, uint32_t sign) {
    cpu.eflags = (cpu.eflags & ~0x8d5u) | parity(value & 0xff) | (value == 0 ? 0x40u : 0u) | (value & sign ? 0x80u : 0u);
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

void child(Run &run, ClawSourceContext &cpu, uint32_t target, uint32_t receiver, uint32_t pc, std::initializer_list<uint32_t> arguments, uint32_t popBytes) {
    push(run, cpu, pc);
    ClawSourceContext next = cpu;
    next.inputMask = 0x7ff;
    next.outputMask = 0x7ff;
    next.preserveMask = 0x472;
    next.eip = target;
    try {
        run.source_call(target, receiver, pc, next, arguments, 0, popBytes);
    } catch (...) {
        std::memcpy(&cpu.eax, &next.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&cpu.eax, &next.eax, 11 * sizeof(uint32_t));
}

// 0x4f65f2: preserve the physical saves and dependency return sites.
void source(Run &run, ClawSourceContext &cpu) {
    cpu.eip = 0x4f65f2;
    push(run, cpu, cpu.ebx);
    cpu.eip = 0x4f65f3;
    push(run, cpu, cpu.esi);
    cpu.eip = 0x4f65f4;
    push(run, cpu, cpu.edi);
    cpu.esi = cpu.ecx;
    cpu.eip = 0x4f65f7;
    child(run, cpu, 0x4f6433, 0, 0x4f65fc, {}, 0);
    cpu.ebx = run.get(cpu.esp + 0x10);
    cpu.eax = run.get(cpu.eax);
    logical(cpu, cpu.ebx, 0x80000000);
    run.put(cpu.esi + 0x00, cpu.eax);
    bool resource = false;
    if (cpu.ebx) {
        cpu.eax = cpu.ebx >> 16;
        logical(cpu, cpu.eax & 0xffff, 0x8000);
        resource = !(cpu.eax & 0xffff);
        if (resource) {
            cpu.eax = cpu.ebx & 0xffff;
            push(run, cpu, cpu.eax);
            cpu.ecx = cpu.esi;
            cpu.eip = 0x4f6618;
            child(run, cpu, 0x4fb253, cpu.ecx, 0x4f661d, {cpu.eax}, 4);
        } else {
            logical(cpu, cpu.ebx, 0x80000000);
            cpu.eip = 0x4f6627;
            push(run, cpu, cpu.ebx);
            cpu.eip = 0x4f6628;
            child(run, cpu, 0x5469e4, 0, 0x4f662e, {cpu.ebx}, 4);
            cpu.edi = cpu.eax;
        }
    } else {
        cpu.edi = 0;
        logical(cpu, 0, 0x80000000);
    }
    if (!resource) {
        logical(cpu, cpu.edi, 0x80000000);
        if (cpu.edi) {
            push(run, cpu, cpu.edi);
            cpu.ecx = cpu.esi;
            cpu.eip = 0x4f6637;
            child(run, cpu, 0x4f6480, cpu.ecx, 0x4f663c, {cpu.edi}, 4);
            push(run, cpu, cpu.edi);
            push(run, cpu, cpu.ebx);
            uint32_t destination = run.get(cpu.esi + 0x00);
            push(run, cpu, destination);
            cpu.eip = 0x4f6640;
            child(run, cpu, 0x4a4a80, 0, 0x4f6645, {destination, cpu.ebx, cpu.edi}, 0);
            uint32_t before = cpu.esp;
            cpu.esp += 0x0c;
            logical(cpu, cpu.esp, 0x80000000);
            cpu.eflags |= cpu.esp < before ? 1u : 0u;
            cpu.eflags |= ((before ^ 0x0c ^ cpu.esp) & 0x10);
            cpu.eflags |= ((~(before ^ 0x0c) & (before ^ cpu.esp)) >> 20) & 0x800;
        }
    }
    cpu.eax = cpu.esi;
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
    cpu.ebx = pop(run, cpu);
    cpu.eip = 0x4f664d;
}

ClawSourceContract contract(uint32_t) {
    return {0x7ff, 0x7ff, 0x472, 4};
}

bool optional(uint32_t function) {
    return function == 0x4f65f2;
}

uint32_t sourceBody(Run &run, uint32_t, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    source(run, cpu);
    return cpu.eax;
}
}

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_static_string_constructor_entry, owned, contract, optional, ordinary, sourceBody)
