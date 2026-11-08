#include "ClawRuntime.hpp"

namespace {

int owned(uint32_t function) {
    if (function == 0x49e470 || function == 0x4a2010)
        return 2;
    return -1;
}

uint32_t body(claw::Run &run, uint32_t function, uint32_t,
              const uint32_t *arguments) {
    const uint32_t object = arguments[0];
    // The two duration fields moved in the v1.3 object layout.
    const uint32_t firstOffset = function == 0x49e470 ? 0x148 : 0x164;
    const uint32_t secondOffset = function == 0x49e470 ? 0x14c : 0x168;
    if (run.get(object + firstOffset) == 0) {
        run.put(object + firstOffset, 0x5dc);
    }
    if (run.get(object + secondOffset) == 0) {
        run.put(object + secondOffset, 0x5dc);
    }
    const uint32_t secondDuration = run.get(object + secondOffset);
    const uint32_t firstDuration = run.get(object + firstOffset);
    // The destination stores the wrapping sum of both durations.
    run.put(arguments[1] + 0x4c, secondDuration + firstDuration);
    return object;
}

}

CLAW_MODULE_ENTRY(claw_oracle_profile_entry, owned, body)
