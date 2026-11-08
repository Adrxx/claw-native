#ifndef CLAW_SCENE_STARTUP_COMPOSITION_RUNTIME_H
#define CLAW_SCENE_STARTUP_COMPOSITION_RUNTIME_H
#include "SinglePlayerSceneRuntime.h"
#include "SceneLifecycleRuntime.h"
#include "ImageRegistryRuntime.h"
#include "BootyResultsRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawSceneStartupCompositionContext {
    ClawSceneActorHost scene;
    /* Borrowed views. Their raw host/callback members are never left pointing at
    this call's stack. Source globals are synchronized to live raw aliases at
    source dependency boundaries and on return; raw aliases are authoritative. */
    ClawSinglePlayerSceneContext *startup;
    ClawSceneLifecycleContext *lifecycle;
    ClawSceneDisplayContext *display;
    ClawGraphicsManagerLifecycleContext *graphics;
    ClawPaletteResourceContext *palette;
    ClawAudioManagerLifecycleContext *audio;
    ClawWorldFileContext *world;
    ClawImageRegistryContext *imageRegistry;
    ClawGameImageGlobals *images;
    ClawCArrayContext *arrays;
    ClawBootyResultsContext *collections;
    uint32_t maximumOperations, fault;
} ClawSceneStartupCompositionContext;
typedef struct ClawSceneStartupCompositionCall {
    uint32_t function, receiver, argumentCount, arguments[8], localMask, bufferCount;
    /* Bit256 receiver, argument bits otherwise; buffers receiver first then
    arguments ascending. Nonlocal raw output pointers retain their tokens.
    A raw live alias may also be exposed with mask0; its raw argument token
    remains authoritative. bufferTokens is reserved and currently zero.
    All borrowed pointers/name bytes are synchronous. */
    void *buffers[3];
    uint32_t bufferBytes[3], bufferTokens[3];
    const char *name;
} ClawSceneStartupCompositionCall;
typedef uint32_t (*ClawSceneStartupCompositionDependency)(ClawSceneStartupCompositionContext *,
                                                          const ClawSceneStartupCompositionCall *, void *);
/* Composition of frozen scene4ce960/4cea10(default11-manager graph), display,
   graphics/audio/palette/world and elected controller/collection services.
   New thin source leaves4ca280(sound-controller audio election, master100),
   4cf7e0(sound-controller readiness),4f701d(CObject metadata getter) only.
   Missing meaningful bodies remain exact addressed services, never implicit
   success. No CRT/logic/resource bootstrap or asset load is invented.
   Supported inventory/evidence: docs/scene-startup-composition-runtime.md.
   Setfault0. Return1
   covered/completed, EAX separately (source return0 may be ordinary failure).
   fault1 missing span/context/service;2 ABI/unsafe;3 operation budget. */
uint32_t claw_scene_startup_composition_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                              uint32_t argumentCount, ClawSceneStartupCompositionContext *,
                                              ClawSceneStartupCompositionDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
