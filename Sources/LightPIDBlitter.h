#ifndef CLAW_LIGHT_PID_BLITTER_H
#define CLAW_LIGHT_PID_BLITTER_H
#include "PIDBlitter.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawLightPIDBlitState {
    uint32_t renderWord, effectMode, effectValue, formatByte;
    //4c4c20 top-skip reads an unwritten local; caller supplies its original seed.
    uint32_t bothTopSkipSeed;
} ClawLightPIDBlitState;
typedef struct ClawLightPIDBlitTable {
    //Exact3-word table object:active,length,payloadToken; the pixel bodies read+8.
    //Null table pointer models compressed+1c==0, accepted without lock/writes.
    uint32_t words[3];
    const uint8_t *data;
    size_t capacity;
} ClawLightPIDBlitTable;
typedef struct ClawLightPIDBlitInfo {
    size_t consumed, writes;
    uint32_t lockCount, unlockCount;
} ClawLightPIDBlitInfo;
//Whole4bffa0 dispatch profile with frozen mode1 composition and exact mode2
//8-bit bodies. Modes4/8/22/50 are explicit unsupported boundaries here.
//scratch128 represents live original542bb0 bytes, including retained tail.
//Separate buffers must not alias. Native bounds validation rejects atomically;
//original dispatcher rejects also return0. Output/info/scratch remain untouched.
//Literal zero still writes via the source color table; transparent runs skip.
uint32_t claw_light_pid_blit8(const uint8_t *pid, size_t length, const ClawPIDBlitCommand *,
                              const ClawLightPIDBlitState *, const ClawLightPIDBlitTable *, uint8_t *output,
                              uint8_t *coverage, size_t capacity, size_t rowStride, uint8_t *scratch128,
                              ClawLightPIDBlitInfo *);
#ifdef __cplusplus
}
#endif
#endif
