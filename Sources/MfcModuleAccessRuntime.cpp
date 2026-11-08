// Original MFC module state lookup and checked local allocation
//
// Whole original wrappers; their MFC dependencies execute through the host.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x50228f:
        return 0;
    case 0x502f84:
        return 1;
    default:
        return -1;
    }
}

// 0x50228f. cdecl, 0 stack argument(s), returns u32.
uint32_t function_50228f(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t savedStackPointer = run.stackPointer;
    run.stackPointer = run.frame - 8;
    uint32_t thread = run.call(0x50335e, 0x53ec9c, {0x502335});
    // Thread +4 is the overriding module pointer, not the thread record itself.
    uint32_t module = run.get(thread + 4);
    if (!module) {
        run.stackPointer = run.frame - 8;
        module = run.call(0x503420, 0x53eca0, {0x502369});
    }
    run.stackPointer = savedStackPointer;
    return module;
}

// 0x502f84. stdcall, 1 stack argument(s), returns u32.
uint32_t function_502f84(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t savedStackPointer = run.stackPointer;
    run.stackPointer = run.frame - 16;
    uint32_t allocation = run.icall(0x546aa8, {0x40, arguments[0]});
    if (!allocation) {
        run.stackPointer = run.frame - 8;
        run.call(0x4f50fd, 0);
    }
    run.stackPointer = savedStackPointer;
    return allocation;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x50228f:
        return function_50228f(run, receiver, arguments);
    case 0x502f84:
        return function_502f84(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

ClawSourceContract source_contract(uint32_t function) {
    if (function == 0x50228f) return {0x7ff, 0x7ff, 0x400, 0};
    if (function == 0x502f84) return {0x7ff, 0x7ff, 0x472, 4};
    return {};
}

bool optional_source(uint32_t function) {
    return function == 0x50228f || function == 0x502f84;
}

// 0x50228f. The two original calls reuse the same physical outgoing frame.
uint32_t source_getter_50228f(Run &run) {
    auto &cpu = run.source();
    cpu.esp -= 4;
    run.put(cpu.esp, 0x502335);
    cpu.ecx = 0x53ec9c;
    auto child = cpu;
    child.esp -= 4;
    child.eip = 0x50335e;
    run.source_call(0x50335e, cpu.ecx, 0x50229e, child, {0x502335}, 0, 4);
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
    // Thread +4 is loaded only after the child has performed its stack writes.
    cpu.eax = run.get(cpu.eax + 4);
    uint32_t parity = cpu.eax & 0xff;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    cpu.eflags = (cpu.eflags & ~0x8d5u) | (cpu.eax & 0x80000000u ? 0x80u : 0u) |
                 (cpu.eax == 0 ? 0x40u : 0u) | ((parity & 1) ? 0u : 4u);
    if (!cpu.eax) {
        cpu.esp -= 4;
        run.put(cpu.esp, 0x502369);
        cpu.ecx = 0x53eca0;
        child = cpu;
        child.preserveMask = 0;
        child.esp -= 4;
        child.eip = 0x503420;
        run.source_call(0x503420, cpu.ecx, 0x5022b4, child, {0x502369}, 0, 4);
        std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
    }
    return cpu.eax;
}

uint32_t source_body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (function == 0x50228f) return source_getter_50228f(run);
    if (function != 0x502f84) run.fail(CLAW_FAULT_ABI, function);
    auto &cpu = run.source();
    cpu.esp -= 4;
    run.put(cpu.esp, cpu.esi);
    const uint32_t size = run.get(cpu.esp + 8);
    cpu.esp -= 4;
    run.put(cpu.esp, size);
    cpu.esp -= 4;
    run.put(cpu.esp, 0x40);
    const uint32_t target = run.get(0x546aa8);
    auto child = cpu;
    child.esp -= 4;
    child.eip = target;
    run.source_call(target, 0, 0x502f91, child, {0x40, size}, 0, 8);
    cpu = child;
    cpu.esi = cpu.eax;
    // TEST's arithmetic result: CF/OF clear, SZP from the pointer.
    uint32_t parity = cpu.esi & 0xff;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    cpu.eflags = (cpu.eflags & ~0x8d5u) | (cpu.esi & 0x80000000u ? 0x80u : 0u) |
                 (cpu.esi == 0 ? 0x40u : 0u) | ((parity & 1) ? 0u : 4u);
    if (!cpu.esi) {
        child = cpu;
        child.esp -= 4;
        child.eip = 0x4f50fd;
        run.source_call(0x4f50fd, 0, 0x502f9c, child);
        cpu = child;
    }
    cpu.eax = cpu.esi;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 4;
    return cpu.eax;
}

} // namespace

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_mfc_module_access_entry, owned, source_contract, optional_source, body, source_body)
