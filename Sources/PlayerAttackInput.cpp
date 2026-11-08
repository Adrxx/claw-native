#include "PlayerAttackInput.h"
#include <algorithm>
#include <cstring>
namespace {
using S = ClawPlayerLocomotion;
using T = ClawPlayerAttackContext;
using D = ClawPlayerLocomotionDependency;
uint32_t &a(S *s, uint32_t offset) {
    return s->actor[offset / 4];
}
uint32_t effect(S *s, D d, void *c, uint32_t entry, uint32_t x = 0, uint32_t y = 0, uint32_t z = 0) {
    return d ? d(s, entry, x, y, z, c) : 0;
}
void restore(S *s, D d, void *c, bool transition, bool deletion = false) {
    auto &p = s->privateWords;
    s->inputLatched &= 0xfcffffff;
    if (p[75]) {
        if (transition)
            effect(s, d, c, 0x421010, p[75], 0x4207a0, 1);
        else if (s->weaponLogicStatus > 0)
            s->weaponLogicCallback = 0x4207a0;
        if (deletion) {
            if (!s->weaponDeleteCount)
                effect(s, d, c, 0x4dbd20, p[75], 0);
            else
                s->weaponDeleteFlags |= 1;
        } else
            effect(s, d, c, 0x420fc0, p[75], 0);
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
void projectile(S *s, T *t, D d, void *c) {
    auto &p = s->privateWords;
    uint32_t weapon = p[12];
    if (weapon < 1 || weapon > 3)
        return;
    uint32_t speed = p[0] ? 700 : uint32_t(-700);
    if (weapon == 3) {
        uint32_t denominator = p[66] - p[65];
        if (!denominator)
            denominator = 1;
        int64_t quotient = int64_t(int32_t((p[64] - p[65]) * 200)) / int32_t(denominator);
        // Original signed idiv has a trap for INT_MIN/-1; this mathematical
        // quotient is bounded only for inputs on which the original returns.
        int32_t charge = std::min<int64_t>(200, std::max<int64_t>(0, quotient));
        speed = p[0] ? uint32_t(charge) : uint32_t(-charge);
    }
    t->spawnX = a(s, 0x4c) + (p[0] ? p[21] : 0 - p[21]);
    t->spawnY = a(s, 0x50) + p[22];
    t->spawnZ = a(s, 0x64) + (weapon == 1 ? uint32_t(-1) : 1);
    t->spawnName = weapon == 1 ? 0x522dc8 : weapon == 2 ? 0x522e00 : 0x522bec;
    t->spawnFlags = 0x40000;
    t->projectileToken = effect(s, d, c, 0x4c8da0, t->spawnName, t->spawnX, t->spawnY);
    if (!t->projectileToken)
        return;
    auto &b = t->projectileActor;
    b[0xd0 / 4] = weapon == 2 ? 0x2000000 : 0x20;
    b[0xd4 / 4] = 4;
    if (weapon == 3) {
        --p[30];
        b[0x158 / 4] = speed;
        b[0x104 / 4] = 15;
        return;
    }
    b[0x148 / 4] = speed;
    b[0x14c / 4] = 0;
    if (weapon == 1) {
        t->projectileLogicRepeat = p[58];
        if (int32_t(p[28]) > 0)
            --p[28];
        b[0x104 / 4] = 8;
        effect(s, d, c, 0x4c7970, t->projectileToken, 0x524130);
    } else {
        if (int32_t(p[29]) > 0)
            --p[29];
        b[0x164 / 4] |= 8;
        b[0x104 / 4] = 25;
        t->projectileLogicRepeat = p[58];
        if (!p[0])
            b[0x40 / 4] |= 2;
    }
}
} // namespace
extern "C" int32_t claw_player_nearest_attack_target(S *s, T *t, const ClawPlayerAttackCandidate *candidates,
                                                     uint32_t count) {
    int32_t distance = 999999;
    t->targetToken = 0;
    for (uint32_t i = 0; i < count; ++i) {
        const auto &b = candidates[i].actor;
        if (b[0xd0 / 4] != 4 && b[0xd0 / 4] != 0x200)
            continue;
        uint32_t dy = b[0x50 / 4] - a(s, 0x50), sign = uint32_t(int32_t(dy) >> 31);
        if (int32_t((dy ^ sign) - sign) >= 100)
            continue;
        uint32_t allowance = (b[0x164 / 4] & 0x400) ? 0 : 48, edge, gap;
        if (!s->privateWords[0]) {
            edge = b[0x130 / 4] + b[0x4c / 4] - allowance;
            if (int32_t(edge) >= int32_t(a(s, 0x4c)))
                continue;
            gap = a(s, 0x128) + a(s, 0x4c) - edge;
        } else {
            edge = b[0x128 / 4] + b[0x4c / 4] + allowance;
            if (int32_t(a(s, 0x4c)) >= int32_t(edge))
                continue;
            gap = edge - a(s, 0x130) - a(s, 0x4c);
        }
        if (int32_t(gap) < distance) {
            distance = int32_t(gap);
            t->targetToken = candidates[i].token;
            std::memcpy(t->targetActor, b, sizeof(t->targetActor));
        }
    }
    return distance;
}
extern "C" uint32_t claw_player_attack_random_range(S *s, uint32_t lower, uint32_t upper, D d, void *c) {
    uint32_t span = upper - lower + 1, random = effect(s, d, c, 0x4a3050);
    if (!span)
        return (random & 1) ? lower : upper;
    int64_t remainder = int64_t(int32_t(random)) % int32_t(span);
    return lower + uint32_t(remainder);
}
extern "C" uint32_t claw_player_can_lift(S *s, const T *t) {
    const auto &b = t->targetActor;
    auto &p = s->privateWords;
    if (!(b[0x164 / 4] & 1) || p[1])
        return 0;
    uint32_t allowance = (b[0x164 / 4] & 0x400) ? 0 : 20;
    if (a(s, 0xcc) != 1 && a(s, 0xcc) != 2)
        return 0;
    if (int32_t(a(s, 0x4c) + allowance) < int32_t(b[0x4c / 4]) && !p[0])
        return 0;
    if (int32_t(b[0x4c / 4]) < int32_t(a(s, 0x4c) - allowance) && p[0])
        return 0;
    uint32_t vertical = a(s, 0x124) - b[0x50 / 4] - b[0x124 / 4] + a(s, 0x50);
    uint32_t sign = uint32_t(int32_t(vertical) >> 31);
    return int32_t((vertical ^ sign) - sign) < 21;
}
extern "C" void claw_player_enter_climb(S *s, D d, void *c) {
    restore(s, d, c, false);
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
extern "C" void claw_player_enter_attack_stand(S *s, D d, void *c) {
    if (s->logicState == 5000)
        return;
    s->logicState = 24;
    a(s, 0xcc) = 1;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    a(s, 0x128) = s->privateWords[0] ? uint32_t(-22) : uint32_t(-15);
    a(s, 0x12c) = uint32_t(-45);
    a(s, 0x130) = s->privateWords[0] ? 15 : 22;
    a(s, 0x134) = 52;
    a(s, 0x118) = uint32_t(-16);
    a(s, 0x11c) = uint32_t(-52);
    a(s, 0x120) = 16;
    a(s, 0x124) = 60;
    s->privateWords[69] = 1500;
    s->privateWords[63] = 650;
    s->privateWords[72] = 15000;
    s->privateWords[73] = effect(s, d, c, 0x4f6286, 0x5246d0);
}
extern "C" void claw_player_start_attack(S *s, T *t, uint32_t code, D d, void *c) {
    auto &p = s->privateWords;
    ++p[58];
    p[1] = 1;
    p[7] = 0;
    p[8] = 0;
    p[72] = 15000;
    p[73] = a(s, 0x190);
    p[15] = code;
    auto anim = [&](uint32_t name) {
        effect(s, d, c, 0x4c79e0, name, 0);
    };
    auto melee = [&](uint32_t name, int left, int top, int right, int bottom, uint32_t damage, uint32_t bonus,
                     uint32_t hard, uint32_t variant, uint32_t extra = 0) {
        anim(name);
        a(s, 0x138) = left;
        a(s, 0x13c) = top;
        a(s, 0x140) = right;
        a(s, 0x144) = bottom;
        a(s, 0x104) = damage;
        if (extra)
            anim(extra);
        if (s->powerup == 0x26bc)
            a(s, 0x104) = bonus;
        if (t->difficulty)
            a(s, 0x104) = hard;
        p[5] = variant;
    };
    auto shot = [&](uint32_t full, uint32_t empty, uint32_t ammo, uint32_t x, int y, uint32_t frame) {
        anim(int32_t(p[ammo]) < 1 ? empty : full);
        p[4] = 0;
        p[21] = x;
        p[22] = y;
        p[27] = frame;
        p[5] = 0;
    };
    bool power = s->powerup >= 0x26b8 && s->powerup <= 0x26bb;
    switch (code) {
    case 1:
        melee(0x524a98, 30, -2, 112, 19, 5, 10, 20, 0, power ? 0x524a84 : 0);
        p[21] = 95;
        p[22] = 15;
        break;
    case 3:
        melee(0x5248a4, 0, -2, 56, 19, 5, 10, 20, 0);
        break;
    case 4:
        melee(0x5248b0, 0, -19, 56, 19, 5, 10, 20, 1);
        break;
    case 5:
        if (int32_t(p[28]) > 0 && int32_t(effect(s, d, c, 0x4a3050)) % 100 < 30)
            effect(s, d, c, 0x48c8a0, 0x524a50, 0);
        shot(0x524a44, 0x524a30, 28, 71, -21, 2);
        break;
    case 6:
        shot(0x5249b0, 0x5249a0, 29, 54, -8, 1);
        break;
    case 7:
        melee(0x524abc, 30, 19, 105, 37, 2, 4, 10, 0, power ? 0x524aa4 : 0);
        p[21] = 95;
        p[22] = 25;
        break;
    case 8:
        melee(0x524a74, 30, -2, 112, 19, 5, 10, 20, 0, power ? 0x524a5c : 0);
        p[21] = 75;
        p[22] = 10;
        break;
    case 9:
        shot(0x5249f8, 0x5249e0, 28, 71, -21, 1);
        break;
    case 10:
        shot(0x524990, 0x52497c, 29, 75, -8, 1);
        break;
    case 11: {
        p[1] = 0;
        p[15] = 0;
        t->targetToken = 0;
        int32_t distance = effect(s, d, c, 0x41d750);
        if (distance < 64 && t->targetToken && (t->targetActor[0x164 / 4] & 1) && claw_player_can_lift(s, t))
            effect(s, d, c, 0x41dc50, t->targetToken);
        break;
    }
    case 12:
    case 16: {
        uint32_t threshold = code == 12 ? 25 : 35;
        if (int32_t(p[30]) > 0 && int32_t(effect(s, d, c, 0x4a3050)) % 100 < int32_t(threshold))
            effect(s, d, c, 0x48c8a0, 0x524970, 0);
        shot(code == 12 ? 0x524914 : 0x524958, code == 12 ? 0x524900 : 0x524940, 30, 60, code == 12 ? -8 : 12, 1);
        p[64] = 0;
        p[65] = 50;
        p[66] = 2000;
        p[74] = effect(s, d, c, 0x4f6286, code == 12 ? 0x5248ec : 0x524928);
        p[7] = 1;
        break;
    }
    case 13:
        melee(0x524898, 0, -2, 56, 19, 5, 10, 20, 0);
        break;
    case 14:
        shot(0x524a20, 0x524a08, 28, 71, 23, 2);
        break;
    case 15:
        shot(0x5249d0, 0x5249bc, 29, 68, 24, 0);
        break;
    case 18:
        shot(0x5248d8, 0x5248c0, 30, 60, -16, 1);
        p[64] = 500;
        p[65] = 50;
        p[66] = 2000;
        break;
    default:
        restore(s, d, c, false, true);
        break;
    }
    if (!p[0] && a(s, 0x138) != 0x80000000) {
        uint32_t left = a(s, 0x138);
        a(s, 0x138) = 0 - a(s, 0x140);
        a(s, 0x140) = 0 - left;
    }
    if (t->damage100)
        a(s, 0x104) = 100;
    else if (t->damage0)
        a(s, 0x104) = 0;
}
extern "C" void claw_player_select_weapon_attack(S *s, T *t, D d, void *c) {
    if (s->privateWords[1])
        return;
    uint32_t weapon = s->privateWords[12];
    if (weapon < 1 || weapon > 3)
        return;
    bool air = s->logicState == 4 || s->logicState == 25;
    uint32_t code = weapon == 1   ? (air                   ? 9
                                     : s->logicState == 26 ? 14
                                                           : 5)
                    : weapon == 2 ? (air                   ? 10
                                     : s->logicState == 26 ? 15
                                                           : 6)
                                  : (air                   ? 18
                                     : s->logicState == 26 ? 16
                                                           : 12);
    claw_player_start_attack(s, t, code, d, c);
}
extern "C" uint32_t claw_player_select_attack(S *s, T *t, D d, void *c) {
    auto &p = s->privateWords;
    if (p[1])
        return 0;
    uint32_t pressed = t->pressed;
    if (!(pressed & 2)) {
        if (pressed & 4) {
            claw_player_select_weapon_attack(s, t, d, c);
            return p[1];
        }
        if (pressed & 0x40) {
            p[12] = 1;
            claw_player_select_weapon_attack(s, t, d, c);
            return p[1];
        }
        if (pressed & 0x80) {
            p[12] = 2;
            claw_player_select_weapon_attack(s, t, d, c);
            return p[1];
        }
        if (pressed & 0x100) {
            p[12] = 3;
            claw_player_select_weapon_attack(s, t, d, c);
            return p[1];
        }
        if (!(pressed & 0x20) || a(s, 0xcc) != 1)
            return 0;
        t->targetToken = 0;
        int32_t distance = effect(s, d, c, 0x41d750);
        if (distance > 63 || !t->targetToken || !(t->targetActor[0x164 / 4] & 1) || !claw_player_can_lift(s, t))
            return 0;
        effect(s, d, c, 0x41dc50, t->targetToken);
        return 1;
    }
    uint32_t code = 0;
    if (s->logicState == 25 || s->logicState == 4)
        code = 8;
    else if (s->logicState == 26)
        code = 7;
    else if (s->powerup >= 0x26b8 && s->powerup <= 0x26bb)
        code = 1;
    else {
        t->targetToken = 0;
        int32_t distance = effect(s, d, c, 0x41d750);
        uint32_t choice = claw_player_attack_random_range(s, 0, 3, d, c);
        if (distance > 150)
            t->targetToken = 0;
        if (choice == 0 || choice == 3)
            choice = claw_player_attack_random_range(s, 0, 3, d, c);
        if ((s->inputHeld & 0x4000000) && !(s->inputHeld & 0x3000000)) {
            if (distance < 64 && t->targetToken && (t->targetActor[0x164 / 4] & 1) && claw_player_can_lift(s, t))
                effect(s, d, c, 0x41dc50, t->targetToken);
            return p[1];
        }
        if (!t->targetToken || (t->targetActor[0x164 / 4] & 0x400)) {
            if (distance < 32)
                choice = claw_player_attack_random_range(s, 1, 3, d, c);
            else if (distance < 150)
                choice = 0;
        } else
            choice = 0;
        if (choice > 3)
            return p[1];
        const uint32_t codes[] = {1, 4, 3, 13};
        code = codes[choice];
    }
    claw_player_start_attack(s, t, code, d, c);
    return p[1];
}
extern "C" void claw_player_update_attack(S *s, T *t, D d, void *c) {
    auto &p = s->privateWords;
    uint32_t marker = effect(s, d, c, 0x4c82a0, s->animationDelta);
    if (a(s, 0x1a4) && !a(s, 0x19c)) {
        restore(s, d, c, true);
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
            projectile(s, t, d, c);
        }
        break;
    case 3:
        if (((t->pressed & 4) || (p[12] == 1 && (t->pressed & 0x40)) || (p[12] == 2 && (t->pressed & 0x80))) &&
            (p[12] != 1 || int32_t(p[28]) > 0)) {
            ++p[58];
            p[4] = 0;
            effect(s, d, c, 0x420970, p[27]);
        }
        break;
    case 4:
        if (!(s->inputHeld & 0x104)) {
            p[64] = std::max(p[64], p[65]);
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
