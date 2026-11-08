// Observed Level 1 level object actions batch 2
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
    case 0x44f840:
        return 0;
    case 0x44f850:
        return 1;
    case 0x452b00:
        return 1;
    case 0x452c50:
        return 1;
    case 0x462350:
        return 1;
    case 0x462410:
        return 1;
    case 0x462af0:
        return 1;
    case 0x462ef0:
        return 1;
    case 0x463120:
        return 0;
    case 0x4631e0:
        return 0;
    case 0x46a8d0:
        return 1;
    case 0x46c2c0:
        return 0;
    default:
        return -1;
    }
}

// A call through an import-table slot: the slot holds the address of the real function.
uint32_t importCall(Run &run, uint32_t slot, std::initializer_list<uint32_t> arguments) {
    uint32_t function = run.get(slot);
    return run.call(function, 0, arguments);
}

// Signed 32-bit remainder with the original idiv trap for the one overflowing case.
int32_t signedRemainder(Run &run, uint32_t dividend, uint32_t divisor) {
    int32_t numerator = s32(dividend);
    int32_t denominator = s32(divisor);
    if (denominator == -1) {
        if (numerator == INT32_MIN)
            run.fail(CLAW_FAULT_HALT, 0x44f875);
        return 0;
    }
    return numerator % denominator;
}

// Sign-folding sequence used by the original for a random parity bit:
// xor with the sign mask, subtract it, keep bit 0, then undo the fold.
uint32_t foldedParity(uint32_t value) {
    uint32_t mask = 0;
    if (value & 0x80000000)
        mask = 0xffffffff;
    uint32_t folded = value ^ mask;
    folded = folded - mask;
    folded = folded & 1;
    folded = folded ^ mask;
    folded = folded - mask;
    return folded;
}

uint32_t stringLength(Run &run, uint32_t text) {
    uint32_t length = 0;
    while (run.get8(text + length) != 0)
        length = length + 1;
    return length;
}

// Appends the NUL-terminated `source` (terminator included) to `destination`.
void appendString(Run &run, uint32_t destination, uint32_t source) {
    uint32_t count = stringLength(run, source) + 1;
    uint32_t end = destination + stringLength(run, destination);
    for (uint32_t index = 0; index < count; ++index)
        run.put8(end + index, run.get8(source + index));
}

// 0x44f840. Tail call through virtual slot 0x48 of the receiver.
uint32_t function_44f840(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return run.vcall(receiver, 0x48);
}

// 0x44f850. Bounded random number; a bound of -1 asks for a parity bit minus one (0 or -1).
uint32_t function_44f850(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t bound = arguments[0];
    if (bound == 0xffffffff) {
        uint32_t value = run.call(0x4a3050, 0, {});
        uint32_t parity = foldedParity(value);
        return parity - 1;
    }
    uint32_t value = run.call(0x4a3050, 0, {});
    return uint32_t(signedRemainder(run, value, bound + 1));
}

// 0x452c50. Fills the first variant's rectangles and the three scale floats.
uint32_t function_452c50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    run.put(record + 0x44, 0);
    importCall(run, 0x546d5c, {record + 0x58, 0xffffffe8, 0xfffffff8, 0x18, 0x20});
    importCall(run, 0x546d5c, {record + 0x78, 0xffffffe8, 0xffffffd2, 0x18, 0x20});
    importCall(run, 0x546d5c, {record + 0x68, 0xffffffe0, 0xfffffff8, 0x24, 0x20});
    run.put(0x5262b0, 0x3f800000);
    run.put(0x5262b4, 0x3f800000);
    run.put(0x5262b8, 0x3f800000);
    return 1;
}

// 0x452b00. Clears the 0x30-word variant record, stamps the variant and builds its tables.
uint32_t function_452b00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t variant = arguments[0];
    if (s32(variant) <= 0)
        return 0;
    for (uint32_t word = 0; word < 0x30; ++word)
        run.put(0x5378a0 + word * 4, 0);
    run.put(0x537960, 0x5378a0);
    run.put(0x5378a0, variant);
    run.put(0x537964, variant);
    const uint32_t recordArgument[1] = {0x5378a0};
    uint32_t index = variant - 1;
    if (index > 13)
        return 0;
    switch (index) {
    case 0:
        return function_452c50(run, 0, recordArgument);
    case 1:
        return run.call(0x452cc0, 0, {0x5378a0});
    case 2:
        return run.call(0x452d50, 0, {0x5378a0});
    case 3:
        return run.call(0x452db0, 0, {0x5378a0});
    case 4:
        return run.call(0x452ea0, 0, {0x5378a0});
    case 5:
        return run.call(0x452f80, 0, {0x5378a0});
    case 6:
        return run.call(0x453070, 0, {0x5378a0});
    case 7:
        return run.call(0x453150, 0, {0x5378a0});
    case 8:
        return run.call(0x453240, 0, {0x5378a0});
    case 9:
        return run.call(0x453310, 0, {0x5378a0});
    case 10:
        return run.call(0x453410, 0, {0x5378a0});
    case 11:
        return run.call(0x453500, 0, {0x5378a0});
    case 12:
        return run.call(0x453600, 0, {0x5378a0});
    default:
        return run.call(0x4536f0, 0, {0x5378a0});
    }
}

// Looks one animation or sound name up in an Officer's resource table, with the
// "GAME_NULL" entry as the fallback when the name is missing.
uint32_t lookupOrNull(Run &run, uint32_t table, uint32_t name) {
    uint32_t found = run.call(0x4062e0, table, {name});
    if (found == 0)
        found = run.call(0x4062e0, table, {0x5234b4});
    return found;
}

uint32_t function_463120(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x462410. Officer constructor: loads its animations, sounds and rectangles.
// Officer fields: +0x0c owner record, +0x10 state record, +0x128 resource table, +0x12c owner (animator).
// The incoming argument slot (frame + 4) doubles as the out-parameter of the resource lookups.
uint32_t function_462410(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    run.call(0x44c000, self, {arguments[0]});
    run.put(self + 0x458, 0);
    run.put(self + 0x45c, 0);
    run.put(self + 0x460, 0);
    run.put(self + 0x464, 0);
    run.put(self + 0x468, 0);
    run.put(self + 0x46c, 0);
    run.put(self, 0x50ea0c);
    run.call(0x4c7970, run.get(self + 0x12c), {0x529854});
    uint32_t table = self + 0x128;
    run.put(self + 0x308, lookupOrNull(run, table, 0x52983c));
    run.put(self + 0x30c, lookupOrNull(run, table, 0x529820));
    run.put(self + 0x310, lookupOrNull(run, table, 0x529808));
    run.put(self + 0x318, lookupOrNull(run, table, 0x5297f0));
    run.put(self + 0x31c, lookupOrNull(run, table, 0x5297d8));
    run.put(self + 0x320, lookupOrNull(run, table, 0x5297c0));
    run.put(self + 0x324, lookupOrNull(run, table, 0x5297a8));
    run.put(self + 0x328, lookupOrNull(run, table, 0x529790));
    run.put(self + 0x32c, lookupOrNull(run, table, 0x52977c));
    run.put(self + 0x374, lookupOrNull(run, table, 0x52977c));
    run.put(self + 0x334, lookupOrNull(run, table, 0x529764));
    run.put(self + 0x338, lookupOrNull(run, table, 0x52974c));
    run.put(self + 0x33c, lookupOrNull(run, table, 0x529738));
    run.put(self + 0x340, lookupOrNull(run, table, 0x529738));
    run.put(self + 0x344, lookupOrNull(run, table, 0x529724));
    run.put(self + 0x34c, lookupOrNull(run, table, 0x529820));
    run.put(self + 0x378, lookupOrNull(run, table, 0x52970c));
    run.put(self + 0x37c, lookupOrNull(run, table, 0x5296f4));
    run.put(self + 0x380, lookupOrNull(run, table, 0x5296f4));
    run.put(self + 0x36c, lookupOrNull(run, table, 0x5296dc));
    uint32_t outParameter = run.automatic(4);
    uint32_t randomValue = run.call(0x4a3050, 0, {});
    if (s32(randomValue) % 100 < 0x32) {
        uint32_t owner = run.get(self + 0x12c);
        uint32_t soundTable = run.get(run.get(owner + 0xc) + 0x28) + 0x10;
        run.put(outParameter, 0);
        run.call(0x4f6286, soundTable, {0x5296c4, outParameter});
        run.put(self + 0x3a4, run.get(outParameter));
    } else {
        uint32_t owner = run.get(self + 0x12c);
        uint32_t soundTable = run.get(run.get(owner + 0xc) + 0x28) + 0x10;
        run.put(outParameter, 0);
        run.call(0x4f6286, soundTable, {0x5296ac, outParameter});
        run.put(self + 0x3a4, run.get(outParameter));
    }
    uint32_t owner = run.get(self + 0x12c);
    run.put(outParameter, 0);
    uint32_t soundTable = run.get(run.get(owner + 0xc) + 0x28) + 0x10;
    run.call(0x4f6286, soundTable, {0x529694, outParameter});
    run.put(self + 0x410, run.get(outParameter));
    owner = run.get(self + 0x12c);
    soundTable = run.get(run.get(owner + 0xc) + 0x28) + 0x10;
    run.put(outParameter, 0);
    run.call(0x4f6286, soundTable, {0x529678, outParameter});
    run.put(self + 0x3a0, run.get(outParameter));
    owner = run.get(self + 0x12c);
    uint32_t soundOwner = run.get(run.get(owner + 0xc) + 0x28);
    run.put(self + 0x450, run.call(0x4061b0, soundOwner, {0x529664}));
    owner = run.get(self + 0x12c);
    soundOwner = run.get(run.get(owner + 0xc) + 0x28);
    uint32_t secondSound = run.call(0x4061b0, soundOwner, {0x529650});
    run.put(self + 0x454, secondSound);
    importCall(run, 0x546d5c, {self + 0x230, 0xffffff77, 0xffffffe5, 0, 0xfffffff9});
    importCall(run, 0x546d5c, {self + 0x240, 0xffffff77, 0x14, 0, 0x28});
    run.put(self + 0x220, run.get(self + 0x230));
    run.put(self + 0x224, run.get(self + 0x234));
    run.put(self + 0x228, run.get(self + 0x238));
    run.put(self + 0x22c, run.get(self + 0x23c));
    importCall(run, 0x546d5c, {self + 0x210, 0xffffffff, 0xffffffff, 1, 1});
    importCall(run, 0x546d5c, {self + 0x250, 0xffffffec, 0xffffffc4, 0x14, 0x33});
    importCall(run, 0x546d5c, {self + 0x260, 0xffffffd0, 0xffffffd4, 0x2a, 0x13});
    run.put(self + 0x28c, 100);
    run.put(self + 0x290, 0x28);
    run.put(self + 0x294, 100);
    run.put(self + 0x298, 0x28);
    run.put(self + 0x29c, 100);
    run.put(self + 0x2a0, 0x28);
    run.put(self + 0x2a4, 100);
    run.put(self + 0x2a8, 0x28);
    run.put(self + 0x2ac, 100);
    run.put(self + 0x2b0, 0x28);
    run.call(0x4208b0, run.get(self + 0x12c), {0xffffffec, 0xffffffce, 0x14, 0x32});
    uint32_t boxLeft = run.get(self + 0x250);
    uint32_t boxTop = run.get(self + 0x254);
    uint32_t boxRight = run.get(self + 0x258);
    uint32_t boxBottom = run.get(self + 0x25c);
    run.call(0x40f6c0, run.get(self + 0x12c), {boxLeft, boxTop, boxRight, boxBottom});
    run.put(self + 0x2b8, 0xfffffff6);
    run.put(self + 0x2b4, 10);
    run.put(self + 0x2bc, 0xffffffd3);
    run.put(self + 0x2c0, 0xffffffec);
    run.put(self + 0x2c4, 0x14);
    run.put(self + 0x2c8, 0xfffffff1);
    run.put(self + 0x2e4, 0x32);
    double healthScale = double(run.getf(0x5262b8)) * double(run.getf(0x50ea00));
    uint32_t health = run.call_x87(0x4a30e0, 0, healthScale, {});
    if (health < 100)
        health = 99;
    run.put(self + 0x2e4, health);
    if (run.get(0x537964) == 1)
        run.put(run.get(self + 0xc) + 0x10c, 3);
    else
        run.put(run.get(self + 0xc) + 0x10c, 7);
    uint32_t damageOwner = run.get(self + 0xc);
    double damageScale = double(s32(run.get(damageOwner + 0x10c))) * double(run.getf(0x5262b4));
    uint32_t damage = run.call_x87(0x4a30e0, 0, damageScale, {});
    run.put(damageOwner + 0x10c, damage);
    run.put(run.get(self + 0xc) + 0x104, 10);
    uint32_t speedOwner = run.get(self + 0xc);
    double speedScale = double(s32(run.get(speedOwner + 0x104))) * double(run.getf(0x5262b0));
    uint32_t speed = run.call_x87(0x4a30e0, 0, speedScale, {});
    run.put(speedOwner + 0x104, speed);
    run.call(0x40abf0, table, {});
    uint32_t idleArguments[1] = {0};
    function_463120(run, self, idleArguments);
    return self;
}

// 0x462350. Dispatches on the state record's event: constructs the Officer on event 0,
// forwards 0x1d and 0x1e to it, ignores 0x3e8 and sends everything else to the generic handler.
uint32_t function_462350(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t owner = arguments[0];
    uint32_t state = run.get(owner + 0x6c);
    uint32_t event = run.get(state + 0x1c);
    if (event > 0x1d) {
        if (event == 0x1e) {
            run.vcall(run.get(state + 0x18), 0x1c);
            return 1;
        }
        if (event == 0x3e8)
            return 1;
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    if (event == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
        return 1;
    }
    if (event != 0) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    run.put(state + 0x1c, 0x3e8);
    uint32_t memory = run.call(0x4f63ec, 0, {0x470});
    uint32_t officer = 0;
    if (memory != 0) {
        uint32_t constructorArguments[1] = {owner};
        uint32_t callerFrame = run.frame;
        run.frame = callerFrame - 0x1c;
        officer = function_462410(run, memory, constructorArguments);
        run.frame = callerFrame;
    }
    run.vcall(officer, 0x10);
    run.put(state + 0x18, officer);
    return 1;
}

// 0x462af0. Dispatches an event id through the growable handler table at 0x537ba0.
// Table fields: 0x537ba8 lowest id, 0x537bac highest id, 0x537bb0 entries, 0x537bb8 stride,
// 0x537bb4 fallback entry, 0x537bc0 flag.
uint32_t function_462af0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t ident = arguments[0];
    uint32_t low = run.get(0x537ba8);
    run.put(0x537bc0, 0);
    uint32_t entry = 0;
    if (s32(ident) < s32(low) || s32(ident) > s32(run.get(0x537bac))) {
        uint32_t found = run.call(0x4db6e0, 0x537ba0, {ident, 0});
        if (found == 0) {
            uint32_t message = run.get(0x544b4c);
            uint32_t code = run.call(0x4db5f0, 0, {});
            uint32_t context = run.get(0x537ba4);
            run.put(0x544b14, code);
            run.call(0x4db4d0, context, {0x537ba0, message, 0xc});
            entry = run.get(0x537bb4);
            low = run.get(0x537ba8);
        } else {
            low = run.get(0x537ba8);
            entry = (ident - low) * run.get(0x537bb8) + run.get(0x537bb0);
        }
    } else {
        entry = (ident - low) * run.get(0x537bb8) + run.get(0x537bb0);
    }
    if (run.get(entry) == 0) {
        run.call(0x44c840, receiver, {ident});
        return 0;
    }
    run.put(0x537bc0, 0);
    if (s32(ident) < s32(low) || s32(ident) > s32(run.get(0x537bac))) {
        uint32_t found = run.call(0x4db6e0, 0x537ba0, {ident, 0});
        if (found == 0) {
            uint32_t message = run.get(0x544b4c);
            uint32_t code = run.call(0x4db5f0, 0, {});
            uint32_t context = run.get(0x537ba4);
            run.put(0x544b14, code);
            run.call(0x4db4d0, context, {0x537ba0, message, 0xc});
            uint32_t fallback = run.get(0x537bb4);
            run.call(run.get(fallback), receiver, {});
            return 0;
        }
        low = run.get(0x537ba8);
    }
    uint32_t handlerEntry = (ident - low) * run.get(0x537bb8) + run.get(0x537bb0);
    run.call(run.get(handlerEntry), receiver, {});
    return 0;
}

// 0x462ef0. Picks the strike box and strike animation for the Officer.
// Fields: +0x220 active box, +0x230 and +0x240 the two strike boxes, +0x310 strike animation.
uint32_t function_462ef0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    run.call(0x44d000, self, {arguments[0]});
    uint32_t outParameter = run.automatic(4);
    uint32_t spareParameter = run.automatic(-4);
    if (run.get(run.get(0x537e88) + 0xcc) == 5) {
        run.put(outParameter, 0);
        run.put(self + 0x220, run.get(self + 0x240));
        run.put(self + 0x224, run.get(self + 0x244));
        run.put(self + 0x228, run.get(self + 0x248));
        run.put(self + 0x22c, run.get(self + 0x24c));
        uint32_t owner = run.get(self + 0x12c);
        uint32_t table = run.get(run.get(owner + 0xc) + 0x2c) + 0x10;
        run.call(0x4f6286, table, {0x529870, outParameter});
        if (run.get(outParameter) == 0) {
            run.put(spareParameter, 0);
            owner = run.get(self + 0x12c);
            table = run.get(run.get(owner + 0xc) + 0x2c) + 0x10;
            run.call(0x4f6286, table, {0x5234b4, spareParameter});
            run.put(self + 0x310, run.get(spareParameter));
            return 0;
        }
        run.put(self + 0x310, run.get(outParameter));
        return 0;
    }
    run.put(outParameter, 0);
    run.put(self + 0x220, run.get(self + 0x230));
    run.put(self + 0x224, run.get(self + 0x234));
    run.put(self + 0x228, run.get(self + 0x238));
    run.put(self + 0x22c, run.get(self + 0x23c));
    uint32_t owner = run.get(self + 0x12c);
    uint32_t table = run.get(run.get(owner + 0xc) + 0x2c) + 0x10;
    run.call(0x4f6286, table, {0x529808, outParameter});
    uint32_t animation = run.get(outParameter);
    if (animation == 0) {
        run.put(spareParameter, 0);
        owner = run.get(self + 0x12c);
        table = run.get(run.get(owner + 0xc) + 0x2c) + 0x10;
        run.call(0x4f6286, table, {0x5234b4, spareParameter});
        animation = run.get(spareParameter);
    }
    run.put(self + 0x310, animation);
    return 0;
}

// 0x463120. Returns the Officer to its idle pose, sometimes with a sound first.
uint32_t function_463120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    run.put(self + 0x50, 0);
    run.put(self + 0x54, 0);
    uint32_t chance = run.call(0x4a3050, 0, {});
    if (s32(chance) % 100 < 0x21) {
        uint32_t pick = run.call(0x4a3050, 0, {});
        uint32_t index = foldedParity(pick);
        uint32_t owner = run.get(self + 0x12c);
        uint32_t gate = run.get(owner + 0x38);
        uint32_t sound = run.get(self + index * 4 + 0x450);
        if (gate != 0xffffffff)
            run.call(0x48ce40, 0, {run.get(self + 0xc), sound, 0});
    }
    uint32_t state = run.get(self + 0x10);
    run.put(self + 0x24, run.get(state + 0x1c));
    uint32_t idle = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(self + 0x10) + 0x1c, idle);
    uint32_t owner = run.get(self + 0x12c);
    uint32_t standing = run.get(self + 0x318);
    uint32_t frameTime = run.get(owner + 0x190);
    uint32_t animator = owner + 0x188;
    run.put(self + 0x134, frameTime);
    run.call(0x4c8220, animator, {standing});
    run.call(0x4c82a0, animator, {run.get(0x5430c4)});
    run.put(self + 0x46c, 0xfa0);
    run.put(self + 0x468, run.get(0x537210));
    return 0;
}

// 0x4631e0. Per-tick Officer behaviour: rotates stand animations, then acts on the state.
uint32_t function_4631e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t ticks = run.get(0x537210);
    uint32_t lastChange = run.get(self + 0x458);
    uint32_t interval = run.get(self + 0x45c);
    if (ticks - lastChange >= interval) {
        run.put(self + 0x45c, 1000);
        run.put(self + 0x458, run.get(0x537210));
        uint32_t pick = run.call(0x4a3050, 0, {});
        uint32_t remainder = uint32_t(s32(pick) % 5);
        if (remainder <= 4) {
            uint32_t animation = 0;
            switch (remainder) {
            case 0:
                animation = run.get(self + 0x318);
                break;
            case 1:
                animation = run.get(self + 0x31c);
                break;
            case 2:
                animation = run.get(self + 0x320);
                break;
            case 3:
                animation = run.get(self + 0x324);
                break;
            default:
                animation = run.get(self + 0x328);
                break;
            }
            uint32_t owner = run.get(self + 0x12c);
            uint32_t frameTime = run.get(owner + 0x190);
            uint32_t animator = owner + 0x188;
            run.put(self + 0x134, frameTime);
            run.call(0x4c8220, animator, {animation});
            run.call(0x4c82a0, animator, {run.get(0x5430c4)});
        }
    }
    uint32_t mode = run.get(self + 0x184);
    if (mode > 6)
        return 0;
    if (mode <= 4) {
        run.vcall(self, 0x44);
        return 0;
    }
    uint32_t sinceStrike = run.get(0x537210) - run.get(self + 0x468);
    if (sinceStrike < run.get(self + 0x46c))
        return 0;
    uint32_t chance = run.call(0x4a3050, 0, {});
    if (s32(chance) % 100 >= 0x14)
        return 0;
    run.call(0x44edd0, self, {});
    return 0;
}

// Calls original code the way function 0x46a8d0 does: three registers are saved on entry and the
// arguments are pushed, so the callee's entry ESP sits that far below this function's entry frame.
uint32_t callFromMenu(Run &run, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments) {
    run.stackPointer = run.frame - 0x10 - 4 * uint32_t(arguments.size());
    uint32_t result = run.call(function, receiver, arguments);
    run.stackPointer = 0;
    return result;
}

uint32_t virtualFromMenu(Run &run, uint32_t object, uint32_t offset, std::initializer_list<uint32_t> arguments) {
    run.stackPointer = run.frame - 0x10 - 4 * uint32_t(arguments.size());
    uint32_t result = run.vcall(object, offset, arguments);
    run.stackPointer = 0;
    return result;
}

// Repeats ShowCursor(0) until the display counter is negative.
void hideCursor(Run &run) {
    uint32_t count = importCall(run, 0x546d54, {0});
    while (s32(count) >= 0)
        count = importCall(run, 0x546d54, {0});
}

// 0x46a8d0. Leaves the Officer-style pause menu: hides the cursor and restores the game for the
// given exit reason (9 resume, 10 nothing, 11 and 12 full restore, anything else partial).
uint32_t function_46a8d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    uint32_t reason = arguments[0];
    hideCursor(run);
    if (reason == 10)
        return 1;
    callFromMenu(run, 0x42d1f0, run.get(self + 0x4), {0});
    if (reason == 0xb || reason == 0xc) {
        uint32_t source = self + 0x360;
        if (run.get(self + 0x2c) != 0) {
            uint32_t target = run.get(run.get(run.get(self + 0x2c) + 0x10) + 0x10);
            if (target != 0) {
                for (uint32_t word = 0; word < 0x100; ++word)
                    run.put(target + word * 4, run.get(source + word * 4));
            }
        }
        callFromMenu(run, 0x46ddc0, self, {});
        callFromMenu(run, 0x42abf0, run.get(self + 0x4), {});
        run.put(0x537210, run.get(self + 0x760));
        callFromMenu(run, 0x431300, run.get(0x537204), {});
        run.put(run.get(0x537204) + 0xc, 0xffffffff);
        callFromMenu(run, 0x4b3ab0, run.get(0x537200), {});
        run.put(run.get(0x537200) + 0x20c, 0xffffffff);
        return 1;
    }
    if (callFromMenu(run, 0x42af50, run.get(self + 0x4), {}) == 0) {
        if (callFromMenu(run, 0x42a000, run.get(self + 0x4), {1}) == 0)
            return 0;
    }
    hideCursor(run);
    callFromMenu(run, 0x42abf0, run.get(self + 0x4), {});
    if (reason != 9) {
        uint32_t menu = run.get(self + 0x2c);
        callFromMenu(run, 0x4bb990, run.get(menu + 0x10), {0, 0x100, 0, 0, 0, 0xfa});
        callFromMenu(run, 0x4caaa0, run.get(run.get(self + 0xc) + 0x4), {0});
        menu = run.get(self + 0x2c);
        callFromMenu(run, 0x4bb800, run.get(menu + 0x10), {0, 0x100, self + 0x360, 0});
        callFromMenu(run, 0x4bb870, run.get(run.get(self + 0x2c) + 0x10), {});
        virtualFromMenu(run, run.get(run.get(self + 0xc) + 0x8), 0x24, {1});
        uint32_t game = run.get(self + 0xc);
        callFromMenu(run, 0x4cb9b0, run.get(game + 0x24), {run.get(run.get(game + 0x4) + 0x14), run.get(game + 0x8)});
        game = run.get(self + 0xc);
        uint32_t device = run.get(game + 0xc);
        uint32_t view = run.get(game + 0x4);
        virtualFromMenu(run, device, 0x34, {run.get(view + 0x14), run.get(view + 0x18)});
        uint32_t panel = run.get(run.get(self + 0xc) + 0x24);
        uint32_t panelItem = run.get(panel + 0x5c);
        if (panelItem != 0)
            callFromMenu(run, 0x4d2000, panelItem, {});
        callFromMenu(run, 0x490130, self, {0x529fa8, 0x32, 0x5dc});
        uint32_t window = run.get(self + 0x4);
        uint32_t windowItem = run.get(window + 0x14);
        if (windowItem != 0)
            callFromMenu(run, 0x4b54f0, run.get(window + 0x50), {0x524d80, 1});
    } else {
        virtualFromMenu(run, run.get(run.get(self + 0xc) + 0x8), 0x24, {1});
        uint32_t game = run.get(self + 0xc);
        callFromMenu(run, 0x4cb9b0, run.get(game + 0x24), {run.get(run.get(game + 0x4) + 0x14), run.get(game + 0x8)});
        game = run.get(self + 0xc);
        uint32_t device = run.get(game + 0xc);
        uint32_t view = run.get(game + 0x4);
        virtualFromMenu(run, device, 0x34, {run.get(view + 0x14), run.get(view + 0x18)});
        game = run.get(self + 0xc);
        callFromMenu(run, 0x4b98b0, run.get(run.get(run.get(game + 0x4) + 0x10) + 0x2c), {0});
        uint32_t panel = run.get(run.get(self + 0xc) + 0x24);
        uint32_t panelItem = run.get(panel + 0x5c);
        if (panelItem != 0)
            callFromMenu(run, 0x4d2000, panelItem, {});
        callFromMenu(run, 0x48f470, self, {0xfa});
    }
    callFromMenu(run, 0x42abf0, run.get(self + 0x4), {});
    if (reason != 9)
        return 1;
    run.put(0x537210, run.get(self + 0x760));
    return 1;
}

// Calls original code the way function 0x46c2c0 does: its frame is 0x264 bytes deep at the call
// sites, so the callee's entry ESP is that far below the entry frame, less the pushed arguments.
uint32_t callFromOverlay(Run &run, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments) {
    run.stackPointer = run.frame - 0x268 - 4 * uint32_t(arguments.size());
    uint32_t result = run.call(function, receiver, arguments);
    run.stackPointer = 0;
    return result;
}

// 0x46c2c0. Draws the debug overlay text: builds a status line from the flag byte at 0x537264
// (0x10 fps, 0x01 objects, 0x04 position, 0x40 timing, 0x80 clock, 0x02 extra) and paints it on the
// back buffer's device context. Locals: text at frame - 0x20c, scratch at frame - 0x24c.
uint32_t function_46c2c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t flags = run.get8(0x537264);
    if (flags & 0x20)
        return 0;
    uint32_t text = run.automatic(-0x20c);
    uint32_t scratch = run.automatic(-0x24c);
    uint32_t clock = run.automatic(-0x250);
    uint32_t deviceContext = run.automatic(-0x254);
    run.put8(text, 0);
    if (flags & 0x10) {
        uint32_t view = run.get(self + 0x4);
        callFromOverlay(run, 0x4a3920, 0, {scratch, 0x52a044, run.get(view + 0x18)});
        appendString(run, text, scratch);
        flags = run.get8(0x537264);
    }
    if (flags & 0x01) {
        uint32_t game = run.get(self + 0xc);
        uint32_t objects = run.get(game + 0x8);
        callFromOverlay(run, 0x4a3920, 0, {scratch, 0x52a070, run.get(objects + 0x1c)});
        appendString(run, text, scratch);
        flags = run.get8(0x537264);
    }
    if (flags & 0x04) {
        uint32_t player = run.get(0x537e88);
        callFromOverlay(run, 0x4a3920, 0, {scratch, 0x52a060, run.get(player + 0x4c), run.get(player + 0x50)});
        appendString(run, text, scratch);
        flags = run.get8(0x537264);
    }
    if (flags & 0x40)
        appendString(run, text, 0x52a050);
    if (flags & 0x80) {
        uint32_t ticks = run.get(0x537210);
        callFromOverlay(run, 0x49c860, 0, {clock, ticks});
        callFromOverlay(run, 0x4f6920, clock, {0x52a040});
        appendString(run, text, run.get(clock));
        callFromOverlay(run, 0x4f6920, clock, {0x52a040});
        callFromOverlay(run, 0x4f6584, clock, {});
        flags = run.get8(0x537264);
    }
    if (flags & 0x02) {
        uint32_t view = run.get(self + 0x4);
        uint32_t viewItem = run.get(run.get(view + 0x30) + 0x8);
        uint32_t layer = run.get(self + 0x14c);
        uint32_t counted = run.get(viewItem + 0x1c);
        // The slot at +0x50 takes its two arguments on the stack and the caller removes them
        // only after formatting, so the formatter sees both of them again after the result.
        uint32_t method = run.get(run.get(self) + 0x50);
        run.stackPointer = run.frame - 0x270;
        uint32_t reading = run.call(method, self, {layer, counted});
        callFromOverlay(run, 0x4a3920, 0, {scratch, 0x52a01c, reading, layer, counted});
        appendString(run, text, scratch);
    }
    uint32_t kind = run.vcall(self, 0x10);
    if (kind != 4) {
        if (run.get8(text) == 0) {
            uint32_t view = run.get(self + 0x4);
            uint32_t viewItem = run.get(run.get(view + 0x4c) + 0xc);
            if (viewItem == 0) {
                callFromOverlay(run, 0x4224f0, run.get(view + 0x4c), {run.get(0x53720c)});
                return 0;
            }
        }
    }
    uint32_t game = run.get(self + 0xc);
    uint32_t surfaceOwner = run.get(run.get(run.get(game + 0x4) + 0x14) + 0x2c);
    run.put(run.automatic(-0x254), 0);
    uint32_t surface = run.get(surfaceOwner + 0x8);
    uint32_t getContext = run.get(run.get(surface) + 0x44);
    run.call(getContext, 0, {surface, deviceContext});
    uint32_t context = run.get(deviceContext);
    if (context == 0)
        return 0;
    importCall(run, 0x546888, {context, 1});
    importCall(run, 0x546880, {run.get(deviceContext), 0xffffff});
    run.vcall(self, 0x64, {run.get(deviceContext)});
    if (run.get8(text) != 0) {
        uint32_t left = run.get(0x5370c8);
        uint32_t bottom = run.get(0x5370d4);
        uint32_t right = run.get(0x5370d0);
        uint32_t top = bottom - 0x1c;
        uint32_t box = run.automatic(-0x24c);
        run.put(box, left);
        run.put(box + 0x8, right);
        run.put(box + 0x4, top);
        run.put(box + 0xc, bottom);
        if (s32(left) > 0) {
            importCall(run, 0x546d30, {run.get(deviceContext), text, 0xffffffff, box, 0x20});
        } else {
            uint32_t length = stringLength(run, text);
            importCall(run, 0x546890, {run.get(deviceContext), 0, top, text, length});
        }
    }
    uint32_t releaseSurface = run.get(surfaceOwner + 0x8);
    uint32_t releaseContext = run.get(run.get(releaseSurface) + 0x68);
    run.call(releaseContext, 0, {releaseSurface, run.get(deviceContext)});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x44f840:
        return function_44f840(run, receiver, arguments);
    case 0x44f850:
        return function_44f850(run, receiver, arguments);
    case 0x452b00:
        return function_452b00(run, receiver, arguments);
    case 0x452c50:
        return function_452c50(run, receiver, arguments);
    case 0x462350:
        return function_462350(run, receiver, arguments);
    case 0x462410:
        return function_462410(run, receiver, arguments);
    case 0x462af0:
        return function_462af0(run, receiver, arguments);
    case 0x462ef0:
        return function_462ef0(run, receiver, arguments);
    case 0x463120:
        return function_463120(run, receiver, arguments);
    case 0x4631e0:
        return function_4631e0(run, receiver, arguments);
    case 0x46a8d0:
        return function_46a8d0(run, receiver, arguments);
    case 0x46c2c0:
        return function_46c2c0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_object_actions_02_entry, owned, body)
