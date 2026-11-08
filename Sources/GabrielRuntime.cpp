#include "GabrielRuntime.h"
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
const uint32_t boss[] = {0x444120, 0x44d000, 0x4433b0, 0x44d3c0, 0x40e1b0, 0x444d90, 0x4bb030, 0x4c96b0, 0x40e5b0,
                         0x43dfa0, 0x404dd0, 0x44d460, 0x44d570, 0x44d5a0, 0x44d700, 0x44d730, 0x44d760, 0x44d9f0,
                         0x4441f0, 0x43ed70, 0x43eee0, 0x43ee10, 0x43efe0, 0x40e660, 0x43f640, 0x43f740, 0x43fa10,
                         0x43fcb0, 0x43fd60, 0x43fe00, 0x44dbb0, 0x43ffa0, 0x404e00, 0x44de30, 0x44df10, 0x4407d0,
                         0x43f500, 0x4409d0, 0x440b20, 0x440c90, 0x440410, 0x4bb030, 0x404e10, 0x444140, 0x445810};
const uint32_t bomb[] = {0x484d90, 0x4c9e30, 0x445af0, 0x4063b0, 0x408860, 0x4bb030, 0x4bb030, 0x4c96b0,
                         0x4c96b0, 0x4dca10, 0x408870, 0x446340, 0x432550, 0x4c96b0, 0x432560, 0x408510};
const uint32_t cannon[] = {0x484d90, 0x4c9e30, 0x446670, 0x4041b0, 0x4c96b0, 0x4bb030, 0x4bb030, 0x4c96b0, 0x4c96b0};
const char *label(uint32_t t) {
    switch (t) {
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
double add(double a, double b) {
    volatile double v = a + b;
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
bool owned(uint32_t);
struct Run {
    ClawGabrielContext &c;
    ClawGabrielDependency d;
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
        ClawGabrielCall e{};
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
        uint32_t vt = read(t), f = claw_gabriel_function(vt, slot);
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
    if (t >= 0x50de1c && uint64_t(t) + n * 4 <= 0x50de1c + sizeof boss && t % 4 == 0)
        return const_cast<uint32_t *>(boss) + (t - 0x50de1c) / 4;
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
uint64_t bossDependency(ClawRauxContext *, const ClawRauxCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (e->function == 0x4c8220 || e->function == 0x4c82a0 || e->function == 0x4c79e0 || e->function == 0x420a10) {
        if (e->argumentCount == 1)
            return r.invoke(e->function, e->receiver, {e->arguments[0]});
        if (e->argumentCount == 2)
            return r.invoke(e->function, e->receiver, {e->arguments[0], e->arguments[1]});
    }
    ClawGabrielCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, 12, q.arguments);
    q.name = e->name;
    return r.d ? r.d(&r.c, &q, r.user) : 0;
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
uint32_t make(Run &r, uint32_t p, uint32_t name, uint32_t dx, uint32_t dy) {
    auto a = r.read(p + 300);
    return r.invoke(0x4c8da0, r.read(r.read(r.read(p + 0x130) + 12) + 8),
                    {0, r.read(a + 76) + dx, r.read(a + 80) + dy, r.read(a + 100) - 1, name, 0x40000});
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
double sub(double a, double b) {
    volatile double v = a - b;
    return v;
}
double div(double a, double b) {
    volatile double v = a / b;
    return v;
}
void inlineRetarget(ClawPlayerPhysics &p, double x, double y) {
    const double dx = sub(x, p.position[0]), dy = sub(y, p.position[1]), dz = -p.position[2];
    auto ax = p.acceleration[0], ay = p.acceleration[1], az = p.acceleration[2];
    double a2 = add(add(mul(ax, ax), mul(ay, ay)), mul(az, az)), d2 = add(add(mul(dx, dx), mul(dy, dy)), mul(dz, dz)),
           dot = sub(sub(-mul(ax, dx), mul(ay, dy)), mul(az, dz));
    double actualSpeed = std::sqrt(mul(sub(std::sqrt(mul(mul(d2, a2), 4)), mul(dot, -2)), .5));
    claw_physics_retarget(&p, x, y, -0.0);
    double q = mul(a2, .25);
    if (actualSpeed >= .1 && q >= -.1 && q <= .1) {
        double distance = add(add(std::abs(dx), std::abs(dz)), std::abs(dy));
        p.velocity[0] = mul(div(dx, distance), actualSpeed);
        p.velocity[1] = mul(div(dy, distance), actualSpeed);
        p.velocity[2] = mul(div(dz, distance), actualSpeed);
    }
}

uint32_t body(Run &r, uint32_t f, uint32_t p, const uint32_t *a) {
    auto &g = *r.c.globals;
    switch (f) {
    case 0x443290:
    case 0x446550:
    case 0x4459d0: {
        auto primary = r.read(a[0] + 108), state = r.read(primary + 28);
        if (!state) {
            r.put(primary + 28, 1000);
            auto object = r.invoke(0x4f63ec, 0, {claw_gabriel_allocation_bytes(f)});
            if (object)
                r.invoke(f == 0x443290 ? 0x443ab0 : f == 0x446550 ? 0x446a70 : 0x445ef0, object, {a[0]});
            r.virt(object, 16);
            r.put(primary + 24, object);
        } else if (state == 29 || state == 30)
            r.virt(r.read(primary + 24), state == 29 ? 32 : 28);
        else if (state != 1000)
            r.invoke(0x4dc870, 0, {r.read(primary + 24)});
        return 1;
    }
    case 0x443ab0: {
        r.invoke(0x40e0d0, p, {a[0]});
        for (uint32_t off = 0x4dc; off <= 0x508; off += 4)
            r.put(p + off, 0);
        r.put(p, 0x50de1c);
        r.put(0x53774c, p);
        r.invoke(0x4c7970, r.read(p + 300), {0x527788});
        uint32_t fields[] = {0x338, 0x334, 0x460, 0x464, 0x468, 0x46c, 0x470, 0x474,
                             0x478, 0x47c, 0x480, 0x484, 0x488, 0x48c, 0x490, 0x494};
        uint32_t literals[] = {0x527770, 0x527758, 0x527744, 0x527730, 0x527718, 0x527700, 0x5276e8, 0x5276d0,
                               0x5276b8, 0x5276a0, 0x527688, 0x527670, 0x527658, 0x527640, 0x527628, 0x527610};
        for (unsigned i = 0; i < 16; ++i)
            r.put(p + fields[i], r.sequence(p, literals[i]));
        for (uint32_t i = 0; i < 5; ++i)
            r.put(p + 0x498 + i * 4, r.invoke(0x4f6286, r.soundRegistry(p), {0x5275f8 - i * 24}));
        uint32_t sounds[] = {0x527580, 0x527580, 0x527568, 0x527550, 0x527538, 0x527520,
                             0x527508, 0x5274f0, 0x5274f0, 0x5274d8, 0x5274c0, 0x5274a8};
        for (uint32_t i = 0; i < 12; ++i)
            r.put(p + 0x4ac + i * 4, r.invoke(0x4061b0, r.read(r.read(r.read(p + 300) + 12) + 40), {sounds[i]}));
        auto actor = r.read(p + 300);
        r.put(actor + 0xd0, 4);
        r.put(actor + 0xd4, 0x3000062);
        r.put(actor + 0x164, r.read(actor + 0x164) & ~1u);
        relativeBounds(r, r.read(p + 300), p + 0x220);
        relativeBounds(r, r.read(p + 300), p + 0x210);
        r.invoke(0x406290, r.read(p + 300));
        r.invoke(0x406240, r.read(p + 300));
        for (uint32_t off = 0x28c; off <= 0x2b0; off += 4)
            r.put(p + off, (off - 0x28c) % 8 ? 2000 : 3000);
        actor = r.read(p + 300);
        r.put(actor + 80, r.read(actor + 80) - 32);
        actor = r.read(p + 0x128);
        r.invoke(0x4cd800, r.read(r.read(actor + 12) + 36), {actor, 0});
        r.put(r.read(p + 0x128) + 0xcc, 1);
        r.put(r.read(p + 12) + 0x10c, 100);
        r.put(r.read(p + 12) + 0x10c, truncLow(mul(double(sign(r.read(r.read(p + 12) + 0x10c))), g.healthScale)));
        r.put(p + 0x534, 0);
        r.put(p + 0x514, 0);
        r.put(p + 0x524, 0);
        auto x = truncLow(add(r.real(p + 104), -10));
        r.put(p + 0x528, x);
        r.put(p + 0x52c, x - 150);
        r.put(p + 0x530, 0x1472);
        for (auto off : {0x514u, 0x524u, 0x518u, 0x51cu, 0x520u})
            r.put(p + off, 0);
        r.put(p + 0x534, 1);
        r.invoke(0x444140, p);
        return p;
    }
    case 0x4433b0:
    case 0x445af0:
    case 0x446670: {
        uint32_t cls = f == 0x4433b0 ? 0x537728 : f == 0x445af0 ? 0x537758 : 0x537788, fn = r.registry(cls, a[0]);
        if (fn) {
            fn = r.registry(cls, a[0]);
            r.invoke(fn, p);
        } else
            r.invoke(f == 0x4433b0 ? 0x40e280 : f == 0x445af0 ? 0x408580 : 0x4141f0, p, {a[0]});
        return 0;
    }
    case 0x444120:
        r.invoke(0x445950, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x445950:
        r.put(0x53774c, 0);
        r.invoke(0x47e810, p);
        return 0;
    case 0x444140:
        r.transition(p, 0x523268);
        {
            auto n = r.invoke(0x4a3050, 0);
            select(r, p, sign(n) % 100 < 50 ? 0x460 : 0x464);
        }
        return 0;
    case 0x4441b0:
        r.animate(p);
        if (r.read(0x53c9c0) == 2)
            r.virt(p, 0xb0);
        return 0;
    case 0x4441f0:
        r.transition(p, 0x523148);
        if (!r.read(p + 0x520)) {
            if (r.read(p + 0x18c) == 2)
                face(r, p, true, 3);
            else
                r.invoke(0x406310, p + 0x128);
            select(r, p, sign(r.invoke(0x4a3050, 0)) % 100 < 50 ? 0x460 : 0x464);
            r.put(p + 0x4e0, 1000);
            r.put(p + 0x4dc, g.tick);
        }
        return 0;
    case 0x4442c0:
        if (!r.read(p + 0x520)) {
            r.animate(p);
            if (completed(r, p) && g.tick - r.read(p + 0x4dc) >= r.read(p + 0x4e0) && !r.read(p + 0x534))
                r.invoke(0x444330, p);
        }
        return 0;
    case 0x444330: {
        auto random = r.invoke(0x4a3050, 0);
        face(r, p, r.read(p + 0x18c) == 2, 0);
        auto n = sign(random) % 3;
        if (n == 0)
            r.invoke(0x4444d0, p);
        else if (n == 1)
            r.invoke(0x4446f0, p);
        else if (n == 2)
            r.invoke(0x444850, p);
        else
            r.virt(p, 0x48);
        return 0;
    }
    case 0x4444d0:
        face(r, p, false, 1);
        r.transition(p, 0x52746c);
        select(r, p, 0x490);
        r.put(p + 0x50c, 0);
        r.put(p + 0x510, 0);
        {
            auto n = sign(r.invoke(0x4a3050, 0)) % 3;
            r.invoke(0x405f60, p, {r.read(p + 0x498 + uint32_t(n) * 4)});
        }
        r.put(p + 0x508, 500);
        r.put(p + 0x504, g.tick);
        return 0;
    case 0x4445d0:
        if (g.tick - r.read(p + 0x504) < r.read(p + 0x508))
            return 0;
        r.animate(p);
        if (r.read(r.read(p + 300) + 0x16c) == 401 && !r.read(p + 0x510)) {
            r.put(p + 0x510, 1);
            auto n = sign(r.invoke(0x4a3050, 0)) % 4;
            for (int i = 0; i < 4; ++i)
                if (i != n) {
                    auto child = make(r, p, 0x522afc, uint32_t(-75), uint32_t(-75));
                    r.invoke(r.read(r.read(child + 108) + 16), 0, {child});
                    r.invoke(0x446130, r.read(r.read(child + 108) + 24), {uint32_t(i * 125 - 475)});
                }
        }
        if (completed(r, p))
            r.virt(p, 0x48);
        return 0;
    case 0x4446f0:
        if (sign(r.read(p + 0x524)) > 1) {
            r.virt(p, 0x48);
            return 0;
        }
        r.transition(p, 0x52745c);
        select(r, p, 0x478);
        r.put(p + 0x50c, 0);
        r.put(p + 0x510, 0);
        return 0;
    case 0x444760:
        r.animate(p);
        if (!r.read(p + 0x50c)) {
            r.put(p + 0x50c, 1);
            auto n = sign(r.invoke(0x4a3050, 0)) % 4;
            r.invoke(0x405f60, p, {r.read(p + 0x4a4 + uint32_t(n) * 4)});
        }
        if (completed(r, p) && !r.read(p + 0x510)) {
            r.put(p + 0x510, 1);
            auto child = make(r, p, 0x522c68, 150, uint32_t(-10));
            if (child) {
                r.invoke(r.read(r.read(child + 108) + 16), 0, {child});
                r.invoke(0x483e40, r.read(r.read(child + 108) + 24));
            }
            r.put(p + 0x524, r.read(p + 0x524) + 1);
            r.virt(p, 0x48);
        }
        return 0;
    case 0x444850:
        r.transition(p, 0x52744c);
        select(r, p, 0x490);
        face(r, p, true, 2);
        r.put(p + 0x510, 0);
        {
            auto n = sign(r.invoke(0x4a3050, 0)) % 2;
            r.invoke(0x405f60, p, {r.read(p + 0x4b4 + uint32_t(n) * 4)});
        }
        r.put(p + 0x508, 500);
        r.put(p + 0x504, g.tick);
        return 0;
    case 0x444960:
        if (g.tick - r.read(p + 0x504) >= r.read(p + 0x508)) {
            r.animate(p);
            if (r.read(r.read(p + 300) + 0x16c) == 401 && !r.read(p + 0x510)) {
                r.put(p + 0x518, 1);
                r.put(p + 0x510, 1);
            }
            if (completed(r, p)) {
                face(r, p, false, 0);
                r.virt(p, 0x48);
            }
        }
        return 0;
    case 0x444aa0:
        r.transition(p, 0x52743c);
        select(r, p, 0x338);
        r.put(p + 0x514, r.read(p + 0x514) + 1);
        if (sign(r.read(p + 0x514)) < 5) {
            auto n = sign(r.invoke(0x4a3050, 0)) % 2;
            r.audio(r.read(p + 0x4c8 + uint32_t(n) * 4));
            r.put(p + 0x508, 500);
            r.put(p + 0x504, g.tick);
        }
        r.put(p + 0x50c, 0);
        r.put(p + 0x510, 0);
        return 0;
    case 0x444b70:
        if (g.tick - r.read(p + 0x504) >= r.read(p + 0x508)) {
            r.animate(p);
            if (completed(r, p) && !r.read(p + 0x510)) {
                r.put(p + 0x510, 1);
                r.put(r.read(p + 12) + 0x10c, r.read(r.read(p + 12) + 0x10c) - 20);
                if (sign(r.read(p + 0x514)) > 4) {
                    r.put(r.read(p + 12) + 0x10c, 0);
                    r.invoke(0x444f80, p);
                } else
                    r.invoke(0x4444d0, p);
            }
        }
        return 0;
    case 0x444c20:
        face(r, p, r.read(p + 0x18c) == 2, 4);
        r.transition(p, 0x527430);
        select(r, p, 0x494);
        r.put(p + 0x50c, 0);
        r.put(p + 0x510, 0);
        return 0;
    case 0x444d00:
        r.animate(p);
        if (!r.read(p + 0x50c)) {
            r.put(p + 0x50c, 1);
            auto n = sign(r.invoke(0x4a3050, 0)) % 3;
            r.invoke(0x405f60, p, {r.read(p + 0x4bc + uint32_t(n) * 4)});
        }
        if (completed(r, p) && !r.read(p + 0x510)) {
            r.put(p + 0x510, 1);
            r.virt(p, 0x48);
        }
        return 0;
    case 0x444d90: {
        if (r.read(p + 0x520))
            return 0;
        auto attacker = r.read(r.read(p + 12) + 0x74);
        if (!attacker)
            return 0;
        if (r.read(attacker + 0xd0) != 0x40) {
            auto pp = r.read(r.read(g.playerToken + 108) + 20), serial = r.read(pp + 0xe8);
            if (serial == r.read(p + 0x19c))
                return 0;
            r.put(p + 0x19c, serial);
            for (auto name : {0x527430u, 0x52743cu, 0x5231f8u, 0x527424u, 0x527418u, 0x52740cu}) {
                auto cell = r.invoke(0x406020, 0x537698, {r.read(r.read(p + 16) + 28)});
                if (!r.invoke(0x4a3810, 0, {r.read(cell), name}))
                    return 0;
            }
            if (g.tick - r.read(p + 0x4f4) < r.read(p + 0x4f8))
                return 0;
            if (r.read(attacker + 0xd0) != 0x40) {
                r.put(p + 0x4f8, 500);
                r.put(p + 0x4f4, g.tick);
                r.invoke(0x444c20, p);
            } else
                goto cannonHit;
        } else {
        cannonHit:
            r.put(p + 0x4f8, 1000);
            r.put(p + 0x4f4, g.tick);
            r.invoke(0x444aa0, p);
            r.invoke(0x440e20, p, {attacker});
            r.put(attacker + 8, r.read(attacker + 8) | 0x10000);
        }
        if (r.read(attacker + 0xd0) == 0x20 || r.read(attacker + 0xd0) == 0x2000000)
            r.put(attacker + 8, r.read(attacker + 8) | 0x10000);
        return 0;
    }
    case 0x444f80:
        r.transition(p, 0x5231f8);
        select(r, p, 0x468);
        face(r, p, r.read(p + 0x18c) == 2, r.read(p + 0x18c) == 2 ? 4 : 3);
        r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) | 0x80);
        r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) | 4);
        r.put(p + 0x50c, 0);
        r.put(p + 0x510, 0);
        return 0;
    case 0x445090:
        r.animate(p);
        if (!r.read(p + 0x50c) && !r.invoke(0x48cf90, 0, {r.read(p + 12)})) {
            r.invoke(0x405f60, p, {r.read(p + 0x4d0)});
            r.put(p + 0x50c, 1);
            r.put(p + 0x4e8, 4000);
            r.put(p + 0x4e4, g.tick);
        }
        if (r.read(r.read(p + 300) + 0x16c) == 900 && g.tick - r.read(p + 0x4fc) >= r.read(p + 0x500)) {
            r.put(p + 0x500, 100);
            r.put(p + 0x4fc, g.tick);
            face(r, p, !(r.read(r.read(p + 300) + 0x40) & 2), 0);
        }
        if (r.read(p + 0x50c) && g.tick - r.read(p + 0x4e4) >= r.read(p + 0x4e8) && !r.read(p + 0x510)) {
            r.put(p + 0x510, 1);
            r.invoke(0x4452d0, p);
        }
        return 0;
    case 0x4455b0:
        r.animate(p);
        if (r.read(r.read(p + 12) + 0xcc) == 1) {
            r.real(p + 0x50, 0);
            r.real(p + 0x58, 0);
            r.real(p + 0x60, 0);
            r.invoke(0x445600, p);
        }
        return 0;
    case 0x445600:
        r.transition(p, 0x527418);
        select(r, p, 0x470);
        r.put(p + 0x510, 0);
        return 0;
    case 0x445660:
        r.animate(p);
        if (completed(r, p) && !r.read(p + 0x510)) {
            r.put(p + 0x510, 1);
            r.invoke(0x4456c0, p);
        }
        return 0;
    case 0x4456c0:
        r.transition(p, 0x52740c);
        select(r, p, 0x474);
        r.put(p + 0x50c, 0);
        r.put(p + 0x510, 0);
        return 0;
    case 0x445720:
        if (!r.read(p + 0x50c)) {
            if (!r.invoke(0x48cf90, 0, {r.read(p + 12)})) {
                r.invoke(0x405f60, p, {r.read(p + 0x4d8)});
                r.put(p + 0x50c, 1);
            }
            if (!r.read(p + 0x50c))
                return 0;
        }
        r.animate(p);
        if (completed(r, p) && !r.read(p + 0x510)) {
            r.put(p + 0x510, 1);
            if (sign(r.read(g.playerToken + 0x10c)) > 0) {
                r.invoke(0x420590, 0);
                r.invoke(0x40e5c0, p);
                r.put(p + 0x520, 1);
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
    case 0x4452d0: {
        r.transition(p, 0x527424);
        select(r, p, 0x46c);
        face(r, p, true, 2);
        r.put(r.read(p + 12) + 0xcc, 8);
        ClawPlayerPhysics physics;
        std::memcpy(&physics, r.span(p + 40, sizeof physics / 4), sizeof physics);
        inlineRetarget(physics, double(sign(r.read(p + 0x52c))), double(sign(r.read(p + 0x530) - 100)));
        for (unsigned i = 0; i < 3; ++i)
            r.real(p + 0x50 + i * 8, physics.velocity[i]);
        return 0;
    }
    case 0x446130: {
        r.real(p + 0x40, 2000);
        ClawPlayerPhysics physics;
        std::memcpy(&physics, r.span(p + 40, sizeof physics / 4), sizeof physics);
        auto x = add(double(sign(a[0])), r.real(p + 104));
        inlineRetarget(physics, x, r.real(p + 112));
        for (unsigned i = 0; i < 3; ++i)
            r.real(p + 0x50 + i * 8, physics.velocity[i]);
        return 0;
    }
    case 0x445810:
        if (r.read(p + 0x520)) {
            r.virt(p, 0x48);
            return 0;
        }
        r.put(r.read(p + 12) + 0x10c, 100);
        r.put(r.read(p + 12) + 0x10c, truncLow(mul(double(sign(r.read(r.read(p + 12) + 0x10c))), g.healthScale)));
        r.put(r.read(p + 12) + 0xcc, 7);
        r.invoke(0x40e560, p);
        r.virt(p, 0x24);
        r.put(r.read(p + 12) + 0xcc, 8);
        for (auto off : {0x50u, 0x58u, 0x60u, 0x38u})
            r.real(p + off, 0);
        r.real(p + 0x40, 2000);
        r.put(r.read(p + 300) + 80, r.read(r.read(p + 300) + 80) - 32);
        r.invoke(0x4cd800, r.read(r.read(r.read(p + 0x128) + 12) + 36), {r.read(p + 0x128), 0});
        r.put(r.read(p + 0x128) + 0xcc, 1);
        r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) & ~0x80u);
        r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) & ~4u);
        r.put(p + 0x514, 0);
        r.put(p + 0x524, 0);
        {
            auto x = truncLow(add(r.real(p + 104), -10));
            r.put(p + 0x528, x);
            r.put(p + 0x52c, x - 150);
        }
        r.put(p + 0x530, 0x1472);
        for (auto off : {0x518u, 0x51cu, 0x520u})
            r.put(p + off, 0);
        r.put(p + 0x534, 1);
        r.virt(p, 0x48);
        return 0;
    default:
        r.c.fault = 3;
        throw Failure{};
    }
}

bool owned(uint32_t f) {
    switch (f) {
    case 0x443290:
    case 0x446550:
    case 0x4459d0:
    case 0x443ab0:
    case 0x4433b0:
    case 0x445af0:
    case 0x446670:
    case 0x444120:
    case 0x445950:
    case 0x444140:
    case 0x4441b0:
    case 0x4441f0:
    case 0x4442c0:
    case 0x444330:
    case 0x4444d0:
    case 0x4445d0:
    case 0x4446f0:
    case 0x444760:
    case 0x444850:
    case 0x444960:
    case 0x444aa0:
    case 0x444b70:
    case 0x444c20:
    case 0x444d00:
    case 0x444d90:
    case 0x444f80:
    case 0x445090:
    case 0x4452d0:
    case 0x4455b0:
    case 0x445600:
    case 0x445660:
    case 0x4456c0:
    case 0x445720:
    case 0x445810:
    case 0x446130:
        return true;
    default:
        return false;
    }
}
} // namespace
extern "C" uint32_t claw_gabriel_allocation_bytes(uint32_t f) {
    return f == 0x443290 ? 0x538 : f == 0x446550 ? 0x98 : f == 0x4459d0 ? 0x198 : 0;
}
extern "C" uint32_t claw_gabriel_function(uint32_t vt, uint32_t slot) {
    if (slot % 4)
        return 0;
    if (vt == 0x50de1c && slot / 4 < 45)
        return boss[slot / 4];
    if (vt == 0x50df44 && slot / 4 < 9)
        return cannon[slot / 4];
    if (vt == 0x50ded4 && slot / 4 < 16)
        return bomb[slot / 4];
    return 0;
}
extern "C" uint32_t claw_gabriel_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, ClawGabrielContext *c,
                                       ClawGabrielDependency d, void *u, uint32_t *out) {
    if (!c || !c->globals || !owned(f))
        return 0;
    uint32_t need = 0;
    switch (f) {
    case 0x443290:
    case 0x446550:
    case 0x4459d0:
    case 0x443ab0:
    case 0x4433b0:
    case 0x445af0:
    case 0x446670:
    case 0x444120:
    case 0x446130:
        need = 1;
        break;
    default:
        break;
    }
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
        auto result = body(r, f, t, args);
        if (out)
            *out = result;
        return !c->fault;
    } catch (Failure &) {
        return 0;
    }
}
