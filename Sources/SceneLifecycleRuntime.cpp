#include "SceneLifecycleRuntime.h"
#include "ActorDestruction.h"
#include "AmbientAudioBackendRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
struct Run;
uint32_t displayService(ClawSceneDisplayContext *, const ClawSceneDisplayCall *, void *);
uint32_t graphicsService(ClawGraphicsManagerLifecycleContext *, const ClawGraphicsManagerLifecycleCall *, void *);
uint32_t audioService(ClawAudioManagerLifecycleContext *, const ClawAudioManagerLifecycleCall *, void *);
uint32_t paletteService(ClawPaletteResourceContext *, const ClawPaletteResourceCall *, void *);
uint32_t worldService(ClawWorldFileContext *, const ClawWorldFileCall *, void *);
uint32_t poolService(ClawAmbientAudioBackendContext *, const ClawAmbientAudioBackendCall *, void *);
struct Run {
    ClawSceneLifecycleContext &c;
    ClawSceneLifecycleDependency dependency;
    void *user;
    uint32_t operations = 0;
    uint32_t *temporary = nullptr;
    static constexpr uint32_t temporaryToken = 0xfffff000;
    static int32_t signedWord(uint32_t x) {
        int32_t y;
        std::memcpy(&y, &x, 4);
        return y;
    }
    void tick() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000)) {
            c.fault = 3;
            throw Failure{};
        }
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failure{};
        if (t == temporaryToken && temporary && n <= 1)
            return temporary;
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failure{};
        }
        return p;
    }
    uint32_t get(uint32_t t, uint32_t b = 0) {
        return *span(t + b);
    }
    void set(uint32_t t, uint32_t b, uint32_t v) {
        *span(t + b) = v;
    }
    uint32_t service(ClawSceneLifecycleCall &q) {
        if (c.fault)
            throw Failure{};
        if (dependency)
            return dependency(&c, &q, user);
        if (!q.localMask && q.argumentCount <= 4 && c.scene.call) {
            ClawSceneActorCall a{};
            a.function = q.function;
            a.receiver = q.receiver;
            a.argumentCount = q.argumentCount;
            std::copy_n(q.arguments, q.argumentCount, a.arguments);
            return c.scene.call(c.scene.context, a);
        }
        c.fault = 1;
        throw Failure{};
    }
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        uint32_t args[8]{};
        std::copy(a.begin(), a.end(), args);
        if (owned(f))
            return entry(f, t, args, uint32_t(a.size()));
        uint32_t out = 0;
        if (c.display &&
            (f == 0x4cf760 || f == 0x4cf730 || f == 0x4bc810 || f == 0x4bb060 || f == 0x4cabe0 || f == 0x45fe40)) {
            auto &x = *c.display;
            x.scene = heap();
            if (!claw_scene_display_entry(f, t, args, uint32_t(a.size()), &x, displayService, this, &out) || x.fault) {
                c.fault = x.fault ? x.fault : 2;
                throw Failure{};
            }
            return out;
        }
        if (c.graphics && f == 0x4bc1b0) {
            auto &x = *c.graphics;
            x.scene = heap();
            if (!claw_graphics_manager_lifecycle_entry(f, t, args, uint32_t(a.size()), &x, graphicsService, this,
                                                       &out) ||
                x.fault) {
                c.fault = x.fault ? x.fault : 2;
                throw Failure{};
            }
            return out;
        }
        if (c.audio && f == 0x4b4770) {
            auto &x = *c.audio;
            x.scene = heap();
            if (!claw_audio_manager_lifecycle_entry(f, t, args, uint32_t(a.size()), &x, audioService, this, &out) ||
                x.fault) {
                c.fault = x.fault ? x.fault : 2;
                throw Failure{};
            }
            return out;
        }
        if (c.palette && f == 0x4d47f0) {
            auto &x = *c.palette;
            x.scene = heap();
            if (!claw_palette_resource_entry(f, t, args, uint32_t(a.size()), &x, paletteService, this, &out) ||
                x.fault) {
                c.fault = x.fault ? x.fault : 2;
                throw Failure{};
            }
            return out;
        }
        if (c.world && (f == 0x4cdd10 || f == 0x4cde00)) {
            auto &x = *c.world;
            x.scene = heap();
            ClawWorldFileArguments a2{};
            a2.count = uint32_t(a.size());
            std::copy_n(args, a2.count, a2.words);
            if (!claw_world_file_entry(f, t, a2, &x, worldService, this, &out) || x.fault) {
                c.fault = x.fault ? x.fault : 2;
                throw Failure{};
            }
            return out;
        }
        if (f == 0x4f5ac8 || f == 0x4f5172) {
            ClawAmbientAudioBackendContext x{};
            x.scene = heap();
            x.maximumTraversal = c.maximumOperations;
            if (!claw_ambient_audio_backend_entry(f, t, args, uint32_t(a.size()), &x, poolService, this, &out) ||
                x.fault) {
                c.fault = x.fault ? x.fault : 2;
                throw Failure{};
            }
            return out;
        }
        ClawSceneLifecycleCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy_n(args, q.argumentCount, q.arguments);
        if (t == temporaryToken) {
            q.receiver = 0;
            q.localMask = 256;
            q.bufferCount = 1;
            q.buffers[0] = temporary;
            q.bufferBytes[0] = 4;
        }
        return service(q);
    }
    uint32_t virt(uint32_t t, uint32_t offset, std::initializer_list<uint32_t> a = {}) {
        return invoke(get(get(t), offset), t, a);
    }
    static uint32_t *lookup(void *v, uint32_t t, uint32_t n) {
        return static_cast<Run *>(v)->span(t, n);
    }
    static uint32_t allocate(void *v, uint32_t n) {
        return static_cast<Run *>(v)->invoke(0x4f63ec, 0, {n});
    }
    static uint32_t clock(void *v) {
        auto &r = *static_cast<Run *>(v);
        if (!r.c.scene.readClock) {
            r.c.fault = 1;
            throw Failure{};
        }
        return r.c.scene.readClock(r.c.scene.context);
    }
    ClawSceneActorHost heap() {
        return {this, lookup, allocate, free, callback, clock};
    }
    static void free(void *v, uint32_t t) {
        static_cast<Run *>(v)->invoke(0x4f6428, 0, {t});
    }
    static uint32_t callback(void *v, ClawSceneActorCall e) {
        auto &r = *static_cast<Run *>(v);
        ClawSceneLifecycleCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, q.argumentCount, q.arguments);
        return r.service(q);
    }
    void stringDestroy(uint32_t t) {
        ClawActorDestructionGlobals g{};
        g.emptyStringToken = get(0x52e1c8) + 12;
        ClawSceneActorHost h{this, lookup, nullptr, free, callback, nullptr};
        uint32_t fault = 0, out = 0;
        if (!claw_actor_destruction_entry(0x4f6584, t, 0, &g, h, &fault, &out) || fault) {
            c.fault = fault ? fault : 2;
            throw Failure{};
        }
    }
    void stringRelease(uint32_t t) {
        if (get(t) - 12 == get(0x52e1c8))
            return;
        stringDestroy(t);
        set(t, 0, get(0x52e1cc));
    }
    void stringAssign(uint32_t t, uint32_t source) {
        uint32_t data = get(source);
        if (get(t) == data)
            return;
        uint32_t oldHeader = get(t) - 12;
        if ((signedWord(get(oldHeader)) < 0 && oldHeader != get(0x52e1c8)) || signedWord(get(data - 12)) < 0) {
            invoke(0x4f6650, t, {get(data - 8), data});
            return;
        }
        stringRelease(t);
        data = get(source);
        set(t, 0, data);
        set(data - 12, 0, get(data - 12) + 1);
    }
    void next(uint32_t map, uint32_t *position, uint32_t *key, uint32_t *value, uint32_t keyToken = temporaryToken) {
        uint32_t node = *position;
        if (node == 0xffffffff) {
            uint32_t bucket = 0;
            while (bucket < get(map, 8)) {
                tick();
                node = get(get(map, 4), bucket * 4);
                if (node)
                    break;
                ++bucket;
            }
        }
        uint32_t following = get(node);
        if (!following) {
            uint32_t bucket = get(node, 4) + 1;
            while (bucket < get(map, 8)) {
                tick();
                following = get(get(map, 4), bucket * 4);
                if (following)
                    break;
                ++bucket;
            }
        }
        *position = following;
        uint32_t *saved = temporary;
        if (keyToken == temporaryToken)
            temporary = key;
        stringAssign(keyToken, node + 8);
        temporary = saved;
        *value = get(node, 12);
    }
    void mapClear(uint32_t t) {
        if (get(t, 4)) {
            uint32_t bucket = 0;
            while (bucket < get(t, 8)) {
                tick();
                uint32_t node = get(get(t, 4), bucket * 4);
                while (node) {
                    tick();
                    stringDestroy(node + 8);
                    node = get(node);
                }
                ++bucket;
            }
            invoke(0x4f6428, 0, {get(t, 4)});
            set(t, 4, 0);
        }
        set(t, 12, 0);
        set(t, 16, 0);
        invoke(0x4f5ac8, get(t, 20));
        set(t, 20, 0);
    }
    void controllerClear(uint32_t t, bool palette) {
        uint32_t position = get(t, 28) ? 0xffffffffu : 0, key = get(0x52e1cc), value = 0;
        while (position) {
            tick();
            next(t + 16, &position, &key, &value);
            if (value)
                virt(value, 4, {1});
        }
        mapClear(t + 16);
        if (palette)
            set(t, 100, 0);
        uint32_t *saved = temporary;
        temporary = &key;
        stringDestroy(temporaryToken);
        temporary = saved;
    }
    void baseFinish(uint32_t t) {
        set(t, 4, 0xffffffff);
        set(t, 8, 0);
        set(t, 12, 0);
        set(t, 0, 0x50becc);
    }
    void cleanup(uint32_t t) {
        for (uint32_t offset : {40u, 32u, 4u, 8u, 12u, 16u, 20u, 24u, 44u, 36u}) {
            uint32_t object = get(t, offset);
            if (object) {
                virt(object, offset == 32 ? 0 : 4, {1});
                set(t, offset, 0);
            }
        }
        uint32_t graphics = get(t, 28);
        if (graphics) {
            invoke(0x4bc1b0, graphics);
            invoke(0x4f6428, 0, {graphics});
            set(t, 28, 0);
        }
    }
    static bool owned(uint32_t f) {
        switch (f) {
        case 0x4ceef0:
        case 0x4ce9c0:
        case 0x4ce9a0:
        case 0x4cefc0:
        case 0x4cf0a0:
        case 0x4cf0c0:
        case 0x4d4370:
        case 0x4cf160:
        case 0x4cf180:
        case 0x4cf150:
        case 0x4cf940:
        case 0x4cf960:
        case 0x4cf930:
        case 0x4cf9d0:
        case 0x4cf9f0:
        case 0x4cdf30:
        case 0x4cdf40:
        case 0x4cf800:
        case 0x4cf820:
        case 0x4ca2e0:
        case 0x4ca300:
        case 0x4cfa80:
        case 0x4d0240:
        case 0x4d6290:
        case 0x4f5e1e:
        case 0x4f61a1:
        case 0x4f61f3:
        case 0x4f5d00:
        case 0x4f667d:
        case 0x4f64ba:
        case 0x4cf8a0:
        case 0x4cf8c0:
        case 0x4cf280:
        case 0x4cf2a0:
        case 0x4f565f:
            return true;
        default:
            return false;
        }
    }
    uint32_t entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        auto need = [&](uint32_t k) {
            if (n != k) {
                c.fault = 2;
                throw Failure{};
            }
        };
        switch (f) {
        case 0x4ceef0:
            need(0);
            cleanup(t);
            return 0;
        case 0x4ce9c0:
            need(0);
            set(t, 0, 0x513ab8);
            cleanup(t);
            set(t, 0, 0x50becc);
            return 0;
        case 0x4ce9a0:
            need(1);
            entry(0x4ce9c0, t, nullptr, 0);
            if (a[0] & 1)
                invoke(0x4f6428, 0, {t});
            return t;
        case 0x4cefc0:
            need(0);
            {
                uint32_t holder = get(t, 4);
                if (!holder || !get(t, 8) || !get(t, 12) || !get(t, 16) || !get(t, 20))
                    return 0;
                return virt(holder, 20) && get(t, 36);
            }
        case 0x4cf0a0:
        case 0x4cf160:
        case 0x4cf940:
        case 0x4cf9d0:
        case 0x4cf800:
        case 0x4cf8a0:
        case 0x4cf280:
            need(1);
            {
                uint32_t destructor = f == 0x4cf0a0   ? 0x4cf0c0
                                      : f == 0x4cf160 ? 0x4cf180
                                      : f == 0x4cf940 ? 0x4cf960
                                      : f == 0x4cf9d0 ? 0x4cf9f0
                                      : f == 0x4cf8a0 ? 0x4cf8c0
                                      : f == 0x4cf280 ? 0x4cf2a0
                                                      : 0x4cf820;
                entry(destructor, t, nullptr, 0);
                if (a[0] & 1)
                    invoke(0x4f6428, 0, {t});
                return t;
            }
        case 0x4cf8c0:
        case 0x4cf2a0:
            need(0);
            set(t, 0, f == 0x4cf8c0 ? 0x513c20 : 0x513be8);
            invoke(f == 0x4cf8c0 ? 0x4c89e0 : 0x4c89f0, t);
            entry(0x4f565f, t + 16, nullptr, 0);
            baseFinish(t);
            return 0;
        case 0x4f565f:
            need(0);
            set(t, 0, 0x5107bc);
            invoke(0x4f5172, t);
            set(t, 0, 0x50becc);
            return 0;
        case 0x4cf0c0:
            need(0);
            set(t, 0, 0x513b28);
            controllerClear(t, true);
            for (uint32_t offset : {72u, 44u, 16u})
                entry(0x4f61f3, t + offset, nullptr, 0);
            baseFinish(t);
            return 0;
        case 0x4cf180:
            need(0);
            set(t, 0, 0x513b88);
            entry(0x4cfa80, t, nullptr, 0);
            entry(0x4f61f3, t + 16, nullptr, 0);
            baseFinish(t);
            return 0;
        case 0x4cf960:
            need(0);
            set(t, 0, 0x513b60);
            controllerClear(t, false);
            entry(0x4f61f3, t + 16, nullptr, 0);
            baseFinish(t);
            return 0;
        case 0x4cf9f0:
            need(0);
            set(t, 0, 0x513ad8);
            entry(0x4cdf30, t, nullptr, 0);
            entry(0x4f5d00, t + 16, nullptr, 0);
            baseFinish(t);
            return 0;
        case 0x4cf820:
            need(0);
            set(t, 0, 0x513b00);
            entry(0x4ca2e0, t, nullptr, 0);
            entry(0x4f5d00, t + 16, nullptr, 0);
            baseFinish(t);
            return 0;
        case 0x4d4370:
            need(0);
            controllerClear(t, true);
            return 0;
        case 0x4d0240:
        case 0x4d6290:
        case 0x4cdf30:
        case 0x4cdf40:
        case 0x4ca300:
            need(0);
            controllerClear(t, false);
            return 0;
        case 0x4ca2e0:
            need(0);
            controllerClear(t, false);
            set(t, 44, 0);
            return 0;
        case 0x4cfa80:
            need(0);
            virt(t, 88);
            set(0x54316c, 0, 0);
            set(0x543170, 0, 0);
            if (c.image)
                c.image->surfaceLoadFlags = c.image->surfaceColorKey = 0;
            return 0;
        case 0x4cf150:
            need(0);
            return 18;
        case 0x4cf930:
            need(0);
            return 19;
        case 0x4f5e1e:
            need(3);
            next(t, span(a[0]), span(a[1]), span(a[2]), a[1]);
            return 0;
        case 0x4f61a1:
            need(0);
            mapClear(t);
            return 0;
        case 0x4f61f3:
        case 0x4f5d00:
            need(0);
            set(t, 0, f == 0x4f61f3 ? 0x5105c4 : 0x510054);
            mapClear(t);
            set(t, 0, 0x50becc);
            return 0;
        case 0x4f667d:
            need(1);
            stringAssign(t, a[0]);
            return t;
        case 0x4f64ba:
            need(0);
            stringRelease(t);
            return 0;
        default:
            c.fault = 2;
            throw Failure{};
        }
    }
};
template <class T> uint32_t forward(Run &r, const T &e) {
    if (Run::owned(e.function) && !e.localMask)
        return r.entry(e.function, e.receiver, e.arguments, e.argumentCount);
    if (r.c.display && !e.localMask && (e.function == 0x4bc810 || e.function == 0x4bb060))
        return r.invoke(e.function, e.receiver, {e.arguments[0]});
    ClawSceneLifecycleCall q{};
    q.function = e.function;
    q.receiver = e.receiver;
    q.argumentCount = e.argumentCount;
    std::copy_n(e.arguments, q.argumentCount, q.arguments);
    q.localMask = e.localMask;
    q.bufferCount = e.bufferCount;
    for (uint32_t i = 0; i < e.bufferCount; ++i) {
        q.buffers[i] = e.buffers[i];
        q.bufferBytes[i] = e.bufferBytes[i];
    }
    return r.service(q);
}
uint32_t displayService(ClawSceneDisplayContext *, const ClawSceneDisplayCall *e, void *v) {
    return forward(*static_cast<Run *>(v), *e);
}
uint32_t graphicsService(ClawGraphicsManagerLifecycleContext *, const ClawGraphicsManagerLifecycleCall *e, void *v) {
    return forward(*static_cast<Run *>(v), *e);
}
uint32_t paletteService(ClawPaletteResourceContext *, const ClawPaletteResourceCall *e, void *v) {
    return forward(*static_cast<Run *>(v), *e);
}
uint32_t audioService(ClawAudioManagerLifecycleContext *, const ClawAudioManagerLifecycleCall *e, void *v) {
    auto &r = *static_cast<Run *>(v);
    ClawSceneLifecycleCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, q.argumentCount, q.arguments);
    return r.service(q);
}
uint32_t worldService(ClawWorldFileContext *, const ClawWorldFileCall *e, void *v) {
    auto &r = *static_cast<Run *>(v);
    ClawSceneLifecycleCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, q.argumentCount, q.arguments);
    return r.service(q);
}
uint32_t poolService(ClawAmbientAudioBackendContext *, const ClawAmbientAudioBackendCall *e, void *v) {
    auto &r = *static_cast<Run *>(v);
    ClawSceneLifecycleCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, q.argumentCount, q.arguments);
    return r.service(q);
}
} // namespace
struct HostRestoration {
    ClawSceneActorHost *pointers[12]{};
    ClawSceneActorHost values[12]{};
    uint32_t count = 0;
    void add(ClawSceneActorHost *p) {
        if (p) {
            pointers[count] = p;
            values[count] = *p;
            ++count;
        }
    }
    explicit HostRestoration(ClawSceneLifecycleContext &c) {
        add(c.display ? &c.display->scene : nullptr);
        add(c.graphics ? &c.graphics->scene : nullptr);
        add(c.audio ? &c.audio->scene : nullptr);
        add(c.palette ? &c.palette->scene : nullptr);
        add(c.world ? &c.world->scene : nullptr);
        auto *g = c.display ? c.display->graphics : nullptr;
        add(g ? &g->scene : nullptr);
        add(g && g->palette ? &g->palette->scene : nullptr);
        add(c.graphics && c.graphics->palette ? &c.graphics->palette->scene : nullptr);
        add(c.world && c.world->arrays ? &c.world->arrays->scene : nullptr);
    }
    ~HostRestoration() {
        while (count) {
            --count;
            *pointers[count] = values[count];
        }
    }
};
extern "C" uint32_t claw_scene_lifecycle_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                               ClawSceneLifecycleContext *c, ClawSceneLifecycleDependency d, void *u,
                                               uint32_t *out) {
    if (!c || !out || !Run::owned(f) || (n && !a) || n > 8)
        return 0;
    if (c->fault)
        return 0;
    HostRestoration restoration(*c);
    Run r{*c, d, u};
    try {
        *out = r.entry(f, t, a, n);
    } catch (Failure &) {
    }
    return c->fault ? 0 : 1;
}
