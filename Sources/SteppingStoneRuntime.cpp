// SteppingStone object logic
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
    case 0x49e810:
        return 1;
    default:
        return -1;
    }
}

// Object fields used: +0x08 flags, +0x0c owner, +0x38 and +0x4c sound ids,
// +0x64 timer, +0x6c logic state block, +0xd0 draw flags, +0x128..+0x134 rect,
// +0x16c rest value, +0x170 linked object, +0x174 cached value, +0x188
// animation player (+0x14 and +0x1c are its flags). State block: +0x10 handler,
// +0x1c state, +0x64 position, +0xbc speed.
void playSound(Run &run, uint32_t self, uint32_t name) {
    uint32_t id = run.get(self + 0x4c);
    uint32_t receiver = run.get(run.get(self + 0x0c) + 0x28);
    run.call(0x4ca610, receiver, {name, id, 0, 0});
}

// 0x49e810. Per-frame logic of a stepping stone. Always returns 1.
uint32_t function_49e810(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t self = arguments[0];
    uint32_t block = run.get(self + 0x6c);
    uint32_t state = run.get(block + 0x1c);
    if (state == 0x3ea) {
        if (run.get(self + 0x38) != 0xffffffffu)
            playSound(run, self, 0x52dd8c);
        run.put(block + 0x1c, 0x3ed);
        return 1;
    }
    if (state == 0) {
        uint32_t linked = run.get(self + 0x170);
        run.put(self + 0x158, 0);
        run.put(self + 0x15c, 0);
        if (linked) {
            uint32_t value = run.get(linked + 0x64);
            run.put(self + 0x16c, value);
            uint32_t result = run.call(0x40f680, linked, {value});
            run.put(self + 0x174, result);
        }
        uint32_t flags = run.get(self + 0x08);
        run.put(self + 0xd0, 0x80);
        flags |= 1;
        run.put(self + 0x08, flags);
        uint32_t source = run.get(0x537960) + 0x88;
        run.put(self + 0x128, run.get(source));
        run.put(self + 0x12c, run.get(source + 4));
        run.put(self + 0x130, run.get(source + 8));
        run.put(self + 0x134, run.get(source + 0xc));
        run.put(self + 0x134, run.get(self + 0x134) + 0x20);
        if (run.get(self + 0x64) == 0) {
            flags |= 0x20000;
            run.put(self + 0x64, 0x7d0);
            run.put(self + 0x08, flags);
        }
        uint32_t handler = run.get(block + 0x10);
        if (handler == 0x49ead0)
            run.put(block + 0xbc, 0x2ee);
        if (handler == 0x49eaf0)
            run.put(block + 0xbc, 0x5dc);
        if (handler == 0x49eb10)
            run.put(block + 0xbc, 0x8ca);
        run.call(0x49e470, 0, {self, block});
        run.put(block + 0x1c, 0x3ee);
        linked = run.get(self + 0x170);
        if (linked) {
            uint32_t sum = run.get(linked + 0x68) + run.get(linked + 0x64);
            uint32_t half = uint32_t(s32(sum) >> 1);
            if (s32(sum) < 0)
                half = uint32_t(s32(sum + 1) >> 1);
            run.put(block + 0x64, half);
        }
        return 1;
    }
    if (state < 0x3eb || state > 0x3ef)
        return 1;
    if (state == 0x3eb || state == 0x3ed) {
        uint32_t rest = state == 0x3eb ? 1 : 0x80;
        run.call(0x4c82a0, self + 0x188, {run.get(0x5430c4)});
        if (run.get(self + 0x16c) == run.get(block + 0x64))
            run.put(self + 0xd0, rest);
        if (run.get(self + 0x1a4) == 0)
            return 1;
        if (run.get(self + 0x19c) != 0)
            return 1;
        run.put(self + 0xd0, rest);
        if (state == 0x3eb) {
            run.call(0x4c79e0, self, {0x52dd14, 0});
            run.put(block + 0x1c, 0x3ef);
        } else {
            run.call(0x4c79e0, self, {0x52dd04, 0});
            run.put(block + 0x1c, 0x3ee);
        }
        return 1;
    }
    if (state == 0x3ec) {
        run.put(self + 0xd0, 1);
        run.call(0x4c79e0, self, {0x52dd04, 0});
        if (run.get(self + 0x38) != 0xffffffffu)
            playSound(run, self, 0x52dd7c);
        run.put(block + 0x1c, 0x3eb);
        return 1;
    }
    uint32_t moving = run.call(0x49e4b0, 0, {self, block, run.get(0x537210)});
    if (state == 0x3ee) {
        if (moving == 0)
            run.put(block + 0x1c, 0x3ec);
    } else if (moving != 0) {
        run.put(block + 0x1c, 0x3ea);
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49e810:
        return function_49e810(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_stepping_stone_entry, owned, body)
