// Soldier construction and registered tick
//
// Recovered from the decompile and disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x48a980:
        return 1;
    case 0x48aa40:
        return 1;
    case 0x48b6b0:
        return 0;
    default:
        return -1;
    }
}

uint32_t function_48aa40(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_48b6b0(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x48a980. cdecl, 1 stack argument (the owner), returns 1.
// Owner +0x6c is the logic state record. State record +0x18 is the child
// object and +0x1c is the command word.
uint32_t function_48a980(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t owner = arguments[0];
    uint32_t state = run.get(owner + 0x6c);
    uint32_t command = run.get(state + 0x1c);
    if (command > 0x1d) {
        if (command == 0x1e) {
            // Virtual slot 0x1c of the child.
            uint32_t child = run.get(state + 0x18);
            run.vcall(child, 0x1c);
            return 1;
        }
        if (command == 0x3e8)
            return 1;
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    if (command == 0x1d) {
        // Virtual slot 0x20 of the child.
        uint32_t child = run.get(state + 0x18);
        run.vcall(child, 0x20);
        return 1;
    }
    if (command != 0) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    run.put(state + 0x1c, 0x3e8);
    uint32_t memory = run.call(0x4f63ec, 0, {0x480});
    uint32_t soldier = 0;
    if (memory) {
        const uint32_t constructorArguments[1] = {owner};
        soldier = function_48aa40(run, memory, constructorArguments);
    }
    // A null allocation falls through to the original's null dereference.
    run.vcall(soldier, 0x10);
    run.put(state + 0x18, soldier);
    return 1;
}

// Looks a name up in the resource table and falls back to GAME_NULL (0x5234b4).
uint32_t lookupOrNull(Run &run, uint32_t table, uint32_t name) {
    uint32_t found = run.call(0x4062e0, table, {name});
    if (found == 0)
        found = run.call(0x4062e0, table, {0x5234b4});
    return found;
}

// Looks a sound up through the level sound manager (+0x12c -> +0xc -> +0x28
// plus 0x10), writing the result through the incoming argument slot.
uint32_t lookupSound(Run &run, uint32_t self, uint32_t name) {
    uint32_t slot = run.automatic(4);
    run.put(slot, 0);
    uint32_t owner = run.get(self + 0x12c);
    uint32_t level = run.get(owner + 0xc);
    uint32_t manager = run.get(level + 0x28);
    run.call(0x4f6286, manager + 0x10, {name, slot});
    return run.get(slot);
}

// Looks a name up in the level sound manager's second table.
uint32_t lookupSoundId(Run &run, uint32_t self, uint32_t name) {
    uint32_t owner = run.get(self + 0x12c);
    uint32_t level = run.get(owner + 0xc);
    uint32_t manager = run.get(level + 0x28);
    return run.call(0x4061b0, manager, {name});
}

// 0x48aa40. thiscall, 1 stack argument (the owner), returns this.
uint32_t function_48aa40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    run.call(0x44c000, self, {arguments[0]});
    run.put(self + 0x464, 0);
    run.put(self + 0x468, 0);
    run.put(self + 0x46c, 0);
    run.put(self + 0x470, 0);
    run.put(self + 0x474, 0);
    run.put(self + 0x478, 0);
    run.put(self, 0x50f774);
    run.call(0x4c7970, run.get(self + 0x12c), {0x52c46c});
    // Flag set: bit count at +0x2fc, inline words from +0x300, heap above 0x20.
    uint32_t bits = run.get(self + 0x2fc);
    uint32_t flagSet = self + 0x2f4;
    if (bits <= 8) {
        run.call(0x4dbd20, flagSet, {8});
    } else {
        if (bits > 0x20)
            flagSet = run.get(flagSet + 0xc);
        else
            flagSet = flagSet + 0xc;
        uint32_t flags = run.get(flagSet);
        flags = flags | 0x100;
        run.put(flagSet, flags);
    }
    uint32_t table = self + 0x128;
    run.put(self + 0x450, 0);
    run.put(self + 0x308, lookupOrNull(run, table, 0x52c454));
    run.put(self + 0x30c, lookupOrNull(run, table, 0x52c438));
    run.put(self + 0x310, lookupOrNull(run, table, 0x52c420));
    run.put(self + 0x370, lookupOrNull(run, table, 0x52c408));
    run.put(self + 0x318, lookupOrNull(run, table, 0x52c3f4));
    run.put(self + 0x31c, lookupOrNull(run, table, 0x52c3dc));
    run.put(self + 0x32c, lookupOrNull(run, table, 0x52c3c8));
    run.put(self + 0x374, lookupOrNull(run, table, 0x52c3c8));
    run.put(self + 0x334, lookupOrNull(run, table, 0x52c3b0));
    run.put(self + 0x338, lookupOrNull(run, table, 0x52c398));
    run.put(self + 0x33c, lookupOrNull(run, table, 0x52c384));
    run.put(self + 0x344, lookupOrNull(run, table, 0x52c370));
    run.put(self + 0x34c, lookupOrNull(run, table, 0x52c438));
    run.put(self + 0x378, lookupOrNull(run, table, 0x52c358));
    run.put(self + 0x37c, lookupOrNull(run, table, 0x52c340));
    run.put(self + 0x380, lookupOrNull(run, table, 0x52c340));
    run.put(self + 0x36c, lookupOrNull(run, table, 0x52c328));
    run.put(self + 0x3a4, lookupSound(run, self, 0x52c310));
    run.put(self + 0x410, lookupSound(run, self, 0x52c2f8));
    run.put(self + 0x414, lookupSound(run, self, 0x52c2e0));
    run.put(self + 0x418, lookupSoundId(run, self, 0x52c2e0));
    run.put(self + 0x3a0, lookupSoundId(run, self, 0x52c2c4));
    run.put(self + 0x3b4, lookupSoundId(run, self, 0x52c2a8));
    run.put(self + 0x460, lookupSoundId(run, self, 0x52c290));
    // SetRect import slot at 0x546d5c: (rect, left, top, right, bottom).
    run.icall(0x546d5c, {self + 0x220, uint32_t(-0x4d), uint32_t(-0x32), 0, uint32_t(-0x1e)});
    run.icall(0x546d5c, {self + 0x210, uint32_t(-1), uint32_t(-1), 1, 1});
    uint32_t hitRect = self + 0x250;
    run.icall(0x546d5c, {hitRect, uint32_t(-0xb), uint32_t(-0x3c), 0xb, 0x32});
    run.icall(0x546d5c, {self + 0x260, uint32_t(-0x29), uint32_t(-0x17), 0x2b, 0x1f});
    uint32_t bottom = run.get(hitRect + 0xc);
    uint32_t right = run.get(hitRect + 0x8);
    uint32_t top = run.get(hitRect + 0x4);
    uint32_t left = run.get(hitRect);
    run.call(0x40f6c0, run.get(self + 0x12c), {left, top, right, bottom});
    run.call(0x4208b0, run.get(self + 0x12c), {uint32_t(-0xf), uint32_t(-0x32), 0xf, 0x32});
    run.put(self + 0x28c, 0x190);
    run.put(self + 0x294, 0x12c);
    run.put(self + 0x29c, 0x12c);
    run.put(self + 0x290, 0x32);
    run.put(self + 0x2a4, 0x50);
    run.put(self + 0x2ac, 0x50);
    run.put(self + 0x298, 0x32);
    run.put(self + 0x2a0, 0x32);
    run.put(self + 0x2a8, 0x32);
    run.put(self + 0x2b0, 0x32);
    run.put(self + 0x2b4, 0);
    run.put(self + 0x2b8, 0);
    run.put(self + 0x2bc, 0xffffffbf);
    run.put(self + 0x2c0, 0xffffffec);
    run.put(self + 0x2c4, 0x14);
    run.put(self + 0x2c8, 0xfffffff1);
    run.put(self + 0x2e4, 0x19);
    // fld float [0x5262b8]; fmul float [0x50f768]; __ftol (0x4a30e0).
    double scaled = double(run.getf(0x5262b8)) * double(run.getf(0x50f768));
    uint32_t converted = run.call_x87(0x4a30e0, 0, scaled);
    if (converted <= 0x63)
        converted = 0x63;
    run.put(self + 0x2e4, converted);
    uint32_t record = 0;
    if (run.get(0x537964) == 1) {
        record = run.get(self + 0xc);
        run.put(record + 0x10c, 3);
    } else {
        record = run.get(self + 0xc);
        run.put(record + 0x10c, 7);
    }
    record = run.get(self + 0xc);
    double health = double(run.gets(record + 0x10c)) * double(run.getf(0x5262b4));
    uint32_t healthInt = run.call_x87(0x4a30e0, 0, health);
    run.put(record + 0x10c, healthInt);
    record = run.get(self + 0xc);
    run.put(record + 0x104, 0xa);
    record = run.get(self + 0xc);
    double damage = double(run.gets(record + 0x104)) * double(run.getf(0x5262b0));
    uint32_t damageInt = run.call_x87(0x4a30e0, 0, damage);
    run.put(record + 0x104, damageInt);
    run.call(0x40abf0, table, {});
    function_48b6b0(run, self, nullptr);
    return self;
}

// 0x48b6b0. thiscall, 0 stack arguments, returns 0.
uint32_t function_48b6b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    run.put(self + 0x50, 0);
    run.put(self + 0x54, 0);
    uint32_t state = run.get(self + 0x10);
    run.put(self + 0x24, run.get(state + 0x1c));
    uint32_t idle = run.call(0x4dba00, 0x537668, {0x523148});
    state = run.get(self + 0x10);
    run.put(state + 0x1c, idle);
    uint32_t owner = run.get(self + 0x12c);
    uint32_t stand = run.get(self + 0x318);
    run.put(self + 0x134, run.get(owner + 0x190));
    run.call(0x4c8220, owner + 0x188, {stand});
    run.put(self + 0x478, 0xfa0);
    run.put(self + 0x474, run.get(0x537210));
    uint32_t timer = run.get(0x5430c4);
    owner = run.get(self + 0x12c);
    run.call(0x4c82a0, owner + 0x188, {timer});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48a980:
        return function_48a980(run, receiver, arguments);
    case 0x48aa40:
        return function_48aa40(run, receiver, arguments);
    case 0x48b6b0:
        return function_48b6b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_soldier_construct_tick_entry, owned, body)
