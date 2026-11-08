// Low Detail dormant scenery filter
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x46eff0:
        return 1;
    default:
        return -1;
    }
}


// 0x46eff0. Actor +0x6c points to its primary logic record; +0x10 of
// that record identifies the callback. Selected scenery receives hidden
// actor flag +0x08 bit 0x10000 and dormant-record flag +0x40 bit 1.
uint32_t filter(Run &run, uint32_t actor) {
    if (actor == 0)
        return 0;
    uint32_t logic = run.get(actor + 0x6c);
    if (logic == 0)
        return 0;
    uint32_t callback = run.get(logic + 0x10);
    if (callback != 0x461970 && callback != 0x4618e0 && callback != 0x461770 && callback != 0x4617d0)
        return 0;
    run.put(actor + 0x08, run.get(actor + 0x08) | 0x10000);
    run.put(actor + 0x40, run.get(actor + 0x40) | 1);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *arguments) {
    switch (function) {
    case 0x46eff0:
        return filter(run, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_low_detail_scenery_entry, owned, body)
