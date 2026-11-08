// Original v1.0 LavaGeyser callback: initialize its runtime object, dispatch
// command methods, or destroy it for other command values.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

constexpr uint32_t kLogicState = 0x6c; // Level-object pointer to callback state.
constexpr uint32_t kRuntimeObject = 0x18; // State's constructed geyser object.
constexpr uint32_t kCommand = 0x1c; // State's unsigned callback command.

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4559e0:
        return 1;
    default:
        return -1;
    }
}

// 0x4559e0. cdecl callback with one level-object argument; sets EAX to 1.
uint32_t function_4559e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t levelObject = arguments[0];
    uint32_t state = run.get(levelObject + kLogicState);
    uint32_t command = run.get(state + kCommand);
    if (command == 0) {
        run.put(state + kCommand, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0xa8});
        uint32_t geyser = 0;
        if (allocation)
            geyser = run.call(0x455ed0, allocation, {levelObject});
        run.vcall(geyser, 0x10); // Runtime initialization method.
        run.put(state + kRuntimeObject, geyser);
    } else if (command == 29) {
        run.vcall(run.get(state + kRuntimeObject), 0x20); // Command 29 method.
    } else if (command == 30) {
        run.vcall(run.get(state + kRuntimeObject), 0x1c); // Command 30 method.
    } else if (command != 1000) {
        run.call(0x4dc870, 0, {run.get(state + kRuntimeObject)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4559e0:
        return function_4559e0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_lava_geyser_entry, owned, body)
