// End Life command: player kill 0x41f490
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
    case 0x41f490:
        return 1;
    default:
        return -1;
    }
}

// 0x41f490. cdecl, 1 stack argument(s), returns void.
// Actor fields: +0x10c health (signed), +0x6c logic object pointer.
// Logic object field: +0x14 private state pointer.
uint32_t function_41f490(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    if (actor == 0)
        return 0;
    if (s32(run.get(actor + 0x10c)) <= 0)
        return 0;
    uint32_t logic = run.get(actor + 0x6c);
    run.put(actor + 0x10c, 0);
    uint32_t state = run.get(logic + 0x14);
    run.call(0x417b00, 0, {actor, logic, state, 0});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x41f490:
        return function_41f490(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_player_end_life_entry, owned, body)
