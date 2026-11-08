// TownGuard2 object logic
//
// Original callback state dispatch recovered against the canonical host.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4968d0:
        return 1;
    default:
        return -1;
    }
}

// 0x4968d0. Constructs the guard on first dispatch, then routes lifecycle
// requests or ordinary updates through the existing creature.
uint32_t function_4968d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    constexpr uint32_t objectContext = 0x6c;
    constexpr uint32_t contextCreature = 0x18;
    constexpr uint32_t contextState = 0x1c;
    uint32_t object = arguments[0];
    uint32_t context = run.get(object + objectContext);
    uint32_t state = run.get(context + contextState);
    if (state == 0) {
        run.put(context + contextState, 1000);
        uint32_t storage = run.call(0x4f63ec, 0, {0x498});
        uint32_t creature = 0;
        if (storage != 0) {
            creature = run.call(0x496990, storage, {object});
        }
        run.vcall(creature, 0x10);
        run.put(context + contextCreature, creature);
    } else if (state == 29) {
        run.vcall(run.get(context + contextCreature), 0x20);
    } else if (state == 30) {
        run.vcall(run.get(context + contextCreature), 0x1c);
    } else if (state != 1000) {
        run.call(0x4dc870, 0, {run.get(context + contextCreature)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4968d0:
        return function_4968d0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_town_guard2_entry, owned, body)
