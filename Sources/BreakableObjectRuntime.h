#ifndef CLAW_BREAKABLE_OBJECT_RUNTIME_H
#define CLAW_BREAKABLE_OBJECT_RUNTIME_H
#include "SceneActorRuntime.h"
#include "WorldLootRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Original raw object graph. PowderKeg allocates0x410, spawned Crate0x418,
// stacked parent0x4c; full actor128/common logic93 spans remain caller-owned.
typedef struct ClawBreakableGlobals {
    uint32_t animationDelta, audioEnabled, audioPosition, crateImageChoice;
    float damageScale, healthScale;
    // Original state-function range descriptors537ea0 (keg),537308 (crate).
    // The documented profile must supply actual runtime registration backing.
    uint32_t kegStates[10], crateStates[10];
} ClawBreakableGlobals;
typedef struct ClawBreakableContext {
    ClawSceneActorHost scene;
    ClawBreakableGlobals *globals;
    ClawWorldLootGlobals *loot;
    uint32_t fault;
} ClawBreakableContext;
typedef struct ClawBreakableCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawBreakableCall;
// Shared generic construction/FSM/states, resource lookup/binding, scene spawn,
// loot, audio and FX remain exact identified dependency calls. Hosts may compose
// frozen modules; unsupported dependencies must not become fabricated no-ops.
// Lookup4f6286 returns resolved metadata token (out pointer transport adapted).
typedef uint64_t (*ClawBreakableDependency)(ClawBreakableContext *, const ClawBreakableCall *, void *);
// Caller args correspond to original stack args; receiver is thiscall ECX, or0
// for cdecl actor callbacks. Return native support status separately from EAX.
// fault1 absent raw span/service,2 invalid ABI/domain are bounded extensions.
uint32_t claw_breakable_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                              ClawBreakableContext *, ClawBreakableDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
