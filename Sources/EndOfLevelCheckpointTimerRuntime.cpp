// End-of-level checkpoint timer entries
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
    case 0x40db30:
        return 1;
    case 0x40db50:
        return 0;
    case 0x42a630:
        return 0;
    case 0x4c9fc0:
        return 1;
    case 0x4c9fe0:
        return 0;
    case 0x4d3eb0:
        return 0;
    default:
        return -1;
    }
}

uint32_t function_4c9fe0(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x40db50. Sets the vtable pointer at +0x00 and the one at +0x28.
void resetVtables40db50(Run &run, uint32_t object) {
    run.put(object + 0x28, 0x50b014);
    run.put(object + 0x00, 0x50b014);
}

// 0x40db30. Scalar deleting destructor: resets, frees when bit 0 of the flag is set.
uint32_t function_40db30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    resetVtables40db50(run, receiver);
    if ((arguments[0] & 1) != 0)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x40db50. thiscall, no stack arguments.
uint32_t function_40db50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    resetVtables40db50(run, receiver);
    return 0;
}

// 0x42a630. +0x2c is an object pointer; true when its virtual method at +0x10
// returns 3, 4 or 6. The method is called again for each comparison.
uint32_t function_42a630(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x2c) == 0)
        return 0;
    uint32_t object = run.get(receiver + 0x2c);
    uint32_t method = run.get(run.get(object) + 0x10);
    uint32_t kind = run.call(method, object);
    if (kind == 3)
        return 1;
    object = run.get(receiver + 0x2c);
    method = run.get(run.get(object) + 0x10);
    kind = run.call(method, object);
    if (kind == 4)
        return 1;
    object = run.get(receiver + 0x2c);
    method = run.get(run.get(object) + 0x10);
    kind = run.call(method, object);
    return kind == 6 ? 1 : 0;
}

// 0x4c9fc0. Scalar deleting destructor of the timer object.
uint32_t function_4c9fc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4c9fe0(run, receiver, nullptr);
    if ((arguments[0] & 1) != 0)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// Deletes the object at pointer field `field` through its virtual method at +4
// (argument 1) and clears the field, when the field is not null.
void deleteMember(Run &run, uint32_t object, uint32_t field) {
    uint32_t member = run.get(object + field);
    if (member == 0)
        return;
    uint32_t method = run.get(run.get(member) + 0x4);
    run.call(method, member, {1});
    run.put(object + field, 0);
}

// 0x4d3eb0. Walks the list whose head node is at +0x1b8 (node: +0 next, +8 item),
// deletes every item through its virtual method at +4, then RemoveAll (0x4f5172)
// on the list at +0x1b4.
void function_4d3eb0_body(Run &run, uint32_t object) {
    uint32_t node = run.get(object + 0x1b8);
    while (node != 0) {
        uint32_t current = node;
        node = run.get(current);
        uint32_t item = run.get(current + 0x8);
        if (item != 0) {
            uint32_t method = run.get(run.get(item) + 0x4);
            run.call(method, item, {1});
        }
    }
    run.call(0x4f5172, object + 0x1b4);
}

uint32_t function_4d3eb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    function_4d3eb0_body(run, receiver);
    return 0;
}

// 0x4c9fe0. Destructor chain of the timer object: three stages, each of which
// resets the same fields, then the final base destructor 0x45fe20.
uint32_t function_4c9fe0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    const uint32_t self = receiver;
    run.put(self + 0x00, 0x513830);
    function_4d3eb0_body(run, self);
    run.put(self + 0x168, 0xffffffff);
    run.put(self + 0x16c, 0xffffffff);
    run.put(self + 0x174, 0);
    run.put(self + 0x170, 0);
    deleteMember(run, self, 0x6c);
    deleteMember(run, self, 0x70);
    deleteMember(run, self, 0x78);
    run.put(self + 0xc4, 0xffffffff);
    run.put(self + 0xac, 0x80000000);
    run.put(self + 0x4c, 0x80000000);
    run.put(self + 0x20, 0x80000000);
    run.put(self + 0x38, 0xffffffff);
    run.call(0x4f565f, self + 0x1b4);
    run.put(self + 0x00, 0x5137f0);
    run.put(self + 0x168, 0xffffffff);
    run.put(self + 0x16c, 0xffffffff);
    run.put(self + 0x174, 0);
    run.put(self + 0x170, 0);
    deleteMember(run, self, 0x6c);
    deleteMember(run, self, 0x70);
    deleteMember(run, self, 0x78);
    run.put(self + 0xac, 0x80000000);
    run.put(self + 0xc4, 0xffffffff);
    run.put(self + 0x4c, 0x80000000);
    run.put(self + 0x38, 0xffffffff);
    run.put(self + 0x20, 0x80000000);
    run.put(self + 0x188, 0x513870);
    run.call(0x4c8210, self + 0x188);
    run.put(self + 0x188, 0x50becc);
    run.put(self + 0x00, 0x513770);
    deleteMember(run, self, 0x6c);
    deleteMember(run, self, 0x70);
    deleteMember(run, self, 0x78);
    run.put(self + 0xac, 0x80000000);
    run.put(self + 0xc4, 0xffffffff);
    run.put(self + 0x20, 0x80000000);
    run.put(self + 0x38, 0xffffffff);
    run.put(self + 0x00, 0x513888);
    run.put(self + 0x4c, 0x80000000);
    run.put(self + 0x20, 0x80000000);
    run.put(self + 0x38, 0xffffffff);
    run.call(0x45fe20, self);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40db30:
        return function_40db30(run, receiver, arguments);
    case 0x40db50:
        return function_40db50(run, receiver, arguments);
    case 0x42a630:
        return function_42a630(run, receiver, arguments);
    case 0x4c9fc0:
        return function_4c9fc0(run, receiver, arguments);
    case 0x4c9fe0:
        return function_4c9fe0(run, receiver, arguments);
    case 0x4d3eb0:
        return function_4d3eb0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_end_of_level_checkpoint_timer_entry, owned, body)
