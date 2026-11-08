#ifndef CLAW_SCENE_DISPLAY_RUNTIME_H
#define CLAW_SCENE_DISPLAY_RUNTIME_H
#include "GraphicsManagerLifecycleRuntime.h"
#include "GameImageRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_SCENE_DISPLAY_HOLDER_BYTES 28u
#define CLAW_SCENE_DISPLAY_PRIMARY_BYTES 48u
#define CLAW_SCENE_DISPLAY_AUXILIARY_BYTES 52u
typedef struct ClawSceneDisplayContext {
    ClawSceneActorHost scene;
    //Optional source graphics startup/reset and frozen image surface cores.
    //When absent those exact addresses remain dependency services.
    ClawGraphicsManagerLifecycleContext *graphics;
    ClawGameImageGlobals *image;
    uint32_t maximumOperations, fault;
} ClawSceneDisplayContext;
typedef struct ClawSceneDisplayCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    uint32_t localMask, bufferCount;
    uint32_t *buffers[2];
    uint32_t bufferBytes[2];
} ClawSceneDisplayCall;
typedef uint32_t (*ClawSceneDisplayDependency)(ClawSceneDisplayContext *, const ClawSceneDisplayCall *, void *);
//Original holder4ca6f0(w,h,depth,flags),4cf730 readiness,4ca8b0 cleanup,
//4cf780 destructor,4cf760(flags) deleting,4cf750 type15.
//Renderer4d63c0(surface,arg2) is source queue drain, not physical present.
//Bodies and finite default wrapper/factory inventory are documented at handoff.
//All receivers are raw32-bit tokens; original VT identities remain in heap.
//COM receiver0 includes interface as argument0. Synchronous local pointers
//are token0/localMask-marked with writable buffers; other pointers are tokens.
//Return1 means covered completed body; meaningful original EAX in result.
//fault1 missing span/service,2 ABI/unsafe domain,3 traversal budget.
uint32_t claw_scene_display_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                  uint32_t argumentCount, ClawSceneDisplayContext *, ClawSceneDisplayDependency, void *,
                                  uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
