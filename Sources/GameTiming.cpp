#include "GameTiming.h"

void claw_timing_initialize(ClawTimingManager *manager, ClawClockState *clock, ClawTimingHost host) {
    manager->pacingEnabled = 0;
    claw_timing_reset_rate(manager, 1, host);
    claw_timing_reset_clock(clock, host);
}

void claw_timing_wait(uint32_t milliseconds, ClawTimingHost host) {
    if (host.observeWait)
        host.observeWait(host.context, milliseconds);
    uint32_t sample = host.read(host.context);
    const uint32_t deadline = sample + milliseconds;
    while (sample <= deadline)
        sample = host.read(host.context);
}

void claw_timing_reset_rate(ClawTimingManager *manager, uint32_t clearReportedRate, ClawTimingHost host) {
    manager->frameCount = 0;
    manager->frameCountStart = host.read(host.context);
    if (clearReportedRate)
        manager->reportedFrameRate = UINT32_MAX;
}

void claw_timing_reset_clock(ClawClockState *clock, ClawTimingHost host) {
    clock->nowMilliseconds = host.read(host.context);
    clock->deltaMilliseconds = 0;
    clock->pacedFrameStart = 0;
}

uint32_t claw_timing_update(ClawTimingManager *manager, ClawClockState *clock, ClawTimingHost host) {
    const uint32_t sample = host.read(host.context);
    clock->deltaMilliseconds = sample - clock->nowMilliseconds;
    clock->nowMilliseconds = sample;
    if (clock->countdown == 0)
        clock->countdown = clock->countdownReload;
    else if (clock->deltaMilliseconds < clock->countdown)
        clock->countdown -= clock->deltaMilliseconds;
    else
        clock->countdown = 0;

    // Avoid implementation-defined unsigned-to-signed conversion.
    if (manager->pacingEnabled != 0 && manager->pacingEnabled < 0x80000000u) {
        if (clock->pacedFrameStart != 0) {
            const uint32_t elapsed = host.read(host.context) - clock->pacedFrameStart;
            if (elapsed < manager->minimumFrameMilliseconds)
                claw_timing_wait(manager->minimumFrameMilliseconds - elapsed, host);
        }
        clock->pacedFrameStart = host.read(host.context);
    }
    ++manager->frameCount;
    if (clock->nowMilliseconds - manager->frameCountStart >= 2000u) {
        manager->reportedFrameRate = manager->frameCount >> 1;
        claw_timing_reset_rate(manager, 0, host);
    }
    return 1;
}

void claw_timing_publish_stage(const ClawClockState *clock, ClawFrameClock *stage, uint32_t *accumulatedMilliseconds) {
    stage->nowMilliseconds = clock->nowMilliseconds;
    *accumulatedMilliseconds += clock->deltaMilliseconds;
    stage->deltaMilliseconds = clock->deltaMilliseconds;
}

void claw_timing_update_animation(ClawFrameClock *animation, uint32_t refresh, ClawTimingHost host) {
    if (refresh) {
        const uint32_t sample = host.read(host.context);
        animation->deltaMilliseconds = sample - animation->nowMilliseconds;
        animation->nowMilliseconds = sample;
    }
}

void claw_timing_set_replay(ClawFrameClock *stage, uint32_t *accumulatedMilliseconds, ClawFrameClock *animation,
                            uint32_t now, uint32_t delta, uint32_t accumulated) {
    stage->nowMilliseconds = now;
    stage->deltaMilliseconds = delta;
    *accumulatedMilliseconds = accumulated;
    animation->nowMilliseconds = now;
    animation->deltaMilliseconds = delta;
}
