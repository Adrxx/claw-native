// FrontStatue object logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x471780:
        return 1;
    default:
        return -1;
    }
}

// 0x471780. cdecl, 1 stack argument(s), returns void.
uint32_t function_471780(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Global +0x52a194 selects the powerup configuration.
    run.put(0x52a194, 3);
    // Object +0x6c points to its configuration record.
    uint32_t configuration = run.get(object + 0x6c);
    // Configuration +0x64 is reset and +0x54 receives the sentinel.
    run.put(configuration + 0x64, 0);
    run.put(configuration + 0x54, 0xffffffff);
    return run.call(0x471530, 0, {object});
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x471780:
        return function_471780(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_front_statue_entry, owned, body)
