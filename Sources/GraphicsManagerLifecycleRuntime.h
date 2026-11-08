#ifndef CLAW_GRAPHICS_MANAGER_LIFECYCLE_RUNTIME_H
#define CLAW_GRAPHICS_MANAGER_LIFECYCLE_RUNTIME_H
#include "GraphicsManagerConstructionRuntime.h"
#include "PaletteResourceRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_GRAPHICS_MANAGER_BYTES 2180u
#define CLAW_GRAPHICS_MODE_DESCRIPTOR_BYTES 108u
typedef struct ClawGraphicsManagerLifecycleGlobals {
    uint32_t sharedDevice;        //541398, reused without AddRef and not cleared by teardown.
    uint32_t cooperativeHolder;   //541374, actual live manager token.
    uint32_t channelShift[3];     //54135c/360/364 source mask first-bit positions.
    uint32_t channelReduction[3]; //541368/36c/370 =8-popcount, with original wrapping.
} ClawGraphicsManagerLifecycleGlobals;
typedef struct ClawGraphicsManagerLifecycleContext {
    ClawSceneActorHost scene;
    ClawGraphicsManagerLifecycleGlobals *globals;
    //Optional frozen palette context; same raw heap and cooperative alias.
    ClawPaletteResourceContext *palette;
    uint32_t maximumOperations, fault;
} ClawGraphicsManagerLifecycleContext;
typedef struct ClawGraphicsManagerLifecycleCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    //Source local pointer argument[i] is normalized0 with localMask bit i.
    //Heap pointers remain actual tokens. Buffers expose synchronous local bytes.
    uint32_t localMask, bufferCount;
    uint32_t *buffers[2];
    uint32_t bufferBytes[2];
} ClawGraphicsManagerLifecycleCall;
typedef uint32_t (*ClawGraphicsManagerLifecycleDependency)(ClawGraphicsManagerLifecycleContext *,
                                                           const ClawGraphicsManagerLifecycleCall *, void *);
//Raw original thiscall ABI:4bc220(HWND,GUID,width,height,bpp,coopFlags),RET24;
//4bc400(restoreFlag),RET4;4bc1b0 destructor(no manager free);
//4bcc50 enum,4bcda0 stdcall(descriptor,ignored),4bcde0(modeA,modeB);
//4bd1c0(width,height,bpp),4bd0c0 current pixel-format;
//4bc4b0 surfaces,4bc9d0 palettes;4bc5f0(flags)/4bc610/4b9540 surface cleanup;
//4f551d raw array destructor,4f5192 list destructor.
//Existing constructor4bc120 and CArray/CPtrList/palette cores compose their
//frozen APIs. Global mode array must be a live five-word span at541378;
//initialize it through actual4bc0e0/frozen array ctor, not guessed storage.
//DirectDrawCreate is import slot546850(GUID,&manager[0],0). COM functions use
//actual vtable identities with receiver0 and interface token in argument0.
//Physical COM/window/descriptors and polymorphic unknown deletions are named
//services, not fake successful device startup. fault1 missing span/service,
//2 ABI or unsafe bound,3 runaway traversal; preserve reached source prefixes.
//Return1 recognizes covered completed body; original meaningful EAX via result.
uint32_t claw_graphics_manager_lifecycle_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                               uint32_t argumentCount, ClawGraphicsManagerLifecycleContext *,
                                               ClawGraphicsManagerLifecycleDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
