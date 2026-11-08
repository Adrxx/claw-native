#pragma once
#include "GenericEnemy.h"
#include "SceneActorRuntime.h"
#include "PlayerDamage.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef ClawGenericEnemy ClawBullet;
// Only private words0..83 belong to the original0x150-byte (336-byte) allocation. The
// wider frozen snapshot storage is preserved as portable compatibility padding.
typedef struct ClawBulletContext {
    ClawGenericEnemyContext *generic;
    const ClawGenericEnemyState *projectileStates;
    size_t projectileStateCount;
    ClawSceneActorHost scene;
    // Without scene.lookup, resource callbacks refresh these exact raw views.
    uint32_t imageRegistryToken, imageRootToken, imageRootHeader[28];
    const uint32_t *imageFrames;
    int32_t imageFrameOrigin;
    size_t imageFrameCount;
    uint32_t imageLeafToken, imageLeafHeader[10];
    uint32_t fault;
} ClawBulletContext;
void claw_bullet_context_defaults(ClawBulletContext *);
uint32_t claw_bullet_construct(ClawBullet *, ClawBulletContext *, ClawGenericEnemyDependency, void *);
uint32_t claw_bullet_tick(ClawBullet *, ClawBulletContext *, ClawGenericEnemyDependency, void *);
uint32_t claw_bullet_entry(ClawBullet *, ClawBulletContext *, uint32_t function, uint32_t argument,
                           ClawGenericEnemyDependency, void *, uint32_t *result);
// After the original interaction host elects CaptainClawHit and binds actor74,
// compose its frozen body. damage.attackerActor is canonical at dependencies.
uint32_t claw_bullet_player_hit(ClawBullet *, ClawBulletContext *, ClawPlayerLocomotion *, ClawPlayerDamageContext *,
                                ClawPlayerInputContext *, ClawPlayerLocomotionDependency, void *);
#ifdef __cplusplus
}
#endif
