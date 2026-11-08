#ifndef CLAW_SCENE_ACTOR_RUNTIME_H
#define CLAW_SCENE_ACTOR_RUNTIME_H
#include "GameTiming.h"
#include "WorldObjectRuntime.h"
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawSceneActorGlobals {
    uint32_t initializationFlags;               // Low byte 0x5430d0, static array guards.
    uint32_t deletionArray[5], reorderArray[5]; // Original CArray metadata.
    ClawFrameClock animation;
} ClawSceneActorGlobals;
typedef struct ClawSceneActorCall {
    uint32_t function, receiver, arguments[4], argumentCount;
} ClawSceneActorCall;
typedef struct ClawSceneActorHost {
    void *context;
    // Exact sized spans; tokens may identify interiors (list nodes/arrays).
    uint32_t *(*lookup)(void *context, uint32_t token, uint32_t words);
    uint32_t (*allocate)(void *context, uint32_t bytes);
    void (*free)(void *context, uint32_t token);
    // Named lookup4f6286 returns resolved entry token, not original bool.
    // Gameplay callbacks receive actor as one cdecl argument (receiver0).
    // Destruction uses actor vtable+4 (generic5137f0 resolves4c9be0), with
    // receiveractorToken and delete=1; other vtables need lookup metadata.
    uint32_t (*call)(void *context, ClawSceneActorCall call);
    uint32_t (*readClock)(void *context);
} ClawSceneActorHost;
typedef struct ClawSceneActorCreate {
    uint32_t id, x, y, z, entryToken, flags;
} ClawSceneActorCreate;
// Creator4c8be0 / namedwrapper4c8da0, composed with frozen common constructor.
// No forced40000; flags pass through. Immediate200000 executes after insertion.
// Container+0xc points to parent scene; parent+0x14 supplies registry object.
// Native faults1 missing span,2 allocation/null-node path; no normal-return claim.
uint32_t claw_scene_actor_create(uint32_t containerToken, ClawSceneActorCreate args, ClawSceneActorHost host,
                                 uint32_t *fault);
uint32_t claw_scene_actor_create_named(uint32_t containerToken, ClawSceneActorCreate args, uint32_t nameToken,
                                       ClawSceneActorHost host, uint32_t *fault);
// Complete insertion4c9320. Raw original CList and pooled node storage mutate.
void claw_scene_actor_insert(uint32_t containerToken, uint32_t actorToken, ClawSceneActorHost host, uint32_t *fault);
// Complete frame dispatch4c8fc0 and deferred deletion/reorder scheduling.
// Gameplay and actor destruction are explicit calls; node/array bodies recovered.
void claw_scene_actor_update(uint32_t containerToken, ClawSceneActorGlobals *globals, uint32_t refreshClock,
                             ClawSceneActorHost host, uint32_t *fault);
typedef struct ClawSceneStageState {
    ClawFrameClock stage;
    uint32_t accumulatedMilliseconds, playerToken;
} ClawSceneStageState;
// Complete46ace0 /46ad70 actor phases, including services46c860/4d1fd0/4d2000
// and final optional image100 override. Interactions call4c9390 is delegated to
// the frozen ActorInteractions implementation through host.call.
// owner+0xc is parent, parent+8 actor container, parent+24 map, map+5c plane.
// owner+764 requests the image100 override; owner+4 is the stage manager.
// Returns update-pass count (native diagnostic;46ad70 also returns this count).
uint32_t claw_scene_stage_run(uint32_t ownerToken, ClawSceneStageState *stage, ClawSceneActorGlobals *globals,
                              uint32_t subdivide, ClawSceneActorHost host, uint32_t *fault);
// Observed46ac30/475dc0 choice: unsigned18<stageDelta<100 subdivides.
uint32_t claw_scene_stage_update(uint32_t ownerToken, ClawSceneStageState *stage, ClawSceneActorGlobals *globals,
                                 ClawSceneActorHost host, uint32_t *fault);
#ifdef __cplusplus
}
#endif
#endif
