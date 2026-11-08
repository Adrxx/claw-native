// Level 13 Red Tail construction, cleanup, dispatch and home state.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x47f800:
    case 0x47ff90:
    case 0x4805a0:
        return 1;
    case 0x4805c0:
    case 0x480630:
    case 0x480640:
    case 0x4806c0:
        return 0;
    default:
        return -1;
    }
}

// 0x47f800. The global table is indexed by a signed state id.
uint32_t dispatchState(Run &run, uint32_t receiver, uint32_t state) {
    uint32_t lower = run.get(0x53c180);
    run.put(0x53c198, 0);
    uint32_t slot;
    if ((s32(state) < s32(lower) || s32(state) > s32(run.get(0x53c184))) &&
        !run.call(0x4db6e0, 0x53c178, {state, 0})) {
        uint32_t message = run.get(0x544b4c);
        uint32_t location = run.call(0x4db5f0, 0);
        uint32_t context = run.get(0x53c17c);
        run.put(0x544b14, location);
        run.call(0x4db4d0, context, {0x53c178, message, 0xc});
        slot = run.get(0x53c18c);
        lower = run.get(0x53c180);
    } else {
        lower = run.get(0x53c180);
        slot = (state - lower) * run.get(0x53c190) + run.get(0x53c188);
    }
    if (!run.get(slot)) {
        run.call(0x40e280, receiver, {state});
        return 0;
    }
    run.put(0x53c198, 0);
    if ((s32(state) < s32(lower) || s32(state) > s32(run.get(0x53c184))) &&
        !run.call(0x4db6e0, 0x53c178, {state, 0})) {
        uint32_t message = run.get(0x544b4c);
        uint32_t location = run.call(0x4db5f0, 0);
        uint32_t context = run.get(0x53c17c);
        run.put(0x544b14, location);
        run.call(0x4db4d0, context, {0x53c178, message, 0xc});
        slot = run.get(0x53c18c);
    } else {
        lower = run.get(0x53c180);
        slot = (state - lower) * run.get(0x53c190) + run.get(0x53c188);
    }
    run.call(run.get(slot), receiver);
    return 0;
}

uint32_t animationLookup(Run &run, uint32_t animations, uint32_t name) {
    uint32_t animation = run.call(0x4062e0, animations, {name});
    if (!animation) {
        animation = run.call(0x4062e0, animations, {0x5234b4});
    }
    return animation;
}

uint32_t soundLookup(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t sounds = run.get(run.get(actor + 0xc) + 0x28);
    return run.call(0x4061b0, sounds, {name});
}

// 0x47ff90. +0x128 is the animation owner, +0x12c its actor.
uint32_t construct(Run &run, uint32_t receiver, uint32_t argument) {
    auto fp = run.x87_entry(0x47ff90);
    fp.popCount = 0;
    fp.pushCount = 0;
    run.call_x87_exact(0x40e0d0, receiver, fp, {argument});
    run.put(receiver + 0x4b0, 0);
    run.put(receiver + 0x4b4, 0);
    run.put(receiver + 0x4b8, 0);
    run.put(receiver + 0x4bc, 0);
    run.put(receiver, 0x50f264);
    run.put(0x53c19c, receiver);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x52b6b4});
    uint32_t animations = receiver + 0x128;
    run.put(receiver + 0x308, animationLookup(run, animations, 0x52b698));
    run.put(receiver + 0x30c, animationLookup(run, animations, 0x52b698));
    run.put(receiver + 0x338, animationLookup(run, animations, 0x52b680));
    run.put(receiver + 0x334, animationLookup(run, animations, 0x52b668));
    run.put(receiver + 0x344, animationLookup(run, animations, 0x52b654));
    run.put(receiver + 0x350, animationLookup(run, animations, 0x52b640));
    run.put(receiver + 0x33c, animationLookup(run, animations, 0x52b62c));
    run.put(receiver + 0x32c, animationLookup(run, animations, 0x52b614));
    run.put(receiver + 0x374, animationLookup(run, animations, 0x52b614));
    run.put(receiver + 0x464, animationLookup(run, animations, 0x52b5fc));
    run.put(receiver + 0x468, animationLookup(run, animations, 0x52b5e4));
    run.put(receiver + 0x46c, animationLookup(run, animations, 0x52b5cc));
    run.put(receiver + 0x470, animationLookup(run, animations, 0x52b5b4));
    run.put(receiver + 0x474, animationLookup(run, animations, 0x52b59c));
    run.put(receiver + 0x478, animationLookup(run, animations, 0x52b584));
    run.put(receiver + 0x47c, animationLookup(run, animations, 0x52b570));
    // +0x2f4 is the dynamic flag set; +8 is its bit capacity.
    uint32_t flags = receiver + 0x2f4;
    uint32_t capacity = run.get(flags + 0x8);
    if (capacity <= 8) {
        run.call(0x4dbd20, flags, {8});
    } else {
        uint32_t data = capacity > 0x20 ? run.get(flags + 0xc) : flags + 0xc;
        run.put(data, run.get(data) | 0x100);
    }
    capacity = run.get(flags + 0x8);
    if (capacity > 9) {
        uint32_t data = capacity > 0x20 ? run.get(flags + 0xc) : flags + 0xc;
        run.put(data, run.get(data) ^ 0x200);
    }
    run.put(receiver + 0x480, soundLookup(run, receiver, 0x52b558));
    run.put(receiver + 0x414, soundLookup(run, receiver, 0x52b540));
    run.put(receiver + 0x418, soundLookup(run, receiver, 0x52b528));
    run.put(receiver + 0x3a4, soundLookup(run, receiver, 0x52b510));
    run.put(receiver + 0x484, soundLookup(run, receiver, 0x52b4f8));
    run.put(receiver + 0x488, soundLookup(run, receiver, 0x52b4e0));
    run.put(receiver + 0x48c, soundLookup(run, receiver, 0x52b4c8));
    run.put(receiver + 0x490, soundLookup(run, receiver, 0x52b4b0));
    run.put(receiver + 0x4a8, soundLookup(run, receiver, 0x52b498));
    run.put(receiver + 0x494, soundLookup(run, receiver, 0x52b480));
    run.put(receiver + 0x498, soundLookup(run, receiver, 0x52b468));
    run.put(receiver + 0x49c, soundLookup(run, receiver, 0x52b450));
    run.put(receiver + 0x4a0, soundLookup(run, receiver, 0x52b438));
    run.put(receiver + 0x4a4, soundLookup(run, receiver, 0x52b420));
    run.put(receiver + 0x4ac, soundLookup(run, receiver, 0x52b408));
    run.put(receiver + 0x40c, soundLookup(run, receiver, 0x52b3f0));
    run.put(run.get(receiver + 0x12c) + 0xd0, 4);
    run.put(run.get(receiver + 0x12c) + 0xd4, 0x3000062);
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(actor + 0x164, run.get(actor + 0x164) & 0xfffffffe);
    run.call(0x4061e0, run.get(receiver + 0x12c), {receiver + 0x220});
    run.call(0x4061e0, run.get(receiver + 0x12c), {receiver + 0x210});
    run.call(0x406290, run.get(receiver + 0x12c));
    run.call(0x406240, run.get(receiver + 0x12c));
    run.icall(0x546d5c, {receiver + 0x220, 0xffffffe1, 0xffffffcd, 0x26, 0x3e});
    run.icall(0x546d5c, {receiver + 0x4c0, 0xffffffcc, 0xffffffef, 0x33, 0x29});
    run.icall(0x546d5c, {receiver + 0x4d0, 0xffffffc8, 0xffffffe4, 0, 0x16});
    run.icall(0x546d5c, {receiver + 0x250, 0xffffffe1, 0xffffffcd, 0x26, 0x3e});
    run.call(0x4208b0, run.get(receiver + 0x12c), {0xffffffe1, 0xffffffcd, 0x26, 0x3e});
    run.put(receiver + 0x4e0, 0);
    run.put(receiver + 0x404, 0xfa);
    run.put(receiver + 0x400, 0xfa);
    run.put(receiver + 0x28c, 0x7d0);
    run.put(receiver + 0x290, 0x3e8);
    run.put(receiver + 0x294, 0x258);
    run.put(receiver + 0x298, 0x3e8);
    run.put(receiver + 0x29c, 0x12c);
    run.put(receiver + 0x2a0, 0x3e8);
    run.put(receiver + 0x2a4, 0xc8);
    run.put(receiver + 0x2a8, 0x3e8);
    run.put(receiver + 0x2ac, 0x64);
    run.put(receiver + 0x2b0, 0x3e8);
    run.call(0x40abf0, animations);
    run.put(run.get(receiver + 0xc) + 0x10c, 0x64);
    uint32_t root = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(root + 0x10c)});
    double multiplier = static_cast<double>(run.getf(0x5262b4));
    uint64_t multiplierBits;
    std::memcpy(&multiplierBits, &multiplier, sizeof(multiplierBits));
    run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(multiplierBits), uint32_t(multiplierBits >> 32)});
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    uint32_t scaled = run.call_x87_exact(0x4a30e0, 0, fp);
    run.put(root + 0x10c, scaled);
    run.call(0x405060, receiver);
    run.x87_finish(0x47ff90, fp);
    return receiver;
}

// 0x4805c0. Release dynamic flags and the two CString members.
uint32_t destroy(Run &run, uint32_t receiver) {
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}

// 0x4805a0. The low flag bit selects deletion after destruction.
uint32_t deletingDestroy(Run &run, uint32_t receiver, uint32_t flags) {
    destroy(run, receiver);
    if (flags & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x480630. Notify the receiver through virtual slot +0x44.
uint32_t notify(Run &run, uint32_t receiver) {
    run.vcall(receiver, 0x44);
    return 0;
}

// 0x480640. Begin home state, selecting +0x350 animation and reset timers.
uint32_t beginHome(Run &run, uint32_t receiver) {
    run.call(0x44d9f0, receiver);
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {run.get(receiver + 0x350)});
    run.put(receiver + 0x4bc, 0x1f4);
    run.put(receiver + 0x4b8, run.get(0x537210));
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x5c, 0);
    if (!run.get(receiver + 0x4e0)) {
        actor = run.get(receiver + 0x12c);
        run.put(actor + 0x8, run.get(actor + 0x8) & 0xfffffffe);
        actor = run.get(receiver + 0x12c);
        run.put(actor + 0x8, run.get(actor + 0x8) & 0xfffffffb);
    }
    return 0;
}

// 0x4806c0. Update facing and choose the next action after the home delay.
uint32_t home(Run &run, uint32_t receiver) {
    if (run.get(receiver + 0x4e0)) {
        return 0;
    }
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t mode = run.get(receiver + 0x18c);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t facing = run.get8(actor + 0x40);
    if (mode == 2) {
        if (!(facing & 2)) {
            uint32_t left = run.get(receiver + 0x138);
            uint32_t right = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0u - right);
            run.put(receiver + 0x140, 0u - left);
            run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            actor = run.get(receiver + 0x12c);
            run.call(0x406120, actor);
            run.call(0x406150, actor);
            run.call(0x406180, actor);
        }
    } else if (facing & 2) {
        uint32_t left = run.get(receiver + 0x138);
        uint32_t right = run.get(receiver + 0x140);
        run.put(receiver + 0x138, 0u - right);
        run.put(receiver + 0x140, 0u - left);
        run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffd);
        run.call(0x4060b0, run.get(receiver + 0x12c));
    }
    uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x4b8);
    if (elapsed < run.get(receiver + 0x4bc)) {
        return 0;
    }
    uint32_t state = run.get(receiver + 0x184);
    if (state > 6) {
        return 0;
    }
    if (state == 0 || state == 5 || state == 6) {
        run.call(0x482550, receiver, {0});
        return 0;
    }
    int32_t choice = s32(run.call(0x4a3050, 0)) % 0x65;
    if (state != 4) {
        if (choice < 0x5a) {
            run.call(0x480860, receiver);
            return 0;
        }
    } else {
        uint32_t available = run.call(0x482510, receiver);
        if (available) {
            if (choice < 0x21) {
                run.call(0x480e50, receiver);
                return 0;
            }
            if (choice < 0x42) {
                run.call(0x480fd0, receiver);
                return 0;
            }
        } else {
            if (choice < 0x2d) {
                run.call(0x480aa0, receiver);
                return 0;
            }
            if (choice < 0x50) {
                run.call(0x4815b0, receiver);
                return 0;
            }
        }
    }
    run.call(0x4817e0, receiver, {0});
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x47f800:
        return dispatchState(run, receiver, arguments[0]);
    case 0x47ff90:
        return construct(run, receiver, arguments[0]);
    case 0x4805a0:
        return deletingDestroy(run, receiver, arguments[0]);
    case 0x4805c0:
        return destroy(run, receiver);
    case 0x480630:
        return notify(run, receiver);
    case 0x480640:
        return beginHome(run, receiver);
    case 0x4806c0:
        return home(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_level_thirteen_red_tail_core_01_entry, owned, body)
