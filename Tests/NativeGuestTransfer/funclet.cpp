// Transport-only catch fixture. Whole-singleton recovery is admitted separately.
#include "ClawRuntime.hpp"
namespace {
uint32_t entered = 0, continued = 0, destroyed = 0;
struct Lifetime { ~Lifetime() { ++destroyed; } };
void catch_body(claw::Run &run, const ClawGuestEHInvocation &) {
    Lifetime lifetime;
    ++entered;
    auto &cpu = run.source();
    cpu.esp -= 4;
    run.put(cpu.esp, 16);
    auto child = cpu;
    child.esp -= 4;
    child.eip = 0x502f05;
    run.put(child.esp, 0x50345b);
    run.source_call(0x502f05, 0, 0x50345b, child, {16}, 0, 4);
    cpu = child;
    cpu.esp -= 4;
    run.put(cpu.esp, 0);
    cpu.esp -= 4;
    run.put(cpu.esp, 0);
    child = cpu;
    child.esp -= 4;
    child.eip = 0x4a5690;
    run.put(child.esp, 0x503464);
    run.source_call(0x4a5690, 0, 0x503464, child, {0, 0}, 0, 8);
    ++continued;
}
void incorrect_return(claw::Run &, const ClawGuestEHInvocation &) { ++continued; }
}
CLAW_GUEST_FUNCLET_ENTRY(transport_catch, catch_body)
CLAW_GUEST_FUNCLET_ENTRY(transport_returning_catch, incorrect_return)
extern "C" void catch_reset() { entered = continued = destroyed = 0; }
extern "C" uint32_t catch_entered() { return entered; }
extern "C" uint32_t catch_continued() { return continued; }
extern "C" uint32_t catch_destroyed() { return destroyed; }
