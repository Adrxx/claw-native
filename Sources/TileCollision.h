#ifndef CLAW_TILE_COLLISION_H
#define CLAW_TILE_COLLISION_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t type, width, height, insideAttribute, outsideAttribute;
    int32_t left, top, right, bottom;
} ClawTileDescription;
uint32_t claw_tile_attribute(const ClawTileDescription *tile, int32_t x, int32_t y);
uint32_t claw_world_point_attribute(const uint32_t *cells, const uint32_t *rowOffsets, int32_t pixelWidth,
                                    int32_t pixelHeight, uint32_t shiftX, uint32_t shiftY,
                                    const ClawTileDescription *descriptions, uint32_t descriptionCount, uint32_t actorX,
                                    uint32_t actorY, uint32_t bottomOffset, uint32_t xOffset);
#ifdef __cplusplus
}
#endif
#endif
