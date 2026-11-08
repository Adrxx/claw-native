// BreakPlank callback: constructs the plank controller and dispatches object
// events to it. Controller construction and updates remain original callees.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x40f7b0:
        return 1;
    default:
        return -1;
    }
}

// 0x40f7b0. cdecl object callback; event 0 initializes, 29 and 30 dispatch
// controller methods, 1000 is idle, and other events update the controller.
uint32_t function_40f7b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c: callback data.
    uint32_t data = run.get(object + 0x6c);
    // Callback data +0x1c: event code; +0x18: controller pointer.
    uint32_t event = run.get(data + 0x1c);
    if (event == 0) {
        run.put(data + 0x1c, 1000);
        uint32_t controller = run.call(0x4f63ec, 0, {0xa4});
        if (controller != 0)
            controller = run.call(0x40f870, controller, {object});
        run.vcall(controller, 0x10);
        run.put(data + 0x18, controller);
    } else if (event == 29) {
        run.vcall(run.get(data + 0x18), 0x20);
    } else if (event == 30) {
        run.vcall(run.get(data + 0x18), 0x1c);
    } else if (event != 1000) {
        run.call(0x4dc870, 0, {run.get(data + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40f7b0:
        return function_40f7b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_break_plank_entry, owned, body)
