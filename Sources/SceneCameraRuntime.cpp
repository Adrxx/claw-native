#include "SceneCameraRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
namespace {
int32_t si(uint32_t v) {
    int32_t x;
    std::memcpy(&x, &v, 4);
    return x;
}
struct Run {
    ClawSceneCameraGlobals *g;
    ClawSceneCameraHost h;
    uint32_t *fault;
};
void fail(Run &r, uint32_t f = 1) {
    if (r.fault)
        *r.fault = f;
}
bool bad(const Run &r) {
    return r.fault && *r.fault;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    if (!r.h.heap.lookup) {
        fail(r);
        return nullptr;
    }
    auto *p = r.h.heap.lookup(r.h.heap.context, t, n);
    if (!p)
        fail(r);
    return p;
}
uint32_t service(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {}) {
    if (!r.h.heap.call) {
        fail(r);
        return 0;
    }
    ClawSceneActorCall c{};
    c.function = f;
    c.receiver = receiver;
    c.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), c.arguments);
    return r.h.heap.call(r.h.heap.context, c);
}
uint32_t platform(Run &r, uint32_t slot, std::initializer_list<uint32_t> args = {}, uint32_t *buffer = nullptr,
                  uint32_t n = 0, uint32_t token = 0) {
    if (!r.h.platform) {
        fail(r);
        return 0;
    }
    ClawSceneCameraPlatformCall c{};
    c.importSlot = slot;
    c.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), c.arguments);
    c.buffer = buffer;
    c.bufferWords = n;
    c.bufferToken = token;
    return r.h.platform(r.h.platformContext, c);
}
bool key(Run &r, uint32_t v, bool low = false) {
    const uint32_t value = platform(r, 0x546ce4, {v});
    return (value & (low ? 0x8001u : 0x8000u)) != 0;
}
constexpr uint32_t directions[] = {0x10000000, 0x20000000, 0x40000000, 0x80000000};
void deviceReset(Run &r, uint32_t *d) {
    d[0x210 / 4] = d[0x214 / 4] = d[0x20c / 4] = 0;
    if (d[0x1cc / 4] & 1)
        for (size_t i = 0; i < 12; ++i)
            platform(r, 0x546ce4, {d[0x1dc / 4 + i]});
    if (d[0x1cc / 4] & 4) {
        d[0x240 / 4] = uint32_t(si(platform(r, 0x546c44, {0})) / 2);
        d[0x244 / 4] = uint32_t(si(platform(r, 0x546c44, {1})) / 2);
        platform(r, 0x546d9c, {d[0x240 / 4], d[0x244 / 4]});
    }
}
void devicePoll(Run &r, uint32_t token, uint32_t *d) {
    d[0x210 / 4] = d[0x214 / 4] = 0;
    if (d[0x1cc / 4] & 1) {
        for (size_t i = 0; i < 12; ++i)
            if (key(r, d[0x1dc / 4 + i], i >= 4))
                d[0x210 / 4] |= i < 4 ? directions[i] : 1u << (i - 4);
    }
    if (d[0x1cc / 4] & 4) {
        uint32_t local[2]{};
        platform(r, 0x546cd0, {}, local, 2);
        if (si(d[0x230 / 4]) < si(0u - d[0x238 / 4]))
            d[0x210 / 4] |= directions[0];
        if (si(d[0x230 / 4]) > si(d[0x238 / 4]))
            d[0x210 / 4] |= directions[1];
        if (si(d[0x234 / 4]) < si(0u - d[0x23c / 4]))
            d[0x210 / 4] |= directions[2];
        if (si(d[0x234 / 4]) > si(d[0x23c / 4]))
            d[0x210 / 4] |= directions[3];
        if (key(r, 1, true))
            d[0x210 / 4] |= 1;
        if (key(r, 2, true))
            d[0x210 / 4] |= 2;
        platform(r, 0x546d9c, {d[0x240 / 4], d[0x244 / 4]});
    }
    if (d[0x1cc / 4] & 2) {
        d[0x19c / 4] = 0x83;
        platform(r, 0x546de8, {d[0]}, d + 0x198 / 4, 13, token + 0x198);
        if (d[0x1a0 / 4] < d[0x220 / 4])
            d[0x210 / 4] |= directions[0];
        if (d[0x1a0 / 4] > d[0x224 / 4])
            d[0x210 / 4] |= directions[1];
        if (d[0x1a4 / 4] < d[0x228 / 4])
            d[0x210 / 4] |= directions[2];
        if (d[0x1a4 / 4] > d[0x22c / 4])
            d[0x210 / 4] |= directions[3];
        d[0x210 / 4] |= d[0x1b8 / 4] & 15;
        if (d[0x1d4 / 4]) {
            d[0x210 / 4] |= d[0x1b8 / 4] & 0xf0;
            if (d[0x40 / 4] > 8 && !d[0x1d8 / 4] && (d[0x1b8 / 4] & 0x100))
                d[0x210 / 4] |= 0x100;
        }
    }
    d[0x214 / 4] = d[0x210 / 4];
    uint32_t mask = 0xf000000f;
    if (d[0x1d4 / 4])
        mask |= 0x1f0;
    const uint32_t held = d[0x214 / 4];
    const uint32_t old = d[0x20c / 4];
    d[0x210 / 4] &= ~(held & old & mask);
    d[0x20c / 4] = (old & ~mask) | (held & mask);
}
void mappingReset(Run &r, uint32_t *p) {
    auto *d = span(r, p[0], 146);
    if (!d)
        return;
    deviceReset(r, d);
    p[1] = p[2] = p[3] = p[28] = 0;
}
void mappingPoll(Run &r, uint32_t *p) {
    auto *d = span(r, p[0], 146);
    if (!d)
        return;
    devicePoll(r, p[0], d);
    p[2] = p[1] = 0;
    for (size_t i = 0; i < 4; ++i)
        if (d[0x214 / 4] & directions[i])
            p[2] |= 0x1000000u << i;
    constexpr uint32_t bits[] = {1, 2, 4, 8, 0x20, 0x40, 0x80, 0x100, 0x200};
    constexpr uint32_t offsets[] = {4, 5, 6, 7, 9, 10, 11, 12, 13};
    for (size_t i = 0; i < 9; ++i)
        if (d[0x214 / 4] & p[offsets[i]])
            p[2] |= bits[i];
    for (size_t i = 0; i < 4; ++i)
        if (key(r, p[14 + i]))
            p[2] |= 0x1000000u << i;
    for (size_t i = 0; i < 9; ++i)
        if (key(r, p[18 + (offsets[i] - 4)]))
            p[2] |= bits[i];
    p[28] = p[2];
    constexpr uint32_t mask = 0xf0003efu;
    p[1] |= p[2] & ~p[3] & mask;
    p[3] = (p[3] & ~mask) | (p[2] & mask);
}
float fl(uint32_t v) {
    float x;
    std::memcpy(&x, &v, 4);
    return x;
}
uint32_t fb(float v) {
    uint32_t x;
    std::memcpy(&x, &v, 4);
    return x;
}
double add(double a, double b) {
    volatile double x = a + b;
    return x;
}
double sub(double a, double b) {
    volatile double x = a - b;
    return x;
}
double mul(double a, double b) {
    volatile double x = a * b;
    return x;
}
uint32_t truncLow(double v) {
    uint64_t b;
    std::memcpy(&b, &v, 8);
    int e = int((b >> 52) & 2047) - 1023;
    if (e < 0 || e >= 63)
        return 0;
    uint64_t m = (b & 0xfffffffffffffULL) | 0x10000000000000ULL;
    m = e >= 52 ? m << (e - 52) : m >> (52 - e);
    return b >> 63 ? 0u - uint32_t(m) : uint32_t(m);
}
void clampPlane(Run &r, uint32_t *p) {
    for (size_t axis = 0; axis < 2; ++axis) {
        const size_t pos = 4 + axis, extent = 12 + axis;
        double v = double(fl(p[pos]));
        const int32_t e = si(p[extent]);
        if (!std::isfinite(v) || e <= 0) {
            fail(r, 2);
            return;
        }
        const bool wrap = bool(p[2] & (4u << axis));
        if (wrap) {
            size_t iterations = 0;
            if (v < 0) {
                do {
                    v = add(v, double(e));
                    if (++iterations > 1000000) {
                        fail(r, 2);
                        return;
                    }
                } while (v < 0);
                p[pos] = fb(float(v));
                v = double(fl(p[pos]));
            }
            const double roundedExtent = double(float(e));
            if (v >= roundedExtent) {
                do {
                    v = sub(v, roundedExtent);
                    if (++iterations > 1000000) {
                        fail(r, 2);
                        return;
                    }
                } while (v >= roundedExtent);
                p[pos] = fb(float(v));
            }
        } else if (v < 0)
            p[pos] = 0;
        else if (double(e) <= v)
            p[pos] = fb(float(e - 1));
    }
    p[0x84 / 4] = truncLow(double(fl(p[4])));
    p[0x88 / 4] = truncLow(double(fl(p[5])));
    for (size_t axis = 0; axis < 2; ++axis) {
        const size_t low = 16 + axis, high = 18 + axis;
        const bool wrap = bool(p[2] & (4u << axis));
        p[low] = p[33 + axis] - p[30 + axis];
        if (si(p[low]) < 0)
            p[low] = wrap ? p[12 + axis] + p[low] : 0;
        p[high] = p[28 + axis] - 1 + p[low];
        if (si(p[12 + axis]) <= si(p[high]) && !wrap) {
            const uint32_t correction = p[high] - p[12 + axis] + 1;
            p[high] -= correction;
            p[low] -= correction;
        }
    }
}
void setPlane(Run &r, uint32_t *p, uint32_t x, uint32_t y) {
    p[4] = fb(float(p[2] & 1 ? double(si(x)) : mul(double(si(x)), double(fl(p[6])))));
    p[5] = fb(float(p[2] & 1 ? double(si(y)) : mul(double(si(y)), double(fl(p[7])))));
    clampPlane(r, p);
}
void worldFollow(Run &r, uint32_t token, uint32_t x, uint32_t y) {
    auto *w = span(r, token, 25);
    if (!w)
        return;
    auto *main = span(r, w[0x5c / 4], 45);
    if (!main)
        return;
    setPlane(r, main, x, y);
    if (bad(r))
        return;
    const uint32_t cx = main[33], cy = main[34];
    for (uint32_t i = 0; si(i) < si(w[15]); ++i)
        if (i != w[24]) {
            auto *table = span(r, w[14], i + 1);
            if (!table)
                return;
            auto *p = span(r, table[i], 45);
            if (!p)
                return;
            setPlane(r, p, cx, cy);
            if (bad(r))
                return;
        }
}
uint32_t absWrap(uint32_t v) {
    const uint32_t sign = si(v) < 0 ? 0xffffffff : 0;
    return (v ^ sign) - sign;
}
void target(Run &r, uint32_t *c, uint32_t *player) {
    c[2] = player[0x4c / 4];
    c[3] = player[0x50 / 4];
    if (r.g->forcedX != 0xffffffff) {
        c[2] = r.g->forcedX;
        c[3] = r.g->forcedY;
    }
}
void teleport(uint32_t *c) {
    if (si(absWrap(c[2] - c[0])) > 500 || si(absWrap(c[3] - c[1])) > 500) {
        c[0] = c[2];
        c[1] = c[3];
    }
}
void smooth(Run &r, uint32_t *c, uint32_t sx, uint32_t sy) {
    if (r.g->forcedX != 0xffffffff) {
        c[2] = r.g->forcedX;
        c[3] = r.g->forcedY;
    }
    const uint32_t speeds[] = {sx, sy};
    for (size_t axis = 0; axis < 2; ++axis) {
        const uint32_t step = (speeds[axis] * r.g->animationDelta) / 1000;
        if (si(c[axis]) < si(c[axis + 2])) {
            c[axis] += step;
            if (si(c[axis + 2]) < si(c[axis]))
                c[axis] = c[axis + 2];
        } else if (si(c[axis + 2]) < si(c[axis])) {
            c[axis] -= step;
            if (si(c[axis]) < si(c[axis + 2]))
                c[axis] = c[axis + 2];
        }
    }
}
void shake(Run &r, uint32_t *c) {
    if (c[4] < r.g->animationDelta) {
        c[4] = uint32_t(si(service(r, 0x4a3050, 0)) % 36);
        const uint32_t x = service(r, 0x4a3050, 0), y = service(r, 0x4a3050, 0);
        c[0] += uint32_t(si(x) % 13) - 6;
        c[1] += uint32_t(si(y) % 13) - 6;
    } else
        c[4] -= r.g->animationDelta;
}
void inputStage(Run &r, uint32_t owner) {
    auto *w = span(r, owner, 474);
    if (!w)
        return;
    auto *m = span(r, w[1], 20);
    if (!m)
        return;
    auto *cfg = span(r, m[0x4c / 4], 13);
    if (!cfg)
        return;
    auto *input = span(r, r.g->inputMappingToken, 29);
    if (!input)
        return;
    if (cfg[12]) {
        mappingReset(r, input);
        return;
    }
    w[0x764 / 4] = r.g->stageDelta < w[0x764 / 4] ? w[0x764 / 4] - r.g->stageDelta : 0;
    if (w[0x764 / 4]) {
        mappingReset(r, input);
        return;
    }
    mappingPoll(r, input);
    auto *d = span(r, r.g->inputDeviceToken, 146);
    if (!d)
        return;
    if ((d[0x210 / 4] & 0x100) && !r.g->menuBlocked) {
        auto *window = span(r, m[1], 2);
        if (window)
            platform(r, 0x546d50, {window[1], 0x111, 0x8080, 0});
    }
}
uint32_t detached(Run &r, uint32_t actor) {
    auto *mapping = span(r, r.g->inputMappingToken, 29);
    if (!mapping)
        return 0;
    if (r.g->detachedOwnerToken && !(mapping[2] & 0xf000003)) {
        auto *owner = span(r, r.g->detachedOwnerToken, 6);
        if (!owner)
            return 0;
        if (owner[5]) {
            auto *cell = span(r, owner[5], 1);
            if (!cell)
                return 0;
            if (*cell) {
                auto *p = span(r, *cell, 128);
                auto *a = span(r, actor, 128);
                if (!p || !a)
                    return 0;
                auto *parent = span(r, a[3], 10);
                if (!parent)
                    return 0;
                worldFollow(r, parent[9], p[0x4c / 4], p[0x50 / 4]);
                return 1;
            }
        }
    }
    r.g->detachedMode = r.g->detachedOwnerToken = 0;
    return 0;
}
uint32_t follow(Run &r, uint32_t token) {
    if (!r.g->playerToken)
        return 0;
    if (r.g->detachedMode)
        return detached(r, token);
    auto *a = span(r, token, 128);
    if (!a)
        return 0;
    auto *l = span(r, a[0x6c / 4], 93);
    if (!l)
        return 0;
    uint32_t ctoken = l[5];
    if (r.g->forcedX != 0xffffffff && l[7])
        l[7] = 0x22b8;
    auto *player = span(r, r.g->playerToken, 128);
    if (!player)
        return 0;
    auto *c = ctoken && l[7] != 0 ? span(r, ctoken, 5) : nullptr;
    if (l[7] == 0) {
        r.g->forcedX = r.g->forcedY = 0xffffffff;
        if (!r.h.heap.allocate) {
            fail(r);
            return 0;
        }
        ctoken = r.h.heap.allocate(r.h.heap.context, 20);
        l[5] = ctoken;
        c = span(r, ctoken, 5);
        if (!c)
            return 0;
        std::fill_n(c, 5, 0);
        c[0] = player[0x4c / 4];
        c[1] = player[0x50 / 4];
        l[7] = 24;
        target(r, c, player);
        teleport(c);
        const uint32_t mode = player[0xcc / 4];
        const uint32_t speed = mode == 3 || mode == 4 ? 4000 : mode == 8 ? 99999 : 500;
        smooth(r, c, speed, speed);
    } else if (l[7] == 24) {
        auto *pl = span(r, player[0x6c / 4], 93);
        if (!pl)
            return 0;
        const uint32_t st = pl[7];
        uint32_t ready = 1;
        if (st == 26 || st == 0x138b) {
            auto *privatePlayer = span(r, pl[5], 78);
            if (!privatePlayer)
                return 0;
            ready = privatePlayer[0x110 / 4];
        }
        if (st != 0x138c) {
            if ((st == 26 || st == 0x138b) && !ready) {
                if (!c) {
                    fail(r);
                    return 0;
                }
                l[7] = st;
                c[2] = player[0x4c / 4];
                c[3] = player[0x50 / 4] + (st == 26 ? 200u : uint32_t(-200));
                smooth(r, c, 250, 250);
            } else {
                if (!c) {
                    fail(r);
                    return 0;
                }
                target(r, c, player);
                teleport(c);
                const uint32_t mode = player[0xcc / 4];
                const uint32_t speed = mode == 3 || mode == 4 ? 4000 : mode == 8 ? 99999 : 500;
                smooth(r, c, speed, speed);
            }
        }
    } else if (l[7] == 26 || l[7] == 0x138b) {
        auto *pl = span(r, player[0x6c / 4], 93);
        if (!pl)
            return 0;
        if (!c) {
            fail(r);
            return 0;
        }
        auto *pv = pl[7] == l[7] ? span(r, pl[5], 78) : nullptr;
        if (bad(r))
            return 0;
        if (pl[7] == l[7] && !pv[0x110 / 4]) {
            c[2] = player[0x4c / 4];
            c[3] = player[0x50 / 4] + (l[7] == 26 ? 200u : uint32_t(-200));
            smooth(r, c, 250, 250);
        } else {
            l[7] = 24;
            target(r, c, player);
            teleport(c);
            const uint32_t mode = player[0xcc / 4];
            const uint32_t speed = mode == 3 || mode == 4 ? 4000 : mode == 8 ? 99999 : 500;
            smooth(r, c, speed, speed);
        }
    } else if (l[7] == 0x22b8) {
        if (!c) {
            fail(r);
            return 0;
        }
        if (r.g->forcedX != 0xffffffff)
            smooth(r, c, 400, 400);
        else {
            l[7] = 24;
            target(r, c, player);
            teleport(c);
            const uint32_t mode = player[0xcc / 4];
            const uint32_t speed = mode == 3 || mode == 4 ? 4000 : mode == 8 ? 99999 : 500;
            smooth(r, c, speed, speed);
        }
    }
    if (r.g->animationNow < r.g->shakeUntil) {
        if (!c) {
            fail(r);
            return 0;
        }
        shake(r, c);
    }
    if (c) {
        auto *parent = span(r, a[3], 10);
        if (!parent)
            return 0;
        worldFollow(r, parent[9], c[0], c[1]);
    }
    return 1;
}
} // namespace
uint32_t claw_scene_camera_entry(uint32_t f, uint32_t receiver, uint32_t x, uint32_t y, ClawSceneCameraGlobals *globals,
                                 ClawSceneCameraHost host, uint32_t *fault, uint32_t *result) {
    if (!globals) {
        if (fault)
            *fault = 1;
        return 0;
    }
    Run r{globals, host, fault};
    uint32_t value = 0;
    uint32_t *p = nullptr;
    switch (f) {
    case 0x46c860:
        inputStage(r, receiver);
        break;
    case 0x430ec0:
        p = span(r, receiver, 29);
        if (p) {
            mappingPoll(r, p);
            value = 1;
        }
        break;
    case 0x431300:
        p = span(r, receiver, 29);
        if (p) {
            mappingReset(r, p);
            value = 1;
        }
        break;
    case 0x4b3490:
        p = span(r, receiver, 146);
        if (p)
            devicePoll(r, receiver, p);
        break;
    case 0x4b3ab0:
        p = span(r, receiver, 146);
        if (p)
            deviceReset(r, p);
        break;
    case 0x430d30: {
        p = span(r, receiver, 29);
        constexpr uint32_t defaults[] = {1, 2, 4, 8, 0, 0x10, 0x20, 0x40, 0x80, 0};
        if (p)
            std::copy_n(defaults, 10, p + 4);
        break;
    }
    case 0x430d80: {
        p = span(r, receiver, 29);
        constexpr uint32_t defaults[] = {0x25, 0x27, 0x26, 0x28, 0x20, 0x11, 0x12,
                                         0x10, 0,    0x5a, 0x31, 0x32, 0x33, 0x34};
        if (p)
            std::copy_n(defaults, 14, p + 14);
        break;
    }
    case 0x4b3430: {
        p = span(r, receiver, 146);
        if (!p)
            break;
        if ((x & 2) && !p[0x1d0 / 4])
            x &= ~2u;
        if (x & 4) {
            p[0x240 / 4] = uint32_t(si(platform(r, 0x546c44, {0})) / 2);
            p[0x244 / 4] = uint32_t(si(platform(r, 0x546c44, {1})) / 2);
            platform(r, 0x546d9c, {p[0x240 / 4], p[0x244 / 4]});
        }
        p[0x1cc / 4] = x;
        break;
    }
    case 0x486240:
        value = follow(r, receiver);
        break;
    case 0x486d70:
        value = detached(r, receiver);
        break;
    case 0x486d30:
        globals->detachedMode = globals->detachedOwnerToken = 0;
        value = 1;
        break;
    case 0x42d5f0:
        worldFollow(r, receiver, x, y);
        break;
    case 0x4d0a60:
        p = span(r, receiver, 45);
        if (p)
            clampPlane(r, p);
        break;
    case 0x4d0c50: {
        p = span(r, receiver, 45);
        auto *rect = span(r, x, 4);
        if (!p || !rect || rect[0] == 0x80000000)
            break;
        std::copy_n(rect, 4, p + 20);
        p[28] = rect[2] - rect[0] + 1;
        p[29] = rect[3] - rect[1] + 1;
        p[30] = uint32_t(si(p[28]) / 2);
        p[31] = uint32_t(si(p[29]) / 2);
        clampPlane(r, p);
        break;
    }
    default:
        return 0;
    }
    if (result)
        *result = value;
    return 1;
}
uint32_t claw_scene_camera_projection(uint32_t token, ClawSceneActorHost host, ClawSpriteProjection *out,
                                      uint32_t *fault) {
    if (!out || !host.lookup) {
        if (fault)
            *fault = 1;
        return 0;
    }
    auto *p = host.lookup(host.context, token, 45);
    if (!p) {
        if (fault)
            *fault = 1;
        return 0;
    }
    *out = {p[2], p[12], p[13], p[16], p[17], p[18], p[19], p[20], p[21]};
    return 1;
}
