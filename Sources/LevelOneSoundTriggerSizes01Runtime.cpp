// Level 1 sound trigger size variants
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
    case 0x48c450:
        return 1;
    case 0x48c470:
        return 1;
    case 0x48c490:
        return 1;
    case 0x48c4b0:
        return 1;
    case 0x48ca80:
        return 1;
    case 0x48caa0:
        return 1;
    case 0x48cac0:
        return 1;
    case 0x48cae0:
        return 1;
    default:
        return -1;
    }
}

// 0x48c450. cdecl, 1 stack argument(s), returns void.
uint32_t function_48c450(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    run.put(0x53c9b4, 0x3);
    run.call(0x48c1e0, 0, {arguments[0]});
    return 0;
}

// 0x48c470. cdecl, 1 stack argument(s), returns void.
uint32_t function_48c470(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    run.put(0x53c9b4, 0x4);
    run.call(0x48c1e0, 0, {arguments[0]});
    return 0;
}

// 0x48c490. cdecl, 1 stack argument(s), returns void.
uint32_t function_48c490(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    run.put(0x53c9b4, 0x5);
    run.call(0x48c1e0, 0, {arguments[0]});
    return 0;
}

// 0x48c4b0. cdecl, 1 stack argument(s), returns void.
uint32_t function_48c4b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    run.put(0x53c9b4, 0x6);
    run.call(0x48c1e0, 0, {arguments[0]});
    return 0;
}

// 0x48ca80. cdecl, 1 stack argument(s), returns void.
uint32_t function_48ca80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    run.put(0x53c9b4, 0x9);
    run.call(0x48c8f0, 0, {arguments[0]});
    return 0;
}

// 0x48caa0. cdecl, 1 stack argument(s), returns void.
uint32_t function_48caa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    run.put(0x53c9b4, 0xa);
    run.call(0x48c8f0, 0, {arguments[0]});
    return 0;
}

// 0x48cac0. cdecl, 1 stack argument(s), returns void.
uint32_t function_48cac0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    run.put(0x53c9b4, 0xb);
    run.call(0x48c8f0, 0, {arguments[0]});
    return 0;
}

// 0x48cae0. cdecl, 1 stack argument(s), returns void.
uint32_t function_48cae0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    run.put(0x53c9b4, 0xc);
    run.call(0x48c8f0, 0, {arguments[0]});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48c450:
        return function_48c450(run, receiver, arguments);
    case 0x48c470:
        return function_48c470(run, receiver, arguments);
    case 0x48c490:
        return function_48c490(run, receiver, arguments);
    case 0x48c4b0:
        return function_48c4b0(run, receiver, arguments);
    case 0x48ca80:
        return function_48ca80(run, receiver, arguments);
    case 0x48caa0:
        return function_48caa0(run, receiver, arguments);
    case 0x48cac0:
        return function_48cac0(run, receiver, arguments);
    case 0x48cae0:
        return function_48cae0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_sound_trigger_sizes_01_entry, owned, body)
