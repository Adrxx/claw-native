#include "GabrielWeaponsRuntime.h"
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
const uint32_t base[] = {0x484d90, 0x4c9e30, 0x4141f0, 0x4041b0, 0x4c96b0, 0x4bb030, 0x4bb030, 0x4c96b0, 0x4c96b0};
const uint32_t ball[] = {0x484d90, 0x4c9e30, 0x473f40, 0x4063b0, 0x4741f0, 0x4bb030,
                         0x4bb030, 0x4c96b0, 0x4c96b0, 0x4dca10, 0x474290, 0x4bb030};
const char *label(uint32_t t) {
    switch (t) {
    case 0x522dbc:
        return "CannonBall";
    case 0x522d54:
        return "LogicHit";
    case 0x522d48:
        return "LogicAttack";
    case 0x5234ec:
        return "LS_HOME";
    case 0x524548:
        return "LS_FIRING";
    case 0x524538:
        return "LS_VERTFIRING";
    case 0x52788c:
        return "LS_ROTATE";
    case 0x524418:
        return "LS_EXPLODING";
    case 0x52458c:
        return "LEVEL_CANNONBALL";
    case 0x524574:
        return "LEVEL_CANNONBALL_FALL";
    case 0x522afc:
        return "GabrielBomb";
    case 0x522c68:
        return "RedTailPirate";
    case 0x523148:
        return "LS_IDLE";
    case 0x5231f8:
        return "LS_DEADACT1";
    case 0x523268:
        return "LS_STARTUP";
    case 0x5234b4:
        return "GAME_NULL";
    case 0x52740c:
        return "LS_DEADACT4";
    case 0x527418:
        return "LS_DEADACT3";
    case 0x527424:
        return "LS_DEADACT2";
    case 0x527430:
        return "LS_BLOCKED";
    case 0x52743c:
        return "LS_CANNONHIT";
    case 0x52744c:
        return "LS_CANNONATTACK";
    case 0x52745c:
        return "LS_THUGATTACK1";
    case 0x52746c:
        return "LS_MULTIBOMBATTACK";
    case 0x5274a8:
        return "LEVEL_GABRIEL_00400010";
    case 0x5274c0:
        return "LEVEL_GABRIEL_00400007";
    case 0x5274d8:
        return "LEVEL_GABRIEL_00400009";
    case 0x5274f0:
        return "LEVEL_GABRIEL_00400023";
    case 0x527508:
        return "LEVEL_GABRIEL_00400030";
    case 0x527520:
        return "LEVEL_GABRIEL_00400017";
    case 0x527538:
        return "LEVEL_GABRIEL_00400016";
    case 0x527550:
        return "LEVEL_GABRIEL_00400015";
    case 0x527568:
        return "LEVEL_GABRIEL_00400014";
    case 0x527580:
        return "LEVEL_GABRIEL_00400022";
    case 0x527598:
        return "LEVEL_GABRIEL_00400012";
    case 0x5275b0:
        return "LEVEL_GABRIEL_00400011";
    case 0x5275c8:
        return "LEVEL_GABRIEL_00400029";
    case 0x5275e0:
        return "LEVEL_GABRIEL_00400028";
    case 0x5275f8:
        return "LEVEL_GABRIEL_00400002";
    case 0x527610:
        return "LEVEL_GABRIEL_BLOCKED";
    case 0x527628:
        return "LEVEL_GABRIEL_STRIKE7";
    case 0x527640:
        return "LEVEL_GABRIEL_STRIKE6";
    case 0x527658:
        return "LEVEL_GABRIEL_STRIKE5";
    case 0x527670:
        return "LEVEL_GABRIEL_STRIKE4";
    case 0x527688:
        return "LEVEL_GABRIEL_STRIKE3";
    case 0x5276a0:
        return "LEVEL_GABRIEL_STRIKE2";
    case 0x5276b8:
        return "LEVEL_GABRIEL_STRIKE1";
    case 0x5276d0:
        return "LEVEL_GABRIEL_KILLFALL4";
    case 0x5276e8:
        return "LEVEL_GABRIEL_KILLFALL3";
    case 0x527700:
        return "LEVEL_GABRIEL_KILLFALL2";
    case 0x527718:
        return "LEVEL_GABRIEL_KILLFALL1";
    case 0x527730:
        return "LEVEL_GABRIEL_IDLE2";
    case 0x527744:
        return "LEVEL_GABRIEL_IDLE1";
    case 0x527758:
        return "LEVEL_GABRIEL_HITLOW";
    case 0x527770:
        return "LEVEL_GABRIEL_HITHIGH";
    case 0x527788:
        return "LEVEL_GABRIEL";
    case 0x5277c4:
        return "LEVEL_GABRIELBOMB_BOMBWHISTLE1";
    case 0x5277e4:
        return "LEVEL_GABRIELBOMB_SEXPLOSION3";
    case 0x527804:
        return "LEVEL_GABRIELBOMB_SEXPLOSION2";
    case 0x527824:
        return "LEVEL_GABRIELBOMB_SEXPLOSION1";
    case 0x527844:
        return "LEVEL_GABRIELBOMB_EXPLODE";
    case 0x527860:
        return "LEVEL_GABRIELBOMB_FALL";
    case 0x527878:
        return "LEVEL_GABRIELBOMB";
    case 0x5278d0:
        return "LEVEL_GABRIELCANNON_CANNON";
    case 0x5278ec:
        return "LEVEL_GABRIELCANNON_CANNONDROP";
    case 0x52790c:
        return "LEVEL_GABRIELCANNON_CANNONRISE";
    case 0x52792c:
        return "LEVEL_GABRIELCANNON_REST";
    case 0x527948:
        return "LEVEL_GABRIELCANNON_RISE";
    case 0x527964:
        return "LEVEL_GABRIELCANNON_VERTIFIRE";
    case 0x527984:
        return "LEVEL_GABRIELCANNON_HORZFIRE";
    case 0x5279a4:
        return "LEVEL_GABRIELCANNON";
    default:
        return nullptr;
    }
}
int32_t sign(uint32_t v) {
    int32_t x;
    std::memcpy(&x, &v, 4);
    return x;
}
bool owned(uint32_t);
struct Run {
    ClawGabrielWeaponsContext &c;
    ClawGabrielWeaponsDependency d;
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
        ClawGabrielWeaponsCall e{};
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
        uint32_t vt = read(t), f = claw_gabriel_weapons_function(vt, slot);
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
    for (auto vt : {0x50b9dcu, 0x50ba04u, 0x50df44u, 0x50ded4u})
        if (t >= vt && (t - vt) % 4 == 0) {
            uint32_t count = vt == 0x50ba04 ? 12 : vt == 0x50ded4 ? 16 : 9;
            if ((t - vt) / 4 + n <= count) {
                if (vt == 0x50b9dc)
                    return const_cast<uint32_t *>(base) + (t - vt) / 4;
                if (vt == 0x50ba04)
                    return const_cast<uint32_t *>(ball) + (t - vt) / 4;
            }
        }
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
void release(void *u, uint32_t t) {
    auto &r = *static_cast<Run *>(u);
    r.invoke(0x4f6428, 0, {t});
}
ClawSceneActorHost host(Run &r) {
    return {&r, lookup, nullptr, release, sceneCall, nullptr};
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
    case 5:
        return r.invoke(f, t, {a[0], a[1], a[2], a[3], a[4]});
    case 6:
        return r.invoke(f, t, {a[0], a[1], a[2], a[3], a[4], a[5]});
    default:
        r.c.fault = 3;
        throw Failure{};
    }
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
uint64_t projectileDependency(ClawPlayerProjectileContext *, const ClawPlayerProjectileCall *e, void *u) {
    auto &view = *static_cast<AnimationView *>(u);
    auto &r = *view.r;
    std::copy_n(view.words, 109, r.span(view.actor, 109));
    uint64_t result;
    if (e->name && !e->argumentCount) {
        ClawGabrielWeaponsCall q{};
        q.function = e->function;
        q.receiver = e->receiver;
        q.name = e->name;
        if (!r.d) {
            r.c.fault = 1;
            throw Failure{};
        }
        result = r.d(&r.c, &q, r.user);
    } else
        result = routed(r, e->function, e->receiver, e->arguments, e->argumentCount);
    std::copy_n(r.span(view.actor, 109), 109, view.words);
    return result;
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
    if (c.composeCore) {
        ClawGabrielContext b{host(*this), c.globals, 1, c.composeAnimation, c.composeImages, c.maximumSteps, 0};
        if (claw_gabriel_entry(f, t, args, uint32_t(a.size()), &b, coreDependency, this, &out)) {
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
    if (c.composeProjectiles) {
        uint32_t receiver = t, count = uint32_t(a.size());
        if (f == 0x4dc870) {
            receiver = args[0];
            count = 0;
        }
        if (f == 0x4dc870 || f == 0x473c50 || f == 0x4084b0 || f == 0x408580 || f == 0x408860 || f == 0x408870 ||
            f == 0x4089d0 || f == 0x408510 || f == 0x473f40 || f == 0x4741f0 || f == 0x474290 || f == 0x4742f0 ||
            f == 0x4dca10 || f == 0x4063b0) {
            if (!c.bullet || !c.bullet->generic) {
                c.fault = 1;
                throw Failure{};
            }
            auto bullet = *c.bullet;
            auto generic = *bullet.generic;
            bullet.generic = &generic;
            ClawPlayerProjectileGlobals g{c.globals->tick,         c.globals->animationDelta, read(0x53724c),
                                          c.globals->managerToken, c.globals->audioEnabled,   c.globals->masterVolume};
            auto h = host(*this);
            AnimationView view{};
            view.r = this;
            view.actor = f == 0x473c50 || f == 0x4084b0 ? args[0] : read(receiver + 12);
            std::copy_n(span(view.actor, 109), 109, view.words);
            h.context = &view;
            h.lookup = animationLookup;
            h.call = animationCall;
            ClawPlayerProjectileContext x{h, &g, &bullet, c.composeAnimation, 0};
            auto ok = claw_player_projectile_entry(f, receiver, args, count, &x, projectileDependency, &view, &out);
            std::copy_n(view.words, 109, span(view.actor, 109));
            if (x.fault) {
                c.fault = x.fault;
                throw Failure{};
            }
            if (ok)
                return out;
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
    if (f == 0x40fe90) {
        rect(t + 0x138, args[0], args[1], args[2], args[3]);
        return 0;
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
void cannonSelect(Run &r, uint32_t p, uint32_t name, uint32_t field) {
    r.transition(p, name);
    r.put(p + 0x34, r.read(r.read(p + 0x2c) + 400));
    r.invoke(0x4c8220, r.read(p + 0x2c) + 392, {r.read(p + field)});
}
void bombSelect(Run &r, uint32_t p, uint32_t field) {
    r.put(p + 0x134, r.read(r.read(p + 300) + 400));
    r.invoke(0x4c8220, r.read(p + 300) + 392, {r.read(p + field)});
}
bool completed(Run &r, uint32_t actor) {
    return r.read(actor + 420) && !r.read(actor + 412);
}
void cannonMirror(Run &r, uint32_t p) {
    auto actor = r.read(p + 44);
    if (!(r.read(actor + 64) & 2)) {
        r.mirror(p, 56);
        r.put(actor + 64, r.read(actor + 64) | 2);
        actor = r.read(p + 44);
        for (auto off : {0x118u, 0x128u, 0x138u})
            if (r.read(actor + off) != 0x80000000)
                r.mirror(actor, off);
    }
    actor = r.read(p + 12);
    auto speed = r.read(actor + 0x148);
    if (sign(speed) > 0) {
        r.put(actor + 0x148, 0 - speed);
        r.put(p + 0x5c, 0 - r.read(p + 0x5c));
        r.put(p + 100, 0 - r.read(p + 100));
    }
}
void fired(Run &r, uint32_t p, bool vertical) {
    auto visual = r.read(p + 44);
    auto mark = r.invoke(0x4c82a0, visual + 392, {r.c.globals->animationDelta});
    if (mark == 1 && !r.read(p + 88)) {
        r.put(p + 88, 1);
        visual = r.read(p + 44);
        auto child = r.invoke(0x4c8da0, r.read(r.read(r.read(p + 48) + 12) + 8),
                              {0, r.read(visual + 76) + r.read(p + (vertical ? 100 : 92)),
                               r.read(visual + 80) + r.read(p + (vertical ? 104 : 96)), r.read(visual + 100) - 1,
                               0x522dbc, 0x40000});
        if (!child) {
            r.c.fault = 2;
            throw Failure{};
        }
        r.invoke(r.read(r.read(child + 108) + 16), 0, {child});
        auto projectile = r.read(r.read(child + 108) + 24);
        r.real(projectile + 80, double(sign(r.read(r.read(p + 12) + 0x148))));
        r.real(projectile + 88, double(sign(r.read(r.read(p + 12) + 0x14c))));
        r.put(projectile + 64, 0);
        r.put(projectile + 68, 0);
        r.audio(r.read(p + 84));
        if (sign(r.read(r.read(p + 12) + 0x148)) < 0) {
            projectile = r.read(r.read(child + 108) + 24);
            auto actor = r.read(projectile + 300);
            if (!(r.read(actor + 64) & 2)) {
                r.mirror(projectile, 0x138);
                r.put(actor + 64, r.read(actor + 64) | 2);
                actor = r.read(projectile + 300);
                for (auto off : {0x118u, 0x128u, 0x138u})
                    if (r.read(actor + off) != 0x80000000)
                        r.mirror(actor, off);
            }
        }
    }
    if (completed(r, r.read(p + 44)))
        r.invoke(0x4145b0, p);
}
uint32_t body(Run &r, uint32_t f, uint32_t p, const uint32_t *a) {
    auto &g = *r.c.globals;
    switch (f) {
    case 0x414b20: {
        auto primary = r.read(a[0] + 108), state = r.read(primary + 28);
        if (!state) {
            r.put(primary + 28, 1000);
            auto child = r.invoke(0x4f63ec, 0, {0x150});
            if (child)
                r.invoke(0x414be0, child, {a[0]});
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
    case 0x414be0:
        r.invoke(0x473c50, p, {a[0]});
        r.put(p, 0x50ba04);
        r.put(p + 64, 0);
        r.put(p + 68, 0);
        if (!r.read(a[0] + 0x170))
            r.invoke(0x4c7970, r.read(p + 300), {0x52458c});
        r.put(p + 0x148, r.invoke(0x4f6286, r.read(r.read(r.read(p + 300) + 12) + 44) + 16, {0x524574}));
        r.put(r.read(p + 300) + 0xd0, 0x40);
        r.put(r.read(p + 300) + 0xd4, 2);
        if (!r.read(r.read(p + 12) + 0x104))
            r.put(r.read(p + 12) + 0x104, 10);
        r.invoke(0x474290, p);
        return p;
    case 0x414030: {
        r.put(p, 0x50b064);
        r.put(p + 8, a[0]);
        r.put(p + 12, a[0]);
        r.put(p + 16, r.read(a[0] + 108));
        r.put(p + 4, 0);
        r.invoke(0x4c7fa0, a[0], {0x522d54});
        r.invoke(0x4c8060, r.read(p + 12), {0x522d48});
        r.put(p + 20, 0);
        r.put(p + 24, 0);
        r.put(p + 28, 1001);
        r.put(p + 32, 2);
        r.put(p + 40, a[0]);
        r.put(p + 44, a[0]);
        r.put(p + 48, r.read(a[0] + 108));
        r.put(p + 116, 0);
        r.put(p + 120, 0);
        r.put(p, 0x50b9dc);
        auto actor = r.read(p + 12);
        if (!r.read(actor + 0x148))
            r.put(actor + 0x148, 500);
        actor = r.read(p + 12);
        if (!r.read(actor + 0x14c))
            r.put(actor + 0x14c, 0);
        actor = r.read(p + 12);
        if (!r.read(actor + 0x104))
            r.put(actor + 0x104, 10);
        actor = r.read(p + 12);
        if (!r.read(actor + 100)) {
            r.put(actor + 100, 0xf96);
            r.put(actor + 8, r.read(actor + 8) | 0x20000);
        }
        for (auto off : {72u, 76u, 80u, 112u, 84u})
            r.put(p + off, 0);
        if (r.read(r.read(p + 44) + 64) & 2)
            cannonMirror(r, p);
        r.put(p + 92, 50);
        r.put(p + 96, 10);
        r.put(p + 100, 0u - 26);
        r.put(p + 104, 0u - 10);
        actor = r.read(p + 44);
        r.put(actor + 8, r.read(actor + 8) | 1);
        r.put(r.read(p + 44) + 8, r.read(r.read(p + 44) + 8) | 0x40);
        return p;
    }
    case 0x4141f0: {
        if (r.registry(0x534bf8, a[0]))
            r.invoke(r.registry(0x534bf8, a[0]), p);
        else
            r.invoke(0x4a36f0, 0, {p});
        return 0;
    }
    case 0x4145b0:
        cannonSelect(r, p, 0x5234ec, 72);
        return 0;
    case 0x4145f0:
        r.invoke(0x4c82a0, r.read(p + 44) + 392, {g.animationDelta});
        if (r.read(p + 120) <= g.tick - r.read(p + 116)) {
            r.put(p + 120, 3000);
            r.put(p + 116, g.tick);
            r.invoke(0x414640, p);
        }
        return 0;
    case 0x414640:
        r.invoke(r.read(p + 112) ? 0x414860 : 0x414660, p);
        return 0;
    case 0x414660:
    case 0x414860:
        cannonSelect(r, p, f == 0x414660 ? 0x524548 : 0x524538, f == 0x414660 ? 76 : 80);
        r.put(p + 88, 0);
        return 0;
    case 0x4146b0:
    case 0x4148b0:
        fired(r, p, f == 0x4148b0);
        return 0;
    case 0x414a60:
        cannonMirror(r, p);
        return 0;
    case 0x446a70:
        r.invoke(0x414030, p, {a[0]});
        r.put(p, 0x50df44);
        r.invoke(0x4c7970, r.read(p + 44), {0x5279a4});
        for (uint32_t i = 0; i < 2; ++i)
            r.put(p + 76 + i * 4,
                  r.invoke(0x4f6286, r.read(r.read(r.read(p + 44) + 12) + 44) + 16, {0x527984 - i * 32}));
        r.put(p + 124, r.invoke(0x4f6286, r.read(r.read(r.read(p + 44) + 12) + 44) + 16, {0x527948}));
        r.put(p + 128, r.invoke(0x4f6286, r.read(r.read(r.read(p + 44) + 12) + 44) + 16, {0x52792c}));
        for (uint32_t i = 0; i < 3; ++i)
            r.put(p + (i < 2 ? 132 + i * 4 : 84), r.invoke(0x4f6286, r.read(r.read(r.read(p + 44) + 12) + 40) + 16,
                                                           {i == 0   ? 0x52790cu
                                                            : i == 1 ? 0x5278ecu
                                                                     : 0x5278d0u}));
        r.put(p + 92, 50);
        r.put(p + 96, 54);
        r.put(p + 100, 0u - 26);
        r.put(p + 104, 0u - 10);
        if (r.read(r.read(p + 44) + 64) & 2) {
            r.put(p + 92, 0u - 50);
            r.put(p + 100, 26);
        }
        r.invoke(0x446c20, p);
        return p;
    case 0x446c20: {
        r.put(p + 140, 0);
        r.put(p + 144, 0);
        if (r.read(0x53774c)) {
            r.put(r.read(0x53774c) + 0x518, 0);
            r.put(r.read(0x53774c) + 0x51c, 0);
            r.put(r.read(0x53774c) + 0x534, r.read(r.read(0x53774c) + 0x534) & ~1u);
        }
        auto actor = r.read(p + 44), root = r.read(actor + 0x170);
        if (root) {
            uint32_t image =
                sign(r.read(root + 100)) < 2 && sign(r.read(root + 104)) > 0 ? r.read(r.read(root + 20) + 4) : 0;
            r.put(actor + 0x174, image);
            r.put(actor + 0x16c, 1);
        }
        r.invoke(0x4145b0, p);
        return 0;
    }
    case 0x446ca0:
        if (r.read(0x53774c) && !r.read(r.read(0x53774c) + 0x520)) {
            if (r.read(r.read(0x53774c) + 0x534) & 1) {
                r.invoke(0x446c20, p);
                return 0;
            }
            r.invoke(0x4c82a0, r.read(p + 44) + 392, {g.animationDelta});
            if (r.read(p + 140) && r.read(p + 144)) {
                r.put(p + 140, 0);
                r.invoke(0x446e10, p);
                return 0;
            }
            if (r.read(r.read(0x53774c) + 0x51c) && !r.read(p + 144)) {
                r.put(p + 140, 0);
                r.invoke(0x446d70, p);
                return 0;
            }
            if (r.read(r.read(0x53774c) + 0x518)) {
                r.invoke(0x414640, p);
                r.put(r.read(0x53774c) + 0x518, 0);
                r.put(p + 140, 1);
            }
        }
        return 0;
    case 0x446d70:
    case 0x446e10:
        cannonSelect(r, p, 0x52788c, f == 0x446d70 ? 124 : 128);
        r.put(r.read(p + 12) + 0x148, f == 0x446d70 ? 0 : 0u - 500);
        r.put(r.read(p + 12) + 0x14c, f == 0x446d70 ? 0u - 500 : 0);
        r.put(p + 148, 0);
        if (f == 0x446e10 && r.read(0x53774c))
            r.put(r.read(0x53774c) + 0x51c, 0);
        r.put(p + 144, f == 0x446d70 ? 1 : 0);
        r.put(p + 112, f == 0x446d70 ? 1 : 0);
        r.audio(r.read(p + (f == 0x446d70 ? 132 : 136)));
        return 0;
    case 0x446eb0:
        r.invoke(0x4c82a0, r.read(p + 44) + 392, {g.animationDelta});
        if (completed(r, r.read(p + 44)))
            r.invoke(0x4145b0, p);
        return 0;
    case 0x445ef0:
        r.invoke(0x4084b0, p, {a[0]});
        r.put(p, 0x50ded4);
        if (!r.read(r.read(p + 300) + 0x170))
            r.invoke(0x4c7970, r.read(p + 300), {0x527878});
        for (auto off : {0x150u, 0x148u})
            r.put(p + off, r.invoke(0x4f6286, r.read(r.read(r.read(p + 300) + 12) + 44) + 16, {0x527860}));
        r.put(p + 0x170, r.invoke(0x4f6286, r.read(r.read(r.read(p + 300) + 12) + 44) + 16, {0x527844}));
        for (uint32_t i = 0; i < 2; ++i)
            r.put(p + 0x174 + i * 4,
                  r.invoke(0x4f6286, r.read(r.read(r.read(p + 300) + 12) + 40) + 16, {0x527824 - i * 32}));
        r.put(p + 0x17c, r.invoke(0x4061b0, r.read(r.read(r.read(p + 300) + 12) + 40), {0x5277e4}));
        for (uint32_t i = 0; i < 3; ++i)
            r.put(p + 0x180 + i * 4, r.invoke(0x4061b0, r.read(r.read(r.read(p + 300) + 12) + 40), {0x5277c4}));
        r.put(p + 0x18c, 0);
        r.invoke(0x40fe90, r.read(p + 300), {0u - 50, 0u - 50, 50, 50});
        r.put(r.read(p + 300) + 0xd0, 0x40);
        r.invoke(0x406290, r.read(p + 300));
        if (!r.read(r.read(p + 12) + 0x104))
            r.put(r.read(p + 12) + 0x104, 15);
        r.put(r.read(p + 300) + 0x164, r.read(r.read(p + 300) + 0x164) | 0x2020);
        r.put(p + 0x15c, 0);
        r.put(p + 0x168, 10000);
        r.put(r.read(p + 12) + 0xcc, 7);
        r.put(p + 400, 0);
        return p;
    case 0x446340:
        r.transition(p, 0x524418);
        r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) | 4);
        r.put(r.read(p + 300) + 0xd0, 0x1000000);
        bombSelect(r, p, 0x170);
        r.put(p + 200, 1);
        {
            auto i = sign(r.invoke(0x4a3050, 0)) % 3;
            r.audio(r.read(p + 0x174 + uint32_t(i) * 4));
        }
        return 0;
    case 0x4463f0:
        if (r.read(0x53774c) && r.read(r.read(0x53774c) + 0x520)) {
            r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) | 0x80);
            r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) | 0x10000);
            return 0;
        }
        if (r.animate(p) == 1 && !r.read(p + 0x18c)) {
            r.put(p + 0x18c, 1);
            r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) & ~0x80u);
        }
        if (completed(r, r.read(p + 300)))
            r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) | 0x10000);
        return 0;
    case 0x446490:
        if (!r.read(p + 400)) {
            r.put(p + 400, 1);
            auto i = sign(r.invoke(0x4a3050, 0)) % 3;
            if (r.read(p + 0x180 + uint32_t(i) * 4) && g.audioEnabled)
                r.invoke(0x4b45f0, r.read(r.read(p + 0x180 + uint32_t(i) * 4) + 16), {g.masterVolume, 0, 0, 0});
        }
        if (r.read(0x53774c)) {
            if (r.read(r.read(0x53774c) + 0x520)) {
                r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) | 0x80);
                r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) | 0x10000);
                return 0;
            }
            r.animate(p);
            if (double(sign(r.read(r.read(0x53774c) + 0x530))) <= r.real(p + 112))
                r.virt(p, 44);
        }
        return 0;
    case 0x432550:
        r.put(p + 200, 1);
        return 0;
    case 0x432560:
        r.put(p + 200, 1);
        r.virt(p, 44);
        return 0;
    default:
        r.c.fault = 3;
        throw Failure{};
    }
}
bool owned(uint32_t f) {
    switch (f) {
    case 0x414b20:
    case 0x414be0:
    case 0x414030:
    case 0x4141f0:
    case 0x4145b0:
    case 0x4145f0:
    case 0x414640:
    case 0x414660:
    case 0x4146b0:
    case 0x414860:
    case 0x4148b0:
    case 0x414a60:
    case 0x446a70:
    case 0x446c20:
    case 0x446ca0:
    case 0x446d70:
    case 0x446e10:
    case 0x446eb0:
    case 0x445ef0:
    case 0x446340:
    case 0x4463f0:
    case 0x446490:
    case 0x432550:
    case 0x432560:
        return true;
    default:
        return false;
    }
}
} // namespace
extern "C" uint32_t claw_gabriel_weapons_allocation_bytes(uint32_t f) {
    return f == 0x414b20 ? 0x150 : claw_gabriel_allocation_bytes(f);
}
extern "C" uint32_t claw_gabriel_weapons_function(uint32_t vt, uint32_t slot) {
    if (slot % 4)
        return 0;
    if (vt == 0x50b9dc && slot / 4 < 9)
        return base[slot / 4];
    if (vt == 0x50ba04 && slot / 4 < 12)
        return ball[slot / 4];
    return claw_gabriel_function(vt, slot);
}
extern "C" uint32_t claw_gabriel_weapons_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                               ClawGabrielWeaponsContext *c, ClawGabrielWeaponsDependency d, void *u,
                                               uint32_t *out) {
    if (!c || !c->globals)
        return 0;
    uint32_t need =
        f == 0x414b20 || f == 0x414be0 || f == 0x414030 || f == 0x4141f0 || f == 0x446a70 || f == 0x445ef0 ? 1 : 0;
    bool supported =
        owned(f) ||
        (c->composeCore && (f == 0x4459d0 || f == 0x446550 || f == 0x445af0 || f == 0x446670 || f == 0x446130)) ||
        (c->composeProjectiles && (f == 0x484d90 || f == 0x456030 || f == 0x4dc870 || f == 0x408860 || f == 0x408870 ||
                                   f == 0x4089d0 || f == 0x408510 || f == 0x473f40 || f == 0x4741f0 || f == 0x474290 ||
                                   f == 0x4742f0 || f == 0x4dca10 || f == 0x4063b0));
    if (!supported)
        return 0;
    if (!owned(f))
        need = f == 0x4459d0 || f == 0x446550 || f == 0x445af0 || f == 0x446670 || f == 0x446130 || f == 0x484d90 ||
                       f == 0x4dc870 || f == 0x473f40
                   ? 1
                   : 0;
    if (n != need || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    if (c->fault || n > 12 || (n && !a))
        return 0;
    uint32_t args[12]{};
    std::copy_n(a, n, args);
    Run r{*c, d, u};
    try {
        uint32_t value;
        if (owned(f))
            value = body(r, f, t, args);
        else if (c->composeCore && (f == 0x4459d0 || f == 0x446550 || f == 0x445af0 || f == 0x446670 || f == 0x446130))
            value = r.invoke(f, t, n ? std::initializer_list<uint32_t>{args[0]} : std::initializer_list<uint32_t>{});
        else if (c->composeProjectiles &&
                 (f == 0x484d90 || f == 0x456030 || f == 0x4dc870 || f == 0x408860 || f == 0x408870 || f == 0x4089d0 ||
                  f == 0x408510 || f == 0x473f40 || f == 0x4741f0 || f == 0x474290 || f == 0x4742f0 || f == 0x4dca10 ||
                  f == 0x4063b0))
            value = r.invoke(f, t, n ? std::initializer_list<uint32_t>{args[0]} : std::initializer_list<uint32_t>{});
        else
            return 0;
        if (out)
            *out = value;
        return !c->fault;
    } catch (Failure &) {
        return 0;
    }
}
