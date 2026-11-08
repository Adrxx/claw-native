// LavaHand object logic
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4561c0:
        return 1;
    default:
        return -1;
    }
}

// 0x4561c0. cdecl, 1 stack argument(s), returns void.
uint32_t function_4561c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    // Object +0x6c points to logic data; +0x1c is the action and +0x18 the hand.
    uint32_t logic = run.get(object + 0x6c);
    uint32_t action = run.get(logic + 0x1c);
    if (action == 0) {
        run.put(logic + 0x1c, 1000);
        uint32_t memory = run.call(0x4f63ec, 0, {0xb8});
        uint32_t hand = 0;
        if (memory)
            hand = run.call(0x4566b0, memory, {object});
        run.vcall(hand, 0x10);
        run.put(logic + 0x18, hand);
    } else if (action == 0x1d) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (action == 0x1e) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (action != 1000) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4561c0:
        return function_4561c0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_lava_hand_entry, owned, body)
