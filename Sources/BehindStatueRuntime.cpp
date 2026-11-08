// BehindStatue object logic
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4717b0:
        return 1;
    default:
        return -1;
    }
}

// 0x4717b0. cdecl, 1 stack argument(s), returns void.
uint32_t function_4717b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    run.put(0x52a194, 2); // Global crate powerup variant.
    uint32_t descriptor = run.get(object + 0x6c); // Object descriptor.
    run.put(descriptor + 0x64, 0); // Descriptor powerup state.
    run.put(descriptor + 0x54, 1); // Descriptor activation flag.
    return run.call(0x471530, 0, {object});
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4717b0:
        return function_4717b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_behind_statue_entry, owned, body)
