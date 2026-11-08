#include "FlareRuntime.h"
#include "GenericEnemy.h"
#include "PlayerPowerupRuntime.h"
#include "StackedActorLifecycleRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failed {};
struct Run {
    ClawFlareContext &c;
    ClawFlareDependency dependency;
    void *user;
    uint32_t steps = 0;
    static int32_t si(uint32_t x) {
        int32_t v;
        std::memcpy(&v, &x, 4);
        return v;
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failed{};
        }
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    void next() {
        if (++steps > (c.maximumSteps ? c.maximumSteps : 65536)) {
            c.fault = 2;
            throw Failed{};
        }
    }
    uint64_t external(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}, const char *name = nullptr) {
        ClawFlareCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        e.name = name;
        std::copy(a.begin(), a.end(), e.arguments);
        return external(e);
    }
    uint64_t external(const ClawFlareCall &e) {
        uint64_t value = 0;
        if (dependency)
            value = dependency(&c, &e, user);
        else if (c.scene.call && e.argumentCount <= 4) {
            ClawSceneActorCall q{};
            q.function = e.function;
            q.receiver = e.receiver;
            q.argumentCount = e.argumentCount;
            std::copy_n(e.arguments, e.argumentCount, q.arguments);
            value = c.scene.call(c.scene.context, q);
        } else {
            c.fault = 1;
            throw Failed{};
        }
        if (c.fault)
            throw Failed{};
        return value;
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
    }
    static uint32_t allocate(void *p, uint32_t n) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.scene.allocate) {
            r.c.fault = 1;
            throw Failed{};
        }
        return r.c.scene.allocate(r.c.scene.context, n);
    }
    static void release(void *p, uint32_t t) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.scene.free) {
            r.c.fault = 1;
            throw Failed{};
        }
        r.c.scene.free(r.c.scene.context, t);
    }
    static uint32_t call(void *p, ClawSceneActorCall e) {
        return uint32_t(static_cast<Run *>(p)->invoke(e.function, e.receiver, e.arguments, e.argumentCount));
    }
    static uint32_t clock(void *p) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.scene.readClock) {
            r.c.fault = 1;
            throw Failed{};
        }
        return r.c.scene.readClock(r.c.scene.context);
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, call, clock};
    }
    // Frozen ANI shadows use128 words internally. Actual animated actors are
    //109 words: supply a local read-only padding tail and commit only109 words.
    struct AnimationView {
        Run *r;
        uint32_t actor, words[128];
    };
    static uint32_t *animationLookup(void *p, uint32_t t, uint32_t n) {
        auto &q = *static_cast<AnimationView *>(p);
        if (t >= q.actor && (t - q.actor) % 4 == 0 && (t - q.actor) / 4 + n <= 128)
            return q.words + (t - q.actor) / 4;
        return q.r->span(t, n);
    }
    static uint32_t animationCall(void *p, ClawSceneActorCall e) {
        auto &q = *static_cast<AnimationView *>(p);
        std::copy_n(q.words, 109, q.r->span(q.actor, 109));
        uint32_t value = uint32_t(q.r->invoke(e.function, e.receiver, e.arguments, e.argumentCount));
        std::copy_n(q.r->span(q.actor, 109), 109, q.words);
        return value;
    }
    uint32_t animation(uint32_t f, uint32_t t, uint32_t arg) {
        if (!c.composeAnimation)
            return uint32_t(external(f, t, {arg}));
        if (!c.animation) {
            c.fault = 1;
            throw Failed{};
        }
        uint32_t fault = 0, value = 0;
        auto h = host();
        AnimationView view{};
        if (f == 0x4c82a0) {
            view.r = this;
            view.actor = get(t + 4);
            auto *actual = c.scene.lookup ? c.scene.lookup(c.scene.context, view.actor, 109) : nullptr;
            if (actual) {
                std::copy_n(actual, 109, view.words);
                h.context = &view;
                h.lookup = animationLookup;
                h.call = animationCall;
                h.allocate = nullptr;
                h.free = nullptr;
                h.readClock = nullptr;
            } else
                view.actor = 0;
        }
        if (!claw_actor_animation_entry(f, t, arg, 0, c.animation, h, &fault, &value) || fault) {
            c.fault = fault ? fault : 1;
            throw Failed{};
        }
        if (f == 0x4c82a0 && view.actor)
            std::copy_n(view.words, 109, span(view.actor, 109));
        return value;
    }
    static uint32_t effectCall(ClawPlayerPowerupRuntimeContext *q, const ClawPlayerPowerupCall *e, void *p) {
        auto &r = *static_cast<Run *>(p);
        uint32_t value = uint32_t(r.invoke(e->function, e->receiver, e->arguments, e->argumentCount));
        if (r.c.fault)
            q->fault = r.c.fault;
        return value;
    }
    uint32_t effects(uint32_t t, uint32_t mode) {
        if (!c.composeEffects)
            return uint32_t(external(0x4ce7b0, t, {mode}));
        ClawPlayerPowerupGlobals unused{};
        ClawPlayerPowerupRuntimeContext q{host(), &unused, 0};
        uint32_t value = 0;
        if (!claw_player_powerup_entry(0x4ce7b0, t, &mode, 1, &q, effectCall, this, &value) || q.fault) {
            c.fault = q.fault ? q.fault : 1;
            throw Failed{};
        }
        return value;
    }
    uint32_t imageEffect(uint32_t t, const uint32_t *args) {
        if (!c.composeEffects)
            return uint32_t(external(0x4c6130, t, {args[0], args[1]}));
        if (!c.images) {
            c.fault = 1;
            throw Failed{};
        }
        ClawGameImageArguments a{};
        a.count = 2;
        a.words[0] = args[0];
        a.words[1] = args[1];
        ClawGameImageHost h{};
        h.heap = host();
        uint32_t fault = 0, value = 0;
        if (!claw_game_image_entry(0x4c6130, t, a, c.images, h, &fault, &value) || fault) {
            c.fault = fault ? fault : 1;
            throw Failed{};
        }
        return value;
    }
    uint32_t imagePointer(uint32_t t, uint32_t pointer) {
        if (!pointer)
            return 0;
        uint32_t value = 0;
        for (uint32_t i = get(t + 100); si(i) <= si(get(t + 104)); ++i) {
            next();
            uint32_t image = 0;
            if (si(i) >= si(get(t + 100)) && si(i) <= si(get(t + 104)))
                image = get(get(t + 20) + i * 4);
            if (image) {
                uint32_t compressed = get(image + 48);
                if (compressed) {
                    put(compressed + 28, pointer);
                    ++value;
                }
            }
        }
        return value;
    }
    uint32_t cell(uint32_t table, uint32_t state) {
        put(table + 32, 0);
        int32_t low = si(get(table + 8));
        if (si(state) < low || si(state) > si(get(table + 12))) {
            uint32_t grown = uint32_t(external(0x4db6e0, table, {state, 0}));
            if (!grown) {
                uint32_t message = get(0x544b4c);
                put(0x544b14, uint32_t(external(0x4db5f0, 0)));
                external(0x4db4d0, get(table + 4), {table, message, 12});
                return get(table + 20);
            }
            low = si(get(table + 8));
        }
        return get(table + 16) + (state - uint32_t(low)) * get(table + 24);
    }
    uint32_t nameToken(uint32_t state) {
        uint32_t token = cell(0x537698, state);
        uint32_t n = get(0x5376b8), at = get(0x5376b4);
        for (uint32_t i = 0; i < n; ++i, at += 4) {
            next();
            if (at)
                external(0x4f6439, at);
        }
        return uint32_t(external(0x4f6974, token, {0}));
    }
    uint32_t dispatch(uint32_t p, uint32_t state) {
        uint32_t token = cell(0x537ac0, state);
        if (get(token)) {
            token = cell(0x537ac0, state);
            return uint32_t(invoke(get(token), p, nullptr, 0));
        }
        external(0x4a36f0, 0, {p});
        return 0;
    }
    struct FSM {
        Run *r;
        uint32_t p, phase;
        ClawGenericEnemy state;
        ClawGenericEnemyContext context;
        ClawGenericEnemyState view;
    };
    void transfer(FSM &q, bool push) {
        auto *e = span(q.p, 19);
        auto *a = span(q.context.actorToken, 109);
        auto *l = span(q.context.primaryToken, 93);
        if (push) {
            std::copy_n(q.state.enemy, 19, e);
            std::copy_n(q.state.actor, 109, a);
            std::copy_n(q.state.primary, 93, l);
        } else {
            std::copy_n(e, 19, q.state.enemy);
            std::copy_n(a, 109, q.state.actor);
            std::copy_n(l, 93, q.state.primary);
        }
    }
    static uint64_t fsmCall(ClawGenericEnemy *s, ClawGenericEnemyContext *c, const ClawGenericEnemyCall *e, void *p) {
        auto &q = *static_cast<FSM *>(p);
        q.state = *s;
        q.context = *c;
        q.r->transfer(q, true);
        uint64_t value = q.r->invoke(e->function, e->receiver, e->arguments, e->argumentCount);
        q.r->transfer(q, false);
        if (++q.phase == 2)
            q.view.nameToken = q.r->nameToken(uint32_t(q.view.state));
        *s = q.state;
        *c = q.context;
        return value;
    }
    void tick(uint32_t p) {
        if (!c.composeFSM) {
            external(0x4dc870, 0, {p});
            return;
        }
        FSM q{};
        q.r = this;
        q.p = p;
        q.context.actorToken = get(p + 12);
        q.context.primaryToken = get(p + 16);
        q.context.enemyToken = p;
        std::copy_n(span(get(p), 9), 9, q.context.virtualFunctions);
        transfer(q, false);
        q.view.state = si(q.state.primary[7]);
        q.view.nameToken = nameToken(uint32_t(q.view.state));
        q.context.states = &q.view;
        q.context.stateCount = 1;
        if (!claw_generic_enemy_tick(&q.state, &q.context, fsmCall, &q)) {
            c.fault = 2;
            throw Failed{};
        }
        transfer(q, true);
    }
    uint32_t construct(uint32_t p, uint32_t actor) {
        put(p, 0x50b064);
        put(p + 8, actor);
        put(p + 12, actor);
        put(p + 16, get(actor + 108));
        put(p + 4, 0);
        external(0x4c7fa0, actor, {0x522d54}, "LogicHit");
        external(0x4c8060, get(p + 12), {0x522d48}, "LogicAttack");
        put(p + 20, 0);
        put(p + 24, 0);
        put(p + 28, 1001);
        put(p + 32, 2);
        put(p + 40, actor);
        put(p + 44, actor);
        put(p + 48, get(actor + 108));
        put(p, 0x50e74c);
        return p;
    }
    uint32_t idleStart(uint32_t p) {
        put(p + 36, get(get(p + 16) + 28));
        uint32_t id = uint32_t(external(0x4dba00, 0x537668, {0x523148}, "LS_IDLE"));
        put(get(p + 16) + 28, id);
        uint32_t actor = get(p + 44);
        uint32_t sequence = get(p + 72);
        put(p + 52, get(actor + 400));
        animation(0x4c8220, actor + 392, sequence);
        return 0;
    }
    void initialize(uint32_t p) {
        uint32_t actor = get(p + 44), manager = get(actor + 368);
        put(actor + 208, 1);
        if (manager) {
            effects(manager, 2);
            imagePointer(manager, get(get(get(0x5371fc) + 44) + 0x768));
        }
        actor = get(p + 44);
        uint32_t sequence = get(p + 72);
        put(p + 52, get(actor + 400));
        animation(0x4c8220, actor + 392, sequence);
        idleStart(p);
    }
    uint32_t wrapper(uint32_t actor, bool other) {
        uint32_t primary = get(actor + 108), state = get(primary + 28);
        if (!state) {
            put(primary + 28, 1000);
            uint32_t p = allocate(this, 76);
            if (p) {
                construct(p, actor);
                put(p, other ? 0x50e724 : 0x50e6fc);
                uint32_t name = other ? 0x528720 : 0x5286e8;
                external(0x4c7970, get(p + 44), {name}, other ? "GAME_LIGHTFX_WOLVINGTONLFX" : "GAME_LIGHTFX_FLARE");
                uint32_t registry = get(get(get(p + 44) + 12) + 44) + 16;
                put(p + 72, uint32_t(external(0x4f6286, registry, {name})));
            }
            invoke(get(get(p) + 16), p, nullptr, 0);
            put(primary + 24, p);
        } else if (state == 29 || state == 30) {
            uint32_t p = get(primary + 24);
            invoke(get(get(p) + (state == 29 ? 32 : 28)), p, nullptr, 0);
        } else if (state != 1000)
            tick(get(primary + 24));
        return 1;
    }
    uint64_t invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        switch (f) {
        case 0x457f00:
            return wrapper(a[0], false);
        case 0x458010:
            return wrapper(a[0], true);
        case 0x458120:
            return construct(t, a[0]);
        case 0x4581c0:
            initialize(t);
            return 0;
        case 0x458280:
            return dispatch(t, a[0]);
        case 0x458530:
            return idleStart(t);
        case 0x458570:
            animation(0x4c82a0, get(t + 44) + 392, get(0x5430c4));
            return 0;
        case 0x4dc870:
            tick(a[0]);
            return 0;
        case 0x4c8220:
        case 0x4c82a0:
            return animation(f, t, a[0]);
        case 0x4ce7b0:
            return effects(t, a[0]);
        case 0x4ce850:
            return imagePointer(t, a[0]);
        case 0x4c6130:
            return imageEffect(t, a);
        case 0x4041b0:
        case 0x484d90:
        case 0x456030:
        case 0x4c9e30:
        case 0x4c96b0:
        case 0x4bb030: {
            ClawStackedActorLifecycleContext q{host(), 0};
            uint32_t value = 0;
            if (!claw_stacked_actor_lifecycle_entry(f, t, a, n, &q, &value) || q.fault) {
                c.fault = q.fault ? q.fault : 1;
                throw Failed{};
            }
            return value;
        }
        default: {
            ClawFlareCall e{};
            e.function = f;
            e.receiver = t;
            e.argumentCount = n;
            if (n > 8) {
                c.fault = 2;
                throw Failed{};
            }
            std::copy_n(a, n, e.arguments);
            return external(e);
        }
        }
    }
};
bool supported(uint32_t f, uint32_t &n) {
    n = 0;
    switch (f) {
    case 0x4581c0:
    case 0x458530:
    case 0x458570:
    case 0x456030:
    case 0x4c96b0:
    case 0x4bb030:
        return true;
    case 0x457f00:
    case 0x458010:
    case 0x458120:
    case 0x458280:
    case 0x4dc870:
    case 0x4041b0:
    case 0x484d90:
    case 0x4c9e30:
    case 0x4ce850:
        n = 1;
        return true;
    default:
        return false;
    }
}
} // namespace
extern "C" void claw_flare_defaults(ClawFlareContext *c) {
    if (c) {
        c->composeAnimation = c->composeFSM = c->composeEffects = 1;
        c->maximumSteps = 65536;
    }
}
extern "C" uint32_t claw_flare_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, ClawFlareContext *c,
                                     ClawFlareDependency d, void *u, uint32_t *result) {
    uint32_t need;
    if (!supported(f, need))
        return 0;
    if (result)
        *result = 0;
    if (!c)
        return 1;
    c->fault = 0;
    if (n != need || (n && !a)) {
        c->fault = 2;
        return 1;
    }
    Run r{*c, d, u};
    uint64_t value = 0;
    try {
        value = r.invoke(f, t, a, n);
    } catch (Failed &) {
    }
    if (result)
        *result = uint32_t(value);
    return 1;
}
