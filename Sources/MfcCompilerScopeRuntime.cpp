// Whole original compiler scope registration. The explicit compiler context
// carries source registers, FS head and genuine continuation; ordinary entries
// and native safety faults retain their separate contracts.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
bool owned(uint32_t function) { return function == 0x4a48c0; }
void function_4a48c0(Run &run, ClawCompilerContext &context) {
    uint32_t frame = context.esp;
    uint32_t handler = context.eax;
    uint32_t oldBase = context.ebp;
    run.put(frame - 4, 0xffffffffu);
    run.put(frame - 8, handler);
    run.put(frame - 12, context.fsHead);
    context.fsHead = frame - 12;
    uint32_t continuation = run.get(frame);
    context.eax = continuation;
    run.put(frame, oldBase);
    context.ebp = frame;
    run.put(frame - 16, continuation);
    context.esp = frame - 12;
    context.eip = continuation;
}
void body(Run &run, uint32_t function, ClawCompilerContext &context) {
    if (function != 0x4a48c0)
        run.fail(CLAW_FAULT_ABI, function);
    function_4a48c0(run, context);
}
}
CLAW_COMPILER_MODULE_ENTRY(claw_mfc_compiler_scope_entry, owned, body)
