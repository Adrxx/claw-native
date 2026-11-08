#include "BootyStoryRuntime.h"
#include "PlaneRenderer.h"
#include "ActorResourceBindings.h"
#include "PickupPointsRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
#include <limits>
#include <map>
#include <array>
namespace {
struct Failure {};
bool owned(uint32_t);
uint32_t body(struct Run &, uint32_t, uint32_t, const uint32_t *);
struct Run {
    ClawBootyStoryContext &c;
    ClawBootyStoryDependency d;
    void *u;
    uint32_t steps = 0;
    std::map<uint32_t, std::array<uint32_t, 128>> actors;
    ClawSceneActorGlobals *frame = nullptr;
    Run(ClawBootyStoryContext &v, ClawBootyStoryDependency e, void *w) : c(v), d(e), u(w) {
    }
    void publishFrame() {
        if (!frame)
            return;
        auto *p = raw(0x5430d0);
        *p = (*p & 0xffffff00) | (frame->initializationFlags & 255);
        std::copy_n(frame->deletionArray, 5, raw(0x5430f0, 5));
        std::copy_n(frame->reorderArray, 5, raw(0x5430d8, 5));
        *raw(0x5430c8) = frame->animation.nowMilliseconds;
        *raw(0x5430c4) = frame->animation.deltaMilliseconds;
    }
    uint32_t *raw(uint32_t t, uint32_t n = 1) {
        auto p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failure{};
        }
        return p;
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        for (auto &[b, a] : actors)
            if (t >= b && uint64_t(t) + uint64_t(n) * 4 <= uint64_t(b) + 436)
                return a.data() + (t - b) / 4;
        if (n == 128) {
            auto found = actors.find(t);
            if (found != actors.end())
                return found->second.data();
            auto p = raw(t, 109);
            auto &a = actors[t];
            std::copy_n(p, 109, a.data());
            return a.data();
        }
        return raw(t, n);
    }
    void commit() {
        publishFrame();
        for (auto &[b, a] : actors)
            std::copy_n(a.data(), 109, raw(b, 109));
    }
    void refresh() {
        if (frame) {
            frame->initializationFlags = *raw(0x5430d0) & 255;
            std::copy_n(raw(0x5430f0, 5), 5, frame->deletionArray);
            std::copy_n(raw(0x5430d8, 5), 5, frame->reorderArray);
            frame->animation.nowMilliseconds = *raw(0x5430c8);
            frame->animation.deltaMilliseconds = *raw(0x5430c4);
        }
        for (auto i = actors.begin(); i != actors.end();) {
            auto p = c.scene.lookup ? c.scene.lookup(c.scene.context, i->first, 109) : nullptr;
            if (!p) {
                i = actors.erase(i);
                continue;
            }
            std::copy_n(p, 109, i->second.data());
            ++i;
        }
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    uint32_t call(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, const char *name = nullptr, uint32_t mask = 0,
                  std::initializer_list<void *> buffers = {}, std::initializer_list<uint32_t> sizes = {}) {
        if (!d || n > 40) {
            c.fault = 1;
            throw Failure{};
        }
        ClawBootyStoryCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        q.name = name;
        q.localMask = mask;
        uint32_t i = 0;
        for (auto p : buffers)
            q.buffers[i++] = p;
        q.bufferCount = i;
        i = 0;
        for (auto v : sizes)
            q.bufferBytes[i++] = v;
        commit();
        auto v = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        refresh();
        return v;
    }
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {});
    uint32_t virt(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        if (!t) {
            c.fault = 2;
            throw Failure{};
        }
        return invoke(get(get(t) + slot), t, a);
    }
    uint32_t local(uint32_t f, uint32_t *cell, std::initializer_list<uint32_t> a = {}) {
        uint32_t args[40]{};
        std::copy(a.begin(), a.end(), args);
        return call(f, 0, args, uint32_t(a.size()), nullptr, 256, {cell}, {4});
    }
    uint32_t format(uint32_t *cell, uint32_t fmt, std::initializer_list<uint32_t> extra) {
        uint32_t args[40]{};
        args[1] = fmt;
        std::copy(extra.begin(), extra.end(), args + 2);
        return call(0x4f4f58, 0, args, uint32_t(extra.size() + 2), nullptr, 1, {cell}, {4});
    }
    uint32_t join(uint32_t f, uint32_t *destination, uint32_t *source) {
        uint32_t arg = 0;
        return call(f, 0, &arg, 1, nullptr, 257, {source, destination}, {4, 4});
    }
    uint32_t lookup(uint32_t registry, uint32_t name) {
        uint32_t token = 0, args[2] = {name, 0};
        call(0x4f6286, registry, args, 2, nullptr, 2, {&token}, {4});
        return token;
    }
    uint32_t registry(uint32_t app) {
        return get(get(app + 48) + 40) + 16;
    }
    void post(uint32_t p) {
        invoke(0x546d50, 0, {get(get(get(p + 4) + 4) + 4), 0x111, 0x807c, 0});
    }
    void cursor() {
        while (int32_t(invoke(0x546d54, 0, {0})) >= 0) {
        }
    }
    void timer(uint32_t t) {
        uint32_t delta = get(0x53720c), v = get(t);
        put(t, delta < v ? v - delta : 0);
    }
    void sound(uint32_t name, uint32_t mode = 0) {
        auto app = get(0x5371fc);
        if (!app)
            return;
        auto p = lookup(registry(app), name);
        if (p && get(0x532c0c)) {
            if (mode)
                invoke(0x4b45f0, get(p + 16), {get(0x532c10), 0, 0, 0});
            else
                invoke(0x4b3dc0, get(p + 16), {100, 0, 0, 0});
        }
    }
};
uint32_t *hostLookup(void *u, uint32_t t, uint32_t n) {
    auto &r = *static_cast<Run *>(u);
    try {
        if (++r.steps > (r.c.maximumSteps ? r.c.maximumSteps : 65536)) {
            r.c.fault = 3;
            throw Failure{};
        }
        return r.span(t, n);
    } catch (Failure &) {
        return nullptr;
    }
}
uint32_t hostCall(void *u, ClawSceneActorCall q) {
    auto &r = *static_cast<Run *>(u);
    try {
        r.publishFrame();
        uint32_t args[40]{};
        std::copy_n(q.arguments, q.argumentCount, args);
        if (owned(q.function))
            return body(r, q.function, q.receiver, args);
        return r.call(q.function, q.receiver, args, q.argumentCount);
    } catch (Failure &) {
        return 0;
    }
}
uint32_t hostAlloc(void *u, uint32_t n) {
    auto &r = *static_cast<Run *>(u);
    return r.invoke(0x4f63ec, 0, {n});
}
void hostFree(void *u, uint32_t t) {
    auto &r = *static_cast<Run *>(u);
    r.commit();
    r.actors.erase(t);
    r.invoke(0x4f6428, 0, {t});
}
uint32_t hostClock(void *u) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c.scene.readClock) {
        r.c.fault = 1;
        return 0;
    }
    r.commit();
    auto v = r.c.scene.readClock(r.c.scene.context);
    r.refresh();
    return v;
}
ClawSceneActorHost host(Run &r) {
    return {&r, hostLookup, hostAlloc, hostFree, hostCall, hostClock};
}
uint32_t progressionDependency(ClawBootyProgressionContext *, const ClawBootyProgressionCall *q, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (q->argumentCount > 40) {
        r.c.fault = 3;
        throw Failure{};
    }
    ClawBootyStoryCall e{};
    e.function = q->function;
    e.receiver = q->receiver;
    e.argumentCount = q->argumentCount;
    std::copy_n(q->arguments, e.argumentCount, e.arguments);
    e.name = q->name;
    e.localMask = q->localMask;
    e.bufferCount = q->bufferCount;
    std::copy_n(q->buffers, 3, e.buffers);
    std::copy_n(q->bufferBytes, 3, e.bufferBytes);
    r.commit();
    uint32_t v = r.d(&r.c, &e, r.u);
    r.refresh();
    return v;
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    if (++steps > (c.maximumSteps ? c.maximumSteps : 65536)) {
        c.fault = 3;
        throw Failure{};
    }
    uint32_t args[40]{};
    std::copy(a.begin(), a.end(), args);
    if (owned(f))
        return body(*this, f, t, args);
    if (c.composeFrame && f == 0x4c8fc0) {
        ClawSceneActorGlobals g{};
        g.initializationFlags = get(0x5430d0) & 255;
        std::copy_n(raw(0x5430f0, 5), 5, g.deletionArray);
        std::copy_n(raw(0x5430d8, 5), 5, g.reorderArray);
        g.animation.nowMilliseconds = get(0x5430c8);
        g.animation.deltaMilliseconds = get(0x5430c4);
        frame = &g;
        uint32_t fault = 0;
        try {
            claw_scene_actor_update(t, &g, args[0], host(*this), &fault);
            publishFrame();
        } catch (...) {
            frame = nullptr;
            throw;
        }
        frame = nullptr;
        if (fault || c.fault) {
            if (!c.fault)
                c.fault = fault;
            throw Failure{};
        }
        return 0;
    }
    if (c.composeFrame && f == 0x4c91d0) {
        ClawPlaneRendererHost h{host(*this), nullptr, nullptr};
        uint32_t fault = 0;
        if (!claw_plane_renderer_actor_list(t, args[0], h, &fault)) {
            c.fault = fault ? fault : 1;
            throw Failure{};
        }
        return 0;
    }
    if (c.display) {
        auto x = *c.display;
        x.scene = host(*this);
        x.fault = 0;
        auto bridge = [](ClawSceneDisplayContext *, const ClawSceneDisplayCall *q, void *u) -> uint32_t {
            auto &r = *static_cast<Run *>(u);
            ClawBootyStoryCall e{};
            e.function = q->function;
            e.receiver = q->receiver;
            e.argumentCount = q->argumentCount;
            std::copy_n(q->arguments, e.argumentCount, e.arguments);
            e.localMask = q->localMask;
            e.bufferCount = q->bufferCount;
            for (uint32_t i = 0; i < 2; ++i) {
                e.buffers[i] = q->buffers[i];
                e.bufferBytes[i] = q->bufferBytes[i];
            }
            if (!e.localMask && owned(e.function))
                return body(r, e.function, e.receiver, e.arguments);
            r.commit();
            auto v = r.d(&r.c, &e, r.u);
            r.refresh();
            return v;
        };
        uint32_t out = 0;
        if (claw_scene_display_entry(f, t, args, uint32_t(a.size()), &x, bridge, this, &out)) {
            if (x.fault) {
                c.fault = x.fault;
                throw Failure{};
            }
            return out;
        }
        if (x.fault) {
            c.fault = x.fault;
            throw Failure{};
        }
    }
    if (c.results) {
        auto x = *c.results;
        x.scene = host(*this);
        x.fault = 0;
        auto bridge = [](ClawBootyResultsContext *, const ClawBootyResultsCall *q, void *u) -> uint32_t {
            auto &r = *static_cast<Run *>(u);
            if (q->argumentCount > 40) {
                r.c.fault = 3;
                throw Failure{};
            }
            ClawBootyStoryCall e{};
            e.function = q->function;
            e.receiver = q->receiver;
            e.argumentCount = q->argumentCount;
            std::copy_n(q->arguments, e.argumentCount, e.arguments);
            e.name = q->name;
            e.localMask = q->localMask;
            e.bufferCount = q->bufferCount;
            std::copy_n(q->buffers, 3, e.buffers);
            std::copy_n(q->bufferBytes, 3, e.bufferBytes);
            if (!e.localMask && owned(e.function))
                return body(r, e.function, e.receiver, e.arguments);
            r.commit();
            auto v = r.d(&r.c, &e, r.u);
            r.refresh();
            return v;
        };
        uint32_t out = 0;
        if (claw_booty_results_entry(f, t, args, uint32_t(a.size()), &x, bridge, this, &out)) {
            if (x.fault) {
                c.fault = x.fault;
                throw Failure{};
            }
            return out;
        }
        if (x.fault) {
            c.fault = x.fault;
            throw Failure{};
        }
    }
    if (c.composeImages && f == 0x4c7900) {
        auto registry = get(get(t + 12) + 16) + 16, root = lookup(registry, args[0]);
        uint32_t selected = 0;
        ClawActorBindingContext b{};
        b.imageRegistryToken = registry;
        b.image.token = root;
        if (root) {
            b.image.minimum = int32_t(get(root + 100));
            b.image.maximum = int32_t(get(root + 104));
            ClawPickupPointsContext p{};
            p.scene = host(*this);
            uint32_t index = args[1];
            if (!claw_pickup_points_entry(0x40f680, root, &index, 1, &p, nullptr, nullptr, &selected) || p.fault) {
                c.fault = p.fault ? p.fault : 1;
                throw Failure{};
            }
            b.image.firstImageIndex = int32_t(index);
            b.image.images = &selected;
            b.image.imageCount = 1;
        }
        ClawActorResourceBindings s{};
        std::copy_n(span(t, 109), 109, s.actor);
        auto resolved = [](ClawActorResourceBindings *, ClawActorBindingContext *b, const ClawActorBindingCall *,
                           void *) {
            return b->image.token;
        };
        if (!claw_actor_bind_indexed_image(&s, &b, "", int32_t(args[1]), resolved, nullptr)) {
            c.fault = 3;
            throw Failure{};
        }
        std::copy_n(s.actor, 109, span(t, 109));
        return 1;
    }
    if (c.composeAnimation) {
        if (f == 0x4c79e0 || f == 0x4c7a40 || f == 0x420a10)
            span(t, 128);
        else if (f == 0x4c8210 || f == 0x4c8220 || f == 0x4c8260 || f == 0x4c82a0 || f == 0x420970) {
            auto owner = get(t + 4);
            if (owner && t == owner + 0x188)
                span(owner, 128);
        }
        ClawActorAnimationGlobals g{get(0x5430c4), get(0x532c10)};
        uint32_t out = 0, fault = 0;
        if (claw_actor_animation_entry(f, t, args[0], args[1], &g, host(*this), &fault, &out)) {
            if (fault) {
                c.fault = fault;
                throw Failure{};
            }
            return out;
        }
    }
    if (c.composeCreation && f == 0x4c8da0) {
        ClawSceneActorCreate q{args[0], args[1], args[2], args[3], 0, args[5]};
        uint32_t fault = 0;
        auto out = claw_scene_actor_create_named(t, q, args[4], host(*this), &fault);
        if (fault) {
            c.fault = fault;
            throw Failure{};
        }
        return out;
    }
    if (c.composeProgression) {
        if (!c.progression) {
            c.fault = 1;
            throw Failure{};
        }
        auto p = *c.progression;
        p.scene = host(*this);
        p.fault = 0;
        uint32_t out = 0;
        if ((f == 0x48f0d0 || f == 0x40b5c0) && p.base) {
            auto b = *p.base;
            b.host = host(*this);
            b.fault = 0;
            auto bridge = [](ClawSinglePlayerSceneContext *, ClawSinglePlayerSceneCall q, void *u) -> uint32_t {
                auto &r = *static_cast<Run *>(u);
                ClawBootyStoryCall e{};
                e.function = q.function;
                e.receiver = q.receiver;
                e.argumentCount = q.argumentCount;
                std::copy_n(q.arguments, q.argumentCount, e.arguments);
                e.localMask = q.localMask;
                e.bufferCount = q.bufferCount;
                std::copy_n(q.buffers, 3, e.buffers);
                std::copy_n(q.bufferBytes, 3, e.bufferBytes);
                if (!e.localMask && owned(e.function))
                    return body(r, e.function, e.receiver, e.arguments);
                r.commit();
                auto v = r.d(&r.c, &e, r.u);
                r.refresh();
                return v;
            };
            if (claw_single_player_scene_entry(f, t, args, uint32_t(a.size()), &b, bridge, this, &out)) {
                if (b.fault) {
                    c.fault = b.fault;
                    throw Failure{};
                }
                return out;
            }
        }
        if (claw_booty_progression_entry(f, t, args, uint32_t(a.size()), &p, progressionDependency, this, &out)) {
            if (p.fault) {
                c.fault = p.fault;
                throw Failure{};
            }
            return out;
        }
    }
    return call(f, t, args, uint32_t(a.size()));
}
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
double divv(double a, double b) {
    volatile double v = a / b;
    return v;
}
uint32_t ftol(double v) {
    if (!std::isfinite(v) || v >= 9223372036854775808.0 || v < -9223372036854775808.0)
        return 0;
    return uint32_t(int64_t(v));
}
float floatWord(uint32_t w) {
    float v;
    std::memcpy(&v, &w, 4);
    return v;
}
uint32_t wordFloat(double v) {
    float f = float(v);
    uint32_t w;
    std::memcpy(&w, &f, 4);
    return w;
}
const uint32_t piecePositions[24] = {0xffffff9c, 0xffffff10, 740,        0xffffff10, 0xffffff9c, 0xffffff06,
                                     740,        0xffffff06, 0xffffff9c, 0xffffff10, 0xffffff9c, 640,
                                     560,        385,        109,        316,        275,        222,
                                     316,        363,        502,        293,        483,        112};
const uint32_t amuletPositions[18] = {364, 162, 239, 342, 353, 364, 214, 262, 275,
                                      163, 398, 341, 284, 368, 423, 263, 320, 249};
static const uint32_t mapPath[300] = {
    0xe1,       0x3d,       0xd4,       0x45,       0xc5,       0x47,       0xb5,       0x46,       0xa6,
    0x43,       0x96,       0x43,       0x88,       0x47,       0x79,       0x49,       0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0x24,       0x67,       0x1e,
    0x73,       0x1e,       0x81,       0x24,       0x8d,       0x2b,       0x99,       0x31,       0xa5,
    0x31,       0xb3,       0x2f,       0xc1,       0x2c,       0xcf,       0x30,       0xdc,       0x39,
    0xe7,       0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0x77,       0xe4,       0x85,       0xe3,       0x91,       0xea,
    0x98,       0xf6,       0x9a,       0x104,      0xa1,       0x110,      0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xe0,       0x12d,      0xd6,       0x138,      0xce,       0x144,      0xc4,       0x14f,      0xba,
    0x15a,      0xae,       0x164,      0xa1,       0x16d,      0x98,       0x17b,      0x97,       0x18a,
    0x9b,       0x198,      0xa3,       0x1a4,      0xad,       0x1af,      0xba,       0x1b9,      0xc9,
    0x1bf,      0xda,       0x1bf,      0xe8,       0x1b6,      0xf8,       0x1b2,      0x108,      0x1b1,
    0x119,      0x1b0,      0x12a,      0x1ad,      0x13a,      0x1aa,      0x14b,      0x1a6,      0x15c,
    0x1a2,      0x16a,      0x198,      0x176,      0x18c,      0x17b,      0x17e,      0x179,      0x16f,
    0x172,      0x162,      0x168,      0x159,      0x15e,      0x150,      0x16f,      0x132,      0x17c,
    0x134,      0x186,      0x12c,      0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff, 0xffffffff};
uint32_t body(Run &r, uint32_t f, uint32_t p, const uint32_t *a) {
    switch (f) {
    case 0x40b860: {
        if (!r.invoke(0x48f0d0, p, {a[0], a[1], a[2]}))
            return 0;
        r.put(0x5349a0, 0);
        for (auto off : {0x158u, 0x160u, 0x164u, 0x154u})
            r.put(p + off, 0);
        r.put(0x523b50, 0xffffffff);
        r.put(p + 32, r.invoke(0x4b7f20, r.get(p + 8), {0x523b1c}));
        if (!r.get(p + 32))
            return 0;
        r.put(p + 36, r.invoke(0x4b7f20, r.get(p + 8), {0x523734}));
        if (!r.get(p + 36))
            return 0;
        auto images = r.invoke(0x4b7cd0, r.get(p + 32), {0x523ce0});
        if (!images)
            return 0;
        r.virt(r.get(r.get(p + 12) + 16), 72, {images, 0x523b14, 0x523728});
        auto ani = r.invoke(0x4b7cd0, r.get(p + 32), {0x523cd8});
        if (!ani)
            return 0;
        r.invoke(0x4ce0d0, r.get(r.get(p + 12) + 44), {ani, 0x523b14, 0x523728});
        auto level = r.get(p + 20);
        if (int32_t(level) <= 0 || int32_t(level) >= 15)
            return 0;
        uint32_t formatted = 0, logicName = 0, imageName = 0;
        r.local(0x4f6439, &formatted);
        r.format(&formatted, 0x523cc8, {int32_t(level) < 10 ? 0x523cd4u : 0x523cd0u, level});
        if (level & 1) {
            r.put(0x5349a0, 1);
            if (int32_t(level) > 11)
                r.put(0x5349a0, 0);
        }
        r.local(0x4f65f2, &logicName, {0x5224b8});
        if (!r.get(0x5349a0))
            r.local(0x4f66cc, &logicName, {0x5224a8});
        auto container = r.get(r.get(p + 12) + 8);
        auto name = r.local(0x4f6974, &logicName, {1});
        auto actor = r.invoke(0x4c8da0, container, {0, 0, 0, 9999, name, 0});
        r.put(p + 0x160, actor);
        r.local(0x4f65f2, &imageName, {0x523cb0});
        r.join(0x4f695c, &imageName, &formatted);
        if (level == 13) {
            r.local(0x4f6920, &imageName, {0x523ca4});
            r.invoke(0x4c7900, r.get(p + 0x160), {imageName, 1});
            r.invoke(0x4c79e0, r.get(p + 0x160), {0x523c94, 0});
        } else {
            r.invoke(0x4c7900, r.get(p + 0x160), {imageName, 1});
            if (!r.get(0x5349a0)) {
                uint32_t name2 = 0;
                r.local(0x4f6439, &name2);
                r.format(&name2, 0x523c88, {level});
                r.invoke(0x4c79e0, r.get(p + 0x160), {name2, 0});
                r.local(0x4f6584, &name2);
            }
        }
        if (!r.get(p + 0x160)) {
            r.c.fault = 2;
            throw Failure{};
        }
        auto logic = r.get(r.get(p + 0x160) + 108);
        r.put(logic + 100, 1);
        r.put(logic + 104, level);
        r.put(logic + 308, 5000);
        if (level == 14)
            r.put(logic + 104, 17);
        if (r.get(0x5349a0) && level != 1) {
            r.put(logic + 100, 0);
            r.put(logic + 308, 2000);
            auto progress =
                r.invoke(0x4c8da0, r.get(r.get(p + 12) + 8), {0, 0xffffffce, 0xffffffce, 9998, 0x522494, 0});
            r.put(p + 0x164, progress);
            r.invoke(0x4c7900, progress, {0x523c78, 1});
            if (!progress) {
                r.c.fault = 2;
                throw Failure{};
            }
            auto pl = r.get(r.get(p + 0x164) + 108);
            if (pl) {
                r.put(pl + 100, level);
                r.put(pl + 360, logic);
                r.put(pl + 308, 5000);
            }
        }
        auto doubled = level + level - 1;
        r.format(&formatted, 0x523cc8, {int32_t(doubled) < 10 ? 0x523cd4u : 0x523cd0u, doubled});
        uint32_t arg = 0;
        r.call(0x4f667d, p + 0x15c, &arg, 1, nullptr, 1, {&formatted}, {4});
        r.invoke(0x4f6920, p + 0x15c, {r.get(0x5349a0) ? 0x523c74u : 0x523c6cu});
        const uint32_t voices[14] = {0x523c58, 0x523c44, 0x523c30, 0x523c1c, 0x523c08, 0x523bf4, 0x523be0,
                                     0x523bcc, 0x523bb8, 0x523ba4, 0x523b90, 0x523b7c, 0x523b68, 0x523b54};
        r.invoke(0x4f66cc, p + 0x168, {voices[level - 1]});
        r.cursor();
        r.local(0x4f6584, &imageName);
        r.local(0x4f6584, &logicName);
        r.local(0x4f6584, &formatted);
        return 1;
    }
    case 0x40bf80:
        r.invoke(0x48ffa0, p, {r.get(p + 0x15c), 1, 0, 1});
        {
            auto holder = r.get(r.get(p + 12) + 4);
            r.invoke(0x4ca9e0, holder, {r.get(holder + 20)});
            r.invoke(0x4caa90, r.get(r.get(p + 12) + 4));
            r.invoke(0x4caa20, r.get(r.get(p + 12) + 4), {1});
        }
        return 1;
    case 0x40bca0: {
        auto result = r.invoke(0x40bf80, p);
        r.invoke(0x4f66cc, 0x53499c, {r.get(0x5349a0) ? 0x523cf8u : 0x523ce8u});
        auto token = r.lookup(r.registry(r.get(p + 4)), r.get(0x53499c));
        if (token) {
            if (r.get(0x5349a0)) {
                if (r.get(0x532c0c))
                    r.invoke(0x4b3dc0, r.get(token + 16), {25, 0, 0, 1});
                r.invoke(0x4b3fe0, r.get(token + 16), {80, 750, 0});
                return result;
            }
            if (r.get(0x532c0c))
                r.invoke(0x4b3dc0, r.get(token + 16), {100, 0, 0, 0});
        }
        return result;
    }
    case 0x40bfd0: {
        if (r.get(0x523b50))
            return 0;
        uint32_t name = 0;
        r.local(0x4f65f2, &name, {0x523d28});
        if (r.get(p + 20) == 14)
            r.local(0x4f66cc, &name, {0x523d18});
        if (r.get(0x5349a0))
            r.local(0x4f66cc, &name, {0x523d08});
        auto token = r.lookup(r.registry(r.get(0x5371fc)), name);
        bool waiting = false;
        if (token && r.invoke(0x4b3e70, r.get(token + 16)))
            waiting = true;
        else {
            token = r.lookup(r.registry(r.get(p + 4)), r.get(p + 0x168));
            if (token) {
                if (r.invoke(0x4b3e70, r.get(token + 16)))
                    waiting = true;
                else if (!r.get(p + 0x154)) {
                    if (r.get(0x532c0c))
                        r.invoke(0x4b3dc0, r.get(token + 16), {100, 0, 0, 0});
                    r.put(p + 0x154, 1);
                    r.put(0x523b50, 1);
                } else if (!r.get(0x5349a0)) {
                    token = r.lookup(r.registry(r.get(p + 4)), r.get(0x53499c));
                    if (token && r.invoke(0x4b3e70, r.get(token + 16)))
                        waiting = true;
                }
            }
        }
        if (waiting)
            r.put(0x523b50, 1);
        r.local(0x4f6584, &name);
        return 0;
    }
    case 0x40bd60:
        if (r.get(0x523b50) != 0xffffffff)
            r.timer(0x523b50);
        r.invoke(0x40bfd0, p);
        r.invoke(0x4b3490, r.get(0x537200));
        if (((r.get(r.get(0x537200) + 0x210) & 0xffffff) || !r.get(0x523b50)) && !r.get(p + 0x158)) {
            r.put(p + 0x158, 1);
            r.post(p);
        }
        r.virt(r.get(r.get(p + 12) + 8), 36, {1});
        {
            auto scene = r.get(p + 12), holder = r.get(scene + 4);
            r.virt(r.get(scene + 12), 52, {r.get(holder + 20), r.get(holder + 24)});
        }
        r.virt(r.get(r.get(p + 12) + 8), 40, {r.get(r.get(r.get(p + 12) + 4) + 20)});
        {
            auto holder = r.get(r.get(p + 12) + 4);
            r.invoke(0x4b98b0, r.get(r.get(holder + 16) + 44), {0});
            auto presentation = r.get(holder + 24);
            r.invoke(0x4b9d80, r.get(r.get(holder + 20) + 44), {0, 0, r.get(presentation + 44), presentation + 28, 16});
        }
        return 1;
    case 0x40be60:
        if (!r.invoke(0x4ca930, r.get(r.get(p + 12) + 4)))
            return 0;
        {
            auto result = r.invoke(0x40bf80, p);
            auto images = r.invoke(0x4b7cd0, r.get(p + 32), {0x523ce0});
            if (!images)
                return 0;
            if (r.virt(r.get(r.get(p + 12) + 16), 76, {images, 0x523b14, 0x523728}) == 0xffffffff)
                return 0;
            r.cursor();
            return result;
        }
    case 0x40bed0:
        if (!r.virt(p, 12))
            return 0;
        if (!r.get(p + 44))
            return 0;
        {
            auto result = r.invoke(0x40bf80, p);
            r.cursor();
            return r.invoke(0x48f470, p, {250}) ? result : 0;
        }
    case 0x40bd50:
        return 1;
    case 0x40bf30:
        if ((a[0] == 27 || a[0] == 32 || a[0] == 13) && !r.get(p + 0x158)) {
            r.put(p + 0x158, 1);
            r.post(p);
        }
        return 1;
    case 0x40bc80:
        r.invoke(0x4c89e0, r.get(r.get(p + 12) + 8));
        r.invoke(0x48f180, p);
        return 0;
    case 0x40b620:
        r.put(p, 0x50b544);
        r.invoke(0x40bc80, p);
        r.invoke(0x4f6584, p + 0x168);
        r.invoke(0x4f6584, p + 0x15c);
        r.put(p, 0x50b4ec);
        r.invoke(0x48f180, p);
        return 0;
    case 0x40b600:
        r.invoke(0x40b620, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x4ca900: {
        auto selected = r.get(p + (a[1] == 2 ? 24 : 20));
        if (!selected)
            return 0;
        return r.virt(selected, 48, {a[0]});
    }
    case 0x4d4190: {
        auto kind = r.invoke(0x4b61b0, a[0]);
        uint32_t mode = 0;
        if (kind == 0x424d50)
            mode = 1;
        else if (kind == 0x504358)
            mode = 2;
        else if (kind == 0x504944)
            mode = 4;
        else if (kind == 0x524944)
            mode = 3;
        else
            return 0;
        auto data = r.invoke(0x4b61c0, a[0]);
        if (!data)
            return 0;
        auto result = r.invoke(0x4b95b0, r.get(p + 44), {r.get(r.get(p + 12) + 28), data, mode, r.get(a[0] + 20), 0});
        r.invoke(0x4b6230, a[0]);
        return result;
    }
    case 0x4b95b0: {
        if (!a[3])
            return 0;
        uint32_t value = 0;
        if (a[2] == 1)
            value = r.invoke(0x4bdda0, p, {a[0], a[1], a[3]});
        else if (a[2] == 2)
            value = r.invoke(0x4bebc0, p, {a[0], a[1], a[3]});
        else if (a[2] == 4)
            value = r.invoke(0x4bf680, p, {a[0], a[1], a[3], a[4]});
        else
            return 0;
        return value ? 1u : 0u;
    }
    case 0x4ca9e0: {
        auto image = r.get(p + 16);
        if (!image)
            return 0;
        auto target = r.get(image + 44);
        if (!target)
            return 0;
        auto surface = r.get(a[0] + 44);
        if (!surface)
            return 0;
        return r.invoke(0x4b9c50, surface, {target}) == 0;
    }
    case 0x4caa90:
        if (r.get(p + 24))
            r.virt(r.get(p + 24), 28);
        return 0;
    case 0x4caa20:
        if (r.virt(r.get(p + 24), 20))
            return 0;
        {
            auto source = r.get(p + 20);
            if (!r.virt(r.get(p + 24), 36, {r.get(source + 16), r.get(source + 20)}))
                return 0;
            if (a[0]) {
                source = r.get(p + 20);
                r.invoke(0x4b9d80, r.get(r.get(p + 24) + 44), {0, 0, r.get(source + 44), source + 28, 16});
            }
            return 1;
        }
    case 0x40c150: {
        p = a[0];
        auto l = r.get(p + 108), s = r.get(l + 28);
        if (s < 6) {
            if (s == 0) {
                r.put(l + 28, 5);
                auto index = int32_t(r.get(l + 104) + 1) / 2 - 1;
                r.put(l + 148, uint32_t(index));
                if (index < 0 || index > 5) {
                    r.c.fault = 2;
                    throw Failure{};
                }
                r.put(p + 76, piecePositions[index * 2]);
                r.put(p + 80, piecePositions[index * 2 + 1]);
            } else if (s == 5) {
                r.timer(l + 308);
                if (!r.get(l + 308) && r.get(l + 100))
                    r.put(l + 28, 0x2330);
            }
            return 1;
        }
        if (s == 0x2330) {
            auto index = int32_t(r.get(l + 148));
            r.put(l + 304, 2000);
            if (index < 0 || index > 5) {
                r.c.fault = 2;
                throw Failure{};
            }
            auto x = piecePositions[index * 2], y = piecePositions[index * 2 + 1], xx = piecePositions[index * 2 + 12],
                 yy = piecePositions[index * 2 + 13];
            r.put(l + 48, xx);
            r.put(l + 44, x);
            r.put(l + 56, yy);
            r.put(l + 52, y);
            double dx = double(int32_t(xx - x));
            r.put(l + 352, wordFloat(mul(mul(dx, 1000.0), 0.0005)));
            r.put(l + 320, wordFloat(divv(double(int32_t(yy - y)), dx)));
            r.sound(0x523d34);
            r.put(l + 28, 0x2331);
            return 1;
        }
        if (s != 0x2331)
            return 1;
        r.timer(l + 304);
        double step = mul(mul(double(r.get(0x53720c)), double(floatWord(r.get(l + 352)))), 0.001);
        auto x = r.get(p + 76), target = r.get(l + 48);
        bool done = false;
        if (step > 0) {
            if (int32_t(x) < int32_t(target)) {
                x += ftol(step);
                r.put(p + 76, x);
                if (int32_t(x) >= int32_t(r.get(l + 48))) {
                    r.put(p + 76, r.get(l + 48));
                    done = true;
                }
            } else
                done = true;
        } else {
            if (int32_t(x) > int32_t(target)) {
                x += ftol(step);
                r.put(p + 76, x);
                if (int32_t(x) <= int32_t(r.get(l + 48))) {
                    r.put(p + 76, r.get(l + 48));
                    done = true;
                }
            } else
                done = true;
        }
        r.put(p + 80, ftol(mul(double(int32_t(r.get(p + 76) - r.get(l + 44))), double(floatWord(r.get(l + 320))))) +
                          r.get(l + 52));
        if (!done)
            return 1;
        r.put(p + 76, r.get(l + 48));
        r.put(p + 80, r.get(l + 56));
        if (r.get(0x523b50) == 0xffffffff)
            r.put(0x523b50, 0);
        auto app = r.get(0x5371fc);
        if (app) {
            auto token = r.lookup(r.registry(app), 0x523d34);
            if (token && r.invoke(0x4b3e70, r.get(token + 16)))
                r.invoke(0x4b3e30, r.get(token + 16));
            token = r.lookup(r.registry(r.get(0x5371fc)), 0x523d08);
            if (token && r.get(0x532c0c))
                r.invoke(0x4b3dc0, r.get(token + 16), {100, 0, 0, 0});
        }
        r.put(l + 28, 0x232f);
        return 1;
    }
    case 0x40d1a0: {
        p = a[0];
        auto l = r.get(p + 108), s = r.get(l + 28);
        if (!s) {
            r.put(p + 64, r.get(p + 64) | 1);
            r.put(l + 164, 0);
            int index = int32_t(r.get(l + 104) + 1) / 2 - 1;
            if (index < 0 || index > 8) {
                r.put(l + 28, 0x232f);
                return 0;
            }
            r.put(p + 76, amuletPositions[index * 2]);
            r.put(p + 80, amuletPositions[index * 2 + 1]);
            r.put(l + 28, 5);
            return 1;
        }
        if (s != 5)
            return 1;
        r.timer(l + 308);
        if (r.get(l + 308))
            return 1;
        r.put(p + 64, r.get(p + 64) & ~1u);
        r.invoke(0x4c82a0, p + 0x188, {r.get(0x5430c4)});
        uint32_t name = 0;
        r.local(0x4f65f2, &name, {0x523d28});
        if (r.get(l + 104) == 17)
            r.local(0x4f66cc, &name, {0x523d18});
        auto token = r.lookup(r.registry(r.get(0x5371fc)), name);
        uint32_t busy = 0;
        if (!r.get(l + 164) && token) {
            if (!r.invoke(0x4b3e70, r.get(token + 16))) {
                if (r.get(0x532c0c))
                    r.invoke(0x4b3dc0, r.get(token + 16), {100, 0, 0, 0});
                r.put(l + 164, 1);
            }
            busy = r.invoke(0x4b3e70, r.get(token + 16));
        } else if (token && r.get(l + 164))
            busy = r.invoke(0x4b3e70, r.get(token + 16));
        if (r.get(p + 420) && !r.get(p + 412) && !busy) {
            if (r.get(l + 104) == 13) {
                auto app = r.get(0x5371fc), child = r.invoke(0x4c8da0, r.get(r.get(app + 48) + 8),
                                                             {0, 0xffffff9c, 0xffffff9c, 9999, 0x5224a8, 0});
                r.put(child + 64, r.get(child + 64) | 1);
                r.invoke(0x4c7900, child, {0x523d6c, 1});
                r.invoke(0x4c79e0, child, {0x523d5c, 0});
                auto logic = r.get(child + 108);
                r.put(logic + 104, 15);
                r.put(logic + 308, 2000);
            } else
                r.put(0x523b50, 0);
            r.put(l + 28, 0x232f);
        }
        r.local(0x4f6584, &name);
        return 1;
    }
    case 0x40c4f0: {
        p = a[0];
        auto l = r.get(p + 108), s = r.get(l + 28);
        if (s < 0x232c) {
            if (s == 0x232b) {
                r.put(l + 304, 400);
                r.put(p + 64, r.get(p + 64) | 1);
                r.put(l + 28, 0x232c);
            } else if (!s) {
                r.timer(l + 308);
                if (!r.get(l + 308))
                    r.put(l + 28, 0x2332);
            }
            return 1;
        }
        switch (s) {
        case 0x232c:
            r.timer(l + 304);
            if (r.get(l + 304))
                break;
            if (r.get(0x5371fc)) {
                uint32_t name = 0;
                r.local(0x4f65f2, &name, {r.get(0x5349a4) & 1 ? 0x523d50u : 0x523d44u});
                auto registry = r.get(r.get(r.get(0x5371fc) + 48) + 40);
                if (!r.get(registry + 48)) {
                    auto token = r.lookup(registry + 16, name);
                    if (token && r.get(0x532c0c))
                        r.invoke(0x4b45f0, r.get(token + 16), {r.get(0x532c10), 0, 0, 0});
                }
                r.local(0x4f6584, &name);
            }
            r.put(p + 64, r.get(p + 64) & ~1u);
            r.put(l + 28, 0x232f);
            r.put(0x5349a4, r.get(0x5349a4) + 1);
            if (r.get(0x5349a4) == 30) {
                r.put(l + 28, 0x232d);
                break;
            }
            {
                auto child = r.invoke(0x4c8da0, r.get(r.get(r.get(0x5371fc) + 48) + 8),
                                      {0, 0xffffffce, 0xffffffce, 9998, 0x522494, 0});
                if (child)
                    r.invoke(0x4c7900, child, {0x523c78, 1});
                if (!child) {
                    r.c.fault = 2;
                    throw Failure{};
                }
                auto nl = r.get(child + 108);
                if (nl) {
                    r.put(nl + 100, r.get(l + 100));
                    r.put(nl + 360, r.get(l + 360));
                    r.put(nl + 308, 0);
                }
            }
            break;
        case 0x232d:
            r.put(0x5349a4, 0);
            r.put(l + 304, 300);
            r.put(l + 28, 0x232e);
            break;
        case 0x232e:
            r.timer(l + 304);
            if (!r.get(l + 304) && r.get(l + 360)) {
                r.put(r.get(l + 360) + 100, 1);
                r.put(l + 28, 0x232f);
            }
            break;
        case 0x2332: {
            r.put(p + 64, r.get(p + 64) | 1);
            r.put(l + 28, 0x232b);
            int level = int32_t(r.get(l + 100) + 1) / 2;
            if (level - 1 < 1) {
                r.put(p + 8, r.get(p + 8) | 0x10000);
                break;
            }
            level -= 2;
            auto i = int32_t(r.get(0x5349a4));
            if (level < 0 || level > 4 || i < 0 || i > 29) {
                r.put(l + 28, 0x232f);
                break;
            }
            auto at = (i + level * 30) * 2;
            auto x = mapPath[at], y = mapPath[at + 1];
            if (x != 0xffffffff && y != 0xffffffff) {
                r.put(p + 76, x);
                r.put(p + 80, y);
            } else
                r.put(l + 28, 0x232d);
            break;
        }
        default:
            break;
        }
        return 1;
    }
    default:
        r.c.fault = 3;
        throw Failure{};
    }
}
bool owned(uint32_t f) {
    switch (f) {
    case 0x4ca900:
    case 0x4d4190:
    case 0x4b95b0:
    case 0x4ca9e0:
    case 0x4caa90:
    case 0x4caa20:
    case 0x40b860:
    case 0x40bf80:
    case 0x40bca0:
    case 0x40bfd0:
    case 0x40bd60:
    case 0x40be60:
    case 0x40bed0:
    case 0x40bd50:
    case 0x40bf30:
    case 0x40bc80:
    case 0x40b620:
    case 0x40b600:
    case 0x40c150:
    case 0x40d1a0:
    case 0x40c4f0:
        return true;
    default:
        return false;
    }
}
} // namespace
extern "C" uint32_t claw_booty_story_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                           ClawBootyStoryContext *c, ClawBootyStoryDependency d, void *u,
                                           uint32_t *out) {
    if (!c || !owned(f))
        return 0;
    uint32_t need = f == 0x4b95b0   ? 5
                    : f == 0x4d4190 ? 1
                    : f == 0x4ca900 ? 2
                    : f == 0x40b860 ? 3
                    : f == 0x40bf30 ? 2
                    : f == 0x4ca9e0 || f == 0x4caa20 || f == 0x40bca0 || f == 0x40bd50 || f == 0x40b600 ||
                            f == 0x40c150 || f == 0x40d1a0 || f == 0x40c4f0
                        ? 1
                        : 0;
    if (n != need || (n && !a) || ((f == 0x40c150 || f == 0x40d1a0 || f == 0x40c4f0) && t)) {
        c->fault = 3;
        return 0;
    }
    uint32_t args[40]{};
    if (n)
        std::copy_n(a, n, args);
    if (c->fault)
        return 0;
    Run r{*c, d, u};
    try {
        auto v = body(r, f, t, args);
        r.commit();
        if (out)
            *out = v;
        return !c->fault;
    } catch (Failure &) {
        r.frame = nullptr;
        try {
            r.commit();
        } catch (Failure &) {
        }
        return 0;
    }
}
