#ifndef CLAW_LIGHT_PALETTE_RUNTIME_H
#define CLAW_LIGHT_PALETTE_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_LIGHT_PALETTE_OWNER_WORDS 478u
#define CLAW_LIGHT_PALETTE_MANAGER_WORDS 6u
#define CLAW_LIGHT_PALETTE_TABLE_WORDS 3u
typedef struct ClawLightPaletteContext {
    ClawSceneActorHost scene;
    //40-byte caller scratch represents source local CMemFile. No heap ownership
    //claim; required only for whole4c7850 memory-file decoder orchestration.
    uint32_t temporaryFileToken, composeCore, maximumSteps, fault;
} ClawLightPaletteContext;
typedef struct ClawLightPaletteCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    //Bit0 receiver is source local CMemFile; buffer0 is its10-word snapshot.
    //Heap output arguments retain their live original tokens. Synchronous only.
    uint32_t localMask, bufferCount;
    uint32_t *buffers[2];
    uint32_t bufferBytes[2];
    const char *name;
} ClawLightPaletteCall;
//Integer result low32. Non-normal numeric CRT4f1b30 service uses four32-bit IEEE double
//words(base,exponent) and returns IEEE double bits; original x87 ABI adapted.
//Normal exponent1 uses the pinned256-value original numeric profile.
typedef uint64_t (*ClawLightPaletteDependency)(ClawLightPaletteContext *, const ClawLightPaletteCall *, void *);
void claw_light_palette_defaults(ClawLightPaletteContext *);
//Original raw graph: owner478words, owner4 app, app78 bitdepth, app58 manager,
//owner1c resource manager, owner360 palette256 four-byte entries, owner768/
//76c/770 table tokens. Manager6words:active,vtable,data,size,capacity,growBy.
//Table3words:active,byteLength,data. Source5430b0/b4/b8/bc are live effect
//tokens,5430c0 live comparator palette; no guessed alpha/default color table.
//Whole startup46e160 and source CLT/table factory/read/generated math/cleanup
//inventory is documented with final evidence. Byte-rank qsort is the original
//4f1e20/1fd0/2030 specialization, preserving tie order. Source identities and
//physical resource/MFC/CRT/palette transport remain explicit exact services.
//Supported1 requirefault0; unsupported0. Native safety1 missing graph/service,
//2 ABI/unbounded rejection. Meaningful original return is separate.
uint32_t claw_light_palette_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                  uint32_t argumentCount, ClawLightPaletteContext *, ClawLightPaletteDependency, void *,
                                  uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
