#ifndef CLAW_SURFACE_TRANSFORM_RUNTIME_H
#define CLAW_SURFACE_TRANSFORM_RUNTIME_H
#include "GameImageRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef uint8_t *(*ClawSurfaceTransformByteLookup)(void *, uint32_t, uint32_t);
typedef struct ClawSurfaceTransformContext {
    ClawSceneActorHost scene;
    void *byteContext;
    ClawSurfaceTransformByteLookup bytes;
    ClawGameImageGlobals *images;
    uint32_t maximumOperations, fault;
} ClawSurfaceTransformContext;
typedef uint32_t (*ClawSurfaceTransformDependency)(ClawSurfaceTransformContext *, const ClawGameImageCall *, void *);
/* Whole4b99d0(surface), no stack arguments; original void incidental EAX is
 excluded. Flips only width(+18) BYTES per row, even at other pixel depths;
 stride(+1c) is bytes, signed height(+14)<=1 returns without locking.
 Source lock4b9730(surface,0) composes frozen GameImage when images supplied.
 Allocates exactly width bytes, preserves padding/middle row and unlocks via
 live surface+8 DD virtual+80(receiver0,args[DD,0]) before freeing scratch.
 Byte lookup should be exact; fallback requires containing aligned words.
 Failed scratch allocation still unlocks; failed lock does not allocate.
 Return1 is completion, result0; fault1 missing graph/service/span,2 ABI,
 3 operation budget are native safety diagnostics, not source error values.*/
uint32_t claw_surface_transform_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                      uint32_t argumentCount, ClawSurfaceTransformContext *,
                                      ClawSurfaceTransformDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
