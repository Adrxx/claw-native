// Level 1 Soldier state and destructor callbacks, batch 1
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
    case 0x48b670:
        return 0;
    case 0x48b880:
        return 0;
    case 0x48afd0:
        return 1;
    case 0x48aff0:
        return 0;
    case 0x404e00:
        return 1;
    case 0x404e10:
        return 0;
    case 0x43f500:
        return 1;
    case 0x43fcb0:
        return 1;
    case 0x43fd60:
        return 1;
    case 0x43fe00:
        return 0;
    default:
        return -1;
    }
}

// Soldier fields used here: +0x10 animation owner (its +0x1c is the current
// state name), +0x24 saved state name, +0x128 embedded sub-object (its +0x4 is
// the owning record), +0x134 and +0x370 current animation, +0x46c and +0x470
// timestamp and interval. Globals: 0x537210 tick counter, 0x537668 string table,
// 0x537964 mode, 0x537e88 game state.

// Saves the current state name and installs the one the string table maps `name` to.
// Shared by the original state setters.
void switchStateName(Run &run, uint32_t soldier, uint32_t name) {
    uint32_t owner = run.get(soldier + 0x10);
    uint32_t current = run.get(owner + 0x1c);
    run.put(soldier + 0x24, current);
    uint32_t mapped = run.call(0x4dba00, 0x537668, {name});
    uint32_t owner2 = run.get(soldier + 0x10);
    run.put(owner2 + 0x1c, mapped);
}

// Copies the record's animation word into +0x134 and starts `animation` on the record.
void startAnimation(Run &run, uint32_t soldier, uint32_t animationField) {
    uint32_t record = run.get(soldier + 0x12c);
    uint32_t animation = run.get(animationField);
    uint32_t word = run.get(record + 0x190);
    run.put(soldier + 0x134, word);
    run.call(0x4c8220, record + 0x188, {animation});
}

// 0x48b880. thiscall, 0 stack argument(s), returns u32.
uint32_t function_48b880(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t sub = receiver + 0x128;
    switchStateName(run, receiver, 0x524548);
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t record = run.get(sub + 0x4);
        if ((run.get8(record + 0x40) & 2) == 0) {
            uint32_t first = run.get(sub + 0x10);
            uint32_t second = run.get(sub + 0x18);
            run.put(sub + 0x10, 0u - second);
            run.put(sub + 0x18, 0u - first);
            uint32_t flags = run.get(record + 0x40);
            run.put(record + 0x40, flags | 2);
            run.call(0x4060b0, run.get(sub + 0x4));
        }
    } else {
        run.call(0x406310, sub);
    }
    uint32_t result;
    if (run.get(0x537964) == 2 && run.get(run.get(0x537e88) + 0xcc) == 5) {
        uint32_t local = run.automatic(-4);
        uint32_t owner = run.get(sub + 0x4);
        uint32_t table = run.get(run.get(owner + 0xc) + 0x2c);
        run.put(local, 0);
        run.call(0x4f6286, table + 0x10, {0x52c488, local});
        result = run.get(local);
        if (result == 0)
            result = run.call(0x4062e0, sub, {0x5234b4});
    } else {
        uint32_t owner = run.get(sub + 0x4);
        uint32_t table = run.get(run.get(owner + 0xc) + 0x2c);
        result = run.call(0x4061b0, table, {0x52c408});
        if (result == 0) {
            uint32_t owner2 = run.get(sub + 0x4);
            uint32_t table2 = run.get(run.get(owner2 + 0xc) + 0x2c);
            result = run.call(0x4061b0, table2, {0x5234b4});
        }
    }
    run.put(receiver + 0x370, result);
    uint32_t record = run.get(receiver + 0x12c);
    if ((run.get8(record + 0x40) & 2) != 0) {
        run.put(receiver + 0x454, 0x41);
        run.put(receiver + 0x45c, 0x1f4);
    } else {
        run.put(receiver + 0x454, 0xffffffbf);
        run.put(receiver + 0x45c, 0xfffffe0c);
    }
    if (run.get(0x537964) == 2 && run.get(run.get(0x537e88) + 0xcc) == 5)
        run.put(receiver + 0x458, 0xa);
    else
        run.put(receiver + 0x458, 0xffffffda);
    uint32_t record2 = run.get(sub + 0x4);
    uint32_t animation = run.get(receiver + 0x370);
    uint32_t word = run.get(record2 + 0x190);
    run.put(sub + 0xc, word);
    run.call(0x4c8220, record2 + 0x188, {animation});
    run.put(receiver + 0x1a0, 0);
    return 0;
}

// 0x48b670. thiscall, 0 stack argument(s), returns u32.
uint32_t function_48b670(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t now = run.get(0x537210);
    uint32_t last = run.get(receiver + 0x46c);
    uint32_t interval = run.get(receiver + 0x470);
    if (now - last >= interval) {
        function_48b880(run, receiver, nullptr);
        run.put(receiver + 0x470, 0x1f4);
        uint32_t tick = run.get(0x537210);
        run.put(receiver + 0x46c, tick);
    }
    return 0;
}

// 0x48aff0. thiscall, 0 stack argument(s), returns void.
// The original's exception-chain registration is not modeled.
uint32_t function_48aff0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}

// 0x48afd0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_48afd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_48aff0(run, receiver, nullptr);
    if ((arguments[0] & 1) != 0)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x404e00. thiscall, 1 stack argument(s), returns void.
uint32_t function_404e00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x1ac, arguments[0]);
    return 0;
}

// 0x404e10. thiscall, 0 stack argument(s), returns void.
uint32_t function_404e10(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t owner = run.get(receiver + 0xc);
    uint32_t value = run.get(owner + 0x10c);
    run.put(owner + 0x10c, value + 0xfffffffc);
    return 0;
}

// 0x43f500. thiscall, 1 stack argument(s), returns u32.
uint32_t function_43f500(Run &run, uint32_t receiver, const uint32_t *arguments) {
    switchStateName(run, receiver, 0x5271c0);
    run.put(receiver + 0x3e4, arguments[0]);
    uint32_t tick = run.get(0x537210);
    run.put(receiver + 0x3e0, tick);
    return 0;
}

// 0x43fcb0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_43fcb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.putd(receiver + 0x50, double(s32(0u - arguments[0])));
    switchStateName(run, receiver, 0x5271f4);
    startAnimation(run, receiver, receiver + 0x354);
    return 0;
}

// 0x43fd60. thiscall, 1 stack argument(s), returns u32.
uint32_t function_43fd60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.putd(receiver + 0x50, double(s32(arguments[0])));
    switchStateName(run, receiver, 0x5271e4);
    startAnimation(run, receiver, receiver + 0x354);
    return 0;
}

// 0x43fe00. thiscall, 0 stack argument(s), returns u32.
uint32_t function_43fe00(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    switchStateName(run, receiver, 0x527218);
    startAnimation(run, receiver, receiver + 0x314);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48b670:
        return function_48b670(run, receiver, arguments);
    case 0x48b880:
        return function_48b880(run, receiver, arguments);
    case 0x48afd0:
        return function_48afd0(run, receiver, arguments);
    case 0x48aff0:
        return function_48aff0(run, receiver, arguments);
    case 0x404e00:
        return function_404e00(run, receiver, arguments);
    case 0x404e10:
        return function_404e10(run, receiver, arguments);
    case 0x43f500:
        return function_43f500(run, receiver, arguments);
    case 0x43fcb0:
        return function_43fcb0(run, receiver, arguments);
    case 0x43fd60:
        return function_43fd60(run, receiver, arguments);
    case 0x43fe00:
        return function_43fe00(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_soldier_01_entry, owned, body)
