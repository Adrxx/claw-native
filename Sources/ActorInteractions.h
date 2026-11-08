#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t token;
    uint32_t actor[128], primary[93], secondary[93], contact[93];
} ClawInteractionActor;
typedef struct {
    uint32_t function, actorToken, peerToken, logicToken;
    uint32_t kind; // 0 secondary hit; 1 contact (portable event tag).
} ClawActorInteractionCall;
typedef void (*ClawActorInteractionDependency)(ClawInteractionActor *actors, size_t count,
                                               const ClawActorInteractionCall *, void *);
// Complete original4c9390 scene pair scan over a caller-provided fixed list
// order. Callback bodies are explicit dependencies; they may mutate actor/logic
// buffers but must not alter list membership/order or represented identities.
// Original pointer fields actor6c/70/78 correspond to these three logic buffers.
// Includes masks/flags, inclusive wrapped world rectangles, contact-before-hit,
// generic flag8 damage and original cached-mask/reverse-pass ordering.
// Return1 on completion,0 for invalid native list/size; original entry is void.
uint32_t claw_actor_interactions(ClawInteractionActor *, size_t count, ClawActorInteractionDependency, void *);
// Complete original4c9ae0 direct damage/hit dispatch without pair mask/geometry
// gating. Return1 on completion,0 for invalid native indices (safety extension).
uint32_t claw_actor_interaction_hurt(ClawInteractionActor *, size_t count, uint32_t defenderIndex,
                                     uint32_t attackerIndex, ClawActorInteractionDependency, void *);
// Complete original4c95b0: translated hit(defender)/attack(attacker) overlap;
// INT_MIN left sentinels disable rectangles. Touching edges count as overlap.
uint32_t claw_actor_interaction_overlap(const ClawInteractionActor *defender, const ClawInteractionActor *attacker);
#ifdef __cplusplus
}
#endif
