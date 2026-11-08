// Synthetic source import and original optional-callee callers, no game bytes.
#include "ClawRuntime.hpp"
namespace {
int owned(uint32_t f) { return f == 0x401000 || f == 0x401020 || f == 0x401040 ? 0 : -1; }
ClawSourceContract contract(uint32_t) { return {0x7ff, 0x7ff, 0x472, 0}; }
bool optional(uint32_t f) { return f == 0x401040; }
uint32_t ordinary(claw::Run &run, uint32_t, uint32_t, const uint32_t *) {
    run.stackPointer = run.frame - 8;
    return run.call(0x401100, 0, {0x33});
}
uint32_t source(claw::Run &run, uint32_t f, uint32_t, const uint32_t *) {
    auto &s = run.source();
    if (f == 0x401020) s.eax = run.get(0x402000);
    ClawSourceContext child = s;
    child.esp -= 8;
    child.eip = f == 0x401040 ? 0x401100 : f == 0x401020 ? s.eax : 0x402000;
    const uint32_t pc = f == 0x401000 ? 0x401008 : f == 0x401020 ? 0x401029 : 0x401047;
    run.put(child.esp + 4, 0x33);
    run.put(child.esp, pc);
    uint32_t value = run.source_call(child.eip, 0, pc, child, {0x33}, 0, f == 0x401040 ? 0 : 4);
    std::memcpy(&s.eax, &child.eax, 11 * sizeof(uint32_t));
    if (f == 0x401040) s.esp += 4;
    return value;
}
}
CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_source_imports_entry, owned, contract, optional, ordinary, source)
