// Independent synthetic clients of the owned x87 result channel. Test only.
#include "ClawRuntime.hpp"

namespace {
constexpr uint32_t LOAD = 0x401000, PRODUCED = 0x401020, MODE = 0x401060;
constexpr uint32_t NONE = 0x401080, TWO = 0x4010a0, CONTROL = 0x4010c0, PRODUCER = 0x4010e0;

int owned(uint32_t function) {
    switch (function) {
    case LOAD: case PRODUCED: case NONE: case TWO: case CONTROL: return 2;
    case MODE: return 3;
    default: return -1;
    }
}

// Each body follows its synthetic original: load or produce one binary64.
uint32_t body(claw::Run &run, uint32_t function, uint32_t, const uint32_t *a) {
    if (function == PRODUCED) {
        auto fp = run.x87_entry(function);
        fp.popCount = 0;
        fp.pushCount = 1;
        fp.returned = fp.eax = fp.edx = 0;
        run.call_x87_exact(PRODUCER, 0, fp, {a[0], a[1]});
        fp.returned = fp.eax = fp.edx = 0;
        run.x87_return(function, fp);
        return 0;
    }
    if (function != MODE) {
        auto fp = run.x87_entry(function);
        run.x87_step(CLAW_X87_F64, fp, {a[0], a[1]});
        run.x87_return(function, fp);
        return 0;
    }
    // MODE: the original loads the binary64 in a[1], a[2]; a[0] selects a
    // correct or deliberately wrong native publication.
    const uint32_t mode = a[0];
    ClawX87State fp{};
    if (mode == 11) {  // built without asking: the host's reset entry state
        fp.size = sizeof(fp); fp.version = CLAW_X87_VERSION; fp.control = 0x023f;
    } else {
        fp = run.x87_entry(function);
    }
    if (mode == 9) fp = run.x87_entry(function);
    run.x87_step(CLAW_X87_F64, fp, {a[1], a[2]});
    switch (mode) {
    case 1: fp.slots[0].significand ^= 1; break;
    case 2: fp.status ^= 0x4000; break;
    case 3: return 0;
    case 6: run.x87_step(CLAW_X87_F64, fp, {a[1], a[2]}); break;
    case 7: fp.status ^= 0x0800; break;
    case 10: fp.control ^= 0x0400; break;
    default: break;
    }
    run.x87_return(mode == 8 ? LOAD : function, fp);
    if (mode == 4) run.x87_return(function, fp);
    if (mode == 5) run.x87_step(CLAW_X87_CHS, fp);
    return 0;
}
}
CLAW_MODULE_ENTRY(claw_x87_result_selftest_entry, owned, body)

namespace {
// Selftest client of hash-checked 0x420af0 restricted to its first exit:
// when the +0x10 factor equals the zero constant, the original returns the
// +0x28 binary64 after an equal compare. Other inputs are not implemented.
int motion_owned(uint32_t function) { return function == 0x420af0 ? 2 : -1; }
uint32_t motion_body(claw::Run &run, uint32_t function, uint32_t receiver, const uint32_t *) {
    auto fp = run.x87_entry(function);
    const uint32_t low = run.get(receiver + 0x10), high = run.get(receiver + 0x14);
    if (run.get(0x50ba88) || run.get(0x50ba8c) || low || (high & 0x7fffffffu))
        run.fail(CLAW_FAULT_UNIMPLEMENTED, function);
    // FLD m64 then FCOMP m64 equal: TOP restored, C3 set, C2/C1/C0 clear.
#ifndef SELFTEST_X87R_WRONG_SW
    fp.status = (fp.status & ~0x4700u) | 0x4000u;
#endif
    run.x87_step(CLAW_X87_F64, fp, {run.get(receiver + 0x28), run.get(receiver + 0x2c)});
#ifdef SELFTEST_X87R_WRONG_BIT
    fp.slots[0].significand ^= 0x800;
#endif
    run.x87_return(function, fp);
    return 0;
}
}
CLAW_MODULE_ENTRY(claw_x87_result_motion_selftest_entry, motion_owned, motion_body)
