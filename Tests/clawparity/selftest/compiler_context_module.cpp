// Synthetic transport consumer; no original compiler-helper implementation.
#include "ClawRuntime.hpp"

static bool owns(uint32_t function) { return function == 0x401000; }

static void body(claw::Run &run, uint32_t, ClawCompilerContext &context) {
    const uint32_t continuation = context.continuation;
    ClawCompilerContext child = context;
    child.eip = 0x401100;
    child.esp -= 4;
    child.continuation = 0x401005;
    run.put(child.esp, child.continuation);
    run.context_call(child.eip, child);
    context = child;
    context.continuation = continuation;
    // The ordinary bridge must inherit the FS head produced by the child.
    run.stackPointer = context.esp - 4;
    context.eax = run.call(0x401180, 0);
    context.eax = run.call_x87(0x4011a0, 0, 0.0);
    context.eip = continuation;
}
CLAW_COMPILER_MODULE_ENTRY(claw_compiler_context_selftest, owns, body)

extern "C" uint32_t claw_compiler_context_validate(ClawHost *host, ClawCompilerContext *context,
                                                 uint32_t returned) {
    try {
        claw::Run run(*host);
        run.validate_context(*context, 0x401000, returned != 0);
        return 1;
    } catch (claw::Failure &) {
        return 0;
    }
}

extern "C" uint32_t claw_compiler_context_call(ClawHost *host, ClawCompilerContext *context) {
    try {
        claw::Run run(*host);
        run.context_call(0x401100, *context);
        return 1;
    } catch (claw::Failure &) {
        return 0;
    }
}

// A register value grants no memory access. This exercises the same checked
// dereference that an owned native body would use with an opaque EBP.
extern "C" uint32_t claw_compiler_context_dereference(ClawHost *host, ClawCompilerContext *context) {
    try {
        claw::Run run(*host);
        run.put(context->ebp - 4, context->eax);
        return 1;
    } catch (claw::Failure &) {
        return 0;
    }
}
