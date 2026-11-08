#include "PlayerStanding.h"
#include "PlayerEngine.h"
#include <cstring>
#include <initializer_list>

namespace {
using S = ClawPlayerLocomotion;
using D = ClawPlayerLocomotionDependency;
uint32_t &a(S *s, uint32_t offset) {
    return s->actor[offset / 4];
}
uint32_t effect(S *s, D d, void *c, uint32_t entry, uint32_t x = 0, uint32_t y = 0, uint32_t z = 0) {
    return d ? d(s, entry, x, y, z, c) : 0;
}
void moveRect(S *s) {
    a(s, 0x118) = uint32_t(-16);
    a(s, 0x11c) = uint32_t(-52);
    a(s, 0x120) = 16;
    a(s, 0x124) = 60;
}
void hitRect(S *s) {
    a(s, 0x128) = s->privateWords[0] ? uint32_t(-22) : uint32_t(-15);
    a(s, 0x12c) = uint32_t(-45);
    a(s, 0x130) = s->privateWords[0] ? 15 : 22;
    a(s, 0x134) = 52;
}
void mirror(S *s) {
    for (uint32_t offset : {0x118u, 0x128u, 0x138u})
        if (a(s, offset) != 0x80000000u) {
            uint32_t left = a(s, offset);
            a(s, offset) = 0u - a(s, offset + 8);
            a(s, offset + 8) = 0u - left;
        }
}
void face(S *s, bool right) {
    ClawPlayerBody body;
    body.renderFlags = a(s, 0x40);
    std::memcpy(&body.moveRect, &a(s, 0x118), 16);
    std::memcpy(&body.hitRect, &a(s, 0x128), 16);
    std::memcpy(&body.attackRect, &a(s, 0x138), 16);
    ClawPlayerDirection direction{s->privateWords[0], s->privateWords[69]};
    if (right)
        claw_player_face_right(&body, &direction);
    else
        claw_player_face_left(&body, &direction);
    a(s, 0x40) = body.renderFlags;
    s->privateWords[0] = direction.facing;
    s->privateWords[69] = direction.idleTimer;
    std::memcpy(&a(s, 0x118), &body.moveRect, 16);
    std::memcpy(&a(s, 0x128), &body.hitRect, 16);
    std::memcpy(&a(s, 0x138), &body.attackRect, 16);
}
void platform(S *s, D d, void *c, uint32_t &x, uint32_t &y) {
    if ((a(s, 8) & 0x10) && a(s, 0x80)) {
        x += effect(s, d, c, 0x158, a(s, 0x80));
        y += effect(s, d, c, 0x15c, a(s, 0x80));
    }
}
void fall(S *s, D d, void *c, bool edge) {
    auto &p = s->privateWords;
    if (p[15] == 8 || p[15] == 9 || p[15] == 10 || p[15] == 18)
        p[73] = effect(s, d, c, edge ? 0x4f6286 : 0x4061b0, 0x5246dc);
    else {
        claw_player_cleanup_move(s, d, c);
        effect(s, d, c, 0x4c79e0, 0x5246dc, 0);
    }
    s->logicState = 25;
    a(s, 0xcc) = 4;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    a(s, 8) &= 0xffffffef;
    hitRect(s);
    moveRect(s);
    p[16] = 0;
    s->physics.velocity[1] = 0;
    s->physics.acceleration[1] = 2250;
}
void climb(S *s, D d, void *c) {
    claw_player_cleanup_move(s, d, c);
    s->logicState = 27;
    effect(s, d, c, 0x4c79e0, 0x5246c4, 0);
    a(s, 0xcc) = 6;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    a(s, 8) &= 0xffffffef;
    s->privateWords[11] = 0;
    s->privateWords[26] = 0;
    s->physics.acceleration[1] = 0;
}
void lookUp(S *s, D d, void *c) {
    auto &p = s->privateWords;
    s->inputLatched &= 0xfcffffff;
    if (p[75]) {
        if (s->weaponLogicStatus > 0)
            s->weaponLogicCallback = 0x4207a0;
        if (!s->weaponDeleteCount)
            effect(s, d, c, 0x4dbd20, p[75], 0);
        else
            s->weaponDeleteFlags |= 1;
        p[75] = 0;
    }
    p[15] = 0;
    p[8] = 1;
    if (p[1]) {
        p[1] = 0;
        effect(s, d, c, 0x420a10, p[73], 0);
        a(s, 8) |= 0x80;
    }
    s->logicState = 5003;
    effect(s, d, c, 0x4c79e0, 0x524768, 0);
    a(s, 0xcc) = 1;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    p[68] = 250;
}
void restoreLiftRect(S *s) {
    for (uint32_t i = 0; i < 4; ++i)
        a(s, 0x118 + i * 4) = s->privateWords[54 + i];
}
void lift(S *s, D d, void *c, ClawPlayerStandingContext *extra) {
    auto &p = s->privateWords;
    uint32_t x = a(s, 0x4c), y = a(s, 0x50);
    if ((s->inputHeld & 0x1000000) && p[2]) {
        if (p[0])
            face(s, false);
        if (p[3] || s->physics.velocity[0] == 30.) {
            effect(s, d, c, 0x4c79e0, 0x524758, 0);
            s->physics.velocity[0] = -30.;
            p[3] = 0;
        }
    } else if ((s->inputHeld & 0x2000000) && p[2]) {
        if (!p[0])
            face(s, true);
        if (p[3] || s->physics.velocity[0] == -30.) {
            effect(s, d, c, 0x4c79e0, 0x524758, 0);
            s->physics.velocity[0] = 30.;
            p[3] = 0;
        }
    } else
        s->physics.velocity[0] = 0;
    if (effect(s, d, c, 0x4c82a0, s->animationDelta) != 1) {
        volatile double seconds = double(s->stageDelta) * .001;
        claw_physics_update(&s->physics, seconds);
        x += claw_physics_pixel_x(&s->physics, &s->pixelScratch);
    }
    platform(s, d, c, x, y);
    effect(s, d, c, 0x4cbb60, x, y, 24);
    if (a(s, 0xcc) != 4) {
        if ((a(s, 0x1a4) && !a(s, 0x19c) && !p[2]) || (p[2] && s->physics.velocity[0] == 0.)) {
            effect(s, d, c, 0x4c79e0, 0x52474c, 0);
            p[2] = 1;
            p[3] = 1;
        }
        if (p[2] && (extra->inputPressed & 0x22)) {
            restoreLiftRect(s);
            effect(s, d, c, 0x41b1f0);
        }
        if (s->animationDelta < p[60]) {
            p[60] -= s->animationDelta;
            return;
        }
        effect(s, d, c, 0x421010, p[75], 0x4207a0, 1);
        effect(s, d, c, 0x420fc0, p[75], 0);
        p[75] = 0;
        restoreLiftRect(s);
        claw_player_enter_stand(s, d, c);
        return;
    }
    effect(s, d, c, 0x421010, p[75], 0x4207a0, 1);
    extra->liftedWeaponVelocityX = s->physics.velocity[0] > 0 ? 225. : (s->physics.velocity[0] < 0 ? -225. : 0.);
    effect(s, d, c, 0x420fc0, p[75], 0);
    p[75] = 0;
    restoreLiftRect(s);
    effect(s, d, c, 0x417930, 0);
}
void idleSpeech(S *s, D d, void *c, ClawPlayerStandingContext *extra) {
    // Original 0x4a3050 executes this LCG in the CRT thread record.
    extra->randomState = extra->randomState * 214013u + 2531011u;
    uint32_t choice = ((extra->randomState >> 16) & 0x7fff) % 12;
    const uint32_t strings[12] = {0x524eb0, 0x524ea4, 0x524e98, 0x524e8c, 0x524e80, 0x524e70,
                                  0x524e60, 0x524e50, 0x524e40, 0x524e30, 0x524e20, 0x524e10};
    effect(s, d, c, 0x48c8a0, strings[choice], 0);
}
bool leftEdge(S *s, D d, void *c) {
    if (a(s, 8) & 0x10)
        return false;
    if (!effect(s, d, c, 0x4cd1c0, a(s, 0x120)))
        return false;
    uint32_t x = a(s, 0x120) - 12;
    if (int32_t(x) <= int32_t(a(s, 0x118)))
        return false;
    do {
        if (effect(s, d, c, 0x4cd1c0, x))
            return false;
        x -= 4;
    } while (int32_t(a(s, 0x118)) < int32_t(x));
    return effect(s, d, c, 0x4cd1c0, a(s, 0x118)) == 0;
}
} // namespace

extern "C" void claw_player_update_stand(S *s, D d, void *c, ClawPlayerStandingContext *extra) {
    auto &p = s->privateWords;
    if (s->logicState == 5000) {
        lift(s, d, c, extra);
        return;
    }
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    uint32_t options = 24;
    if (s->inputHeld & 0x4000000) {
        options = 25;
        p[72] = 15000;
    } else if (s->inputHeld & 0x8000000) {
        options = 26;
        p[72] = 15000;
    }
    uint32_t x = a(s, 0x4c), y = a(s, 0x50);
    if (p[33]) {
        for (double &v : s->physics.remainder)
            v = 0;
        s->physics.velocity[0] = int32_t(p[33]);
        volatile double seconds = double(s->stageDelta) * .001;
        claw_physics_update(&s->physics, seconds);
        x += claw_physics_pixel_x(&s->physics, &s->pixelScratch);
    }
    platform(s, d, c, x, y);
    effect(s, d, c, 0x4cbb60, x, y, options);
    uint32_t animationResult = 0;
    if (a(s, 0xcc) == 4)
        fall(s, d, c, false);
    else if (a(s, 0xcc) == 6)
        climb(s, d, c);
    else if (!p[1])
        animationResult = effect(s, d, c, 0x4c82a0, s->animationDelta);
    else
        effect(s, d, c, 0x41c5a0);
    if ((!p[1] || p[8]) && (s->inputHeld & 0x8000000) && a(s, 0xcc) == 1) {
        claw_player_cleanup_move(s, d, c);
        s->logicState = 26;
        effect(s, d, c, 0x4c79e0, 0x524740, 0);
        a(s, 0xcc) = 5;
        a(s, 0x148) = 0;
        a(s, 0x14c) = 0;
        a(s, 0x128) = uint32_t(-15);
        a(s, 0x12c) = 10;
        a(s, 0x130) = 22;
        a(s, 0x134) = 52;
        a(s, 0x118) = uint32_t(-16);
        a(s, 0x11c) = 10;
        a(s, 0x120) = 16;
        a(s, 0x124) = 60;
        if (!p[0])
            mirror(s);
        p[68] = 1000;
    } else if (!p[1] && !p[62] && (s->inputHeld & 0x4000000) && a(s, 0xcc) == 1) {
        p[63] = s->animationDelta < p[63] ? p[63] - s->animationDelta : 0;
        if (!p[63])
            lookUp(s, d, c);
    }
    if (p[72] && !p[1]) {
        p[72] = s->stageDelta < p[72] ? p[72] - s->stageDelta : 0;
        if (!p[72])
            effect(s, d, c, 0x4c79e0, 0x524734, 1);
    }
    if (animationResult == 99)
        idleSpeech(s, d, c, extra);
    if (a(s, 0x1a4) && !a(s, 0x19c)) {
        effect(s, d, c, 0x4c79e0, 0x5246d0, 1);
        p[72] = 15000;
    }
}

extern "C" void claw_player_update_stand_edge(S *s, D d, void *c) {
    auto &p = s->privateWords;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    uint32_t options = (s->inputHeld & 0x4000000) ? 25 : ((s->inputHeld & 0x8000000) ? 26 : 24);
    uint32_t x = a(s, 0x4c), y = a(s, 0x50);
    platform(s, d, c, x, y);
    effect(s, d, c, 0x4cbb60, x, y, options);
    if (a(s, 0xcc) == 4)
        fall(s, d, c, true);
    else if (a(s, 0xcc) == 6)
        climb(s, d, c);
    else
        effect(s, d, c, 0x4c82a0, s->animationDelta);
    if (!p[0]) {
        if (!leftEdge(s, d, c))
            claw_player_enter_stand(s, d, c);
        return;
    }
    uint32_t keep = 0;
    if (!(a(s, 8) & 0x10) && effect(s, d, c, 0x4cd1c0, a(s, 0x118))) {
        uint32_t probe = a(s, 0x118) + 12;
        if (int32_t(probe) < int32_t(a(s, 0x120))) {
            bool inside = false;
            do {
                if (effect(s, d, c, 0x4cd1c0, probe)) {
                    inside = true;
                    break;
                }
                probe += 4;
            } while (int32_t(probe) < int32_t(a(s, 0x120)));
            if (!inside)
                keep = effect(s, d, c, 0x4cd1c0, a(s, 0x120)) == 0;
        }
    }
    if (keep)
        return;
    claw_player_cleanup_move(s, d, c);
    s->logicState = 24;
    effect(s, d, c, 0x4c79e0, 0x5246d0, 1);
    a(s, 0xcc) = 1;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    a(s, 0x104) = 0;
    a(s, 8) |= 0x80;
    hitRect(s);
    moveRect(s);
    p[63] = 650;
    p[69] = 1500;
    p[72] = 15000;
    p[70] = 0;
    for (double &v : s->physics.remainder)
        v = 0;
    a(s, 0x1b0) = 0x3f800000;
}
