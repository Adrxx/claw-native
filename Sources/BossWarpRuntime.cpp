// BossWarp object logic
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
    case 0x470870:
        return 1;
    default:
        return -1;
    }
}

// 0x470870. cdecl, 1 stack argument(s), returns void (EAX is always 1).
// Object fields used: +0x08 flags, +0x0c owner, +0x4c/+0x50 position, +0x64 score,
// +0x6c state block (+0x1c phase, +0x168 power-up handle), +0x174 bounds source,
// +0x138..+0x144 clip rectangle, +0x188 sub-object, +0x190 animation.
uint32_t function_470870(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase == 0) {
        run.put(state + 0x168, 0);
        uint32_t value = run.get(object + 0x64);
        run.put(object + 0xc8, 0);
        if (value == 0) {
            uint32_t flags = run.get(object + 0x08);
            run.put(object + 0x64, 1000);
            run.put(object + 0x08, flags | 0x20000);
        }
        if (run.get(object + 0x190) == 0) {
            run.call(0x4c79e0, object, {0x52a218, 0});
            if (run.get(object + 0x190) == 0)
                run.call(0x4c79e0, object, {0x52a198, 0});
        }
        uint32_t bounds = run.get(object + 0x174);
        run.put(object + 0x108, 0x270f);
        run.put(object + 0xd0, 0x100);
        run.put(object + 0xfc, 0x26ae);
        if (bounds != 0) {
            uint32_t a = run.get(bounds + 0x20);
            uint32_t b = run.get(bounds + 0x18);
            run.put(object + 0x138, a - b);
            uint32_t c = run.get(bounds + 0x24);
            uint32_t d = run.get(bounds + 0x1c);
            run.put(object + 0x13c, c - d);
            a = run.get(bounds + 0x20);
            b = run.get(bounds + 0x18);
            run.put(object + 0x140, a + b - 1);
            c = run.get(bounds + 0x24);
            d = run.get(bounds + 0x1c);
            run.put(object + 0x144, c + d - 1);
        }
        uint32_t left = run.get(object + 0x138);
        uint32_t right = run.get(object + 0x140);
        uint32_t top = run.get(object + 0x13c);
        run.put(object + 0x138, left - 6);
        uint32_t bottom = run.get(object + 0x144);
        run.put(object + 0x140, right + 6);
        run.put(object + 0x144, bottom + 2);
        run.put(object + 0x13c, top - 10);
        uint32_t owner = run.get(object + 0x0c);
        uint32_t table = run.get(owner + 0x28);
        uint32_t local = run.automatic(4);
        run.put(local, 0);
        run.call(0x4f6286, table + 0x10, {0x52a204, local});
        run.put(state + 0x168, run.get(local));
        uint32_t manager = run.get(0x5371fc);
        uint32_t target = run.get(manager + 0x2c);
        uint32_t result = run.vcall(target, 0x10);
        if (result == 4) {
            uint32_t score = run.get(object + 0x64);
            uint32_t flags = run.get(object + 0x08);
            uint32_t x = run.get(object + 0x4c);
            uint32_t y = run.get(object + 0x50);
            run.put(object + 0x08, flags | 0x10000);
            uint32_t host = run.get(run.get(object + 0x0c) + 8);
            run.call(0x4c8da0, host, {0, x, y, score, 0x52293c, 0x240000});
            return 1;
        }
        run.put(state + 0x1c, 5);
    } else if (phase == 5) {
        run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x470870:
        return function_470870(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_boss_warp_entry, owned, body)
