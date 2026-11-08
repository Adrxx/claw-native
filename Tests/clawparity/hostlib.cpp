// Native memory host for the comparison harness.
//
// The module under test reads and writes through ClawHost::bytes. This file
// serves those requests from three plain buffers that mirror the emulated
// machine's address space: a heap, the program image and the stack. In strict
// mode a heap access must lie inside one live object, so a native read or
// write outside the object the original touched is reported, not ignored.
#include "ClawRuntime.h"
#include <cstddef>

extern "C" {

size_t claw_host_sizeof() { return sizeof(ClawHost); }
size_t claw_host_offset(uint32_t index) {
    const size_t offsets[] = {offsetof(ClawHost, user), offsetof(ClawHost, bytes), offsetof(ClawHost, call),
                             offsetof(ClawHost, maximumOperations), offsetof(ClawHost, fault),
                             offsetof(ClawHost, faultAddress), offsetof(ClawHost, floatResult),
                             offsetof(ClawHost, entryStackPointer), offsetof(ClawHost, remainingOperations),
                             offsetof(ClawHost, compilerContext), offsetof(ClawHost, sourceContext), offsetof(ClawHost, sourceReturnPC),
                             offsetof(ClawHost, guestSession), offsetof(ClawHost, callbackCPU)};
    return index < sizeof(offsets) / sizeof(offsets[0]) ? offsets[index] : size_t(-1);
}

uint32_t claw_call_argument_capacity() { return CLAW_CALL_ARGUMENT_CAPACITY; }
size_t claw_call_sizeof() { return sizeof(ClawCall); }
size_t claw_call_offset(uint32_t index) {
    const size_t offsets[] = {offsetof(ClawCall, function), offsetof(ClawCall, receiver),
        offsetof(ClawCall, receiver2), offsetof(ClawCall, argumentCount), offsetof(ClawCall, arguments),
        offsetof(ClawCall, stackPointer), offsetof(ClawCall, x87ArgumentCount), offsetof(ClawCall, x87Argument),
        offsetof(ClawCall, compilerContext), offsetof(ClawCall, sourceContext), offsetof(ClawCall, sourceReturnPC),
        offsetof(ClawCall, sourceTransferVersion), offsetof(ClawCall, sourceTransferKind),
        offsetof(ClawCall, sourceTransferSite), offsetof(ClawCall, sourceCallerFunction), offsetof(ClawCall, sourceDisposition), offsetof(ClawCall, x87State), offsetof(ClawCall, x87Operation), offsetof(ClawCall, callbackCPU), offsetof(ClawCall, callbackActivation)};
    return index < sizeof(offsets) / sizeof(offsets[0]) ? offsets[index] : size_t(-1);
}
size_t claw_callback_cpu_sizeof() { return sizeof(ClawCallbackCPU); }
size_t claw_callback_cpu_offset(uint32_t index) {
    const size_t offsets[] = {offsetof(ClawCallbackCPU, size), offsetof(ClawCallbackCPU, version),
        offsetof(ClawCallbackCPU, target), offsetof(ClawCallbackCPU, entryStackPointer),
        offsetof(ClawCallbackCPU, activation), offsetof(ClawCallbackCPU, cpu)};
    return index < sizeof(offsets) / sizeof(offsets[0]) ? offsets[index] : size_t(-1);
}
size_t claw_source_disposition_sizeof() { return sizeof(ClawSourceDisposition); }
size_t claw_source_disposition_offset(uint32_t index) {
    const size_t offsets[] = {offsetof(ClawSourceDisposition, size), offsetof(ClawSourceDisposition, version),
        offsetof(ClawSourceDisposition, disposition), offsetof(ClawSourceDisposition, callerFunction),
        offsetof(ClawSourceDisposition, sourceSite), offsetof(ClawSourceDisposition, targetFunction),
        offsetof(ClawSourceDisposition, entryStackPointer), offsetof(ClawSourceDisposition, returnPC),
        offsetof(ClawSourceDisposition, request)};
    return index < sizeof(offsets) / sizeof(offsets[0]) ? offsets[index] : size_t(-1);
}
size_t claw_context_sizeof() { return sizeof(ClawCompilerContext); }
size_t claw_context_offset(uint32_t index) {
    const size_t offsets[] = {offsetof(ClawCompilerContext, size), offsetof(ClawCompilerContext, version),
        offsetof(ClawCompilerContext, inputMask), offsetof(ClawCompilerContext, outputMask),
        offsetof(ClawCompilerContext, eax), offsetof(ClawCompilerContext, ebx), offsetof(ClawCompilerContext, ecx),
        offsetof(ClawCompilerContext, edx), offsetof(ClawCompilerContext, esi), offsetof(ClawCompilerContext, edi),
        offsetof(ClawCompilerContext, ebp), offsetof(ClawCompilerContext, esp), offsetof(ClawCompilerContext, eip),
        offsetof(ClawCompilerContext, eflags), offsetof(ClawCompilerContext, fsHead),
        offsetof(ClawCompilerContext, continuation), offsetof(ClawCompilerContext, reserved0),
        offsetof(ClawCompilerContext, reserved1)};
    return index < sizeof(offsets) / sizeof(offsets[0]) ? offsets[index] : size_t(-1);
}

size_t claw_source_sizeof() { return sizeof(ClawSourceContext); }
size_t claw_source_offset(uint32_t index) {
    const size_t offsets[] = {offsetof(ClawSourceContext, size), offsetof(ClawSourceContext, version),
        offsetof(ClawSourceContext, inputMask), offsetof(ClawSourceContext, outputMask),
        offsetof(ClawSourceContext, eax), offsetof(ClawSourceContext, ebx), offsetof(ClawSourceContext, ecx),
        offsetof(ClawSourceContext, edx), offsetof(ClawSourceContext, esi), offsetof(ClawSourceContext, edi),
        offsetof(ClawSourceContext, ebp), offsetof(ClawSourceContext, esp), offsetof(ClawSourceContext, eip),
        offsetof(ClawSourceContext, eflags), offsetof(ClawSourceContext, fsHead),
        offsetof(ClawSourceContext, preserveMask), offsetof(ClawSourceContext, reserved0),
        offsetof(ClawSourceContext, reserved1)};
    return index < sizeof(offsets) / sizeof(offsets[0]) ? offsets[index] : size_t(-1);
}

struct ClawArenaSpan {
    uint32_t token;
    uint32_t size;
};

struct ClawArena {
    uint8_t *heap;
    uint32_t heapBase;
    uint32_t heapSize;
    uint8_t *image;
    uint32_t imageBase;
    uint32_t imageSize;
    uint8_t *stack;
    uint32_t stackBase;
    uint32_t stackSize;
    const ClawArenaSpan *spans; // sorted by token, never overlapping
    uint32_t spanCount;
    uint32_t strict;
    uint64_t accesses;
};

static bool inside(uint32_t token, uint64_t end, uint32_t base, uint32_t size) {
    return token >= base && end <= uint64_t(base) + size;
}

uint8_t *claw_arena_bytes(void *user, uint32_t token, uint32_t count) {
    ClawArena *arena = static_cast<ClawArena *>(user);
    arena->accesses++;
    uint64_t end = uint64_t(token) + count;
    if (inside(token, end, arena->heapBase, arena->heapSize)) {
        if (arena->strict) {
            uint32_t low = 0, high = arena->spanCount;
            while (low < high) { // first span whose token is above `token`
                uint32_t middle = low + (high - low) / 2;
                if (arena->spans[middle].token <= token)
                    low = middle + 1;
                else
                    high = middle;
            }
            if (!low)
                return nullptr;
            const ClawArenaSpan &span = arena->spans[low - 1];
            if (end > uint64_t(span.token) + span.size)
                return nullptr;
        }
        return arena->heap + (token - arena->heapBase);
    }
    if (inside(token, end, arena->imageBase, arena->imageSize))
        return arena->image + (token - arena->imageBase);
    if (inside(token, end, arena->stackBase, arena->stackSize))
        return arena->stack + (token - arena->stackBase);
    return nullptr;
}

} // extern "C"

extern "C" size_t claw_x87_state_sizeof() { return sizeof(ClawX87State); }
extern "C" size_t claw_x87_state_offset(uint32_t index) {
    const size_t offsets[] = {offsetof(ClawX87State, size), offsetof(ClawX87State, version), offsetof(ClawX87State, control), offsetof(ClawX87State, status), offsetof(ClawX87State, count), offsetof(ClawX87State, popCount), offsetof(ClawX87State, pushCount), offsetof(ClawX87State, returned), offsetof(ClawX87State, eax), offsetof(ClawX87State, edx), offsetof(ClawX87State, reserved0), offsetof(ClawX87State, reserved1), offsetof(ClawX87State, slots)};
    return index < sizeof(offsets) / sizeof(offsets[0]) ? offsets[index] : size_t(-1);
}

extern "C" size_t claw_x87_value_sizeof() { return sizeof(ClawX87Value); }
extern "C" size_t claw_x87_value_offset(uint32_t index) {
    const size_t offsets[] = {offsetof(ClawX87Value, significand), offsetof(ClawX87Value, signExponent), offsetof(ClawX87Value, reserved)};
    return index < sizeof(offsets) / sizeof(offsets[0]) ? offsets[index] : size_t(-1);
}
