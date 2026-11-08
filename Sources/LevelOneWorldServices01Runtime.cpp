// Level 1 rect, timer and view service entries
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
    case 0x422350:
        return 0;
    case 0x4296f0:
        return 4;
    case 0x42ce20:
        return 1;
    case 0x42d1f0:
        return 1;
    default:
        return -1;
    }
}

// 0x422350. Runs the base initializer on the object, initializes the member
// at +0x1c, then clears the pointer at +0x30.
uint32_t function_422350(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x4f5288, receiver);
    run.call(0x4f650f, receiver + 0x1c);
    run.put(receiver + 0x30, 0);
    return 0;
}

// 0x4296f0. SetRect(this, a, b, c, d) through the import slot.
uint32_t function_4296f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x546d5c, 0, {receiver, arguments[0], arguments[1], arguments[2], arguments[3]});
    return 0;
}

// 0x42ce20. Records the flag at +0x128 and updates bit 1 of the flags word at
// +0x8 of the selected entry, unless bit 0 of that word is set.
// +0x30 world, world+0x24 info, info+0x38 entry array, info+0x3c count.
uint32_t function_42ce20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t flag = arguments[0];
    uint32_t available = run.vcall(receiver, 0xc);
    if (available == 0)
        return 0;
    uint32_t world = run.get(receiver + 0x30);
    if (world == 0)
        return 0;
    if (run.get(world + 0x24) == 0)
        return 0;
    run.put(receiver + 0x128, flag);
    uint32_t info = run.get(world + 0x24);
    uint32_t count = run.get(info + 0x3c);
    uint32_t index = count;
    if (index == 4)
        index = 3;
    index = index - 1;
    uint32_t entry;
    if (s32(index) < 0 || s32(index) >= s32(count)) {
        entry = 0;
    } else {
        uint32_t entries = run.get(info + 0x38);
        entry = run.get(entries + index * 4);
    }
    if (entry == 0)
        return 0;
    uint32_t bits = run.get(entry + 0x8);
    if ((bits & 1) != 0)
        return 0;
    if (flag != 0) {
        run.put(entry + 0x8, bits & 0xfffffffd);
        return 0;
    }
    run.put(entry + 0x8, bits | 2);
    return 0;
}

// 0x42d1f0. Re-applies the stored flag, then calls 0x429ed0 with the field
// at +0x68, 1 and the argument.
uint32_t function_42d1f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t stored[1] = {run.get(receiver + 0x128)};
    function_42ce20(run, receiver, stored);
    uint32_t target = run.get(receiver + 0x68);
    run.call(0x429ed0, receiver, {target, 1, arguments[0]});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x422350:
        return function_422350(run, receiver, arguments);
    case 0x4296f0:
        return function_4296f0(run, receiver, arguments);
    case 0x42ce20:
        return function_42ce20(run, receiver, arguments);
    case 0x42d1f0:
        return function_42d1f0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_world_services_01_entry, owned, body)
