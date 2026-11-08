#include "RauxRuntime.h"
#include "ActorResourceBindings.h"
#include "ActorWrapperRuntime.h"
#include "PickupPointsRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
namespace {
const uint32_t methods[] = {0x47e7f0, 0x47ece0, 0x47e8e0, 0x44d3c0, 0x40e1b0, 0x44df60, 0x4bb030, 0x4c96b0, 0x40e5b0,
                            0x43dfa0, 0x404dd0, 0x47eef0, 0x4a07e0, 0x4a07e0, 0x4a07e0, 0x4b7aa0, 0x44d760, 0x44d9f0,
                            0x47f020, 0x43ed70, 0x43eee0, 0x43ee10, 0x43efe0, 0x40e660, 0x43f640, 0x43f740, 0x43fa10,
                            0x43fcb0, 0x43fd60, 0x43fe00, 0x44dbb0, 0x43ffa0, 0x404e00, 0x44de30, 0x44df10, 0x4407d0,
                            0x43f500, 0x4409d0, 0x440b20, 0x440c90, 0x440410, 0x4bb030, 0x404e10, 0x405060, 0x47eeb0};
int32_t sign(uint32_t v) {
    int32_t x;
    std::memcpy(&x, &v, 4);
    return x;
}
double add(double a, double b) {
    volatile double v = a + b;
    return v;
}
double sub(double a, double b) {
    volatile double v = a - b;
    return v;
}
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
double div(double a, double b) {
    volatile double v = a / b;
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
const char *label(uint32_t t) {
    switch (t) {
    case 0x52b2f0:
        return "LEVEL_RAUX";
    case 0x52b2dc:
        return "LEVEL_RAUX_ADVANCE";
    case 0x52b2c4:
        return "LEVEL_RAUX_FASTADVANCE";
    case 0x52b2b0:
        return "LEVEL_RAUX_STRIKE";
    case 0x52b2a0:
        return "LEVEL_RAUX_FALL";
    case 0x52b290:
        return "LEVEL_RAUX_DEAD";
    case 0x52b27c:
        return "LEVEL_RAUX_HITLOW";
    case 0x52b268:
        return "LEVEL_RAUX_HITHIGH";
    case 0x52b258:
        return "LEVEL_RAUX_JUMP";
    case 0x52b244:
        return "LEVEL_RAUX_JUMPBACK";
    case 0x52b234:
        return "LEVEL_RAUX_HOME";
    case 0x52b220:
        return "LEVEL_RAUX_HOME1";
    case 0x52b210:
        return "LEVEL_RAUX_IDLE";
    case 0x52b1fc:
        return "LEVEL_RAUX_LIFTED";
    case 0x52b1e8:
        return "LEVEL_RAUX_LIFTED2";
    case 0x52b1d4:
        return "LEVEL_RAUX_THROWN";
    case 0x52b1bc:
        return "LEVEL_RAUX_BLOCKHIGH";
    case 0x52b1a8:
        return "LEVEL_RAUX_BLOCKLOW";
    case 0x5234b4:
        return "GAME_NULL";
    case 0x524098:
        return "GAME_AMULETRISE";
    case 0x52b194:
        return "LEVEL_RAUX_00840005";
    case 0x52b184:
        return "LEVEL_DOGINAIR";
    case 0x52b318:
        return "LEVEL_STAB";
    case 0x52b304:
        return "LEVEL_RAUX_BLOCK1";
    case 0x528510:
        return "LEVEL_STAB2";
    case 0x52b324:
        return "LEVEL_RAUX_BLOCK2";
    case 0x528504:
        return "LEVEL_STAB3";
    case 0x523268:
        return "LS_STARTUP";
    case 0x523148:
        return "LS_IDLE";
    case 0x52874c:
        return "LS_JUMPOVER";
    case 0x523204:
        return "LS_HITLOW";
    case 0x523210:
        return "LS_HITHIGH";
    case 0x52b338:
        return "LEVEL_RAUX_00840003";
    case 0x522aac:
        return "EndLevelGem";
    default:
        return nullptr;
    }
}
bool covered(uint32_t f) {
    switch (f) {
    case 0x4a07e0:
    case 0x47e210:
    case 0x47e2d0:
    case 0x40e0d0:
    case 0x40e1b0:
    case 0x40e280:
    case 0x40e560:
    case 0x40e580:
    case 0x40e5b0:
    case 0x40e660:
    case 0x420590:
    case 0x47e7f0:
    case 0x47e810:
    case 0x47ece0:
    case 0x47e8e0:
    case 0x47eef0:
    case 0x47f020:
    case 0x47eeb0:
    case 0x47f0c0:
    case 0x47f160:
    case 0x47f290:
    case 0x47f600:
    case 0x47f680:
    case 0x47f6b0:
    case 0x405060:
    case 0x4208b0:
    case 0x40abf0:
        return true;
    default:
        return false;
    }
}
struct Run {
    ClawRauxContext &c;
    ClawRauxDependency d;
    void *user;
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            return nullptr;
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p)
            c.fault = 1;
        return p;
    }
    uint32_t read(uint32_t t) {
        auto *p = span(t);
        return p ? *p : 0;
    }
    void put(uint32_t t, uint32_t v) {
        if (auto *p = span(t))
            *p = v;
    }
    double real(uint32_t t) {
        double v = 0;
        if (auto *p = span(t, 2))
            std::memcpy(&v, p, 8);
        return v;
    }
    void real(uint32_t t, double v) {
        if (auto *p = span(t, 2))
            std::memcpy(p, &v, 8);
    }
    uint64_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        if (c.fault)
            return 0;
        if (!d) {
            c.fault = 1;
            return 0;
        }
        ClawRauxCall e{};
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
        uint32_t vt = read(t), f = claw_raux_function(vt, slot);
        if (!f)
            f = read(vt + slot);
        invoke(f, t, a);
    }
    void rect(uint32_t t, uint32_t a, uint32_t b, uint32_t c, uint32_t d) {
        put(t, a);
        put(t + 4, b);
        put(t + 8, c);
        put(t + 12, d);
    }
    void mirror(uint32_t a, uint32_t off) {
        uint32_t old = read(a + off);
        put(a + off, 0 - read(a + off + 8));
        put(a + off + 8, 0 - old);
    }
    uint32_t registry(uint32_t t, uint32_t state) {
        put(t + 0x20, 0);
        uint32_t slot;
        if (sign(state) < sign(read(t + 8)) || sign(read(t + 12)) < sign(state)) {
            slot = invoke(0x4db6e0, t, {state, 0});
            if (!slot) {
                uint32_t location = invoke(0x4db5f0, 0);
                put(0x544b14, location);
                invoke(0x4db4d0, read(t + 4), {t, read(0x544b4c), 12});
                slot = read(t + 20);
            }
        } else
            slot = (state - read(t + 8)) * read(t + 24) + read(t + 16);
        return read(slot);
    }
    uint32_t soundRegistry(uint32_t p) {
        return read(read(read(p + 300) + 12) + 0x28) + 16;
    }
    uint32_t sequence(uint32_t p, uint32_t literal) {
        uint32_t t = invoke(0x4062e0, p + 0x128, {literal});
        return t ? t : invoke(0x4062e0, p + 0x128, {0x5234b4});
    }
    void animate(uint32_t p) {
        invoke(0x4c82a0, read(p + 300) + 0x188, {c.globals->animationDelta});
    }
};
uint32_t execute(Run &, uint32_t, uint32_t, const uint32_t *);
uint32_t *hostLookup(void *u, uint32_t t, uint32_t n) {
    return static_cast<Run *>(u)->span(t, n);
}
uint32_t hostCall(void *u, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(u);
    switch (e.argumentCount) {
    case 0:
        return r.invoke(e.function, e.receiver);
    case 1:
        return r.invoke(e.function, e.receiver, {e.arguments[0]});
    case 2:
        return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1]});
    case 3:
        return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2]});
    default:
        return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]});
    }
}
ClawSceneActorHost host(Run &r) {
    return {&r, hostLookup, nullptr, nullptr, hostCall, nullptr};
}
uint32_t resolved(ClawActorResourceBindings *, ClawActorBindingContext *c, const ClawActorBindingCall *, void *) {
    return c->image.token;
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    if (c.fault)
        return 0;
    uint32_t args[12]{};
    std::copy(a.begin(), a.end(), args);
    if (covered(f))
        return execute(*this, f, t, args);
    uint32_t out = 0;
    if ((f == 0x4c8220 || f == 0x4c82a0) && c.composeAnimation) {
        ClawActorAnimationGlobals g{c.globals->animationDelta, c.globals->masterVolume};
        uint32_t fault = 0;
        claw_actor_animation_entry(f, t, args[0], args[1], &g, host(*this), &fault, &out);
        if (fault)
            c.fault = fault;
        return out;
    }
    if (f == 0x4062e0 || f == 0x40f6c0) {
        ClawActorWrapperContext x{host(*this), 0};
        claw_actor_wrapper_entry(f, t, args, uint32_t(a.size()), &x, nullptr, nullptr, &out);
        if (x.fault)
            c.fault = x.fault;
        return out;
    }
    if (f == 0x4c7970 && c.composeImages) {
        uint32_t registry = read(read(t + 12) + 16) + 16, root = invoke(0x4f6286, registry, {args[0]});
        ClawActorBindingContext x{};
        x.imageRegistryToken = registry;
        x.image.token = root;
        uint32_t image = 0;
        if (root) {
            x.image.minimum = sign(read(root + 100));
            x.image.maximum = sign(read(root + 104));
            ClawPickupPointsContext get{};
            get.scene = host(*this);
            uint32_t index = uint32_t(x.image.minimum);
            claw_pickup_points_entry(0x40f680, root, &index, 1, &get, nullptr, nullptr, &image);
            if (get.fault)
                c.fault = get.fault;
            x.image.firstImageIndex = x.image.minimum;
            x.image.images = &image;
            x.image.imageCount = 1;
        }
        auto *p = span(t, 109);
        if (!p)
            return 0;
        ClawActorResourceBindings state{};
        std::copy_n(p, 109, state.actor);
        if (!claw_actor_bind_default_image(&state, &x, label(args[0]), resolved, nullptr)) {
            c.fault = 3;
            return 0;
        }
        std::copy_n(state.actor, 109, p);
        return 1;
    }
    return uint32_t(call(f, t, a));
}
void target(Run &r, uint32_t p, double x, double y, double z) {
    const double ax = r.real(p + 0x38), ay = r.real(p + 0x40), az = r.real(p + 0x48), dx = sub(x, r.real(p + 0x68)),
                 dy = sub(y, r.real(p + 0x70)), dz = z == 0 ? -r.real(p + 0x78) : sub(z, r.real(p + 0x78));
    double dot = sub(sub(-mul(ax, dx), mul(ay, dy)), mul(az, dz));
    double aa = add(add(mul(ax, ax), mul(ay, ay)), mul(az, az));
    double distance = add(add(mul(dx, dx), mul(dy, dy)), mul(dz, dz));
    double speed = std::sqrt(mul(sub(std::sqrt(mul(mul(distance, aa), 4)), mul(dot, -2)), 0.5));
    if (!(speed >= 0.1)) {
        r.real(p + 0x50, 0);
        r.real(p + 0x58, 0);
        r.real(p + 0x60, 0);
        return;
    }
    aa = mul(aa, 0.25);
    if (-0.1 <= aa && aa <= 0.1) {
        double length = add(add(std::abs(dx), std::abs(dy)), std::abs(dz));
        r.real(p + 0x50, mul(div(dx, length), speed));
        r.real(p + 0x58, mul(div(dy, length), speed));
        r.real(p + 0x60, mul(div(dz, length), speed));
        return;
    }
    double time = div(sub(mul(speed, speed), dot), add(aa, aa)), root = std::sqrt(time);
    r.real(p + 0x50, div(sub(dx, mul(mul(time, ax), 0.5)), root));
    r.real(p + 0x58, div(sub(dy, mul(mul(time, ay), 0.5)), root));
    r.real(p + 0x60, div(sub(dz, mul(mul(time, az), 0.5)), root));
}
uint32_t execute(Run &r, uint32_t f, uint32_t p, const uint32_t *a) {
    auto &g = *r.c.globals;
    switch (f) {
    case 0x4a07e0:
        r.put(a[0] + 8, r.read(a[0] + 8) | 0x10000);
        r.virt(p, 0x9c);
        return 0;
    case 0x47e210: {
        uint32_t l = r.read(a[0] + 108), state = r.read(l + 28);
        if (!state) {
            r.put(l + 28, 1000);
            uint32_t object = r.invoke(0x4f63ec, 0, {0x478});
            if (object)
                r.invoke(0x47e2d0, object, {a[0]});
            r.virt(object, 0x10);
            r.put(l + 24, object);
        } else if (state == 29)
            r.virt(r.read(l + 24), 0x20);
        else if (state == 30)
            r.virt(r.read(l + 24), 0x1c);
        else if (state != 1000)
            r.invoke(0x4dc870, 0, {r.read(l + 24)});
        return 1;
    }
    case 0x40e0d0:
        r.invoke(0x44c000, p, {a[0]});
        r.put(p, 0x50b5d4);
        r.put(p + 0x458, r.invoke(0x4f6286, r.soundRegistry(p), {0x524098}));
        r.put(r.read(p + 12) + 8, r.read(r.read(p + 12) + 8) | 0x80000);
        r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) | 2);
        g.bossActorToken = r.read(p + 12);
        r.put(p + 0x45c, 0);
        r.put(p + 0x450, r.read(r.read(p + 12) + 76));
        r.put(p + 0x454, r.read(r.read(p + 12) + 80));
        return p;
    case 0x47e2d0: {
        r.invoke(0x40e0d0, p, {a[0]});
        for (uint32_t o = 0x460; o <= 0x474; o += 4)
            r.put(p + o, 0);
        r.put(p, 0x50f1ac);
        r.invoke(0x4c7970, r.read(p + 300), {0x52b2f0});
        const uint32_t names[] = {0x52b2dc, 0x52b2c4, 0x52b2b0, 0x52b2a0, 0x52b290, 0x52b27c, 0x52b268,
                                  0x52b258, 0x52b244, 0x52b234, 0x52b220, 0x52b2c4, 0x52b210, 0x52b1fc,
                                  0x52b1e8, 0x52b1e8, 0x52b1d4, 0x52b1bc, 0x52b1a8};
        const uint32_t fields[] = {0x308, 0x30c, 0x310, 0x32c, 0x374, 0x334, 0x338, 0x33c, 0x340, 0x344,
                                   0x348, 0x34c, 0x350, 0x378, 0x37c, 0x380, 0x36c, 0x384, 0x388};
        for (uint32_t i = 0; i < 19 && !r.c.fault; ++i) {
            r.put(p + fields[i], r.sequence(p, names[i]));
            if (i == 2)
                for (uint32_t o : {0x318u, 0x31cu, 0x320u})
                    r.put(p + o, 0);
        }
        r.put(p + 0x3a4, r.invoke(0x4f6286, r.soundRegistry(p), {0x52b194}));
        r.put(p + 0x410, r.invoke(0x4f6286, r.soundRegistry(p), {0x52b184}));
        r.rect(p + 0x220, uint32_t(-117), uint32_t(-4), uint32_t(-30), 21);
        r.rect(p + 0x210, uint32_t(-1), uint32_t(-1), 1, 1);
        r.rect(p + 0x250, uint32_t(-15), uint32_t(-60), 15, 52);
        r.rect(p + 0x260, uint32_t(-15), uint32_t(-60), 15, 52);
        const uint32_t offsets[] = {0x28c, 0x290, 0x29c, 0x2a0, 0x2a4, 0x2a8, 0x2ac,
                                    0x2b0, 0x2b4, 0x2b8, 0x2bc, 0x2c0, 0x2c4, 0x2c8};
        const uint32_t values[] = {500,           20, 300,          20, 150, 20, 100, 20, 0, 0, uint32_t(-60),
                                   uint32_t(-20), 20, uint32_t(-15)};
        for (uint32_t i = 0; i < 14; ++i)
            r.put(p + offsets[i], values[i]);
        r.put(p + 0x2e4, 100);
        uint32_t range = truncLow(mul(double(g.rangeScale), 100));
        r.put(p + 0x2e4, range < 100 ? 99 : range);
        r.put(r.read(p + 12) + 0x10c, 100);
        r.put(r.read(p + 12) + 0x10c,
              truncLow(mul(double(sign(r.read(r.read(p + 12) + 0x10c))), double(g.healthScale))));
        r.put(r.read(p + 12) + 0x104, 10);
        r.put(r.read(p + 12) + 0x104,
              truncLow(mul(double(sign(r.read(r.read(p + 12) + 0x104))), double(g.damageScale))));
        uint32_t size = r.read(p + 0x2fc);
        if (size > 9) {
            uint32_t bit = size <= 32 ? p + 0x300 : r.read(p + 0x300);
            r.put(bit, r.read(bit) ^ 0x200);
        }
        uint32_t actor = r.read(p + 300);
        r.invoke(0x40f6c0, actor, {r.read(p + 0x250), r.read(p + 0x254), r.read(p + 0x258), r.read(p + 0x25c)});
        r.invoke(0x4208b0, r.read(p + 300), {0, uint32_t(-60), 20, 35});
        r.invoke(0x40abf0, p + 0x128);
        r.invoke(0x405060, p);
        return p;
    }
    case 0x4208b0:
        r.rect(p + 0x128, a[0], a[1], a[2], a[3]);
        return 0;
    case 0x40abf0:
        r.put(r.read(p + 4) + 80, r.read(r.read(p + 4) + 80) - 32);
        r.invoke(0x4cd800, r.read(r.read(r.read(p) + 12) + 0x24), {r.read(p), 0});
        r.put(r.read(p) + 0xcc, 1);
        return 0;
    case 0x405060:
        r.put(p + 0x24, r.read(r.read(p + 0x10) + 28));
        r.put(r.read(p + 0x10) + 28, r.invoke(0x4dba00, 0x537668, {0x523268}));
        r.put(p + 0x134, r.read(r.read(p + 300) + 400));
        r.invoke(0x4c8220, r.read(p + 300) + 0x188, {r.read(p + 0x350)});
        return 0;
    case 0x40e1b0: {
        uint32_t actor = r.read(p + 12);
        r.rect(actor + 0x138, r.read(p + 0x210), r.read(p + 0x214), r.read(p + 0x218), r.read(p + 0x21c));
        if (r.read(r.read(p + 300) + 0x40) & 2)
            r.mirror(r.read(p + 12), 0x138);
        r.put(p + 0x3b0, r.read(p + 0x3a4));
        return 0;
    }
    case 0x47e7f0:
        r.invoke(0x47e810, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x47e810:
        r.put(p, 0x50b16c);
        r.invoke(0x4dbcd0, p + 0x2f4);
        r.invoke(0x4f6584, p + 0x1a8);
        r.invoke(0x4f6584, p + 0x1a4);
        r.put(p, 0x50b014);
        return 0;
    case 0x40e560:
        r.real(p + 0x68, double(sign(r.read(p + 0x450))));
        r.real(p + 0x70, double(sign(r.read(p + 0x454))));
        return 0;
    case 0x47eeb0:
        r.invoke(0x40e560, p);
        r.put(r.read(p + 12) + 0x10c, 100);
        r.put(r.read(p + 12) + 0x10c,
              truncLow(mul(double(sign(r.read(r.read(p + 12) + 0x10c))), double(g.healthScale))));
        return 0;
    case 0x40e5b0:
        r.invoke(0x44cfd0, p);
        g.bossActorToken = 0;
        return 0;
    case 0x420590:
        if (g.playerToken) {
            uint32_t l = r.read(g.playerToken + 108);
            if (l)
                r.put(l + 28, 5010);
        }
        return 0;

    case 0x40e660:
        r.invoke(0x44e0c0, p, {a[0]});
        if (sign(r.read(g.playerToken + 0x10c)) > 0) {
            r.invoke(0x420590, 0);
            r.invoke(0x40e5c0, p);
        }
        return 0;
    case 0x40e580:
        r.animate(p);
        if (r.read(0x53c9c0) == 2)
            r.virt(p, 0x48);
        return 0;
    case 0x47f020:
        r.put(p + 0x50, 0);
        r.put(p + 0x54, 0);
        r.put(p + 0x24, r.read(r.read(p + 16) + 28));
        r.put(r.read(p + 16) + 28, r.invoke(0x4dba00, 0x537668, {0x523148}));
        r.put(p + 0x134, r.read(r.read(p + 300) + 400));
        r.invoke(0x4c8220, r.read(p + 300) + 0x188, {r.read(p + 0x350)});
        if (sign(r.read(p + 0x3c4)) >= 0 && sign(r.read(p + 0x3c4)) < 500)
            r.invoke(0x48ceb0, 0, {r.read(p + 12), 0x52b338, 0});
        r.put(p + 0x474, 4000);
        r.put(p + 0x470, g.tick);
        return 0;
    case 0x47e8e0: {
        uint32_t f = r.registry(0x53c148, a[0]);
        if (f) {
            f = r.registry(0x53c148, a[0]);
            r.invoke(f, p);
        } else
            r.invoke(0x40e280, p, {a[0]});
        return 0;
    }
    case 0x40e280: {
        uint32_t f = r.registry(0x5349b8, a[0]);
        if (f) {
            f = r.registry(0x5349b8, a[0]);
            r.invoke(f, p);
        } else
            r.invoke(0x44c840, p, {a[0]});
        return 0;
    }
    case 0x47ece0: {
        r.invoke(0x44d000, p, {a[0]});
        int32_t random = sign(r.invoke(0x4a3050, 0)) % 3;
        if (random == 0) {
            r.put(p + 0x3a0, r.invoke(0x4f6286, r.soundRegistry(p), {0x52b318}));
            r.put(p + 0x3bc, r.invoke(0x4f6286, r.soundRegistry(p), {0x52b304}));
        } else if (random == 1) {
            r.put(p + 0x3a0, r.invoke(0x4f6286, r.soundRegistry(p), {0x528510}));
            r.put(p + 0x3bc, r.invoke(0x4f6286, r.soundRegistry(p), {0x52b324}));
        } else if (random == 2)
            r.put(p + 0x3a0, r.invoke(0x4f6286, r.soundRegistry(p), {0x528504}));
        uint32_t l = r.read(g.playerToken + 108), priv = r.read(l + 20);
        if (!r.read(priv + 4))
            return l;
        uint32_t facing = r.read(p + 0x18c);
        if ((facing != 3 || !r.read(priv)) && (facing != 2 || r.read(priv)))
            return facing;
        uint32_t relation = r.read(p + 0x184);
        if (relation != 3 && relation != 4)
            return relation;
        uint32_t value = r.invoke(0x4a3050, 0);
        if (sign(r.read(p + 0x2e4)) <= sign(value) % 100)
            return uint32_t(sign(value) / 100);
        uint32_t distance = r.read(p + 0x3c4);
        if (sign(distance) >= 0 && sign(distance) < 100) {
            if (sign(r.read(p + 0x20)) >= 2)
                r.put(p + 0x14, 0x44e620);
        } else if (sign(distance) >= 100 && sign(distance) < 200) {
            if (sign(r.read(p + 0x20)) >= 2)
                r.put(p + 0x14, 0x455350);
        } else if (sign(distance) >= 200 && sign(distance) < 500 && sign(r.read(p + 0x20)) > 1)
            r.put(p + 0x14, 0x47f290);
        return distance;
    }
    case 0x47eef0: {
        r.invoke(0x43e9c0, p, {350});
        uint32_t current = r.invoke(0x441030, 0x537698, {r.read(r.read(p + 16) + 28)});
        auto release = [&]() {
            for (uint32_t n = r.read(0x5376b8), t = r.read(0x5376b4); n && !r.c.fault; --n, t += 4)
                if (t)
                    r.invoke(0x4f6439, t);
        };
        release();
        uint32_t cmp = r.invoke(0x4a3810, 0, {r.read(current), 0x523204});
        if (cmp) {
            current = r.invoke(0x441030, 0x537698, {r.read(r.read(p + 16) + 28)});
            release();
            cmp = r.invoke(0x4a3810, 0, {r.read(current), 0x523210});
        }
        if (!cmp) {
            r.virt(p, 0x44);
            return 0;
        }
        if (sign(r.read(p + 0x3c4)) >= 0 && sign(r.read(p + 0x3c4)) < 100) {
            r.virt(p, 0x9c);
            return 0;
        }
        uint32_t priv = r.read(r.read(g.playerToken + 108) + 20);
        r.invoke(r.read(priv + 20) ? 0x44f510 : 0x44f3c0, p);
        r.virt(p, 0x28, {a[0]});
        r.invoke(0x440e20, p, {a[0]});
        return 0;
    }
    case 0x47f0c0: {
        r.animate(p);
        switch (r.read(p + 0x184)) {
        case 0:
        case 1:
        case 2:
        case 5:
        case 6:
            if (r.read(p + 0x474) <= g.tick - r.read(p + 0x470) && !g.jumpDisabled &&
                sign(r.invoke(0x4a3050, 0)) % 100 < 5)
                r.invoke(0x44edd0, p);
            break;
        case 3:
        case 4:
            r.virt(p, 0x44);
            break;
        default:
            break;
        }
        return 0;
    }
    case 0x47f160: {
        uint32_t actor = r.read(p + 300), face = r.read(p + 0x18c);
        if ((face == 2 && !(r.read(actor + 0x40) & 2)) || (face != 2 && (r.read(actor + 0x40) & 2))) {
            r.mirror(p, 0x138);
            r.put(actor + 0x40, face == 2 ? r.read(actor + 0x40) | 2 : r.read(actor + 0x40) & ~2u);
            actor = r.read(p + 300);
            r.invoke(0x406120, actor);
            r.invoke(0x406150, actor);
            r.invoke(0x406180, actor);
        }
        int32_t random = sign(r.invoke(0x4a3050, 0)) % 121;
        uint32_t relation = r.read(p + 0x184);
        if (relation == 2) {
            if (random < 20)
                r.invoke(0x47f290, p);
        } else if (relation == 3) {
            if (random < sign(r.read(p + 0x2e4)))
                r.virt(p, 0x58);
            else if (random < sign(r.read(p + 0x2e4) + 20))
                r.virt(p, 0x68);
        } else if (relation == 4)
            r.virt(p, sign(r.invoke(0x4a3050, 0)) % 100 < 50 ? 0x64 : 0x58);
        r.invoke(0x44da20, p);
        return 0;
    }
    case 0x47f290: {
        uint32_t actor = r.read(p + 12);
        if (r.read(actor + 0xcc) != 1)
            return 0;
        uint32_t x = r.read(p + 0x18c) == 3 ? truncLow(r.real(p + 0x80)) + 20 : truncLow(r.real(p + 0x98)) - 20;
        double targetX = double(sign(x));
        if (!(r.real(p + 0x80) <= targetX && targetX <= r.real(p + 0x98)))
            return 0;
        uint32_t source = r.read(p + 0x128), y = r.read(source + 0x124) + 1 + r.read(source + 80);
        uint32_t type = r.invoke(0x4207f0, r.read(r.read(source + 12) + 0x24), {x, y});
        if (type != 1) {
            source = r.read(p + 0x128);
            type = r.invoke(0x4207f0, r.read(r.read(source + 12) + 0x24), {x, y});
            if (type != 2) {
                source = r.read(p + 0x128);
                type = r.invoke(0x4207f0, r.read(r.read(source + 12) + 0x24), {x, y});
                if (type != 3)
                    return 0;
            }
        }
        source = r.read(p + 0x128);
        if (r.invoke(0x4207f0, r.read(r.read(source + 12) + 0x24), {x, y - 1}))
            return 0;
        target(r, p, targetX, double(sign(r.read(g.playerToken + 0x124) + r.read(g.playerToken + 80))), 0);
        r.put(p + 24, 0x43f720);
        r.put(p + 32, 1);
        r.put(r.read(p + 300) + 8, r.read(r.read(p + 300) + 8) | 4);
        r.invoke(r.read(p + 0x18c) == 2 ? 0x4357a0 : 0x406310, p + 0x128);
        r.put(r.read(p + 12) + 0xcc, 8);
        r.put(p + 0x24, r.read(r.read(p + 16) + 28));
        r.put(r.read(p + 16) + 28, r.invoke(0x4dba00, 0x537668, {0x52874c}));
        r.put(p + 0x134, r.read(r.read(p + 300) + 400));
        r.invoke(0x4c8220, r.read(p + 300) + 0x188, {r.read(p + 0x33c)});
        return 0;
    }
    case 0x47f600:
        r.animate(p);
        r.rect(r.read(p + 12) + 0x138, uint32_t(-14), 1, 9, 39);
        if (r.read(r.read(p + 300) + 0x40) & 2)
            r.mirror(r.read(p + 12), 0x138);
        if (r.read(r.read(p + 12) + 0xcc) == 1) {
            r.invoke(0x43f720, p);
            r.virt(p, 0x44);
        }
        return 0;
    case 0x47f680:
    case 0x47f6b0:
        r.invoke(f == 0x47f680 ? 0x44f660 : 0x44f490, p);
        if (r.read(r.read(p + 300) + 0x1a4) && !r.read(r.read(p + 300) + 0x19c))
            r.virt(p, 0x58);
        return 0;
    default:
        return 0;
    }
}
} // namespace
extern "C" uint32_t claw_raux_private_bytes(void) {
    return 0x478;
}
extern "C" uint32_t claw_raux_function(uint32_t vt, uint32_t slot) {
    return vt == 0x50f1ac && slot % 4 == 0 && slot / 4 < 45 ? methods[slot / 4] : 0;
}
extern "C" uint32_t claw_raux_entry(uint32_t f, uint32_t receiver, const uint32_t *args, uint32_t n, ClawRauxContext *c,
                                    ClawRauxDependency d, void *user, uint32_t *out) {
    if (!c || !c->globals || !covered(f))
        return 0;
    uint32_t expected = 0;
    switch (f) {
    case 0x4a07e0:
    case 0x47e210:
    case 0x47e2d0:
    case 0x40e0d0:
    case 0x47e7f0:
    case 0x47ece0:
    case 0x47e8e0:
    case 0x40e280:
    case 0x47eef0:
    case 0x40e660:
        expected = 1;
        break;
    case 0x4208b0:
        expected = 4;
        break;
    default:
        break;
    }
    if (n != expected || (n && !args)) {
        c->fault = 3;
        return 0;
    }
    uint32_t words[12]{};
    if (n)
        std::copy_n(args, n, words);
    Run r{*c, d, user};
    uint32_t value = execute(r, f, receiver, words);
    if (out)
        *out = value;
    return !c->fault;
}
