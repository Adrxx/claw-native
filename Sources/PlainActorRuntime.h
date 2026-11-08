#pragma once
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlainActorCreate {
    uint32_t id, z, entryToken, flags;
} ClawPlainActorCreate;
// Original4c8a20/4c8b90: non-animated0x168 actor, primary0x174, forcedX/Y0.
// Host reserves128-word snapshot padding for the interface, preserving every
// word above original0x168 bytes. Registry/gameplay/destruction/physical allocation
// remain host services. Meaningful return is the original actor identity.
// Missing named metadata gives native fault1 before creation; the original
// dereferences null after construction. That safety extension is not parity.
uint32_t claw_plain_actor_create(uint32_t container, ClawPlainActorCreate, ClawSceneActorHost, uint32_t *fault);
uint32_t claw_plain_actor_create_named(uint32_t container, ClawPlainActorCreate, uint32_t nameToken, ClawSceneActorHost,
                                       uint32_t *fault);
#ifdef __cplusplus
}
#endif
