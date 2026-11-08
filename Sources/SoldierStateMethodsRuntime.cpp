// Soldier state dispatch and idle behaviour
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
    case 0x48b0c0:
        return 1;
    case 0x48b730:
        return 0;
    default:
        return -1;
    }
}

// 0x48b0c0. thiscall, 1 stack argument, returns void.
// Global table object at 0x53c328: +0x08 low key (0x53c330), +0x0c high key
// (0x53c334), +0x14 entries (0x53c338), +0x18 entry stride (0x53c340),
// 0x53c33c default entry, 0x53c32c owner for the error report, 0x544b4c the
// error text, 0x544b14 error result, 0x53c348 a flag cleared on each lookup.
// Looks up the handler entry for `key`; a zero entry falls back to 0x44c840,
// otherwise the handler stored in the entry is called on the receiver.
uint32_t function_48b0c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t key = arguments[0];
    uint32_t ecx = run.get(0x53c330);
    run.put(0x53c348, 0);
    uint32_t eax = 0;
    bool inRange = !(s32(key) < s32(ecx)) && !(s32(key) > s32(run.get(0x53c334)));
    if (inRange) {
        eax = key;
    } else {
        uint32_t found = run.call(0x4db6e0, 0x53c328, {key, 0});
        if (found != 0) {
            ecx = run.get(0x53c330);
            eax = key;
            inRange = true;
        } else {
            // Original-fault path: the report call never returns normally.
            uint32_t text = run.get(0x544b4c);
            uint32_t result = run.call(0x4db5f0, 0, {});
            uint32_t owner = run.get(0x53c32c);
            run.put(0x544b14, result);
            run.call(0x4db4d0, owner, {0x53c328, text, 0xc});
            eax = run.get(0x53c33c);
            ecx = run.get(0x53c330);
        }
    }
    if (inRange) {
        uint32_t base = run.get(0x53c338);
        eax = (eax - ecx) * run.get(0x53c340);
        eax = eax + base;
    }
    // Unguarded read of the entry (faults on the original-fault path).
    if (run.get(eax) == 0) {
        run.call(0x44c840, receiver, {key});
        return 0;
    }
    run.put(0x53c348, 0);
    uint32_t handler = 0;
    bool outside = s32(key) < s32(ecx);
    if (!outside)
        outside = !(s32(key) <= s32(run.get(0x53c334)));
    if (outside) {
        uint32_t found = run.call(0x4db6e0, 0x53c328, {key, 0});
        if (found == 0) {
            // Second original-fault path, same fault as the first.
            uint32_t text = run.get(0x544b4c);
            uint32_t result = run.call(0x4db5f0, 0, {});
            uint32_t owner = run.get(0x53c32c);
            run.put(0x544b14, result);
            run.call(0x4db4d0, owner, {0x53c328, text, 0xc});
            uint32_t entry = run.get(0x53c33c);
            handler = run.get(entry);
            run.call(handler, receiver, {});
            return 0;
        }
        ecx = run.get(0x53c330);
    }
    uint32_t entry = key - ecx;
    uint32_t base = run.get(0x53c338);
    entry = entry * run.get(0x53c340);
    entry = entry + base;
    handler = run.get(entry);
    run.call(handler, receiver, {});
    return 0;
}

// 0x48b730. thiscall, 0 stack arguments, returns u32 (always 0).
// Soldier fields: +0x464/+0x468 last time and delay of the animation pick,
// +0x474/+0x478 last time and delay of the idle roll, +0x12c animation owner
// (+0x188 animation sub-object, +0x190 current frame), +0x134 saved frame,
// +0x318/+0x31c the two animation choices, +0x190 and +0x194 the actor
// records compared against the player at 0x537e88. 0x537210 is the clock.
uint32_t function_48b730(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t elapsed = run.get(0x537210) - run.get(self + 0x464);
    if (!(elapsed < run.get(self + 0x468))) {
        run.put(self + 0x468, 0x3e8);
        run.put(self + 0x464, run.get(0x537210));
        uint32_t roll = run.call(0x4a3050, 0, {});
        uint32_t sign = uint32_t(s32(roll) >> 31);
        uint32_t pick = ((roll ^ sign) - sign) & 1;
        pick = pick ^ sign;
        pick = pick - sign;
        bool choose = true;
        uint32_t animation = 0;
        if (pick == 0) {
            animation = run.get(self + 0x318);
        } else if (pick - 1 == 0) {
            animation = run.get(self + 0x31c);
        } else {
            choose = false;
        }
        if (choose) {
            uint32_t owner = run.get(self + 0x12c);
            uint32_t frame = run.get(owner + 0x190);
            run.put(self + 0x134, frame);
            run.call(0x4c8220, owner + 0x188, {animation});
            uint32_t speed = run.get(0x5430c4);
            uint32_t again = run.get(self + 0x12c);
            run.call(0x4c82a0, again + 0x188, {speed});
        }
    }
    bool near = false;
    if (run.get(0x534eac) != 0x26b7) {
        uint32_t player = run.get(0x537e88);
        uint32_t target = run.get(self + 0x194);
        uint32_t playerX = run.get(player + 0x4c);
        uint32_t targetY = run.get(target + 0x50);
        uint32_t targetX = run.get(target + 0x4c);
        uint32_t actor = run.get(self + 0x190);
        uint32_t level = run.get(actor + 0xc);
        uint32_t checker = run.get(level + 0x24);
        uint32_t hit = run.call(0x4cda10, checker, {targetX, targetY, playerX, 0x20});
        if (hit != 0) {
            uint32_t record = run.get(self + 0x194);
            uint32_t playerRecord = run.get(0x537e88);
            uint32_t recordY = run.get(record + 0x50);
            uint32_t playerY = run.get(playerRecord + 0x50);
            uint32_t upper = recordY + 0x32;
            if (!(s32(playerY) >= s32(upper))) {
                uint32_t lower = recordY - 0x32;
                if (!(s32(playerY) <= s32(lower))) {
                    if (run.get(record + 0x38) != 0xffffffffu)
                        near = true;
                }
            }
        }
    }
    if (near) {
        run.vcall(self, 0x44, {});
        return 0;
    }
    uint32_t idle = run.get(0x537210) - run.get(self + 0x474);
    uint32_t idleDelay = run.get(self + 0x478);
    if (!(idle < idleDelay)) {
        bool roll5 = false;
        if (run.get(0x541334) == 0) {
            uint32_t value = run.call(0x4a3050, 0, {});
            roll5 = s32(value) % 100 < 5;
        }
        if (roll5)
            run.call(0x44edd0, self, {});
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48b0c0:
        return function_48b0c0(run, receiver, arguments);
    case 0x48b730:
        return function_48b730(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_soldier_state_methods_entry, owned, body)
