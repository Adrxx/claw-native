#include "BouncingGoodieLogic.h"
#include "PlayerPhysics.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
namespace {
double load(const uint32_t *p, uint32_t o) {
    double v;
    std::memcpy(&v, p + o / 4, 8);
    return v;
}
void store(uint32_t *p, uint32_t o, double v) {
    std::memcpy(p + o / 4, &v, 8);
}
double sub(double a, double b) {
    volatile double v = a - b;
    return v;
}
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
struct Run {
    ClawBouncingGoodieContext *x;
    ClawGenericEnemyDependency d;
    void *user;
    uint32_t depth = 0, guard = 0;
};
uint32_t execute(ClawBouncingGoodie *, Run &, uint32_t, uint32_t, uint32_t *);
uint64_t external(ClawBouncingGoodie *s, Run &r, const ClawGenericEnemyCall *c) {
    if (r.depth)
        s->enemy[0x2fc / 4] = r.guard;
    uint64_t v = r.d ? r.d(s, r.x->generic, c, r.user) : 0;
    if (r.depth) {
        r.guard = s->enemy[0x2fc / 4];
        s->enemy[0x2fc / 4] = 0;
    }
    return v;
}
uint64_t call(ClawBouncingGoodie *s, Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr) {
    ClawGenericEnemyCall c{};
    c.function = f;
    c.receiver = receiver;
    c.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), c.arguments);
    c.name = name;
    return external(s, r, &c);
}
uint64_t bridge(ClawGenericEnemy *s, ClawGenericEnemyContext *, const ClawGenericEnemyCall *c, void *user) {
    auto &r = *static_cast<Run *>(user);
    uint32_t v;
    if (c->receiver == r.x->generic->enemyToken &&
        execute(s, r, c->function, c->argumentCount ? c->arguments[0] : 0, &v))
        return v;
    return external(s, r, c);
}
uint32_t common(ClawBouncingGoodie *s, Run &r, uint32_t f, uint32_t arg) {
    if (!r.depth++) {
        r.guard = s->enemy[0x2fc / 4];
        s->enemy[0x2fc / 4] = 0;
    }
    uint32_t supported = claw_generic_enemy_entry(s, r.x->generic, f, arg, bridge, &r);
    if (!--r.depth)
        s->enemy[0x2fc / 4] = r.guard;
    return supported;
}
void invoke(ClawBouncingGoodie *s, Run &r, uint32_t f, uint32_t arg = 0, bool has = false) {
    uint32_t v;
    if (execute(s, r, f, arg, &v) || common(s, r, f, arg))
        return;
    if (has)
        call(s, r, f, r.x->generic->enemyToken, {arg});
    else
        call(s, r, f, r.x->generic->enemyToken);
}
void virt(ClawBouncingGoodie *s, Run &r, uint32_t slot, uint32_t arg = 0, bool has = false) {
    invoke(s, r, r.x->generic->virtualFunctions[slot / 4], arg, has);
}
uint32_t stateID(ClawBouncingGoodie *s, Run &r, const char *name) {
    if (r.d)
        return uint32_t(call(s, r, 0x4dba00, 0x537668, {}, name));
    auto *g = r.x->generic;
    for (size_t n = 0; n < g->stateCount; ++n)
        if (g->states[n].name && !std::strcmp(g->states[n].name, name))
            return uint32_t(g->states[n].state);
    r.x->fault = 1;
    return 0;
}
const ClawGenericEnemyState *state(Run &r, uint32_t id) {
    auto *g = r.x->generic;
    for (size_t n = 0; n < g->stateCount; ++n)
        if (uint32_t(g->states[n].state) == id)
            return g->states + n;
    r.x->fault = 1;
    return nullptr;
}
void begin(ClawBouncingGoodie *s, Run &r, const char *name) {
    s->enemy[9] = s->primary[7];
    s->primary[7] = stateID(s, r, name);
}
void rect(ClawBouncingGoodie *s, Run &r, uint32_t offset) {
    if (!s->actor[0x174 / 4])
        return;
    auto *h = r.x->imageHeader;
    auto *a = s->actor + offset / 4;
    a[0] = h[8] - h[6];
    a[1] = h[9] - h[7];
    a[2] = h[8] - 1 + h[6];
    a[3] = h[9] - 1 + h[7];
}
void sequence(ClawBouncingGoodie *s, Run &r, uint32_t token) {
    s->enemy[0x134 / 4] = s->actor[0x190 / 4];
    call(s, r, 0x4c8220, r.x->generic->actorToken + 0x188, {token});
}
void animate(ClawBouncingGoodie *s, Run &r) {
    call(s, r, 0x4c82a0, r.x->generic->actorToken + 0x188, {r.x->generic->animationDelta});
}
void audio(ClawBouncingGoodie *s, Run &r) {
    uint32_t token = s->enemy[0x188 / 4];
    auto *x = r.x->shared;
    if (!token || !x || !x->audioEnabled)
        return;
    for (size_t n = 0; n < x->resourceCount; ++n)
        if (x->resources[n].token == token) {
            call(s, r, 0x4b45f0, x->resources[n].controllerToken, {x->audioPosition, 0, 0, 0});
            return;
        }
    r.x->fault = 1;
}
void enable(ClawBouncingGoodie *s, Run &r) {
    auto *x = r.x->loot;
    auto *a = s->actor;
    auto *g = r.x->generic;
    if (!x) {
        call(s, r, 0x4736b0, 0, {g->actorToken});
        return;
    }
    if (!x->words[340])
        call(s, r, 0x4719e0, 0, {a[0xc / 4]});
    uint32_t n = 0;
    for (; int32_t(n) < int32_t(x->itemCount); ++n) {
        if (n >= 66) {
            r.x->fault = 1;
            return;
        }
        if (x->words[n] == a[0x170 / 4])
            break;
    }
    if (int32_t(n) < int32_t(x->itemCount)) {
        a[1] = n ? n : 33;
        a[0xfc / 4] = x->words[66 + n];
        s->primary[0x168 / 4] = x->words[274 + n];
        if (a[0xd0 / 4] == 1)
            a[0xd0 / 4] = x->words[132 + n];
    } else {
        a[1] = 0;
        a[0xfc / 4] = 100;
        s->primary[0x168 / 4] = 0;
    }
    a[2] &= ~1u;
    rect(s, r, 0x138);
    a[0x13c / 4] -= 10;
}
void pickup(ClawBouncingGoodie *s, Run &r) {
    s->enemy[0xc8 / 4] = 1;
    sequence(s, r, 0);
    s->actor[2] &= ~2u;
    call(s, r, 0x473660, 0, {s->enemy[2], s->enemy[0x184 / 4]});
}
uint32_t construct(ClawBouncingGoodie *s, Run &r) {
    auto *e = s->enemy;
    auto *a = s->actor;
    auto *l = s->primary;
    auto *g = r.x->generic;
    e[0] = 0x50b064;
    e[2] = e[3] = g->actorToken;
    e[4] = a[0x6c / 4];
    e[1] = 0;
    call(s, r, 0x4c7fa0, g->actorToken, {}, "LogicHit");
    call(s, r, 0x4c8060, g->actorToken, {}, "LogicAttack");
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
    for (uint32_t o : {0x80u, 0x88u, 0x98u, 0xa0u}) {
        uint32_t source = o == 0x80 ? 0x2c : o == 0x88 ? 0x34 : o == 0x98 ? 0x30 : 0x38;
        store(e, o, l[source / 4] ? double(int32_t(l[source / 4])) : load(g->defaults, o < 0x90 ? 0 : 8));
    }
    store(e, 0x68, double(int32_t(a[0x4c / 4])));
    store(e, 0x70, double(int32_t(a[0x50 / 4])));
    store(e, 0x78, 0);
    store(e, 0x50, double(int32_t(a[0x148 / 4])));
    store(e, 0x58, double(int32_t(a[0x14c / 4])));
    store(e, 0x60, 0);
    for (uint32_t o : {0x38u, 0x40u, 0x48u})
        store(e, o, 0);
    store(e, 0x28, mul(double(g->tick), 0.001));
    store(e, 0x30, 0);
    for (uint32_t o : {0xe8u, 0xf0u, 0xf8u})
        store(e, o, double(g->defaults[12]));
    e[0x120 / 4] = e[0x124 / 4] = 0;
    a[0xcc / 4] = 7;
    common(s, r, 0x4dca10, 0);
    e[0x128 / 4] = e[0x12c / 4] = e[0x178 / 4] = e[0x17c / 4] = g->actorToken;
    e[0x130 / 4] = e[0x180 / 4] = a[0x6c / 4];
    e[0x14c / 4] = e[0x150 / 4] = 0;
    const uint32_t offsets[] = {0xf0, 0xf8, 0xf4, 0xfc, 0x100, 0x108, 0x104, 0x10c, 0x100};
    for (uint32_t n = 0; n < 9; ++n) {
        uint32_t v = n == 8 ? a[offsets[n] / 4] : l[offsets[n] / 4];
        e[(0x154 + n * 4) / 4] = v;
        ++e[0x14c / 4];
        if (v)
            ++e[0x150 / 4];
    }
    e[0x198 / 4] = e[0x19c / 4] = 0;
    e[0] = 0x50b68c;
    e[0x18c / 4] =
        a[0x190 / 4] ? a[0x190 / 4] : uint32_t(call(s, r, 0x4f6286, r.x->sequenceRegistryToken, {}, "GAME_CYCLE100"));
    e[0x190 / 4] = e[0x194 / 4] = 0;
    if (!a[0x174 / 4]) {
        r.x->fault = 2;
        return g->enemyToken;
    }
    rect(s, r, 0x118);
    a[0x118 / 4] -= 10;
    a[0x11c / 4] -= 10;
    a[0x120 / 4] += 10;
    rect(s, r, 0x128);
    e[0x188 / 4] = uint32_t(call(s, r, 0x4f6286, g->soundRegistryToken, {}, "GAME_PUBOUNCE1"));
    if (!a[0x64 / 4]) {
        a[0x64 / 4] = 1000;
        a[2] |= 0x20000;
    }
    if (e[1]) {
        if (!r.x->scene.lookup) {
            r.x->fault = 2;
            return g->enemyToken;
        }
        auto *owner = r.x->scene.lookup(r.x->scene.context, e[1], 4);
        auto *ownerActor = owner ? r.x->scene.lookup(r.x->scene.context, owner[3], 128) : nullptr;
        if (!ownerActor) {
            r.x->fault = 2;
            return g->enemyToken;
        }
        uint32_t z = ownerActor[0x64 / 4] + 500;
        if (a[0x64 / 4] != z) {
            a[0x64 / 4] = z;
            a[2] |= 0x20000;
        }
    }
    for (uint32_t o : {0x80u, 0x88u, 0x90u})
        std::copy(g->defaults, g->defaults + 2, e + o / 4);
    for (uint32_t o : {0x98u, 0xa0u, 0xa8u})
        std::copy(g->defaults + 2, g->defaults + 4, e + o / 4);
    a[0xcc / 4] = 7;
    a[2] |= 3;
    a[0xd0 / 4] = 1;
    uint32_t v;
    execute(s, r, 0x40efa0, 0, &v);
    return g->enemyToken;
}
uint32_t execute(ClawBouncingGoodie *s, Run &r, uint32_t f, uint32_t arg, uint32_t *result) {
    uint32_t value = 0;
    auto *e = s->enemy;
    auto *a = s->actor;
    auto *g = r.x->generic;
    switch (f) {
    case 0x40e750:
        value = construct(s, r);
        break;
    case 0x40efa0:
        sequence(s, r, e[0x18c / 4]);
        begin(s, r, "LS_FALLING");
        a[0xcc / 4] = 8;
        e[0x19c / 4] = 125;
        e[0x198 / 4] = g->tick;
        break;
    case 0x40f010:
        animate(s, r);
        if (g->tick - e[0x198 / 4] >= e[0x19c / 4] && !e[0x190 / 4]) {
            e[0x190 / 4] = 1;
            enable(s, r);
        }
        if (a[0x164 / 4] & 0x200)
            pickup(s, r);
        else if (a[0xcc / 4] == 1) {
            enable(s, r);
            execute(s, r, 0x40f0e0, 0, &value);
        }
        break;
    case 0x40f0e0: {
        ++e[0x194 / 4];
        audio(s, r);
        begin(s, r, "LS_BOUNCE");
        a[0xcc / 4] = 8;
        const double target = sub(load(e, 0x70), 1), acceleration = load(e, 0x40), old = load(e, 0x58);
        double velocity = old;
        if (acceleration != 0) {
            velocity = sub(mul(old, old), mul(mul(sub(target, load(e, 0x70)), acceleration), -2));
            if (velocity < 0)
                velocity = 0;
            velocity = std::sqrt(velocity);
            if (old <= 0)
                velocity = -velocity;
        }
        store(e, 0x58, velocity);
        store(e, 0xb8, -1);
        store(e, 0x70, target);
        store(e, 0x60, 0);
        store(e, 0x58, mul(load(e, 0x58), -0.5));
        if (load(e, 0x58) < -500)
            store(e, 0x58, -500);
        break;
    }
    case 0x40f200:
        animate(s, r);
        if (!(a[0x164 / 4] & 0x200) && int32_t(e[0x194 / 4]) < 4) {
            if (a[0xcc / 4] == 1)
                execute(s, r, 0x40f0e0, 0, &value);
        } else
            pickup(s, r);
        break;
    case 0x40f390:
        begin(s, r, "LS_DEAD");
        e[8] = 1;
        e[0xc8 / 4] = 1;
        a[0x48 / 4] = 30;
        a[0x44 / 4] = 0;
        a[0x40 / 4] |= 8;
        e[0x19c / 4] = 1000;
        e[0x198 / 4] = g->tick;
        break;
    case 0x40f400:
        animate(s, r);
        if (g->tick - e[0x198 / 4] >= e[0x19c / 4])
            a[2] |= 0x10000;
        break;
    case 0x40f2a0:
        common(s, r, 0x4dca10, 0);
        if (e[0x120 / 4] & 0x100000) {
            auto *v = state(r, s->primary[7]);
            if (v && v->name && std::strcmp(v->name, "LS_DEAD"))
                execute(s, r, 0x40f390, 0, &value);
        }
        break;
    case 0x40ebe0: {
        const ClawGenericEnemyState *v = nullptr;
        for (size_t n = 0; n < r.x->stateCount; ++n)
            if (uint32_t(r.x->states[n].state) == arg) {
                v = r.x->states + n;
                break;
            }
        if (!v) {
            r.x->fault = 1;
            break;
        }
        if (v->function)
            invoke(s, r, v->function);
        else
            call(s, r, 0x4a36f0, 0, {g->enemyToken});
        break;
    }
    case 0x4736b0:
        enable(s, r);
        break;
    case 0x4dc870: {
        const uint32_t id = s->primary[7];
        auto *v = state(r, id);
        if (!v)
            break;
        virt(s, r, 4, v->nameToken, true);
        virt(s, r, 8, id, true);
        v = state(r, id);
        if (v)
            virt(s, r, 12, v->nameToken, true);
        value = 1;
        break;
    }
    case 0x484d90: {
        const uint32_t token = g->enemyToken;
        e[0] = 0x50b014;
        if (arg & 1) {
            if (r.x->scene.free)
                r.x->scene.free(r.x->scene.context, token);
            else
                call(s, r, 0x4f6428, 0, {token});
        }
        value = token;
        break;
    }
    case 0x456030:
        e[0] = 0x50b014;
        break;
    case 0x4c9e30:
    case 0x4c96b0:
    case 0x4bb030:
        break;
    case 0x4063b0:
        common(s, r, f, arg);
        break;
    default:
        return 0;
    }
    if (result)
        *result = value;
    return 1;
}
} // namespace
extern "C" void claw_bouncing_goodie_context_defaults(ClawBouncingGoodieContext *x) {
    if (!x || !x->generic)
        return;
    const uint32_t v[] = {0x484d90, 0x4c9e30, 0x40ebe0, 0x4063b0, 0x4c96b0,
                          0x4bb030, 0x4bb030, 0x4c96b0, 0x4c96b0, 0x40f2a0};
    std::copy(v, v + 10, x->generic->virtualFunctions);
}
extern "C" uint32_t claw_bouncing_goodie_entry(ClawBouncingGoodie *s, ClawBouncingGoodieContext *x, uint32_t f,
                                               uint32_t arg, ClawGenericEnemyDependency d, void *user,
                                               uint32_t *result) {
    if (!s || !x || !x->generic)
        return 0;
    Run r{x, d, user};
    return execute(s, r, f, arg, result);
}
extern "C" uint32_t claw_bouncing_goodie_callback(ClawBouncingGoodie *s, ClawBouncingGoodieContext *x,
                                                  ClawGenericEnemyDependency d, void *user) {
    if (!s || !x || !x->generic)
        return 0;
    Run r{x, d, user};
    uint32_t mode = s->primary[7], result = 0;
    if (mode == 0) {
        s->primary[7] = 1000;
        uint32_t token =
            x->scene.allocate ? x->scene.allocate(x->scene.context, 0x1a0) : uint32_t(call(s, r, 0x4f63ec, 0, {0x1a0}));
        if (!token) {
            x->fault = 2;
            return 0;
        }
        x->generic->enemyToken = token;
        construct(s, r);
        virt(s, r, 0x10);
        s->primary[6] = token;
    } else if (mode == 29)
        virt(s, r, 0x20);
    else if (mode == 30)
        virt(s, r, 0x1c);
    else if (mode != 1000)
        execute(s, r, 0x4dc870, 0, &result);
    return 1;
}
