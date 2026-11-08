// Level 1 shared human enemy states, batch 1
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
    case 0x44da20:
        return 0;
    case 0x44dd30:
        return 0;
    case 0x44de50:
        return 0;
    case 0x44e510:
        return 0;
    case 0x44ea10:
        return 0;
    case 0x44ea60:
        return 0;
    case 0x44ebb0:
        return 0;
    case 0x44ec80:
        return 0;
    case 0x44f290:
        return 0;
    case 0x44f490:
        return 0;
    case 0x44f660:
        return 0;
    case 0x44f800:
        return 0;
    default:
        return -1;
    }
}

// Enemy object fields used here: +0x00 vtable, +0x08 state, +0x0c controller,
// +0x10 definition, +0x20 and +0x24 saved values, +0x50 double velocity,
// +0x68 double position, +0x80 and +0x98 double limits, +0x128 body record
// (+0x04 body), +0x138 and +0x140 horizontal extents, +0x184 kind, +0x18c
// facing, +0x2e4 chance threshold, +0x2fc and +0x300 flag bits, +0x30c and
// +0x344 animation sequences, +0x38c and +0x3a4 sound handles, +0x400 and
// +0x404 speeds, +0x428 and +0x42c, +0x438 and +0x43c timestamps with
// durations. Body fields: +0x08 flags, +0x40 facing flags, +0x188 animation.
const uint32_t kTable = 0x537698;
const uint32_t kTrie = 0x537668;
const uint32_t kTime = 0x537210;
const uint32_t kDelta = 0x5430c4;
const uint32_t kSoundFlag = 0x532c0c;
const uint32_t kSoundArgument = 0x532c10;

// A double compare followed by `test ah, 0x40`: equal, or unordered.
bool equalOrUnordered(double a, double b) {
    if (a < b)
        return false;
    if (a > b)
        return false;
    return true;
}

// Swap and negate the two extents at +0x138 and +0x140.
void mirrorExtents(Run &run, uint32_t object) {
    uint32_t first = run.get(object + 0x138);
    uint32_t second = run.get(object + 0x140);
    run.put(object + 0x138, 0u - second);
    run.put(object + 0x140, 0u - first);
}

// Turn the body to face left: set flag 2 and refresh the three derived views.
void mirrorBodyOn(Run &run, uint32_t object) {
    uint32_t body = run.get(object + 0x12c);
    mirrorExtents(run, object);
    run.put(body + 0x40, run.get(body + 0x40) | 2);
    uint32_t again = run.get(object + 0x12c);
    run.call(0x406120, again);
    run.call(0x406150, again);
    run.call(0x406180, again);
}

// Free the pointers held in the global pointer list.
void releaseList(Run &run) {
    uint32_t cursor = run.get(0x5376b4);
    uint32_t count = run.get(0x5376b8);
    for (; count != 0; --count) {
        if (cursor != 0)
            run.call(0x4f6439, cursor);
        cursor += 4;
    }
}

// Advance the animation record of the body by the frame delta.
void advanceAnimation(Run &run, uint32_t object) {
    uint32_t body = run.get(object + 0x12c);
    run.call(0x4c82a0, body + 0x188, {run.get(kDelta)});
}

// Stop both sound handles and flag the body once the timer has run out.
void finishTimer(Run &run, uint32_t object) {
    uint32_t sound = run.get(object + 0x3a4);
    if (sound != 0) {
        if (run.get(kSoundFlag) != 0) {
            uint32_t argument = run.get(kSoundArgument);
            run.call(0x4b45f0, run.get(sound + 0x10), {argument, 0, 0, 0});
        }
    }
    sound = run.get(object + 0x38c);
    if (sound != 0) {
        if (run.get(kSoundFlag) != 0) {
            uint32_t argument = run.get(kSoundArgument);
            run.call(0x4b45f0, run.get(sound + 0x10), {argument, 0, 0, 0});
        }
    }
    run.call(0x42df90, object + 0x128);
    uint32_t body = run.get(object + 0x12c);
    run.put(body + 0x08, run.get(body + 0x08) | 0x10000);
}

// 0x44ebb0. Starts the fast advance: faces the body, sets the speed and swaps
// in the LS_FASTADVANCE value.
uint32_t function_44ebb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = receiver;
    if (run.get(object + 0x18c) == 2) {
        uint32_t body = run.get(object + 0x12c);
        if ((run.get8(body + 0x40) & 2) == 0)
            mirrorBodyOn(run, object);
    } else {
        run.call(0x406310, object + 0x128);
    }
    uint32_t speed = run.get(object + 0x404);
    if (run.get(object + 0x18c) == 3)
        speed = 0u - speed;
    run.putd(object + 0x50, double(s32(speed)));
    uint32_t definition = run.get(object + 0x10);
    run.put(object + 0x24, run.get(definition + 0x1c));
    uint32_t value = run.call(0x4dba00, kTrie, {0x527d84});
    definition = run.get(object + 0x10);
    run.put(definition + 0x1c, value);
    uint32_t body = run.get(object + 0x12c);
    uint32_t sequence = run.get(object + 0x30c);
    run.put(object + 0x134, run.get(body + 0x190));
    run.call(0x4c8220, body + 0x188, {sequence});
    return 0;
}

// 0x44da20. LS_HOME state.
uint32_t function_44da20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = receiver;
    uint32_t definition = run.get(object + 0x10);
    uint32_t entry = run.call(0x441030, kTable, {run.get(definition + 0x1c)});
    releaseList(run);
    uint32_t name = run.get(entry);
    uint32_t different = run.call(0x4a3810, 0, {name, 0x5234ec});
    if (different != 0)
        return 0;
    if (run.get(object + 0x18c) == 2) {
        uint32_t body = run.get(object + 0x12c);
        if ((run.get8(body + 0x40) & 2) == 0)
            mirrorBodyOn(run, object);
    } else {
        run.call(0x406310, object + 0x128);
    }
    int32_t roll = s32(run.call(0x4a3050, 0));
    uint32_t kind = run.get(object + 0x184);
    if (kind > 6)
        return 0;
    switch (kind) {
    case 0:
    case 1:
        function_44ebb0(run, object, nullptr);
        return 0;
    case 2:
        run.call(0x4a1180, object);
        return 0;
    case 3:
    case 4:
        break;
    default:
        run.call(0x44edd0, object);
        return 0;
    }
    if (roll % 0x1a5 < s32(run.get(object + 0x2e4))) {
        run.vcall(object, 0x58);
        return 0;
    }
    uint32_t body = run.get(object + 0x12c);
    uint32_t sequence = run.get(object + 0x344);
    run.put(object + 0x134, run.get(body + 0x190));
    run.call(0x4c8220, body + 0x188, {sequence});
    run.call(0x4c82a0, body + 0x188, {run.get(kDelta)});
    int32_t again = s32(run.call(0x4a3050, 0));
    run.vcall(object, 0x90, {uint32_t(again % 0x12d) + 0x12c});
    return 0;
}

// 0x44dd30. LS_PAUSE state.
uint32_t function_44dd30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = receiver;
    uint32_t entry = run.call(0x441030, kTable, {run.get(object + 0x24)});
    releaseList(run);
    uint32_t name = run.get(entry);
    uint32_t different = run.call(0x4a3810, 0, {name, 0x5271c0});
    if (different == 0) {
        run.vcall(object, 0x78);
        return 0;
    }
    uint32_t elapsed = run.get(kTime) - run.get(object + 0x428);
    if (elapsed < run.get(object + 0x42c)) {
        run.call(0x43ff60, object);
        return 0;
    }
    finishTimer(run, object);
    return 0;
}

// 0x44de50. Waits for the timer, then finishes.
uint32_t function_44de50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = receiver;
    advanceAnimation(run, object);
    uint32_t elapsed = run.get(kTime) - run.get(object + 0x428);
    if (elapsed < run.get(object + 0x42c)) {
        uint32_t controller = run.get(object + 0x0c);
        if (run.get(controller + 0xcc) == 1)
            run.vcall(object, 0x78);
        return 0;
    }
    finishTimer(run, object);
    return 0;
}

// 0x44e510. Turns around to match the facing, then reacts to the controller.
uint32_t function_44e510(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = receiver;
    advanceAnimation(run, object);
    uint32_t body = run.get(object + 0x12c);
    if (run.get(object + 0x18c) == 2) {
        if ((run.get8(body + 0x40) & 2) == 0) {
            mirrorExtents(run, object);
            run.put(body + 0x40, run.get(body + 0x40) | 2);
            body = run.get(object + 0x12c);
            uint32_t first = run.get(body + 0x118);
            if (first != 0x80000000) {
                uint32_t second = run.get(body + 0x120);
                run.put(body + 0x118, 0u - second);
                run.put(body + 0x120, 0u - first);
            }
            first = run.get(body + 0x128);
            if (first != 0x80000000) {
                uint32_t second = run.get(body + 0x130);
                run.put(body + 0x128, 0u - second);
                run.put(body + 0x130, 0u - first);
            }
            run.call(0x406180, body);
        }
    } else {
        if ((run.get8(body + 0x40) & 2) != 0) {
            mirrorExtents(run, object);
            run.put(body + 0x40, run.get(body + 0x40) & 0xfffffffd);
            uint32_t again = run.get(object + 0x12c);
            run.call(0x406120, again);
            run.call(0x406150, again);
            run.call(0x406180, again);
        }
    }
    uint32_t controller = run.get(object + 0x0c);
    if (run.get(controller + 0xcc) == 1)
        run.vcall(object, 0x44);
    return 0;
}

// 0x44ea10. Clears body flag 4 and rests once the controller allows.
uint32_t function_44ea10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = receiver;
    advanceAnimation(run, object);
    uint32_t controller = run.get(object + 0x0c);
    if (run.get(controller + 0xcc) == 1) {
        uint32_t body = run.get(object + 0x12c);
        run.put(body + 0x08, run.get(body + 0x08) & 0xfffffffb);
        run.vcall(object, 0x44);
        run.put(object + 0x20, 2);
    }
    return 0;
}

// 0x44ea60. Tracking state: turns at the limits and keeps the speed.
uint32_t function_44ea60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = receiver;
    bool atLow = equalOrUnordered(run.getd(object + 0x68), run.getd(object + 0x80));
    bool atHigh = false;
    if (!atLow)
        atHigh = equalOrUnordered(run.getd(object + 0x68), run.getd(object + 0x98));
    if (atLow || atHigh)
        run.vcall(object, 0x48);
    uint32_t body = run.get(object + 0x12c);
    uint32_t flags = run.get8(body + 0x40);
    if (run.get(object + 0x18c) == 2) {
        if ((flags & 2) == 0)
            mirrorBodyOn(run, object);
    } else if ((flags & 2) != 0) {
        mirrorExtents(run, object);
        run.put(body + 0x40, run.get(body + 0x40) & 0xfffffffd);
        run.call(0x4060b0, run.get(object + 0x12c));
    }
    uint32_t speed = run.get(object + 0x400);
    if (run.get(object + 0x18c) == 3)
        speed = 0u - speed;
    run.putd(object + 0x50, double(s32(speed)));
    advanceAnimation(run, object);
    switch (run.get(object + 0x184)) {
    case 0:
        function_44ebb0(run, object, nullptr);
        return 0;
    case 3:
    case 4:
    case 5:
    case 6:
        run.vcall(object, 0x44);
        return 0;
    default:
        return 0;
    }
}

// 0x44ec80. Seek state.
uint32_t function_44ec80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = receiver;
    bool turn = false;
    bool faceBody = true;
    if (equalOrUnordered(run.getd(object + 0x68), run.getd(object + 0x80)) && run.get(object + 0x18c) == 3) {
        turn = true;
    } else if (equalOrUnordered(run.getd(object + 0x68), run.getd(object + 0x98))) {
        if (run.get(object + 0x18c) == 2)
            turn = true;
        else
            faceBody = false;
    }
    if (turn)
        run.vcall(object, 0x48);
    if (faceBody && run.get(object + 0x18c) == 2) {
        uint32_t body = run.get(object + 0x12c);
        if ((run.get8(body + 0x40) & 2) == 0)
            mirrorBodyOn(run, object);
    } else {
        run.call(0x406310, object + 0x128);
    }
    advanceAnimation(run, object);
    run.call(0x4a3050, 0);
    switch (run.get(object + 0x184)) {
    case 0:
    case 1:
    case 5: {
        uint32_t speed = run.get(object + 0x404);
        if (run.get(object + 0x18c) == 3)
            speed = 0u - speed;
        run.putd(object + 0x50, double(s32(speed)));
        return 0;
    }
    case 2:
        run.call(0x4a1180, object);
        return 0;
    case 3:
    case 4:
        run.vcall(object, 0x44);
        return 0;
    case 6:
        run.call(0x44edd0, object);
        return 0;
    default:
        return 0;
    }
}

// 0x44f290. Scan state: looks for the player.
uint32_t function_44f290(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = receiver;
    advanceAnimation(run, object);
    uint32_t bits = 0;
    uint32_t count = run.get(object + 0x2fc);
    if (count > 8) {
        uint32_t word = object + 0x300;
        if (count > 0x20)
            word = run.get(object + 0x300);
        bits = (run.get(word) >> 8) & 1;
    }
    if (bits != 0) {
        bool seen = false;
        if (run.get(0x534eac) != 0x26b7) {
            uint32_t target = run.get(object + 0x194);
            uint32_t player = run.get(0x537e88);
            uint32_t owner = run.get(object + 0x190);
            uint32_t map = run.get(run.get(owner + 0x0c) + 0x24);
            uint32_t hit = run.call(0x4cda10, map, {run.get(target + 0x4c), run.get(target + 0x50), run.get(player + 0x4c), 0x20});
            if (hit != 0) {
                target = run.get(object + 0x194);
                player = run.get(0x537e88);
                uint32_t targetY = run.get(target + 0x50);
                uint32_t playerY = run.get(player + 0x50);
                if (s32(playerY) < s32(targetY + 0x32)) {
                    if (s32(playerY) > s32(targetY - 0x32)) {
                        if (run.get(target + 0x38) != 0xffffffff)
                            seen = true;
                    }
                }
            }
        }
        if (seen)
            run.vcall(object, 0x44);
    }
    int32_t roll = s32(run.call(0x4a3050, 0));
    switch (run.get(object + 0x184)) {
    case 0:
    case 1:
    case 2:
    case 3:
    case 4:
        run.vcall(object, 0x44);
        break;
    case 5:
    case 6:
        if (roll % 0xc9 == 1) {
            uint32_t elapsed = run.get(kTime) - run.get(object + 0x438);
            if (elapsed >= run.get(object + 0x43c))
                run.call(0x44edd0, object);
        }
        break;
    default:
        break;
    }
    return 0;
}

// 0x44f490 and 0x44f660 share one body: slows the velocity until the
// animation ends.
uint32_t slowDown(Run &run, uint32_t object) {
    advanceAnimation(run, object);
    uint32_t record = run.get(object + 0x12c) + 0x188;
    if (run.get(record + 0x1c) != 0) {
        if (run.get(record + 0x14) == 0) {
            run.vcall(object, 0x44);
            run.put(object + 0x20, 2);
            return 0;
        }
    }
    if (!equalOrUnordered(run.getd(object + 0x50), run.getd(0x50e100))) {
        if (run.get(object + 0x18c) == 3) {
            run.putd(object + 0x50, run.getd(object + 0x50) - run.getd(0x50e108));
            return 0;
        }
        run.putd(object + 0x50, run.getd(object + 0x50) - run.getd(0x50e110));
    }
    return 0;
}

// 0x44f490.
uint32_t function_44f490(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return slowDown(run, receiver);
}

// 0x44f660.
uint32_t function_44f660(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return slowDown(run, receiver);
}

// 0x44f800. Stops and rests once the controller allows.
uint32_t function_44f800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = receiver;
    advanceAnimation(run, object);
    uint32_t controller = run.get(object + 0x0c);
    if (run.get(controller + 0xcc) == 1) {
        run.put(object + 0x50, 0);
        run.put(object + 0x54, 0);
        run.vcall(object, 0x44);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x44da20:
        return function_44da20(run, receiver, arguments);
    case 0x44dd30:
        return function_44dd30(run, receiver, arguments);
    case 0x44de50:
        return function_44de50(run, receiver, arguments);
    case 0x44e510:
        return function_44e510(run, receiver, arguments);
    case 0x44ea10:
        return function_44ea10(run, receiver, arguments);
    case 0x44ea60:
        return function_44ea60(run, receiver, arguments);
    case 0x44ebb0:
        return function_44ebb0(run, receiver, arguments);
    case 0x44ec80:
        return function_44ec80(run, receiver, arguments);
    case 0x44f290:
        return function_44f290(run, receiver, arguments);
    case 0x44f490:
        return function_44f490(run, receiver, arguments);
    case 0x44f660:
        return function_44f660(run, receiver, arguments);
    case 0x44f800:
        return function_44f800(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_human_enemies_01_entry, owned, body)
