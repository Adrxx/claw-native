// Original extended static records and string range construction
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
    case 0x440f30:
        return 2;
    case 0x453cc0:
        return 0;
    case 0x453d00:
        return 0;
    case 0x45acb0:
        return 0;
    case 0x4f54ea:
        return 0;
    default:
        return -1;
    }
}

// Arithmetic flags from the original 32-bit instructions.
uint32_t logicalFlags(uint32_t value) {
    uint32_t low = value & 0xffu;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    return 2u | ((!value) ? 0x40u : 0u) | (value & 0x80000000u ? 0x80u : 0u) | ((low & 1u) ? 0u : 4u);
}
uint32_t addFlags(uint32_t left, uint32_t right) {
    uint32_t value = left + right;
    return logicalFlags(value) | (value < left ? 1u : 0u) | ((left ^ right ^ value) & 0x10u) | ((~(left ^ right) & (left ^ value) & 0x80000000u) ? 0x800u : 0u);
}
uint32_t decrementFlags(uint32_t value, uint32_t flags) {
    uint32_t result = value - 1u;
    return logicalFlags(result) | (flags & 1u) | ((value ^ 1u ^ result) & 0x10u) | (value == 0x80000000u ? 0x800u : 0u);
}

// 0x440f30. Full physical registration frame and original whole callees.
uint32_t function_440f30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    auto &parent = run.source();
    auto cpu = parent;
    const uint32_t entry = cpu.esp;
    run.put(entry - 0x04, 0xffffffffu);
    run.put(entry - 0x08, 0x506228);
    cpu.eax = cpu.fsHead;
    run.put(entry - 0x0c, cpu.eax);
    cpu.fsHead = entry - 0x0c;
    cpu.eax = run.get(entry + 0x08);
    run.put(entry - 0x14, cpu.ebx);
    cpu.ebx = cpu.ecx;
    run.put(entry - 0x18, cpu.esi);
    cpu.ecx = run.get(entry + 0x04);
    run.put(entry - 0x1c, 1);
    run.put(entry - 0x20, cpu.eax);
    run.put(entry - 0x24, cpu.ecx);
    run.put(entry - 0x28, 4);
    cpu.ecx = cpu.ebx;
    run.put(entry - 0x10, cpu.ebx);
    run.put(entry - 0x2c, 0x440f63);
    cpu.esp = entry - 0x2c;
    cpu.eip = 0x4dbb10;
    cpu.preserveMask = 0x472;
    run.source_call(0x4dbb10, cpu.ecx, 0x440f63, cpu, {4, arguments[0], arguments[1], 1}, 0, 16);
    cpu.esi = run.get(cpu.ebx + 0x1c); // Array backing.
    run.put(entry - 0x04, 0);
    cpu.eflags = logicalFlags(cpu.esi);
    run.put(cpu.ebx + 0x00, 0x50dbf4);
    if (cpu.esi) {
        cpu.eax = run.get(cpu.ebx + 0x20); // Element count.
        cpu.edx = cpu.eax;
        cpu.eflags = decrementFlags(cpu.eax, cpu.eflags);
        --cpu.eax;
        cpu.eflags = logicalFlags(cpu.edx);
        if (cpu.edx) {
            run.put(entry - 0x1c, cpu.edi);
            cpu.edi = cpu.eax + 1u;
            do {
                cpu.eflags = logicalFlags(cpu.esi);
                if (cpu.esi) {
                    cpu.ecx = cpu.esi;
                    run.put(entry - 0x20, 0x440f91);
                    cpu.esp = entry - 0x20;
                    cpu.eip = 0x4f6439;
                    run.source_call(0x4f6439, cpu.ecx, 0x440f91, cpu);
                }
                cpu.eflags = addFlags(cpu.esi, 4);
                cpu.esi += 4;
                cpu.eflags = decrementFlags(cpu.edi, cpu.eflags);
                --cpu.edi;
            } while (cpu.edi);
            cpu.edi = run.get(entry - 0x1c);
        }
    }
    cpu.ecx = run.get(entry - 0x0c);
    cpu.eax = cpu.ebx;
    cpu.esi = run.get(entry - 0x18);
    cpu.fsHead = cpu.ecx;
    cpu.ebx = run.get(entry - 0x14);
    cpu.eflags = addFlags(entry - 0x10, 0x10);
    cpu.esp = entry;
    std::memcpy(&parent.eax, &cpu.eax, 11 * sizeof(uint32_t));
    (void)receiver;
    return cpu.eax;
}

// 0x453cc0. Absolute coordinate record stores, preserving CPU state.
uint32_t function_453cc0(Run &run, uint32_t, const uint32_t *) {
    run.put(0x5379b8, 0xffffffd0);
    run.put(0x5379bc, 0xffffffd3);
    run.put(0x5379c0, 1);
    run.put(0x5379c4, 0xfffffff9);
    return run.host.sourceContext ? run.source().eax : 0;
}

// 0x453d00. Absolute coordinate record stores, preserving CPU state.
uint32_t function_453d00(Run &run, uint32_t, const uint32_t *) {
    run.put(0x5379a8, 0xffffff51);
    run.put(0x5379ac, 0xffffffea);
    run.put(0x5379b0, 0xfffffff3);
    run.put(0x5379b4, 9);
    return run.host.sourceContext ? run.source().eax : 0;
}

// 0x45acb0. Absolute coordinate record stores, preserving CPU state.
uint32_t function_45acb0(Run &run, uint32_t, const uint32_t *) {
    run.put(0x537b48, 5);
    run.put(0x537b4c, 0x1c5);
    run.put(0x537b50, 0x27b);
    run.put(0x537b54, 0x1de);
    return run.host.sourceContext ? run.source().eax : 0;
}

// 0x4f54ea. Vtable at +0, zero record fields at +4,+16,+12,+8.
uint32_t function_4f54ea(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x00, 0x51079c);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x08, 0);
    if (run.host.sourceContext) {
        run.source().ecx = 0;
        run.source().eflags = 0x46;
    }
    return receiver;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x440f30:
        return function_440f30(run, receiver, arguments);
    case 0x453cc0:
        return function_453cc0(run, receiver, arguments);
    case 0x453d00:
        return function_453d00(run, receiver, arguments);
    case 0x45acb0:
        return function_45acb0(run, receiver, arguments);
    case 0x4f54ea:
        return function_4f54ea(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x440f30: return {2047u, 2047u, 1138u, 8u};
    case 0x453cc0: return {2047u, 2047u, 1138u, 0u};
    case 0x453d00: return {2047u, 2047u, 1138u, 0u};
    case 0x45acb0: return {2047u, 2047u, 1138u, 0u};
    case 0x4f54ea: return {2047u, 2047u, 1138u, 0u};
    default: return {};
    }
}
static bool source_optional(uint32_t function) {
    switch (function) {
    case 0x440f30: return false;
    case 0x453cc0: return true;
    case 0x453d00: return true;
    case 0x45acb0: return true;
    case 0x4f54ea: return true;
    default: return false;
    }
}
CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_static_extended_records_entry, owned, source_contract, source_optional, body, body)
