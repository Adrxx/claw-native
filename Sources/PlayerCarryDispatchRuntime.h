#pragma once
#include "LiftThrowRuntime.h"
#include "PlayerInputDispatch.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerCarryDispatchContext {
    ClawLiftThrowContext *lift;
    uint32_t actorToken, primaryToken, privateToken;
    uint32_t ignoreHazards, cheat, fault; /*live537230/537214; faultdiagnostic*/
} ClawPlayerCarryDispatchContext;
typedef struct ClawPlayerCarryDispatchCall {
    uint32_t function, receiver, argumentCount, arguments[4];
} ClawPlayerCarryDispatchCall;
typedef uint32_t (*ClawPlayerCarryDispatchDependency)(ClawPlayerCarryDispatchContext *,
                                                      const ClawPlayerCarryDispatchCall *, void *);
/* Whole415df0 bounded initial5000/5001. Captured actor/primary/private tokens
 identify live sized spans128/93/78; supply source identities, not host pointers.
 Incoming state/input snapshots are exported to these spans and source aliases;
 exact frozen41a850/41b280 executes through LiftThrow's rich services. Other
 carry source fields/targets/resources remain owned by the borrowed Lift context.
 Common tail composes claw_player_input_epilogue unchanged. Its rich dependency
 writes raw heap, borrowedphysics/globals andcontextignoreHazards/cheat;
 completeactor/private,primary state/invul/bounds andinputwords4/8/C are imported
 after every service. Captured primary/private identity persists even if actor
 pointer fields change inside a callback, matching415df0 source locals.
 Common services:420910(thissoundregistry,name),41fc30 cdecl(actor,primary,
 private,stageDelta),4cd740(thisworld,actor,0),417c50 cdecl(actor,primary,private).
 Legacy scene.call fallback supports these four rawargs; no inferred damage,
 powerup/collision/audio behavior is substituted. Unsupported initial state
 returns0 untouched; coveredreturns1 withfault0 oncompletion. Fault1 span/alias,
 otherfaults propagatefrozenLift; reachedprefix imports arepreserved. SourceEAX1
 is meaningful only afterordinarycompletion. No fake logicstate28 epilogue.*/
uint32_t claw_player_dispatch_carry(ClawPlayerLocomotion *, ClawPlayerInputContext *, ClawPlayerCarryDispatchContext *,
                                    ClawLiftThrowDependency, ClawPlayerCarryDispatchDependency, void *);
#ifdef __cplusplus
}
#endif
