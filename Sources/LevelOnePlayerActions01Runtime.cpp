// Observed Level 1 player actions batch 1
//
// Recovered from the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"
#include <cmath>
#include <cstring>

namespace {

using claw::Run;
using claw::s32;
using claw::recovered::v10::ActorFields;
using claw::recovered::v10::LogicHolderFields;
using claw::recovered::v10::ActorContextFields;
using claw::recovered::v10::BounceLogicState;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x40e690:
        return 1;
    case 0x40e750:
        return 1;
    case 0x40ebe0:
        return 1;
    case 0x40efa0:
        return 0;
    case 0x40f010:
        return 0;
    case 0x40f0e0:
        return 0;
    case 0x40f200:
        return 0;
    case 0x40f2a0:
        return 0;
    case 0x40f6a0:
        return 1;
    case 0x40f6f0:
        return 0;
    case 0x40f760:
        return 1;
    default:
        return -1;
    }
}

// Low and high 32-bit halves of a binary64 value, as pushed on the stack.
uint32_t lowWord(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    return uint32_t(bits);
}

uint32_t highWord(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    return uint32_t(bits >> 32);
}

uint32_t dispatchBounceLogic(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t constructBounceLogic(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t dispatchActionHandler(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t enterFallingAnimation(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t stepFallingAnimation(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t enterBounceAnimation(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t stepBounceAnimation(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t refreshDeadHandler(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t setUnknown0x64AndMarkChanged(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t resetMotionVectorDefaults(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t bindActorContext(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x40e690. cdecl, one argument: the actor. Drives the logic state machine
// held in actor+0x6c: +0x1c is the state, +0x18 the logic object. Always
// returns 1.
uint32_t dispatchBounceLogic(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Views retain 32-bit guest tokens and access memory only through run.
    ActorFields actor{run, arguments[0]};
    uint32_t holder = actor.holder();
    LogicHolderFields holderFields{run, holder};
    uint32_t state = holderFields.state();
    if (state == uint32_t(BounceLogicState::CallVirtual20)) {
        uint32_t logic = holderFields.logic();
        run.vcall(logic, 0x20);
        return 1;
    }
    if (state == uint32_t(BounceLogicState::Uninitialized)) {
        holderFields.state(uint32_t(BounceLogicState::Initialized));
        uint32_t memory = run.call(0x4f63ec, 0, {0x1a0});
        uint32_t logic = 0;
        if (memory != 0) {
            uint32_t made[1] = {actor};
            logic = constructBounceLogic(run, memory, made);
        }
        run.vcall(logic, 0x10);
        holderFields.logic(logic);
        return 1;
    }
    if (state == uint32_t(BounceLogicState::CallVirtual1c)) {
        uint32_t logic = holderFields.logic();
        run.vcall(logic, 0x1c);
        return 1;
    }
    if (state == uint32_t(BounceLogicState::Initialized))
        return 1;
    uint32_t logic = holderFields.logic();
    run.call(0x4dc870, 0, {logic});
    return 1;
}

// Appends one entry to the slot list at base+0x2c. base+0x24 is the fill
// index, base+0x28 counts the non-zero entries met. The value comes from
// [[base+holderOffset]+valueOffset].
void appendSlot(Run &run, uint32_t base, uint32_t holderOffset, uint32_t valueOffset) {
    uint32_t index = run.get(base + 0x24);
    uint32_t previous = run.get(base + index * 4 + 0x2c);
    index = index + 1;
    run.put(base + 0x24, index);
    if (previous != 0) {
        uint32_t counted = run.get(base + 0x28);
        run.put(base + 0x28, counted + 1);
    }
    uint32_t holder = run.get(base + holderOffset);
    uint32_t value = run.get(holder + valueOffset);
    run.put(base + index * 4 + 0x2c, value);
}

// Stores a double from an integer field, or a constant pair when it is zero.
void storeCounted(Run &run, uint32_t object, uint32_t sourceOffset, uint32_t target, uint32_t lowConstant) {
    uint32_t inner = run.get(object + 0x10);
    uint32_t count = run.get(inner + sourceOffset);
    if (count == 0) {
        uint32_t low = run.get(lowConstant);
        uint32_t high = run.get(lowConstant + 4);
        run.put(object + target, low);
        run.put(object + target + 4, high);
    } else {
        double converted = double(s32(count));
        run.putd(object + target, converted);
    }
}

// 0x40e750. thiscall, one argument: the actor. Constructs the bounce logic
// object in place and returns it.
uint32_t constructBounceLogic(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    ActorFields actor{run, arguments[0]};
    run.call(0x4082f0, self, {actor});
    uint32_t sprite = self + 0x28;
    run.call(0x4080a0, sprite);
    run.put(self, 0x50b2a4);
    storeCounted(run, self, 0x2c, 0x80, 0x513e10);
    storeCounted(run, self, 0x34, 0x88, 0x513e10);
    storeCounted(run, self, 0x30, 0x98, 0x513e18);
    storeCounted(run, self, 0x38, 0xa0, 0x513e18);
    uint32_t clock = run.get(0x537210);
    double scaledClock = double(clock);
    double scale = run.getd(0x50b6b8);
    scaledClock = scaledClock * scale;
    uint32_t owner = run.get(self + 0xc);
    double d4c = double(s32(run.get(owner + 0x4c)));
    double d50 = double(s32(run.get(owner + 0x50)));
    double d148 = double(s32(run.get(owner + 0x148)));
    double d14c = double(s32(run.get(owner + 0x14c)));
    run.call(0x408220, sprite,
             {lowWord(d4c), highWord(d4c), lowWord(d50), highWord(d50), 0, 0,
              lowWord(d148), highWord(d148), lowWord(d14c), highWord(d14c),
              0, 0, 0, 0, 0, 0, 0, 0,
              lowWord(scaledClock), highWord(scaledClock), 0, 0});
    uint32_t extra = run.get(0x513e40);
    double extraValue = double(extra);
    run.call(0x4082d0, sprite, {lowWord(extraValue), highWord(extraValue)});
    owner = run.get(self + 0xc);
    run.put(self + 0x120, 0);
    run.put(self + 0x124, 0);
    run.put(owner + 0xcc, 7);
    run.call(0x4dca10, self);
    uint32_t context = self + 0x128;
    uint32_t bind[1] = {actor};
    bindActorContext(run, context, bind);
    // Context fields: +0x50 and +0x54 actor, +0x58 its +0x6c block, +0x24
    // fill index, +0x28 non-zero count, +0x2c first of the slot list.
    run.put(context + 0x50, actor);
    run.put(context + 0x54, actor);
    uint32_t block = actor.holder();
    run.put(context + 0x28, 0);
    run.put(context + 0x58, block);
    run.put(context + 0x24, 0);
    uint32_t first = run.get(block + 0xf0);
    run.put(context + 0x2c, first);
    // Nine checks of the slot list, eight of them followed by an append.
    uint32_t index = run.get(context + 0x24);
    uint32_t previous = run.get(context + index * 4 + 0x2c);
    run.put(context + 0x24, index + 1);
    if (previous != 0) {
        uint32_t counted = run.get(context + 0x28);
        run.put(context + 0x28, counted + 1);
    }
    uint32_t holder = run.get(context + 0x58);
    uint32_t value = run.get(holder + 0xf8);
    run.put(context + (index + 1) * 4 + 0x2c, value);
    appendSlot(run, context, 0x58, 0xf4);
    appendSlot(run, context, 0x58, 0xfc);
    appendSlot(run, context, 0x58, 0x100);
    appendSlot(run, context, 0x58, 0x108);
    appendSlot(run, context, 0x58, 0x104);
    appendSlot(run, context, 0x58, 0x10c);
    appendSlot(run, context, 0x54, 0x100);
    index = run.get(context + 0x24);
    previous = run.get(context + index * 4 + 0x2c);
    run.put(context + 0x24, index + 1);
    if (previous != 0) {
        uint32_t counted = run.get(context + 0x28);
        run.put(context + 0x28, counted + 1);
    }
    run.put(self + 0x198, 0);
    run.put(self + 0x19c, 0);
    run.put(self, 0x50b68c);
    uint32_t cycle = run.get(actor + 0x190);
    if (cycle == 0) {
        uint32_t board = run.get(self + 0x12c);
        uint32_t table = run.get(board + 0xc);
        uint32_t named = run.get(table + 0x2c);
        uint32_t found = run.call(0x4061b0, named, {0x5240d8});
        run.put(self + 0x18c, found);
    } else {
        run.put(self + 0x18c, cycle);
    }
    run.put(self + 0x190, 0);
    run.put(self + 0x194, 0);
    run.call(0x406290, run.get(self + 0x12c));
    uint32_t rectangle = run.automatic(-28);
    run.call(0x4061e0, run.get(self + 0x12c), {rectangle});
    run.call(0x4ffa56, rectangle, {10, 10, 10, 0});
    uint32_t r0 = run.get(rectangle);
    uint32_t r1 = run.get(rectangle + 4);
    uint32_t r2 = run.get(rectangle + 8);
    uint32_t r3 = run.get(rectangle + 0xc);
    run.call(0x40f6c0, run.get(self + 0x12c), {r0, r1, r2, r3});
    run.call(0x406240, run.get(self + 0x12c));
    uint32_t sound = run.call(0x40f780, context, {0x5240c8});
    owner = run.get(self + 0xc);
    run.put(self + 0x188, sound);
    if (run.get(owner + 0x64) == 0) {
        uint32_t flagArgument[1] = {0x3e8};
        setUnknown0x64AndMarkChanged(run, owner, flagArgument);
    }
    uint32_t parent = run.get(self + 4);
    if (parent != 0) {
        uint32_t parentOwner = run.get(parent + 0xc);
        uint32_t parentValue = run.get(parentOwner + 0x64);
        uint32_t flagArgument[1] = {parentValue + 0x1f4};
        setUnknown0x64AndMarkChanged(run, run.get(self + 0xc), flagArgument);
    }
    resetMotionVectorDefaults(run, sprite, nullptr);
    owner = run.get(self + 0xc);
    run.put(owner + 0xcc, 7);
    uint32_t board = run.get(self + 0x12c);
    uint32_t flags = run.get(board + 8);
    run.put(board + 8, flags | 3);
    board = run.get(self + 0x12c);
    run.put(board + 0xd0, 1);
    enterFallingAnimation(run, self, nullptr);
    return self;
}

// Returns the address of the 0x5349e0 table entry for an id (table minimum
// at 0x5349e8, maximum at 0x5349ec, base at 0x5349f0, stride at 0x5349f8), or
// the default entry when the lookup misses. `low` carries the minimum as last
// read.
uint32_t handlerEntry(Run &run, uint32_t id, uint32_t &low) {
    bool inRange = true;
    if (s32(id) < s32(low))
        inRange = false;
    else if (s32(id) > s32(run.get(0x5349ec)))
        inRange = false;
    if (!inRange) {
        uint32_t found = run.call(0x4db6e0, 0x5349e0, {id, 0});
        if (found == 0) {
            uint32_t name = run.get(0x544b4c);
            uint32_t code = run.call(0x4db5f0, 0);
            uint32_t owner = run.get(0x5349e4);
            run.put(0x544b14, code);
            run.call(0x4db4d0, owner, {0x5349e0, name, 0xc});
            uint32_t entry = run.get(0x5349f4);
            low = run.get(0x5349e8);
            return entry;
        }
        low = run.get(0x5349e8);
    }
    uint32_t offset = id - low;
    uint32_t base = run.get(0x5349f0);
    offset = offset * run.get(0x5349f8);
    return offset + base;
}

// 0x40ebe0. thiscall, one argument: a handler id. Calls the handler table
// entry for the id on the receiver, or the generic fallback when the entry
// is empty.
uint32_t dispatchActionHandler(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t id = arguments[0];
    uint32_t low = run.get(0x5349e8);
    run.put(0x534a00, 0);
    uint32_t entry = handlerEntry(run, id, low);
    if (run.get(entry) == 0) {
        run.call(0x4a36f0, 0, {receiver});
        return 0;
    }
    run.put(0x534a00, 0);
    uint32_t target = handlerEntry(run, id, low);
    run.call(run.get(target), receiver);
    return 0;
}

// 0x40efa0. thiscall with no stack arguments. Enters the falling animation.
uint32_t enterFallingAnimation(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t board = run.get(receiver + 0x12c);
    uint32_t cycle = run.get(receiver + 0x18c);
    uint32_t saved = run.get(board + 0x190);
    run.put(receiver + 0x134, saved);
    run.call(0x4c8220, board + 0x188, {cycle});
    uint32_t actor = run.get(receiver + 0x10);
    uint32_t previous = run.get(actor + 0x1c);
    run.put(receiver + 0x24, previous);
    uint32_t key = run.call(0x4dba00, 0x537668, {0x5236fc});
    uint32_t target = run.get(receiver + 0x10);
    run.put(target + 0x1c, key);
    uint32_t owner = run.get(receiver + 0xc);
    run.put(owner + 0xcc, 8);
    run.put(receiver + 0x19c, 0x7d);
    uint32_t clock = run.get(0x537210);
    run.put(receiver + 0x198, clock);
    return 0;
}

// Shared by 0x40f010 and 0x40f200: the animation is finished, so mark the
// logic done and notify.
void finishAnimation(Run &run, uint32_t receiver) {
    run.put(receiver + 0xc8, 1);
    uint32_t board = run.get(receiver + 0x12c);
    uint32_t saved = run.get(board + 0x190);
    run.put(receiver + 0x134, saved);
    run.call(0x4c8220, board + 0x188, {0});
    board = run.get(receiver + 0x12c);
    uint32_t flags = run.get(board + 8);
    flags = flags & 0xfffffffd;
    run.put(board + 8, flags);
    uint32_t message = run.get(receiver + 0x184);
    uint32_t target = run.get(receiver + 8);
    run.call(0x473660, 0, {target, message});
}

// 0x40f010. thiscall with no stack arguments. Steps the falling animation.
uint32_t stepFallingAnimation(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t step = run.get(0x5430c4);
    uint32_t board = run.get(receiver + 0x12c);
    run.call(0x4c82a0, board + 0x188, {step});
    uint32_t clock = run.get(0x537210);
    uint32_t started = run.get(receiver + 0x198);
    uint32_t delay = run.get(receiver + 0x19c);
    uint32_t elapsed = clock - started;
    if (elapsed >= delay) {
        uint32_t fired = run.get(receiver + 0x190);
        if (fired == 0) {
            uint32_t pending = run.get(receiver + 0xc);
            run.put(receiver + 0x190, 1);
            run.call(0x4736b0, 0, {pending});
        }
    }
    uint32_t owner = run.get(receiver + 0xc);
    uint32_t flags = run.get(owner + 0x164);
    if ((flags & 0x200) != 0) {
        finishAnimation(run, receiver);
        return 0;
    }
    if (run.get(owner + 0xcc) == 1) {
        run.call(0x4736b0, 0, {owner});
        enterBounceAnimation(run, receiver, nullptr);
    }
    return 0;
}

// 0x40f0e0. thiscall with no stack arguments. Lands: counts the bounce, plays its sound, switches to
// the bounce animation and reflects and damps the vertical motion.
uint32_t enterBounceAnimation(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t bounces = run.get(receiver + 0x194);
    uint32_t sound = run.get(receiver + 0x188);
    bounces = bounces + 1;
    run.put(receiver + 0x194, bounces);
    if (sound != 0) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t volume = run.get(0x532c10);
        if (enabled != 0) {
            uint32_t handle = run.get(sound + 0x10);
            run.call(0x4b45f0, handle, {volume, 0, 0, 0});
        }
    }
    uint32_t actor = run.get(receiver + 0x10);
    uint32_t previous = run.get(actor + 0x1c);
    run.put(receiver + 0x24, previous);
    uint32_t key = run.call(0x4dba00, 0x537668, {0x5240e8});
    uint32_t target = run.get(receiver + 0x10);
    run.put(target + 0x1c, key);
    uint32_t owner = run.get(receiver + 0xc);
    run.put(owner + 0xcc, 8);
    // Doubles: +0x40 gravity, +0x50 and +0x58 velocities, +0x70 height.
    double height = run.getd(receiver + 0x70);
    double lift = run.getd(0x50b6c0);
    double landed = height - lift;
    double gravity = run.getd(receiver + 0x40);
    double zero = run.getd(0x50b6c8);
    double speed;
    bool flat = !(gravity < zero) && !(gravity > zero);
    if (flat) {
        speed = run.getd(receiver + 0x58);
    } else {
        double drop = landed - run.getd(receiver + 0x70);
        double current = run.getd(receiver + 0x58);
        double square = current * current;
        double pull = drop * run.getd(receiver + 0x40);
        double twice = run.getd(0x50b6d0);
        double scaled = pull * twice;
        double discriminant = square - scaled;
        if (zero > discriminant)
            discriminant = zero;
        speed = std::sqrt(discriminant);
        double direction = run.getd(receiver + 0x58);
        if (!(direction > zero))
            speed = -speed;
    }
    run.putd(receiver + 0x58, speed);
    run.put(receiver + 0xb8, 0);
    run.put(receiver + 0xbc, 0xbff00000);
    run.putd(receiver + 0x70, landed);
    double horizontal = run.getd(receiver + 0x50);
    double damped = run.getd(receiver + 0x58);
    double damping = run.getd(0x50b6d8);
    damped = damped * damping;
    run.putd(receiver + 0x50, horizontal);
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x64, 0);
    run.putd(receiver + 0x58, damped);
    double stored = run.getd(receiver + 0x58);
    double floorSpeed = run.getd(0x50b6e0);
    if (!(stored >= floorSpeed)) {
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x5c, 0xc07f4000);
    }
    return 0;
}

// 0x40f200. thiscall with no stack arguments. Steps the landed state.
uint32_t stepBounceAnimation(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t step = run.get(0x5430c4);
    uint32_t board = run.get(receiver + 0x12c);
    run.call(0x4c82a0, board + 0x188, {step});
    uint32_t owner = run.get(receiver + 0xc);
    uint32_t flags = run.get(owner + 0x164);
    if ((flags & 0x200) == 0 && s32(run.get(receiver + 0x194)) <= 3) {
        if (run.get(owner + 0xcc) == 1)
            enterBounceAnimation(run, receiver, nullptr);
        return 0;
    }
    finishAnimation(run, receiver);
    return 0;
}

// 0x40f2a0. thiscall with no stack arguments. Refreshes the base state and, when flag 0x100000 is
// set, looks the current name up in the 0x537698 table, frees the table's
// scratch list and runs the dead handler when the name matches.
uint32_t refreshDeadHandler(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x4dca10, receiver);
    uint32_t flags = run.get(receiver + 0x120);
    if ((flags & 0x100000) == 0)
        return 0;
    uint32_t actor = run.get(receiver + 0x10);
    uint32_t id = run.get(actor + 0x1c);
    uint32_t low = run.get(0x5376a0);
    run.put(0x5376b8, 0);
    uint32_t entry;
    bool inRange = true;
    if (s32(id) < s32(low))
        inRange = false;
    else if (s32(id) > s32(run.get(0x5376a4)))
        inRange = false;
    if (inRange) {
        uint32_t offset = id - low;
        uint32_t base = run.get(0x5376a8);
        offset = offset * run.get(0x5376b0);
        entry = offset + base;
    } else {
        uint32_t found = run.call(0x4db6e0, 0x537698, {id, 0});
        if (found != 0) {
            uint32_t minimum = run.get(0x5376a0);
            uint32_t base = run.get(0x5376a8);
            uint32_t offset = id - minimum;
            offset = offset * run.get(0x5376b0);
            entry = offset + base;
        } else {
            uint32_t name = run.get(0x544b4c);
            uint32_t code = run.call(0x4db5f0, 0);
            uint32_t owner = run.get(0x53769c);
            run.put(0x544b14, code);
            run.call(0x4db4d0, owner, {0x537698, name, 0xc});
            entry = run.get(0x5376ac);
        }
    }
    uint32_t count = run.get(0x5376b8);
    uint32_t cursor = run.get(0x5376b4);
    if (count != 0) {
        uint32_t remaining = count;
        do {
            if (cursor != 0)
                run.call(0x4f6439, cursor);
            cursor = cursor + 4;
            remaining = remaining - 1;
        } while (remaining != 0);
    }
    uint32_t text = run.get(entry);
    uint32_t matched = run.call(0x4a3810, 0, {text, 0x5234f4});
    if (matched != 0)
        run.call(0x40f390, receiver);
    return 0;
}

// 0x40f6a0. thiscall, one argument. Sets +0x64, flagging +8 when it changed.
uint32_t setUnknown0x64AndMarkChanged(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t value = arguments[0];
    uint32_t current = run.get(receiver + 0x64);
    if (current != value) {
        run.put(receiver + 0x64, value);
        uint32_t flags = run.get(receiver + 8);
        run.put(receiver + 8, flags | 0x20000);
    }
    return 0;
}

// 0x40f6f0. thiscall with no stack arguments. Copies three pairs of
// binary64 defaults, preserving each low/high word read and write.
uint32_t resetMotionVectorDefaults(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t a = run.get(0x513e10);
    uint32_t b = run.get(0x513e14);
    run.put(receiver + 0x58, a);
    run.put(receiver + 0x5c, b);
    a = run.get(0x513e18);
    b = run.get(0x513e1c);
    run.put(receiver + 0x70, a);
    run.put(receiver + 0x74, b);
    a = run.get(0x513e10);
    b = run.get(0x513e14);
    run.put(receiver + 0x60, a);
    run.put(receiver + 0x64, b);
    a = run.get(0x513e18);
    b = run.get(0x513e1c);
    run.put(receiver + 0x78, a);
    run.put(receiver + 0x7c, b);
    a = run.get(0x513e10);
    b = run.get(0x513e14);
    run.put(receiver + 0x68, a);
    run.put(receiver + 0x6c, b);
    a = run.get(0x513e18);
    b = run.get(0x513e1c);
    run.put(receiver + 0x80, a);
    run.put(receiver + 0x84, b);
    return 0;
}

// 0x40f760. thiscall, one argument: binds the context to an actor.
uint32_t bindActorContext(Run &run, uint32_t receiver, const uint32_t *arguments) {
    ActorFields actor{run, arguments[0]};
    ActorContextFields contextFields{run, receiver};
    contextFields.actor(actor);
    contextFields.actorAlias(actor);
    uint32_t block = actor.holder();
    contextFields.holder(block);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40e690:
        return dispatchBounceLogic(run, receiver, arguments);
    case 0x40e750:
        return constructBounceLogic(run, receiver, arguments);
    case 0x40ebe0:
        return dispatchActionHandler(run, receiver, arguments);
    case 0x40efa0:
        return enterFallingAnimation(run, receiver, arguments);
    case 0x40f010:
        return stepFallingAnimation(run, receiver, arguments);
    case 0x40f0e0:
        return enterBounceAnimation(run, receiver, arguments);
    case 0x40f200:
        return stepBounceAnimation(run, receiver, arguments);
    case 0x40f2a0:
        return refreshDeadHandler(run, receiver, arguments);
    case 0x40f6a0:
        return setUnknown0x64AndMarkChanged(run, receiver, arguments);
    case 0x40f6f0:
        return resetMotionVectorDefaults(run, receiver, arguments);
    case 0x40f760:
        return bindActorContext(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_player_actions_01_entry, owned, body)
