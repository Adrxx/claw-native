#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
// Complete original actor/common-logic/enemy allocation snapshots. Pointer
// fields are identities, never native pointers. Contact is actor+0x78.
typedef struct {
    uint32_t actor[128], primary[93], secondary[93], contact[93], enemy[264];
} ClawGenericEnemy;
// Resolved original state registry entry. IDs are assigned by original runtime
// registration, so the host must supply its verified table, not guessed numbers.
typedef struct {
    int32_t state;
    uint32_t function, nameToken;
    const char *name;
} ClawGenericEnemyState;
typedef struct {
    uint32_t actorToken, primaryToken, secondaryToken, contactToken, enemyToken;
    // soundRegistryToken is the registry at actor.scene+0x28 -> manager+0x10;
    // its historical API label does not assert these GAME_ entries are audio.
    uint32_t sceneToken, tileManagerToken, soundRegistryToken, playerToken;
    uint32_t playerActor[128], platformActor[128];
    uint32_t tick, animationDelta, levelWord, forcedRandom, hitMode;
    // Original globals 0x513e10..0x513e6f; the defaults helper copies the
    // hash-pinned image values. Runtime tuning remains caller-owned.
    uint32_t defaults[24];
    uint32_t virtualFunctions[64];
    const ClawGenericEnemyState *states;
    size_t stateCount;
    // Inline <=32-bit bitsets are stored in enemy+300. Larger valid bitsets
    // use this supplied backing, corresponding to the original +300 token.
    uint32_t *bitWords;
    size_t bitWordCount;
    uint32_t emptyStringToken, bitHandlerToken;
} ClawGenericEnemyContext;
typedef struct {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawGenericEnemyCall;
// Original integer EAX return in low32, or original floating return encoded as
// IEEE double bits when an event explicitly requires it. May mutate snapshots.
typedef uint64_t (*ClawGenericEnemyDependency)(ClawGenericEnemy *, ClawGenericEnemyContext *,
                                               const ClawGenericEnemyCall *, void *);
void claw_generic_enemy_context_defaults(ClawGenericEnemyContext *);
uint32_t claw_generic_enemy_construct(ClawGenericEnemy *, ClawGenericEnemyContext *, ClawGenericEnemyDependency,
                                      void *);
uint32_t claw_generic_enemy_tick(ClawGenericEnemy *, ClawGenericEnemyContext *, ClawGenericEnemyDependency, void *);
uint32_t claw_generic_enemy_dispatch(ClawGenericEnemy *, ClawGenericEnemyContext *, int32_t state,
                                     ClawGenericEnemyDependency, void *);
uint32_t claw_generic_enemy_pre(ClawGenericEnemy *, ClawGenericEnemyContext *, ClawGenericEnemyDependency, void *);
uint32_t claw_generic_enemy_post(ClawGenericEnemy *, ClawGenericEnemyContext *, ClawGenericEnemyDependency, void *);
uint32_t claw_generic_enemy_motion(ClawGenericEnemy *, ClawGenericEnemyContext *, ClawGenericEnemyDependency, void *);
// Invoke a supported recovered common entry by original identity. Unsupported
// entries return0 with no guessed behavior; Rat-specific entries are adapters.
// Return values are native completion/support status; original void/zero-return
// callback EAX is not substituted with a claimed gameplay return value.
uint32_t claw_generic_enemy_entry(ClawGenericEnemy *, ClawGenericEnemyContext *, uint32_t function, uint32_t argument,
                                  ClawGenericEnemyDependency, void *);
#ifdef __cplusplus
}
#endif
