// Original application registry configuration string write, value delete and close
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
    case 0x4b5df0:
        return 2;
    case 0x4b5f80:
        return 1;
    case 0x4b5d70:
        return 0;
    default:
        return -1;
    }
}

// Configuration object fields: +0x00 open flag, +0x08 .. +0x14 and +0x18 registry key handles.
// 0x4b5df0. Writes a REG_SZ value (type 1) of the NUL-terminated string to the
// key at +0x18. Returns 1 when the registry status is zero, else 0.
uint32_t function_4b5df0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t name = arguments[0];
    uint32_t text = arguments[1];
    if (run.get(receiver + 0x00) == 0)
        return 0;
    if (name == 0)
        return 0;
    if (text == 0)
        return 0;
    uint32_t count = 0;
    uint32_t cursor = text;
    uint8_t byte;
    do {
        byte = run.get8(cursor);
        cursor = cursor + 1;
        count = count + 1;
    } while (byte != 0);
    uint32_t status = run.icall(0x546824, {run.get(receiver + 0x18), name, 0, 1, text, count});
    return status == 0 ? 1 : 0;
}

// 0x4b5f80. Deletes the named value from the key at +0x18. Returns 1 when the
// registry status is zero, else 0.
uint32_t function_4b5f80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t name = arguments[0];
    if (run.get(receiver + 0x00) == 0)
        return 0;
    if (name == 0)
        return 0;
    uint32_t status = run.icall(0x546820, {run.get(receiver + 0x18), name});
    return status == 0 ? 1 : 0;
}

// 0x4b5d70. When open, clears the flag and closes the handles at +0x08, +0x0c,
// +0x10, +0x14 (only when different from +0x18) and +0x18.
uint32_t function_4b5d70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x00) == 0)
        return 0;
    uint32_t first = run.get(receiver + 0x08);
    run.put(receiver + 0x00, 0);
    run.icall(0x546830, {first});
    run.icall(0x546830, {run.get(receiver + 0x0c)});
    run.icall(0x546830, {run.get(receiver + 0x10)});
    uint32_t fifth = run.get(receiver + 0x14);
    uint32_t sixth = run.get(receiver + 0x18);
    if (fifth != sixth)
        run.icall(0x546830, {fifth});
    run.icall(0x546830, {run.get(receiver + 0x18)});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b5df0:
        return function_4b5df0(run, receiver, arguments);
    case 0x4b5f80:
        return function_4b5f80(run, receiver, arguments);
    case 0x4b5d70:
        return function_4b5d70(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_application_configuration_writes_entry, owned, body)
