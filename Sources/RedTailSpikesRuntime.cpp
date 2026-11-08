// RedTailSpikes object logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4842b0:
        return 1;
    default:
        return -1;
    }
}

// 0x4842b0. cdecl, 1 stack argument(s), returns void.
uint32_t function_4842b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c is the logic data; data +0x1c is the command and
    // data +0x18 is the spike controller.
    uint32_t data = run.get(object + 0x6c);
    uint32_t command = run.get(data + 0x1c);
    if (command == 0) {
        run.put(data + 0x1c, 1000);
        uint32_t controller = run.call(0x4f63ec, 0, {0x48});
        if (controller)
            controller = run.call(0x484680, controller, {object});
        run.vcall(controller, 0x10);
        run.put(data + 0x18, controller);
    } else if (command == 0x1d) {
        run.vcall(run.get(data + 0x18), 0x20);
    } else if (command == 0x1e) {
        run.vcall(run.get(data + 0x18), 0x1c);
    } else if (command != 1000) {
        run.call(0x4dc870, 0, {run.get(data + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4842b0:
        return function_4842b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_red_tail_spikes_entry, owned, body)
