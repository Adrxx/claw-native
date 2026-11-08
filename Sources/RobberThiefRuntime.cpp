// Original v1.0 RobberThief object-message callback.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x485270:
        return 1;
    default:
        return -1;
    }
}

// 0x485270. cdecl callback with one object argument; EAX is set to 1.
uint32_t dispatchMessage(Run &run, uint32_t object) {
    // Object +0x6c: callback state; state +0x1c: message code.
    uint32_t state = run.get(object + 0x6c);
    uint32_t message = run.get(state + 0x1c);
    if (message == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x478});
        uint32_t creature = 0;
        if (allocation)
            creature = run.call(0x485330, allocation, {object});
        run.vcall(creature, 0x10);
        // State +0x18: creature associated with this object.
        run.put(state + 0x18, creature);
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
    (void)receiver;
    switch (function) {
    case 0x485270:
        return dispatchMessage(run, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_robber_thief_entry, owned, body)
