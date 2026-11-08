#pragma once
#include "HumanEnemy.h"
#ifdef __cplusplus
extern "C" {
#endif
// Bounded common entry controllers required by Human/Soldier vtables. Reuses
// existing Human pointer views. Unknown multi-argument strike overloads remain
// explicit caller dependencies; no arguments are silently discarded.
uint32_t claw_common_enemy_entry(ClawGenericEnemy *, ClawHumanEnemyContext *, uint32_t function, uint32_t argument,
                                 ClawGenericEnemyDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
