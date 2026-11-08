#include "RatLogic.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
namespace {
double load(const uint32_t *p, size_t o) {
    double v;
    std::memcpy(&v, p + o / 4, 8);
    return v;
}
void store(uint32_t *p, size_t o, double v) {
    std::memcpy(p + o / 4, &v, 8);
}
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
double sub(double a, double b) {
    volatile double v = a - b;
    return v;
}
uint32_t truncLow(double v) {
    uint64_t b;
    std::memcpy(&b, &v, 8);
    int e = int((b >> 52) & 2047) - 1023;
    if (e < 0 || e >= 63)
        return 0;
    uint64_t m = (b & 0xfffffffffffffULL) | 0x10000000000000ULL;
    m = e >= 52 ? m << (e - 52) : m >> (52 - e);
    return b >> 63 ? 0u - uint32_t(m) : uint32_t(m);
}
int32_t absWrap(uint32_t v) {
    uint32_t sign = uint32_t(int32_t(v) >> 31);
    return int32_t((v ^ sign) - sign);
}
struct Invocation {
    ClawRatContext *c;
    ClawGenericEnemyDependency d;
    void *user;
};
uint64_t call(ClawRat *s, Invocation &i, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr) {
    ClawGenericEnemyCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), e.arguments);
    e.name = name;
    return i.d ? i.d(s, &i.c->generic, &e, i.user) : 0;
}
uint32_t execute(ClawRat *, Invocation &, uint32_t, uint32_t, uint32_t *);
uint64_t bridge(ClawGenericEnemy *s, ClawGenericEnemyContext *, const ClawGenericEnemyCall *e, void *user) {
    auto &i = *static_cast<Invocation *>(user);
    uint32_t r = 0;
    if (e->receiver == i.c->generic.enemyToken &&
        execute(s, i, e->function, e->argumentCount ? e->arguments[0] : 0, &r))
        return r;
    return i.d ? i.d(s, &i.c->generic, e, i.user) : 0;
}
void virtualCall(ClawRat *s, Invocation &i, uint32_t slot, uint32_t arg = 0, bool hasArg = false) {
    const uint32_t f = i.c->generic.virtualFunctions[slot / 4];
    uint32_t r;
    if (execute(s, i, f, arg, &r))
        return;
    if (claw_generic_enemy_entry(s, &i.c->generic, f, arg, bridge, &i))
        return;
    if (hasArg)
        call(s, i, f, i.c->generic.enemyToken, {arg});
    else
        call(s, i, f, i.c->generic.enemyToken);
}
bool bit(ClawRat *s, Invocation &i, uint32_t index) {
    const auto n = s->enemy[0x2fc / 4];
    if (n <= index)
        return false;
    if (n <= 32)
        return (s->enemy[0x300 / 4] >> index) & 1;
    auto &c = i.c->generic;
    return c.bitWords && index / 32 < c.bitWordCount && ((c.bitWords[index / 32] >> (index & 31)) & 1);
}
const ClawGenericEnemyState *state(Invocation &i, int32_t id) {
    auto &c = i.c->generic;
    for (size_t n = 0; n < c.stateCount; ++n)
        if (c.states[n].state == id)
            return c.states + n;
    return nullptr;
}
uint32_t lookup(ClawRat *s, Invocation &i, const char *name) {
    if (i.d)
        return uint32_t(call(s, i, 0x4dba00, 0x537668, {}, name));
    auto &c = i.c->generic;
    for (size_t n = 0; n < c.stateCount; ++n)
        if (c.states[n].name && std::strcmp(c.states[n].name, name) == 0)
            return uint32_t(c.states[n].state);
    i.c->fault = 3;
    return 0;
}
void mirror(ClawRat *s, bool right) {
    auto *a = s->actor;
    auto *e = s->enemy;
    if (bool(a[0x40 / 4] & 2) == right)
        return;
    const auto old = e[0x138 / 4];
    e[0x138 / 4] = 0u - e[0x140 / 4];
    e[0x140 / 4] = 0u - old;
    a[0x40 / 4] = right ? a[0x40 / 4] | 2 : a[0x40 / 4] & ~2u;
    for (auto o : {0x118, 0x128, 0x138})
        if (a[o / 4] != 0x80000000) {
            auto left = a[o / 4];
            a[o / 4] = 0u - a[(o + 8) / 4];
            a[(o + 8) / 4] = 0u - left;
        }
}
void begin(ClawRat *s, Invocation &i, const char *name) {
    store(s->enemy, 0x50, 0);
    s->enemy[0x24 / 4] = s->primary[7];
    s->primary[7] = lookup(s, i, name);
}
uint32_t execute(ClawRat *s, Invocation &i, uint32_t f, uint32_t arg, uint32_t *result) {
    auto *e = s->enemy;
    auto *a = s->actor;
    auto &c = *i.c;
    auto &g = c.generic;
    uint32_t r = 0;
    switch (f) {
    case 0x47cd70: {
        const auto *entry = state(i, int32_t(arg));
        if (!entry || !entry->name) {
            c.fault = 3;
            break;
        }
        uint32_t target = 0;
        const char *names[] = {"LS_HOME", "LS_MOVINGLEFT", "LS_MOVINGRIGHT", "LS_THROWING"};
        const uint32_t fs[] = {0x47d1b0, 0x47d470, 0x47d490, 0x47d660};
        for (size_t n = 0; n < 4; ++n)
            if (std::strcmp(entry->name, names[n]) == 0)
                target = fs[n];
        if (target)
            execute(s, i, target, 0, &r);
        else
            claw_generic_enemy_dispatch(s, &g, int32_t(arg), bridge, &i);
        break;
    }
    case 0x405000:
        std::copy(e + 0x210 / 4, e + 0x220 / 4, a + 0x138 / 4);
        if (a[0x40 / 4] & 2) {
            auto old = a[0x138 / 4];
            a[0x138 / 4] = 0u - a[0x140 / 4];
            a[0x140 / 4] = 0u - old;
        }
        break;
    case 0x4357a0:
        mirror(s, true);
        break;
    case 0x406310:
        mirror(s, false);
        break;
    case 0x4c96b0:
    case 0x4bb030:
        break;
    case 0x47d150:
        begin(s, i, "LS_HOME");
        if (e[0x400 / 4] && c.audioManagerAvailable)
            call(s, i, 0x4b45f0, c.soundPoolToken, {c.masterVolume, 0, 0, 0});
        break;
    case 0x47d4b0:
    case 0x47d540:
    case 0x47d5d0:
        begin(s, i, "LS_THROWING");
        e[0x134 / 4] = a[0x190 / 4];
        call(s, i, 0x4c8220, g.actorToken + 0x188, {e[(f == 0x47d4b0 ? 0x35c : 0x360) / 4]});
        e[0x1a0 / 4] = 0;
        e[0x404 / 4] = f == 0x47d4b0 ? 0 : f == 0x47d540 ? uint32_t(-500) : 500;
        e[0x408 / 4] = f == 0x47d4b0 ? 250 : 0;
        e[0x40c / 4] = f == 0x47d4b0 ? 1500 : 0;
        e[0x410 / 4] = f == 0x47d4b0 ? 1 : f == 0x47d540 ? uint32_t(-13) : 13;
        e[0x414 / 4] = f == 0x47d4b0 ? uint32_t(-12) : uint32_t(-22);
        break;
    case 0x47d2f0: {
        bool eligible = false;
        const auto py = g.playerActor[0x50 / 4];
        if (g.levelWord != 0x26b7) {
            const auto q =
                call(s, i, 0x4cda10, g.tileManagerToken, {a[0x4c / 4], a[0x50 / 4], g.playerActor[0x4c / 4], 0x20});
            eligible = q && int32_t(py) < int32_t(a[0x50 / 4] + 50) && int32_t(a[0x50 / 4] - 50) < int32_t(py) &&
                       a[0x38 / 4] != 0xffffffff;
        }
        if (eligible) {
            mirror(s, e[0x18c / 4] == 2);
            if (absWrap(truncLow(load(e, 0x70)) - py) < 50 && e[0x41c / 4] <= g.tick - e[0x418 / 4]) {
                e[0x41c / 4] = 1000;
                e[0x418 / 4] = g.tick;
                virtualCall(s, i, e[0x18c / 4] == 2 ? 0xb0 : 0xac);
                r = 1;
            } else if (absWrap(truncLow(load(e, 0x68)) - g.playerActor[0x4c / 4]) < 40 &&
                       load(e, 0x70) < double(int32_t(py)) && !g.forcedRandom &&
                       int32_t(uint32_t(call(s, i, 0x4a3050, 0))) % 100 < int32_t(e[0x2e4 / 4])) {
                virtualCall(s, i, 0xa8);
                r = 1;
            }
        }
        break;
    }
    case 0x47d1b0:
        call(s, i, 0x4c82a0, g.actorToken + 0x188, {g.animationDelta});
        if (!bit(s, i, 2)) {
            const auto *previous = state(i, int32_t(e[0x24 / 4]));
            if (!previous || !previous->name) {
                c.fault = 3;
                break;
            }
            virtualCall(s, i, std::strcmp(previous->name, "LS_MOVINGRIGHT") ? 0x6c : 0x70, 60, true);
        } else
            execute(s, i, 0x47d2f0, 0, &r);
        r = 0;
        break;
    case 0x47d470:
    case 0x47d490:
        execute(s, i, 0x47d2f0, 0, &r);
        if (!r)
            claw_generic_enemy_entry(s, &g, f == 0x47d470 ? 0x43fd10 : 0x43fdc0, 0, bridge, &i);
        r = 0;
        break;
    case 0x47d780:
        if (c.playerPrivate[0xe8 / 4] != e[0x19c / 4]) {
            e[0x19c / 4] = c.playerPrivate[0xe8 / 4];
            if (c.attackerActor[0xd0 / 4] == 0x20)
                c.attackerActor[2] |= 0x10000;
            virtualCall(s, i, 0x5c, 0, true);
        }
        break;
    case 0x47d660: {
        const auto marker = call(s, i, 0x4c82a0, g.actorToken + 0x188, {g.animationDelta});
        if (marker == 1) {
            if (!e[0x1a0 / 4]) {
                const auto bomb = uint32_t(call(
                    s, i, 0x4c8da0, c.objectManagerToken,
                    {0, e[0x410 / 4] + a[0x4c / 4], e[0x414 / 4] + a[0x50 / 4], a[0x64 / 4] - 1, 0x522d1c, 0x40000},
                    "RatBomb"));
                if (!bomb) {
                    c.fault = 2;
                    break;
                }
                c.projectileToken = bomb;
                call(s, i, c.projectilePrimary[0x10 / 4], 0, {bomb});
                store(c.projectileEnemy, 0x50, double(int32_t(e[0x404 / 4])));
                store(c.projectileEnemy, 0x58, double(int32_t(e[0x408 / 4])));
                store(c.projectileEnemy, 0x40, double(int32_t(e[0x40c / 4])));
                if (e[0x404 / 4]) {
                    const bool alias = c.projectileEnemy[0x12c / 4] == c.projectileToken;
                    if (alias)
                        std::copy(c.projectileActor, c.projectileActor + 128, c.projectileVisualActor);
                    c.projectileVisualActor[0x164 / 4] |= 0x2020;
                    if (alias)
                        c.projectileActor[0x164 / 4] = c.projectileVisualActor[0x164 / 4];
                    c.projectileActor[2] &= ~0x80u;
                    if (alias)
                        c.projectileVisualActor[2] = c.projectileActor[2];
                }
                call(s, i, c.projectileActivateFunction, c.projectileEnemyToken);
            }
            ++e[0x1a0 / 4];
        }
        if (a[0x1a4 / 4] && !a[0x19c / 4])
            virtualCall(s, i, 0x44);
        break;
    }
    default:
        return 0;
    }
    if (result)
        *result = r;
    return 1;
}
} // namespace
void claw_rat_context_defaults(ClawRatContext *c) {
    if (!c)
        return;
    claw_generic_enemy_context_defaults(&c->generic);
    c->damageScale = c->healthScale = c->rangeScale = 1;
    const uint32_t v[] = {0x47cc80, 0x404fc0, 0x47cd70, 0x4063b0, 0x405000, 0x47d780, 0x4bb030, 0x4c96b0, 0x43e9b0,
                          0x43dfa0, 0x404dd0, 0x404eb0, 0x404eb0, 0x404eb0, 0x404eb0, 0x404eb0, 0x4c9e30, 0x47d150,
                          0x404f00, 0x43ed70, 0x43eee0, 0x43ee10, 0x43efe0, 0x43f120, 0x43f640, 0x43f740, 0x43fa10,
                          0x43fcb0, 0x43fd60, 0x43fe00, 0x43fe60, 0x43ffa0, 0x404e00, 0x440120, 0x440420, 0x4407d0,
                          0x43f500, 0x4409d0, 0x440b20, 0x440c90, 0x440410, 0x4bb030, 0x47d4b0, 0x47d540, 0x47d5d0};
    std::copy(v, v + 45, c->generic.virtualFunctions);
}
uint32_t claw_rat_construct(ClawRat *s, ClawRatContext *c, ClawGenericEnemyDependency d, void *user) {
    if (!s || !c)
        return 0;
    Invocation i{c, d, user};
    auto &g = c->generic;
    auto *e = s->enemy;
    auto *a = s->actor;
    if (!claw_generic_enemy_construct(s, &g, bridge, &i)) {
        c->fault = 3;
        return 0;
    }
    e[0x418 / 4] = e[0x41c / 4] = 0;
    e[0] = 0x50f084;
    store(e, 0x70, sub(load(e, 0x70), 32));
    e[0x2d0 / 4] = 5;
    e[0x2e4 / 4] = 10;
    auto range = truncLow(mul(double(c->rangeScale), 10));
    e[0x2e4 / 4] = range < 100 ? 99 : range;
    a[0x10c / 4] = 1;
    a[0x10c / 4] = truncLow(mul(double(int32_t(a[0x10c / 4])), double(c->healthScale)));
    a[0x104 / 4] = 5;
    a[0x104 / 4] = truncLow(mul(double(int32_t(a[0x104 / 4])), double(c->damageScale)));
    if (!a[0x148 / 4])
        a[0x148 / 4] = 60;
    call(s, i, 0x4c7970, g.actorToken, {}, "LEVEL_RAT");
    if (a[0x170 / 4]) {
        a[0x174 / 4] = uint32_t(call(s, i, 0x40f680, a[0x170 / 4], {12}));
        a[0x16c / 4] = 12;
    }
    const char *names[] = {"LEVEL_RAT_WALK", "LEVEL_RAT_IDLE", "LEVEL_RAT_THROWSOUTH", "LEVEL_RAT_THROWEASTWEST",
                           "LEVEL_RAT_DEAD"};
    const size_t offsets[] = {0x354, 0x350, 0x35c, 0x360, 0x374};
    for (size_t n = 0; n < 5; ++n) {
        uint32_t token = uint32_t(call(s, i, 0x4f6286, c->sequenceRegistryToken, {}, names[n]));
        if (!token)
            token = uint32_t(call(s, i, 0x4f6286, c->sequenceRegistryToken, {}, "GAME_NULL"));
        e[offsets[n] / 4] = token;
    }
    e[0x400 / 4] = uint32_t(call(s, i, 0x4f6286, g.soundRegistryToken, {}, "GAME_EEHH"));
    e[0x3a4 / 4] = uint32_t(call(s, i, 0x4f6286, g.soundRegistryToken, {}, "GAME_MOUSEKILL"));
    uint32_t r;
    execute(s, i, 0x47d150, 0, &r);
    for (auto index : {3u, 0u}) {
        if (e[0x2fc / 4] <= index)
            call(s, i, 0x4dbd20, g.enemyToken + 0x2f4, {index});
        else if (e[0x2fc / 4] <= 32)
            e[0x300 / 4] |= 1u << index;
        else if (g.bitWords && g.bitWordCount)
            g.bitWords[0] |= 1u << index;
        else {
            c->fault = 3;
            return 0;
        }
    }
    a[2] |= 0x40;
    a[0xd0 / 4] = 4;
    a[0xd4 / 4] = 0x3000022;
    if (a[0x170 / 4]) {
        a[0x16c / 4] = uint32_t(c->imageMinimum);
        a[0x174 / 4] = uint32_t(call(s, i, 0x40f680, a[0x170 / 4], {uint32_t(c->imageMinimum)}));
    }
    if (a[0x174 / 4])
        for (auto offset : {0x138, 0x128}) {
            a[offset / 4] = c->imageHeader[0x20 / 4] - c->imageHeader[0x18 / 4];
            a[(offset + 4) / 4] = c->imageHeader[0x24 / 4] - c->imageHeader[0x1c / 4];
            a[(offset + 8) / 4] = c->imageHeader[0x18 / 4] - 1 + c->imageHeader[0x20 / 4];
            a[(offset + 12) / 4] = c->imageHeader[0x24 / 4] - 1 + c->imageHeader[0x1c / 4];
        }
    a[0x118 / 4] = uint32_t(-10);
    a[0x11c / 4] = 20;
    a[0x120 / 4] = 10;
    a[0x124 / 4] = 30;
    a[0x124 / 4] += 3;
    a[0x50 / 4] -= 32;
    call(s, i, 0x4cd800, g.tileManagerToken, {g.actorToken, 0});
    a[0xcc / 4] = 1;
    return g.enemyToken;
}
uint32_t claw_rat_tick(ClawRat *s, ClawRatContext *c, ClawGenericEnemyDependency d, void *user) {
    if (!s || !c)
        return 0;
    Invocation i{c, d, user};
    switch (s->primary[7]) {
    case 0: {
        s->primary[7] = 1000;
        const auto token = uint32_t(call(s, i, 0x4f63ec, 0, {0x420}));
        if (!token) {
            c->fault = 1;
            return 0;
        }
        c->generic.enemyToken = token;
        if (!claw_rat_construct(s, c, d, user))
            return 0;
        virtualCall(s, i, 0x10);
        s->primary[0x18 / 4] = token;
        break;
    }
    case 29:
        virtualCall(s, i, 0x20);
        break;
    case 30:
        virtualCall(s, i, 0x1c);
        break;
    case 1000:
        break;
    default:
        if (!claw_generic_enemy_tick(s, &c->generic, bridge, &i)) {
            c->fault = 3;
            return 0;
        }
        break;
    }
    return 1;
}
uint32_t claw_rat_entry(ClawRat *s, ClawRatContext *c, uint32_t f, uint32_t arg, ClawGenericEnemyDependency d,
                        void *user, uint32_t *result) {
    if (!s || !c)
        return 0;
    Invocation i{c, d, user};
    return execute(s, i, f, arg, result);
}
uint32_t claw_rat_actor_word(const ClawRat *s, uint32_t o) {
    return s && o % 4 == 0 && o < 512 ? s->actor[o / 4] : 0;
}
void claw_rat_set_actor_word(ClawRat *s, uint32_t o, uint32_t v) {
    if (s && o % 4 == 0 && o < 512)
        s->actor[o / 4] = v;
}
uint32_t claw_rat_enemy_word(const ClawRat *s, uint32_t o) {
    return s && o % 4 == 0 && o < 1056 ? s->enemy[o / 4] : 0;
}
void claw_rat_set_enemy_word(ClawRat *s, uint32_t o, uint32_t v) {
    if (s && o % 4 == 0 && o < 1056)
        s->enemy[o / 4] = v;
}
