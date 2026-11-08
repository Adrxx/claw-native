// CutThroat object callback recovered from the original v1.0 instructions.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

int owned(uint32_t function) {
    return function == 0x4379d0 ? 1 : -1;
}

// 0x4379d0. Creates the creature or dispatches the object's current command.
uint32_t updateCutThroat(Run &run, uint32_t object) {
    uint32_t state = run.get(object + 0x6c); // Object's logic-state record.
    uint32_t command = run.get(state + 0x1c); // Current logic command.
    if (command == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t storage = run.call(0x4f63ec, 0, {0x480});
        uint32_t creature = 0;
        if (storage)
            creature = run.call(0x437a90, storage, {object});
        run.vcall(creature, 0x10);
        run.put(state + 0x18, creature); // Constructed creature pointer.
    } else if (command == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (command == 0x1e) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (command != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *arguments) {
    switch (function) {
    case 0x4379d0:
        return updateCutThroat(run, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_cut_throat_entry, owned, body)
