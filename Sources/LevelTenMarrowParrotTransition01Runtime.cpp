// Level 10 Marrow to Parrot transition recovered from the original v1.0 body.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x459830:
        return 0;
    default:
        return -1;
    }
}

// 0x459830. Actor +0x10 is logic, +0x12c sprite, +0x68 position,
// +0x138/+0x140 horizontal bounds, +0x4a4 animation and +0x488 speech.
uint32_t function_00459830(Run &run, uint32_t actor) {
    uint32_t logic = run.get(actor + 0x10);
    run.put(actor + 0x24, run.get(logic + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x528758});
    logic = run.get(actor + 0x10);
    run.put(logic + 0x1c, state);
    uint32_t sprite = run.get(actor + 0x12c);
    if (run.getd(actor + 0x68) > run.getd(0x50e778)) {
        if (run.get8(sprite + 0x40) & 2u) {
            uint32_t left = run.get(actor + 0x138);
            uint32_t right = run.get(actor + 0x140);
            run.put(actor + 0x138, 0u - right);
            run.put(actor + 0x140, 0u - left);
            run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffdu);
            sprite = run.get(actor + 0x12c);
            // Sprite +0x118/+0x120 bounds preserve the original sentinel.
            left = run.get(sprite + 0x118);
            if (left != 0x80000000u) {
                right = run.get(sprite + 0x120);
                run.put(sprite + 0x118, 0u - right);
                run.put(sprite + 0x120, 0u - left);
            }
            run.call(0x406150, sprite);
            run.call(0x406180, sprite);
        }
        run.put(actor + 0x4d0, 0xffffffc6u);
    } else {
        if (!(run.get8(sprite + 0x40) & 2u)) {
            uint32_t left = run.get(actor + 0x138);
            uint32_t right = run.get(actor + 0x140);
            run.put(actor + 0x138, 0u - right);
            run.put(actor + 0x140, 0u - left);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2u);
            sprite = run.get(actor + 0x12c);
            run.call(0x406120, sprite);
            run.call(0x406150, sprite);
            run.call(0x406180, sprite);
        }
        run.put(actor + 0x4d0, 0x3a);
    }
    sprite = run.get(actor + 0x12c);
    uint32_t animation = run.get(actor + 0x4a4);
    run.put(actor + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    run.put(actor + 0x20, 1);
    sprite = run.get(actor + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 4u);
    sprite = run.get(actor + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 0x80u);
    uint32_t speech = run.get(actor + 0x488);
    uint32_t entity = run.get(actor + 0xc);
    run.call(0x48ce40, 0, {entity, speech, 0});
    run.put(actor + 0x1a0, 0);
    run.put(actor + 0x46c, 0x1388);
    run.put(actor + 0x468, run.get(0x537210));
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *) {
    switch (function) {
    case 0x459830:
        return function_00459830(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_ten_marrow_parrot_transition_01_entry, owned, body)
