#ifndef CLAW_SURFACE_BLIT_RUNTIME_H
#define CLAW_SURFACE_BLIT_RUNTIME_H
#include "PCXImageRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Raw original arguments. Optional synchronous spans replace only local
   pointer tokens: destination =4b9ce0 arg0; source =4b9ce0 arg2,
   4b9d80 arg3, or4b9950 arg1 (two-word color-key pair).
   Corresponding words must be0 when a span is supplied. Null span with word0
   retains an actual original null rectangle/pair. */
typedef struct ClawSurfaceBlitArguments {
    uint32_t words[5], count;
    uint32_t *destination, *source;
} ClawSurfaceBlitArguments;
typedef struct ClawSurfaceBlitContext {
    ClawSceneActorHost scene;
    /* Optional borrowed owner views, copied for this call. Frozen PCX owns
    restore4b9e60; frozen GameImage owns key convenience4b9990. */
    ClawPCXImageContext *pcx;
    ClawGameImageGlobals *image;
    uint32_t maximumOperations, fault;
} ClawSurfaceBlitContext;
typedef struct ClawSurfaceBlitCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    /* Local pointer args normalized0 with bit i; buffers in argument order.
    All physical calls use receiver0 and interface token in argument0.
    Nonlocal raw pointer arguments preserve their actual tokens. */
    uint32_t localMask, bufferCount;
    uint32_t *buffers[2];
    uint32_t bufferBytes[2];
} ClawSurfaceBlitCall;
typedef uint32_t (*ClawSurfaceBlitDependency)(ClawSurfaceBlitContext *, const ClawSurfaceBlitCall *, void *);
/* Whole4b9ce0(destRECT,sourceSurface,sourceRECT,flags,FX),4b9d80(x,y,
   sourceSurface,sourceRECT,flags),4b9950(flags,keyPair),4b9990(key),4b9e60().
   Blt/BltFast preserve original HRESULT and one restore/retry ordering.
   Underlying DirectDraw endpoints/diagnostics/registered restore callbacks
   remain exact services. Source image kind/flags stay with elected callers.
   Return1 covered/completed; meaningful HRESULT/restore EAX via result.
   4b9990 is void; result0. Setfault0. Fault1 missing span/service,2 ABI,
   3 operation bound. Full joining/evidence:surface-blit-runtime.md. */
uint32_t claw_surface_blit_entry(uint32_t function, uint32_t receiver, ClawSurfaceBlitArguments,
                                 ClawSurfaceBlitContext *, ClawSurfaceBlitDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
