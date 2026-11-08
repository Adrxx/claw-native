#ifndef CLAW_BOOTY_PROGRESSION_RUNTIME_H
#define CLAW_BOOTY_PROGRESSION_RUNTIME_H
#include "SpecialCommandRuntime.h"
#include "SinglePlayerSceneRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Default child0x158/VT50b43c; source807c elects story child0x16c/VT50b544 (mode3),
// then results child0x184/VT50b494 when story reports mode1.
// Movie42b140 requires caller-owned0x86a8-byte automatic storage at scratchToken;
// seed is preserved, and physical movie/graphics services remain explicit.
typedef struct ClawBootyProgressionContext {
    ClawSceneActorHost scene;
    ClawSpecialCommandGlobals *globals;
    ClawSinglePlayerSceneContext *base;
    uint32_t scratchToken, composeBase, maximumSteps, fault;
} ClawBootyProgressionContext;
typedef struct ClawBootyProgressionCall {
    uint32_t function, receiver, argumentCount, arguments[40];
    const char *name;
    uint32_t localMask, bufferCount;
    void *buffers[3];
    uint32_t bufferBytes[3];
} ClawBootyProgressionCall;
typedef uint32_t (*ClawBootyProgressionDependency)(ClawBootyProgressionContext *, const ClawBootyProgressionCall *,
                                                   void *);
// Public full426e30 only807c args=(0,807c,0); no callable invented interior label.
// Default initializer40b6a0(app,level,previous),enter40b720(previous),
// input40b7d0(key,unused). Movie42b140(app receiver,level);deleting40afa0(flags),
// depart48d320(nextMode);base enter40af30(previousMode). Zero-return40af40 takes2words;40af50 takes3words.
// Other exported methods take no arguments.
// Unknown0;requirefault0. Fault1 missing service/span,2 unsafeprefix,3 ABI/guard.
// Meaningful originalEAX separate; additional results/story/progression services
// are actual addressed dependencies, never a synthetic next-level increment.
uint32_t claw_booty_progression_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                      uint32_t argumentCount, ClawBootyProgressionContext *,
                                      ClawBootyProgressionDependency, void *, uint32_t *result);
uint32_t claw_booty_progression_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
