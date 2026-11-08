#ifndef CLAW_PAPER_ROLL_RUNTIME_H
#define CLAW_PAPER_ROLL_RUNTIME_H
#include "PlayerFadeBlendRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_PAPER_ROLL_BYTES 0x494u
#define CLAW_PAPER_ROLL_DESCRIPTOR_BYTES 52u
typedef struct ClawPaperRollContext {
    ClawPlayerFadeBlendContext *common;
    /* Caller-owned synchronous scratch:52-byte descriptor,64-byte formatted
    resource name,4-byte lookup output,4-byte by-value CString. No source heap
    allocation or independent time/RNG identity is implied. */
    uint32_t descriptorToken, nameToken, lookupToken, stringToken, maximumOperations;
    /* Live original532c0c/532c10 aliases supplied by the host. */
    uint32_t *soundEnabled, *soundVolume;
    /* Optional exact byte spans for non-word-sized physical buffers. */
    void *byteContext;
    uint8_t *(*bytes)(void *, uint32_t token, uint32_t byteCount);
} ClawPaperRollContext;
/* Same raw SceneActorHost and rich six-argument dependency as the frozen fade
   runner. Recognized complete entries return1 only with common->fade->fault0;
   result is separate meaningful EAX. Physical surfaces/PCX/resource/palette,
   CString transport and optional generated table routines retain exact calls.
   No opacity, host sleep, copied PCX codec or fake device success is supplied.
   Source factory4ec050 is supported only for type0. Local descriptor differs
   from the frozen36-byte circle descriptor; do not share their scratch spans.
   Fault1 missing graph/service,2 bounded unsafe/ABI/stalled domain,3 missing
   source profile. Guards preserve the reached prefix, not an original exit. */
uint32_t claw_paper_roll_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                               ClawPaperRollContext *, ClawPlayerFadeDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
