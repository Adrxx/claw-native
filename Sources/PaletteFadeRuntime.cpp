#include "PaletteFadeRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
struct Run {
    ClawPaletteFadeContext &c;
    ClawPaletteFadeDependency dependency;
    void *user;
    uint32_t operations = 0;
    [[noreturn]] void fail(uint32_t fault = 1) {
        if (!c.fault)
            c.fault = fault;
        throw Failure{};
    }
    void step() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000))
            fail(3);
    }
    static int32_t si(uint32_t value) {
        int32_t v;
        std::memcpy(&v, &value, 4);
        return v;
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
    uint8_t byte(uint32_t t) {
        return reinterpret_cast<uint8_t *>(span(t & ~3u))[t & 3];
    }
    void byte(uint32_t t, uint32_t v) {
        reinterpret_cast<uint8_t *>(span(t & ~3u))[t & 3] = uint8_t(v);
    }
    uint32_t service(ClawPaletteFadeCall &q) {
        step();
        if (!dependency)
            fail();
        uint32_t v = dependency(&c, &q, user);
        if (c.fault)
            throw Failure{};
        return v;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawPaletteFadeCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        return service(q);
    }
    uint32_t physical(uint32_t object, uint32_t slot, std::initializer_list<uint32_t> a, uint32_t buffer = 0,
                      uint32_t count = 0) {
        ClawPaletteFadeCall q{};
        q.function = get(get(object) + slot);
        q.argumentCount = uint32_t(a.size()) + 1;
        q.arguments[0] = object;
        std::copy(a.begin(), a.end(), q.arguments + 1);
        if (count) {
            q.bufferCount = 1;
            q.buffers[0] = span(buffer, count);
            q.bufferBytes[0] = count * 4;
        }
        return service(q);
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        return static_cast<Run *>(u)->span(t, n);
    }
    static uint32_t paletteService(ClawPaletteResourceContext *, const ClawPaletteResourceCall *e, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawPaletteFadeCall q{};
        q.function = e->function;
        q.receiver = e->receiver;
        q.argumentCount = e->argumentCount;
        std::copy_n(e->arguments, e->argumentCount, q.arguments);
        q.localMask = e->localMask;
        q.bufferCount = e->bufferCount;
        for (uint32_t i = 0; i < e->bufferCount; ++i) {
            q.buffers[i] = e->buffers[i];
            q.bufferBytes[i] = e->bufferBytes[i];
        }
        return r.service(q);
    }
    uint32_t owner(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
        ClawPaletteResourceContext q{};
        if (c.palette)
            q = *c.palette;
        ClawPaletteResourceGlobals globals{};
        globals.cooperativeHolder = get(0x541374);
        q.globals = &globals;
        q.scene.context = this;
        q.scene.lookup = lookup;
        q.fault = 0;
        uint32_t args[6]{};
        std::copy(a.begin(), a.end(), args);
        uint32_t out = 0;
        if (!claw_palette_resource_entry(f, t, args, uint32_t(a.size()), &q, paletteService, this, &out) || q.fault)
            fail(q.fault ? q.fault : 1);
        if (c.palette && c.palette->globals)
            c.palette->globals->cooperativeHolder = get(0x541374);
        return out;
    }
    uint32_t channel(uint32_t old, uint32_t target, uint32_t elapsed, uint32_t duration) {
        int32_t divisor = si(duration), product = si((target - old) * elapsed);
        if (!divisor || (product == si(0x80000000) && divisor == -1))
            fail(2);
        return old + uint32_t(product / divisor);
    }
    void cancel(uint32_t t) {
        if (!get(t + 52))
            return;
        put(t + 52, 0);
        uint32_t target = get(t + 20);
        if (target) {
            owner(0x4bb800, t, {get(t + 44), get(t + 48), target, 0});
            put(t + 20, 0);
        } else {
            uint32_t packed = get(t + 28);
            owner(0x4bb910, t, {get(t + 44), get(t + 48), packed & 255, (packed >> 8) & 255, (packed >> 16) & 255, 0});
        }
    }
    uint32_t tick(uint32_t t) {
        if (!get(t + 52))
            return 0;
        uint32_t elapsed = call(0x546df0, 0) - get(t + 36);
        if (elapsed >= get(t + 32)) {
            cancel(t);
            return 0;
        }
        bool table = get(t + 20) != 0;
        if (elapsed != get(t + 40)) {
            uint32_t i = get(t + 44);
            while (si(i) < si(get(t + 44) + get(t + 48))) {
                step();
                for (uint32_t k = 0; k < 3; ++k) {
                    uint32_t old = byte(get(t + 24) + i * 4 + k),
                             target = table ? byte(get(t + 20) + i * 4 + k) : byte(t + 28 + k);
                    byte(get(t + 12) + i * 4 + k, channel(old, target, elapsed, get(t + 32)));
                }
                ++i;
            }
            uint32_t start = get(t + 44), count = get(t + 48), data = get(t + 12) + start * 4;
            physical(get(t + 4), 24, {0, start, count, data}, data, count);
        }
        put(t + 40, elapsed);
        return 1;
    }
    void blocking(uint32_t t, const uint32_t *a) {
        uint32_t data = get(t + 12);
        uint32_t hr = physical(get(t + 4), 16, {0, 0, 256, data}, data, 256);
        if (hr)
            call(0x4bd260, 0, {0x532500, 0x41b, hr});
        uint32_t saved = call(0x4f63ec, 0, {1024});
        for (uint32_t i = 0; i < 256; ++i)
            put(saved + i * 4, get(get(t + 12) + i * 4));
        uint32_t begin = call(0x546df0, 0), elapsed = 10, previous = 9;
        while (elapsed < a[3]) {
            step();
            if (elapsed != previous) {
                uint32_t end = a[0] + a[1];
                for (uint32_t i = a[0]; si(i) < si(end); ++i) {
                    step();
                    for (uint32_t k = 0; k < 3; ++k) {
                        uint32_t old = byte(saved + i * 4 + k), target = byte(a[2] + i * 4 + k);
                        byte(get(t + 12) + i * 4 + k, channel(old, target, elapsed, a[3]));
                    }
                }
                uint32_t output = get(t + 12) + a[0] * 4;
                physical(get(t + 4), 24, {0, a[0], a[1], output}, output, a[1]);
            }
            previous = elapsed;
            elapsed = call(0x546df0, 0) - begin;
        }
        owner(0x4bb800, t, {a[0], a[1], a[2], 0});
        call(0x4f6428, 0, {saved});
    }
    void backup(uint32_t t) {
        uint32_t saved = get(t + 16);
        if (!saved)
            return;
        for (uint32_t i = 0; i < 256; ++i)
            put(get(t + 12) + i * 4, get(saved + i * 4));
        uint32_t holder = get(0x541374);
        if (holder)
            physical(get(holder), 0x58, {1, 0});
        physical(get(t + 4), 24, {0, 0, 256, saved}, saved, 256);
    }
};
} // namespace
extern "C" uint32_t claw_palette_fade_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                            ClawPaletteFadeContext *c, ClawPaletteFadeDependency d, void *u,
                                            uint32_t *out) {
    if (!c || !out || c->fault)
        return 0;
    uint32_t count = 0;
    switch (f) {
    case 0x4bbd90:
        count = 4;
        break;
    case 0x4bb8c0:
        count = 1;
        break;
    case 0x4bbb70:
    case 0x4bbd20:
        break;
    default:
        return 0;
    }
    if (n != count || (n && !a)) {
        c->fault = 2;
        return 0;
    }
    Run r{*c, d, u};
    try {
        r.step();
        *out = 0;
        if (f == 0x4bbd90)
            r.blocking(t, a);
        else if (f == 0x4bbb70)
            *out = r.tick(t);
        else if (f == 0x4bbd20)
            r.cancel(t);
        else
            r.backup(t);
        if (c->palette && c->palette->globals)
            c->palette->globals->cooperativeHolder = r.get(0x541374);
    } catch (Failure &) {
        return 0;
    }
    return 1;
}
