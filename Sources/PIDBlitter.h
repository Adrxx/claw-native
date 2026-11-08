#pragma once
#include <stdint.h>
#include <stddef.h>
#include "ClawRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    int32_t left, top, right, bottom;
} ClawPIDBlitRect;
typedef struct {
    ClawPIDBlitRect destination, source;
    uint32_t flipX, flipY;
    // Original 0x4c0cc0 initializes a skip counter with this pointer value.
    // Use the observed 32-bit original address, or a normal positive token
    // > image width (e.g. 0x01003000) for the usual original-address case.
    uint32_t originalSourceRectAddress;
} ClawPIDBlitCommand;
typedef struct {
    size_t consumed, writes;
} ClawPIDBlitInfo;
// Full compressed PID, eight-bit destination. Reproduces original 0x4bffa0
// dispatch and four pixel loops including their clipping/off-by-one quirks.
// Destination coordinates address the buffer's logical origin. All actual
// byte addresses must fall within capacity; pitch padding may be written.
// coverage may be null; otherwise literal writes set it to 1, skips preserve it.
// Input/output/coverage must not alias. Info may be null. Return 1 on success;
// return 0 on original dispatcher rejection or bounded native safety rejection.
// Failure leaves every output untouched. Safe dimensions/stream checks extend
// the original; no malformed-input, other bit depths or DirectDraw parity claim.
uint32_t claw_pid_blit8(const uint8_t *pid, size_t length, const ClawPIDBlitCommand *command, uint8_t *output,
                        uint8_t *coverage, size_t capacity, size_t rowStride, ClawPIDBlitInfo *info);
// Canonical raw 0x4c00b0, thiscall3(destination RECT, surface, source RECT),
// semantic void. Eight-bit valid nonaliasing streams and safe spans only;
// unsupported or unsafe inputs fault through ClawHost. Physical lock/unlock
// remain explicit services. Native display election is a separate join.
uint32_t claw_pid_blitter_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                 uint32_t argumentCount, ClawHost *host, uint32_t *result);
#ifdef __cplusplus
}
#endif
