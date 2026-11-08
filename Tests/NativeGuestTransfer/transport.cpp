// Synthetic transport scaffold, not a recovered singleton implementation.
#include "ClawRuntime.hpp"
namespace {
uint32_t continued = 0, destroyed = 0;
struct Lifetime { ~Lifetime() { ++destroyed; } };
int owns(uint32_t f) { return f == 0x503420 ? 0 : -1; }
ClawSourceContract contract(uint32_t) { return {0x7ff, 0x7ff, 0x472, 0}; }
uint32_t body(claw::Run &run, uint32_t, uint32_t, const uint32_t *) {
    Lifetime lifetime;
    auto child = run.source();
    child.esp -= 4;
    child.eip = 0x502369;
    run.put(child.esp, 0x503450);
    auto value = run.source_call(0x502369, 0, 0x503450, child);
    ++continued;
    return value;
}
}
CLAW_GUEST_SOURCE_MODULE_ENTRY(transport_entry, owns, contract, body)
extern "C" void transport_reset() { continued = destroyed = 0; }
extern "C" uint32_t transport_continued() { return continued; }
extern "C" uint32_t transport_destroyed() { return destroyed; }
// Intentionally lacks the opt-in entry contract; a guest graph must reject it.
CLAW_SOURCE_MODULE_ENTRY(transport_unsupported_entry, owns, contract, body)

// A synthetic parent/child mask crossing, independent of recovered root code.
namespace {
int header_owns(uint32_t f) { return f == 0x503420 ? 1 : -1; }
ClawSourceContract zero_header(uint32_t) { return {0x7ff, 0x7ff, 0, 4}; }
ClawSourceContract nonzero_header(uint32_t) { return {0x7ff, 0x7ff, 0x400, 4}; }
uint32_t header_body(claw::Run &run, uint32_t, uint32_t, const uint32_t *) {
    auto &parent = run.source();
    auto child = parent;
    child.preserveMask = 0x472;
    child.esp -= 4;
    child.eip = 0x502369;
    run.put(child.esp, 0x503450);
    auto value = run.source_call(0x502369, 0, 0x503450, child);
    std::memcpy(&parent.eax, &child.eax, 11 * sizeof(uint32_t));
    return value;
}
}
CLAW_GUEST_SOURCE_MODULE_ENTRY(transport_zero_header_entry, header_owns, zero_header, header_body)
CLAW_GUEST_SOURCE_MODULE_ENTRY(transport_nonzero_header_entry, header_owns, nonzero_header, header_body)
