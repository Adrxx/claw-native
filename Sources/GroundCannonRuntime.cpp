#include "GroundCannonRuntime.h"
#include "ActorResourceBindings.h"
#include "PickupPointsRuntime.h"
#include "StackedActorLifecycleRuntime.h"
#include <algorithm>
#include <cstring>
namespace {
struct Failure {};
constexpr uint32_t vt[] = {0x484d90, 0x4c9e30, 0x449590, 0x4041b0, 0x4c96b0, 0x4bb030, 0x4bb030, 0x4c96b0, 0x4c96b0};
int32_t sign(uint32_t v) {
    int32_t n;
    std::memcpy(&n, &v, 4);
    return n;
}
const char *label(uint32_t t) {
    switch (t) {
    case 0x522dbc:
        return "CannonBall";
    case 0x527b14:
        return "LEVEL_CANNON";
    case 0x527b00:
        return "LEVEL_CANNON_FIRING";
    case 0x527aec:
        return "LEVEL_CANNON_HOME";
    default:
        return nullptr;
    }
}
struct Run {
    ClawGroundCannonContext &c;
    ClawGroundCannonDependency d;
    void *u;
    uint32_t steps = 0;
    [[noreturn]] void fail(uint32_t n = 1) {
        if (!c.fault)
            c.fault = n;
        throw Failure{};
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p)
            fail();
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    uint32_t invoke(uint32_t, uint32_t, const uint32_t *, uint32_t);
    uint32_t call(uint32_t f, uint32_t t, const uint32_t *a = nullptr, uint32_t n = 0) {
        if (!d)
            fail();
        ClawGroundCannonCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        if (n > 12)
            fail(3);
        std::copy_n(a, n, q.arguments);
        for (uint32_t i = 0; i < n; ++i)
            if (label(a[i]))
                q.name = label(a[i]);
        auto value = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        return uint32_t(value);
    }
    uint32_t one(uint32_t f, uint32_t t, uint32_t a) {
        return invoke(f, t, &a, 1);
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        auto &r = *static_cast<Run *>(p);
        if (t >= 0x50dfd4 && (t - 0x50dfd4) % 4 == 0 && (t - 0x50dfd4) / 4 + n <= 9)
            return const_cast<uint32_t *>(vt) + (t - 0x50dfd4) / 4;
        return r.span(t, n);
    }
    static uint32_t hostCall(void *p, ClawSceneActorCall q) {
        return static_cast<Run *>(p)->invoke(q.function, q.receiver, q.arguments, q.argumentCount);
    }
    static void release(void *p, uint32_t t) {
        auto &r = *static_cast<Run *>(p);
        if (r.c.scene.free)
            r.c.scene.free(r.c.scene.context, t);
        else
            r.call(0x4f6428, 0, &t, 1);
    }
    ClawSceneActorHost host() {
        return {this, lookup, nullptr, release, hostCall, nullptr};
    }
    static uint64_t shared(ClawGabrielWeaponsContext *, const ClawGabrielWeaponsCall *q, void *p) {
        auto &r = *static_cast<Run *>(p);
        if (q->name && !q->argumentCount) {
            if (!r.d)
                r.fail();
            auto value = r.d(&r.c, q, r.u);
            if (r.c.fault)
                throw Failure{};
            return value;
        }
        return r.invoke(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    uint32_t table(uint32_t t, uint32_t id) {
        put(t + 32, 0);
        uint32_t slot;
        if (sign(id) < sign(get(t + 8)) || sign(get(t + 12)) < sign(id)) {
            uint32_t a[] = {id, 0};
            if (!invoke(0x4db6e0, t, a, 2)) {
                uint32_t text = get(0x544b4c);
                put(0x544b14, invoke(0x4db5f0, 0, nullptr, 0));
                uint32_t b[] = {t, text, 12};
                invoke(0x4db4d0, get(t + 4), b, 3);
                slot = get(t + 20);
            } else
                slot = get(t + 16) + (id - get(t + 8)) * get(t + 24);
        } else
            slot = get(t + 16) + (id - get(t + 8)) * get(t + 24);
        return slot;
    }
    uint32_t name(uint32_t id) {
        uint32_t token = table(0x537698, id), at = get(0x5376b4), n = get(0x5376b8);
        for (uint32_t i = 0; i < n; ++i, at += 4) {
            if (++steps > (c.maximumSteps ? c.maximumSteps : 65536))
                fail(3);
            if (at)
                invoke(0x4f6439, at, nullptr, 0);
        }
        return one(0x4f6974, token, 0);
    }
    struct FSM {
        Run *r;
        uint32_t p, phase = 0;
        ClawGenericEnemy state{};
        ClawGenericEnemyContext context{};
        ClawGenericEnemyState view{};
    };
    void transfer(FSM &q, bool push) {
        auto *e = span(q.p, 31);
        auto *a = span(q.context.actorToken, 109);
        auto *l = span(q.context.primaryToken, 93);
        if (push) {
            std::copy_n(q.state.enemy, 31, e);
            std::copy_n(q.state.actor, 109, a);
            std::copy_n(q.state.primary, 93, l);
        } else {
            std::copy_n(e, 31, q.state.enemy);
            std::copy_n(a, 109, q.state.actor);
            std::copy_n(l, 93, q.state.primary);
        }
    }
    static uint64_t fsm(ClawGenericEnemy *s, ClawGenericEnemyContext *c, const ClawGenericEnemyCall *e, void *p) {
        auto &q = *static_cast<FSM *>(p);
        q.state = *s;
        q.context = *c;
        q.r->transfer(q, true);
        auto value = q.r->invoke(e->function, e->receiver, e->arguments, e->argumentCount);
        q.r->transfer(q, false);
        if (++q.phase == 2)
            q.view.nameToken = q.r->name(uint32_t(q.view.state));
        *s = q.state;
        *c = q.context;
        return value;
    }
    void tick(uint32_t p) {
        FSM q{};
        q.r = this;
        q.p = p;
        q.context.actorToken = get(p + 12);
        q.context.primaryToken = get(p + 16);
        q.context.enemyToken = p;
        std::copy_n(vt, 9, q.context.virtualFunctions);
        transfer(q, false);
        q.view.state = sign(q.state.primary[7]);
        q.view.nameToken = name(uint32_t(q.view.state));
        q.context.states = &q.view;
        q.context.stateCount = 1;
        if (!claw_generic_enemy_tick(&q.state, &q.context, fsm, &q))
            fail(3);
        transfer(q, true);
    }
    static uint32_t resolved(ClawActorResourceBindings *, ClawActorBindingContext *c, const ClawActorBindingCall *,
                             void *) {
        return c->image.token;
    }
    void image(uint32_t actor, uint32_t literal) {
        uint32_t registry = get(get(actor + 12) + 16) + 16, root = call(0x4f6286, registry, &literal, 1), selected = 0;
        ClawActorBindingContext b{};
        b.imageRegistryToken = registry;
        b.image.token = root;
        if (root) {
            b.image.minimum = sign(get(root + 100));
            b.image.maximum = sign(get(root + 104));
            ClawPickupPointsContext p{};
            p.scene = host();
            uint32_t index = uint32_t(b.image.minimum);
            if (!claw_pickup_points_entry(0x40f680, root, &index, 1, &p, nullptr, nullptr, &selected) || p.fault)
                fail(p.fault ? p.fault : 1);
            b.image.firstImageIndex = b.image.minimum;
            b.image.images = &selected;
            b.image.imageCount = 1;
        }
        ClawActorResourceBindings s{};
        std::copy_n(span(actor, 109), 109, s.actor);
        if (!claw_actor_bind_default_image(&s, &b, label(literal), resolved, nullptr))
            fail(3);
        std::copy_n(s.actor, 109, span(actor, 109));
    }
};
uint32_t Run::invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
    if (++steps > (c.maximumSteps ? c.maximumSteps : 65536))
        fail(3);
    uint32_t out = 0;
    if (f == 0x4493c0) {
        auto actor = a[0], primary = get(actor + 108), state = get(primary + 28);
        if (!state) {
            put(primary + 28, 1000);
            uint32_t size = 124, child = call(0x4f63ec, 0, &size, 1);
            if (child)
                one(0x449480, child, actor);
            if (!child)
                fail(2);
            invoke(get(get(child) + 16), child, nullptr, 0);
            put(primary + 24, child);
        } else if (state == 29 || state == 30) {
            auto p = get(primary + 24);
            invoke(get(get(p) + (state == 29 ? 32 : 28)), p, nullptr, 0);
        } else if (state != 1000)
            one(0x4dc870, 0, get(primary + 24));
        return 1;
    }
    if (f == 0x449480) {
        one(0x414030, t, a[0]);
        put(t, 0x50dfd4);
        one(0x4c7970, get(t + 44), 0x527b14);
        put(t + 76, one(0x4f6286, get(get(get(t + 44) + 12) + 44) + 16, 0x527b00));
        put(t + 72, one(0x4f6286, get(get(get(t + 44) + 12) + 44) + 16, 0x527aec));
        return t;
    }
    if (f == 0x449590) {
        uint32_t id = a[0];
        if (get(table(0x537818, id)))
            invoke(get(table(0x537818, id)), t, nullptr, 0);
        else
            one(0x4141f0, t, id);
        return 0;
    }
    if (f == 0x42a680)
        return 0;
    if (f == 0x4dc870 && n == 1 && get(a[0]) == 0x50dfd4) {
        tick(a[0]);
        return 0;
    }
    if (f == 0x4c7970 && c.composeImages) {
        image(t, a[0]);
        return 1;
    }
    if (f == 0x484d90 || f == 0x456030 || f == 0x4041b0 || f == 0x4c9e30 || f == 0x4c96b0 || f == 0x4bb030) {
        ClawStackedActorLifecycleContext x{host(), 0};
        if (!claw_stacked_actor_lifecycle_entry(f, t, a, n, &x, &out) || x.fault)
            fail(x.fault ? x.fault : 1);
        return out;
    }
    auto x = c;
    x.scene = host();
    x.fault = 0;
    if (claw_gabriel_weapons_entry(f, t, a, n, &x, shared, this, &out)) {
        if (x.fault)
            fail(x.fault);
        return out;
    }
    if (x.fault)
        fail(x.fault);
    return call(f, t, a, n);
}
bool supported(uint32_t f, uint32_t &n) {
    n = 0;
    switch (f) {
    case 0x4493c0:
    case 0x449480:
    case 0x449590:
    case 0x414030:
    case 0x4141f0:
    case 0x414b20:
    case 0x414be0:
    case 0x4dc870:
    case 0x484d90:
    case 0x4041b0:
    case 0x4c9e30:
        n = 1;
        return true;
    case 0x42a680:
    case 0x4145b0:
    case 0x4145f0:
    case 0x414640:
    case 0x414660:
    case 0x4146b0:
    case 0x414860:
    case 0x4148b0:
    case 0x414a60:
    case 0x456030:
    case 0x4c96b0:
    case 0x4bb030:
        return true;
    default:
        return false;
    }
}
} // namespace
extern "C" uint32_t claw_ground_cannon_function(uint32_t v, uint32_t slot) {
    if (v == 0x50dfd4 && slot % 4 == 0 && slot < 36)
        return vt[slot / 4];
    return claw_gabriel_weapons_function(v, slot);
}
extern "C" uint32_t claw_ground_cannon_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                             ClawGroundCannonContext *c, ClawGroundCannonDependency d, void *u,
                                             uint32_t *out) {
    uint32_t need = 0;
    if (!supported(f, need) || !c || !c->globals)
        return 0;
    if (n != need || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    if (c->fault)
        return 0;
    Run r{*c, d, u};
    try {
        auto result = r.invoke(f, t, a, n);
        if (out)
            *out = result;
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
