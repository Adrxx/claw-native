// Game state resume helper and in-game menu helper
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
    case 0x46ddc0:
        return 0;
    case 0x46df20:
        return 0;
    default:
        return -1;
    }
}

// 0x46ddc0. thiscall, 0 stack argument(s), returns void.
// Follows this+0x0c -> +0x04 -> +0x10 -> +0x2c and calls 0x4b98b0 on that object with 0.
uint32_t function_46ddc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t a = run.get(receiver + 0x0c);
    uint32_t b = run.get(a + 0x04);
    uint32_t c = run.get(b + 0x10);
    uint32_t target = run.get(c + 0x2c);
    run.call(0x4b98b0, target, {0});
    return 0;
}

// 0x46df20. thiscall, 0 stack argument(s), returns void.
// Fields of the surface (this+0x0c chain): +0x08 DirectDraw interface,
// +0x14 height (unsigned compare), +0x18 width in bytes (signed), +0x1c pitch.
uint32_t function_46df20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t state = run.get(receiver + 0x0c);
    uint32_t first = run.get(state + 0x24);
    uint32_t second = run.get(run.get(state + 0x04) + 0x14);
    uint32_t third = run.get(state + 0x08);
    run.call(0x4cb9b0, first, {second, third});
    uint32_t state2 = run.get(receiver + 0x0c);
    uint32_t surface = run.get(run.get(state2 + 0x04) + 0x14);
    surface = run.get(surface + 0x2c);
    uint32_t pixels = run.call(0x4b9730, surface, {0});
    if (pixels == 0)
        return 0;
    uint32_t row = 0;
    if (run.get(surface + 0x14) != 0) {
        do {
            uint32_t cursor = run.get(surface + 0x1c) * row + pixels;
            uint32_t column = 0;
            uint32_t half = uint32_t(s32(run.get(surface + 0x18)) / 2);
            if (s32(half) > 0) {
                do {
                    uint32_t value = run.get(cursor);
                    if ((row & 1) != 0)
                        value = 0;
                    run.put(cursor, value & 0xffff);
                    cursor += 4;
                    column += 1;
                    half = uint32_t(s32(run.get(surface + 0x18)) / 2);
                } while (s32(column) < s32(half));
            }
            row += 1;
        } while (row < run.get(surface + 0x14));
    }
    uint32_t interface = run.get(surface + 0x08);
    uint32_t method = run.get(run.get(interface) + 0x80);
    run.call(method, 0, {interface, 0});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x46ddc0:
        return function_46ddc0(run, receiver, arguments);
    case 0x46df20:
        return function_46df20(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_game_state_resume_helpers_entry, owned, body)
