// Level 1 Claw rope states
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
    case 0x403ab0:
        return 0;
    case 0x403ac0:
        return 0;
    case 0x418080:
        return 3;
    case 0x4181c0:
        return 3;
    default:
        return -1;
    }
}

// 0x403ab0. Sum of the owner's field +0x4c (read through +0x0c) and this +0x140.
uint32_t function_403ab0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t owner = run.get(receiver + 0xc);
    uint32_t offset = run.get(receiver + 0x140);
    uint32_t base = run.get(owner + 0x4c);
    return base + offset;
}

// 0x403ac0. Sum of the owner's field +0x50 (read through +0x0c) and this +0x144.
uint32_t function_403ac0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t owner = run.get(receiver + 0xc);
    uint32_t offset = run.get(receiver + 0x144);
    uint32_t base = run.get(owner + 0x50);
    return base + offset;
}

// Mirrors one rectangle edge pair when its first value is not the sentinel.
void mirrorPair(Run &run, uint32_t object, uint32_t first, uint32_t second) {
    uint32_t value = run.get(object + first);
    if (value == 0x80000000u)
        return;
    uint32_t other = run.get(object + second);
    run.put(object + first, 0u - other);
    run.put(object + second, 0u - value);
}

// 0x418080. cdecl(object, unused, state). When *state is set, flips the object
// (+0x40 flags bit 1) and negates and swaps three pairs at +0x118/+0x120,
// +0x128/+0x130 and +0x138/+0x140, then clears *state and sets state+0x114.
void function_418080(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t state = arguments[2];
    if (run.get(state) == 0)
        return;
    uint32_t flags = run.get(object + 0x40);
    run.put(object + 0x40, flags | 2);
    mirrorPair(run, object, 0x118, 0x120);
    mirrorPair(run, object, 0x128, 0x130);
    mirrorPair(run, object, 0x138, 0x140);
    run.put(state, 0);
    run.put(state + 0x114, 0x5dc);
}

// 0x4181c0. cdecl(object, unused, state). Positions the rope object relative
// to the Claw object reached through state+0x134, and on the flag in
// global 0x537204 resets the state for the jump animation.
void function_4181c0(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t second = arguments[1];
    uint32_t state = arguments[2];
    run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
    uint32_t claw = 0;
    if (run.get(state) != 0) {
        uint32_t a = run.get(state + 0x134);
        uint32_t b = run.get(a + 0x6c);
        claw = run.get(b + 0x18);
        uint32_t x = function_403ab0(run, claw, nullptr);
        run.put(object + 0x4c, x + 8);
        uint32_t c = run.get(state + 0x134);
        uint32_t d = run.get(c + 0x6c);
        claw = run.get(d + 0x18);
    } else {
        uint32_t a = run.get(state + 0x134);
        uint32_t b = run.get(a + 0x6c);
        claw = run.get(b + 0x18);
        uint32_t x = function_403ab0(run, claw, nullptr);
        run.put(object + 0x4c, x - 8);
        uint32_t c = run.get(state + 0x134);
        uint32_t d = run.get(c + 0x6c);
        claw = run.get(d + 0x18);
    }
    uint32_t y = function_403ac0(run, claw, nullptr);
    run.put(object + 0x50, y + 0x14);
    uint32_t global = run.get(0x537204);
    if ((run.get8(global + 0x4) & 1) == 0)
        return;
    run.put(state + 0x11c, 0x1f4);
    global = run.get(0x537204);
    uint32_t bits = run.get(global + 0xc) & 0xfdffffffu;
    run.put(global + 0xc, bits);
    global = run.get(0x537204);
    bits = run.get(global + 0xc) & 0xfeffffffu;
    run.put(global + 0xc, bits);
    uint32_t holder = run.get(state + 0x12c);
    if (holder != 0) {
        uint32_t inner = run.get(holder + 0x6c);
        uint32_t target = run.get(inner + 0x18);
        run.call(0x421010, target, {0x4207a0, 1});
        run.call(0x420fc0, target + 0x2f4, {0});
        run.put(state + 0x12c, 0);
    }
    uint32_t pending = run.get(state + 0x4);
    run.put(state + 0x3c, 0);
    run.put(state + 0x20, 1);
    if (pending != 0) {
        uint32_t value = run.get(state + 0x124);
        run.put(state + 0x4, 0);
        run.call(0x420a10, object, {value, 0});
        uint32_t flags = run.get(object + 0x8);
        run.put(object + 0x8, flags | 0x80);
    }
    run.put(second + 0x1c, 4);
    run.call(0x4c79e0, object, {0x5246a8, 0});
    uint32_t flags = run.get(object + 0x8) & 0xffffffefu;
    run.put(object + 0xcc, 3);
    run.put(object + 0x148, 0);
    run.put(object + 0x14c, 0);
    run.put(object + 0x8, flags);
    run.call(0x417050, 0, {object, state});
    run.call(0x4170b0, 0, {object, state});
    uint32_t mode = run.get(0x534eac);
    if (mode == 0x26bc) {
        run.put(0x534de8, 0);
        run.put(0x534dec, 0xc07f4000);
    } else {
        uint32_t flag = run.get(state + 0x114);
        run.put(0x534de8, 0);
        run.put(0x534dec, 0xc07f4000);
        if (flag != 0)
            run.put(0x534dec, 0xc07a9000);
    }
    run.put(state + 0x118, 0xfa);
    run.put(state + 0x5c, 0);
    uint32_t px = run.get(object + 0x50);
    run.put(state + 0x60, px);
    uint32_t py = run.get(object + 0x50) - 0x2d;
    run.put(state + 0x10c, 0);
    run.put(state + 0x64, py);
    run.put(0x534dd0, 0);
    run.put(0x534dd4, 0x40a19400);
    run.putd(0x534df8, double(run.gets(object + 0x4c)));
    uint32_t high = run.get(0x534dfc);
    uint32_t low = run.get(0x534df8);
    run.putd(0x534e00, double(run.gets(object + 0x50)));
    double third = double(run.gets(state + 0x64));
    uint64_t thirdBits;
    std::memcpy(&thirdBits, &third, 8);
    run.call(0x420dd0, 0x534db8, {low, high, uint32_t(thirdBits), uint32_t(thirdBits >> 32), 0, 0});
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x403ab0:
        return function_403ab0(run, receiver, arguments);
    case 0x403ac0:
        return function_403ac0(run, receiver, arguments);
    case 0x418080:
        function_418080(run, receiver, arguments);
        return 0;
    case 0x4181c0:
        function_4181c0(run, receiver, arguments);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_claw_rope_01_entry, owned, body)
