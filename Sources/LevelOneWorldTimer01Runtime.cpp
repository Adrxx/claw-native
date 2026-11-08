// Level 1 timer-update entry 0x4224f0
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
    case 0x4224f0:
        return 1;
    default:
        return -1;
    }
}

// Timer object fields used here: +0x0c mode, +0x1c string, +0x20 elapsed,
// +0x24 short threshold, +0x28 long threshold, +0x2c flash elapsed,
// +0x30 flash active.
// Calls the map remove-start and string release pair on the argument slot.
void expire(Run &run, uint32_t receiver) {
    run.call(0x4f53eb, receiver, {run.automatic(4)});
    run.call(0x4f6584, run.automatic(4));
    run.put(receiver + 0x20, 0);
}

// 0x4224f0. thiscall, 1 stack argument (elapsed time), returns void.
uint32_t function_4224f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t delta = arguments[0];
    if (run.get(receiver + 0x30) != 0) {
        uint32_t flash = run.get(receiver + 0x2c) + delta;
        run.put(receiver + 0x2c, flash);
        if (flash > 0x2710) {
            run.put(receiver + 0x30, 0);
            run.call(0x4f650f, receiver + 0x1c);
        }
    }
    uint32_t mode = run.get(receiver + 0xc);
    if (mode == 0)
        run.put(receiver + 0x20, 0);
    uint32_t elapsed = run.get(receiver + 0x20) + delta;
    run.put(receiver + 0x20, elapsed);
    if (s32(mode) > 3) {
        if (elapsed >= run.get(receiver + 0x28))
            expire(run, receiver);
    } else if (elapsed >= run.get(receiver + 0x24) && mode != 0) {
        expire(run, receiver);
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4224f0:
        return function_4224f0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_world_timer_01_entry, owned, body)
