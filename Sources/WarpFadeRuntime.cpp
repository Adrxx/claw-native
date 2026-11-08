#include "WarpFadeRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
namespace {
struct Failed {};
struct Run;
uint32_t route(ClawPlayerFadeContext *, const ClawPlayerFadeCall *, void *);
struct Run {
    ClawWarpFadeContext &w;
    ClawPlayerFadeDependency dependency;
    void *user;
    uint32_t operations = 0;
    ClawPlayerFadeContext &c() {
        return *w.common->fade;
    }
    void tick() {
        if (++operations > (w.maximumOperations ? w.maximumOperations : 1000000)) {
            c().fault = 2;
            throw Failed{};
        }
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c().fault)
            throw Failed{};
        auto *p = c().scene.lookup ? c().scene.lookup(c().scene.context, t, n) : nullptr;
        if (!p) {
            c().fault = 1;
            throw Failed{};
        }
        return p;
    }
    uint32_t rd(uint32_t t) {
        return *span(t);
    }
    void wr(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    static int32_t si(uint32_t x) {
        int32_t y;
        std::memcpy(&y, &x, 4);
        return y;
    }
    float rf(uint32_t t) {
        auto x = rd(t);
        float f;
        std::memcpy(&f, &x, 4);
        return f;
    }
    void wf(uint32_t t, float f) {
        uint32_t x;
        std::memcpy(&x, &f, 4);
        wr(t, x);
    }
    uint8_t *bytes(uint32_t t, uint32_t n) {
        if (!n)
            return nullptr;
        uint64_t size = (uint64_t(n) + (t & 3) + 3) / 4;
        if (size > 0xffffffff) {
            c().fault = 2;
            throw Failed{};
        }
        return reinterpret_cast<uint8_t *>(span(t & ~3u, uint32_t(size))) + (t & 3);
    }
    void pixel(uint32_t dst, uint32_t src, uint32_t n, bool clear) {
        if (si(n) <= 0)
            return;
        auto *d = bytes(dst, n);
        if (clear)
            std::memset(d, 0, n);
        else {
            auto *s = bytes(src, n);
            for (uint32_t i = 0; i < n; ++i)
                d[i] = s[i];
        }
    }
    uint32_t service(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        if (c().fault)
            throw Failed{};
        ClawPlayerFadeCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), e.arguments);
        if (dependency)
            return dependency(&c(), &e, user);
        if (c().scene.call && e.argumentCount <= 4) {
            ClawSceneActorCall q{};
            q.function = f;
            q.receiver = t;
            q.argumentCount = e.argumentCount;
            std::copy(a.begin(), a.end(), q.arguments);
            return c().scene.call(c().scene.context, q);
        }
        c().fault = 1;
        throw Failed{};
    }
    uint32_t frozen(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        uint32_t out = 0, args[6]{};
        std::copy(a.begin(), a.end(), args);
        if (claw_player_fade_blend_entry(f, t, args, uint32_t(a.size()), w.common, route, this, &out))
            return out;
        if (c().fault)
            throw Failed{};
        if (claw_player_fade_entry(f, t, args, uint32_t(a.size()), &c(), route, this, &out))
            return out;
        if (c().fault)
            throw Failed{};
        c().fault = 3;
        throw Failed{};
    }
    static uint32_t trunc(double d) {
        if (!std::isfinite(d) || d < -9223372036854775808.0 || d >= 9223372036854775808.0)
            return 0;
        return uint32_t(uint64_t(int64_t(d)));
    }
    uint32_t rem(uint32_t a, uint32_t b) {
        if (!b || (a == 0x80000000 && b == 0xffffffff)) {
            c().fault = 2;
            throw Failed{};
        }
        return uint32_t(si(a) % si(b));
    }
    uint32_t prime(uint32_t n) {
        for (uint32_t i = 2; si(i) < si(n); ++i) {
            tick();
            if (!rem(n, i))
                return 0;
        }
        return 1;
    }
    void permutation(uint32_t output, uint32_t low, uint32_t high, uint32_t initial) {
        if (si(low) >= si(high))
            return;
        uint32_t difference = high - low, N = difference;
        while (si(N) < 100000) {
            tick();
            if (prime(N))
                break;
            ++N;
        }
        if (si(N) >= 100000)
            N = initial;
        uint32_t allocated = service(0x4f63ec, 0, {N * 4});
        if (!allocated)
            return;
        uint32_t multiplier = allocated;
        for (uint32_t candidate = 1; si(candidate) < si(N - 1); ++candidate) {
            tick();
            for (uint32_t i = 0; si(i) < si(N); ++i)
                wr(allocated + i * 4, 0);
            uint32_t current = initial, count = 0;
            bool unique = true;
            while (si(count) < si(N - 1)) {
                tick();
                current = rem(candidate * current, N);
                const uint32_t address = allocated + (current - 1) * 4;
                if (rd(address)) {
                    unique = false;
                    break;
                }
                ++count;
                wr(address, 1);
            }
            if (unique) {
                multiplier = candidate;
                break;
            }
        }
        uint32_t current = initial;
        for (uint32_t i = 0; si(i) < si(N); ++i) {
            tick();
            current = rem(multiplier * current, N);
            if (si(current - 1) <= si(difference)) {
                uint32_t value = current - 1 + low;
                uint32_t clamp = si(value) >= si(high) ? high : value;
                if (si(clamp) < 0)
                    value = 0;
                else if (si(value) >= si(high))
                    value = high;
                wr(output, value);
                output += 4;
            }
        }
        service(0x4f6428, 0, {allocated});
    }
    uint32_t init(uint32_t t, uint32_t d) {
        wr(t + 0x20, 0);
        wr(t + 0x40, rd(d + 12));
        wr(t + 0x38, rd(d + 4) ? rd(d + 4) : rd(t + 0x24));
        wr(t + 0x3c, rd(d + 8) ? rd(d + 8) : rd(t + 0x28));
        uint32_t surface = rd(t + 0x38);
        if (!surface)
            return 0;
        if (!rd(t + 0x3c))
            wr(t + 0x40, 1);
        wr(t + 0x50, rd(surface + 0x18));
        wr(t + 0x4c, rd(surface + 0x14));
        uint32_t percent = rd(d + 16);
        if (si(percent) < 0 || si(percent) > 100)
            return 0;
        wr(t + 0x58, percent);
        wr(t + 0x54,
           trunc((double(si(percent)) * double(float(0.00999999977648258209228515625))) * double(si(rd(t + 0x4c)))));
        for (uint32_t i = 0; i < 2000; ++i) {
            tick();
            wr(t + 0x5c + i * 4, 0);
            wr(t + 0x3edc + i * 4, 0);
            wr(t + 0x5e1c + i * 4, 0);
            uint32_t width = rd(t + 0x50);
            uint32_t random = service(0x4a3050, 0);
            wr(t + 0x1f9c + i * 4, rem(random, width));
        }
        permutation(t + 0x5e1c, 0, rd(t + 0x50), 1);
        return 1;
    }
    void unlock(uint32_t surface) {
        if (surface) {
            uint32_t dd = rd(surface + 8);
            service(rd(rd(dd) + 0x80), 0, {dd, 0});
        }
    }
    void step(uint32_t t, uint32_t count) {
        if (!count)
            return;
        uint32_t s = rd(t + 0x38);
        if (s)
            wr(t + 0x44, service(0x4b9730, s, {0}));
        s = rd(t + 0x3c);
        if (s)
            wr(t + 0x48, service(0x4b9730, s, {0}));
        const uint32_t bpp = rd(rd(t + 0x38) + 0xac);
        float ratio = float(double(si(rd(t + 0x50))) / double(si(rd(t + 0x54))));
        uint32_t row = rd(t + 0x4c) - count;
        while (si(row) < si(rd(t + 0x4c) - count + rd(t + 0x54))) {
            tick();
            if (si(row) >= 0 && si(row) < si(rd(t + 0x4c))) {
                uint32_t destination = rd(t + 0x44) + row * rd(rd(t + 0x38) + 0x1c);
                uint32_t progress = row + count - rd(t + 0x4c);
                double angle =
                    (double(uint64_t(progress)) / double(si(rd(t + 0x54)))) * double(float(1.5707950592041015625));
                double wave = std::sin(angle);
                wave *= double(si(rd(t + 0x50)));
                wave /= double(ratio);
                uint32_t delta = trunc(wave) - rd(t + 0x5c + row * 4);
                double amount = double(si(delta)) * double(ratio);
                uint32_t integral = trunc(amount), extra = 0;
                uint32_t fraction = t + 0x3edc + row * 4;
                if (double(si(integral)) < amount)
                    wf(fraction, float((amount - double(si(integral))) + double(rf(fraction))));
                if (double(rf(fraction)) >= double(float(1))) {
                    extra = trunc(double(rf(fraction)));
                    wf(fraction, float(double(rf(fraction)) - double(si(extra))));
                }
                bool clear = rd(t + 0x40) != 0;
                uint32_t source = clear ? 0 : rd(t + 0x48) + row * rd(rd(t + 0x3c) + 0x1c);
                uint32_t pixels = integral + extra;
                while (si(pixels) > 0) {
                    tick();
                    uint32_t cursor = t + 0x1f9c + row * 4;
                    wr(cursor, rd(cursor) + 1);
                    if (si(rd(cursor)) > si(rd(t + 0x50)))
                        wr(cursor, 0);
                    uint32_t x = rd(t + 0x5e1c + rd(cursor) * 4);
                    pixel(destination + x * bpp, source + x * bpp, bpp, clear);
                    --pixels;
                }
                wr(t + 0x5c + row * 4, rd(t + 0x5c + row * 4) + delta);
                pixels = trunc(double(ratio) + double(ratio));
                while (si(pixels) > 0) {
                    tick();
                    uint32_t width = rd(t + 0x50);
                    uint32_t x = rem(service(0x4a3050, 0), width);
                    pixel(destination + x * bpp, source + x * bpp, bpp, clear);
                    --pixels;
                }
            }
            ++row;
        }
        row = rd(t + 0x20);
        while (si(row) < si(count)) {
            tick();
            uint32_t y = rd(t + 0x54) - row - 1 + rd(t + 0x4c);
            if (si(y) >= 0 && si(y) < si(rd(t + 0x4c))) {
                uint32_t dst = rd(t + 0x44) + y * rd(rd(t + 0x38) + 0x1c);
                bool clear = rd(t + 0x40) != 0;
                uint32_t src = clear ? 0 : rd(t + 0x48) + y * rd(rd(t + 0x3c) + 0x1c);
                pixel(dst, src, bpp * rd(t + 0x50), clear);
            }
            ++row;
        }
        wr(t + 0x20, count);
        unlock(rd(t + 0x38));
        unlock(rd(t + 0x3c));
    }
    void diagnostic(uint32_t text) {
        frozen(0x4f65f2, w.common->temporaryStringToken, {text});
        frozen(0x4ec6b0, 0, {rd(w.common->temporaryStringToken)});
    }
    uint32_t factory(uint32_t t, uint32_t type, uint32_t desc) {
        if (type != 2) {
            c().fault = 3;
            throw Failed{};
        }
        if (desc && rd(desc) != 3) {
            diagnostic(0x53404c);
            return 0;
        }
        uint32_t effect = service(0x4f63ec, 0, {CLAW_WARP_FADE_BYTES});
        if (effect)
            entry(0x4ed060, effect, nullptr, 0);
        frozen(0x4ecb00, effect, {rd(t), rd(t + 4)});
        frozen(0x4ecb20, effect, {rd(t + 0x24)});
        if (!desc) {
            desc = c().temporaryDescriptorToken;
            entry(0x4ecc00, desc, nullptr, 0);
        }
        if (!init(effect, desc)) {
            diagnostic(0x5340a0);
            uint32_t one = 1;
            uint32_t del = rd(rd(effect));
            if (del == 0x4ed080)
                entry(del, effect, &one, 1);
            else
                service(del, effect, {1});
            return 0;
        }
        uint32_t index = rd(t + 0x18);
        resize(t + 0x10, index + 1);
        wr(rd(t + 0x14) + index * 4, effect);
        return effect;
    }
    static uint32_t arrayCall(ClawCArrayContext *, const ClawCArrayCall *e, void *v) {
        auto &r = *static_cast<Run *>(v);
        ClawPlayerFadeCall q{};
        q.function = e->function;
        q.receiver = e->receiver;
        q.argumentCount = e->argumentCount;
        std::copy_n(e->arguments, e->argumentCount, q.arguments);
        return route(&r.c(), &q, &r);
    }
    void resize(uint32_t t, uint32_t n) {
        ClawCArrayContext context{};
        context.scene = c().scene;
        claw_carray_defaults(&context);
        uint32_t out = 0;
        claw_carray_entry(0x4f5915, t, n, 0xffffffff, 0, &context, arrayCall, this, &out);
        if (context.fault) {
            c().fault = context.fault;
            throw Failed{};
        }
    }
    uint32_t entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        auto need = [&](uint32_t k) {
            if (n != k) {
                c().fault = 2;
                throw Failed{};
            }
        };
        switch (f) {
        case 0x4ed060:
            need(0);
            frozen(0x4ec8d0, t);
            wr(t, 0x514228);
            wr(t + 0x50, 0);
            wr(t + 0x4c, 0);
            return t;
        case 0x4ed0a0:
            need(0);
            wr(t, 0x514228);
            frozen(0x4ec920, t);
            return 0;
        case 0x4ed080:
            need(1);
            entry(0x4ed0a0, t, nullptr, 0);
            if (a[0] & 1)
                service(0x4f6428, 0, {t});
            return t;
        case 0x4ed0b0:
            need(1);
            return init(t, a[0]);
        case 0x4ed1a0:
            need(1);
            step(t, a[0]);
            return 0;
        case 0x4ed5d0:
            need(0);
            return rd(t + 0x54) + rd(t + 0x4c);
        case 0x4ecc00:
            need(0);
            wr(t, 3);
            wr(t + 4, 0);
            wr(t + 8, 0);
            wr(t + 12, 1);
            wr(t + 16, 15);
            return t;
        case 0x4efb00:
            need(4);
            permutation(a[0], a[1], a[2], a[3]);
            return 0;
        case 0x4efc40:
            need(1);
            return prime(a[0]);
        case 0x4ec050:
            need(2);
            return factory(t, a[0], a[1]);
        default: {
            uint32_t out = 0;
            if (!claw_player_fade_entry(f, t, a, n, &c(), route, this, &out)) {
                if (!c().fault)
                    c().fault = 3;
                throw Failed{};
            }
            return out;
        }
        }
    }
};
bool owned(uint32_t f) {
    switch (f) {
    case 0x4ed060:
    case 0x4ed0a0:
    case 0x4ed080:
    case 0x4ed0b0:
    case 0x4ed1a0:
    case 0x4ed5d0:
    case 0x4ecc00:
    case 0x4efb00:
    case 0x4efc40:
        return true;
    default:
        return false;
    }
}
uint32_t route(ClawPlayerFadeContext *, const ClawPlayerFadeCall *e, void *v) {
    auto &r = *static_cast<Run *>(v);
    try {
        if (owned(e->function))
            return r.entry(e->function, e->receiver, e->arguments, e->argumentCount);
        if (e->function == 0x4c61f0 || e->function == 0x4c7510) {
            uint32_t out = 0;
            if (!claw_player_fade_blend_entry(e->function, e->receiver, e->arguments, e->argumentCount, r.w.common,
                                              route, &r, &out) &&
                !r.c().fault)
                r.c().fault = 3;
            return out;
        }
        if (r.dependency)
            return r.dependency(&r.c(), e, r.user);
        if (e->argumentCount <= 4 && r.c().scene.call) {
            ClawSceneActorCall q{};
            q.function = e->function;
            q.receiver = e->receiver;
            q.argumentCount = e->argumentCount;
            std::copy_n(e->arguments, e->argumentCount, q.arguments);
            return r.c().scene.call(r.c().scene.context, q);
        }
        r.c().fault = 1;
    } catch (Failed &) {
    }
    return 0;
}
} // namespace
extern "C" uint32_t claw_warp_fade_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, ClawWarpFadeContext *w,
                                         ClawPlayerFadeDependency d, void *u, uint32_t *result) {
    if (!w || !w->common || !w->common->fade || !result || (n && !a) || n > 6)
        return 0;
    if (!owned(f) && f != 0x4ec050 && f != 0x4ec9c0 && f != 0x4ec600)
        return 0;
    Run r{*w, d, u};
    if (r.c().fault)
        return 0;
    try {
        *result = r.entry(f, t, a, n);
    } catch (Failed &) {
    }
    return r.c().fault ? 0 : 1;
}
