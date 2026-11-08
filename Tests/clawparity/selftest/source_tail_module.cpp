// Synthetic direct-JMP callers; no game bytes or platform code.
#include "ClawRuntime.hpp"
namespace {
int owned(uint32_t function) {
    return function == 0x401000 || function == 0x401020 || function == 0x401040 || function == 0x401060 || function == 0x401080 || function == 0x4010a0 ? 0 : -1;
}
ClawSourceContract contract(uint32_t) { return {0x7ff, 0x7ff, 0x472, 0}; }
uint32_t body(claw::Run &run, uint32_t function, uint32_t, const uint32_t *) {
    auto &s = run.source();
    uint32_t target = 0x401100;
    if (function == 0x401020) { s.ecx = 0x12345678; target = 0x401140; }
    if (function == 0x401040) { s.eax = 0x87654321; target = 0x401180; }
    if (function == 0x401060) target = 0x4011c0;
    if (function == 0x401080) target = 0x401240;
    if (function == 0x4010a0) {
#ifndef CLAW_SELFTEST_SKIP_EMPTY_CALL
        ClawSourceContext constructor = s;
        constructor.eip = 0x401280; constructor.esp -= 4; constructor.preserveMask = 0x400;
        run.put(constructor.esp, 0x4010a5);
        run.source_call(0x401280, 0, 0x4010a5, constructor);
        std::memcpy(&s.eax, &constructor.eax, 11 * sizeof(uint32_t));
#endif
        target = 0x4012a0;
    }
    const uint32_t site = function + (function == 0x401020 || function == 0x401040 || function == 0x4010a0 ? 5 : 0);
    s.eip = site;
    ClawSourceContext child = s;
    child.eip = target;
    child.preserveMask = 0x400;
    run.source_tail(target, function == 0x401020 ? s.ecx : 0, site, child);
}
}
CLAW_SOURCE_MODULE_ENTRY(claw_source_tail_selftest_entry, owned, contract, body)
