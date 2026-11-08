#include "WorldPlaneRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawWorldPlaneContext *c;
    ClawWorldPlaneDependency d;
    void *user;
};
int32_t signedWord(uint32_t v) {
    int32_t x;
    std::memcpy(&x, &v, 4);
    return x;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    if (!r.c->scene.lookup) {
        r.c->fault = 1;
        return nullptr;
    }
    auto *p = r.c->scene.lookup(r.c->scene.context, t, n);
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t read(Run &r, uint32_t t) {
    auto *p = span(r, t, 1);
    return p ? *p : 0;
}
uint32_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr) {
    if (!r.d) {
        r.c->fault = 1;
        return 0;
    }
    ClawWorldPlaneCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), e.arguments);
    e.name = name;
    return r.d(r.c, &e, r.user);
}
uint32_t allocate(Run &r, uint32_t n) {
    if (!r.c->scene.allocate) {
        r.c->fault = 1;
        return 0;
    }
    return r.c->scene.allocate(r.c->scene.context, n);
}
uint32_t floatBits(double x) {
    const float f = float(x);
    uint32_t b;
    std::memcpy(&b, &f, 4);
    return b;
}
double floating(uint32_t b) {
    float f;
    std::memcpy(&f, &b, 4);
    return double(f);
}
double multiply(double a, double b) {
    volatile double v = a * b;
    return v;
}
void clamp(Run &r, uint32_t receiver) {
    ClawSceneCameraGlobals g{};
    ClawSceneCameraHost h{};
    h.heap = r.c->scene;
    uint32_t result = 0;
    claw_scene_camera_entry(0x4d0a60, receiver, 0, 0, &g, h, &r.c->fault, &result);
}
bool byte(Run &r, uint32_t t, uint8_t &out) {
    auto *p = span(r, t & ~3u, 1);
    if (!p)
        return false;
    out = reinterpret_cast<uint8_t *>(p)[t & 3u];
    return true;
}
bool writeByte(Run &r, uint32_t t, uint8_t v) {
    auto *p = span(r, t & ~3u, 1);
    if (!p)
        return false;
    reinterpret_cast<uint8_t *>(p)[t & 3u] = v;
    return true;
}
} // namespace
uint32_t claw_world_plane_construct(uint32_t receiver, uint32_t parent, uint32_t id, uint32_t flags,
                                    ClawWorldPlaneContext *c) {
    if (!c)
        return 0;
    Run r{c, nullptr, nullptr};
    auto *p = span(r, receiver, 86);
    if (!p)
        return 0;
    p[0] = 0x50e924;
    p[1] = id;
    p[2] = flags;
    p[3] = parent;
    // Exact4f58ab embedded CArray constructor, including its untouched words.
    p[0x9c / 4] = 0x5108fc;
    p[0xa0 / 4] = p[0xac / 4] = p[0xa8 / 4] = p[0xa4 / 4] = 0;
    p[0x20 / 4] = p[0x24 / 4] = p[0xb0 / 4] = 0;
    p[0x18 / 4] = p[0x1c / 4] = 0x3f800000;
    p[0] = 0x513d40;
    p[0x50 / 4] = 0xffffffff;
    std::fill_n(p + 0xf4 / 4, 25, 0);
    p[0xf4 / 4] = 100;
    return receiver;
}
uint32_t claw_world_plane_tile_size(uint32_t receiver, uint32_t width, uint32_t height, ClawWorldPlaneContext *c) {
    if (!c)
        return 0;
    Run r{c, nullptr, nullptr};
    auto *p = span(r, receiver, 86);
    if (!p)
        return 0;
    p[0x30 / 4] = p[0x28 / 4] * width;
    p[0x3c / 4] = height;
    p[0x6c / 4] = height;
    p[0x38 / 4] = width;
    p[0x60 / 4] = p[0x64 / 4] = 0;
    p[0x68 / 4] = width;
    p[0x34 / 4] = p[0x2c / 4] * height;
    p[0x8c / 4] = 0;
    for (uint32_t i = width; signedWord(i) > 1; i = uint32_t(signedWord(i) >> 1))
        ++p[0x8c / 4];
    p[0x90 / 4] = 0;
    for (uint32_t i = width; signedWord(i) > 1; i = uint32_t(signedWord(i) >> 1))
        ++p[0x90 / 4];
    return 1;
}
uint32_t claw_world_plane_load(uint32_t receiver, uint32_t record, uint32_t base, uint32_t viewport,
                               ClawWorldPlaneContext *c, ClawWorldPlaneDependency d, void *user) {
    if (!c)
        return 0;
    Run r{c, d, user};
    auto *w = span(r, record, 40);
    if (!w || w[0] != 160)
        return 0;
    auto *p = span(r, receiver, 86);
    if (!p)
        return 0;
    uint32_t cursor = 0;
    uint32_t names = base + w[0x88 / 4];
    for (uint32_t index = 0; index < w[0x7c / 4]; ++index) {
        char name[128];
        uint32_t n = 0;
        uint8_t b;
        if (!byte(r, names + cursor, b))
            return 0;
        while (int8_t(b) < 48 && b) {
            ++cursor;
            if (cursor > 0x1000000) {
                c->fault = 2;
                return 0;
            }
            if (!byte(r, names + cursor, b))
                return 0;
        }
        while (int8_t(b) >= 48 && b) {
            if (n >= 127) {
                c->fault = 2;
                return 0;
            }
            name[n++] = char(b);
            ++cursor;
            if (!byte(r, names + cursor, b))
                return 0;
        }
        name[n] = 0;
        if (n) {
            const uint32_t parent = p[3], registry = read(r, parent + 0x10);
            if (c->fault)
                return 0;
            const uint32_t resource = call(r, 0x4f6286, registry + 16, {}, name);
            if (c->fault)
                return 0;
            call(r, 0x4f582f, receiver + 0x9c, {uint32_t(int32_t(int8_t(uint8_t(index)))), resource});
            if (c->fault)
                return 0;
        }
    }
    p[2] = w[2];
    p[0x94 / 4] = w[0x70 / 4];
    p[0x98 / 4] = w[0x74 / 4];
    p[4] = p[5] = 0;
    p[0x80 / 4] = 0xfff0bdc1;
    p[0x28 / 4] = w[0x60 / 4];
    p[0x2c / 4] = w[0x64 / 4];
    p[0x38 / 4] = w[0x58 / 4];
    p[0x3c / 4] = w[0x5c / 4];
    p[0x80 / 4] = w[0x90 / 4];
    auto *rect = span(r, viewport, 4);
    if (!rect)
        return 0;
    std::copy_n(rect, 4, p + 0x50 / 4);
    p[0x60 / 4] = p[0x64 / 4] = 0;
    p[0x68 / 4] = p[0x38 / 4];
    p[0x6c / 4] = p[0x3c / 4];
    p[0x30 / 4] = p[0x38 / 4] * p[0x28 / 4];
    p[0x34 / 4] = p[0x3c / 4] * p[0x2c / 4];
    if (!(p[2] & 16))
        claw_world_plane_tile_size(receiver, w[0x58 / 4], w[0x5c / 4], c);
    else {
        const uint32_t resource = signedWord(p[0xa4 / 4]) > 0 ? read(r, p[0xa0 / 4]) : 0;
        const uint32_t count = read(r, resource + 0x18);
        if (c->fault)
            return 0;
        for (uint32_t i = 0; signedWord(i) < signedWord(count); ++i) {
            const uint32_t minimum = read(r, resource + 0x64), maximum = read(r, resource + 0x68);
            if (c->fault)
                return 0;
            uint32_t image = 0;
            if (signedWord(i) >= signedWord(minimum) && signedWord(i) <= signedWord(maximum))
                image = read(r, read(r, resource + 0x14) + i * 4);
            if (c->fault)
                return 0;
            if (image) {
                const uint32_t width = read(r, image + 0x10), height = read(r, image + 0x14);
                if (c->fault)
                    return 0;
                claw_world_plane_tile_size(receiver, width, height, c);
                break;
            }
        }
    }
    uint32_t length = 0;
    uint8_t b;
    do {
        if (length >= 164 || !byte(r, record + 16 + length, b)) {
            if (!c->fault)
                c->fault = 2;
            return 0;
        }
        if (!writeByte(r, receiver + 0xb4 + length, b))
            return 0;
        ++length;
    } while (b);
    p[0x144 / 4] = w[0x78 / 4];
    p[2] = w[2];
    rect = span(r, viewport, 4);
    if (!rect)
        return 0;
    if (rect[0] != 0x80000000) {
        std::copy_n(rect, 4, p + 0x50 / 4);
        p[0x70 / 4] = rect[2] - rect[0] + 1;
        p[0x74 / 4] = rect[3] - rect[1] + 1;
        p[0x78 / 4] = uint32_t(signedWord(p[0x70 / 4]) / 2);
        p[0x7c / 4] = uint32_t(signedWord(p[0x74 / 4]) / 2);
        clamp(r, receiver);
        if (c->fault)
            return 0;
    }
    p[0x18 / 4] = floatBits(multiply(double(signedWord(p[0x94 / 4])), floating(0x3c23d70a)));
    p[0x1c / 4] = floatBits(multiply(double(signedWord(p[0x98 / 4])), floating(0x3c23d70a)));
    const uint32_t tileBytes = p[0x2c / 4] * p[0x28 / 4] * 4;
    const uint32_t tiles = allocate(r, tileBytes);
    if (c->fault)
        return 0;
    p[0x20 / 4] = tiles;
    uint32_t input = base + w[0x84 / 4];
    for (uint32_t i = 0; i < p[0x2c / 4] * p[0x28 / 4]; ++i) {
        if (i >= 0x4000000) {
            c->fault = 2;
            return 0;
        }
        auto *target = span(r, p[0x20 / 4] + i * 4, 1);
        const uint32_t value = read(r, input);
        if (!target || c->fault)
            return 0;
        *target = value;
        input += 4;
    }
    const uint32_t rows = allocate(r, p[0x2c / 4] * 4);
    if (c->fault)
        return 0;
    p[0x24 / 4] = rows;
    for (uint32_t i = 0; signedWord(i) < signedWord(p[0x2c / 4]); ++i) {
        if (i >= 0x4000000) {
            c->fault = 2;
            return 0;
        }
        auto *target = span(r, p[0x24 / 4] + i * 4, 1);
        if (!target)
            return 0;
        *target = i * p[0x28 / 4];
    }
    double y = double(signedWord(w[0x6c / 4])), x = double(signedWord(w[0x68 / 4]));
    if (!(p[2] & 1)) {
        x = multiply(x, floating(p[0x18 / 4]));
        y = multiply(y, floating(p[0x1c / 4]));
    }
    p[4] = floatBits(x);
    p[5] = floatBits(y);
    clamp(r, receiver);
    if (c->fault)
        return 0;
    if (w[0x8c / 4] && !call(r, 0x4d1620, receiver, {base + w[0x8c / 4], w[0x80 / 4]}))
        return 0;
    return c->fault ? 0 : 1;
}
uint32_t claw_world_plane_add(uint32_t world, uint32_t record, uint32_t base, uint32_t unused, ClawWorldPlaneContext *c,
                              ClawWorldPlaneDependency d, void *user) {
    (void)unused;
    if (!c)
        return 0;
    Run r{c, d, user};
    auto *w = span(r, world, 25);
    if (!w)
        return 0;
    const uint32_t plane = allocate(r, 0x158);
    if (c->fault)
        return 0;
    if (!plane) {
        c->fault = 2;
        return 0;
    }
    claw_world_plane_construct(plane, w[3], w[0x3c / 4], 0, c);
    if (c->fault)
        return 0;
    if (!claw_world_plane_load(plane, record, base, world + 0x10, c, d, user)) {
        if (!c->fault)
            call(r, 0x4d2210, plane, {1});
        return 0;
    }
    call(r, 0x4f582f, world + 0x34, {w[0x3c / 4], plane});
    if (c->fault)
        return 0;
    auto *p = span(r, plane, 86);
    if (!p)
        return 0;
    if (p[2] & 1) {
        w[0x5c / 4] = plane;
        w[0x60 / 4] = w[0x3c / 4] - 1;
    }
    return plane;
}
