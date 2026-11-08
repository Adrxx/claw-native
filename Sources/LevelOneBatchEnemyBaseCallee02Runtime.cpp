// Level 1 enemy shared helpers 0x404dd0, 0x43f640, 0x43f740
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
    case 0x404dd0:
        return 1;
    case 0x43f640:
        return 0;
    case 0x43f740:
        return 0;
    default:
        return -1;
    }
}

// 0x404dd0. Subtracts the argument's +0x104 from the counter at +0x10c of the
// object at receiver+0x0c, only while that counter is positive.
uint32_t function_404dd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t holder = run.get(receiver + 0x0c);
    uint32_t counter = run.get(holder + 0x10c);
    if (s32(counter) <= 0)
        return 0;
    uint32_t amount = run.get(arguments[0] + 0x104);
    run.put(holder + 0x10c, counter - amount);
    return 0;
}

// 0x43f640. Enemy jump start: when the holder at +0x0c has state 1, resets the
// velocity fields, sets the state to 8 and looks up the "LS_JUMP" animation key.
uint32_t function_43f640(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t holder = run.get(receiver + 0x0c);
    if (run.get(holder + 0xcc) != 1)
        return 0;
    run.put(receiver + 0x18, 0x43f720);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x5c, 0xc082c000);
    run.put(receiver + 0x64, 0);
    run.put(receiver + 0x20, 1);
    uint32_t second = run.get(receiver + 0x12c);
    uint32_t flags = run.get(second + 0x08);
    run.put(second + 0x08, flags | 4);
    uint32_t holderAgain = run.get(receiver + 0x0c);
    run.put(holderAgain + 0xcc, 8);
    uint32_t owner = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(owner + 0x1c));
    uint32_t key = run.call(0x4dba00, 0x537668, {0x527204});
    uint32_t ownerAgain = run.get(receiver + 0x10);
    run.put(ownerAgain + 0x1c, key);
    uint32_t secondAgain = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(secondAgain + 0x190));
    run.call(0x4c8220, secondAgain + 0x188, {run.get(receiver + 0x33c)});
    return 0;
}

// Calls 0x4207f0 on the tile map of the primary object at receiver+0x128.
uint32_t tileCheck(Run &run, uint32_t receiver, uint32_t x, uint32_t y) {
    uint32_t primary = run.get(receiver + 0x128);
    uint32_t mid = run.get(primary + 0x0c);
    uint32_t tiles = run.get(mid + 0x24);
    return run.call(0x4207f0, tiles, {x, y});
}

// 0x43f740. Enemy move-back: picks a target x from rand and the double at
// +0x68 (mode 3 adds, otherwise subtracts), checks it against the double bound
// at +0x98 (mode 3) or +0x80 and against tiles, then starts "LS_MOVEBACK".
uint32_t function_43f740(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t mode = run.get(receiver + 0x18c);
    double source = run.getd(receiver + 0x68);
    uint32_t random = run.call(0x4a3050, 0, {});
    uint32_t remainder = uint32_t(s32(random) % 0x33);
    uint32_t base = remainder + 0x4b;
    uint32_t truncated = run.call_x87(0x4a30e0, 0, source, {});
    uint32_t x = 0;
    if (mode == 3) {
        x = base + truncated;
        run.put(receiver + 0x280, x);
        double bound = run.getd(receiver + 0x98);
        if (!(bound >= double(s32(x))))
            return 0;
    } else {
        x = truncated - base;
        run.put(receiver + 0x280, x);
        double bound = run.getd(receiver + 0x80);
        if (bound > double(s32(x)))
            return 0;
    }
    uint32_t primary = run.get(receiver + 0x128);
    uint32_t y = run.get(primary + 0x124) + run.get(primary + 0x50) + 1;
    if (tileCheck(run, receiver, x, y) != 1) {
        if (tileCheck(run, receiver, x, y) != 2) {
            if (tileCheck(run, receiver, x, y) != 3)
                return 0;
        }
    }
    uint32_t last = tileCheck(run, receiver, x, y - 1);
    if (last != 0)
        return 0;
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, mode == 3 ? 0x4062c000 : 0xc062c000);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x5c, 0);
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x64, 0);
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t second = run.get(receiver + 0x12c);
        if ((run.get8(second + 0x40) & 2) == 0) {
            uint32_t first = run.get(receiver + 0x138);
            uint32_t other = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0 - other);
            run.put(receiver + 0x140, 0 - first);
            uint32_t flags = run.get(second + 0x40);
            run.put(second + 0x40, flags | 2);
            run.call(0x4060b0, run.get(receiver + 0x12c), {});
        }
    } else {
        run.call(0x406310, receiver + 0x128, {});
    }
    uint32_t owner = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(owner + 0x1c));
    uint32_t key = run.call(0x4dba00, 0x537668, {0x5271a8});
    uint32_t ownerAgain = run.get(receiver + 0x10);
    run.put(ownerAgain + 0x1c, key);
    uint32_t second = run.get(receiver + 0x12c);
    uint32_t argument = run.get(receiver + 0x308);
    run.put(receiver + 0x134, run.get(second + 0x190));
    run.call(0x4c8220, second + 0x188, {argument});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x404dd0:
        return function_404dd0(run, receiver, arguments);
    case 0x43f640:
        return function_43f640(run, receiver, arguments);
    case 0x43f740:
        return function_43f740(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_enemy_base_callee_02_entry, owned, body)
