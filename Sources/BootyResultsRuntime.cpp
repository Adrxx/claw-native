#include "BootyResultsRuntime.h"
#include "ActorResourceBindings.h"
#include "ActorWrapperRuntime.h"
#include "ActorDestruction.h"
#include "PickupPointsRuntime.h"
#include "StackedActorLifecycleRuntime.h"
#include <algorithm>
#include <cstring>
#include <cstdio>
#include <cmath>
#include <initializer_list>
extern "C" int claw_simple_animation_step_v10(uint32_t *, uint32_t *, uint32_t *, uint32_t, uint32_t, uint32_t *,
                                              uint32_t *, uint32_t *);
namespace {
struct Failure {};
int32_t si(uint32_t v) {
    int32_t s;
    std::memcpy(&s, &v, 4);
    return s;
}
uint32_t ftol(double v) {
    if (!std::isfinite(v) || v >= 0x1p63 || v < -0x1p63)
        return 0;
    return uint32_t(int64_t(v));
}
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
double div(double a, double b) {
    volatile double v = a / b;
    return v;
}
bool owned(uint32_t);
struct Run {
    ClawBootyResultsContext &c;
    ClawBootyResultsDependency d;
    void *u;
    uint32_t steps = 0;
    [[noreturn]] void fail(uint32_t n = 1) {
        if (!c.fault)
            c.fault = n;
        throw Failure{};
    }
    void step() {
        if (++steps > (c.maximumSteps ? c.maximumSteps : 1000000))
            fail(3);
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (t < 4096)
            fail(2);
        if (c.fault)
            throw Failure{};
        auto p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
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
    float single(uint32_t t) {
        float v;
        std::memcpy(&v, span(t), 4);
        return v;
    }
    void single(uint32_t t, double v) {
        float f = float(v);
        std::memcpy(span(t), &f, 4);
    }
    const char *text(uint32_t t) {
        return reinterpret_cast<const char *>(span(t & ~3)) + (t & 3);
    }
    uint32_t event(ClawBootyResultsCall &q) {
        if (!d)
            fail();
        auto v = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        return v;
    }
    uint32_t call(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        ClawBootyResultsCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        if (n > 40)
            fail(3);
        std::copy_n(a, n, q.arguments);
        if (n && ((f == 0x4f6286) || (f == 0x4c7970) || (f == 0x4c7900) || (f == 0x4c79e0) || (f == 0x4b7f20) ||
                  (f == 0x4b7cd0) || (f == 0x4f65f2) || (f == 0x4f66cc) || (f == 0x4f6920)))
            q.name = text(a[0]);
        return event(q);
    }
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t> = {});
    uint32_t virt(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        if (!t)
            fail(2);
        uint32_t v = get(t), f = claw_booty_results_function(v, slot);
        if (!f)
            f = get(v + slot);
        return invoke(f, t, a);
    }
    uint32_t primary(uint32_t a) {
        return get(a + 108);
    }
    uint32_t container() {
        return get(get(get(0x5371fc) + 48) + 8);
    }
    uint32_t create(uint32_t parent, uint32_t x, uint32_t y, uint32_t z, uint32_t name) {
        return invoke(0x4c8da0, parent, {0, x, y, z, name, 0});
    }
    uint32_t allocate(uint32_t n) {
        return invoke(0x4f63ec, 0, {n});
    }
    uint32_t dataString(uint32_t f, uint32_t *cell, std::initializer_list<uint32_t> a = {}) {
        ClawBootyResultsCall q{};
        q.function = f;
        q.receiver = 0;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        q.localMask = 256;
        q.bufferCount = 1;
        q.buffers[0] = cell;
        q.bufferBytes[0] = 4;
        if (a.size())
            q.name = text(*a.begin());
        return event(q);
    }
    void formatString(uint32_t *cell, uint32_t fmt, std::initializer_list<uint32_t> a) {
        ClawBootyResultsCall q{};
        q.function = 0x4f4f58;
        q.argumentCount = uint32_t(a.size()) + 2;
        q.arguments[0] = 0;
        q.arguments[1] = fmt;
        std::copy(a.begin(), a.end(), q.arguments + 2);
        q.localMask = 1;
        q.bufferCount = 1;
        q.buffers[0] = cell;
        q.bufferBytes[0] = 4;
        q.name = text(fmt);
        event(q);
    }
    void assignString(uint32_t receiver, uint32_t *cell) {
        ClawBootyResultsCall q{};
        q.function = 0x4f667d;
        q.receiver = receiver;
        q.argumentCount = 1;
        q.localMask = 1;
        q.bufferCount = 1;
        q.buffers[0] = cell;
        q.bufferBytes[0] = 4;
        event(q);
    }
    void digits(uint32_t group, uint32_t value, bool wrapper) {
        char b[16]{};
        ClawBootyResultsCall q{};
        q.function = 0x4a3920;
        q.argumentCount = 3;
        q.arguments[1] = 0x52c6f8;
        q.arguments[2] = value;
        q.name = "%010i";
        q.localMask = 1;
        q.bufferCount = 1;
        q.buffers[0] = b;
        q.bufferBytes[0] = 16;
        event(q);
        uint32_t length = uint32_t(std::strlen(b)), i = 0;
        while (si(i) < si(get(group + 8))) {
            step();
            uint32_t n = get(group + 8);
            if (n > length)
                fail(3);
            uint32_t actor = get(group + 12 + i * 4), index = uint32_t(int32_t(int8_t(b[length - n + i])) - 48);
            if (wrapper)
                invoke(0x4209d0, actor, {index});
            else {
                ClawActorWrapperContext x{host(), 0};
                uint32_t out = 0;
                claw_actor_wrapper_entry(0x4209d0, actor, &index, 1, &x, nullptr, nullptr, &out);
                if (x.fault)
                    fail(x.fault);
            }
            put(primary(actor) + 104, 0xffffffff);
            ++i;
        }
    }
    void setNumber(uint32_t group, uint32_t value, bool wrapper = false) {
        if (get(group + 4) != value) {
            put(group + 4, value);
            digits(group, value, wrapper);
        }
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
    }
    static uint32_t hostCall(void *p, ClawSceneActorCall q) {
        auto &r = *static_cast<Run *>(p);
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
    static uint32_t hostAllocate(void *p, uint32_t n) {
        return static_cast<Run *>(p)->allocate(n);
    }
    static void release(void *p, uint32_t t) {
        static_cast<Run *>(p)->invoke(0x4f6428, 0, {t});
    }
    static uint32_t clock(void *p) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.scene.readClock)
            r.fail();
        return r.c.scene.readClock(r.c.scene.context);
    }
    ClawSceneActorHost host() {
        return {this, lookup, hostAllocate, release, hostCall, clock};
    }
    static uint32_t numberDependency(ClawCheckpointTimerContext *, const ClawCheckpointTimerCall *e, void *p) {
        auto &r = *static_cast<Run *>(p);
        ClawBootyResultsCall q{};
        q.function = e->function;
        q.receiver = e->receiver;
        q.argumentCount = e->argumentCount;
        std::copy_n(e->arguments, 8, q.arguments);
        q.name = e->name;
        q.localMask = e->localMask;
        if (e->buffer) {
            q.bufferCount = 1;
            q.buffers[0] = e->buffer;
            q.bufferBytes[0] = e->bufferBytes;
        }
        return r.event(q);
    }
    static uint32_t progressionDependency(ClawBootyProgressionContext *, const ClawBootyProgressionCall *q, void *p) {
        auto &r = *static_cast<Run *>(p);
        if (owned(q->function)) {
            uint32_t a[40]{};
            std::copy_n(q->arguments, q->argumentCount, a);
            switch (q->argumentCount) {
            case 0:
                return r.invoke(q->function, q->receiver);
            case 1:
                return r.invoke(q->function, q->receiver, {a[0]});
            case 2:
                return r.invoke(q->function, q->receiver, {a[0], a[1]});
            case 3:
                return r.invoke(q->function, q->receiver, {a[0], a[1], a[2]});
            default:
                r.fail(3);
            }
        }
        auto copy = *q;
        return r.event(copy);
    }
    static uint32_t baseDependency(ClawSinglePlayerSceneContext *, ClawSinglePlayerSceneCall e, void *p) {
        auto &r = *static_cast<Run *>(p);
        ClawBootyResultsCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, 8, q.arguments);
        q.localMask = e.localMask;
        q.bufferCount = e.bufferCount;
        std::copy_n(e.buffers, 3, q.buffers);
        std::copy_n(e.bufferBytes, 3, q.bufferBytes);
        return r.event(q);
    }
    struct AnimationView {
        Run *r;
        uint32_t actor, words[128]{};
    };
    static uint32_t *animationLookup(void *p, uint32_t t, uint32_t n) {
        auto &q = *static_cast<AnimationView *>(p);
        if (t == q.actor && n == 128)
            return q.words;
        if (t >= q.actor && (t - q.actor) % 4 == 0 && (t - q.actor) / 4 + n <= 109)
            return q.words + (t - q.actor) / 4;
        return q.r->span(t, n);
    }
    static uint32_t animationCall(void *p, ClawSceneActorCall e) {
        auto &q = *static_cast<AnimationView *>(p);
        std::copy_n(q.words, 109, q.r->span(q.actor, 109));
        auto v = hostCall(q.r, e);
        std::copy_n(q.r->span(q.actor, 109), 109, q.words);
        return v;
    }
    void image(uint32_t actor, uint32_t name, uint32_t index, bool indexed) {
        uint32_t registry = get(get(actor + 12) + 16) + 16, root = invoke(0x4f6286, registry, {name}), selected = 0;
        ClawActorBindingContext b{};
        b.imageRegistryToken = registry;
        b.image.token = root;
        if (root) {
            b.image.minimum = si(get(root + 100));
            b.image.maximum = si(get(root + 104));
            if (!indexed)
                index = uint32_t(b.image.minimum);
            ClawPickupPointsContext p{};
            p.scene = host();
            if (!claw_pickup_points_entry(0x40f680, root, &index, 1, &p, nullptr, nullptr, &selected) || p.fault)
                fail(p.fault ? p.fault : 1);
            b.image.firstImageIndex = si(index);
            b.image.images = &selected;
            b.image.imageCount = 1;
        }
        ClawActorResourceBindings s{};
        std::copy_n(span(actor, 109), 109, s.actor);
        auto dep = [](ClawActorResourceBindings *, ClawActorBindingContext *b, const ClawActorBindingCall *, void *) {
            return b->image.token;
        };
        uint32_t ok = indexed ? claw_actor_bind_indexed_image(&s, &b, text(name), si(index), dep, nullptr)
                              : claw_actor_bind_default_image(&s, &b, text(name), dep, nullptr);
        if (!ok)
            fail(3);
        std::copy_n(s.actor, 109, span(actor, 109));
    }
    uint32_t numbers(uint32_t p, const uint32_t *a) {
        auto actor = a[0], h = get(primary(actor) + 24);
        if (!h)
            return 0;
        uint32_t count = si(a[2]) > 9 ? 10 : a[2];
        put(p + 8, count);
        uint32_t i = 0, x = a[4];
        while (si(i) < si(get(p + 8))) {
            step();
            auto child = create(get(get(actor + 12) + 8), 0, 0, get(actor + 100) + 1, 0x522994);
            if (!child)
                return 0;
            put(p + 12 + i * 4, child);
            auto l = primary(child);
            if (!l)
                return 0;
            invoke(0x4c7970, child, {a[6]});
            auto hud = allocate(96);
            if (hud) {
                put(hud + 40, 0x50b5cc);
                put(hud, 0x50b5c4);
            }
            invoke(0x490760, hud, {child, get(h + 20), get(h + 24), get(h + 4), x, get(h + 12), get(h + 16) + a[5]});
            put(l + 24, hud);
            x += a[3];
            ++i;
        }
        put(p + 4, 0xffffcfc7);
        if (a[1] != 0xffffcfc7) {
            put(p + 4, a[1]);
            digits(p, a[1], false);
        }
        return 1;
    }
    void timeout(uint32_t p) {
        auto delta = get(0x53720c), v = get(p);
        put(p, delta < v ? v - delta : 0);
    }
    void post(uint32_t app) {
        invoke(0x546d50, 0, {get(get(app + 4) + 4), 0x111, 0x807c, 0});
    }
};
uint32_t body(Run &, uint32_t, uint32_t, const uint32_t *);
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    step();
    uint32_t args[40]{};
    std::copy(a.begin(), a.end(), args);
    if (owned(f))
        return body(*this, f, t, args);
    uint32_t out = 0;
    if (f == 0x498f40) {
        auto actor = args[0], l = primary(actor);
        uint32_t invoked = 0, receiver = 0, argument = 0;
        auto result = claw_simple_animation_step_v10(span(l + 28), span(l + 360), span(actor + 200), actor,
                                                     get(0x5430c4), &invoked, &receiver, &argument);
        if (invoked)
            invoke(0x4c82a0, receiver, {argument});
        return uint32_t(result);
    }
    if (c.composeBase && f == 0x48f0d0) {
        if (!c.progression || !c.progression->base)
            fail();
        auto b = *c.progression->base;
        b.host = host();
        if (!claw_single_player_scene_entry(f, t, args, uint32_t(a.size()), &b, baseDependency, this, &out) || b.fault)
            fail(b.fault ? b.fault : 1);
        return out;
    }
    if (c.progression) {
        auto p = *c.progression;
        p.scene = host();
        p.fault = 0;
        if (claw_booty_progression_entry(f, t, args, uint32_t(a.size()), &p, progressionDependency, this, &out)) {
            if (p.fault)
                fail(p.fault);
            return out;
        }
        if (p.fault)
            fail(p.fault);
    }
    if (c.composeNumbers && c.numbers) {
        auto n = *c.numbers;
        n.scene = host();
        n.fault = 0;
        if (claw_checkpoint_timer_entry(f, t, args, uint32_t(a.size()), &n, numberDependency, this, &out)) {
            if (n.fault)
                fail(n.fault);
            return out;
        }
        if (n.fault)
            fail(n.fault);
    }
    if (c.composeScene && (f == 0x4c8fc0 || f == 0x4c9320)) {
        uint32_t fault = 0;
        if (f == 0x4c8fc0) {
            if (!c.actors)
                fail();
            claw_scene_actor_update(t, c.actors, args[0], host(), &fault);
        } else
            claw_scene_actor_insert(t, args[0], host(), &fault);
        if (fault)
            fail(fault);
        return 0;
    }
    if (c.composeAnimation && (f == 0x4c82a0 || f == 0x4c79e0 || f == 0x4c8220)) {
        ClawActorAnimationGlobals g{get(0x5430c4), get(0x532c10)};
        auto h = host();
        AnimationView view{};
        if (f == 0x4c82a0 || f == 0x4c79e0) {
            view.r = this;
            view.actor = f == 0x4c82a0 ? get(t + 4) : t;
            std::copy_n(span(view.actor, 109), 109, view.words);
            h.context = &view;
            h.lookup = animationLookup;
            h.call = animationCall;
        }
        uint32_t fault = 0;
        if (!claw_actor_animation_entry(f, t, args[0], args[1], &g, h, &fault, &out) || fault)
            fail(fault ? fault : 1);
        if (view.actor)
            std::copy_n(view.words, 109, span(view.actor, 109));
        return out;
    }
    if (c.composeImages && (f == 0x4c7970 || f == 0x4c7900)) {
        image(t, args[0], args[1], f == 0x4c7900);
        return 1;
    }
    if (f == 0x4209d0 || f == 0x4061b0) {
        ClawActorWrapperContext x{host(), 0};
        if (!claw_actor_wrapper_entry(f, t, args, uint32_t(a.size()), &x, nullptr, nullptr, &out) || x.fault)
            fail(x.fault ? x.fault : 1);
        return out;
    }
    if (f == 0x484d90) {
        ClawStackedActorLifecycleContext x{host(), 0};
        if (!claw_stacked_actor_lifecycle_entry(f, t, args, uint32_t(a.size()), &x, &out) || x.fault)
            fail(x.fault ? x.fault : 1);
        return out;
    }
    if (f == 0x4c9be0) {
        ClawActorDestructionGlobals g{get(0x53c9ac), get(0x53c9b0), get(0x52e1cc)};
        AnimationView view{};
        view.r = this;
        view.actor = t;
        std::copy_n(span(t, 109), 109, view.words);
        auto h = host();
        h.context = &view;
        h.lookup = animationLookup;
        h.call = animationCall;
        h.free = [](void *p, uint32_t token) {
            auto &v = *static_cast<AnimationView *>(p);
            std::copy_n(v.words, 109, v.r->span(v.actor, 109));
            v.r->invoke(0x4f6428, 0, {token});
            std::copy_n(v.r->span(v.actor, 109), 109, v.words);
        };
        uint32_t fault = 0;
        if (!claw_actor_destruction_entry(f, t, args[0], &g, h, &fault, &out) || fault)
            fail(fault ? fault : 1);
        std::copy_n(view.words, 109, span(t, 109));
        return out;
    }
    return call(f, t, args, uint32_t(a.size()));
}
uint32_t body(Run &r, uint32_t f, uint32_t p, const uint32_t *a) {
    switch (f) {
    case 0x40d470: {
        if (!r.invoke(0x48f0d0, p, {a[0], a[1], a[2]}))
            return 0;
        r.put(p + 32, r.invoke(0x4b7f20, r.get(p + 8), {0x523b1c}));
        if (!r.get(p + 32))
            return 0;
        r.put(p + 36, r.invoke(0x4b7f20, r.get(p + 8), {0x523734}));
        if (!r.get(p + 36))
            return 0;
        if (r.get(r.get(p + 4) + 304)) {
            auto images = r.invoke(0x4b7cd0, r.get(p + 32), {0x523ce0});
            if (!images)
                return 0;
            r.virt(r.get(r.get(p + 12) + 16), 72, {images, 0x523b14, 0x523728});
            auto anis = r.invoke(0x4b7cd0, r.get(p + 32), {0x523cd8});
            if (!anis)
                return 0;
            r.invoke(0x4ce0d0, r.get(r.get(p + 12) + 44), {anis, 0x523b14, 0x523728});
        }
        uint32_t s = a[2], lengths[9]{};
        r.dataString(0x4f6439, &s);
        for (uint32_t i = 0; i < 9; ++i) {
            r.formatString(&s, 0x524094, {r.get(0x523d98 + i * 32)});
            lengths[i] = r.get(s - 8);
        }
        uint32_t sum = 0;
        for (uint32_t i = 0; i < 9; ++i)
            sum += r.get(0x534d08 + i * 4) * r.get(0x523d98 + i * 32);
        auto total = r.get(0x534cc4), old = total - sum;
        uint32_t app = r.get(p + 4), container = r.get(r.get(p + 12) + 8);
        auto totalActor = r.create(container, 420, 466, 9998, 0x5224d8);
        r.invoke(0x4c7900, totalActor, {0x524084, 5});
        auto l = r.primary(totalActor), hud = r.allocate(96);
        if (hud) {
            r.put(hud + 40, 0x50b5cc);
            r.put(hud, 0x50b5c4);
        }
        r.invoke(0x490760, hud, {totalActor, 10, 99, 1, 420, 4, 466});
        r.put(l + 24, hud);
        auto totalNumbers = r.allocate(52);
        if (totalNumbers)
            r.put(totalNumbers, 0x50b5cc);
        r.formatString(&s, 0x524094, {sum});
        r.invoke(0x4903c0, totalNumbers, {totalActor, 0, r.get(s - 8), 11, 490, 0xffffffff, 0x524070});
        auto oldActor = r.create(container, 90, 466, 9998, 0x5224d8);
        r.invoke(0x4c7900, oldActor, {0x524084, 4});
        l = r.primary(oldActor);
        hud = r.allocate(96);
        if (hud) {
            r.put(hud + 40, 0x50b5cc);
            r.put(hud, 0x50b5c4);
        }
        r.invoke(0x490760, hud, {oldActor, 10, 99, 1, 90, 4, 466});
        r.put(l + 24, hud);
        auto oldNumbers = r.allocate(52);
        if (oldNumbers)
            r.put(oldNumbers, 0x50b5cc);
        r.formatString(&s, 0x524094, {total});
        r.invoke(0x4903c0, oldNumbers, {oldActor, old, r.get(s - 8), 11, 155, 0xffffffff, 0x524070});
        r.put(0x5349a8, 1);
        for (uint32_t i = 0; i < 9; ++i) {
            uint32_t index = 8 - i, row = 0x523d90 + index * 32,
                     actor = r.create(container, uint32_t(-100), uint32_t(-100), 9998 + i, 0x5224e8);
            r.put(p + 0x15c + i * 4, actor);
            if (!actor)
                continue;
            uint32_t image = 0;
            r.dataString(0x4f65f2, &image, {r.get(row)});
            if (si(r.get(row + 28)) >= 0)
                r.dataString(0x4f6920, &image, {r.get(0x523eb0 + r.get(row + 28) * 4)});
            r.invoke(0x4c7970, actor, {image});
            auto primary = r.primary(actor), counter = r.allocate(184);
            if (counter) {
                r.put(counter + 40, 0x50b5cc);
                r.put(counter, 0x50b5bc);
                for (uint32_t off = 96; off < 140; off += 4)
                    r.put(counter + off, 0);
                r.put(0x52d4e0, 8);
                r.put(counter + 168, 0);
                for (uint32_t off = 140; off <= 164; off += 4)
                    r.put(counter + off, off == 152 ? 1 : 0);
                r.put(counter + 172, 0x3ff00000);
                r.put(counter + 176, 0);
                r.put(counter + 180, 0);
                r.put(0x53cac4, r.get(0x53cac4) + 1);
            }
            if (!counter)
                r.fail(2);
            auto count = r.get(0x534d08 + index * 4);
            r.put(counter + 140, index);
            r.put(counter + 144, count);
            r.put(counter + 148, count);
            r.put(counter + 152, r.get(row + 24));
            if (si(count) < si(r.get(0x5381e0 + index * 4)))
                count = r.get(0x5381e0 + index * 4);
            r.put(counter + 156, count);
            r.put(counter + 160, 160);
            r.put(counter + 164, 55 + i * 44);
            r.put(0x53cac8, totalNumbers);
            r.put(0x53cacc, oldNumbers);
            r.put(counter + 168, r.get(row + 16));
            r.put(counter + 172, r.get(row + 20));
            r.put(counter + 132, oldActor);
            r.put(counter + 180, total);
            r.put(counter + 136, totalActor);
            r.put(counter + 176, sum);
            r.invoke(0x490760, counter, {actor, 10, 99, 1, r.get(counter + 160), 4, r.get(counter + 164)});
            r.put(primary + 24, counter);
            if (r.get(counter + 144) != r.get(counter + 156))
                r.put(0x5349a8, 0);
            r.dataString(0x4f6584, &image);
        }
        if (!r.get(app + 304)) {
            uint32_t title = 0;
            r.dataString(0x4f6439, &title);
            uint32_t level = r.get(p + 20) * 2;
            r.formatString(&title, 0x523cc8, {si(level) < 10 ? 0x523cd4u : 0x523cd0u, level});
            r.assignString(p + 384, &title);
            r.invoke(0x4f6920, p + 384, {r.get(0x5349a0) ? 0x523c74u : 0x523c6cu});
            r.dataString(0x4f6584, &title);
        } else
            r.invoke(0x4f66cc, p + 384, {0x524064});
        r.dataString(0x4f6584, &s);
        return 1;
    }
    case 0x40dc50:
        r.invoke(0x48ffa0, p, {r.get(p + 384), 1, 0, 0});
        r.invoke(0x4ca9e0, r.get(r.get(p + 12) + 4), {r.get(r.get(r.get(p + 12) + 4) + 20)});
        r.invoke(0x4caa90, r.get(r.get(p + 12) + 4));
        r.invoke(0x4caa20, r.get(r.get(p + 12) + 4), {1});
        return 1;
    case 0x40dca0:
        return r.invoke(0x40dc50, p);
    case 0x40dcb0:
        r.invoke(0x4f6286, r.get(r.get(p + 12) + 40) + 16, {0x52374c});
        if (r.get(p + 44)) {
            r.invoke(0x4bb990, r.get(r.get(p + 44) + 16), {0, 256, 0, 0, 0, 500});
            for (uint32_t i = 0; i < 2; ++i) {
                auto h = r.get(r.get(p + 12) + 4);
                r.invoke(0x4b97c0, r.get(r.get(h + 20) + 44), {0});
                r.invoke(0x4b98b0, r.get(r.get(h + 16) + 44), {0});
            }
        }
        return 1;
    case 0x40dc10:
        if (r.get(p + 12)) {
            r.invoke(0x4caa90, r.get(r.get(p + 12) + 4));
            r.virt(r.get(r.get(p + 12) + 16), 88);
            r.invoke(0x4cdf40, r.get(r.get(p + 12) + 44));
            r.invoke(0x4c89e0, r.get(r.get(p + 12) + 8));
        }
        r.invoke(0x48f180, p);
        return 0;
    case 0x40b040:
        r.put(p, 0x50b494);
        r.invoke(0x40dc10, p);
        r.invoke(0x4f6584, p + 384);
        r.put(p, 0x50b4ec);
        r.invoke(0x48f180, p);
        return 0;
    case 0x40b020:
        r.invoke(0x40b040, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x40e020:
        if (a[0] == 27 || a[0] == 32 || a[0] == 13)
            r.invoke(0x40e040, p);
        return 1;
    case 0x40e040:
        for (uint32_t i = 0; i < 9; ++i) {
            auto actor = r.get(p + 348 + i * 4);
            if (!actor)
                continue;
            auto l = r.primary(actor), state = r.get(l + 28);
            if (r.get(0x52d4e0) == 0xffffffff && state == 0x2334)
                r.put(l + 312, 0);
            else if (state == 0x2331 || state == 0x232c || state == 0x232d || state == 0x232e || state == 0x232f ||
                     state == 0x2329 || state == 0x2334)
                r.put(l + 312, r.get(0x52d4e4));
            else
                r.put(l + 28, 0x2330);
        }
        return 1;
    case 0x40dd50: {
        r.invoke(0x4b3490, r.get(0x537200));
        if (r.get(r.get(0x537200) + 528) & 0xffffff)
            r.invoke(0x40e040, p);
        if (r.get(r.get(p + 4) + 156))
            r.invoke(0x45fbb0, r.get(r.get(r.get(r.get(p + 12) + 4) + 20) + 44), {5, 0, 635, 25});
        r.virt(r.get(r.get(p + 12) + 8), 36, {1});
        auto scene = r.get(p + 12), h = r.get(scene + 4);
        r.virt(r.get(scene + 12), 52, {r.get(h + 20), r.get(h + 24)});
        r.virt(r.get(scene + 8), 40, {r.get(r.get(scene + 4) + 20)});
        h = r.get(r.get(p + 12) + 4);
        r.invoke(0x4b98b0, r.get(r.get(h + 16) + 44), {0});
        r.invoke(0x4b9d80, r.get(r.get(h + 20) + 44), {0, 0, r.get(r.get(h + 24) + 44), r.get(h + 24) + 28, 16});
        bool done = true;
        for (uint32_t i = 0; i < 9; ++i) {
            auto actor = r.get(p + 348 + i * 4);
            if (actor && r.get(r.primary(actor) + 28) != 0x2331)
                done = false;
        }
        if (done && !r.get(p + 340)) {
            r.put(p + 340, 1);
            r.post(r.get(p + 4));
        }
        return 1;
    }
    case 0x40de90: {
        if (!r.invoke(0x4ca930, r.get(r.get(p + 12) + 4)))
            return 0;
        auto result = r.invoke(0x40dc50, p), images = r.invoke(0x4b7cd0, r.get(p + 32), {0x523ce0});
        if (!images)
            return 0;
        if (r.virt(r.get(r.get(p + 12) + 16), 76, {images, 0x523b14, 0x523728}) == 0xffffffff)
            return 0;
        while (si(r.invoke(0x546d54, 0, {0})) >= 0)
            r.step();
        return result;
    }
    case 0x40df00:
        if (!r.virt(p, 12) || !r.get(p + 44))
            return 0;
        {
            auto result = r.invoke(0x40dc50, p);
            while (si(r.invoke(0x546d54, 0, {0})) >= 0)
                r.step();
            return r.invoke(0x48f470, p, {250}) ? result : 0;
        }
    case 0x40df60: {
        if (!r.virt(p, 12) || !r.invoke(0x490370, p))
            return 0;
        auto h = r.get(r.get(p + 12) + 4), dest = r.get(h + 20), source = r.get(h + 24);
        if (dest && source)
            r.invoke(0x4b9d80, r.get(dest + 44), {0, 0, r.get(source + 44), source + 28, 16});
        auto scene = r.get(p + 12);
        h = r.get(scene + 4);
        r.virt(r.get(scene + 12), 52, {r.get(h + 20), r.get(h + 24)});
        r.virt(r.get(scene + 8), 40, {r.get(r.get(scene + 4) + 20)});
        h = r.get(r.get(p + 12) + 4);
        r.invoke(0x4b98b0, r.get(r.get(h + 16) + 44), {0});
        r.invoke(0x4b9d80, r.get(r.get(h + 20) + 44), {0, 0, r.get(r.get(h + 24) + 44), r.get(h + 24) + 28, 16});
        while (si(r.invoke(0x546d54, 0, {0})) >= 0)
            r.step();
        return 1;
    }
    case 0x4903c0:
        return r.numbers(p, a);
    case 0x499c30:
        r.setNumber(p, a[0]);
        return 0;
    case 0x40db10:
        r.invoke(0x40db60, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x40db60:
        r.put(p, 0x50b5bc);
        for (uint32_t off = 96; off < 112; off += 4) {
            auto n = r.get(p + off);
            if (n)
                r.virt(n, 0, {1});
        }
        r.put(0x53cac4, r.get(0x53cac4) - 1);
        if (!r.get(0x53cac4)) {
            for (auto address : {0x53cac8u, 0x53caccu})
                if (r.get(address))
                    r.virt(r.get(address), 0, {1});
        }
        r.put(p + 40, 0x50b014);
        r.put(p, 0x50b014);
        return 0;
    case 0x4c89e0:
        r.virt(p, 60);
        return 0;
    case 0x4c89f0: {
        uint32_t at = r.get(p + 20);
        while (at) {
            r.step();
            auto next = r.get(at), actor = r.get(at + 8);
            if (actor)
                r.virt(actor, 4, {1});
            at = next;
        }
        r.invoke(0x4f5172, p + 16);
        return 0;
    }
    default:
        break;
    }
    switch (f) {
    case 0x490370: {
        if (!r.get(p + 4) || !r.get(r.get(p + 4) + 4))
            return 0;
        uint32_t paint[16]{};
        ClawBootyResultsCall q{};
        q.function = 0x546cb4;
        q.argumentCount = 2;
        q.arguments[0] = r.get(r.get(r.get(p + 4) + 4) + 4);
        q.localMask = 2;
        q.bufferCount = 1;
        q.buffers[0] = paint;
        q.bufferBytes[0] = 64;
        r.event(q);
        q.function = 0x546cb8;
        q.arguments[0] = r.get(r.get(r.get(p + 4) + 4) + 4);
        r.event(q);
        return 1;
    }
    case 0x48ffa0: {
        if (!r.get(p + 12) || !r.get(p + 8) || !r.get(p + 32))
            return 0;
        char name[64]{};
        ClawBootyResultsCall q{};
        q.function = 0x4a3920;
        q.argumentCount = 3;
        q.arguments[1] = 0x528e54;
        q.arguments[2] = a[0];
        q.localMask = 1;
        q.bufferCount = 1;
        q.buffers[0] = name;
        q.bufferBytes[0] = 64;
        q.name = r.text(0x528e54);
        r.event(q);
        q = {};
        q.function = 0x4b7dc0;
        q.receiver = r.get(p + 32);
        q.argumentCount = 2;
        q.arguments[1] = 0x504358;
        q.localMask = 1;
        q.bufferCount = 1;
        q.buffers[0] = name;
        q.bufferBytes[0] = 64;
        q.name = name;
        auto file = r.event(q);
        if (!file)
            return 0;
        if (r.get(p + 44)) {
            r.invoke(0x4d46f0, r.get(r.get(p + 12) + 24), {r.get(p + 44)});
            r.put(p + 44, 0);
        }
        auto length = std::strlen(r.text(a[0]));
        if (length >= sizeof name)
            r.fail(3);
        std::memcpy(name, r.text(a[0]), length + 1);
        auto manager = r.get(r.get(p + 12) + 24);
        q = {};
        q.function = r.get(r.get(manager) + 48);
        q.receiver = manager;
        q.argumentCount = 3;
        q.arguments[0] = file;
        q.arguments[2] = a[2] != 0;
        q.localMask = 2;
        q.bufferCount = 1;
        q.buffers[0] = name;
        q.bufferBytes[0] = 64;
        q.name = name;
        auto palette = r.event(q);
        r.put(p + 44, palette);
        if (!palette)
            return 0;
        if (a[3]) {
            r.invoke(0x4bb870, r.get(palette + 16));
            r.invoke(0x4bb910, r.get(r.get(p + 44) + 16), {0, 256, 0, 0, 0, 0});
        }
        palette = r.get(p + 44);
        r.put(r.get(r.get(p + 12) + 24) + 100, palette);
        r.virt(palette, 52);
        if (!r.invoke(0x4ca900, r.get(r.get(p + 12) + 4), {file, 1}))
            return 0;
        if (a[1])
            r.invoke(0x4b98b0, r.get(r.get(r.get(r.get(p + 12) + 4) + 16) + 44), {0});
        if (a[3] && r.get(p + 44)) {
            auto core = r.get(r.get(p + 44) + 16);
            r.invoke(0x4bbd90, core, {0, 256, r.get(core + 16), 750});
        }
        return 1;
    }
    case 0x48f470: {
        if (!r.get(p + 44))
            return 0;
        r.invoke(0x4bbd20, r.get(r.get(p + 44) + 16));
        auto core = r.get(r.get(p + 44) + 16);
        if (a[0])
            r.invoke(0x4bb910, core, {0, 256, 0, 0, 0, 0});
        else
            r.invoke(0x4bb8c0, core, {0});
        auto palette = r.get(p + 44);
        r.put(r.get(r.get(p + 12) + 24) + 100, palette);
        r.virt(palette, 52);
        if (a[0]) {
            core = r.get(r.get(p + 44) + 16);
            r.invoke(0x4bbd90, core, {0, 256, r.get(core + 16), a[0]});
        }
        return 1;
    }
    case 0x4995d0: {
        if (!r.get(p + 144))
            return 1;
        auto t = ftol(div(mul(double(si(r.get(p + 148))), r.real(0x50fc50)), double(si(r.get(p + 144)))));
        auto x = 25 - t;
        auto absolute = si(x) < 0 ? 0 - x : x;
        return ftol(mul(double(si(absolute)), r.real(p + 168)));
    }
    case 0x499170: {
        if (r.get(p + 100))
            return 0;
        uint32_t s = p;
        auto group = [&](uint32_t off, uint32_t lengthValue, uint32_t initial, uint32_t x) {
            auto n = r.allocate(52);
            if (n)
                r.put(n, 0x50b5cc);
            r.put(p + off, n);
            r.formatString(&s, 0x524094, {lengthValue});
            r.invoke(0x4903c0, n, {a[0], initial, r.get(s - 8), 11, x, 0, 0x524070});
        };
        auto symbol = [&](uint32_t off, uint32_t x, uint32_t y, uint32_t index) {
            auto actor = r.create(r.container(), x, y, 9998, 0x5224d8);
            r.put(p + off, actor);
            if (actor)
                r.invoke(0x4c7900, actor, {0x524084, index});
        };
        auto n = r.allocate(52);
        if (n)
            r.put(n, 0x50b5cc);
        r.put(p + 100, n);
        r.dataString(0x4f6439, &s);
        r.formatString(&s, 0x524094, {r.get(p + 144)});
        r.invoke(0x4903c0, n, {a[0], 0, r.get(s - 8), 11, r.get(p + 160) + 40, 0, 0x524070});
        symbol(116, r.get(p + 160) + 110, r.get(p + 164) + 4, 1);
        group(108, r.get(p + 156), r.get(p + 156), r.get(p + 160) + 150);
        symbol(120, r.get(p + 160) + 215, r.get(p + 164) + 4, 2);
        auto value = r.get(0x523d98 + r.get(p + 140) * 32);
        group(104, value, value, r.get(p + 160) + 233);
        symbol(124, r.get(p + 160) + 299, r.get(p + 164), 3);
        group(96, value * r.get(p + 144), 0, r.get(p + 160) + 321);
        r.dataString(0x4f6584, &s);
        return 1;
    }
    case 0x499450: {
        if (r.get(p + 112))
            return 0;
        auto sound = r.get(r.get(r.get(0x5371fc) + 48) + 40);
        if (!r.get(sound + 48)) {
            auto resource = r.invoke(0x4f6286, sound + 16, {r.get(0x523d94 + r.get(p + 140) * 32)});
            if (resource && r.get(0x532c0c))
                r.invoke(0x4b45f0, r.get(resource + 16), {r.get(0x532c10), 0, 0, 0});
        }
        auto actor = r.create(r.container(), r.get(p + 160), r.get(p + 164), 9998, 0x5224d8);
        r.put(p + 112, actor);
        uint32_t s = 0, row = 0x523d90 + r.get(p + 140) * 32;
        r.dataString(0x4f65f2, &s, {r.get(row)});
        if (si(r.get(row + 28)) >= 0)
            r.dataString(0x4f6920, &s, {r.get(0x523eb0 + r.get(row + 28) * 4)});
        r.invoke(0x4c7970, actor, {s});
        auto selected = r.get(actor + 368), coins = r.invoke(0x4f6286, r.get(r.get(a[0] + 12) + 16) + 16, {0x523ff8});
        if (selected == coins)
            r.invoke(0x4c79e0, actor, {0x52d510, 0});
        r.dataString(0x4f6584, &s);
        return 1;
    }
    case 0x499630: {
        auto interval = r.invoke(0x4995d0, p);
        if (!interval || (interval == 0xffffffff && r.get(0x52d4e8) == 0x80000000))
            r.fail(2);
        auto count = uint32_t(si(r.get(0x52d4e8)) / si(interval)) + 1;
        if (si(r.get(p + 148)) <= si(count))
            count = r.get(p + 148);
        for (uint32_t i = 0; si(i) < si(count); ++i) {
            r.step();
            auto actor = r.create(r.container(), r.get(0x52d4ec), r.get(0x53cad0), 9998, 0x5224c8);
            uint32_t s = 0, row = 0x523d90 + r.get(p + 140) * 32;
            r.dataString(0x4f65f2, &s, {r.get(row)});
            if (si(r.get(row + 28)) >= 0) {
                auto random = r.invoke(0x4a3050, 0);
                r.dataString(0x4f6920, &s, {r.get(0x523eb0 + uint32_t(si(random) % 4) * 4)});
            }
            r.invoke(0x4c7970, actor, {s});
            auto selected = r.get(actor + 368),
                 coins = r.invoke(0x4f6286, r.get(r.get(a[0] + 12) + 16) + 16, {0x523ff8});
            if (selected == coins)
                r.invoke(0x4c79e0, actor, {0x52d510, 0});
            auto l = r.primary(actor);
            r.put(l + 304, i * interval);
            r.put(l + 100, r.get(p + 160));
            r.put(l + 104, r.get(p + 164));
            r.dataString(0x4f6584, &s);
        }
        return count;
    }
    case 0x4997c0: {
        auto delta = (r.get(p + 140) & 1) ? a[0] : 0 - a[0];
        auto shift = [&](uint32_t actor) {
            r.put(actor + 76, r.get(actor + 76) + delta);
        };
        shift(r.get(p + 112));
        for (auto off : {100u, 108u, 104u, 96u}) {
            if (off == 108)
                shift(r.get(p + 116));
            if (off == 104)
                shift(r.get(p + 120));
            if (off == 96)
                shift(r.get(p + 124));
            for (uint32_t i = 0; si(i) < si(r.get(r.get(p + off) + 8)); ++i) {
                r.step();
                shift(r.get(r.get(p + off) + 12 + i * 4));
            }
        }
        if (r.get(p + 128))
            shift(r.get(p + 128));
        return 1;
    }
    case 0x4998c0: {
        if (!a[0]) {
            auto sound = r.get(r.get(r.get(0x5371fc) + 48) + 40);
            if (!r.get(sound + 48)) {
                auto resource = r.invoke(0x4061b0, sound, {0x52d520});
                if (resource)
                    r.invoke(0x4208e0, resource, {r.get(0x532c10), 0, 0, 0});
            }
            auto group = r.get(p + 100), old = r.get(group + 4), amount = r.get(p + 152);
            if (si(r.get(p + 144)) < si(old + amount))
                amount = r.get(p + 144) - old;
            r.setNumber(group, old + amount, true);
            auto points = r.get(0x523d98 + r.get(p + 140) * 32) * amount;
            for (auto groupToken : {r.get(p + 96), r.get(0x53cac8), r.get(0x53cacc)})
                r.invoke(0x499c30, groupToken, {r.get(groupToken + 4) + points});
            auto remaining = r.get(p + 148) - r.get(p + 152);
            r.put(p + 148, si(remaining) < 0 ? 0 : remaining);
        } else {
            r.setNumber(r.get(p + 100), r.get(p + 144), true);
            r.setNumber(r.get(p + 96), r.get(0x523d98 + r.get(p + 140) * 32) * r.get(p + 144), true);
            r.setNumber(r.get(0x53cac8), r.get(p + 176), true);
            r.setNumber(r.get(0x53cacc), r.get(p + 180), true);
        }
        return 1;
    }
    case 0x499cd0: {
        r.put(r.get(p + 136) + 76, r.get(r.get(p + 136) + 76) - a[0]);
        for (uint32_t i = 0; si(i) < si(r.get(r.get(0x53cac8) + 8)); ++i) {
            r.step();
            auto actor = r.get(r.get(0x53cac8) + 12 + i * 4);
            r.put(actor + 76, r.get(actor + 76) - a[0]);
        }
        r.put(r.get(p + 132) + 76, r.get(r.get(p + 132) + 76) + a[0]);
        for (uint32_t i = 0; si(i) < si(r.get(r.get(0x53cacc) + 8)); ++i) {
            r.step();
            auto actor = r.get(r.get(0x53cacc) + 12 + i * 4);
            r.put(actor + 76, r.get(actor + 76) + a[0]);
        }
        return 1;
    }
    case 0x499d60: {
        if (r.get(p + 144) == r.get(p + 156)) {
            auto sound = r.get(r.get(r.get(0x5371fc) + 48) + 40);
            auto resource = r.invoke(0x4f6286, sound + 16, {0x52d540});
            if (resource) {
                auto volume = ftol(mul(double(si(r.get(0x532c10))), r.real(0x50fc58)));
                if (si(volume) > 100)
                    volume = 100;
                if (r.get(0x532c0c))
                    r.invoke(0x4b45f0, r.get(resource + 16), {volume, 0, 0, 0});
            }
            auto actor =
                r.create(r.get(r.get(a[0] + 12) + 8), r.get(p + 160), r.get(p + 164), r.get(a[0] + 100) + 1, 0x5224d8);
            r.put(p + 128, actor);
            r.invoke(0x4c7970, actor, {0x52d530});
            r.invoke(0x4c79e0, actor, {0x52d510, 0});
            r.put(r.primary(actor) + 32, uint32_t(si(r.invoke(0x4a3050, 0)) % 251));
        }
        r.put(a[0] + 76, r.get(0x52d4ec));
        r.put(a[0] + 80, r.get(0x53cad0));
        r.put(0x52d4e0, r.get(0x52d4e0) - 1);
        return 1;
    }
    case 0x498f90: {
        auto actor = a[0], l = r.primary(actor), state = r.get(l + 28);
        switch (state) {
        case 0:
            r.put(l + 360, 0);
            r.put(actor + 200, 0);
            r.put(l + 28, 5);
            return 1;
        case 5:
            r.timeout(l + 304);
            if (!r.get(l + 304))
                r.put(l + 28, 0x2332);
            break;
        case 0x2332: {
            auto duration = r.get(0x52d4e8);
            r.put(l + 304, duration);
            r.single(l + 352,
                     div(mul(double(si(r.get(l + 100) - r.get(0x52d4ec))), r.real(0x50fc40)), double(duration)));
            r.put(l + 28, 0x2333);
            r.single(l + 356,
                     div(mul(double(si(r.get(l + 104) - r.get(0x53cad0))), r.real(0x50fc40)), double(duration)));
            break;
        }
        case 0x2333:
            r.timeout(l + 304);
            for (uint32_t off = 0; off < 8; off += 4) {
                auto pos = r.get(actor + 76 + off), target = r.get(l + 100 + off);
                if (si(pos) < si(target)) {
                    pos += ftol(mul(mul(double(r.single(l + 352 + off)), double(r.get(0x53720c))), r.real(0x50fc48)));
                    r.put(actor + 76 + off, si(target) < si(pos) ? target : pos);
                }
            }
            if (!r.get(l + 304)) {
                r.put(actor + 8, r.get(actor + 8) | 0x10000);
                return 0;
            }
            break;
        default:
            return 1;
        }
        r.invoke(0x4c82a0, actor + 392, {r.get(0x5430c4)});
        return 1;
    }
    case 0x498930: {
        auto actor = a[0], l = r.primary(actor), counter = r.get(l + 24), state = r.get(l + 28);
        bool animate = true;
        switch (state) {
        case 0:
            r.put(0x53cad4, 0);
            r.put(0x53cad8, 0);
            r.put(l + 312, r.get(0x52d4e4));
            r.put(l + 360, 0);
            r.put(actor + 200, 0);
            r.put(actor + 76, r.get(0x52d4ec));
            r.put(actor + 80, r.get(0x53cad0));
            if (!r.get(actor + 400)) {
                auto selected = r.get(actor + 368),
                     coins = r.invoke(0x4f6286, r.get(r.get(actor + 12) + 16) + 16, {0x523ff8});
                if (selected == coins)
                    r.invoke(0x4c79e0, actor, {0x52d510, 0});
            }
            r.put(l + 28, 5);
            return 1;
        case 5:
            if (r.get(0x52d4e0) == r.get(counter + 140))
                r.put(l + 28, 0x232a);
            break;
        case 0x2329:
            if (r.get(0x52d4e0) == 0xffffffff) {
                if (!r.get(r.get(0x5371fc) + 304) && r.get(0x5349a8) && !r.get(0x53cad4)) {
                    auto perfect = r.create(r.container(), 320, 240, 100000, 0x5224d8);
                    r.put(0x53cad4, perfect);
                    if (perfect) {
                        r.invoke(0x4c7900, perfect, {0x52d500, 1});
                        r.invoke(0x4c79e0, perfect, {0x52d4f0, 0});
                        auto sound = r.get(r.get(r.get(0x5371fc) + 48) + 40);
                        if (!r.get(sound + 48)) {
                            auto resource = r.invoke(0x4f6286, sound + 16, {0x52d500});
                            if (resource && r.get(0x532c0c))
                                r.invoke(0x4b45f0, r.get(resource + 16), {r.get(0x532c10), 0, 0, 0});
                        }
                    }
                    if (si(r.get(0x534cfc)) < 10)
                        r.put(0x534cfc, r.get(0x534cfc) + 1);
                }
                r.put(l + 28, 0x2334);
                if (r.get(r.get(0x53499c) - 8) && !r.get(0x53cad8)) {
                    auto resource = r.invoke(0x4f6286, r.get(r.get(r.get(0x5371fc) + 48) + 40) + 16, {r.get(0x53499c)});
                    if (resource && !r.get(0x5349a0) && r.get(0x532c0c))
                        r.invoke(0x4b3dc0, r.get(resource + 16), {100, 0, 0, 0});
                    r.put(0x53cad8, 1);
                }
            }
            break;
        case 0x232a:
            r.put(l + 304, r.get(0x52d4e8));
            r.put(l + 308, r.invoke(0x4995d0, counter));
            r.single(l + 352, div(mul(double(si(r.get(counter + 160) - r.get(0x52d4ec))), r.real(0x50fc40)),
                                  double(r.get(l + 304))));
            r.put(actor + 80, r.get(counter + 164));
            r.put(l + 172, 0);
            r.put(l + 28, 0x232b);
            break;
        case 0x232b:
            r.timeout(l + 304);
            if (!r.get(l + 172) && si(r.get(actor + 76)) < si(r.get(counter + 160))) {
                auto x = r.get(actor + 76) +
                         ftol(mul(mul(double(r.single(l + 352)), double(r.get(0x53720c))), r.real(0x50fc48)));
                r.put(actor + 76, si(r.get(counter + 160)) < si(x) ? r.get(counter + 160) : x);
            }
            if (!r.get(l + 304)) {
                if (!r.get(l + 172)) {
                    r.put(actor + 76, r.get(0x52d4ec));
                    r.put(actor + 80, r.get(0x53cad0));
                    r.invoke(0x499450, counter, {actor});
                    r.invoke(0x499170, counter, {actor});
                    r.put(l + 172, 1);
                }
                r.put(l + 304, r.get(0x52d4e8));
                r.invoke(0x499630, counter, {actor});
            }
            if (r.get(l + 172) == 1) {
                bool finish = !r.get(counter + 144);
                if (!finish) {
                    r.timeout(l + 308);
                    if (!r.get(l + 308)) {
                        if (si(r.get(counter + 148)) < 1)
                            finish = true;
                        else {
                            r.invoke(0x4998c0, counter, {0});
                            r.put(l + 308, r.invoke(0x4995d0, counter));
                        }
                    }
                }
                if (finish) {
                    r.invoke(0x499d60, counter, {actor});
                    r.put(l + 312, r.get(0x52d4e4));
                    r.put(l + 28, 0x2329);
                }
            }
            break;
        case 0x232c:
            if (r.get(0x52d4e0) == 0xffffffff) {
                r.put(l + 28, 0x232d);
                r.put(l + 304, 18 - 2 * r.get(counter + 140));
                r.put(l + 100, 25);
                r.put(l + 104, 25);
            }
            break;
        case 0x232d:
            r.timeout(l + 304);
            if (r.get(l + 304))
                return 1;
            {
                auto old = r.get(l + 104);
                r.put(l + 104, old - 1);
                if (si(old) < 1) {
                    r.put(l + 28, r.get(counter + 140) == 1 ? 0x232e : 0x2331);
                    return 1;
                }
                r.invoke(0x4997c0, counter, {r.get(l + 100)});
                r.put(l + 304, 18 - 2 * r.get(counter + 140));
                return 1;
            }
        case 0x232e:
            r.put(l + 304, 75);
            r.put(l + 100, 25);
            r.put(l + 108, 25);
            r.put(l + 28, 0x232f);
            break;
        case 0x232f:
            r.timeout(l + 304);
            {
                auto old = r.get(l + 108);
                r.put(l + 108, old - 1);
                if (si(old) < 1) {
                    r.put(l + 28, 0x2331);
                    return 1;
                }
                r.invoke(0x499cd0, counter, {r.get(l + 100)});
                r.put(l + 304, 75);
                return 1;
            }
        case 0x2330:
            if (r.get(counter + 140) == r.get(0x52d4e0)) {
                r.invoke(0x499450, counter, {actor});
                r.invoke(0x499170, counter, {actor});
                r.invoke(0x4998c0, counter, {1});
                r.invoke(0x499d60, counter, {actor});
                r.put(l + 312, r.get(0x52d4e4));
                r.put(l + 28, 0x2329);
            }
            break;
        case 0x2331:
            break;
        case 0x2334:
            r.timeout(l + 312);
            if (!r.get(l + 312))
                r.put(l + 28, 0x232c);
            break;
        default:
            animate = false;
            break;
        }
        if (animate)
            r.invoke(0x4c82a0, actor + 392, {r.get(0x5430c4)});
        return 1;
    }
    default:
        r.fail(3);
    }
}
bool owned(uint32_t f) {
    switch (f) {
    case 0x40d470:
    case 0x40dc50:
    case 0x40dca0:
    case 0x40dcb0:
    case 0x40dc10:
    case 0x40b040:
    case 0x40b020:
    case 0x40e020:
    case 0x40e040:
    case 0x40dd50:
    case 0x40de90:
    case 0x40df00:
    case 0x40df60:
    case 0x4903c0:
    case 0x499c30:
    case 0x40db10:
    case 0x40db60:
    case 0x4c89e0:
    case 0x4c89f0:
    case 0x490370:
    case 0x48ffa0:
    case 0x48f470:
    case 0x4995d0:
    case 0x499170:
    case 0x499450:
    case 0x499630:
    case 0x4997c0:
    case 0x4998c0:
    case 0x499cd0:
    case 0x499d60:
    case 0x498f90:
    case 0x498930:
        return true;
    default:
        return false;
    }
}
uint32_t arity(uint32_t f) {
    switch (f) {
    case 0x40d470:
        return 3;
    case 0x48ffa0:
        return 4;
    case 0x4903c0:
        return 7;
    case 0x40e020:
        return 2;
    case 0x40dca0:
    case 0x40dcb0:
    case 0x40b020:
    case 0x499c30:
    case 0x40db10:
    case 0x48f470:
    case 0x499170:
    case 0x499450:
    case 0x499630:
    case 0x4997c0:
    case 0x4998c0:
    case 0x499cd0:
    case 0x499d60:
    case 0x498f90:
    case 0x498930:
        return 1;
    default:
        return 0;
    }
}
} // namespace
extern "C" uint32_t claw_booty_results_entry(uint32_t f, uint32_t receiver, const uint32_t *a, uint32_t count,
                                             ClawBootyResultsContext *c, ClawBootyResultsDependency d, void *u,
                                             uint32_t *out) {
    if (!c || !out)
        return 0;
    if (!owned(f))
        return 0;
    if (count != arity(f) || (count && !a)) {
        c->fault = 3;
        return 0;
    }
    try {
        Run r{*c, d, u};
        uint32_t arguments[40]{};
        std::copy_n(a, count, arguments);
        *out = body(r, f, receiver, arguments);
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
extern "C" uint32_t claw_booty_results_function(uint32_t vt, uint32_t slot) {
    if (vt == 0x50b494) {
        static const uint32_t a[] = {0x40b020, 0x40d470, 0x40dc10, 0x40af20, 0x4bd240, 0x40dd50, 0x40de90,
                                     0x40df00, 0x40df60, 0x40dca0, 0x40dcb0, 0x40af40, 0x40e020, 0x40af50,
                                     0x40af50, 0x40af50, 0x4bb030, 0x4bb030, 0x48fcf0, 0x4bd250};
        if (slot % 4 == 0 && slot / 4 < 20)
            return a[slot / 4];
    }
    if (slot == 0) {
        if (vt == 0x50b5bc)
            return 0x40db10;
        if (vt == 0x50b5cc)
            return 0x484d90;
        if (vt == 0x50b5c4)
            return 0x40db30;
    }
    return 0;
}
