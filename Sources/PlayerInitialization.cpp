#include "PlayerInitialization.h"
#include "PlayerEngine.h"
#include <cstring>
#include <initializer_list>
namespace {
using S = ClawPlayerLocomotion;
using J = ClawPlayerInitializationContext;
using I = ClawPlayerInputContext;
using D = ClawPlayerLocomotionDependency;
uint32_t &a(S *s, uint32_t offset) {
    return s->actor[offset / 4];
}
uint32_t effect(S *s, D d, void *c, uint32_t entry, uint32_t x = 0, uint32_t y = 0, uint32_t z = 0) {
    return d ? d(s, entry, x, y, z, c) : 0;
}
void zOrder(S *s, uint32_t z) {
    if (a(s, 0x64) != z) {
        a(s, 0x64) = z;
        a(s, 8) |= 0x20000;
    }
}
void mirror(S *s) {
    for (uint32_t offset : {0x118u, 0x128u, 0x138u})
        if (a(s, offset) != 0x80000000) {
            uint32_t left = a(s, offset);
            a(s, offset) = 0 - a(s, offset + 8);
            a(s, offset + 8) = 0 - left;
        }
}
void faceRight(S *s) {
    ClawPlayerBody body;
    body.renderFlags = a(s, 0x40);
    std::memcpy(&body.moveRect, &a(s, 0x118), 16);
    std::memcpy(&body.hitRect, &a(s, 0x128), 16);
    std::memcpy(&body.attackRect, &a(s, 0x138), 16);
    ClawPlayerDirection direction{s->privateWords[0], s->privateWords[69]};
    claw_player_face_right(&body, &direction);
    a(s, 0x40) = body.renderFlags;
    s->privateWords[0] = direction.facing;
    s->privateWords[69] = direction.idleTimer;
    std::memcpy(&a(s, 0x118), &body.moveRect, 16);
    std::memcpy(&a(s, 0x128), &body.hitRect, 16);
    std::memcpy(&a(s, 0x138), &body.attackRect, 16);
}
void initialize(S *s, J *j, I *i, D d, void *c) {
    j->cachedX = j->cachedY = 0xffffffff;
    i->minimumX = i->minimumY = 50;
    i->maximumX = j->worldWidth - 50;
    i->maximumY = j->worldHeight - 50;
    if (!j->privateToken)
        j->privateToken = effect(s, d, c, 0x4f63ec, 0x138);
    j->powerupRemaining = 0;
    s->powerup = 0;
    std::memcpy(s->privateWords, j->defaults, sizeof(j->defaults));
    auto &p = s->privateWords;
    a(s, 0x10c) = p[18];
    a(s, 0xf8) = p[17];
    effect(s, d, c, 0x4c7900, 0x523734, 11);
    a(s, 0x4c) = j->startX;
    a(s, 0x50) = j->startY;
    zOrder(s, 4000);
    effect(s, d, c, 0x4c7fa0, 0x522e70);
    a(s, 8) = (a(s, 8) & 0xffffffef) | 0x80;
    a(s, 0xd0) = 2;
    a(s, 0xd4) = 0x1b50544;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    a(s, 0xf4) = 1;
    a(s, 0x80) = 0;
    a(s, 0x118) = uint32_t(-16);
    a(s, 0x11c) = uint32_t(-52);
    a(s, 0x120) = 16;
    a(s, 0x124) = 60;
    a(s, 0x128) = uint32_t(-25);
    a(s, 0x12c) = uint32_t(-45);
    a(s, 0x130) = 12;
    a(s, 0x134) = 52;
    a(s, 0x138) = uint32_t(-15);
    a(s, 0x13c) = uint32_t(-45);
    a(s, 0x140) = 22;
    a(s, 0x144) = 34;
    effect(s, d, c, 0x4cd800, 0);
    p[0] = 0;
    p[6] = 0;
    p[58] = 0;
    p[11] = 5;
    p[1] = 0;
    p[73] = 0;
    p[19] = a(s, 0x4c);
    p[20] = a(s, 0x50);
    p[68] = 0;
    p[76] = 0;
    p[77] = 0;
    p[75] = 0;
    p[73] = 0;
    p[74] = 0;
    p[33] = 0;
    p[71] = 0;
    if (!p[9])
        std::memset(p + 34, 0, 40);
    p[0] = 1;
    claw_player_enter_stand(s, d, c);
    mirror(s);
    p[0] = 0;
    faceRight(s);
    if (effect(s, d, c, 0x10, j->configurationToken) == 4)
        p[31] = 9;
    const double velocity[] = {0, 0, 0}, acceleration[] = {0, 2250, 0};
    claw_physics_initialize(&s->physics, velocity, acceleration, 0);
    s->physics.maximumDelta[0] = 32;
    s->physics.maximumDelta[1] = 32;
    claw_physics_limit_velocity(&s->physics, 1000);
    effect(s, d, c, 0x4bc110);
    if (!j->imageOffsetsAdjusted && a(s, 0x170)) {
        const uint32_t adjustments[] = {4, 8, 12, 16, 40, 54, 58};
        for (uint32_t index = 0; index < 7; ++index) {
            j->ladderImageTokens[index] = effect(s, d, c, 0x40f680, a(s, 0x170), 383 + index);
            if (j->ladderImageTokens[index])
                j->ladderImageWord24[index] += adjustments[index];
        }
    }
}
void respawn(S *s, J *j, I *i, D d, void *c) {
    auto &p = s->privateWords;
    j->cachedX = j->cachedY = 0xffffffff;
    p[18] = 100;
    a(s, 0x10c) = 100;
    uint32_t x = j->checkpointX, y = j->checkpointY;
    if (x == 0xffffffff || y == 0xffffffff) {
        x = p[19];
        y = p[20];
    }
    effect(s, d, c, 0x4c7900, 0x523734, 11);
    a(s, 0x50) = y;
    a(s, 0x4c) = x;
    zOrder(s, 4000);
    a(s, 0xd4) |= 0x1000004;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    a(s, 8) &= 0xffbffffa;
    a(s, 0x40) &= 0xfffffff6;
    effect(s, d, c, 0x4cd800, 0);
    claw_player_enter_stand(s, d, c);
    i->invulnerabilityTimer = 0;
    p[11] = 5;
    p[73] = 0;
    p[1] = 0;
    p[6] = 0;
    p[7] = 0;
    p[8] = 0;
    p[33] = 0;
    p[71] = 0;
    if (a(s, 0x4c) != p[19])
        effect(s, d, c, 0x420910, 0x5246b4);
    if (effect(s, d, c, 0x10, j->configurationToken) == 4)
        p[31] = 9;
    j->accumulator += j->accumulatorStep;
    if (j->accumulator < j->accumulatorMinimum)
        j->accumulator = j->accumulatorMinimum;
    effect(s, d, c, 0x4bc110);
    effect(s, d, c, 0x41f990, 0, 0);
    if (j->resetObjectToken)
        effect(s, d, c, 0xb0, j->resetObjectToken);
}
void epilogue(S *s, I *i, D d, void *c) {
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
} // namespace
extern "C" void claw_player_construct_defaults(S *s, J *j) {
    std::memset(j->defaults, 0, sizeof(j->defaults));
    j->defaults[30] = 3;
    j->defaults[31] = 3;
    j->accumulator = j->accumulatorMinimum;
    j->defaults[12] = 1;
    j->defaults[28] = 10;
    j->defaults[29] = 5;
    j->defaults[18] = 100;
    j->defaults[59] = 1000000;
    j->powerupRemaining = 0;
    s->powerup = 0;
    j->powerupAuxiliary = 0;
    if (j->difficulty) {
        j->defaults[28] = 50;
        j->defaults[29] = 40;
        j->defaults[30] = 20;
        j->defaults[31] = 9;
    }
}
extern "C" uint32_t claw_player_default_word(const J *j, uint32_t index) {
    return index < 78 ? j->defaults[index] : 0;
}
extern "C" void claw_player_set_default_word(J *j, uint32_t index, uint32_t value) {
    if (index < 78)
        j->defaults[index] = value;
}
extern "C" uint32_t claw_player_initialization_image_word(const J *j, uint32_t index) {
    return index < 7 ? j->ladderImageWord24[index] : 0;
}
extern "C" void claw_player_set_initialization_image_word(J *j, uint32_t index, uint32_t token, uint32_t value) {
    if (index < 7) {
        j->ladderImageTokens[index] = token;
        j->ladderImageWord24[index] = value;
    }
}
extern "C" uint32_t claw_player_dispatch_initialization(S *s, J *j, I *i, D d, void *c) {
    if (s->logicState == 0)
        initialize(s, j, i, d, c);
    else if (s->logicState == 23)
        respawn(s, j, i, d, c);
    else
        return 0;
    epilogue(s, i, d, c);
    return 1;
}
