#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t left, top, right, bottom;
} ClawSpriteRect;
typedef struct {
    uint32_t width, height, halfWidth, halfHeight, offsetX, offsetY;
    uint32_t compressed, surfaceToken, compressedToken, surfaceKind;
} ClawSpriteGeometry;
typedef struct {
    uint32_t flags, extentX, extentY, cameraX, cameraY, visibleEndX, visibleEndY, screenOffsetX, screenOffsetY;
} ClawSpriteProjection;
typedef struct {
    uint32_t flags, x, y, displacementX, displacementY, renderFlags, blinkRemaining, blinkInterval;
    ClawSpriteRect clip;
    uint32_t drawX, drawY;
    ClawSpriteRect drawn;
    uint32_t drawWidth, drawHeight, drawStatus;
} ClawSpriteDrawActor;
typedef struct {
    uint32_t width, height, surfaceToken, animationDelta, directDrawFlip;
    ClawSpriteRect worldClip;
    ClawSpriteProjection projection;
} ClawSpriteDrawContext;
typedef struct {
    uint32_t kind; // 0 no draw, 1 unflipped surface, 2 flipped surface, 3 compressed PID.
    uint32_t receiverToken, sourceToken, surfaceKind, flipX, flipY;
    ClawSpriteRect destination, source; // inclusive for compressed, exclusive for surface calls.
} ClawSpriteDrawCommand;

// Geometry field stores from PID image loaders 0x4d2410/0x4d25e0, after resource/decode setup.
// Does not load pixels, allocate a surface or alter token/kind fields.
void claw_sprite_set_geometry(ClawSpriteGeometry *, uint32_t width, uint32_t height, uint32_t offsetX,
                              uint32_t offsetY);

// Complete original v1.0 0x4061e0. Null image leaves the supplied rectangle untouched.
uint32_t claw_sprite_relative_bounds(const ClawSpriteGeometry *, ClawSpriteRect *);
// Complete original v1.0 0x4c96d0, including its one-period wrapping behavior.
void claw_sprite_project(const ClawSpriteProjection *, uint32_t *x, uint32_t *y);
// Original 0x4d2890 dispatcher and its seven geometry paths, with blits exposed as commands.
// Pixel blitters/DirectDraw are not implemented or claimed by this interface.
void claw_sprite_prepare_draw(const ClawSpriteGeometry *, ClawSpriteDrawActor *, ClawSpriteDrawContext *,
                              ClawSpriteDrawCommand *);
#ifdef __cplusplus
}
#endif
