// Results state methods and destructors
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
    case 0x40b0b0:
        return 0;
    case 0x40b140:
        return 1;
    case 0x40b1f0:
        return 0;
    case 0x40b300:
        return 2;
    case 0x429790:
        return 1;
    case 0x4297b0:
        return 0;
    default:
        return -1;
    }
}

uint32_t function_4297b0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4297b0(Run &run, uint32_t receiver, const uint32_t *arguments);

// Calls an original function whose callee-entry ESP (return word included) is
// `depth` bytes below the current owned function's entry ESP.
uint32_t callAt(Run &run, uint32_t depth, uint32_t function, uint32_t receiver,
                std::initializer_list<uint32_t> arguments = {}) {
    run.stackPointer = run.frame - depth;
    uint32_t value = run.call(function, receiver, arguments);
    run.stackPointer = 0;
    return value;
}

// Virtual call with the same stack placement as callAt.
uint32_t vcallAt(Run &run, uint32_t depth, uint32_t object, uint32_t slot,
                 std::initializer_list<uint32_t> arguments = {}) {
    uint32_t method = run.get(run.get(object) + slot);
    return callAt(run, depth, method, object, arguments);
}

// Fields of the results state: +0x04 owner, +0x0c parent, +0x154 child
// object, +0x15c value passed to 0x429ed0. Parent +0x28 holds a record whose
// +0x2c is a service object and whose +0x10 is a keyed collection.

// 0x40b0b0. Releases the child object and tears down shared state.
uint32_t function_40b0b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t service = run.get(run.get(run.get(receiver + 0xc) + 0x28) + 0x2c);
    if (service != 0)
        callAt(run, 8, 0x4b4b40, service);
    callAt(run, 8, 0x4ca300, run.get(run.get(receiver + 0xc) + 0x28));
    callAt(run, 12, 0x4f66cc, 0x53499c, {0x534938});
    uint32_t child = run.get(receiver + 0x154);
    if (child != 0) {
        vcallAt(run, 12, child, 0x0, {1});
        run.put(receiver + 0x154, 0);
    }
    callAt(run, 8, 0x48f180, receiver);
    uint32_t value = run.get(receiver + 0x15c);
    callAt(run, 20, 0x429ed0, run.get(receiver + 0x4), {value, 0, 1});
    return 0;
}

// 0x40b140. Drains the collection entry for the current key, then forwards.
uint32_t function_40b140(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (run.get(receiver + 0x154) == 0)
        return 1;
    uint32_t key = run.get(0x53499c);
    if (run.get(key - 8) != 0) {
        // Local slot is the ecx push: entry minus 4.
        uint32_t local = run.automatic(-4);
        run.put(local, 0);
        uint32_t collection = run.get(run.get(receiver + 0xc) + 0x28) + 0x10;
        callAt(run, 24, 0x4f6286, collection, {run.get(0x53499c), local});
        uint32_t entry = run.get(local);
        if (entry != 0 && callAt(run, 16, 0x4b3e70, run.get(entry + 0x10)) != 0) {
            callAt(run, 28, 0x4b3fe0, run.get(entry + 0x10), {0, 1000, 1});
            while (callAt(run, 16, 0x4b3e70, run.get(entry + 0x10)) != 0) {
                uint32_t service = run.get(run.get(run.get(receiver + 0xc) + 0x28) + 0x2c);
                if (service != 0)
                    callAt(run, 16, 0x4b4b80, service);
            }
        }
    }
    uint32_t child = run.get(receiver + 0x154);
    return vcallAt(run, 20, child, 0x28, {arguments[0]});
}

// 0x40b1f0. Starts the child object after checking the service object.
uint32_t function_40b1f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x154) == 0)
        return 1;
    uint32_t checked = run.get(run.get(run.get(run.get(receiver + 0xc) + 0x4) + 0x10) + 0x2c);
    uint32_t object = run.get(checked + 0x8);
    bool needs = true;
    if (object != 0) {
        uint32_t method = run.get(run.get(object) + 0x60);
        needs = callAt(run, 12, method, 0, {object}) != 0;
    }
    if (needs) {
        if (vcallAt(run, 8, receiver, 0x18) == 0) {
            callAt(run, 16, 0x429e10, run.get(receiver + 0x4), {0x8006, 0x2ee2});
            return 0;
        }
    }
    uint32_t service = run.get(run.get(run.get(receiver + 0xc) + 0x28) + 0x2c);
    if (service != 0)
        callAt(run, 8, 0x4b4b80, service);
    vcallAt(run, 8, run.get(receiver + 0x154), 0x14);
    return 1;
}

// 0x40b300. Forwards two arguments to the child object when present.
uint32_t function_40b300(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t child = run.get(receiver + 0x154);
    if (child == 0)
        return 1;
    return vcallAt(run, 12, child, 0x30, {arguments[0], arguments[1]});
}

// 0x429790. Scalar deleting destructor.
uint32_t function_429790(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t entry = run.frame;
    run.frame = entry - 8;
    function_4297b0(run, receiver, arguments);
    run.frame = entry;
    if ((arguments[0] & 1) != 0)
        callAt(run, 12, 0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4297b0. Destructor: sets vtable 0x50c0c4, runs 0x40b0b0, resets vtable
// to 0x50b4ec, then base cleanup 0x48f180. Its frame holds the exception
// registration (three words) plus two saved registers.
uint32_t function_4297b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t entry = run.frame;
    run.put(receiver, 0x50c0c4);
    run.frame = entry - 24;
    function_40b0b0(run, receiver, arguments);
    run.frame = entry;
    run.put(receiver, 0x50b4ec);
    callAt(run, 24, 0x48f180, receiver);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40b0b0:
        return function_40b0b0(run, receiver, arguments);
    case 0x40b140:
        return function_40b140(run, receiver, arguments);
    case 0x40b1f0:
        return function_40b1f0(run, receiver, arguments);
    case 0x40b300:
        return function_40b300(run, receiver, arguments);
    case 0x429790:
        return function_429790(run, receiver, arguments);
    case 0x4297b0:
        return function_4297b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_eol_results_state_entry, owned, body)
