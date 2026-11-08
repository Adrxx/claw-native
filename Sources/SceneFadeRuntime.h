#pragma once
#include "PlayerFadeBlendRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_SCENE_TYPE2_FADER_BYTES 0x7d5cu
#define CLAW_SCENE_TYPE2_FADER_WORDS 8023u
typedef struct ClawSceneFadeContext {
    ClawPlayerFadeBlendContext *blend;
} ClawSceneFadeContext;
/*4ec050 only source type2(type,packetToken),null packet uses borrowed fade's
 temporaryDescriptorToken as five-word automatic scratch;4ecc00 packet ctor;
 4ed060 ctor,4ed0b0(packet) init,4ed1a0(step),4ed5d0 maxsteps;
 4ed080(delete)/4ed0a0 destructor;4efb00 cdecl(output,min,max,start);
 4efc40 cdecl(value). Shared4ec9c0(duration,initialWait,pumpFlag),4ec990,
 4ec600/4ec8d0/4ecb00/4ecb20 compose frozen PlayerFadeRuntime.
 Own source type2 virtual methods are routed while composing the runner.
 4a3050 composes frozen WorldLoot LCG after explicit4a7dc0 thread lookup;
 returned thread token must expose the shared seed at+14 (no new private RNG).
 Physical locks/unlocks, clocks and DD vertical-blank transport use frozen fade's
 exact-address dependency ABI. Read trajectories must actually progress;
 maximumClockReads bounds stalled original prefixes, not a source timeout.
 Diagnostic CString uses borrowed Blend scratch/empty tokens and frozen bodies.
 Width1..1999,height0..2000 and bpp0..4 cover fixed source arrays; other
 unsafe profiles fault2 rather than invent normal original completion.
 Faults live in blend->fade->fault:1 missing span/service,2 bounded unsafe or
 stalled profile,3 unsupported factory type. No synthetic animation clock. */
uint32_t claw_scene_fade_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                               ClawSceneFadeContext *, ClawPlayerFadeDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
