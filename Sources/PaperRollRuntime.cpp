#include "PaperRollRuntime.h"
#include "LightPaletteRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
namespace {
struct Failed {};
struct Run;
bool owned(uint32_t f);
uint32_t route(ClawPlayerFadeContext *, const ClawPlayerFadeCall *, void *);
struct Run {
    ClawPaperRollContext &w;
    ClawPlayerFadeDependency dependency;
    void *user;
    uint32_t operations = 0;
    ClawPlayerFadeContext &c() {
        return *w.common->fade;
    }
    void tick() {
        if (++operations > (w.maximumOperations ? w.maximumOperations : 64000000)) {
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
        if (w.bytes) {
            auto *p = w.bytes(w.byteContext, t, n);
            if (!p) {
                c().fault = 1;
                throw Failed{};
            }
            return p;
        }
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
    uint8_t rb(uint32_t p) {
        return *bytes(p, 1);
    }
    void wb(uint32_t p, uint8_t v) {
        *bytes(p, 1) = v;
    }
    uint32_t invoke(uint32_t f, uint32_t p, std::initializer_list<uint32_t> a = {}) {
        uint32_t args[6]{};
        std::copy(a.begin(), a.end(), args);
        if (f == 0x4c6260) {
            ClawLightPaletteContext light{};
            light.scene = c().scene;
            uint32_t out = 0;
            if (!claw_light_palette_entry(f, p, args, uint32_t(a.size()), &light, nullptr, nullptr, &out)) {
                c().fault = light.fault ? light.fault : 3;
                throw Failed{};
            }
            return out;
        }
        return owned(f) ? entry(f, p, args, uint32_t(a.size())) : service(f, p, a);
    }
    uint32_t virt(uint32_t p, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        return invoke(rd(rd(p) + slot), p, a);
    }
    uint32_t init(uint32_t t, uint32_t d) {
        wr(t + 0x20, 0);
        if (!d)
            return 0;
        wr(t + 0x38, rd(d + 4) ? rd(d + 4) : rd(t + 0x24));
        wr(t + 0x3c, rd(d + 8) ? rd(d + 8) : rd(t + 0x28));
        if (!rd(t + 0x38) || !rd(t + 0x3c))
            return 0;
        wr(t + 0x40, rd(d + 12) ? rd(d + 12) : rd(t + 0x3c));
        invoke(0x4c6260, t + 4);
        auto s = rd(t + 0x38), q = rd(t + 0x3c), p = rd(t + 0x40);
        wr(t + 0x60, rd(s + 0x18));
        wr(t + 0x64, rd(s + 0x14));
        wr(t + 0x68, rd(q + 0x18));
        wr(t + 0x6c, rd(q + 0x14));
        wr(t + 0x70, rd(p + 0x18));
        wr(t + 0x74, rd(p + 0x14));
        if (rd(t + 0x60) != rd(t + 0x68) || rd(t + 0x64) != rd(t + 0x6c) || rd(t + 0x60) != rd(t + 0x70) ||
            rd(t + 0x64) != rd(t + 0x74) || rd(t + 0x70) != rd(t + 0x68) || rd(t + 0x74) != rd(t + 0x6c))
            return 0;
        uint32_t mode = rd(d + 20);
        if (mode < 1 || mode > 3)
            return 0;
        wr(t + 0x50, mode);
        wr(t + 0x54, rd(d + 24));
        wr(t + 0x58, rd(d + 16));
        uint32_t radius = rd(t + 0x58);
        if (mode != 3 && si(rd(t + 0x60)) < si(trunc(double(si(radius)) * 3.14159)))
            return 0;
        wr(t + 0x478, service(0x4f63ec, 0, {radius * 8}));
        for (uint32_t i = 0; si(i) < si(rd(t + 0x58) * 2); ++i) {
            tick();
            float r = float(si(rd(t + 0x58)));
            double x = (double(si(i)) - double(r)) / double(r);
            wr(rd(t + 0x478) + i * 4, trunc(std::acos(x) * double(r)));
        }
        wr(t + 0x5c, rd(d + 28));
        if (rd(rd(t + 0x38) + 0xa4) != 8)
            wr(t + 0x5c, 0);
        if (rd(t + 0x5c)) {
            if (rd(d + 32)) {
                wr(t + 0x30, 0);
                wr(t + 0x1c, rd(d + 32));
            } else {
                if (service(0x4f2190, 0, {rd(d + 36), 0})) {
                    wr(t + 0x1c, service(0x4c62e0, t + 4, {rd(rd(d + 40) + 12), 32, 32, 50, 200}));
                } else {
                    service(0x4f6449, w.stringToken, {d + 36});
                    wr(t + 0x1c, service(0x4c7180, t + 4, {rd(w.stringToken)}));
                    if (!rd(t + 0x1c))
                        wr(t + 0x5c, 0);
                }
            }
            uint32_t len = rd(t + 0x58) * 2;
            wr(t + 0x48c, service(0x4f63ec, 0, {len}));
            for (uint32_t i = 0; si(i) < si(len); ++i) {
                tick();
                wb(rd(t + 0x48c) + i,
                   uint8_t(16 - trunc(std::sin((double(si(i)) / double(si(len))) * double(float(3.140000104904175))) *
                                      -32.0)));
            }
        }
        wr(t + 0x44, service(0x4f63ec, 0, {rd(t + 0x64) * 4}));
        wr(t + 0x48, service(0x4f63ec, 0, {rd(t + 0x6c) * 4}));
        wr(t + 0x4c, service(0x4f63ec, 0, {rd(t + 0x74) * 4}));
        for (uint32_t i = 0; si(i) < si(rd(t + 0x64)); ++i) {
            tick();
            for (auto off : {0x44u, 0x48u, 0x4cu})
                wr(rd(t + off) + i * 4, rd(rd(t + off - 12) + 28) * i);
        }
        uint32_t maximum = si(rd(t + 0x60)) < si(rd(t + 0x64)) ? rd(t + 0x64) : rd(t + 0x60);
        wr(t + 0x488, service(0x4f63ec, 0, {rd(rd(t + 0x38) + 0xac) * maximum}));
        return 1;
    }
    void curve(uint32_t t, uint32_t pos, uint32_t delta) {
        uint32_t len = rd(t + 0x58) * 2;
        if (si(delta) <= 0)
            return;
        uint32_t bpp = rd(rd(t + 0x38) + 0xac), mode = rd(t + 0x50), direction = rd(t + 0x54);
        bool right = (mode == 1 && direction) || (mode == 2 && !direction),
             left = (mode == 1 && !direction) || (mode == 2 && direction);
        if (!right && !left)
            return;
        uint32_t denom = trunc(double(si(rd(t + 0x58))) * 3.14159) - rd(t + 0x58);
        double scale = double(si(len)) / double(si(denom));
        uint32_t split =
            right ? len - trunc(scale * double(si(rd(t + 0x60) - len - pos))) : trunc(scale * double(si(pos)));
        for (uint32_t y = 0; si(y) < si(rd(t + 0x64)); ++y) {
            tick();
            uint32_t dst = rd(rd(t + 0x44) + y * 4) + pos * bpp + rd(t + 0x47c),
                     paper = rd(rd(t + 0x4c) + y * 4) + pos * bpp + rd(t + 0x484),
                     source = rd(rd(t + 0x48) + y * 4) + pos * bpp + rd(t + 0x480);
            auto one = [&](uint32_t i, bool curled) {
                tick();
                if (rd(t + 0x5c)) {
                    uint8_t value =
                        curled ? rb(rd(rd(t + 0x1c) + 8) + uint32_t(rb(paper + rd(rd(t + 0x478) + i * 4))) * 64 +
                                    rb(rd(t + 0x48c) + i))
                               : rb(source + i);
                    wb(rd(t + 0x488) + i, value);
                } else if (bpp >= 1 && bpp <= 3) {
                    for (uint32_t component = 0; component < bpp; ++component) {
                        uint32_t from =
                            curled ? paper + rd(rd(t + 0x478) + i * 4) * bpp + component : source + i * bpp + component;
                        wb(rd(t + 0x488) + i * bpp + component, rb(from));
                    }
                }
            };
            for (uint32_t i = 0; si(i) < si(split); ++i)
                one(i, left);
            for (uint32_t i = split; si(i) < si(len); ++i)
                one(i, right);
            pixel(dst, rd(t + 0x488), len * bpp, false);
            if (!rd(t + 0x54))
                pixel(right ? dst + len * bpp : dst - delta * bpp, 0, delta * bpp, true);
            else
                pixel(right ? dst - delta * bpp : dst + len * bpp,
                      rd(rd(t + 0x48) + y * 4) + rd(t + 0x480) + (right ? pos - delta : pos + len) * bpp, delta * bpp,
                      false);
        }
    }
    void straight(uint32_t t, uint32_t pos, uint32_t delta) {
        if (si(delta) <= 0)
            return;
        uint32_t len = rd(t + 0x58) * 2, bpp = rd(rd(t + 0x38) + 0xac), mode = rd(t + 0x50);
        if (mode != 1 && mode != 2)
            return;
        uint32_t lead = mode == 1 ? delta : 0, tail = rd(t + 0x488) + (mode == 1 ? 0 : bpp * len),
                 srcbase = rd(t + 0x480) + (mode == 1 ? pos - delta : pos + len) * bpp,
                 targetbase = rd(t + 0x47c) + (pos - lead) * bpp, paperbase = rd(t + 0x484) + (pos - lead) * bpp;
        for (uint32_t y = 0; si(y) < si(rd(t + 0x64)); ++y) {
            tick();
            uint32_t dst = rd(rd(t + 0x44) + y * 4) + targetbase, paper = rd(rd(t + 0x4c) + y * 4) + paperbase;
            for (uint32_t i = 0; si(i) < si(len); ++i) {
                tick();
                if (rd(t + 0x5c)) {
                    auto shade = rb(rd(t + 0x48c) + i);
                    auto curve = rd(rd(t + 0x478) + i * 4);
                    wb(rd(t + 0x488) + lead + i, rb(rd(rd(t + 0x1c) + 8) + uint32_t(rb(paper + curve)) * 64 + shade));
                } else if (bpp >= 1 && bpp <= 3)
                    for (uint32_t component = 0; component < bpp; ++component)
                        wb(rd(t + 0x488) + (lead + i) * bpp + component,
                           rb(paper + rd(rd(t + 0x478) + i * 4) * bpp + component));
            }
            pixel(tail, rd(rd(t + 0x48) + y * 4) + srcbase, delta * bpp, !rd(t + 0x54));
            pixel(dst, rd(t + 0x488), (len + delta) * bpp, false);
        }
    }
    void unlock(uint32_t s) {
        uint32_t dd = rd(s + 8);
        service(rd(rd(dd) + 0x80), 0, {dd, 0});
    }
    void step(uint32_t t, uint32_t count) {
        wr(t + 0x47c, service(0x4b9730, rd(t + 0x38), {0}));
        uint32_t data = service(0x4b9730, rd(t + 0x3c), {0});
        wr(t + 0x480, data);
        if (rd(t + 0x3c) != rd(t + 0x40))
            data = service(0x4b9730, rd(t + 0x40), {0});
        wr(t + 0x484, data);
        uint32_t radius = rd(t + 0x58), threshold = trunc(double(si(radius)) * 3.14159),
                 offset = rd(t + 0x50) == 3 && rd(t + 0x54) ? uint32_t(si(rd(t + 0x60)) / 2) : 0;
        if (!rd(t + 0x54) && !count) {
            uint32_t pitch = uint32_t(std::min(si(rd(rd(t + 0x38) + 28)), si(rd(rd(t + 0x3c) + 28))));
            for (uint32_t y = 0; si(y) < si(rd(t + 0x64)); ++y) {
                tick();
                pixel(rd(rd(t + 0x44) + y * 4) + rd(t + 0x47c), rd(rd(t + 0x48) + y * 4) + rd(t + 0x480), pitch, false);
            }
        }
        auto dispatch = [&](bool curved, bool opening) {
            uint32_t mode = rd(t + 0x50), width = rd(t + 0x60);
            auto paint = [&](uint32_t p) {
                uint32_t delta = count - rd(t + 32);
                if (curved)
                    curve(t, p, delta);
                else
                    straight(t, p, delta);
            };
            if (mode == 1)
                paint(count);
            else if (mode == 2)
                paint(width - count - radius * 2);
            else if (mode == 3) {
                wr(t + 0x50, 1);
                paint(opening ? uint32_t(si(width) / 2) + count : count);
                wr(t + 0x50, 2);
                uint32_t w2 = rd(t + 0x60), half = uint32_t(si(w2) / 2);
                paint(opening ? (curved ? w2 - half : half) - count - radius * 2 : w2 - count - radius * 2);
                wr(t + 0x50, 3);
            }
        };
        if (rd(t + 0x54)) {
            dispatch(rd(t + 0x60) - threshold - rd(t + 0x58) < offset + count, true);
            if (!rd(t + 0x54))
                dispatch(!(threshold - rd(t + 0x58) < offset + count), false);
        } else
            dispatch(!(threshold - rd(t + 0x58) < offset + count), false);
        wr(t + 32, count);
        unlock(rd(t + 0x38));
        unlock(rd(t + 0x3c));
        if (rd(t + 0x3c) != rd(t + 0x40))
            unlock(rd(t + 0x40));
    }
    void descriptor(uint32_t t) {
        frozen(0x4ecb30, t);
        service(0x4f6439, t + 36);
        wr(t, 1);
        for (auto off : {4u, 8u, 12u, 28u, 32u})
            wr(t + off, 0);
        wr(t + 16, 50);
        wr(t + 20, 1);
        wr(t + 24, 1);
        service(0x4f66cc, t + 36, {0x534938});
        wr(t + 40, 0);
    }
    void diagnostic(uint32_t text) {
        frozen(0x4f65f2, w.common->temporaryStringToken, {text});
        frozen(0x4ec6b0, 0, {rd(w.common->temporaryStringToken)});
    }
    uint32_t factory(uint32_t t, uint32_t type, uint32_t desc) {
        if (type) {
            c().fault = 3;
            throw Failed{};
        }
        if (desc && rd(desc) != 1) {
            diagnostic(0x53404c);
            return 0;
        }
        uint32_t effect = service(0x4f63ec, 0, {CLAW_PAPER_ROLL_BYTES});
        if (effect)
            invoke(0x4ee880, effect);
        frozen(0x4ecb00, effect, {rd(t), rd(t + 4)});
        frozen(0x4ecb20, effect, {rd(t + 0x24)});
        bool local = !desc;
        if (local) {
            desc = w.descriptorToken;
            descriptor(desc);
        }
        uint32_t valid = init(effect, desc);
        if (local)
            service(0x4f6584, desc + 36);
        if (!valid) {
            diagnostic(0x5340a0);
            virt(effect, 0, {1});
            return 0;
        }
        uint32_t index = rd(t + 0x18);
        resize(t + 0x10, index + 1);
        wr(rd(t + 0x14) + index * 4, effect);
        return effect;
    }
    uint32_t rollerPalette(uint32_t app) {
        if (!virt(app, 12))
            return 0;
        auto manager = rd(app + 0x58);
        if (!manager)
            return 0;
        auto cached = rd(app + 0x8c);
        if (cached)
            return cached;
        auto resources = rd(app + 0x34);
        if (!resources)
            return 0;
        auto resource = service(0x4b7f00, resources, {0x525e38, 0x434c54});
        if (!resource)
            return 0;
        auto length = rd(resource + 20), data = service(0x4b61c0, resource);
        if (!data)
            return 0;
        wr(app + 0x8c, service(0x4c7360, manager, {data, length}));
        service(0x4b6230, resource);
        return rd(app + 0x8c);
    }
    uint32_t primary(uint32_t p) {
        return rd(rd(rd(rd(p + 12) + 4) + 16) + 44);
    }
    uint32_t wrapper(uint32_t p, const uint32_t *a, bool unroll) {
        auto manager = rd(p + 16);
        if (!manager)
            return 0;
        auto graphics = rd(rd(p + 12) + 28);
        if (!graphics)
            return 0;
        auto target = primary(p);
        if (!target)
            return 0;
        uint32_t width = rd(target + 24), height = rd(target + 20);
        if (!unroll) {
            wr(p + 60, service(0x4bc670, graphics, {width, height, 8, 0x800, 0xffffffff}));
            if (!rd(p + 60) || service(0x4b9c50, rd(p + 60), {target}))
                return 0;
        } else {
            service(0x4a3920, 0, {w.nameToken, 0x528e54, a[0]});
            auto file = service(0x4b7dc0, rd(p + 32), {w.nameToken, 0x504358});
            if (!file)
                return 0;
            auto data = service(0x4b61c0, file);
            if (!data)
                return 0;
            wr(p + 60, service(0x4bc520, graphics, {data, 2, rd(file + 20), 0x800, 0xffffffff}));
            if (!rd(p + 60))
                return 0;
            if (!rd(p + 44)) {
                wr(p + 44, virt(rd(rd(p + 12) + 24), 48, {file, 0, 0}));
                if (!rd(p + 44))
                    return 0;
            }
            service(0x4b6230, file);
            if (a[1])
                service(0x4bbf60, rd(rd(p + 44) + 16));
            if (a[2]) {
                service(0x4bb870, rd(rd(p + 44) + 16));
                service(0x4bb990, rd(rd(p + 44) + 16), {0, 256, 0, 0, 0, a[2]});
                service(0x4b97c0, rd(rd(rd(rd(p + 12) + 4) + 20) + 44), {0});
                service(0x4b98b0, primary(p), {0});
                service(0x4bb8c0, rd(rd(p + 44) + 16), {0});
            }
            wr(rd(rd(p + 12) + 24) + 100, rd(p + 44));
            virt(rd(p + 44), 52);
        }
        if (!rd(p + 64)) {
            auto file = service(0x4b7f00, rd(p + 8), {0x528e38, 0x504358});
            if (!file)
                return 0;
            auto data = service(0x4b61c0, file);
            if (!data)
                return 0;
            wr(p + 64, service(0x4bc520, graphics, {data, 2, rd(file + 20), 0x800, 0xffffffff}));
            service(0x4b6230, file);
            if (!rd(p + 64))
                return 0;
        }
        auto paper = rd(p + 64);
        if (rd(paper + 24) != width || rd(paper + 20) != height)
            return 0;
        auto palette = rollerPalette(rd(p + 4));
        auto d = w.descriptorToken;
        descriptor(d);
        wr(d + 4, target);
        wr(d + 8, rd(p + 60));
        wr(d + 12, rd(p + 64));
        wr(d + 16, 40);
        wr(d + 20, 3);
        wr(d + 24, unroll ? 1 : 0);
        wr(d + 28, palette ? 1 : 0);
        wr(d + 32, palette);
        auto effect = factory(manager, 0, d);
        if (!effect) {
            service(0x4f6584, d + 36);
            return 0;
        }
        frozen(0x42d420, rd(p + 4));
        uint32_t duration = unroll ? a[4] : a[0], wait = unroll ? a[3] : 0;
        if (!c().globals) {
            c().fault = 1;
            throw Failed{};
        }
        if (c().globals->bypass) {
            frozen(0x4b8960, 0, {duration});
            if (unroll) {
                if (rd(p + 60))
                    service(0x4b9c50, primary(p), {rd(p + 60)});
            } else
                service(0x4b97c0, primary(p), {0});
        } else {
            auto sound = rd(rd(p + 12) + 40);
            if (!rd(sound + 48)) {
                wr(w.lookupToken, 0);
                service(0x4f6286, sound + 16, {unroll ? (wait ? 0x52c6d8u : 0x528e30u) : 0x52c6d0u, w.lookupToken});
                if (rd(w.lookupToken) && !w.soundEnabled) {
                    c().fault = 1;
                    throw Failed{};
                }
                if (rd(w.lookupToken) && *w.soundEnabled) {
                    if (!w.soundVolume) {
                        c().fault = 1;
                        throw Failed{};
                    }
                    service(0x4b45f0, rd(rd(w.lookupToken) + 16), {*w.soundVolume, 0, 0, 0});
                }
            }
            frozen(0x4ec9c0, effect, {duration, wait, 0});
        }
        frozen(0x42d440, rd(p + 4));
        frozen(0x4ec600, manager, {effect});
        service(0x4bc4f0, graphics, {rd(p + 60)});
        wr(p + 60, 0);
        service(0x4f6584, d + 36);
        return 1;
    }
    uint32_t entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        auto need = [&](uint32_t x) {
            if (n != x) {
                c().fault = 2;
                throw Failed{};
            }
        };
        switch (f) {
        case 0x48f500:
            need(1);
            return wrapper(t, a, false);
        case 0x48f740:
            need(5);
            return wrapper(t, a, true);
        case 0x42a4f0:
            need(0);
            return rollerPalette(t);
        case 0x4ecb40:
            need(0);
            descriptor(t);
            return t;
        case 0x4ee880:
            need(0);
            frozen(0x4ec8d0, t);
            wr(t, 0x514270);
            for (auto off : {0x478u, 0x44u, 0x48u, 0x4cu, 0x488u, 0x48cu, 0x20u})
                wr(t + off, 0);
            return t;
        case 0x4ee8e0:
            need(0);
            wr(t, 0x514270);
            for (auto off : {0x478u, 0x44u, 0x48u, 0x4cu, 0x488u, 0x48cu})
                if (rd(t + off))
                    service(0x4f6428, 0, {rd(t + off)});
            frozen(0x4ec920, t);
            return 0;
        case 0x4ee8c0:
            need(1);
            invoke(0x4ee8e0, t);
            if (a[0] & 1)
                service(0x4f6428, 0, {t});
            return t;
        case 0x4ee9a0:
            need(1);
            return init(t, a[0]);
        case 0x4eecc0:
            need(1);
            step(t, a[0]);
            return 0;
        case 0x4ef010:
            need(2);
            curve(t, a[0], a[1]);
            return 0;
        case 0x4ef7d0:
            need(2);
            straight(t, a[0], a[1]);
            return 0;
        case 0x4efac0:
            need(0);
            if (rd(t + 0x50) == 1 || rd(t + 0x50) == 2)
                return rd(t + 0x60) - rd(t + 0x58) * 2;
            if (rd(t + 0x50) == 3)
                return uint32_t(si(rd(t + 0x60) - rd(t + 0x58) * 4) / 2);
            return 0;
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
    case 0x48f500:
    case 0x48f740:
    case 0x42a4f0:
    case 0x4ecb40:
    case 0x4ee880:
    case 0x4ee8e0:
    case 0x4ee8c0:
    case 0x4ee9a0:
    case 0x4eecc0:
    case 0x4ef010:
    case 0x4ef7d0:
    case 0x4efac0:
    case 0x4ec050:
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
extern "C" uint32_t claw_paper_roll_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                          ClawPaperRollContext *w, ClawPlayerFadeDependency d, void *u,
                                          uint32_t *result) {
    if (!w || !w->common || !w->common->fade || !result || (n && !a) || n > 6)
        return 0;
    if (!owned(f) && f != 0x4ec9c0 && f != 0x4ec600)
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
