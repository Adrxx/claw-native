#ifndef CLAW_STATE_FIVE_RUNTIME_H
#define CLAW_STATE_FIVE_RUNTIME_H
#include "ApplicationLevelProgressionRuntime.h"
#include "PaperRollRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_STATE_FIVE_BYTES 0x2c8u
#define CLAW_STATE_FIVE_WORDS 178u
// Original mode5 is the retail STATES_MENU controller, not a native custom UI.
// Constructor and common application transition remain in frozen modules.
// Globals537b58,537b48..54,528a60/64/68,525508,54132c,53720c,
// 5371fc,537200,532c0c/10 are borrowed live raw source aliases.
typedef struct ClawStateFiveContext {
    ClawSceneActorHost scene;
    ClawApplicationLevelProgressionContext *application;
    ClawSinglePlayerSceneContext *base;
    ClawSpecialCommandContext *special;
    ClawBootyResultsContext *results;
    ClawBootyStoryContext *story;
    ClawSceneLifecycleContext *lifecycle;
    ClawSceneActorGlobals *actors;
    ClawPaperRollContext *paper;
    uint32_t composeBase, composeShared, composeScene, maximumOperations, fault;
} ClawStateFiveContext;
typedef ClawBootyProgressionCall ClawStateFiveCall;
typedef uint32_t (*ClawStateFiveDependency)(ClawStateFiveContext *, const ClawStateFiveCall *, void *);
// Raw thiscall methods use actual stack words. Input45ba50 takes two words;
// mouse45bd90 takes three; accelerator45e990 takes two.
// Image45f940 is cdecl with one owning CString data token/RET0;45be10
// is thiscall(dataToken,outputCStringCell,outputFrameCell)/RET12.
// Overlay45fbb0 is cdecl5 words. The52-byte page child VT50e8e4
// exposes14 slots; paper descriptor transport contains44 defined bytes.
// EAX is separate from covered/fault status.
// Actual widget/IFC, resource, physical DD/GDI/audio/window/media transports
// remain named address boundaries where not composed. Never return dummy
// success for a missing meaningful subtree. Stack locals use rich localMask.
uint32_t claw_state_five_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                               ClawStateFiveContext *, ClawStateFiveDependency, void *, uint32_t *result);
uint32_t claw_state_five_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
