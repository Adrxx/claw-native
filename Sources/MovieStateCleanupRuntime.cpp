// Movie state stop and cleanup, translated from the original v1.0 instructions.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x4efcd0:
        return 0;
    case 0x4efd00:
        return 0;
    default:
        return -1;
    }
}

// 0x4efd00. +0x0 initialized, +0x4/+0x8 active state, +0x124 embedded
// file object, and +0x134 playback status.
uint32_t stop(Run &run, uint32_t receiver) {
    if (run.get(receiver + 0x0) == 0)
        return 0;
    if (run.get(receiver + 0x4) == 0 && run.get(receiver + 0x8) == 0)
        return 0;
    run.vcall(receiver + 0x124, 0x54, {});
    run.put(receiver + 0x4, 0);
    run.put(receiver + 0x8, 0);
    run.put(receiver + 0x134, 0);
    return 1;
}

// 0x4efcd0. +0x138 is the embedded array reset by the original callee.
uint32_t cleanup(Run &run, uint32_t receiver) {
    if (run.get(receiver + 0x0) != 0) {
        stop(run, receiver);
        run.call(0x4f5915, receiver + 0x138, {0, 0xffffffff});
        run.put(receiver + 0x0, 0);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *) {
    switch (function) {
    case 0x4efcd0:
        return cleanup(run, receiver);
    case 0x4efd00:
        return stop(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_movie_state_cleanup_entry, owned, body)
