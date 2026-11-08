// Mercat object logic recovered against the original v1.0 instructions.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x45ff00:
        return 1;
    default:
        return -1;
    }
}

// 0x45ff00. Creates the creature on first use, then dispatches its state.
uint32_t function_45ff00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    constexpr uint32_t objectState = 0x6c;
    constexpr uint32_t creatureField = 0x18;
    constexpr uint32_t stateField = 0x1c;
    uint32_t object = arguments[0];
    // Object +0x6c points to the state record, whose +0x18 holds the creature
    // and +0x1c holds the dispatch state.
    uint32_t record = run.get(object + objectState);
    uint32_t state = run.get(record + stateField);
    if (state == 0) {
        run.put(record + stateField, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x4e0});
        uint32_t creature = 0;
        if (allocation != 0) {
            creature = run.call(0x45ffc0, allocation, {object});
        }
        run.vcall(creature, 0x10);
        run.put(record + creatureField, creature);
    } else if (state == 29) {
        run.vcall(run.get(record + creatureField), 0x20);
    } else if (state == 30) {
        run.vcall(run.get(record + creatureField), 0x1c);
    } else if (state != 1000) {
        run.call(0x4dc870, 0, {run.get(record + creatureField)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x45ff00:
        return function_45ff00(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_mercat_entry, owned, body)
