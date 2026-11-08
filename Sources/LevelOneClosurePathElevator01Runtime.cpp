// Level 1 closure: Path elevator helpers
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"
#include <array>

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x468170:
        return 1;
    case 0x4681c0:
        return 3;
    case 0x4682c0:
        return 3;
    case 0x4683a0:
        return 1;
    case 0x468540:
        return 1;
    case 0x468840:
        return 2;
    case 0x468890:
        return 4;
    case 0x4688f0:
        return 1;
    case 0x49f020:
        return 1;
    case 0x49f040:
        return 0;
    default:
        return -1;
    }
}

// Elevator path object fields: +0x04 owner, +0x08 source object, +0x0c divisor
// (defaults to 100), +0x10 total duration, +0x14 time offset, +0x00..+0x7c
// step types (32 entries), +0x80..+0xfc step values, +0x100 step count.

// 0x468170. Sums value * 1000 / divisor over the steps of the receiver.
uint32_t function_468170(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t divisor = arguments[0];
    if (divisor == 0)
        return 0;
    uint32_t count = run.get(receiver + 0x100);
    uint32_t total = 0;
    uint32_t slot = receiver + 0x80;
    if (s32(count) > 0) {
        do {
            uint32_t value = run.get(slot);
            slot += 4;
            total = total + (value * 1000) / divisor;
            count = count - 1;
        } while (count != 0);
    }
    return total;
}

// 0x4682c0. stdcall. Applies a step of the given type to the (x, y) pair.
uint32_t function_4682c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t pair = arguments[0];
    uint32_t type = arguments[1];
    uint32_t amount = arguments[2];
    if (type == 5)
        return 0;
    switch (type) {
    case 1:
        run.put(pair, run.get(pair) - amount);
        run.put(pair + 4, run.get(pair + 4) + amount);
        break;
    case 2:
        run.put(pair + 4, run.get(pair + 4) + amount);
        break;
    case 3:
        run.put(pair, run.get(pair) + amount);
        run.put(pair + 4, run.get(pair + 4) + amount);
        break;
    case 4:
        run.put(pair, run.get(pair) - amount);
        break;
    case 6:
        run.put(pair, run.get(pair) + amount);
        break;
    case 7:
        run.put(pair, run.get(pair) - amount);
        run.put(pair + 4, run.get(pair + 4) - amount);
        break;
    case 8:
        run.put(pair + 4, run.get(pair + 4) - amount);
        break;
    case 9:
        run.put(pair, run.get(pair) + amount);
        run.put(pair + 4, run.get(pair + 4) - amount);
        break;
    default:
        break;
    }
    return 0;
}

// 0x4681c0. Accumulates the displacement after `elapsed` into the output pair.
// Locals: x at entry-8, y at entry-4.
uint32_t function_4681c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t out = arguments[0];
    uint32_t elapsed = arguments[1];
    uint32_t divisor = arguments[2];
    uint32_t pair = run.automatic(-8);
    run.put(pair, 0);
    run.put(pair + 4, 0);
    if (divisor == 0 || s32(run.get(receiver + 0x100)) < 1) {
        run.put(out, 0);
        run.put(out + 4, 0);
        return 0;
    }
    uint32_t index = 0;
    uint32_t slot = receiver + 0x80;
    while (true) {
        uint32_t value = run.get(slot);
        uint32_t span = (value * 1000) / divisor;
        if (elapsed < span)
            break;
        function_4682c0(run, 0, std::array<uint32_t, 3>{pair, run.get(slot - 0x80), run.get(slot)}.data());
        elapsed = elapsed - span;
        if (elapsed == 0) {
            run.put(out, run.get(pair));
            run.put(out + 4, run.get(pair + 4));
            return 0;
        }
        index = index + 1;
        slot = slot + 4;
        if (s32(run.get(receiver + 0x100)) <= s32(index)) {
            run.put(out, run.get(pair));
            run.put(out + 4, run.get(pair + 4));
            return 0;
        }
    }
    uint32_t partial = (divisor * elapsed) / 1000;
    uint32_t type = run.get(receiver + index * 4);
    function_4682c0(run, 0, std::array<uint32_t, 3>{pair, type, partial}.data());
    run.put(out, run.get(pair));
    run.put(out + 4, run.get(pair + 4));
    return 0;
}

// Appends one step when there is room: count < 0x20.
void appendFixed(Run &run, uint32_t receiver, uint32_t type) {
    if (s32(run.get(receiver + 0x100)) < 0x20) {
        run.put(receiver + run.get(receiver + 0x100) * 4, type);
        run.put(receiver + run.get(receiver + 0x100) * 4 + 0x80, 100);
        run.put(receiver + 0x100, run.get(receiver + 0x100) + 1);
    }
}

// 0x4683a0. Builds a preset step list for pattern 1 or 2.
uint32_t function_4683a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t pattern = arguments[0];
    if (pattern == 1) {
        appendFixed(run, receiver, 6);
        appendFixed(run, receiver, 7);
        appendFixed(run, receiver, 6);
    } else {
        if (pattern != 2)
            return 0;
        appendFixed(run, receiver, 6);
        appendFixed(run, receiver, 7);
        appendFixed(run, receiver, 5);
        appendFixed(run, receiver, 6);
    }
    appendFixed(run, receiver, 1);
    return 1;
}

// 0x468840. Appends (type, value) when there is room and both are nonzero.
uint32_t function_468840(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t type = arguments[0];
    uint32_t value = arguments[1];
    if (s32(run.get(receiver + 0x100)) < 0x20 && type != 0 && value != 0) {
        run.put(receiver + run.get(receiver + 0x100) * 4, type);
        run.put(receiver + run.get(receiver + 0x100) * 4 + 0x80, value);
        run.put(receiver + 0x100, run.get(receiver + 0x100) + 1);
        return 1;
    }
    return 0;
}

// Appends one (type, value) pair, reading the count from the receiver.
// Used by 0x468540 where the original keeps the count in a register.
bool appendPair(Run &run, uint32_t receiver, uint32_t count, uint32_t type, uint32_t value) {
    if (s32(count) < 0x20 && type != 0 && value != 0) {
        run.put(receiver + count * 4, type);
        run.put(receiver + run.get(receiver + 0x100) * 4 + 0x80, value);
        run.put(receiver + 0x100, run.get(receiver + 0x100) + 1);
        return true;
    }
    return false;
}

// 0x468540. Copies the step pairs found in the source object into the receiver.
uint32_t function_468540(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[0];
    if (source == 0)
        return 0;
    uint32_t type = run.get(source + 0x118);
    if (type == 0x80000000)
        return 0;
    if (type == 0)
        return 0;
    uint32_t count = run.get(receiver + 0x100);
    uint32_t value = run.get(source + 0x11c);
    if (!appendPair(run, receiver, count, type, value))
        return 0;
    static const uint32_t offsets[6][2] = {
        {0x120, 0x124}, {0x128, 0x12c}, {0x130, 0x134}, {0x138, 0x13c}, {0x140, 0x144}, {0x54, 0x58},
    };
    for (int i = 0; i < 6; ++i) {
        count = run.get(receiver + 0x100);
        value = run.get(source + offsets[i][1]);
        type = run.get(source + offsets[i][0]);
        if (!appendPair(run, receiver, count, type, value))
            return 1;
    }
    count = run.get(receiver + 0x100);
    value = run.get(source + 0x60);
    type = run.get(source + 0x5c);
    if (!appendPair(run, receiver, count, type, value))
        return 1;
    count = run.get(receiver + 0x100);
    if (run.get(source + 0x6c) != 0)
        return 1;
    // The original faults here on the null-page read; nothing after it is observable.
    run.get(0xf4);
    run.get(0xf0);
    return 1;
}

// 0x468890. Initializes the path object; returns whether the duration is nonzero.
uint32_t function_468890(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t owner = arguments[0];
    uint32_t source = arguments[1];
    uint32_t divisor = arguments[2];
    if (owner == 0)
        return 0;
    if (source == 0)
        return 0;
    if (divisor == 0)
        divisor = 100;
    run.put(receiver + 4, owner);
    run.put(receiver + 8, source);
    run.put(receiver + 0xc, divisor);
    run.put(receiver + 0x14, arguments[3]);
    std::array<uint32_t, 1> args{divisor};
    uint32_t total = function_468170(run, source, args.data());
    run.put(receiver + 0x10, total);
    return total != 0 ? 1 : 0;
}

// 0x4688f0. Moves the owner along the path for the given time.
// Locals: x at entry-8, y at entry-4.
uint32_t function_4688f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t duration = run.get(receiver + 0x10);
    if (duration == 0)
        return 0;
    uint32_t time = arguments[0] + run.get(receiver + 0x14);
    uint32_t pair = run.automatic(-8);
    std::array<uint32_t, 3> args{pair, time - (time / duration) * duration, run.get(receiver + 0xc)};
    function_4681c0(run, run.get(receiver + 8), args.data());
    uint32_t owner = run.get(receiver + 4);
    uint32_t oldX = run.get(owner + 0x4c);
    uint32_t oldY = run.get(owner + 0x50);
    uint32_t newX = run.get(owner + 0xe8) + run.get(pair);
    uint32_t newY = run.get(owner + 0xec) + run.get(pair + 4);
    run.put(owner + 0x4c, newX);
    run.put(run.get(receiver + 4) + 0x50, newY);
    uint32_t deltaX = newX - oldX;
    run.put(run.get(receiver + 4) + 0x158, deltaX);
    uint32_t deltaY = newY - oldY;
    run.put(run.get(receiver + 4) + 0x15c, deltaY);
    uint32_t absX = s32(deltaX) < 0 ? 0u - deltaX : deltaX;
    uint32_t absY = s32(deltaY) < 0 ? 0u - deltaY : deltaY;
    if (s32(absX) > 99 || s32(absY) > 99) {
        run.put(run.get(receiver + 4) + 0x158, 0);
        run.put(run.get(receiver + 4) + 0x15c, 0);
    }
    return 0;
}

// 0x49f040. Destructor body: frees the buffer at +8 and clears the fields.
uint32_t function_49f040(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x0, 0x50fee4);
    uint32_t buffer = run.get(receiver + 8);
    if (buffer != 0)
        run.call(0x4f6428, 0, {buffer});
    run.put(receiver + 4, 0);
    run.put(receiver + 8, 0);
    run.put(receiver + 0xc, 0);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x0, 0x50b014);
    return 0;
}

// 0x49f020. Scalar deleting destructor.
uint32_t function_49f020(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_49f040(run, receiver, nullptr);
    if ((arguments[0] & 1) != 0)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x468170:
        return function_468170(run, receiver, arguments);
    case 0x4681c0:
        return function_4681c0(run, receiver, arguments);
    case 0x4682c0:
        return function_4682c0(run, receiver, arguments);
    case 0x4683a0:
        return function_4683a0(run, receiver, arguments);
    case 0x468540:
        return function_468540(run, receiver, arguments);
    case 0x468840:
        return function_468840(run, receiver, arguments);
    case 0x468890:
        return function_468890(run, receiver, arguments);
    case 0x4688f0:
        return function_4688f0(run, receiver, arguments);
    case 0x49f020:
        return function_49f020(run, receiver, arguments);
    case 0x49f040:
        return function_49f040(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_closure_path_elevator_01_entry, owned, body)
