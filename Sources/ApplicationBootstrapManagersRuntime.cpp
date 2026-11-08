// Original application bootstrap manager construction
//
// Native translations of the five whole original bootstrap functions.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x493c20:
        return 0;
    case 0x4ec010:
        return 3;
    case 0x422890:
        return 1;
    case 0x430590:
        return 2;
    case 0x42b900:
        return 0;
    default:
        return -1;
    }
}

// 0x493c20. Receiver +4 owns the 128-byte character lookup buffer.
uint32_t function_493c20(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t buffer = run.call(0x4f63ec, 0, {0x80});
    run.put(receiver + 4, buffer);
    if (!buffer)
        return 0;
    for (uint32_t offset = 0; offset < 0x80; offset += 4)
        run.put(buffer + offset, 0);
    for (uint32_t index = 0; index < 10; ++index)
        run.put8(run.get(receiver + 4) + 0x30 + index, uint8_t(0x1b + index));
    for (uint32_t index = 0; index < 26; ++index)
        run.put8(run.get(receiver + 4) + 0x41 + index, uint8_t(index + 1));
    for (uint32_t index = 0; index < 26; ++index)
        run.put8(run.get(receiver + 4) + 0x61 + index, uint8_t(index + 1));
    const uint8_t punctuation[][2] = {
        {0x2c, 0x25}, {0x20, 0}, {0x2e, 0x26}, {0x21, 0x27},
        {0x3f, 0x28}, {0x3d, 0x29}, {0x3c, 0x2a}, {0x3e, 0x2b},
        {0x28, 0x2c}, {0x29, 0x2d}, {0x5b, 0x2e}, {0x5d, 0x2f},
        {0x40, 0x30}, {0x23, 0x31}, {0x24, 0x32}, {0x25, 0x33},
        {0x5e, 0x34}, {0x26, 0x35}, {0x2a, 0x36}
    };
    for (const auto &entry : punctuation)
        run.put8(run.get(receiver + 4) + entry[0], entry[1]);
    return 1;
}

// 0x4ec010. +0 owner, +4 resource, +8 initialized flag, +0x24 opaque handle.
uint32_t function_4ec010(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver, arguments[0]);
    run.put(receiver + 0x24, arguments[2]);
    run.put(receiver + 4, arguments[1]);
    run.put(receiver + 8, 1);
    return 1;
}

// 0x422890. +0 owner, +0x20 command text terminator, +0x120..128 state.
uint32_t function_422890(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver, arguments[0]);
    run.put8(receiver + 0x20, 0);
    run.put(receiver + 0x120, 0);
    run.put(receiver + 0x124, 0);
    run.put(receiver + 0x128, 0);
    run.call(0x4229c0, receiver);
    return 1;
}

// 0x430590. +0 input device; +4,+8,+0xc,+0x70 state; +0x74 name map.
uint32_t function_430590(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver, arguments[0]);
    run.put(receiver + 4, 0);
    run.put(receiver + 8, 0);
    run.put(receiver + 0xc, 0);
    run.put(receiver + 0x70, 0);
    run.call(0x430d30, receiver);
    run.call(0x430d80, receiver);
    uint32_t mode = run.get(0x53723c) == 0 ? 2 : 0;
    run.call(0x4b3430, run.get(receiver), {mode});
    run.call(0x4b3ab0, run.get(receiver));
    run.call(0x4b3490, run.get(receiver));
    // Device +0x214 contains the raw direction/button state.
    if (arguments[1] == 0 && (run.get(run.get(receiver) + 0x214) & 0xf0000000u))
        run.call(0x4b3430, run.get(receiver), {0});
    const uint32_t bindings[][2] = {
        {0x5263b0, 0}, {0x526540, 0x12}, {0x526538, 0x11}, {0x526530, 0x10},
        {0x526528, 0x20}, {0x526520, 0x2d}, {0x526518, 0x2e}, {0x52650c, 0x21},
        {0x526504, 0x22}, {0x5264fc, 0x24}, {0x5264f8, 0x23},
        {0x5264f4, 0x41}, {0x5264f0, 0x42}, {0x5264ec, 0x43}, {0x5264e8, 0x44},
        {0x5264e4, 0x45}, {0x5264e0, 0x46}, {0x5264dc, 0x47}, {0x5264d8, 0x48},
        {0x5264d4, 0x49}, {0x5264d0, 0x4a}, {0x5264cc, 0x4b}, {0x5264c8, 0x4c},
        {0x5264c4, 0x4d}, {0x5264c0, 0x4e}, {0x5264bc, 0x4f}, {0x5264b8, 0x50},
        {0x5264b4, 0x51}, {0x5264b0, 0x52}, {0x5264ac, 0x53}, {0x5264a8, 0x54},
        {0x5264a4, 0x55}, {0x5264a0, 0x56}, {0x52649c, 0x57}, {0x526498, 0x58},
        {0x526494, 0x59}, {0x526490, 0x5a},
        {0x52648c, 0x31}, {0x526488, 0x32}, {0x526484, 0x33}, {0x526480, 0x34},
        {0x52647c, 0x35}, {0x526478, 0x36}, {0x526474, 0x37}, {0x526470, 0x38},
        {0x52646c, 0x39}, {0x523cd0, 0x30},
        {0x526460, 0x61}, {0x526454, 0x62}, {0x526448, 0x63}, {0x52643c, 0x64},
        {0x526430, 0x65}, {0x526424, 0x66}, {0x526418, 0x67}, {0x52640c, 0x68},
        {0x526400, 0x69}, {0x5263f4, 0x60},
        {0x5263f0, 0x2d}, {0x5263ec, 0x3d}, {0x5263e8, 0x2c}, {0x5263e4, 0x2e},
        {0x5263e0, 0x2f}, {0x5263dc, 0x3b}, {0x5263d8, 0x27}, {0x5263d4, 0x5b},
        {0x5263d0, 0x5d}, {0x525f60, 0x5c}
    };
    for (const auto &binding : bindings) {
        uint32_t value = run.call(0x4f62a8, receiver + 0x74, {binding[0]});
        run.put(value, binding[1]);
    }
    run.call(0x431300, receiver);
    run.call(0x430ec0, receiver);
    return 1;
}

// 0x42b900. thiscall wrapper, no arguments, void result.
uint32_t function_42b900(Run &run, uint32_t receiver, const uint32_t *) {
    // push -1 followed by call: unchanged callee entry is eight bytes lower.
    run.stackPointer = run.frame - 8;
    run.call(0x42b140, receiver, {0xffffffffu});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x493c20:
        return function_493c20(run, receiver, arguments);
    case 0x4ec010:
        return function_4ec010(run, receiver, arguments);
    case 0x422890:
        return function_422890(run, receiver, arguments);
    case 0x430590:
        return function_430590(run, receiver, arguments);
    case 0x42b900:
        return function_42b900(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_application_bootstrap_managers_entry, owned, body)
