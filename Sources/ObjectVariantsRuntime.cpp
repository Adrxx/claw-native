// Numbered variants of FloorSpike, SawBlade and SteppingStone (FloorSpike2, FloorSpike3, FloorSpike4, SawBlade2, SawBlade3, SteppingStone2, SteppingStone3, SteppingStone4)
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
    case 0x461fe0:
        return 1;
    case 0x462000:
        return 1;
    case 0x462020:
        return 1;
    case 0x4622f0:
        return 1;
    case 0x462310:
        return 1;
    case 0x49ead0:
        return 1;
    case 0x49eaf0:
        return 1;
    case 0x49eb10:
        return 1;
    default:
        return -1;
    }
}

// 0x461fe0. cdecl, 1 stack argument(s), returns void.
uint32_t function_461fe0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Selects variant 2 in the global at 0x537b8c, then runs the base function with the same object.
    run.put(0x537b8c, 2);
    run.stackPointer = run.frame - 8; // PUSH argument and CALL return word.
    run.call(0x461d50, 0, {arguments[0]});
    return 0;
}

// 0x462000. cdecl, 1 stack argument(s), returns void.
uint32_t function_462000(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Selects variant 3 in the global at 0x537b8c, then runs the base function with the same object.
    run.put(0x537b8c, 3);
    run.stackPointer = run.frame - 8; // PUSH argument and CALL return word.
    run.call(0x461d50, 0, {arguments[0]});
    return 0;
}

// 0x462020. cdecl, 1 stack argument(s), returns void.
uint32_t function_462020(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Selects variant 4 in the global at 0x537b8c, then runs the base function with the same object.
    run.put(0x537b8c, 4);
    run.stackPointer = run.frame - 8; // PUSH argument and CALL return word.
    run.call(0x461d50, 0, {arguments[0]});
    return 0;
}

// 0x4622f0. cdecl, 1 stack argument(s), returns void.
uint32_t function_4622f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Selects variant 2 in the global at 0x537b90, then runs the base function with the same object.
    run.put(0x537b90, 2);
    run.stackPointer = run.frame - 8; // PUSH argument and CALL return word.
    run.call(0x462040, 0, {arguments[0]});
    return 0;
}

// 0x462310. cdecl, 1 stack argument(s), returns void.
uint32_t function_462310(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Selects variant 3 in the global at 0x537b90, then runs the base function with the same object.
    run.put(0x537b90, 3);
    run.stackPointer = run.frame - 8; // PUSH argument and CALL return word.
    run.call(0x462040, 0, {arguments[0]});
    return 0;
}

// 0x49ead0. cdecl, 1 stack argument(s), returns void.
uint32_t function_49ead0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Selects variant 2 in the global at 0x53ebf0, then runs the base function with the same object.
    run.put(0x53ebf0, 2);
    run.stackPointer = run.frame - 8; // PUSH argument and CALL return word.
    run.call(0x49e810, 0, {arguments[0]});
    return 0;
}

// 0x49eaf0. cdecl, 1 stack argument(s), returns void.
uint32_t function_49eaf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Selects variant 3 in the global at 0x53ebf0, then runs the base function with the same object.
    run.put(0x53ebf0, 3);
    run.stackPointer = run.frame - 8; // PUSH argument and CALL return word.
    run.call(0x49e810, 0, {arguments[0]});
    return 0;
}

// 0x49eb10. cdecl, 1 stack argument(s), returns void.
uint32_t function_49eb10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Selects variant 4 in the global at 0x53ebf0, then runs the base function with the same object.
    run.put(0x53ebf0, 4);
    run.stackPointer = run.frame - 8; // PUSH argument and CALL return word.
    run.call(0x49e810, 0, {arguments[0]});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x461fe0:
        return function_461fe0(run, receiver, arguments);
    case 0x462000:
        return function_462000(run, receiver, arguments);
    case 0x462020:
        return function_462020(run, receiver, arguments);
    case 0x4622f0:
        return function_4622f0(run, receiver, arguments);
    case 0x462310:
        return function_462310(run, receiver, arguments);
    case 0x49ead0:
        return function_49ead0(run, receiver, arguments);
    case 0x49eaf0:
        return function_49eaf0(run, receiver, arguments);
    case 0x49eb10:
        return function_49eb10(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_object_variants_entry, owned, body)
