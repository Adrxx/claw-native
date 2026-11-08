#include "PlayerPoseStates.h"
#include "PlayerEngine.h"
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
void hitRect(S *s) {
    a(s, 0x128) = s->privateWords[0] ? uint32_t(-22) : uint32_t(-15);
    a(s, 0x12c) = uint32_t(-45);
    a(s, 0x130) = s->privateWords[0] ? 15 : 22;
    a(s, 0x134) = 52;
}
void moveRect(S *s) {
    a(s, 0x118) = uint32_t(-16);
    a(s, 0x11c) = uint32_t(-52);
    a(s, 0x120) = 16;
    a(s, 0x124) = 60;
}
void face(S *s, bool right) {
    ClawPlayerBody b;
    b.renderFlags = a(s, 0x40);
    std::memcpy(&b.moveRect, &a(s, 0x118), 16);
    std::memcpy(&b.hitRect, &a(s, 0x128), 16);
    std::memcpy(&b.attackRect, &a(s, 0x138), 16);
    ClawPlayerDirection direction{s->privateWords[0], s->privateWords[69]};
    if (right)
        claw_player_face_right(&b, &direction);
    else
        claw_player_face_left(&b, &direction);
    a(s, 0x40) = b.renderFlags;
    s->privateWords[0] = direction.facing;
    s->privateWords[69] = direction.idleTimer;
    std::memcpy(&a(s, 0x118), &b.moveRect, 16);
    std::memcpy(&a(s, 0x128), &b.hitRect, 16);
    std::memcpy(&a(s, 0x138), &b.attackRect, 16);
}
void preMove(S *s, D d, void *c, bool zeroSpeed) {
    auto &p = s->privateWords;
    p[68] = s->animationDelta < p[68] ? p[68] - s->animationDelta : 0;
    uint32_t x = a(s, 0x4c), y = a(s, 0x50);
    if (zeroSpeed) {
        a(s, 0x148) = 0;
        a(s, 0x14c) = 0;
    }
    if ((a(s, 8) & 0x10) && a(s, 0x80)) {
        x += effect(s, d, c, 0x158, a(s, 0x80));
        y += effect(s, d, c, 0x15c, a(s, 0x80));
    }
    if (p[33]) {
        for (auto &v : s->physics.remainder)
            v = 0;
        s->physics.velocity[0] = int32_t(p[33]);
        volatile double seconds = double(s->stageDelta) * .001;
        claw_physics_update(&s->physics, seconds);
        x += claw_physics_pixel_x(&s->physics, &s->pixelScratch);
    }
    effect(s, d, c, 0x4cbb60, x, y, 8);
}
void fall(S *s, D d, void *c) {
    auto &p = s->privateWords;
    if (p[15] == 8 || p[15] == 9 || p[15] == 10 || p[15] == 18)
        p[73] = effect(s, d, c, 0x4f6286, 0x5246dc);
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
void lookupExit(S *s, D d, void *c) {
    auto &p = s->privateWords;
    s->inputLatched &= 0xfcffffff;
    if (p[75]) {
        effect(s, d, c, 0x421010, p[75], 0x4207a0, 1);
        effect(s, d, c, 0x420fc0, p[75], 0);
        p[75] = 0;
    }
    p[15] = 0;
    p[8] = 1;
    if (p[1]) {
        p[1] = 0;
        effect(s, d, c, 0x420a10, p[73], 0);
        a(s, 8) |= 0x80;
    }
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
    for (auto &v : s->physics.remainder)
        v = 0;
    a(s, 0x1b0) = 0x3f800000;
}
void duckAttack(S *s, D d, void *c, uint32_t pressed) {
    auto &p = s->privateWords;
    uint32_t marker = effect(s, d, c, 0x4c82a0, s->animationDelta);
    if (a(s, 0x1a4) && !a(s, 0x19c)) {
        claw_player_cleanup_move(s, d, c);
        return;
    }
    if (p[7])
        p[8] = 1;
    a(s, 8) |= 0x80;
    switch (marker) {
    case 1:
        a(s, 8) &= 0xffffff7f;
        p[7] = 1;
        break;
    case 2:
        p[7] = 1;
        if (!p[4]) {
            p[4] = 1;
            if (p[12] == 1)
                effect(s, d, c, 0x41c9f0);
            else if (p[12] == 2)
                effect(s, d, c, 0x41cab0);
            else if (p[12] == 3)
                effect(s, d, c, 0x41cb80);
        }
        break;
    case 3:
        if (((pressed & 4) || (p[12] == 1 && (pressed & 0x40)) || (p[12] == 2 && (pressed & 0x80))) &&
            (p[12] != 1 || int32_t(p[28]) > 0)) {
            ++p[58];
            p[4] = 0;
            effect(s, d, c, 0x420970, p[27]);
        }
        break;
    case 4:
        if (!(s->inputHeld & 0x104)) {
            p[64] = p[65] < p[64] ? p[64] : p[65];
            effect(s, d, c, 0x420a10, p[74], 0);
        } else {
            p[64] += s->stageDelta;
            if (p[66] <= p[64]) {
                p[64] = p[66];
                effect(s, d, c, 0x420a10, p[74], 0);
            }
        }
        break;
    case 5:
        p[7] = 1;
        effect(s, d, c, 0x41cc60);
        break;
    }
}
} // namespace
extern "C" void claw_player_update_duck(S *s, D d, void *c, const ClawPlayerPoseContext *pose) {
    preMove(s, d, c, true);
    auto &p = s->privateWords;
    if (a(s, 0xcc) == 4)
        fall(s, d, c);
    else if (!p[1])
        effect(s, d, c, 0x4c82a0, s->animationDelta);
    else
        duckAttack(s, d, c, pose->inputPressed);
    bool canChange = !p[1] || p[8];
    if (canChange && !(s->inputHeld & 0x8000000) && a(s, 0xcc) == 5) {
        claw_player_enter_stand(s, d, c);
        return;
    }
    if (canChange) {
        if (p[0] && (s->inputHeld & 0x1000000)) {
            face(s, false);
            return;
        }
        if (!p[0] && (s->inputHeld & 0x2000000))
            face(s, true);
    }
}
extern "C" void claw_player_update_lookup(S *s, D d, void *c) {
    preMove(s, d, c, false);
    if (a(s, 0xcc) == 4)
        fall(s, d, c);
    else
        effect(s, d, c, 0x4c82a0, s->animationDelta);
    if (!(s->inputHeld & 0x4000000) && a(s, 0xcc) == 1)
        lookupExit(s, d, c);
}
