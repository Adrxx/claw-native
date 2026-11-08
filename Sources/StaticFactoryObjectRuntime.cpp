// Original static factory object construction
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
    case 0x440ee0:
        return 1;
    case 0x4dc280:
        return 2;
    case 0x4dc200:
        return 2;
    default:
        return -1;
    }
}

// Arithmetic flags from the physical ADD ESP, 0x10 at 0x4dc2ed.
uint32_t add_stack_flags(uint32_t left, uint32_t result) {
    uint32_t flags = 2;
    if (result < left) flags |= 0x1;
    uint32_t low = result & 0xff;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    if (!(low & 1)) flags |= 0x4;
    if ((left ^ 0x10 ^ result) & 0x10) flags |= 0x10;
    if (!result) flags |= 0x40;
    if (result & 0x80000000) flags |= 0x80;
    if ((~(left ^ 0x10) & (left ^ result)) & 0x80000000) flags |= 0x800;
    return flags;
}

// 0x4dc200: leaf nested record constructor.
uint32_t function_4dc200(Run &run, uint32_t receiver, const uint32_t *arguments) {
    auto &cpu = run.source();
    cpu.edx = (cpu.edx & 0xffff0000) | (arguments[0] & 0xffff);
    cpu.eax = receiver;
    cpu.ecx = arguments[1];
    // Factory pointer, tag, reserved word, and record vtable.
    run.put(receiver + 0x4, cpu.ecx);
    run.put16(receiver + 0x8, uint16_t(cpu.edx));
    run.put(receiver + 0xc, 0);
    run.put(receiver + 0x0, 0x513e38);
    return cpu.eax;
}

// 0x4dc280: inline FS registration and base/nested construction.
uint32_t function_4dc280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    auto &cpu = run.source();
    const uint32_t entry = cpu.esp;
    run.put(entry - 0x4, 0xffffffff);
    run.put(entry - 0x8, 0x50a098);
    cpu.eax = cpu.fsHead;
    run.put(entry - 0xc, cpu.eax);
    cpu.fsHead = entry - 0xc;
    run.put(entry - 0x10, cpu.ecx);
    run.put(entry - 0x14, cpu.esi);
    run.put(entry - 0x18, cpu.edi);
    cpu.esi = cpu.ecx;
    run.put(entry - 0x1c, 0x544b80);
    run.put(entry - 0x10, cpu.esi);
    run.put(entry - 0x20, 0x4dc2a8);
    cpu.esp = entry - 0x20;
    cpu.eip = 0x4db620;
    auto child = cpu;
    run.source_call(0x4db620, receiver, 0x4dc2a8, child, {0x544b80}, 0, 4);
    cpu = child;
    cpu.eax = run.get(cpu.esp + 0x1c);
    cpu.ecx = run.get(cpu.esp + 0x20);
    cpu.edi = cpu.esi + 0x8;
    run.put(entry - 0x1c, cpu.eax);
    run.put(entry - 0x20, cpu.ecx);
    cpu.ecx = cpu.edi;
    run.put(entry - 0x4, 0);
    run.put(entry - 0x24, 0x4dc2c4);
    cpu.esp = entry - 0x24;
    cpu.eip = 0x4dc200;
    const uint32_t nestedArguments[] = {arguments[1], arguments[0]};
    function_4dc200(run, cpu.ecx, nestedArguments);
    cpu.eip = run.get(cpu.esp);
    cpu.esp += 0xc;
    cpu.ecx = run.get(cpu.esp + 0xc);
    run.put(cpu.edi + 0x0, 0x50db94);
    run.put(cpu.esi + 0x18, 0);
    run.put(cpu.esi + 0x28, 0);
    run.put(cpu.esi + 0x0, 0x50db9c);
    cpu.eax = cpu.esi;
    cpu.edi = run.get(cpu.esp);
    cpu.esp += 0x4;
    cpu.fsHead = cpu.ecx;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 0x4;
    const uint32_t beforeAdd = cpu.esp;
    cpu.esp += 0x10;
    cpu.eflags = add_stack_flags(beforeAdd, cpu.esp);
    return cpu.eax;
}

// 0x440ee0: static factory with opaque factory pointer 0x4c96b0.
uint32_t function_440ee0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    auto &cpu = run.source();
    const uint32_t entry = cpu.esp;
    cpu.eax = run.get(entry + 0x4);
    run.put(entry - 0x4, cpu.esi);
    run.put(entry - 0x8, cpu.eax);
    cpu.esi = cpu.ecx;
    run.put(entry - 0xc, 0x4c96b0);
    run.put(entry - 0x10, 0x440ef2);
    cpu.esp = entry - 0x10;
    cpu.eip = 0x4dc280;
    const uint32_t nestedArguments[] = {0x4c96b0, arguments[0]};
    function_4dc280(run, receiver, nestedArguments);
    cpu.eip = run.get(cpu.esp);
    cpu.esp += 0xc;
    run.put(cpu.esi + 0x0, 0x50dbec);
    run.put(cpu.esi + 0x8, 0x50dbe4);
    cpu.eax = cpu.esi;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 0x4;
    return cpu.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x440ee0:
        return function_440ee0(run, receiver, arguments);
    case 0x4dc280:
        return function_4dc280(run, receiver, arguments);
    case 0x4dc200:
        return function_4dc200(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x440ee0: return {2047u, 2047u, 1138u, 4u};
    case 0x4dc280: return {2047u, 2047u, 1138u, 8u};
    case 0x4dc200: return {2047u, 2047u, 1138u, 8u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_static_factory_object_entry, owned, source_contract, body)
