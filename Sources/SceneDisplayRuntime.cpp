#include "SceneDisplayRuntime.h"
#include "AmbientAudioBackendRuntime.h"
#include "SinglePlayerSceneRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
struct Run;
uint32_t graphicsService(ClawGraphicsManagerLifecycleContext *, const ClawGraphicsManagerLifecycleCall *, void *);
uint32_t listService(ClawAmbientAudioBackendContext *, const ClawAmbientAudioBackendCall *, void *);
uint32_t imageService(void *, ClawGameImageCall);
struct Run {
    ClawSceneDisplayContext &c;
    ClawSceneDisplayDependency d;
    void *user;
    uint32_t operations = 0;
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
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failure{};
        }
        return p;
    }
    uint32_t get(uint32_t t, uint32_t offset = 0) {
        return *span(t + offset);
    }
    void set(uint32_t t, uint32_t offset, uint32_t v) {
        *span(t + offset) = v;
    }
    uint32_t service(ClawSceneDisplayCall &q) {
        if (d)
            return d(&c, &q, user);
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
        if ((f == 0x4bc220 || f == 0x4bd1c0 || f == 0x4bc5f0 || f == 0x4bc610 || f == 0x4b9540 || f == 0x4f551d) &&
            c.graphics) {
            auto &x = *c.graphics;
            x.scene = c.scene;
            uint32_t out = 0;
            if (!claw_graphics_manager_lifecycle_entry(f, t, args, uint32_t(a.size()), &x, graphicsService, this,
                                                       &out) ||
                x.fault) {
                c.fault = x.fault ? x.fault : 2;
                throw Failure{};
            }
            return out;
        }
        if (f == 0x4f51c5 || f == 0x4f5212 || f == 0x4f5172) {
            ClawAmbientAudioBackendContext x{};
            x.scene = c.scene;
            x.maximumTraversal = c.maximumOperations;
            uint32_t out = 0;
            if (!claw_ambient_audio_backend_entry(f, t, args, uint32_t(a.size()), &x, listService, this, &out) ||
                x.fault) {
                c.fault = x.fault ? x.fault : 2;
                throw Failure{};
            }
            return out;
        }
        if (f == 0x45fde0) {
            ClawSinglePlayerSceneGlobals g{};
            ClawSinglePlayerSceneContext x{};
            x.host = c.scene;
            x.globals = &g;
            uint32_t out = 0;
            if (!claw_single_player_scene_entry(f, t, args, uint32_t(a.size()), &x, nullptr, nullptr, &out) ||
                x.fault) {
                c.fault = x.fault ? x.fault : 2;
                throw Failure{};
            }
            return out;
        }
        if ((f == 0x4b9180 || f == 0x4b9380 || f == 0x4b9990 || f == 0x4bc490) && c.image) {
            ClawGameImageArguments a2{};
            a2.count = uint32_t(a.size());
            std::copy_n(args, a2.count, a2.words);
            ClawGameImageHost host{heap(), this, imageService};
            uint32_t fault = 0, out = 0;
            if (!claw_game_image_entry(f, t, a2, c.image, host, &fault, &out) || fault) {
                c.fault = fault ? fault : 2;
                throw Failure{};
            }
            return out;
        }
        ClawSceneDisplayCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy_n(args, q.argumentCount, q.arguments);
        return service(q);
    }
    uint32_t virt(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        return invoke(get(get(t), slot), t, a);
    }
    uint32_t com(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        ClawSceneDisplayCall q{};
        q.function = get(get(t), slot);
        q.argumentCount = uint32_t(a.size() + 1);
        q.arguments[0] = t;
        std::copy(a.begin(), a.end(), q.arguments + 1);
        return service(q);
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
    }
    static uint32_t allocate(void *p, uint32_t n) {
        return static_cast<Run *>(p)->invoke(0x4f63ec, 0, {n});
    }
    static void free(void *p, uint32_t t) {
        static_cast<Run *>(p)->invoke(0x4f6428, 0, {t});
    }
    static uint32_t callback(void *p, ClawSceneActorCall q) {
        auto &r = *static_cast<Run *>(p);
        ClawSceneDisplayCall e{};
        e.function = q.function;
        e.receiver = q.receiver;
        e.argumentCount = q.argumentCount;
        std::copy_n(q.arguments, q.argumentCount, e.arguments);
        return r.service(e);
    }
    static uint32_t clock(void *p) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.scene.readClock) {
            r.c.fault = 1;
            throw Failure{};
        }
        return r.c.scene.readClock(r.c.scene.context);
    }
    ClawSceneActorHost heap() {
        return {this, lookup, allocate, free, callback, clock};
    }
    void sticky(uint32_t t, uint32_t value) {
        uint32_t parent = get(t, 12);
        if (!get(parent, 56))
            set(parent, 56, value);
    }
    void geometry(uint32_t t, uint32_t w, uint32_t h) {
        set(t, 20, h);
        set(t, 40, h);
        set(t, 16, w);
        set(t, 28, 0);
        set(t, 32, 0);
        set(t, 36, w);
    }
    uint32_t holderInitialize(uint32_t t, const uint32_t *a) {
        uint32_t token = invoke(0x4f63ec, 0, {48});
        if (token) {
            invoke(0x4cab90, token, {get(t, 12), 0, 0});
            set(token, 0, 0x5138d8);
            set(token, 44, 0);
        }
        set(t, 16, token);
        for (uint32_t index = 1; index <= 2; ++index) {
            token = invoke(0x4f63ec, 0, {52});
            if (token) {
                invoke(0x45fde0, token, {get(t, 12), index, 0});
                set(token, 16, 0);
                set(token, 0, 0x50e8e4);
                set(token, 44, 0);
                set(token, 48, 1);
            }
            set(t, 16 + index * 4, token);
        }
        if (!virt(get(t, 16), 44, {a[0], a[1], a[2]})) {
            sticky(t, 2001);
            return 0;
        }
        if (!virt(get(t, 20), 36, {a[0], a[1]})) {
            sticky(t, 2002);
            return 0;
        }
        if (!(a[3] & 1) && !virt(get(t, 24), 36, {a[0], a[1]})) {
            sticky(t, 2003);
            return 0;
        }
        return 1;
    }
    void holderCleanup(uint32_t t) {
        for (uint32_t offset : {16u, 20u, 24u}) {
            uint32_t child = get(t, offset);
            if (child) {
                virt(child, 4, {1});
                set(t, offset, 0);
            }
        }
    }
    uint32_t primaryInitialize(uint32_t t, const uint32_t *a) {
        set(t, 16, a[0]);
        set(t, 20, a[1]);
        set(t, 24, a[2]);
        uint32_t parent = get(t, 12), manager = get(parent, 28);
        uint32_t flags = signedWord(a[0]) > 320 ? 17 : 81;
        uint32_t ok =
            invoke(0x4bc220, manager, {get(parent, 48), (get(parent, 52) & 16) ? 2u : 0u, a[0], a[1], a[2], flags});
        if (!ok) {
            uint32_t error = get(manager, 0x880);
            sticky(t, error >= 1001 && error <= 1005 ? 0x80e9 + error - 1001 : 3001);
            return 0;
        }
        uint32_t primary = invoke(0x4bc890, manager, {(get(get(t, 12), 52) & 2) ? 2u : 1u});
        set(t, 44, primary);
        if (primary && virt(primary, 20))
            return 1;
        sticky(t, 3002);
        return 0;
    }
    uint32_t auxiliaryInitialize(uint32_t t, const uint32_t *a) {
        if (signedWord(a[0]) < 1 || signedWord(a[1]) < 1) {
            sticky(t, get(t, 4) == 1 ? 4001 : 4002);
            return 0;
        }
        geometry(t, a[0], a[1]);
        uint32_t token = 0;
        if (get(t, 4) == 1) {
            uint32_t parent = get(t, 12);
            token = invoke(0x4bcf80, get(parent, 28), {get(get(get(parent, 4), 16), 44), 4});
            set(t, 44, token);
            if (!token) {
                sticky(t, 4003);
                return 0;
            }
            if (get(t, 4) == 1) {
                set(t, 48, 1);
                return 1;
            }
        }
        token = invoke(0x4bc670, get(get(t, 12), 28), {a[0], a[1], 0, 0, 0xffffffff});
        set(t, 44, token);
        if (!token) {
            sticky(t, 4004);
            return 0;
        }
        set(t, 48, 1);
        return 1;
    }
    void auxiliaryCleanup(uint32_t t) {
        if (get(t, 44) && get(t, 48)) {
            invoke(0x4bc4f0, get(get(t, 12), 28), {get(t, 44)});
            set(t, 44, 0);
        }
        set(t, 16, 0);
    }
    void objectCleanup(uint32_t t) {
        set(t, 4, 0xffffffff);
        set(t, 16, 0);
        set(t, 8, 0);
        set(t, 12, 0);
        set(t, 0, 0x50becc);
    }
    uint32_t createSurface(uint32_t table) {
        uint32_t t = invoke(0x4f63ec, 0, {188});
        if (t) {
            uint32_t fault = 0, out = 0;
            if (!claw_graphics_string_array_construct(t + 144, c.scene, &fault, &out) || fault) {
                c.fault = fault ? fault : 2;
                throw Failure{};
            }
            for (uint32_t offset : {8u, 4u, 120u, 164u, 180u})
                set(t, offset, 0);
            set(t, 0, table);
        }
        return t;
    }
    uint32_t blankFactory(uint32_t manager, const uint32_t *a) {
        uint32_t t = createSurface(0x513690);
        if (!virt(t, 44, {manager, a[0], a[1], a[2], a[3], a[4]})) {
            if (t)
                virt(t, 0, {1});
            return 0;
        }
        invoke(0x4bc490, manager, {t});
        return t;
    }
    uint32_t primaryFactory(uint32_t manager, const uint32_t *a) {
        uint32_t t = createSurface(0x5136c0);
        if (!virt(t, 36, {manager, 24, 33, a[0]})) {
            if (t)
                virt(t, 0, {1});
            return 0;
        }
        invoke(0x4bc490, manager, {t});
        set(manager, 0x474, get(t, 164));
        return t;
    }
    uint32_t attachedFactory(uint32_t manager, const uint32_t *a) {
        uint32_t caps = a[1], attached = 0, dd = get(a[0], 8);
        ClawSceneDisplayCall q{};
        q.function = get(get(dd), 48);
        q.argumentCount = 3;
        q.arguments[0] = dd;
        q.localMask = 6;
        q.bufferCount = 2;
        q.buffers[0] = &caps;
        q.buffers[1] = &attached;
        q.bufferBytes[0] = q.bufferBytes[1] = 4;
        uint32_t hr = service(q);
        if (hr) {
            invoke(0x4bd260, 0, {0x532524, 0x64a, hr});
            return 0;
        }
        uint32_t t = createSurface(0x513588);
        if (!virt(t, 4, {attached})) {
            if (t)
                virt(t, 0, {1});
            return 0;
        }
        invoke(0x4bc490, manager, {t});
        return t;
    }
    uint32_t attachSurface(uint32_t t, uint32_t dd) {
        set(t, 8, dd);
        std::memset(span(t + 12, 27), 0, 108);
        set(t, 12, 108);
        uint32_t hr = com(get(t, 8), 88, {t + 12});
        if (hr)
            invoke(0x4bd260, 0, {0x5324dc, 0x7b, hr});
        uint32_t bits = get(t, 96), factor = bits == 16 ? 2 : bits == 24 ? 3 : bits == 32 ? 4 : 1;
        set(t, 184, 0);
        set(t, 164, bits);
        uint32_t stride = get(t, 24) * factor;
        set(t, 168, stride);
        set(t, 172, factor);
        set(t, 132, stride);
        set(t, 124, 0);
        set(t, 128, 0);
        set(t, 176, get(t, 28) / factor);
        set(t, 136, get(t, 20));
        set(t, 140, get(t, 168) * get(t, 20));
        set(t, 120, get(t, 120) | 1);
        return 1;
    }
    void drain(uint32_t t, const uint32_t *a) {
        uint32_t node = get(t, 20);
        while (node) {
            tick();
            uint32_t child = get(node, 8), next = get(node);
            virt(child, 40, {a[0], a[1]});
            set(child, 100, get(child, 100) - 1);
            uint32_t ready = virt(a[1], 20);
            if (ready || signedWord(get(child, 100)) <= 0) {
                invoke(0x4f5212, t + 16, {node});
                if (child)
                    virt(child, 4, {1});
            }
            node = next;
        }
    }
    static bool owned(uint32_t f) {
        switch (f) {
        case 0x4ca6f0:
        case 0x4cf730:
        case 0x4ca8b0:
        case 0x4cf780:
        case 0x4cf760:
        case 0x4cf750:
        case 0x4d63c0:
        case 0x4cab90:
        case 0x4cabc0:
        case 0x4cacb0:
        case 0x4cac00:
        case 0x4cac40:
        case 0x4caca0:
        case 0x4cabe0:
        case 0x45fec0:
        case 0x45fe40:
        case 0x45fe60:
        case 0x4d4000:
        case 0x4d4160:
        case 0x4d5510:
        case 0x4bc670:
        case 0x4bc890:
        case 0x4bcf80:
        case 0x4bc4f0:
        case 0x4b9150:
        case 0x4b91f0:
        case 0x4bf970:
        case 0x4bfb80:
        case 0x4bfbd0:
        case 0x4bb000:
        case 0x4bc810:
        case 0x4bc830:
        case 0x4bb060:
        case 0x4bb080:
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
        case 0x4ca6f0:
            need(4);
            return holderInitialize(t, a);
        case 0x4cf730:
            need(0);
            return get(t, 20) && get(t, 24) && get(t, 16);
        case 0x4ca8b0:
            need(0);
            holderCleanup(t);
            return 0;
        case 0x4cf780:
            need(0);
            set(t, 0, 0x513c68);
            holderCleanup(t);
            set(t, 4, 0xffffffff);
            set(t, 8, 0);
            set(t, 12, 0);
            set(t, 0, 0x50becc);
            return 0;
        case 0x4cf760:
            need(1);
            entry(0x4cf780, t, nullptr, 0);
            if (a[0] & 1)
                invoke(0x4f6428, 0, {t});
            return t;
        case 0x4cf750:
            need(0);
            return 15;
        case 0x4d63c0:
            need(2);
            drain(t, a);
            return 0;
        case 0x4cab90:
            need(3);
            set(t, 4, a[1]);
            set(t, 8, a[2]);
            set(t, 12, a[0]);
            set(t, 0, 0x513908);
            set(t, 16, 0);
            return t;
        case 0x4cabc0:
        case 0x4cacb0:
            need(0);
            return (f == 0x4cabc0 || get(t, 44)) && signedWord(get(t, 16)) > 0 && get(t, 12) && get(t, 4) != 0xffffffff;
        case 0x4cac00:
            need(2);
            if (signedWord(a[0]) < 1 || signedWord(a[1]) < 1)
                return 0;
            geometry(t, a[0], a[1]);
            return 1;
        case 0x4cac40:
            need(3);
            if (signedWord(a[0]) < 1 || signedWord(a[1]) < 1 || (a[2] != 8 && a[2] != 16 && a[2] != 24 && a[2] != 32))
                return 0;
            geometry(t, a[0], a[1]);
            set(t, 24, a[2]);
            return 1;
        case 0x4caca0:
            need(0);
            set(t, 16, 0);
            return 0;
        case 0x45fec0:
            need(0);
            objectCleanup(t);
            return 0;
        case 0x4cabe0:
            need(1);
            objectCleanup(t);
            if (a[0] & 1)
                invoke(0x4f6428, 0, {t});
            return t;
        case 0x45fe60:
            need(0);
            set(t, 0, 0x50e8e4);
            auxiliaryCleanup(t);
            objectCleanup(t);
            return 0;
        case 0x45fe40:
            need(1);
            entry(0x45fe60, t, nullptr, 0);
            if (a[0] & 1)
                invoke(0x4f6428, 0, {t});
            return t;
        case 0x4d4000:
            need(2);
            return auxiliaryInitialize(t, a);
        case 0x4d4160:
            need(0);
            auxiliaryCleanup(t);
            return 0;
        case 0x4d5510:
            need(3);
            return primaryInitialize(t, a);
        case 0x4bc670:
            need(5);
            return blankFactory(t, a);
        case 0x4bc890:
            need(1);
            return primaryFactory(t, a);
        case 0x4bcf80:
            need(2);
            return attachedFactory(t, a);
        case 0x4bc4f0:
            need(1);
            invoke(0x4f5212, t + 0x3b8, {get(a[0], 4)});
            if (a[0])
                virt(a[0], 0, {1});
            return 0;
        case 0x4b9150:
        case 0x4bfbd0:
            need(2);
            if (a[1]) {
                for (uint32_t i = 0; i < 27; ++i)
                    set(t, 12 + i * 4, get(a[1], i * 4));
            }
            return f == 0x4bfbd0 ? (virt(t, 32, {a[0]}) != 0) : virt(t, 32, {a[0]});
        case 0x4b91f0:
            need(1);
            return attachSurface(t, a[0]);
        case 0x4bf970:
            need(6);
            if (!invoke(0x4b9180, t, {a[0], a[1], a[2], a[3], a[4] | 64}))
                return 0;
            if (a[5] != 0xffffffff)
                invoke(0x4b9990, t, {a[5]});
            return 1;
        case 0x4bfb80: {
            need(4);
            std::memset(span(t + 12, 27), 0, 108);
            set(t, 16, a[2]);
            set(t, 116, a[1] | 0x200);
            set(t, 12, 108);
            set(t, 32, a[3]);
            uint32_t pair[2] = {a[0], 0};
            return entry(0x4b9150, t, pair, 2) != 0;
        }
        case 0x4bb000:
            need(0);
            return get(t, 8) && signedWord(get(t, 132)) > 0 && signedWord(get(t, 136)) > 0;
        case 0x4bc830:
        case 0x4bb080:
            need(0);
            invoke(0x4bc610, t);
            return 0;
        case 0x4bc810:
        case 0x4bb060:
            need(1);
            entry(f == 0x4bc810 ? 0x4bc830 : 0x4bb080, t, nullptr, 0);
            if (a[0] & 1)
                invoke(0x4f6428, 0, {t});
            return t;
        default:
            c.fault = 2;
            throw Failure{};
        }
    }
};
uint32_t graphicsService(ClawGraphicsManagerLifecycleContext *, const ClawGraphicsManagerLifecycleCall *e, void *v) {
    auto &r = *static_cast<Run *>(v);
    if (Run::owned(e->function) && !e->localMask)
        return r.entry(e->function, e->receiver, e->arguments, e->argumentCount);
    ClawSceneDisplayCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, q.argumentCount, q.arguments);
    q.localMask = e->localMask;
    q.bufferCount = e->bufferCount;
    for (uint32_t i = 0; i < 2; ++i) {
        q.buffers[i] = e->buffers[i];
        q.bufferBytes[i] = e->bufferBytes[i];
    }
    return r.service(q);
}
uint32_t listService(ClawAmbientAudioBackendContext *, const ClawAmbientAudioBackendCall *e, void *v) {
    auto &r = *static_cast<Run *>(v);
    ClawSceneDisplayCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, q.argumentCount, q.arguments);
    return r.service(q);
}
uint32_t imageService(void *v, ClawGameImageCall e) {
    auto &r = *static_cast<Run *>(v);
    if (e.function == 0x4f51c5)
        return r.invoke(e.function, e.receiver, {e.arguments[0]});
    ClawSceneDisplayCall q{};
    q.function = e.function;
    q.receiver = e.receiver;
    q.argumentCount = e.argumentCount;
    std::copy_n(e.arguments, q.argumentCount, q.arguments);
    if (e.source) {
        q.localMask = 1u << 2;
        q.bufferCount = 1;
        q.buffers[0] = e.source;
        q.bufferBytes[0] = 8;
    }
    return r.service(q);
}
} // namespace
extern "C" uint32_t claw_scene_display_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                             ClawSceneDisplayContext *c, ClawSceneDisplayDependency d, void *u,
                                             uint32_t *out) {
    if (!c || !out || !Run::owned(f) || (n && !a) || n > 8)
        return 0;
    if (c->fault)
        return 0;
    Run r{*c, d, u};
    try {
        *out = r.entry(f, t, a, n);
    } catch (Failure &) {
    }
    return c->fault ? 0 : 1;
}
