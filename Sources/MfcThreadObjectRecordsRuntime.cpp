#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x4f6a9a:
    case 0x50354d:
    case 0x503510:
        return 0;
    default:
        return -1;
    }
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
void zeroFlags(ClawSourceContext &cpu) {
    cpu.eflags = 0x46;
}

// 0x4f6a9a: base vtable and seven initial record words.
uint32_t function_4f6a9a(Run &run, uint32_t receiver, const uint32_t *) {
    auto &cpu = run.source();
    cpu.eax = receiver;
    push(run, cpu, 1);
    cpu.ecx = pop(run, cpu);
    cpu.edx = 0;
    zeroFlags(cpu);
    run.put(cpu.eax, 0x510174);
    run.put(cpu.eax + 4, cpu.ecx);
    run.put(cpu.eax + 8, cpu.edx);
    run.put(cpu.eax + 0xc, cpu.edx);
    run.put(cpu.eax + 0x10, cpu.edx);
    run.put(cpu.eax + 0x14, cpu.ecx);
    run.put(cpu.eax + 0x18, cpu.edx);
    return cpu.eax;
}

// 0x50354d: cursor POINT at +0x5c, leaving unrelated record holes intact.
uint32_t function_50354d(Run &run, uint32_t receiver, const uint32_t *) {
    auto &cpu = run.source();
    push(run, cpu, cpu.esi);
    cpu.esi = receiver;
    push(run, cpu, cpu.edi);
    cpu.edi = 0;
    zeroFlags(cpu);
    cpu.eax = cpu.esi + 0x5c;
    run.put(cpu.esi + 0x1c, cpu.edi);
    push(run, cpu, cpu.eax);
    run.put(cpu.esi + 0x20, cpu.edi);
    run.put(cpu.esi + 0x28, cpu.edi);
    run.put(cpu.esi + 0x2c, cpu.edi);
    run.put(cpu.esi + 0x34, cpu.edi);
    run.put(cpu.esi + 0x64, cpu.edi);
    push(run, cpu, 0x50356f);
    auto child = cpu;
    child.eip = 0x546cd0;
    run.source_call(0x546cd0, 0, 0x50356f, child, {cpu.eax}, 0, 4);
    cpu = child;
    run.put(cpu.esi + 0x58, cpu.edi);
    run.put(cpu.esi + 0x54, cpu.edi);
    run.put(cpu.esi + 0x24, 1);
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
    return cpu.eax;
}

// 0x503510: whole original compiler helper establishes the registration frame.
uint32_t function_503510(Run &run, uint32_t receiver, const uint32_t *) {
    (void)receiver;
    auto &cpu = run.source();
    cpu.eax = 0x508ca4;
    push(run, cpu, 0x50351a);
    ClawCompilerContext helper{};
    helper.size = sizeof(helper);
    helper.version = CLAW_CONTEXT_VERSION;
    helper.inputMask = 0x7ff;
    helper.outputMask = 0x7ff;
    helper.continuation = 0x50351a;
    std::memcpy(&helper.eax, &cpu.eax, 11 * sizeof(uint32_t));
    helper.eip = 0x4a48c0;
    run.context_call(0x4a48c0, helper);
    std::memcpy(&cpu.eax, &helper.eax, 11 * sizeof(uint32_t));
    push(run, cpu, cpu.ecx);
    push(run, cpu, cpu.esi);
    cpu.esi = cpu.ecx;
    run.put(cpu.ebp - 0x10, cpu.esi);
    push(run, cpu, 0x503526);
    cpu.eip = 0x4f6a9a;
    function_4f6a9a(run, cpu.ecx, nullptr);
    cpu.eip = pop(run, cpu);
    cpu.eax = 0;
    zeroFlags(cpu);
    cpu.ecx = cpu.esi;
    run.put(cpu.ebp - 4, cpu.eax);
    run.put(cpu.esi, 0x511a94);
    run.put(cpu.esi + 0x4c, cpu.eax);
    run.put(cpu.esi + 0x50, cpu.eax);
    push(run, cpu, 0x50353e);
    cpu.eip = 0x50354d;
    function_50354d(run, cpu.ecx, nullptr);
    cpu.eip = pop(run, cpu);
    cpu.ecx = run.get(cpu.ebp - 0xc);
    cpu.eax = cpu.esi;
    cpu.fsHead = cpu.ecx;
    cpu.esi = pop(run, cpu);
    cpu.esp = cpu.ebp;
    cpu.ebp = pop(run, cpu);
    return cpu.eax;
}

uint32_t ordinary_body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *) {
    if (function == 0x4f6a9a) {
        run.put(receiver, 0x510174);
        run.put(receiver + 4, 1);
        run.put(receiver + 8, 0);
        run.put(receiver + 0xc, 0);
        run.put(receiver + 0x10, 0);
        run.put(receiver + 0x14, 1);
        run.put(receiver + 0x18, 0);
        return receiver;
    }
    if (function == 0x50354d) {
        run.put(receiver + 0x1c, 0);
        run.put(receiver + 0x20, 0);
        run.put(receiver + 0x28, 0);
        run.put(receiver + 0x2c, 0);
        run.put(receiver + 0x34, 0);
        run.put(receiver + 0x64, 0);
        run.stackPointer = run.automatic(-16);
        uint32_t result = run.icall(0x546cd0, {receiver + 0x5c});
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x54, 0);
        run.put(receiver + 0x24, 1);
        return result;
    }
    run.fail(CLAW_FAULT_ABI, function);
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4f6a9a: return function_4f6a9a(run, receiver, arguments);
    case 0x50354d: return function_50354d(run, receiver, arguments);
    case 0x503510: return function_503510(run, receiver, arguments);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
ClawSourceContract source_contract(uint32_t function) {
    return owned(function) >= 0 ? ClawSourceContract{0x7ff, 0x7ff, 0x472, 0} : ClawSourceContract{};
}
bool optional(uint32_t function) {
    return function == 0x4f6a9a || function == 0x50354d;
}
}
CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_mfc_thread_object_records_entry, owned, source_contract, optional, ordinary_body, body)
