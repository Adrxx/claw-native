// JumpSwitch object logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x453b10:
        return 1;
    default:
        return -1;
    }
}

// 0x453b10. cdecl, 1 stack argument(s), returns void.
uint32_t function_453b10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // +0x6c points to the callback state; +0x1c is its event code.
    uint32_t state = run.get(object + 0x6c);
    uint32_t event = run.get(state + 0x1c);
    if (event == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x48});
        uint32_t instance = 0;
        if (allocation)
            instance = run.call(0x453bd0, allocation, {object});
        run.vcall(instance, 0x10);
        // +0x18 retains the constructed switch instance.
        run.put(state + 0x18, instance);
    } else if (event == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (event == 0x1e) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (event != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x453b10:
        return function_453b10(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_jump_switch_entry, owned, body)
