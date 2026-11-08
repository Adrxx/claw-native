// Original graphics manager record constructor
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4ce960:
        return 0;
    default:
        return -1;
    }
}

// 0x4ce960. thiscall, no stack arguments, returns the constructed receiver.
uint32_t function_4ce960(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver, 0x513ab8);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x24, 0);
    run.put(receiver + 0x28, 0);
    run.put(receiver + 0x2c, 0);
    run.put(receiver + 0x34, 0);
    run.put(receiver + 0x38, 0);
    run.put(0x5430c8, 0);
    run.put(0x5430c4, 0);
    return receiver;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4ce960:
        return function_4ce960(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_graphics_record_constructor_entry, owned, body)
