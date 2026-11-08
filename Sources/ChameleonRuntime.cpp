// Original Captain Claw v1.0 Chameleon object callback.
// Routes object state to creature creation, lifecycle methods, or update.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

int owned(uint32_t function) {
    return function == 0x421200 ? 1 : -1;
}

// 0x421200. cdecl object callback; original EAX is always 1 on return.
uint32_t chameleonCallback(Run &run, uint32_t object) {
    // Object +0x6c: logic record.
    uint32_t logic = run.get(object + 0x6c);
    // Logic +0x1c: callback state; +0x18: creature instance.
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        run.put(logic + 0x1c, 1000);
        uint32_t storage = run.call(0x4f63ec, 0, {0x488});
        uint32_t creature = 0;
        if (storage != 0)
            creature = run.call(0x421710, storage, {object});
        run.vcall(creature, 0x10);
        run.put(logic + 0x18, creature);
    } else if (state == 0x1d) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (state == 0x1e) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (state != 1000) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *arguments) {
    switch (function) {
    case 0x421200:
        return chameleonCallback(run, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_chameleon_entry, owned, body)
