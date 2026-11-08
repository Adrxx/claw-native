#ifndef CLAW_PLAYER_PROJECTILE_RUNTIME_H
#define CLAW_PLAYER_PROJECTILE_RUNTIME_H
#include "BulletLogic.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerProjectileGlobals {
    uint32_t tick, animationDelta, magicDisabled, ownerToken, audioEnabled, masterVolume;
} ClawPlayerProjectileGlobals;
typedef struct ClawPlayerProjectileContext {
    ClawSceneActorHost scene;
    ClawPlayerProjectileGlobals *globals;
    // Borrowed frozen Bullet/shared-physics adapter. Its generic identities are
    // refreshed from the live raw receiver; actual registry/state profiles remain
    // caller supplied. Only the original allocation prefix is imported/exported.
    ClawBulletContext *bullet;
    uint32_t composeAnimation, fault;
} ClawPlayerProjectileContext;
typedef struct ClawPlayerProjectileCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawPlayerProjectileCall;
typedef uint64_t (*ClawPlayerProjectileDependency)(ClawPlayerProjectileContext *, const ClawPlayerProjectileCall *,
                                                   void *);
// Entry486e70 is the exact unsigned wrapped deadline extender; args=(duration),
// receiver0. Reads raw outer clock541328 and updates raw53c260 through scene.
// It has no external services. Result is the computed candidate, even if the
// existing deadline wins the comparison.
// Wrapper cdecl actor: receiver0,args[0]=actor. Constructor thiscall(actor).
// Other owned methods use raw private receiver and optional state/delete arg.
// Successful support/completion is separate from recovered meaningful EAX.
// Physical allocation, named creation, registry, sound and scene transport
// remain explicit services. fault1 missing raw span/service;2 source unsafe
// prefix;3 bounded loop/domain rejection. No guessed success on failure.
uint32_t claw_player_projectile_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                      uint32_t argumentCount, ClawPlayerProjectileContext *,
                                      ClawPlayerProjectileDependency, void *, uint32_t *result);
uint32_t claw_player_projectile_private_bytes(uint32_t registeredCallback);
#ifdef __cplusplus
}
#endif
#endif
