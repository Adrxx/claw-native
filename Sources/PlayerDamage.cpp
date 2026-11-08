#include "PlayerDamage.h"
#include <cstring>
namespace {
using S = ClawPlayerLocomotion;
using T = ClawPlayerDamageContext;
using I = ClawPlayerInputContext;
using D = ClawPlayerLocomotionDependency;
uint32_t &a(S *s, uint32_t offset) {
    return s->actor[offset / 4];
}
uint32_t effect(S *s, D d, void *c, uint32_t entry, uint32_t x = 0, uint32_t y = 0, uint32_t z = 0) {
    return d ? d(s, entry, x, y, z, c) : 0;
}
void cleanup(S *s, D d, void *c, uint32_t restore) {
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
        effect(s, d, c, restore, p[73]);
        a(s, 8) |= 0x80;
    }
}
void sound(S *s, D d, void *c, uint32_t name, bool registry = false) {
    if (s->audioRegistryDisabled)
        return;
    uint32_t token = effect(s, d, c, registry ? 0x4f6286 : 0x4061b0, name);
    if (token)
        effect(s, d, c, 0x4208e0, token, s->audioPosition);
}
void finishDeath(S *s, T *t, D d, void *c) {
    auto &p = s->privateWords;
    if (effect(s, d, c, 0x10, t->configurationToken) != 4)
        --p[31];
    if (t->infiniteLives)
        ++p[31];
    ++p[32];
    effect(s, d, c, 0x546d50, t->windowToken, 0x111, int32_t(p[31]) < 1 ? 0x8006 : 0x803a);
    p[6] = 1;
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
extern "C" uint32_t claw_player_damage_attacker_word(const T *t, uint32_t offset) {
    return offset < 512 && !(offset & 3) ? t->attackerActor[offset / 4] : 0;
}
extern "C" void claw_player_set_damage_attacker_word(T *t, uint32_t offset, uint32_t value) {
    if (offset < 512 && !(offset & 3))
        t->attackerActor[offset / 4] = value;
}
extern "C" void claw_player_enter_fall_death(S *s, T *t, uint32_t notice, D d, void *c) {
    cleanup(s, d, c, 0x4c8220);
    s->logicState = 5004;
    t->logicWord20 = 750;
    effect(s, d, c, 0x4c79e0, 0x5246e8, 1);
    uint32_t flags = a(s, 8) & 0xffffffef;
    a(s, 0xcc) = 4;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    a(s, 8) = flags | 5;
    if (a(s, 0x64) != 8500) {
        a(s, 0x64) = 8500;
        a(s, 8) = flags | 0x20005;
    }
    a(s, 0x10c) = 0;
    s->privateWords[16] = 0;
    s->physics.velocity[1] = 0;
    s->physics.acceleration[1] = 2250;
    if (notice)
        effect(s, d, c, 0x41ebd0);
    effect(s, d, c, 0x4b7aa0);
    effect(s, d, c, 0x41f990, 0, 0);
}
extern "C" void claw_player_enter_spike_death(S *s, T *t, D d, void *c) {
    cleanup(s, d, c, 0x420a10);
    s->logicState = 5005;
    effect(s, d, c, 0x4c79e0, 0x524708, 1);
    a(s, 0xcc) = 4;
    a(s, 0x148) = 0;
    a(s, 0x14c) = 0;
    a(s, 8) = (a(s, 8) & 0xffffffef) | 5;
    a(s, 0x48) = 20;
    a(s, 0x44) = 0;
    a(s, 0x10c) = 0;
    if (t->overlayMode == 1) {
        a(s, 0x40) |= 1;
        effect(s, d, c, 0x461c40, a(s, 0x4c), a(s, 0x50) - t->overlayOffsetY, a(s, 0x64) + 2);
    }
    if (!s->audioRegistryDisabled) {
        uint32_t token = effect(s, d, c, 0x4f6286, 0x5246f8);
        if (token && t->audioManagerAvailable)
            effect(s, d, c, 0x4b45f0, t->resolvedSoundPoolToken, s->audioPosition);
    }
    effect(s, d, c, 0x41ebd0);
    effect(s, d, c, 0x4b7aa0);
    effect(s, d, c, 0x41f990, 0, 0);
}
extern "C" void claw_player_update_fall_death(S *s, T *t, D d, void *c) {
    uint32_t oldY = a(s, 0x50);
    effect(s, d, c, 0x4c82a0, s->animationDelta);
    volatile double seconds = double(s->stageDelta) * .001;
    claw_physics_update(&s->physics, seconds);
    uint32_t first = claw_physics_pixel_y(&s->physics, &s->pixelScratchY),
             second = claw_physics_pixel_y(&s->physics, &s->pixelScratchY);
    s->privateWords[16] += second + 1;
    a(s, 0x50) = oldY + first;
    if (int32_t(s->privateWords[16]) > 800 && !s->privateWords[6])
        finishDeath(s, t, d, c);
}
extern "C" void claw_player_update_spike_death(S *s, T *t, D d, void *c) {
    effect(s, d, c, 0x4c82a0, s->animationDelta);
    if (a(s, 0x1a4) && !a(s, 0x19c) && !s->privateWords[6])
        finishDeath(s, t, d, c);
}
extern "C" void claw_player_update_hurt(S *s, D d, void *c) {
    uint32_t x = a(s, 0x4c), y = a(s, 0x50);
    if ((a(s, 8) & 0x10) && a(s, 0x80)) {
        x += effect(s, d, c, 0x158, a(s, 0x80));
        y += effect(s, d, c, 0x15c, a(s, 0x80));
    }
    if (effect(s, d, c, 0x4c82a0, s->animationDelta) == 1) {
        uint32_t product = s->animationDelta * a(s, 0x148);
        if (int32_t(a(s, 0x148)) > 0)
            x += product / 1000;
        else if (int32_t(a(s, 0x148)) < 0)
            x -= (0 - product) / 1000;
    } else
        a(s, 0x148) = 0;
    effect(s, d, c, 0x4cbb60, x, y, 8);
    if (a(s, 0xcc) == 4)
        a(s, 8) &= 0xffffffef;
    if (a(s, 0x1a4) && !a(s, 0x19c)) {
        cleanup(s, d, c, 0x4c8220);
        s->logicState = 24;
        effect(s, d, c, 0x4c79e0, 0x5246d0, 1);
        a(s, 0xcc) = 1;
        a(s, 0x148) = 0;
        a(s, 0x14c) = 0;
        a(s, 0x104) = 0;
        a(s, 8) |= 0x80;
        a(s, 0x128) = s->privateWords[0] ? uint32_t(-22) : uint32_t(-15);
        a(s, 0x12c) = uint32_t(-45);
        a(s, 0x130) = s->privateWords[0] ? 15 : 22;
        a(s, 0x134) = 52;
        a(s, 0x118) = uint32_t(-16);
        a(s, 0x11c) = uint32_t(-52);
        a(s, 0x120) = 16;
        a(s, 0x124) = 60;
        s->privateWords[63] = 650;
        s->privateWords[69] = 1500;
        s->privateWords[72] = 15000;
        s->privateWords[70] = 0;
        for (auto &r : s->physics.remainder)
            r = 0;
        a(s, 0x1b0) = 0x3f800000;
    }
}
extern "C" uint32_t claw_player_hit(S *s, T *t, I *input, D d, void *c) {
    if (!a(s, 0x74))
        return 0;
    auto &b = t->attackerActor;
    auto &p = s->privateWords;
    uint32_t type = b[0xd0 / 4], damage = 0;
    bool enemy = type == 4 && !(b[0x164 / 4] & 0x10) && p[75] != a(s, 0x74);
    bool projectile = type == 0x10 || type == 0x40 || type == 0x1000000;
    if (enemy || projectile) {
        if (type == 0x40 && b[0xfc / 4] == 0x26bf) {
            if (t->configurationToken) {
                sound(s, d, c, 0x524800);
                t->configurationWord764 = 2000;
            }
            b[8 / 4] |= 0x10000;
        } else {
            input->invulnerabilityTimer = 850;
            a(s, 0x48) = 33;
            a(s, 0x44) = 0;
            if (projectile)
                sound(s, d, c, 0x524800);
            int32_t choice = int32_t(effect(s, d, c, 0x4a3050)) % 4;
            const uint32_t hits[] = {0x524870, 0x524864, 0x524858, 0x52484c};
            if (choice >= 0)
                sound(s, d, c, hits[choice], projectile && choice == 3);
            choice = int32_t(effect(s, d, c, 0x4a3050)) % 4;
            const uint32_t voices[] = {0x52483c, 0x52482c, 0x52481c, 0x52480c};
            if (choice >= 0)
                sound(s, d, c, voices[choice], projectile);
            a(s, 0xd4) &= enemy ? 0xfffffffb : 0xfefffffb;
            damage = b[0x104 / 4];
            if (!damage)
                damage = 1;
            if (projectile) {
                if (b[0x164 / 4] & 0x20)
                    effect(s, d, c, 0x2c, t->attackerToken);
                else if (type != 0x1000000)
                    b[8 / 4] |= 0x10000;
            }
        }
    } else if (type == 0x100)
        effect(s, d, c, 0x41ee60, t->attackerToken);
    else if (type == 0x40000) {
        a(s, 0xf8) += b[0xfc / 4];
        effect(s, d, c, 0x41d6f0, t->attackerToken);
        effect(s, d, c, 0x41f850, t->attackerToken);
        if (!effect(s, d, c, 0x473ae0, t->attackerToken))
            b[8 / 4] |= 0x10000;
    } else if (type == 0x10000) {
        if (int32_t(b[0xfc / 4]) < 101) {
            if (int32_t(a(s, 0x10c)) < 100) {
                a(s, 0x10c) += b[0xfc / 4];
                if (int32_t(a(s, 0x10c)) > 100)
                    a(s, 0x10c) = 100;
                effect(s, d, c, 0x41d6f0, t->attackerToken);
                b[8 / 4] |= 0x10000;
            }
        } else {
            uint32_t duration = int32_t(b[0x108 / 4]) > 0 ? b[0x108 / 4] : b[0xfc / 4];
            effect(s, d, c, 0x41f990, 0x26bc, duration);
            effect(s, d, c, 0x41d6f0, t->attackerToken);
            b[8 / 4] |= 0x10000;
        }
    } else if (type == 0x200000 || type == 0x100000 || type == 0x800000) {
        if (type == 0x200000) {
            a(s, 0x10c) += b[0xfc / 4];
            if (int32_t(a(s, 0x10c)) > 100)
                a(s, 0x10c) = 100;
        } else {
            uint32_t word = type == 0x100000 ? 29 : 28;
            p[word] += b[0xfc / 4];
            if (int32_t(p[word]) > 99)
                p[word] = 99;
        }
        effect(s, d, c, 0x41d6f0, t->attackerToken);
        b[8 / 4] |= 0x10000;
    }
    if (int32_t(damage) > 0) {
        a(s, 0x10c) -= damage;
        if (int32_t(a(s, 0x10c)) < 1)
            claw_player_enter_fall_death(s, t, 1, d, c);
        else if (s->logicState != 31) {
            cleanup(s, d, c, 0x420a10);
            s->logicState = 31;
            effect(s, d, c, 0x4c79e0, int32_t(effect(s, d, c, 0x4a3050)) % 100 < 50 ? 0x5247f0 : 0x5247e0, 0);
            uint32_t x = a(s, 0x4c), y = a(s, 0x50);
            a(s, 0x148) = 0;
            a(s, 0x14c) = 0;
            if (a(s, 0xcc) == 1 || a(s, 0xcc) == 5 || a(s, 0xcc) == 2) {
                if (int32_t(b[0x4c / 4]) < int32_t(x)) {
                    a(s, 0x148) = 200;
                    x -= 4;
                } else {
                    a(s, 0x148) = uint32_t(-200);
                    x += 4;
                }
            }
            if (b[0x138 / 4] != 0x80000000) {
                uint32_t midpoint = uint32_t(int32_t(b[0x13c / 4] + b[0x144 / 4]) / 2) + b[0x50 / 4];
                uint32_t top = a(s, 0x12c) + y, bottom = a(s, 0x134) + y;
                if (int32_t(midpoint) <= int32_t(top))
                    midpoint = top;
                y = int32_t(bottom) <= int32_t(midpoint) ? bottom : midpoint;
            }
            uint32_t z = a(s, 0x64);
            int32_t ry = int32_t(effect(s, d, c, 0x4a3050)) % 9, rx = int32_t(effect(s, d, c, 0x4a3050)) % 9;
            effect(s, d, c, 0x461a00, x + uint32_t(rx) - 4, y + uint32_t(ry) - 4, z + 1);
            if (a(s, 0xcc) != 4 && a(s, 0xcc) != 3 && a(s, 0xcc) != 8)
                a(s, 0xcc) = 1;
            else
                a(s, 0xcc) = (a(s, 8) & 0x10) ? 1 : 4;
        }
    }
    return 1;
}
extern "C" uint32_t claw_player_dispatch_damage(S *s, T *t, I *i, D d, void *c) {
    switch (s->logicState) {
    case 28:
        break;
    case 31:
        claw_player_update_hurt(s, d, c);
        break;
    case 5004:
        claw_player_update_fall_death(s, t, d, c);
        break;
    case 5005:
        claw_player_update_spike_death(s, t, d, c);
        break;
    default:
        return 0;
    }
    epilogue(s, i, d, c);
    return 1;
}
