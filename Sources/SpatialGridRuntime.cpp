#include "SpatialGridRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawSceneActorHost h;
    uint32_t *fault;
};
int32_t si(uint32_t x) {
    int32_t y;
    std::memcpy(&y, &x, 4);
    return y;
}
void fail(Run &r, uint32_t n = 1) {
    if (r.fault)
        *r.fault = n;
}
bool bad(Run &r) {
    return r.fault && *r.fault;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    if (!r.h.lookup) {
        fail(r);
        return nullptr;
    }
    auto *p = r.h.lookup(r.h.context, t, n);
    if (!p)
        fail(r);
    return p;
}
uint32_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {}) {
    if (!r.h.call) {
        fail(r);
        return 0;
    }
    ClawSceneActorCall c{};
    c.function = f;
    c.receiver = receiver;
    c.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), c.arguments);
    return r.h.call(r.h.context, c);
}
uint32_t allocate(Run &r, uint32_t n) {
    if (!r.h.allocate) {
        fail(r);
        return 0;
    }
    return r.h.allocate(r.h.context, n);
}
void release(Run &r, uint32_t t) {
    if (!r.h.free) {
        fail(r);
        return;
    }
    r.h.free(r.h.context, t);
}
uint32_t vf(Run &r, uint32_t vt, uint32_t slot) {
    if (vt == 0x513db0)
        return slot == 4 ? 0x4d4a90 : slot == 0x14 ? 0x4d4870 : 0;
    auto *p = span(r, vt + slot, 1);
    return p ? *p : 0;
}
uint32_t truncFloat(uint32_t bits) {
    float v;
    std::memcpy(&v, &bits, 4);
    double d = v;
    if (!std::isfinite(d) || d >= 9223372036854775808. || d < -9223372036854775808.)
        return 0;
    return uint32_t(int64_t(d));
}
uint32_t sar(uint32_t x, uint32_t bits) {
    return uint32_t(si(x) >> (bits & 31));
}
bool limit(Run &r, uint32_t n) {
    if (n > 1000000) {
        fail(r, 2);
        return false;
    }
    return true;
}
void cellInsert(Run &r, uint32_t cell, uint32_t member) {
    auto *c = span(r, cell, 2);
    auto *m = span(r, member, 6);
    if (!c || !m)
        return;
    m[0] = c[0];
    m[1] = 0;
    if (c[0]) {
        auto *old = span(r, c[0], 2);
        if (!old)
            return;
        old[1] = member;
        c[0] = member;
    } else {
        c[1] = member;
        c[0] = member;
    }
}
void cellRemove(Run &r, uint32_t cell, uint32_t member) {
    auto *c = span(r, cell, 2);
    auto *m = span(r, member, 2);
    if (!c || !m)
        return;
    if (!m[1])
        c[0] = m[0];
    else {
        auto *prev = span(r, m[1], 1);
        if (!prev)
            return;
        prev[0] = m[0];
    }
    if (m[0]) {
        auto *next = span(r, m[0], 2);
        if (!next)
            return;
        next[1] = m[1];
    } else
        c[1] = m[1];
}
uint32_t registerMember(Run &r, uint32_t layer, uint32_t member) {
    auto *p = span(r, layer, 17);
    auto *m = span(r, member, 6);
    if (!p || !m)
        return 0;
    uint32_t index = sar(m[5] - p[11], p[6]) * p[3] + sar(m[4] - p[10], p[5]);
    uint32_t cell = p[16] + index * 8;
    m[3] = cell;
    cellInsert(r, cell, member);
    ++p[2];
    return 1;
}
void registerActor(Run &r, uint32_t grid, uint32_t actor) {
    auto *p = span(r, grid, 28);
    auto *a = span(r, actor, 128);
    if (!p || !a)
        return;
    registerMember(r, p[(a[2] & 0x800000) ? 2 : (a[2] & 0x1000000) ? 3 : 1], actor + 0x88);
}
void sceneRemove(Run &r, uint32_t list, uint32_t node) {
    auto *c = span(r, list, 7);
    auto *n = span(r, node, 3);
    if (!c || !n)
        return;
    if (node == c[1])
        c[1] = n[0];
    else {
        auto *q = span(r, n[1], 1);
        if (!q)
            return;
        q[0] = n[0];
    }
    if (node == c[2])
        c[2] = n[1];
    else {
        auto *q = span(r, n[0], 2);
        if (!q)
            return;
        q[1] = n[1];
    }
    n[0] = c[4];
    --c[3];
    c[4] = node;
    if (!c[3]) {
        c[3] = c[4] = c[2] = c[1] = 0;
        uint32_t block = c[5], count = 0;
        while (block) {
            if (!limit(r, ++count))
                return;
            auto *q = span(r, block, 1);
            if (!q)
                return;
            uint32_t next = q[0];
            release(r, block);
            if (bad(r))
                return;
            block = next;
        }
        c[5] = 0;
    }
}
void destroyActor(Run &r, uint32_t actor) {
    auto *a = span(r, actor, 1);
    if (!a)
        return;
    uint32_t fn = a[0] == 0x5137f0 ? 0x4c9be0 : vf(r, a[0], 4);
    if (!bad(r))
        call(r, fn, actor, {1});
}
void actorCallback(Run &r, uint32_t actor, uint32_t state, bool restore) {
    auto *a = span(r, actor, 128);
    if (!a)
        return;
    auto *l = span(r, a[27], 93);
    if (!l)
        return;
    uint32_t old = l[7];
    l[7] = state;
    call(r, l[4], 0, {actor});
    if (restore && l[7] == state)
        l[7] = old;
}
void activate(Run &r, uint32_t layer, uint32_t member) {
    auto *p = span(r, layer, 17);
    if (!p)
        return;
    uint32_t fn = vf(r, p[0], 0x14);
    if (bad(r))
        return;
    if (fn == 0x4d4870) {
        auto *m = span(r, member, 7);
        if (!m)
            return;
        auto *a = span(r, m[6], 128);
        if (!a)
            return;
        auto *parent = span(r, a[3], 3);
        if (!parent)
            return;
        claw_scene_actor_insert(parent[2], m[6], r.h, r.fault);
    } else
        call(r, fn, layer, {member});
}
uint32_t query(Run &r, uint32_t layer, uint32_t x1, uint32_t y1, uint32_t x2, uint32_t y2, uint32_t remove) {
    auto *p = span(r, layer, 17);
    if (!p)
        return 0;
    uint32_t found = 0;
    if (si(p[12]) < si(x1) || si(x2) < si(p[10]) || si(p[13]) < si(y1) || si(y2) < si(p[11]))
        return 0;
    x1 = uint32_t(std::max(si(x1), si(p[10])));
    x2 = uint32_t(std::min(si(x2), si(p[12])));
    y1 = uint32_t(std::max(si(y1), si(p[11])));
    y2 = uint32_t(std::min(si(y2), si(p[13])));
    uint32_t row = sar(y1 - p[11], p[6]), lastRow = sar(y2 - p[11], p[6]), col = sar(x1 - p[10], p[5]),
             lastCol = sar(x2 - p[10], p[5]), index = row * p[3] + col;
    if (si(row) > si(lastRow))
        return 0;
    uint32_t rows = lastRow - row + 1;
    if (!limit(r, rows))
        return 0;
    for (uint32_t y = 0; y < rows; ++y) {
        if (si(col) <= si(lastCol)) {
            uint32_t cols = lastCol - col + 1;
            if (!limit(r, cols))
                return 0;
            uint32_t byteIndex = index * 8;
            for (uint32_t x = 0; x < cols; ++x) {
                auto *cell = span(r, p[16] + byteIndex, 2);
                if (!cell)
                    return found;
                uint32_t at = cell[0], loops = 0;
                while (at) {
                    if (!limit(r, ++loops))
                        return found;
                    auto *m = span(r, at, 7);
                    if (!m)
                        return found;
                    uint32_t next = m[0];
                    if (si(x1) <= si(m[4]) && si(y1) <= si(m[5]) && si(m[4]) <= si(x2) && si(m[5]) <= si(y2)) {
                        if (remove) {
                            cellRemove(r, p[16] + byteIndex, at);
                            m[3] = 0;
                            --p[2];
                        }
                        activate(r, layer, at);
                        ++found;
                        if (bad(r))
                            return found;
                    }
                    at = next;
                }
                byteIndex += 8;
            }
        }
        index += p[3];
    }
    return found;
}
uint32_t stageActivate(Run &r, uint32_t grid, uint32_t x, uint32_t y) {
    auto *p = span(r, grid, 28);
    if (!p)
        return 0;
    if (p[26] == x && p[27] == y)
        return 0;
    p[26] = x;
    p[27] = y;
    uint32_t counts[3]{};
    for (uint32_t i = 0; i < 3; ++i) {
        const uint32_t half = 16 + i * 2;
        counts[i] = query(r, p[1 + i], x - p[half], y - p[half + 1], x + p[half], y + p[half + 1], 1);
        if (bad(r))
            return 0;
    }
    return counts[0] + counts[1] + counts[2];
}
uint32_t iteratorNext(Run &r, uint32_t *it) {
    uint32_t loops = 0;
    while (limit(r, ++loops)) {
        it[2] = it[3];
        if (!it[3]) {
            do {
                if (si(it[13]) < si(it[10])) {
                    ++it[12];
                    ++it[13];
                } else {
                    if (si(it[11]) <= si(it[14]))
                        return 0;
                    auto *layer = span(r, it[1], 17);
                    if (!layer)
                        return 0;
                    it[15] += layer[3];
                    it[12] = it[15];
                    it[13] = it[8];
                    ++it[14];
                }
                auto *layer = span(r, it[1], 17);
                if (!layer)
                    return 0;
                auto *cell = span(r, layer[16] + it[12] * 8, 2);
                if (!cell)
                    return 0;
                it[2] = cell[0];
                if (!limit(r, ++loops))
                    return 0;
            } while (!it[2]);
        }
        auto *m = span(r, it[2], 7);
        if (!m)
            return 0;
        it[3] = m[0];
        if (si(it[4]) <= si(m[4]) && si(it[5]) <= si(m[5]) && si(m[4]) <= si(it[6]) && si(m[5]) <= si(it[7])) {
            if (it[16]) {
                auto *layer = span(r, it[1], 17);
                if (!layer)
                    return 0;
                cellRemove(r, layer[16] + it[12] * 8, it[2]);
                m[3] = 0;
                --layer[2];
            }
            return it[2];
        }
        // Original nonmatching-member branch rereads the same current pointer; the
        // native safety bound explicitly represents that nontermination rather than
        // inventing an advance the original did not perform.
        while (limit(r, ++loops)) {
            m = span(r, it[2], 7);
            if (!m)
                return 0;
            it[3] = m[0];
            if (si(it[4]) <= si(m[4]) && si(it[5]) <= si(m[5]) && si(m[4]) <= si(it[6]) && si(m[5]) <= si(it[7]))
                return it[2];
        }
        return 0;
    }
    return 0;
}
uint32_t iteratorStart(Run &r, uint32_t *it, const uint32_t *a) {
    auto *p = span(r, a[0], 17);
    if (!p)
        return 0;
    it[4] = a[1];
    it[1] = a[0];
    it[5] = a[2];
    it[6] = a[3];
    it[7] = a[4];
    it[16] = a[5];
    if (si(p[12]) < si(it[4]) || si(it[6]) < si(p[10]) || si(p[13]) < si(it[5]) || si(it[7]) < si(p[11]))
        return 0;
    it[4] = uint32_t(std::max(si(it[4]), si(p[10])));
    it[6] = uint32_t(std::min(si(it[6]), si(p[12])));
    it[5] = uint32_t(std::max(si(it[5]), si(p[11])));
    it[7] = uint32_t(std::min(si(it[7]), si(p[13])));
    it[9] = sar(it[5] - p[11], p[6]);
    it[8] = sar(it[4] - p[10], p[5]);
    it[11] = sar(it[7] - p[11], p[6]);
    it[10] = sar(it[6] - p[10], p[5]);
    it[14] = it[9];
    it[13] = it[8];
    it[15] = p[3] * it[9] + it[8];
    it[12] = it[15];
    auto *cell = span(r, p[16] + it[12] * 8, 2);
    if (!cell)
        return 0;
    it[3] = cell[0];
    return iteratorNext(r, it);
}
uint32_t iterateLayer(Run &r, uint32_t grid, uint32_t layer, bool destroy) {
    auto *p = span(r, layer, 17);
    if (!p)
        return 0;
    uint32_t args[6] = {layer, p[10], p[11], p[12], p[13], 0}, it[17] = {0x513de0, 0, 0};
    uint32_t member = iteratorStart(r, it, args), count = 0;
    while (member) {
        auto *m = span(r, member, 7);
        if (!m)
            return count;
        uint32_t actor = m[6];
        if (destroy) {
            if (actor)
                destroyActor(r, actor);
            ++count;
        } else {
            auto *a = span(r, actor, 128);
            if (!a)
                return count;
            bool needed = bool(a[2] & 2);
            if (!needed) {
                auto *logic = span(r, a[27], 93);
                if (!logic)
                    return count;
                needed = bool(logic[2] & 4);
            }
            if (needed) {
                auto *g = span(r, grid, 28);
                if (!g)
                    return count;
                claw_scene_actor_insert(g[0], actor, r.h, r.fault);
                if (bad(r))
                    return count;
                cellRemove(r, m[3], member);
                m[3] = 0;
                --p[2];
                ++count;
            }
        }
        if (bad(r))
            return count;
        member = iteratorNext(r, it);
    }
    return count;
}
uint32_t iterateGrid(Run &r, uint32_t grid, bool destroy) {
    auto *p = span(r, grid, 28);
    if (!p)
        return 0;
    uint32_t count = 0;
    for (uint32_t i = 1; i <= 3; ++i) {
        if (destroy && !p[i])
            continue;
        count += iterateLayer(r, grid, p[i], destroy);
        if (bad(r))
            return count;
    }
    return count;
}
uint32_t stageResidency(Run &r, uint32_t grid, uint32_t x, uint32_t y) {
    auto *p = span(r, grid, 28);
    if (!p)
        return 0;
    const uint32_t hx[3] = {p[16], p[18], p[20]}, hy[3] = {p[17], p[19], p[21]}, container = p[0];
    auto *c = span(r, container, 11);
    if (!c)
        return 0;
    uint32_t at = c[5], changes = 0, loops = 0;
    while (at) {
        if (!limit(r, ++loops))
            return changes;
        auto *node = span(r, at, 3);
        if (!node)
            return changes;
        uint32_t actor = node[2], next = node[0];
        auto *a = span(r, actor, 128);
        if (!a)
            return changes;
        if ((a[2] & 0x40) && (si(x) < si(p[22] - 320) || si(p[24] + 320) < si(x) || si(y) < si(p[23] - 220) ||
                              si(p[25] + 220) < si(y))) {
            if (a[2] & 0x80000)
                actorCallback(r, actor, 29, false);
            sceneRemove(r, container + 16, at);
            destroyActor(r, actor);
            if (bad(r))
                return changes;
        }
        if (!(a[2] & 2) && (a[2] & 0x40000)) {
            uint32_t ax = a[19], ay = a[20];
            if (si(ax) < si(p[22]))
                ax = p[22];
            if (si(ay) < si(p[23]))
                ay = p[23];
            if (si(p[24]) <= si(ax))
                ax = p[24];
            if (si(p[25]) <= si(ay))
                ay = p[25];
            a[38] = ax;
            a[39] = ay;
            const uint32_t flags = a[2], i = (flags & 0x800000) ? 1 : (flags & 0x1000000) ? 2 : 0;
            uint32_t layer = p[1 + i];
            if (si(ax) < si(x - hx[i]) || si(ay) < si(y - hy[i]) || si(x + hx[i]) < si(ax) || si(y + hy[i]) < si(ay)) {
                if (!(flags & 0x20)) {
                    if (flags & 0x100000)
                        actorCallback(r, actor, 30, true);
                    sceneRemove(r, container + 16, at);
                    registerMember(r, layer, actor + 0x88);
                } else {
                    if (flags & 0x80000)
                        actorCallback(r, actor, 29, false);
                    sceneRemove(r, container + 16, at);
                    destroyActor(r, actor);
                }
                ++changes;
                if (bad(r))
                    return changes;
            }
        }
        at = next;
    }
    return changes;
}
void layerClear(Run &r, uint32_t layer) {
    auto *p = span(r, layer, 17);
    if (!p)
        return;
    if (p[1]) {
        uint32_t cells = p[16];
        if (cells)
            release(r, cells - 4);
        p[1] = 0;
    }
}
uint32_t layerDelete(Run &r, uint32_t layer, uint32_t flags) {
    auto *p = span(r, layer, 17);
    if (!p)
        return 0;
    p[0] = 0x513dc8;
    layerClear(r, layer);
    p[0] = 0x50becc;
    if (flags & 1)
        release(r, layer);
    return layer;
}
void gridClear(Run &r, uint32_t grid) {
    auto *p = span(r, grid, 28);
    if (!p)
        return;
    for (uint32_t i = 1; i <= 3; ++i)
        if (p[i]) {
            auto *l = span(r, p[i], 17);
            if (!l)
                return;
            uint32_t fn = vf(r, l[0], 4);
            if (bad(r))
                return;
            if (fn == 0x4d4a90)
                layerDelete(r, p[i], 1);
            else
                call(r, fn, p[i], {1});
            p[i] = 0;
            if (bad(r))
                return;
        }
}
uint32_t exponent(uint32_t x) {
    uint32_t n = 0;
    while (x > 1) {
        x >>= 1;
        ++n;
    }
    return n;
}
uint32_t layerConstruct(Run &r, uint32_t token, const uint32_t *a) {
    auto *p = span(r, token, 17);
    if (!p)
        return 0;
    p[2] = 0;
    std::copy_n(a, 4, p + 10);
    uint32_t left = a[0], right = a[2], top = a[1], bottom = a[3];
    if (si(right) < si(left))
        std::swap(left, right);
    if (si(bottom) < si(top))
        std::swap(top, bottom);
    p[8] = right - left;
    p[9] = bottom - top;
    if (si(a[4]) <= 0 || si(a[5]) <= 0) {
        fail(r, 2);
        return 0;
    }
    p[5] = exponent(a[4]);
    p[6] = exponent(a[5]);
    p[14] = 1u << p[5];
    p[15] = 1u << p[6];
    p[3] = uint32_t(si(p[8]) / si(p[14])) + 1;
    p[4] = uint32_t(si(p[9]) / si(p[15])) + 1;
    p[7] = p[3] * p[4];
    if (!limit(r, p[7]))
        return 0;
    uint32_t block = allocate(r, p[7] * 8 + 4);
    p[16] = 0;
    if (block) {
        auto *cells = span(r, block, p[7] * 2 + 1);
        if (!cells)
            return 0;
        cells[0] = p[7];
        std::fill_n(cells + 1, p[7] * 2, 0);
        p[16] = block + 4;
        p[1] = 1;
        return 1;
    }
    return 0;
}
void rectangles(uint32_t *p, const uint32_t *first, const uint32_t *second, const uint32_t *third) {
    const uint32_t *dims[] = {first, second, third};
    const uint32_t offsets[] = {4, 12, 8};
    for (uint32_t i = 0; i < 3; ++i) {
        uint32_t n = offsets[i];
        p[n] = p[n + 1] = 0;
        p[n + 2] = dims[i][0] - 1;
        p[n + 3] = dims[i][1] - 1;
        p[16 + i * 2] = uint32_t(si(dims[i][0]) / 2);
        p[17 + i * 2] = uint32_t(si(dims[i][1]) / 2);
    }
    p[26] = p[27] = 0xffffa932;
}
uint32_t gridConstruct(Run &r, uint32_t grid, const uint32_t *a) {
    auto *p = span(r, grid, 28);
    if (!p || !a[0])
        return 0;
    for (uint32_t i = 1; i <= 3; ++i) {
        uint32_t t = allocate(r, 0x44);
        if (t) {
            auto *l = span(r, t, 17);
            if (!l)
                return 0;
            l[1] = 0;
            l[0] = 0x513db0;
        }
        p[i] = t;
    }
    if (!p[1] || !p[2] || !p[3])
        return 0;
    auto *rect = span(r, a[1], 4);
    if (!rect)
        return 0;
    for (uint32_t i = 0; i < 3; ++i) {
        auto *dims = span(r, a[2 + i], 2);
        if (!dims)
            return 0;
        uint32_t args[6] = {rect[0], rect[1], rect[2], rect[3], dims[0], dims[1]};
        if (!layerConstruct(r, p[1 + i], args))
            return 0;
    }
    auto *d0 = span(r, a[5], 2);
    auto *d1 = span(r, a[6], 2);
    auto *d2 = span(r, a[7], 2);
    if (!d0 || !d1 || !d2)
        return 0;
    rectangles(p, d0, d1, d2);
    p[0] = a[0];
    std::copy_n(rect, 4, p + 22);
    return 1;
}
void planeResize(Run &r, uint32_t token) {
    auto *p = span(r, token, 45);
    if (!p || !p[44])
        return;
    auto *parent = span(r, p[3], 10);
    if (!parent || !parent[9])
        return;
    auto *world = span(r, parent[9], 56);
    auto *grid = span(r, p[44], 28);
    if (!world || !grid)
        return;
    rectangles(grid, world + 50, world + 52, world + 54);
}
uint32_t planeConstruct(Run &r, uint32_t token, uint32_t record, uint32_t count) {
    auto *p = span(r, token, 45);
    if (!p || !record)
        return 0;
    if (p[44]) {
        gridClear(r, p[44]);
        release(r, p[44]);
        if (bad(r))
            return 0;
    }
    uint32_t rect[4] = {0, 0, p[12] - 1, p[13] - 1};
    auto *parent = span(r, p[3], 10);
    if (!parent || !parent[2] || !parent[9])
        return 0;
    const uint32_t container = parent[2];
    auto *world = span(r, parent[9], 56);
    if (!world)
        return 0;
    uint32_t pairs[12];
    std::copy_n(world + 44, 12, pairs);
    uint32_t t = allocate(r, 0x70);
    if (t) {
        auto *grid = span(r, t, 28);
        if (!grid)
            return 0;
        std::fill_n(grid, 4, 0);
    }
    p[44] = t;
    if (!t) {
        fail(r, 2);
        return 0;
    }
    // Stack-local source rectangle/pairs are materialized directly; they are not
    // exposed as invented original heap identities.
    auto *grid = span(r, t, 28);
    if (!grid)
        return 0;
    for (uint32_t i = 1; i <= 3; ++i) {
        uint32_t l = allocate(r, 0x44);
        if (l) {
            auto *layer = span(r, l, 17);
            if (!layer)
                return 0;
            layer[1] = 0;
            layer[0] = 0x513db0;
        }
        grid[i] = l;
    }
    uint32_t ok = grid[1] && grid[2] && grid[3];
    if (ok)
        for (uint32_t i = 0; i < 3; ++i) {
            uint32_t args[6] = {rect[0], rect[1], rect[2], rect[3], pairs[i * 2], pairs[i * 2 + 1]};
            if (!layerConstruct(r, grid[i + 1], args)) {
                ok = 0;
                break;
            }
        }
    if (ok) {
        rectangles(grid, pairs + 6, pairs + 8, pairs + 10);
        grid[0] = container;
        std::copy_n(rect, 4, grid + 22);
    } else {
        gridClear(r, p[44]);
        release(r, p[44]);
        p[44] = 0;
        return 0;
    }
    if (si(count) < 1)
        return 1;
    if (!limit(r, count))
        return 0;
    for (uint32_t i = 0; si(i) < si(count); ++i) {
        uint32_t n = call(r, 0x4d17e0, token, {record});
        if (!n)
            return 0;
        record += n;
    }
    return 1;
}
} // namespace
uint32_t claw_spatial_grid_entry(uint32_t f, uint32_t receiver, ClawSpatialGridArguments args, ClawSceneActorHost h,
                                 uint32_t *fault, uint32_t *result) {
    Run r{h, fault};
    uint32_t value = 0;
    const uint32_t *a = args.words;
    uint32_t needed = 0;
    switch (f) {
    case 0x4d4890:
        needed = 8;
        break;
    case 0x4f48a0:
    case 0x4f4490:
        needed = 6;
        break;
    case 0x4f46b0:
        needed = 5;
        break;
    case 0x4f4860:
    case 0x4cb040:
    case 0x4d1620:
    case 0x4d4b50:
    case 0x4d4d10:
        needed = 2;
        break;
    case 0x4f4680:
    case 0x4cb0e0:
    case 0x4d51a0:
    case 0x4f4630:
    case 0x4d4a90:
        needed = 1;
        break;
    default:
        break;
    }
    if (args.count < needed) {
        fail(r, 2);
        return 1;
    }
    switch (f) {
    case 0x4d1fd0:
    case 0x4d2000: {
        auto *p = span(r, receiver, 45);
        if (p && p[44])
            value = f == 0x4d1fd0 ? stageActivate(r, p[44], truncFloat(p[4]), truncFloat(p[5]))
                                  : stageResidency(r, p[44], truncFloat(p[4]), truncFloat(p[5]));
        break;
    }
    case 0x4d4b50:
        value = stageActivate(r, receiver, a[0], a[1]);
        break;
    case 0x4d4d10:
        value = stageResidency(r, receiver, a[0], a[1]);
        break;
    case 0x4d51a0:
        registerActor(r, receiver, a[0]);
        break;
    case 0x4f4630:
        value = registerMember(r, receiver, a[0]);
        break;
    case 0x4f46b0:
        value = query(r, receiver, a[0], a[1], a[2], a[3], a[4]);
        break;
    case 0x4d2030: {
        auto *p = span(r, receiver, 45);
        if (p && p[44])
            value = iterateGrid(r, p[44], false);
        break;
    }
    case 0x4d4c40:
        value = iterateGrid(r, receiver, false);
        break;
    case 0x4d50e0:
        value = iterateGrid(r, receiver, true);
        break;
    case 0x4f4860:
    case 0x4f48a0: {
        auto *it = span(r, receiver, 17);
        if (!it)
            break;
        if (f == 0x4f48a0)
            value = iteratorStart(r, it, a);
        else {
            auto *p = span(r, a[0], 17);
            if (!p)
                break;
            uint32_t bounds[6] = {a[0], p[10], p[11], p[12], p[13], a[1]};
            value = iteratorStart(r, it, bounds);
        }
        break;
    }
    case 0x4f49c0: {
        auto *it = span(r, receiver, 17);
        if (it)
            value = iteratorNext(r, it);
        break;
    }
    case 0x4f4680: {
        auto *p = span(r, receiver, 17);
        auto *m = span(r, a[0], 7);
        if (!p || !m)
            break;
        cellRemove(r, m[3], a[0]);
        m[3] = 0;
        --p[2];
        break;
    }
    case 0x4f4490:
        value = layerConstruct(r, receiver, a);
        break;
    case 0x4d4890:
        value = gridConstruct(r, receiver, a);
        break;
    case 0x4d1620:
        value = planeConstruct(r, receiver, a[0], a[1]);
        break;
    case 0x4d2050:
        planeResize(r, receiver);
        break;
    case 0x4d4b00:
        gridClear(r, receiver);
        break;
    case 0x4d4a90:
        value = layerDelete(r, receiver, a[0]);
        break;
    case 0x4f45f0:
        layerClear(r, receiver);
        break;
    case 0x4cb040:
    case 0x4cb0e0: {
        auto *world = span(r, receiver, 56);
        if (!world)
            break;
        if (f == 0x4cb040) {
            world[4] = world[5] = 0;
            world[6] = a[0] - 1;
            world[7] = a[1] - 1;
        } else {
            auto *rect = span(r, a[0], 4);
            if (!rect)
                break;
            for (uint32_t i = 0; i < 4; ++i)
                world[4 + i] = rect[i];
        }
        constexpr uint32_t sizes[] = {500, 250, 1000, 1000, 250, 125, 1600, 1200, 2560, 1920, 768, 576};
        std::copy_n(sizes, 12, world + 44);
        value = 1;
        break;
    }
    default:
        return 0;
    }
    if (result)
        *result = value;
    return 1;
}
