// Original clock update and busy pacing
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b82f0:
        return 0;
    case 0x4b83f0:
        return 1;
    default:
        return -1;
    }
}

// 0x4b83f0 GameTimingWait. The unsigned deadline and samples wrap at 32 bits.
uint32_t wait(Run &run, uint32_t duration) {
    uint32_t clock = run.get(0x546df0);
    uint32_t sample = run.call(clock, 0);
    uint32_t deadline = sample + duration;
    while (sample <= deadline) {
        sample = run.call(clock, 0);
    }
    return sample;
}

// 0x4b82f0 GameTimingUpdate. Globals hold current time, delta, paced start,
// countdown, and reload at 0x541328 through 0x541338 respectively.
uint32_t update(Run &run, uint32_t receiver) {
    uint32_t clock = run.get(0x546df0);
    uint32_t sample = run.call(clock, 0);
    uint32_t previous = run.get(0x541328);
    run.put(0x541328, sample);
    uint32_t countdown = run.get(0x541334);
    uint32_t delta = sample - previous;
    run.put(0x54132c, delta);
    if (countdown == 0) {
        run.put(0x541334, run.get(0x541338));
    } else if (delta >= countdown) {
        run.put(0x541334, 0);
    } else {
        run.put(0x541334, countdown - delta);
    }
    // +0x1c is signed pacing enabled; +0x28 is unsigned minimum duration.
    if (s32(run.get(receiver + 0x1c)) > 0) {
        if (run.get(0x541330) != 0) {
            uint32_t pacedSample = run.call(clock, 0);
            uint32_t elapsed = pacedSample - run.get(0x541330);
            uint32_t minimum = run.get(receiver + 0x28);
            if (elapsed < minimum) {
                wait(run, minimum - elapsed);
            }
        }
        uint32_t pacedStart = run.call(clock, 0);
        run.put(0x541330, pacedStart);
    }
    // +0x20 is frame count, +0x24 reporting epoch, +0x18 reported rate.
    uint32_t count = run.get(receiver + 0x20);
    uint32_t epoch = run.get(receiver + 0x24);
    count += 1;
    run.put(receiver + 0x20, count);
    uint32_t interval = run.get(0x541328) - epoch;
    if (interval >= 2000) {
        run.put(receiver + 0x18, count >> 1);
        run.call(0x4b83a0, receiver, {0});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b82f0:
        return update(run, receiver);
    case 0x4b83f0:
        return wait(run, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_game_timing_canonical_entry, owned, body)
