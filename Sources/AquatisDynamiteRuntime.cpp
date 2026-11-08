// AquatisDynamite object logic
//
// Recovered from the original v1.0 disassembly.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x406dd0:
        return 1;
    default:
        return -1;
    }
}

// 0x406dd0. cdecl, 1 stack argument(s), returns void.
uint32_t function_406dd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c holds the logic state record.
    uint32_t state = run.get(object + 0x6c);
    // State +0x1c is the message code; +0x18 holds the runtime object.
    uint32_t message = run.get(state + 0x1c);
    if (message == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x54});
        uint32_t dynamite = 0;
        if (allocation)
            dynamite = run.call(0x4071a0, allocation, {object});
        run.vcall(dynamite, 0x10);
        run.put(state + 0x18, dynamite);
    } else if (message == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (message == 0x1e) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (message != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x406dd0:
        return function_406dd0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_aquatis_dynamite_entry, owned, body)
