#include "PlayerAirStates.h"
#include <cstring>
namespace {
using S = ClawPlayerLocomotion;
using D = ClawPlayerLocomotionDependency;
uint32_t &a(S *s, uint32_t offset) {
    return s->actor[offset / 4];
}
uint32_t effect(S *s, D d, void *c, uint32_t entry, uint32_t x = 0, uint32_t y = 0, uint32_t z = 0) {
    return d ? d(s, entry, x, y, z, c) : 0;
}
void rectangles(S *s) {
    a(s, 0x128) = s->privateWords[0] ? uint32_t(-22) : uint32_t(-15);
    a(s, 0x12c) = uint32_t(-45);
    a(s, 0x130) = s->privateWords[0] ? 15 : 22;
    a(s, 0x134) = 52;
    a(s, 0x118) = uint32_t(-16);
    a(s, 0x11c) = uint32_t(-52);
    a(s, 0x120) = 16;
    a(s, 0x124) = 60;
}
void falling(S *s, D d, void *c, uint32_t registryEntry) {
    auto &p = s->privateWords;
    if (p[15] == 8 || p[15] == 9 || p[15] == 10 || p[15] == 18)
        p[73] = effect(s, d, c, registryEntry, 0x5246dc);
    else {
        claw_player_cleanup_move(s, d, c);
        effect(s, d, c, 0x4c79e0, 0x5246dc, 0);
    }
    s->logicState = 25;
    a(s, 0xcc) = 4;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    a(s, 8) &= 0xffffffef;
    rectangles(s);
    p[16] = 0;
    s->physics.velocity[1] = 0;
    s->physics.acceleration[1] = 2250;
}
} // namespace
extern "C" void claw_player_update_climb(S *s, const ClawPlayerAirInput *input, D d, void *c) {
    auto &p = s->privateWords;
    uint32_t oldX = a(s, 0x4c), oldY = a(s, 0x50);
    if ((input->pressed & 1) && !(s->inputHeld & 0x4000000)) {
        claw_player_cleanup_move(s, d, c);
        s->logicState = 4;
        effect(s, d, c, 0x4c79e0, 0x5246a8, 0);
        a(s, 0xcc) = 3;
        a(s, 0x148) = 0;
        a(s, 0x14c) = 0;
        a(s, 8) &= 0xffffffef;
        rectangles(s);
        s->physics.velocity[1] = (s->powerup == 0x26bc || !p[69]) ? -500. : -425.;
        p[70] = 250;
        p[23] = 0;
        p[24] = a(s, 0x50);
        p[67] = 0;
        p[25] = a(s, 0x50) - 45;
        s->physics.acceleration[1] = 2250;
        s->physics.position[0] = static_cast<int32_t>(a(s, 0x4c));
        s->physics.position[1] = static_cast<int32_t>(a(s, 0x50));
        claw_physics_retarget(&s->physics, s->physics.position[0], static_cast<int32_t>(p[25]), 0);
        return;
    }
    if (!p[26]) {
        uint32_t top = oldY + a(s, 0x11c);
        if (effect(s, d, c, 0x4207f0, oldX, top) == 3)
            p[26] = 0;
        else {
            uint32_t height = a(s, 0x124) - a(s, 0x11c), y = top;
            for (;;) {
                if (static_cast<int32_t>(height) < 1) {
                    y = 0;
                    break;
                }
                --height;
                ++y;
                if (effect(s, d, c, 0x4207f0, a(s, 0x4c), y) == 3)
                    break;
            }
            p[26] = y;
        }
    }
    if (s->inputHeld & 0x4000000) {
        a(s, 0x14c) = s->powerup == 0x26bc ? uint32_t(-250) : uint32_t(-200);
        if (p[11] != 8) {
            p[11] = 8;
            effect(s, d, c, 0x4c79e0, 0x5246c4, 0);
        }
    } else if (s->inputHeld & 0x8000000) {
        a(s, 0x14c) = s->powerup == 0x26bc ? 250 : 200;
        if (p[11] != 2) {
            p[11] = 2;
            effect(s, d, c, 0x4c79e0, 0x5247a0, 0);
        }
    } else {
        if (p[11] != 5) {
            p[11] = 5;
            effect(s, d, c, 0x4c79e0, 0x524790, 0);
        }
        a(s, 0x14c) = 0;
    }
    s->physics.velocity[1] = static_cast<int32_t>(a(s, 0x14c));
    volatile double seconds = double(s->stageDelta) * .001;
    claw_physics_update(&s->physics, seconds);
    uint32_t y = oldY + claw_physics_pixel_y(&s->physics, &s->pixelScratchY);
    effect(s, d, c, 0x4cbb60, oldX, y, 0);
    bool advance = true;
    uint32_t edge = a(s, 0x124) - p[26] + a(s, 0x50);
    if (p[26] && static_cast<int32_t>(edge) >= 0 && static_cast<int32_t>(edge) < 121) {
        uint32_t image = edge < 17    ? 389
                         : edge < 34  ? 388
                         : edge < 51  ? 387
                         : edge < 68  ? 386
                         : edge < 85  ? 385
                         : edge < 102 ? 384
                                      : 383;
        effect(s, d, c, 0x4209d0, image);
        advance = false;
    }
    if (a(s, 0xcc) == 4) {
        falling(s, d, c, 0x4061b0);
        return;
    }
    if (a(s, 0xcc) == 1) {
        p[62] = 1000;
        claw_player_enter_stand(s, d, c);
        return;
    }
    if (advance)
        effect(s, d, c, 0x4c82a0, s->animationDelta);
}
extern "C" void claw_player_update_land(S *s, D d, void *c) {
    auto &p = s->privateWords;
    uint32_t x = a(s, 0x4c), y = a(s, 0x50);
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    if ((a(s, 8) & 0x10) && a(s, 0x80)) {
        x += effect(s, d, c, 0x158, a(s, 0x80));
        y += effect(s, d, c, 0x15c, a(s, 0x80));
    }
    effect(s, d, c, 0x4cbb60, x, y, 24);
    if (a(s, 0xcc) == 4) {
        falling(s, d, c, 0x4f6286);
        return;
    }
    if (a(s, 0xcc) == 6) {
        claw_player_cleanup_move(s, d, c);
        s->logicState = 27;
        effect(s, d, c, 0x4c79e0, 0x5246c4, 0);
        a(s, 0xcc) = 6;
        a(s, 0x148) = 0;
        a(s, 0x14c) = 0;
        a(s, 8) &= 0xffffffef;
        p[11] = 0;
        p[26] = 0;
        s->physics.acceleration[1] = 0;
        return;
    }
    effect(s, d, c, 0x4c82a0, s->animationDelta);
    if (a(s, 0x1a4) && !a(s, 0x19c)) {
        claw_player_cleanup_move(s, d, c);
        if (s->inputHeld & 0x2000000)
            claw_player_enter_walk_right(s, d, c);
        else if (s->inputHeld & 0x1000000)
            claw_player_enter_walk_left(s, d, c);
        else
            claw_player_enter_stand(s, d, c);
    }
}
