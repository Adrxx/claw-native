#include "WolvingtonRuntime.h"
#include "ActorWrapperRuntime.h"
#include "ActorResourceBindings.h"
#include "PickupPointsRuntime.h"
#include "StackedActorLifecycleRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
const uint32_t methods[] = {0x4a0140, 0x4a0740, 0x4a0230, 0x44d3c0, 0x40e1b0, 0x44df60, 0x4bb030, 0x4c96b0, 0x40e5b0,
                            0x43dfa0, 0x404dd0, 0x44d460, 0x4a07e0, 0x4a07e0, 0x4a07e0, 0x4b7aa0, 0x44d760, 0x4a0800,
                            0x44f1b0, 0x43ed70, 0x43eee0, 0x43ee10, 0x43efe0, 0x40e660, 0x43f640, 0x43f740, 0x43fa10,
                            0x43fcb0, 0x43fd60, 0x43fe00, 0x44dbb0, 0x43ffa0, 0x404e00, 0x44de30, 0x44df10, 0x4407d0,
                            0x43f500, 0x4409d0, 0x440b20, 0x440c90, 0x440410, 0x4bb030, 0x404e10, 0x405060, 0x47eeb0};
const char *label(uint32_t t) {
    switch (t) {
    case 0x523148:
        return "LS_IDLE";
    case 0x522e14:
        return "WolvingtonLFX";
    case 0x522594:
        return "GlitterBaby";
    case 0x5242f0:
        return "LEVEL_WOLVINGTONMAGIC";
    case 0x52417c:
        return "GAME_CYCLE50";
    case 0x522d54:
        return "LogicHit";
    case 0x522d48:
        return "LogicAttack";
    case 0x522da8:
        return "WolvingtonBullet";
    case 0x523204:
        return "LS_HITLOW";
    case 0x523210:
        return "LS_HITHIGH";
    case 0x5234b4:
        return "GAME_NULL";
    case 0x5234ec:
        return "LS_HOME";
    case 0x5240e8:
        return "LS_BOUNCE";
    case 0x527d94:
        return "LS_ADVANCE";
    case 0x528720:
        return "GAME_LIGHTFX_WOLVINGTONLFX";
    case 0x52ded4:
        return "LEVEL_WOLVINGTON_UPPERCUT";
    case 0x52def0:
        return "LEVEL_BLOCK2";
    case 0x52df00:
        return "LEVEL_WOLVINGTON_00880005";
    case 0x52df1c:
        return "LEVEL_WOLVINGTON_00880007";
    case 0x52df38:
        return "LEVEL_WOLVINGTON_00880003";
    case 0x52df54:
        return "LEVEL_WOLVINGTON_BLOCK";
    case 0x52df6c:
        return "LEVEL_WOLVINGTON_THROWN";
    case 0x52df84:
        return "LEVEL_WOLVINGTON_STRIKE1";
    case 0x52dfa0:
        return "LEVEL_WOLVINGTON_LIFTED2";
    case 0x52dfbc:
        return "LEVEL_WOLVINGTON_LIFTED";
    case 0x52dfd4:
        return "LEVEL_WOLVINGTON_KILLFALL";
    case 0x52dff0:
        return "LEVEL_WOLVINGTON_JUMP";
    case 0x52e008:
        return "LEVEL_WOLVINGTON_IDLE";
    case 0x52e020:
        return "LEVEL_WOLVINGTON_HITLOW";
    case 0x52e038:
        return "LEVEL_WOLVINGTON_HITHIGH";
    case 0x52e054:
        return "LEVEL_WOLVINGTON_FASTADVANCE";
    case 0x52e074:
        return "LEVEL_WOLVINGTON_ADVANCE";
    case 0x52e090:
        return "LEVEL_WOLVINGTON";
    case 0x52e0a4:
        return "LS_RUNUPPERCUT";
    case 0x52e0b4:
        return "LS_SWORDATTACK";
    case 0x52e0c4:
        return "LS_SUPPERCUT";
    case 0x52e0d4:
        return "LS_GATTACK";
    case 0x52e0e0:
        return "LS_SGATTACK";
    case 0x52e0f8:
        return "LEVEL_WOLVINGTON_WMAGICLOW";
    case 0x52e114:
        return "LEVEL_WOLVINGTON_STRIKE4";
    case 0x52e130:
        return "LEVEL_WOLVINGTON_WMAGIC";
    case 0x52e148:
        return "LEVEL_WOLVINGTON_STRIKE3";
    case 0x52e164:
        return "LEVEL_WOLVINGTON_STRIKE2";
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
bool owned(uint32_t f) {
    switch (f) {
    case 0x44f1b0:
    case 0x410340:
    case 0x411cf0:
    case 0x411e70:
    case 0x412150:
    case 0x49fb30:
    case 0x49fbf0:
    case 0x4a0140:
    case 0x4a0160:
    case 0x4a0230:
    case 0x4a0740:
    case 0x4a0800:
    case 0x4a0960:
    case 0x4a0a90:
    case 0x4a0ae0:
    case 0x4a0b30:
    case 0x4a0c10:
    case 0x4a0cf0:
    case 0x4a0ec0:
    case 0x4a0f40:
    case 0x4a0fd0:
    case 0x4a1020:
    case 0x4a10b0:
    case 0x4a10f0:
    case 0x4a1180:
    case 0x4a1250:
        return true;
    default:
        return false;
    }
}
struct Run {
    ClawWolvingtonContext &c;
    ClawWolvingtonDependency d;
    void *user;
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
        ClawWolvingtonCall e{};
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
        uint32_t vt = read(t), f = claw_wolvington_function(vt, slot);
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
    if (t >= 0x50ff2c && uint64_t(t) + n * 4 <= 0x50ff2c + sizeof methods && t % 4 == 0)
        return const_cast<uint32_t *>(methods) + (t - 0x50ff2c) / 4;
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
    ClawWolvingtonCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, 12, q.arguments);
    q.name = e->name;
    return r.d ? r.d(&r.c, &q, r.user) : 0;
}
uint32_t resolved(ClawActorResourceBindings *, ClawActorBindingContext *c, const ClawActorBindingCall *, void *) {
    return c->image.token;
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    uint32_t args[12]{};
    std::copy(a.begin(), a.end(), args);
    if (owned(f))
        return body(*this, f, t, args);
    uint32_t out = 0;
    if (c.composeBoss || f == 0x47e810) {
        ClawRauxContext b{host(*this), c.globals, c.composeAnimation, c.composeImages, 0};
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
        claw_actor_animation_entry(f, t, args[0], args[1], &g, host(*this), &c.fault, &out);
        if (c.fault)
            throw Failure{};
        return out;
    }
    if (f == 0x4062e0 || f == 0x4061b0 || f == 0x40f6c0) {
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
uint32_t body(Run &r, uint32_t f, uint32_t p, const uint32_t *a) {
    auto &g = *r.c.globals;
    switch (f) {
    case 0x410340: {
        auto l = r.read(a[0] + 108), id = r.read(l + 28);
        if (!id) {
            r.put(l + 28, 1000);
            auto object = r.invoke(0x4f63ec, 0, {0x158});
            if (object)
                r.invoke(0x411cf0, object, {a[0]});
            r.virt(object, 16);
            r.put(l + 24, object);
        } else if (id == 29)
            r.virt(r.read(l + 24), 32);
        else if (id == 30)
            r.virt(r.read(l + 24), 28);
        else if (id != 1000)
            r.invoke(0x4dc870, 0, {r.read(l + 24)});
        return 1;
    }
    case 0x411cf0: {
        r.invoke(0x4107c0, p, {a[0]});
        r.put(p, 0x50b87c);
        r.invoke(0x4c7970, r.read(p + 300), {0x5242f0});
        r.put(p + 0x148, r.invoke(0x4f6286, r.read(r.read(r.read(p + 300) + 12) + 44) + 16, {0x52417c}));
        r.put(r.read(p + 12) + 8, r.read(r.read(p + 12) + 8) | 0x80000);
        if (!r.read(0x53724c) && r.read(g.managerToken + 0x124)) {
            auto actor = r.read(p + 300);
            r.put(p + 0x154,
                  r.invoke(0x4c8da0, r.read(r.read(r.read(p + 0x130) + 12) + 8),
                           {0, r.read(actor + 76), r.read(actor + 80), r.read(actor + 100) - 1, 0x522e14, 0x40000}));
            r.put(p + 0x150, 2);
        } else {
            r.put(p + 0x154, 0);
            r.put(p + 0x150, 1);
        }
        r.put(r.read(p + 300) + 0xd0, 0x40);
        return p;
    }
    case 0x411e70: {
        auto fn = r.registry(0x534ad8, a[0]);
        if (fn) {
            fn = r.registry(0x534ad8, a[0]);
            r.invoke(fn, p);
        } else
            r.invoke(0x473f40, p, {a[0]});
        return 0;
    }
    case 0x412150: {
        r.invoke(0x4742f0, p);
        if (sign(r.read(p + 0x150)) > 4096) {
            r.c.fault = 3;
            throw Failure{};
        }
        for (int32_t i = 0; i < sign(r.read(p + 0x150)); ++i) {
            if (i >= 4096) {
                r.c.fault = 3;
                throw Failure{};
            }
            auto coordinate = [&](uint32_t off) {
                auto actor = r.read(p + 12);
                auto l = r.read(actor + off), right = r.read(actor + off + 8), width = right - l + 1;
                auto random = r.invoke(0x4a3050, 0);
                if (!width)
                    return (random & 1) ? l : right;
                if (width == 0xffffffff && random == 0x80000000) {
                    r.c.fault = 2;
                    throw Failure{};
                }
                return uint32_t(sign(random) % sign(width)) + l;
            };
            auto px = r.real(p + 0x68);
            auto xc = coordinate(0x118);
            auto x = truncLow(add(px, double(sign(xc))));
            auto py = r.real(p + 0x70);
            auto yc = coordinate(0x11c);
            auto y = truncLow(add(py, double(sign(yc))));
            auto child = r.invoke(0x4c8da0, r.read(r.read(r.read(p + 0x130) + 12) + 8),
                                  {0, x, y, r.read(r.read(p + 12) + 100) - 1, 0x522594, 0x40000});
            r.invoke(r.read(r.read(child + 108) + 16), 0, {child});
        }
        if (r.read(p + 0x154)) {
            if (r.real(p + 0x50) < 0) {
                auto light = r.read(r.read(r.read(p + 0x154) + 108) + 24), visual = r.read(light + 44);
                if (!(r.read(visual + 0x40) & 2)) {
                    r.mirror(light, 56);
                    r.put(visual + 0x40, r.read(visual + 0x40) | 2);
                    visual = r.read(light + 44);
                    if (r.read(visual + 0x118) != 0x80000000)
                        r.mirror(visual, 0x118);
                    r.invoke(0x406150, visual);
                    r.invoke(0x406180, visual);
                }
            }
            auto x = truncLow(r.real(p + 0x68));
            r.put(r.read(p + 0x154) + 76, x);
            auto y = truncLow(r.real(p + 0x70));
            r.put(r.read(p + 0x154) + 80, y);
        }
        return 0;
    }
    case 0x49fb30: {
        auto l = r.read(a[0] + 108), id = r.read(l + 28);
        if (!id) {
            r.put(l + 28, 1000);
            auto object = r.invoke(0x4f63ec, 0, {0x478});
            if (object)
                r.invoke(0x49fbf0, object, {a[0]});
            r.virt(object, 0x10);
            r.put(l + 24, object);
        } else if (id == 29)
            r.virt(r.read(l + 24), 0x20);
        else if (id == 30)
            r.virt(r.read(l + 24), 0x1c);
        else if (id != 1000)
            r.invoke(0x4dc870, 0, {r.read(l + 24)});
        return 1;
    }
    case 0x49fbf0: {
        r.invoke(0x40e0d0, p, {a[0]});
        r.put(p, 0x50ff2c);
        r.invoke(0x4c7970, r.read(p + 300), {0x52e090});
        const uint32_t names[] = {0x52e074, 0x52e054, 0x52e038, 0x52e020, 0x52e008, 0x52dff0,
                                  0x52dff0, 0x52dfd4, 0x52dfd4, 0x52dfbc, 0x52dfa0, 0x52df84,
                                  0x52dfa0, 0x52df6c, 0x52e054, 0x52df54, 0x52df54};
        const uint32_t fields[] = {0x308, 0x30c, 0x338, 0x334, 0x350, 0x33c, 0x340, 0x32c, 0x374,
                                   0x378, 0x37c, 0x310, 0x380, 0x36c, 0x34c, 0x384, 0x388};
        for (unsigned i = 0; i < 17; ++i)
            r.put(p + fields[i], r.sequence(p, names[i]));
        r.put(p + 0x3a4, r.invoke(0x4f6286, r.soundRegistry(p), {0x52df38}));
        r.put(p + 0x410, r.invoke(0x4f6286, r.soundRegistry(p), {0x52df1c}));
        uint32_t manager = r.read(r.read(r.read(p + 300) + 12) + 0x28);
        for (auto pair :
             {std::pair<uint32_t, uint32_t>{0x40c, 0x52df00}, {0x3bc, 0x52def0}, {0x3c0, 0x52def0}, {0x474, 0x52ded4}})
            r.put(p + pair.first, r.invoke(0x4061b0, manager, {pair.second}));
        r.rect(p + 0x230, uint32_t(-101), uint32_t(-60), uint32_t(-41), uint32_t(-21));
        r.rect(p + 0x240, uint32_t(-67), 9, 4, 48);
        for (unsigned o = 0; o < 16; o += 4)
            r.put(p + 0x220 + o, r.read(p + 0x230 + o));
        r.rect(p + 0x210, uint32_t(-1), uint32_t(-1), 1, 1);
        r.rect(p + 0x250, uint32_t(-20), uint32_t(-60), 20, 61);
        r.rect(p + 0x260, uint32_t(-20), uint32_t(-15), 20, 15);
        auto actor = r.read(p + 300);
        r.invoke(0x4208b0, actor, {uint32_t(-20), uint32_t(-50), 20, 50});
        r.invoke(0x40f6c0, actor, {r.read(p + 0x250), r.read(p + 0x254), r.read(p + 0x258), r.read(p + 0x25c)});
        const uint32_t offsets[] = {0x2b4, 0x2b8, 0x2bc, 0x2c0, 0x2c4, 0x2c8, 0x28c, 0x290,
                                    0x294, 0x298, 0x29c, 0x2a0, 0x2a4, 0x2a8, 0x2ac, 0x2b0};
        const uint32_t values[] = {
            10, uint32_t(-10), uint32_t(-45), uint32_t(-20), 20, uint32_t(-15), 500, 40, 300, 40, 200, 40, 56, 40, 56,
            40};
        for (unsigned i = 0; i < 16; ++i)
            r.put(p + offsets[i], values[i]);
        r.put(p + 0x2e4, 50);
        auto range = truncLow(mul(double(g.rangeScale), 50));
        r.put(p + 0x2e4, range < 100 ? 99 : range);
        r.put(r.read(p + 12) + 0x10c, 100);
        r.put(r.read(p + 12) + 0x10c,
              truncLow(mul(double(sign(r.read(r.read(p + 12) + 0x10c))), double(g.healthScale))));
        r.put(r.read(p + 12) + 0x104, 30);
        r.put(r.read(p + 12) + 0x104,
              truncLow(mul(double(sign(r.read(r.read(p + 12) + 0x104))), double(g.damageScale))));
        r.put(p + 0x460, 0);
        actor = r.read(p + 300);
        r.put(actor + 0x164, r.read(actor + 0x164) & ~1u);
        r.invoke(0x40abf0, p + 0x128);
        r.invoke(0x405060, p);
        return p;
    }
    case 0x4a0140:
        r.invoke(0x4a0160, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x4a0160:
        r.invoke(0x47e810, p);
        return 0;
    case 0x4a0230: {
        auto fn = r.registry(0x53ec68, a[0]);
        if (fn) {
            fn = r.registry(0x53ec68, a[0]);
            r.invoke(fn, p);
        } else
            r.invoke(0x40e280, p, {a[0]});
        return 0;
    }
    case 0x4a0740: {
        r.invoke(0x44d000, p, {a[0]});
        auto player = r.read(r.read(g.playerToken + 108) + 20), value = player;
        if (r.read(player + 4) &&
            ((r.read(p + 0x18c) == 3 && r.read(player)) || (r.read(p + 0x18c) == 2 && !r.read(player)))) {
            auto mode = r.read(player + 60);
            value = mode - 1;
            if (mode == 1 || mode == 2 || mode == 7 || mode == 8) {
                value = r.read(p + 0x184);
                if (value == 3 || value == 4) {
                    auto chance = r.read(p + 0x2e4), random = r.invoke(0x4a3050, 0);
                    value = uint32_t(sign(random) / 100);
                    if (sign(random) % 100 < sign(chance) && sign(r.read(p + 32)) > 1)
                        r.put(p + 20, 0x44e620);
                }
            }
        }
        return value;
    }
    case 0x44f1b0: {
        if (r.read(p + 0x18c) == 2) {
            auto actor = r.read(p + 300);
            if (!(r.read(actor + 0x40) & 2)) {
                r.mirror(p, 0x138);
                r.put(actor + 0x40, r.read(actor + 0x40) | 2);
                r.invoke(0x4060b0, r.read(p + 300));
            }
        } else
            r.invoke(0x406310, p + 0x128);
        r.real(p + 0x50, 0);
        r.transition(p, 0x523148);
        if (sign(r.invoke(0x4a3050, 0)) % 100 < 33 && r.read(r.read(p + 300) + 56) != 0xffffffff)
            r.invoke(0x48ce40, 0, {r.read(p + 12), r.read(p + 0x420), 0});
        r.put(p + 0x134, r.read(r.read(p + 300) + 400));
        r.invoke(0x4c8220, r.read(p + 300) + 0x188, {r.read(p + 0x350)});
        r.put(p + 0x43c, 2000);
        r.put(p + 0x438, g.tick);
        return 0;
    }
    case 0x4a0800: {
        auto compare = [&](uint32_t name) {
            auto cell = r.invoke(0x441030, 0x537698, {r.read(r.read(p + 16) + 28)});
            for (auto count = r.read(0x5376b8), t = r.read(0x5376b4); count; --count, t += 4)
                if (t)
                    r.invoke(0x4f6439, t);
            return r.invoke(0x4a3810, 0, {r.read(cell), name});
        };
        if (!compare(0x523210) || !compare(0x523204)) {
            r.invoke(0x43e9c0, p, {500});
            r.invoke(0x4a10b0, p);
            return 0;
        }
        if (!compare(0x5240e8)) {
            r.invoke(0x4a0a90, p);
            return 0;
        }
        r.real(p + 0x50, 0);
        r.transition(p, 0x5234ec);
        return 0;
    }
    case 0x4a0960:
    case 0x4a1250: {
        if (f == 0x4a1250 && (r.real(p + 0x68) == r.real(p + 0x80) || r.real(p + 0x68) == r.real(p + 0x98)))
            r.virt(p, 0x48);
        if (r.read(p + 0x18c) == 2) {
            auto actor = r.read(p + 300);
            if (!(r.read(actor + 0x40) & 2)) {
                r.mirror(p, 0x138);
                r.put(actor + 0x40, r.read(actor + 0x40) | 2);
                r.invoke(0x4060b0, r.read(p + 300));
            }
        } else
            r.invoke(0x406310, p + 0x128);
        if (f == 0x4a1250) {
            auto speed = r.read(p + 0x400);
            r.real(p + 0x50, double(sign(r.read(p + 0x18c) == 3 ? 0u - speed : speed)));
            r.animate(p);
            switch (r.read(p + 0x184)) {
            case 0:
                r.invoke(0x44ebb0, p);
                return 0;
            case 1:
            case 2:
                if (sign(r.read(p + 0x3c4)) >= 0 && sign(r.read(p + 0x3c4)) < 10)
                    r.invoke(0x4a0a90, p);
                if (sign(r.read(p + 0x3c4)) > 9 && sign(r.read(p + 0x3c4)) < 20)
                    r.invoke(0x4a10b0, p);
                return 0;
            case 3:
            case 4:
            case 5:
            case 6:
                r.virt(p, 0x44);
                return 0;
            default:
                return 0;
            }
        }
        switch (r.read(p + 0x184)) {
        case 0:
        case 1:
        case 2:
            if (sign(r.read(p + 0x3c4)) >= 0 && sign(r.read(p + 0x3c4)) < 300)
                r.invoke(0x4a0a90, p);
            if (sign(r.read(p + 0x3c4)) > 299 && sign(r.read(p + 0x3c4)) < 400)
                r.invoke(0x4a10b0, p);
            if (sign(r.read(p + 0x3c4)) > 399 && sign(r.read(p + 0x3c4)) < 1000)
                r.invoke(0x4a1180, p);
            return 0;
        case 3:
        case 4:
            if (sign(r.read(p + 0x3c4)) >= 0 && sign(r.read(p + 0x3c4)) < 500)
                r.invoke(r.read(g.playerToken + 0xcc) == 5 ? 0x4a0fd0 : 0x4a0ec0, p);
            else
                r.virt(p, 0x64);
            return 0;
        case 5:
        case 6:
            r.invoke(0x44edd0, p);
            return 0;
        default:
            return 0;
        }
    }
    case 0x4a1180: {
        if (r.read(p + 0x18c) == 2) {
            auto actor = r.read(p + 300);
            if (!(r.read(actor + 0x40) & 2)) {
                r.mirror(p, 0x138);
                r.put(actor + 0x40, r.read(actor + 0x40) | 2);
                actor = r.read(p + 300);
                r.invoke(0x406120, actor);
                r.invoke(0x406150, actor);
                r.invoke(0x406180, actor);
            }
        } else
            r.invoke(0x406310, p + 0x128);
        auto speed = r.read(p + 0x400);
        r.real(p + 0x50, double(sign(r.read(p + 0x18c) == 3 ? 0u - speed : speed)));
        r.transition(p, 0x527d94);
        r.put(p + 0x134, r.read(r.read(p + 300) + 400));
        r.invoke(0x4c8220, r.read(p + 300) + 0x188, {r.read(p + 0x308)});
        return 0;
    }
    case 0x4a0cf0: {
        r.invoke(r.read(p + 0x18c) == 2 ? 0x4357a0 : 0x406310, p + 0x128);
        if (r.animate(p) == 1 && !r.read(p + 0x1a0)) {
            r.put(p + 0x1a0, 1);
            auto actor = r.read(p + 300);
            auto child = r.invoke(0x4c8da0, r.read(r.read(r.read(p + 0x130) + 12) + 8),
                                  {0, r.read(p + 0x468) + r.read(actor + 76), r.read(p + 0x46c) + r.read(actor + 80),
                                   r.read(actor + 100) - 1, 0x522da8, 0x40000});
            r.put(child + 0x104, 15);
            r.put(child + 0xd0, 0x40);
            r.invoke(r.read(r.read(child + 108) + 16), 0, {child});
            auto priv = r.read(r.read(child + 108) + 24);
            r.real(priv + 0x50, double(sign(r.read(p + 0x470))));
            priv = r.read(r.read(child + 108) + 24);
            r.real(priv + 0x58, 0);
            priv = r.read(r.read(child + 108) + 24);
            r.real(priv + 0x40, 0);
            if (sign(r.read(p + 0x470)) < 0) {
                priv = r.read(r.read(child + 108) + 24);
                auto visual = r.read(priv + 300);
                if (!(r.read(visual + 0x40) & 2)) {
                    r.mirror(priv, 0x138);
                    r.put(visual + 0x40, r.read(visual + 0x40) | 2);
                    visual = r.read(priv + 300);
                    for (auto off : {0x118u, 0x128u, 0x138u})
                        if (r.read(visual + off) != 0x80000000)
                            r.mirror(visual, off);
                }
            }
        }
        if (r.read(r.read(p + 300) + 0x1a4) && !r.read(r.read(p + 300) + 0x19c)) {
            if (r.read(p + 0x460))
                r.invoke(0x4a0a90, p);
            else
                r.virt(p, 0x44);
        }
        return 0;
    }
    case 0x4a0a90:
        r.transition(p, 0x52e0e0);
        r.real(p + 0x50, 0);
        r.put(p + 0x460, 1);
        r.put(p + 0x464, uint32_t(sign(r.invoke(0x4a3050, 0)) % 11));
        return 0;
    case 0x4a0ae0: {
        if (r.read(p + 0x464) == 10) {
            r.virt(p, 0x44);
            r.put(p + 0x460, 0);
        }
        auto value = r.read(p + 0x464);
        r.put(p + 0x464, value + 1);
        r.invoke(value & 1 ? 0x4a0b30 : 0x4a0c10, p);
        return 0;
    }
    case 0x4a0b30:
    case 0x4a0c10:
        r.transition(p, 0x52e0d4);
        r.put(p + 0x134, r.read(r.read(p + 300) + 400));
        r.invoke(0x4c79e0, r.read(p + 300), {f == 0x4a0b30 ? 0x52e114u : 0x52e148u, 0});
        r.audio(r.invoke(0x4f6286, r.soundRegistry(p), {f == 0x4a0b30 ? 0x52e0f8u : 0x52e130u}));
        if (!(r.read(r.read(p + 300) + 0x40) & 2)) {
            r.put(p + 0x468, uint32_t(-65));
            r.put(p + 0x470, uint32_t(-300));
        } else {
            r.put(p + 0x468, 65);
            r.put(p + 0x470, 300);
        }
        r.put(p + 0x46c, f == 0x4a0b30 ? 10 : uint32_t(-20));
        r.put(p + 0x1a0, 0);
        return 0;
    case 0x4a0ec0:
        r.audio(r.read(p + 0x474));
        r.transition(p, 0x52e0c4);
        r.put(p + 0x134, r.read(r.read(p + 300) + 400));
        r.invoke(0x4c79e0, r.read(p + 300), {0x52e164, 0});
        r.real(p + 0x50, 0);
        return 0;
    case 0x4a0fd0:
        r.transition(p, 0x52e0b4);
        r.put(p + 0x134, r.read(r.read(p + 300) + 400));
        r.invoke(0x4c79e0, r.read(p + 300), {0x52df84, 0});
        return 0;
    case 0x4a10b0:
        r.invoke(0x44ebb0, p);
        r.transition(p, 0x52e0a4);
        r.put(r.read(p + 300) + 0x1b0, 0x3e800000);
        return 0;
    case 0x4a0f40:
    case 0x4a1020:
        if (r.animate(p) == 1) {
            auto actor = r.read(p + 12);
            if (f == 0x4a0f40)
                r.rect(actor + 0x138, uint32_t(-59), uint32_t(-63), uint32_t(-36), uint32_t(-8));
            else
                r.rect(actor + 0x138, uint32_t(-95), 1, uint32_t(-24), 42);
            if (r.read(r.read(p + 300) + 0x40) & 2)
                r.mirror(r.read(p + 12), 0x138);
        }
        if (r.read(r.read(p + 300) + 0x1a4) && !r.read(r.read(p + 300) + 0x19c))
            r.virt(p, 0x44);
        return 0;
    case 0x4a10f0:
        r.animate(p);
        switch (r.read(p + 0x184)) {
        case 0:
        case 1:
        case 2:
        case 5:
            break;
        case 3:
        case 4:
            r.invoke(0x4a0ec0, p);
            [[fallthrough]];
        default:
            return 0;
        }
        r.real(p + 0x50, double(sign(r.read(p + 0x18c) == 3 ? 0u - (r.read(p + 0x404) * 4) : r.read(p + 0x404) << 2)));
        return 0;
    default:
        r.c.fault = 3;
        throw Failure{};
    }
}
} // namespace
extern "C" uint32_t claw_wolvington_allocation_bytes(uint32_t f) {
    return f == 0x49fb30 ? 0x478 : f == 0x410340 ? 0x158 : 0;
}
extern "C" uint32_t claw_wolvington_private_bytes(void) {
    return 0x478;
}
extern "C" uint32_t claw_wolvington_function(uint32_t vt, uint32_t slot) {
    const uint32_t bullet[] = {0x484d90, 0x4c9e30, 0x411e70, 0x4063b0, 0x4741f0, 0x4bb030,
                               0x4bb030, 0x4c96b0, 0x414010, 0x4dca10, 0x474290, 0x4bb030};
    if (slot % 4)
        return 0;
    if (vt == 0x50ff2c && slot / 4 < 45)
        return methods[slot / 4];
    if (vt == 0x50b87c && slot / 4 < 12)
        return bullet[slot / 4];
    return 0;
}
extern "C" uint32_t claw_wolvington_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                          ClawWolvingtonContext *c, ClawWolvingtonDependency d, void *user,
                                          uint32_t *out) {
    if (!c || !c->globals || !owned(f))
        return 0;
    uint32_t expected = 0;
    switch (f) {
    case 0x410340:
    case 0x411cf0:
    case 0x411e70:
    case 0x49fb30:
    case 0x49fbf0:
    case 0x4a0140:
    case 0x4a0230:
    case 0x4a0740:
        expected = 1;
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
    uint32_t args[12]{};
    if (n)
        std::copy_n(a, n, args);
    Run r{*c, d, user};
    try {
        auto result = body(r, f, t, args);
        if (out)
            *out = result;
        return !c->fault;
    } catch (Failure &) {
        return 0;
    }
}
