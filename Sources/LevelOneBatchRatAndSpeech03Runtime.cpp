// Level 1 enemy speech and Wolvington helper, batch 3
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
    case 0x48ce40:
        return 3;
    case 0x48ceb0:
        return 3;
    case 0x4a1180:
        return 0;
    default:
        return -1;
    }
}

// Globals: 0x53c9ac current logic object, 0x53c9a8 lock flag, 0x53c9b0 stored
// first argument, 0x5371fc game object.

// 0x48ce40. cdecl, 3 arguments. Stores a speech id and sound id on the logic
// object when the preconditions hold.
uint32_t function_48ce40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t first = arguments[0];
    uint32_t second = arguments[1];
    uint32_t third = arguments[2];
    if (first == 0)
        return 0;
    if (second == 0)
        return 0;
    uint32_t logic = run.get(0x53c9ac);
    if (logic == 0)
        return 0;
    if (third == 0) {
        if (run.get(0x53c9a8) != 0)
            return 0;
    }
    if (run.get(logic + 0x6c) == 0)
        return 0;
    // +0x184 value, +0x6c sub object, +0x1c its state.
    run.put(logic + 0x184, second);
    uint32_t again = run.get(0x53c9ac);
    uint32_t sub = run.get(again + 0x6c);
    run.put(sub + 0x1c, 0x3e9);
    run.put(0x53c9b0, first);
    return 1;
}

// 0x48ceb0. cdecl, 3 arguments. Like 0x48ce40 but looks the value up by name.
uint32_t function_48ceb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t first = arguments[0];
    uint32_t name = arguments[1];
    uint32_t third = arguments[2];
    if (first == 0)
        return 0;
    if (name == 0)
        return 0;
    uint32_t logic = run.get(0x53c9ac);
    if (logic == 0)
        return 0;
    if (third == 0) {
        if (run.get(0x53c9a8) != 0)
            return 0;
    }
    if (run.get(logic + 0x6c) == 0)
        return 0;
    // The original reuses its first argument slot as the output local.
    uint32_t slot = run.automatic(4);
    run.put(slot, 0);
    uint32_t game = run.get(0x5371fc);
    uint32_t table = run.get(run.get(game + 0x30) + 0x28);
    run.call(0x4f6286, table + 0x10, {name, slot});
    uint32_t found = run.get(slot);
    if (found == 0)
        return 0;
    uint32_t current = run.get(0x53c9ac);
    run.put(current + 0x184, found);
    uint32_t current2 = run.get(0x53c9ac);
    uint32_t sub = run.get(current2 + 0x6c);
    run.put(sub + 0x1c, 0x3e9);
    run.put(0x53c9b0, first);
    return 1;
}

// 0x4a1180. thiscall. Fields: +0x18c state, +0x128 embedded record (its +4 is
// the object at +0x12c, +0x10/+0x18 at +0x138/+0x140, +0xc at +0x134),
// +0x400 value, +0x50 double, +0x10 and +0x24, +0x308 argument.
uint32_t function_4a1180(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t record = self + 0x128;
    if (run.get(self + 0x18c) == 2) {
        uint32_t object = run.get(record + 0x4);
        if ((run.get8(object + 0x40) & 2) == 0) {
            uint32_t low = run.get(record + 0x10);
            uint32_t high = run.get(record + 0x18);
            run.put(record + 0x10, 0u - high);
            run.put(record + 0x18, 0u - low);
            uint32_t flags = run.get(object + 0x40);
            run.put(object + 0x40, flags | 2u);
            uint32_t target = run.get(record + 0x4);
            run.call(0x406120, target);
            run.call(0x406150, target);
            run.call(0x406180, target);
        }
    } else {
        run.call(0x406310, record);
    }
    uint32_t value = run.get(self + 0x400);
    if (run.get(self + 0x18c) == 3)
        value = 0u - run.get(self + 0x400);
    run.putd(self + 0x50, double(s32(value)));
    uint32_t owner = run.get(self + 0x10);
    uint32_t saved = run.get(owner + 0x1c);
    run.put(self + 0x24, saved);
    uint32_t result = run.call(0x4dba00, 0x537668, {0x527d94});
    uint32_t owner2 = run.get(self + 0x10);
    run.put(owner2 + 0x1c, result);
    uint32_t object2 = run.get(record + 0x4);
    uint32_t argument = run.get(self + 0x308);
    uint32_t copied = run.get(object2 + 0x190);
    run.put(record + 0xc, copied);
    run.call(0x4c8220, object2 + 0x188, {argument});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48ce40:
        return function_48ce40(run, receiver, arguments);
    case 0x48ceb0:
        return function_48ceb0(run, receiver, arguments);
    case 0x4a1180:
        return function_4a1180(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_rat_and_speech_03_entry, owned, body)
