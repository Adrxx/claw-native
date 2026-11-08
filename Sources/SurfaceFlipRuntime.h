#ifndef CLAW_SURFACE_FLIP_RUNTIME_H
#define CLAW_SURFACE_FLIP_RUNTIME_H
#include "SurfaceBlitRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawSurfaceFlipContext {
    ClawSceneActorHost scene;
    /* Optional borrowed source restore owner, copied for this call. Existing
    SurfaceBlit composes the frozen PCX4b9e60 callback/fallback body. */
    ClawSurfaceBlitContext *blit;
    uint32_t maximumOperations, fault;
} ClawSurfaceFlipContext;
typedef ClawSurfaceBlitCall ClawSurfaceFlipCall;
typedef uint32_t (*ClawSurfaceFlipDependency)(ClawSurfaceFlipContext *, const ClawSurfaceFlipCall *, void *);
/* Whole original4b98b0(optional sourceSurface),RET4. Source DD is captured
   once and retained across restore; destination DD/vtable are reread on the
   single retry. Physical Flip is destination DD virtual+2c with receiver0,
   args[destDD,capturedSourceDDor0,1]. Exact errors/restore/diagnostics preserved.
   Return1 covered/completed; meaningful source HRESULT through result.
   Setfault0; faults1 missing span/service,2 ABI,3 operation bound.
   Joining/evidence:docs/surface-flip-runtime.md. */
uint32_t claw_surface_flip_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                 uint32_t argumentCount, ClawSurfaceFlipContext *, ClawSurfaceFlipDependency, void *,
                                 uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
