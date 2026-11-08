// Level 2 per-level setup
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
    case 0x452cc0:
        return 1;
    default:
        return -1;
    }
}

// 0x452cc0. Level 2 per-level setup of one object (argument 1). Returns 0 for
// a null object. Fields: +0x44 flag, +0xb0/+0xb4/+0xb8 constants, rectangles
// at +0x58, +0x78 and +0x68 through SetRect (import slot 0x546d5c).
uint32_t function_452cc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    if (object == 0)
        return 0;
    run.put(object + 0x44, 1);
    run.put(object + 0xb0, 0x32);
    run.put(object + 0xb4, 0x4e67);
    run.put(object + 0xb8, 0x803);
    run.icall(0x546d5c, {object + 0x58, uint32_t(-0x18), uint32_t(-6), 0x26, 0x20});
    run.icall(0x546d5c, {object + 0x78, uint32_t(-0x18), uint32_t(-0x2e), 0x18, 0x20});
    run.icall(0x546d5c, {object + 0x68, uint32_t(-0x2c), uint32_t(-8), 0x2e, 0x20});
    run.put(0x5262b0, 0x3f800000);
    run.put(0x5262b4, 0x3f800000);
    run.put(0x5262b8, 0x3f800000);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x452cc0:
        return function_452cc0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_two_setup_entry, owned, body)
