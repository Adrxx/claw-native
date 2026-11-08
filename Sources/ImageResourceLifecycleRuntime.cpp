#include "ImageResourceLifecycleRuntime.h"
#include "PlayerFadeBlendRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
template <class T> struct Restore {
    T &target;
    T old;
    explicit Restore(T &t) : target(t), old(t) {
    }
    ~Restore() {
        target = old;
    }
};
struct Run {
    ClawImageResourceLifecycleContext &c;
    ClawImageResourceLifecycleDependency dependency;
    void *user;
    uint32_t operations = 0;
    [[noreturn]] void fail(uint32_t n = 1) {
        if (!c.fault)
            c.fault = n;
        throw Failure{};
    }
    void step() {
        if (c.fault)
            throw Failure{};
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000))
            fail(3);
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        step();
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p)
            fail();
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    uint32_t scalar(uint32_t t) {
        uint32_t v = 0;
        for (uint32_t i = 0; i < 4; ++i)
            v |= uint32_t(byte(t + i)) << (i * 8);
        return v;
    }
    uint8_t byte(uint32_t t) {
        return reinterpret_cast<uint8_t *>(span(t & ~3u))[t & 3u];
    }
    void byte(uint32_t t, uint8_t v) {
        reinterpret_cast<uint8_t *>(span(t & ~3u))[t & 3u] = v;
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    uint32_t event(const ClawImageResourceLifecycleCall &q) {
        step();
        if (!dependency)
            fail();
        auto out = dependency(&c, &q, user);
        if (c.fault)
            throw Failure{};
        return out;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawImageResourceLifecycleCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        return invoke(q);
    }
    uint32_t method(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        return call(get(get(t) + slot), t, a);
    }
    static bool owned(uint32_t f) {
        switch (f) {
        case 0x4d2540:
        case 0x4d26c0:
        case 0x4d27a0:
        case 0x4ce900:
        case 0x4ce8e0:
        case 0x4bfc20:
        case 0x4d2790:
        case 0x4bf680:
            return true;
        default:
            return false;
        }
    }
    static bool gameOwned(uint32_t f) {
        switch (f) {
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
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        auto &r = *static_cast<Run *>(u);
        return r.c.scene.lookup ? r.c.scene.lookup(r.c.scene.context, t, n) : nullptr;
    }
    static uint32_t allocate(void *u, uint32_t n) {
        return static_cast<Run *>(u)->call(0x4f63ec, 0, {n});
    }
    static void release(void *u, uint32_t p) {
        static_cast<Run *>(u)->call(0x4f6428, 0, {p});
    }
    static uint32_t clock(void *u) {
        auto &r = *static_cast<Run *>(u);
        if (!r.c.scene.readClock)
            r.fail();
        return r.c.scene.readClock(r.c.scene.context);
    }
    static uint32_t hostCall(void *u, ClawSceneActorCall e) {
        ClawImageResourceLifecycleCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        return static_cast<Run *>(u)->invoke(q);
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, hostCall, clock};
    }
    uint32_t complete(uint32_t covered, uint32_t fault, uint32_t result) {
        if (fault)
            fail(fault);
        if (!covered)
            fail(2);
        return result;
    }
    template <class Q> uint32_t rich(const Q &e) {
        ClawImageResourceLifecycleCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        if (e.argumentCount > 10 || e.bufferCount > 2)
            fail(2);
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        q.localMask = e.localMask;
        q.bufferCount = e.bufferCount;
        for (uint32_t i = 0; i < q.bufferCount; ++i) {
            q.buffers[i] = e.buffers[i];
            q.bufferBytes[i] = e.bufferBytes[i];
        }
        return q.localMask ? event(q) : invoke(q);
    }
    static uint32_t loadingService(ClawImageControllerLoadingContext *, const ClawImageControllerLoadingCall *q,
                                   void *u) {
        return static_cast<Run *>(u)->rich(*q);
    }
    static uint32_t displayService(ClawSceneDisplayContext *, const ClawSceneDisplayCall *q, void *u) {
        return static_cast<Run *>(u)->rich(*q);
    }
    static uint32_t lifecycleService(ClawSceneLifecycleContext *, const ClawSceneLifecycleCall *q, void *u) {
        return static_cast<Run *>(u)->rich(*q);
    }
    static uint32_t stringService(ClawCStringAssignmentContext *, const ClawCStringAssignmentCall *q, void *u) {
        ClawImageResourceLifecycleCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        return static_cast<Run *>(u)->invoke(out);
    }
    static uint32_t poolService(ClawAmbientAudioBackendContext *, const ClawAmbientAudioBackendCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        if (q->outputWord)
            r.fail(2);
        ClawImageResourceLifecycleCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        return r.invoke(out);
    }
    static uint32_t storyService(ClawBootyStoryContext *, const ClawBootyStoryCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        if (q->name)
            r.fail(2);
        return r.rich(*q);
    }
    void imageFromRaw() {
        if (!c.images)
            return;
        c.images->surfaceLoadFlags = get(0x54316c);
        c.images->surfaceColorKey = get(0x543170);
        for (uint32_t i = 0; i < 4; ++i)
            c.images->compressedEffect[i] = get(0x5430b0 + i * 4);
        for (uint32_t i = 0; i < 256; ++i)
            c.images->embeddedPalette[i] = get(0x5427b0 + i * 4);
    }
    void imageToRaw() {
        if (!c.images)
            return;
        for (uint32_t i = 0; i < 256; ++i)
            put(0x5427b0 + i * 4, c.images->embeddedPalette[i]);
    }
    uint32_t imagePacket(const ClawGameImageCall &e) {
        ClawImageResourceLifecycleCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        if (e.destination) {
            if (!e.source || e.function != 0x546d58)
                fail(2);
            q.localMask = 3;
            q.bufferCount = 2;
            q.buffers[0] = e.destination;
            q.buffers[1] = e.source;
            q.bufferBytes[0] = q.bufferBytes[1] = 16;
        } else if (e.source) {
            if (e.argumentCount != 3 || e.arguments[2])
                fail(2);
            q.localMask = 4;
            q.bufferCount = 1;
            q.buffers[0] = e.source;
            q.bufferBytes[0] = 8;
        }
        return q.localMask ? event(q) : invoke(q);
    }
    static uint32_t imageService(void *u, ClawGameImageCall e) {
        auto &r = *static_cast<Run *>(u);
        r.imageToRaw();
        auto v = r.imagePacket(e);
        r.imageFromRaw();
        return v;
    }
    static uint32_t pcxService(ClawPCXImageContext *, const ClawPCXImageCall *q, void *u) {
        ClawGameImageCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        out.destination = q->destination;
        out.source = q->source;
        return static_cast<Run *>(u)->imagePacket(out);
    }
    static uint32_t blitService(ClawSurfaceBlitContext *, const ClawSurfaceBlitCall *q, void *u) {
        return static_cast<Run *>(u)->rich(*q);
    }
    uint32_t body(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        uint32_t required = f == 0x4bf680                    ? 4
                            : f == 0x4d2540                  ? 3
                            : f == 0x4d27a0                  ? 2
                            : f == 0x4ce8e0 || f == 0x4d2790 ? 1
                                                             : 0;
        if (n != required || (n && !a))
            fail(2);
        if (f == 0x4bf680) {
            uint32_t data = a[1], flags = scalar(data + 4), width = scalar(data + 8), height = scalar(data + 12);
            if ((width & 3) || get(t + 24) != width || get(t + 20) != height)
                return 0;
            uint32_t palette = get(a[0] + 0x878) ? a[0] + 0x478 : 0, depth = get(a[0] + 0x474), change = depth != 8;
            if (flags & 0x80) {
                if (a[2] <= 768)
                    return 0;
                uint32_t source = data + a[2] - 768;
                for (uint32_t i = 0; i < 256; ++i) {
                    for (uint32_t j = 0; j < 3; ++j)
                        byte(0x5423b0 + i * 4 + j, byte(source++));
                    byte(0x5423b0 + i * 4 + 3, 0);
                }
                palette = 0x5423b0;
            } else if (change && !palette)
                return 0;
            uint32_t temporary = 0;
            if (!change) {
                if (!call(0x4babe0, t, {data + 32}))
                    return 0;
            } else {
                temporary = call(0x4f63ec, 0, {width * height});
                if (!temporary)
                    return 0;
                if (!call(0x4bef50, 0, {temporary, data + 32, width, height})) {
                    call(0x4f6428, 0, {temporary});
                    return 0;
                }
                if (!call(0x4b9e90, t, {temporary, 8, palette, 1})) {
                    call(0x4f6428, 0, {temporary});
                    return 0;
                }
            }
            if (temporary)
                call(0x4f6428, 0, {temporary});
            if (flags & 1)
                call(0x4b9990, t, {a[3]});
            return 1;
        }
        if (f == 0x4bfc20) {
            auto p = get(t + 12);
            if (p)
                call(0x4f6428, 0, {p});
            p = get(t + 32);
            if (p)
                call(0x4f6428, 0, {p});
            return 0;
        }
        if (f == 0x4d26c0) {
            put(t + 16, 0);
            put(t + 20, 0);
            if (get(t + 44)) {
                auto surface = get(t + 44), parent = get(t + 12);
                call(0x4bc4f0, get(parent + 28), {surface});
                put(t + 44, 0);
            }
            auto compressed = get(t + 48);
            if (compressed) {
                call(0x4bfc20, compressed);
                call(0x4f6428, 0, {compressed});
                put(t + 48, 0);
            }
            return 0;
        }
        if (f == 0x4ce900) {
            put(t, 0x513a70);
            call(0x4d26c0, t);
            put(t + 4, 0xffffffff);
            put(t + 8, 0);
            put(t + 12, 0);
            put(t, 0x50becc);
            return 0;
        }
        if (f == 0x4ce8e0) {
            call(0x4ce900, t);
            if (a[0] & 1)
                call(0x4f6428, 0, {t});
            return t;
        }
        if (f == 0x4d2790) {
            auto surface = get(t + 44);
            if (surface)
                call(0x4b99d0, surface);
            return 0;
        }
        if (f == 0x4d2540) {
            uint32_t key = a[2] ? get(0x543170) : 0xffffffff, flags = get(0x54316c) ? 0x800 : 0;
            auto surface = call(0x4bc670, get(get(t + 12) + 28), {a[0], a[1], 0, flags, key});
            put(t + 44, surface);
            if (!surface)
                return 0;
            auto width = get(surface + 24);
            put(t + 16, width);
            auto height = get(surface + 20);
            put(t + 20, height);
            put(t + 24, uint32_t(int32_t(width) >> 1));
            put(t + 28, uint32_t(int32_t(height) >> 1));
            put(t + 40, get(surface + 184) ? 0x11 : 0x10);
            put(t + 32, 0);
            put(t + 36, 0);
            return 1;
        }
        if (!get(t + 44))
            return 1;
        auto dd = get(get(t + 44) + 8);
        if (dd && !call(get(get(dd) + 0x60), 0, {dd}))
            return 1;
        dd = get(get(t + 44) + 8);
        if (call(get(get(dd) + 0x6c), 0, {dd})) {
            method(t, 0x1c);
            return method(t, 0x2c, {a[0], a[1]});
        }
        uint32_t kind = call(0x4b61b0, a[0]), format = kind == 0x424d50   ? 1
                                                       : kind == 0x504358 ? 2
                                                       : kind == 0x524944 ? 3
                                                       : kind == 0x504944 ? 4
                                                                          : 0;
        if (!format)
            return 0;
        auto data = call(0x4b61c0, a[0]);
        if (!data)
            return 0;
        auto size = get(a[0] + 20);
        if (!size)
            return 0;
        return call(0x4b95b0, get(t + 44), {get(get(t + 12) + 28), data, format, size, get(0x543170)});
    }
    uint32_t invoke(const ClawImageResourceLifecycleCall &q) {
        step();
        if (q.argumentCount > 10)
            fail(2);
        if (owned(q.function))
            return body(q.function, q.receiver, q.arguments, q.argumentCount);
        uint32_t out = 0, covered = 0;
        if (q.function == 0x4f6433) {
            ClawPlayerFadeContext fade{};
            ClawPlayerFadeBlendContext blend{};
            blend.fade = &fade;
            covered = claw_player_fade_blend_entry(q.function, q.receiver, q.arguments, q.argumentCount, &blend,
                                                   nullptr, nullptr, &out);
            return complete(covered, fade.fault, out);
        }
        if (c.loading) {
            Restore<ClawSceneActorHost> h(c.loading->scene);
            c.loading->scene = host();
            ClawGameImageGlobals *nullImage = nullptr;
            ClawGameImageHost *nullHost = nullptr;
            Restore<ClawGameImageGlobals *> im(c.loading->registry ? c.loading->registry->images : nullImage);
            Restore<ClawGameImageHost *> ih(c.loading->registry ? c.loading->registry->imageHost : nullHost);
            if (c.loading->registry) {
                c.loading->registry->images = nullptr;
                c.loading->registry->imageHost = nullptr;
            }
            covered = claw_image_controller_loading_entry(q.function, q.receiver, q.arguments, q.argumentCount,
                                                          c.loading, loadingService, this, &out);
            if (c.loading->fault)
                fail(c.loading->fault);
            if (covered)
                return out;
        }
        if (c.images && gameOwned(q.function)) {
            imageFromRaw();
            ClawGameImageArguments a{};
            a.count = q.argumentCount;
            if (a.count > 8)
                fail(2);
            std::copy_n(q.arguments, a.count, a.words);
            ClawGameImageHost h{host(), this, imageService};
            uint32_t fault = 0;
            covered = claw_game_image_entry(q.function, q.receiver, a, c.images, h, &fault, &out);
            imageToRaw();
            return complete(covered, fault, out);
        }
        if (c.display) {
            Restore<ClawSceneActorHost> h(c.display->scene);
            c.display->scene = host();
            covered = claw_scene_display_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.display,
                                               displayService, this, &out);
            if (c.display->fault)
                fail(c.display->fault);
            if (covered)
                return out;
        }
        if (c.story && q.function == 0x4b95b0) {
            Restore<ClawSceneActorHost> h(c.story->scene);
            c.story->scene = host();
            covered = claw_booty_story_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.story,
                                             storyService, this, &out);
            return complete(covered, c.story->fault, out);
        }
        if (c.pcx) {
            Restore<ClawSceneActorHost> h(c.pcx->scene);
            c.pcx->scene = host();
            if (q.function == 0x4be810)
                covered =
                    claw_pcx_creation_entry(q.receiver, q.arguments, q.argumentCount, c.pcx, pcxService, this, &out);
            else
                covered = claw_pcx_image_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.pcx, pcxService,
                                               this, &out);
            if (c.pcx->fault)
                fail(c.pcx->fault);
            if (covered)
                return out;
        }
        if (c.blit) {
            Restore<ClawSceneActorHost> h(c.blit->scene);
            c.blit->scene = host();
            ClawSurfaceBlitArguments a{};
            a.count = q.argumentCount;
            if (a.count <= 5) {
                std::copy_n(q.arguments, a.count, a.words);
                covered = claw_surface_blit_entry(q.function, q.receiver, a, c.blit, blitService, this, &out);
            }
            if (c.blit->fault)
                fail(c.blit->fault);
            if (covered)
                return out;
        }
        if (c.strings) {
            Restore<ClawSceneActorHost> h(c.strings->scene);
            c.strings->scene = host();
            covered = claw_cstring_assignment_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.strings,
                                                    stringService, this, &out);
            if (c.strings->fault)
                fail(c.strings->fault);
            if (covered)
                return out;
        }
        if (c.lifecycle) {
            Restore<ClawSceneActorHost> h(c.lifecycle->scene);
            c.lifecycle->scene = host();
            covered = claw_scene_lifecycle_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.lifecycle,
                                                 lifecycleService, this, &out);
            if (c.lifecycle->fault)
                fail(c.lifecycle->fault);
            if (covered)
                return out;
        }
        if (q.function == 0x4f6584) {
            ClawActorDestructionGlobals g{};
            g.emptyStringToken = get(0x52e1cc);
            covered = claw_actor_destruction_entry(q.function, q.receiver, 0, &g, host(), &c.fault, &out);
            return complete(covered, c.fault, out);
        }
        if (c.loading && c.loading->pools &&
            (q.function == 0x4f51c5 || q.function == 0x4f5212 || q.function == 0x4f5172 || q.function == 0x4f5192)) {
            auto &pool = *c.loading->pools;
            Restore<ClawSceneActorHost> h(pool.scene);
            pool.scene = host();
            covered = claw_ambient_audio_backend_entry(q.function, q.receiver, q.arguments, q.argumentCount, &pool,
                                                       poolService, this, &out);
            return complete(covered, pool.fault, out);
        }
        return event(q);
    }
};
} // namespace
extern "C" uint32_t claw_image_resource_lifecycle_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                        ClawImageResourceLifecycleContext *c,
                                                        ClawImageResourceLifecycleDependency d, void *u,
                                                        uint32_t *out) {
    if (!c || !out || n > 10 || (n && !a))
        return 0;
    try {
        Run r{*c, d, u};
        ClawImageResourceLifecycleCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        if (!Run::owned(f) && !Run::gameOwned(f)) {
            switch (f) {
            case 0x4cff40:
            case 0x4d0120:
            case 0x4cf230:
            case 0x4cfa80:
            case 0x4d0240:
            case 0x4d2380:
            case 0x4ce320:
            case 0x4ce5e0:
            case 0x4ce770:
            case 0x4d0380:
            case 0x4ce2d0:
            case 0x4b7210:
            case 0x4b6b60:
            case 0x4b61b0:
            case 0x4b61c0:
            case 0x4b6230:
            case 0x4be810:
            case 0x4b9e60:
            case 0x4b95b0:
                break;
            default:
                return 0;
            }
        }
        *out = r.invoke(q);
        return c->fault ? 0 : 1;
    } catch (Failure &) {
    }
    return 0;
}
