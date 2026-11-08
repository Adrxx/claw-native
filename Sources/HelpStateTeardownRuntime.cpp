// Help screen state destructor
// Recovered from the original v1.0 owned-function disassembly.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x429670:
        return 1;
    case 0x429690:
        return 0;
    default:
        return -1;
    }
}

// 0x429690. Destroys the help screen state: sets the derived vtable, runs the
// member teardown at 0x449930, sets the base vtable, then runs the base
// destructor at 0x48f180. Both callees take the object in ECX.
uint32_t function_429690(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x50c11c);
    run.call(0x449930, receiver, {});
    run.put(receiver, 0x50b4ec);
    run.call(0x48f180, receiver, {});
    return 0;
}

// 0x429670. Scalar deleting destructor: tears the object down, then frees it
// when bit 0 of the flag argument is set. Returns the object.
uint32_t function_429670(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_429690(run, receiver, nullptr);
    if ((arguments[0] & 1) != 0)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x429670:
        return function_429670(run, receiver, arguments);
    case 0x429690:
        return function_429690(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_help_state_teardown_entry, owned, body)
