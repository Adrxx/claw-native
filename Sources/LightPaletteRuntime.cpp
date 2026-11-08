#include "LightPaletteRuntime.h"
#include "PlayerFadeBlendRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
namespace {
//Exact256 discrete_CIpow(base,1) outputs from pinned original/CW53.
//The CRT does not always return the input bit-for-bit. This finite profile
//is source-generated data, not a replacement general pow implementation.
const uint64_t powOne[256] = {
    0x3ff0000000000000ULL, 0x3fefdfffffe05fc0ULL, 0x3fefc03fc000fd84ULL, 0x3fefa0be829ca244ULL, 0x3fef817b8cdc60fbULL,
    0x3fef627626c928e6ULL, 0x3fef43ad9b3dacbbULL, 0x3fef252137d89c75ULL, 0x3fef06d04cef2f9dULL, 0x3feee8ba2d7ffde2ULL,
    0x3feecade2f2623e8ULL, 0x3feead3baa0cb25bULL, 0x3fee8fd1f8e2654aULL, 0x3fee72a078cda1e7ULL, 0x3fee55a68960b8dfULL,
    0x3fee38e38c8e6b75ULL, 0x3fee1c56e69eb1b3ULL, 0x3fedfffffe23c000ULL, 0x3fede3de3bef4a79ULL, 0x3fedc7f10b080479ULL,
    0x3fedac37d89f5aceULL, 0x3fed90b214076714ULL, 0x3fed755f2ea91accULL, 0x3fed5a3e9bfaa0c6ULL, 0x3fed3f4fd175f383ULL,
    0x3fed2492468fa72fULL, 0x3fed0a0574ade605ULL, 0x3fecefa8d71f9dbaULL, 0x3fecd57beb13dcdaULL, 0x3fecbb7e2f915ed0ULL,
    0x3feca1af256e457fULL, 0x3fec880e4f47ff4dULL, 0x3fec6e9b317b5888ULL, 0x3fec5555521cb71dULL, 0x3fec3c3c38f07f8fULL,
    0x3fec234f6f63a23fULL, 0x3fec0a8e80844ffeULL, 0x3febf1f8f8fad502ULL, 0x3febd98e6702994bULL, 0x3febc14e5a6345a0ULL,
    0x3feba938646a0c36ULL, 0x3feb914c17e31433ULL, 0x3feb79890913073dULL, 0x3feb61eecdb0c03fULL, 0x3feb4a7cfcdf1aa6ULL,
    0x3feb33332f26e148ULL, 0x3feb1c10fe70dc4fULL, 0x3feb051605fffd4fULL, 0x3feaee41e26ba8f9ULL, 0x3fead794319a1d9cULL,
    0x3feac10c92baf5e4ULL, 0x3feaaaaaa641c71dULL, 0x3fea946e0de0da6eULL, 0x3fea7e566c840059ULL, 0x3fea6863664b7dfdULL,
    0x3fea5294a0871373ULL, 0x3fea3ce9c1b11ac4ULL, 0x3fea27627169bedeULL, 0x3fea11fe58724a0bULL, 0x3fe9fcbd20a88b57ULL,
    0x3fe9e79e7502526fULL, 0x3fe9d2a201890170ULL, 0x3fe9bdc77355342fULL, 0x3fe9a90e788a7c7fULL, 0x3fe99476c05332ffULL,
    0x3fe97ffffadc5c01ULL, 0x3fe96ba9d951a014ULL, 0x3fe957740dd957c6ULL, 0x3fe9435e4b90aa33ULL, 0x3fe92f684687bdfcULL,
    0x3fe91b91b3bdfc3fULL, 0x3fe907da491e6528ULL, 0x3fe8f441bd7bf5c0ULL, 0x3fe8e0c7c88e1e9dULL, 0x3fe8cd6c22ed4b17ULL,
    0x3fe8ba2e860f789aULL, 0x3fe8a70eac44ddd7ULL, 0x3fe8940c50b4a16eULL, 0x3fe881272f599fb9ULL, 0x3fe86e5f04ff3f76ULL,
    0x3fe85bb38f3e54faULL, 0x3fe849248c7a1399ULL, 0x3fe836b1bbdd0cffULL, 0x3fe8245add563e31ULL, 0x3fe8121fb19629e8ULL,
    0x3fe7fffffa0c0001ULL, 0x3fe7edfb78e2d1c4ULL, 0x3fe7dc11f0fed2b3ULL, 0x3fe7ca4325faa5acULL, 0x3fe7b88edc24b612ULL,
    0x3fe7a6f4d87c9ccdULL, 0x3fe79574e0b090cdULL, 0x3fe7840ebb1ae2f3ULL, 0x3fe772c22ebf8507ULL, 0x3fe7618f03499b9bULL,
    0x3fe7507501091a8cULL, 0x3fe73f73f0f06c06ULL, 0x3fe72e8b9c9221baULL, 0x3fe71dbbce1eb022ULL, 0x3fe70d04506233a2ULL,
    0x3fe6fc64eec23f49ULL, 0x3fe6ebdd753bb507ULL, 0x3fe6db6db060a731ULL, 0x3fe6cb156d564313ULL, 0x3fe6bad479d2c471ULL,
    0x3fe6aaaaa41b71c9ULL, 0x3fe69a97bb02a11dULL, 0x3fe68a9b8de5c533ULL, 0x3fe67ab5ecab8306ULL, 0x3fe66ae6a7c1cf59ULL,
    0x3fe65b2d901c142fULL, 0x3fe64b8a77315e0eULL, 0x3fe63bfd2efa90e5ULL, 0x3fe62c8589f0a46dULL, 0x3fe61d235b0ae7ddULL,
    0x3fe60dd675bd4cddULL, 0x3fe5fe9eadf6b983ULL, 0x3fe5ef7bd81f613eULL, 0x3fe5e06dc9172493ULL, 0x3fe5d1745633f78cULL,
    0x3fe5c28f55404ea7ULL, 0x3fe5b3be9c799243ULL, 0x3fe5a502028e9852ULL, 0x3fe596595e9e2442ULL, 0x3fe587c488356cf9ULL,
    0x3fe57943574ea8c9ULL, 0x3fe56ad5a44f9f41ULL, 0x3fe55c7b480840bdULL, 0x3fe54e341bb1439cULL, 0x3fe53ffff8eac702ULL,
    0x3fe531deb9bafb0bULL, 0x3fe523d0388cce54ULL, 0x3fe515d4502ea0c5ULL, 0x3fe507eadbd0fb85ULL, 0x3fe4fa13b7054df9ULL,
    0x3fe4ec4ebdbcafbaULL, 0x3fe4de9bcc46a773ULL, 0x3fe4d0fabf4ff685ULL, 0x3fe4c36b73e1695fULL, 0x3fe4b5edc75eac7bULL,
    0x3fe4a881978525dfULL, 0x3fe49b26c26ad31cULL, 0x3fe48ddd267d2baaULL, 0x3fe480a4a2800790ULL, 0x3fe4737d158c8a4fULL,
    0x3fe466665f1011eeULL, 0x3fe459605ecb2a20ULL, 0x3fe44c6af4d08367ULL, 0x3fe43f860183ee33ULL, 0x3fe432b1659959d4ULL,
    0x3fe425ed0213d746ULL, 0x3fe41938b8449fb7ULL, 0x3fe40c9469ca1eb5ULL, 0x3fe3fffff88f0003ULL, 0x3fe3f37b46c940f5ULL,
    0x3fe3e70636f9454eULL, 0x3fe3daa0abe8ef85ULL, 0x3fe3ce4a88aabc78ULL, 0x3fe3c203b098e260ULL, 0x3fe3b5cc07547314ULL,
    0x3fe3a9a370c4817bULL, 0x3fe39d89d1154a24ULL, 0x3fe3917f0cb75f00ULL, 0x3fe38583085ed61aULL, 0x3fe37995a9027b5cULL,
    0x3fe36db6d3db053cULL, 0x3fe361e66e624c57ULL, 0x3fe356245e5285ddULL, 0x3fe34a7089a580d1ULL, 0x3fe33ecad693e60aULL,
    0x3fe333332b947ae4ULL, 0x3fe327a96f5b66a5ULL, 0x3fe31c2d88d97a77ULL, 0x3fe310bf5f3b7c00ULL, 0x3fe3055ed9e97279ULL,
    0x3fe2fa0be085f652ULL, 0x3fe2eec65aed833cULL, 0x3fe2e38e3135cca7ULL, 0x3fe2d8634bad149eULL, 0x3fe2cd4592d984f6ULL,
    0x3fe2c234ef788ad2ULL, 0x3fe2b7314a7e345fULL, 0x3fe2ac3a8d1490d9ULL, 0x3fe2a150a09b12b3ULL, 0x3fe296736ea5f3efULL,
    0x3fe28ba2e0fd9c93ULL, 0x3fe280dee19e0b38ULL, 0x3fe276275ab63fa2ULL, 0x3fe26b7c36a7a762ULL, 0x3fe260dd60058c73ULL,
    0x3fe2564ac19485d0ULL, 0x3fe24bc44649e9f8ULL, 0x3fe24149d94b4352ULL, 0x3fe236db65edc676ULL, 0x3fe22c78d7b5ca4fULL,
    0x3fe222221a564201ULL, 0x3fe217d719b038a9ULL, 0x3fe20d97c1d24eceULL, 0x3fe20363fef83997ULL, 0x3fe1f93bbd8a43b0ULL,
    0x3fe1ef1eea1ccfe1ULL, 0x3fe1e50d716fdd44ULL, 0x3fe1db07406e8d20ULL, 0x3fe1d10c442eaa60ULL, 0x3fe1c71c69f03295ULL,
    0x3fe1bd379f1ce08fULL, 0x3fe1b35dd147b876ULL, 0x3fe1a98eee2c9568ULL, 0x3fe19fcae3afb892ULL, 0x3fe196119fdd59bcULL,
    0x3fe18c6310e9394aULL, 0x3fe182bf252e33a1ULL, 0x3fe17925cb2dd5fcULL, 0x3fe16f96f18ff492ULL, 0x3fe1661287224223ULL,
    0x3fe15c987ad7e8d6ULL, 0x3fe15328bbc92465ULL, 0x3fe149c33932dd99ULL, 0x3fe14067e2764706ULL, 0x3fe13716a7187b12ULL,
    0x3fe12dcf76c21b30ULL, 0x3fe12492413ef057ULL, 0x3fe11b5ef67d8cadULL, 0x3fe11235868eee61ULL, 0x3fe10915e1a623adULL,
    0x3fe0fffff817f004ULL, 0x3fe0f6f3ba5a725aULL, 0x3fe0edf11904cc95ULL, 0x3fe0e4f804cecc09ULL, 0x3fe0dc086e909319ULL,
    0x3fe0d322474243dfULL, 0x3fe0ca457ffbabe3ULL, 0x3fe0c17209f3f0e6ULL, 0x3fe0b8a7d6813e9fULL, 0x3fe0afe6d7187590ULL,
    0x3fe0a72efd4cdaceULL, 0x3fe09e803acfc8bfULL, 0x3fe095da817060dfULL, 0x3fe08d3dc31b3e6bULL, 0x3fe084a9f1da2a00ULL,
    0x3fe07c1effd3ce2eULL, 0x3fe0739cdf4b6ce7ULL, 0x3fe06b2382a095e3ULL, 0x3fe062b2dc4eddddULL, 0x3fe05a4adeed96b5ULL,
    0x3fe051eb7d2f8869ULL, 0x3fe04994a9e2aaf3ULL, 0x3fe0414657efe0f0ULL, 0x3fe039007a5ab323ULL, 0x3fe030c304410cc9ULL,
    0x3fe0288de8daf8b5ULL, 0x3fe020611b7a5f42ULL, 0x3fe0183c8f8ac4f9ULL, 0x3fe0102038910a18ULL, 0x3fe0080c0a2b2ac3ULL,
    0x3fdffffff0200008ULL,
};
struct Failed {};
struct Run {
    ClawLightPaletteContext &c;
    ClawLightPaletteDependency dependency;
    void *user;
    uint32_t steps = 0;
    static int32_t si(uint32_t v) {
        int32_t x;
        std::memcpy(&x, &v, 4);
        return x;
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failed{};
        }
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    uint8_t *bytes(uint32_t t, uint32_t n) {
        uint64_t count = (uint64_t(n) + (t & 3) + 3) / 4;
        if (count > 0xffffffff) {
            c.fault = 2;
            throw Failed{};
        }
        return reinterpret_cast<uint8_t *>(span(t & ~3u, uint32_t(count))) + (t & 3);
    }
    uint32_t byte(uint32_t t) {
        return *bytes(t, 1);
    }
    void byte(uint32_t t, uint32_t v) {
        *bytes(t, 1) = uint8_t(v);
    }
    void next() {
        if (++steps > (c.maximumSteps ? c.maximumSteps : 1000000)) {
            c.fault = 2;
            throw Failed{};
        }
    }
    uint64_t external(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}, const char *name = nullptr) {
        ClawLightPaletteCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        q.name = name;
        std::copy(a.begin(), a.end(), q.arguments);
        return external(q);
    }
    uint64_t external(ClawLightPaletteCall q) {
        uint64_t value = 0;
        if (dependency)
            value = dependency(&c, &q, user);
        else if (c.scene.call && q.argumentCount <= 4 && !q.localMask) {
            ClawSceneActorCall e{};
            e.function = q.function;
            e.receiver = q.receiver;
            e.argumentCount = q.argumentCount;
            std::copy_n(q.arguments, q.argumentCount, e.arguments);
            value = c.scene.call(c.scene.context, e);
        } else {
            c.fault = 1;
            throw Failed{};
        }
        if (c.fault)
            throw Failed{};
        return value;
    }
    uint32_t allocate(uint32_t n) {
        return uint32_t(external(0x4f63ec, 0, {n}));
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
    }
    static uint32_t call(void *p, ClawSceneActorCall e) {
        return uint32_t(static_cast<Run *>(p)->invoke(e.function, e.receiver, e.arguments, e.argumentCount));
    }
    ClawSceneActorHost host() {
        ClawSceneActorHost h{};
        h.context = this;
        h.lookup = lookup;
        h.call = call;
        return h;
    }
    static uint32_t coreCall(ClawPlayerFadeContext *c, const ClawPlayerFadeCall *e, void *p) {
        auto &r = *static_cast<Run *>(p);
        uint32_t value = uint32_t(r.invoke(e->function, e->receiver, e->arguments, e->argumentCount));
        if (r.c.fault)
            c->fault = r.c.fault;
        return value;
    }
    uint32_t core(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        if (!c.composeCore) {
            ClawLightPaletteCall q{};
            q.function = f;
            q.receiver = t;
            q.argumentCount = n;
            std::copy_n(a, n, q.arguments);
            return uint32_t(external(q));
        }
        ClawPlayerFadeContext fade{};
        fade.scene = host();
        ClawPlayerFadeBlendContext blend{};
        blend.fade = &fade;
        uint32_t value = 0;
        if (!claw_player_fade_blend_entry(f, t, a, n, &blend, coreCall, this, &value) || fade.fault) {
            c.fault = fade.fault ? fade.fault : 1;
            throw Failed{};
        }
        return value;
    }
    uint32_t core(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        uint32_t args[6]{};
        std::copy(a.begin(), a.end(), args);
        return core(f, t, args, uint32_t(a.size()));
    }
    uint32_t table(uint32_t owner, uint32_t size) {
        uint32_t p = allocate(12);
        if (!p)
            return 0;
        core(0x4c76d0, p);
        if (!core(0x4c76f0, p, {size}))
            return 0;
        uint32_t index = get(owner + 12);
        core(0x4dee30, owner + 4, {index + 1, 0xffffffff});
        put(get(owner + 8) + index * 4, p);
        return p;
    }
    uint32_t local(uint32_t f, std::initializer_list<uint32_t> a = {}) {
        if (!c.temporaryFileToken) {
            c.fault = 1;
            throw Failed{};
        }
        ClawLightPaletteCall q{};
        q.function = f;
        q.receiver = 0;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        q.localMask = 1;
        q.bufferCount = 1;
        q.buffers[0] = span(c.temporaryFileToken, 10);
        q.bufferBytes[0] = 40;
        return uint32_t(external(q));
    }
    uint32_t read(uint32_t p, uint32_t file) {
        external(get(get(file) + 60), file, {p + 4, 4});
        uint32_t size = get(p + 4);
        if (!core(0x4c76f0, p, {size}))
            return 0;
        external(get(get(file) + 60), file, {get(p + 8), get(p + 4)});
        put(p, 1);
        return 1;
    }
    uint32_t decode(uint32_t p, uint32_t data, uint32_t size) {
        local(0x4ff5f9, {1024});
        local(0x4ff645, {data, size, 0});
        uint32_t file = c.temporaryFileToken;
        auto load = [&](uint32_t dst, uint32_t n) {
            local(get(get(file) + 60), {dst, n});
        };
        load(p + 4, 4);
        uint32_t result = 0;
        if (core(0x4c76f0, p, {get(p + 4)})) {
            load(get(p + 8), get(p + 4));
            put(p, 1);
            result = 1;
        }
        put(p, result);
        local(0x4ff682);
        return result;
    }
    uint32_t load(uint32_t owner, uint32_t data, uint32_t size) {
        uint32_t p = allocate(12);
        if (p)
            core(0x4c76d0, p);
        uint32_t index = get(owner + 12);
        core(0x4dee30, owner + 4, {index + 1, 0xffffffff});
        put(get(owner + 8) + index * 4, p);
        if (!decode(p, data, size)) {
            core(0x4c7510, owner, {p});
            return 0;
        }
        return p;
    }
    static double add(double a, double b) {
        volatile double v = a + b;
        return v;
    }
    static double sub(double a, double b) {
        volatile double v = a - b;
        return v;
    }
    static double mul(double a, double b) {
        volatile double v = a * b;
        return v;
    }
    static double div(double a, double b) {
        volatile double v = a / b;
        return v;
    }
    static uint32_t low(double v) {
        uint64_t bits;
        std::memcpy(&bits, &v, 8);
        int e = int((bits >> 52) & 2047) - 1023;
        if (e < 0 || e >= 63)
            return 0;
        uint64_t value = (bits & 0xfffffffffffffULL) | 0x10000000000000ULL;
        value = e >= 52 ? value << (e - 52) : value >> (52 - e);
        return bits >> 63 ? 0u - uint32_t(value) : uint32_t(value);
    }
    double power(double base, double exponent, uint32_t weighted) {
        if (exponent == 1) {
            double v;
            std::memcpy(&v, powOne + weighted, 8);
            return v;
        }
        uint64_t a, b;
        std::memcpy(&a, &base, 8);
        std::memcpy(&b, &exponent, 8);
        uint64_t v = external(0x4f1b30, 0, {uint32_t(a), uint32_t(a >> 32), uint32_t(b), uint32_t(b >> 32)});
        double result;
        std::memcpy(&result, &v, 8);
        return result;
    }
    uint32_t light(uint32_t owner, const uint32_t *a) {
        uint32_t palette = a[0], width = a[1], gain = a[2], exponent = a[3], lift = a[4] & 255,
                 p = table(owner, width << 8);
        if (!p)
            return 0;
        uint32_t destination = get(p + 8);
        float fw = float(si(width)), fg = float(si(gain - 100));
        for (uint32_t i = 0; i < 256; ++i) {
            for (uint32_t j = 0; si(j) < si(width); ++j) {
                next();
                uint32_t c0 = byte(palette + i * 4), c1 = byte(palette + i * 4 + 1), c2 = byte(palette + i * 4 + 2);
                const uint32_t weighted =
                    low(add(add(mul(double(c0), double(.5859375f)), mul(double(c1), double(.296875f))),
                            mul(double(c2), double(.109375f)))) &
                    255;
                const double base = div(1, sub(mul(double(weighted), double(.003921568859368563f)), -1));
                const double result = power(base, double(si(exponent)), weighted);
                const float factor = float(
                    sub(mul(div(double(si(j)), double(fw)), mul(mul(result, double(fg)), double(.009999999776482582f))),
                        -1));
                auto channel = [&](uint32_t v) {
                    double n = mul(double(v + lift), double(factor));
                    return low(!(n >= 255) ? n : 255) & 255;
                };
                uint32_t r = channel(byte(palette + i * 4)), g = channel(c1), b = channel(c2);
                uint32_t index = core(0x4c7580, 0, {palette, r, g, b});
                byte(destination + j, index);
            }
            destination += width;
        }
        return p;
    }
    static int32_t divide(int32_t a, int32_t b) {
        if (!b || (a == int32_t(0x80000000) && b == -1))
            throw Failed{};
        return a / b;
    }
    uint32_t average(uint32_t owner, uint32_t palette, uint32_t weight0, uint32_t weight1) {
        uint32_t p = table(owner, 65536);
        if (!p)
            return 0;
        int32_t total = divide(si(weight0 + weight1), 100);
        if (!total) {
            c.fault = 2;
            throw Failed{};
        }
        uint32_t destination = get(p + 8);
        for (uint32_t i = 0; i < 256; ++i) {
            for (uint32_t j = 0; j < 256; ++j) {
                next();
                uint32_t values[3];
                for (uint32_t k = 0; k < 3; ++k) {
                    int32_t left = divide(si(byte(palette + j * 4 + k) * weight1), 100),
                            right = divide(si(byte(palette + i * 4 + k) * weight0), 100);
                    values[k] = uint32_t(divide(si(uint32_t(left) + uint32_t(right)), total)) & 255;
                }
                byte(destination + j, core(0x4c7580, 0, {palette, values[0], values[1], values[2]}));
            }
            destination += 256;
        }
        return p;
    }
    //Whole4f1e20 control flow specialized to the source rank-table byte domain.
    //Keep pivot/selection swaps and strict comparisons: equal-color tie order
    //differs fromstd::sort. Other sort descriptors remain exact CRT services.
    void byteSort(uint32_t start, uint32_t count) {
        if (count < 2)
            return;
        uint32_t low = start, high = start + count - 1;
        struct Frame {
            uint32_t low, high;
        } stack[30];
        uint32_t depth = 0;
        auto swap = [&](uint32_t a, uint32_t b) {
            if (a != b) {
                uint32_t x = byte(a), y = byte(b);
                byte(a, y);
                byte(b, x);
            }
        };
        for (;;) {
            next();
            uint32_t n = high - low + 1;
            if (n > 8) {
                swap(low + n / 2, low);
                uint32_t left = low, right = high + 1;
                for (;;) {
                    do {
                        ++left;
                    } while (left <= high && si(compare(left, low)) <= 0);
                    do {
                        --right;
                    } while (right > low && si(compare(right, low)) >= 0);
                    if (left > right)
                        break;
                    swap(left, right);
                }
                swap(low, right);
                if (si(right - low - 1) < si(high - left)) {
                    if (left < high) {
                        if (depth >= 30) {
                            c.fault = 2;
                            throw Failed{};
                        }
                        stack[depth++] = {left, high};
                    }
                    if (low + 1 < right) {
                        high = right - 1;
                        continue;
                    }
                } else {
                    if (low + 1 < right) {
                        if (depth >= 30) {
                            c.fault = 2;
                            throw Failed{};
                        }
                        stack[depth++] = {low, right - 1};
                    }
                    low = left;
                    if (left < high)
                        continue;
                }
            } else {
                for (uint32_t end = high; low < end; --end) {
                    uint32_t best = low;
                    for (uint32_t p = low + 1; p <= end; ++p)
                        if (si(compare(p, best)) > 0)
                            best = p;
                    swap(best, end);
                }
            }
            if (!depth)
                return;
            auto frame = stack[--depth];
            low = frame.low;
            high = frame.high;
        }
    }
    uint32_t rank(uint32_t owner, uint32_t palette) {
        uint32_t p = table(owner, 512);
        if (!p)
            return 0;
        uint32_t dst = get(p + 8);
        put(0x5430c0, palette);
        for (uint32_t i = 0; i < 256; ++i)
            byte(dst + i, i);
        byteSort(dst, 256);
        for (uint32_t i = 0; i < 256; ++i)
            for (uint32_t j = 0; j < 256; ++j) {
                next();
                if (byte(dst + j) == i) {
                    byte(dst + 256 + i, j);
                    break;
                }
            }
        return p;
    }
    uint32_t compare(uint32_t x, uint32_t y) {
        uint32_t palette = get(0x5430c0);
        auto luminance = [&](uint32_t t) {
            uint32_t color = byte(t);
            return low(add(add(mul(double(byte(palette + color * 4 + 2)), double(.109375f)),
                               mul(double(byte(palette + color * 4 + 1)), double(.296875f))),
                           mul(double(byte(palette + color * 4)), double(.5859375f)))) &
                   255;
        };
        uint32_t a = luminance(x), b = luminance(y);
        return a < b ? 0xffffffff : a > b ? 1 : 0;
    }
    void install(uint32_t p, uint32_t mode) {
        switch (mode) {
        case 2:
            put(0x5430b0, p);
            break;
        case 4:
            put(0x5430b4, p);
            break;
        case 8:
            put(0x5430b8, p);
            break;
        case 50:
            put(0x5430bc, p);
            break;
        default:
            break;
        }
    }
    uint32_t startup(uint32_t owner) {
        uint32_t app = get(owner + 4);
        if (get(app + 120) != 8)
            return 1;
        uint32_t manager = get(app + 88);
        if (!manager)
            return 0;
        uint32_t palette = owner + 864;
        put(owner + 1896, 0);
        put(owner + 1900, 0);
        put(owner + 1904, 0);
        for (uint32_t i = 0; i < 2; ++i) {
            uint32_t resource = uint32_t(external(0x4b7dc0, get(owner + 28), {i ? 0x52a088u : 0x52a09cu, 0x434c54},
                                                  i ? "PALETTES_AVERAGE" : "PALETTES_LIGHT"));
            if (resource) {
                uint32_t data = uint32_t(external(0x4b61c0, resource));
                if (data)
                    put(owner + 1896 + i * 4, load(manager, data, get(resource + 20)));
                external(0x4b6230, resource);
            }
            if (!get(owner + 1896 + i * 4)) {
                uint32_t value;
                if (i)
                    value = average(manager, palette, 100, 100);
                else {
                    uint32_t args[] = {palette, 256, 400, 1, 16};
                    value = light(manager, args);
                }
                put(owner + 1896 + i * 4, value);
                if (!value)
                    return 0;
            }
        }
        uint32_t value = rank(manager, palette);
        put(owner + 1904, value);
        if (!value)
            return 0;
        if (get(owner + 1900))
            install(get(owner + 1900), 2);
        if (get(owner + 1900))
            install(get(owner + 1900), 4);
        if (get(owner + 1904))
            install(get(owner + 1904), 50);
        return 1;
    }
    uint64_t invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        switch (f) {
        case 0x46e160:
            return startup(t);
        case 0x4c61d0:
            put(t + 4, 0x5136e8);
            put(t + 8, 0);
            put(t + 20, 0);
            put(t + 16, 0);
            put(t + 12, 0);
            put(t, 0);
            return t;
        case 0x4c6260:
            put(t, 1);
            return 1;
        case 0x4c7360:
            return load(t, a[0], a[1]);
        case 0x4c7730:
            return read(t, a[0]);
        case 0x4c7850:
            return decode(t, a[0], a[1]);
        case 0x4c68e0:
            return light(t, a);
        case 0x4c6d90:
            return average(t, a[0], a[1], a[2]);
        case 0x4c6fa0:
            return rank(t, a[0]);
        case 0x4c70b0:
            return compare(a[0], a[1]);
        case 0x4c60a0:
            install(a[0], a[1]);
            return 0;
        case 0x4c76d0:
        case 0x4c76f0:
        case 0x4c7580:
        case 0x4dee30:
        case 0x4c78d0:
        case 0x4c76e0:
        case 0x4c7510:
        case 0x4c6270:
        case 0x4c61f0:
            return core(f, t, a, n);
        default: {
            ClawLightPaletteCall q{};
            q.function = f;
            q.receiver = t;
            q.argumentCount = n;
            std::copy_n(a, n, q.arguments);
            return external(q);
        }
        }
    }
};
bool supported(uint32_t f, uint32_t &n) {
    n = 0;
    switch (f) {
    case 0x46e160:
    case 0x4c61d0:
    case 0x4c6260:
    case 0x4c76d0:
    case 0x4c78d0:
    case 0x4c76e0:
    case 0x4c6270:
    case 0x4c61f0:
        return true;
    case 0x4c7730:
    case 0x4c6fa0:
    case 0x4c76f0:
    case 0x4c7510:
        n = 1;
        return true;
    case 0x4c7360:
    case 0x4c7850:
    case 0x4c70b0:
    case 0x4c60a0:
    case 0x4dee30:
        n = 2;
        return true;
    case 0x4c6d90:
        n = 3;
        return true;
    case 0x4c7580:
        n = 4;
        return true;
    case 0x4c68e0:
        n = 5;
        return true;
    default:
        return false;
    }
}
} // namespace
extern "C" void claw_light_palette_defaults(ClawLightPaletteContext *c) {
    if (c) {
        c->composeCore = 1;
        c->maximumSteps = 1000000;
    }
}
extern "C" uint32_t claw_light_palette_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                             ClawLightPaletteContext *c, ClawLightPaletteDependency d, void *u,
                                             uint32_t *out) {
    uint32_t need;
    if (!supported(f, need))
        return 0;
    if (out)
        *out = 0;
    if (!c)
        return 1;
    c->fault = 0;
    if (n != need || (n && !a)) {
        c->fault = 2;
        return 1;
    }
    Run r{*c, d, u};
    uint64_t value = 0;
    try {
        value = r.invoke(f, t, a, n);
    } catch (Failed &) {
        if (!c->fault)
            c->fault = 2;
    }
    if (out)
        *out = uint32_t(value);
    return 1;
}
