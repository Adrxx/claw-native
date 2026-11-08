#ifndef CLAW_PALETTE_FADE_RUNTIME_H
#define CLAW_PALETTE_FADE_RUNTIME_H
#include "PaletteResourceRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPaletteFadeContext {
    ClawSceneActorHost scene;
    /* Borrowed existing owner view; copied when final set/fill is elected.
    Raw cooperative alias541374 is authoritative and synchronized on return. */
    ClawPaletteResourceContext *palette;
    uint32_t maximumOperations, fault;
} ClawPaletteFadeContext;
typedef struct ClawPaletteFadeCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    /* Exact physical/IAT identities. Receiver0 for physical COM/import calls;
    interface token is arg0. Live raw palette/output pointers retain tokens.
    Synchronous buffer views use the frozen PaletteResource conventions. */
    uint32_t localMask, bufferCount;
    uint32_t *buffers[2];
    uint32_t bufferBytes[2];
} ClawPaletteFadeCall;
typedef uint32_t (*ClawPaletteFadeDependency)(ClawPaletteFadeContext *, const ClawPaletteFadeCall *, void *);
/* Whole original4bbd90(start,count,targetTable,duration) is a BLOCKING table
   fade, RET16, not a scheduler. timeGetTime import546df0 must progress.
   4bbb70() updates an already source-configured scheduled fade;4bbd20()
   finalizes/cancels;4bb8c0(unused) copies the256-entry backup and applies it.
   Frozen PaletteResource owns final4bb800/4bb910, arrays/list/destruction.
   No guessed scheduler setup/visual interpolation or duration changes.
   Return1 covered/completed. Tick4bbb70 meaningful EAX0/1 in result; other
   entries void/result0. Setfault0; faults1 span/service,2 ABI,3 operation bound.
   Context/clock/physical joining:docs/palette-fade-runtime.md. */
uint32_t claw_palette_fade_entry(uint32_t function, uint32_t backend, const uint32_t *arguments, uint32_t argumentCount,
                                 ClawPaletteFadeContext *, ClawPaletteFadeDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
