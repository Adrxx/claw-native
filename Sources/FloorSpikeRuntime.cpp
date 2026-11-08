// FloorSpike object logic
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
    case 0x461d50:
        return 1;
    default:
        return -1;
    }
}

// Object fields used here: +0x08 flags, +0x0c owner (its +0x28 is the sound
// player), +0x38 sound id (-1 = none), +0x4c sound argument, +0x64 timer,
// +0x6c logic record, +0xd0 constant, +0x104 counter, +0x138..+0x144 hit box,
// +0x174 source rectangle, +0x188 animation (its +0x14 pending, +0x1c done).
// Logic record: +0x10 handler, +0x1c state, +0xbc value.
const uint32_t kStringDown = 0x529584;
const uint32_t kStringBackward = 0x52959c;
const uint32_t kStringForward = 0x5295b0;
const uint32_t kStringUp = 0x5295c0;

// Plays a sound through the owner's sound player when the object has one.
void playSound(Run &run, uint32_t object, uint32_t name) {
    if (run.get(object + 0x38) != 0xffffffffu) {
        uint32_t id = run.get(object + 0x4c);
        uint32_t owner = run.get(object + 0x0c);
        uint32_t player = run.get(owner + 0x28);
        run.call(0x4ca610, player, {name, id, 0, 0});
    }
}

// 0x461d50. FloorSpike state machine, always returns 1 (void for callers).
uint32_t function_461d50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t record = run.get(object + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state == 0x3ea) {
        playSound(run, object, kStringUp);
        run.call(0x4c79e0, object, {kStringForward, 0});
        run.put(record + 0x1c, 0x3ed);
        return 1;
    }
    if (state == 0) {
        uint32_t rect = run.get(object + 0x174);
        if (rect != 0) {
            run.put(object + 0x138, run.get(rect + 0x20) - run.get(rect + 0x18));
            run.put(object + 0x13c, run.get(rect + 0x24) - run.get(rect + 0x1c));
            run.put(object + 0x140, run.get(rect + 0x20) + run.get(rect + 0x18) - 1);
            run.put(object + 0x144, run.get(rect + 0x24) + run.get(rect + 0x1c) - 1);
        }
        uint32_t top = run.get(object + 0x13c);
        uint32_t flags = run.get(object + 0x08);
        top = top - 10;
        flags = flags | 0x80;
        run.put(object + 0x13c, top);
        run.put(object + 0x08, flags);
        run.put(object + 0xd0, 0x1000000);
        if (run.get(object + 0x64) == 0) {
            run.put(object + 0x64, 2000);
            run.put(object + 0x08, flags | 0x20000);
        }
        if (run.get(object + 0x104) == 0)
            run.put(object + 0x104, 10);
        uint32_t handler = run.get(record + 0x10);
        if (handler == 0x461fe0)
            run.put(record + 0xbc, 0x2ee);
        if (handler == 0x462000)
            run.put(record + 0xbc, 0x5dc);
        if (handler == 0x462020)
            run.put(record + 0xbc, 0x8ca);
        run.call(0x49e470, 0, {object, record});
        run.put(record + 0x1c, 0x3ef);
        return 1;
    }
    if (state == 0x3eb) {
        run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
        if (run.get(object + 0x188 + 0x1c) != 0 && run.get(object + 0x188 + 0x14) == 0) {
            run.call(0x4c79e0, object, {kStringBackward, 0});
            run.put(record + 0x1c, 0x3ef);
        }
        return 1;
    }
    if (state == 0x3ec) {
        uint32_t flags = run.get(object + 0x08) | 0x80;
        run.put(object + 0x08, flags);
        run.call(0x4c79e0, object, {kStringBackward, 0});
        playSound(run, object, kStringDown);
        run.put(record + 0x1c, 0x3eb);
        return 1;
    }
    if (state == 0x3ed) {
        run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
        if (run.get(object + 0x188 + 0x1c) != 0 && run.get(object + 0x188 + 0x14) == 0) {
            uint32_t flags = run.get(object + 0x08) & 0xffffff7fu;
            run.put(object + 0x08, flags);
            run.call(0x4c79e0, object, {kStringForward, 0});
            run.put(record + 0x1c, 0x3ee);
        }
        return 1;
    }
    if (state == 0x3ee) {
        uint32_t result = run.call(0x49e4b0, 0, {object, record, run.get(0x537210)});
        if (result == 0)
            run.put(record + 0x1c, 0x3ec);
        return 1;
    }
    if (state == 0x3ef) {
        uint32_t result = run.call(0x49e4b0, 0, {object, record, run.get(0x537210)});
        if (result != 0)
            run.put(record + 0x1c, 0x3ea);
        return 1;
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x461d50:
        return function_461d50(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_floor_spike_entry, owned, body)
