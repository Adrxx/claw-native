// Whole original CWinApp constructor
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
    case 0x50257f:
        return 1;
    default:
        return -1;
    }
}

void copy_cpu(ClawSourceContext &to, const ClawSourceContext &from) {
    std::memcpy(&to.eax, &from.eax, 11 * sizeof(uint32_t));
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

void child(Run &run, ClawSourceContext &cpu, uint32_t function, uint32_t returnPC,
           uint32_t preserve, uint32_t receiver = 0,
           std::initializer_list<uint32_t> arguments = {}, uint32_t popBytes = 0) {
    push(run, cpu, returnPC);
    ClawSourceContext context = cpu;
    context.preserveMask = preserve;
    context.eip = function;
    run.source_call(function, receiver, returnPC, context, arguments, 0, popBytes);
    copy_cpu(cpu, context);
}

void compare_zero(ClawSourceContext &cpu, uint32_t value) {
    uint32_t byte = value & 255;
    byte ^= byte >> 4;
    byte ^= byte >> 2;
    byte ^= byte >> 1;
    cpu.eflags = (cpu.eflags & ~0x8d5u) | ((byte & 1) ? 0 : 4) |
                 (value == 0 ? 0x40 : 0) | (value & 0x80000000u ? 0x80 : 0);
}

// 0x50257f. Complete constructor with original compiler and child frames.
uint32_t function_50257f(Run &run, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    cpu.eax = 0x5086f4;
    push(run, cpu, 0x502589);
    ClawCompilerContext compiler{};
    compiler.size = sizeof(compiler);
    compiler.version = 1;
    compiler.inputMask = 0x7ff;
    compiler.outputMask = 0x7ff;
    std::memcpy(&compiler.eax, &cpu.eax, 11 * sizeof(uint32_t));
    compiler.eip = 0x4a48c0;
    compiler.continuation = 0x502589;
    run.context_call(0x4a48c0, compiler);
    std::memcpy(&cpu.eax, &compiler.eax, 11 * sizeof(uint32_t));
    push(run, cpu, cpu.ecx);
    push(run, cpu, cpu.ebx);
    push(run, cpu, cpu.esi);
    cpu.esi = cpu.ecx;
    push(run, cpu, cpu.edi);
    run.put(cpu.ebp - 0x10, cpu.esi);
    child(run, cpu, 0x503510, 0x502597, 0x472, cpu.ecx);
    cpu.edi = 0;
    compare_zero(cpu, 0);
    // Receiver vtable and owned name pointer.
    run.put(cpu.esi, 0x5106cc);
    compare_zero(cpu, run.get(cpu.ebp + 8));
    run.put(cpu.ebp - 4, cpu.edi);
    if (!(cpu.eflags & 0x40)) {
        push(run, cpu, run.get(cpu.ebp + 8));
        child(run, cpu, 0x4a56e0, 0x5025af, 0x472, 0, {run.get(cpu.esp)});
        cpu.ecx = pop(run, cpu);
        run.put(cpu.esi + 0x78, cpu.eax);
    } else {
        run.put(cpu.esi + 0x78, cpu.edi);
    }
    child(run, cpu, 0x50228f, 0x5025bd, 0x400);
    cpu.ebx = cpu.eax;
    push(run, cpu, 0x502301);
    cpu.ecx = cpu.ebx + 0x1070;
    child(run, cpu, 0x50335e, 0x5025cf, 0x400, cpu.ecx, {0x502301}, 4);
    // Publish application, thread handle and thread ID in physical order.
    run.put(cpu.eax + 4, cpu.esi);
    child(run, cpu, 0x5469bc, 0x5025d8, 0);
    run.put(cpu.esi + 0x28, cpu.eax);
    child(run, cpu, 0x5469c0, 0x5025e1, 0);
    cpu.ecx = run.get(cpu.ebp - 0xc);
    run.put(cpu.esi + 0x2c, cpu.eax);
    run.put(cpu.ebx + 4, cpu.esi);
    run.put(cpu.esi + 0x68, cpu.edi);
    run.put(cpu.esi + 0x8c, cpu.edi);
    run.put(cpu.esi + 0x90, cpu.edi);
    run.put(cpu.esi + 0x7c, cpu.edi);
    run.put(cpu.esi + 0x88, cpu.edi);
    run.put(cpu.esi + 0xa8, cpu.edi);
    run.put(cpu.esi + 0x80, cpu.edi);
    run.put16(cpu.esi + 0xb2, uint16_t(cpu.edi));
    run.put16(cpu.esi + 0xb0, uint16_t(cpu.edi));
    run.put(cpu.esi + 0x70, cpu.edi);
    run.put(cpu.esi + 0xac, cpu.edi);
    run.put(cpu.esi + 0xa0, cpu.edi);
    run.put(cpu.esi + 0xa4, cpu.edi);
    run.put(cpu.esi + 0x94, cpu.edi);
    run.put(cpu.esi + 0x98, cpu.edi);
    run.put(cpu.esi + 0xb4, cpu.edi);
    run.put(cpu.esi + 0xbc, cpu.edi);
    run.put(cpu.esi + 0x84, cpu.edi);
    run.put(cpu.esi + 0xb8, 0x200);
    cpu.eax = cpu.esi;
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
    cpu.fsHead = cpu.ecx;
    cpu.ebx = pop(run, cpu);
    cpu.esp = cpu.ebp;
    cpu.ebp = pop(run, cpu);
    return cpu.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x50257f:
        return function_50257f(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x50257f: return {2047u, 2047u, 1138u, 4u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_mfc_application_object_entry, owned, source_contract, body)
