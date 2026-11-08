#ifndef CLAW_GRAPHICS_MANAGER_CONSTRUCTION_RUNTIME_H
#define CLAW_GRAPHICS_MANAGER_CONSTRUCTION_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
//Whole original4bc120: exact2180-byte manager, two sourceCPtrList ctors,
//whole20-byte CStringArray ctor4f54ea, and six final zero stores.
//All other allocation seed bytes remain untouched. No physical device startup
//or manager destructor claim. Missing/short spans are native diagnostics.
uint32_t claw_graphics_manager_construct(uint32_t token, ClawSceneActorHost, uint32_t *fault, uint32_t *result);
uint32_t claw_graphics_string_array_construct(uint32_t token, ClawSceneActorHost, uint32_t *fault, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
