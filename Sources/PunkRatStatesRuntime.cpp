// Retail PunkRat Level 2 states
//
// Recovered from the original v1.0 instructions in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x474330:
        return 1;
    case 0x4743f0:
        return 1;
    case 0x4746f0:
        return 1;
    case 0x474710:
        return 0;
    case 0x4747e0:
        return 1;
    case 0x474bc0:
        return 0;
    case 0x474c50:
        return 0;
    case 0x474d00:
        return 0;
    case 0x474db0:
        return 0;
    case 0x474e10:
        return 0;
    case 0x474e60:
        return 0;
    case 0x474ec0:
        return 0;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// Resolve indirect targets locally whenever this module owns the destination.
uint32_t indirectCall(Run &run, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
    int count = owned(function);
    if (count < 0) {
        return run.call(function, receiver, arguments);
    }
    if (uint32_t(count) != arguments.size()) {
        run.fail(CLAW_FAULT_ABI, function);
    }
    return body(run, function, receiver, arguments.begin());
}

uint32_t virtualCall(Run &run, uint32_t receiver, uint32_t offset, std::initializer_list<uint32_t> arguments = {}) {
    return indirectCall(run, run.get(run.get(receiver) + offset), receiver, arguments);
}

// Object fields: +0x0c actor, +0x10 state, +0x12c render object,
// +0x68 position, +0x80/+0x98 endpoints, +0x404 sound, +0x408 cannon.
uint32_t function_4743f0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_474710(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_474bc0(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x474330.
uint32_t function_474330(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c);
    uint32_t command = run.get(state + 0x1c);
    if (command == 0) {
        run.put(state + 0x1c, 1000);
        uint32_t result = run.call(0x4f63ec, 0, {0x410});
        if (result) {
            uint32_t input[] = {object};
            uint32_t frame = run.frame;
            run.frame = frame - 0x1c;
            result = function_4743f0(run, result, input);
            run.frame = frame;
        }
        virtualCall(run, result, 0x10);
        run.put(state + 0x18, result);
    } else if (command == 0x1d) {
        virtualCall(run, run.get(state + 0x18), 0x20);
    } else if (command == 0x1e) {
        virtualCall(run, run.get(state + 0x18), 0x1c);
    } else if (command != 1000) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}

// 0x4743f0.
uint32_t function_4743f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x4332f0, receiver, {arguments[0]});
    run.put(receiver, 0x50eee4);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x52a784});
    if (run.get(receiver + 0x2e4) == 0) {
        run.put(receiver + 0x2e4, 10);
    }
    uint32_t actor = run.get(receiver + 0x0c);
    if (run.get(actor + 0x148) == 0) {
        run.put(actor + 0x148, 500);
    }
    run.putd(receiver + 0x80, run.getd(receiver + 0x68) - run.getd(0x50eec8));
    run.putd(receiver + 0x98, run.getd(receiver + 0x68) - run.getd(0x50eed0));
    run.put(run.get(receiver + 0x0c) + 0x10c, 2);
    actor = run.get(receiver + 0x0c);
    uint32_t converted = run.call_x87(0x4a30e0, 0, double(run.gets(actor + 0x10c)) * double(run.getf(0x5262b4)));
    run.put(actor + 0x10c, converted);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0x404e0000);
    uint32_t resource = run.call(0x4061b0, run.get(run.get(run.get(receiver + 0x12c) + 0x0c) + 0x2c), {0x52a770});
    if (!resource) {
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x354, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x52a75c});
    if (!resource) {
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x350, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x52a748});
    if (!resource) {
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x314, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x52a730});
    if (!resource) {
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x310, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x52a71c});
    if (!resource) {
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x344, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x52a704});
    if (!resource) {
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x400, resource);
    uint32_t output = run.automatic(4);
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0x0c) + 0x28) + 0x10, {0x52a6f8, output});
    run.put(receiver + 0x404, run.get(output));
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0x0c) + 0x28) + 0x10, {0x52a6e8, output});
    run.put(receiver + 0x3a4, run.get(output));
    run.call(0x43fd60, receiver, {0x3c});
    run.put(run.get(receiver + 0x0c) + 0xcc, 2);
    uint32_t render = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(render + 0x190));
    run.call(0x4c8220, render + 0x188, {run.get(receiver + 0x314)});
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t size = run.get(receiver + 0x2fc);
    if (size <= 1) {
        run.call(0x4dbd20, receiver + 0x2f4, {1});
    } else {
        uint32_t bits = size <= 0x20 ? receiver + 0x300 : run.get(receiver + 0x300);
        run.put(bits, run.get(bits) | 2);
    }
    render = run.get(receiver + 0x12c);
    run.put(render + 0x08, run.get(render + 0x08) | 0x40);
    run.put(run.get(receiver + 0x12c) + 0xd0, 4);
    run.put(run.get(receiver + 0x12c) + 0xd4, 0x3000032);
    render = run.get(receiver + 0x12c);
    run.put(render + 0x128, 0xffffffec);
    run.put(render + 0x12c, 0xffffffd8);
    run.put(render + 0x130, 0x14);
    run.put(render + 0x134, 0x28);
    render = run.get(receiver + 0x12c);
    run.put(render + 0x118, 0xffffffd8);
    run.put(render + 0x11c, 0xffffffd8);
    run.put(render + 0x120, 0x28);
    run.put(render + 0x124, 0x28);
    return receiver;
}

// 0x4746f0.
uint32_t function_4746f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_474710(run, receiver, nullptr);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x474710.
uint32_t function_474710(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}

uint32_t stateSlot(Run &run, uint32_t command, uint32_t returnPC) {
    uint32_t lower = run.get(0x538460);
    if (s32(command) < s32(lower) || s32(command) > run.gets(0x538464)) {
        if (!run.call(0x4db6e0, 0x538458, {command, 0})) {
            uint32_t context = run.get(0x544b4c);
            // 0x4db5f0 only returns its caller PC; retain the original site.
            run.call(0x4db5f0, 0);
            run.put(0x544b14, returnPC);
            run.call(0x4db4d0, run.get(0x53845c), {0x538458, context, 0x0c});
            return run.get(0x53846c);
        }
        lower = run.get(0x538460);
    }
    return (command - lower) * run.get(0x538470) + run.get(0x538468);
}

// 0x4747e0.
uint32_t function_4747e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t command = arguments[0];
    run.put(0x538478, 0);
    uint32_t slot = stateSlot(run, command, 0x474840);
    if (run.get(slot)) {
        run.put(0x538478, 0);
        slot = stateSlot(run, command, 0x4748ba);
        indirectCall(run, run.get(slot), receiver);
    } else {
        run.call(0x43d490, receiver, {command});
    }
    return 0;
}

// 0x474bc0.
uint32_t function_474bc0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t actor = run.get(receiver + 0x0c);
    if (run.get(actor + 0x64) != 0xed8) {
        run.put(actor + 0x64, 0xed8);
        run.put(actor + 0x08, run.get(actor + 0x08) | 0x20000);
    }
    uint32_t render = run.get(receiver + 0x12c);
    uint32_t x = run.get(render + 0x4c) + ((run.get(render + 0x40) & 2) ? 0xffffffecu : 0);
    uint32_t y = run.get(render + 0x50) + 0x0f;
    uint32_t depth = run.get(render + 0x64) - 1;
    uint32_t cannon = run.call(0x4c8da0, run.get(run.get(run.get(receiver + 0x130) + 0x0c) + 0x08), {0, x, y, depth, 0x522d0c, 0x40000});
    run.put(receiver + 0x408, cannon);
    indirectCall(run, run.get(run.get(cannon + 0x6c) + 0x10), 0, {cannon});
    if (run.get8(run.get(receiver + 0x12c) + 0x40) & 2) {
        run.call(0x414a60, run.get(run.get(run.get(receiver + 0x408) + 0x6c) + 0x18));
    }
    return 0;
}

// Shared literal sequence in 0x474c50 and 0x474d00.
void idleSound(Run &run, uint32_t receiver) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    bool play = false;
    if (!run.get(0x541334)) {
        play = s32(run.call(0x4a3050, 0)) % 100 < 10;
    }
    if (play) {
        uint32_t sound = run.get(receiver + 0x404);
        if (sound && run.get(0x532c0c)) {
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
        }
    }
}

// 0x474c50. C3 is set both for equal and unordered comparisons.
uint32_t function_474c50(Run &run, uint32_t receiver, const uint32_t *) {
    idleSound(run, receiver);
    double position = run.getd(receiver + 0x68);
    double target = run.getd(receiver + 0x80);
    if (!(position < target) && !(position > target)) {
        if (!(run.get8(run.get(receiver + 0x12c) + 0x40) & 2) && run.get(0x534eac) != 0x26b7) {
            virtualCall(run, receiver, 0x58);
        } else {
            virtualCall(run, receiver, 0x70, {0x3c});
        }
    }
    return 0;
}

// 0x474d00.
uint32_t function_474d00(Run &run, uint32_t receiver, const uint32_t *) {
    idleSound(run, receiver);
    double position = run.getd(receiver + 0x68);
    double target = run.getd(receiver + 0x98);
    if (!(position < target) && !(position > target)) {
        if ((run.get8(run.get(receiver + 0x12c) + 0x40) & 2) && run.get(0x534eac) != 0x26b7) {
            virtualCall(run, receiver, 0x58);
        } else {
            virtualCall(run, receiver, 0x6c, {0x3c});
        }
    }
    return 0;
}

// 0x474db0.
uint32_t function_474db0(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t render = run.get(receiver + 0x12c);
    if (run.get(render + 0x1a4) && !run.get(render + 0x19c)) {
        run.call(0x414640, run.get(run.get(run.get(receiver + 0x408) + 0x6c) + 0x18));
        virtualCall(run, receiver, 0xa8);
    }
    return 0;
}

// 0x474e10.
uint32_t function_474e10(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t render = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(render + 0x190));
    run.call(0x4c8220, render + 0x188, {run.get(receiver + 0x400)});
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52a794});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    return 0;
}

// 0x474e60.
uint32_t function_474e60(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t render = run.get(receiver + 0x12c);
    if (run.get(render + 0x1a4) && !run.get(render + 0x19c)) {
        if (run.get8(render + 0x40) & 2) {
            virtualCall(run, receiver, 0x6c, {0x3c});
        } else {
            virtualCall(run, receiver, 0x70, {0x3c});
        }
    }
    return 0;
}

// 0x474ec0.
uint32_t function_474ec0(Run &run, uint32_t receiver, const uint32_t *) {
    virtualCall(run, receiver, 0x5c, {0});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x474330:
        return function_474330(run, receiver, arguments);
    case 0x4743f0:
        return function_4743f0(run, receiver, arguments);
    case 0x4746f0:
        return function_4746f0(run, receiver, arguments);
    case 0x474710:
        return function_474710(run, receiver, arguments);
    case 0x4747e0:
        return function_4747e0(run, receiver, arguments);
    case 0x474bc0:
        return function_474bc0(run, receiver, arguments);
    case 0x474c50:
        return function_474c50(run, receiver, arguments);
    case 0x474d00:
        return function_474d00(run, receiver, arguments);
    case 0x474db0:
        return function_474db0(run, receiver, arguments);
    case 0x474e10:
        return function_474e10(run, receiver, arguments);
    case 0x474e60:
        return function_474e60(run, receiver, arguments);
    case 0x474ec0:
        return function_474ec0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_punk_rat_states_entry, owned, body)
