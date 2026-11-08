#ifndef CLAW_PLAYER_FADE_RUNTIME_H
#define CLAW_PLAYER_FADE_RUNTIME_H
#include "CArrayRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerFadeGlobals {
    uint32_t bypass;
} ClawPlayerFadeGlobals;
typedef struct ClawPlayerFadeContext {
    ClawSceneActorHost scene;
    ClawPlayerFadeGlobals *globals;
    // Original local descriptor word3 is uninitialized and copied unchanged.
    // Caller-owned36-byte scratch represents the synchronous local descriptor;
    // it has no original heap ownership/allocation claim.
    uint32_t descriptorWord3, temporaryDescriptorToken, maximumClockReads, fault;
} ClawPlayerFadeContext;
typedef struct ClawPlayerFadeCall {
    uint32_t function, receiver, argumentCount, arguments[6];
} ClawPlayerFadeCall;
typedef uint32_t (*ClawPlayerFadeDependency)(ClawPlayerFadeContext *, const ClawPlayerFadeCall *, void *);
// An unknown public entry returns0 without changing fault/result.
// Raw token receiver and up to6 thiscall/cdecl arguments. Recognized complete
// bodies return1; native faults return0. Fault1 missing graph/service,2 bounded
// unsafe/stalled domain,3 unrecovered path (factory diagnostic or gradient>0
// pixel blend). Faults preserve reached prefix and are not original safe exits.
// Complete default respawn48fae0/48fbe0, circle factory type1,2075-word circle,
// runner4ec9c0(duration,initialWait,pumpFlag), and gradient<=0 clear/copy pixels.
// Physical surfaces, their locks/unlocks, music and resource lifetime remain
// ordered services. Clock service identities546a24 and546df0 are import SLOT
// identities, deliberately distinct; supply progressing UInt32 trajectories.
// Radius numeric profile covers nonnegative integer x,y,width-x,height-y
// <=1024; pixel rows<=1024, bytesPerPixel1..4. Larger domains fault2.
// Word-based lookup accepts aligned interiors; byte writes preserve padding.
// Original void incidental EAX is excluded; constructors/factory/init/radius
// expose meaningful returns. No host opacity/sleep or event-pump is invented.
uint32_t claw_player_fade_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                                ClawPlayerFadeContext *, ClawPlayerFadeDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
