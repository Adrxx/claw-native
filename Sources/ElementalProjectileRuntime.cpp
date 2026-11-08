#include "ElementalProjectileRuntime.h"
#include "ActorResourceBindings.h"
#include "PickupPointsRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
struct Profile {
    uint32_t callback, ctor, vt, dispatch, table, flight, image, ani;
};
const Profile profiles[] = {{0x410100, 0x410ec0, 0x50b7bc, 0x411030, 0x534ba0, 0x411310, 0x5241e4, 0x5241d4},
                            {0x4101c0, 0x411370, 0x50b80c, 0x4114e0, 0x534a38, 0x4117c0, 0x524244, 0x524230},
                            {0x410280, 0x411820, 0x50b844, 0x411990, 0x534b00, 0x411c70, 0x5242a4, 0x524294}};
const Profile *profile(uint32_t f) {
    for (auto &p : profiles)
        if (f == p.callback || f == p.ctor || f == p.dispatch || f == p.flight || f == p.vt)
            return &p;
    return nullptr;
}
const char *label(uint32_t t) {
    switch (t) {
    case 0x5241e4:
        return "GAME_PROJECTILES_FIRESWORD";
    case 0x5241d4:
        return "GAME_FIRESWORD";
    case 0x524244:
        return "GAME_PROJECTILES_LIGHTNINGSWORD";
    case 0x524230:
        return "GAME_LIGHTNINGSWORD";
    case 0x5242a4:
        return "GAME_PROJECTILES_ICESWORD";
    case 0x524294:
        return "GAME_ICESWORD";
    case 0x522e24:
        return "Flare";
    default:
        return nullptr;
    }
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
int32_t si(uint32_t v) {
    int32_t s;
    std::memcpy(&s, &v, 4);
    return s;
}
bool inherited(uint32_t f) {
    switch (f) {
    case 0x4107c0:
    case 0x473c50:
    case 0x4741f0:
    case 0x474290:
    case 0x4742f0:
    case 0x473f40:
    case 0x4dc870:
    case 0x4dca10:
    case 0x4063b0:
    case 0x484d90:
    case 0x456030:
    case 0x4c9e30:
    case 0x4c96b0:
    case 0x4bb030:
        return true;
    default:
        return false;
    }
}
struct Run {
    ClawElementalProjectileContext &c;
    ClawElementalProjectileDependency d;
    void *u;
    uint32_t depth = 0;
    [[noreturn]] void fail(uint32_t n = 1) {
        if (!c.fault)
            c.fault = n;
        throw Failure{};
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failure{};
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
    uint64_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        if (!d)
            fail();
        ClawElementalProjectileCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), e.arguments);
        for (auto v : a)
            if (label(v)) {
                e.name = label(v);
                break;
            }
        uint64_t result = d(&c, &e, u);
        if (c.fault)
            throw Failure{};
        return result;
    }
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t> = {});
    uint32_t virt(uint32_t t, uint32_t off) {
        return invoke(get(get(t) + off), t);
    }
    void image(uint32_t actor, uint32_t literal) {
        uint32_t registry = get(get(actor + 12) + 16) + 16, root = uint32_t(call(0x4f6286, registry, {literal}));
        ClawActorBindingContext c{};
        c.imageRegistryToken = registry;
        c.image.token = root;
        uint32_t selected = 0;
        if (root) {
            c.image.minimum = si(get(root + 100));
            c.image.maximum = si(get(root + 104));
            ClawPickupPointsContext p{};
            p.scene = host();
            uint32_t index = uint32_t(c.image.minimum);
            if (!claw_pickup_points_entry(0x40f680, root, &index, 1, &p, nullptr, nullptr, &selected) || p.fault)
                fail(p.fault ? p.fault : 1);
            c.image.firstImageIndex = c.image.minimum;
            c.image.images = &selected;
            c.image.imageCount = 1;
        }
        ClawActorResourceBindings s{};
        std::copy_n(span(actor, 128), 128, s.actor);
        if (!claw_actor_bind_default_image(
                &s, &c, label(literal),
                [](ClawActorResourceBindings *, ClawActorBindingContext *c, const ClawActorBindingCall *, void *) {
                    return c->image.token;
                },
                nullptr))
            fail();
        std::copy_n(s.actor, 128, span(actor, 128));
    }
    uint32_t table(uint32_t t, uint32_t state) {
        put(t + 32, 0);
        uint32_t cell;
        if (si(state) < si(get(t + 8)) || si(state) > si(get(t + 12))) {
            if (!invoke(0x4db6e0, t, {state, 0})) {
                uint32_t text = get(0x544b4c);
                put(0x544b14, invoke(0x4db5f0, 0));
                invoke(0x4db4d0, get(t + 4), {t, text, 12});
                cell = get(t + 20);
            } else
                cell = get(t + 16) + (state - get(t + 8)) * get(t + 24);
        } else
            cell = get(t + 16) + (state - get(t + 8)) * get(t + 24);
        return get(cell);
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        return static_cast<Run *>(u)->span(t, n);
    }
    static uint32_t hostCall(void *u, ClawSceneActorCall q) {
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
    static void release(void *u, uint32_t t) {
        auto &r = *static_cast<Run *>(u);
        if (r.c.scene.free)
            r.c.scene.free(r.c.scene.context, t);
        else
            r.call(0x4f6428, 0, {t});
    }
    ClawSceneActorHost host() {
        return {this, lookup, nullptr, release, hostCall, nullptr};
    }
};
uint32_t body(Run &, uint32_t, uint32_t, const uint32_t *);
uint64_t sharedDependency(ClawPlayerProjectileContext *, const ClawPlayerProjectileCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (!profile(e->function) && e->function != 0x411cd0 && !inherited(e->function)) {
        if (!r.d)
            r.fail();
        uint64_t v = r.d(&r.c, e, r.u);
        if (r.c.fault)
            throw Failure{};
        return v;
    }
    switch (e->argumentCount) {
    case 0:
        return r.invoke(e->function, e->receiver);
    case 1:
        return r.invoke(e->function, e->receiver, {e->arguments[0]});
    case 2:
        return r.invoke(e->function, e->receiver, {e->arguments[0], e->arguments[1]});
    case 3:
        return r.invoke(e->function, e->receiver, {e->arguments[0], e->arguments[1], e->arguments[2]});
    case 4:
        return r.invoke(e->function, e->receiver, {e->arguments[0], e->arguments[1], e->arguments[2], e->arguments[3]});
    default:
        r.fail(3);
    }
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    if (++depth > 64)
        fail(3);
    uint32_t args[12]{};
    std::copy(a.begin(), a.end(), args);
    uint32_t value = 0;
    if (f == 0x4c7970) {
        image(t, args[0]);
        value = 1;
    } else if (profile(f) || f == 0x411cd0)
        value = body(*this, f, t, args);
    else if (inherited(f)) {
        ClawPlayerProjectileContext shared = c;
        shared.scene = host();
        shared.fault = 0;
        if (!claw_player_projectile_entry(f, t, args, uint32_t(a.size()), &shared, sharedDependency, this, &value) ||
            shared.fault)
            fail(shared.fault ? shared.fault : 1);
    } else
        value = uint32_t(call(f, t, a));
    --depth;
    return value;
}
uint32_t body(Run &r, uint32_t f, uint32_t t, const uint32_t *a) {
    if (f == 0x411cd0) {
        uint32_t flare = r.get(t + 0x150);
        if (flare)
            r.put(flare + 8, r.get(flare + 8) | 0x10000);
        return 0;
    }
    auto *p = profile(f);
    if (f == p->callback) {
        uint32_t actor = a[0], primary = r.get(actor + 108), state = r.get(primary + 28);
        if (!state) {
            r.put(primary + 28, 1000);
            uint32_t object = r.invoke(0x4f63ec, 0, {0x158});
            if (object)
                object = r.invoke(p->ctor, object, {actor});
            if (!object)
                r.fail(2);
            r.virt(object, 16);
            r.put(primary + 24, object);
        } else if (state == 29 || state == 30)
            r.virt(r.get(primary + 24), state == 29 ? 32 : 28);
        else if (state != 1000)
            r.invoke(0x4dc870, r.get(primary + 24));
        return 1;
    }
    if (f == p->ctor) {
        r.invoke(0x4107c0, t, {a[0]});
        r.put(t, p->vt);
        uint32_t actor = r.get(t + 300);
        r.invoke(0x4c7970, actor, {p->image});
        actor = r.get(t + 300);
        r.put(t + 0x148, r.invoke(0x4f6286, r.get(r.get(actor + 12) + 44) + 16, {p->ani}));
        actor = r.get(t + 12);
        r.put(actor + 8, r.get(actor + 8) | 0x80000);
        uint32_t flare = 0;
        if (!r.c.globals->magicDisabled && r.get(r.c.globals->ownerToken + 0x124)) {
            actor = r.get(t + 300);
            uint32_t container = r.get(r.get(r.get(t + 0x130) + 12) + 8);
            flare = r.invoke(0x4c8da0, container,
                             {0, r.get(actor + 76), r.get(actor + 80), r.get(actor + 100) - 1, 0x522e24, 0x40000});
        }
        r.put(t + 0x150, flare);
        return t;
    }
    if (f == p->dispatch) {
        uint32_t fn = r.table(p->table, a[0]);
        if (fn) {
            fn = r.table(p->table, a[0]);
            r.invoke(fn, t);
        } else
            r.invoke(0x473f40, t, {a[0]});
        return 0;
    }
    r.invoke(0x4742f0, t);
    uint32_t flare = r.get(t + 0x150);
    if (flare) {
        volatile double x = r.real(t + 0x68) - r.real(r.real(t + 0x50) > r.real(0x50b7f0) ? 0x50b7f8 : 0x50b800);
        r.put(flare + 76, ftol(x));
        r.put(r.get(t + 0x150) + 80, ftol(r.real(t + 0x70)));
    }
    return 0;
}
} // namespace
extern "C" uint32_t claw_elemental_projectile_private_bytes(uint32_t f) {
    for (auto &p : profiles)
        if (f == p.callback)
            return 0x158;
    return 0;
}
extern "C" uint32_t claw_elemental_projectile_function(uint32_t vt, uint32_t slot) {
    auto *p = profile(vt);
    if (!p || p->vt != vt || slot % 4 || slot >= 48)
        return 0;
    const uint32_t v[] = {0x484d90, 0x4c9e30, p->dispatch, 0x4063b0, 0x4741f0, 0x4bb030,
                          0x4bb030, 0x4c96b0, 0x411cd0,    0x4dca10, 0x474290, 0x4bb030};
    return v[slot / 4];
}
extern "C" uint32_t claw_elemental_projectile_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                    ClawElementalProjectileContext *c,
                                                    ClawElementalProjectileDependency d, void *u, uint32_t *out) {
    auto *p = profile(f);
    if ((p && f == p->vt) || (!p && f != 0x411cd0 && !inherited(f)))
        return 0;
    if (!c || !c->globals)
        return 0;
    uint32_t expected = (p && (f == p->callback || f == p->ctor || f == p->dispatch)) || f == 0x484d90 ||
                                f == 0x4c9e30 || f == 0x4063b0 || f == 0x4107c0 || f == 0x473c50 || f == 0x473f40 ||
                                f == 0x4dc870
                            ? 1
                            : 0;
    if (n != expected || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    if (c->fault)
        return 0;
    Run r{*c, d, u};
    try {
        uint32_t value = 0;
        if (f == 0x4dc870)
            value = r.invoke(f, a[0]);
        else if (n)
            value = r.invoke(f, t, {a[0]});
        else
            value = r.invoke(f, t);
        if (out)
            *out = value;
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
