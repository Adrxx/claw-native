// Level 1 closure: Rat logic helpers
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
    case 0x47cd70:
        return 1;
    case 0x47d4b0:
        return 0;
    case 0x47d540:
        return 0;
    case 0x47d5d0:
        return 0;
    case 0x47d780:
        return 0;
    default:
        return -1;
    }
}

// Shared prologue of the three Rat state setters (0x47d4b0, 0x47d540, 0x47d5d0).
// Object fields: +0x10 sub-object (+0x1c handle), +0x24 saved handle, +0x50 and
// +0x54 cleared, +0x12c owner (+0x188 sub-object, +0x190 value), +0x134 copy of
// the owner value, +0x1a0 cleared. Returns nothing; the caller stores the rest.
void ratSetterCommon(Run &run, uint32_t self, uint32_t argumentOffset) {
    run.put(self + 0x50, 0);
    run.put(self + 0x54, 0);
    uint32_t handleOwner = run.get(self + 0x10);
    uint32_t savedHandle = run.get(handleOwner + 0x1c);
    run.put(self + 0x24, savedHandle);
    uint32_t handle = run.call(0x4dba00, 0x537668, {0x52b0b0});
    uint32_t handleOwnerAgain = run.get(self + 0x10);
    run.put(handleOwnerAgain + 0x1c, handle);
    uint32_t owner = run.get(self + 0x12c);
    uint32_t argument = run.get(self + argumentOffset);
    uint32_t ownerValue = run.get(owner + 0x190);
    run.put(self + 0x134, ownerValue);
    run.call(0x4c8220, owner + 0x188, {argument});
    run.put(self + 0x1a0, 0);
}

// Globals used by 0x47cd70: 0x53c0e8 table object, 0x53c0ec its allocator
// receiver, 0x53c0f0 lowest index, 0x53c0f4 highest index, 0x53c0f8 entries,
// 0x53c0fc fallback entry, 0x53c100 entry stride, 0x53c108 cleared on each lookup.

// 0x47cd70. Looks up the handler slot for `index` in the table at 0x53c0e8. If
// the slot holds a nonzero handler pointer, calls that handler with the object
// as receiver; otherwise calls the default handler 0x43d490 with the index.
void dispatchHandler(Run &run, uint32_t self, uint32_t index) {
    uint32_t low = run.get(0x53c0f0);
    run.put(0x53c108, 0);
    uint32_t entry;
    if (s32(index) < s32(low) || s32(index) > s32(run.get(0x53c0f4))) {
        uint32_t grown = run.call(0x4db6e0, 0x53c0e8, {index, 0});
        if (grown) {
            low = run.get(0x53c0f0);
            entry = (index - low) * run.get(0x53c100) + run.get(0x53c0f8);
        } else {
            uint32_t message = run.get(0x544b4c);
            uint32_t result = run.call(0x4db5f0, 0, {});
            uint32_t allocator = run.get(0x53c0ec);
            run.put(0x544b14, result);
            run.call(0x4db4d0, allocator, {0x53c0e8, message, 0xc});
            entry = run.get(0x53c0fc);
            low = run.get(0x53c0f0);
        }
    } else {
        entry = (index - low) * run.get(0x53c100) + run.get(0x53c0f8);
    }
    if (run.get(entry) == 0) {
        run.call(0x43d490, self, {index});
        return;
    }
    run.put(0x53c108, 0);
    uint32_t slot;
    if (s32(index) < s32(low) || s32(index) > s32(run.get(0x53c0f4))) {
        uint32_t grown = run.call(0x4db6e0, 0x53c0e8, {index, 0});
        if (grown) {
            low = run.get(0x53c0f0);
            slot = (index - low) * run.get(0x53c100) + run.get(0x53c0f8);
        } else {
            uint32_t message = run.get(0x544b4c);
            uint32_t result = run.call(0x4db5f0, 0, {});
            uint32_t allocator = run.get(0x53c0ec);
            run.put(0x544b14, result);
            run.call(0x4db4d0, allocator, {0x53c0e8, message, 0xc});
            slot = run.get(0x53c0fc);
        }
    } else {
        slot = (index - low) * run.get(0x53c100) + run.get(0x53c0f8);
    }
    run.call(run.get(slot), self, {});
}

// 0x47cd70. thiscall, 1 stack argument, returns void.
uint32_t function_47cd70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    dispatchHandler(run, receiver, arguments[0]);
    return 0;
}

// 0x47d4b0. Sets up the throwing state: common prologue with argument +0x35c,
// then the throw parameters at +0x404..+0x414.
uint32_t function_47d4b0(Run &run, uint32_t receiver, const uint32_t *) {
    ratSetterCommon(run, receiver, 0x35c);
    run.put(receiver + 0x404, 0);
    run.put(receiver + 0x410, 1);
    run.put(receiver + 0x414, 0xfffffff4);
    run.put(receiver + 0x408, 0xfa);
    run.put(receiver + 0x40c, 0x5dc);
    return 0;
}

// 0x47d540. Same prologue with argument +0x360; throw parameters differ.
uint32_t function_47d540(Run &run, uint32_t receiver, const uint32_t *) {
    ratSetterCommon(run, receiver, 0x360);
    run.put(receiver + 0x408, 0);
    run.put(receiver + 0x40c, 0);
    run.put(receiver + 0x410, 0xfffffff3);
    run.put(receiver + 0x414, 0xffffffea);
    run.put(receiver + 0x404, 0xfffffe0c);
    return 0;
}

// 0x47d5d0. Same prologue with argument +0x360; throw parameters differ.
uint32_t function_47d5d0(Run &run, uint32_t receiver, const uint32_t *) {
    ratSetterCommon(run, receiver, 0x360);
    run.put(receiver + 0x408, 0);
    run.put(receiver + 0x40c, 0);
    run.put(receiver + 0x410, 0xd);
    run.put(receiver + 0x414, 0xffffffea);
    run.put(receiver + 0x404, 0x1f4);
    return 0;
}

// 0x47d780. Compares a value reached through global 0x537e88 (+0x6c, +0x14,
// +0xe8) with the cached copy at +0x19c; on change stores it, sets flag 0x10000
// in the window object when its kind (+0xd0) is 0x20, and calls virtual +0x5c(0).
uint32_t function_47d780(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t root = run.get(0x537e88);
    uint32_t level1 = run.get(root + 0x6c);
    uint32_t level2 = run.get(level1 + 0x14);
    uint32_t current = run.get(level2 + 0xe8);
    uint32_t cached = run.get(receiver + 0x19c);
    if (current == cached)
        return 0;
    uint32_t window = run.get(receiver + 0xc);
    run.put(receiver + 0x19c, current);
    uint32_t windowObject = run.get(window + 0x74);
    if (run.get(windowObject + 0xd0) == 0x20) {
        uint32_t flags = run.get(windowObject + 0x8);
        run.put(windowObject + 0x8, flags | 0x10000);
    }
    run.vcall(receiver, 0x5c, {0});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x47cd70:
        return function_47cd70(run, receiver, arguments);
    case 0x47d4b0:
        return function_47d4b0(run, receiver, arguments);
    case 0x47d540:
        return function_47d540(run, receiver, arguments);
    case 0x47d5d0:
        return function_47d5d0(run, receiver, arguments);
    case 0x47d780:
        return function_47d780(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_closure_rat_01_entry, owned, body)
