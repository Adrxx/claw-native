#include "SceneStartupCompositionRuntime.h"
#include "AmbientAudioBackendRuntime.h"
#include <algorithm>
#include <cstring>
#include <vector>
namespace {
struct Failure {};
struct Run {
    ClawSceneStartupCompositionContext &c;
    ClawSceneStartupCompositionDependency dependency;
    void *user;
    uint32_t operations = 0;
    enum Kind { Base, Graphics, Palette, Image };
    std::vector<Kind> active;
    Run(ClawSceneStartupCompositionContext &c, ClawSceneStartupCompositionDependency d, void *u)
        : c(c), dependency(d), user(u) {
    }
    ClawSinglePlayerSceneContext base{};
    ClawSceneLifecycleContext life{};
    ClawSceneDisplayContext display{};
    ClawGraphicsManagerLifecycleContext graphics{};
    ClawPaletteResourceContext palette{};
    ClawAudioManagerLifecycleContext audio{};
    ClawWorldFileContext world{};
    ClawImageRegistryContext registry{};
    ClawCArrayContext arrays{};
    ClawBootyResultsContext collections{};
    ClawGameImageHost imageHost{};
    bool haveBase = false, haveLife = false, haveDisplay = false, haveGraphics = false, havePalette = false,
         haveAudio = false, haveWorld = false, haveRegistry = false, haveCollections = false;
    ClawGameImageGlobals *image = nullptr;
    [[noreturn]] void fail(uint32_t code = 1) {
        if (!c.fault)
            c.fault = code;
        throw Failure{};
    }
    void step() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000))
            fail(3);
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
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        return static_cast<Run *>(u)->span(t, n);
    }
    static uint32_t allocate(void *u, uint32_t n) {
        uint32_t a[] = {n};
        return static_cast<Run *>(u)->external(0x4f63ec, 0, a, 1);
    }
    static void release(void *u, uint32_t t) {
        uint32_t a[] = {t};
        static_cast<Run *>(u)->external(0x4f6428, 0, a, 1);
    }
    static uint32_t call(void *u, ClawSceneActorCall q) {
        return static_cast<Run *>(u)->invoke(q.function, q.receiver, q.arguments, q.argumentCount);
    }
    static uint32_t clock(void *u) {
        auto &r = *static_cast<Run *>(u);
        if (!r.c.scene.readClock)
            r.fail();
        r.publish();
        auto v = r.c.scene.readClock(r.c.scene.context);
        r.import();
        return v;
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, call, clock};
    }
    static constexpr uint32_t ga[] = {0x538418, 0x54316c, 0x537210, 0x53c9c0, 0x5349dc, 0x537e88, 0x534ca4,
                                      0x52be14, 0x52be18, 0x537204, 0x53ec44, 0x537268, 0x537214, 0x537218,
                                      0x53721c, 0x537220, 0x537228, 0x537224, 0x53722c, 0x537230, 0x537264};
    static constexpr uint32_t ca[] = {0x537e88, 0x537200, 0x537204, 0x53720c, 0x537258, 0x5430c8,
                                      0x5430c4, 0x52be14, 0x52be18, 0x53c25c, 0x53c260, 0x53c264};
    template <class T, size_t N> void words(T *p, const uint32_t (&addresses)[N], bool write) {
        if (!p)
            return;
        uint32_t values[N];
        if (write)
            std::memcpy(values, p, N * 4);
        for (size_t i = 0; i < N; ++i)
            if (write)
                put(addresses[i], values[i]);
            else
                values[i] = get(addresses[i]);
        if (!write)
            std::memcpy(p, values, N * 4);
    }
    void sync(Kind k, bool write) {
        if (k == Base && haveBase) {
            words(base.globals, ga, write);
            words(base.camera, ca, write);
        }
        if (k == Graphics && haveGraphics && graphics.globals) {
            auto *g = graphics.globals;
            uint32_t a[] = {0x541398, 0x541374, 0x54135c, 0x541360, 0x541364, 0x541368, 0x54136c, 0x541370};
            uint32_t v[8];
            if (write)
                std::memcpy(v, g, 32);
            for (uint32_t i = 0; i < 8; ++i)
                if (write)
                    put(a[i], v[i]);
                else
                    v[i] = get(a[i]);
            if (!write)
                std::memcpy(g, v, 32);
        }
        if (k == Palette && havePalette && palette.globals) {
            if (write)
                put(0x541374, palette.globals->cooperativeHolder);
            else
                palette.globals->cooperativeHolder = get(0x541374);
        }
        if (k == Image && image) {
            if (write) {
                put(0x5430c4, image->animationDelta);
                std::copy_n(image->directDrawFX, 25, span(0x543108, 25));
                put(0x54316c, image->surfaceLoadFlags);
                put(0x543170, image->surfaceColorKey);
                std::copy_n(image->compressedEffect, 4, span(0x5430b0, 4));
                std::copy_n(image->embeddedPalette, 256, span(0x5427b0, 256));
            } else {
                image->animationDelta = get(0x5430c4);
                std::copy_n(span(0x543108, 25), 25, image->directDrawFX);
                image->surfaceLoadFlags = get(0x54316c);
                image->surfaceColorKey = get(0x543170);
                std::copy_n(span(0x5430b0, 4), 4, image->compressedEffect);
                std::copy_n(span(0x5427b0, 256), 256, image->embeddedPalette);
            }
        }
    }
    void publish() {
        for (auto k : active)
            sync(k, true);
    }
    void import() {
        for (auto k : {Base, Graphics, Palette, Image})
            sync(k, false);
    }
    struct Scope {
        Run &r;
        Kind k;
        Scope(Run &r, Kind k) : r(r), k(k) {
            r.publish();
            r.sync(k, false);
            r.active.push_back(k);
        }
        ~Scope() {
            if (!r.c.fault) {
                r.publish();
                r.import();
            }
            r.active.pop_back();
        }
    };
    void initialize() {
        auto h = host();
        if (c.startup) {
            base = *c.startup;
            base.host = h;
            base.fault = 0;
            haveBase = true;
        }
        if (c.graphics) {
            graphics = *c.graphics;
            graphics.scene = h;
            graphics.fault = 0;
            haveGraphics = true;
        }
        if (c.palette) {
            palette = *c.palette;
            palette.scene = h;
            palette.fault = 0;
            havePalette = true;
        }
        if (c.audio) {
            audio = *c.audio;
            audio.scene = h;
            audio.fault = 0;
            haveAudio = true;
        } else {
            audio.scene = h;
            audio.maximumTraversal = c.maximumOperations;
            haveAudio = true;
        }
        if (c.arrays)
            arrays = *c.arrays;
        arrays.scene = h;
        arrays.fault = 0;
        if (c.world) {
            world = *c.world;
            world.scene = h;
            world.arrays = &arrays;
            world.fault = 0;
            haveWorld = true;
        }
        if (c.images)
            image = c.images;
        else if (c.imageRegistry)
            image = c.imageRegistry->images;
        else if (c.display)
            image = c.display->image;
        if (c.display) {
            display = *c.display;
            display.scene = h;
            display.graphics = haveGraphics ? &graphics : nullptr;
            display.image = image;
            display.fault = 0;
            haveDisplay = true;
        }
        if (c.imageRegistry) {
            registry = *c.imageRegistry;
            registry.scene = h;
            registry.arrays = &arrays;
            registry.images = image;
            imageHost = {h, this, imageService};
            registry.imageHost = image ? &imageHost : nullptr;
            registry.fault = 0;
            haveRegistry = true;
        }
        if (haveGraphics)
            graphics.palette = havePalette ? &palette : nullptr;
        if (c.collections) {
            collections = *c.collections;
            collections.scene = h;
            collections.fault = 0;
            haveCollections = true;
        }
        if (c.lifecycle) {
            life = *c.lifecycle;
            life.scene = h;
            life.display = haveDisplay ? &display : nullptr;
            life.graphics = haveGraphics ? &graphics : nullptr;
            life.audio = &audio;
            life.palette = havePalette ? &palette : nullptr;
            life.world = haveWorld ? &world : nullptr;
            life.image = image;
            life.fault = 0;
            haveLife = true;
        }
    }
    uint32_t service(ClawSceneStartupCompositionCall &q) {
        step();
        publish();
        if (!dependency)
            fail();
        uint32_t v = dependency(&c, &q, user);
        if (c.fault)
            throw Failure{};
        import();
        return v;
    }
    uint32_t external(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        ClawSceneStartupCompositionCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        if (n > 8)
            fail(2);
        std::copy_n(a, n, q.arguments);
        return service(q);
    }
    uint32_t invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        uint32_t out = 0;
        if (dispatch(f, t, a, n, out))
            return out;
        return external(f, t, a, n);
    }
    template <class T> uint32_t forward(const T &e) {
        publish();
        uint32_t out = 0;
        if (!e.localMask && dispatch(e.function, e.receiver, e.arguments, e.argumentCount, out))
            return out;
        ClawSceneStartupCompositionCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        q.localMask = e.localMask;
        q.bufferCount = e.bufferCount;
        for (uint32_t i = 0; i < e.bufferCount; ++i) {
            q.buffers[i] = e.buffers[i];
            q.bufferBytes[i] = e.bufferBytes[i];
        }
        return service(q);
    }
    static uint32_t baseService(ClawSinglePlayerSceneContext *, ClawSinglePlayerSceneCall e, void *u) {
        auto &r = *static_cast<Run *>(u);
        r.publish();
        uint32_t out = 0;
        if (!e.localMask && r.dispatch(e.function, e.receiver, e.arguments, e.argumentCount, out))
            return out;
        ClawSceneStartupCompositionCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        q.localMask = e.localMask;
        q.bufferCount = e.bufferCount;
        uint32_t b = 0;
        if (e.localMask & 256) {
            uint32_t slot = 0;
            for (uint32_t i = 0; i < e.argumentCount; ++i)
                if (e.localMask & (1u << i))
                    ++slot;
            q.buffers[b] = e.buffers[slot];
            q.bufferBytes[b++] = e.bufferBytes[slot];
        }
        for (uint32_t i = 0; i < e.argumentCount; ++i)
            if (e.localMask & (1u << i)) {
                uint32_t slot = 0;
                for (uint32_t j = 0; j < i; ++j)
                    if (e.localMask & (1u << j))
                        ++slot;
                q.buffers[b] = e.buffers[slot];
                q.bufferBytes[b++] = e.bufferBytes[slot];
            }
        while (b < e.bufferCount) {
            q.buffers[b] = e.buffers[b];
            q.bufferBytes[b] = e.bufferBytes[b];
            ++b;
        }
        return r.service(q);
    }
    static uint32_t displayService(ClawSceneDisplayContext *, const ClawSceneDisplayCall *e, void *u) {
        return static_cast<Run *>(u)->forward(*e);
    }
    static uint32_t graphicsService(ClawGraphicsManagerLifecycleContext *, const ClawGraphicsManagerLifecycleCall *e,
                                    void *u) {
        return static_cast<Run *>(u)->forward(*e);
    }
    static uint32_t paletteService(ClawPaletteResourceContext *, const ClawPaletteResourceCall *e, void *u) {
        return static_cast<Run *>(u)->forward(*e);
    }
    static uint32_t lifecycleService(ClawSceneLifecycleContext *, const ClawSceneLifecycleCall *e, void *u) {
        return static_cast<Run *>(u)->forward(*e);
    }
    static uint32_t collectionService(ClawBootyResultsContext *, const ClawBootyResultsCall *e, void *u) {
        return static_cast<Run *>(u)->forward(*e);
    }
    static uint32_t arrayService(ClawCArrayContext *, const ClawCArrayCall *e, void *u) {
        return static_cast<Run *>(u)->external(e->function, e->receiver, e->arguments, e->argumentCount);
    }
    static uint32_t poolService(ClawAmbientAudioBackendContext *, const ClawAmbientAudioBackendCall *e, void *u) {
        return static_cast<Run *>(u)->external(e->function, e->receiver, e->arguments, e->argumentCount);
    }
    static uint32_t audioService(ClawAudioManagerLifecycleContext *, const ClawAudioManagerLifecycleCall *e, void *u) {
        auto &r = *static_cast<Run *>(u);
        return r.external(e->function, e->receiver, e->arguments, e->argumentCount);
    }
    static uint32_t worldService(ClawWorldFileContext *, const ClawWorldFileCall *e, void *u) {
        auto &r = *static_cast<Run *>(u);
        uint32_t out = 0;
        if (!e->size && !e->temporary && r.dispatch(e->function, e->receiver, e->arguments, e->argumentCount, out))
            return out;
        ClawSceneStartupCompositionCall q{};
        q.function = e->function;
        q.receiver = e->receiver;
        q.argumentCount = e->argumentCount;
        std::copy_n(e->arguments, e->argumentCount, q.arguments);
        q.name = e->name;
        if (e->temporary) {
            q.localMask = 256;
            q.bufferCount = 1;
            q.buffers[0] = e->temporary;
            q.bufferBytes[0] = 16;
        }
        if (e->size) {
            q.localMask |= 2;
            q.buffers[q.bufferCount] = e->size;
            q.bufferBytes[q.bufferCount++] = 4;
        }
        return r.service(q);
    }
    static uint32_t imageService(void *u, ClawGameImageCall e) {
        auto &r = *static_cast<Run *>(u);
        uint32_t out = 0;
        if (!e.source && !e.destination && r.dispatch(e.function, e.receiver, e.arguments, e.argumentCount, out))
            return out;
        ClawSceneStartupCompositionCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        if (e.function == 0x546d58) {
            q.localMask = 3;
            q.bufferCount = 2;
            q.buffers[0] = e.destination;
            q.buffers[1] = e.source;
            q.bufferBytes[0] = q.bufferBytes[1] = 16;
        } else if (e.source || e.destination) {
            if (e.destination) {
                q.localMask |= 1;
                q.buffers[q.bufferCount] = e.destination;
                q.bufferBytes[q.bufferCount++] = 16;
            }
            if (e.source) {
                q.localMask |= e.function == 0x4b9d80 ? 8u : 4u;
                q.buffers[q.bufferCount] = e.source;
                q.bufferBytes[q.bufferCount++] =
                    e.function != 0x4b9ce0 && e.function != 0x4bffa0 && e.function != 0x4b9d80 ? 8u : 16u;
            }
        }
        return r.service(q);
    }
    static bool imageEntry(uint32_t f) {
        switch (f) {
        case 0x4d2890:
        case 0x4b9380:
        case 0x4b9180:
        case 0x4b9730:
        case 0x4bb0e0:
        case 0x4b9990:
        case 0x4bc490:
        case 0x4bc520:
        case 0x4bf9c0:
        case 0x4bf310:
        case 0x4bfbf0:
        case 0x4bfc50:
        case 0x4c6130:
        case 0x4d25e0:
        case 0x4d22f0:
        case 0x4ce3d0:
        case 0x4d2410:
            return true;
        default:
            return false;
        }
    }
    bool dispatch(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, uint32_t &out) {
        step();
        if (n > 8 || (n && !a))
            fail(2);
        publish();
        if (f == 0x4ca280) {
            if (n != 1)
                fail(2);
            uint32_t parent = get(t + 12);
            out = 0;
            if (!parent)
                return true;
            uint32_t manager = get(parent + 32);
            if (!a[0] && (!manager || !get(manager + 120)))
                return true;
            put(t + 48, manager ? 0 : 1);
            put(t + 44, manager);
            put(0x532c10, 100);
            out = 1;
            return true;
        }
        if (f == 0x4cf7e0) {
            if (n)
                fail(2);
            out = get(t + 44) || get(t + 48);
            return true;
        }
        if (f == 0x4f701d) {
            if (n)
                fail(2);
            out = 0x5105d8;
            return true;
        }
        if (f == 0x4b47e0 && t == 0 && (!c.scene.lookup || !c.scene.lookup(c.scene.context, 20, 1))) {
            if (n != 2)
                fail(2);
            const uint32_t args[] = {0, 20, 0};
            uint32_t hr = external(0x4f4480, 0, args, 3);
            if (hr) {
                out = 0;
                return true;
            }
            fail(1);
        }
        if (f == 0x4bc120) {
            if (n)
                fail(2);
            uint32_t fault = 0;
            if (!claw_graphics_manager_construct(t, host(), &fault, &out) || fault)
                fail(fault ? fault : 1);
            return true;
        }
        if (haveBase) {
            Scope scope(*this, Base);
            base.fault = 0;
            if (claw_single_player_scene_entry(f, t, a, n, &base, baseService, this, &out)) {
                if (base.fault)
                    fail(base.fault);
                return true;
            }
        }
        if (haveDisplay) {
            Scope gs(*this, Graphics);
            Scope is(*this, Image);
            display.fault = 0;
            if (claw_scene_display_entry(f, t, a, n, &display, displayService, this, &out)) {
                return true;
            }
            if (display.fault)
                fail(display.fault);
        }
        if (haveGraphics) {
            Scope scope(*this, Graphics);
            graphics.fault = 0;
            if (claw_graphics_manager_lifecycle_entry(f, t, a, n, &graphics, graphicsService, this, &out))
                return true;
            if (graphics.fault)
                fail(graphics.fault);
        }
        if (havePalette) {
            Scope scope(*this, Palette);
            palette.fault = 0;
            uint32_t handled = claw_palette_resource_entry(f, t, a, n, &palette, paletteService, this, &out);
            if (palette.fault)
                fail(palette.fault);
            if (handled)
                return true;
        }
        audio.fault = 0;
        if (claw_audio_manager_lifecycle_entry(f, t, a, n, &audio, audioService, this, &out))
            return true;
        if (audio.fault)
            fail(audio.fault);
        if (haveWorld && n <= 4) {
            ClawWorldFileArguments q{};
            q.count = n;
            std::copy_n(a, n, q.words);
            world.fault = 0;
            if (claw_world_file_entry(f, t, q, &world, worldService, this, &out))
                return true;
            if (world.fault)
                fail(world.fault);
        }
        if (haveRegistry && n <= 5) {
            Scope scope(*this, Image);
            ClawImageRegistryArguments q{};
            q.count = n;
            std::copy_n(a, n, q.words);
            registry.fault = 0;
            if (claw_image_registry_entry(f, t, q, &registry, &out))
                return true;
            if (registry.fault)
                fail(registry.fault);
        }
        if (image && imageEntry(f)) {
            Scope scope(*this, Image);
            ClawGameImageArguments q{};
            q.count = n;
            std::copy_n(a, n, q.words);
            uint32_t fault = 0;
            ClawGameImageHost h{host(), this, imageService};
            if (!claw_game_image_entry(f, t, q, image, h, &fault, &out) || fault)
                fail(fault ? fault : 1);
            return true;
        }
        if (haveLife) {
            sync(Palette, false);
            Scope gs(*this, Graphics);
            Scope is(*this, Image);
            life.fault = 0;
            if (claw_scene_lifecycle_entry(f, t, a, n, &life, lifecycleService, this, &out))
                return true;
            if (life.fault)
                fail(life.fault);
        }
        if (haveCollections && (f == 0x4c89e0 || f == 0x4c89f0)) {
            collections.fault = 0;
            if (!claw_booty_results_entry(f, t, a, n, &collections, collectionService, this, &out) || collections.fault)
                fail(collections.fault ? collections.fault : 1);
            return true;
        }
        if (f == 0x4f58ab || f == 0x4f5915 || f == 0x4f582f) {
            arrays.fault = 0;
            if (!claw_carray_entry(f, t, n ? a[0] : 0, n > 1 ? a[1] : 0, 0, &arrays, arrayService, this, &out) ||
                arrays.fault)
                fail(arrays.fault ? arrays.fault : 1);
            return true;
        }
        if (f == 0x4f51c5 || f == 0x4f5212 || f == 0x4f5172 || f == 0x4f5aa8 || f == 0x4f5ac8) {
            ClawAmbientAudioBackendContext q{};
            q.scene = host();
            q.maximumTraversal = c.maximumOperations;
            if (!claw_ambient_audio_backend_entry(f, t, a, n, &q, poolService, this, &out) || q.fault)
                fail(q.fault ? q.fault : 1);
            return true;
        }
        return false;
    }
};
} // namespace
extern "C" uint32_t claw_scene_startup_composition_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                         ClawSceneStartupCompositionContext *c,
                                                         ClawSceneStartupCompositionDependency d, void *u,
                                                         uint32_t *out) {
    if (!c || !out || c->fault)
        return 0;
    Run r{*c, d, u};
    try {
        r.initialize();
        bool handled = r.dispatch(f, t, a, n, *out);
        if (!handled)
            return 0;
        r.publish();
        for (auto k : {Run::Base, Run::Graphics, Run::Palette, Run::Image})
            r.sync(k, false);
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
