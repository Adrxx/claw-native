#include "SpriteGeometry.h"

static bool less(uint32_t a, uint32_t b) {
    return (a ^ 0x80000000u) < (b ^ 0x80000000u);
}
static uint32_t maxSigned(uint32_t a, uint32_t b) {
    return less(a, b) ? b : a;
}
static uint32_t minSigned(uint32_t a, uint32_t b) {
    return less(a, b) ? a : b;
}

extern "C" void claw_sprite_set_geometry(ClawSpriteGeometry *g, uint32_t w, uint32_t h, uint32_t ox, uint32_t oy) {
    g->width = w;
    g->height = h;
    g->halfWidth = (w >> 1) | (w & 0x80000000u);
    g->halfHeight = (h >> 1) | (h & 0x80000000u);
    g->offsetX = ox;
    g->offsetY = oy;
}

extern "C" uint32_t claw_sprite_relative_bounds(const ClawSpriteGeometry *g, ClawSpriteRect *r) {
    if (!g)
        return 0;
    *r = {g->offsetX - g->halfWidth, g->offsetY - g->halfHeight, g->offsetX + g->halfWidth - 1u,
          g->offsetY + g->halfHeight - 1u};
    return 1;
}

static void wrap(uint32_t &p, uint32_t extent, uint32_t camera, uint32_t visibleEnd) {
    if (less(p, 0))
        p += extent;
    else if (!less(p, extent))
        p -= extent;
    if (!less(visibleEnd, extent) && less(p, camera) && !less(visibleEnd - extent, p))
        p += extent;
}
extern "C" void claw_sprite_project(const ClawSpriteProjection *p, uint32_t *x, uint32_t *y) {
    if (p->flags & 4u)
        wrap(*x, p->extentX, p->cameraX, p->visibleEndX);
    if (p->flags & 8u)
        wrap(*y, p->extentY, p->cameraY, p->visibleEndY);
    *x = *x - p->cameraX + p->screenOffsetX;
    *y = *y - p->cameraY + p->screenOffsetY;
}

extern "C" void claw_sprite_prepare_draw(const ClawSpriteGeometry *g, ClawSpriteDrawActor *a, ClawSpriteDrawContext *c,
                                         ClawSpriteDrawCommand *out) {
    *out = {};
    uint32_t flags = a->renderFlags;
    if (flags & 1u) {
        a->drawStatus = 0xffffffffu;
        return;
    }
    if (flags & 8u) {
        if (c->animationDelta < a->blinkRemaining)
            a->blinkRemaining -= c->animationDelta;
        else {
            a->blinkRemaining = a->blinkInterval;
            a->renderFlags = flags ^ 0x10000000u;
        }
        flags = a->renderFlags;
        if (!(flags & 0x10000000u)) {
            a->drawStatus = 0xffffffffu;
            return;
        }
    }
    const bool flipX = flags & 2u, flipY = flags & 4u;
    uint32_t x = a->x - g->halfWidth;
    uint32_t y = a->y - g->halfHeight;
    x = flipX ? x - a->displacementX - g->offsetX : x + a->displacementX + g->offsetX;
    y = flipY ? y - a->displacementY - g->offsetY : y + a->displacementY + g->offsetY;
    if (a->flags & 0x40000u)
        claw_sprite_project(&c->projection, &x, &y);
    const ClawSpriteRect full = {x, y, x + g->width - 1u, y + g->height - 1u};
    const ClawSpriteRect clip =
        a->flags & 0x40000u
            ? c->worldClip
            : (a->clip.left == 0x80000000u ? ClawSpriteRect{0, 0, c->width - 1u, c->height - 1u} : a->clip);
    const ClawSpriteRect dst = {maxSigned(full.left, clip.left), maxSigned(full.top, clip.top),
                                minSigned(full.right, clip.right), minSigned(full.bottom, clip.bottom)};
    const uint32_t w = dst.right - dst.left + 1u, h = dst.bottom - dst.top + 1u;
    if (!less(0, w) || !less(0, h)) {
        a->drawStatus = 0xffffffffu;
        return;
    }
    uint32_t sourceX, sourceY;
    if (g->compressed) {
        // Original compressed x-only path passes left cropping to its pixel blitter,
        // unlike the surface x-only path, which passes right cropping.
        sourceX = flipX && flipY ? full.right - dst.right : dst.left - full.left;
        sourceY = flipY ? full.bottom - dst.bottom : dst.top - full.top;
        out->kind = 3;
        out->receiverToken = g->compressedToken;
        out->sourceToken = c->surfaceToken;
        out->source = {sourceX, sourceY, sourceX + w - 1u, sourceY + h - 1u};
        out->destination = dst;
    } else {
        sourceX = flipX ? full.right - dst.right : dst.left - full.left;
        sourceY = flipY ? full.bottom - dst.bottom : dst.top - full.top;
        out->kind = flipX || flipY ? 2u : 1u;
        out->receiverToken = c->surfaceToken;
        out->sourceToken = g->surfaceToken;
        out->surfaceKind = g->surfaceKind;
        out->source = {sourceX, sourceY, sourceX + w, sourceY + h};
        out->destination = {dst.left, dst.top, dst.right + 1u, dst.bottom + 1u};
        if (out->kind == 2)
            c->directDrawFlip = (flipX ? 2u : 0u) | (flipY ? 4u : 0u);
    }
    out->flipX = flipX;
    out->flipY = flipY;
    a->drawX = dst.left;
    a->drawY = dst.top;
    a->drawn = dst;
    a->drawWidth = w;
    a->drawHeight = h;
    a->drawStatus = 0;
}
