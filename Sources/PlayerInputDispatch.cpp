#include "PlayerInputDispatch.h"
#include "PlayerEngine.h"
#include <cstring>
#include <cmath>
namespace {
using S = ClawPlayerLocomotion;
using I = ClawPlayerInputContext;
using D = ClawPlayerLocomotionDependency;
uint32_t &a(S *s, uint32_t offset) {
    return s->actor[offset / 4];
}
uint32_t effect(S *s, D d, void *c, uint32_t entry, uint32_t x = 0, uint32_t y = 0, uint32_t z = 0) {
    return d ? d(s, entry, x, y, z, c) : 0;
}
double mul(double x, double y) {
    volatile double r = x * y;
    return r;
}
double sub(double x, double y) {
    volatile double r = x - y;
    return r;
}
double add(double x, double y) {
    volatile double r = x + y;
    return r;
}
double div(double x, double y) {
    volatile double r = x / y;
    return r;
}
uint32_t ftolLow(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    int e = int((bits >> 52) & 0x7ff) - 1023;
    if (e < 0 || e >= 63)
        return 0;
    uint64_t magnitude = (bits & 0x000fffffffffffffULL) | 0x0010000000000000ULL;
    magnitude = e >= 52 ? magnitude << (e - 52) : magnitude >> (52 - e);
    return bits >> 63 ? 0u - uint32_t(magnitude) : uint32_t(magnitude);
}
void face(S *s, bool right) {
    ClawPlayerBody body;
    body.renderFlags = a(s, 0x40);
    std::memcpy(&body.moveRect, &a(s, 0x118), 16);
    std::memcpy(&body.hitRect, &a(s, 0x128), 16);
    std::memcpy(&body.attackRect, &a(s, 0x138), 16);
    ClawPlayerDirection dir{s->privateWords[0], s->privateWords[69]};
    if (right)
        claw_player_face_right(&body, &dir);
    else
        claw_player_face_left(&body, &dir);
    a(s, 0x40) = body.renderFlags;
    s->privateWords[0] = dir.facing;
    s->privateWords[69] = dir.idleTimer;
    std::memcpy(&a(s, 0x118), &body.moveRect, 16);
    std::memcpy(&a(s, 0x128), &body.hitRect, 16);
    std::memcpy(&a(s, 0x138), &body.attackRect, 16);
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
void placeY(S *s, double target) {
    auto &p = s->physics;
    if (p.acceleration[1] != 0) {
        double square =
            sub(mul(p.velocity[1], p.velocity[1]), mul(mul(sub(target, p.position[1]), p.acceleration[1]), -2.));
        if (square < 0)
            square = 0;
        double velocity = std::sqrt(square);
        if (p.velocity[1] <= 0)
            velocity = -velocity;
        p.velocity[1] = velocity;
    }
    p.delta[1] = sub(p.delta[1], sub(p.position[1], target));
    p.position[1] = target;
}
void carry(S *s, D d, void *c, uint32_t &x, uint32_t &y) {
    if ((a(s, 8) & 0x10) && a(s, 0x80)) {
        x += effect(s, d, c, 0x158, a(s, 0x80));
        y += effect(s, d, c, 0x15c, a(s, 0x80));
    }
}
void inlineJump(S *s, D d, void *c) {
    auto &p = s->privateWords;
    effect(s, d, c, 0x41c4e0);
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
    uint32_t oldX = a(s, 0x4c), oldY = a(s, 0x50);
    effect(s, d, c, 0x41f4c0);
    if (s->inputHeld & 0x2000000) {
        face(s, true);
        a(s, 0x148) = 225;
    } else if (s->inputHeld & 0x1000000) {
        face(s, false);
        a(s, 0x148) = uint32_t(-225);
    } else
        a(s, 0x148) = 0;
    a(s, 0x148) += p[33];
    s->physics.velocity[0] = static_cast<int32_t>(a(s, 0x148));
    claw_physics_update(&s->physics, mul(double(s->stageDelta), .001));
    uint32_t x = oldX + claw_physics_pixel_x(&s->physics, &s->pixelScratch),
             y = oldY + claw_physics_pixel_y(&s->physics, &s->pixelScratchY);
    p[67] += s->stageDelta;
    if (s->physics.velocity[1] >= 0) {
        placeY(s, static_cast<int32_t>(p[25]));
        y = p[25];
    }
    if (static_cast<int32_t>(y) < static_cast<int32_t>(p[25]))
        y = p[25];
    uint32_t beforeY = a(s, 0x50);
    effect(s, d, c, 0x4cbb60, x, y, (s->inputHeld & 0x4000000) ? 17 : 0);
    p[23] += beforeY - a(s, 0x50);
    if (a(s, 0xcc) == 4)
        effect(s, d, c, 0x417930, 0);
    else if (a(s, 0xcc) == 6)
        effect(s, d, c, 0x4170f0);
    else {
        effect(s, d, c, p[1] ? 0x41c5a0 : 0x4c82a0, p[1] ? 0 : s->animationDelta);
        if (static_cast<int32_t>(a(s, 0x50)) <= static_cast<int32_t>(p[25]))
            effect(s, d, c, 0x417930, 1);
    }
}
void inlineWalk(S *s, D d, void *c, bool right) {
    auto &p = s->privateWords;
    effect(s, d, c, 0x41c4e0);
    s->logicState = right ? 8 : 9;
    face(s, right);
    effect(s, d, c, 0x4c79e0, 0x52469c, 0);
    a(s, 0xcc) = 2;
    a(s, 0x148) = right ? 225 : uint32_t(-225);
    a(s, 0x14c) = 0;
    p[62] = 0;
    for (auto &v : s->physics.remainder)
        v = 0;
    uint32_t oldX = a(s, 0x4c), y = a(s, 0x50), delta = right ? s->animationDelta : s->stageDelta;
    p[69] = delta < p[69] ? p[69] - delta : 0;
    a(s, 0x1b0) = 0x3f800000;
    int32_t speed = 225;
    if (s->powerup == 0x26bc) {
        speed = 300;
        a(s, 0x1b0) = 0x3f4ccccd;
    } else if (!p[69]) {
        speed = 285;
        a(s, 0x1b0) = 0x3f666666;
    }
    a(s, 0x148) = (right ? uint32_t(speed) : uint32_t(-speed)) + p[33];
    s->physics.velocity[0] = static_cast<int32_t>(a(s, 0x148));
    claw_physics_update(&s->physics, mul(double(s->stageDelta), .001));
    uint32_t x = oldX + claw_physics_pixel_x(&s->physics, &s->pixelScratch);
    carry(s, d, c, x, y);
    effect(s, d, c, 0x4cbb60, x, y, 8);
    if (a(s, 0xcc) == 1)
        effect(s, d, c, 0x4171d0);
    else if (a(s, 0xcc) == 4)
        effect(s, d, c, 0x417930, 0);
    else
        effect(s, d, c, 0x4c82a0, s->animationDelta);
}
void teeter(S *s, D d, void *c) {
    auto &p = s->privateWords;
    face(s, false);
    effect(s, d, c, 0x41c4e0);
    s->logicState = 5006;
    effect(s, d, c, 0x4c79e0, 0x524690, 1);
    a(s, 0xcc) = 1;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    p[69] = 1500;
    if (static_cast<int32_t>(effect(s, d, c, 0x4a3050)) % 100 < 45)
        effect(s, d, c, 0x48c8a0, 0x524684, 0);
    uint32_t options = (s->inputHeld & 0x4000000) ? 25 : (s->inputHeld & 0x8000000) ? 26 : 24;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    uint32_t x = a(s, 0x4c), y = a(s, 0x50);
    carry(s, d, c, x, y);
    effect(s, d, c, 0x4cbb60, x, y, options);
    if (a(s, 0xcc) == 4)
        effect(s, d, c, 0x417930, 0);
    else if (a(s, 0xcc) == 6)
        effect(s, d, c, 0x4170f0);
    else
        effect(s, d, c, 0x4c82a0, s->animationDelta);
    if (!effect(s, d, c, p[0] ? 0x41e710 : 0x41e790))
        effect(s, d, c, 0x4171d0);
}
void standing(S *s, I *i, D d, void *c) {
    auto &p = s->privateWords;
    bool allowed = !(p[1] && !p[8]);
    if (allowed && (i->pressed & 1)) {
        inlineJump(s, d, c);
        return;
    }
    if (allowed && (i->pressed & 0x2000000)) {
        inlineWalk(s, d, c, true);
        return;
    }
    if (allowed && (i->pressed & 0x1000000)) {
        inlineWalk(s, d, c, false);
        return;
    }
    uint32_t edge = 0;
    if (a(s, 8) & 0x10)
        edge = effect(s, d, c, 0x4bb030);
    else if (effect(s, d, c, 0x4cd1c0, a(s, 0x120))) {
        uint32_t left = a(s, 0x118), probe = a(s, 0x120) - 12;
        if (static_cast<int32_t>(left) < static_cast<int32_t>(probe)) {
            bool blocked = false;
            do {
                if (effect(s, d, c, 0x4cd1c0, probe)) {
                    blocked = true;
                    break;
                }
                probe -= 4;
            } while (static_cast<int32_t>(left) < static_cast<int32_t>(probe));
            if (!blocked)
                edge = effect(s, d, c, 0x4cd1c0, left) == 0;
        }
    }
    if (edge) {
        teeter(s, d, c);
        return;
    }
    if (!effect(s, d, c, 0x41e710)) {
        effect(s, d, c, 0x41d850);
        effect(s, d, c, 0x419030);
    } else {
        face(s, true);
        effect(s, d, c, 0x417480);
        effect(s, d, c, 0x419c80);
    }
}
} // namespace
extern "C" void claw_player_input_epilogue(S *s, I *i, D d, void *c) {
    auto &p = s->privateWords;
    if ((i->pressed & 8) && !p[1]) {
        p[12] += 1;
        if (static_cast<int32_t>(p[12]) > 3)
            p[12] = 1;
        effect(s, d, c, 0x420910, 0x524678);
    }
    if (i->invulnerabilityTimer) {
        if (s->stageDelta < i->invulnerabilityTimer)
            i->invulnerabilityTimer -= s->stageDelta;
        else {
            i->invulnerabilityTimer = 0;
            a(s, 0xd4) |= 0x1000004;
            a(s, 0x40) &= 0xfffffff7;
        }
    }
    p[62] = s->stageDelta < p[62] ? p[62] - s->stageDelta : 0;
    p[71] = s->stageDelta < p[71] ? p[71] - s->stageDelta : 0;
    effect(s, d, c, 0x41fc30, s->stageDelta);
    if (s->logicState != 5004) {
        uint32_t x = a(s, 0x4c), y = a(s, 0x50);
        if (static_cast<int32_t>(x) < static_cast<int32_t>(i->minimumX))
            x = i->minimumX;
        if (static_cast<int32_t>(i->maximumX) < static_cast<int32_t>(x))
            x = i->maximumX;
        if (static_cast<int32_t>(y) < static_cast<int32_t>(i->minimumY))
            y = i->minimumY;
        if (static_cast<int32_t>(i->maximumY) < static_cast<int32_t>(y))
            y = i->maximumY;
        a(s, 0x4c) = x;
        a(s, 0x50) = y;
    }
    uint32_t flags = a(s, 8);
    if (!i->ignoreHazards) {
        if (!(flags & 0x400000)) {
            if ((flags & 0x10) && effect(s, d, c, 0x4cd740, 0) == 4 && s->logicState != 5004 && s->logicState != 5005)
                effect(s, d, c, 0x417c50);
        } else {
            if (s->logicState != 5004 && s->logicState != 5005)
                effect(s, d, c, 0x417c50);
            a(s, 8) &= 0xffbfffff;
        }
    } else
        a(s, 8) &= 0xffbfffff;
    if (i->cheat) {
        a(s, 0x10c) = 100;
        p[28] = 99;
        p[29] = 99;
        p[30] = 99;
        p[31] = 10;
    }
}
extern "C" uint32_t claw_player_dispatch_input(S *s, I *i, D d, void *c) {
    uint32_t initial = s->logicState;
    switch (initial) {
    case 4:
        effect(s, d, c, 0x41d850);
        effect(s, d, c, 0x41b630);
        break;
    case 8:
    case 9:
        if (s->inputHeld & 0x8000000) {
            effect(s, d, c, 0x4171d0);
            effect(s, d, c, 0x419030);
        } else if (initial == 8) {
            if (s->inputHeld & 0x2000000)
                effect(s, d, c, 0x4183e0);
            else if (s->inputHeld & 0x1000000) {
                effect(s, d, c, 0x417dd0);
                effect(s, d, c, 0x418790);
            } else {
                effect(s, d, c, 0x4171d0);
                effect(s, d, c, 0x419030);
            }
        } else {
            if (s->inputHeld & 0x1000000)
                effect(s, d, c, 0x418790);
            else if (s->inputHeld & 0x2000000) {
                effect(s, d, c, 0x417f20);
                effect(s, d, c, 0x4183e0);
            } else {
                effect(s, d, c, 0x4171d0);
                effect(s, d, c, 0x419030);
            }
        }
        if (effect(s, d, c, 0x41d850))
            effect(s, d, c, 0x417380);
        else if (i->pressed & 1)
            effect(s, d, c, 0x417590);
        break;
    case 24:
        standing(s, i, d, c);
        break;
    case 25:
        effect(s, d, c, 0x41d850);
        effect(s, d, c, 0x418b40);
        break;
    case 26:
        effect(s, d, c, 0x41d850);
        effect(s, d, c, 0x419fd0);
        break;
    case 27:
        effect(s, d, c, 0x41bb70);
        break;
    case 5002:
        effect(s, d, c, 0x4198d0);
        break;
    case 5003:
        if (i->pressed & 1) {
            effect(s, d, c, 0x417590);
            effect(s, d, c, 0x41b630);
        } else
            effect(s, d, c, 0x41a490);
        break;
    case 5006:
        if (i->pressed & 1) {
            effect(s, d, c, 0x417590);
            effect(s, d, c, 0x41b630);
        } else if (s->inputHeld & 0x2000000) {
            effect(s, d, c, 0x417f20);
            effect(s, d, c, 0x4183e0);
        } else if (s->inputHeld & 0x1000000) {
            effect(s, d, c, 0x417dd0);
            effect(s, d, c, 0x418790);
        } else
            effect(s, d, c, 0x419c80);
        break;
    default:
        return 0;
    }
    claw_player_input_epilogue(s, i, d, c);
    return 1;
}
extern "C" void claw_player_update_jump_hold(S *s) {
    auto &w = s->privateWords;
    auto &p = s->physics;
    if (!(s->inputHeld & 1)) {
        w[70] = 0;
        return;
    }
    if (!w[70])
        return;
    w[70] = s->animationDelta < w[70] ? w[70] - s->animationDelta : 0;
    float factor;
    if (s->highJump) {
        a(s, 0x14c) = uint32_t(-750);
        factor = .78f;
    } else if (s->powerup == 0x26bc) {
        a(s, 0x14c) = uint32_t(-500);
        factor = .78f;
    } else if (!w[69]) {
        a(s, 0x14c) = uint32_t(-500);
        factor = .68f;
    } else {
        a(s, 0x14c) = uint32_t(-425);
        factor = .58f;
    }
    uint32_t target = ftolLow(sub(static_cast<int32_t>(w[24]), mul(double(uint32_t(250 - w[70])), double(factor))));
    if (static_cast<int32_t>(target) > static_cast<int32_t>(w[25]))
        target = w[25];
    w[25] = target;
    // Preserve the helper's inlined 53-bit operation order, which differs
    // from the general retarget routine when acceleration has several axes.
    double dy = sub(static_cast<int32_t>(target), p.position[1]), dz = -p.position[2];
    double dot = sub(sub(-mul(0., p.acceleration[0]), mul(dy, p.acceleration[1])), mul(dz, p.acceleration[2]));
    double square = add(add(mul(p.acceleration[2], p.acceleration[2]), mul(p.acceleration[1], p.acceleration[1])),
                        mul(p.acceleration[0], p.acceleration[0]));
    double distance = add(add(mul(dz, dz), mul(dy, dy)), mul(0., 0.));
    double speed = std::sqrt(mul(sub(std::sqrt(mul(mul(distance, square), 4.)), mul(dot, -2.)), .5));
    if (speed < .1) {
        p.velocity[0] = p.velocity[1] = p.velocity[2] = 0;
        return;
    }
    double quarter = mul(square, .25);
    if (quarter >= -.1 && quarter <= .1) {
        double length = add(add(std::abs(dz), std::abs(0.)), std::abs(dy));
        p.velocity[0] = mul(div(0., length), speed);
        p.velocity[1] = mul(div(dy, length), speed);
        p.velocity[2] = mul(div(dz, length), speed);
    } else {
        double durationSquared = div(sub(mul(speed, speed), dot), add(quarter, quarter)),
               duration = std::sqrt(durationSquared);
        p.velocity[0] = div(sub(0., mul(mul(durationSquared, p.acceleration[0]), .5)), duration);
        p.velocity[1] = div(sub(dy, mul(mul(durationSquared, p.acceleration[1]), .5)), duration);
        p.velocity[2] = div(sub(dz, mul(mul(durationSquared, p.acceleration[2]), .5)), duration);
    }
}
extern "C" uint32_t claw_player_left_ledge(S *s, D d, void *c) {
    if (a(s, 8) & 0x10)
        return 0;
    uint32_t left = a(s, 0x118), right = a(s, 0x120), probe = left + 12;
    if (!effect(s, d, c, 0x4cd1c0, left) || static_cast<int32_t>(right) <= static_cast<int32_t>(probe))
        return 0;
    do {
        if (effect(s, d, c, 0x4cd1c0, probe))
            return 0;
        probe += 4;
    } while (static_cast<int32_t>(probe) < static_cast<int32_t>(right));
    return effect(s, d, c, 0x4cd1c0, right) == 0;
}
extern "C" uint32_t claw_player_right_ledge(S *s, D d, void *c) {
    if (a(s, 8) & 0x10)
        return 0;
    uint32_t left = a(s, 0x118), right = a(s, 0x120), probe = right - 12;
    if (!effect(s, d, c, 0x4cd1c0, right) || static_cast<int32_t>(probe) <= static_cast<int32_t>(left))
        return 0;
    do {
        if (effect(s, d, c, 0x4cd1c0, probe))
            return 0;
        probe -= 4;
    } while (static_cast<int32_t>(left) < static_cast<int32_t>(probe));
    return effect(s, d, c, 0x4cd1c0, left) == 0;
}
extern "C" int32_t claw_player_enter_teeter(S *s, D d, void *c) {
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
    s->logicState = 5006;
    effect(s, d, c, 0x4c79e0, 0x524690, 1);
    a(s, 0xcc) = 1;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    p[69] = 1500;
    int32_t random = static_cast<int32_t>(effect(s, d, c, 0x4a3050));
    int32_t result = random / 100;
    if (random % 100 < 45)
        result = static_cast<int32_t>(effect(s, d, c, 0x48c8a0, 0x524684, 0));
    return result;
}
extern "C" void claw_player_update_powerup_timer(S *s, ClawPlayerPowerupContext *p, uint32_t delta, D d, void *c) {
    p->remaining = delta < p->remaining ? p->remaining - delta : 0;
    if (!p->remaining && s->powerup) {
        p->expired = 1;
        effect(s, d, c, 0x41f990, 0, 0);
        effect(s, d, c, 0x4bc110);
        return;
    }
    if (s->powerup == 0x26b7) {
        if (a(s, 0x174) && p->overlaySequenceToken)
            effect(s, d, c, 0x4c6130, p->overlaySequenceToken, 2, 0);
    } else if (s->powerup == 0x26bd) {
        effect(s, d, c, 0x420070, delta);
        a(s, 0xd4) &= 0xfeffffbb;
    }
}
