#include "PlayerLocomotion.h"
#include "PlayerEngine.h"
#include <cstring>
#include <cmath>

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
void cleanup(S *s, D d, void *c, bool useTransition, bool walkRestore) {
    s->inputLatched &= 0xfcffffff;
    auto &p = s->privateWords;
    if (p[75]) {
        if (useTransition)
            effect(s, d, c, 0x421010, p[75], 0x4207a0, 1);
        else if (s->weaponLogicStatus > 0)
            s->weaponLogicCallback = 0x4207a0;
        effect(s, d, c, 0x420fc0, p[75], 0, 0);
        p[75] = 0;
    }
    p[15] = 0;
    p[8] = 1;
    if (p[1]) {
        p[1] = 0;
        effect(s, d, c, walkRestore ? 0x4c8220 : 0x420a10, p[73], 0, 0);
        a(s, 8) |= 0x80;
    }
}
void standFields(S *s, D d, void *c) {
    auto &p = s->privateWords;
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
    for (auto &x : s->physics.remainder)
        x = 0;
    a(s, 0x1b0) = 0x3f800000;
}
void face(S *s, bool right) {
    ClawPlayerBody b;
    b.renderFlags = a(s, 0x40);
    std::memcpy(&b.moveRect, &a(s, 0x118), 16);
    std::memcpy(&b.hitRect, &a(s, 0x128), 16);
    std::memcpy(&b.attackRect, &a(s, 0x138), 16);
    ClawPlayerDirection p{s->privateWords[0], s->privateWords[69]};
    if (right)
        claw_player_face_right(&b, &p);
    else
        claw_player_face_left(&b, &p);
    a(s, 0x40) = b.renderFlags;
    s->privateWords[0] = p.facing;
    s->privateWords[69] = p.idleTimer;
    std::memcpy(&a(s, 0x118), &b.moveRect, 16);
    std::memcpy(&a(s, 0x128), &b.hitRect, 16);
    std::memcpy(&a(s, 0x138), &b.attackRect, 16);
}
void walkEntry(S *s, D d, void *c, bool right) {
    cleanup(s, d, c, false, true);
    s->logicState = right ? 8 : 9;
    face(s, right);
    effect(s, d, c, 0x4c79e0, 0x52469c, 0);
    a(s, 0xcc) = 2;
    a(s, 0x148) = right ? 225 : uint32_t(-225);
    a(s, 0x14c) = 0;
    s->privateWords[62] = 0;
    for (auto &x : s->physics.remainder)
        x = 0;
}
void walking(S *s, D d, void *c, bool right) {
    auto &p = s->privateWords;
    uint32_t timerDelta = right ? s->animationDelta : s->stageDelta;
    p[69] = timerDelta < p[69] ? p[69] - timerDelta : 0;
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
    volatile double seconds = static_cast<double>(s->stageDelta) * 0.001;
    claw_physics_update(&s->physics, seconds);
    uint32_t x = a(s, 0x4c) + claw_physics_pixel_x(&s->physics, &s->pixelScratch), y = a(s, 0x50);
    // The adapter supplies platform delta through this dependency when needed.
    if ((a(s, 8) & 0x10) && a(s, 0x80)) {
        x += effect(s, d, c, 0x158, a(s, 0x80));
        y += effect(s, d, c, 0x15c, a(s, 0x80));
    }
    effect(s, d, c, 0x4cbb60, x, y, 8);
    if (a(s, 0xcc) == 1) {
        cleanup(s, d, c, true, false);
        standFields(s, d, c);
        return;
    }
    if (a(s, 0xcc) != 4) {
        effect(s, d, c, 0x4c82a0, s->animationDelta);
        return;
    }
    if (p[15] == 8 || p[15] == 9 || p[15] == 10 || p[15] == 18) {
        p[73] = effect(s, d, c, 0x4f6286, 0x5246dc);
    } else {
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
double add(double x, double y) {
    volatile double r = x + y;
    return r;
}
double sub(double x, double y) {
    volatile double r = x - y;
    return r;
}
double mul(double x, double y) {
    volatile double r = x * y;
    return r;
}
double div(double x, double y) {
    volatile double r = x / y;
    return r;
}
void jumpRetarget(S *s) {
    // This inlined version adds the constant y acceleration square last,
    // unlike 0x420dd0. Reordering changes some velocities by one ULP.
    auto &p = s->physics;
    double dy = sub(static_cast<int32_t>(s->privateWords[25]), p.position[1]), dz = -p.position[2];
    double square =
        sub(add(mul(p.acceleration[2], p.acceleration[2]), mul(p.acceleration[0], p.acceleration[0])), -5062500.);
    double dot = sub(sub(-mul(0., p.acceleration[0]), mul(dy, 2250.)), mul(dz, p.acceleration[2]));
    double distance = add(add(mul(dz, dz), mul(dy, dy)), mul(0., 0.));
    double speed = std::sqrt(mul(sub(std::sqrt(mul(mul(distance, square), 4.)), mul(dot, -2.)), .5));
    if (speed < .1) {
        p.velocity[0] = p.velocity[1] = p.velocity[2] = 0;
        return;
    }
    double quarter = mul(square, .25);
    if (quarter >= -.1 && quarter <= .1) {
        double length = add(add(std::abs(dy), std::abs(dz)), std::abs(0.));
        p.velocity[0] = mul(div(0., length), speed);
        p.velocity[1] = mul(div(dy, length), speed);
        p.velocity[2] = mul(div(dz, length), speed);
    } else {
        double durationSquared = div(sub(mul(speed, speed), dot), add(quarter, quarter));
        double duration = std::sqrt(durationSquared);
        p.velocity[0] = div(sub(0., mul(mul(durationSquared, p.acceleration[0]), .5)), duration);
        p.velocity[1] = div(sub(dy, mul(durationSquared, 1125.)), duration);
        p.velocity[2] = div(sub(dz, mul(mul(durationSquared, p.acceleration[2]), .5)), duration);
    }
}
void airDirection(S *s) {
    if (s->inputHeld & 0x2000000) {
        face(s, true);
        a(s, 0x148) = 225;
    } else if (s->inputHeld & 0x1000000) {
        face(s, false);
        a(s, 0x148) = uint32_t(-225);
    } else
        a(s, 0x148) = 0;
}
void climbEntry(S *s, D d, void *c) {
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
uint32_t ftolLow(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    int exponent = int((bits >> 52) & 0x7ff) - 1023;
    if (exponent < 0 || exponent >= 63)
        return 0;
    uint64_t magnitude = (bits & 0x000fffffffffffffULL) | 0x0010000000000000ULL;
    magnitude = exponent >= 52 ? magnitude << (exponent - 52) : magnitude >> (52 - exponent);
    return bits >> 63 ? 0u - uint32_t(magnitude) : uint32_t(magnitude);
}
} // namespace
extern "C" {
uint32_t claw_player_actor_word(const S *s, uint32_t offset) {
    return offset < 512 && !(offset & 3) ? s->actor[offset / 4] : 0;
}
void claw_player_set_actor_word(S *s, uint32_t offset, uint32_t value) {
    if (offset < 512 && !(offset & 3))
        s->actor[offset / 4] = value;
}
uint32_t claw_player_private_word(const S *s, uint32_t i) {
    return i < 78 ? s->privateWords[i] : 0;
}
void claw_player_set_private_word(S *s, uint32_t i, uint32_t v) {
    if (i < 78)
        s->privateWords[i] = v;
}
uint32_t claw_player_enter_stand(S *s, D d, void *c) {
    cleanup(s, d, c, false, false);
    standFields(s, d, c);
    return s->privateWords[0];
}
void claw_player_enter_walk_left(S *s, D d, void *c) {
    walkEntry(s, d, c, false);
}
void claw_player_enter_walk_right(S *s, D d, void *c) {
    walkEntry(s, d, c, true);
}
void claw_player_enter_jump(S *s, D d, void *c) {
    cleanup(s, d, c, true, false);
    s->logicState = 4;
    effect(s, d, c, 0x4c79e0, 0x5246a8, 0);
    a(s, 0xcc) = 3;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    a(s, 8) &= 0xffffffef;
    hitRect(s);
    moveRect(s);
    s->physics.acceleration[1] = 2250;
    auto &p = s->privateWords;
    p[70] = 250;
    p[23] = 0;
    p[24] = a(s, 0x50);
    p[67] = 0;
    p[25] = a(s, 0x50) - 45;
    s->physics.position[0] = static_cast<int32_t>(a(s, 0x4c));
    s->physics.position[1] = static_cast<int32_t>(a(s, 0x50));
    jumpRetarget(s);
}
void claw_player_cleanup_move(S *s, D d, void *c) {
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
        effect(s, d, c, 0x4c8220, p[73]);
        a(s, 8) |= 0x80;
    }
}
void claw_player_enter_fall(S *s, uint32_t skipAnimation, D d, void *c) {
    auto &p = s->privateWords;
    if (p[15] == 8 || p[15] == 9 || p[15] == 10 || p[15] == 18)
        p[73] = effect(s, d, c, 0x4f6286, 0x5246dc);
    else {
        cleanup(s, d, c, false, false);
        if (!skipAnimation)
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
void claw_player_update_fall(S *s, D d, void *c) {
    auto &p = s->privateWords;
    uint32_t oldX = a(s, 0x4c), oldY = a(s, 0x50);
    airDirection(s);
    s->physics.velocity[0] = static_cast<int32_t>(a(s, 0x148));
    claw_physics_update(&s->physics, mul(double(s->stageDelta), .001));
    uint32_t x = oldX + claw_physics_pixel_x(&s->physics, &s->pixelScratch);
    uint32_t y = oldY + claw_physics_pixel_y(&s->physics, &s->pixelScratchY);
    uint32_t options = (s->inputHeld & 0x4000000) ? 25 : 24;
    effect(s, d, c, 0x4cbb60, x, y, options);
    p[16] += a(s, 0x50) - oldY;
    if (a(s, 0xcc) == 1) {
        if (!s->audioRegistryDisabled) {
            uint32_t token = effect(s, d, c, 0x4f6286, 0x524724);
            if (token)
                effect(s, d, c, 0x4208e0, token, s->audioPosition, 0);
        }
        claw_player_cleanup_move(s, d, c);
        if (static_cast<int32_t>(p[16]) >= 1000) {
            s->logicState = 5002;
            effect(s, d, c, 0x4c79e0, 0x524718, 1);
            a(s, 0xcc) = 1;
            a(s, 0x148) = 0;
            a(s, 0x14c) = 0;
            p[69] = 1500;
            return;
        }
        if (!(s->inputHeld & 0x3000000)) {
            standFields(s, d, c);
            return;
        }
        bool right = s->inputHeld & 0x2000000;
        s->logicState = right ? 8 : 9;
        face(s, right);
        effect(s, d, c, 0x4c79e0, 0x52469c, 0);
        a(s, 0xcc) = 2;
        a(s, 0x148) = right ? 225 : uint32_t(-225);
        a(s, 0x14c) = 0;
        p[62] = 0;
        for (auto &v : s->physics.remainder)
            v = 0;
        return;
    }
    if (a(s, 0xcc) == 6) {
        climbEntry(s, d, c);
        return;
    }
    if (p[1]) {
        effect(s, d, c, 0x41c5a0);
        return;
    }
    effect(s, d, c, 0x4c82a0, s->animationDelta);
    if (static_cast<int32_t>(p[16]) > 600)
        effect(s, d, c, 0x4209d0, 401);
}
void claw_player_update_jump(S *s, D d, void *c) {
    auto &p = s->privateWords;
    uint32_t oldX = a(s, 0x4c), oldY = a(s, 0x50);
    if (!(s->inputHeld & 1))
        p[70] = 0;
    else if (p[70]) {
        p[70] = s->animationDelta < p[70] ? p[70] - s->animationDelta : 0;
        float factor;
        if (s->highJump) {
            a(s, 0x14c) = uint32_t(-750);
            factor = .78f;
        } else if (s->powerup == 0x26bc) {
            a(s, 0x14c) = uint32_t(-500);
            factor = .78f;
        } else if (!p[69]) {
            a(s, 0x14c) = uint32_t(-500);
            factor = .68f;
        } else {
            a(s, 0x14c) = uint32_t(-425);
            factor = .58f;
        }
        uint32_t target = ftolLow(sub(static_cast<int32_t>(p[24]), mul(double(uint32_t(250 - p[70])), double(factor))));
        if (static_cast<int32_t>(p[25]) < static_cast<int32_t>(target))
            target = p[25];
        p[25] = target;
        claw_physics_retarget(&s->physics, s->physics.position[0], static_cast<int32_t>(p[25]), 0);
    }
    airDirection(s);
    a(s, 0x148) += p[33];
    s->physics.velocity[0] = static_cast<int32_t>(a(s, 0x148));
    claw_physics_update(&s->physics, mul(double(s->stageDelta), .001));
    uint32_t x = oldX + claw_physics_pixel_x(&s->physics, &s->pixelScratch);
    uint32_t y = oldY + claw_physics_pixel_y(&s->physics, &s->pixelScratchY);
    p[67] += s->stageDelta;
    if (s->physics.velocity[1] >= 0) {
        double target = static_cast<int32_t>(p[25]);
        if (s->physics.acceleration[1] != 0) {
            double square = sub(mul(s->physics.velocity[1], s->physics.velocity[1]),
                                mul(mul(sub(target, s->physics.position[1]), s->physics.acceleration[1]), -2.));
            if (square < 0)
                square = 0;
            double velocity = std::sqrt(square);
            if (s->physics.velocity[1] <= 0)
                velocity = -velocity;
            s->physics.velocity[1] = velocity;
        }
        s->physics.delta[1] = sub(s->physics.delta[1], sub(s->physics.position[1], target));
        s->physics.position[1] = target;
        y = p[25];
    }
    if (static_cast<int32_t>(y) < static_cast<int32_t>(p[25]))
        y = p[25];
    effect(s, d, c, 0x4cbb60, x, y, (s->inputHeld & 0x4000000) ? 17 : 0);
    p[23] += oldY - a(s, 0x50);
    if (a(s, 0xcc) == 6) {
        climbEntry(s, d, c);
        return;
    }
    if (a(s, 0xcc) != 4) {
        effect(s, d, c, p[1] ? 0x41c5a0 : 0x4c82a0, p[1] ? 0 : s->animationDelta);
        if (static_cast<int32_t>(a(s, 0x50)) <= static_cast<int32_t>(p[25]))
            claw_player_enter_fall(s, 1, d, c);
        return;
    }
    if (p[15] == 8 || p[15] == 9 || p[15] == 10 || p[15] == 18)
        p[73] = effect(s, d, c, 0x4061b0, 0x5246dc);
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
void claw_player_update_walk_right(S *s, D d, void *c) {
    walking(s, d, c, true);
}
void claw_player_update_walk_left(S *s, D d, void *c) {
    walking(s, d, c, false);
}
}
