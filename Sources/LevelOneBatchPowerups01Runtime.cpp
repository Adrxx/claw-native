// Level 1 powerup pickups: special, curse, health, ammo, glitterless
//
// Object layout used here (this = the pickup object, passed as the argument):
// +0x04 frame index, +0x08 flags, +0x0c owner, +0x4c x, +0x50 y, +0x64 z,
// +0x6c logic record, +0xc8 glitter object, +0xd0 draw flags, +0xfc value,
// +0x138..+0x144 bounds, +0x164 input flags, +0x170 image id, +0x174 frame
// rectangle, +0x188 animation, +0x190 animation set.
// Logic record: +0x10 update function, +0x1c state, +0x64/+0x68 velocity,
// +0x130 timer, +0x168 and +0x16c scratch.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x470430:
        return 1;
    case 0x470a20:
        return 1;
    case 0x470100:
        return 1;
    case 0x470d00:
        return 1;
    case 0x471100:
        return 1;
    default:
        return -1;
    }
}

// Global data used by these functions.
const uint32_t kPowerupTableCount = 0x52a190;
const uint32_t kPowerupIds = 0x537ec8;
const uint32_t kPowerupValues = 0x537fd0;
const uint32_t kPowerupDrawFlags = 0x5380d8;
const uint32_t kPowerupScratch = 0x538310;
const uint32_t kGameGlobals = 0x5371fc;
const uint32_t kFrameTime = 0x53720c;
const uint32_t kAnimationArgument = 0x5430c4;
const uint32_t kMenuActive = 0x538418;
const uint32_t kExtraCheck = 0x52550c;

// Calls 0x4f6286 on the owner's lookup table with the name at `name`, storing
// the result in the local that shares the argument slot (entry + 4). Returns
// the stored result.
uint32_t lookupName(Run &run, uint32_t self, uint32_t name) {
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    uint32_t table = run.get(run.get(self + 0x0c) + 0x10) + 0x10;
    run.call(0x4f6286, table, {name, local});
    return run.get(local);
}

// First-state animation selection when the pickup has no animation set.
void chooseAnimation(Run &run, uint32_t self) {
    if (run.get(self + 0x190) != 0)
        return;
    uint32_t image = run.get(self + 0x170);
    uint32_t coins = lookupName(run, self, 0x5279b8);
    uint32_t name = 0x52a198;
    if (image == coins)
        name = 0x5240d8;
    run.call(0x4c79e0, self, {name, 0});
}

// Copies the frame rectangle into the bounds fields.
void copyBounds(Run &run, uint32_t self) {
    uint32_t rect = run.get(self + 0x174);
    if (rect == 0)
        return;
    uint32_t width = run.get(rect + 0x20) - run.get(rect + 0x18);
    run.put(self + 0x138, width);
    uint32_t height = run.get(rect + 0x24) - run.get(rect + 0x1c);
    run.put(self + 0x13c, height);
    uint32_t right = run.get(rect + 0x20) - 1 + run.get(rect + 0x18);
    run.put(self + 0x140, right);
    uint32_t bottom = run.get(rect + 0x24) - 1 + run.get(rect + 0x1c);
    run.put(self + 0x144, bottom);
}

// Widens the bounds by a fixed margin.
void padBounds(Run &run, uint32_t self) {
    uint32_t left = run.get(self + 0x138) - 6;
    uint32_t top = run.get(self + 0x13c) - 10;
    uint32_t right = run.get(self + 0x140) + 6;
    uint32_t bottom = run.get(self + 0x144) + 2;
    run.put(self + 0x138, left);
    run.put(self + 0x13c, top);
    run.put(self + 0x140, right);
    run.put(self + 0x144, bottom);
}

// Finds this pickup's image id in the powerup table and applies its row.
void applyTableRow(Run &run, uint32_t self) {
    uint32_t count = run.get(kPowerupTableCount);
    uint32_t image = run.get(self + 0x170);
    uint32_t index = 0;
    if (s32(count) > 0) {
        do {
            if (run.get(kPowerupIds + index * 4) == image) {
                run.put(self + 0x04, index);
                if (index == 0)
                    run.put(self + 0x04, 0x21);
                uint32_t value = run.get(kPowerupValues + index * 4);
                run.put(self + 0xfc, value);
                uint32_t record = run.get(self + 0x6c);
                uint32_t scratch = run.get(kPowerupScratch + index * 4);
                run.put(record + 0x168, scratch);
                if (run.get(self + 0xd0) == 1) {
                    uint32_t flags = run.get(kPowerupDrawFlags + index * 4);
                    run.put(self + 0xd0, flags);
                }
                return;
            }
            index = index + 1;
        } while (s32(index) < s32(count));
    }
    run.put(self + 0x04, 0);
    run.put(self + 0xfc, 100);
    uint32_t record = run.get(self + 0x6c);
    run.put(record + 0x168, 0);
}

// Creates the glitter object at the pickup's position.
uint32_t createGlitter(Run &run, uint32_t self) {
    uint32_t manager = run.get(run.get(self + 0x0c) + 0x08);
    uint32_t x = run.get(self + 0x4c);
    uint32_t y = run.get(self + 0x50);
    uint32_t z = run.get(self + 0x64) + 1;
    return run.call(0x4c8da0, manager, {1, x, y, z, 0x522950, 0x40000});
}

// Shared state 0x1d: ask the glitter object to finish.
void finishGlitter(Run &run, uint32_t self) {
    uint32_t glitter = run.get(self + 0xc8);
    if (glitter == 0)
        return;
    uint32_t flags = run.get(glitter + 8) | 0x10000;
    run.put(glitter + 8, flags);
}

void tickAnimation(Run &run, uint32_t self) {
    run.call(0x4c82a0, self + 0x188, {run.get(kAnimationArgument)});
}

// 0x470100. Forwards to the treasure powerup update at 0x46fd10.
uint32_t function_470100(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return run.call(0x46fd10, 0, {arguments[0]});
}

// 0x470430. Special powerup update.
uint32_t function_470430(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t self = arguments[0];
    uint32_t record = run.get(self + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state <= 5) {
        if (state == 5) {
            tickAnimation(run, self);
            if ((run.get(self + 0x164) & 0x200) == 0)
                return 1;
            run.put(record + 0x1c, 9000);
            return 1;
        }
        if (state != 0)
            return 1;
        run.put(record + 0x168, 0);
        run.put(self + 0xc8, 0);
        if (run.get(self + 0x64) == 0) {
            run.put(self + 0x64, 1000);
            uint32_t flags = run.get(self + 8) | 0x20000;
            run.put(self + 8, flags);
        }
        chooseAnimation(run, self);
        uint32_t flags = run.get(self + 8) | 0x80000;
        run.put(self + 8, flags);
        run.put(self + 0xd0, 0x100);
        copyBounds(run, self);
        padBounds(run, self);
        if (run.get(kMenuActive) == 0)
            run.call(0x4719e0, 0, {run.get(self + 0x0c)});
        applyTableRow(run, self);
        uint32_t glitter = 0;
        uint32_t mode = run.vcall(run.get(run.get(kGameGlobals) + 0x2c), 0x10);
        bool finish = false;
        if (mode == 4) {
            uint32_t image = run.get(self + 0x170);
            uint32_t extraLife = lookupName(run, self, 0x52a1ec);
            if (image == extraLife)
                finish = true;
        }
        if (finish) {
            uint32_t flags2 = run.get(self + 8) | 0x10000;
            run.put(self + 8, flags2);
            return 1;
        }
        if (run.get(record + 0x10) != 0x470100) {
            if (run.get(run.get(kGameGlobals) + 0x124) != 0) {
                uint32_t image = run.get(self + 0x170);
                uint32_t warp = lookupName(run, self, 0x52a07c);
                if (image != warp)
                    glitter = createGlitter(run, self);
            }
        }
        if (glitter != 0)
            run.put(self + 0xc8, glitter);
        run.put(record + 0x1c, 5);
        return 1;
    }
    if (state != 0x1d) {
        if (state == 9000) {
            uint32_t flags = run.get(self + 8) | 0x21;
            run.put(self + 8, flags);
            uint32_t glitter = run.get(self + 0xc8);
            if (glitter != 0) {
                uint32_t glitterFlags = run.get(glitter + 8) | 0x10000;
                run.put(glitter + 8, glitterFlags);
                run.put(self + 0xc8, 0);
            }
            uint32_t camera = run.get(run.get(run.get(self + 0x0c) + 0x24) + 0x5c);
            uint32_t cameraX = run.get(camera + 0x84);
            uint32_t cameraY = run.get(camera + 0x88);
            run.put(record + 0x130, 400);
            uint32_t dx = (cameraX + 0x12c) * 1000 - run.get(self + 0x4c) * 1000;
            run.put(record + 0x64, dx / 400);
            run.put(record + 0x1c, 0x2329);
            uint32_t dy = run.get(self + 0x50) * 1000 - (cameraY - 0xc8) * 1000;
            run.put(record + 0x68, dy / 400);
            return 1;
        }
        if (state != 0x2329)
            return 1;
        uint32_t elapsed = run.get(kFrameTime);
        uint32_t timer = run.get(record + 0x130);
        if (elapsed < timer)
            run.put(record + 0x130, timer - elapsed);
        else
            run.put(record + 0x130, 0);
        if (run.get(record + 0x130) == 0) {
            uint32_t flags = run.get(self + 8) | 0x10000;
            run.put(self + 8, flags);
        }
        uint32_t velocityX = run.get(record + 0x64);
        if (velocityX != 0) {
            uint32_t step = (run.get(kFrameTime) * velocityX) / 1000;
            run.put(self + 0x4c, run.get(self + 0x4c) + step);
        }
        uint32_t velocityY = run.get(record + 0x68);
        if (velocityY != 0) {
            uint32_t step = (run.get(kFrameTime) * velocityY) / 1000;
            run.put(self + 0x50, run.get(self + 0x50) - step);
        }
        tickAnimation(run, self);
        return 1;
    }
    finishGlitter(run, self);
    return 1;
}

// 0x470a20. Curse powerup update.
uint32_t function_470a20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t self = arguments[0];
    uint32_t record = run.get(self + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state != 0) {
        if (state == 5) {
            tickAnimation(run, self);
            uint32_t target = run.get(record + 0x16c);
            if (target == 0)
                return 1;
            uint32_t hit = run.call(0x436860, target, {run.get(self + 0x4c), run.get(self + 0x50)});
            if (hit == 0)
                return 1;
            uint32_t flags = run.get(self + 8) | 0x10000;
            run.put(self + 8, flags);
            return 1;
        }
        if (state != 0x1d)
            return 1;
        finishGlitter(run, self);
        return 1;
    }
    run.put(record + 0x168, 0);
    run.put(record + 0x16c, 0);
    uint32_t mode = run.vcall(run.get(run.get(kGameGlobals) + 0x2c), 0x10);
    bool proceed = mode == 4;
    if (proceed)
        proceed = run.get(kExtraCheck) != 0;
    if (proceed) {
        mode = run.vcall(run.get(run.get(kGameGlobals) + 0x2c), 0x10);
        proceed = mode == 4;
    }
    if (!proceed) {
        uint32_t flags = run.get(self + 8) | 0x10000;
        run.put(self + 8, flags);
        return 0;
    }
    uint32_t partner = run.get(run.get(run.get(kGameGlobals) + 0x2c) + 0xbd4);
    run.put(record + 0x16c, partner);
    run.put(self + 0xc8, 0);
    if (run.get(self + 0x64) == 0) {
        run.put(self + 0x64, 1000);
        uint32_t flags = run.get(self + 8) | 0x20000;
        run.put(self + 8, flags);
    }
    chooseAnimation(run, self);
    uint32_t flags = run.get(self + 8) | 0x80000;
    run.put(self + 8, flags);
    run.put(self + 0xd0, 0x100);
    copyBounds(run, self);
    padBounds(run, self);
    if (run.get(kMenuActive) == 0)
        run.call(0x4719e0, 0, {run.get(self + 0x0c)});
    applyTableRow(run, self);
    uint32_t glitter = 0;
    if (run.get(record + 0x10) != 0x470100) {
        if (run.get(run.get(kGameGlobals) + 0x124) != 0)
            glitter = createGlitter(run, self);
    }
    if (glitter != 0)
        run.put(self + 0xc8, glitter);
    run.put(record + 0x1c, 5);
    return 1;
}

// 0x470d00. Health powerup update.
uint32_t function_470d00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t self = arguments[0];
    uint32_t record = run.get(self + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state != 0) {
        if (state == 5) {
            tickAnimation(run, self);
            return 1;
        }
        if (state == 0x1d)
            finishGlitter(run, self);
        return 1;
    }
    run.put(record + 0x168, 0);
    if (run.get(self + 0x190) == 0)
        run.call(0x4c79e0, self, {0x52a198, 0});
    if (run.get(self + 0x64) == 0) {
        run.put(self + 0x64, 1000);
        uint32_t flags = run.get(self + 8) | 0x20000;
        run.put(self + 8, flags);
    }
    uint32_t flags = run.get(self + 8) | 0x80000;
    run.put(self + 8, flags);
    run.put(self + 0xd0, 0x10000);
    copyBounds(run, self);
    if (run.get(kMenuActive) == 0)
        run.call(0x4719e0, 0, {run.get(self + 0x0c)});
    applyTableRow(run, self);
    uint32_t glitter = 0;
    if (run.get(run.get(kGameGlobals) + 0x124) != 0)
        glitter = createGlitter(run, self);
    if (glitter != 0) {
        run.put(self + 0xc8, glitter);
        run.put(record + 0x1c, 5);
        return 1;
    }
    run.put(self + 0xc8, 0);
    run.put(record + 0x1c, 5);
    return 1;
}

// 0x471100. Ammo powerup update.
uint32_t function_471100(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t self = arguments[0];
    uint32_t record = run.get(self + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state != 0) {
        if (state == 5) {
            tickAnimation(run, self);
            return 1;
        }
        if (state == 0x1d)
            finishGlitter(run, self);
        return 1;
    }
    run.put(record + 0x168, 0);
    if (run.get(self + 0x190) == 0)
        run.call(0x4c79e0, self, {0x52a198, 0});
    if (run.get(self + 0x64) == 0) {
        run.put(self + 0x64, 1000);
        uint32_t flags = run.get(self + 8) | 0x20000;
        run.put(self + 8, flags);
    }
    run.put(self + 0xd0, 0x800000);
    copyBounds(run, self);
    uint32_t flags = run.get(self + 8) | 0x80000;
    run.put(self + 8, flags);
    if (run.get(kMenuActive) == 0)
        run.call(0x4719e0, 0, {run.get(self + 0x0c)});
    applyTableRow(run, self);
    uint32_t image = run.get(self + 0x170);
    uint32_t dynamite = lookupName(run, self, 0x5235d0);
    if (image == dynamite)
        run.put(self + 0xd0, 0x100);
    uint32_t glitter = 0;
    if (run.get(run.get(kGameGlobals) + 0x124) != 0)
        glitter = createGlitter(run, self);
    if (glitter != 0)
        run.put(self + 0xc8, glitter);
    else
        run.put(self + 0xc8, 0);
    run.put(record + 0x1c, 5);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x470430:
        return function_470430(run, receiver, arguments);
    case 0x470a20:
        return function_470a20(run, receiver, arguments);
    case 0x470100:
        return function_470100(run, receiver, arguments);
    case 0x470d00:
        return function_470d00(run, receiver, arguments);
    case 0x471100:
        return function_471100(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_powerups_01_entry, owned, body)
