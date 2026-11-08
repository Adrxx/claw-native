#ifndef CLAW_BOOTY_RESULTS_RUNTIME_H
#define CLAW_BOOTY_RESULTS_RUNTIME_H
#include "BootyProgressionRuntime.h"
#include "CheckpointTimerRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_BOOTY_RESULTS_BYTES 0x184u
#define CLAW_BOOTY_TREASURE_COUNTER_BYTES 0xb8u
#define CLAW_BOOTY_SCORE_NUMBER_BYTES 0x34u
typedef struct ClawBootyResultsContext {
    ClawSceneActorHost scene;
    ClawBootyProgressionContext *progression;
    ClawCheckpointTimerContext *numbers;
    ClawSceneActorGlobals *actors;
    uint32_t composeBase, composeNumbers, composeScene, composeAnimation, composeImages;
    uint32_t maximumSteps, fault;
} ClawBootyResultsContext;
typedef ClawBootyProgressionCall ClawBootyResultsCall;
typedef uint32_t (*ClawBootyResultsDependency)(ClawBootyResultsContext *, const ClawBootyResultsCall *, void *);
// Results388 bytes/VT50b494, TreasureCounter498930 cdecl(actor), private46words,
// VT50b5bc2words (delete40db10, RTTI514c30); score number13words/VT50b5cc
//2words (delete484d90, RTTI514cd0). Do not treat RTTI as callable slots.
// Result init40d470(app,level,oldMode);40e020(key,unused) RET8;40dca0(oldMode)
// RET4;40dcb0(nextMode) RET4;deleting40b020/40db10(flags). Number4903c0
// thiscall(actor,value,digits,spacing,x,yOffset,imageName), seven args.
// Counter helper thiscall entries retain exact raw actor/value args;4995d0 is
// ECX private/no stack args, only its meaningful low EAX is public.
// Live original globals are raw scene-host aliases:534cc4 total score,
//534d08..28 current treasure counts,5381e0..8200 maxima,5349a0/a8 and53499c
// shared story/music,52d4e0..ec,53cac4..d8,5371fc/537200/53720c/5430c4 and
//532c0c/10. Source numeric states2329..2334 are not substituted registry IDs.
// Rich automatic CString/printf buffers use localMask/three buffers. Allocation,
// metadata/resource loading, physical renderer/audio/OS and later application
//8021/8036/8075 remain explicit transport; no inferred next-level increment.
// Unknown0;requirefault0. Fault1 span/service,2 unchecked prefix,3 ABI/guard.
uint32_t claw_booty_results_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                  uint32_t argumentCount, ClawBootyResultsContext *, ClawBootyResultsDependency, void *,
                                  uint32_t *result);
uint32_t claw_booty_results_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
