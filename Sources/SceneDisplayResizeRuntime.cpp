#include "SceneDisplayResizeRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
struct Run {
    ClawSceneDisplayResizeContext &c;
    ClawSceneDisplayResizeDependency d;
    void *u;
    uint32_t operations = 0;
    void tick() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000)) {
            c.fault = 3;
            throw Failure{};
        }
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        tick();
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failure{};
        }
        return p;
    }
    uint32_t get(uint32_t t, uint32_t o = 0) {
        return *span(t + o);
    }
    void put(uint32_t t, uint32_t o, uint32_t v) {
        *span(t + o) = v;
    }
    static int32_t signedWord(uint32_t v) {
        int32_t s;
        std::memcpy(&s, &v, 4);
        return s;
    }
    uint32_t service(const ClawSceneDisplayResizeCall &q) {
        if (!d) {
            c.fault = 1;
            throw Failure{};
        }
        auto v = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        return v;
    }
    static uint32_t displayService(ClawSceneDisplayContext *, const ClawSceneDisplayCall *q, void *u) {
        return static_cast<Run *>(u)->service(*q);
    }
    static uint32_t graphicsService(ClawGraphicsManagerLifecycleContext *, const ClawGraphicsManagerLifecycleCall *q,
                                    void *u) {
        ClawSceneDisplayResizeCall e{};
        e.function = q->function;
        e.receiver = q->receiver;
        e.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, 8, e.arguments);
        e.localMask = q->localMask;
        e.bufferCount = q->bufferCount;
        std::copy_n(q->buffers, 2, e.buffers);
        std::copy_n(q->bufferBytes, 2, e.bufferBytes);
        return static_cast<Run *>(u)->service(e);
    }
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        tick();
        uint32_t args[8]{};
        std::copy(a.begin(), a.end(), args);
        uint32_t out = 0;
        if (c.display) {
            auto x = *c.display;
            x.scene = c.scene;
            x.fault = 0;
            ClawGraphicsManagerLifecycleContext graphicsView{};
            auto *borrowed = c.graphics ? c.graphics : x.graphics;
            if (borrowed) {
                graphicsView = *borrowed;
                graphicsView.scene = c.scene;
                graphicsView.fault = 0;
                x.graphics = &graphicsView;
            }
            if (claw_scene_display_entry(f, t, args, uint32_t(a.size()), &x, displayService, this, &out)) {
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
        if (c.graphics) {
            auto x = *c.graphics;
            x.scene = c.scene;
            x.fault = 0;
            if (claw_graphics_manager_lifecycle_entry(f, t, args, uint32_t(a.size()), &x, graphicsService, this,
                                                      &out)) {
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
        ClawSceneDisplayResizeCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy_n(args, q.argumentCount, q.arguments);
        return service(q);
    }
    uint32_t virt(uint32_t t, uint32_t slot) {
        return invoke(get(get(t), slot), t);
    }
    bool admitted(const uint32_t *a) {
        return signedWord(a[0]) > 0 && signedWord(a[1]) > 0 && (a[2] == 8 || a[2] == 16 || a[2] == 24 || a[2] == 32);
    }
    void geometry(uint32_t p, const uint32_t *a, bool primary) {
        if (primary)
            put(p, 24, a[2]);
        else {
            put(p, 28, 0);
            put(p, 32, 0);
        }
        put(p, 16, a[0]);
        put(p, 20, a[1]);
        if (primary) {
            put(p, 28, 0);
            put(p, 32, 0);
        } else
            put(p, 24, a[2]);
        put(p, 36, a[0]);
        put(p, 40, a[1]);
    }
    uint32_t body(uint32_t f, uint32_t p, const uint32_t *a) {
        if (get(p, 16) == a[0] && get(p, 20) == a[1] && get(p, 24) == a[2])
            return 1;
        if (f == 0x4d4280) {
            invoke(0x4bc4f0, get(get(p, 12), 28), {get(p, 44)});
            put(p, 44, 0);
            if (get(p, 4) == 1) {
                auto parent = get(p, 12), primary = get(get(parent, 4), 16);
                auto surface = invoke(0x4bcf80, get(parent, 28), {get(primary, 44), 4});
                put(p, 44, surface);
                if (!surface)
                    return 0;
            }
            if (get(p, 4) != 1) {
                auto surface = invoke(0x4bc670, get(get(p, 12), 28), {a[0], a[1], a[2], 0, 0xffffffff});
                put(p, 44, surface);
                if (!surface)
                    return 0;
            }
            if (!admitted(a))
                return 0;
            geometry(p, a, false);
            return 1;
        }
        auto manager = get(get(p, 12), 28);
        if (!manager)
            return 0;
        invoke(0x4bc4f0, manager, {get(p, 44)});
        put(p, 44, 0);
        if (invoke(0x4bd1c0, manager, {a[0], a[1], a[2]}))
            return 0;
        auto mode = get(get(p, 12), 52) & 2 ? 2u : 1u;
        auto surface = invoke(0x4bc890, manager, {mode});
        put(p, 44, surface);
        if (!surface || !virt(surface, 20) || !admitted(a))
            return 0;
        geometry(p, a, true);
        return 1;
    }
};
} // namespace
extern "C" uint32_t claw_scene_display_resize_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                    ClawSceneDisplayResizeContext *c,
                                                    ClawSceneDisplayResizeDependency d, void *u, uint32_t *out) {
    if (!c || (f != 0x4d4280 && f != 0x4d5720))
        return 0;
    if (c->fault)
        return 0;
    if (!a || n != 3 || !out) {
        c->fault = 2;
        return 0;
    }
    uint32_t args[3];
    std::copy_n(a, 3, args);
    Run r{*c, d, u};
    try {
        *out = r.body(f, t, args);
    } catch (Failure &) {
    }
    return c->fault ? 0 : 1;
}
