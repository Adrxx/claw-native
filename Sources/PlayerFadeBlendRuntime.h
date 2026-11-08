#ifndef CLAW_PLAYER_FADE_BLEND_RUNTIME_H
#define CLAW_PLAYER_FADE_BLEND_RUNTIME_H
#include "PlayerFadeRuntime.h"
#include "ActorDestruction.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerFadeBlendContext {
    ClawPlayerFadeContext *fade;
    uint32_t temporaryStringToken, emptyStringToken;
    // Explicit seed for source4ed800's unwritten local capture pixel pointer
    // when effect+40 is absent. Ordinary positive fade-out calls pre first.
    uint32_t uninitializedCapturePixelToken;
} ClawPlayerFadeBlendContext;
// Uses frozen fade host/global/fault and dependency ABI. New whole4ed800 and
// helper4ee170 cover positive gradient palette-byte loops; gradient<=0 composes
// frozen PlayerFadeRuntime. Whole circle factory4ec050 type1 also covers its
// diagnostic CString lifetime using4f65f2/4f6480/4ec6b0 and frozen destruction.
// 4ee170 args:row,radiusSquared,radius,palettePixels,destPixels,sourcePixels.
// 4ec6b0 arg0 is its by-value CString DATA token; temporaryStringToken represents
// the source stack object. 4f65f2 args:stringToken;4f6480 args:length.
// Source palettebuilder4c6bd0 takes(palette256four-bytecolors,gradientWidth,
// packedTargetColor),RET12.4c7580 is cdecl(palette,channel0,channel1,channel2).
// Palette ctor4c76d0/allocate4c76f0 and arrayresize4dee30 are also exposed.
// Palette reset4c78d0/destructor4c76e0, owner remove4c7510/clear4c6270
// and embedded owner destruction4c61f0 recover actual heap free ordering.
// Unknown public entry returns0 unchanged. Recognized fault propagates through
// fade->fault:1 missing graph/service;2 unsafe/unbounded domain;3 other factory
// types. No original safe-null/overflow-return claim is made.
uint32_t claw_player_fade_blend_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                      uint32_t argumentCount, ClawPlayerFadeBlendContext *, ClawPlayerFadeDependency,
                                      void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
