#include "GameImageRuntime.h"
#include "ClawRuntime.hpp"
#include "PIDSurfaceRaster.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#include <vector>
namespace {
struct Run {
    ClawGameImageHost h;
    ClawGameImageGlobals *g;
    uint32_t *fault;
    uint32_t error = 0;
};
void fail(Run &r, uint32_t code = 1) {
    r.error = code;
    if (r.fault)
        *r.fault = code;
}
bool bad(Run &r) {
    return r.error || (r.fault && *r.fault);
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    auto *p = r.h.heap.lookup ? r.h.heap.lookup(r.h.heap.context, t, n) : nullptr;
    if (!p)
        fail(r);
    return p;
}
uint32_t word(Run &r, uint32_t t) {
    auto *p = span(r, t, 1);
    return p ? *p : 0;
}
uint32_t service(Run &r, uint32_t f, uint32_t recv, std::initializer_list<uint32_t> args, uint32_t *dst = nullptr,
                 uint32_t *src = nullptr) {
    if (bad(r))
        return 0;
    if (!r.h.service) {
        fail(r);
        return 0;
    }
    ClawGameImageCall c{};
    c.function = f;
    c.receiver = recv;
    c.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), c.arguments);
    c.destination = dst;
    c.source = src;
    return r.h.service(r.h.serviceContext, c);
}
void draw(Run &r, uint32_t image, uint32_t actor, uint32_t target) {
    auto *a = span(r, actor, 128);
    if (!a)
        return;
    uint32_t flags = a[16];
    if (flags & 1) {
        a[14] = 0xffffffff;
        return;
    }
    if (flags & 8) {
        if (r.g->animationDelta < a[17])
            a[17] -= r.g->animationDelta;
        else {
            a[17] = a[18];
            a[16] = flags ^ 0x10000000;
        }
        flags = a[16];
        if (!(flags & 0x10000000)) {
            a[14] = 0xffffffff;
            return;
        }
    }
    auto *im = span(r, image, 13);
    auto *t = span(r, target, 12);
    if (!im || !t)
        return;
    ClawSpriteGeometry geometry{im[4], im[5], im[6], im[7], im[8], im[9], im[12] != 0, im[11], im[12], im[10]};
    ClawSpriteDrawActor temporary{};
    temporary.flags = a[2];
    temporary.x = a[19];
    temporary.y = a[20];
    temporary.displacementX = a[4];
    temporary.displacementY = a[5];
    temporary.renderFlags = flags & ~8u;
    temporary.blinkRemaining = a[17];
    temporary.blinkInterval = a[18];
    std::memcpy(&temporary.clip, a + 21, 16);
    ClawSpriteDrawContext context{};
    context.width = t[4];
    context.height = t[5];
    context.surfaceToken = t[11];
    context.animationDelta = r.g->animationDelta;
    context.directDrawFlip = r.g->directDrawFX[1];
    if (temporary.flags & 0x40000) {
        uint32_t holder = a[15];
        uint32_t plane = word(r, holder + 0x5c);
        auto *p = span(r, plane, 22);
        if (!p)
            return;
        context.projection = {p[2], p[12], p[13], p[16], p[17], p[18], p[19], p[20], p[21]};
        uint32_t world = word(r, im[3] + 0x24);
        auto *clip = span(r, world + 0x10, 4);
        if (!clip)
            return;
        uint32_t source[4];
        std::copy(clip, clip + 4, source);
        uint32_t destination[4]{};
        service(r, 0x546d58, 0, {0, 0}, destination, source);
        if (bad(r))
            return;
        std::memcpy(&context.worldClip, destination, 16);
    }
    ClawSpriteDrawCommand command{};
    claw_sprite_prepare_draw(&geometry, &temporary, &context, &command);
    if (!command.kind) {
        a[14] = 0xffffffff;
        return;
    }
    // Original resolves surface/kind at the blit boundary, after CopyRect.
    const uint32_t receiver = word(r, target + 0x2c);
    if (bad(r))
        return;
    if (command.kind == 1) {
        service(r, 0x4b9d80, receiver,
                {command.destination.left, command.destination.top, word(r, image + 0x2c), 0, word(r, image + 0x28)},
                nullptr, reinterpret_cast<uint32_t *>(&command.source));
    } else if (command.kind == 2) {
        r.g->directDrawFX[1] = context.directDrawFlip;
        service(r, 0x4b9ce0, receiver, {0, word(r, image + 0x2c), 0, 0x8800, 0x543108},
                reinterpret_cast<uint32_t *>(&command.destination), reinterpret_cast<uint32_t *>(&command.source));
    } else {
        service(r, 0x4bffa0, word(r, image + 0x30), {0, receiver, 0, command.flipX, command.flipY},
                reinterpret_cast<uint32_t *>(&command.destination), reinterpret_cast<uint32_t *>(&command.source));
    }
    if (bad(r))
        return;
    // Blit failure is ignored; actor result stores follow the original callback.
    const uint32_t x = command.kind == 1 ? temporary.drawX : command.destination.left;
    const uint32_t y = command.kind == 1 ? temporary.drawY : command.destination.top;
    a[6] = a[8] = x;
    a[7] = a[9] = y;
    a[12] = temporary.drawWidth;
    a[13] = temporary.drawHeight;
    a[14] = 0;
    a[10] = command.kind == 1 ? temporary.drawn.right : command.destination.right - (command.kind == 2);
    a[11] = command.kind == 1 ? temporary.drawn.bottom : command.destination.bottom - (command.kind == 2);
}
uint32_t entry(Run &, uint32_t, uint32_t, const uint32_t *);
uint32_t vt(Run &r, uint32_t token, uint32_t offset) {
    uint32_t v = word(r, token);
    if (bad(r))
        return 0;
    if (v == 0x513690) {
        if (offset == 0)
            return 0x4bc5f0;
        if (offset == 0x20)
            return 0x4b9380;
        if (offset == 0x24)
            return 0x4bf9c0;
    }
    if (v == 0x513a70) {
        if (offset == 4)
            return 0x4ce8e0;
        if (offset == 0x30)
            return 0x4d22f0;
    }
    return word(r, v + offset);
}
uint32_t invoke(Run &r, uint32_t f, uint32_t token, std::initializer_list<uint32_t> args) {
    uint32_t values[8]{};
    std::copy(args.begin(), args.end(), values);
    switch (f) {
    case 0x4d2890:
    case 0x4b9380:
    case 0x4b9180:
    case 0x4b9730:
    case 0x4bb0e0:
    case 0x4b9990:
    case 0x4bc490:
    case 0x4bc520:
    case 0x4bf9c0:
    case 0x4bf310:
    case 0x4bfbf0:
    case 0x4bfc50:
    case 0x4c6130:
    case 0x4d25e0:
    case 0x4d22f0:
    case 0x4ce3d0:
    case 0x4d2410:
        return entry(r, f, token, values);
    default:
        return service(r, f, token, args);
    }
}
uint32_t allocation(Run &r, uint32_t size) {
    if (!r.h.heap.allocate) {
        fail(r);
        return 0;
    }
    uint32_t token = r.h.heap.allocate(r.h.heap.context, size);
    if (!token)
        fail(r, 2);
    return token;
}
uint32_t describeSurface(Run &r, uint32_t receiver, uint32_t manager) {
    auto *s = span(r, receiver, 47);
    if (!s)
        return 0;
    uint32_t display = word(r, manager);
    if (!display)
        return 0;
    uint32_t f = word(r, word(r, display) + 0x18);
    if (bad(r))
        return 0;
    uint32_t hr = service(r, f, 0, {display, receiver + 0xc, receiver + 8, 0});
    if (hr) {
        service(r, 0x4bd260, 0, {0x5324dc, 0xd2, hr});
        return 0;
    }
    std::fill(s + 3, s + 30, 0);
    s[3] = 108;
    uint32_t dd = s[2];
    f = word(r, word(r, dd) + 0x58);
    if (bad(r))
        return 0;
    hr = service(r, f, 0, {dd, receiver + 0xc});
    if (hr)
        service(r, 0x4bd260, 0, {0x5324dc, 0xe1, hr});
    const uint32_t bits = s[24];
    s[46] = 0;
    s[41] = bits;
    s[43] = bits == 16 ? 2 : bits == 24 ? 3 : bits == 32 ? 4 : 1;
    s[42] = s[6] * s[43];
    s[31] = s[32] = 0;
    s[33] = s[6];
    s[44] = s[7] / s[43];
    s[34] = s[5];
    s[35] = s[5] * s[42];
    return 1;
}
uint32_t lock(Run &r, uint32_t receiver, uint32_t rect) {
    auto *s = span(r, receiver, 47);
    if (!s)
        return 0;
    uint32_t dd = s[2], f = word(r, word(r, dd) + 0x64);
    if (bad(r))
        return 0;
    uint32_t hr = service(r, f, 0, {dd, rect, receiver + 0xc, 1, 0});
    if (!hr)
        return s[12];
    if (hr == 0x887601c2) {
        uint32_t restored = service(r, vt(r, receiver, 0x1c), receiver, {});
        if (restored) {
            hr = service(r, f, 0, {dd, 0, receiver + 0xc, 1, 0});
            if (!hr)
                return s[12];
            service(r, 0x4bd260, 0, {0x5324dc, 0x1e9, hr});
        }
    } else
        service(r, 0x4bd260, 0, {0x5324dc, 0x1ef, hr});
    return 0;
}
uint32_t entry(Run &r, uint32_t f, uint32_t receiver, const uint32_t *v) {
    if (f == 0x4d2890) {
        draw(r, receiver, v[0], v[1]);
        return 0;
    }
    if (f == 0x4b9380)
        return describeSurface(r, receiver, v[0]);
    if (f == 0x4b9180) {
        auto *s = span(r, receiver, 47);
        if (!s)
            return 0;
        std::fill(s + 3, s + 30, 0);
        s[29] = v[4];
        s[5] = v[2];
        s[6] = v[1];
        s[3] = 108;
        s[4] = 7;
        if (v[3] && v[3] != word(r, v[0] + 0x474)) {
            s[4] = 0x1007;
            s[21] = 32;
            s[24] = v[3];
        }
        return invoke(r, vt(r, receiver, 0x20), receiver, {v[0]});
    }
    if (f == 0x4b9730)
        return lock(r, receiver, v[0]);
    if (f == 0x4bb0e0) {
        uint32_t dd = word(r, receiver + 8);
        service(r, word(r, word(r, dd) + 0x80), 0, {dd, 0});
        return 0;
    }
    if (f == 0x4b9990) {
        auto *s = span(r, receiver, 47);
        if (!s)
            return 0;
        s[46] = v[0] != 0xffffffff;
        uint32_t pair[2] = {v[0], v[0]}, dd = s[2];
        uint32_t hr = service(r, word(r, word(r, dd) + 0x74), 0, {dd, 8, 0}, nullptr, pair);
        if (hr)
            service(r, 0x4bd260, 0, {0x5324dc, 0x331, hr});
        return 0;
    }
    if (f == 0x4bc490) {
        uint32_t node = service(r, 0x4f51c5, receiver + 0x3b8, {v[0]});
        auto *at = span(r, v[0] + 4, 1);
        if (at)
            *at = node;
        return 0;
    }
    if (f == 0x4bc520) {
        uint32_t token = allocation(r, 188);
        auto *s = span(r, token, 47);
        if (!s)
            return 0;
        s[36] = 0x51079c;
        std::fill(s + 37, s + 41, 0);
        s[1] = s[2] = s[30] = s[41] = s[45] = 0;
        s[0] = 0x513690;
        uint32_t ok = invoke(r, vt(r, token, 0x24), token, {receiver, v[0], v[1], v[2], v[3], v[4]});
        if (!ok) {
            service(r, vt(r, token, 0), token, {1});
            return 0;
        }
        invoke(r, 0x4bc490, receiver, {token});
        return token;
    }
    if (f == 0x4bf9c0) {
        if (!v[3])
            return 0;
        uint32_t ok = 0;
        if (v[2] == 4)
            ok = invoke(r, 0x4bf310, receiver, {v[0], v[1], v[3], v[4] | 0x40, v[5]});
        else if (v[2] == 1 || v[2] == 2)
            ok = service(r, v[2] == 1 ? 0x4bdad0 : 0x4be810, receiver, {v[0], v[1], v[3], v[4] | 0x40});
        else
            return 0;
        if (!ok)
            return 0;
        if (v[2] != 4 && v[5] != 0xffffffff)
            invoke(r, 0x4b9990, receiver, {v[5]});
        return 1;
    }
    if (f == 0x4bf310) {
        if (v[2] < 32 || v[2] > 0x4000000) {
            fail(r, 2);
            return 0;
        }
        auto *pid = span(r, v[1], (v[2] + 3) / 4);
        auto *manager = span(r, v[0], 0x87c / 4);
        if (!pid || !manager)
            return 0;
        uint32_t flags = pid[1], width = pid[2], height = pid[3];
        if (width & 3)
            return 0;
        uint32_t load = v[3];
        if (flags & 4)
            load = (load & ~0x4000u) | 0x800;
        else if (flags & 2)
            load &= ~0x800u;
        if (manager[0x474 / 4] != 8) {
            fail(r, 2);
            return 0;
        }
        if (flags & 0x80) {
            if (v[2] < 0x301)
                return 0;
            auto *palette = reinterpret_cast<uint8_t *>(pid) + v[2] - 768;
            for (uint32_t i = 0; i < 256; ++i)
                r.g->embeddedPalette[i] =
                    palette[i * 3] | uint32_t(palette[i * 3 + 1]) << 8 | uint32_t(palette[i * 3 + 2]) << 16;
        }
        if (!invoke(r, 0x4b9180, receiver, {v[0], width, height, 0, load}))
            return 0;
        auto *s = span(r, receiver, 47);
        if (!s)
            return 0;
        if (s[6] != width || s[5] != height) {
            fail(r, 2);
            return 0;
        }
        uint32_t pixels = lock(r, receiver, 0);
        if (!pixels)
            return 0;
        uint32_t stride = s[7];
        uint64_t capacity = uint64_t(stride) * height;
        if (capacity > 0x4000000) {
            fail(r, 2);
            return 0;
        }
        auto *output = span(r, pixels, uint32_t((capacity + 3) / 4));
        if (!output)
            return 0;
        std::vector<uint8_t> coverage(size_t(capacity), 0);
        std::vector<uint8_t> encoded(v[2]);
        std::memcpy(encoded.data(), pid, v[2]);
        uint32_t cachedHeader[4] = {10, flags, width, height};
        std::memcpy(encoded.data(), cachedHeader, 16);
        ClawPIDSurfaceRasterInfo info{};
        if (!claw_pid_decode_surface_raster8(encoded.data(), v[2], v[4] != 0xffffffff,
                                             reinterpret_cast<uint8_t *>(output), coverage.data(), size_t(capacity),
                                             stride, &info)) {
            fail(r, 2);
            return 0;
        }
        invoke(r, 0x4bb0e0, receiver, {});
        if (flags & 1)
            invoke(r, 0x4b9990, receiver, {v[4]});
        return 1;
    }
    if (f == 0x4bfbf0) {
        auto *c = span(r, receiver, 10);
        if (!c)
            return 0;
        c[3] = c[4] = c[7] = c[0] = c[8] = 0;
        c[5] = 1;
        c[6] = 0x80;
        c[9] = (c[9] & 0xffffff00) | 1;
        return receiver;
    }
    if (f == 0x4bfc50) {
        auto *c = span(r, receiver, 10);
        if (!c)
            return 0;
        c[4] = v[1] - 32;
        uint32_t bits = v[2] & 255;
        if (bits != 8 && bits != 16)
            return 0;
        if (v[1] < 32 || v[1] > 0x4000000) {
            fail(r, 2);
            return 0;
        }
        auto *pid = span(r, v[0], (v[1] + 3) / 4);
        if (!pid)
            return 0;
        if (bits == 16 && (pid[1] & 0x80)) {
            fail(r, 2);
            return 0;
        }
        c[9] = (c[9] & 0xffffff00) | 1;
        c[1] = pid[2];
        c[2] = pid[3];
        if (c[3]) {
            if (!r.h.heap.free) {
                fail(r);
                return 0;
            }
            r.h.heap.free(r.h.heap.context, c[3]);
        }
        if (c[4] > 0x4000000) {
            fail(r, 2);
            return 0;
        }
        c[3] = allocation(r, c[4]);
        auto *destination = span(r, c[3], (c[4] + 3) / 4);
        if (!destination)
            return 0;
        std::memcpy(destination, reinterpret_cast<uint8_t *>(pid) + 32, c[4]);
        return 1;
    }
    if (f == 0x4c6130) {
        auto *c = span(r, receiver, 10);
        if (!c)
            return 0;
        c[5] = v[0];
        uint32_t effect = v[1];
        if (!effect) {
            switch (v[0]) {
            case 2:
                effect = r.g->compressedEffect[0];
                break;
            case 4:
                effect = r.g->compressedEffect[1];
                break;
            case 8:
                effect = r.g->compressedEffect[2];
                break;
            case 50:
                effect = r.g->compressedEffect[3];
                break;
            default:
                return 0;
            }
        }
        c[7] = effect;
        return 0;
    }
    if (f == 0x4d25e0) {
        auto *image = span(r, receiver, 13);
        if (!image)
            return 0;
        uint32_t token = allocation(r, 40);
        invoke(r, 0x4bfbf0, token, {});
        image[12] = token;
        uint32_t container = word(r, image[3] + 4), target = word(r, container + 0x10),
                 bits = word(r, target + 0x18) & 255;
        if (bad(r))
            return 0;
        if (!invoke(r, 0x4bfc50, token, {v[0], v[1], bits}))
            return 0;
        auto *c = span(r, token, 10);
        auto *pid = span(r, v[0], 6);
        if (!c || !pid)
            return 0;
        ClawSpriteGeometry geom{};
        claw_sprite_set_geometry(&geom, c[1], c[2], pid[4], pid[5]);
        image[4] = geom.width;
        image[5] = geom.height;
        image[6] = geom.halfWidth;
        image[7] = geom.halfHeight;
        image[10] = 0x11;
        image[8] = geom.offsetX;
        image[9] = geom.offsetY;
        return 1;
    }
    if (f == 0x4d22f0) {
        auto *image = span(r, receiver, 13);
        if (!image)
            return 0;
        uint32_t token =
            service(r, 0x4bc740, word(r, image[3] + 0x1c),
                    {v[0], r.g->surfaceLoadFlags ? 0x800u : 0u, v[1] ? r.g->surfaceColorKey : 0xffffffffu});
        image[11] = token;
        if (!token)
            return 0;
        auto *s = span(r, token, 47);
        if (!s)
            return 0;
        ClawSpriteGeometry geom{};
        claw_sprite_set_geometry(&geom, s[6], s[5], 0, 0);
        image[4] = geom.width;
        image[5] = geom.height;
        image[6] = geom.halfWidth;
        image[7] = geom.halfHeight;
        image[10] = s[46] ? 0x11 : 0x10;
        image[8] = image[9] = 0;
        return 1;
    }
    if (f == 0x4ce3d0) {
        auto *manager = span(r, receiver, 27);
        if (!manager)
            return 0;
        const int32_t id = int32_t(v[1]);
        if (id < 0) {
            fail(r, 2);
            return 0;
        }
        if (id < int32_t(manager[6]) && word(r, manager[5] + v[1] * 4))
            return 0;
        uint32_t token = allocation(r, 52);
        auto *im = span(r, token, 13);
        if (!im)
            return 0;
        im[1] = v[1];
        im[2] = 0;
        im[3] = manager[3];
        im[0] = 0x513a70;
        im[4] = im[5] = im[11] = im[12] = 0;
        if (!invoke(r, vt(r, token, 0x30), token, {v[0], v[2]})) {
            service(r, vt(r, token, 4), token, {1});
            return 0;
        }
        service(r, 0x4f582f, receiver + 0x10, {v[1], token});
        if (id < int32_t(manager[25]))
            manager[25] = v[1];
        if (int32_t(manager[26]) < id)
            manager[26] = v[1];
        return token;
    }
    if (f == 0x4d2410) {
        auto *image = span(r, receiver, 13);
        if (!image)
            return 0;
        if (v[1] < 1 || v[1] > 4)
            return 0;
        auto *pid = span(r, v[0], 6);
        if (!pid)
            return 0;
        if (v[1] == 4 && (pid[1] & 0x20)) {
            if (!invoke(r, 0x4d25e0, receiver, {v[0], v[2]}))
                return 0;
            if (image[12] && (pid[1] & 0x40))
                invoke(r, 0x4c6130, image[12], {2, 0});
            return 1;
        }
        image[8] = (v[1] == 3 || v[1] == 4) ? pid[4] : 0;
        image[9] = (v[1] == 3 || v[1] == 4) ? pid[5] : 0;
        uint32_t token =
            invoke(r, 0x4bc520, word(r, image[3] + 0x1c),
                   {v[0], v[1], v[2], r.g->surfaceLoadFlags ? 0x800u : 0u, v[3] ? r.g->surfaceColorKey : 0xffffffffu});
        image[11] = token;
        if (!token)
            return 0;
        auto *s = span(r, token, 47);
        if (!s)
            return 0;
        ClawSpriteGeometry geom{};
        claw_sprite_set_geometry(&geom, s[6], s[5], image[8], image[9]);
        image[4] = geom.width;
        image[5] = geom.height;
        image[6] = geom.halfWidth;
        image[7] = geom.halfHeight;
        image[10] = s[46] ? 0x11 : 0x10;
        return 1;
    }
    fail(r, 2);
    return 0;
}
} // namespace
uint32_t claw_game_image_entry(uint32_t function, uint32_t receiver, ClawGameImageArguments args,
                               ClawGameImageGlobals *globals, ClawGameImageHost host, uint32_t *fault,
                               uint32_t *result) {
    Run r{host, globals, fault};
    if (result)
        *result = 0;
    if (!globals) {
        fail(r);
        return 0;
    }
    uint32_t required = 0;
    switch (function) {
    case 0x4d2890:
    case 0x4d22f0:
    case 0x4c6130:
    case 0x4d25e0:
        required = 2;
        break;
    case 0x4b9380:
    case 0x4b9730:
    case 0x4b9990:
    case 0x4bc490:
        required = 1;
        break;
    case 0x4b9180:
    case 0x4bc520:
    case 0x4bf310:
        required = 5;
        break;
    case 0x4bf9c0:
        required = 6;
        break;
    case 0x4bfc50:
    case 0x4ce3d0:
        required = 3;
        break;
    case 0x4d2410:
        required = 4;
        break;
    default:
        break;
    }
    if (args.count < required || args.count > 8) {
        fail(r, 2);
        return 0;
    }
    uint32_t value = entry(r, function, receiver, args.words);
    if (result)
        *result = value;
    return !bad(r);
}
