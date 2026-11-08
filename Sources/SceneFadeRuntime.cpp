#include "SceneFadeRuntime.h"
#include "WorldLootRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
struct Run {
    ClawSceneFadeContext &c;
    ClawPlayerFadeDependency d;
    void *u;
    ClawPlayerFadeContext &f() {
        return *c.blend->fade;
    }
    uint32_t *p(uint32_t t, uint32_t n = 1) {
        if (f().fault)
            throw Failure{};
        auto v = f().scene.lookup ? f().scene.lookup(f().scene.context, t, n) : nullptr;
        if (!v) {
            f().fault = 1;
            throw Failure{};
        }
        return v;
    }
    uint32_t get(uint32_t t, uint32_t off = 0) {
        return *p(t + off);
    }
    void put(uint32_t t, uint32_t off, uint32_t v) {
        *p(t + off) = v;
    }
    void bad(uint32_t code = 2) {
        f().fault = code;
        throw Failure{};
    }
    uint32_t service(uint32_t fn, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawPlayerFadeCall e{};
        e.function = fn;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), e.arguments);
        if (d)
            return d(&f(), &e, u);
        if (a.size() > 4 || !f().scene.call)
            bad(1);
        ClawSceneActorCall s{};
        s.function = fn;
        s.receiver = t;
        s.argumentCount = e.argumentCount;
        std::copy(a.begin(), a.end(), s.arguments);
        return f().scene.call(f().scene.context, s);
    }
    static uint32_t composed(ClawPlayerFadeContext *, const ClawPlayerFadeCall *e, void *v) {
        auto &r = *static_cast<Run *>(v);
        uint32_t result = 0;
        if (e->function == 0x4ed1a0 || e->function == 0x4ed5d0 || e->function == 0x4ed080 || e->function == 0x4ed0a0 ||
            e->function == 0x4ec050 || e->function == 0x4c96b0 || e->function == 0x4c61f0 || e->function == 0x4c7510) {
            if (!claw_scene_fade_entry(e->function, e->receiver, e->arguments, e->argumentCount, &r.c, r.d, r.u,
                                       &result) &&
                !r.f().fault)
                r.f().fault = 3;
            return result;
        }
        if (r.d)
            return r.d(&r.f(), e, r.u);
        switch (e->argumentCount) {
        case 0:
            return r.service(e->function, e->receiver);
        case 1:
            return r.service(e->function, e->receiver, {e->arguments[0]});
        case 2:
            return r.service(e->function, e->receiver, {e->arguments[0], e->arguments[1]});
        case 3:
            return r.service(e->function, e->receiver, {e->arguments[0], e->arguments[1], e->arguments[2]});
        default:
            r.bad(1);
        }
        return 0;
    }
    uint32_t frozen(uint32_t fn, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        uint32_t args[6]{}, out = 0;
        std::copy(a.begin(), a.end(), args);
        if (!claw_player_fade_entry(fn, t, args, uint32_t(a.size()), &f(), composed, this, &out))
            throw Failure{};
        return out;
    }
    uint32_t blend(uint32_t fn, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        uint32_t args[6]{}, out = 0;
        std::copy(a.begin(), a.end(), args);
        if (!claw_player_fade_blend_entry(fn, t, args, uint32_t(a.size()), c.blend, composed, this, &out))
            throw Failure{};
        return out;
    }
    uint32_t random() {
        auto thread = service(0x4a7dc0, 0);
        return claw_world_loot_next_random(p(thread + 0x14));
    }
    uint32_t ftol(double x) {
        if (!std::isfinite(x) || x < -9223372036854775808.0 || x >= 9223372036854775808.0)
            return 0;
        return uint32_t(uint64_t(int64_t(x)));
    }
    float fraction(uint32_t t) {
        float x;
        auto v = get(t);
        std::memcpy(&x, &v, 4);
        return x;
    }
    void fraction(uint32_t t, float x) {
        uint32_t v;
        std::memcpy(&v, &x, 4);
        put(t, 0, v);
    }
    uint8_t *bytes(uint32_t t, uint32_t n) {
        if (!n)
            return nullptr;
        return reinterpret_cast<uint8_t *>(p(t & ~3u, (n + (t & 3u) + 3) / 4)) + (t & 3u);
    }
    void transfer(uint32_t dst, uint32_t src, uint32_t n, bool clear) {
        if (int32_t(n) <= 0)
            return;
        auto a = bytes(dst, n);
        if (clear)
            std::memset(a, 0, n);
        else {
            auto b = bytes(src, n);
            for (uint32_t i = 0; i < n; ++i)
                a[i] = b[i];
        }
    }
    bool prime(uint32_t value) {
        auto n = int32_t(value);
        if (n < 3)
            return true;
        if (n > 100000)
            bad();
        for (int32_t i = 2; i < n; ++i)
            if (n % i == 0)
                return false;
        return true;
    }
    void permutation(uint32_t output, uint32_t lo, uint32_t hi, uint32_t start) {
        if (int32_t(lo) >= int32_t(hi))
            return;
        auto diff = hi - lo, modulus = diff;
        while (int32_t(modulus) < 100000 && !prime(modulus))
            ++modulus;
        if (int32_t(modulus) >= 100000)
            modulus = start;
        if (!modulus || int32_t(modulus) > 100000)
            bad();
        auto temp = service(0x4f63ec, 0, {modulus * 4});
        if (!temp)
            return;
        auto multiplier = temp;
        uint32_t trial = 1;
        if (int32_t(modulus - 1) > 1) {
            for (; int32_t(trial) < int32_t(modulus - 1); ++trial) {
                std::memset(p(temp, modulus), 0, modulus * 4);
                bool good = true;
                auto value = start;
                for (uint32_t i = 0; i < modulus - 1; ++i) {
                    value = uint32_t(int32_t(trial * value) % int32_t(modulus));
                    if (get(temp, (value - 1) * 4)) {
                        good = false;
                        break;
                    }
                    put(temp, (value - 1) * 4, 1);
                }
                if (good) {
                    multiplier = trial;
                    break;
                }
            }
        }
        auto value = start;
        for (uint32_t i = 0; i < modulus; ++i) {
            value = uint32_t(int32_t(multiplier * value) % int32_t(modulus));
            if (int32_t(value - 1) <= int32_t(diff)) {
                auto result = value - 1 + lo;
                if (int32_t(std::min(int32_t(result), int32_t(hi))) < 0)
                    result = 0;
                else if (int32_t(result) >= int32_t(hi))
                    result = hi;
                put(output, 0, result);
                output += 4;
            }
        }
        service(0x4f6428, 0, {temp});
    }
    uint32_t ctor(uint32_t t) {
        frozen(0x4ec8d0, t);
        put(t, 0, 0x514228);
        put(t, 0x50, 0);
        put(t, 0x4c, 0);
        return t;
    }
    uint32_t init(uint32_t t, uint32_t desc) {
        put(t, 0x20, 0);
        put(t, 0x40, get(desc, 12));
        put(t, 0x38, get(desc, 4) ? get(desc, 4) : get(t, 0x24));
        put(t, 0x3c, get(desc, 8) ? get(desc, 8) : get(t, 0x28));
        auto surface = get(t, 0x38);
        if (!surface)
            return 0;
        if (!get(t, 0x3c))
            put(t, 0x40, 1);
        put(t, 0x50, get(surface, 0x18));
        put(t, 0x4c, get(surface, 0x14));
        auto percent = get(desc, 16);
        if (int32_t(percent) < 0 || int32_t(percent) > 100)
            return 0;
        put(t, 0x58, percent);
        put(t, 0x54, ftol((double(int32_t(percent)) * double(0.009999999776482582f)) * double(int32_t(get(t, 0x4c)))));
        for (uint32_t i = 0; i < 2000; ++i) {
            put(t, 0x5c + i * 4, 0);
            put(t, 0x3edc + i * 4, 0);
            put(t, 0x5e1c + i * 4, 0);
            auto width = get(t, 0x50);
            auto v = random();
            if (!width || int32_t(width) < 0)
                bad();
            put(t, 0x1f9c + i * 4, uint32_t(int32_t(v) % int32_t(width)));
        }
        auto width = get(t, 0x50);
        if (width >= 2000 || get(t, 0x4c) > 2000)
            bad();
        permutation(t + 0x5e1c, 0, width, 1);
        return 1;
    }
    void unlock(uint32_t surface) {
        if (surface) {
            auto dd = get(surface, 8);
            service(get(get(dd), 0x80), 0, {dd, 0});
        }
    }
    void step(uint32_t t, uint32_t value) {
        if (!value)
            return;
        auto s = get(t, 0x38);
        if (s)
            put(t, 0x44, service(0x4b9730, s, {0}));
        s = get(t, 0x3c);
        if (s)
            put(t, 0x48, service(0x4b9730, s, {0}));
        const auto height = get(t, 0x4c), band = get(t, 0x54), width = get(t, 0x50), bpp = get(get(t, 0x38), 0xac);
        const float scale = float(double(int32_t(width)) / double(int32_t(band)));
        if (width >= 2000 || height > 2000 || bpp > 4)
            bad();
        auto row = height - value;
        for (uint32_t loops = 0; int32_t(row) < int32_t(get(t, 0x4c) - value + get(t, 0x54)); ++row) {
            if (++loops > 100000)
                bad();
            if (int32_t(row) < 0 || int32_t(row) >= int32_t(get(t, 0x4c)))
                continue;
            auto dst = get(t, 0x44) + get(get(t, 0x38), 0x1c) * row;
            auto src = get(t, 0x48) + (get(t, 0x3c) ? get(get(t, 0x3c), 0x1c) * row : 0);
            const bool clear = get(t, 0x40) != 0;
            auto phase = double(uint64_t(row + value - get(t, 0x4c))) / double(int32_t(get(t, 0x54)));
            auto progress =
                ftol((std::sin(phase * double(1.5707950592041016f)) * double(int32_t(get(t, 0x50)))) / double(scale));
            auto delta = progress - get(t, 0x5c + row * 4);
            double pixels = double(int32_t(delta)) * double(scale);
            auto integral = ftol(pixels), extra = 0u;
            auto residual = fraction(t + 0x3edc + row * 4);
            if (double(int32_t(integral)) < pixels) {
                residual = float((pixels - double(int32_t(integral))) + double(residual));
                fraction(t + 0x3edc + row * 4, residual);
            }
            if (residual >= 1.0f) {
                extra = ftol(residual);
                fraction(t + 0x3edc + row * 4, float(double(residual) - double(int32_t(extra))));
            }
            auto n = extra + integral;
            if (int32_t(n) > 100000)
                bad();
            for (uint32_t i = 0; int32_t(i) < int32_t(n); ++i) {
                auto index = get(t, 0x1f9c + row * 4) + 1;
                if (int32_t(index) > int32_t(get(t, 0x50)))
                    index = 0;
                put(t, 0x1f9c + row * 4, index);
                auto x = get(t, 0x5e1c + index * 4);
                transfer(dst + x * bpp, src + x * bpp, bpp, clear);
            }
            put(t, 0x5c + row * 4, get(t, 0x5c + row * 4) + delta);
            auto count = ftol(double(scale) + double(scale));
            if (int32_t(count) > 100000)
                bad();
            for (uint32_t i = 0; int32_t(i) < int32_t(count); ++i) {
                auto w = get(t, 0x50);
                auto rand = random();
                if (!w || int32_t(w) < 0)
                    bad();
                auto x = uint32_t(int32_t(rand) % int32_t(w));
                transfer(dst + x * bpp, src + x * bpp, bpp, clear);
            }
        }
        auto previous = get(t, 0x20);
        for (uint32_t loops = 0; int32_t(previous) < int32_t(value); ++previous) {
            if (++loops > 100000)
                bad();
            auto r = get(t, 0x54) - previous - 1 + get(t, 0x4c);
            if (int32_t(r) < 0 || int32_t(r) >= int32_t(get(t, 0x4c)))
                continue;
            auto dst = get(t, 0x44) + get(get(t, 0x38), 0x1c) * r;
            auto src = get(t, 0x48) + (get(t, 0x3c) ? get(get(t, 0x3c), 0x1c) * r : 0);
            transfer(dst, src, bpp * get(t, 0x50), get(t, 0x40) != 0);
        }
        put(t, 0x20, value);
        unlock(get(t, 0x38));
        unlock(get(t, 0x3c));
    }
    void diagnostic(uint32_t text) {
        auto temp = c.blend->temporaryStringToken;
        blend(0x4f65f2, temp, {text});
        blend(0x4ec6b0, 0, {get(temp)});
    }
    uint32_t factory(uint32_t manager, uint32_t type, uint32_t descriptor) {
        if (type != 2)
            bad(3);
        if (descriptor && get(descriptor) != 3) {
            diagnostic(0x53404c);
            return 0;
        }
        auto t = service(0x4f63ec, 0, {CLAW_SCENE_TYPE2_FADER_BYTES});
        if (t)
            ctor(t);
        frozen(0x4ecb00, t, {get(manager), get(manager, 4)});
        frozen(0x4ecb20, t, {get(manager, 0x24)});
        if (!descriptor) {
            descriptor = f().temporaryDescriptorToken;
            uint32_t v[5] = {3, 0, 0, 1, 15};
            std::copy(v, v + 5, p(descriptor, 5));
        }
        if (!init(t, descriptor)) {
            diagnostic(0x5340a0);
            if (t) {
                auto fn = get(get(t));
                if (fn == 0x4ed080)
                    destroy(t, 1);
                else
                    service(fn, t, {1});
            }
            return 0;
        }
        auto index = get(manager, 0x18);
        ClawCArrayContext ac{};
        ac.scene = f().scene;
        claw_carray_defaults(&ac);
        uint32_t result = 0;
        claw_carray_entry(0x4f5915, manager + 0x10, index + 1, 0xffffffff, 0, &ac, arrayDependency, this, &result);
        if (ac.fault) {
            f().fault = ac.fault;
            throw Failure{};
        }
        put(get(manager, 0x14), index * 4, t);
        return t;
    }
    static uint32_t arrayDependency(ClawCArrayContext *, const ClawCArrayCall *e, void *v) {
        return static_cast<Run *>(v)->service(e->function, e->receiver, {e->arguments[0]});
    }
    void dtor(uint32_t t) {
        put(t, 0, 0x514228);
        frozen(0x4ec920, t);
    }
    uint32_t destroy(uint32_t t, uint32_t flag) {
        dtor(t);
        if (flag & 1)
            service(0x4f6428, 0, {t});
        return t;
    }
};
} // namespace
extern "C" uint32_t claw_scene_fade_entry(uint32_t fn, uint32_t receiver, const uint32_t *a, uint32_t n,
                                          ClawSceneFadeContext *c, ClawPlayerFadeDependency d, void *u, uint32_t *out) {
    if (!c || !c->blend || !c->blend->fade || !out || (!a && n))
        return 0;
    auto &f = *c->blend->fade;
    uint32_t required = 0;
    switch (fn) {
    case 0x4ec050:
    case 0x4ecb00:
        required = 2;
        break;
    case 0x4ed0b0:
    case 0x4ed1a0:
    case 0x4ed080:
    case 0x4ec990:
    case 0x4ec600:
    case 0x4ecb20:
        required = 1;
        break;
    case 0x4ec9c0:
        required = 3;
        break;
    case 0x4efb00:
        required = 4;
        break;
    case 0x4efc40:
        required = 1;
        break;
    case 0x4c96b0:
    case 0x4ed060:
    case 0x4ed5d0:
    case 0x4ed0a0:
    case 0x4ecc00:
    case 0x4ec8d0:
    case 0x4c61f0:
    case 0x4c7510:
        required = fn == 0x4c7510 ? 1 : 0;
        break;
    default:
        return 0;
    }
    if (n != required) {
        f.fault = 2;
        return 0;
    }
    Run r{*c, d, u};
    *out = 0;
    try {
        switch (fn) {
        case 0x4c96b0:
            break;
        case 0x4ec050:
            *out = r.factory(receiver, a[0], a[1]);
            break;
        case 0x4ed060:
            *out = r.ctor(receiver);
            break;
        case 0x4ed0b0:
            *out = r.init(receiver, a[0]);
            break;
        case 0x4ed1a0:
            r.step(receiver, a[0]);
            break;
        case 0x4ed5d0:
            *out = r.get(receiver, 0x54) + r.get(receiver, 0x4c);
            break;
        case 0x4ed080:
            *out = r.destroy(receiver, a[0]);
            break;
        case 0x4ed0a0:
            r.dtor(receiver);
            break;
        case 0x4efb00:
            r.permutation(a[0], a[1], a[2], a[3]);
            break;
        case 0x4efc40:
            *out = r.prime(a[0]);
            break;
        case 0x4ecc00: {
            uint32_t v[5] = {3, 0, 0, 1, 15};
            std::copy(v, v + 5, r.p(receiver, 5));
            *out = receiver;
            break;
        }
        case 0x4c61f0:
            r.blend(fn, receiver);
            break;
        case 0x4c7510:
            r.blend(fn, receiver, {a[0]});
            break;
        default: {
            std::initializer_list<uint32_t> z{};
            if (n == 0)
                *out = r.frozen(fn, receiver, z);
            else if (n == 1)
                *out = r.frozen(fn, receiver, {a[0]});
            else if (n == 2)
                *out = r.frozen(fn, receiver, {a[0], a[1]});
            else
                *out = r.frozen(fn, receiver, {a[0], a[1], a[2]});
            break;
        }
        }
    } catch (Failure &) {
    }
    return f.fault ? 0 : 1;
}
