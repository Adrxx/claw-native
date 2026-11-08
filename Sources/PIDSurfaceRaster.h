#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t width, height;
    int32_t offsetX, offsetY;
    size_t consumed;
    uint32_t colorKeyEnabled;
} ClawPIDSurfaceRasterInfo;
// Original 8-bit uncompressed PID surface raster (flag 0x20 absent).
// useColorKey corresponds to original image-loader parameter 4. The 8-bit
// original color key is index zero; it is enabled only if flags & 1 and this
// parameter is nonzero. Every source pixel is decoded, even a keyed index zero.
// output/coverage must be independent, nonaliasing buffers; stride >= width.
// Coverage is zero only for an enabled color key matching index zero, else one.
// Width must be divisible by four, as required by original 0x4bf310.
// Return 1 on success; failure leaves all outputs/info untouched. Bounded
// malformed-input rejection is a native extension, not original unsafe parity.
uint32_t claw_pid_decode_surface_raster8(const uint8_t *pid, size_t length, uint32_t useColorKey, uint8_t *output,
                                         uint8_t *coverage, size_t capacity, size_t rowStride,
                                         ClawPIDSurfaceRasterInfo *info);
#ifdef __cplusplus
}
#endif
