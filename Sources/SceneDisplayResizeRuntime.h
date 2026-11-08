#ifndef CLAW_SCENE_DISPLAY_RESIZE_RUNTIME_H
#define CLAW_SCENE_DISPLAY_RESIZE_RUNTIME_H
#include "SceneDisplayRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawSceneDisplayResizeContext {
    ClawSceneActorHost scene;
    //Borrowed source wrappers/factories and optional graphics mode/device core.
    //When absent elected original addresses remain explicit services.
    ClawSceneDisplayContext *display;
    ClawGraphicsManagerLifecycleContext *graphics;
    uint32_t maximumOperations, fault;
} ClawSceneDisplayResizeContext;
typedef ClawSceneDisplayCall ClawSceneDisplayResizeCall;
typedef uint32_t (*ClawSceneDisplayResizeDependency)(ClawSceneDisplayResizeContext *,
                                                     const ClawSceneDisplayResizeCall *, void *);
//Whole original4d4280(aux52bytes) and4d5720(primary48bytes), thiscall
//(width,height,depth), RET12. Equality precedes all admission/dependencies.
//Changed dimensions replace surfaces BEFORE signed positive/depth admission;
//failed admission preserves reached mutations, without rollback.
//Return1 recognized/completed; meaningful EAX via result. fault1 missing
//span/service,2 ABI/unsafe prefix,3 bounded operation budget. Requirefault0.
uint32_t claw_scene_display_resize_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                         uint32_t argumentCount, ClawSceneDisplayResizeContext *,
                                         ClawSceneDisplayResizeDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
