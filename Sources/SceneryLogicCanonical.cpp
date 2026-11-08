// Original scenery callbacks
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x461730:
        return 1;
    case 0x461750:
        return 1;
    case 0x461770:
        return 1;
    case 0x4617d0:
        return 1;
    case 0x461830:
        return 1;
    case 0x461870:
        return 1;
    case 0x4618e0:
        return 1;
    case 0x461970:
        return 1;
    default:
        return -1;
    }
}

// Actor fields: flags +0x08, depth +0x64, logic pointer +0x6c,
// animation state +0x188 and animation identity +0x190.
// Logic +0x1c is its initialization state. Settings +0x124 enables candy.
void initialize(Run &run, uint32_t actor, uint32_t depth, bool animated, bool settings) {
    const uint32_t logic = run.get(actor + 0x6c);
    if (run.get(logic + 0x1c) != 0) {
        if (animated)
            run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
        return;
    }
    run.put(actor + 0x08, run.get(actor + 0x08) | 1u);
    run.put(logic + 0x1c, 5u);
    if (animated && run.get(actor + 0x190) == 0)
        run.call(0x4c79e0, actor, {0x5240d8, 0});
    if (run.get(actor + 0x64) == 0) {
        const uint32_t flags = run.get(actor + 0x08);
        run.put(actor + 0x64, depth);
        run.put(actor + 0x08, flags | 0x20000u);
    }
    if (settings && run.get(run.get(0x5371fc) + 0x124) == 0)
        run.put(actor + 0x08, run.get(actor + 0x08) | 0x10000u);
}

// 0x461730 DoNothing.
uint32_t function_461730(Run &run, uint32_t, const uint32_t *arguments) {
    const uint32_t actor = arguments[0];
    run.put(actor + 0x08, run.get(actor + 0x08) | 1u);
    return 1;
}

// 0x461750 DoNothingNormal.
uint32_t function_461750(Run &run, uint32_t, const uint32_t *arguments) {
    const uint32_t actor = arguments[0];
    run.put(actor + 0x08, run.get(actor + 0x08) | 1u);
    return 2;
}

// 0x461770 FrontCandy.
uint32_t function_461770(Run &run, uint32_t, const uint32_t *arguments) {
    initialize(run, arguments[0], 0x13ec, false, true);
    return 1;
}

// 0x4617d0 BehindCandy.
uint32_t function_4617d0(Run &run, uint32_t, const uint32_t *arguments) {
    initialize(run, arguments[0], 0x3de, false, true);
    return 1;
}

// 0x461830 GooCoverup.
uint32_t function_461830(Run &run, uint32_t, const uint32_t *arguments) {
    initialize(run, arguments[0], 0x1f4a, false, false);
    return 1;
}

// 0x461870 GooBubble.
uint32_t function_461870(Run &run, uint32_t, const uint32_t *arguments) {
    initialize(run, arguments[0], 0x1f40, true, false);
    return 1;
}

// 0x4618e0 FrontAniCandy.
uint32_t function_4618e0(Run &run, uint32_t, const uint32_t *arguments) {
    initialize(run, arguments[0], 0x13ec, true, true);
    return 1;
}

// 0x461970 BehindAniCandy.
uint32_t function_461970(Run &run, uint32_t, const uint32_t *arguments) {
    initialize(run, arguments[0], 0x3de, true, true);
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x461730:
        return function_461730(run, receiver, arguments);
    case 0x461750:
        return function_461750(run, receiver, arguments);
    case 0x461770:
        return function_461770(run, receiver, arguments);
    case 0x4617d0:
        return function_4617d0(run, receiver, arguments);
    case 0x461830:
        return function_461830(run, receiver, arguments);
    case 0x461870:
        return function_461870(run, receiver, arguments);
    case 0x4618e0:
        return function_4618e0(run, receiver, arguments);
    case 0x461970:
        return function_461970(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_scenery_logic_canonical_entry, owned, body)
