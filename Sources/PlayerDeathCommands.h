#ifndef CLAW_PLAYER_DEATH_COMMANDS_H
#define CLAW_PLAYER_DEATH_COMMANDS_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerDeathCommandGlobals {
    uint32_t playerToken, masterVolume, keyboardToken, mouseToken;
    ClawClockState clock;
    ClawFrameClock stage, animation;
} ClawPlayerDeathCommandGlobals;
// Exact branches of application command entry426e30 for803a/8006.
// Run after posted messages are dequeued, outside the damage callback.
// Returns1 for either recognized command, even when respawn gates reject it.
// Other commands return0 untouched (bounded native scope).
uint32_t claw_player_death_command(uint32_t applicationToken, uint32_t command, ClawPlayerDeathCommandGlobals *globals,
                                   ClawSceneActorHost host, uint32_t *fault);
// Complete respawn controller46be40. Its player primary callback is invoked
// immediately with logic23, followed by cleanup and two scene frame passes.
uint32_t claw_player_respawn(uint32_t gameStateToken, ClawPlayerDeathCommandGlobals *globals, ClawSceneActorHost host,
                             uint32_t *fault);
// Transition428c40 bounded to new states5/12 (the game-over branches).
// State constructors/subobject services, virtual UI/resource lifecycle,
// renderer/plane/input services remain explicit host.call dependencies.
// Retained-state history and all controller-owned mutations are recovered.
uint32_t claw_player_game_over_transition(uint32_t applicationToken, uint32_t newState, uint32_t parameter,
                                          uint32_t retainPrevious, ClawPlayerDeathCommandGlobals *globals,
                                          ClawSceneActorHost host, uint32_t *fault);
// Additive source428c40 composition for original new types3/8. The constructor
// callback executes the elected allocation/inline constructor in the same raw
// heap and returns its token (0 preserves source allocation failure). It receives
// the original fourth transition word, even where the common path ignores it.
// Types5/12 still use the existing frozen constructors; no callback is consulted.
// Common outgoing lifecycle/history/a0 bypass/reset/init/enter/footer is shared.
typedef uint32_t (*ClawApplicationStateConstructor)(uint32_t application, uint32_t newState, uint32_t extraWord,
                                                    ClawSceneActorHost host, uint32_t *fault, void *user);
uint32_t claw_application_state_transition(uint32_t applicationToken, uint32_t newState, uint32_t parameter,
                                           uint32_t retainPrevious, uint32_t extraWord,
                                           ClawPlayerDeathCommandGlobals *globals, ClawSceneActorHost host,
                                           ClawApplicationStateConstructor constructor, void *user, uint32_t *fault);
// Cleanup46e2d0/46e340 marks actors with actor+164 bit2000 for deferred removal.
void claw_player_death_cleanup(uint32_t gameStateToken, ClawSceneActorHost host, uint32_t *fault);
void claw_player_death_cleanup_actor(uint32_t actorToken, ClawSceneActorHost host, uint32_t *fault);
//42c060 destroys retained states in array order, then frees/reset history.
void claw_player_death_clear_history(uint32_t applicationToken, ClawSceneActorHost host, uint32_t *fault);
// Fault1: missing token span;2: allocation/null storage failure;3: unsupported
// transition type. A fault is diagnostic, never a normal original return.
#ifdef __cplusplus
}
#endif
#endif
