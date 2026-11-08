// TowerCannonLeft object logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x495d40:
        return 1;
    default:
        return -1;
    }
}

// 0x495d40. cdecl, 1 stack argument(s), returns void.
uint32_t function_495d40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c); // Object's callback state record.
    uint32_t command = run.get(state + 0x1c); // State command.
    if (command == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t cannon = run.call(0x4f63ec, 0, {0x7c});
        if (cannon)
            cannon = run.call(0x495ec0, cannon, {object});
        run.vcall(cannon, 0x10);
        run.put(state + 0x18, cannon); // Constructed cannon instance.
    } else if (command == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (command == 0x1e) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (command != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x495d40:
        return function_495d40(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_tower_cannon_left_entry, owned, body)
