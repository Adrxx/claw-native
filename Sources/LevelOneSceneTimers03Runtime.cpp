// Level 1 scene timer and Actor storage helpers
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4c9e20:
        return 0;
    case 0x4c9e40:
        return 2;
    case 0x4c9e50:
        return 3;
    case 0x4c9fa0:
        return 0;
    case 0x4c9fb0:
        return 0;
    case 0x4ca1b0:
        return 0;
    case 0x4d3f50:
        return 2;
    case 0x4d3f80:
        return 3;
    case 0x4d3fc0:
        return 3;
    default:
        return -1;
    }
}

// 0x4c9e20. cdecl, 0 stack argument(s), returns u32.
uint32_t function_4c9e20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0x16;
}

// 0x4c9e40. stdcall, 2 stack argument(s), returns u32.
uint32_t function_4c9e40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0;
}

// 0x4c9e50. stdcall, 3 stack argument(s), returns u32.
uint32_t function_4c9e50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0;
}

// 0x4c9fa0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4c9fa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return run.get(receiver + 0x6c) != 0 ? 1 : 0;
}

// 0x4c9fb0. cdecl, 0 stack argument(s), returns u32.
uint32_t function_4c9fb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0x1b;
}

// 0x4ca1b0. thiscall, 0 stack argument(s), returns void.
uint32_t function_4ca1b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x4d3eb0, receiver);
    run.put(receiver + 0x168, 0xffffffff);
    run.put(receiver + 0x16c, 0xffffffff);
    run.put(receiver + 0x174, 0);
    run.put(receiver + 0x170, 0);
    uint32_t first = run.get(receiver + 0x6c);
    if (first != 0) {
        run.vcall(first, 4, {1});
        run.put(receiver + 0x6c, 0);
    }
    uint32_t second = run.get(receiver + 0x70);
    if (second != 0) {
        run.vcall(second, 4, {1});
        run.put(receiver + 0x70, 0);
    }
    uint32_t third = run.get(receiver + 0x78);
    if (third != 0) {
        run.vcall(third, 4, {1});
        run.put(receiver + 0x78, 0);
    }
    run.put(receiver + 0xc4, 0xffffffff);
    run.put(receiver + 0xac, 0x80000000);
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    return 0;
}

// 0x4d3f50. thiscall, 2 stack argument(s), returns void.
uint32_t function_4d3f50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t node = run.get(receiver + 0x1b8);
    while (node != 0) {
        uint32_t next = run.get(node);
        uint32_t object = run.get(node + 8);
        run.vcall(object, 0x30, {arguments[0], arguments[1]});
        node = next;
    }
    return 0;
}

// 0x4d3f80. thiscall, 3 stack argument(s), returns void.
uint32_t function_4d3f80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t node = run.get(receiver + 0x1b8);
    while (node != 0) {
        uint32_t next = run.get(node);
        uint32_t object = run.get(node + 8);
        run.vcall(object, 0x34, {arguments[0], arguments[1], arguments[2]});
        node = next;
    }
    return 0;
}

// 0x4d3fc0. thiscall, 3 stack argument(s), returns void.
uint32_t function_4d3fc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t node = run.get(receiver + 0x1b8);
    while (node != 0) {
        uint32_t next = run.get(node);
        uint32_t object = run.get(node + 8);
        run.vcall(object, 0x38, {arguments[0], arguments[1], arguments[2]});
        node = next;
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4c9e20:
        return function_4c9e20(run, receiver, arguments);
    case 0x4c9e40:
        return function_4c9e40(run, receiver, arguments);
    case 0x4c9e50:
        return function_4c9e50(run, receiver, arguments);
    case 0x4c9fa0:
        return function_4c9fa0(run, receiver, arguments);
    case 0x4c9fb0:
        return function_4c9fb0(run, receiver, arguments);
    case 0x4ca1b0:
        return function_4ca1b0(run, receiver, arguments);
    case 0x4d3f50:
        return function_4d3f50(run, receiver, arguments);
    case 0x4d3f80:
        return function_4d3f80(run, receiver, arguments);
    case 0x4d3fc0:
        return function_4d3fc0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_scene_timers_03_entry, owned, body)
