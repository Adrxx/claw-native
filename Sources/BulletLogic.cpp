#include "BulletLogic.h"
#include "PlayerPhysics.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
namespace {
struct Run {
    ClawBulletContext *x;
    ClawGenericEnemyDependency d;
    void *user;
    uint32_t depth = 0, guard = 0;
};
uint32_t execute(ClawBullet *, Run &, uint32_t, uint32_t, uint32_t *);
double load(const uint32_t *p, uint32_t off) {
    double value;
    std::memcpy(&value, p + off / 4, 8);
    return value;
}
void store(uint32_t *p, uint32_t off, double value) {
    std::memcpy(p + off / 4, &value, 8);
}
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
uint64_t external(ClawBullet *s, Run &r, const ClawGenericEnemyCall *e) {
    if (r.depth)
        s->enemy[0x2fc / 4] = r.guard;
    uint64_t value = 0;
    if (r.d)
        value = r.d(s, r.x->generic, e, r.user);
    else
        r.x->fault = 1;
    if (r.depth) {
        r.guard = s->enemy[0x2fc / 4];
        s->enemy[0x2fc / 4] = 0;
    }
    return value;
}
uint64_t call(ClawBullet *s, Run &r, uint32_t fn, uint32_t receiver, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr) {
    ClawGenericEnemyCall e{};
    e.function = fn;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    e.name = name;
    std::copy(args.begin(), args.end(), e.arguments);
    return external(s, r, &e);
}
uint64_t bridge(ClawGenericEnemy *s, ClawGenericEnemyContext *, const ClawGenericEnemyCall *e, void *p) {
    auto &r = *static_cast<Run *>(p);
    uint32_t value;
    if (e->receiver == r.x->generic->enemyToken &&
        execute(s, r, e->function, e->argumentCount ? e->arguments[0] : 0, &value))
        return value;
    return external(s, r, e);
}
uint32_t common(ClawBullet *s, Run &r, uint32_t fn, uint32_t arg) {
    if (!r.depth++) {
        r.guard = s->enemy[0x2fc / 4];
        s->enemy[0x2fc / 4] = 0;
    }
    uint32_t support = fn == 0x4dc870 ? claw_generic_enemy_tick(s, r.x->generic, bridge, &r)
                                      : claw_generic_enemy_entry(s, r.x->generic, fn, arg, bridge, &r);
    if (!--r.depth)
        s->enemy[0x2fc / 4] = r.guard;
    return support;
}
void invoke(ClawBullet *s, Run &r, uint32_t fn, uint32_t arg = 0, bool hasArg = false) {
    uint32_t value;
    if (execute(s, r, fn, arg, &value))
        return;
    if (hasArg)
        call(s, r, fn, r.x->generic->enemyToken, {arg});
    else
        call(s, r, fn, r.x->generic->enemyToken);
}
void virt(ClawBullet *s, Run &r, uint32_t off, uint32_t arg = 0, bool hasArg = false) {
    invoke(s, r, r.x->generic->virtualFunctions[off / 4], arg, hasArg);
}
uint32_t stateID(ClawBullet *s, Run &r, const char *name) {
    auto *g = r.x->generic;
    if (r.d)
        return uint32_t(call(s, r, 0x4dba00, 0x537668, {}, name));
    for (size_t n = 0; n < g->stateCount; ++n)
        if (g->states[n].name && !std::strcmp(g->states[n].name, name))
            return uint32_t(g->states[n].state);
    r.x->fault = 1;
    return 0;
}
const uint32_t *root(Run &r, uint32_t token) {
    if (r.x->scene.lookup) {
        auto *p = r.x->scene.lookup(r.x->scene.context, token, 27);
        if (!p)
            r.x->fault = 1;
        return p;
    }
    if (token != r.x->imageRootToken) {
        r.x->fault = 1;
        return nullptr;
    }
    return r.x->imageRootHeader;
}
const uint32_t *leaf(Run &r, uint32_t token) {
    if (r.x->scene.lookup) {
        auto *p = r.x->scene.lookup(r.x->scene.context, token, 10);
        if (!p)
            r.x->fault = 1;
        return p;
    }
    if (token != r.x->imageLeafToken) {
        r.x->fault = 1;
        return nullptr;
    }
    return r.x->imageLeafHeader;
}
void selectFirst(ClawBullet *s, Run &r) {
    uint32_t token = s->actor[0x170 / 4];
    if (!token)
        return;
    const uint32_t *h = root(r, token);
    if (!h)
        return;
    uint32_t id = h[0x64 / 4];
    s->actor[0x16c / 4] = id;
    uint32_t frame = 0;
    if (int32_t(id) >= int32_t(h[0x64 / 4]) && int32_t(id) <= int32_t(h[0x68 / 4])) {
        if (r.x->scene.lookup) {
            auto *p = r.x->scene.lookup(r.x->scene.context, h[0x14 / 4] + id * 4, 1);
            if (!p) {
                r.x->fault = 1;
                return;
            }
            frame = *p;
        } else {
            int64_t index = int64_t(int32_t(id)) - r.x->imageFrameOrigin;
            if (index < 0 || uint64_t(index) >= r.x->imageFrameCount || !r.x->imageFrames) {
                r.x->fault = 1;
                return;
            }
            frame = r.x->imageFrames[index];
        }
    }
    s->actor[0x174 / 4] = frame;
}
uint32_t setImage(ClawBullet *s, Run &r, uint32_t literal) {
    const char *name = literal == 0x524130 ? "GAME_BULLETS" : literal == 0x52c4a0 ? "LEVEL_MUSKETBALL" : nullptr;
    if (!name)
        return 0;
    uint32_t registry = r.x->imageRegistryToken;
    if (r.x->scene.lookup) {
        auto *p = r.x->scene.lookup(r.x->scene.context, s->actor[3] + 0x10, 1);
        if (!p) {
            r.x->fault = 1;
            return 1;
        }
        registry = *p + 0x10;
    }
    s->actor[0x170 / 4] = uint32_t(call(s, r, 0x4f6286, registry, {}, name));
    selectFirst(s, r);
    return 1;
}
void rect(ClawBullet *s, Run &r, uint32_t off) {
    uint32_t token = s->actor[0x174 / 4];
    if (!token)
        return;
    const uint32_t *h = leaf(r, token);
    if (!h)
        return;
    s->actor[off / 4] = h[8] - h[6];
    s->actor[(off + 4) / 4] = h[9] - h[7];
    s->actor[(off + 8) / 4] = h[8] - 1 + h[6];
    s->actor[(off + 12) / 4] = h[7] - 1 + h[9];
}
uint32_t base(ClawBullet *s, Run &r) {
    auto *g = r.x->generic;
    auto *e = s->enemy;
    auto *a = s->actor;
    auto *l = s->primary;
    uint32_t receiver = g->enemyToken;
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
    for (uint32_t off : {0x80u, 0x88u, 0x98u, 0xa0u}) {
        uint32_t source = off == 0x80 ? 0x2c : off == 0x88 ? 0x34 : off == 0x98 ? 0x30 : 0x38;
        store(e, off, l[source / 4] ? double(int32_t(l[source / 4])) : load(g->defaults, off < 0x90 ? 0 : 8));
    }
    store(e, 0x68, double(int32_t(a[0x4c / 4])));
    store(e, 0x70, double(int32_t(a[0x50 / 4])));
    store(e, 0x78, 0);
    store(e, 0x50, double(int32_t(a[0x148 / 4])));
    store(e, 0x58, double(int32_t(a[0x14c / 4])));
    store(e, 0x60, 0);
    for (uint32_t off : {0x38u, 0x40u, 0x48u, 0x30u})
        store(e, off, 0);
    store(e, 0x28, mul(double(g->tick), 0.001));
    for (uint32_t off : {0xe8u, 0xf0u, 0xf8u})
        store(e, off, double(g->defaults[12]));
    e[0x120 / 4] = e[0x124 / 4] = 0;
    a[0xcc / 4] = 7;
    common(s, r, 0x4dca10, 0);
    e[0x128 / 4] = e[0x12c / 4] = g->actorToken;
    e[0x130 / 4] = a[0x6c / 4];
    e[0] = 0x50ee8c;
    a[2] |= 0x60;
    a[0x164 / 4] |= 0x2000;
    e[0x148 / 4] = 0;
    for (uint32_t off : {0x80u, 0x88u, 0x90u})
        std::memcpy(e + off / 4, g->defaults, 8);
    for (uint32_t off : {0x98u, 0xa0u, 0xa8u})
        std::memcpy(e + off / 4, g->defaults + 2, 8);
    return receiver;
}
uint32_t execute(ClawBullet *s, Run &r, uint32_t fn, uint32_t arg, uint32_t *result) {
    auto *g = r.x->generic;
    auto *e = s->enemy;
    auto *a = s->actor;
    uint32_t value = 0;
    switch (fn) {
    case 0x4c7970:
        if (!setImage(s, r, arg))
            return 0;
        break;
    case 0x473c50:
        value = base(s, r);
        break;
    case 0x4107c0:
        value = base(s, r);
        e[0] = 0x50b714;
        store(e, 0x40, 0);
        if (!a[0x170 / 4]) {
            setImage(s, r, 0x524130);
            selectFirst(s, r);
        }
        break;
    case 0x4741f0:
        rect(s, r, 0x118);
        rect(s, r, 0x138);
        virt(s, r, 0x28);
        break;
    case 0x474290:
        e[9] = s->primary[7];
        s->primary[7] = stateID(s, r, "LS_FALLING");
        if (e[0x148 / 4]) {
            e[0x134 / 4] = a[0x190 / 4];
            call(s, r, 0x4c8220, g->actorToken + 0x188, {e[0x148 / 4]});
        }
        a[0xcc / 4] = 8;
        break;
    case 0x4742f0:
        if (e[0x148 / 4])
            call(s, r, 0x4c82a0, g->actorToken + 0x188, {g->animationDelta});
        if (e[0x120 / 4] & 0x10000)
            a[2] |= 0x10000;
        break;
    case 0x473f40: {
        const ClawGenericEnemyState *entry = nullptr;
        for (size_t n = 0; n < r.x->projectileStateCount; ++n)
            if (r.x->projectileStates[n].state == int32_t(arg)) {
                entry = r.x->projectileStates + n;
                break;
            }
        if (!entry) {
            r.x->fault = 1;
            break;
        }
        if (entry->function)
            invoke(s, r, entry->function);
        else
            call(s, r, 0x4a36f0, 0, {g->enemyToken});
        break;
    }
    case 0x484d90: {
        uint32_t receiver = g->enemyToken;
        e[0] = 0x50b014;
        if (arg & 1) {
            if (r.x->scene.free)
                r.x->scene.free(r.x->scene.context, receiver);
            else
                call(s, r, 0x4f6428, 0, {receiver});
        }
        value = receiver;
        break;
    }
    case 0x456030:
        e[0] = 0x50b014;
        break;
    case 0x4c9e30:
    case 0x4bb030:
    case 0x4c96b0:
        break;
    case 0x4dca10:
    case 0x4063b0:
    case 0x4dc870:
        if (!common(s, r, fn, arg)) {
            r.x->fault = 1;
            return 0;
        }
        break;
    default:
        return 0;
    }
    if (result)
        *result = value;
    return 1;
}
struct Hit {
    ClawBullet *bullet;
    ClawPlayerDamageContext *damage;
    ClawPlayerLocomotionDependency d;
    void *user;
};
uint32_t hitBridge(ClawPlayerLocomotion *p, uint32_t f, uint32_t a, uint32_t b, uint32_t c, void *user) {
    auto &h = *static_cast<Hit *>(user);
    std::copy(h.damage->attackerActor, h.damage->attackerActor + 128, h.bullet->actor);
    uint32_t value = h.d ? h.d(p, f, a, b, c, h.user) : 0;
    std::copy(h.damage->attackerActor, h.damage->attackerActor + 128, h.bullet->actor);
    return value;
}
} // namespace
extern "C" void claw_bullet_context_defaults(ClawBulletContext *x) {
    if (!x || !x->generic)
        return;
    const uint32_t v[] = {0x484d90, 0x4c9e30, 0x473f40, 0x4063b0, 0x4741f0, 0x4bb030,
                          0x4bb030, 0x4c96b0, 0x4c96b0, 0x4dca10, 0x474290, 0x4bb030};
    std::copy(v, v + 12, x->generic->virtualFunctions);
}
extern "C" uint32_t claw_bullet_construct(ClawBullet *s, ClawBulletContext *x, ClawGenericEnemyDependency d,
                                          void *user) {
    if (!s || !x || !x->generic)
        return 0;
    Run r{x, d, user};
    uint32_t result = 0;
    execute(s, r, 0x4107c0, 0, &result);
    return result;
}
extern "C" uint32_t claw_bullet_tick(ClawBullet *s, ClawBulletContext *x, ClawGenericEnemyDependency d, void *user) {
    if (!s || !x || !x->generic)
        return 0;
    Run r{x, d, user};
    auto *g = x->generic;
    switch (s->primary[7]) {
    case 0: {
        s->primary[7] = 1000;
        uint32_t token = uint32_t(call(s, r, 0x4f63ec, 0, {0x150}));
        if (!token) {
            x->fault = 2;
            return 0;
        }
        g->enemyToken = token;
        if (!claw_bullet_construct(s, x, d, user))
            return 0;
        virt(s, r, 0x10);
        s->primary[0x18 / 4] = token;
        break;
    }
    case 29:
        virt(s, r, 0x20);
        break;
    case 30:
        virt(s, r, 0x1c);
        break;
    case 1000:
        break;
    default:
        if (!common(s, r, 0x4dc870, 0)) {
            x->fault = 1;
            return 0;
        }
        break;
    }
    return 1;
}
extern "C" uint32_t claw_bullet_entry(ClawBullet *s, ClawBulletContext *x, uint32_t fn, uint32_t arg,
                                      ClawGenericEnemyDependency d, void *user, uint32_t *result) {
    if (!s || !x || !x->generic)
        return 0;
    if (fn == 0x40fec0) {
        uint32_t status = claw_bullet_tick(s, x, d, user);
        if (result)
            *result = status;
        return status;
    }
    Run r{x, d, user};
    return execute(s, r, fn, arg, result);
}
extern "C" uint32_t claw_bullet_player_hit(ClawBullet *s, ClawBulletContext *x, ClawPlayerLocomotion *player,
                                           ClawPlayerDamageContext *damage, ClawPlayerInputContext *input,
                                           ClawPlayerLocomotionDependency d, void *user) {
    if (!s || !x || !x->generic || !player || !damage || !input || player->actor[0x74 / 4] != x->generic->actorToken)
        return 0;
    damage->attackerToken = x->generic->actorToken;
    std::copy(s->actor, s->actor + 128, damage->attackerActor);
    Hit h{s, damage, d, user};
    uint32_t result = claw_player_hit(player, damage, input, hitBridge, &h);
    std::copy(damage->attackerActor, damage->attackerActor + 128, s->actor);
    return result;
}
