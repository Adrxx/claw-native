// In-game cheat command helpers: toggle message, power-up grant, layer toggles, fall speed
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
    case 0x42af90:
        return 2;
    case 0x41fc00:
        return 2;
    case 0x42a750:
        return 0;
    case 0x42a7b0:
        return 0;
    case 0x42a7f0:
        return 0;
    case 0x440de0:
        return 0;
    case 0x440e00:
        return 0;
    default:
        return -1;
    }
}

// 0x42af90. thiscall(this, name, state). Formats "%s is ON/OFF" into the
// buffer at 0x5370d8 and passes it to the status message sender 0x42af70.
uint32_t function_42af90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t format = 0x525eb8;
    if (arguments[1] == 0)
        format = 0x525eac;
    run.call(0x4a3920, 0, {0x5370d8, format, arguments[0]});
    return run.call(0x42af70, receiver, {0x5370d8});
}

// 0x41fc00. cdecl(a, b). Forwards to 0x41f990 with the game object at
// 0x537e88, its field +0x6c, and that field's +0x14.
uint32_t function_41fc00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t game = run.get(0x537e88);
    if (game == 0)
        return 0;
    uint32_t inner = run.get(game + 0x6c);
    uint32_t innerField = run.get(inner + 0x14);
    return run.call(0x41f990, 0, {game, inner, innerField, arguments[0], arguments[1]});
}

// 0x42a750. fastcall(this). If the virtual check at slot +0xc passes, flips
// bit 1 of the flags (+0x8) of one entry of the layer list, unless bit 0 is set.
// Layer list: +0x38 array pointer, +0x3c count; this+0x30 -> +0x24 -> list owner.
uint32_t function_42a750(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t ok = run.vcall(receiver, 0xc, {});
    if (ok == 0)
        return 0;
    if (run.get(receiver + 0x30) == 0)
        return 0;
    uint32_t owner = run.get(run.get(receiver + 0x30) + 0x24);
    if (owner == 0)
        return 0;
    uint32_t count = run.get(owner + 0x3c);
    uint32_t index = count;
    if (index == 4)
        index = 3;
    index = index - 1;
    uint32_t entry = 0;
    if (s32(index) >= 0 && s32(index) < s32(count))
        entry = run.get(run.get(owner + 0x38) + index * 4);
    if (entry == 0)
        return 0;
    uint32_t flags = run.get(entry + 0x8);
    if ((flags & 1) != 0)
        return 0;
    run.put(entry + 0x8, flags ^ 2);
    return 1;
}

// 0x42a7b0. fastcall(this). Flips bit 1 of the flags (+0x8) of the object at
// owner+0x5c.
uint32_t function_42a7b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t ok = run.vcall(receiver, 0xc, {});
    if (ok == 0)
        return 0;
    if (run.get(receiver + 0x30) == 0)
        return 0;
    uint32_t owner = run.get(run.get(receiver + 0x30) + 0x24);
    if (owner == 0)
        return 0;
    uint32_t entry = run.get(owner + 0x5c);
    if (entry == 0)
        return 0;
    uint32_t flags = run.get(entry + 0x8);
    run.put(entry + 0x8, flags ^ 2);
    return 1;
}

// 0x42a7f0. fastcall(this). Flips bit 1 of the flags (+0x8) of the first
// entry of the layer list, unless bit 0 is set.
uint32_t function_42a7f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t ok = run.vcall(receiver, 0xc, {});
    if (ok == 0)
        return 0;
    if (run.get(receiver + 0x30) == 0)
        return 0;
    uint32_t owner = run.get(run.get(receiver + 0x30) + 0x24);
    if (owner == 0)
        return 0;
    uint32_t entry = 0;
    if (s32(run.get(owner + 0x3c)) > 0)
        entry = run.get(run.get(owner + 0x38));
    if (entry == 0)
        return 0;
    uint32_t flags = run.get(entry + 0x8);
    if ((flags & 1) != 0)
        return 0;
    run.put(entry + 0x8, flags ^ 2);
    return 1;
}

// 0x440de0. cdecl(). Sets the three floats at 0x5262b0 to 5.0f.
uint32_t function_440de0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.put(0x5262b0, 0x40a00000);
    run.put(0x5262b4, 0x40a00000);
    run.put(0x5262b8, 0x40a00000);
    return 0;
}

// 0x440e00. cdecl(). Sets the three floats at 0x5262b0 to 1.0f.
uint32_t function_440e00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.put(0x5262b0, 0x3f800000);
    run.put(0x5262b4, 0x3f800000);
    run.put(0x5262b8, 0x3f800000);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42af90:
        return function_42af90(run, receiver, arguments);
    case 0x41fc00:
        return function_41fc00(run, receiver, arguments);
    case 0x42a750:
        return function_42a750(run, receiver, arguments);
    case 0x42a7b0:
        return function_42a7b0(run, receiver, arguments);
    case 0x42a7f0:
        return function_42a7f0(run, receiver, arguments);
    case 0x440de0:
        return function_440de0(run, receiver, arguments);
    case 0x440e00:
        return function_440e00(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_cheat_command_toggles_entry, owned, body)
