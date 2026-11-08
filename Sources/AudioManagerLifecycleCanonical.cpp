// Original audio manager initialization and lifecycle
//
// Translated from the hash-checked original packet disassembly.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
uint32_t function_4b4790(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b4860(Run &run, uint32_t receiver, const uint32_t *arguments);

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b3c80:
        return 0;
    case 0x4b4670:
        return 0;
    case 0x4b4710:
        return 0;
    case 0x4b4770:
        return 1;
    case 0x4b4790:
        return 0;
    case 0x4b47e0:
        return 2;
    case 0x4b4860:
        return 0;
    case 0x4b4b40:
        return 0;
    default:
        return -1;
    }
}

// 0x4b3c80. cdecl, 0 stack argument(s), returns void.
uint32_t function_4b3c80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    // Global volume lookup table, 101 entries at 0x541178.
    for (uint32_t index = 0; index <= 100; ++index) {
        uint32_t value = run.call(0x4b3b90, 0, {index});
        run.put(0x541178 + index * 4, value);
    }
    return 0;
}

// 0x4b4670. thiscall, 0 stack argument(s), returns void.
uint32_t function_4b4670(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // +0x10 parent manager; +0x78 enabled; +0x30 child list head.
    if (!run.get(run.get(receiver + 0x10) + 0x78))
        return 0;
    uint32_t link = run.get(receiver + 0x30);
    uint32_t node = link ? link - 4 : 0;
    while (node) {
        run.call(0x4b3e30, node, {});
        // +0x04 is the embedded next link, reloaded after stopping.
        link = run.get(node + 0x04);
        node = link ? link - 4 : 0;
    }
    return 0;
}

// 0x4b4710. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4b4710(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // +0x04, +0x08, +0x0c, +0x10 list state; +0x78 enabled.
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x10, 0);
    run.put(receiver, 0x513514);
    run.put(receiver + 0x78, 0);
    function_4b3c80(run, 0, nullptr);
    return receiver;
}

// 0x4b4770. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4b4770(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4b4790(run, receiver, nullptr);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4b4790. thiscall, 0 stack argument(s), returns void.
uint32_t function_4b4790(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver, 0x513514);
    if (run.get(receiver + 0x78))
        function_4b4860(run, receiver, nullptr);
    return 0;
}

// 0x4b47e0. thiscall, 2 stack argument(s), returns u32.
uint32_t function_4b47e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // +0x14 DirectSound device interface.
    if (run.call(0x4f4480, 0, {0, receiver + 0x14, 0}))
        return 0;
    uint32_t device = run.get(receiver + 0x14);
    uint32_t method = run.get(run.get(device) + 0x18);
    uint32_t result = run.call(method, 0, {device, arguments[0], arguments[1]});
    if (result) {
        run.call(0x4b4ed0, 0, {0x53228c, 0x27d, 1});
        device = run.get(receiver + 0x14);
        method = run.get(run.get(device) + 0x08);
        run.call(method, 0, {device});
        return 0;
    }
    // +0x7c initialization state; +0x78 enabled.
    run.put(receiver + 0x7c, 0);
    run.put(receiver + 0x78, 1);
    return 1;
}

// 0x4b4860. thiscall, 0 stack argument(s), returns void.
uint32_t function_4b4860(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x78)) {
        uint32_t link = run.get(receiver + 0x04);
        uint32_t node = link ? link - 4 : 0;
        while (node) {
            run.call(0x4b4ae0, receiver, {node});
            link = run.get(receiver + 0x04);
            node = link ? link - 4 : 0;
        }
        uint32_t device = run.get(receiver + 0x14);
        uint32_t method = run.get(run.get(device) + 0x08);
        run.call(method, 0, {device});
    }
    run.put(receiver + 0x78, 0);
    return 0;
}

// 0x4b4b40. thiscall, 0 stack argument(s), returns void.
uint32_t function_4b4b40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (!run.get(receiver + 0x78))
        return 0;
    uint32_t link = run.get(receiver + 0x04);
    uint32_t node = link ? link - 4 : 0;
    while (node) {
        run.call(0x4b3e30, node, {});
        function_4b4670(run, node, nullptr);
        link = run.get(node + 0x04);
        node = link ? link - 4 : 0;
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b3c80:
        return function_4b3c80(run, receiver, arguments);
    case 0x4b4670:
        return function_4b4670(run, receiver, arguments);
    case 0x4b4710:
        return function_4b4710(run, receiver, arguments);
    case 0x4b4770:
        return function_4b4770(run, receiver, arguments);
    case 0x4b4790:
        return function_4b4790(run, receiver, arguments);
    case 0x4b47e0:
        return function_4b47e0(run, receiver, arguments);
    case 0x4b4860:
        return function_4b4860(run, receiver, arguments);
    case 0x4b4b40:
        return function_4b4b40(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_audio_manager_lifecycle_entry, owned, body)
