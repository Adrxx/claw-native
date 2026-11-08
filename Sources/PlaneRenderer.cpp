#include "PlaneRenderer.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawPlaneRendererHost h;
    uint32_t *fault;
    uint32_t error = 0, visits = 0;
};
int32_t si(uint32_t v) {
    int32_t x;
    std::memcpy(&x, &v, 4);
    return x;
}
void fail(Run &r, uint32_t code = 1) {
    r.error = code;
    if (r.fault)
        *r.fault = code;
}
bool bad(Run &r) {
    return r.error || (r.fault && *r.fault);
}
bool visit(Run &r) {
    if (++r.visits > 1000000) {
        fail(r, 2);
        return false;
    }
    return true;
}
uint32_t *span(Run &r, uint32_t token, uint32_t count) {
    if (!r.h.scene.lookup) {
        fail(r);
        return nullptr;
    }
    auto *p = r.h.scene.lookup(r.h.scene.context, token, count);
    if (!p)
        fail(r);
    return p;
}
uint32_t word(Run &r, uint32_t token) {
    auto *p = span(r, token, 1);
    return p ? *p : 0;
}
uint32_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args) {
    if (!r.h.scene.call) {
        fail(r);
        return 0;
    }
    ClawSceneActorCall c{};
    c.function = f;
    c.receiver = receiver;
    c.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), c.arguments);
    return r.h.scene.call(r.h.scene.context, c);
}
uint32_t virtualEntry(Run &r, uint32_t token, uint32_t offset) {
    const uint32_t vt = word(r, token);
    if (bad(r))
        return 0;
    if (vt == 0x5137f0 && offset == 0x2c)
        return 0x4c9e00;
    if (vt == 0x513c20 && offset == 0x28)
        return 0x4c91d0;
    if (vt == 0x513a70 && offset == 0x38)
        return 0x4d2890;
    return word(r, vt + offset);
}
void actor(Run &r, uint32_t token, uint32_t target) {
    uint32_t fn = virtualEntry(r, token, 0x2c);
    if (bad(r))
        return;
    if (fn == 0x4c9e00) {
        auto *a = span(r, token, 128);
        if (!a)
            return;
        if (a[0x174 / 4]) {
            uint32_t f = virtualEntry(r, a[0x174 / 4], 0x38);
            if (!bad(r))
                call(r, f, a[0x174 / 4], {token, target});
        }
    } else
        call(r, fn, token, {target});
}
void actors(Run &r, uint32_t token, uint32_t target) {
    uint32_t fn = virtualEntry(r, token, 0x28);
    if (bad(r))
        return;
    if (fn != 0x4c91d0) {
        call(r, fn, token, {target});
        return;
    }
    auto *c = span(r, token, 6);
    if (!c)
        return;
    uint32_t at = c[5];
    while (at && visit(r)) {
        auto *n = span(r, at, 3);
        if (!n)
            return;
        uint32_t next = n[0];
        actor(r, n[2], target);
        if (bad(r))
            return;
        at = next;
    }
}
void graphics(Run &r, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> args, uint32_t *rectangle,
              uint32_t token = 0) {
    if (!r.h.graphics) {
        fail(r);
        return;
    }
    ClawPlaneGraphicsCall c{};
    c.function = function;
    c.receiver = receiver;
    c.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), c.arguments);
    c.rectangleToken = token;
    c.rectangle = rectangle;
    r.h.graphics(r.h.graphicsContext, c);
}
void tile(Run &r, uint32_t plane, uint32_t *p, uint32_t receiver, uint32_t index, uint32_t x, uint32_t y,
          uint32_t *rect, uint32_t rectToken = 0) {
    if (!visit(r))
        return;
    const uint32_t value = word(r, p[8] + index * 4);
    if (bad(r) || value == 0xffffffff)
        return;
    if (value == 0xeeeeeeee) {
        uint32_t destination[4] = {x, y, x + (rect[2] - rect[0]), y + (rect[3] - rect[1])};
        graphics(r, 0x4b9ce0, receiver, {0, 0, 0x1000400, plane + 0xf4}, destination);
        return;
    }
    const uint32_t manager = word(r, p[0xa0 / 4] + (value >> 16) * 4);
    if (bad(r))
        return;
    auto *m = span(r, manager, 27);
    if (!m)
        return;
    const uint32_t id = value & 0xffff;
    uint32_t image = 0;
    if (si(m[0x64 / 4]) <= si(id) && si(id) <= si(m[0x68 / 4]))
        image = word(r, m[0x14 / 4] + id * 4);
    if (bad(r))
        return;
    // Original dereferences a null image after an out-of-range/missing lookup.
    if (!image) {
        fail(r);
        return;
    }
    auto *imageWords = span(r, image, 12);
    if (!imageWords)
        return;
    graphics(r, 0x4b9d80, receiver, {x, y, imageWords[0x2c / 4], imageWords[0x28 / 4]}, rect, rectToken);
}
void plane(Run &r, uint32_t token, uint32_t target) {
    auto *p = span(r, token, 86);
    if (!p || p[2] & 2)
        return;
    const uint32_t sx = p[0x8c / 4] & 31, sy = p[0x90 / 4] & 31, firstCol = uint32_t(si(p[16]) >> sx),
                   nextCol = firstCol + 1, firstRow = uint32_t(si(p[17]) >> sy), nextRow = firstRow + 1;
    const uint32_t firstWidth = (nextCol << sx) - p[16], firstHeight = (nextRow << sy) - p[17],
                   lastCol = uint32_t(si(p[18]) >> sx), lastRow = uint32_t(si(p[19]) >> sy),
                   lastWidth = p[18] - (lastCol << sx) + 1, lastHeight = p[19] - (lastRow << sy) + 1,
                   middleCols = lastCol - firstCol - 1, middleRows = lastRow - firstRow - 1;
    uint32_t topLeft[4] = {p[14] - firstWidth, p[15] - firstHeight, p[14], p[15]},
             topMiddle[4] = {0, p[15] - firstHeight, p[14], p[15]},
             middleLeft[4] = {p[14] - firstWidth, 0, p[14], p[15]}, middleRight[4] = {0, 0, lastWidth, p[15]};
    const uint32_t receiver = word(r, target + 0x2c);
    if (bad(r))
        return;
    uint32_t y = p[21], rowOffset = word(r, p[9] + firstRow * 4), x = p[20];
    if (bad(r))
        return;
    tile(r, token, p, receiver, rowOffset + firstCol, x, y, topLeft);
    if (bad(r))
        return;
    x += firstWidth;
    uint32_t col = nextCol;
    if (si(p[10]) <= si(col))
        col = 0;
    for (uint32_t n = middleCols; si(n) > 0; --n) {
        tile(r, token, p, receiver, rowOffset + col, x, y, topMiddle);
        if (bad(r))
            return;
        x += p[14];
        ++col;
        if (si(p[10]) <= si(col))
            col = 0;
    }
    topLeft[2] = lastWidth;
    topLeft[3] = p[15];
    topLeft[1] = p[15] - firstHeight;
    topLeft[0] = 0;
    tile(r, token, p, receiver, rowOffset + col, x, y, topLeft);
    if (bad(r))
        return;
    y += firstHeight;
    uint32_t row = nextRow;
    if (si(p[11]) <= si(row))
        row = 0;
    for (uint32_t n = middleRows; si(n) > 0; --n) {
        x = p[20];
        rowOffset = word(r, p[9] + row * 4);
        if (bad(r))
            return;
        tile(r, token, p, receiver, rowOffset + firstCol, x, y, middleLeft);
        if (bad(r))
            return;
        x += firstWidth;
        col = nextCol;
        if (si(p[10]) <= si(col))
            col = 0;
        for (uint32_t j = middleCols; si(j) > 0; --j) {
            tile(r, token, p, receiver, rowOffset + col, x, y, p + 0x60 / 4, token + 0x60);
            if (bad(r))
                return;
            x += p[14];
            ++col;
            if (si(p[10]) <= si(col))
                col = 0;
        }
        tile(r, token, p, receiver, rowOffset + col, x, y, middleRight);
        if (bad(r))
            return;
        y += p[15];
        ++row;
        if (si(p[11]) <= si(row))
            row = 0;
    }
    topLeft[2] = p[14];
    uint32_t bottomMiddle[4] = {0, 0, p[14], lastHeight};
    x = p[20];
    rowOffset = word(r, p[9] + row * 4);
    if (bad(r))
        return;
    topLeft[0] = p[14] - firstWidth;
    topLeft[3] = lastHeight;
    topLeft[1] = 0;
    tile(r, token, p, receiver, rowOffset + firstCol, x, y, topLeft);
    if (bad(r))
        return;
    x += firstWidth;
    col = nextCol;
    if (si(p[10]) <= si(col))
        col = 0;
    for (uint32_t n = middleCols; si(n) > 0; --n) {
        tile(r, token, p, receiver, rowOffset + col, x, y, bottomMiddle);
        if (bad(r))
            return;
        x += p[14];
        ++col;
        if (si(p[10]) <= si(col))
            col = 0;
    }
    topLeft[0] = topLeft[1] = 0;
    topLeft[2] = lastWidth;
    topLeft[3] = lastHeight;
    tile(r, token, p, receiver, rowOffset + col, x, y, topLeft);
}
void world(Run &r, uint32_t token, uint32_t target, uint32_t scene) {
    auto *w = span(r, token, 25);
    if (!w)
        return;
    uint32_t first = 0;
    if ((w[2] & 1) && scene + 16) {
        if (si(w[15]) > 0)
            first = word(r, w[14]);
        if (bad(r))
            return;
    }
    if (first) {
        uint32_t p0 = si(w[15]) > 0 ? word(r, w[14]) : 0;
        if (bad(r))
            return;
        plane(r, p0, target);
        if (bad(r))
            return;
        uint32_t count = w[15];
        auto *c = span(r, scene, 6);
        if (!c)
            return;
        uint32_t at = c[5];
        for (uint32_t i = 1; si(i) < si(count) && visit(r); ++i) {
            uint32_t pt = si(i) >= 0 && si(i) < si(count) ? word(r, w[14] + i * 4) : 0;
            const uint32_t z = word(r, pt + 0x80);
            if (bad(r))
                return;
            bool stopped = false;
            while (at && !stopped && visit(r)) {
                uint32_t saved = at;
                auto *n = span(r, at, 3);
                if (!n)
                    return;
                at = n[0];
                auto *a = span(r, n[2], 128);
                if (!a)
                    return;
                if (si(a[25]) >= si(z)) {
                    at = saved;
                    stopped = true;
                } else
                    actor(r, n[2], target);
                if (bad(r))
                    return;
            }
            pt = si(i) >= 0 && si(i) < si(w[15]) ? word(r, w[14] + i * 4) : 0;
            if (bad(r))
                return;
            plane(r, pt, target);
            if (bad(r))
                return;
            count = w[15];
        }
        while (at && visit(r)) {
            auto *n = span(r, at, 3);
            if (!n)
                return;
            uint32_t next = n[0];
            actor(r, n[2], target);
            if (bad(r))
                return;
            at = next;
        }
        return;
    }
    uint32_t i = 0;
    while (si(i) <= si(w[24]) && visit(r)) {
        uint32_t p0 = word(r, w[14] + i * 4);
        if (bad(r))
            return;
        plane(r, p0, target);
        if (bad(r))
            return;
        ++i;
    }
    actors(r, scene, target);
    if (bad(r))
        return;
    i = w[24] + 1;
    while (si(i) < si(w[15]) && visit(r)) {
        uint32_t p0 = word(r, w[14] + i * 4);
        if (bad(r))
            return;
        plane(r, p0, target);
        if (bad(r))
            return;
        ++i;
    }
}
} // namespace
uint32_t claw_plane_renderer_draw(uint32_t planeToken, uint32_t target, ClawPlaneRendererHost h, uint32_t *fault) {
    Run r{h, fault};
    plane(r, planeToken, target);
    return !bad(r);
}
uint32_t claw_plane_renderer_world(uint32_t worldToken, uint32_t target, uint32_t scene, ClawPlaneRendererHost h,
                                   uint32_t *fault) {
    Run r{h, fault};
    world(r, worldToken, target, scene);
    return !bad(r);
}

uint32_t claw_plane_renderer_actor(uint32_t token, uint32_t target, ClawPlaneRendererHost h, uint32_t *fault) {
    Run r{h, fault};
    actor(r, token, target);
    return !bad(r);
}

uint32_t claw_plane_renderer_actor_list(uint32_t token, uint32_t target, ClawPlaneRendererHost h, uint32_t *fault) {
    Run r{h, fault};
    actors(r, token, target);
    return !bad(r);
}
