#pragma once
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawEnemySpeechGlobals {
    uint32_t managerToken, playerToken, audioManagerToken;
    uint32_t clawBusy, clawActorToken, enemyBusy, enemyActorToken, speakerToken, stageDelta;
} ClawEnemySpeechGlobals;
typedef struct ClawEnemySpeechContext {
    ClawSceneActorHost scene;
    ClawEnemySpeechGlobals *globals;
    const char *nameHint; // Synchronous optional label for raw48ceb0 name arg.
    uint32_t fault;
} ClawEnemySpeechContext;
typedef struct ClawEnemySpeechCall {
    uint32_t function, receiver, argumentCount, arguments[4];
    const char *name;
} ClawEnemySpeechCall;
typedef uint32_t (*ClawEnemySpeechDependency)(ClawEnemySpeechContext *, const ClawEnemySpeechCall *, void *);
//48ce40/48ceb0 cdecl(speaker,sound/name,force),48cc60 cdecl(actor).
//420370 cdecl(attackerType),48cf50/90 cdecl(speaker). Also raw adapters over
// frozen player48c820/48c8a0 queues and profile-checkedSpeechActor48c630.
// Support separate from meaningful result;420370/48cf50 are void. All actor/
// primary/resource fields remain live heap spans; voice playback is4b45f0.
uint32_t claw_enemy_speech_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                 uint32_t argumentCount, ClawEnemySpeechContext *, ClawEnemySpeechDependency, void *,
                                 uint32_t *result);
// Source startup caller profile for Claw/EnemyDialogSound actors: namedscene
// creation(id0,x0,y0,z1000,flags40000). Does not eagerly tick/register them.
uint32_t claw_enemy_speech_create(uint32_t containerToken, uint32_t enemyProfile, ClawEnemySpeechContext *,
                                  ClawEnemySpeechDependency, void *);
#ifdef __cplusplus
}
#endif
