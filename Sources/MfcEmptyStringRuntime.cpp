// Original MFC empty string construction
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4f6433:
        return 0;
    case 0x4f6439:
        return 0;
    default:
        return -1;
    }
}

// 0x4f6433. cdecl, 0 stack argument(s), returns u32.
uint32_t function_4f6433(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.source().eax = 0x52e1ccu;
    return run.source().eax;
}

// 0x4f6439. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4f6439(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    auto &cpu = run.source();
    const uint32_t entryStack = cpu.esp;
    const uint32_t savedESI = run.automatic(-4);
    const uint32_t childReturn = run.automatic(-8);
    run.put(savedESI, cpu.esi);
    cpu.esp = savedESI;
    cpu.esi = receiver;
    run.put(childReturn, 0x4f6441u);
    cpu.esp = childReturn;
    cpu.eip = 0x4f6433u;
    function_4f6433(run, 0, nullptr);
    cpu.eip = run.get(cpu.esp);
    cpu.esp += 4u;
    cpu.eax = run.get(cpu.eax);
    // CString +0 holds its current character-storage pointer.
    run.put(cpu.esi, cpu.eax);
    cpu.eax = cpu.esi;
    cpu.esi = run.get(cpu.esp);
    cpu.esp = entryStack;
    return cpu.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4f6433:
        return function_4f6433(run, receiver, arguments);
    case 0x4f6439:
        return function_4f6439(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4f6433: return {2047u, 2047u, 1138u, 0u};
    case 0x4f6439: return {2047u, 2047u, 1138u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_mfc_empty_string_entry, owned, source_contract, body)
