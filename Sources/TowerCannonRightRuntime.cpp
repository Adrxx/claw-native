// TowerCannonRight object logic
//
// Recovered from the original v1.0 disassembly.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x495e00:
        return 1;
    default:
        return -1;
    }
}

// 0x495e00. cdecl, 1 stack argument(s), returns void.
uint32_t function_495e00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c points to logic data; logic +0x1c is the event code.
    uint32_t logic = run.get(object + 0x6c);
    uint32_t event = run.get(logic + 0x1c);
    if (event == 0) {
        run.put(logic + 0x1c, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x7c});
        uint32_t cannon = 0;
        if (allocation)
            cannon = run.call(0x495f90, allocation, {object});
        run.vcall(cannon, 0x10);
        // Logic +0x18 holds the constructed cannon object.
        run.put(logic + 0x18, cannon);
    } else if (event == 0x1d) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (event == 0x1e) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (event != 1000) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x495e00:
        return function_495e00(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_tower_cannon_right_entry, owned, body)
