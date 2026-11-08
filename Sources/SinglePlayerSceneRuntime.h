#ifndef CLAW_SINGLE_PLAYER_SCENE_RUNTIME_H
#define CLAW_SINGLE_PLAYER_SCENE_RUNTIME_H
#include "SceneCameraRuntime.h"
#include "SpatialGridRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_SINGLE_PLAYER_OWNER_BYTES 0x778u
#define CLAW_SINGLE_PLAYER_OWNER_WORDS 478u
#define CLAW_ORIGINAL_APPLICATION_BYTES 0x134u
#define CLAW_ORIGINAL_APPLICATION_WORDS 77u
typedef struct ClawSinglePlayerSceneGlobals {
    uint32_t lootInitialized, imageLoading, accumulatedTick, word53c9c0, word5349dc;
    uint32_t playerToken, word534ca4, forcedX, forcedY, inputMappingToken, buildNumber;
    /*42aa50 ordered stores:537268,537214,218,21c,220,228,224,22c,230,264.*/
    uint32_t resetFlags[10];
} ClawSinglePlayerSceneGlobals;
typedef struct ClawSinglePlayerSceneCall {
    uint32_t function, receiver, argumentCount, arguments[8], localMask, bufferCount;
    /* Automatic pointer arguments ->token0/mask bit i; local receiver ->bit8.
    Buffers in marked argument order, then receiver; live raw output buffers
    may follow. IAT slots identify platform calls. */
    void *buffers[3];
    uint32_t bufferBytes[3];
} ClawSinglePlayerSceneCall;
typedef struct ClawSinglePlayerSceneContext {
    ClawSceneActorHost host;
    ClawSinglePlayerSceneGlobals *globals;
    ClawSceneCameraGlobals *camera;
    uint32_t composeBase, composeLevel, composeCamera, composeSpatial, fault;
} ClawSinglePlayerSceneContext;
typedef uint32_t (*ClawSinglePlayerSceneDependency)(ClawSinglePlayerSceneContext *, ClawSinglePlayerSceneCall, void *);
void claw_single_player_scene_defaults(ClawSinglePlayerSceneContext *);
/* Exact inlined428d5d..428dce constructor after successful0x778 allocation:
   base40b5c0, CString+250 and derived stores. Other words preserved. */
uint32_t claw_single_player_scene_construct(uint32_t ownerToken, ClawSinglePlayerSceneContext *,
                                            ClawSinglePlayerSceneDependency, void *);
/* Entries40b5c0/48f0d0/46a6d0/46aeb0/42af50/42aa50,
   scene ctor4ce960 (15words;animation reset via camera), base object45fde0,
   world ctor4cace0 (delegates WorldFileRuntime/frozen CArray),scene init4cea10,
   exact7word collection ctors4f5620/4f6118/4f5cbd(growBlock),
   actualinit probes4bd250/4cdf20 and imageFX reset4cfa60;
   application ctor4254a0 (77words) and complete base timer ctor4b8240. For base/init,
   arguments=(managerToken,level,parameter); for level46aeb0=(level,unused).
   Object/world ctor=(parent,type,flags);scene init=(HWND,width,height,depth,flags).
   The inlined owner CString ctor reads shared empty-data cell52e1cc.
   Image-controller initialization requires live host span543108 (25words),
   the frozen GameImageRuntime directDrawFX view. Application/timer ctors
   require live clock span541328 (5words) and host.readClock; they compose
   frozen GameTiming. No context/global struct layout changes.
   Only meaningful original EAX is exposed; safe faults aren't original exits.
   Resource loading, graphics/audio/OS, saved-level decoding and actor creation
   remain exact-address dependency services. Frozen input/grid compose when
   selected; actual world loader service must itself route recovered modules. */
uint32_t claw_single_player_scene_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                        uint32_t argumentCount, ClawSinglePlayerSceneContext *,
                                        ClawSinglePlayerSceneDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
