// In-game Options Display and Audio page refresh
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x452800:
        return 0;
    case 0x452870:
        return 0;
    default:
        return -1;
    }
}

// 0x452800. thiscall, 0 stack argument(s), returns u32.
uint32_t function_452800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // +0x298 active page, +0x04 enabled state, +0x26c display sprite.
    if (run.get(receiver + 0x298) != 0x59da)
        return 0;
    if (!run.get(receiver + 0x04))
        return 0;
    if (!run.get(receiver + 0x26c))
        return 0;
    // +0x154 control lookup object; a found control's +0x3c is its state.
    uint32_t control = run.call(0x4dd020, receiver + 0x154, {0x5b06});
    if (control && control + 0x3c) {
        uint32_t state = run.call(0x4ed050, control + 0x3c);
        uint32_t image = (state & 6) ? 0x2e : 0x2d;
        run.call(0x4c7900, run.get(receiver + 0x26c), {0x527e60, image});
    }
    return 1;
}

// 0x452870. thiscall, 0 stack argument(s), returns u32.
uint32_t function_452870(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x298) != 0x59db)
        return 0;
    if (!run.get(receiver + 0x04))
        return 0;
    // +0x264 and +0x268 are the first and second audio sprites.
    if (!run.get(receiver + 0x264))
        return 0;
    if (!run.get(receiver + 0x268))
        return 0;
    uint32_t control = run.call(0x4dd020, receiver + 0x154, {0x5aa1});
    if (control && control + 0x3c) {
        uint32_t state = run.call(0x4ed050, control + 0x3c);
        uint32_t image = (state & 6) ? 0x2a : 0x29;
        run.call(0x4c7900, run.get(receiver + 0x264), {0x527e60, image});
    }
    control = run.call(0x4dd020, receiver + 0x154, {0x5aa4});
    if (control && control + 0x3c) {
        uint32_t state = run.call(0x4ed050, control + 0x3c);
        uint32_t image = (state & 6) ? 0x2c : 0x2b;
        run.call(0x4c7900, run.get(receiver + 0x268), {0x527e60, image});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x452800:
        return function_452800(run, receiver, arguments);
    case 0x452870:
        return function_452870(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_in_game_options_page_refresh_entry, owned, body)
