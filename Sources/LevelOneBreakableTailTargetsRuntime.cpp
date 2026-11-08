// Level 1 breakable tail-jump bodies
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x433fb0:
        return 0;
    case 0x433f30:
        return 0;
    default:
        return -1;
    }
}

// 0x433fb0. Fields: +0x58 double, +0x70 double, +0xa0 double, +0xc8 flag,
// +0x12c state object (+0x08 flags), +0x400 linked object, +0x404 and +0x40c ints.
uint32_t function_433fb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0xc8, 0);
    uint32_t state = run.get(receiver + 0x12c);
    uint32_t flags = run.get(state + 0x08);
    flags = flags | 2;
    run.put(state + 0x08, flags);
    if (run.get(receiver + 0x404) == 0) {
        run.putd(receiver + 0xa0, double(run.gets(receiver + 0x40c)));
    }
    uint32_t linked = run.get(receiver + 0x400);
    if (linked != 0) {
        double value = run.getd(receiver + 0x70) - run.getd(0x50c838);
        run.putd(linked + 0xa0, value);
    }
    double left = run.getd(receiver + 0x70);
    double right = run.getd(receiver + 0xa0);
    // fcomp then test C3: set for equal or unordered.
    bool equalOrUnordered = !(left < right) && !(left > right);
    if (equalOrUnordered) {
        double speed = run.getd(receiver + 0x58);
        double limit = run.getd(0x50c840);
        if (speed > limit) {
            double scaled = run.getd(receiver + 0x58) * run.getd(0x50c848);
            run.putd(receiver + 0x58, scaled);
            return 0;
        }
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x5c, 0);
        run.put(receiver + 0xc8, 1);
        uint32_t state2 = run.get(receiver + 0x12c);
        uint32_t flags2 = run.get(state2 + 0x08);
        flags2 = flags2 & 0xfffffffd;
        run.put(state2 + 0x08, flags2);
    }
    return 0;
}

// 0x433f30. Calls 0x4c82a0 on the state object's +0x188 member with the global
// at 0x5430c4, then sets flag 0x10000 when +0x1a4 is set and +0x19c is clear.
uint32_t function_433f30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t global = run.get(0x5430c4);
    uint32_t state = run.get(receiver + 0x12c);
    run.call(0x4c82a0, state + 0x188, {global});
    uint32_t state2 = run.get(receiver + 0x12c);
    if (run.get(state2 + 0x1a4) != 0) {
        if (run.get(state2 + 0x19c) == 0) {
            uint32_t flags = run.get(state2 + 0x08);
            flags = flags | 0x10000;
            run.put(state2 + 0x08, flags);
        }
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x433fb0:
        return function_433fb0(run, receiver, arguments);
    case 0x433f30:
        return function_433f30(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_breakable_tail_targets_entry, owned, body)
