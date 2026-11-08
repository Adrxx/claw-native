#include "AquatisRuntime.h"
#include "ActorWrapperRuntime.h"
#include "ActorResourceBindings.h"
#include "PickupPointsRuntime.h"
#include "StackedActorLifecycleRuntime.h"
#include "PlayerPhysics.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#include <cmath>
namespace {
struct Failure {};
const uint32_t boss[] = {0x404e20, 0x44d000, 0x404310, 0x44d3c0, 0x40e1b0, 0x405af0, 0x4bb030, 0x4c96b0, 0x40e5b0,
                         0x43dfa0, 0x404dd0, 0x44d460, 0x44d570, 0x44d5a0, 0x44d700, 0x44d730, 0x44d760, 0x44d9f0,
                         0x4050b0, 0x43ed70, 0x43eee0, 0x43ee10, 0x43efe0, 0x40e660, 0x43f640, 0x43f740, 0x43fa10,
                         0x43fcb0, 0x43fd60, 0x43fe00, 0x44dbb0, 0x43ffa0, 0x404e00, 0x44de30, 0x44df10, 0x4407d0,
                         0x43f500, 0x4409d0, 0x440b20, 0x440c90, 0x440410, 0x4bb030, 0x404e10, 0x405060, 0x405ed0};
const char *label(uint32_t t) {
    switch (t) {
    case 0x522ae4:
        return "Aquatis";
    case 0x523268:
        return "LS_STARTUP";
    case 0x523148:
        return "LS_IDLE";
    case 0x523258:
        return "LS_HIGHPUNCH";
    case 0x52324c:
        return "LS_LOWPUNCH";
    case 0x52323c:
        return "LS_SUPERFRENZY";
    case 0x523228:
        return "LS_STALACTITEHIT";
    case 0x52321c:
        return "LS_SCARED";
    case 0x523210:
        return "LS_HITHIGH";
    case 0x523204:
        return "LS_HITLOW";
    case 0x5231f8:
        return "LS_DEADACT1";
    case 0x5234f4:
        return "LS_DEAD";
    case 0x5234b4:
        return "GAME_NULL";
    case 0x5234d8:
        return "LEVEL_KINGAQUATIS";
    case 0x5234c0:
        return "LEVEL_AQUATIS_HITHIGH";
    case 0x52349c:
        return "LEVEL_AQUATIS_HITLOW";
    case 0x523488:
        return "LEVEL_AQUATIS_IDLE1";
    case 0x523474:
        return "LEVEL_AQUATIS_IDLE2";
    case 0x52345c:
        return "LEVEL_AQUATIS_KILLFALL";
    case 0x523448:
        return "LEVEL_AQUATIS_IDLE3";
    case 0x523430:
        return "LEVEL_AQUATIS_STRIKE1";
    case 0x523418:
        return "LEVEL_AQUATIS_STRIKE2";
    case 0x523400:
        return "LEVEL_AQUATIS_00480011";
    case 0x5233e8:
        return "LEVEL_AQUATIS_00480012";
    case 0x5233d0:
        return "LEVEL_AQUATIS_00480013";
    case 0x5233b8:
        return "LEVEL_AQUATIS_00480015";
    case 0x5233a0:
        return "LEVEL_AQUATIS_00480006";
    case 0x523388:
        return "LEVEL_AQUATIS_00480000";
    case 0x523370:
        return "LEVEL_AQUATIS_00480001";
    case 0x523358:
        return "LEVEL_AQUATIS_00480002";
    case 0x523340:
        return "LEVEL_AQUATIS_00480005";
    default:
        return nullptr;
    }
}
int32_t sign(uint32_t v) {
    int32_t x;
    std::memcpy(&x, &v, 4);
    return x;
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
bool owned(uint32_t);
struct Run {
    ClawAquatisContext &c;
    ClawAquatisDependency d;
    void *user;
    uint32_t steps = 0;
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failure{};
        auto p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failure{};
        }
        return p;
    }
    uint32_t read(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    double real(uint32_t t) {
        double v;
        std::memcpy(&v, span(t, 2), 8);
        return v;
    }
    void real(uint32_t t, double v) {
        std::memcpy(span(t, 2), &v, 8);
    }
    uint64_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        if (!d) {
            c.fault = 1;
            throw Failure{};
        }
        ClawAquatisCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), e.arguments);
        for (auto x : a)
            if (label(x))
                e.name = label(x);
        return d(&c, &e, user);
    }
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t> = {});
    void virt(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        uint32_t vt = read(t), f = claw_aquatis_function(vt, slot);
        if (!f)
            f = read(vt + slot);
        invoke(f, t, a);
    }
    void rect(uint32_t t, uint32_t l, uint32_t top, uint32_t right, uint32_t bottom) {
        put(t, l);
        put(t + 4, top);
        put(t + 8, right);
        put(t + 12, bottom);
    }
    void mirror(uint32_t t, uint32_t off) {
        auto l = read(t + off);
        put(t + off, 0 - read(t + off + 8));
        put(t + off + 8, 0 - l);
    }
    uint32_t soundRegistry(uint32_t p) {
        return read(read(read(p + 300) + 12) + 0x28) + 16;
    }
    uint32_t sequence(uint32_t p, uint32_t t) {
        auto s = invoke(0x4062e0, p + 0x128, {t});
        return s ? s : invoke(0x4062e0, p + 0x128, {0x5234b4});
    }
    uint32_t animate(uint32_t p) {
        return invoke(0x4c82a0, read(p + 300) + 0x188, {c.globals->animationDelta});
    }
    void transition(uint32_t p, uint32_t name) {
        put(p + 0x24, read(read(p + 16) + 28));
        put(read(p + 16) + 28, invoke(0x4dba00, 0x537668, {name}));
    }
    void audio(uint32_t sound) {
        if (sound && c.globals->audioEnabled)
            invoke(0x4b45f0, read(sound + 16), {c.globals->masterVolume, 0, 0, 0});
    }
    uint32_t registry(uint32_t t, uint32_t id) {
        put(t + 32, 0);
        uint32_t slot;
        if (sign(id) < sign(read(t + 8)) || sign(read(t + 12)) < sign(id)) {
            slot = invoke(0x4db6e0, t, {id, 0});
            if (!slot) {
                put(0x544b14, invoke(0x4db5f0, 0));
                invoke(0x4db4d0, read(t + 4), {t, read(0x544b4c), 12});
                slot = read(t + 20);
            }
        } else
            slot = (id - read(t + 8)) * read(t + 24) + read(t + 16);
        return read(slot);
    }
};
uint32_t body(Run &, uint32_t, uint32_t, const uint32_t *);
uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
    auto &r = *static_cast<Run *>(u);
    if (t >= 0x50b0b4 && uint64_t(t) + n * 4 <= 0x50b0b4 + sizeof boss && t % 4 == 0)
        return const_cast<uint32_t *>(boss) + (t - 0x50b0b4) / 4;
    return r.c.scene.lookup ? r.c.scene.lookup(r.c.scene.context, t, n) : nullptr;
}
uint32_t sceneCall(void *u, ClawSceneActorCall q) {
    auto &r = *static_cast<Run *>(u);
    switch (q.argumentCount) {
    case 0:
        return r.invoke(q.function, q.receiver);
    case 1:
        return r.invoke(q.function, q.receiver, {q.arguments[0]});
    case 2:
        return r.invoke(q.function, q.receiver, {q.arguments[0], q.arguments[1]});
    case 3:
        return r.invoke(q.function, q.receiver, {q.arguments[0], q.arguments[1], q.arguments[2]});
    default:
        return r.invoke(q.function, q.receiver, {q.arguments[0], q.arguments[1], q.arguments[2], q.arguments[3]});
    }
}
ClawSceneActorHost host(Run &r) {
    return {&r, lookup, nullptr, nullptr, sceneCall, nullptr};
}
uint32_t routed(Run &r, uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
    switch (n) {
    case 0:
        return r.invoke(f, t);
    case 1:
        return r.invoke(f, t, {a[0]});
    case 2:
        return r.invoke(f, t, {a[0], a[1]});
    case 3:
        return r.invoke(f, t, {a[0], a[1], a[2]});
    case 4:
        return r.invoke(f, t, {a[0], a[1], a[2], a[3]});
    default:
        r.c.fault = 3;
        throw Failure{};
    }
}
uint64_t bossDependency(ClawRauxContext *, const ClawRauxCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (owned(e->function) || e->function == 0x4c8220 || e->function == 0x4c82a0 || e->function == 0x4c79e0 ||
        e->function == 0x420a10)
        return routed(r, e->function, e->receiver, e->arguments, e->argumentCount);
    ClawAquatisCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, 12, q.arguments);
    q.name = e->name;
    return r.d ? r.d(&r.c, &q, r.user) : 0;
}
uint64_t coreDependency(ClawGabrielContext *, const ClawGabrielCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    return routed(r, e->function, e->receiver, e->arguments, e->argumentCount);
}
struct AnimationView {
    Run *r;
    uint32_t actor, words[128]{};
};
uint32_t *animationLookup(void *p, uint32_t t, uint32_t n) {
    auto &q = *static_cast<AnimationView *>(p);
    if (t >= q.actor && (t - q.actor) % 4 == 0 && (t - q.actor) / 4 + n <= 128)
        return q.words + (t - q.actor) / 4;
    return q.r->span(t, n);
}
uint32_t animationCall(void *p, ClawSceneActorCall e) {
    auto &q = *static_cast<AnimationView *>(p);
    std::copy_n(q.words, 109, q.r->span(q.actor, 109));
    auto v = sceneCall(q.r, e);
    std::copy_n(q.r->span(q.actor, 109), 109, q.words);
    return v;
}

uint32_t resolved(ClawActorResourceBindings *, ClawActorBindingContext *c, const ClawActorBindingCall *, void *) {
    return c->image.token;
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    if (++steps > (c.maximumSteps ? c.maximumSteps : 65536)) {
        c.fault = 3;
        throw Failure{};
    }
    uint32_t args[12]{};
    std::copy(a.begin(), a.end(), args);
    if (owned(f))
        return body(*this, f, t, args);
    uint32_t out = 0;
    if (f == 0x4441b0) {
        ClawGabrielContext g{host(*this), c.globals, 1, 0, 0, c.maximumSteps, 0};
        if (claw_gabriel_entry(f, t, args, uint32_t(a.size()), &g, coreDependency, this, &out)) {
            if (g.fault) {
                c.fault = g.fault;
                throw Failure{};
            }
            return out;
        }
    }
    if (c.composeBoss || f == 0x47e810) {
        ClawRauxContext b{host(*this), c.globals, 0, c.composeImages, 0};
        if (claw_raux_entry(f, t, args, uint32_t(a.size()), &b, bossDependency, this, &out)) {
            if (b.fault) {
                c.fault = b.fault;
                throw Failure{};
            }
            return out;
        }
        if (b.fault) {
            c.fault = b.fault;
            throw Failure{};
        }
    }
    if (c.composeAnimation && (f == 0x4c79e0 || f == 0x4c8220 || f == 0x4c82a0 || f == 0x420a10)) {
        ClawActorAnimationGlobals g{c.globals->animationDelta, c.globals->masterVolume};
        auto h = host(*this);
        AnimationView view{};
        if (f == 0x4c82a0) {
            view.r = this;
            view.actor = read(t + 4);
            std::copy_n(span(view.actor, 109), 109, view.words);
            h.context = &view;
            h.lookup = animationLookup;
            h.call = animationCall;
        }
        claw_actor_animation_entry(f, t, args[0], args[1], &g, h, &c.fault, &out);
        if (f == 0x4c82a0 && view.actor)
            std::copy_n(view.words, 109, span(view.actor, 109));
        if (c.fault)
            throw Failure{};
        return out;
    }
    if (f == 0x4062e0 || f == 0x4061b0 || f == 0x40f6c0 || f == 0x406240 || f == 0x406290 || f == 0x4209d0) {
        ClawActorWrapperContext w{host(*this), 0};
        claw_actor_wrapper_entry(f, t, args, uint32_t(a.size()), &w, nullptr, nullptr, &out);
        if (w.fault) {
            c.fault = w.fault;
            throw Failure{};
        }
        return out;
    }

    if (f == 0x484d90 || f == 0x4041b0 || f == 0x4c9e30 || f == 0x456030 || f == 0x4c96b0 || f == 0x4bb030) {
        ClawStackedActorLifecycleContext z{host(*this), 0};
        claw_stacked_actor_lifecycle_entry(f, t, args, uint32_t(a.size()), &z, &out);
        if (z.fault) {
            c.fault = z.fault;
            throw Failure{};
        }
        return out;
    }
    if (f == 0x4c7970 && c.composeImages) {
        auto registry = read(read(t + 12) + 16) + 16, root = invoke(0x4f6286, registry, {args[0]});
        ClawActorBindingContext x{};
        x.imageRegistryToken = registry;
        x.image.token = root;
        uint32_t image = 0;
        if (root) {
            x.image.minimum = sign(read(root + 100));
            x.image.maximum = sign(read(root + 104));
            ClawPickupPointsContext points{};
            points.scene = host(*this);
            uint32_t index = uint32_t(x.image.minimum);
            claw_pickup_points_entry(0x40f680, root, &index, 1, &points, nullptr, nullptr, &image);
            if (points.fault) {
                c.fault = points.fault;
                throw Failure{};
            }
            x.image.firstImageIndex = x.image.minimum;
            x.image.images = &image;
            x.image.imageCount = 1;
        }
        auto p = span(t, 109);
        ClawActorResourceBindings state{};
        std::copy_n(p, 109, state.actor);
        if (!claw_actor_bind_default_image(&state, &x, label(args[0]), resolved, nullptr)) {
            c.fault = 3;
            throw Failure{};
        }
        std::copy_n(state.actor, 109, p);
        return 1;
    }
    return uint32_t(call(f, t, a));
}
void face(Run &r, uint32_t p, bool flipped, uint32_t kind) {
    if (kind == 5) {
        r.invoke(0x406310, p + 0x128);
        return;
    }
    auto actor = r.read(p + 300);
    if (bool(r.read(actor + 0x40) & 2) == flipped)
        return;
    r.mirror(p, 0x138);
    r.put(actor + 0x40, flipped ? r.read(actor + 0x40) | 2 : r.read(actor + 0x40) & ~2u);
    actor = r.read(p + 300);
    if (kind == 3) {
        r.invoke(0x4060b0, actor);
        return;
    }
    if (kind == 4) {
        r.invoke(0x406120, actor);
        r.invoke(0x406150, actor);
        r.invoke(0x406180, actor);
        return;
    }
    for (auto off : {0x118u, 0x128u, 0x138u}) {
        if ((kind == 1 && off != 0x118) || (kind == 2 && off == 0x138))
            continue;
        if (r.read(actor + off) != 0x80000000)
            r.mirror(actor, off);
    }
    if (kind == 1) {
        r.invoke(0x406150, actor);
        r.invoke(0x406180, actor);
    }
    if (kind == 2)
        r.invoke(0x406180, actor);
}
void select(Run &r, uint32_t p, uint32_t field) {
    r.put(p + 0x134, r.read(r.read(p + 300) + 400));
    r.invoke(0x4c8220, r.read(p + 300) + 0x188, {r.read(p + field)});
}
bool completed(Run &r, uint32_t p) {
    return r.read(r.read(p + 300) + 0x1a4) && !r.read(r.read(p + 300) + 0x19c);
}
void relativeBounds(Run &r, uint32_t actor, uint32_t out) {
    auto image = r.read(actor + 0x174);
    if (!image)
        return;
    ClawSpriteGeometry g{};
    ClawSpriteRect q{};
    g.offsetX = r.read(image + 32);
    g.halfWidth = r.read(image + 24);
    claw_sprite_relative_bounds(&g, &q);
    r.put(out, q.left);
    g.offsetY = r.read(image + 36);
    g.halfHeight = r.read(image + 28);
    claw_sprite_relative_bounds(&g, &q);
    r.put(out + 4, q.top);
    g.halfWidth = r.read(image + 24);
    g.offsetX = r.read(image + 32);
    claw_sprite_relative_bounds(&g, &q);
    r.put(out + 8, q.right);
    g.offsetY = r.read(image + 36);
    g.halfHeight = r.read(image + 28);
    claw_sprite_relative_bounds(&g, &q);
    r.put(out + 12, q.bottom);
}
uint32_t body(Run &r, uint32_t f, uint32_t p, const uint32_t *a) {
    auto &g = *r.c.globals;
    switch (f) {
    case 0x4041f0: {
        auto primary = r.read(a[0] + 108), state = r.read(primary + 28);
        if (!state) {
            r.put(primary + 28, 1000);
            auto child = r.invoke(0x4f63ec, 0, {0x4f0});
            if (child)
                r.invoke(0x404990, child, {a[0]});
            if (!child) {
                r.c.fault = 2;
                throw Failure{};
            }
            r.virt(child, 16);
            r.put(primary + 24, child);
        } else if (state == 29 || state == 30)
            r.virt(r.read(primary + 24), state == 29 ? 32 : 28);
        else if (state != 1000)
            r.invoke(0x4dc870, 0, {r.read(primary + 24)});
        return 1;
    }
    case 0x404990: {
        r.invoke(0x40e0d0, p, {a[0]});
        for (uint32_t off = 0x4cc; off <= 0x4e8; off += 4)
            r.put(p + off, 0);
        r.put(p, 0x50b0b4);
        r.put(0x534874, p);
        r.invoke(0x4c7970, r.read(p + 300), {0x5234d8});
        uint32_t fields[] = {0x338, 0x334, 0x350, 0x464, 0x374, 0x460, 0x468, 0x46c};
        uint32_t names[] = {0x5234c0, 0x52349c, 0x523488, 0x523474, 0x52345c, 0x523448, 0x523430, 0x523418};
        for (unsigned i = 0; i < 8; ++i)
            r.put(p + fields[i], r.sequence(p, names[i]));
        for (uint32_t i = 0; i < 3; ++i)
            r.put(p + 0x470 + i * 4, r.invoke(0x4f6286, r.soundRegistry(p), {0x523400 - i * 24}));
        for (uint32_t i = 0; i < 2; ++i)
            r.put(p + 0x488 + i * 4, r.invoke(0x4f6286, r.soundRegistry(p), {0x5233b8 - i * 24}));
        for (uint32_t i = 0; i < 4; ++i)
            r.put(p + 0x490 + i * 4, r.invoke(0x4061b0, r.soundRegistry(p) - 16, {0x523388 - i * 24}));
        r.put(r.read(p + 300) + 0xd0, 4);
        r.put(r.read(p + 300) + 0xd4, 0x3000026);
        r.put(r.read(p + 300) + 0x164, r.read(r.read(p + 300) + 0x164) & ~1u);
        relativeBounds(r, r.read(p + 300), p + 0x220);
        relativeBounds(r, r.read(p + 300), p + 0x210);
        r.invoke(0x406290, r.read(p + 300));
        r.invoke(0x406240, r.read(p + 300));
        r.put(r.read(p + 12) + 0x104, 15);
        r.put(r.read(p + 12) + 0x104, truncLow(mul(double(sign(r.read(r.read(p + 12) + 0x104))), g.damageScale)));
        for (uint32_t off = 0x28c; off <= 0x298; off += 4)
            r.put(p + off, (off - 0x28c) % 8 ? 500 : 2500);
        r.put(r.read(p + 12) + 0x10c, 100);
        r.put(r.read(p + 12) + 0x10c, truncLow(mul(double(sign(r.read(r.read(p + 12) + 0x10c))), g.healthScale)));
        for (uint32_t off = 0x4a0; off <= 0x4ac; off += 4)
            r.put(p + off, 0);
        r.put(p + 0x4b4, 0);
        r.put(p + 0x4b0, r.read(r.read(p + 12) + 80) - 50);
        r.put(p + 0x4b8, 1);
        for (auto off : {0x4bcu, 0x4c0u, 0x4c4u})
            r.put(p + off, 0);
        r.put(p + 0x4c8, 1);
        r.put(p + 0x4ec, 0);
        r.put(p + 200, 1);
        r.invoke(0x405060, p);
        return p;
    }
    case 0x404310:
        if (r.registry(0x534850, a[0]))
            r.invoke(r.registry(0x534850, a[0]), p);
        else
            r.invoke(0x40e280, p, {a[0]});
        return 0;
    case 0x404e20:
        r.invoke(0x405fa0, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x405fa0:
        r.put(0x534874, 0);
        r.put(p, 0x50b16c);
        r.invoke(0x4dbcd0, p + 0x2f4);
        r.invoke(0x4f6584, p + 0x1a8);
        r.invoke(0x4f6584, p + 0x1a4);
        r.put(p, 0x50b014);
        return 0;
    case 0x405f60:
        if (a[0])
            r.invoke(0x48ce40, 0, {r.read(p + 12), a[0], 0});
        return 0;
    case 0x405060:
        r.transition(p, 0x523268);
        select(r, p, 0x350);
        return 0;
    case 0x4050b0:
        r.transition(p, 0x523148);
        if (r.read(p + 0x4b8)) {
            face(r, p, r.read(p + 0x18c) == 2, r.read(p + 0x18c) == 2 ? 3 : 5);
            r.put(p + 0x4d0, 1000);
            r.put(p + 0x4cc, g.tick);
            auto n = sign(r.invoke(0x4a3050, 0)) % 101;
            select(r, p, n < 50 ? 0x350 : 0x464);
            n = sign(r.invoke(0x4a3050, 0)) % 3;
            r.invoke(0x405f60, p, {r.read(p + 0x470 + uint32_t(n) * 4)});
        }
        return 0;
    case 0x4051a0:
        if (r.read(p + 0x4b8) && !r.read(p + 0x4ec)) {
            r.animate(p);
            if (r.read(p + 0x4c0))
                r.invoke(0x4053d0, p);
            auto relation = sign(r.read(p + 0x184));
            if (relation > 1 && relation < 5 && r.read(p + 0x4d0) <= g.tick - r.read(p + 0x4cc)) {
                r.invoke(0x405240, p);
                return 0;
            }
            if (completed(r, p))
                r.virt(p, 0x48);
        }
        return 0;
    case 0x405240: {
        auto n = sign(r.invoke(0x4a3050, 0)) % 2;
        face(r, p, r.read(p + 0x18c) == 2, 0);
        if (!n)
            r.invoke(0x4055e0, p);
        else if (n == 1)
            r.invoke(0x405740, p);
        else
            r.virt(p, 0x48);
        return 0;
    }
    case 0x4053d0:
        r.transition(p, 0x52321c);
        select(r, p, 0x460);
        r.put(p + 0x4a0, 0);
        r.put(p + 0x4a4, 0);
        r.put(p + 0x4d8, 4000);
        r.put(p + 0x4d4, g.tick);
        return 0;
    case 0x405440:
        r.animate(p);
        if (!r.read(p + 0x4a0)) {
            r.put(p + 0x4a0, 1);
            r.invoke(0x405f60, p, {r.read(p + 0x49c)});
        }
        if (r.read(p + 0x4d8) <= g.tick - r.read(p + 0x4d4) && !r.read(p + 0x4c0) && !r.read(p + 0x4c4))
            r.virt(p, 0x48);
        return 0;
    case 0x4054c0:
        r.transition(p, 0x52323c);
        select(r, p, 0x468);
        r.put(p + 0x4b4, 1);
        r.put(p + 0x4a0, 0);
        r.put(p + 0x4a4, 0);
        r.put(p + 0x4e0, 4000);
        r.put(p + 0x4dc, g.tick);
        return 0;
    case 0x405540:
        r.animate(p);
        if (!r.read(p + 0x4a0)) {
            r.put(p + 0x4a0, 1);
            r.invoke(0x405f60, p, {r.read(p + 0x498)});
        }
        if (r.read(p + 0x4e0) <= g.tick - r.read(p + 0x4dc)) {
            r.put(p + 0x4b4, 0);
            r.virt(p, 0x48);
            return 0;
        }
        r.invoke(!r.read(0x534878) ? 0x4055e0 : 0x405740, p);
        r.put(0x534878, !r.read(0x534878));
        return 0;
    case 0x4055e0:
    case 0x405740:
        r.transition(p, f == 0x4055e0 ? 0x523258 : 0x52324c);
        select(r, p, f == 0x4055e0 ? 0x468 : 0x46c);
        r.put(p + 0x4a4, 0);
        r.put(p + 0x4a0, 0);
        return 0;
    case 0x405640:
    case 0x4057a0:
        r.animate(p);
        if (!r.read(p + 0x4a0)) {
            r.put(p + 0x4a0, 1);
            r.audio(r.read(p + (f == 0x405640 ? 0x490 : 0x494)));
        }
        if (r.read(r.read(p + 300) + 0x16c) == (f == 0x405640 ? 204 : 207)) {
            r.rect(r.read(p + 12) + 0x138, f == 0x405640 ? 0u - 118 : 0u - 130, f == 0x405640 ? 0u - 76 : 10, 0,
                   f == 0x405640 ? 10 : 60);
            if (r.read(r.read(p + 300) + 64) & 2)
                r.mirror(r.read(p + 12), 0x138);
        }
        if (completed(r, p)) {
            if (r.read(p + 0x4b4))
                r.transition(p, 0x52323c);
            else
                r.virt(p, 0x48);
        }
        return 0;
    case 0x4058b0:
        r.transition(p, 0x523228);
        face(r, p, r.read(p + 0x18c) == 2, r.read(p + 0x18c) == 2 ? 4 : 5);
        select(r, p, 0x464);
        r.audio(r.read(p + 0x418));
        r.audio(r.read(p + 0x41c));
        r.put(p + 0x4a0, 0);
        r.put(p + 0x4a4, 0);
        r.put(r.read(p + 12) + 0x10c, r.read(r.read(p + 12) + 0x10c) - 20);
        r.put(p + 0x4a8, r.read(p + 0x4a8) + 1);
        if (sign(r.read(p + 0x4a8)) > 4) {
            r.put(r.read(p + 12) + 0x10c, 0);
            r.invoke(0x405d50, p);
        }
        return 0;
    case 0x4059e0:
        r.animate(p);
        if (!r.read(p + 0x4a0)) {
            r.put(p + 0x4a0, 1);
            r.invoke(0x405f60, p, {r.read(p + 0x488)});
        }
        if (completed(r, p) && !r.read(p + 0x4a4)) {
            r.put(p + 0x4a4, 1);
            r.invoke(0x4054c0, p);
        }
        return 0;
    case 0x405a60:
        r.animate(p);
        if (completed(r, p)) {
            r.put(p + 0x4ac, r.read(p + 0x4ac) + 1);
            if (r.read(p + 0x4ac) == 3) {
                r.put(p + 0x4ac, 0);
                r.invoke(0x4053d0, p);
                return 0;
            }
            if (sign(r.invoke(0x4a3050, 0)) % 101 < 85)
                r.invoke(0x405240, p);
            else
                r.virt(p, 0x48);
        }
        return 0;
    case 0x405af0: {
        if (!r.read(p + 0x4b8) || r.read(p + 0x4b4))
            return 0;
        for (auto name : {0x52323cu, 0x523228u, 0x5234f4u, 0x523210u, 0x523204u, 0x5231f8u}) {
            auto cell = r.invoke(0x406020, 0x537698, {r.read(r.read(p + 16) + 28)});
            if (!r.invoke(0x4a3810, 0, {r.read(cell), name}))
                return 0;
        }
        if (r.read(p + 0x4e8) > g.tick - r.read(p + 0x4e4))
            return 0;
        auto attacker = r.read(r.read(p + 12) + 116);
        if (!attacker)
            return 0;
        bool accepted = false;
        if (r.read(attacker + 208) == 4) {
            r.put(p + 0x4e8, 1000);
            r.put(p + 0x4e4, g.tick);
            r.invoke(0x4058b0, p);
            accepted = true;
        } else {
            auto cell = r.invoke(0x441030, 0x537698, {r.read(r.read(p + 16) + 28)});
            auto n = r.read(0x5376b8), t = r.read(0x5376b4);
            if (n > 4096) {
                r.c.fault = 3;
                throw Failure{};
            }
            for (uint32_t i = 0; i < n; ++i, t += 4)
                if (t)
                    r.invoke(0x4f6439, t);
            if (r.invoke(0x4a3810, 0, {r.read(cell), 0x52321c})) {
                r.put(p + 0x4e8, 500);
                r.put(p + 0x4e4, g.tick);
                r.invoke(r.read(r.read(r.read(g.playerToken + 108) + 20) + 20) ? 0x44f510 : 0x44f3c0, p);
                accepted = true;
                r.put(p + 200, 1);
            }
        }
        if (accepted)
            r.invoke(0x440e20, p, {attacker});
        if (r.read(attacker + 208) == 0x20)
            r.put(attacker + 8, r.read(attacker + 8) | 0x10000);
        return 0;
    }
    case 0x405d50:
        r.transition(p, 0x5231f8);
        select(r, p, 0x374);
        r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) | 0x80);
        r.rect(p + 0x220, 0x80000000, 0, 0, 0);
        r.rect(p + 0x210, 0x80000000, 0, 0, 0);
        r.put(p + 0x4a0, 0);
        r.put(p + 0x4a4, 0);
        return 0;
    case 0x405df0:
        r.animate(p);
        if (!r.read(p + 0x4a0)) {
            r.put(p + 0x4a0, 1);
            r.invoke(0x405f60, p, {r.read(p + 0x48c)});
        }
        if (completed(r, p) && !r.read(p + 0x4a4)) {
            r.put(p + 0x4a4, 1);
            if (sign(r.read(g.playerToken + 0x10c)) > 0) {
                r.invoke(0x420590, 0);
                r.invoke(0x40e5c0, p);
                r.invoke(0x48cf50, 0, {r.read(p + 12)});
                r.put(p + 0x4b8, 0);
                auto bits = r.read(p + 0x2fc);
                if (bits < 5)
                    r.invoke(0x4dbd20, p + 0x2f4, {4});
                else if (bits > 32)
                    r.put(r.read(p + 0x300), r.read(r.read(p + 0x300)) | 16);
                else
                    r.put(p + 0x300, r.read(p + 0x300) | 16);
            }
        }
        return 0;
    case 0x405ed0:
        if (r.read(p + 0x4b8)) {
            r.put(r.read(p + 12) + 0x10c, 100);
            r.put(r.read(p + 12) + 0x10c, truncLow(mul(double(sign(r.read(r.read(p + 12) + 0x10c))), g.healthScale)));
            for (auto off : {0x4a0u, 0x4a4u, 0x4a8u, 0x4acu})
                r.put(p + off, 0);
            r.put(p + 0x4b0, r.read(r.read(p + 12) + 80) - 50);
            for (auto off : {0x4b4u, 0x4bcu, 0x4c0u, 0x4c4u, 0x4c8u})
                r.put(p + off, 0);
            r.put(p + 0x4ec, 1022);
            r.virt(p, 0x48);
        }
        return 0;
    default:
        r.c.fault = 3;
        throw Failure{};
    }
}
bool owned(uint32_t f) {
    switch (f) {
    case 0x4041f0:
    case 0x404990:
    case 0x404310:
    case 0x404e20:
    case 0x405fa0:
    case 0x405f60:
    case 0x405060:
    case 0x4050b0:
    case 0x4051a0:
    case 0x405240:
    case 0x4053d0:
    case 0x405440:
    case 0x4054c0:
    case 0x405540:
    case 0x4055e0:
    case 0x405740:
    case 0x405640:
    case 0x4057a0:
    case 0x4058b0:
    case 0x4059e0:
    case 0x405a60:
    case 0x405af0:
    case 0x405d50:
    case 0x405df0:
    case 0x405ed0:
        return true;
    default:
        return false;
    }
}
} // namespace
extern "C" uint32_t claw_aquatis_allocation_bytes(uint32_t f) {
    return f == 0x4041f0 ? 0x4f0 : 0;
}
extern "C" uint32_t claw_aquatis_function(uint32_t vt, uint32_t slot) {
    return vt == 0x50b0b4 && slot % 4 == 0 && slot / 4 < 45 ? boss[slot / 4] : 0;
}
extern "C" uint32_t claw_aquatis_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, ClawAquatisContext *c,
                                       ClawAquatisDependency d, void *u, uint32_t *out) {
    if (!c || !c->globals || !owned(f))
        return 0;
    uint32_t need = f == 0x4041f0 || f == 0x404990 || f == 0x404310 || f == 0x404e20 || f == 0x405f60 ? 1 : 0;
    if (n != need || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    if (c->fault)
        return 0;
    uint32_t args[12]{};
    if (n)
        std::copy_n(a, n, args);
    Run r{*c, d, u};
    try {
        auto v = body(r, f, t, args);
        if (out)
            *out = v;
        return !c->fault;
    } catch (Failure &) {
        return 0;
    }
}
