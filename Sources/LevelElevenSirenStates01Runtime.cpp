// Original Level 11 Siren dispatch and state behavior.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x489850:
    case 0x489c50:
    case 0x48a0d0:
    case 0x48a160:
        return 1;
    case 0x48a0f0:
    case 0x48a240:
    case 0x48a2e0:
    case 0x48a420:
    case 0x48a590:
    case 0x48a7d0:
        return 0;
    default:
        return -1;
    }
}

// Animation lookup with the original GAME_NULL fallback.
uint32_t animation(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t result = run.call(0x4062e0, receiver + 0x128, {name});
    if (!result)
        result = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    return result;
}

void mirrorBounds(Run &run, uint32_t object) {
    uint32_t left = run.get(object + 0x138);
    uint32_t right = run.get(object + 0x140);
    run.put(object + 0x138, 0u - right);
    run.put(object + 0x140, 0u - left);
}

void refresh(Run &run, uint32_t actor) {
    run.call(0x406120, actor);
    run.call(0x406150, actor);
    run.call(0x406180, actor);
}

uint32_t convertedProduct(Run &run, ClawX87State &fp, double value, double factor) {
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    run.x87_step(CLAW_X87_F64, fp, {uint32_t(bits), uint32_t(bits >> 32)});
    std::memcpy(&bits, &factor, sizeof(bits));
    run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(bits), uint32_t(bits >> 32)});
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

// 0x489850. Dispatch table bounds and stride are signed-key game state.
uint32_t dispatch(Run &run, uint32_t receiver, uint32_t key) {
    uint32_t minimum = run.get(0x53c300);
    run.put(0x53c318, 0);
    uint32_t slot;
    if (s32(key) < s32(minimum) || s32(key) > run.gets(0x53c304)) {
        uint32_t grown = run.call(0x4db6e0, 0x53c2f8, {key, 0});
        if (!grown) {
            uint32_t message = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            run.call(0x4db4d0, run.get(0x53c2fc), {0x53c2f8, message, 0xc});
            slot = run.get(0x53c30c);
            minimum = run.get(0x53c300);
        } else {
            minimum = run.get(0x53c300);
            slot = (key - minimum) * run.get(0x53c310) + run.get(0x53c308);
        }
    } else {
        slot = (key - minimum) * run.get(0x53c310) + run.get(0x53c308);
    }
    if (!run.get(slot)) {
        run.call(0x44c840, receiver, {key});
        return 0;
    }
    run.put(0x53c318, 0);
    if (s32(key) < s32(minimum) || s32(key) > run.gets(0x53c304)) {
        uint32_t grown = run.call(0x4db6e0, 0x53c2f8, {key, 0});
        if (!grown) {
            uint32_t message = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            run.call(0x4db4d0, run.get(0x53c2fc), {0x53c2f8, message, 0xc});
            run.call(run.get(run.get(0x53c30c)), receiver);
            return 0;
        }
        minimum = run.get(0x53c300);
    }
    slot = (key - minimum) * run.get(0x53c310) + run.get(0x53c308);
    run.call(run.get(slot), receiver);
    return 0;
}

// 0x48a240. Select idle animation and random home duration/sound.
uint32_t home(Run &run, uint32_t receiver) {
    run.call(0x44d9f0, receiver);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t selected = run.get(receiver + 0x344);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {selected});
    uint32_t random = run.call(0x4a3050, 0);
    run.put(receiver + 0x494, uint32_t(s32(random) % 1001) + 1000u);
    run.put(receiver + 0x490, run.get(0x537210));
    random = run.call(0x4a3050, 0);
    int32_t choice = s32(random) % 101;
    if (choice < 25)
        run.call(0x48ce40, 0, {run.get(receiver + 0xc), run.get(receiver + 0x460), 0});
    else if (choice > 75)
        run.call(0x48ce40, 0, {run.get(receiver + 0xc), run.get(receiver + 0x464), 0});
    return 0;
}

// 0x489c50. Base construction, animations, sounds and physical constants.
uint32_t construct(Run &run, uint32_t receiver, uint32_t argument) {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    run.call_x87_exact(0x44c000, receiver, fp, {argument});
    for (uint32_t offset = 0x468; offset <= 0x494; offset += 4)
        run.put(receiver + offset, 0);
    run.put(receiver, 0x50f694);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x52c204});
    run.put(receiver + 0x344, animation(run, receiver, 0x52c1f0));
    run.put(receiver + 0x308, animation(run, receiver, 0x52c1dc));
    run.put(receiver + 0x34c, animation(run, receiver, 0x52c1dc));
    run.put(receiver + 0x30c, animation(run, receiver, 0x52c1c4));
    run.put(receiver + 0x338, animation(run, receiver, 0x52c1b0));
    run.put(receiver + 0x334, animation(run, receiver, 0x52c19c));
    run.put(receiver + 0x350, animation(run, receiver, 0x52c1f0));
    run.put(receiver + 0x33c, animation(run, receiver, 0x52c188));
    run.put(receiver + 0x340, animation(run, receiver, 0x52c188));
    run.put(receiver + 0x32c, animation(run, receiver, 0x52c170));
    run.put(receiver + 0x374, animation(run, receiver, 0x52c170));
    run.put(receiver + 0x378, animation(run, receiver, 0x52c15c));
    run.put(receiver + 0x37c, animation(run, receiver, 0x52c148));
    run.put(receiver + 0x310, animation(run, receiver, 0x52c134));
    run.put(receiver + 0x380, animation(run, receiver, 0x52c120));
    run.put(receiver + 0x36c, animation(run, receiver, 0x52c120));
    const uint32_t soundOffsets[] = {0x450, 0x3a4, 0x454, 0x458, 0x45c, 0x460, 0x410, 0x464};
    const uint32_t soundNames[] = {0x52c108, 0x52c0f0, 0x52c0d8, 0x52c0c0, 0x52c0a8, 0x52c090, 0x52c078, 0x52c060};
    for (uint32_t i = 0; i < 8; ++i) {
        uint32_t manager = run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28);
        uint32_t sound = run.call(0x4061b0, manager, {soundNames[i]});
        run.put(receiver + soundOffsets[i], sound);
    }
    run.call(0x4208b0, run.get(receiver + 0x12c), {0xffffffec, 0xffffffce, 0x14, 0x32});
    run.call(0x406290, run.get(receiver + 0x12c));
    run.icall(0x546d5c, {receiver + 0x260, 0xffffffde, 0xffffffd4, 0x2e, 0xb});
    run.call(0x420fc0, receiver + 0x2f4, {8});
    run.put(receiver + 0x4a4, 0x5a);
    run.put(receiver + 0x2e4, 0x32);
    uint32_t value = convertedProduct(run, fp, double(run.getf(0x5262b8)), double(run.getf(0x50f688)));
    if (value <= 99)
        value = 99;
    run.put(receiver + 0x2e4, value);
    run.put(run.get(receiver + 0xc) + 0x10c, 9);
    uint32_t actor = run.get(receiver + 0xc);
    value = convertedProduct(run, fp, double(run.gets(actor + 0x10c)), double(run.getf(0x5262b4)));
    run.put(actor + 0x10c, value);
    run.put(run.get(receiver + 0xc) + 0x104, 10);
    actor = run.get(receiver + 0xc);
    value = convertedProduct(run, fp, double(run.gets(actor + 0x104)), double(run.getf(0x5262b0)));
    run.put(actor + 0x104, value);
    run.call(0x40abf0, receiver + 0x128);
    home(run, receiver);
    return receiver;
}

// 0x48a0f0. Destroy owned base subobjects in their original order.
uint32_t destroy(Run &run, uint32_t receiver) {
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}

// 0x48a0d0. Deleting destructor tests the low flag byte.
uint32_t deleteObject(Run &run, uint32_t receiver, uint32_t flags) {
    destroy(run, receiver);
    if (flags & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x48a160. Player-facing chance/timer update after the base notification.
uint32_t notify(Run &run, uint32_t receiver, uint32_t argument) {
    run.call(0x44d000, receiver, {argument});
    if (run.get(0x537964) != 12)
        return 0;
    uint32_t player = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (!run.get(player + 4))
        return 0;
    uint32_t direction = run.get(receiver + 0x18c);
    if (!((direction == 3 && run.get(player)) || (direction == 2 && !run.get(player))))
        return 0;
    uint32_t mode = run.get(receiver + 0x184);
    if (mode != 3 && mode != 4)
        return 0;
    if (run.get(0x537210) - run.get(receiver + 0x488) < run.get(receiver + 0x48c))
        return 0;
    uint32_t chance = run.get(receiver + 0x4a4);
    uint32_t random = run.call(0x4a3050, 0);
    if (s32(random) % 100 >= s32(chance))
        return 0;
    if (run.gets(receiver + 0x20) >= 2)
        run.put(receiver + 0x14, 0x44e620);
    uint32_t reduced = run.get(receiver + 0x4a4) - 30u;
    run.put(receiver + 0x4a4, reduced);
    if (s32(reduced) < 0)
        run.put(receiver + 0x4a4, 0);
    run.put(receiver + 0x48c, 500);
    run.put(receiver + 0x488, run.get(0x537210));
    return 0;
}

// 0x48a2e0. Home animation, orientation and state decision.
uint32_t homeUpdate(Run &run, uint32_t receiver) {
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t actor = run.get(receiver + 0x12c);
        if (!(run.get8(actor + 0x40) & 2)) {
            mirrorBounds(run, receiver);
            run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            refresh(run, run.get(receiver + 0x12c));
        }
    } else {
        run.call(0x406310, receiver + 0x128);
    }
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (run.get(0x537210) - run.get(receiver + 0x490) < run.get(receiver + 0x494))
        return 0;
    uint32_t mode = run.get(receiver + 0x184);
    if (mode > 6)
        return 0;
    if (mode >= 5) {
        run.put(receiver + 0x4a4, 0x5a);
        run.call(0x44edd0, receiver);
    } else if (mode >= 2) {
        run.vcall(receiver, 0x58);
    } else {
        uint32_t random = run.call(0x4a3050, 0);
        int32_t threshold = mode == 0 ? 50 : 25;
        if (s32(random) % 101 >= threshold) {
            run.vcall(receiver, 0x58);
        } else {
            run.call(0x48ce40, 0, {run.get(receiver + 0xc), run.get(receiver + 0x45c), 0});
            run.call(0x4a1180, receiver);
        }
    }
    return 0;
}

// 0x48a420. Enter singing, respecting cooldown and actor orientation.
uint32_t sing(Run &run, uint32_t receiver) {
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    if (run.get(0x537210) - run.get(receiver + 0x470) < run.get(receiver + 0x474)) {
        run.vcall(receiver, 0x44);
        return 0;
    }
    uint32_t direction = run.get(receiver + 0x18c);
    uint32_t actor = run.get(receiver + 0x12c);
    if (direction == 2) {
        if (!(run.get8(actor + 0x40) & 2)) {
            mirrorBounds(run, receiver);
            run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            refresh(run, run.get(receiver + 0x12c));
        }
    } else if (run.get8(actor + 0x40) & 2) {
        mirrorBounds(run, receiver);
        run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffd);
        run.call(0x4060b0, run.get(receiver + 0x12c));
    }
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52c030});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    actor = run.get(receiver + 0x12c);
    uint32_t selected = run.get(receiver + 0x310);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {selected});
    run.put(receiver + 0x49c, 0xfffffff6);
    bool flipped = (run.get8(run.get(receiver + 0x12c) + 0x40) & 2) != 0;
    run.put(receiver + 0x498, flipped ? 28u : 0xffffffe4);
    run.put(receiver + 0x4a0, flipped ? 200u : 0xffffff38);
    run.put(receiver + 0x4a8, 0);
    run.put(receiver + 0x4ac, 0);
    return 0;
}

// 0x48a590. Singing sound lifetime and projectile emission.
uint32_t singingUpdate(Run &run, uint32_t receiver) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (run.get(run.get(receiver + 0x12c) + 0x16c) == 202 && !run.get(receiver + 0x4ac)) {
        uint32_t sound = run.get(receiver + 0x450);
        run.put(receiver + 0x4ac, 1);
        if (sound)
            run.call(0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
        sound = run.get(receiver + 0x450);
        if (sound) {
            run.put(receiver + 0x47c, run.get(run.get(sound + 0x10) + 0x28));
            run.put(receiver + 0x478, run.get(0x537210));
        }
        run.put(receiver + 0x474, 4000);
        run.put(receiver + 0x470, run.get(0x537210));
    }
    uint32_t tick = run.get(0x537210);
    if (run.get(receiver + 0x4ac) && tick - run.get(receiver + 0x480) >= run.get(receiver + 0x484) && run.gets(receiver + 0x4a8) < 4) {
        uint32_t yOffset = run.get(receiver + 0x49c);
        run.put(receiver + 0x4a8, run.get(receiver + 0x4a8) + 1u);
        uint32_t actor = run.get(receiver + 0x12c);
        uint32_t z = run.get(actor + 0x64) - 1u;
        uint32_t y = yOffset + run.get(actor + 0x50);
        uint32_t x = run.get(receiver + 0x498) + run.get(actor + 0x4c);
        uint32_t manager = run.get(run.get(run.get(receiver + 0x130) + 0xc) + 8);
        uint32_t projectile = run.call(0x4c8da0, manager, {0, x, y, z, 0x522d90, 0x40000});
        run.call(0x4c7970, projectile, {0x524394});
        uint32_t controller = run.get(projectile + 0x6c);
        run.put(projectile + 0x104, 0);
        run.put(projectile + 0xd0, 0x40);
        run.call(run.get(controller + 0x10), 0, {projectile});
        uint32_t logic = run.get(run.get(projectile + 0x6c) + 0x18);
        run.putd(logic + 0x50, double(run.gets(receiver + 0x4a0)));
        logic = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(logic + 0x58, 0);
        run.put(logic + 0x5c, 0);
        logic = run.get(run.get(projectile + 0x6c) + 0x18);
        run.put(logic + 0x40, 0);
        run.put(logic + 0x44, 0);
        if (run.gets(receiver + 0x4a0) < 0) {
            logic = run.get(run.get(projectile + 0x6c) + 0x18);
            uint32_t image = run.get(logic + 0x12c);
            if (!(run.get8(image + 0x40) & 2)) {
                mirrorBounds(run, logic);
                run.put(image + 0x40, run.get(image + 0x40) | 2);
                image = run.get(logic + 0x12c);
                uint32_t left = run.get(image + 0x118);
                if (left != 0x80000000) {
                    run.put(image + 0x118, 0u - run.get(image + 0x120));
                    run.put(image + 0x120, 0u - left);
                }
                left = run.get(image + 0x128);
                if (left != 0x80000000) {
                    run.put(image + 0x128, 0u - run.get(image + 0x130));
                    run.put(image + 0x130, 0u - left);
                }
                run.call(0x406180, image);
            }
        }
        run.put(receiver + 0x484, 300);
        run.put(receiver + 0x480, run.get(0x537210));
        tick = run.get(0x537210);
    }
    if (run.get(receiver + 0x4ac) && tick - run.get(receiver + 0x478) >= run.get(receiver + 0x47c))
        run.vcall(receiver, 0x44);
    return 0;
}

// 0x48a7d0. Stop singing, play exit sound, then original lifted transition.
uint32_t stopSinging(Run &run, uint32_t receiver) {
    run.call(0x48cf50, 0, {run.get(receiver + 0xc)});
    run.call(0x48ce40, 0, {run.get(receiver + 0xc), run.get(receiver + 0x410), 0});
    run.call(0x440420, receiver);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x489850:
        return dispatch(run, receiver, arguments[0]);
    case 0x489c50:
        return construct(run, receiver, arguments[0]);
    case 0x48a0d0:
        return deleteObject(run, receiver, arguments[0]);
    case 0x48a0f0:
        return destroy(run, receiver);
    case 0x48a160:
        return notify(run, receiver, arguments[0]);
    case 0x48a240:
        return home(run, receiver);
    case 0x48a2e0:
        return homeUpdate(run, receiver);
    case 0x48a420:
        return sing(run, receiver);
    case 0x48a590:
        return singingUpdate(run, receiver);
    case 0x48a7d0:
        return stopSinging(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_level_eleven_siren_states_01_entry, owned, body)
