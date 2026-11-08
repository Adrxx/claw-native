#include "SurfaceFlipRuntime.h"
#include <algorithm>
#include <initializer_list>
namespace {
struct Failure {};
struct Run {
    ClawSurfaceFlipContext &c;
    ClawSurfaceFlipDependency dependency;
    void *user;
    uint32_t operations = 0;
    [[noreturn]] void fail(uint32_t f = 1) {
        if (!c.fault)
            c.fault = f;
        throw Failure{};
    }
    void step() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 65536))
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
    uint32_t method(uint32_t t, uint32_t slot) {
        return get(get(t) + slot);
    }
    uint32_t service(const ClawSurfaceFlipCall &q) {
        step();
        if (!dependency)
            fail();
        uint32_t v = dependency(&c, &q, user);
        if (c.fault)
            throw Failure{};
        return v;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawSurfaceFlipCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        return service(q);
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        return static_cast<Run *>(u)->span(t, n);
    }
    static uint32_t blitService(ClawSurfaceBlitContext *, const ClawSurfaceBlitCall *q, void *u) {
        return static_cast<Run *>(u)->service(*q);
    }
    uint32_t restore(uint32_t surface) {
        uint32_t f = method(surface, 0x1c);
        if (f != 0x4b9e60)
            return call(f, surface);
        ClawSurfaceBlitContext q{};
        if (c.blit)
            q = *c.blit;
        q.scene = c.scene;
        q.scene.context = this;
        q.scene.lookup = lookup;
        q.fault = 0;
        ClawSurfaceBlitArguments a{};
        uint32_t out = 0;
        if (!claw_surface_blit_entry(f, surface, a, &q, blitService, this, &out) || q.fault)
            fail(q.fault ? q.fault : 1);
        return out;
    }
    uint32_t flip(uint32_t surface, uint32_t source) {
        uint32_t sourceDD = source ? get(source + 8) : 0;
        auto physical = [&]() {
            uint32_t dd = get(surface + 8);
            return call(method(dd, 0x2c), 0, {dd, sourceDD, 1});
        };
        uint32_t hr = physical();
        if (!hr)
            return 0;
        if (hr != 0x887601c2) {
            call(0x4bd260, 0, {0x5324dc, 0x29a, hr});
            return hr;
        }
        if (!restore(surface))
            return hr;
        hr = physical();
        if (hr)
            call(0x4bd260, 0, {0x5324dc, 0x294, hr});
        return hr;
    }
};
} // namespace
extern "C" uint32_t claw_surface_flip_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                            ClawSurfaceFlipContext *c, ClawSurfaceFlipDependency d, void *u,
                                            uint32_t *out) {
    if (f != 0x4b98b0 || !c || !out || c->fault)
        return 0;
    if (n != 1 || !a) {
        c->fault = 2;
        return 0;
    }
    Run r{*c, d, u};
    try {
        r.step();
        *out = r.flip(t, a[0]);
    } catch (Failure &) {
        return 0;
    }
    return 1;
}
