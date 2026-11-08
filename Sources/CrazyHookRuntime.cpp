// Original v1.0 CrazyHook object callback: initialization and message dispatch.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x434190:
        return 1;
    default:
        return -1;
    }
}

// Object +0x6c is callback state; state +0x18 is the creature and +0x1c
// is the message. Creature virtual slots +0x10, +0x20 and +0x1c are the
// initialization, message 29 and message 30 callbacks respectively.
constexpr uint32_t kCallbackState = 0x6c;
constexpr uint32_t kCreature = 0x18;
constexpr uint32_t kMessage = 0x1c;

// 0x434190. cdecl, one stack argument; EAX is 1 on normal return.
uint32_t function_434190(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + kCallbackState);
    uint32_t message = run.get(state + kMessage);
    if (message == 0) {
        run.put(state + kMessage, 1000);
        uint32_t creature = run.call(0x4f63ec, 0, {0x498});
        if (creature)
            creature = run.call(0x434250, creature, {object});
        run.vcall(creature, 0x10);
        run.put(state + kCreature, creature);
    } else if (message == 29) {
        run.vcall(run.get(state + kCreature), 0x20);
    } else if (message == 30) {
        run.vcall(run.get(state + kCreature), 0x1c);
    } else if (message != 1000) {
        run.call(0x4dc870, 0, {run.get(state + kCreature)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x434190:
        return function_434190(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_crazy_hook_entry, owned, body)
