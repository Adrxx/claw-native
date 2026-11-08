#ifndef CLAW_WORLD_PLANE_RUNTIME_H
#define CLAW_WORLD_PLANE_RUNTIME_H
#include "SceneCameraRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Original plane size0x158 bytes (86 words), WWD record0xa0 bytes (40 words).
// Scene lookup returns stable aligned writable word spans. Name byte helpers
// lookup(token&~3,1) then access byte(token&3), retaining the shared host ABI.
typedef struct ClawWorldPlaneContext {
    ClawSceneActorHost scene;
    uint32_t fault;
} ClawWorldPlaneContext;
typedef struct ClawWorldPlaneCall {
    uint32_t function, receiver, argumentCount, arguments[4];
    //4f6286 temporary name is adapted as text; original output pointer becomes
    // the returned resource token. Other arguments retain raw pointer identity.
    const char *name;
} ClawWorldPlaneCall;
typedef uint32_t (*ClawWorldPlaneDependency)(ClawWorldPlaneContext *, const ClawWorldPlaneCall *, void *);
// Exact4d03b0 constructor(parent,id,flags), preserves unwritten raw words.
// Returns receiver token on success; constructor performs no allocations.
uint32_t claw_world_plane_construct(uint32_t receiver, uint32_t parent, uint32_t id, uint32_t flags,
                                    ClawWorldPlaneContext *);
// Whole4d0450(record,decodedWorldBase,inclusiveViewport). Resource-array
// insertion4f582f and object/grid initialization4d1620 remain explicit services.
// Tile/row allocations use scene.allocate and preserve original ownership.
// Frozen4d0a60 clamp is composed, not approximated. Returns original0/1.
uint32_t claw_world_plane_load(uint32_t receiver, uint32_t recordToken, uint32_t worldBaseToken, uint32_t viewportToken,
                               ClawWorldPlaneContext *, ClawWorldPlaneDependency, void *);
// Exact4d0cd0 dimensions/extent/bitshift setter. Both shift fields derive
// from width in the original, including when height differs.
uint32_t claw_world_plane_tile_size(uint32_t receiver, uint32_t width, uint32_t height, ClawWorldPlaneContext *);
// Whole4cb7b0 world add-plane(record,decodedWorldBase,unused): allocates0x158,
// constructs with parent=world+c,id=world+3c,flags0, loads with world+10 rect,
// inserts at current world+3c through original4f582f. Last flags1 plane wins
// main-plane token/index. Failure delegates original deleting destructor.
uint32_t claw_world_plane_add(uint32_t worldToken, uint32_t recordToken, uint32_t worldBaseToken, uint32_t unused,
                              ClawWorldPlaneContext *, ClawWorldPlaneDependency, void *);
#ifdef __cplusplus
}
#endif
#endif
