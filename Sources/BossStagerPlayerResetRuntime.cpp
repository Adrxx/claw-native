// BossStager player reset
//
// Translation of the pinned original game routine.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x420170:
        return 0;
    default:
        return -1;
    }
}

// 0x420170. cdecl, zero arguments, semantic void.
uint32_t function_420170(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t player = run.get(0x537e88);
    if (!player)
        return 0;
    uint32_t primary = run.get(player + 0x6c); // Primary state object.
    if (run.get(primary + 0x1c) == 0x1391)
        return 0;
    uint32_t input = run.get(0x537204);
    uint32_t data = run.get(primary + 0x14); // Player private data.
    run.put(input + 0xc, run.get(input + 0xc) & 0xfdffffff);
    input = run.get(0x537204);
    run.put(input + 0xc, run.get(input + 0xc) & 0xfeffffff);
    uint32_t carried = run.get(data + 0x12c); // Carried actor.
    if (carried) {
        uint32_t enemy = run.get(run.get(carried + 0x6c) + 0x18);
        if (run.gets(enemy + 0x20) >= 1)
            run.put(enemy + 0x14, 0x4207a0);
        uint32_t capacity = run.get(enemy + 0x2fc); // Bit-array capacity.
        if (!capacity) {
            run.stackPointer = run.frame - 0x18;
            run.call(0x4dbd20, enemy + 0x2f4, {0});
        } else {
            uint32_t bits = enemy + 0x300;
            if (capacity > 0x20)
                bits = run.get(bits);
            run.put(bits, run.get(bits) | 1);
        }
        run.put(data + 0x12c, 0);
    }
    uint32_t restore = run.get(data + 0x4); // Restore saved animation.
    run.put(data + 0x3c, 0);
    run.put(data + 0x20, 1);
    if (restore) {
        uint32_t animation = run.get(data + 0x124);
        run.put(data + 0x4, 0);
        run.stackPointer = run.frame - 0x18;
        run.call(0x4c8220, player + 0x188, {animation});
        run.put(player + 0x8, run.get(player + 0x8) | 0x80);
    }
    // Four saved registers, outgoing operands, then the CALL return word.
    run.stackPointer = run.frame - 0x20;
    run.call(0x41c4e0, 0, {player, primary, data});
    run.put(primary + 0x1c, 0x18);
    run.stackPointer = run.frame - 0x1c;
    run.call(0x4c79e0, player, {0x5246d0, 1});
    uint32_t flags = run.get(player + 0x8);
    run.put(player + 0xcc, 1);
    run.put(player + 0x148, 0);
    run.put(player + 0x14c, 0);
    run.put(player + 0x104, 0);
    run.put(player + 0x8, flags | 0x80);
    run.stackPointer = run.frame - 0x24;
    if (run.get(data + 0x0)) {
        run.call(0x4208b0, player, {0xffffffea, 0xffffffd3, 0xf, 0x34});
    } else {
        run.call(0x4208b0, player, {0xfffffff1, 0xffffffd3, 0x16, 0x34});
    }
    run.stackPointer = run.frame - 0x1c;
    run.call(0x4170b0, 0, {player, data});
    run.put(data + 0xfc, 0x28a);
    run.put(data + 0x114, 0x5dc);
    run.put(data + 0x120, 0x3a98);
    run.put(data + 0x118, 0);
    run.put(0x534e60, 0);
    run.put(0x534e64, 0);
    run.put(0x534e68, 0);
    run.put(0x534e6c, 0);
    run.put(0x534e70, 0);
    run.put(0x534e74, 0);
    run.put(player + 0x1b0, 0x3f800000);
    if (!run.get(data + 0x0)) {
        uint32_t visibility = run.get(player + 0x40);
        uint32_t left = run.get(player + 0x118); // Move rectangle left/right.
        run.put(player + 0x40, visibility & 0xfffffffd);
        if (left != 0x80000000) {
            uint32_t right = run.get(player + 0x120);
            run.put(player + 0x118, 0u - right);
            run.put(player + 0x120, 0u - left);
        }
        // The caller discards the two cdecl arguments at 0x42030a.
        run.stackPointer = run.frame - 0x14;
        run.call(0x406150, player);
        run.stackPointer = run.frame - 0x14;
        run.call(0x406180, player);
        run.put(data + 0x0, 1);
        run.put(data + 0x114, 0x5dc);
    }
    run.put(primary + 0x1c, 0x1391);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x420170:
        return function_420170(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_boss_stager_player_reset_entry, owned, body)
