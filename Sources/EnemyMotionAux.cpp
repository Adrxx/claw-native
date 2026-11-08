#include "EnemyMotionAux.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
namespace {
double load(const uint32_t *p, uint32_t b) {
    double v;
    std::memcpy(&v, p + b / 4, 8);
    return v;
}
void store(uint32_t *p, uint32_t b, double v) {
    std::memcpy(p + b / 4, &v, 8);
}
double sub(double a, double b) {
    volatile double v = a - b;
    return v;
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
    ClawEnemyMotionAuxContext *x;
    ClawGenericEnemyDependency dependency;
    void *user;
};
uint32_t run(ClawGenericEnemy *, Invocation &, uint32_t, uint32_t, uint32_t *);
uint64_t call(ClawGenericEnemy *s, Invocation &i, uint32_t f, uint32_t receiver,
              std::initializer_list<uint32_t> args = {}, const char *name = nullptr) {
    ClawGenericEnemyCall c{};
    c.function = f;
    c.receiver = receiver;
    c.argumentCount = uint32_t(args.size());
    c.name = name;
    std::copy(args.begin(), args.end(), c.arguments);
    return i.dependency ? i.dependency(s, i.x->human->generic, &c, i.user) : 0;
}
uint64_t bridge(ClawGenericEnemy *s, ClawGenericEnemyContext *g, const ClawGenericEnemyCall *c, void *user) {
    auto &i = *static_cast<Invocation *>(user);
    uint32_t r = 0;
    if (c->receiver == g->enemyToken && run(s, i, c->function, c->argumentCount ? c->arguments[0] : 0, &r))
        return r;
    return i.dependency ? i.dependency(s, g, c, i.user) : 0;
}
bool state(ClawGenericEnemy *s, Invocation &i, const char *name) {
    auto *g = i.x->human->generic;
    if (i.dependency) {
        s->primary[7] = uint32_t(call(s, i, 0x4dba00, 0x537668, {}, name));
        return true;
    }
    for (size_t n = 0; n < g->stateCount; ++n)
        if (g->states[n].name && !std::strcmp(g->states[n].name, name)) {
            s->primary[7] = uint32_t(g->states[n].state);
            return true;
        }
    i.x->fault = 1;
    return false;
}
void select(ClawGenericEnemy *s, Invocation &i, uint32_t offset) {
    s->enemy[0x134 / 4] = s->actor[0x190 / 4];
    call(s, i, 0x4c8220, i.x->human->generic->actorToken + 0x188, {s->enemy[offset / 4]});
}
void animate(ClawGenericEnemy *s, Invocation &i) {
    call(s, i, 0x4c82a0, i.x->human->generic->actorToken + 0x188, {i.x->human->generic->animationDelta});
}
void restore(ClawGenericEnemy *s) {
    s->actor[0x50 / 4] += s->actor[0x124 / 4] - s->enemy[0x27c / 4];
    std::copy(s->enemy + 0x270 / 4, s->enemy + 0x280 / 4, s->actor + 0x118 / 4);
}
uint32_t worldProbe(Invocation &i, uint32_t x, uint32_t y) {
    auto *w = i.x->world;
    if (!w || !w->cells || !w->rowOffsets || !w->descriptions || w->width <= 0 || w->height <= 0 || w->shiftX > 30 ||
        w->shiftY > 30) {
        i.x->fault = 2;
        return 0;
    }
    return claw_world_point_attribute(w->cells, w->rowOffsets, w->width, w->height, w->shiftX, w->shiftY,
                                      w->descriptions, w->descriptionCount, x, y, 0, 0);
}
uint32_t probe(ClawGenericEnemy *s, Invocation &i, uint32_t x, uint32_t y) {
    return i.dependency ? uint32_t(call(s, i, 0x4207f0, i.x->human->generic->tileManagerToken, {x, y}))
                        : worldProbe(i, x, y);
}
bool ground(ClawGenericEnemy *s, Invocation &i, uint32_t offset, uint32_t y) {
    return probe(s, i, s->actor[0x4c / 4] + offset, y) == 1 || probe(s, i, s->actor[0x4c / 4] + offset, y) == 2 ||
           probe(s, i, s->actor[0x4c / 4] + offset, y) == 3;
}
uint32_t ledge(ClawGenericEnemy *s, Invocation &i) {
    uint32_t y = s->actor[0x50 / 4] + s->actor[0x124 / 4] + 1;
    if (!ground(s, i, 0, y) || probe(s, i, s->actor[0x4c / 4], y - 1) != 0)
        return 0;
    for (int32_t left = -1; left > -50; --left) {
        y = s->actor[0x50 / 4] + s->actor[0x124 / 4] + 1;
        const uint32_t first = worldProbe(i, s->actor[0x4c / 4] + uint32_t(left), y);
        if (i.x->fault)
            return 0;
        const bool supported = first == 1 || probe(s, i, s->actor[0x4c / 4] + uint32_t(left), y) == 2 ||
                               probe(s, i, s->actor[0x4c / 4] + uint32_t(left), y) == 3;
        if (!supported || probe(s, i, s->actor[0x4c / 4] + uint32_t(left), y - 1) != 0) {
            for (uint32_t right = 1; right < 50; ++right) {
                y = s->actor[0x50 / 4] + s->actor[0x124 / 4] + 1;
                if (!ground(s, i, right, y) || probe(s, i, s->actor[0x4c / 4] + right, y - 1) != 0)
                    return 1;
            }
            return 0;
        }
    }
    return 0;
}
uint32_t run(ClawGenericEnemy *s, Invocation &i, uint32_t f, uint32_t arg, uint32_t *result) {
    if (result)
        *result = 0;
    auto *e = s->enemy;
    auto *a = s->actor;
    auto *g = i.x->human->generic;
    switch (f) {
    case 0x43eab0:
        if (result)
            *result = ledge(s, i);
        else
            ledge(s, i);
        return 1;
    case 0x440420: {
        e[8] = 1;
        e[9] = s->primary[7];
        if (!state(s, i, "LS_LIFTED"))
            return 1;
        e[6] = 0x440710;
        e[7] = s->primary[7];
        a[0xcc / 4] = 7;
        const double target = sub(load(e, 0x70), 1), acceleration = load(e, 0x40), velocity = load(e, 0x58);
        double v = velocity;
        if (acceleration != 0) {
            v = sub(mul(velocity, velocity), mul(mul(sub(target, load(e, 0x70)), acceleration), -2));
            if (v < 0)
                v = 0;
            v = std::sqrt(v);
            if (velocity <= 0)
                v = -v;
        }
        store(e, 0x58, v);
        store(e, 0xb8, -1);
        store(e, 0x70, sub(load(e, 0x70), 1));
        for (uint32_t offset : {0x80u, 0x88u, 0x90u})
            std::copy(g->defaults, g->defaults + 2, e + offset / 4);
        for (uint32_t offset : {0x98u, 0xa0u, 0xa8u})
            std::copy(g->defaults + 2, g->defaults + 4, e + offset / 4);
        e[0xc8 / 4] = 1;
        a[2] |= 2;
        e[0x2cc / 4] = 0;
        e[0x284 / 4] = truncLow(load(e, 0x70)) + a[0x124 / 4];
        a[2] |= 4;
        std::copy(a + 0x118 / 4, a + 0x128 / 4, e + 0x270 / 4);
        std::copy(e + 0x260 / 4, e + 0x270 / 4, a + 0x118 / 4);
        return 1;
    }
    case 0x440710:
    case 0x440350:
        e[8] = 2;
        a[2] &= ~2u;
        if (f == 0x440710)
            a[0xcc / 4] = 8;
        else
            store(e, 0x50, 0);
        restore(s);
        a[0xd0 / 4] = 4;
        a[2] &= ~4u;
        select(s, i, 0x344);
        animate(s, i);
        return 1;
    case 0x440120: {
        e[8] = 1;
        e[6] = 0x440350;
        e[7] = s->primary[7];
        select(s, i, 0x380);
        e[9] = s->primary[7];
        if (!state(s, i, "LS_THROWN"))
            return 1;
        a[0xcc / 4] = 8;
        a[2] |= 4;
        a[0xd0 / 4] = 0x10;
        store(e, 0x50, 0);
        store(e, 0x58, 0);
        store(e, 0x60, 0);
        e[0xc8 / 4] = 0;
        const uint32_t weight = e[0x1ac / 4], scale = i.x->strongThrow ? 20 : 2;
        uint32_t vx = i.x->strongThrow ? (weight + 2) * 100 : weight * 3 + 200;
        if (i.x->human->sharedStates->playerPrivate[0] == 0)
            vx = 0u - vx;
        store(e, 0x50, double(int32_t(vx)));
        store(e, 0x58, double(int32_t(0u - 600 - scale * weight)));
        store(e, 0x60, 0);
        return 1;
    }
    case 0x4407d0:
        select(s, i, 0x37c);
        e[9] = s->primary[7];
        if (!state(s, i, "LS_FLAILING"))
            return 1;
        store(e, 0x68,
              double(int32_t(e[(i.x->human->sharedStates->playerPrivate[0] == 0 ? 0x2b4 : 0x2b8) / 4] +
                             g->playerActor[0x4c / 4])));
        store(e, 0x70, double(int32_t(e[0x2bc / 4] + g->playerActor[0x50 / 4])));
        return 1;
    case 0x4409d0:
        e[8] = 1;
        e[9] = s->primary[7];
        if (!state(s, i, "LS_DROPPED"))
            return 1;
        a[0xcc / 4] = 8;
        a[2] |= 5;
        e[0xc8 / 4] = 0;
        e[0x3f4 / 4] = 1000;
        e[0x3f0 / 4] = g->tick;
        return 1;
    case 0x440410:
        e[0x2cc / 4] = 1;
        return 1;
    case 0x4405b0:
    case 0x440260:
    case 0x440870:
    case 0x440a50:
        return claw_generic_enemy_state_entry(s, g, i.x->human->sharedStates, f, arg, bridge, &i);
    default:
        return 0;
    }
}
} // namespace
extern "C" uint32_t claw_enemy_motion_aux_entry(ClawGenericEnemy *s, ClawEnemyMotionAuxContext *x, uint32_t f,
                                                uint32_t arg, ClawGenericEnemyDependency d, void *user,
                                                uint32_t *result) {
    if (!s || !x || !x->human || !x->human->generic || !x->human->sharedStates)
        return 0;
    Invocation i{x, d, user};
    return run(s, i, f, arg, result);
}
