// Level 13 chameleon
//
// Canonical translation of the owned actor routines.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Actor fields: +0x0c world, +0x10 state, +0x12c sprite, +0x184 mode,
// +0x18c facing, +0x45c..+0x478 timers, +0x47c overlay, +0x480 opacity.
uint32_t function_421b80(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_421d70(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_421f80(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4220e0(Run &run, uint32_t receiver, const uint32_t *arguments);

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x421320:
        return 1;
    case 0x421710:
        return 1;
    case 0x421b60:
        return 1;
    case 0x421b80:
        return 0;
    case 0x421bf0:
        return 1;
    case 0x421d70:
        return 0;
    case 0x421e00:
        return 0;
    case 0x421f80:
        return 0;
    case 0x422050:
        return 0;
    case 0x4220e0:
        return 0;
    case 0x4221b0:
        return 0;
    default:
        return -1;
    }
}

// 0x421320. State table dispatch.
uint32_t stateSlot(Run &run, uint32_t state) {
    run.put(0x534ef0, 0);
    if (s32(state) < run.gets(0x534ed8) || s32(state) > run.gets(0x534edc)) {
        if (!run.call(0x4db6e0, 0x534ed0, {state, 0})) {
            uint32_t message = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            run.call(0x4db4d0, run.get(0x534ed4), {0x534ed0, message, 0xc});
            return run.get(0x534ee4);
        }
    }
    return (state - run.get(0x534ed8)) * run.get(0x534ee8) + run.get(0x534ee0);
}
uint32_t function_421320(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t slot = stateSlot(run, arguments[0]);
    if (run.get(slot)) {
        slot = stateSlot(run, arguments[0]);
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x44c840, receiver, {arguments[0]});
    }
    return 0;
}

// 0x421710. Constructor.
uint32_t function_421710(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x44c000, receiver, {arguments[0]});
    run.put(receiver + 0x45c, 0);
    run.put(receiver + 0x460, 0);
    run.put(receiver + 0x464, 0);
    run.put(receiver + 0x468, 0);
    run.put(receiver + 0x46c, 0);
    run.put(receiver + 0x470, 0);
    run.put(receiver + 0x474, 0);
    run.put(receiver + 0x478, 0);
    run.put(receiver + 0x0, 0x50bb2c);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x5250a0});
    uint32_t animation0 = run.call(0x4062e0, receiver + 0x128, {0x525088});
    if (!animation0) {
        animation0 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x344, animation0);
    uint32_t animation1 = run.call(0x4062e0, receiver + 0x128, {0x52506c});
    if (!animation1) {
        animation1 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x308, animation1);
    uint32_t animation2 = run.call(0x4062e0, receiver + 0x128, {0x52506c});
    if (!animation2) {
        animation2 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x34c, animation2);
    uint32_t animation3 = run.call(0x4062e0, receiver + 0x128, {0x52506c});
    if (!animation3) {
        animation3 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x30c, animation3);
    uint32_t animation4 = run.call(0x4062e0, receiver + 0x128, {0x525058});
    if (!animation4) {
        animation4 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x338, animation4);
    uint32_t animation5 = run.call(0x4062e0, receiver + 0x128, {0x525058});
    if (!animation5) {
        animation5 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x334, animation5);
    uint32_t animation6 = run.call(0x4062e0, receiver + 0x128, {0x525088});
    if (!animation6) {
        animation6 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x350, animation6);
    uint32_t animation7 = run.call(0x4062e0, receiver + 0x128, {0x525040});
    if (!animation7) {
        animation7 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x33c, animation7);
    uint32_t animation8 = run.call(0x4062e0, receiver + 0x128, {0x525040});
    if (!animation8) {
        animation8 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x340, animation8);
    uint32_t animation9 = run.call(0x4062e0, receiver + 0x128, {0x525024});
    if (!animation9) {
        animation9 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x32c, animation9);
    uint32_t animation10 = run.call(0x4062e0, receiver + 0x128, {0x525024});
    if (!animation10) {
        animation10 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x374, animation10);
    uint32_t animation11 = run.call(0x4062e0, receiver + 0x128, {0x52500c});
    if (!animation11) {
        animation11 = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    }
    run.put(receiver + 0x310, animation11);
    uint32_t manager0 = run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28);
    uint32_t sound0 = run.call(0x4061b0, manager0, {0x524fec});
    run.put(receiver + 0x3a0, sound0);
    uint32_t manager1 = run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28);
    uint32_t sound1 = run.call(0x4061b0, manager1, {0x524fcc});
    run.put(receiver + 0x3a4, sound1);
    uint32_t manager2 = run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28);
    uint32_t sound2 = run.call(0x4061b0, manager2, {0x524fac});
    run.put(receiver + 0x458, sound2);
    uint32_t manager3 = run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28);
    uint32_t sound3 = run.call(0x4061b0, manager3, {0x524f8c});
    run.put(receiver + 0x40c, sound3);
    uint32_t manager4 = run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28);
    uint32_t sound4 = run.call(0x4061b0, manager4, {0x524f70});
    run.put(receiver + 0x450, sound4);
    uint32_t manager5 = run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28);
    uint32_t sound5 = run.call(0x4061b0, manager5, {0x524f54});
    run.put(receiver + 0x454, sound5);
    run.call(0x406240, run.get(receiver + 0x12c));
    run.call(0x406290, run.get(receiver + 0x12c));
    uint32_t setRect = run.get(0x546d5c);
    run.call(setRect, 0, {receiver + 0x220, uint32_t(-0x7f), uint32_t(-0x20), uint32_t(-0x10), uint32_t(-8)});
    run.put(receiver + 0x404, 0xb4);
    run.put(receiver + 0x47c, 0);
    uint32_t region = run.get(run.get(receiver + 0x12c) + 0x170);
    if (region) {
        uint32_t world = run.get(run.get(0x5371fc) + 0x2c);
        if (world) {
            uint32_t overlay = 0;
            if (run.gets(region + 0x64) <= 0x385 && run.gets(region + 0x68) >= 0x385) {
                overlay = run.get(run.get(region + 0x14) + 0xe14);
            }
            run.put(receiver + 0x47c, overlay);
            if (overlay) {
                uint32_t palette = run.get(world + 0x770);
                if (palette) {
                    uint32_t surface = run.get(overlay + 0x30);
                    if (surface) {
                        run.put(surface + 0x1c, palette);
                    }
                }
                uint32_t surface = run.get(run.get(receiver + 0x47c) + 0x30);
                if (surface) {
                    run.call(0x4c6130, surface, {1, 0});
                }
            }
        }
    }
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x164, run.get(sprite + 0x164) & 0xfffffffe);
    uint32_t count = run.get(receiver + 0x2fc);
    if (count > 9) {
        uint32_t flags = count <= 0x20 ? receiver + 0x300 : run.get(receiver + 0x300);
        run.put(flags, run.get(flags) ^ 0x200);
    }
    run.call(setRect, 0, {receiver + 0x260, uint32_t(-0x25), 0x11, 0x30, 0x31});
    run.put(run.get(receiver + 0xc) + 0x10c, 1);
    uint32_t world = run.get(receiver + 0xc);
    uint32_t value = run.call_x87(0x4a30e0, 0, double(run.gets(world + 0x10c)) * double(run.getf(0x5262b4)));
    run.put(world + 0x10c, value);
    run.put(run.get(receiver + 0xc) + 0x104, 10);
    world = run.get(receiver + 0xc);
    value = run.call_x87(0x4a30e0, 0, double(run.gets(world + 0x104)) * double(run.getf(0x5262b0)));
    run.put(world + 0x104, value);
    sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x50, run.get(sprite + 0x50) - 0x20);
    uint32_t actor = run.get(receiver + 0x128);
    run.call(0x4cd800, run.get(run.get(actor + 0xc) + 0x24), {actor, 0});
    run.put(run.get(receiver + 0x128) + 0xcc, 1);
    function_421d70(run, receiver, nullptr);
    return receiver;
}

// 0x421b60. Deleting destructor.
uint32_t function_421b60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_421b80(run, receiver, nullptr);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x421b80. Destructor.
uint32_t function_421b80(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x0, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver + 0x0, 0x50b014);
    return 0;
}

// 0x421bf0. Update state checks and reactive phase-out.
uint32_t compareState(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t string = run.call(0x441030, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
    uint32_t pointer = run.get(0x5376b4);
    uint32_t count = run.get(0x5376b8);
    while (count--) {
        if (pointer) {
            run.call(0x4f6439, pointer);
        }
        pointer += 4;
    }
    return run.call(0x4a3810, 0, {run.get(string), name}) == 0;
}
uint32_t function_421bf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x44d000, receiver, {arguments[0]});
    if (compareState(run, receiver, 0x524f1c)) {
        return 1;
    }
    if (compareState(run, receiver, 0x524f10)) {
        return 1;
    }
    if (compareState(run, receiver, 0x5234f4)) {
        return 1;
    }
    if (run.get(0x537964) != 0xe) {
        return 0;
    }
    uint32_t player = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    uint32_t result = run.get(player + 0x4);
    if (!result) {
        return result;
    }
    result = run.get(receiver + 0x18c);
    if (!((result == 3 && run.get(player) != 0) || (result == 2 && run.get(player) == 0))) {
        return result;
    }
    result = run.get(receiver + 0x184);
    if (result != 3 && result != 4) {
        return result;
    }
    result = run.call(0x4a3050, 0);
    if (s32(result) % 100 < 3) {
        return function_421f80(run, receiver, nullptr);
    }
    return uint32_t(s32(result) / 100);
}

// 0x421d70. Idle entry.
uint32_t function_421d70(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x44d9f0, receiver);
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x344);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffe);
    sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xfffffffe);
    uint32_t random = run.call(0x4a3050, 0);
    if (s32(random) % 100 < 3) {
        uint32_t sound = run.get(receiver + 0x458);
        if (sound && run.get(0x532c0c)) {
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
        }
    }
    return 0;
}

// 0x421e00. AI decision update.
uint32_t function_421e00(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t sprite = run.get(receiver + 0x12c);
        if (!(run.get8(sprite + 0x40) & 2)) {
            uint32_t lower = run.get(receiver + 0x138);
            uint32_t upper = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0u - upper);
            run.put(receiver + 0x140, 0u - lower);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            run.call(0x4060b0, run.get(receiver + 0x12c));
        }
    } else {
        run.call(0x406310, receiver + 0x128);
    }
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t mode = run.get(receiver + 0x184);
    if (mode > 6) {
        return 0;
    }
    uint32_t random = run.call(0x4a3050, 0);
    if (mode <= 1) {
        if (s32(random) % 0x65 < 0x42) {
            run.call(0x44ebb0, receiver);
            return 0;
        }
    } else if (mode <= 4) {
        int32_t choice = s32(random) % 0x65;
        if (choice < 0x28) {
            if (run.get(0x537210) - run.get(receiver + 0x45c) < run.get(receiver + 0x460)) {
                return 0;
            }
            run.call(0x43efe0, receiver);
            random = run.call(0x4a3050, 0);
            run.put(receiver + 0x460, uint32_t(s32(random) % 0x1f5) + 500);
            run.put(receiver + 0x45c, run.get(0x537210));
            return 0;
        }
        if (choice >= 0x50) {
            return 0;
        }
    } else {
        if (s32(random) % 100 < 3) {
            uint32_t sound = run.get(receiver + 0x458);
            if (sound && run.get(0x532c0c)) {
                run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
            }
        }
        run.call(0x44edd0, receiver);
        return 0;
    }
    function_421f80(run, receiver, nullptr);
    return 0;
}

// 0x421f80. Phase-out entry.
uint32_t function_421f80(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(0x537210) - run.get(receiver + 0x46c) < run.get(receiver + 0x470)) {
        run.vcall(receiver, 0x44);
        return 0;
    }
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x524f1c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 1);
    uint32_t world = run.get(receiver + 0xc);
    run.put(receiver + 0x480, 0xff);
    uint32_t region = run.get(world + 0x170);
    if (region) {
        uint32_t overlay = 0;
        if (run.gets(region + 0x64) <= 0x385 && run.gets(region + 0x68) >= 0x385) {
            overlay = run.get(run.get(region + 0x14) + 0xe14);
        }
        run.put(world + 0x174, overlay);
        run.put(world + 0x16c, 0x385);
    }
    uint32_t overlay = run.get(receiver + 0x47c);
    if (overlay) {
        uint32_t surface = run.get(overlay + 0x30);
        if (surface) {
            run.call(0x4c6130, surface, {0x32, 0});
        }
    }
    return 0;
}

// 0x422050. Fade-out update.
uint32_t function_422050(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(0x537210) - run.get(receiver + 0x464) >= run.get(receiver + 0x468)) {
        run.put(receiver + 0x480, run.get(receiver + 0x480) - 10);
        run.put(receiver + 0x468, 5);
        run.put(receiver + 0x464, run.get(0x537210));
    }
    uint32_t opacity = run.get(receiver + 0x480);
    uint32_t overlay = run.get(receiver + 0x47c);
    if (overlay) {
        uint32_t surface = run.get(overlay + 0x30);
        if (surface) {
            run.put(surface + 0x18, s32(opacity) < 0 ? 0 : opacity);
        }
    }
    if (s32(opacity) < 0) {
        function_4220e0(run, receiver, nullptr);
    }
    return 0;
}

// 0x4220e0. Phase-in entry.
uint32_t function_4220e0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x524f10});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x40, run.get(sprite + 0x40) | 1);
    run.put(receiver + 0x480, 0);
    uint32_t upper = run.call_x87(0x4a30e0, 0, run.getd(receiver + 0x98));
    uint32_t lower = run.call_x87(0x4a30e0, 0, run.getd(receiver + 0x80));
    uint32_t range = upper - lower + 1;
    uint32_t random = run.call(0x4a3050, 0);
    uint32_t position = upper;
    if (!range) {
        if (random & 1) {
            position = lower;
        }
    } else {
        position = uint32_t(int64_t(s32(random)) % int64_t(s32(range))) + lower;
    }
    uint32_t world = run.get(0x537e88);
    uint32_t origin = run.get(world + 0x4c);
    uint32_t left = run.get(world + 0x118) + origin;
    uint32_t right = run.get(world + 0x120) + origin;
    random = run.call(0x4a3050, 0);
    run.put(receiver + 0x478, uint32_t(s32(random) % 0x5dd));
    run.put(receiver + 0x474, run.get(0x537210));
    if (s32(position) < s32(left) || s32(position) > s32(right)) {
        run.putd(receiver + 0x68, double(s32(position)));
    }
    return 0;
}

// 0x4221b0. Fade-in update.
uint32_t function_4221b0(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(0x537210) - run.get(receiver + 0x474) < run.get(receiver + 0x478)) {
        return 0;
    }
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffe);
    if (run.get(0x537210) - run.get(receiver + 0x464) >= run.get(receiver + 0x468)) {
        run.put(receiver + 0x480, run.get(receiver + 0x480) + 10);
        run.put(receiver + 0x468, 5);
        run.put(receiver + 0x464, run.get(0x537210));
    }
    uint32_t opacity = run.get(receiver + 0x480);
    uint32_t overlay = run.get(receiver + 0x47c);
    if (s32(opacity) > 0xff) {
        if (overlay) {
            uint32_t surface = run.get(overlay + 0x30);
            if (surface) {
                run.put(surface + 0x18, 0xff);
                surface = run.get(run.get(receiver + 0x47c) + 0x30);
                if (surface) {
                    run.call(0x4c6130, surface, {1, 0});
                }
            }
        }
        run.put(receiver + 0x470, 1000);
        run.put(receiver + 0x46c, run.get(0x537210));
        run.vcall(receiver, 0x44);
        return 0;
    }
    if (overlay) {
        uint32_t surface = run.get(overlay + 0x30);
        if (surface) {
            run.put(surface + 0x18, opacity);
        }
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x421320:
        return function_421320(run, receiver, arguments);
    case 0x421710:
        return function_421710(run, receiver, arguments);
    case 0x421b60:
        return function_421b60(run, receiver, arguments);
    case 0x421b80:
        return function_421b80(run, receiver, arguments);
    case 0x421bf0:
        return function_421bf0(run, receiver, arguments);
    case 0x421d70:
        return function_421d70(run, receiver, arguments);
    case 0x421e00:
        return function_421e00(run, receiver, arguments);
    case 0x421f80:
        return function_421f80(run, receiver, arguments);
    case 0x422050:
        return function_422050(run, receiver, arguments);
    case 0x4220e0:
        return function_4220e0(run, receiver, arguments);
    case 0x4221b0:
        return function_4221b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_thirteen_chameleon_entry, owned, body)
