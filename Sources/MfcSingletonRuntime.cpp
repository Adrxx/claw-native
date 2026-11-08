#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    return function == 0x503420 ? 1 : -1;
}

ClawSourceContract contract(uint32_t) {
    return {CLAW_CONTEXT_ALL, CLAW_CONTEXT_ALL, 0, 4};
}

void push(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}

uint32_t pop(Run &run, ClawSourceContext &cpu) {
    const uint32_t value = run.get(cpu.esp);
    cpu.esp += 4;
    return value;
}

void zeroFlags(ClawSourceContext &cpu, uint32_t value) {
    uint32_t parity = value & 255;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    cpu.eflags = (cpu.eflags & ~0x8d5u) | (value == 0 ? 0x40u : 0u) |
                 (value & 0x80000000u ? 0x80u : 0u) | (!(parity & 1) ? 4u : 0u);
}

void sourceCall(Run &run, ClawSourceContext &cpu, uint32_t target, uint32_t pc,
                std::initializer_list<uint32_t> arguments, uint32_t popBytes) {
    push(run, cpu, pc);
    cpu.eip = target;
    auto child = cpu;
    child.preserveMask = target == 0x502369 ? 0x472u : 0u;
    run.source_call(target, 0, pc, child, arguments, 0, popBytes);
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
}

// 0x503420. Full source state and physical compiler frame.
uint32_t body(Run &run, uint32_t, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    cpu.eax = 0x508bf8;
    push(run, cpu, 0x50342a);
    cpu.eip = 0x4a48c0;
    ClawCompilerContext compiler{};
    compiler.size = sizeof(compiler);
    compiler.version = CLAW_CONTEXT_VERSION;
    compiler.inputMask = CLAW_CONTEXT_ALL;
    compiler.outputMask = CLAW_CONTEXT_ALL;
    compiler.continuation = 0x50342a;
    std::memcpy(&compiler.eax, &cpu.eax, 11 * sizeof(uint32_t));
    run.context_call(0x4a48c0, compiler);
    std::memcpy(&cpu.eax, &compiler.eax, 11 * sizeof(uint32_t));
    push(run, cpu, cpu.ecx);
    push(run, cpu, cpu.ecx);
    push(run, cpu, cpu.ecx);
    push(run, cpu, cpu.ebx);
    push(run, cpu, cpu.esi);
    cpu.esi = cpu.ecx;
    push(run, cpu, cpu.edi);
    // Compiler parent frame: saved body ESP and singleton owner.
    run.put(cpu.ebp - 0x10, cpu.esp);
    run.put(cpu.ebp - 0x14, cpu.esi);
    uint32_t owner = run.get(cpu.esi);
    zeroFlags(cpu, owner);
    if (!owner) {
        push(run, cpu, 16);
        sourceCall(run, cpu, 0x502e95, 0x503444, {16}, 4);
        run.put(cpu.ebp - 4, 0);
        zeroFlags(cpu, 0);
        owner = run.get(cpu.esi);
        zeroFlags(cpu, owner);
        if (!owner) {
            const uint32_t factory = run.get(cpu.ebp + 8);
            sourceCall(run, cpu, factory, 0x503450, {}, 0);
            run.put(cpu.esi, cpu.eax);
        }
        run.put(cpu.ebp - 4, 0xffffffffu);
        zeroFlags(cpu, 0xffffffffu);
        push(run, cpu, 16);
        sourceCall(run, cpu, 0x502f05, 0x503478, {16}, 4);
    }
    cpu.eax = run.get(cpu.esi);
    cpu.ecx = run.get(cpu.ebp - 0xc);
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
    cpu.fsHead = cpu.ecx;
    cpu.ebx = pop(run, cpu);
    cpu.esp = cpu.ebp;
    cpu.ebp = pop(run, cpu);
    return cpu.eax;
}

#ifdef CLAW_ENABLE_GUEST_TRANSFER
// 0x503454. Genuine dispatcher-selected typed catch; it never returns.
void catchBody(Run &run, const ClawGuestEHInvocation &invocation) {
    auto cpu = invocation.cpu;
    push(run, cpu, 16);
    sourceCall(run, cpu, 0x502f05, 0x50345b, {16}, 4);
    if (!claw_guest_validate_eh(&run.host, &invocation))
        run.fail(CLAW_FAULT_ABI, invocation.entryPC);
    push(run, cpu, 0);
    push(run, cpu, 0);
    sourceCall(run, cpu, 0x4a5690, 0x503464, {0, 0}, 8);
    run.fail(CLAW_FAULT_ABI, 0x503464);
}
#endif
} // namespace

#ifdef CLAW_ENABLE_GUEST_TRANSFER
CLAW_GUEST_SOURCE_MODULE_ENTRY(claw_mfc_singleton_entry, owned, contract, body)
CLAW_GUEST_FUNCLET_ENTRY(claw_mfc_singleton_eh_entry, catchBody)
#else
CLAW_SOURCE_MODULE_ENTRY(claw_mfc_singleton_entry, owned, contract, body)
#endif
