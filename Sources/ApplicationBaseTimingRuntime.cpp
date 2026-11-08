// Application base record and timing helpers
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
    case 0x4b8240:
        return 0;
    case 0x4b8280:
        return 2;
    case 0x4b83a0:
        return 1;
    case 0x4b83d0:
        return 0;
    default:
        return -1;
    }
}

// Logical TEST/XOR flags, retaining the fixed flag bit.
void test_flags(Run &run, uint32_t value) {
    uint32_t low = value & 0xff;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    run.source().eflags = 2u | ((low & 1u) ? 0u : 4u) | (value == 0 ? 0x40u : 0u) | (value & 0x80000000u ? 0x80u : 0u);
}

void push(Run &run, uint32_t value) {
    run.source().esp -= 4;
    run.put(run.source().esp, value);
}

void clock_call(Run &run, uint32_t returnPC) {
    push(run, returnPC);
    auto child = run.source();
    child.eip = 0x546df0;
    run.source_call(0x546df0, 0, returnPC, child);
    run.source() = child;
}

// 0x4b83a0. Reset elapsed time and optionally invalidate the prior time.
uint32_t function_4b83a0(Run &run, uint32_t receiver, const uint32_t *) {
    auto &cpu = run.source();
    push(run, cpu.esi);
    cpu.esi = cpu.ecx;
    run.put(receiver + 0x20, 0);
    clock_call(run, 0x4b83b0);
    run.put(cpu.esi + 0x24, cpu.eax);
    cpu.eax = run.get(cpu.esp + 0x08);
    test_flags(run, cpu.eax);
    if (cpu.eax != 0) {
        run.put(cpu.esi + 0x18, 0xffffffffu);
    }
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 4;
    return cpu.eax;
}

// 0x4b83d0. Publish the physical tick and clear clock accumulators.
uint32_t function_4b83d0(Run &run, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    clock_call(run, 0x4b83d6);
    run.put(0x541328, cpu.eax);
    cpu.eax = 0;
    test_flags(run, cpu.eax);
    run.put(0x54132c, cpu.eax);
    run.put(0x541330, cpu.eax);
    return cpu.eax;
}

void reset_calls(Run &run, uint32_t firstReturn, uint32_t secondReturn) {
    auto &cpu = run.source();
    push(run, firstReturn);
    cpu.eip = 0x4b83a0;
    cpu.eax = function_4b83a0(run, cpu.ecx, nullptr);
    cpu.eip = run.get(cpu.esp);
    cpu.esp += 8;
    cpu.ecx = cpu.esi;
    push(run, secondReturn);
    cpu.eip = 0x4b83d0;
    cpu.eax = function_4b83d0(run, cpu.ecx, nullptr);
    cpu.eip = run.get(cpu.esp);
    cpu.esp += 4;
}

// 0x4b8240. Initialize the base record, then both timing domains.
uint32_t function_4b8240(Run &run, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    push(run, cpu.esi);
    cpu.esi = cpu.ecx;
    cpu.ecx = 1;
    cpu.eax = 0;
    test_flags(run, cpu.eax);
    run.put(cpu.esi + 0x10, cpu.ecx);
    run.put(cpu.esi + 0x14, cpu.ecx);
    push(run, cpu.ecx);
    cpu.ecx = cpu.esi;
    run.put(cpu.esi + 0x00, 0x50bf04);
    run.put(cpu.esi + 0x04, cpu.eax);
    run.put(cpu.esi + 0x08, cpu.eax);
    run.put(cpu.esi + 0x0c, cpu.eax);
    run.put(cpu.esi + 0x1c, cpu.eax);
    reset_calls(run, 0x4b826a, 0x4b8271);
    cpu.eax = cpu.esi;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 4;
    return cpu.eax;
}

// 0x4b8280. Bind a valid window record and initialize timing.
uint32_t function_4b8280(Run &run, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    cpu.eax = run.get(cpu.esp + 0x04);
    push(run, cpu.esi);
    test_flags(run, cpu.eax);
    cpu.esi = cpu.ecx;
    if (cpu.eax != 0) {
        cpu.ecx = run.get(cpu.eax + 0x04);
        test_flags(run, cpu.ecx);
        if (cpu.ecx != 0) {
            run.put(cpu.esi + 0x04, cpu.eax);
            cpu.eax = run.get(cpu.eax + 0x08);
            push(run, 1);
            cpu.ecx = cpu.esi;
            run.put(cpu.esi + 0x08, cpu.eax);
            run.put(cpu.esi + 0x1c, 0);
            reset_calls(run, 0x4b82b5, 0x4b82bc);
            cpu.eax = 0x64;
            cpu.esi = run.get(cpu.esp);
            cpu.esp += 4;
            run.put(0x541338, cpu.eax);
            run.put(0x541334, cpu.eax);
            cpu.eax = 1;
            return cpu.eax;
        }
        cpu.eax = 0;
        test_flags(run, cpu.eax);
    }
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 4;
    return cpu.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b8240:
        return function_4b8240(run, receiver, arguments);
    case 0x4b8280:
        return function_4b8280(run, receiver, arguments);
    case 0x4b83a0:
        return function_4b83a0(run, receiver, arguments);
    case 0x4b83d0:
        return function_4b83d0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4b8240: return {2047u, 2047u, 0u, 0u};
    case 0x4b8280: return {2047u, 2047u, 0u, 8u};
    case 0x4b83a0: return {2047u, 2047u, 0u, 4u};
    case 0x4b83d0: return {2047u, 2047u, 0u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_application_base_timing_entry, owned, source_contract, body)
