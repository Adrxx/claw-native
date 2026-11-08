// Level 1 closure projectile, elemental bullet, rat bomb and flare helpers
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
    case 0x410a80:
        return 1;
    case 0x414010:
        return 0;
    case 0x411030:
        return 1;
    case 0x4114e0:
        return 1;
    case 0x411990:
        return 1;
    case 0x411cd0:
        return 0;
    case 0x4030e0:
        return 1;
    case 0x458280:
        return 1;
    default:
        return -1;
    }
}

// Dispatch table at `table`: +0x04 grow context, +0x08 low index, +0x0c high
// index, +0x10 entry array, +0x14 default entry, +0x18 entry stride, +0x20 flag.
// Returns the entry address, mirroring the original's register flow. `low`
// carries the ECX value the original keeps live between the two lookups.
uint32_t lookupEntry(Run &run, uint32_t table, uint32_t index, uint32_t &low) {
    bool inRange = true;
    if (s32(index) < s32(low))
        inRange = false;
    else if (s32(index) > s32(run.get(table + 0x0c)))
        inRange = false;
    if (inRange) {
        uint32_t offset = index - low;
        uint32_t data = run.get(table + 0x10);
        offset = offset * run.get(table + 0x18);
        return offset + data;
    }
    uint32_t grown = run.call(0x4db6e0, table, {index, 0});
    if (grown) {
        low = run.get(table + 0x08);
        uint32_t offset = index - low;
        uint32_t data = run.get(table + 0x10);
        offset = offset * run.get(table + 0x18);
        return offset + data;
    }
    // The original faults here: 0x4db6e0 clobbers EBP with the failed
    // realloc result 0 and 0x4dc680 then reads [ebp+4]. No case reaches this.
    return 0;
}

// Shared body of the five dispatch stubs. Looks the id up in the table, and if
// the entry's first word is nonzero calls the pointer stored there with the
// receiver in ECX; otherwise returns false so the caller runs its fallback.
bool dispatchEntry(Run &run, uint32_t table, uint32_t receiver, uint32_t id) {
    uint32_t low = run.get(table + 0x08);
    run.put(table + 0x20, 0);
    uint32_t entry = lookupEntry(run, table, id, low);
    if (run.get(entry) == 0)
        return false;
    run.put(table + 0x20, 0);
    entry = lookupEntry(run, table, id, low);
    uint32_t target = run.get(entry);
    run.call(target, receiver, {});
    return true;
}

// 0x410a80. Dispatches id through table 0x534ab0, else 0x473f40.
uint32_t function_410a80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t id = arguments[0];
    if (dispatchEntry(run, 0x534ab0, receiver, id))
        return 0;
    run.call(0x473f40, receiver, {id});
    return 0;
}

// 0x414010. Sets bit 0x10000 in the flags word (+8) of the object at +0x154.
uint32_t function_414010(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t linked = run.get(receiver + 0x154);
    if (linked == 0)
        return 0;
    uint32_t flags = run.get(linked + 0x08);
    run.put(linked + 0x08, flags | 0x10000);
    return 0;
}

// 0x411030. Dispatches id through table 0x534ba0, else 0x473f40.
uint32_t function_411030(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t id = arguments[0];
    if (dispatchEntry(run, 0x534ba0, receiver, id))
        return 0;
    run.call(0x473f40, receiver, {id});
    return 0;
}

// 0x4114e0. Dispatches id through table 0x534a38, else 0x473f40.
uint32_t function_4114e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t id = arguments[0];
    if (dispatchEntry(run, 0x534a38, receiver, id))
        return 0;
    run.call(0x473f40, receiver, {id});
    return 0;
}

// 0x411990. Dispatches id through table 0x534b00, else 0x473f40.
uint32_t function_411990(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t id = arguments[0];
    if (dispatchEntry(run, 0x534b00, receiver, id))
        return 0;
    run.call(0x473f40, receiver, {id});
    return 0;
}

// 0x411cd0. Sets bit 0x10000 in the flags word (+8) of the object at +0x150.
uint32_t function_411cd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t linked = run.get(receiver + 0x150);
    if (linked == 0)
        return 0;
    uint32_t flags = run.get(linked + 0x08);
    run.put(linked + 0x08, flags | 0x10000);
    return 0;
}

// 0x4030e0. Stores the vtable 0x50b014; frees the object when bit 0 of the
// byte argument is set. Returns the receiver.
uint32_t function_4030e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t mode = arguments[0] & 0xff;
    run.put(receiver, 0x50b014);
    if ((mode & 1) != 0)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x458280. Dispatches id through table 0x537ac0, else 0x4a36f0(receiver).
uint32_t function_458280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t id = arguments[0];
    if (dispatchEntry(run, 0x537ac0, receiver, id))
        return 0;
    run.call(0x4a36f0, 0, {receiver});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x410a80:
        return function_410a80(run, receiver, arguments);
    case 0x414010:
        return function_414010(run, receiver, arguments);
    case 0x411030:
        return function_411030(run, receiver, arguments);
    case 0x4114e0:
        return function_4114e0(run, receiver, arguments);
    case 0x411990:
        return function_411990(run, receiver, arguments);
    case 0x411cd0:
        return function_411cd0(run, receiver, arguments);
    case 0x4030e0:
        return function_4030e0(run, receiver, arguments);
    case 0x458280:
        return function_458280(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_closure_projectiles_01_entry, owned, body)
