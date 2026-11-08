// SawBlade object logic
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
    case 0x462040:
        return 1;
    default:
        return -1;
    }
}

// 0x462040. SawBlade state machine. Fields of the object: +0x08 flags, +0x0c
// owner, +0x38 id, +0x4c sound id, +0x64 and +0x104 counters, +0x6c logic
// block, +0xd0 value, +0x138..+0x144 bounds, +0x174 source rectangle,
// +0x188 animation. Logic block: +0x10 callback, +0x1c state, +0xbc value.
uint32_t function_462040(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t self = arguments[0];
    uint32_t logic = run.get(self + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0x3ea) {
        if (run.get(self + 0x38) != 0xffffffffu) {
            uint32_t owner = run.get(self + 0x0c);
            uint32_t receiverObject = run.get(owner + 0x28);
            uint32_t sound = run.get(self + 0x4c);
            run.call(0x4ca610, receiverObject, {0x529624, sound, 0, 0});
        }
        run.call(0x4c79e0, self, {0x529610, 0});
        run.put(logic + 0x1c, 0x3ed);
        return 1;
    }
    if (state == 0) {
        uint32_t rect = run.get(self + 0x174);
        if (rect != 0) {
            run.put(self + 0x138, run.get(rect + 0x20) - run.get(rect + 0x18));
            run.put(self + 0x13c, run.get(rect + 0x24) - run.get(rect + 0x1c));
            run.put(self + 0x140, run.get(rect + 0x20) + run.get(rect + 0x18) - 1);
            run.put(self + 0x144, run.get(rect + 0x24) + run.get(rect + 0x1c) - 1);
        }
        uint32_t left = run.get(self + 0x138);
        uint32_t right = run.get(self + 0x140);
        uint32_t top = run.get(self + 0x13c);
        run.put(self + 0x138, left + 0x14);
        uint32_t flags = run.get(self + 0x08);
        run.put(self + 0x140, right - 0x14);
        uint32_t counter = run.get(self + 0x64);
        run.put(self + 0x13c, top - 0x14);
        flags |= 0x80;
        run.put(self + 0x08, flags);
        run.put(self + 0xd0, 0x1000000);
        if (counter == 0) {
            run.put(self + 0x64, 0x7d0);
            run.put(self + 0x08, flags | 0x20000);
        }
        if (run.get(self + 0x104) == 0)
            run.put(self + 0x104, 10);
        uint32_t callback = run.get(logic + 0x10);
        if (callback == 0x4622f0)
            run.put(logic + 0xbc, 0x2ee);
        if (callback == 0x462310)
            run.put(logic + 0xbc, 0x5dc);
        if (callback == 0x462330)
            run.put(logic + 0xbc, 0x8ca);
        run.call(0x49e470, 0, {self, logic});
        run.put(logic + 0x1c, 0x3ef);
        return 1;
    }
    if (state < 0x3eb)
        return 1;
    switch (state) {
    case 0x3eb: {
        run.call(0x4c82a0, self + 0x188, {run.get(0x5430c4)});
        if (run.get(self + 0x188 + 0x1c) != 0 && run.get(self + 0x188 + 0x14) == 0) {
            run.put(logic + 0x1c, 0x3ef);
            return 1;
        }
        break;
    }
    case 0x3ec: {
        uint32_t flags = run.get(self + 0x08);
        flags |= 0x80;
        run.put(self + 0x08, flags);
        run.call(0x4c79e0, self, {0x5295fc, 0});
        if (run.get(self + 0x38) != 0xffffffffu) {
            uint32_t sound = run.get(self + 0x4c);
            uint32_t receiverObject = run.get(run.get(self + 0x0c) + 0x28);
            run.call(0x4ca610, receiverObject, {0x5295e8, sound, 0, 0});
        }
        run.put(logic + 0x1c, 0x3eb);
        return 1;
    }
    case 0x3ed: {
        run.call(0x4c82a0, self + 0x188, {run.get(0x5430c4)});
        if (run.get(self + 0x188 + 0x1c) != 0 && run.get(self + 0x188 + 0x14) == 0) {
            uint32_t flags = run.get(self + 0x08);
            flags &= 0xffffff7fu;
            run.put(self + 0x08, flags);
            run.call(0x4c79e0, self, {0x5295d4, 0});
            run.put(logic + 0x1c, 0x3ee);
        }
        break;
    }
    case 0x3ee: {
        run.call(0x4c82a0, self + 0x188, {run.get(0x5430c4)});
        uint32_t result = run.call(0x49e4b0, 0, {self, logic, run.get(0x537210)});
        if (result == 0) {
            run.put(logic + 0x1c, 0x3ec);
            return 1;
        }
        break;
    }
    case 0x3ef: {
        uint32_t result = run.call(0x49e4b0, 0, {self, logic, run.get(0x537210)});
        if (result != 0) {
            run.put(logic + 0x1c, 0x3ea);
            return 1;
        }
        break;
    }
    default:
        break;
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x462040:
        return function_462040(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_saw_blade_entry, owned, body)
