#include "HumanEnemy.h"
#include "PlayerPhysics.h"
#include <algorithm>
#include <cmath>
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
double add(double a, double b) {
    volatile double v = a + b;
    return v;
}
double sub(double a, double b) {
    volatile double v = a - b;
    return v;
}
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
double div(double a, double b) {
    volatile double v = a / b;
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
    ClawHumanEnemyContext *x;
    ClawGenericEnemyDependency d;
    void *user;
};
uint32_t run(ClawHumanEnemy *, Invocation &, uint32_t, uint32_t, uint32_t *);
uint32_t word(ClawHumanEnemy *s, Invocation &i, uint32_t b) {
    return claw_human_enemy_private_word(s, i.x, b);
}
void put(ClawHumanEnemy *s, Invocation &i, uint32_t b, uint32_t v) {
    claw_human_enemy_set_private_word(s, i.x, b, v);
}
uint64_t call(ClawHumanEnemy *s, Invocation &i, uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {},
              const char *name = nullptr) {
    ClawGenericEnemyCall e{};
    e.function = f;
    e.receiver = t;
    e.argumentCount = uint32_t(a.size());
    e.name = name;
    std::copy(a.begin(), a.end(), e.arguments);
    return i.d ? i.d(s, i.x->generic, &e, i.user) : 0;
}
uint64_t bridge(ClawGenericEnemy *s, ClawGenericEnemyContext *, const ClawGenericEnemyCall *e, void *u) {
    auto &i = *static_cast<Invocation *>(u);
    uint32_t r = 0;
    if (e->receiver == i.x->generic->enemyToken && run(s, i, e->function, e->argumentCount ? e->arguments[0] : 0, &r))
        return r;
    return i.d ? i.d(s, i.x->generic, e, i.user) : 0;
}
void invoke(ClawHumanEnemy *s, Invocation &i, uint32_t f, uint32_t arg = 0, bool has = false) {
    uint32_t r;
    if (run(s, i, f, arg, &r))
        return;
    auto *g = i.x->generic;
    if (claw_generic_enemy_state_entry(s, g, i.x->sharedStates, f, arg, bridge, &i))
        return;
    if (claw_generic_enemy_entry(s, g, f, arg, bridge, &i))
        return;
    if (has)
        call(s, i, f, g->enemyToken, {arg});
    else
        call(s, i, f, g->enemyToken);
}
void virt(ClawHumanEnemy *s, Invocation &i, uint32_t slot, uint32_t arg = 0, bool has = false) {
    invoke(s, i, i.x->generic->virtualFunctions[slot / 4], arg, has);
}
bool bit(ClawHumanEnemy *s, Invocation &i, uint32_t n) {
    uint32_t size = s->enemy[0x2fc / 4];
    if (size <= n)
        return false;
    if (size <= 32)
        return (s->enemy[0x300 / 4] >> n) & 1;
    auto *g = i.x->generic;
    if (!g->bitWords || n / 32 >= g->bitWordCount) {
        i.x->fault = 1;
        return false;
    }
    return (g->bitWords[n / 32] >> (n & 31)) & 1;
}
void setBit(ClawHumanEnemy *s, Invocation &i, uint32_t n, bool toggle = false) {
    uint32_t size = s->enemy[0x2fc / 4];
    if (size <= n) {
        i.x->fault = 2;
        return;
    }
    uint32_t *p = size <= 32 ? s->enemy + 0x300 / 4 : i.x->generic->bitWords;
    if (!p) {
        i.x->fault = 1;
        return;
    }
    p += size <= 32 ? 0 : n / 32;
    if (toggle)
        *p ^= 1u << (n & 31);
    else
        *p |= 1u << (n & 31);
}
uint32_t resolve(ClawHumanEnemy *s, Invocation &i, const char *name) {
    return uint32_t(call(s, i, 0x4f6286, i.x->generic->soundRegistryToken, {}, name));
}
uint32_t stateID(ClawHumanEnemy *s, Invocation &i, const char *name) {
    if (i.d)
        return uint32_t(call(s, i, 0x4dba00, 0x537668, {}, name));
    auto *g = i.x->generic;
    for (size_t n = 0; n < g->stateCount; ++n)
        if (g->states[n].name && !std::strcmp(g->states[n].name, name))
            return uint32_t(g->states[n].state);
    i.x->fault = 3;
    return 0;
}
const char *stateName(ClawHumanEnemy *s, Invocation &i, uint32_t id) {
    (void)s;
    auto *g = i.x->generic;
    for (size_t n = 0; n < g->stateCount; ++n)
        if (g->states[n].state == int32_t(id))
            return g->states[n].name;
    i.x->fault = 3;
    return nullptr;
}
void transition(ClawHumanEnemy *s, Invocation &i, const char *name) {
    s->enemy[9] = s->primary[7];
    s->primary[7] = stateID(s, i, name);
}
void animate(ClawHumanEnemy *s, Invocation &i) {
    call(s, i, 0x4c82a0, i.x->generic->actorToken + 0x188, {i.x->generic->animationDelta});
}
void sequence(ClawHumanEnemy *s, Invocation &i, uint32_t token) {
    s->enemy[0x134 / 4] = s->actor[0x190 / 4];
    call(s, i, 0x4c8220, i.x->generic->actorToken + 0x188, {token});
}
void audio(ClawHumanEnemy *s, Invocation &i, uint32_t token) {
    auto *x = i.x->sharedStates;
    if (!token || !x->audioEnabled)
        return;
    uint32_t pool = 0;
    bool found = false;
    for (size_t n = 0; n < x->resourceCount; ++n)
        if (x->resources[n].token == token) {
            pool = x->resources[n].controllerToken;
            found = true;
            break;
        }
    if (!found) {
        i.x->fault = 1;
        return;
    }
    call(s, i, 0x4b45f0, pool, {x->audioPosition, 0, 0, 0});
}
uint32_t random(ClawHumanEnemy *s, Invocation &i) {
    return uint32_t(call(s, i, 0x4a3050, 0));
}
void mirrorRect(uint32_t *a, size_t o) {
    if (a[o / 4] != 0x80000000) {
        uint32_t left = a[o / 4];
        a[o / 4] = 0u - a[(o + 8) / 4];
        a[(o + 8) / 4] = 0u - left;
    }
}
void face(ClawHumanEnemy *s, bool left) {
    auto *a = s->actor;
    auto *e = s->enemy;
    if (bool(a[0x40 / 4] & 2) == left)
        return;
    uint32_t old = e[0x138 / 4];
    e[0x138 / 4] = 0u - e[0x140 / 4];
    e[0x140 / 4] = 0u - old;
    a[0x40 / 4] = left ? a[0x40 / 4] | 2 : a[0x40 / 4] & ~2u;
    for (size_t o : {0x118, 0x128, 0x138})
        mirrorRect(a, o);
}
uint32_t *other(ClawHumanEnemy *s, Invocation &i) {
    uint32_t t = s->enemy[0x194 / 4];
    if (t == i.x->generic->actorToken)
        return s->actor;
    if (t == i.x->otherActorToken && i.x->otherActor)
        return i.x->otherActor;
    i.x->fault = 1;
    return nullptr;
}
bool nearPlatform(ClawHumanEnemy *s, Invocation &i) {
    auto *g = i.x->generic;
    if (g->levelWord == 0x26b7)
        return false;
    auto *a = other(s, i);
    if (!a)
        return false;
    uint32_t clear =
        uint32_t(call(s, i, 0x4cda10, g->tileManagerToken, {a[0x4c / 4], a[0x50 / 4], g->playerActor[0x4c / 4], 32}));
    if (!clear)
        return false;
    uint32_t y = a[0x50 / 4], py = g->playerActor[0x50 / 4];
    return int32_t(py) < int32_t(y + 50) && int32_t(y - 50) < int32_t(py) && a[0x38 / 4] != 0xffffffff;
}
void bounds(ClawHumanEnemy *s, Invocation &i) {
    auto *e = s->enemy;
    auto *g = i.x->generic;
    for (size_t o : {0x80, 0x88, 0x90})
        std::memcpy(e + o / 4, g->defaults, 8);
    for (size_t o : {0x98, 0xa0, 0xa8})
        std::memcpy(e + o / 4, g->defaults + 2, 8);
}
void aim(ClawHumanEnemy *s, Invocation &i, uint32_t targetX, uint32_t targetY) {
    auto *e = s->enemy;
    const double ax = load(e, 0x38), ay = load(e, 0x40), az = load(e, 0x48),
                 dx = sub(double(int32_t(targetX)), load(e, 0x68)), dy = sub(double(int32_t(targetY)), load(e, 0x70)),
                 dz = -load(e, 0x78);
    const double dot = sub(sub(-mul(ax, dx), mul(ay, dy)), mul(az, dz));
    double aa = add(add(mul(ax, ax), mul(ay, ay)), mul(az, az));
    double speed = std::sqrt(
        mul(sub(std::sqrt(mul(mul(add(add(mul(dx, dx), mul(dy, dy)), mul(dz, dz)), aa), 4)), mul(dot, -2)), 0.5));
    const double epsilon = load(i.x->generic->defaults, 16);
    if (speed < epsilon) {
        store(e, 0x50, 0);
        store(e, 0x58, 0);
        store(e, 0x60, 0);
        return;
    }
    aa = mul(aa, 0.25);
    if (-epsilon <= aa && aa <= epsilon) {
        double length = add(add(std::abs(dx), std::abs(dy)), std::abs(dz));
        store(e, 0x50, mul(div(dx, length), speed));
        store(e, 0x58, mul(div(dy, length), speed));
        store(e, 0x60, mul(div(dz, length), speed));
        return;
    }
    double t = div(sub(mul(speed, speed), dot), add(aa, aa)), root = std::sqrt(t);
    store(e, 0x50, div(sub(dx, mul(mul(t, ax), 0.5)), root));
    store(e, 0x58, div(sub(dy, mul(mul(t, ay), 0.5)), root));
    store(e, 0x60, div(sub(dz, mul(mul(t, az), 0.5)), root));
}
void base(ClawHumanEnemy *s, Invocation &i) {
    auto *e = s->enemy;
    auto *a = s->actor;
    auto *l = s->primary;
    auto *g = i.x->generic;
    e[0] = 0x50b064;
    e[2] = e[3] = g->actorToken;
    e[4] = a[0x6c / 4];
    e[1] = 0;
    call(s, i, 0x4c7fa0, g->actorToken, {}, "LogicHit");
    call(s, i, 0x4c8060, g->actorToken, {}, "LogicAttack");
    e[5] = e[6] = 0;
    e[7] = 1001;
    e[8] = 2;
    ClawPlayerPhysics p;
    std::memcpy(&p, e + 0x28 / 4, sizeof p);
    claw_physics_construct(&p);
    for (int axis = 0; axis < 3; ++axis) {
        p.minimum[axis] = load(g->defaults, 0);
        p.maximum[axis] = p.maximumDelta[axis] = p.maximumVelocity[axis] = load(g->defaults, 8);
    }
    std::memcpy(e + 0x28 / 4, &p, sizeof p);
    e[0] = 0x50b2a4;
    for (size_t o : {0x80, 0x88, 0x98, 0xa0}) {
        size_t src = o == 0x80 ? 0x2c : o == 0x88 ? 0x34 : o == 0x98 ? 0x30 : 0x38;
        store(e, o, l[src / 4] ? double(int32_t(l[src / 4])) : load(g->defaults, o < 0x90 ? 0 : 8));
    }
    store(e, 0x68, double(int32_t(a[0x4c / 4])));
    store(e, 0x70, double(int32_t(a[0x50 / 4])));
    store(e, 0x78, 0);
    store(e, 0x50, double(int32_t(a[0x148 / 4])));
    store(e, 0x58, double(int32_t(a[0x14c / 4])));
    store(e, 0x60, 0);
    for (size_t o : {0x38, 0x40, 0x48, 0x30})
        store(e, o, 0);
    store(e, 0x28, mul(double(g->tick), 0.001));
    for (size_t o : {0xe8, 0xf0, 0xf8})
        store(e, o, double(g->defaults[12]));
    e[0x120 / 4] = e[0x124 / 4] = 0;
    a[0xcc / 4] = 7;
    claw_generic_enemy_motion(s, g, bridge, &i);
}
void construct(ClawHumanEnemy *s, Invocation &i) {
    base(s, i);
    auto *e = s->enemy;
    auto *a = s->actor;
    auto *l = s->primary;
    auto *g = i.x->generic;
    e[0x128 / 4] = e[0x12c / 4] = e[0x178 / 4] = e[0x17c / 4] = g->actorToken;
    e[0x130 / 4] = e[0x180 / 4] = a[0x6c / 4];
    e[0x14c / 4] = e[0x150 / 4] = 0;
    const size_t inventory[] = {0xf0, 0xf8, 0xf4, 0xfc, 0x100, 0x108, 0x104, 0x10c, 0x100};
    for (size_t n = 0; n < 9; ++n) {
        uint32_t v = n == 8 ? a[inventory[n] / 4] : l[inventory[n] / 4];
        e[(0x154 + n * 4) / 4] = v;
        ++e[0x14c / 4];
        if (v)
            ++e[0x150 / 4];
    }
    e[0x190 / 4] = e[0x194 / 4] = g->actorToken;
    e[0x198 / 4] = a[0x6c / 4];
    e[0x1a4 / 4] = e[0x1a8 / 4] = g->emptyStringToken;
    e[0x2f4 / 4] = 0x513e34;
    e[0x2f8 / 4] = g->bitHandlerToken;
    e[0x2fc / 4] = 32;
    e[0x300 / 4] = 0;
    for (size_t o = 0x3c8; o <= 0x3fc; o += 4)
        e[o / 4] = 0;
    e[0] = 0x50b16c;
    a[2] |= 0x80000;
    e[1] = l[0x168 / 4];
    e[0x184 / 4] = 6;
    e[0x188 / 4] = 0;
    e[0x288 / 4] = 0;
    const uint32_t ranges[] = {400, 50, 0, 0, 300, 50, 200, 50, 100, 50};
    for (size_t n = 0; n < 10; ++n)
        if (n != 2 && n != 3)
            e[(0x28c + n * 4) / 4] = ranges[n];
    e[0x2e4 / 4] = a[0x108 / 4];
    e[0x2e8 / 4] = a[0x114 / 4];
    e[0x2ec / 4] = e[0x2f0 / 4] = l[0x68 / 4];
    e[0x19c / 4] = 0xffffffff;
    e[0x1a0 / 4] = 0;
    for (size_t o = 0x210; o <= 0x26c; o += 4)
        e[o / 4] = 0;
    if (int32_t(l[0x64 / 4]) > 0)
        e[0x300 / 4] |= 4;
    e[0x300 / 4] |= 0x200;
    for (size_t o = 0x2b4; o <= 0x2c8; o += 4)
        e[o / 4] = 0;
    e[0x1ac / 4] = e[0x2cc / 4] = e[0x2d0 / 4] = 0;
    for (size_t o = 0x308; o <= 0x320; o += 4)
        e[o / 4] = 0;
    for (size_t o = 0x32c; o <= 0x388; o += 4)
        e[o / 4] = 0;
    const char *names[] = {"GAME_SPLASH", "GAME_HIT1", "GAME_HIT2", "GAME_HIT3", "GAME_HIT4", "GAME_PURELEASE1"};
    for (size_t n = 0; n < 6; ++n)
        e[(n < 5 ? 0x38c + n * 4 : 0x148) / 4] = resolve(s, i, names[n]);
    for (size_t o = 0x3a0; o <= 0x3c0; o += 4)
        e[o / 4] = 0;
    store(e, 0x40, 2000);
    a[0x164 / 4] &= ~1u;
    for (uint32_t o = 0x428; o <= 0x444; o += 4)
        put(s, i, o, 0);
    e[0] = 0x50e12c;
    a[2] |= 0x80000;
    for (uint32_t o : {0x424u, 0x448u, 0x408u, 0x40cu, 0x414u, 0x418u})
        put(s, i, o, 0);
    e[0x2d0 / 4] = 10;
    e[0x41c / 4] = resolve(s, i, "GAME_HIT1");
    e[0x3a8 / 4] = resolve(s, i, "LEVEL_DEATHTILE");
    e[0x3ac / 4] = resolve(s, i, "LEVEL_DEATHTILE");
    e[0x410 / 4] = e[0x40c / 4] = 0;
    put(s, i, 0x420, 0);
    e[0x414 / 4] = resolve(s, i, "GAME_SOLHITL2");
    e[0x418 / 4] = resolve(s, i, "GAME_SOLHITHI");
    e[0x408 / 4] = resolve(s, i, "GAME_LELAND");
    put(s, i, 0x44c, 0);
    store(e, 0x50, 0);
    store(e, 0x58, 0);
    std::memcpy(e + 0x88 / 4, g->defaults, 8);
    std::memcpy(e + 0xa0 / 4, g->defaults + 2, 8);
    e[0x400 / 4] = 60;
    e[0x404 / 4] = 120;
    e[0x300 / 4] |= 0x29;
    e[0x124 / 4] = 8;
    a[2] |= 0x40;
    a[0x164 / 4] |= 0x400;
    a[0xd0 / 4] = 4;
    a[0xd4 / 4] = 0x3001032;
    const uint32_t high[] = {uint32_t(-137), uint32_t(-27), 0, uint32_t(-7)}, low[] = {uint32_t(-137), 20, 0, 40},
                   tiny[] = {uint32_t(-1), uint32_t(-1), 1, 1}, movement[] = {uint32_t(-20), uint32_t(-60), 20, 51},
                   alternate[] = {uint32_t(-20), uint32_t(-15), 20, 15}, hit[] = {uint32_t(-20), uint32_t(-50), 20, 50};
    std::copy(high, high + 4, e + 0x230 / 4);
    std::copy(low, low + 4, e + 0x240 / 4);
    std::copy(high, high + 4, e + 0x220 / 4);
    std::copy(tiny, tiny + 4, e + 0x210 / 4);
    std::copy(movement, movement + 4, e + 0x250 / 4);
    std::copy(alternate, alternate + 4, e + 0x260 / 4);
    std::copy(hit, hit + 4, a + 0x128 / 4);
    std::copy(movement, movement + 4, a + 0x118 / 4);
    const uint32_t r[] = {500, 40, 300, 40, 200, 40, 150, 40, 100, 40};
    std::copy(r, r + 10, e + 0x28c / 4);
    e[0x2b4 / 4] = 10;
    e[0x2b8 / 4] = uint32_t(-10);
    e[0x2bc / 4] = uint32_t(-45);
    e[0x2c0 / 4] = uint32_t(-20);
    e[0x2c4 / 4] = 20;
    e[0x2c8 / 4] = uint32_t(-15);
    e[0x2e4 / 4] = 50;
    uint32_t range = truncLow(mul(double(i.x->rangeScale), double(int32_t(e[0x2e4 / 4]))));
    e[0x2e4 / 4] = range < 100 ? 99 : range;
    a[0x10c / 4] = 10;
    a[0x10c / 4] = truncLow(mul(double(i.x->healthScale), double(int32_t(a[0x10c / 4]))));
    a[0x104 / 4] = 10;
    a[0x104 / 4] = truncLow(mul(double(i.x->damageScale), double(int32_t(a[0x104 / 4]))));
}
uint32_t run(ClawHumanEnemy *s, Invocation &i, uint32_t f, uint32_t arg, uint32_t *result) {
    auto *e = s->enemy;
    auto *a = s->actor;
    auto *g = i.x->generic;
    uint32_t r = 0;
    switch (f) {
    case 0x44bc60:
        base(s, i);
        r = g->enemyToken;
        break;
    case 0x44c000:
        construct(s, i);
        r = g->enemyToken;
        break;
    case 0x44c840: {
        const ClawGenericEnemyState *q = nullptr;
        for (size_t n = 0; n < i.x->humanStateCount; ++n)
            if (i.x->humanStates[n].state == int32_t(arg)) {
                q = i.x->humanStates + n;
                break;
            }
        if (!q) {
            i.x->fault = 3;
            break;
        }
        if (q->function)
            invoke(s, i, q->function);
        else
            claw_generic_enemy_state_dispatch(s, g, i.x->sharedStates, int32_t(arg), bridge, &i);
        break;
    }
    case 0x44d000: {
        e[0x3c4 / 4] = i.x->clockCountdown ? 0x1fffffff : uint32_t(int32_t(random(s, i)) % 1001);
        claw_generic_enemy_pre(s, g, bridge, &i);
        bool excluded = false;
        for (uint32_t t : {0x52720cu, 0x527204u, 0x527da0u, 0x5234f4u, 0x5271d8u, 0x5271ccu, 0x5271b4u})
            if (arg == t)
                excluded = true;
        bool enable = bit(s, i, 9) && !excluded && g->tick - word(s, i, 0x440) >= word(s, i, 0x444);
        a[0x164 / 4] = enable ? a[0x164 / 4] | 1 : a[0x164 / 4] & ~1u;
        std::copy(e + 0x210 / 4, e + 0x220 / 4, a + 0x138 / 4);
        if (a[0x40 / 4] & 2) {
            uint32_t left = a[0x138 / 4];
            a[0x138 / 4] = 0u - a[0x140 / 4];
            a[0x140 / 4] = 0u - left;
        }
        a[0x164 / 4] = (a[0x40 / 4] & 2) ? a[0x164 / 4] | 2 : a[0x164 / 4] & ~2u;
        if (nearPlatform(s, i) && bit(s, i, 8))
            break;
        if ((e[0x184 / 4] == 5 || e[0x184 / 4] == 6) && arg != 0x5234f4) {
            if (!bit(s, i, 7)) {
                if (int32_t(e[8]) > 1)
                    e[5] = 0x44f840;
                setBit(s, i, 7);
            }
        } else if (e[0x2fc / 4] >= 8)
            setBit(s, i, 7, true);
        auto *pa = g->platformActor;
        bool supported = a[2] & 0x10;
        if (supported && a[0x80 / 4] && (pa[0x164 / 4] & 0x8000) && i.x->platformPrimary &&
            i.x->platformPrimary[7] == 5) {
            i.x->platformPrimary[7] = 0x457;
            break;
        }
        if (a[0x80 / 4] && (pa[0x164 / 4] & 0x20000) && word(s, i, 0x448)) {
            if (int32_t(e[8]) > 1)
                e[5] = 0x44f6e0;
            break;
        }
        if (supported) {
            if (a[0x80 / 4] && (pa[0x164 / 4] & 0x10000) && i.x->platformPrimary && i.x->platformPrimary[7] == 5) {
                put(s, i, 0x448, 1);
                i.x->platformPrimary[7] = 0x457;
                break;
            }
            setBit(s, i, 2);
            break;
        }
        uint32_t ledge = uint32_t(call(s, i, 0x43eab0, g->enemyToken));
        if (ledge && !bit(s, i, 2) && int32_t(e[8]) > 1)
            e[5] = 0x44e120;
        break;
    }
    case 0x44d3c0: {
        if (e[5]) {
            if (e[6] && s->primary[7] == e[7]) {
                invoke(s, i, e[6]);
                e[6] = 0;
            }
            invoke(s, i, e[5]);
            e[5] = 0;
            e[7] = 1001;
        }
        virt(s, i, 0x24);
        uint32_t t = word(s, i, 0x44c);
        if (t) {
            if (t != i.x->effectToken || !i.x->effectActor) {
                i.x->fault = 1;
                break;
            }
            auto *fx = i.x->effectActor;
            if (fx[0x1a4 / 4] && fx[0x19c / 4] == 0) {
                fx[2] |= 0x10000;
                put(s, i, 0x44c, 0);
                break;
            }
            fx[0x4c / 4] = truncLow(load(e, 0x68));
            fx[0x50 / 4] = truncLow(load(e, 0x70));
        }
        break;
    }
    case 0x44df60: {
        uint32_t bits = i.x->sharedStates->attackerActor[0x164 / 4];
        if (bits & 0x1c0000) {
            const char *name = bits & 0x40000 ? "GAME_FIREDEATH" : bits & 0x80000 ? "GAME_ICEDEATH" : "GAME_FIREDEATH";
            uint32_t t = uint32_t(call(s, i, 0x4f6286, i.x->sequenceRegistryToken, {}, name));
            if (!t)
                t = uint32_t(call(s, i, 0x4f6286, i.x->sequenceRegistryToken, {}, "GAME_NULL"));
            e[0x374 / 4] = t;
        }
        claw_generic_enemy_state_entry(s, g, i.x->sharedStates, 0x43e9e0, 0, bridge, &i);
        break;
    }
    case 0x44e0c0:
        e[0x304 / 4] = arg;
        if (!bit(s, i, 4))
            call(s, i, 0x42df90, g->enemyToken + 0x128);
        claw_generic_enemy_state_entry(s, g, i.x->sharedStates, 0x43f120, arg, bridge, &i);
        break;
    case 0x44d9f0:
        store(e, 0x50, 0);
        transition(s, i, "LS_HOME");
        break;
    case 0x44cfd0:
        claw_generic_enemy_entry(s, g, 0x43e9b0, 0, bridge, &i);
        if (word(s, i, 0x44c)) {
            if (word(s, i, 0x44c) != i.x->effectToken || !i.x->effectActor) {
                i.x->fault = 1;
                break;
            }
            i.x->effectActor[2] |= 0x10000;
            put(s, i, 0x44c, 0);
        }
        break;
    case 0x44df10:
        if (int32_t(random(s, i)) % 100 < 33 && a[0x38 / 4] != 0xffffffff)
            call(s, i, 0x48ce40, 0, {g->actorToken, e[0x410 / 4], 0});
        invoke(s, i, 0x440420);
        break;
    case 0x44edd0:
        if (bit(s, i, 2)) {
            virt(s, i, 0x48);
            break;
        }
        store(e, 0x50, load(e, 0x68) == load(e, 0x98) ? -120 : 120);
        face(s, load(e, 0x68) != load(e, 0x98));
        transition(s, i, "LS_PACING");
        sequence(s, i, e[0x34c / 4]);
        break;
    case 0x44f840:
        virt(s, i, 0x48);
        break;
    case 0x44ebb0:
    case 0x4a1180:
        face(s, e[0x18c / 4] == 2);
        store(e, 0x50,
              double(int32_t(e[0x18c / 4] == 3 ? 0u - e[(f == 0x44ebb0 ? 0x404 : 0x400) / 4]
                                               : e[(f == 0x44ebb0 ? 0x404 : 0x400) / 4])));
        transition(s, i, f == 0x44ebb0 ? "LS_FASTADVANCE" : "LS_ADVANCE");
        sequence(s, i, e[(f == 0x44ebb0 ? 0x30c : 0x308) / 4]);
        break;
    case 0x44f6e0: {
        transition(s, i, "LS_JUMPOFFSPRINGBOARD");
        put(s, i, 0x448, 0);
        store(e, 0x50, int32_t(random(s, i)) % 100 < 50 ? 100 : -100);
        store(e, 0x58, -1500);
        double y = sub(load(e, 0x70), 1), v = load(e, 0x58), acceleration = load(e, 0x40);
        if (acceleration != 0) {
            double square = sub(mul(v, v), mul(mul(sub(y, load(e, 0x70)), acceleration), -2));
            if (square < 0)
                square = 0;
            v = std::sqrt(square);
            if (load(e, 0x58) <= 0)
                v = -v;
        }
        store(e, 0x58, v);
        store(e, 0xb8, -1);
        store(e, 0x70, y);
        a[2] &= ~0x10u;
        a[0xcc / 4] = 8;
        sequence(s, i, e[0x33c / 4]);
        break;
    }
    case 0x44e120: {
        uint32_t dx = truncLow(load(e, 0x68)) - g->playerActor[0x4c / 4],
                 dy = truncLow(load(e, 0x70)) - g->playerActor[0x50 / 4];
        if (int32_t(dx * dx + dy * dy) < 0xf425) {
            face(s, e[0x18c / 4] == 2);
            a[0xcc / 4] = 8;
            transition(s, i, "LS_JUMPATCLAW");
            sequence(s, i, e[0x33c / 4]);
            bounds(s, i);
            audio(s, i, e[0x40c / 4]);
            aim(s, i, g->playerActor[0x4c / 4], g->playerActor[0x50 / 4]);
        } else {
            setBit(s, i, 2);
            virt(s, i, 0x48);
        }
        break;
    }
    case 0x44d760:
        bounds(s, i);
        virt(s, i, 0x60);
        if (arg != i.x->otherActorToken || !i.x->otherPrimary) {
            i.x->fault = 1;
            break;
        }
        aim(s, i, i.x->otherPrimary[0x2c / 4], i.x->otherPrimary[0x34 / 4]);
        break;
    case 0x44dd30: {
        const char *name = stateName(s, i, e[9]);
        if (name && !std::strcmp(name, "LS_PAUSE")) {
            virt(s, i, 0x78);
            break;
        }
        if (word(s, i, 0x42c) <= g->tick - word(s, i, 0x428)) {
            audio(s, i, e[0x3a4 / 4]);
            audio(s, i, e[0x38c / 4]);
            call(s, i, 0x42df90, g->enemyToken + 0x128);
            a[2] |= 0x10000;
            break;
        }
        claw_generic_enemy_state_entry(s, g, i.x->sharedStates, 0x43ff60, 0, bridge, &i);
        break;
    }
    case 0x44de50:
        animate(s, i);
        if (word(s, i, 0x42c) <= g->tick - word(s, i, 0x428)) {
            audio(s, i, e[0x3a4 / 4]);
            audio(s, i, e[0x38c / 4]);
            call(s, i, 0x42df90, g->enemyToken + 0x128);
            a[2] |= 0x10000;
        } else if (a[0xcc / 4] == 1)
            virt(s, i, 0x78);
        break;
    case 0x44e510:
        animate(s, i);
        face(s, e[0x18c / 4] == 2);
        if (a[0xcc / 4] == 1)
            virt(s, i, 0x44);
        break;
    case 0x44ea10:
        animate(s, i);
        if (a[0xcc / 4] == 1) {
            a[2] &= ~4u;
            virt(s, i, 0x44);
            e[8] = 2;
        }
        break;
    case 0x44f800:
        animate(s, i);
        if (a[0xcc / 4] == 1) {
            store(e, 0x50, 0);
            virt(s, i, 0x44);
        }
        break;
    case 0x44f490:
    case 0x44f660:
        animate(s, i);
        if (a[0x1a4 / 4] && a[0x19c / 4] == 0) {
            virt(s, i, 0x44);
            e[8] = 2;
        } else if (load(e, 0x50) != 0)
            store(e, 0x50, sub(load(e, 0x50), e[0x18c / 4] == 3 ? 25 : -25));
        break;
    case 0x44ea60:
        if (load(e, 0x68) == load(e, 0x80) || load(e, 0x68) == load(e, 0x98))
            virt(s, i, 0x48);
        face(s, e[0x18c / 4] == 2);
        store(e, 0x50, double(int32_t(e[0x18c / 4] == 3 ? 0u - e[0x400 / 4] : e[0x400 / 4])));
        animate(s, i);
        switch (e[0x184 / 4]) {
        case 0:
            invoke(s, i, 0x44ebb0);
            break;
        case 3:
        case 4:
        case 5:
        case 6:
            virt(s, i, 0x44);
            break;
        }
        break;
    case 0x44ec80:
        if ((load(e, 0x68) == load(e, 0x80) && e[0x18c / 4] == 3) ||
            (load(e, 0x68) == load(e, 0x98) && e[0x18c / 4] == 2))
            virt(s, i, 0x48);
        face(s, e[0x18c / 4] == 2);
        animate(s, i);
        random(s, i);
        switch (e[0x184 / 4]) {
        case 0:
        case 1:
        case 5:
            store(e, 0x50, double(int32_t(e[0x18c / 4] == 3 ? 0u - e[0x404 / 4] : e[0x404 / 4])));
            break;
        case 2:
            invoke(s, i, 0x4a1180);
            break;
        case 3:
        case 4:
            virt(s, i, 0x44);
            break;
        case 6:
            invoke(s, i, 0x44edd0);
            break;
        }
        break;
    case 0x44ef70:
        animate(s, i);
        if (load(e, 0x68) == load(e, 0x80)) {
            if (int32_t(random(s, i)) % 100 < 50)
                virt(s, i, 0x48);
            else {
                store(e, 0x50, 120);
                face(s, true);
            }
        }
        if (load(e, 0x68) == load(e, 0x98)) {
            if (int32_t(random(s, i)) % 100 < 50)
                virt(s, i, 0x48);
            else {
                store(e, 0x50, -120);
                face(s, false);
            }
        }
        if (!bit(s, i, 8)) {
            if (int32_t(e[0x184 / 4]) >= 0 && int32_t(e[0x184 / 4]) < 5)
                virt(s, i, 0x44);
        } else if (nearPlatform(s, i))
            virt(s, i, 0x44);
        break;
    case 0x44f290:
        animate(s, i);
        if (bit(s, i, 8) && nearPlatform(s, i))
            virt(s, i, 0x44);
        {
            int32_t v = int32_t(random(s, i));
            switch (e[0x184 / 4]) {
            case 0:
            case 1:
            case 2:
            case 3:
            case 4:
                virt(s, i, 0x44);
                break;
            case 5:
            case 6:
                if (v % 201 == 1 && word(s, i, 0x43c) <= g->tick - word(s, i, 0x438))
                    invoke(s, i, 0x44edd0);
                break;
            }
        }
        break;
    case 0x44da20: {
        const char *name = stateName(s, i, s->primary[7]);
        if (!name || std::strcmp(name, "LS_HOME"))
            break;
        face(s, e[0x18c / 4] == 2);
        int32_t v = int32_t(random(s, i));
        switch (e[0x184 / 4]) {
        case 0:
        case 1:
            invoke(s, i, 0x44ebb0);
            break;
        case 2:
            invoke(s, i, 0x4a1180);
            break;
        case 3:
        case 4:
            if (v % 421 < int32_t(e[0x2e4 / 4]))
                virt(s, i, 0x58);
            else {
                sequence(s, i, e[0x344 / 4]);
                animate(s, i);
                virt(s, i, 0x90, uint32_t(int32_t(random(s, i)) % 301 + 300), true);
            }
            break;
        case 5:
        case 6:
            invoke(s, i, 0x44edd0);
            break;
        }
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
uint32_t claw_human_enemy_private_word(const ClawHumanEnemy *s, const ClawHumanEnemyContext *x, uint32_t b) {
    if (b % 4)
        return 0;
    if (b < 0x420)
        return s->enemy[b / 4];
    if (b < 0x470 && x->privateTail)
        return x->privateTail[(b - 0x420) / 4];
    return 0;
}
void claw_human_enemy_set_private_word(ClawHumanEnemy *s, ClawHumanEnemyContext *x, uint32_t b, uint32_t v) {
    if (b % 4)
        return;
    if (b < 0x420)
        s->enemy[b / 4] = v;
    else if (b < 0x470 && x->privateTail)
        x->privateTail[(b - 0x420) / 4] = v;
}
uint32_t claw_human_enemy_entry(ClawHumanEnemy *s, ClawHumanEnemyContext *x, uint32_t f, uint32_t arg,
                                ClawGenericEnemyDependency d, void *u, uint32_t *r) {
    if (!s || !x || !x->generic || !x->sharedStates || !x->privateTail)
        return 0;
    x->fault = 0;
    Invocation i{x, d, u};
    uint32_t supported = run(s, i, f, arg, r);
    return supported && !x->fault;
}
uint32_t claw_human_enemy_construct(ClawHumanEnemy *s, ClawHumanEnemyContext *x, ClawGenericEnemyDependency d,
                                    void *u) {
    uint32_t r;
    return claw_human_enemy_entry(s, x, 0x44c000, 0, d, u, &r);
}
uint32_t claw_human_enemy_dispatch(ClawHumanEnemy *s, ClawHumanEnemyContext *x, int32_t id,
                                   ClawGenericEnemyDependency d, void *u) {
    uint32_t r;
    return claw_human_enemy_entry(s, x, 0x44c840, uint32_t(id), d, u, &r);
}
