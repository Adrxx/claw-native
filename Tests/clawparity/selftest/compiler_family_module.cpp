// Independently authored native companion to the synthetic family fixture.
#include "ClawRuntime.hpp"

static bool owned(uint32_t function) {
    return function == 0x401000;
}

static void body(claw::Run &run, uint32_t, ClawCompilerContext &context) {
    const uint32_t frame = context.esp;
    run.put(frame - 4, context.eax);
    run.put(frame + 0x4, context.ebx);
    context.eax = run.get(frame);
    context.ebp = frame - 4;
    context.fsHead = context.ebp;
    context.esp = frame - 4;
    context.eip = context.continuation;
}

CLAW_COMPILER_MODULE_ENTRY(claw_compiler_family_entry, owned, body)
