// Synthetic two-mode entry. Source and ordinary bodies are explicit.
#include "ClawRuntime.hpp"
static int owned(uint32_t f) { return f == 0x401320 || f == 0x401330 ? 2 : -1; }
static bool optional(uint32_t f) { return f == 0x401320; }
static ClawSourceContract contract(uint32_t f) {
    return {0x7ff, 0x7ff, 0x472, f == 0x401330 ? 8u : 0u};
}
static uint32_t ordinary_body(claw::Run &, uint32_t, uint32_t, const uint32_t *a) { return a[0]; }
static uint32_t source_body(claw::Run &run, uint32_t, uint32_t, const uint32_t *a) {
    (void)run.source();
    return a[0];
}
CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_optional_source_entry, owned, contract, optional, ordinary_body, source_body)
