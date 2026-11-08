// Independent synthetic dynamic callback transport; no game instructions.
#include "ClawRuntime.hpp"
namespace {
int owned(uint32_t f) { return f == 0x401000 || f == 0x401040 ? 0 : -1; }
ClawSourceContract contract(uint32_t) { return {0x7ff, 0x7ff, 0x472, 0}; }
uint32_t body(claw::Run &run, uint32_t f, uint32_t, const uint32_t *) {
    auto &s = run.source();
    ClawSourceContext child = s;
    if (f == 0x401040) {
        child.eip = 0x401100;
        child.esp -= 4;
        run.put(child.esp, 0x401045);
        run.source_call(child.eip, 0, 0x401045, child);
    } else {
        s.eax = run.get(0x402000);
        child = s;
        child.eip = s.eax;
        child.esp -= 12;
        const auto pointer = run.get(0x402004);
        run.put(child.esp + 8, pointer);
        run.put(child.esp + 4, 0x33);
        run.put(child.esp, 0x40100f);
        run.source_call(child.eip, 0, 0x40100f, child, {0x33, pointer});
        child.esp += 8;
    }
    std::memcpy(&s.eax, &child.eax, 11 * sizeof(uint32_t));
    return s.eax;
}
}
CLAW_SOURCE_MODULE_ENTRY(claw_source_fixtures_entry, owned, contract, body)
