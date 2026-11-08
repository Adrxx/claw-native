// Original actor and logic destruction
//
// Normal-return game effects translated from the hash-verified original packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x47cc80:
        return 1;
    case 0x47cca0:
        return 0;
    case 0x48cf50:
        return 1;
    case 0x4c80c0:
        return 1;
    case 0x4c80e0:
        return 0;
    case 0x4c99a0:
        return 1;
    case 0x4c99c0:
        return 0;
    case 0x4c9a70:
        return 0;
    case 0x4c9b30:
        return 1;
    case 0x4c9b50:
        return 0;
    case 0x4c9be0:
        return 1;
    case 0x4c9c00:
        return 0;
    case 0x4c9e60:
        return 1;
    case 0x4c9e80:
        return 0;
    case 0x4dbcd0:
        return 0;
    default:
        return -1;
    }
}

uint32_t function_47cca0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_48cf50(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c80e0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c99c0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9a70(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9b50(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9c00(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9e80(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4dbcd0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_47cc80(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c80c0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c99a0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9b30(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9be0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9e60(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x47cc80. thiscall, 1 stack argument(s), returns u32.
uint32_t function_47cc80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_47cca0(run, receiver, arguments);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x47cca0. thiscall, 0 stack argument(s), returns void.
uint32_t function_47cca0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // +0x00 vtable; +0x2f4 embedded registry buffer; +0x1a8/+0x1a4 strings.
    run.put(receiver + 0x00, 0x50b16c);
    function_4dbcd0(run, receiver + 0x2f4, arguments);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver + 0x00, 0x50b014);
    return 0;
}

// 0x48cf50. cdecl, 1 stack argument(s), returns void.
uint32_t function_48cf50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = run.get(0x53c9ac);
    if (object && arguments[0] == run.get(0x53c9b0)) {
        // +0x6c active object; +0x1c logic kind; +0x130 state.
        uint32_t active = run.get(object + 0x6c);
        if (active && run.get(active + 0x1c) == 0x0f) {
            run.put(active + 0x130, 0);
            run.put(0x53c9b0, 0);
        }
    }
    return 0;
}

// 0x4c80c0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4c80c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4c80e0(run, receiver, arguments);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x4c80e0. thiscall, 0 stack argument(s), returns void.
uint32_t function_4c80e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // +0x10 count; +0x14 owned buffer; +0x18 virtual child.
    run.put(receiver + 0x00, 0x513740);
    uint32_t buffer = run.get(receiver + 0x14);
    run.put(receiver + 0x10, 0);
    if (buffer) {
        run.call(0x4f6428, 0, {buffer});
        run.put(receiver + 0x14, 0);
    }
    uint32_t child = run.get(receiver + 0x18);
    if (child) {
        run.vcall(child, 0x00, {1});
        run.put(receiver + 0x18, 0);
    }
    // Base +0x08/+0x0c state, +0x04 invalid index.
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x04, 0xffffffff);
    run.put(receiver + 0x00, 0x50becc);
    return 0;
}

// 0x4c99a0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4c99a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4c99c0(run, receiver, arguments);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x4c99c0. thiscall, 0 stack argument(s), returns void.
uint32_t function_4c99c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // +0x6c/+0x70/+0x78 virtual children; reload after each callback.
    run.put(receiver + 0x00, 0x513770);
    uint32_t child = run.get(receiver + 0x6c);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x6c, 0);
    }
    child = run.get(receiver + 0x70);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x70, 0);
    }
    child = run.get(receiver + 0x78);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x78, 0);
    }
    // +0xac/+0xc4 bounds, +0x20/+0x38 position, +0x4c state sentinel.
    run.put(receiver + 0xac, 0x80000000);
    run.put(receiver + 0xc4, 0xffffffff);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x04, 0xffffffff);
    run.put(receiver + 0x00, 0x50becc);
    return 0;
}

// 0x4c9a70. thiscall, 0 stack argument(s), returns void.
uint32_t function_4c9a70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t child = run.get(receiver + 0x6c);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x6c, 0);
    }
    child = run.get(receiver + 0x70);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x70, 0);
    }
    child = run.get(receiver + 0x78);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x78, 0);
    }
    run.put(receiver + 0xac, 0x80000000);
    run.put(receiver + 0xc4, 0xffffffff);
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    return 0;
}

// 0x4c9b30. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4c9b30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4c9b50(run, receiver, arguments);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x4c9b50. thiscall, 0 stack argument(s), returns void.
uint32_t function_4c9b50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x00, 0x513870);
    run.call(0x4c8210, receiver);
    run.put(receiver + 0x00, 0x50becc);
    return 0;
}

// 0x4c9be0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4c9be0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4c9c00(run, receiver, arguments);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x4c9c00. thiscall, 0 stack argument(s), returns void.
uint32_t function_4c9c00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x00, 0x5137f0);
    uint32_t child = run.get(receiver + 0x6c);
    // +0x168/+0x16c indices; +0x174/+0x170 pointers.
    run.put(receiver + 0x168, 0xffffffff);
    run.put(receiver + 0x16c, 0xffffffff);
    run.put(receiver + 0x174, 0);
    run.put(receiver + 0x170, 0);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x6c, 0);
    }
    child = run.get(receiver + 0x70);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x70, 0);
    }
    child = run.get(receiver + 0x78);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x78, 0);
    }
    run.put(receiver + 0xc4, 0xffffffff);
    run.put(receiver + 0xac, 0x80000000);
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    run.put(receiver + 0x20, 0x80000000);
    // +0x188 embedded animation state, whose reset remains original-backed.
    run.put(receiver + 0x188, 0x513870);
    run.call(0x4c8210, receiver + 0x188);
    run.put(receiver + 0x188, 0x50becc);
    run.put(receiver + 0x00, 0x513770);
    child = run.get(receiver + 0x6c);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x6c, 0);
    }
    child = run.get(receiver + 0x70);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x70, 0);
    }
    child = run.get(receiver + 0x78);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x78, 0);
    }
    run.put(receiver + 0xac, 0x80000000);
    run.put(receiver + 0xc4, 0xffffffff);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    run.put(receiver + 0x04, 0xffffffff);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x00, 0x50becc);
    return 0;
}

// 0x4c9e60. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4c9e60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4c9e80(run, receiver, arguments);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x4c9e80. thiscall, 0 stack argument(s), returns void.
uint32_t function_4c9e80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x00, 0x5137b0);
    uint32_t child = run.get(receiver + 0x6c);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x6c, 0);
    }
    child = run.get(receiver + 0x70);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x70, 0);
    }
    child = run.get(receiver + 0x78);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x78, 0);
    }
    run.put(receiver + 0xac, 0x80000000);
    run.put(receiver + 0xc4, 0xffffffff);
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    run.put(receiver + 0x00, 0x513770);
    child = run.get(receiver + 0x6c);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x6c, 0);
    }
    child = run.get(receiver + 0x70);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x70, 0);
    }
    child = run.get(receiver + 0x78);
    if (child) {
        run.vcall(child, 0x04, {1});
        run.put(receiver + 0x78, 0);
    }
    run.put(receiver + 0xac, 0x80000000);
    run.put(receiver + 0xc4, 0xffffffff);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x04, 0xffffffff);
    run.put(receiver + 0x00, 0x50becc);
    return 0;
}

// 0x4dbcd0. thiscall, 0 stack argument(s), returns void.
uint32_t function_4dbcd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // +0x08 unsigned capacity; +0x0c buffer; +0x04 original registry receiver.
    uint32_t capacity = run.get(receiver + 0x08);
    run.put(receiver + 0x00, 0x513e34);
    if (capacity > 0x20) {
        run.call(0x4a49b0, 0, {run.get(receiver + 0x0c)});
    }
    run.call(0x4db6c0, receiver);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x47cc80:
        return function_47cc80(run, receiver, arguments);
    case 0x47cca0:
        return function_47cca0(run, receiver, arguments);
    case 0x48cf50:
        return function_48cf50(run, receiver, arguments);
    case 0x4c80c0:
        return function_4c80c0(run, receiver, arguments);
    case 0x4c80e0:
        return function_4c80e0(run, receiver, arguments);
    case 0x4c99a0:
        return function_4c99a0(run, receiver, arguments);
    case 0x4c99c0:
        return function_4c99c0(run, receiver, arguments);
    case 0x4c9a70:
        return function_4c9a70(run, receiver, arguments);
    case 0x4c9b30:
        return function_4c9b30(run, receiver, arguments);
    case 0x4c9b50:
        return function_4c9b50(run, receiver, arguments);
    case 0x4c9be0:
        return function_4c9be0(run, receiver, arguments);
    case 0x4c9c00:
        return function_4c9c00(run, receiver, arguments);
    case 0x4c9e60:
        return function_4c9e60(run, receiver, arguments);
    case 0x4c9e80:
        return function_4c9e80(run, receiver, arguments);
    case 0x4dbcd0:
        return function_4dbcd0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_actor_destruction_canonical_entry, owned, body)
