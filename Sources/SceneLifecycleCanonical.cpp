// Scene and controller lifecycle with resize orchestration
//
// Ordinary successful-return implementations from the original packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4ca2e0:
        return 0;
    case 0x4ca300:
        return 0;
    case 0x4cdf30:
        return 0;
    case 0x4cdf40:
        return 0;
    case 0x4ce9a0:
        return 1;
    case 0x4ce9c0:
        return 0;
    case 0x4ceef0:
        return 0;
    case 0x4cefc0:
        return 0;
    case 0x4cf020:
        return 3;
    case 0x4cf0a0:
        return 1;
    case 0x4cf0c0:
        return 0;
    case 0x4cf150:
        return 0;
    case 0x4cf160:
        return 1;
    case 0x4cf180:
        return 0;
    case 0x4cf280:
        return 1;
    case 0x4cf2a0:
        return 0;
    case 0x4cf800:
        return 1;
    case 0x4cf820:
        return 0;
    case 0x4cf8a0:
        return 1;
    case 0x4cf8c0:
        return 0;
    case 0x4cf930:
        return 0;
    case 0x4cf940:
        return 1;
    case 0x4cf960:
        return 0;
    case 0x4cf9d0:
        return 1;
    case 0x4cf9f0:
        return 0;
    case 0x4cfa80:
        return 0;
    case 0x4d0240:
        return 0;
    case 0x4d4370:
        return 0;
    case 0x4d6290:
        return 0;
    default:
        return -1;
    }
}

// Direct owned calls preserve the original guest frame for address-taken locals.
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

uint32_t invoke(Run &run, int32_t offset, uint32_t function, uint32_t receiver,
                std::initializer_list<uint32_t> arguments = {}) {
    uint32_t savedFrame = run.frame;
    uint32_t savedStack = run.stackPointer;
    uint32_t entry = run.automatic(offset);
    uint32_t result;
    if (owned(function) >= 0) {
        run.frame = entry;
        result = body(run, function, receiver, arguments.begin());
        run.frame = savedFrame;
    } else {
        run.stackPointer = entry;
        result = run.call(function, receiver, arguments);
    }
    run.stackPointer = savedStack;
    return result;
}

uint32_t virtualCall(Run &run, int32_t offset, uint32_t receiver, uint32_t slot,
                     std::initializer_list<uint32_t> arguments = {}) {
    return invoke(run, offset, run.get(run.get(receiver) + slot), receiver, arguments);
}

// Original map-clear bodies 0x4ca300, 0x4cdf40, 0x4d0240, 0x4d4370, 0x4d6290.
// Controller +0x10 is the map, +0x1c its count, +0x64 the selected palette.
uint32_t clearMap(Run &run, uint32_t receiver, bool earlyOutput, bool palette) {
    uint32_t position = run.automatic(-0x18);
    uint32_t output = run.automatic(-0x14);
    uint32_t key = run.automatic(-0x10);
    if (earlyOutput)
        run.put(output, 0);
    run.put(position, run.get(receiver + 0x1c) ? 0xffffffff : 0);
    invoke(run, -0x20, 0x4f6439, key);
    if (!earlyOutput)
        run.put(output, 0);
    if (run.get(position)) {
        do {
            invoke(run, -0x30, 0x4f5e1e, receiver + 0x10, {position, key, output});
            uint32_t value = run.get(output);
            if (value)
                virtualCall(run, -0x28, value, 0x04, {1});
        } while (run.get(position));
    }
    invoke(run, -0x20, 0x4f61a1, receiver + 0x10);
    if (palette)
        run.put(receiver + 0x64, 0);
    invoke(run, -0x20, 0x4f6584, key);
    return 0;
}

// Base controller fields: +0x04 type, +0x08 flags, +0x0c parent.
void finishController(Run &run, uint32_t receiver) {
    run.put(receiver + 0x04, 0xffffffff);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver, 0x50becc);
}

// Original entry 0x4ca2e0.
uint32_t function_4ca2e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    invoke(run, -0x08, 0x4ca300, receiver);
    run.put(receiver + 0x2c, 0);
    return 0;
}

// Original entry 0x4ca300.
uint32_t function_4ca300(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return clearMap(run, receiver, false, false);
}

// Original entry 0x4cdf30.
uint32_t function_4cdf30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return body(run, 0x4cdf40, receiver, arguments);
}

// Original entry 0x4cdf40.
uint32_t function_4cdf40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return clearMap(run, receiver, false, false);
}

// Original entry 0x4ce9a0.
uint32_t function_4ce9a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    invoke(run, -0x08, 0x4ce9c0, receiver);
    if (arguments[0] & 1)
        invoke(run, -0x0c, 0x4f6428, 0, {receiver});
    return receiver;
}

// Original entry 0x4ce9c0.
uint32_t function_4ce9c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x513ab8);
    invoke(run, -0x18, 0x4ceef0, receiver);
    run.put(receiver, 0x50becc);
    return 0;
}

// Original entry 0x4ceef0.
uint32_t function_4ceef0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    {
        uint32_t value = run.get(receiver + 0x28);
        if (value) {
            virtualCall(run, -0x14, value, 0x04, {1});
            run.put(receiver + 0x28, 0);
        }
    }
    {
        uint32_t value = run.get(receiver + 0x20);
        if (value) {
            virtualCall(run, -0x14, value, 0x00, {1});
            run.put(receiver + 0x20, 0);
        }
    }
    {
        uint32_t value = run.get(receiver + 0x04);
        if (value) {
            virtualCall(run, -0x14, value, 0x04, {1});
            run.put(receiver + 0x04, 0);
        }
    }
    {
        uint32_t value = run.get(receiver + 0x08);
        if (value) {
            virtualCall(run, -0x14, value, 0x04, {1});
            run.put(receiver + 0x08, 0);
        }
    }
    {
        uint32_t value = run.get(receiver + 0x0c);
        if (value) {
            virtualCall(run, -0x14, value, 0x04, {1});
            run.put(receiver + 0x0c, 0);
        }
    }
    {
        uint32_t value = run.get(receiver + 0x10);
        if (value) {
            virtualCall(run, -0x14, value, 0x04, {1});
            run.put(receiver + 0x10, 0);
        }
    }
    {
        uint32_t value = run.get(receiver + 0x14);
        if (value) {
            virtualCall(run, -0x14, value, 0x04, {1});
            run.put(receiver + 0x14, 0);
        }
    }
    {
        uint32_t value = run.get(receiver + 0x18);
        if (value) {
            virtualCall(run, -0x14, value, 0x04, {1});
            run.put(receiver + 0x18, 0);
        }
    }
    {
        uint32_t value = run.get(receiver + 0x2c);
        if (value) {
            virtualCall(run, -0x14, value, 0x04, {1});
            run.put(receiver + 0x2c, 0);
        }
    }
    {
        uint32_t value = run.get(receiver + 0x24);
        if (value) {
            virtualCall(run, -0x14, value, 0x04, {1});
            run.put(receiver + 0x24, 0);
        }
    }
    uint32_t graphics = run.get(receiver + 0x1c);
    if (graphics) {
        invoke(run, -0x10, 0x4bc1b0, graphics);
        invoke(run, -0x14, 0x4f6428, 0, {graphics});
        run.put(receiver + 0x1c, 0);
    }
    return 0;
}

// Original entry 0x4cefc0.
uint32_t function_4cefc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t display = run.get(receiver + 0x04);
    if (!display || !run.get(receiver + 0x08) || !run.get(receiver + 0x0c) ||
        !run.get(receiver + 0x10) || !run.get(receiver + 0x14))
        return 0;
    if (!virtualCall(run, -0x08, display, 0x14))
        return 0;
    return run.get(receiver + 0x24) ? 1 : 0;
}

// Original entry 0x4cf020.
uint32_t function_4cf020(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t display = run.get(receiver + 0x04);
    uint32_t primary = run.get(display + 0x10);
    if (run.get(primary + 0x10) == arguments[0] && run.get(primary + 0x14) == arguments[1])
        return 1;
    if (!invoke(run, -0x1c, 0x4ca960, display, {arguments[0], arguments[1], arguments[2]}))
        return 0;
    uint32_t world = run.get(receiver + 0x24);
    if (world && !invoke(run, -0x18, 0x4cb670, world, {arguments[0], arguments[1]}))
        return 0;
    return 1;
}

// Original entry 0x4cf0a0.
uint32_t function_4cf0a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    invoke(run, -0x08, 0x4cf0c0, receiver);
    if (arguments[0] & 1)
        invoke(run, -0x0c, 0x4f6428, 0, {receiver});
    return receiver;
}

// Original entry 0x4cf0c0.
uint32_t function_4cf0c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x513b28);
    invoke(run, -0x18, 0x4d4370, receiver);
    invoke(run, -0x18, 0x4f61f3, receiver + 0x48);
    invoke(run, -0x18, 0x4f61f3, receiver + 0x2c);
    invoke(run, -0x18, 0x4f61f3, receiver + 0x10);
    finishController(run, receiver);
    return 0;
}

// Original entry 0x4cf150.
uint32_t function_4cf150(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0x12;
}

// Original entry 0x4cf160.
uint32_t function_4cf160(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    invoke(run, -0x08, 0x4cf180, receiver);
    if (arguments[0] & 1)
        invoke(run, -0x0c, 0x4f6428, 0, {receiver});
    return receiver;
}

// Original entry 0x4cf180.
uint32_t function_4cf180(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x513b88);
    invoke(run, -0x18, 0x4cfa80, receiver);
    invoke(run, -0x18, 0x4f61f3, receiver + 0x10);
    finishController(run, receiver);
    return 0;
}

// Original entry 0x4cf280.
uint32_t function_4cf280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    invoke(run, -0x08, 0x4cf2a0, receiver);
    if (arguments[0] & 1)
        invoke(run, -0x0c, 0x4f6428, 0, {receiver});
    return receiver;
}

// Original entry 0x4cf2a0.
uint32_t function_4cf2a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x513be8);
    invoke(run, -0x18, 0x4c89f0, receiver);
    invoke(run, -0x18, 0x4f565f, receiver + 0x10);
    finishController(run, receiver);
    return 0;
}

// Original entry 0x4cf800.
uint32_t function_4cf800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    invoke(run, -0x08, 0x4cf820, receiver);
    if (arguments[0] & 1)
        invoke(run, -0x0c, 0x4f6428, 0, {receiver});
    return receiver;
}

// Original entry 0x4cf820.
uint32_t function_4cf820(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x513b00);
    invoke(run, -0x18, 0x4ca2e0, receiver);
    invoke(run, -0x18, 0x4f5d00, receiver + 0x10);
    finishController(run, receiver);
    return 0;
}

// Original entry 0x4cf8a0.
uint32_t function_4cf8a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    invoke(run, -0x08, 0x4cf8c0, receiver);
    if (arguments[0] & 1)
        invoke(run, -0x0c, 0x4f6428, 0, {receiver});
    return receiver;
}

// Original entry 0x4cf8c0.
uint32_t function_4cf8c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x513c20);
    invoke(run, -0x18, 0x4c89e0, receiver);
    invoke(run, -0x18, 0x4f565f, receiver + 0x10);
    finishController(run, receiver);
    return 0;
}

// Original entry 0x4cf930.
uint32_t function_4cf930(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0x13;
}

// Original entry 0x4cf940.
uint32_t function_4cf940(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    invoke(run, -0x08, 0x4cf960, receiver);
    if (arguments[0] & 1)
        invoke(run, -0x0c, 0x4f6428, 0, {receiver});
    return receiver;
}

// Original entry 0x4cf960.
uint32_t function_4cf960(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x513b60);
    invoke(run, -0x18, 0x4d6290, receiver);
    invoke(run, -0x18, 0x4f61f3, receiver + 0x10);
    finishController(run, receiver);
    return 0;
}

// Original entry 0x4cf9d0.
uint32_t function_4cf9d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    invoke(run, -0x08, 0x4cf9f0, receiver);
    if (arguments[0] & 1)
        invoke(run, -0x0c, 0x4f6428, 0, {receiver});
    return receiver;
}

// Original entry 0x4cf9f0.
uint32_t function_4cf9f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x513ad8);
    invoke(run, -0x18, 0x4cdf30, receiver);
    invoke(run, -0x18, 0x4f5d00, receiver + 0x10);
    finishController(run, receiver);
    return 0;
}

// Original entry 0x4cfa80.
uint32_t function_4cfa80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    virtualCall(run, -0x04, receiver, 0x58);
    run.put(0x54316c, 0);
    run.put(0x543170, 0);
    return 0;
}

// Original entry 0x4d0240.
uint32_t function_4d0240(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return clearMap(run, receiver, true, false);
}

// Original entry 0x4d4370.
uint32_t function_4d4370(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return clearMap(run, receiver, true, true);
}

// Original entry 0x4d6290.
uint32_t function_4d6290(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return clearMap(run, receiver, true, false);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4ca2e0:
        return function_4ca2e0(run, receiver, arguments);
    case 0x4ca300:
        return function_4ca300(run, receiver, arguments);
    case 0x4cdf30:
        return function_4cdf30(run, receiver, arguments);
    case 0x4cdf40:
        return function_4cdf40(run, receiver, arguments);
    case 0x4ce9a0:
        return function_4ce9a0(run, receiver, arguments);
    case 0x4ce9c0:
        return function_4ce9c0(run, receiver, arguments);
    case 0x4ceef0:
        return function_4ceef0(run, receiver, arguments);
    case 0x4cefc0:
        return function_4cefc0(run, receiver, arguments);
    case 0x4cf020:
        return function_4cf020(run, receiver, arguments);
    case 0x4cf0a0:
        return function_4cf0a0(run, receiver, arguments);
    case 0x4cf0c0:
        return function_4cf0c0(run, receiver, arguments);
    case 0x4cf150:
        return function_4cf150(run, receiver, arguments);
    case 0x4cf160:
        return function_4cf160(run, receiver, arguments);
    case 0x4cf180:
        return function_4cf180(run, receiver, arguments);
    case 0x4cf280:
        return function_4cf280(run, receiver, arguments);
    case 0x4cf2a0:
        return function_4cf2a0(run, receiver, arguments);
    case 0x4cf800:
        return function_4cf800(run, receiver, arguments);
    case 0x4cf820:
        return function_4cf820(run, receiver, arguments);
    case 0x4cf8a0:
        return function_4cf8a0(run, receiver, arguments);
    case 0x4cf8c0:
        return function_4cf8c0(run, receiver, arguments);
    case 0x4cf930:
        return function_4cf930(run, receiver, arguments);
    case 0x4cf940:
        return function_4cf940(run, receiver, arguments);
    case 0x4cf960:
        return function_4cf960(run, receiver, arguments);
    case 0x4cf9d0:
        return function_4cf9d0(run, receiver, arguments);
    case 0x4cf9f0:
        return function_4cf9f0(run, receiver, arguments);
    case 0x4cfa80:
        return function_4cfa80(run, receiver, arguments);
    case 0x4d0240:
        return function_4d0240(run, receiver, arguments);
    case 0x4d4370:
        return function_4d4370(run, receiver, arguments);
    case 0x4d6290:
        return function_4d6290(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_scene_lifecycle_canonical_entry, owned, body)
