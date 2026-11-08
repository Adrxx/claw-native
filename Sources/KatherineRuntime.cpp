#include "KatherineRuntime.h"
#include "ActorWrapperRuntime.h"
#include "ActorResourceBindings.h"
#include "PickupPointsRuntime.h"
#include "PlayerProjectileRuntime.h"
#include "PlayerPhysics.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
namespace {
struct Failed {};
const uint32_t methods[] = {0x4542f0, 0x4547c0, 0x4543e0, 0x44d3c0, 0x40e1b0, 0x44df60, 0x4bb030, 0x4c96b0, 0x40e5b0,
                            0x43dfa0, 0x404dd0, 0x4548c0, 0x4a07e0, 0x4a07e0, 0x4a07e0, 0x4b7aa0, 0x44d760, 0x44d9f0,
                            0x454b90, 0x43ed70, 0x43eee0, 0x43ee10, 0x43efe0, 0x40e660, 0x454cb0, 0x43f740, 0x43fa10,
                            0x43fcb0, 0x43fd60, 0x43fe00, 0x44dbb0, 0x43ffa0, 0x404e00, 0x44de30, 0x44df10, 0x4407d0,
                            0x43f500, 0x4409d0, 0x440b20, 0x440c90, 0x440410, 0x4bb030, 0x404e10, 0x405060, 0x47eeb0};
int32_t si(uint32_t v) {
    int32_t x;
    std::memcpy(&x, &v, 4);
    return x;
}
double add(double a, double b) {
    volatile double x = a + b;
    return x;
}
double sub(double a, double b) {
    volatile double x = a - b;
    return x;
}
double mul(double a, double b) {
    volatile double x = a * b;
    return x;
}
double div(double a, double b) {
    volatile double x = a / b;
    return x;
}
uint32_t ftol(double v) {
    uint64_t b;
    std::memcpy(&b, &v, 8);
    int e = int((b >> 52) & 2047) - 1023;
    if (e < 0 || e >= 63)
        return 0;
    uint64_t n = (b & 0xfffffffffffffULL) | 0x10000000000000ULL;
    n = e >= 52 ? n << (e - 52) : n >> (52 - e);
    return b >> 63 ? 0u - uint32_t(n) : uint32_t(n);
}
const char *name(uint32_t t) {
    switch (t) {
    case 0x528444:
        return "LEVEL_KATHERINE";
    case 0x52842c:
        return "LEVEL_KATHERINE_WALK";
    case 0x528414:
        return "LEVEL_KATHERINE_STRIKE1";
    case 0x5283fc:
        return "LEVEL_KATHERINE_FALL";
    case 0x5283e4:
        return "LEVEL_KATHERINE_HITLOW";
    case 0x5283cc:
        return "LEVEL_KATHERINE_HITHIGH";
    case 0x5283b4:
        return "LEVEL_KATHERINE_HOME";
    case 0x52839c:
        return "LEVEL_KATHERINE_IDLE";
    case 0x528384:
        return "LEVEL_KATHERINE_LIFTED1";
    case 0x52836c:
        return "LEVEL_KATHERINE_LIFTED2";
    case 0x528354:
        return "LEVEL_KATHERINE_FLIP1";
    case 0x52833c:
        return "LEVEL_KATHERINE_FLIP2";
    case 0x528324:
        return "LEVEL_KATHERINE_FLIP3";
    case 0x52830c:
        return "LEVEL_KATHERINE_THROWN";
    case 0x5282f0:
        return "LEVEL_KATHERINE_BLOCKHIGH";
    case 0x5282d4:
        return "LEVEL_KATHERINE_BLOCKLOW";
    case 0x5282b8:
        return "LEVEL_KATHERINE_00470002";
    case 0x52829c:
        return "LEVEL_KATHERINE_00470012";
    case 0x52846c:
        return "LEVEL_KATHERINE_BLOCK1";
    case 0x528484:
        return "LEVEL_KATHERINE_BLOCK2";
    case 0x52851c:
        return "LEVEL_KATHERINE_00470018";
    case 0x528538:
        return "LEVEL_KATHERINE_00470015";
    case 0x528510:
        return "LEVEL_STAB2";
    case 0x528504:
        return "LEVEL_STAB3";
    case 0x5284ec:
        return "LEVEL_KATHERINE_STRIKE2";
    case 0x5284d0:
        return "LEVEL_KATHERINE_00470000";
    case 0x5284b4:
        return "LEVEL_KATHERINE_00470003";
    case 0x52849c:
        return "LEVEL_KATHERINE_WHIP1";
    case 0x5234b4:
        return "GAME_NULL";
    case 0x527204:
        return "LS_JUMP";
    case 0x528454:
        return "LS_FLIP3";
    case 0x523148:
        return "LS_IDLE";
    case 0x523204:
        return "LS_HITLOW";
    case 0x523210:
        return "LS_HITHIGH";
    default:
        return nullptr;
    }
}
bool specialized(uint32_t f) {
    switch (f) {
    case 0x453d30:
    case 0x453df0:
    case 0x4542f0:
    case 0x454310:
    case 0x4543e0:
    case 0x4547c0:
    case 0x4548c0:
    case 0x454a10:
    case 0x454b90:
    case 0x454c20:
    case 0x454cb0:
    case 0x4550e0:
    case 0x455230:
    case 0x455280:
    case 0x4552d0:
    case 0x455350:
    case 0x455360:
    case 0x4553a0:
    case 0x40f780:
        return true;
    default:
        return false;
    }
}
bool boss(uint32_t f) {
    switch (f) {
    case 0x40e0d0:
    case 0x40e1b0:
    case 0x40e280:
    case 0x40e560:
    case 0x40e580:
    case 0x40e5b0:
    case 0x40e660:
    case 0x420590:
    case 0x4208b0:
    case 0x405060:
    case 0x47eeb0:
    case 0x4a07e0:
        return true;
    default:
        return false;
    }
}
struct Run {
    ClawKatherineContext &c;
    ClawKatherineDependency dependency;
    void *user;
    [[noreturn]] void fail(uint32_t f = 1) {
        if (!c.fault)
            c.fault = f;
        throw Failed{};
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failed{};
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
    double real(uint32_t t) {
        double v;
        std::memcpy(&v, span(t, 2), 8);
        return v;
    }
    void real(uint32_t t, double v) {
        std::memcpy(span(t, 2), &v, 8);
    }
    uint64_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawKatherineCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), e.arguments);
        for (auto q : a)
            if (name(q)) {
                e.name = name(q);
                break;
            }
        uint64_t out;
        if (dependency)
            out = dependency(&c, &e, user);
        else if (c.scene.call && a.size() <= 4) {
            ClawSceneActorCall q{};
            q.function = f;
            q.receiver = t;
            q.argumentCount = e.argumentCount;
            std::copy(a.begin(), a.end(), q.arguments);
            out = c.scene.call(c.scene.context, q);
        } else
            fail();
        if (c.fault)
            throw Failed{};
        return out;
    }
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t> = {});
    uint32_t virt(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        return invoke(get(get(t) + slot), t, a);
    }
    uint32_t sound(uint32_t p) {
        return get(get(get(p + 300) + 12) + 40) + 16;
    }
    void animate(uint32_t p) {
        invoke(0x4c82a0, get(p + 300) + 0x188, {c.globals->animationDelta});
    }
    uint32_t sequence(uint32_t p, uint32_t token) {
        auto v = invoke(0x4062e0, p + 0x128, {token});
        return v ? v : invoke(0x4062e0, p + 0x128, {0x5234b4});
    }
    void rect(uint32_t p, std::initializer_list<uint32_t> a) {
        uint32_t n = 0;
        for (auto v : a)
            put(p + 4 * n++, v);
    }
    void mirror(uint32_t p) {
        auto old = get(p);
        put(p, 0u - get(p + 8));
        put(p + 8, 0u - old);
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        return static_cast<Run *>(u)->span(t, n);
    }
    static uint32_t sceneCall(void *u, ClawSceneActorCall q) {
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
    ClawSceneActorHost host() {
        return {this, lookup, nullptr, nullptr, sceneCall, nullptr};
    }
    uint32_t table(uint32_t t, uint32_t state) {
        put(t + 32, 0);
        uint32_t cell;
        if (si(state) < si(get(t + 8)) || si(state) > si(get(t + 12))) {
            auto found = invoke(0x4db6e0, t, {state, 0});
            if (!found) {
                auto message = get(0x544b4c);
                put(0x544b14, invoke(0x4db5f0, 0));
                invoke(0x4db4d0, get(t + 4), {t, message, 12});
                cell = get(t + 20);
            } else
                cell = get(t + 16) + (state - get(t + 8)) * get(t + 24);
        } else
            cell = get(t + 16) + (state - get(t + 8)) * get(t + 24);
        return get(cell);
    }
};
uint32_t body(Run &, uint32_t, uint32_t, const uint32_t *);
uint32_t forward(Run &r, uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
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
        r.fail(3);
    }
}
uint64_t baseDependency(ClawRauxContext *, const ClawRauxCall *q, void *u) {
    return forward(*static_cast<Run *>(u), q->function, q->receiver, q->arguments, q->argumentCount);
}
uint64_t dispatcherDependency(ClawPlayerProjectileContext *, const ClawPlayerProjectileCall *q, void *u) {
    return forward(*static_cast<Run *>(u), q->function, q->receiver, q->arguments, q->argumentCount);
}
uint32_t imageResolved(ClawActorResourceBindings *, ClawActorBindingContext *c, const ClawActorBindingCall *, void *) {
    return c->image.token;
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    uint32_t args[12]{};
    std::copy(a.begin(), a.end(), args);
    if (specialized(f))
        return body(*this, f, t, args);
    uint32_t out = 0;
    if (boss(f)) {
        ClawRauxContext x{host(), c.globals, c.composeAnimation, c.composeImages, 0};
        if (!claw_raux_entry(f, t, args, uint32_t(a.size()), &x, baseDependency, this, &out) || x.fault)
            fail(x.fault ? x.fault : 1);
        return out;
    }
    if (f == 0x4dc870) {
        ClawPlayerProjectileGlobals g{};
        ClawPlayerProjectileContext x{host(), &g, nullptr, 0, 0};
        if (!claw_player_projectile_entry(f, args[0], nullptr, 0, &x, dispatcherDependency, this, &out) || x.fault)
            fail(x.fault ? x.fault : 1);
        return out;
    }
    if (f == 0x4062e0 || f == 0x4061b0 || f == 0x40f6c0) {
        ClawActorWrapperContext x{host(), 0};
        if (!claw_actor_wrapper_entry(f, t, args, uint32_t(a.size()), &x, nullptr, nullptr, &out) || x.fault)
            fail(x.fault ? x.fault : 1);
        return out;
    }
    if ((f == 0x4c8220 || f == 0x4c82a0) && c.composeAnimation) {
        ClawActorAnimationGlobals g{c.globals->animationDelta, c.globals->masterVolume};
        uint32_t fault = 0;
        if (!claw_actor_animation_entry(f, t, args[0], args[1], &g, host(), &fault, &out) || fault)
            fail(fault ? fault : 1);
        return out;
    }
    if (f == 0x4c7970 && c.composeImages) {
        uint32_t registry = get(get(t + 12) + 16) + 16, root = invoke(0x4f6286, registry, {args[0]});
        ClawActorBindingContext x{};
        x.imageRegistryToken = registry;
        x.image.token = root;
        uint32_t selected = 0;
        if (root) {
            x.image.minimum = si(get(root + 100));
            x.image.maximum = si(get(root + 104));
            ClawPickupPointsContext p{};
            p.scene = host();
            uint32_t index = uint32_t(x.image.minimum);
            if (!claw_pickup_points_entry(0x40f680, root, &index, 1, &p, nullptr, nullptr, &selected) || p.fault)
                fail(p.fault ? p.fault : 1);
            x.image.firstImageIndex = x.image.minimum;
            x.image.images = &selected;
            x.image.imageCount = 1;
        }
        ClawActorResourceBindings s{};
        std::copy_n(span(t, 109), 109, s.actor);
        if (!claw_actor_bind_default_image(&s, &x, name(args[0]), imageResolved, nullptr))
            fail(3);
        std::copy_n(s.actor, 109, span(t, 109));
        return 1;
    }
    return uint32_t(call(f, t, a));
}
void leftTarget(Run &r, uint32_t p, double x) {
    double dx = sub(x, r.real(p + 0x68)), dy = sub(r.real(p + 0x70), r.real(p + 0x70)), dz = -r.real(p + 0x78),
           ax = r.real(p + 0x38), ay = r.real(p + 0x40), az = r.real(p + 0x48);
    double dot = sub(sub(-mul(ax, dx), mul(ay, dy)), mul(az, dz)), aa = add(add(mul(ax, ax), mul(ay, ay)), mul(az, az)),
           dd = add(add(mul(dx, dx), mul(dy, dy)), mul(dz, dz));
    double speed = std::sqrt(mul(sub(std::sqrt(mul(mul(dd, aa), 4)), mul(dot, -2)), .5));
    double threshold = r.real(0x513e20);
    if (!(speed >= threshold)) {
        r.real(p + 0x50, 0);
        r.real(p + 0x58, 0);
        r.real(p + 0x60, 0);
        return;
    }
    aa = mul(aa, .25);
    if (aa < -threshold || threshold < aa) {
        double squared = div(sub(mul(speed, speed), dot), add(aa, aa)), duration = std::sqrt(squared);
        r.real(p + 0x50, div(sub(dx, mul(mul(squared, ax), .5)), duration));
        r.real(p + 0x58, div(sub(dy, mul(mul(squared, ay), .5)), duration));
        r.real(p + 0x60, div(sub(dz, mul(mul(squared, az), .5)), duration));
    } else {
        double distance = add(add(std::abs(dx), std::abs(dz)), std::abs(dy));
        r.real(p + 0x50, mul(div(dx, distance), speed));
        r.real(p + 0x58, mul(div(dy, distance), speed));
        r.real(p + 0x60, mul(div(dz, distance), speed));
    }
}
uint32_t body(Run &r, uint32_t f, uint32_t p, const uint32_t *a) {
    auto &g = *r.c.globals;
    switch (f) {
    case 0x453d30: {
        auto actor = a[0], primary = r.get(actor + 108), state = r.get(primary + 28);
        if (!state) {
            r.put(primary + 28, 1000);
            auto object = r.invoke(0x4f63ec, 0, {0x478});
            if (object)
                object = r.invoke(0x453df0, object, {actor});
            r.virt(object, 16);
            r.put(primary + 24, object);
        } else if (state == 29)
            r.virt(r.get(primary + 24), 32);
        else if (state == 30)
            r.virt(r.get(primary + 24), 28);
        else if (state != 1000)
            r.invoke(0x4dc870, 0, {r.get(primary + 24)});
        return 1;
    }
    case 0x453df0: {
        r.invoke(0x40e0d0, p, {a[0]});
        r.put(p + 0x46c, 0);
        r.put(p + 0x470, 0);
        r.put(p, 0x50e2a4);
        r.invoke(0x4c7970, r.get(p + 300), {0x528444});
        const uint32_t fields[] = {0x30c, 0x308, 0x310, 0x32c, 0x374, 0x334, 0x338, 0x344, 0x34c, 0x350,
                                   0x378, 0x37c, 0x460, 0x464, 0x468, 0x380, 0x36c, 0x384, 0x388};
        const uint32_t names[] = {0x52842c, 0x52842c, 0x528414, 0x5283fc, 0x5283fc, 0x5283e4, 0x5283cc,
                                  0x5283b4, 0x52842c, 0x52839c, 0x528384, 0x52836c, 0x528354, 0x52833c,
                                  0x528324, 0x52836c, 0x52830c, 0x5282f0, 0x5282d4};
        for (uint32_t i = 0; i < 19; ++i)
            r.put(p + fields[i], r.sequence(p, names[i]));
        r.put(p + 0x3a4, r.invoke(0x4f6286, r.sound(p), {0x5282b8}));
        r.put(p + 0x410, r.invoke(0x4061b0, r.get(r.get(r.get(p + 300) + 12) + 40), {0x52829c}));
        const uint32_t offsets[] = {0x290, 0x298, 0x2a0, 0x2a8, 0x2b0, 0x28c, 0x294, 0x29c, 0x2a4, 0x2ac, 0x400, 0x404};
        const uint32_t values[] = {40, 40, 40, 40, 40, 500, 200, 200, 100, 50, 200, 200};
        for (uint32_t i = 0; i < 12; ++i)
            r.put(p + offsets[i], values[i]);
        r.rect(p + 0x220, {uint32_t(-175), uint32_t(-22), uint32_t(-13), 9});
        r.rect(p + 0x210, {uint32_t(-1), uint32_t(-1), 1, 1});
        r.rect(p + 0x250, {uint32_t(-15), uint32_t(-50), 15, 50});
        r.rect(p + 0x260, {uint32_t(-15), uint32_t(-40), 15, 40});
        r.put(p + 0x2bc, uint32_t(-60));
        r.put(p + 0x2b4, 0);
        r.put(p + 0x2b8, 0);
        r.put(p + 0x2c0, uint32_t(-20));
        r.put(p + 0x2c4, 20);
        r.put(p + 0x2c8, uint32_t(-15));
        r.put(p + 0x2e4, 50);
        auto range = ftol(mul(double(g.rangeScale), 50));
        r.put(p + 0x2e4, range < 100 ? 99 : range);
        auto actor = r.get(p + 12);
        r.put(actor + 0x10c, 100);
        actor = r.get(p + 12);
        r.put(actor + 0x10c, ftol(mul(double(si(r.get(actor + 0x10c))), double(g.healthScale))));
        actor = r.get(p + 12);
        r.put(actor + 0x104, 10);
        actor = r.get(p + 12);
        r.put(actor + 0x104, ftol(mul(double(si(r.get(actor + 0x104))), double(g.damageScale))));
        r.invoke(0x40f6c0, r.get(p + 300), {r.get(p + 0x250), r.get(p + 0x254), r.get(p + 0x258), r.get(p + 0x25c)});
        r.invoke(0x4208b0, r.get(p + 300), {uint32_t(-20), uint32_t(-50), 20, 50});
        actor = r.get(p + 300);
        r.put(actor + 80, r.get(actor + 80) - 32);
        r.invoke(0x4cd800, r.get(r.get(r.get(p + 0x128) + 12) + 36), {r.get(p + 0x128), 0});
        r.put(r.get(p + 0x128) + 0xcc, 1);
        r.invoke(0x405060, p);
        return p;
    }
    case 0x4542f0:
        r.invoke(0x454310, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x454310:
        r.put(p, 0x50b16c);
        r.invoke(0x4dbcd0, p + 0x2f4);
        r.invoke(0x4f6584, p + 0x1a8);
        r.invoke(0x4f6584, p + 0x1a4);
        r.put(p, 0x50b014);
        return 0;
    case 0x4543e0: {
        auto fn = r.table(0x537980, a[0]);
        if (fn) {
            fn = r.table(0x537980, a[0]);
            r.invoke(fn, p);
        } else
            r.invoke(0x40e280, p, {a[0]});
        return 0;
    }
    case 0x4547c0: {
        r.invoke(0x44d000, p, {a[0]});
        int32_t value = si(r.invoke(0x4a3050, 0)) % 2;
        if (value == 0 || value == 1)
            r.put(p + 0x3bc, r.invoke(0x4f6286, r.sound(p), {value == 0 ? 0x52846cu : 0x528484u}));
        auto priv = r.get(r.get(g.playerToken + 108) + 20), facing = r.get(p + 0x18c), relation = r.get(p + 0x184);
        if (r.get(priv + 4) && ((facing == 3 && r.get(priv)) || (facing == 2 && !r.get(priv))) &&
            (relation == 3 || relation == 4) && a[0] != 0x527204 && a[0] != 0x528454 && a[0] != 0x52720c &&
            si(r.get(p + 0x3c4)) >= 0 && si(r.get(p + 0x3c4)) < 200 && si(r.get(p + 32)) > 1)
            r.put(p + 20, 0x455350);
        return 0;
    }
    case 0x4548c0: {
        r.invoke(0x43e9c0, p, {500});
        auto stateName = [&]() {
            auto cell = r.invoke(0x441030, 0x537698, {r.get(r.get(p + 16) + 28)});
            auto count = r.get(0x5376b8), token = r.get(0x5376b4);
            for (uint32_t n = 0; n < count; ++n, token += 4)
                if (token)
                    r.invoke(0x4f6439, token);
            return r.get(cell);
        };
        auto value = r.invoke(0x4a3810, 0, {stateName(), 0x523204});
        if (value)
            value = r.invoke(0x4a3810, 0, {stateName(), 0x523210});
        if (!value) {
            r.virt(p, 0x44);
            return 0;
        }
        auto distance = si(r.get(p + 0x3c4));
        if (distance >= 0 && distance < 600) {
            r.virt(p, 0x9c);
            return 0;
        }
        auto priv = r.get(r.get(g.playerToken + 108) + 20);
        r.invoke(r.get(priv + 20) ? 0x44f510 : 0x44f3c0, p);
        r.virt(p, 0x28, {a[0]});
        r.invoke(0x440e20, p, {a[0]});
        return 0;
    }
    case 0x454a10: {
        r.invoke(r.get(p + 0x18c) == 2 ? 0x4357a0 : 0x406310, p + 0x128);
        auto relation = si(r.get(p + 0x184));
        if (relation >= 1 && relation <= 3) {
            auto distance = si(r.get(p + 0x3c4));
            if (distance >= 0 && distance < 400) {
                auto value = si(r.invoke(0x4a3050, 0)) % 100;
                if (r.get(r.get(p + 300) + 0x38) != 0xffffffff)
                    r.invoke(0x48ceb0, 0, {r.get(p + 12), value < 50 ? 0x5284d0u : 0x5284b4u, 0});
                r.virt(p, 0x50, {0x528414, 0x5379a8, 0x52849c});
            } else if (distance >= 400 && distance < 600)
                r.virt(p, 0x60);
            return 0;
        }
        if (relation == 4) {
            auto value = si(r.invoke(0x4a3050, 0)) % 100;
            if (value > 49) {
                value = si(r.invoke(0x4a3050, 0)) % 100;
                r.put(p + 0x3a0, r.invoke(0x4f6286, r.sound(p), {value < 50 ? 0x528510u : 0x528504u}));
                r.virt(p, 0x54, {0x5284ec, 0x5379b8});
            } else
                r.virt(p, 0x64);
            return 0;
        }
        r.invoke(0x44da20, p);
        return 0;
    }
    case 0x454b90:
        r.put(p + 0x50, 0);
        r.put(p + 0x54, 0);
        r.put(p + 36, r.get(r.get(p + 16) + 28));
        r.put(r.get(p + 16) + 28, r.invoke(0x4dba00, 0x537668, {0x523148}));
        if (r.get(r.get(p + 300) + 56) != 0xffffffff)
            r.invoke(0x48ceb0, 0, {r.get(p + 12), 0x52851c, 0});
        r.put(p + 0x134, r.get(r.get(p + 300) + 400));
        r.invoke(0x4c8220, r.get(p + 300) + 0x188, {r.get(p + 0x350)});
        r.animate(p);
        return 0;
    case 0x454c20: {
        r.animate(p);
        auto relation = r.get(p + 0x184);
        if (relation <= 4)
            r.virt(p, 0x44);
        else if ((relation == 5 || relation == 6) && !g.jumpDisabled && si(r.invoke(0x4a3050, 0)) % 100 < 5)
            r.invoke(0x44edd0, p);
        return 0;
    }
    case 0x454cb0: {
        auto distance = uint32_t(si(r.invoke(0x4a3050, 0)) % 201) + 200;
        bool left = r.get(p + 0x18c) == 3;
        auto x = r.get(g.playerToken + 76) + (left ? 0u - distance : distance);
        auto actor = r.get(p + 0x128);
        if (!r.invoke(0x4cda10, r.get(r.get(actor + 12) + 36), {ftol(r.real(p + 0x68)), ftol(r.real(p + 0x70)), x, 32}))
            return 0;
        actor = r.get(p + 0x128);
        x = r.get(g.playerToken + 76) + (left ? 0u - distance : distance);
        auto y = r.get(actor + 80) + 1 + r.get(actor + 0x124);
        uint32_t type = r.invoke(0x4207f0, r.get(r.get(actor + 12) + 36), {x, y});
        if (type != 1) {
            actor = r.get(p + 0x128);
            type = r.invoke(0x4207f0, r.get(r.get(actor + 12) + 36), {x, y});
            if (type != 2) {
                actor = r.get(p + 0x128);
                type = r.invoke(0x4207f0, r.get(r.get(actor + 12) + 36), {x, y});
                if (type != 3)
                    return 0;
            }
        }
        actor = r.get(p + 0x128);
        if (r.invoke(0x4207f0, r.get(r.get(actor + 12) + 36), {x, y - 1}))
            return 0;
        x = r.get(g.playerToken + 76) + (left ? 0u - distance : distance);
        if (left)
            leftTarget(r, p, double(si(x)));
        else {
            ClawPlayerPhysics physics;
            std::memcpy(&physics, r.span(p + 0x28, 60), sizeof physics);
            claw_physics_retarget(&physics, double(si(x)), physics.position[1], 0);
            std::memcpy(r.span(p + 0x28, 60), &physics, sizeof physics);
        }
        r.put(p + 32, 1);
        r.invoke(0x4550e0, p);
        actor = r.get(p + 300);
        r.put(actor + 8, r.get(actor + 8) | 4);
        r.invoke(0x4553a0, p, {0x527204});
        r.put(r.get(p + 12) + 0xcc, 8);
        r.invoke(0x455360, p + 0x128, {r.get(p + 0x464), 0});
        auto sound = r.invoke(0x40f780, p + 0x128, {0x528354});
        if (sound)
            r.invoke(0x4208e0, sound, {g.masterVolume, 0, 0, 0});
        return 0;
    }
    case 0x4550e0: {
        auto actor = r.get(p + 300), flags = r.get(actor + 64);
        bool left = r.get(p + 0x18c) == 2;
        if (left ? bool(flags & 2) : !(flags & 2))
            return 0;
        r.mirror(p + 0x138);
        r.put(actor + 64, left ? flags | 2 : flags & ~2u);
        actor = r.get(p + 300);
        for (auto off : {0x118u, 0x128u, 0x138u})
            if (r.get(actor + off) != 0x80000000)
                r.mirror(actor + off);
        return 0;
    }
    case 0x455230:
        r.animate(p);
        if (r.get(r.get(p + 12) + 0xcc) == 1) {
            r.real(p + 0x50, 0);
            r.real(p + 0x58, 0);
            r.real(p + 0x60, 0);
            r.invoke(0x455280, p);
        }
        return 0;
    case 0x455280:
        r.put(p + 36, r.get(r.get(p + 16) + 28));
        r.put(r.get(p + 16) + 28, r.invoke(0x4dba00, 0x537668, {0x528454}));
        r.put(p + 0x134, r.get(r.get(p + 300) + 400));
        r.invoke(0x4c8220, r.get(p + 300) + 0x188, {r.get(p + 0x468)});
        return 0;
    case 0x4552d0: {
        r.animate(p);
        auto actor = r.get(p + 300);
        if (r.get(actor + 0x1a4) && !r.get(actor + 0x19c)) {
            r.put(actor + 8, r.get(actor + 8) & ~4u);
            auto value = si(r.invoke(0x4a3050, 0)) % 100;
            if (value < 10 && r.get(r.get(p + 300) + 56) != 0xffffffff)
                r.invoke(0x48ceb0, 0, {r.get(p + 12), 0x528538, 0});
            r.put(p + 32, 2);
            r.virt(p, 0x44);
        }
        return 0;
    }
    case 0x455350:
        return r.virt(p, 0x60);
    case 0x455360: {
        auto actor = r.get(p + 4);
        r.put(p + 12, r.get(actor + 400));
        r.invoke(0x4c8220, actor + 0x188, {a[0]});
        if (a[1])
            r.invoke(0x4c82a0, actor + 0x188, {g.animationDelta});
        return 0;
    }
    case 0x4553a0:
        r.put(p + 36, r.get(r.get(p + 16) + 28));
        r.put(r.get(p + 16) + 28, r.invoke(0x4dba00, 0x537668, {a[0]}));
        return 0;
    case 0x40f780:
        return r.invoke(0x4f6286, r.get(r.get(r.get(p + 4) + 12) + 40) + 16, {a[0]});
    default:
        r.fail(3);
    }
}
} // namespace
extern "C" uint32_t claw_katherine_private_bytes(void) {
    return 0x478;
}
extern "C" uint32_t claw_katherine_function(uint32_t vt, uint32_t slot) {
    return vt == 0x50e2a4 && slot % 4 == 0 && slot / 4 < 45 ? methods[slot / 4] : 0;
}
extern "C" uint32_t claw_katherine_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, ClawKatherineContext *c,
                                         ClawKatherineDependency d, void *u, uint32_t *out) {
    if (!c || !c->globals || (!specialized(f) && !boss(f) && f != 0x4dc870))
        return 0;
    uint32_t expected = 0;
    switch (f) {
    case 0x453d30:
    case 0x453df0:
    case 0x4542f0:
    case 0x4543e0:
    case 0x4547c0:
    case 0x4548c0:
    case 0x4553a0:
    case 0x40f780:
    case 0x40e0d0:
    case 0x40e280:
    case 0x40e660:
    case 0x4a07e0:
    case 0x4dc870:
        expected = 1;
        break;
    case 0x455360:
        expected = 2;
        break;
    case 0x4208b0:
        expected = 4;
        break;
    default:
        break;
    }
    if (n != expected || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    if (c->fault)
        return 0;
    Run r{*c, d, u};
    try {
        uint32_t words[12]{};
        if (n)
            std::copy_n(a, n, words);
        uint32_t value = specialized(f) ? body(r, f, t, words) : forward(r, f, t, words, n);
        if (out)
            *out = value;
        return 1;
    } catch (Failed &) {
        return 0;
    }
}
