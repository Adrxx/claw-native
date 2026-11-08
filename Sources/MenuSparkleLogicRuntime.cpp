// Original menu sparkle actor logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x45f840:
        return 1;
    default:
        return -1;
    }
}

// 0x45f840. cdecl, 1 stack argument(s), returns void.
uint32_t function_45f840(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    if (!actor)
        return 0;
    // +0x6c points to logic data: +0x1c state, +0x130 countdown,
    // and +0x20 the next randomized delay.
    uint32_t logic = run.get(actor + 0x6c);
    if (!logic)
        return 0;
    uint32_t state = run.get(logic + 0x1c);
    if (!state) {
        run.call(0x4c7970, actor, {0x5291b4});
        run.call(0x4c79e0, actor, {0x5291a4, 0});
        run.put(logic + 0x1c, 5);
        uint32_t random = run.call(0x4a3050, 0);
        run.put(logic + 0x130, uint32_t(s32(random) % 0xfa1) + 0x3e8);
    } else if (state == 5) {
        uint32_t countdown = run.get(logic + 0x130);
        uint32_t elapsed = run.get(0x53720c);
        if (elapsed >= countdown) {
            run.put(logic + 0x130, 0);
        } else {
            run.put(logic + 0x130, countdown - elapsed);
        }
        if (!run.get(logic + 0x130))
            run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
        // +0x188 is the animation; +0x1a4 is active and +0x19c is progress.
        uint32_t animation = actor + 0x188;
        if (run.get(actor + 0x1a4) && !run.get(animation + 0x14)) {
            if (animation)
                run.call(0x4c8260, animation, {1});
            uint32_t random = run.call(0x4a3050, 0);
            run.put(logic + 0x20, uint32_t(s32(random) % 0xfa1) + 0x3e8);
        }
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x45f840:
        return function_45f840(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_sparkle_logic_entry, owned, body)
