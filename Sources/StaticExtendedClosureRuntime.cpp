// Static startup error reporting and next string thunk
//
// Recovered from the original disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4db4d0:
        return 3;
    case 0x50240a:
        return 0;
    default:
        return -1;
    }
}

uint32_t arithmetic(uint32_t left, uint32_t right, bool subtract, ClawSourceContext &cpu) {
    uint32_t value = subtract ? left - right : left + right;
    uint32_t flags = 2;
    uint32_t parity = value & 0xff;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    if (!(parity & 1)) flags |= 4;
    if (!value) flags |= 0x40;
    if (value & 0x80000000u) flags |= 0x80;
    if ((left ^ right ^ value) & 0x10) flags |= 0x10;
    if (subtract ? left < right : uint64_t(left) + right > 0xffffffffu) flags |= 1;
    if ((subtract ? (left ^ right) & (left ^ value) : ~(left ^ right) & (left ^ value)) & 0x80000000u) flags |= 0x800;
    cpu.eflags = flags;
    return value;
}

void logical(ClawSourceContext &cpu, uint32_t value) {
    arithmetic(value, 0, false, cpu);
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

void invoke(Run &run, ClawSourceContext &cpu, uint32_t target, uint32_t receiver, uint32_t pc,
            std::initializer_list<uint32_t> arguments, uint32_t popBytes) {
    push(run, cpu, pc);
    auto child = cpu;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = (target == 0x4dc3d0 || target == 0x4f2060) ? 0x472 : 0;
    child.eip = target;
    try {
        run.source_call(target, receiver, pc, child, arguments, 0, popBytes);
    } catch (...) {
        std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
}

// 0x4db4d0. Error manager: +0x00 callback, +0x08 status,
// +0x0c reporting mode, +0x14 message prefix.
uint32_t function_4db4d0(Run &run, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    cpu.esp = arithmetic(cpu.esp, 0xa0, true, cpu);
    push(run, cpu, cpu.ebx);
    cpu.ebx = cpu.ecx;
    push(run, cpu, cpu.esi);
    push(run, cpu, cpu.edi);
    arithmetic(run.get(cpu.ebx + 0x0c), 4, true, cpu);
    if (!(cpu.eflags & 0x40)) {
        cpu.eax = run.get(0x544d18);
        logical(cpu, cpu.eax);
        if (cpu.eax) {
            cpu.ecx = run.get(cpu.esp + 0xb0);
            push(run, cpu, cpu.ecx);
            cpu.ecx = cpu.ebx;
            invoke(run, cpu, 0x4dc3d0, cpu.ecx, 0x4db511, {run.get(cpu.esp)}, 4);
        } else {
            cpu.eax = 0xffffffff;
            logical(cpu, cpu.eax);
        }
        arithmetic(cpu.eax, 0xffffffff, true, cpu);
        if (cpu.eax == 0xffffffff) {
            cpu.eax = run.get(cpu.ebx + 0x0c);
            arithmetic(cpu.eax, 2, true, cpu);
            if (cpu.eax == 2) {
                cpu.edi = run.get(cpu.ebx + 0x14);
                cpu.ecx = 0xffffffff;
                logical(cpu, cpu.ecx);
                cpu.eax = 0;
                logical(cpu, cpu.eax);
                cpu.edx = cpu.esp + 0x0c;
                while (cpu.ecx) {
                    uint32_t byte = run.get8(cpu.edi);
                    ++cpu.edi;
                    --cpu.ecx;
                    arithmetic(0, byte, true, cpu);
                    if (!byte) break;
                }
                cpu.ecx = ~cpu.ecx;
                cpu.edi = arithmetic(cpu.edi, cpu.ecx, true, cpu);
                push(run, cpu, 0x4f);
                cpu.eax = cpu.ecx;
                cpu.esi = cpu.edi;
                cpu.edi = cpu.edx;
                cpu.edx = cpu.esp + 0x10;
                cpu.ecx >>= 2;
                while (cpu.ecx) {
                    run.put(cpu.edi, run.get(cpu.esi));
                    cpu.edi += 4;
                    cpu.esi += 4;
                    --cpu.ecx;
                }
                cpu.ecx = cpu.eax & 3;
                logical(cpu, cpu.ecx);
                while (cpu.ecx) {
                    run.put8(cpu.edi, run.get8(cpu.esi));
                    ++cpu.edi;
                    ++cpu.esi;
                    --cpu.ecx;
                }
                cpu.ecx = run.get(cpu.esp + 0xb8);
                push(run, cpu, cpu.ecx);
                push(run, cpu, cpu.edx);
                invoke(run, cpu, 0x4f2060, 0, 0x4db55b, {run.get(cpu.esp), run.get(cpu.esp + 0x04), run.get(cpu.esp + 0x08)}, 0);
                cpu.eax = run.get(cpu.esp + 0xc4);
                cpu.esp = arithmetic(cpu.esp, 0x0c, false, cpu);
                cpu.ecx = cpu.esp + 0x0c;
                push(run, cpu, cpu.eax);
                push(run, cpu, cpu.ecx);
                invoke(run, cpu, run.get(cpu.ebx), 0, 0x4db56d, {run.get(cpu.esp), run.get(cpu.esp + 0x04)}, 0);
                cpu.esp = arithmetic(cpu.esp, 8, false, cpu);
            } else {
                arithmetic(cpu.eax, 1, true, cpu);
                if (cpu.eax == 1) {
                    cpu.edx = (cpu.edx & 0xffff0000u) | run.get16(cpu.esp + 0xb8);
                    run.put16(cpu.ebx + 0x08, uint16_t(cpu.edx));
                }
            }
        } else {
            cpu.ebx = run.get(cpu.ebx + 0x0c);
            arithmetic(cpu.ebx, 2, true, cpu);
            if (cpu.ebx == 2) {
                cpu.ecx = run.get(cpu.esp + 0xb8);
                cpu.edx = run.get(cpu.esp + 0xb4);
                cpu.eax *= 3;
                push(run, cpu, cpu.ecx);
                push(run, cpu, cpu.edx);
                invoke(run, cpu, run.get(cpu.eax * 4 + 0x544b9c), 0, 0x4db5bb, {run.get(cpu.esp), run.get(cpu.esp + 0x04)}, 0);
                cpu.esp = arithmetic(cpu.esp, 8, false, cpu);
            } else {
                arithmetic(cpu.ebx, 1, true, cpu);
                if (cpu.ebx == 1) {
                    cpu.ecx = (cpu.ecx & 0xffff0000u) | run.get16(cpu.esp + 0xb8);
                    cpu.eax *= 3;
                    run.put16(cpu.eax * 4 + 0x544ba0, uint16_t(cpu.ecx));
                }
            }
        }
    } else {
        cpu.eax = (cpu.eax & 0xffff0000u) | run.get16(cpu.esp + 0xb8);
        run.put16(cpu.ebx + 0x08, uint16_t(cpu.eax));
    }
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
    cpu.ebx = pop(run, cpu);
    cpu.esp = arithmetic(cpu.esp, 0xa0, false, cpu);
    return cpu.eax;
}

// 0x50240a. Register the module-list string through the original constructor.
uint32_t function_50240a(Run &run, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    push(run, cpu, 0x52e2a0);
    cpu.ecx = 0x53eca4;
    invoke(run, cpu, 0x4f709b, cpu.ecx, 0x502419, {0x52e2a0}, 4);
    return cpu.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4db4d0:
        return function_4db4d0(run, receiver, arguments);
    case 0x50240a:
        return function_50240a(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4db4d0: return {2047u, 2047u, 1138u, 12u};
    case 0x50240a: return {2047u, 2047u, 0u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_static_extended_closure_entry, owned, source_contract, body)
