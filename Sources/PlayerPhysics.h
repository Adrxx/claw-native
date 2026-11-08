#ifndef CLAW_PLAYER_PHYSICS_H
#define CLAW_PLAYER_PHYSICS_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Original v1.0 physics fields, including the unused word beside stopped.
// Layout is deliberately explicit so differential tests can compare all bytes.
typedef struct {
    double elapsed, timestep;
    double acceleration[3], velocity[3], position[3];
    double minimum[3], maximum[3], delta[3];
    uint32_t stopped, unused;
    double remainder[3], maximumDelta[3], maximumVelocity[3];
} ClawPlayerPhysics;
void claw_physics_construct(ClawPlayerPhysics *physics);
uint32_t claw_physics_initialize(ClawPlayerPhysics *physics, const double *velocity, const double *acceleration,
                                 double timestep);
void claw_physics_limit_velocity(ClawPlayerPhysics *physics, double maximum);
void claw_physics_update(ClawPlayerPhysics *physics, double deltaSeconds);
// Original 0x420dd0 chooses velocity toward a target under current acceleration.
// Returns the original speed result; position and other fields stay unchanged.
double claw_physics_retarget(ClawPlayerPhysics *physics, double x, double y, double z);
// Original conversion returns the low 32 bits of a truncated signed64 value.
// Scratch is the corresponding original global, retained on stopped calls.
uint32_t claw_physics_pixel_x(ClawPlayerPhysics *physics, uint32_t *scratch);
uint32_t claw_physics_pixel_y(ClawPlayerPhysics *physics, uint32_t *scratch);
#ifdef __cplusplus
}
#endif
#endif
