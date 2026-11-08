// Original MFC memory exception construction and nonreturning physical raise
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
    case 0x4f50fd:
        return 0;
    case 0x4a5690:
        return 2;
    default:
        return -1;
    }
}

// Arithmetic flags from the helper's SUB ESP,0x20.
uint32_t subtract_flags(uint32_t left, uint32_t right) {
    uint32_t value = left - right;
    uint32_t flags = 2u;
    flags |= left < right ? 1u : 0u;
    uint32_t low = value & 0xffu;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    flags |= (low & 1u) ? 0u : 4u;
    flags |= ((left ^ right ^ value) & 0x10u);
    flags |= value == 0 ? 0x40u : 0u;
    flags |= value & 0x80000000u ? 0x80u : 0u;
    flags |= ((left ^ right) & (left ^ value) & 0x80000000u) ? 0x800u : 0u;
    return flags;
}

// 0x4a5690. The physical import is the only nonreturning boundary.
uint32_t raise_memory(Run &run, uint32_t entry, uint32_t argument1, uint32_t argument2) {
    auto *cpu = run.host.sourceContext;
    if (cpu) {
        cpu->eflags = subtract_flags(entry, 0x20u);
        cpu->esp = entry - 0x20;
        cpu->eax = run.get(entry + 0x04);
        run.put(entry - 0x24, cpu->esi);
        run.put(entry - 0x28, cpu->edi);
        cpu->esp = entry - 0x28;
        cpu->ecx = 8;
        cpu->esi = 0x512720;
        cpu->edi = entry - 0x20;
    }
    for (uint32_t offset = 0; offset < 0x20; offset += 0x04) {
        run.put(entry - 0x20 + offset, run.get(0x512720 + offset));
        if (cpu) {
            cpu->esi += 0x04;
            cpu->edi += 0x04;
            --cpu->ecx;
        }
    }
    if (cpu) {
        cpu->ecx = run.get(entry + 0x08);
    }
    run.put(entry - 0x08, cpu ? cpu->eax : argument1);
    uint32_t count = run.get(entry - 0x10);
    uint32_t vector = entry - 0x0c;
    run.put(entry - 0x04, cpu ? cpu->ecx : argument2);
    uint32_t flags = run.get(entry - 0x1c);
    run.put(entry - 0x2c, vector);
    uint32_t code = run.get(entry - 0x20);
    run.put(entry - 0x30, count);
    run.put(entry - 0x34, flags);
    run.put(entry - 0x38, code);
    run.put(entry - 0x3c, 0x4a56cf);
    if (cpu) {
        cpu->eax = count;
        cpu->ecx = flags;
        cpu->edx = code;
        cpu->esp = entry - 0x3c;
        cpu->eip = 0x4a56c9;
    }
    run.stackPointer = entry - 0x3c;
    if (cpu) {
        auto physical = *cpu;
        physical.eip = 0x546958;
        physical.preserveMask = 0x472;
        run.source_call(0x546958, 0, 0x4a56cf, physical, {code, flags, count, vector}, 0, 0x10);
    } else {
        run.icall(0x546958, {code, flags, count, vector});
    }
    // These instructions are outside the supported nonreturning domain.
    if (cpu) {
        cpu->edi = run.get(entry - 0x28);
        cpu->esi = run.get(entry - 0x24);
        cpu->eflags = subtract_flags(entry - 0x20, 0xffffffe0u);
        cpu->esp = entry;
    }
    return count;
}

// 0x4f50fd. Keep the pointer cell and owned helper's real frame.
uint32_t function_4f50fd(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t entry = run.frame;
    auto *cpu = run.host.sourceContext;
    if (cpu) {
        run.put(entry - 0x04, cpu->ebp);
        cpu->ebp = entry - 0x04;
        // PUSH ECX reserves this cell; its data is overwritten below before
        // any read or physical callback in the valid bounded-stack domain.
        cpu->eax = entry - 0x08;
    }
    run.put(entry - 0x0c, 0x51eb68);
    run.put(entry - 0x10, entry - 0x08);
    run.put(entry - 0x08, 0x540748);
    run.put(entry - 0x14, 0x4f5116);
    if (cpu) {
        cpu->esp = entry - 0x14;
        cpu->eip = 0x4a5690;
    }
    uint32_t value = raise_memory(run, entry - 0x14, entry - 0x08, 0x51eb68);
    if (cpu) {
        cpu->ebp = run.get(entry - 0x04);
        cpu->esp = entry;
    }
    return value;
}

// 0x4a5690. stdcall2, with the wrapper macro owning normal RET8.
uint32_t function_4a5690(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return raise_memory(run, run.frame, arguments[0], arguments[1]);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4f50fd:
        return function_4f50fd(run, receiver, arguments);
    case 0x4a5690:
        return function_4a5690(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4f50fd: return {2047u, 2047u, 1138u, 0u};
    case 0x4a5690: return {2047u, 2047u, 1138u, 8u};
    default: return {};
    }
}
static bool source_optional(uint32_t function) {
    switch (function) {
    case 0x4f50fd: return true;
    case 0x4a5690: return true;
    default: return false;
    }
}
CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_mfc_memory_throw_entry, owned, source_contract, source_optional, body, body)
