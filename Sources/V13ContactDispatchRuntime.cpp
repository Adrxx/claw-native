// v1.3 collision manager contact mode dispatcher
//
// Recovered from the original v1.3 dispatcher; movement helpers remain original.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4cc920:
        return 4;
    default:
        return -1;
    }
}

// 0x4cc920. thiscall, 4 stack argument(s), returns u32.
uint32_t function_4cc920(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t actor = arguments[0];
    const uint32_t x = arguments[1];
    const uint32_t y = arguments[2];
    const uint32_t options = arguments[3];
    // Manager +0x08 contains the alternate movement selector.
    if (run.get8(receiver + 0x08) & 4) {
        run.stackPointer = run.automatic(-0x14);
        return run.call(0x4d7860, receiver, {actor, x, y, options});
    }

    uint32_t result = 0;
    // Actor +0xe4 is movement mode; +0x5c and +0x60 are current X and Y.
    const uint32_t mode = run.get(actor + 0xe4);
    const uint32_t previousX = run.get(actor + 0x5c);
    const uint32_t previousY = run.get(actor + 0x60);
    run.stackPointer = run.automatic(-0x20);
    switch (mode) {
    case 1:
    case 2:
    case 5:
        result = run.call(0x4cca90, receiver, {actor, x, y, options});
        break;
    case 3:
        result = run.call(0x4cce20, receiver, {actor, x, y, options});
        if (run.get(actor + 0xe4) == 4)
            result |= 0x800000;
        break;
    case 4:
        result = run.call(0x4ccc60, receiver, {actor, x, y, options});
        if (run.get(actor + 0xe4) == 1)
            result |= 0x1000000;
        break;
    case 6:
        result = run.call(0x4ccf20, receiver, {actor, x, y, options});
        break;
    case 7:
        run.put(actor + 0x5c, x);
        run.put(actor + 0x60, y);
        break;
    case 8:
        if (s32(y) < s32(previousY)) {
            result = run.call(0x4cce20, receiver, {actor, x, y, options});
            if (run.get(actor + 0xe4) == 4) {
                result |= 0x800000;
                run.put(actor + 0xe4, 8);
            }
        } else {
            result = run.call(0x4ccc60, receiver, {actor, x, y, options});
            if (run.get(actor + 0xe4) == 1)
                result |= 0x1000000;
        }
        break;
    default:
        break;
    }
    if (result & 0x1820000)
        result |= 0x10000;
    // Actor +0x08 flags are loaded after the movement helper returns.
    const uint32_t flags = run.get(actor + 0x08);
    if (flags & 0x400000)
        result |= 0x100000;
    if (flags & 0x10)
        result |= 0x200000;
    if (run.get(actor + 0x5c) == previousX && run.get(actor + 0x60) == previousY)
        result |= 0x400000;
    return result;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4cc920:
        return function_4cc920(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_v13_contact_dispatch_entry, owned, body)
