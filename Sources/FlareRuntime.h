#ifndef CLAW_FLARE_RUNTIME_H
#define CLAW_FLARE_RUNTIME_H
#include "ActorAnimationRuntime.h"
#include "GameImageRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_FLARE_PRIVATE_BYTES 0x4cu
#define CLAW_FLARE_PRIVATE_WORDS 19u
typedef struct ClawFlareContext {
    ClawSceneActorHost scene;
    ClawActorAnimationGlobals *animation;
    ClawGameImageGlobals *images;
    uint32_t composeAnimation, composeFSM, composeEffects, maximumSteps, fault;
} ClawFlareContext;
typedef struct ClawFlareCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    const char *name;
} ClawFlareCall;
typedef uint64_t (*ClawFlareDependency)(ClawFlareContext *, const ClawFlareCall *, void *);
void claw_flare_defaults(ClawFlareContext *);
//457f00(actor) cdecl Flare;458010(actor) cdecl WolvingtonLFX companion;
//458120(actor) ECX private ctor RET4;4581c0()/458530()/458570() ECX private;
//458280(state) ECX private RET4;4dc870(private) cdecl common FSM;
//4041b0(unusedName),484d90(deleteFlag),4c9e30(unusedName) ECX private RET4;
//456030()/4c96b0()/4bb030() ECX private;4ce850(pointer) ECX image manager RET4.
//Raw class table537ac0, ID-name CString table537698/name trie537668 come
//from frozen LogicStateRegistry bootstrap. No guessed IDs or name literals.
//Init reads live app5371fc->config+768. Main actor/private19/logic93 graph
//stays caller-owned. Image mode2 selects original effects; this module does
//not approximate its physical pixel implementation or invent a Flare TTL.
//Known identity returns1; requirefault0. Unknown0. Native safety1=missing
//span/service,2=ABI/bounded traversal rejection. Meaningful EAX separate.
uint32_t claw_flare_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                          ClawFlareContext *, ClawFlareDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
