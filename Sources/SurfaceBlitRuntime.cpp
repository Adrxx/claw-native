#include "SurfaceBlitRuntime.h"
#include <algorithm>
#include <initializer_list>
namespace {
struct Failure {};
struct Run {
    ClawSurfaceBlitContext &c;
    ClawSurfaceBlitDependency dependency;
    void *user;
    uint32_t operations = 0;
    ClawGameImageGlobals fallbackImage{};
    [[noreturn]] void fail(uint32_t fault = 1) {
        if (!c.fault)
            c.fault = fault;
        throw Failure{};
    }
    void tick() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 65536))
            fail(3);
    }
    uint32_t *span(uint32_t token, uint32_t words = 1) {
        if (c.fault)
            throw Failure{};
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, token, words) : nullptr;
        if (!p)
            fail();
        return p;
    }
    uint32_t get(uint32_t token) {
        return *span(token);
    }
    uint32_t method(uint32_t token, uint32_t offset) {
        return get(get(token) + offset);
    }
    uint32_t service(ClawSurfaceBlitCall &q) {
        tick();
        if (!dependency)
            fail();
        uint32_t value = dependency(&c, &q, user);
        if (c.fault)
            throw Failure{};
        return value;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawSurfaceBlitCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        return service(q);
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        return static_cast<Run *>(u)->span(t, n);
    }
    static uint32_t allocate(void *u, uint32_t n) {
        auto &r = *static_cast<Run *>(u);
        return r.call(0x4f63ec, 0, {n});
    }
    static void release(void *u, uint32_t t) {
        static_cast<Run *>(u)->call(0x4f6428, 0, {t});
    }
    static uint32_t hostCall(void *u, ClawSceneActorCall e) {
        auto &r = *static_cast<Run *>(u);
        ClawSurfaceBlitCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        return r.service(q);
    }
    static uint32_t clock(void *u) {
        auto &r = *static_cast<Run *>(u);
        if (!r.c.scene.readClock)
            r.fail();
        return r.c.scene.readClock(r.c.scene.context);
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, hostCall, clock};
    }
    static uint32_t imageService(void *u, ClawGameImageCall e) {
        auto &r = *static_cast<Run *>(u);
        ClawSurfaceBlitCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        if (e.source) {
            q.localMask = 4;
            q.bufferCount = 1;
            q.buffers[0] = e.source;
            q.bufferBytes[0] = 8;
        }
        return r.service(q);
    }
    static uint32_t pcxService(ClawPCXImageContext *, const ClawPCXImageCall *e, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawSurfaceBlitCall q{};
        q.function = e->function;
        q.receiver = e->receiver;
        q.argumentCount = e->argumentCount;
        std::copy_n(e->arguments, e->argumentCount, q.arguments);
        return r.service(q);
    }
    uint32_t restore(uint32_t f, uint32_t surface) {
        if (f != 0x4b9e60)
            return call(f, surface);
        ClawPCXImageContext q{};
        if (c.pcx)
            q = *c.pcx;
        q.scene = host();
        q.fault = 0;
        uint32_t out = 0;
        if (!claw_pcx_image_entry(f, surface, nullptr, 0, &q, pcxService, this, &out) || q.fault)
            fail(q.fault ? q.fault : 1);
        return out;
    }
    void buffer(ClawSurfaceBlitCall &q, uint32_t index, uint32_t *p, uint32_t bytes) {
        if (!p)
            return;
        q.localMask |= 1u << index;
        q.arguments[index] = 0;
        q.buffers[q.bufferCount] = p;
        q.bufferBytes[q.bufferCount++] = bytes;
    }
    uint32_t blt(uint32_t surface, ClawSurfaceBlitArguments a, bool fast) {
        auto operation = [&]() {
            uint32_t dd = get(surface + 8);
            ClawSurfaceBlitCall q{};
            q.function = method(dd, fast ? 0x1c : 0x14);
            q.argumentCount = 6;
            q.arguments[0] = dd;
            if (fast) {
                q.arguments[1] = a.words[0];
                q.arguments[2] = a.words[1];
                q.arguments[3] = get(a.words[2] + 8);
                q.arguments[4] = a.words[3];
                q.arguments[5] = a.words[4];
                buffer(q, 4, a.source, 16);
            } else {
                q.arguments[1] = a.words[0];
                q.arguments[2] = a.words[1] ? get(a.words[1] + 8) : 0;
                q.arguments[3] = a.words[2];
                q.arguments[4] = a.words[3];
                q.arguments[5] = a.words[4];
                buffer(q, 1, a.destination, 16);
                buffer(q, 3, a.source, 16);
            }
            return service(q);
        };
        uint32_t hr = operation();
        if (hr == 0x887601c2) {
            if (!restore(method(surface, 0x1c), surface))
                return hr;
            /* Source retry unconditionally dereferences the source surface. Ordinary
      lost-surface retry therefore requires the original nonnull source. */
            if (!fast && !a.words[1])
                fail(2);
            hr = operation();
        }
        if (hr)
            call(0x4bd260, 0, {0x5324dc, fast ? 0x4b8u : 0x48eu, hr});
        return hr;
    }
    uint32_t colorKey(uint32_t surface, ClawSurfaceBlitArguments a) {
        uint32_t dd = get(surface + 8);
        ClawSurfaceBlitCall q{};
        q.function = method(dd, 0x74);
        q.argumentCount = 3;
        q.arguments[0] = dd;
        q.arguments[1] = a.words[0];
        q.arguments[2] = a.words[1];
        buffer(q, 2, a.source, 8);
        uint32_t hr = service(q);
        if (hr)
            call(0x4bd260, 0, {0x5324dc, 0x331, hr});
        return hr;
    }
    uint32_t convenienceKey(uint32_t surface, uint32_t key) {
        ClawGameImageArguments a{};
        a.count = 1;
        a.words[0] = key;
        ClawGameImageHost h{host(), this, imageService};
        uint32_t fault = 0, out = 0;
        if (!claw_game_image_entry(0x4b9990, surface, a, c.image ? c.image : &fallbackImage, h, &fault, &out) || fault)
            fail(fault ? fault : 1);
        return 0;
    }
};
} // namespace
extern "C" uint32_t claw_surface_blit_entry(uint32_t f, uint32_t surface, ClawSurfaceBlitArguments a,
                                            ClawSurfaceBlitContext *c, ClawSurfaceBlitDependency d, void *u,
                                            uint32_t *out) {
    if (!c || !out || c->fault)
        return 0;
    uint32_t required = 0;
    switch (f) {
    case 0x4b9ce0:
    case 0x4b9d80:
        required = 5;
        break;
    case 0x4b9950:
        required = 2;
        break;
    case 0x4b9990:
        required = 1;
        break;
    case 0x4b9e60:
        break;
    default:
        return 0;
    }
    if (a.count != required || (a.destination && (f != 0x4b9ce0 || a.words[0])) ||
        (a.source && ((f != 0x4b9ce0 && f != 0x4b9d80 && f != 0x4b9950) || a.words[f == 0x4b9ce0   ? 2
                                                                                   : f == 0x4b9d80 ? 3
                                                                                                   : 1]))) {
        c->fault = 2;
        return 0;
    }
    Run r{*c, d, u};
    try {
        r.tick();
        if (f == 0x4b9ce0 || f == 0x4b9d80)
            *out = r.blt(surface, a, f == 0x4b9d80);
        else if (f == 0x4b9950)
            *out = r.colorKey(surface, a);
        else if (f == 0x4b9990)
            *out = r.convenienceKey(surface, a.words[0]);
        else
            *out = r.restore(f, surface);
    } catch (Failure &) {
        return 0;
    }
    return 1;
}
