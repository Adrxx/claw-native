#ifndef CLAW_WARP_FADE_RUNTIME_H
#define CLAW_WARP_FADE_RUNTIME_H
#include "PlayerFadeBlendRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_WARP_FADE_BYTES 0x7d5cu
#define CLAW_WARP_FADE_WORDS (CLAW_WARP_FADE_BYTES / 4u)
typedef struct ClawWarpFadeContext {
    //Same caller-owned raw scene heap, clock, global bypass alias and CString
    //scratch as frozen circle fade; no independent clock or random seed.
    ClawPlayerFadeBlendContext *common;
    //Native diagnostics only.0 uses1M loop operations per public call.
    uint32_t maximumOperations;
} ClawWarpFadeContext;
//Raw original entries4ed060 ctor,4ed0b0(descriptor5words),4ed1a0(step),
//4ed5d0 maximum,4ed080(deleteFlags),4ed0a0 base destructor;
//4ec050 only type2(type,descriptorOr0),4ecc00 descriptor constructor;
//4efb00 cdecl(output,low,high,initial),4efc40 cdecl(candidate).
//Whole common runner4ec9c0 and removal4ec600 compose frozenPlayerFadeRuntime
//through the same callback, routing actual514228 virtual entries into this
//module. Other common entries may be called directly through their frozen API.
//Dependency ABI is frozenClawPlayerFadeDependency.4a3050 rand must route the
//same shared source CRT thread as gameplay; physical4b9730 lock and actual
//surface DD virtual80 Unlock retain exact receiver/arguments/order.
//Fault lives in common->fade->fault:1 missing graph/service,2 reached bounded
//unsafe/stalled domain,3 unsupported public profile. No fake original safe exit.
//All pixel writes occur in caller spans; forward bytecopy preserves aliases
//and source width-inclusive permutation spill. No opacity/host wait is added.
uint32_t claw_warp_fade_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                              ClawWarpFadeContext *, ClawPlayerFadeDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
