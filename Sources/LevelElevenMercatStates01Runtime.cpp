// Mercat state decisions from the original v1.0 game.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x460c50:
    case 0x460ea0:
    case 0x461360:
    case 0x4614c0:
    case 0x4616e0:
        return 0;
    default:
        return -1;
    }
}

// 0x461360. Enter firing, keeping the facing-dependent projectile values.
uint32_t enterFiring(Run &run, uint32_t actor) {
    // +0x50/+0x54 horizontal velocity; +0x48c/+0x490 firing cooldown.
    run.put(actor + 0x50, 0);
    run.put(actor + 0x54, 0);
    if (run.get(0x537210) - run.get(actor + 0x48c) < run.get(actor + 0x490))
        return 0;
    // +0x18c facing; +0x12c sprite; +0x138/+0x140 horizontal bounds.
    uint32_t sprite = run.get(actor + 0x12c);
    if (run.get(actor + 0x18c) == 2) {
        if (!(run.get8(sprite + 0x40) & 2)) {
            uint32_t left = run.get(actor + 0x138);
            run.put(actor + 0x138, 0u - run.get(actor + 0x140));
            run.put(actor + 0x140, 0u - left);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            sprite = run.get(actor + 0x12c);
            run.call(0x406120, sprite);
            run.call(0x406150, sprite);
            run.call(0x406180, sprite);
        }
    } else if (run.get8(sprite + 0x40) & 2) {
        uint32_t left = run.get(actor + 0x138);
        run.put(actor + 0x138, 0u - run.get(actor + 0x140));
        run.put(actor + 0x140, 0u - left);
        run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffdu);
        run.call(0x4060b0, run.get(actor + 0x12c));
    }
    // +0x10 state record; +0x24 previous state; +0x134 saved animation.
    run.put(actor + 0x24, run.get(run.get(actor + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x524548});
    run.put(run.get(actor + 0x10) + 0x1c, state);
    sprite = run.get(actor + 0x12c);
    uint32_t animation = run.get(actor + 0x310);
    run.put(actor + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    // +0x4cc/+0x4d0 projectile origin, +0x4d4 speed, +0x4dc fired flag.
    run.put(actor + 0x4d0, 0);
    if (run.get8(run.get(actor + 0x12c) + 0x40) & 2) {
        run.put(actor + 0x4cc, 0x1c);
        run.put(actor + 0x4d4, 0x190);
        run.put(actor + 0x1a0, 0);
        run.put(actor + 0x4dc, 0);
    } else {
        run.put(actor + 0x4cc, 0xffffffe4u);
        run.put(actor + 0x4d4, 0xfffffe70u);
        run.put(actor + 0x1a0, 0);
        run.put(actor + 0x4dc, 0);
    }
    return 0;
}

// 0x460c50. Movement-state update and the decision to enter firing.
uint32_t updateMoving(Run &run, uint32_t actor) {
    if (run.get(actor + 0x18c) == 2)
        run.call(0x4357a0, actor + 0x128);
    else
        run.call(0x406310, actor + 0x128);
    run.call(0x4c82a0, run.get(actor + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t now = run.get(0x537210);
    // +0x4a4/+0x4a8 animation timer; +0x184 movement mode.
    if (now - run.get(actor + 0x4a4) < run.get(actor + 0x4a8))
        return 0;
    switch (run.get(actor + 0x184)) {
    case 0:
    case 1:
        if (s32(run.call(0x4a3050, 0)) % 101 < 20) {
            uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 3);
            run.call(0x48ce40, 0, {run.get(actor + 0xc), run.get(actor + 0x45c + index * 4), 0});
            run.call(0x44ebb0, actor);
        }
        break;
    case 2:
        if (s32(run.call(0x4a3050, 0)) % 101 < 20) {
            uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 3);
            run.call(0x48ce40, 0, {run.get(actor + 0xc), run.get(actor + 0x45c + index * 4), 0});
            run.call(0x4a1180, actor);
        }
        break;
    case 3:
    case 4:
        // +0x484/+0x488 next decision timer.
        if (now - run.get(actor + 0x484) >= run.get(actor + 0x488)) {
            run.vcall(actor, 0x58);
            run.put(actor + 0x488, 0x64);
            run.put(actor + 0x484, run.get(0x537210));
        }
        break;
    case 5:
    case 6:
        run.put(actor + 0x4d8, 0x5a);
        run.call(0x44edd0, actor);
        break;
    }
    bool fire = false;
    if (run.get(0x534eac) != 0x26b7) {
        // +0x194 target sprite, +0x190 world context.
        uint32_t target = run.get(actor + 0x194);
        uint32_t player = run.get(0x537e88);
        uint32_t map = run.get(run.get(run.get(actor + 0x190) + 0xc) + 0x24);
        if (run.call(0x4cda10, map, {run.get(target + 0x4c), run.get(target + 0x50), run.get(player + 0x4c), 0x20})) {
            target = run.get(actor + 0x194);
            player = run.get(0x537e88);
            uint32_t y = run.get(target + 0x50);
            uint32_t playerY = run.get(player + 0x50);
            fire = s32(playerY) < s32(y + 0x32) && s32(playerY) > s32(y - 0x32) && run.get(target + 0x38) != 0xffffffffu;
        }
    }
    if (fire)
        enterFiring(run, actor);
    else
        run.call(0x44da20, actor);
    return 0;
}

// 0x460ea0. Home animation selection and movement-mode transitions.
uint32_t updateHome(Run &run, uint32_t actor) {
    if (run.get(0x537210) - run.get(actor + 0x4a4) >= run.get(actor + 0x4a8)) {
        run.put(actor + 0x4a8, 0x3e8);
        run.put(actor + 0x4a4, run.get(0x537210));
        uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 4);
        if (index <= 3) {
            uint32_t animation = run.get(actor + 0x4bc + index * 4);
            uint32_t sprite = run.get(actor + 0x12c);
            run.put(actor + 0x134, run.get(sprite + 0x190));
            uint32_t cursor = sprite + 0x188;
            run.call(0x4c8220, cursor, {animation});
            run.call(0x4c82a0, cursor, {run.get(0x5430c4)});
        }
    }
    uint32_t mode = run.get(actor + 0x184);
    if (mode <= 4) {
        run.vcall(actor, 0x44);
    } else if (mode <= 6) {
        // +0x4ac/+0x4b0 movement cooldown.
        if (run.get(0x537210) - run.get(actor + 0x4ac) >= run.get(actor + 0x4b0) && s32(run.call(0x4a3050, 0)) % 100 < 20) {
            if (run.get(actor + 0x184) == 5) {
                int32_t choice = s32(run.call(0x4a3050, 0)) % 101;
                if (choice < 25) {
                    run.call(0x48ce40, 0, {run.get(actor + 0xc), run.get(actor + 0x454), 0});
                    run.call(0x44edd0, actor);
                    return 0;
                }
                if (choice > 50)
                    run.call(0x48ce40, 0, {run.get(actor + 0xc), run.get(actor + 0x458), 0});
            }
            run.call(0x44edd0, actor);
        }
    }
    return 0;
}

// 0x4614c0. Firing-frame trigger, trident construction, and completion.
uint32_t updateFiring(Run &run, uint32_t actor) {
    run.call(0x4c82a0, run.get(actor + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t sprite = run.get(actor + 0x12c);
    if (run.get(sprite + 0x16c) == 0xcb && !run.get(actor + 0x4dc)) {
        uint32_t sound = run.get(actor + 0x450);
        run.put(actor + 0x4dc, 1);
        if (sound)
            run.call(0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
        if (run.get(0x537964) == 0xb) {
            run.put(actor + 0x490, 0x3e8);
            run.put(actor + 0x48c, run.get(0x537210));
        } else {
            run.put(actor + 0x490, 0x2ee);
            run.put(actor + 0x48c, run.get(0x537210));
        }
    }
    uint32_t now = run.get(0x537210);
    if (run.get(actor + 0x4dc)) {
        // +0x4b4/+0x4b8 projectile repeat timer.
        if (now - run.get(actor + 0x4b4) >= run.get(actor + 0x4b8)) {
            sprite = run.get(actor + 0x12c);
            uint32_t y = run.get(actor + 0x4d0) + run.get(sprite + 0x50);
            uint32_t z = run.get(sprite + 0x64) - 1;
            uint32_t x = run.get(actor + 0x4cc) + run.get(sprite + 0x4c);
            uint32_t world = run.get(run.get(run.get(actor + 0x130) + 0xc) + 8);
            uint32_t projectile = run.call(0x4c8da0, world, {0, x, y, z, 0x522d80, 0x40000});
            run.call(0x4c7970, projectile, {0x5243f8});
            uint32_t logic = run.get(projectile + 0x6c);
            run.put(projectile + 0x104, 0x14);
            run.put(projectile + 0xd0, 0x40);
            run.call(run.get(logic + 0x10), 0, {projectile});
            logic = run.get(projectile + 0x6c);
            uint32_t projectileActor = run.get(logic + 0x18);
            run.putd(projectileActor + 0x50, double(s32(run.get(actor + 0x4d4))));
            projectileActor = run.get(run.get(projectile + 0x6c) + 0x18);
            run.put(projectileActor + 0x58, 0);
            run.put(projectileActor + 0x5c, 0);
            projectileActor = run.get(run.get(projectile + 0x6c) + 0x18);
            run.put(projectileActor + 0x40, 0);
            run.put(projectileActor + 0x44, 0);
            if (s32(run.get(actor + 0x4d4)) > 0) {
                projectileActor = run.get(run.get(projectile + 0x6c) + 0x18);
                uint32_t projectileSprite = run.get(projectileActor + 0x12c);
                if (!(run.get8(projectileSprite + 0x40) & 2)) {
                    uint32_t left = run.get(projectileActor + 0x138);
                    run.put(projectileActor + 0x138, 0u - run.get(projectileActor + 0x140));
                    run.put(projectileActor + 0x140, 0u - left);
                    run.put(projectileSprite + 0x40, run.get(projectileSprite + 0x40) | 2);
                    projectileSprite = run.get(projectileActor + 0x12c);
                    left = run.get(projectileSprite + 0x118);
                    if (left != 0x80000000u) {
                        run.put(projectileSprite + 0x118, 0u - run.get(projectileSprite + 0x120));
                        run.put(projectileSprite + 0x120, 0u - left);
                    }
                    left = run.get(projectileSprite + 0x128);
                    if (left != 0x80000000u) {
                        run.put(projectileSprite + 0x128, 0u - run.get(projectileSprite + 0x130));
                        run.put(projectileSprite + 0x130, 0u - left);
                    }
                    run.call(0x406180, projectileSprite);
                }
            }
            run.put(actor + 0x4b8, 0x1f4);
            run.put(actor + 0x4b4, run.get(0x537210));
            now = run.get(0x537210);
        }
        // +0x494/+0x498 state-completion timer.
        if (now - run.get(actor + 0x494) >= run.get(actor + 0x498))
            run.vcall(actor, 0x44);
    }
    return 0;
}

// 0x4616e0. Death-state sound and unchanged common enemy death transition.
uint32_t enterDeath(Run &run, uint32_t actor) {
    run.call(0x48cf50, 0, {run.get(actor + 0xc)});
    uint32_t sound = run.get(actor + 0x478);
    run.call(0x48ce40, 0, {run.get(actor + 0xc), sound, 0});
    run.call(0x440420, actor);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *) {
    switch (function) {
    case 0x460c50:
        return updateMoving(run, receiver);
    case 0x460ea0:
        return updateHome(run, receiver);
    case 0x461360:
        return enterFiring(run, receiver);
    case 0x4614c0:
        return updateFiring(run, receiver);
    case 0x4616e0:
        return enterDeath(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_eleven_mercat_states_01_entry, owned, body)
