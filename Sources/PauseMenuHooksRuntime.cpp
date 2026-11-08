// Pause menu state slots, rectangles and volume gauges
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
    case 0x450310:
        return 0;
    case 0x450380:
        return 0;
    case 0x4503c0:
        return 0;
    case 0x450430:
        return 0;
    case 0x452930:
        return 0;
    case 0x4529a0:
        return 0;
    case 0x46dde0:
        return 0;
    default:
        return -1;
    }
}

// Calls an owned function that takes no stack arguments, directly in C++.
uint32_t function_452930(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4529a0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_450380(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_46dde0(Run &run, uint32_t receiver, const uint32_t *arguments);

// Models the original's stack: sets the callee-entry ESP for the next outside
// call. `below` is the byte distance under this function's entry frame.
void enter(Run &run, uint32_t below) {
    run.stackPointer = run.frame - below;
}

// Runs an owned function with the frame it has when called from here.
uint32_t owned_call(Run &run, uint32_t below, uint32_t (*function)(Run &, uint32_t, const uint32_t *),
                    uint32_t receiver, const uint32_t *arguments) {
    uint32_t saved = run.frame;
    run.frame = saved - below;
    uint32_t result = function(run, receiver, arguments);
    run.frame = saved;
    return result;
}

// 0x450310. Resumes the pause menu: prepares the surfaces when the gauge
// object (+0x274) reports ready, hides the cursor and repaints.
// Menu fields: +4 application, +0x274 gauge object.
uint32_t function_450310(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t menu = receiver;
    if (run.get(menu + 0x274) == 0)
        return 0;
    if (run.get(menu + 0x4) == 0)
        return 0;
    uint32_t gauge = run.get(menu + 0x274);
    enter(run, 16);
    uint32_t ready = run.vcall(gauge, 0x18);
    if (ready == 0)
        return 0;
    uint32_t result = owned_call(run, 16, function_450380, menu, arguments);
    uint32_t application = run.get(menu + 0x4);
    if (run.get(application + 0x14) != 0) {
        uint32_t pane = run.get(application + 0x50);
        enter(run, 20);
        run.call(0x4b5570, pane, {1});
    }
    uint32_t count = run.icall(0x546d54, {0});
    while (s32(count) >= 0) {
        count = run.icall(0x546d54, {0});
    }
    enter(run, 16);
    run.call(0x452ae0, menu);
    return result;
}

// 0x450380. Prepares the pause surfaces and returns 1.
uint32_t function_450380(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t menu = receiver;
    owned_call(run, 8, function_452930, menu, arguments);
    enter(run, 8);
    run.call(0x46dd90, run.get(menu + 0x274));
    owned_call(run, 8, function_46dde0, run.get(menu + 0x274), arguments);
    owned_call(run, 8, function_4529a0, menu, arguments);
    enter(run, 8);
    run.call(0x451c40, menu);
    return 1;
}

// 0x4503c0. Shows the menu surfaces; returns 1 when it did.
uint32_t function_4503c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t menu = receiver;
    enter(run, 8);
    uint32_t ready = run.vcall(menu, 0xc);
    if (ready == 0)
        return 0;
    if (run.get(menu + 0x274) == 0)
        return 0;
    owned_call(run, 8, function_452930, menu, arguments);
    enter(run, 8);
    run.call(0x46dd90, run.get(menu + 0x274));
    owned_call(run, 8, function_46dde0, run.get(menu + 0x274), arguments);
    uint32_t owner = run.get(menu + 0xc);
    uint32_t inner = run.get(owner + 0x4);
    uint32_t table = run.get(inner + 0x10);
    uint32_t surface = run.get(table + 0x2c);
    enter(run, 12);
    run.call(0x4b98b0, surface, {0});
    owned_call(run, 8, function_46dde0, run.get(menu + 0x274), arguments);
    owned_call(run, 8, function_4529a0, menu, arguments);
    return 1;
}

// 0x450430. Repaints when the menu is ready and 0x490370 accepts it.
uint32_t function_450430(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t menu = receiver;
    uint32_t ready = run.vcall(menu, 0xc);
    if (ready == 0)
        return 0;
    // Callee-entry ESP of 0x490370: one pushed esi plus the return word.
    enter(run, 8);
    uint32_t accepted = run.call(0x490370, menu);
    if (accepted == 0)
        return 0;
    enter(run, 8);
    run.vcall(menu, 0x1c);
    return 0;
}

// 0x452930. Sets bit 0 of the flags word (+0x40) of each present slot
// object at menu +0x254, +0x258, +0x25c, +0x260, +0x264, +0x268, +0x26c.
uint32_t function_452930(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t menu = receiver;
    for (uint32_t offset = 0x254; offset <= 0x26c; offset += 4) {
        uint32_t slot = run.get(menu + offset);
        if (slot != 0)
            run.put(slot + 0x40, run.get(slot + 0x40) | 1);
    }
    return 0;
}

// 0x4529a0. Clears bit 0 of the flags word of the first four slot objects,
// then dispatches on the state id at +0x298 through 0x4525a0.
uint32_t function_4529a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t menu = receiver;
    for (uint32_t offset = 0x254; offset <= 0x260; offset += 4) {
        uint32_t slot = run.get(menu + offset);
        if (slot != 0)
            run.put(slot + 0x40, run.get(slot + 0x40) & 0xfffffffe);
    }
    enter(run, 8);
    run.call(0x4525a0, menu, {run.get(menu + 0x298)});
    return 0;
}

// 0x46dde0. A direct jump to 0x46ddf0 (pixel gauges by display depth).
uint32_t function_46dde0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    enter(run, 0);
    run.call(0x46ddf0, receiver);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x450310:
        return function_450310(run, receiver, arguments);
    case 0x450380:
        return function_450380(run, receiver, arguments);
    case 0x4503c0:
        return function_4503c0(run, receiver, arguments);
    case 0x450430:
        return function_450430(run, receiver, arguments);
    case 0x452930:
        return function_452930(run, receiver, arguments);
    case 0x4529a0:
        return function_4529a0(run, receiver, arguments);
    case 0x46dde0:
        return function_46dde0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_pause_menu_hooks_entry, owned, body)
