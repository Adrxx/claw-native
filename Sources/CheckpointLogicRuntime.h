#pragma once
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawCheckpointGlobals {
    uint32_t managerToken, playerToken, animationDelta, tick, timerRemaining, timerBonus, superKind, skipNextSuper;
    // End-level save branch46d620 only: original534cc8,534cf0..534cfc,
    //534d08[10],534d30[10]. Ordinary checkpoint contacts do not reset these.
    uint32_t defaultHealth, defaultAmmo[4], levelTreasures[10], totalTreasures[10];
    uint32_t audioPosition; //532c10, frozen ANI audio-position argument.
} ClawCheckpointGlobals;
typedef struct ClawCheckpointContext {
    ClawSceneActorHost scene;
    ClawCheckpointGlobals *globals;
    uint32_t composeAnimation, composeContactBinding, composeSave, composeSaveCache, fault;
} ClawCheckpointContext;
typedef struct ClawCheckpointCall {
    uint32_t function, receiver, argumentCount, arguments[4];
    const char *name;
    // Stack-pointer arguments are normalized to0 and marked by localMask.
    // CRT4a3b10(time nullptr)/4a5c60(localtime timestamp) calls expose timestamp[1] as buffers[0] and the current save
    // packet[44] (or standalone record[17]) as buffers[1]. File/cache writes
    // expose their44/17-word argument as buffers[0]. Spans are callback-scoped
    // and mutable, preserving original calendar/file service ordering.
    uint32_t localMask, bufferCount;
    uint32_t *buffers[2];
    uint32_t bufferWords[2];
} ClawCheckpointCall;
typedef uint32_t (*ClawCheckpointDependency)(ClawCheckpointContext *, const ClawCheckpointCall *, void *);
// Cdecl(actor):422ef0,422ff0(void),423060,4231a0,4232c0,4232e0.
// Cdecl49a9d0(out17,counts10,time),49aa40(out17), and thiscall
//46d620(owner,x,y,checkpoint1or2);40af90(this) is original single-player mode3.
// Exact thiscall cache entries49a720(void),49ae60(level,kind),
//49a860(level,record44,kind),49a800(level,record17) use original receiver
// records+2d4/+d24/+1774 (15*44 each), best+21c4 (15*17).
// composeSaveCache selects these bodies inside46d620; file49bbc0 stays explicit.
// No checkpoint-private allocation. Contact allocation is the frozen generic
//93-word513740 object. compose flags use frozen ANI/contact and recovered save
// bodies; zero selects explicit original address services for boundary tests.
// Source defaults/global profile:5371fc,537e88,5430c4,537210,53c9f8,
//52c6e8,536efc,536f00. fault1 missing span/service,3 unsupported args/profile.
// CheckpointTimer491b30 HUD is outside the nine Level1 actor closure.
uint32_t claw_checkpoint_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                               ClawCheckpointContext *, ClawCheckpointDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
