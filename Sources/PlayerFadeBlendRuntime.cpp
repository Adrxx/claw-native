#include "PlayerFadeBlendRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawPlayerFadeBlendContext *b;
    ClawPlayerFadeDependency d;
    void *user;
};
ClawPlayerFadeContext &context(Run &r) {
    return *r.b->fade;
}
int32_t si(uint32_t x) {
    int32_t y;
    std::memcpy(&y, &x, 4);
    return y;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    auto &c = context(r);
    auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
    if (!p)
        c.fault = 1;
    return p;
}
uint32_t rd(Run &r, uint32_t t) {
    auto *p = span(r, t, 1);
    return p ? *p : 0;
}
void wr(Run &r, uint32_t t, uint32_t v) {
    auto *p = span(r, t, 1);
    if (p)
        *p = v;
}
uint8_t *bytes(Run &r, uint32_t t, uint32_t n) {
    if (!n)
        return nullptr;
    const uint64_t count = (uint64_t(n) + (t & 3u) + 3) / 4;
    if (count > 0xffffffffu) {
        context(r).fault = 2;
        return nullptr;
    }
    auto *p = span(r, t & ~3u, uint32_t(count));
    return p ? reinterpret_cast<uint8_t *>(p) + (t & 3u) : nullptr;
}
uint32_t byte(Run &r, uint32_t t) {
    auto *p = bytes(r, t, 1);
    return p ? *p : 0;
}
void storeByte(Run &r, uint32_t t, uint32_t v) {
    auto *p = bytes(r, t, 1);
    if (p)
        *p = uint8_t(v);
}
uint32_t service(Run &r, uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
    if (context(r).fault)
        return 0;
    ClawPlayerFadeCall q{};
    q.function = f;
    q.receiver = t;
    q.argumentCount = uint32_t(a.size());
    std::copy(a.begin(), a.end(), q.arguments);
    if (r.d)
        return r.d(&context(r), &q, r.user);
    if (q.argumentCount <= 4 && context(r).scene.call) {
        ClawSceneActorCall s{};
        s.function = f;
        s.receiver = t;
        s.argumentCount = q.argumentCount;
        std::copy_n(q.arguments, q.argumentCount, s.arguments);
        return context(r).scene.call(context(r).scene.context, s);
    }
    context(r).fault = 1;
    return 0;
}
uint32_t frozen(Run &r, uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
    uint32_t result = 0, v[6]{};
    std::copy(a.begin(), a.end(), v);
    if (!claw_player_fade_entry(f, t, v, uint32_t(a.size()), &context(r), r.d, r.user, &result) && !context(r).fault)
        context(r).fault = 3;
    return result;
}
uint32_t root(double v) {
    if (!std::isfinite(v) || v < -9223372036854775808.0 || v >= 9223372036854775808.0)
        return 0;
    return uint32_t(uint64_t(int64_t(v)));
}
uint32_t integerRoot(uint32_t v) {
    return root(std::sqrt(double(si(v))));
}
void zero(Run &r, uint32_t t, uint32_t n) {
    if (si(n) <= 0)
        return;
    auto *p = bytes(r, t, n);
    if (p)
        std::memset(p, 0, n);
}
void forward(Run &r, uint32_t dst, uint32_t src, uint32_t n) {
    if (si(n) <= 0)
        return;
    auto *a = bytes(r, dst, n);
    auto *b = bytes(r, src, n);
    if (a && b)
        for (uint32_t i = 0; i < n; ++i)
            a[i] = b[i];
}
void unlock(Run &r, uint32_t surface) {
    if (!surface || context(r).fault)
        return;
    uint32_t dd = rd(r, surface + 8);
    service(r, rd(r, rd(r, dd) + 0x80), 0, {dd, 0});
}
// Exact inlined4ed800 and4ee170 band traversal, including duplicate center
// writes and source-byte reads after earlier writes when buffers alias.
void band(Run &r, uint32_t t, uint32_t row, uint32_t square, uint32_t radius, uint32_t palette, uint32_t dst,
          uint32_t src) {
    uint32_t gradient = rd(r, t + 0x2060);
    if (si(gradient) < 1)
        return;
    const uint32_t cy = rd(r, t + 0x50), cx = rd(r, t + 0x4c), dy = row - cy, dySquare = dy * dy;
    uint32_t x = cx - integerRoot(square - dySquare) + 1;
    uint32_t distance = integerRoot((x - cx) * (x - cx) + dySquare);
    const uint32_t dstPitch = rd(r, rd(r, t + 0x38) + 0x1c), srcPitch = rd(r, rd(r, t + 0x3c) + 0x1c);
    const int32_t half = si(rd(r, t + 0x2068)) / 2;
    bool mirror = false;
    uint32_t mirrorRow = 0;
    if (si(cy) >= half && si(row) <= si(cy)) {
        mirrorRow = cy * 2 - row;
        mirror = si(mirrorRow) < si(rd(r, t + 0x2068));
    } else if (si(cy) < half && si(row) >= si(cy)) {
        mirrorRow = cy * 2 - row;
        mirror = si(mirrorRow) >= 0;
    } else
        return;
    uint32_t dstLeft = dst + row * dstPitch + x, srcLeft = src + row * srcPitch + x,
             dstRight = dst + row * dstPitch + cx * 2 - x, srcRight = src + row * srcPitch + cx * 2 - x;
    const uint32_t dstMirrorOffset = (mirrorRow - row) * dstPitch, srcMirrorOffset = (mirrorRow - row) * srcPitch;
    auto pixel = [&](uint32_t d, uint32_t s, uint32_t shade, uint32_t g) {
        const uint32_t value = byte(r, s);
        if (context(r).fault)
            return;
        const uint32_t color = byte(r, palette + value * g + shade);
        if (context(r).fault)
            return;
        storeByte(r, d, color);
    };
    for (uint32_t iterations = 0; !context(r).fault && si(distance) >= si(radius - gradient);) {
        if (si(x) > si(rd(r, t + 0x4c)))
            break;
        if (++iterations > 1000000) {
            context(r).fault = 2;
            return;
        }
        const uint32_t shade = distance - radius + gradient;
        if (si(x) >= 0) {
            pixel(dstLeft, srcLeft, shade, gradient);
            if (mirror)
                pixel(dstLeft + dstMirrorOffset, srcLeft + srcMirrorOffset, shade, rd(r, t + 0x2060));
        }
        ++dstLeft;
        ++srcLeft;
        if (si(rd(r, t + 0x4c) * 2 - x) < si(rd(r, t + 0x2064))) {
            pixel(dstRight, srcRight, shade, rd(r, t + 0x2060));
            if (mirror)
                pixel(dstRight + dstMirrorOffset, srcRight + srcMirrorOffset, shade, rd(r, t + 0x2060));
        }
        --dstRight;
        --srcRight;
        ++x;
        distance = integerRoot((x - rd(r, t + 0x4c)) * (x - rd(r, t + 0x4c)) + dySquare);
        gradient = rd(r, t + 0x2060);
    }
}
void step(Run &r, uint32_t t, uint32_t stepValue) {
    if (si(rd(r, t + 0x2060)) <= 0) {
        frozen(r, 0x4ed800, t, {stepValue});
        return;
    }
    const uint32_t delta = stepValue - rd(r, t + 0x20);
    uint32_t s = rd(r, t + 0x38);
    if (s)
        wr(r, t + 0x54, service(r, 0x4b9730, s, {0}));
    s = rd(r, t + 0x3c);
    if (s)
        wr(r, t + 0x58, service(r, 0x4b9730, s, {0}));
    const uint32_t bpp = rd(r, rd(r, t + 0x38) + 0xac), palette = rd(r, t + 0x1c) ? rd(r, rd(r, t + 0x1c) + 8) : 0;
    const bool clear = rd(r, t + 0x48) != 0;
    uint32_t capture = r.b->uninitializedCapturePixelToken;
    if (clear && rd(r, t + 0x40))
        capture = service(r, 0x4b9730, rd(r, t + 0x40), {0});
    if (bpp < 1 || bpp > 4) {
        context(r).fault = 2;
        return;
    }
    const uint32_t radius = clear ? rd(r, t + 0x5c) - stepValue : stepValue, square = radius * radius,
                   cy = rd(r, t + 0x50);
    uint32_t row = uint32_t(std::max(0, si(cy - radius - delta - (clear ? 0 : rd(r, t + 0x2060)))));
    for (uint32_t iterations = 0;
         !context(r).fault &&
         si(row) < std::min(si(rd(r, t + 0x2068)), si(delta + radius + cy + (clear ? 0 : rd(r, t + 0x2060))));
         ++row) {
        if (++iterations > 1024 || row >= 1024) {
            context(r).fault = 2;
            return;
        }
        const uint32_t dst = rd(r, t + 0x54), src = rd(r, t + 0x58), dstPitch = rd(r, rd(r, t + 0x38) + 0x1c),
                       width = rd(r, t + 0x2064), leftToken = t + 0x60 + row * 4, rightToken = t + 0x1060 + row * 4;
        if (clear && (si(row) < si(cy - radius + 1) || si(row) > si(cy + radius - 1))) {
            zero(r, dst + row * dstPitch, width);
            continue;
        }
        const bool interior = clear || (si(row) > si(cy - radius) && si(row) < si(cy + radius));
        if (interior) {
            const uint32_t dy = row - cy, rootX = integerRoot(square - dy * dy), cx = rd(r, t + 0x4c),
                           right = uint32_t(std::min(si(width), std::max(0, si(cx + rootX)))),
                           left =
                               uint32_t(std::min(si(width), std::max(0, si(cx - rootX + (clear ? 1u : 0xffffffffu))))),
                           oldLeft = rd(r, leftToken), oldRight = rd(r, rightToken);
            if (clear) {
                zero(r, dst + row * dstPitch + oldLeft * bpp, (left - oldLeft) * bpp);
                zero(r, dst + row * dstPitch + right * bpp, (oldRight - right) * bpp);
                band(r, t, row, square, radius, palette, dst, capture);
                if (context(r).fault)
                    return;
            } else {
                const uint32_t srcPitch = rd(r, rd(r, t + 0x3c) + 0x1c);
                forward(r, dst + row * dstPitch + left * bpp, src + row * srcPitch + left * bpp,
                        (oldLeft - left) * bpp);
                forward(r, dst + row * dstPitch + oldRight * bpp, src + row * srcPitch + oldRight * bpp,
                        (right - oldRight) * bpp);
            }
            wr(r, leftToken, left);
            wr(r, rightToken, right);
        }
        if (!clear && si(row) > si(cy - stepValue - rd(r, t + 0x2060)) &&
            si(row) < si(stepValue + rd(r, t + 0x2060) + cy)) {
            const uint32_t outer = stepValue + rd(r, t + 0x2060) - 1;
            band(r, t, row, outer * outer, outer, palette, rd(r, t + 0x54), rd(r, t + 0x58));
        }
    }
    if (context(r).fault)
        return;
    if (clear)
        unlock(r, rd(r, t + 0x40));
    wr(r, t + 0x20, stepValue);
    unlock(r, rd(r, t + 0x38));
    unlock(r, rd(r, t + 0x3c));
}
uint32_t *destructionLookup(void *user, uint32_t t, uint32_t n) {
    auto &r = *static_cast<Run *>(user);
    return span(r, t, n);
}
void destructionFree(void *user, uint32_t t) {
    auto &r = *static_cast<Run *>(user);
    service(r, 0x4f6428, 0, {t});
}
uint32_t destructionCall(void *user, ClawSceneActorCall q) {
    auto &r = *static_cast<Run *>(user);
    if (q.argumentCount == 1)
        return service(r, q.function, q.receiver, {q.arguments[0]});
    if (!q.argumentCount)
        return service(r, q.function, q.receiver);
    context(r).fault = 1;
    return 0;
}
void releaseString(Run &r, uint32_t t) {
    ClawActorDestructionGlobals g{};
    g.emptyStringToken = r.b->emptyStringToken;
    ClawSceneActorHost host{};
    host.context = &r;
    host.lookup = destructionLookup;
    host.free = destructionFree;
    host.call = destructionCall;
    uint32_t result = 0;
    claw_actor_destruction_entry(0x4f6584, t, 0, &g, host, &context(r).fault, &result);
}
void allocateString(Run &r, uint32_t t, uint32_t length) {
    uint32_t data = r.b->emptyStringToken;
    if (length) {
        const uint32_t allocation = service(r, 0x4f63ec, 0, {length + 13});
        wr(r, allocation, 1);
        if (context(r).fault)
            return;
        storeByte(r, allocation + length + 12, 0);
        if (context(r).fault)
            return;
        wr(r, allocation + 4, length);
        wr(r, allocation + 8, length);
        data = allocation + 12;
    }
    wr(r, t, data);
}
void constructString(Run &r, uint32_t t, uint32_t text) {
    wr(r, t, r.b->emptyStringToken);
    if (!text)
        return;
    if (!(text >> 16)) {
        service(r, 0x4fb253, t, {text & 65535});
        return;
    }
    const uint32_t length = service(r, 0x5469e4, 0, {text});
    if (length) {
        allocateString(r, t, length);
        if (context(r).fault)
            return;
        ClawCArrayContext c{};
        c.scene = context(r).scene;
        uint32_t result = 0;
        claw_carray_entry(0x4a4a80, 0, rd(r, t), text, length, &c, nullptr, nullptr, &result);
        if (c.fault)
            context(r).fault = c.fault;
    }
}
uint32_t arrayDependency(ClawCArrayContext *, const ClawCArrayCall *q, void *user) {
    auto &r = *static_cast<Run *>(user);
    return service(r, q->function, q->receiver, {q->arguments[0]});
}
void append(Run &r, uint32_t t, uint32_t effect) {
    const uint32_t index = rd(r, t + 0x18);
    ClawCArrayContext c{};
    c.scene = context(r).scene;
    claw_carray_defaults(&c);
    uint32_t result = 0;
    claw_carray_entry(0x4f5915, t + 0x10, index + 1, 0xffffffff, 0, &c, arrayDependency, &r, &result);
    if (c.fault)
        context(r).fault = c.fault;
    wr(r, rd(r, t + 0x14) + index * 4, effect);
}
void resizePaletteArray(Run &r, uint32_t t, uint32_t size, uint32_t grow) {
    if (!size) {
        if (grow != 0xffffffff)
            wr(r, t + 16, grow);
        const uint32_t data = rd(r, t + 4);
        if (data) {
            service(r, 0x4f6428, 0, {data});
            wr(r, t + 4, 0);
        }
        wr(r, t + 12, 0);
        wr(r, t + 8, 0);
        return;
    }
    ClawCArrayContext c{};
    c.scene = context(r).scene;
    claw_carray_defaults(&c);
    uint32_t result = 0;
    claw_carray_entry(0x4f5915, t, size, grow, 0, &c, arrayDependency, &r, &result);
    if (c.fault)
        context(r).fault = c.fault;
}
uint32_t nearest(Run &r, uint32_t palette, uint32_t a, uint32_t b, uint32_t c) {
    auto *p = bytes(r, palette, 1024);
    if (!p)
        return 0;
    const int32_t values[3] = {int32_t(a & 255), int32_t(b & 255), int32_t(c & 255)};
    uint32_t best = 0;
    int32_t distance = 0;
    for (unsigned k = 0; k < 3; ++k) {
        const int32_t d = values[k] - p[k];
        distance += d * d;
    }
    for (uint32_t i = 1; i < 256; ++i) {
        int32_t current = 0;
        for (unsigned k = 0; k < 3; ++k) {
            const int32_t d = values[k] - p[i * 4 + k];
            current += d * d;
        }
        if (current < distance) {
            best = i;
            distance = current;
        }
    }
    return best;
}
uint32_t paletteAllocate(Run &r, uint32_t t, uint32_t count) {
    if (rd(r, t + 8))
        service(r, 0x4f6428, 0, {rd(r, t + 8)});
    wr(r, t + 4, count);
    const uint32_t data = service(r, 0x4f63ec, 0, {count});
    wr(r, t + 8, data);
    if (!data)
        return 0;
    wr(r, t, 1);
    return 1;
}
uint32_t paletteBuild(Run &r, uint32_t t, uint32_t colors, uint32_t gradient, uint32_t target) {
    const uint32_t object = service(r, 0x4f63ec, 0, {12});
    if (!object)
        return 0;
    wr(r, object, 0);
    wr(r, object + 4, 0);
    wr(r, object + 8, 0);
    if (!paletteAllocate(r, object, gradient << 8))
        return 0;
    const uint32_t index = rd(r, t + 12);
    resizePaletteArray(r, t + 4, index + 1, 0xffffffff);
    if (context(r).fault)
        return 0;
    wr(r, rd(r, t + 8) + index * 4, object);
    if (context(r).fault)
        return 0;
    uint32_t destination = rd(r, object + 8);
    if (si(gradient) > 4096) {
        context(r).fault = 2;
        return 0;
    }
    for (uint32_t color = 0; color < 256 && !context(r).fault; ++color) {
        for (uint32_t shade = 0; si(shade) < si(gradient) && !context(r).fault; ++shade) {
            const double ratio = double(si(shade)) / double(float(si(gradient))), inverse = 1.0 - ratio;
            const uint32_t component2 =
                root(ratio * double((target >> 16) & 255) + inverse * double(byte(r, colors + color * 4 + 2)));
            const uint32_t component1 =
                root(ratio * double((target >> 8) & 255) + inverse * double(byte(r, colors + color * 4 + 1)));
            const uint32_t component0 =
                root(ratio * double(target & 255) + inverse * double(byte(r, colors + color * 4)));
            const uint32_t result = nearest(r, colors, component0, component1, component2);
            storeByte(r, destination + shade, result);
        }
        destination += gradient;
    }
    return object;
}
void paletteReset(Run &r, uint32_t t) {
    if (rd(r, t)) {
        const uint32_t data = rd(r, t + 8);
        if (data) {
            service(r, 0x4f6428, 0, {data});
            wr(r, t + 8, 0);
        }
        wr(r, t + 4, 0);
    }
    wr(r, t, 0);
}
void paletteDelete(Run &r, uint32_t t) {
    if (rd(r, t))
        paletteReset(r, t);
}
void paletteRemove(Run &r, uint32_t t, uint32_t object) {
    uint32_t index = 0;
    while (si(index) < si(rd(r, t + 12))) {
        if (rd(r, rd(r, t + 8) + index * 4) == object)
            break;
        if (++index > 1000000) {
            context(r).fault = 2;
            return;
        }
    }
    if (si(index) >= si(rd(r, t + 12)))
        return;
    paletteReset(r, rd(r, rd(r, t + 8) + index * 4));
    if (context(r).fault)
        return;
    const uint32_t current = rd(r, rd(r, t + 8) + index * 4);
    if (current) {
        paletteDelete(r, current);
        service(r, 0x4f6428, 0, {current});
    }
    uint32_t count = rd(r, t + 12) - index - 1;
    const uint32_t data = rd(r, t + 8);
    for (uint32_t i = 0; i < count; ++i) {
        if (i > 1000000) {
            context(r).fault = 2;
            return;
        }
        wr(r, data + (index + i) * 4, rd(r, data + (index + i + 1) * 4));
    }
    wr(r, t + 12, rd(r, t + 12) - 1);
}
void paletteClear(Run &r, uint32_t t) {
    for (uint32_t index = 0; !context(r).fault && si(index) < si(rd(r, t + 12)); ++index) {
        if (index > 1000000) {
            context(r).fault = 2;
            return;
        }
        paletteReset(r, rd(r, rd(r, t + 8) + index * 4));
        if (context(r).fault)
            return;
        const uint32_t current = rd(r, rd(r, t + 8) + index * 4);
        if (current) {
            paletteDelete(r, current);
            service(r, 0x4f6428, 0, {current});
        }
    }
    const uint32_t data = rd(r, t + 8);
    if (data) {
        service(r, 0x4f6428, 0, {data});
        wr(r, t + 8, 0);
    }
    wr(r, t + 16, 0);
    wr(r, t + 12, 0);
}
void paletteOwnerDelete(Run &r, uint32_t t) {
    if (rd(r, t))
        paletteClear(r, t);
    if (context(r).fault)
        return;
    wr(r, t + 4, 0x5136e8);
    const uint32_t data = rd(r, t + 8);
    if (data)
        service(r, 0x4f6428, 0, {data});
    wr(r, t + 4, 0x50becc);
}
void diagnostic(Run &r, uint32_t text) {
    if (!r.b->temporaryStringToken) {
        context(r).fault = 1;
        return;
    }
    constructString(r, r.b->temporaryStringToken, text);
    if (!context(r).fault)
        releaseString(r, r.b->temporaryStringToken);
}
uint32_t factory(Run &r, uint32_t t, uint32_t type, uint32_t descriptor) {
    if (type != 1) {
        context(r).fault = 3;
        return 0;
    }
    if (descriptor && rd(r, descriptor) != 2) {
        diagnostic(r, 0x53404c);
        return 0;
    }
    const uint32_t effect = service(r, 0x4f63ec, 0, {0x206c});
    if (effect)
        frozen(r, 0x4ed5e0, effect);
    frozen(r, 0x4ecb00, effect, {rd(r, t), rd(r, t + 4)});
    frozen(r, 0x4ecb20, effect, {rd(r, t + 0x24)});
    if (context(r).fault)
        return 0;
    if (!descriptor) {
        descriptor = context(r).temporaryDescriptorToken;
        wr(r, descriptor + 12, context(r).descriptorWord3);
        frozen(r, 0x4ecbc0, descriptor);
    }
    if (!frozen(r, 0x4ed670, effect, {descriptor})) {
        if (context(r).fault)
            return 0;
        diagnostic(r, 0x5340a0);
        if (context(r).fault)
            return 0;
        const uint32_t function = rd(r, rd(r, effect));
        if (function == 0x4ed600)
            frozen(r, function, effect, {1});
        else
            service(r, function, effect, {1});
        return 0;
    }
    append(r, t, effect);
    return effect;
}
} // namespace
uint32_t claw_player_fade_blend_entry(uint32_t fn, uint32_t receiver, const uint32_t *args, uint32_t count,
                                      ClawPlayerFadeBlendContext *b, ClawPlayerFadeDependency d, void *user,
                                      uint32_t *result) {
    if (!b || !b->fade || count > 6 || (!args && count))
        return 0;
    switch (fn) {
    case 0x4ed800:
    case 0x4ee170:
    case 0x4ec050:
    case 0x4ec6b0:
    case 0x4f65f2:
    case 0x4f6480:
    case 0x4f6433:
    case 0x4c6bd0:
    case 0x4c76d0:
    case 0x4c76f0:
    case 0x4c7580:
    case 0x4dee30:
    case 0x4c78d0:
    case 0x4c76e0:
    case 0x4c7510:
    case 0x4c6270:
    case 0x4c61f0:
        break;
    default:
        return 0;
    }
    if (b->fade->fault)
        return 0;
    Run r{b, d, user};
    uint32_t value = 0;
    const uint32_t required =
        fn == 0x4ee170                                                                                             ? 6
        : fn == 0x4c7580                                                                                           ? 4
        : fn == 0x4c6bd0                                                                                           ? 3
        : fn == 0x4ec050 || fn == 0x4dee30                                                                         ? 2
        : fn == 0x4f6433 || fn == 0x4c76d0 || fn == 0x4c78d0 || fn == 0x4c76e0 || fn == 0x4c6270 || fn == 0x4c61f0 ? 0
                                                                                                                   : 1;
    if (count != required) {
        b->fade->fault = 2;
        return 0;
    }
    switch (fn) {
    case 0x4ed800:
        step(r, receiver, args[0]);
        break;
    case 0x4ee170:
        band(r, receiver, args[0], args[1], args[2], args[3], args[4], args[5]);
        break;
    case 0x4ec050:
        value = factory(r, receiver, args[0], args[1]);
        break;
    case 0x4ec6b0:
        wr(r, b->temporaryStringToken, args[0]);
        releaseString(r, b->temporaryStringToken);
        break;
    case 0x4f65f2:
        constructString(r, receiver, args[0]);
        value = receiver;
        break;
    case 0x4f6480:
        allocateString(r, receiver, args[0]);
        break;
    case 0x4f6433:
        value = 0x52e1cc;
        break;
    case 0x4c6bd0:
        value = paletteBuild(r, receiver, args[0], args[1], args[2]);
        break;
    case 0x4c76d0:
        wr(r, receiver, 0);
        wr(r, receiver + 4, 0);
        wr(r, receiver + 8, 0);
        value = receiver;
        break;
    case 0x4c76f0:
        value = paletteAllocate(r, receiver, args[0]);
        break;
    case 0x4c7580:
        value = nearest(r, args[0], args[1], args[2], args[3]);
        break;
    case 0x4dee30:
        resizePaletteArray(r, receiver, args[0], args[1]);
        break;
    case 0x4c78d0:
        paletteReset(r, receiver);
        break;
    case 0x4c76e0:
        paletteDelete(r, receiver);
        break;
    case 0x4c7510:
        paletteRemove(r, receiver, args[0]);
        break;
    case 0x4c6270:
        paletteClear(r, receiver);
        break;
    case 0x4c61f0:
        paletteOwnerDelete(r, receiver);
        break;
    default:
        break;
    }
    if (result)
        *result = value;
    return b->fade->fault ? 0 : 1;
}
