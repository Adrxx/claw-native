#ifndef CLAW_PALETTE_RESOURCE_RUNTIME_H
#define CLAW_PALETTE_RESOURCE_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_PALETTE_RESOURCE_WORDS 5u
#define CLAW_PALETTE_BACKEND_WORDS 14u
#define CLAW_PALETTE_ENTRY_COUNT 256u
typedef struct ClawPaletteResourceGlobals {
    uint32_t cooperativeHolder; //Original541374, holder+0 physicalDDinterface.
} ClawPaletteResourceGlobals;
typedef struct ClawPaletteResourceContext {
    ClawSceneActorHost scene;
    ClawPaletteResourceGlobals *globals;
    //Caller scratch1024bytes represents source system-palette local seed/profile.
    //Required only by4bbf60. No original heap-identity claim.
    uint32_t systemPaletteScratchToken, composeLists, maximumSteps, fault;
} ClawPaletteResourceContext;
typedef struct ClawPaletteResourceCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    //Bit i denotes normalized source-local pointer arguments[i]==0.
    //Buffers expose synchronous bytes for palette/COM/MFC name operations.
    uint32_t localMask, bufferCount;
    uint32_t *buffers[2];
    uint32_t bufferBytes[2];
} ClawPaletteResourceCall;
typedef uint32_t (*ClawPaletteResourceDependency)(ClawPaletteResourceContext *, const ClawPaletteResourceCall *,
                                                  void *);
void claw_palette_resource_defaults(ClawPaletteResourceContext *);
//Raw source roots/ABI documented with final evidence. Resource5words VT513d78;
//backend14words has node0/COMpalette4/payloadc/backup10, seededwords7..10.
//Physical DD/GDI and resource/map/diagnostic transports remain exact services.
//Complete palette list helpers compose frozenAmbientAudioBackend source.
//Recognition1 requiresfault0; meaningful original EAX is separate. Fault1
//missing graph/service,2 ABI/unsafe domain,3 bounded runaway traversal.
uint32_t claw_palette_resource_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                     uint32_t argumentCount, ClawPaletteResourceContext *,
                                     ClawPaletteResourceDependency, void *, uint32_t *result);
//Exact original46afe9..46b000 GetEntries instruction prefix, not whole46aeb0.
//Owner+2c→resource+10→backend+4; physicalGetEntries256entries toowner+360.
uint32_t claw_palette_resource_capture_owner(uint32_t owner, ClawPaletteResourceContext *,
                                             ClawPaletteResourceDependency, void *, uint32_t *hresult);
#ifdef __cplusplus
}
#endif
#endif
