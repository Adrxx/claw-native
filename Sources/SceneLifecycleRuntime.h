#ifndef CLAW_SCENE_LIFECYCLE_RUNTIME_H
#define CLAW_SCENE_LIFECYCLE_RUNTIME_H
#include "SceneDisplayRuntime.h"
#include "AudioManagerLifecycleRuntime.h"
#include "PaletteResourceRuntime.h"
#include "WorldFileRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_SCENE_LIFECYCLE_BYTES 60u
typedef struct ClawSceneLifecycleContext {
    ClawSceneActorHost scene;
    ClawSceneDisplayContext *display;
    ClawGraphicsManagerLifecycleContext *graphics;
    ClawAudioManagerLifecycleContext *audio;
    ClawPaletteResourceContext *palette;
    ClawWorldFileContext *world;
    ClawGameImageGlobals *image;
    uint32_t maximumOperations, fault;
} ClawSceneLifecycleContext;
typedef struct ClawSceneLifecycleCall {
    uint32_t function, receiver, argumentCount, arguments[8], localMask, bufferCount;
    //Synchronous original stack pointers/receiver normalized0; bit8 marks local
    //receiver, argument bits mark local pointer args. Heap pointers stay tokens.
    uint32_t *buffers[3];
    uint32_t bufferBytes[3];
} ClawSceneLifecycleCall;
typedef uint32_t (*ClawSceneLifecycleDependency)(ClawSceneLifecycleContext *, const ClawSceneLifecycleCall *, void *);
//Whole scene4ceef0(),4ce9c0(),4ce9a0(flags),4cefc0 readiness().
//Finite controller/map/CString lifecycle entry inventory documented at freeze.
//Ctor/init4ce960/4cea10 remain frozenSinglePlayerSceneRuntime, not duplicated.
//Optional contexts compose their actual frozen bodies, otherwise exactaddress
//services. Source globals52e1c8/cc and54316c/170 require shared raw aliases.
//No automatic manager/free/stopAll outside source ordering. Unknown private
//polymorphic destruction and locked CString copy branches remain services.
//Return1 means covered completed; meaningful EAX separately. fault1 missing
//span/service,2 ABI/unsafe domain,3 traversal bound are native diagnostics.
uint32_t claw_scene_lifecycle_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                    uint32_t argumentCount, ClawSceneLifecycleContext *, ClawSceneLifecycleDependency,
                                    void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
