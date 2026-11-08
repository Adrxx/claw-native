// Level 1 claw hit box, hit handler and powerup lookup
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x417050:
        return 2;
    case 0x436860:
        return 2;
    default:
        return -1;
    }
}

// 0x417050. cdecl, 2 stack arguments, returns void.
// Sets the claw hit box (+0x128 left, +0x12c top, +0x130 right, +0x134 bottom)
// of the object in argument 0, by the flag read through the pointer in argument 1.
uint32_t function_417050(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t flag = run.get(arguments[1]);
    if (flag != 0) {
        run.put(object + 0x128, 0xffffffea);
        run.put(object + 0x12c, 0xffffffd3);
        run.put(object + 0x130, 0xf);
        run.put(object + 0x134, 0x34);
        return 0;
    }
    run.put(object + 0x128, 0xfffffff1);
    run.put(object + 0x12c, 0xffffffd3);
    run.put(object + 0x130, 0x16);
    run.put(object + 0x134, 0x34);
    return 0;
}

// 0x436860. thiscall, 2 stack arguments, returns u32.
// Walks the list headed at this+4 (node +0 next, +8 entry) and returns the
// first entry whose first two words equal the two arguments, else 0.
uint32_t function_436860(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t node = run.get(receiver + 0x4);
    while (node != 0) {
        uint32_t next = run.get(node);
        uint32_t entry = run.get(node + 0x8);
        node = next;
        if (run.get(entry) != arguments[0])
            continue;
        if (run.get(entry + 0x4) == arguments[1])
            return entry;
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x417050:
        return function_417050(run, receiver, arguments);
    case 0x436860:
        return function_436860(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_powerups_02_entry, owned, body)
