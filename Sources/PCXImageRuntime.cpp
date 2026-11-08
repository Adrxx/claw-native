#include "PCXImageRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
struct Run {
    ClawPCXImageContext &c;
    ClawPCXImageDependency dep;
    void *user;
    uint32_t operations = 0;
    static int32_t si(uint32_t x) {
        int32_t y;
        std::memcpy(&y, &x, 4);
        return y;
    }
    void tick() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 100000000)) {
            c.fault = 3;
            throw Failure{};
        }
    }
    uint32_t *words(uint32_t t, uint32_t n = 1) {
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failure{};
        }
        return p;
    }
    uint32_t get(uint32_t t, uint32_t offset = 0) {
        return *words(t + offset);
    }
    uint8_t *byte(uint32_t t) {
        if (c.bytes) {
            auto *p = c.bytes(c.byteContext, t, 1);
            if (p)
                return p;
            c.fault = 1;
            throw Failure{};
        }
        return reinterpret_cast<uint8_t *>(words(t & ~3u)) + (t & 3);
    }
    uint8_t read(uint32_t t) {
        return *byte(t);
    }
    void write(uint32_t t, uint8_t x) {
        *byte(t) = x;
    }
    int32_t shortSigned(uint32_t t) {
        uint16_t x = uint16_t(read(t)) | uint16_t(read(t + 1)) << 8;
        int16_t y;
        std::memcpy(&y, &x, 2);
        return y;
    }
    uint32_t service(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawPCXImageCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        if (dep)
            return dep(&c, &q, user);
        if (c.scene.call && q.argumentCount <= 4) {
            ClawSceneActorCall e{};
            e.function = f;
            e.receiver = t;
            e.argumentCount = q.argumentCount;
            std::copy(a.begin(), a.end(), e.arguments);
            return c.scene.call(c.scene.context, e);
        }
        c.fault = 1;
        throw Failure{};
    }
    static uint32_t imageService(void *v, ClawGameImageCall e) {
        auto &r = *static_cast<Run *>(v);
        if (owned(e.function) && !e.source && !e.destination)
            return r.entry(e.function, e.receiver, e.arguments, e.argumentCount);
        ClawPCXImageCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        q.source = e.source;
        q.destination = e.destination;
        if (r.dep)
            return r.dep(&r.c, &q, r.user);
        if (!q.destination && !q.source && q.argumentCount <= 4 && r.c.scene.call) {
            ClawSceneActorCall call{};
            call.function = q.function;
            call.receiver = q.receiver;
            call.argumentCount = q.argumentCount;
            std::copy_n(q.arguments, q.argumentCount, call.arguments);
            return r.c.scene.call(r.c.scene.context, call);
        }
        r.c.fault = 1;
        throw Failure{};
    }
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        uint32_t v[8]{};
        std::copy(a.begin(), a.end(), v);
        if (owned(f))
            return entry(f, t, v, uint32_t(a.size()));
        if (c.composeImage && (f == 0x4b9730 || f == 0x4bb0e0)) {
            ClawGameImageArguments x{};
            x.count = uint32_t(a.size());
            std::copy(a.begin(), a.end(), x.words);
            ClawGameImageHost h{c.scene, this, imageService};
            uint32_t fault = 0, out = 0;
            if (!claw_game_image_entry(f, t, x, c.image, h, &fault, &out) || fault) {
                c.fault = fault ? fault : 2;
                throw Failure{};
            }
            return out;
        }
        return service(f, t, a);
    }
    void row(uint32_t &src, uint32_t dst, uint32_t width, uint32_t step) {
        uint32_t left = width;
        while (si(left) > 0) {
            tick();
            uint8_t token = read(src++), value = token;
            uint32_t count = 1;
            if ((token & 0xc0) == 0xc0) {
                count = token & 0x3f;
                value = read(src++);
            }
            for (uint32_t i = 0; i < count; ++i) {
                write(dst, value);
                dst += step;
            }
            left -= count;
        }
    }
    uint32_t surfaceDecode(uint32_t t, uint32_t src, bool rgb) {
        if (!src)
            return 0;
        uint32_t width = 0, height = 0;
        if (!rgb) {
            width = get(t, 24);
            height = get(t, 20);
        }
        uint32_t pixels = invoke(0x4b9730, t, {0});
        if (!pixels)
            return 0;
        for (uint32_t y = 0; si(y) < si(rgb ? get(t, 20) : height); ++y) {
            tick();
            if (rgb) {
                for (uint32_t p = 0; p < 3; ++p) {
                    uint32_t dest = pixels + get(t, 28) * y + 2 - p;
                    row(src, dest, get(t, 24), 3);
                }
            } else
                row(src, pixels + get(t, 28) * y, width, 1);
        }
        invoke(0x4bb0e0, t);
        return 1;
    }
    uint32_t linearDecode(const uint32_t *a, bool rgb) {
        if (!a[0] || !a[1])
            return 0;
        uint32_t src = a[1];
        for (uint32_t y = 0; si(y) < si(a[3]); ++y) {
            tick();
            for (uint32_t p = 0; p < (rgb ? 3u : 1u); ++p)
                row(src, a[0] + a[2] * y * (rgb ? 3u : 1u) + p, a[2], rgb ? 3u : 1u);
        }
        return 1;
    }
    uint32_t quantize(uint32_t t, const uint32_t *a) {
        if (!a[1])
            return 0;
        uint32_t pixels = invoke(0x4b9730, t, {0});
        if (!pixels)
            return 0;
        uint32_t source = a[0], y = a[2] == 2 ? get(t, 20) - 1 : 0;
        while (a[2] == 2 ? si(y) >= 0 : si(y) < si(get(t, 20))) {
            tick();
            uint32_t dest = pixels + y * get(t, 28);
            for (uint32_t x = 0; si(x) < si(get(t, 24)); ++x) {
                tick();
                uint8_t first = read(source), second = read(source + 1), third = read(source + 2);
                source += 3;
                auto distance = [&](uint32_t index) {
                    int32_t p = int32_t(third) - int32_t(read(a[1] + index * 4));
                    int32_t q = int32_t(second) - int32_t(read(a[1] + index * 4 + 1));
                    int32_t s = int32_t(first) - int32_t(read(a[1] + index * 4 + 2));
                    return uint32_t(p * p + q * q + s * s);
                };
                uint32_t best = 0, d = distance(0);
                for (uint32_t i = 1; i < 256; ++i) {
                    uint32_t next = distance(i);
                    if (next < d) {
                        best = i;
                        d = next;
                        if (!d)
                            break;
                    }
                }
                write(dest++, uint8_t(best));
            }
            y += a[2] == 2 ? 0xffffffffu : 1;
        }
        invoke(0x4bb0e0, t);
        return 1;
    }
    uint32_t expand(uint32_t t, const uint32_t *a) {
        if (!a[1])
            return 0;
        uint32_t pixels = invoke(0x4b9730, t, {0});
        if (!pixels)
            return 0;
        uint32_t source = a[0], y = a[2] == 2 ? get(t, 20) - 1 : 0;
        while (a[2] == 2 ? si(y) >= 0 : si(y) < si(get(t, 20))) {
            tick();
            uint32_t dest = pixels + y * get(t, 28);
            for (uint32_t x = 0; si(x) < si(get(t, 24)); ++x) {
                tick();
                uint32_t index = read(source++), pal = a[1] + index * 4;
                write(dest, read(pal + 2));
                write(dest + 1, read(pal + 1));
                write(dest + 2, read(pal));
                dest += 3;
            }
            y += a[2] == 2 ? 0xffffffffu : 1;
        }
        invoke(0x4bb0e0, t);
        return 1;
    }
    uint32_t convert(uint32_t t, const uint32_t *a) {
        uint32_t depth = get(t, 164);
        if (uint32_t(depth == 0) == a[1])
            return invoke(0x4b9b00, t, {a[0], a[3]});
        if (depth == 24) {
            if (a[1] == 8)
                return invoke(0x4ba2d0, t, {a[0], a[2], a[3]});
            if (a[1] == 16)
                return invoke(0x4ba3f0, t, {a[0], a[3]});
        } else if (depth == 16) {
            if (a[1] == 8)
                return invoke(0x4b9fa0, t, {a[0], a[2], a[3]});
            if (a[1] == 24)
                return invoke(0x4ba150, t, {a[0], a[3]});
        } else if (depth == 8) {
            if (a[1] == 16)
                return invoke(0x4ba890, t, {a[0], a[2], a[3]});
            if (a[1] == 24)
                return invoke(0x4ba580, t, {a[0], a[2], a[3]});
        }
        return 0;
    }
    uint32_t load(uint32_t t, const uint32_t *a) {
        uint32_t manager = a[0], data = a[1];
        if (!data)
            return 0;
        uint32_t width = uint32_t(shortSigned(data + 8) - shortSigned(data + 4) + 1),
                 height = uint32_t(shortSigned(data + 10) - shortSigned(data + 6) + 1);
        uint8_t planes = read(data + 65);
        uint32_t depth = planes == 1 ? 8u : planes == 3 ? 24u : 0u;
        if (!depth || get(t, 24) != width || get(t, 20) != height)
            return 0;
        uint32_t target = get(manager, 0x474);
        bool change = target != depth;
        if (change && target == 8 && !get(manager, 0x878))
            return 0;
        uint32_t palette = 0, temporary = 0;
        if (change) {
            if (depth == 8) {
                uint32_t src = data + a[2] - 768;
                for (uint32_t i = 0; i < 256; ++i) {
                    write(0x541bb0 + i * 4, read(src++));
                    write(0x541bb0 + i * 4 + 1, read(src++));
                    write(0x541bb0 + i * 4 + 2, read(src++));
                    write(0x541bb0 + i * 4 + 3, 0);
                }
                palette = 0x541bb0;
            } else if (target == 8 && get(manager, 0x878))
                palette = manager + 0x478;
            temporary = invoke(0x4f63ec, 0, {width * height * (depth == 8 ? 1u : 3u)});
            if (!temporary)
                return 0;
            uint32_t decoded = invoke(depth == 8 ? 0x4bef50 : 0x4bf070, t, {temporary, data + 128, width, height});
            if (!decoded) {
                invoke(0x4f6428, 0, {temporary});
                return 0;
            }
        } else if (!invoke(depth == 8 ? 0x4babe0 : 0x4bad30, t, {data + 128}))
            return 0;
        if (change && !invoke(0x4b9e90, t, {temporary, depth, palette, 1})) {
            invoke(0x4f6428, 0, {temporary});
            return 0;
        }
        if (temporary)
            invoke(0x4f6428, 0, {temporary});
        return 1;
    }
    static bool owned(uint32_t f) {
        switch (f) {
        case 0x4bebc0:
        case 0x4babe0:
        case 0x4bad30:
        case 0x4bef50:
        case 0x4bf070:
        case 0x4b9e90:
        case 0x4ba580:
        case 0x4ba2d0:
        case 0x4bb040:
        case 0x4bb050:
        case 0x4bb0f0:
        case 0x4b9e60:
            return true;
        default:
            return false;
        }
    }
    uint32_t entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        tick();
        uint32_t expected = f == 0x4bebc0 || f == 0x4ba580 || f == 0x4ba2d0   ? 3u
                            : f == 0x4bef50 || f == 0x4bf070 || f == 0x4b9e90 ? 4u
                            : f == 0x4babe0 || f == 0x4bad30 || f == 0x4bb0f0 ? 1u
                                                                              : 0u;
        if (n != expected) {
            c.fault = 2;
            throw Failure{};
        }
        switch (f) {
        case 0x4bebc0:
            return load(t, a);
        case 0x4babe0:
            return surfaceDecode(t, a[0], false);
        case 0x4bad30:
            return surfaceDecode(t, a[0], true);
        case 0x4bef50:
            return linearDecode(a, false);
        case 0x4bf070:
            return linearDecode(a, true);
        case 0x4b9e90:
            return convert(t, a);
        case 0x4ba580:
            return quantize(t, a);
        case 0x4ba2d0:
            return expand(t, a);
        case 0x4bb040:
            return get(t, 24);
        case 0x4bb050:
            return get(t, 20);
        case 0x4bb0f0:
            return get(t, 28) * a[0];
        case 0x4b9e60: {
            uint32_t f = get(t, 180);
            if (f && invoke(f, 0, {t}))
                return 1;
            invoke(0x4bd0a0, 0);
            return 0;
        }
        default:
            c.fault = 2;
            throw Failure{};
        }
    }
};
} // namespace
extern "C" uint32_t claw_pcx_image_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, ClawPCXImageContext *c,
                                         ClawPCXImageDependency d, void *u, uint32_t *out) {
    if (!c || !out || !Run::owned(f) || (n && !a) || n > 8 || c->fault)
        return 0;
    Run r{*c, d, u};
    try {
        *out = r.entry(f, t, a, n);
    } catch (Failure &) {
    }
    return c->fault ? 0 : 1;
}
