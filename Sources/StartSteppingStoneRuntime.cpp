// StartSteppingStone object logic
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
    case 0x49eb30:
        return 1;
    default:
        return -1;
    }
}

// Globals: 0x537960 table with a 16 byte block at +0x88, 0x537e88 game state
// (+0x08 flags, +0x6c -> +0x14 -> +0x80 current selection, +0x80 owner),
// 0x5430c4 timer argument.
// Code labels used as state callbacks: 0x49ead0, 0x49eaf0, 0x49eb10, 0x49ee20.

// Selection id reached through the game state: [[[0x537e88]+0x6c]+0x14]+0x80.
uint32_t currentSelection(Run &run) {
    uint32_t state = run.get(0x537e88);
    uint32_t a = run.get(state + 0x6c);
    uint32_t b = run.get(a + 0x14);
    return run.get(b + 0x80);
}

// 0x49eb30. cdecl, 1 stack argument(s), returns void (EAX is always 1).
// Object fields: +0x08 flags, +0x64 value, +0x6c state block (+0x10 callback,
// +0x1c state, +0x20 timer, +0x64, +0x68, +0xbc), +0xd0, +0x128..+0x134 rect,
// +0x16c, +0x170 linked object, +0x174, +0x188 animator (+0x14, +0x1c).
uint32_t function_49eb30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t self = arguments[0];
    uint32_t block = run.get(self + 0x6c);
    uint32_t state = run.get(block + 0x1c);
    if (state > 0x3ea) {
        uint32_t index = state - 0x3eb;
        if (index > 4)
            return 1;
        uint32_t animator = self + 0x188;
        switch (index) {
        case 0: // 0x3eb
        case 2: { // 0x3ed
            uint32_t timer = run.get(0x5430c4);
            run.call(0x4c82a0, animator, {timer});
            uint32_t saved = run.get(self + 0x16c);
            uint32_t target = run.get(block + 0x64);
            if (saved == target)
                run.put(self + 0xd0, index == 0 ? 0x80 : 1);
            if (run.get(animator + 0x1c) == 0)
                return 1;
            if (run.get(animator + 0x14) != 0)
                return 1;
            if (index == 0) {
                run.call(0x4c79e0, self, {0x52dd14, 0});
                run.put(block + 0x1c, 0x3ef);
                return 1;
            }
            if (run.get(block + 0x10) == 0x49ee20) {
                uint32_t stored = run.get(block + 0x68);
                if (stored == currentSelection(run))
                    return 1;
                uint32_t x = run.get(self + 0xe8);
                uint32_t y = run.get(self + 0xec);
                run.put(self + 0x4c, x);
                run.put(self + 0x50, y);
                uint32_t selection = currentSelection(run);
                run.put(block + 0x1c, 0);
                run.put(block + 0x68, selection);
                return 1;
            }
            run.put(block + 0x1c, 0x3ee);
            return 1;
        }
        case 1: // 0x3ec
            run.put(self + 0xd0, 1);
            run.call(0x4c79e0, self, {0x52dd14, 0});
            run.put(block + 0x1c, 0x3eb);
            return 1;
        case 3: // 0x3ee
            run.put(block + 0x20, 0x3e8);
            run.put(block + 0x1c, 0x3ec);
            return 1;
        default: { // 0x3ef
            uint32_t game = run.get(0x537e88);
            if ((run.get8(game + 8) & 0x10) == 0)
                return 1;
            if (run.get(game + 0x80) != self)
                return 1;
            run.put(block + 0x20, 0x7d);
            run.put(block + 0x1c, 0x3ea);
            run.call(0x4c79e0, self, {0x52dd04, 0});
            return 1;
        }
        }
    }
    if (state == 0x3ea) {
        run.put(block + 0x1c, 0x3ed);
        return 1;
    }
    if (state != 0)
        return 1;
    uint32_t linked = run.get(self + 0x170);
    run.put(self + 0x158, 0);
    run.put(self + 0x15c, 0);
    if (linked != 0) {
        uint32_t value = run.get(linked + 0x64);
        run.put(self + 0x16c, value);
        uint32_t result = run.call(0x40f680, linked, {value});
        run.put(self + 0x174, result);
    }
    uint32_t flags = run.get(self + 8);
    run.put(self + 0xd0, 0x80);
    flags |= 1;
    run.put(self + 8, flags);
    uint32_t table = run.get(0x537960);
    uint32_t source = table + 0x88;
    uint32_t dest = self + 0x128;
    run.put(dest, run.get(source));
    run.put(dest + 4, run.get(source + 4));
    run.put(dest + 8, run.get(source + 8));
    run.put(dest + 12, run.get(source + 12));
    uint32_t bottom = run.get(self + 0x134);
    uint32_t count = run.get(self + 0x64);
    run.put(self + 0x134, bottom + 0x20);
    if (count == 0) {
        run.put(self + 0x64, 2000);
        run.put(self + 8, flags | 0x20000);
    }
    uint32_t callback = run.get(block + 0x10);
    if (callback == 0x49ead0)
        run.put(block + 0xbc, 0x2ee);
    if (callback == 0x49eaf0)
        run.put(block + 0xbc, 0x5dc);
    if (callback == 0x49eb10)
        run.put(block + 0xbc, 0x8ca);
    uint32_t selection = currentSelection(run);
    run.put(block + 0x1c, 0x3ef);
    run.put(block + 0x68, selection);
    linked = run.get(self + 0x170);
    if (linked == 0)
        return 1;
    uint32_t sum = run.get(linked + 0x68) + run.get(linked + 0x64);
    uint32_t sign = uint32_t(s32(sum) >> 31);
    uint32_t half = uint32_t(s32(sum - sign) >> 1);
    run.put(block + 0x64, half);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49eb30:
        return function_49eb30(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_start_stepping_stone_entry, owned, body)
