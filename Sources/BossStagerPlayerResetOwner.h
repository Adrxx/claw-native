#ifndef CLAW_BOSS_STAGER_PLAYER_RESET_OWNER_H
#define CLAW_BOSS_STAGER_PLAYER_RESET_OWNER_H
#include "ClawRuntime.h"
#include "LiftThrowRuntime.h"
#include "PowerupObjectRuntime.h"
#include "RauxRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Borrow the live shared heap and global address mapping through memory.bytes.
// No memory.call fallback is used: the finite eight-helper graph is elected here.
// Physical allocation and animation resource/audio service use scene's existing
// native providers. The globals at537e88/537204/534e60..74 remain caller-owned.
// Completion is separate from semantic void; fault is a native diagnostic.
uint32_t claw_boss_stager_player_reset_source(ClawHost *memory, ClawSceneActorHost scene,
    ClawActorAnimationGlobals *animation, uint32_t *fault);
#ifdef __cplusplus
}
#endif
#endif
