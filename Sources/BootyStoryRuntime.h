#ifndef CLAW_BOOTY_STORY_RUNTIME_H
#define CLAW_BOOTY_STORY_RUNTIME_H
#include "BootyProgressionRuntime.h"
#include "ActorAnimationRuntime.h"
#include "SceneDisplayRuntime.h"
#include "BootyResultsRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Story child364bytes/VT50b544. All three story gameplay actors use original
// generic109word actor+primary93words; there is no specialized private ctor.
// Raw aliases remain in scene heap:manager5371fc,stage53720c,ANI5430c4,
// audio532c0c/10,mode5349a0,step5349a4,loopCString53499c,timer523b50.
typedef struct ClawBootyStoryContext {
    ClawSceneActorHost scene;
    ClawBootyProgressionContext *progression;
    uint32_t composeProgression, composeAnimation, composeCreation, maximumSteps, fault;
    uint32_t composeFrame; // Optional frozen4c8fc0+4c91d0 composition over raw aliases.
    uint32_t composeImages;
    ClawSceneDisplayContext *display;
    ClawBootyResultsContext *results;
} ClawBootyStoryContext;
typedef struct ClawBootyStoryCall {
    uint32_t function, receiver, argumentCount, arguments[40];
    const char *name;
    uint32_t localMask, bufferCount;
    void *buffers[3];
    uint32_t bufferBytes[3];
} ClawBootyStoryCall;
typedef uint32_t (*ClawBootyStoryDependency)(ClawBootyStoryContext *, const ClawBootyStoryCall *, void *);
// Actor callbacks40c150/40d1a0/40c4f0 actualcdecl(actor):receiver0,args[actor].
// Storyinitializer40b860(app,level,previousMode);enter40bca0(previousMode),
// input40bf30(key,unused),departure40bd50(nextMode),delete40b600(flags).
// Surface4ca9e0(wrapper),4caa20(copy),4caa90(noargs),4ca900(file,which),
//4d4190(file),4b95b0(graphics,data,kind,size,variant) source-owned here.
// Other elected entries take noargs. Shared40df60/48ffa0/48f470 are Results
// dependencies unless borrowed results supplied; exact48ffa0 ABI is4words,
//story(title,1,0,1). Borrowed display/resources compose source bodies; physical
//BMP/PCX/PID codecs4bdda0(3)/4bebc0(3)/4bf680(4) remain named services.
// Source meaningful EAX separate;fault1 missing span/service,2 matched unsafe
// table/null prefix,3 ABI/guard or frozen helper safety extension.
uint32_t claw_booty_story_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                                ClawBootyStoryContext *, ClawBootyStoryDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
