#include "TileCollision.h"

extern "C" uint32_t claw_tile_attribute(const ClawTileDescription *t, int32_t x, int32_t y) {
    if (t->type == 1)
        return t->insideAttribute; // original 0x4cddc0
    if (t->type == 2) {            // original 0x4cde10: signed, inclusive rectangle
        return x >= t->left && x <= t->right && y >= t->top && y <= t->bottom ? t->insideAttribute
                                                                              : t->outsideAttribute;
    }
    return 0; // Native loader rejects unsupported types before gameplay.
}

extern "C" uint32_t claw_world_point_attribute(const uint32_t *cells, const uint32_t *rowOffsets, int32_t width,
                                               int32_t height, uint32_t shiftX, uint32_t shiftY,
                                               const ClawTileDescription *descriptions, uint32_t count, uint32_t actorX,
                                               uint32_t actorY, uint32_t bottomOffset, uint32_t xOffset) {
    if (!cells || !rowOffsets || !descriptions || width <= 0 || height <= 0 || shiftX > 30 || shiftY > 30)
        return 0;
    // Original 0x4cd740 adds with wrapping, then clamps signed coordinates.
    int32_t x = int32_t(actorX + xOffset), y = int32_t(actorY + bottomOffset);
    if (x < 0)
        x = 0;
    else if (x >= width)
        x = width - 1;
    if (y < 0)
        y = 0;
    else if (y >= height)
        y = height - 1;
    const uint32_t column = uint32_t(x) >> shiftX, row = uint32_t(y) >> shiftY;
    const uint32_t cell = cells[rowOffsets[row] + column];
    if (cell == 0xffffffff || cell == 0xeeeeeeee)
        return 0;
    const uint32_t id = cell & 0xffff;
    if (id >= count)
        return 0; // Native bounds extension, not original malformed-input parity.
    const int32_t localX = x - int32_t(column << shiftX), localY = y - int32_t(row << shiftY);
    return claw_tile_attribute(descriptions + id, localX, localY);
}
