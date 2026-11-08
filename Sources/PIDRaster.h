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
} ClawPIDRasterInfo;
// Decode compressed PID (flag 0x20), using original palette-index run semantics.
// output/coverage are independent byte planes; rowStride must be >= width.
// Coverage is 0 for skipped transparent pixels, 1 for literal pixels (including index zero).
// Returns 1 on success, 0 for unsupported/truncated/malformed input or insufficient buffer.
// First validates the entire raster, so failure leaves info/output/coverage untouched.
// Original unsafe malformed-input behavior, palette conversion and pixel blit clipping are not claimed.
uint32_t claw_pid_decode_raster8(const uint8_t *pid, size_t length, uint8_t *output, uint8_t *coverage, size_t capacity,
                                 size_t rowStride, ClawPIDRasterInfo *info);
#ifdef __cplusplus
}
#endif
