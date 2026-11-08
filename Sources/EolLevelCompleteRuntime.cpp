// End-of-level level-complete command path
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
    case 0x42ae40:
        return 3;
    case 0x45fe20:
        return 0;
    case 0x462a00:
        return 1;
    case 0x462a20:
        return 0;
    case 0x46ab30:
        return 1;
    case 0x4d2230:
        return 0;
    case 0x4d4ab0:
        return 0;
    case 0x4d5120:
        return 1;
    default:
        return -1;
    }
}

// 0x42ae40. Stores three values in globals and mirrors the first two.
uint32_t function_42ae40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t first = arguments[0];
    uint32_t second = arguments[1];
    uint32_t third = arguments[2];
    run.put(0x537208, first);
    run.put(0x53720c, second);
    run.put(0x537210, third);
    run.put(0x5430c8, first);
    run.put(0x5430c4, second);
    return first;
}

// 0x45fe20. Resets a base object: +4 = -1, +8 = 0, +0xc = 0, vtable 0x50becc.
uint32_t function_45fe20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x04, 0xffffffff);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x00, 0x50becc);
    return 0;
}

// 0x462a20. Destructor body: vtable 0x50b16c, members at +0x2f4, +0x1a8, +0x1a4, final vtable 0x50b014.
uint32_t function_462a20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x00, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver + 0x00, 0x50b014);
    return 0;
}

// 0x462a00. Scalar deleting destructor: destroys, frees when bit 0 of the flag is set.
uint32_t function_462a00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t flags = arguments[0];
    function_462a20(run, receiver, nullptr);
    if ((flags & 1) != 0) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x46ab30. Level-complete command. Stores global 0x537210 at +0x760.
// Callee-entry ESP of each original call is the entry ESP minus the saved esi
// and edi, the pushed arguments and the return word.
uint32_t function_46ab30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t command = arguments[0];
    run.put(receiver + 0x760, run.get(0x537210));
    if (command == 0xb || command == 0xc) {
        uint32_t holder = run.get(receiver + 0x2c);
        if (holder != 0) {
            uint32_t object = run.get(run.get(holder + 0x10) + 0x04);
            uint32_t method = run.get(run.get(object) + 0x10);
            run.stackPointer = run.frame - 0x20;
            run.call(method, 0, {object, 0, 0, 0x100, receiver + 0x360});
        }
        run.stackPointer = run.frame - 0x0c;
        run.call(0x46dd90, receiver);
        run.stackPointer = 0;
        return 1;
    }
    if (run.get(receiver + 0x38) != 0) {
        run.stackPointer = run.frame - 0x0c;
        run.call(0x46bc90, receiver);
    }
    uint32_t owner = run.get(receiver + 0x04);
    if (owner != 0) {
        run.stackPointer = run.frame - 0x0c;
        run.call(0x4f650f, owner + 0xc0);
    }
    uint32_t holder = run.get(receiver + 0x2c);
    if (holder == 0) {
        run.stackPointer = 0;
        return 1;
    }
    run.stackPointer = run.frame - 0x24;
    run.call(0x4bb990, run.get(holder + 0x10), {0, 0x100, 0, 0, 0, 0x1f4});
    run.stackPointer = run.frame - 0x10;
    uint32_t inner = run.get(run.get(receiver + 0x0c) + 0x04);
    run.call(0x4b97c0, run.get(run.get(inner + 0x14) + 0x2c), {0});
    run.call(0x4b98b0, run.get(run.get(inner + 0x10) + 0x2c), {0});
    uint32_t inner2 = run.get(run.get(receiver + 0x0c) + 0x04);
    run.call(0x4b97c0, run.get(run.get(inner2 + 0x14) + 0x2c), {0});
    run.call(0x4b98b0, run.get(run.get(inner2 + 0x10) + 0x2c), {0});
    run.call(0x4bb8c0, run.get(run.get(receiver + 0x2c) + 0x10), {0});
    run.stackPointer = 0;
    return 1;
}

// 0x4d2230. Destructor: releases the member at +0xb0 and buffers at +0x20 and +0x24.
uint32_t function_4d2230(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x00, 0x513d40);
    uint32_t member = run.get(receiver + 0xb0);
    if (member != 0) {
        run.call(0x4d50e0, member);
    }
    uint32_t object = run.get(receiver + 0xb0);
    if (object != 0) {
        run.call(0x4d4b00, object);
        run.call(0x4f6428, 0, {object});
    }
    uint32_t first = run.get(receiver + 0x20);
    if (first != 0) {
        run.call(0x4f6428, 0, {first});
        run.put(receiver + 0x20, 0);
    }
    uint32_t second = run.get(receiver + 0x24);
    if (second != 0) {
        run.call(0x4f6428, 0, {second});
        run.put(receiver + 0x24, 0);
    }
    run.call(0x4f58de, receiver + 0x9c);
    run.put(receiver + 0x04, 0xffffffff);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x00, 0x50becc);
    return 0;
}

// 0x4d4ab0. Destructor: vtable 0x513dc8, 0x4f45f0, then base vtable 0x50becc.
uint32_t function_4d4ab0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x00, 0x513dc8);
    run.call(0x4f45f0, receiver);
    run.put(receiver + 0x00, 0x50becc);
    return 0;
}

// 0x4d5120. Walks a list with a local iterator, calling virtual +4 (arg 1) on each entry's +0x18 object.
uint32_t function_4d5120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t param = arguments[0];
    uint32_t iterator = run.automatic(-0x50);
    uint32_t count = 0;
    run.put(iterator + 0x00, 0x513de0);
    run.put(iterator + 0x04, 0);
    run.put(iterator + 0x08, 0);
    uint32_t entry = run.call(0x4f4860, iterator, {param, 0});
    while (entry != 0) {
        uint32_t object = run.get(entry + 0x18);
        if (object != 0) {
            run.vcall(object, 0x04, {1});
        }
        count = count + 1;
        entry = run.call(0x4f49c0, iterator);
    }
    return count;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42ae40:
        return function_42ae40(run, receiver, arguments);
    case 0x45fe20:
        return function_45fe20(run, receiver, arguments);
    case 0x462a00:
        return function_462a00(run, receiver, arguments);
    case 0x462a20:
        return function_462a20(run, receiver, arguments);
    case 0x46ab30:
        return function_46ab30(run, receiver, arguments);
    case 0x4d2230:
        return function_4d2230(run, receiver, arguments);
    case 0x4d4ab0:
        return function_4d4ab0(run, receiver, arguments);
    case 0x4d5120:
        return function_4d5120(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_eol_level_complete_entry, owned, body)
