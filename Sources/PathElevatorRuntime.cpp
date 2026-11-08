// PathElevator object logic
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
    case 0x49ee30:
        return 1;
    default:
        return -1;
    }
}

// 0x49ee30. Object fields: +0x08 flags, +0x0c owner, +0x6c state block
// (+0x18 helper, +0x1c state, +0xbc value), +0xd0, +0x100 and +0x110
// parameters, +0x118..+0x124 bounds, +0x128..+0x134 color words, +0x158 and
// +0x15c cleared, +0x170 key, +0x174 rectangle. Always returns 1.
uint32_t function_49ee30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t block = run.get(object + 0x6c);
    uint32_t state = run.get(block + 0x1c);
    if (state == 0) {
        uint32_t ok = 1;
        uint32_t path = run.call(0x4f63ec, 0, {0x104});
        if (path)
            run.put(path + 0x100, 0);
        uint32_t found = run.call(0x4683a0, path, {run.get(object + 0x100)});
        if (found == 0) {
            if (run.call(0x468540, path, {object}) == 0)
                ok = 0;
        }
        uint32_t helper = 0;
        uint32_t raw = run.call(0x4f63ec, 0, {0x18});
        if (raw) {
            run.put(raw + 4, 0);
            run.put(raw + 8, 0);
            run.put(raw + 12, 0);
            run.put(raw + 0x14, 0);
            run.put(raw, 0x50fee4);
            helper = raw;
        }
        uint32_t second = run.get(object + 0x110);
        uint32_t first = run.get(block + 0xbc);
        run.call(0x468890, helper, {object, path, first, second});
        uint32_t flags = run.get(object + 8);
        uint32_t rect = run.get(object + 0x174);
        run.put(object + 0xd0, 0x80);
        run.put(object + 8, flags | 1);
        if (rect) {
            uint32_t right = run.get(rect + 0x20);
            uint32_t left = run.get(rect + 0x18);
            run.put(object + 0x118, right - left);
            uint32_t bottom = run.get(rect + 0x24);
            run.put(object + 0x11c, bottom - run.get(rect + 0x1c));
            right = run.get(rect + 0x20);
            left = run.get(rect + 0x18);
            run.put(object + 0x120, right + left - 1);
            bottom = run.get(rect + 0x24);
            uint32_t top = run.get(rect + 0x1c);
            run.put(object + 0x124, bottom + top - 1);
        }
        uint32_t table = run.get(0x537960);
        for (uint32_t i = 0; i < 4; ++i)
            run.put(object + 0x128 + i * 4, run.get(table + 0x68 + i * 4));
        uint32_t level = run.get(run.get(0x5371fc) + 0x2c);
        if (run.get(level + 0x14) == 10) {
            uint32_t key = run.get(object + 0x170);
            uint32_t slot = run.automatic(4);
            run.put(slot, 0);
            uint32_t owner = run.get(object + 0xc);
            run.call(0x4f6286, run.get(owner + 0x10) + 0x10, {0x528a4c, slot});
            if (key == run.get(slot)) {
                table = run.get(0x537960);
                for (uint32_t i = 0; i < 4; ++i)
                    run.put(object + 0x128 + i * 4, run.get(table + 0x98 + i * 4));
            }
        }
        run.put(object + 0x134, run.get(object + 0x134) + 0x20);
        run.put(object + 0x158, 0);
        run.put(object + 0x15c, 0);
        run.put(block + 0x18, helper);
        run.put(block + 0x1c, 1);
        if (ok == 0)
            run.put(block + 0x1c, 5);
        return 1;
    }
    if (state == 1) {
        uint32_t helper = run.get(block + 0x18);
        if (helper) {
            run.call(0x4688f0, helper, {run.get(0x537210)});
            return 1;
        }
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49ee30:
        return function_49ee30(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_path_elevator_entry, owned, body)
