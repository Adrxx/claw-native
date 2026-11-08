// Original CRT catch-object PMD adjustment
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
    case 0x4a8ed0:
        return 2;
    default:
        return -1;
    }
}

// Arithmetic flag helpers retain the fixed bit and model the pinned x86 flags.
uint32_t resultFlags(uint32_t value) {
    uint32_t low = value & 0xffu;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    uint32_t flags = 2u;
    if (!(low & 1u)) flags |= 4u;
    if (!value) flags |= 0x40u;
    if (value & 0x80000000u) flags |= 0x80u;
    return flags;
}

uint32_t addFlags(uint32_t left, uint32_t right, uint32_t sum) {
    uint32_t flags = resultFlags(sum);
    if (sum < left) flags |= 1u;
    if ((left ^ right ^ sum) & 0x10u) flags |= 0x10u;
    if ((~(left ^ right) & (left ^ sum)) & 0x80000000u) flags |= 0x800u;
    return flags;
}

// 0x4a8ed0. cdecl, 2 stack arguments, returns adjusted object word.
uint32_t function_4a8ed0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t descriptor = arguments[1];
    // PMD +0 is mdisp, +4 is pdisp, +8 is vdisp.
    uint32_t value = object + run.get(descriptor);
    uint32_t displacement = run.get(descriptor + 4u);
    if (s32(displacement) >= 0) {
        uint32_t table = run.get(object + displacement);
        uint32_t offset = run.get(descriptor + 8u);
        uint32_t adjustment = run.get(table + offset);
        value += adjustment + displacement;
    }
    return value;
}

// 0x4a8ed0. Physical saved-ESI frame and full source register envelope.
uint32_t sourceFunction(Run &run) {
    auto &cpu = run.source();
    uint32_t entry = cpu.esp;
    cpu.edx = run.get(entry + 8u);
    cpu.esp -= 4u;
    run.put(cpu.esp, cpu.esi);
    cpu.esi = run.get(cpu.esp + 8u);
    cpu.ecx = run.get(cpu.edx);
    cpu.eax = cpu.esi;
    uint32_t left = cpu.eax;
    cpu.eax += cpu.ecx;
    cpu.eflags = addFlags(left, cpu.ecx, cpu.eax);
    cpu.ecx = run.get(cpu.edx + 4u);
    cpu.eflags = resultFlags(cpu.ecx);
    if (s32(cpu.ecx) >= 0) {
        cpu.esi = run.get(cpu.esi + cpu.ecx);
        cpu.edx = run.get(cpu.edx + 8u);
        cpu.edx = run.get(cpu.esi + cpu.edx);
        left = cpu.edx;
        cpu.edx += cpu.ecx;
        cpu.eflags = addFlags(left, cpu.ecx, cpu.edx);
        left = cpu.eax;
        cpu.eax += cpu.edx;
        cpu.eflags = addFlags(left, cpu.edx, cpu.eax);
    }
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 4u;
    return cpu.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4a8ed0:
        return function_4a8ed0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4a8ed0: return {2047u, 2047u, 1138u, 0u};
    default: return {};
    }
}
static bool optional_source(uint32_t function) {
    return function == 0x4a8ed0;
}

static uint32_t source_body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (function == 0x4a8ed0) return sourceFunction(run);
    run.fail(CLAW_FAULT_ABI, function);
}

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_crt_pmd_adjustment_entry, owned, source_contract,
                                  optional_source, body, source_body)
