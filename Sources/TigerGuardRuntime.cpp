// Original v1.0 TigerGuard callback: constructs and activates the guard on
// initial state, dispatches lifecycle states, and forwards ordinary updates.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

constexpr uint32_t kCallbackState = 0x6c; // Callback owner: state object pointer.
constexpr uint32_t kGuard = 0x18; // State object: guard instance pointer.
constexpr uint32_t kState = 0x1c; // State object: lifecycle state code.

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x493eb0:
        return 1;
    default:
        return -1;
    }
}

// 0x493eb0. cdecl callback with one owner argument; EAX is set to 1.
uint32_t function_493eb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t owner = arguments[0];
    uint32_t stateObject = run.get(owner + kCallbackState);
    uint32_t state = run.get(stateObject + kState);
    if (state == 0) {
        run.put(stateObject + kState, 1000);
        uint32_t storage = run.call(0x4f63ec, 0, {0x4e0});
        uint32_t guard = 0;
        if (storage != 0)
            guard = run.call(0x494460, storage, {owner});
        run.vcall(guard, 0x10);
        run.put(stateObject + kGuard, guard);
    } else if (state == 0x1d) {
        run.vcall(run.get(stateObject + kGuard), 0x20);
    } else if (state == 0x1e) {
        run.vcall(run.get(stateObject + kGuard), 0x1c);
    } else if (state != 1000) {
        run.call(0x4dc870, 0, {run.get(stateObject + kGuard)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x493eb0:
        return function_493eb0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_tiger_guard_entry, owned, body)
