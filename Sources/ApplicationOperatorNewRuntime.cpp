// Application allocation and original handler retry
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
    case 0x4f63ec:
        return 1;
    default:
        return -1;
    }
}

uint32_t testFlags(uint32_t value) {
    uint32_t flags = 0x2;
    if (!value)
        flags |= 0x40;
    if (value & 0x80000000)
        flags |= 0x80;
    uint32_t parity = value & 0xff;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    if (!(parity & 1))
        flags |= 0x4;
    return flags;
}

uint32_t compareFlags(uint32_t left, uint32_t right) {
    uint32_t result = left - right;
    uint32_t flags = testFlags(result);
    if (left < right)
        flags |= 0x1;
    if ((left ^ right ^ result) & 0x10)
        flags |= 0x10;
    if (((left ^ right) & (left ^ result)) & 0x80000000)
        flags |= 0x800;
    return flags;
}

void invoke(Run &run, uint32_t target, uint32_t returnPC, bool argument) {
    auto &context = run.source();
    context.esp -= 0x4;
    run.put(context.esp, returnPC);
    auto child = context;
    child.eip = target;
    if (argument)
        run.source_call(target, 0, returnPC, child, {context.ebx});
    else
        run.source_call(target, 0, returnPC, child);
    context = child;
}

// 0x4f63ec. Physical saves and calls preserve the complete source CPU state.
uint32_t function_4f63ec(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.esp -= 0x4;
    run.put(context.esp, context.ebx);
    context.ebx = run.get(context.esp + 0x8);
    context.esp -= 0x4;
    run.put(context.esp, context.esi);
    context.esi = run.get(0x510020);
    context.esp -= 0x4;
    run.put(context.esp, context.edi);
    for (;;) {
        context.esp -= 0x4;
        run.put(context.esp, context.ebx);
        invoke(run, 0x4a48e0, 0x4f63ff, true);
        context.edi = context.eax;
        context.ecx = run.get(context.esp);
        context.esp += 0x4;
        context.eflags = testFlags(context.edi);
        if (context.edi)
            break;
        uint32_t sentinel = run.get(0x510020);
        context.eflags = compareFlags(context.esi, sentinel);
        if (context.esi == sentinel) {
            invoke(run, 0x5022b5, 0x4f6413, false);
            // Module thread state +0x28 is the selected new handler.
            context.esi = run.get(context.eax + 0x28);
        }
        context.eflags = testFlags(context.esi);
        if (!context.esi)
            break;
        context.esp -= 0x4;
        run.put(context.esp, context.ebx);
        invoke(run, context.esi, 0x4f641d, true);
        context.eflags = testFlags(context.eax);
        context.ecx = run.get(context.esp);
        context.esp += 0x4;
        if (!context.eax)
            break;
    }
    context.eax = context.edi;
    context.edi = run.get(context.esp);
    context.esp += 0x4;
    context.esi = run.get(context.esp);
    context.esp += 0x4;
    context.ebx = run.get(context.esp);
    context.esp += 0x4;
    return context.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4f63ec:
        return function_4f63ec(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4f63ec: return {2047u, 2047u, 0u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_application_operator_new_entry, owned, source_contract, body)
