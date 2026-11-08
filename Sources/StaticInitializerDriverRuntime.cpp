// Complete original runtime-selected static table dispatcher
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
    case 0x4a5880:
        return 2;
    default:
        return -1;
    }
}

uint32_t arithmetic_flags(uint32_t left, uint32_t right, uint32_t result, bool subtract) {
    uint32_t flags = 2u;
    uint32_t low = result & 0xffu;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    if (!(low & 1u)) flags |= 4u;
    if (!result) flags |= 0x40u;
    flags |= result & 0x80000000u ? 0x80u : 0u;
    flags |= (left ^ right ^ result) & 0x10u;
    if (subtract) {
        if (left < right) flags |= 1u;
        if (((left ^ right) & (left ^ result)) & 0x80000000u) flags |= 0x800u;
    } else {
        if (result < left) flags |= 1u;
        if ((~(left ^ right) & (left ^ result)) & 0x80000000u) flags |= 0x800u;
    }
    return flags;
}

// 0x4a5880. Runtime-selected cdecl table traversal.
uint32_t function_4a5880(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &cpu = run.source();
    cpu.eip = 0x4a5880;
    cpu.esp -= 0x04;
    run.put(cpu.esp, cpu.esi);
    cpu.eip = 0x4a5881;
    cpu.esi = run.get(cpu.esp + 0x08);
    cpu.eip = 0x4a5885;
    cpu.esp -= 0x04;
    run.put(cpu.esp, cpu.edi);
    cpu.eip = 0x4a5886;
    cpu.edi = run.get(cpu.esp + 0x10);
    cpu.eip = 0x4a588a;
    cpu.eflags = arithmetic_flags(cpu.esi, cpu.edi, cpu.esi - cpu.edi, true);
    while (cpu.esi < cpu.edi) {
        cpu.eip = 0x4a588e;
        cpu.eax = run.get(cpu.esi);
        cpu.eip = 0x4a5890;
        cpu.eflags = arithmetic_flags(0u, 0u, cpu.eax, false) & ~0x811u;
        if (cpu.eax) {
            cpu.eip = 0x4a5894;
            auto child = cpu;
            child.esp -= 0x04;
            child.eip = cpu.eax;
            run.put(child.esp, 0x4a5896);
            try {
                run.source_call(cpu.eax, 0, 0x4a5896, child);
            } catch (...) {
                cpu = child;
                throw;
            }
            cpu = child;
        }
        cpu.eip = 0x4a5896;
        const uint32_t previous = cpu.esi;
        cpu.esi += 0x04;
        cpu.eflags = arithmetic_flags(previous, 0x04, cpu.esi, false);
        cpu.eip = 0x4a5899;
        cpu.eflags = arithmetic_flags(cpu.esi, cpu.edi, cpu.esi - cpu.edi, true);
    }
    cpu.eip = 0x4a589d;
    cpu.edi = run.get(cpu.esp);
    cpu.esp += 0x04;
    cpu.eip = 0x4a589e;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 0x04;
    cpu.eip = 0x4a589f;
    return cpu.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4a5880:
        return function_4a5880(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4a5880: return {2047u, 2047u, 0u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_static_initializer_driver_entry, owned, source_contract, body)
