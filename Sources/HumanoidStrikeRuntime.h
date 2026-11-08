#pragma once
#include "CommonEnemyEntries.h"
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawHumanoidStrikeContext {
    ClawHumanEnemyContext *human;
    ClawSceneActorHost scene; // Rectangle/resource/other raw heap spans.
    // Optional transport labels; raw original name tokens remain arguments.
    const char *sequenceName;
    const char *soundName;
    uint32_t composeAnimation, fault;
} ClawHumanoidStrikeContext;
//43ee10 thiscall(enemy,sequenceNameToken,rectangleToken), RET8.
//43eee0 thiscall(enemy,sequenceNameToken,rectangleToken,soundNameToken), RET12.
//43efe0 zeroarg and43f030 strike update compose frozen common/state bodies.
// All normal meaningful EAX results are0; support is separate. Fault1 missing
// spans/services,2 propagated animator fault/malformed arguments. No allocation.
uint32_t claw_humanoid_strike_entry(ClawGenericEnemy *, ClawHumanoidStrikeContext *, uint32_t function,
                                    const uint32_t *arguments, uint32_t argumentCount, ClawGenericEnemyDependency,
                                    void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
