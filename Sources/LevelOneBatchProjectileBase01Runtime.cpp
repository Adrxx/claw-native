// Level 1 projectile base slot 0x474290
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
    case 0x474290:
        return 0;
    default:
        return -1;
    }
}

// 0x474290. thiscall, 0 stack argument(s), returns u32.
// Object fields: +0x0c owner, +0x10 record, +0x24 saved record value,
// +0x12c source, +0x134 copied value, +0x148 optional argument.
uint32_t function_474290(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t record = run.get(receiver + 0x10);
    uint32_t saved = run.get(record + 0x1c);
    run.put(receiver + 0x24, saved);
    uint32_t lookup = run.call(0x4dba00, 0x537668, {0x5236fc});
    uint32_t record2 = run.get(receiver + 0x10);
    run.put(record2 + 0x1c, lookup);
    uint32_t option = run.get(receiver + 0x148);
    if (option != 0) {
        uint32_t source = run.get(receiver + 0x12c);
        uint32_t value = run.get(source + 0x190);
        run.put(receiver + 0x134, value);
        run.call(0x4c8220, source + 0x188, {option});
    }
    uint32_t owner = run.get(receiver + 0xc);
    run.put(owner + 0xcc, 8);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x474290:
        return function_474290(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_projectile_base_01_entry, owned, body)
