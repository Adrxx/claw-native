#pragma once
#include <stddef.h>
#include <stdint.h>
#include "PIDBlitter.h"
#include "EffectPIDBlitter.h"
#ifdef __cplusplus
extern "C" {
#endif

// Native presentation adaptation, not a recovered original-game routine.
// Owns malloc-allocated straight-alpha RGBA bytes. Dispose or transfer their
// ownership exactly once. On rejection/no visible writes all fields are zero.
typedef struct {
    uint8_t *rgba;
    size_t byteCount;
    uint32_t left, top, width, height;
} ClawNativeIndexedImage;

// Calls the unchanged recovered blitter, then scans EVERY visible covered
// pixel, including stores outside the advertised destination rectangle.
// Padding columns do not become screen pixels. Coverage makes literal zero
// opaque; untouched pixels in the cropped output remain transparent black.
uint32_t claw_native_indexed_present8(const uint8_t *pid, size_t length, const ClawPIDBlitCommand *command,
                                      const uint8_t *paletteRGB, size_t paletteLength, uint32_t viewportWidth,
                                      uint32_t viewportHeight, ClawNativeIndexedImage *result);
void claw_native_indexed_image_dispose(ClawNativeIndexedImage *image);

//Persistent native eight-bit framebuffer transport. The source effect bodies
//read existing destination indices and retain all129 scratch bytes across draws.
//Presentation copies every visible covered write, including neighboring rows.
uint32_t claw_native_indexed_composite8(const uint8_t *pid, size_t length, const ClawPIDBlitCommand *command,
                                        const ClawLightPIDBlitState *state, const ClawLightPIDBlitTable *table,
                                        uint8_t *indices, uint8_t *coverage, size_t capacity, size_t stride,
                                        uint8_t *scratch, size_t scratchCapacity, const uint8_t *paletteRGB,
                                        size_t paletteLength, uint32_t width, uint32_t height,
                                        ClawLightPIDBlitInfo *info, ClawNativeIndexedImage *result);

//Physical DD surface-copy/fill adapters, separate from recovered pixel bodies.
uint32_t claw_native_indexed_surface8(const uint8_t *source, size_t sourceCapacity, uint32_t sourceWidth,
                                      uint32_t sourceHeight, const ClawPIDBlitCommand *command, uint32_t keyEnabled,
                                      uint8_t *indices, size_t capacity, size_t stride, uint32_t width,
                                      uint32_t height);
uint32_t claw_native_indexed_fill8(const ClawPIDBlitRect *rectangle, uint32_t color, uint8_t *indices, size_t capacity,
                                   size_t stride, uint32_t width, uint32_t height);
//Physical display-palette conversion over an already drawn complete frame.
uint32_t claw_native_indexed_frame_present8(const uint8_t *indices, size_t capacity, size_t stride,
                                            const uint8_t *paletteRGB, size_t paletteLength, uint32_t width,
                                            uint32_t height, ClawNativeIndexedImage *result);

#ifdef __cplusplus
}
#endif
