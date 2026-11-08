#pragma once
#include "SceneActorRuntime.h"
#include "SpriteGeometry.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawActorWrapperContext {
    ClawSceneActorHost scene;
    uint32_t fault;
} ClawActorWrapperContext;
typedef struct ClawActorWrapperCall {
    uint32_t function, receiver, argumentCount, arguments[2], localMask;
    /*4f6286 args(nameToken,automaticOutputToken0),mask2. Output starts0.
   Service writes *output and returns the original bool independently; the
   two source getters ignore that bool and return exactly the output word.*/
    uint32_t *output;
} ClawActorWrapperCall;
typedef uint32_t (*ClawActorWrapperDependency)(ClawActorWrapperContext *, const ClawActorWrapperCall *, void *);
/*406240(actor) hitbounds+128 /406290(actor) movebounds+118, receiveractor,
 no stackargs; nullimage174 preserves rectangle. Both compose frozen4061e0
 numeric behavior while retaining source scalar read/store order and aliasing.
 40f6c0(actor,left,top,right,bottom) thiscall RET16, unmodified raw words.
 4209d0(actor,imageID) thiscall RET4; signed inclusive root64/68 range and
 absolute image table root14 (including null/gaps); nullroot170 changesnothing.
 4061b0(registry,nameToken) thiscall RET4 (dictionary registry+10).
 4062e0(embeddedWrapper,nameToken) thiscall RET4, wrapper+4 -> actor+C ->
 parent+2c ANIregistry -> dictionary+10; it does not accept actor as receiver.
 Unknown entry/invalid argcount returns0 unchanged. Recognized returns1,
 including diagnostic fault1 missing span/service; fault isn't original return.
 result exposes meaningful EAX only for4061b0/4062e0; others are originalvoid.
 Legacy scene.call namedlookup may return resolvedtoken as its established ABI;
 rich dependency exposes original dictionary bool/output distinctions above.*/
uint32_t claw_actor_wrapper_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                  uint32_t argumentCount, ClawActorWrapperContext *, ClawActorWrapperDependency, void *,
                                  uint32_t *result);
#ifdef __cplusplus
}
#endif
