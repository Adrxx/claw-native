#include "RatBombLogic.h"
#include "PlayerPhysics.h"
#include <algorithm>
#include <cstring>
#include <cmath>
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
struct Invocation {
    ClawRatBombContext *c;
    ClawGenericEnemyDependency d;
    void *user;
    uint32_t depth = 0, guard = 0;
};
uint32_t execute(ClawRatBomb *, Invocation &, uint32_t, uint32_t, uint32_t *);
uint64_t external(ClawRatBomb *s, Invocation &i, const ClawGenericEnemyCall *e) {
    // The reused shared APIs validate a CEnemy bitset word outside this smaller
    // allocation. Hide that portable guard from every host snapshot/callback.
    if (i.depth)
        s->enemy[0x2fc / 4] = i.guard;
    const uint64_t r = i.d ? i.d(s, &i.c->generic, e, i.user) : 0;
    if (i.depth) {
        i.guard = s->enemy[0x2fc / 4];
        s->enemy[0x2fc / 4] = 0;
    }
    return r;
}
uint64_t call(ClawRatBomb *s, Invocation &i, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr) {
    ClawGenericEnemyCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), e.arguments);
    e.name = name;
    return external(s, i, &e);
}
uint64_t bridge(ClawGenericEnemy *s, ClawGenericEnemyContext *, const ClawGenericEnemyCall *e, void *user) {
    auto &i = *static_cast<Invocation *>(user);
    uint32_t r = 0;
    if (e->receiver == i.c->generic.enemyToken &&
        execute(s, i, e->function, e->argumentCount ? e->arguments[0] : 0, &r))
        return r;
    return external(s, i, e);
}
uint32_t common(ClawRatBomb *s, Invocation &i, uint32_t f, uint32_t arg) {
    if (!i.depth++) {
        i.guard = s->enemy[0x2fc / 4];
        s->enemy[0x2fc / 4] = 0;
    }
    uint32_t r = claw_generic_enemy_entry(s, &i.c->generic, f, arg, bridge, &i);
    if (!--i.depth)
        s->enemy[0x2fc / 4] = i.guard;
    return r;
}
void virtualCall(ClawRatBomb *s, Invocation &i, uint32_t slot, uint32_t arg = 0, bool hasArg = false) {
    const uint32_t f = i.c->generic.virtualFunctions[slot / 4];
    uint32_t r;
    if (execute(s, i, f, arg, &r))
        return;
    if (common(s, i, f, arg))
        return;
    if (hasArg)
        call(s, i, f, i.c->generic.enemyToken, {arg});
    else
        call(s, i, f, i.c->generic.enemyToken);
}
const ClawGenericEnemyState *state(Invocation &i, int32_t id) {
    auto &c = i.c->generic;
    for (size_t n = 0; n < c.stateCount; ++n)
        if (c.states[n].state == id)
            return c.states + n;
    return nullptr;
}
uint32_t lookup(ClawRatBomb *s, Invocation &i, const char *name) {
    if (i.d)
        return uint32_t(call(s, i, 0x4dba00, 0x537668, {}, name));
    auto &c = i.c->generic;
    for (size_t n = 0; n < c.stateCount; ++n)
        if (c.states[n].name && std::strcmp(c.states[n].name, name) == 0)
            return uint32_t(c.states[n].state);
    i.c->fault = 3;
    return 0;
}
void imageRect(uint32_t *a, const uint32_t *h, size_t o) {
    a[o / 4] = h[8] - h[6];
    a[(o + 4) / 4] = h[9] - h[7];
    a[(o + 8) / 4] = h[8] - 1 + h[6];
    a[(o + 12) / 4] = h[7] - 1 + h[9];
}
void mirrorRect(uint32_t *a, size_t o) {
    if (a[o / 4] == 0x80000000)
        return;
    const auto old = a[o / 4];
    a[o / 4] = 0u - a[(o + 8) / 4];
    a[(o + 8) / 4] = 0u - old;
}
void begin(ClawRatBomb *s, Invocation &i, const char *name) {
    s->enemy[0x24 / 4] = s->primary[7];
    s->primary[7] = lookup(s, i, name);
}
uint32_t baseConstruct(ClawRatBomb *s, Invocation &i) {
    auto *e = s->enemy;
    auto *a = s->actor;
    auto *l = s->primary;
    auto &c = i.c->generic;
    e[0] = 0x50b064;
    e[2] = e[3] = c.actorToken;
    e[4] = a[0x6c / 4];
    e[1] = 0;
    call(s, i, 0x4c7fa0, c.actorToken, {}, "LogicHit");
    call(s, i, 0x4c8060, c.actorToken, {}, "LogicAttack");
    e[5] = e[6] = 0;
    e[7] = 1001;
    e[8] = 2;
    ClawPlayerPhysics p;
    std::memcpy(&p, e + 0x28 / 4, sizeof p);
    claw_physics_construct(&p);
    for (int axis = 0; axis < 3; ++axis) {
        p.minimum[axis] = load(c.defaults, 0);
        p.maximum[axis] = p.maximumDelta[axis] = p.maximumVelocity[axis] = load(c.defaults, 8);
    }
    std::memcpy(e + 0x28 / 4, &p, sizeof p);
    e[0] = 0x50b2a4;
    for (auto o : {0x80, 0x88, 0x98, 0xa0}) {
        size_t source = o == 0x80 ? 0x2c : o == 0x88 ? 0x34 : o == 0x98 ? 0x30 : 0x38;
        store(e, o, l[source / 4] ? double(int32_t(l[source / 4])) : load(c.defaults, o < 0x90 ? 0 : 8));
    }
    store(e, 0x68, double(int32_t(a[0x4c / 4])));
    store(e, 0x70, double(int32_t(a[0x50 / 4])));
    store(e, 0x78, 0);
    store(e, 0x50, double(int32_t(a[0x148 / 4])));
    store(e, 0x58, double(int32_t(a[0x14c / 4])));
    store(e, 0x60, 0);
    for (auto o : {0x38, 0x40, 0x48})
        store(e, o, 0);
    store(e, 0x28, mul(double(c.tick), 0.001));
    store(e, 0x30, 0);
    for (auto o : {0xe8, 0xf0, 0xf8})
        store(e, o, double(c.defaults[0x30 / 4]));
    e[0x120 / 4] = e[0x124 / 4] = 0;
    a[0xcc / 4] = 7;
    common(s, i, 0x4dca10, 0);
    e[0x128 / 4] = e[0x12c / 4] = c.actorToken;
    e[0x130 / 4] = a[0x6c / 4];
    e[0] = 0x50ee8c;
    a[2] |= 0x40;
    a[2] |= 0x20;
    a[0x164 / 4] |= 0x2000;
    e[0x148 / 4] = 0;
    for (size_t axis = 0; axis < 3; ++axis) {
        store(e, 0x80 + axis * 8, load(c.defaults, 0));
        store(e, 0x98 + axis * 8, load(c.defaults, 8));
    }
    return c.enemyToken;
}
uint32_t construct(ClawRatBomb *s, Invocation &i) {
    baseConstruct(s, i);
    auto *e = s->enemy;
    auto *a = s->actor;
    auto &c = *i.c;
    auto &g = c.generic;
    e[0] = 0x50f13c;
    if (!a[0x170 / 4])
        call(s, i, 0x4c7970, g.actorToken, {}, "LEVEL_RATBOMB");
    const char *names[] = {"LEVEL_RATBOMB_FALL",    "LEVEL_RATBOMB_FALLEASTWEST",
                           "LEVEL_RATBOMB_EXPLODE", "LEVEL_RATBOMB_BOUNCE",
                           "GAME_BOINKJR",          "GAME_BOMBEXP"};
    for (size_t n = 0; n < 6; ++n)
        e[(0x150 + n * 4) / 4] =
            uint32_t(call(s, i, 0x4f6286, n < 4 ? c.sequenceRegistryToken : g.soundRegistryToken, {}, names[n]));
    e[0x168 / 4] = 0;
    if (a[0x170 / 4]) {
        a[0x16c / 4] = uint32_t(c.imageMinimum);
        a[0x174 / 4] = c.imageMinimum <= c.imageMaximum ? c.minimumImageToken : 0;
    }
    if (a[0x174 / 4])
        imageRect(a, c.imageHeader, 0x128);
    a[0xd0 / 4] = 0x40;
    a[0x118 / 4] = uint32_t(-10);
    a[0x11c / 4] = uint32_t(-200);
    a[0x120 / 4] = 10;
    a[0x124 / 4] = 20;
    a[2] |= 4;
    a[2] |= 0x80;
    a[0x104 / 4] = 15;
    a[0x104 / 4] = truncLow(mul(double(int32_t(a[0x104 / 4])), double(c.damageScale)));
    if (!a[0x64 / 4]) {
        a[0x64 / 4] = 4990;
        a[2] |= 0x20000;
    }
    return g.enemyToken;
}
uint32_t execute(ClawRatBomb *s, Invocation &i, uint32_t f, uint32_t arg, uint32_t *result) {
    auto *e = s->enemy;
    auto *a = s->actor;
    auto &c = *i.c;
    auto &g = c.generic;
    uint32_t r = 0;
    switch (f) {
    case 0x47d890:
        r = construct(s, i);
        break;
    case 0x484d90:
        e[0] = 0x50b014;
        if (arg & 1)
            call(s, i, 0x4f6428, 0, {g.enemyToken});
        r = g.enemyToken;
        break;
    case 0x456030:
        e[0] = 0x50b014;
        break;
    case 0x473c50:
        r = baseConstruct(s, i);
        break;
    case 0x4c9e30:
    case 0x4c96b0:
    case 0x4bb030:
        break;
    case 0x4dca10:
        common(s, i, f, arg);
        break;
    case 0x47e1d0:
        if (a[0x170 / 4]) {
            a[0x16c / 4] = uint32_t(c.imageMinimum);
            a[0x174 / 4] = c.imageMinimum <= c.imageMaximum ? c.minimumImageToken : 0;
        }
        break;
    case 0x406240:
        if (a[0x174 / 4])
            imageRect(a, c.imageHeader, 0x128);
        break;
    case 0x4741f0:
        if (a[0x174 / 4]) {
            imageRect(a, c.imageHeader, 0x118);
            imageRect(a, c.imageHeader, 0x138);
        }
        virtualCall(s, i, 0x28);
        break;
    case 0x47db20:
    case 0x473f40: {
        const auto *entry = state(i, int32_t(arg));
        if (!entry || !entry->name) {
            c.fault = 3;
            break;
        }
        uint32_t target = entry->function;
        if (f == 0x47db20) {
            if (std::strcmp(entry->name, "LS_FALLING") == 0)
                target = 0x47e180;
            else if (std::strcmp(entry->name, "LS_EXPLODING") == 0)
                target = 0x47dfc0;
        }
        if (target) {
            if (!execute(s, i, target, 0, &r) && !common(s, i, target, 0))
                call(s, i, target, g.enemyToken);
        } else
            call(s, i, 0x4a36f0, 0, {g.enemyToken});
        break;
    }
    case 0x47e050: {
        const double velocity = load(e, 0x50);
        e[0x134 / 4] = a[0x190 / 4];
        call(s, i, 0x4c8220, g.actorToken + 0x188, {e[((velocity == 0 || std::isnan(velocity)) ? 0x150 : 0x154) / 4]});
        if (velocity > 0 && !(a[0x40 / 4] & 2)) {
            const auto old = e[0x138 / 4];
            e[0x138 / 4] = 0u - e[0x140 / 4];
            e[0x140 / 4] = 0u - old;
            a[0x40 / 4] |= 2;
            for (auto o : {0x118, 0x128, 0x138})
                mirrorRect(a, o);
        }
        call(s, i, 0x4c82a0, g.actorToken + 0x188, {g.animationDelta});
        begin(s, i, "LS_FALLING");
        a[0xcc / 4] = 8;
        break;
    }
    case 0x47e180:
        call(s, i, 0x4c82a0, g.actorToken + 0x188, {g.animationDelta});
        if (a[0xcc / 4] == 1)
            virtualCall(s, i, 0x2c);
        if (e[0x120 / 4] & 0x10000)
            virtualCall(s, i, 0x2c);
        break;
    case 0x4742f0:
        if (e[0x148 / 4])
            call(s, i, 0x4c82a0, g.actorToken + 0x188, {g.animationDelta});
        if (e[0x120 / 4] & 0x10000)
            a[2] |= 0x10000;
        break;
    case 0x47df20:
        begin(s, i, "LS_EXPLODING");
        a[0xd0 / 4] = 0x1000000;
        e[0x134 / 4] = a[0x190 / 4];
        call(s, i, 0x4c8220, g.actorToken + 0x188, {e[0x158 / 4]});
        e[0xc8 / 4] = 1;
        if (e[0x164 / 4] && c.audioManagerAvailable)
            call(s, i, 0x4b45f0, c.explosionSoundPoolToken, {c.masterVolume, 0, 0, 0});
        e[0x168 / 4] = 0;
        break;
    case 0x47dfc0:
        a[2] |= 0x80;
        if (call(s, i, 0x4c82a0, g.actorToken + 0x188, {g.animationDelta}) == 1 && !e[0x168 / 4]) {
            e[0x168 / 4] = 1;
            a[0x138 / 4] -= 40;
            a[0x13c / 4] -= 40;
            a[0x140 / 4] += 40;
            a[0x144 / 4] += 40;
            a[2] &= ~0x80u;
        }
        if (a[0x1a4 / 4] && !a[0x19c / 4])
            a[2] |= 0x10000;
        break;
    case 0x406150:
        mirrorRect(a, 0x128);
        break;
    case 0x406180:
        mirrorRect(a, 0x138);
        break;
    default:
        return 0;
    }
    if (result)
        *result = r;
    return 1;
}
} // namespace
void claw_rat_bomb_context_defaults(ClawRatBombContext *c) {
    if (!c)
        return;
    claw_generic_enemy_context_defaults(&c->generic);
    c->damageScale = 1;
    const uint32_t v[] = {0x484d90, 0x4c9e30, 0x47db20, 0x4063b0, 0x4741f0, 0x4bb030,
                          0x4bb030, 0x4c96b0, 0x4c96b0, 0x4dca10, 0x47e050, 0x47df20};
    std::copy(v, v + 12, c->generic.virtualFunctions);
}
uint32_t claw_rat_bomb_construct(ClawRatBomb *s, ClawRatBombContext *c, ClawGenericEnemyDependency d, void *user) {
    if (!s || !c)
        return 0;
    Invocation i{c, d, user};
    return construct(s, i);
}
uint32_t claw_rat_bomb_tick(ClawRatBomb *s, ClawRatBombContext *c, ClawGenericEnemyDependency d, void *user) {
    if (!s || !c)
        return 0;
    Invocation i{c, d, user};
    switch (s->primary[7]) {
    case 0: {
        s->primary[7] = 1000;
        const auto token = uint32_t(call(s, i, 0x4f63ec, 0, {0x170}));
        if (!token) {
            c->fault = 1;
            return 0;
        }
        c->generic.enemyToken = token;
        construct(s, i);
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
        if (!i.depth++) {
            i.guard = s->enemy[0x2fc / 4];
            s->enemy[0x2fc / 4] = 0;
        }
        if (!claw_generic_enemy_tick(s, &c->generic, bridge, &i))
            c->fault = 3;
        if (!--i.depth)
            s->enemy[0x2fc / 4] = i.guard;
        if (c->fault)
            return 0;
        break;
    }
    return 1;
}
uint32_t claw_rat_bomb_entry(ClawRatBomb *s, ClawRatBombContext *c, uint32_t f, uint32_t arg,
                             ClawGenericEnemyDependency d, void *user, uint32_t *result) {
    if (!s || !c)
        return 0;
    Invocation i{c, d, user};
    return execute(s, i, f, arg, result);
}
