// Complete original static lock object constructor with physical source and FS state
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
    case 0x4a2cf1:
        return 0;
    default:
        return -1;
    }
}

void push(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}

void adopt(ClawSourceContext &cpu, const ClawSourceContext &child) {
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
}

void sourceChild(Run &run, ClawSourceContext &cpu, uint32_t function,
                 uint32_t receiver, uint32_t pc, uint32_t argument, uint32_t preserve) {
    push(run, cpu, pc);
    auto child = cpu;
    child.eip = function;
    child.preserveMask = preserve;
    try {
        run.source_call(function, receiver, pc, child, {argument}, 0, 4);
    } catch (...) {
        adopt(cpu, child);
        throw;
    }
    adopt(cpu, child);
}

uint32_t addFlags(uint32_t flags, uint32_t left, uint32_t right, uint32_t result) {
    uint32_t bits = 2;
    if (result < left) bits |= 1;
    uint32_t parity = result & 0xff;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    if (!(parity & 1)) bits |= 4;
    if ((left ^ right ^ result) & 0x10) bits |= 0x10;
    if (!result) bits |= 0x40;
    if (result & 0x80000000) bits |= 0x80;
    if ((~(left ^ right) & (left ^ result)) & 0x80000000) bits |= 0x800;
    return (flags & ~0x8d5u) | bits;
}

// 0x4a2cf1. Physical constructor frame and compiler registration.
uint32_t function_4a2cf1(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &cpu = run.source();
    cpu.eax = 0x508bbc;
    push(run, cpu, 0x4a2cfb);
    ClawCompilerContext compiler{};
    compiler.size = sizeof(compiler);
    compiler.version = CLAW_CONTEXT_VERSION;
    compiler.inputMask = 0x7ff;
    compiler.outputMask = 0x7ff;
    std::memcpy(&compiler.eax, &cpu.eax, 11 * sizeof(uint32_t));
    compiler.eip = 0x4a48c0;
    compiler.continuation = 0x4a2cfb;
    run.context_call(0x4a48c0, compiler);
    std::memcpy(&cpu.eax, &compiler.eax, 11 * sizeof(uint32_t));
    push(run, cpu, cpu.ecx);
    push(run, cpu, cpu.ecx);
    push(run, cpu, cpu.esi);
    push(run, cpu, cpu.edi);
    cpu.edi = cpu.ecx;
    push(run, cpu, 0xa);
    // EH locals: -0x10 receiver, -0x14 embedded lock, -4 state.
    run.put(cpu.ebp - 0x10, cpu.edi);
    sourceChild(run, cpu, 0x4f5e89, cpu.ecx, 0x4a2d0b, 0xa, 0x472);
    run.put(cpu.ebp - 0x4, 0);
    cpu.eflags = (cpu.eflags & ~0x8d5u) | 0x46;
    cpu.esi = cpu.edi + 0x1c;
    push(run, cpu, 0);
    cpu.ecx = cpu.esi;
    run.put(cpu.ebp - 0x14, cpu.esi);
    sourceChild(run, cpu, 0x4a2f62, cpu.ecx, 0x4a2d1e, 0, 0);
    run.put(cpu.esi, 0x51194c);
    uint32_t previous = cpu.esi;
    cpu.esi += 8;
    cpu.eflags = addFlags(cpu.eflags, previous, 8, cpu.esi);
    push(run, cpu, cpu.esi);
    run.put8(cpu.ebp - 0x4, 1);
    sourceChild(run, cpu, 0x546aa4, 0, 0x4a2d32, cpu.esi, 0);
    cpu.ecx = run.get(cpu.ebp - 0xc);
    run.put(cpu.edi, 0x511934);
    cpu.eax = cpu.edi;
    cpu.edi = run.get(cpu.esp);
    cpu.esp += 4;
    cpu.fsHead = cpu.ecx;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 4;
    cpu.esp = cpu.ebp;
    cpu.ebp = run.get(cpu.esp);
    cpu.esp += 4;
    return cpu.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4a2cf1:
        return function_4a2cf1(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4a2cf1: return {2047u, 2047u, 0u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_static_lock_object_entry, owned, source_contract, body)
