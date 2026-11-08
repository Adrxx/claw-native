#pragma once
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawElevatorGlobals {
    uint32_t managerToken, defaultsToken, playerToken, tick, animationDelta, wrapperMode;
} ClawElevatorGlobals;
typedef struct ClawElevatorContext {
    ClawSceneActorHost scene;
    ClawElevatorGlobals *globals;
    uint32_t fault;
} ClawElevatorContext;
typedef struct ClawElevatorCall {
    uint32_t function, receiver, argumentCount, arguments[3];
    const char *name;
} ClawElevatorCall;
typedef uint32_t (*ClawElevatorDependency)(ClawElevatorContext *, const ClawElevatorCall *, void *);
// Cdecl entries:49e2a0/49cdd0 and registered49daf0/49db10/49db30/49db50/49db70
// take actor;49e060 takes(actor,primary);49e1c0 takes(actor,primary,absoluteTick).
// No private allocation or guessed animation/movement. Shared globals map to
//5371fc,537960,537e88,537210,5430c4,53ebf0 respectively. Keep player support
// actor+80 and player primary+14->private+80 live in the heap.
// Returns support independently of result (controllers return1; helpers void).
// fault1 missing heap/service,2 original arithmetic trap,3 argument shape.
uint32_t claw_elevator_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                             ClawElevatorContext *, ClawElevatorDependency, void *, uint32_t *result);
typedef struct ClawElevatorLevelProfile {
    uint32_t words[48], selectedToken, levelWord, scaleWords[3];
} ClawElevatorLevelProfile;
// Source452b00/14 finite leaf setters. SelectedToken maps537960 and is5378a0
// on positive levels; levelWord maps537964; scaleWords map5262b0/b4/b8.
// Optional SetRect platform service receives destination offset and4 rawwords;
// its return is ignored. Null service uses equivalent four-word stores.
typedef uint32_t (*ClawElevatorSetRect)(ClawElevatorLevelProfile *, uint32_t destinationOffset,
                                        const uint32_t rectangle[4], void *);
uint32_t claw_elevator_initialize_profile(uint32_t level, ClawElevatorLevelProfile *, ClawElevatorSetRect, void *);
#ifdef __cplusplus
}
#endif
