#include "ImpactParticleRuntime.h"
#include <algorithm>
#include <initializer_list>
namespace {
struct Run {
    ClawImpactParticleContext *c;
    ClawImpactParticleDependency d;
    void *user;
};
bool bad(Run &r) {
    return r.c->fault != 0;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    auto &h = r.c->scene;
    auto *p = h.lookup ? h.lookup(h.context, t, n) : nullptr;
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t rd(Run &r, uint32_t t) {
    auto *p = span(r, t, 1);
    return p ? *p : 0;
}
void wr(Run &r, uint32_t t, uint32_t v) {
    if (bad(r))
        return;
    auto *p = span(r, t, 1);
    if (p)
        *p = v;
}
void mark(Run &r, uint32_t actor) {
    wr(r, actor + 8, rd(r, actor + 8) | 0x10000);
}
uint32_t call(Run &r, uint32_t f, uint32_t recv, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr) {
    if (bad(r))
        return 0;
    if (!r.d) {
        r.c->fault = 1;
        return 0;
    }
    ClawImpactParticleCall e{};
    e.function = f;
    e.receiver = recv;
    e.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), e.arguments);
    e.name = name;
    return r.d(r.c, &e, r.user);
}
uint32_t animation(Run &r, uint32_t f, uint32_t recv, uint32_t a, uint32_t b = 0) {
    if (bad(r))
        return 0;
    if (!r.c->composeAnimation)
        return f == 0x4c79e0 ? call(r, f, recv, {a, b}) : call(r, f, recv, {a});
    uint32_t result = 0;
    if (!claw_actor_animation_entry(f, recv, a, b, &r.c->animation, r.c->scene, &r.c->fault, &result) && !r.c->fault)
        r.c->fault = 2;
    return result;
}
uint32_t create(Run &r, uint32_t scene, uint32_t x, uint32_t y, uint32_t z, uint32_t name, const char *text) {
    const uint32_t container = rd(r, scene + 8);
    if (bad(r))
        return 0;
    if (r.c->composeCreation) {
        ClawSceneActorCreate args{0, x, y, z, 0, 0x40000};
        return claw_scene_actor_create_named(container, args, name, r.c->scene, &r.c->fault);
    }
    return call(r, 0x4c8da0, container, {0, x, y, z, name, 0x40000}, text);
}
uint32_t burst(Run &r, uint32_t actor) {
    const uint32_t source = rd(r, actor + 0x80), logic = rd(r, actor + 0x6c);
    if (!source) {
        mark(r, actor);
        return 0;
    }
    if (rd(r, source + 8) & 0x10000) {
        mark(r, actor);
        return 0;
    }
    if (rd(r, source + 0x38) == 0xffffffff) {
        mark(r, actor);
        return 0;
    }
    const uint32_t state = rd(r, logic + 0x1c);
    if (!state) {
        wr(r, actor + 8, rd(r, actor + 8) | 0x21);
        const int32_t selection = int32_t(call(r, 0x4a3050, 0)) % 3;
        const uint32_t token = selection == 0 ? 0x5294fc : selection == 2 ? 0x529510 : 0x529524;
        animation(r, 0x4c79e0, actor, token, 0);
        wr(r, actor + 0x158, rd(r, actor + 0x4c) - rd(r, source + 0x4c));
        wr(r, actor + 0x15c, rd(r, actor + 0x50) - rd(r, source + 0x50));
        wr(r, logic + 0x1c, 5);
    } else if (state == 5) {
        animation(r, 0x4c82a0, actor + 0x188, r.c->animation.animationDelta);
        if (rd(r, actor + 0x1a4) && !rd(r, actor + 0x19c)) {
            mark(r, actor);
            return 0;
        }
        wr(r, actor + 0x4c, rd(r, source + 0x4c) + rd(r, actor + 0x158));
        wr(r, actor + 0x50, rd(r, source + 0x50) + rd(r, actor + 0x15c));
    }
    return 1;
}
uint32_t splash(Run &r, uint32_t actor) {
    const uint32_t logic = rd(r, actor + 0x6c), state = rd(r, logic + 0x1c);
    if (!state) {
        wr(r, actor + 8, rd(r, actor + 8) | 0x21);
        animation(r, 0x4c79e0, actor, 0x5266ec, 0);
        call(r, 0x4c7970, actor, {0x529538}, "LEVEL_SPLASH");
        wr(r, logic + 0x1c, 5);
    } else if (state == 5) {
        animation(r, 0x4c82a0, actor + 0x188, r.c->animation.animationDelta);
        if (rd(r, actor + 0x1a4) && !rd(r, actor + 0x19c)) {
            mark(r, actor);
            return 0;
        }
    }
    return 1;
}
uint32_t hit(Run &r, const uint32_t *a) {
    const uint32_t source = a[5];
    if (!source)
        return 0;
    if (rd(r, source + 0x38) == 0xffffffff)
        return 0;
    if (rd(r, source + 8) & 0x10000)
        return 0;
    uint32_t created = create(r, a[0], a[1], a[2], a[3], 0x522570, "HitBurst");
    if (!created)
        return 0;
    call(r, 0x4c7970, created, {a[4] ? 0x5294ecu : 0x5294dcu}, a[4] ? "GAME_CLAWHIT" : "GAME_ENEMYHIT");
    wr(r, created + 0x80, source);
    uint32_t fn = rd(r, rd(r, created + 0x6c) + 0x10);
    if (fn == 0x461a90)
        burst(r, created);
    else if (fn == 0x461bc0)
        splash(r, created);
    else
        call(r, fn, 0, {created});
    return 1;
}
} // namespace
extern "C" uint32_t claw_impact_particle_entry(uint32_t f, uint32_t receiver, const uint32_t *args, uint32_t count,
                                               ClawImpactParticleContext *c, ClawImpactParticleDependency d, void *user,
                                               uint32_t *result) {
    (void)receiver;
    if (result)
        *result = 0;
    if (!c)
        return 0;
    uint32_t required;
    switch (f) {
    case 0x461a00:
        required = 6;
        break;
    case 0x461c40:
        required = 4;
        break;
    case 0x461a90:
    case 0x461bc0:
        required = 1;
        break;
    default:
        return 0;
    }
    if (count != required || (count && !args)) {
        c->fault = 2;
        return 0;
    }
    Run r{c, d, user};
    if (bad(r))
        return 0;
    uint32_t value = 0;
    switch (f) {
    case 0x461a00:
        value = hit(r, args);
        break;
    case 0x461c40:
        if (args[0])
            value = create(r, args[0], args[1], args[2], args[3], 0x522568, "Splash") != 0;
        break;
    case 0x461a90:
        value = burst(r, args[0]);
        break;
    case 0x461bc0:
        value = splash(r, args[0]);
        break;
    default:
        break;
    }
    if (result)
        *result = value;
    return !bad(r);
}
