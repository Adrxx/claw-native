// Independently authored synthetic ordinary source caller; no game translation.
#include "ClawRuntime.hpp"

static int owned(uint32_t f) {
    if (f == 0x401000 || f == 0x401300 || f == 0x401340 || f == 0x401360 || f == 0x401370 || f == 0x401380 || f == 0x4013a0) return 0;
    if (f == 0x401320 || f == 0x401330) return 2;
    return -1;
}
static ClawSourceContract contract(uint32_t f) {
    if (f == 0x4013a0) return {};
    if (f == 0x401370) return {0x7ff, 0x5f3, 0x472, 0};
    if (f == 0x401340) return {CLAW_SOURCE_INPUT_REQUIRED | CLAW_CONTEXT_EDX,
        CLAW_SOURCE_OUTPUT_REQUIRED | CLAW_CONTEXT_ECX, CLAW_CONTEXT_FS_HEAD, 0};
    return {CLAW_CONTEXT_ALL, CLAW_CONTEXT_ALL, CLAW_SOURCE_PRESERVABLE, f == 0x401330 ? 8u : 0u};
}
static uint32_t body(claw::Run &run, uint32_t function, uint32_t, const uint32_t *arguments) {
    if (function == 0x4013a0) return 42;
    auto &s = run.source();
    if (function == 0x401340) {
        // ECX is undeclared input/output-selected. EDX input-selected/output-unselected.
        s.ecx = s.eax + s.ecx + s.ebx;
        s.edx += 1;
        return s.esi + s.edi;
    }
    if (function == 0x401360 || function == 0x401380) {
        ClawSourceContext child = s;
        child.esp -= 8;
        child.eip = function == 0x401360 ? 0x401240 : 0x401260;
        run.put(child.esp + 4, 0x33);
        run.put(child.esp, function + 7);
        auto value = run.source_call(child.eip, 0, function + 7, child, {0x33});
        std::memcpy(&s.eax, &child.eax, 11 * sizeof(uint32_t));
        s.esp += 4;
        return value;
    }
    if (function == 0x401300) return s.eax;
    if (function == 0x401320 || function == 0x401330) return arguments[0];
    s.esp -= 4;
    run.put(s.esp, s.ebp);
    s.ebp = s.esp;
    ClawCompilerContext helper{};
    helper.size = sizeof(helper);
    helper.version = 1;
    helper.inputMask = helper.outputMask = CLAW_CONTEXT_ALL;
    std::memcpy(&helper.eax, &s.eax, 11 * sizeof(uint32_t));
    helper.esp -= 4;
    helper.eip = 0x401100;
    helper.continuation = 0x401008;
    run.put(helper.esp, helper.continuation);
    run.context_call(helper.eip, helper);
    std::memcpy(&s.eax, &helper.eax, 11 * sizeof(uint32_t));
    ClawSourceContext child = s;
    child.esp -= 8;
    child.eip = 0x401200;
    run.put(child.esp + 4, 0x33);
    run.put(child.esp, 0x40100f);
    uint32_t value = run.source_call(child.eip, 0, 0x40100f, child, {0x33});
    std::memcpy(&s.eax, &child.eax, 11 * sizeof(uint32_t));
    s.esp += 4;
    s.esp = s.ebp;
    s.ebp = run.get(s.esp);
    s.esp += 4;
    s.fsHead = run.get(s.esp);
    s.esp += 4;
    s.ebp = run.get(s.esp);
    s.esp += 4;
    return value;
}
CLAW_SOURCE_MODULE_ENTRY(claw_source_context_selftest_entry, owned, contract, body)

extern "C" uint32_t claw_source_validate(ClawHost *host, ClawSourceContext *source, uint32_t pc) {
    try { claw::Run run(*host); run.validate_source(*source, 0x401000, pc); return 1; }
    catch (claw::Failure &) { return 0; }
}
extern "C" uint32_t claw_source_call_test(ClawHost *host, ClawSourceContext *source, uint32_t pc, uint32_t pops) {
    try { claw::Run run(*host); run.source_call(source->eip, 0, pc, *source, {0x33}, 0, pops); return 1; }
    catch (claw::Failure &) { return 0; }
}
