#ifndef CLAW_V13_ENEMY_DEATH_SOUND_H
#define CLAW_V13_ENEMY_DEATH_SOUND_H
#include <stdint.h>
static inline uint32_t claw_v13_enemy_dead_bits(uint32_t bits) {
    return bits & 0xfffffffe;
}
static inline uint32_t claw_v13_sound_elapsed(uint32_t tick, uint32_t last, uint32_t interval) {
    return (uint32_t)(tick - last) >= interval;
}
#endif
