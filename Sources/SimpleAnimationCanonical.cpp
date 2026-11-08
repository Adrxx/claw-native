// Simple Animation
//
// Recovered from the original v1.0 entry in the family packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x498f40:
        return 1;
    default:
        return -1;
    }
}

// 0x498f40 SimpleAnimation::logic. cdecl, 1 stack argument(s), returns u32.
uint32_t function_498f40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t object = arguments[0];
    // Object +0x6c points to state; state +0x1c holds the logic state.
    const uint32_t state = run.get(object + 0x6c);
    const uint32_t value = run.get(state + 0x1c);
    if (value == 0) {
        // Clear the state timer (+0x168) and object field (+0xc8).
        run.put(state + 0x168, 0);
        run.put(object + 0xc8, 0);
        run.put(state + 0x1c, 5);
    } else if (value == 5) {
        // The animation is embedded at +0x188; the global supplies its delta.
        run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x498f40:
        return function_498f40(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_simple_animation_entry, owned, body)
