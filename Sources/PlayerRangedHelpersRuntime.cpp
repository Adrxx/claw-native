#include "PlayerRangedHelpersRuntime.h"
#include "ActorResourceBindings.h"
#include "PickupPointsRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#include <limits>
namespace {
struct Failure {};
int32_t si(uint32_t v) {
    int32_t x;
    std::memcpy(&x, &v, 4);
    return x;
}
const char *label(uint32_t t) {
    switch (t) {
    case 0x522dc8:
        return "PistolBullet";
    case 0x522e00:
        return "MagicBullet";
    case 0x522bec:
        return "Dynamite";
    case 0x522df4:
        return "FireBullet";
    case 0x522de4:
        return "LightningBullet";
    case 0x522dd8:
        return "IceBullet";
    case 0x524130:
        return "GAME_BULLETS";
    case 0x5247b0:
        return "CLAW_FIRESWORD";
    case 0x5247c0:
        return "CLAW_LIGHTSWORD";
    case 0x5247d0:
        return "CLAW_ICESWORD";
    default:
        return nullptr;
    }
}
struct Run {
    ClawPlayerRangedHelpersContext &c;
    ClawPlayerRangedHelpersDependency d;
    void *u;
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
    uint64_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawPlayerRangedHelpersCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        for (auto v : a)
            if (label(v)) {
                q.name = label(v);
                break;
            }
        uint64_t value;
        if (d)
            value = d(&c, &q, u);
        else if (c.scene.call && a.size() <= 4) {
            ClawSceneActorCall e{};
            e.function = f;
            e.receiver = t;
            e.argumentCount = q.argumentCount;
            std::copy(a.begin(), a.end(), e.arguments);
            value = c.scene.call(c.scene.context, e);
        } else
            fail();
        if (c.fault)
            throw Failure{};
        return value;
    }
    uint32_t create(uint32_t actor, uint32_t x, uint32_t y, uint32_t z, uint32_t name) {
        uint32_t container = get(get(actor + 12) + 8);
        if (!c.composeCreation)
            return uint32_t(call(0x4c8da0, container, {0, x, y, z, name, 0x40000}));
        uint32_t fault = 0;
        ClawSceneActorCreate args{0, x, y, z, 0, 0x40000};
        uint32_t out = claw_scene_actor_create_named(container, args, name, host(), &fault);
        if (fault)
            fail(fault);
        return out;
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
    }
    static uint32_t hostCall(void *p, ClawSceneActorCall q) {
        auto &r = *static_cast<Run *>(p);
        switch (q.argumentCount) {
        case 0:
            return uint32_t(r.call(q.function, q.receiver));
        case 1:
            return uint32_t(r.call(q.function, q.receiver, {q.arguments[0]}));
        case 2:
            return uint32_t(r.call(q.function, q.receiver, {q.arguments[0], q.arguments[1]}));
        case 3:
            return uint32_t(r.call(q.function, q.receiver, {q.arguments[0], q.arguments[1], q.arguments[2]}));
        default:
            return uint32_t(
                r.call(q.function, q.receiver, {q.arguments[0], q.arguments[1], q.arguments[2], q.arguments[3]}));
        }
    }
    static uint32_t allocate(void *p, uint32_t bytes) {
        auto &r = *static_cast<Run *>(p);
        return r.c.scene.allocate ? r.c.scene.allocate(r.c.scene.context, bytes)
                                  : uint32_t(r.call(0x4f63ec, 0, {bytes}));
    }
    static void release(void *p, uint32_t token) {
        auto &r = *static_cast<Run *>(p);
        if (r.c.scene.free)
            r.c.scene.free(r.c.scene.context, token);
        else
            r.call(0x4f6428, 0, {token});
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, hostCall, nullptr};
    }
    void image(uint32_t actor) {
        if (!c.composeImages) {
            call(0x4c7970, actor, {0x524130});
            return;
        }
        uint32_t registry = get(get(actor + 12) + 16) + 16;
        uint32_t root = uint32_t(call(0x4f6286, registry, {0x524130}));
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
        std::copy_n(span(actor, 128), 128, s.actor);
        if (!claw_actor_bind_default_image(
                &s, &x, "GAME_BULLETS",
                [](ClawActorResourceBindings *, ClawActorBindingContext *p, const ClawActorBindingCall *, void *) {
                    return p->image.token;
                },
                nullptr))
            fail();
        std::copy_n(s.actor, 128, span(actor, 128));
    }
};
uint32_t execute(Run &r, uint32_t f, uint32_t actor, uint32_t p) {
    uint32_t speed = 700, offset = r.get(p + 0x54);
    if (f == 0x41cb80) {
        uint32_t denominator = r.get(p + 0x108) - r.get(p + 0x104);
        if (!denominator)
            denominator = 1;
        int32_t numerator = si((r.get(p + 0x100) - r.get(p + 0x104)) * 200);
        if (numerator == std::numeric_limits<int32_t>::min() && si(denominator) == -1)
            r.fail(2);
        int32_t quotient = numerator / si(denominator);
        speed = uint32_t(std::clamp(quotient, 0, 200));
    }
    if (!r.get(p)) {
        offset = 0u - offset;
        speed = 0u - speed;
    }
    uint32_t x = r.get(actor + 76) + offset, y = r.get(actor + 80) + r.get(p + 0x58),
             z = r.get(actor + 100) + (f == 0x41c9f0 ? 0xffffffffu : 1u), created = 0;
    if (f == 0x41cc60) {
        uint32_t type = r.c.globals->powerup, name = 0, bit = 0, sound = 0;
        if (type == 0x26b8) {
            name = 0x522df4;
            bit = 0x40000;
            sound = 0x5247b0;
        } else if (type == 0x26b9) {
            name = 0x522de4;
            bit = 0x100000;
            sound = 0x5247c0;
        } else if (type == 0x26ba) {
            name = 0x522dd8;
            bit = 0x80000;
            sound = 0x5247d0;
        }
        if (name) {
            created = r.create(actor, x, y, z, name);
            r.put(created + 0x164, r.get(created + 0x164) | bit);
            uint32_t manager = r.get(r.get(actor + 12) + 40);
            if (!r.get(manager + 48)) {
                uint32_t voice = uint32_t(r.call(0x4f6286, manager + 16, {sound}));
                if (voice)
                    r.call(0x4208e0, voice, {r.c.globals->masterVolume, 0, 0, 0});
            }
        }
    } else
        created = r.create(actor, x, y, z, f == 0x41c9f0 ? 0x522dc8 : f == 0x41cab0 ? 0x522e00 : 0x522bec);
    if (!created)
        return 0;
    if (f == 0x41cb80) {
        r.put(p + 120, r.get(p + 120) - 1);
        r.put(created + 0x158, speed);
        r.put(created + 0xd0, 0x20);
        r.put(created + 0xd4, 4);
        r.put(created + 0x104, 15);
        return 1;
    }
    if (f == 0x41cab0 && si(r.get(p + 116)) > 0)
        r.put(p + 116, r.get(p + 116) - 1);
    r.put(created + 0xd0, f == 0x41c9f0 ? 0x20 : 0x2000000);
    r.put(created + 0xd4, 4);
    r.put(created + 0x148, speed);
    r.put(created + 0x14c, 0);
    if (f == 0x41c9f0) {
        r.put(r.get(created + 108) + 0xb8, r.get(p + 0xe8));
        if (si(r.get(p + 112)) > 0)
            r.put(p + 112, r.get(p + 112) - 1);
        r.put(created + 0x104, 8);
        r.image(created);
        return 1;
    }
    r.put(created + 0x164, r.get(created + 0x164) | 8);
    r.put(created + 0x104, 25);
    r.put(r.get(created + 108) + 0xb8, r.get(p + 0xe8));
    if (!r.get(p))
        r.put(created + 64, r.get(created + 64) | 2);
    return 1;
}
} // namespace
extern "C" uint32_t claw_player_ranged_helpers_entry(uint32_t f, const uint32_t *a, uint32_t n,
                                                     ClawPlayerRangedHelpersContext *c,
                                                     ClawPlayerRangedHelpersDependency d, void *u, uint32_t *out) {
    if (f != 0x41c9f0 && f != 0x41cab0 && f != 0x41cb80 && f != 0x41cc60)
        return 0;
    if (!c || !c->globals)
        return 0;
    if (n != 3 || !a) {
        c->fault = 3;
        return 0;
    }
    if (c->fault)
        return 0;
    Run r{*c, d, u};
    try {
        uint32_t value = execute(r, f, a[0], a[2]);
        if (out)
            *out = value;
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
