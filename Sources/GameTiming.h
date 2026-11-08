#ifndef CLAW_GAME_TIMING_H
#define CLAW_GAME_TIMING_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

// Portable representations of the original 32-bit words, not host pointers.
typedef struct {
    uint32_t nowMilliseconds;   // 0x541328
    uint32_t deltaMilliseconds; // 0x54132c
    uint32_t pacedFrameStart;   // 0x541330
    uint32_t countdown;         // 0x541334
    uint32_t countdownReload;   // 0x541338
} ClawClockState;
typedef struct {
    uint32_t reportedFrameRate;        // manager +0x18
    uint32_t pacingEnabled;            // +0x1c: signed > 0 enables pacing
    uint32_t frameCount;               // +0x20
    uint32_t frameCountStart;          // +0x24
    uint32_t minimumFrameMilliseconds; // +0x28: unsigned comparison
} ClawTimingManager;
typedef struct {
    uint32_t nowMilliseconds;   // stage 0x537208 / animation 0x5430c8
    uint32_t deltaMilliseconds; // stage 0x53720c / animation 0x5430c4
} ClawFrameClock;
typedef uint32_t (*ClawReadMillisecondClock)(void *context);
typedef void (*ClawObserveWait)(void *context, uint32_t requestedMilliseconds);
typedef struct {
    void *context;
    ClawReadMillisecondClock read;
    // Optional instrumentation only. The original does not call Sleep.
    ClawObserveWait observeWait;
} ClawTimingHost;

// Timing portion of manager constructor 0x4b8240. The original leaves
// minimumFrameMilliseconds and both countdown words untouched.
void claw_timing_initialize(ClawTimingManager *manager, ClawClockState *clock, ClawTimingHost host);
// 0x4b83f0: exact busy polling, including unsigned deadline wrap and <=.
// read must eventually return a value greater than the computed deadline.
void claw_timing_wait(uint32_t milliseconds, ClawTimingHost host);
// 0x4b83a0; nonzero clearReportedRate assigns 0xffffffff.
void claw_timing_reset_rate(ClawTimingManager *manager, uint32_t clearReportedRate, ClawTimingHost host);
// 0x4b83d0: reads once, clears delta and pacedFrameStart only.
void claw_timing_reset_clock(ClawClockState *clock, ClawTimingHost host);
// 0x4b82f0: complete clock helper, returns 1.
uint32_t claw_timing_update(ClawTimingManager *manager, ClawClockState *clock, ClawTimingHost host);
// Timing portion of 0x428b60; publish even when game callback is paused.
void claw_timing_publish_stage(const ClawClockState *clock, ClawFrameClock *stage, uint32_t *accumulatedMilliseconds);
// Clock portion of 0x4c8fc0; zero refresh keeps both animation words unchanged.
void claw_timing_update_animation(ClawFrameClock *animation, uint32_t refresh, ClawTimingHost host);
// Timing portion of 0x42ae40; replay supplies clock values without a host read.
void claw_timing_set_replay(ClawFrameClock *stage, uint32_t *accumulatedMilliseconds, ClawFrameClock *animation,
                            uint32_t now, uint32_t delta, uint32_t accumulated);

#ifdef __cplusplus
}
#endif
#endif
