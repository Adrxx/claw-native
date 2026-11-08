#ifndef CLAW_IMAGE_RESOURCE_LIFECYCLE_RUNTIME_H
#define CLAW_IMAGE_RESOURCE_LIFECYCLE_RUNTIME_H
#include "ImageControllerLoadingRuntime.h"
#include "SceneLifecycleRuntime.h"
#include "BootyStoryRuntime.h"
#include "PCXCreationRuntime.h"
#include "SurfaceBlitRuntime.h"
#include "CStringAssignmentRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawImageResourceLifecycleContext {
    ClawSceneActorHost scene;
    ClawImageControllerLoadingContext *loading;
    ClawGameImageGlobals *images;
    ClawSceneDisplayContext *display;
    ClawBootyStoryContext *story;
    ClawPCXImageContext *pcx;
    ClawSurfaceBlitContext *blit;
    ClawCStringAssignmentContext *strings;
    ClawSceneLifecycleContext *lifecycle;
    uint32_t maximumOperations, fault;
} ClawImageResourceLifecycleContext;
typedef ClawImageControllerLoadingCall ClawImageResourceLifecycleCall;
typedef uint32_t (*ClawImageResourceLifecycleDependency)(ClawImageResourceLifecycleContext *,
                                                         const ClawImageResourceLifecycleCall *, void *);
/* New whole original image52:4d2540(width,height,key),4d26c0(),
 4d27a0(resource,key),4ce900(),4ce8e0(flags),4d2790(unused).
 Whole surface PID reload4bf680(graphics,data,length,key),RET16 composes
 frozen indexed/linear pixel decoding and conversion; no duplicate codec.
 Compressed40-byte4bfc20() frees payload+0c then auxiliary+20, preserving
 fields and alias ordering. Image clear resets ONLY width/height and owned
 surface/compressed pointers. Original destructor resets base identity last.
 4d27a0: absent/intact surface returns1; failed DD Restore elects virtual clear
 then typed resource initialization; successful Restore reacquires/reloads in
 place WITHOUT source resource release. Preserve live raw54316c/170 aliases.
 CStringAssignment owns exact byte tails: this facade forwards strict lookup
 and leaves its borrowed byte provider untouched; no outer word shadow.
 Optional synchronous views compose frozen registry/dictionary/resource/array,
 GameImage/PCX/Story/Display/CString/SceneLifecycle methods; no duplicate loaders.
 The52-byte image+0c is scene; scene+1c graphics; image+2c surface188, +30
 compressed40. Surface+8 is actual DD token. DD IsLost+60/Restore+6c use
 receiver0 and interface token asargument0. Registered surface+b4 restore
 callback remains caller supplied; frozen4b9e60 invokes cdecl(surface).
 Raw platform/resource/pixel services remain exact rich dependency packets.
 Return1 covered completed, meaningful original EAX separately. fault1 missing
 span/service,2 ABI/unsafe domain,3 operation budget are native diagnostics.
 Initialize every borrowedfault0; no concurrent borrowing during composition.*/
uint32_t claw_image_resource_lifecycle_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                             uint32_t argumentCount, ClawImageResourceLifecycleContext *,
                                             ClawImageResourceLifecycleDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
