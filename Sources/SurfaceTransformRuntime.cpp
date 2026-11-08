#include "SurfaceTransformRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
struct Run {
    ClawSurfaceTransformContext &c;
    ClawSurfaceTransformDependency d;
    void *u;
    uint32_t operations = 0;
    [[noreturn]] void fail(uint32_t n = 1) {
        if (!c.fault)
            c.fault = n;
        throw Failure{};
    }
    void tick() {
        if (c.fault)
            throw Failure{};
        if (++operations > (c.maximumOperations ? c.maximumOperations : 100000000))
            fail(3);
    }
    static int32_t si(uint32_t v) {
        int32_t x;
        std::memcpy(&x, &v, 4);
        return x;
    }
    uint32_t get(uint32_t t) {
        tick();
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, 1) : nullptr;
        if (!p)
            fail();
        return *p;
    }
    uint8_t *byte(uint32_t t) {
        tick();
        if (c.bytes) {
            auto *p = c.bytes(c.byteContext, t, 1);
            if (!p)
                fail();
            return p;
        }
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t & ~3u, 1) : nullptr;
        if (!p)
            fail();
        return reinterpret_cast<uint8_t *>(p) + (t & 3u);
    }
    uint8_t read(uint32_t t) {
        return *byte(t);
    }
    void write(uint32_t t, uint8_t v) {
        *byte(t) = v;
    }
    uint32_t event(const ClawGameImageCall &q) {
        tick();
        if (!d)
            fail();
        auto value = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        return value;
    }
    static uint32_t imageService(void *v, ClawGameImageCall q) {
        return static_cast<Run *>(v)->event(q);
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawGameImageCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        if (f == 0x4b9730 && c.images) {
            ClawGameImageArguments x{};
            x.count = q.argumentCount;
            std::copy_n(q.arguments, x.count, x.words);
            ClawGameImageHost host{c.scene, this, imageService};
            uint32_t fault = 0, value = 0;
            auto covered = claw_game_image_entry(f, t, x, c.images, host, &fault, &value);
            if (fault || !covered)
                fail(fault ? fault : 2);
            return value;
        }
        return event(q);
    }
    void unlock(uint32_t t) {
        uint32_t dd = get(t + 8), f = get(get(dd) + 0x80);
        call(f, 0, {dd, 0});
    }
    void flip(uint32_t t) {
        if (si(get(t + 20)) <= 1)
            return;
        uint32_t pixels = call(0x4b9730, t, {0});
        if (!pixels)
            return;
        uint32_t scratch = call(0x4f63ec, 0, {get(t + 24)});
        if (!scratch) {
            unlock(t);
            return;
        }
        uint32_t height = get(t + 20), width = get(t + 24), half = uint32_t(si(height) / 2);
        for (uint32_t y = 0; si(y) < si(half); ++y) {
            tick();
            uint32_t top = y * get(t + 28);
            for (uint32_t x = 0; si(x) < si(width); ++x)
                write(scratch + x, read(pixels + top + x));
            uint32_t pitch = get(t + 28), bottomRow = height - y - 1;
            top = y * pitch;
            uint32_t bottom = bottomRow * pitch;
            for (uint32_t x = 0; si(x) < si(width); ++x)
                write(pixels + top + x, read(pixels + bottom + x));
            bottom = bottomRow * get(t + 28);
            for (uint32_t x = 0; si(x) < si(width); ++x)
                write(pixels + bottom + x, read(scratch + x));
        }
        unlock(t);
        call(0x4f6428, 0, {scratch});
    }
};
} // namespace
extern "C" uint32_t claw_surface_transform_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                 ClawSurfaceTransformContext *c, ClawSurfaceTransformDependency d,
                                                 void *u, uint32_t *out) {
    if (!c || !out || f != 0x4b99d0 || c->fault)
        return 0;
    if (n) {
        c->fault = 2;
        return 0;
    }
    (void)a;
    try {
        Run r{*c, d, u};
        r.flip(t);
        *out = 0;
        return 1;
    } catch (Failure &) {
    }
    return 0;
}
