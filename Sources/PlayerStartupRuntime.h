#ifndef CLAW_PLAYER_STARTUP_RUNTIME_H
#define CLAW_PLAYER_STARTUP_RUNTIME_H
#include "SinglePlayerSceneRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerStartupContext {
    ClawSceneActorHost scene;
    // Optional facade context for frozen whole46aeb0(level,unused).
    ClawSinglePlayerSceneContext *singlePlayer;
    uint32_t composeCache, composeCamera, maximumPlanes, fault;
} ClawPlayerStartupContext;
typedef ClawSinglePlayerSceneCall ClawPlayerStartupCall;
typedef uint32_t (*ClawPlayerStartupDependency)(ClawPlayerStartupContext *, const ClawPlayerStartupCall *, void *);
// Raw original global spans:534c80[78],534ea8[3],53c9f8,52c6e4,
//53725c,537210,536f00,52e1cc; synchronize aliases with frozen player/frame modules.
//415ce0 cdecl()/receiver0 composes frozen PlayerInitialization defaults;
//46c790()/46d8e0() ECX owner noargs;49af30/49af90(level,kind) ECX record.
//46aeb0 facade composes frozen SinglePlayerSceneRuntime with caller context.
//42af70(message) /422370(message,flagsByte) exact config CStringList insert;
//4f5249(blockSize) ctor,4f5288() clear,4f52f0(previous,next) new node,
//4f5382(message) AddHead /4f53b7(message) AddTail. Config56bytes, list7words,
//nodes12bytes. CString assignment/destruction explicit; frozen4f5aa8/5ac8
//pool allocation/release composed. Insertion preserves all config timer words.
//4222a0(duration,delay) initializes five observed fields and creates font;
//546918 CreateFontA service:argumentCount0/buffers[0] actual14-DWORD args.
//4f53eb(outCStringToken) RemoveHead /4f5359(nodeToken) FreeNode.
//RemoveHead4f6449 copyCtor calls use receiver0/mask256/localtemp buffer4,
//then output receiver witharg0=0/mask1/temp buffer4; finaltemp4f6584 uses
//receiver0/mask256. CString storage/refcounts and exception transport explicit.
//Fault1 missing span/service,2 frozen numeric domain,3 invalid argument shape,
//4 bounded plane/list traversal. Callback fault is preserved.
//compose flags select frozen cache49ae60 and camera4d0a60;0 exact-address service.
void claw_player_startup_defaults(ClawPlayerStartupContext *);
uint32_t claw_player_startup_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                   uint32_t argumentCount, ClawPlayerStartupContext *, ClawPlayerStartupDependency,
                                   void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
