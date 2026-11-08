#ifndef CLAW_EFFECT_PID_BLITTER_H
#define CLAW_EFFECT_PID_BLITTER_H
#include "LightPIDBlitter.h"
#ifdef __cplusplus
extern "C" {
#endif
//Original4bffa0 eight-bit modes4/8/22/50; frozenLightPID handles1/2.
//Same raw state/table/command/info ABI. Mode50 reverse branch reads retained
//scratch[count+1], so full caller scratch requires129bytes, not128.
//Mode4/8 table capacity is its actual mapped size; mode50 uses source512byte
//rank/inverse table. Mode22 requires table object presence, but not a payload.
//Tableobject active/length fields remain ignored by source pixel bodies.
//Buffers must be separate; bounds/malformed rejection is native atomic safety.
//Return0 rejects; all buffers/info untouched. Unknown modes/depths unsupported.
uint32_t claw_effect_pid_blit8(const uint8_t *pid, size_t length, const ClawPIDBlitCommand *,
                               const ClawLightPIDBlitState *, const ClawLightPIDBlitTable *, uint8_t *output,
                               uint8_t *coverage, size_t capacity, size_t rowStride, uint8_t *scratch,
                               size_t scratchCapacity, ClawLightPIDBlitInfo *);
#ifdef __cplusplus
}
#endif
#endif
