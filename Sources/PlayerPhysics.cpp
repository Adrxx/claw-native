#include "PlayerPhysics.h"
#include <cmath>
#include <cstddef>
#include <cstring>

#pragma STDC FP_CONTRACT OFF
static_assert(offsetof(ClawPlayerPhysics, stopped) == 0xa0, "Physics layout");
static_assert(offsetof(ClawPlayerPhysics, remainder) == 0xa8, "Physics layout");
static_assert(sizeof(ClawPlayerPhysics) == 0xf0, "Physics layout");

// Each operation rounds independently, matching the original CRT's 53-bit
// precision. Avoid fused operations and host-dependent float-to-int casts.
static double add(double a, double b) {
    volatile double r = a + b;
    return r;
}
static double subtract(double a, double b) {
    volatile double r = a - b;
    return r;
}
static double multiply(double a, double b) {
    volatile double r = a * b;
    return r;
}
static double divide(double a, double b) {
    volatile double r = a / b;
    return r;
}

static uint32_t ftolLow(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    const int exponent = int((bits >> 52) & 0x7ff) - 1023;
    if (exponent < 0 || exponent >= 63)
        return 0;
    uint64_t magnitude = (bits & 0x000fffffffffffffULL) | 0x0010000000000000ULL;
    magnitude = exponent >= 52 ? magnitude << (exponent - 52) : magnitude >> (52 - exponent);
    return bits >> 63 ? 0u - uint32_t(magnitude) : uint32_t(magnitude);
}

extern "C" void claw_physics_construct(ClawPlayerPhysics *p) {
    // Original global physics constructor 0x415ab0. Delta/unused fields are
    // not written by it; a fresh game receives their original zeroed BSS values.
    p->elapsed = p->timestep = 0;
    p->stopped = 0;
    for (int axis = 0; axis < 3; ++axis) {
        p->acceleration[axis] = p->velocity[axis] = p->position[axis] = p->remainder[axis] = 0;
        p->minimum[axis] = -2147483647.0;
        p->maximum[axis] = p->maximumDelta[axis] = p->maximumVelocity[axis] = 2147483646.0;
    }
}

extern "C" uint32_t claw_physics_initialize(ClawPlayerPhysics *p, const double *velocity, const double *acceleration,
                                            double timestep) {
    // Original 0x420a40 leaves bounds, delays, stopped and remainders untouched.
    p->elapsed = 0;
    p->timestep = timestep;
    for (int axis = 0; axis < 3; ++axis) {
        p->velocity[axis] = velocity[axis];
        p->acceleration[axis] = acceleration[axis];
        p->position[axis] = 0;
    }
    return 1;
}

extern "C" void claw_physics_limit_velocity(ClawPlayerPhysics *p, double maximum) {
    // Original 0x420ad0.
    for (int axis = 0; axis < 3; ++axis)
        p->maximumVelocity[axis] = maximum;
}

static double adjustedVelocity(double velocity, double acceleration, double distance) {
    double radicand = subtract(multiply(velocity, velocity), multiply(multiply(distance, acceleration), -2.0));
    if (radicand < 0)
        radicand = 0;
    const double magnitude = std::sqrt(radicand);
    return velocity <= 0 ? -magnitude : magnitude;
}

extern "C" void claw_physics_update(ClawPlayerPhysics *p, double seconds) {
    // Original 0x403b40: the timer advances even while motion is stopped.
    p->timestep = seconds;
    p->elapsed = add(seconds, p->elapsed);
    if (p->stopped)
        return;
    for (int axis = 0; axis < 3; ++axis) {
        const double accelerationStep = multiply(seconds, p->acceleration[axis]);
        double delta = multiply(subtract(p->velocity[axis], multiply(accelerationStep, -0.5)), seconds);
        p->delta[axis] = delta;
        double limitedDelta = 0;
        bool limited = false;
        if (delta > p->maximumDelta[axis]) {
            limitedDelta = p->maximumDelta[axis];
            limited = true;
        } else if (delta < -p->maximumDelta[axis]) {
            limitedDelta = -p->maximumDelta[axis];
            limited = true;
        }
        if (limited) {
            p->delta[axis] = limitedDelta;
            if (p->acceleration[axis] != 0) {
                const double distance = subtract(add(limitedDelta, p->position[axis]), p->position[axis]);
                p->velocity[axis] = adjustedVelocity(p->velocity[axis], p->acceleration[axis], distance);
            }
        }
        const double oldPosition = p->position[axis];
        const double nextPosition = add(p->position[axis], p->delta[axis]);
        p->position[axis] = nextPosition;
        double bound = 0;
        bool bounded = false;
        if (nextPosition > p->maximum[axis]) {
            bound = p->maximum[axis];
            bounded = true;
        } else if (nextPosition < p->minimum[axis]) {
            bound = p->minimum[axis];
            bounded = true;
        }
        if (bounded) {
            if (p->acceleration[axis] != 0)
                p->velocity[axis] =
                    adjustedVelocity(p->velocity[axis], p->acceleration[axis], subtract(bound, nextPosition));
            p->position[axis] = bound;
            p->delta[axis] = subtract(bound, oldPosition);
        } else {
            p->velocity[axis] = add(accelerationStep, p->velocity[axis]);
        }
        if (p->velocity[axis] > p->maximumVelocity[axis])
            p->velocity[axis] = p->maximumVelocity[axis];
    }
}

static uint32_t pixel(ClawPlayerPhysics *p, uint32_t *scratch, int axis) {
    // Original 0x420cd0/0x420d50, including fractional accumulation order.
    if (p->stopped)
        return 0;
    const double delta = p->delta[axis];
    const double wholeDelta = double(int32_t(ftolLow(delta)));
    const double accumulated = add(subtract(delta, wholeDelta), p->remainder[axis]);
    *scratch = ftolLow(add(delta, accumulated));
    p->remainder[axis] = subtract(accumulated, double(int32_t(ftolLow(accumulated))));
    return *scratch;
}
extern "C" uint32_t claw_physics_pixel_x(ClawPlayerPhysics *p, uint32_t *scratch) {
    return pixel(p, scratch, 0);
}
extern "C" uint32_t claw_physics_pixel_y(ClawPlayerPhysics *p, uint32_t *scratch) {
    return pixel(p, scratch, 1);
}

extern "C" double claw_physics_retarget(ClawPlayerPhysics *p, double x, double y, double z) {
    // Original 0x420dd0. Keep the original addition order, threshold and zero
    // distance return of 1.0; replacing this with a textbook jump formula changes
    // the initial vertical velocity and subsequent integer positions.
    const double dx = subtract(x, p->position[0]);
    const double dy = subtract(y, p->position[1]);
    const double dz = subtract(z, p->position[2]);
    const double ax = p->acceleration[0], ay = p->acceleration[1], az = p->acceleration[2];
    const double dot = subtract(subtract(-multiply(ax, dx), multiply(ay, dy)), multiply(az, dz));
    const double accelerationSquared = add(add(multiply(ax, ax), multiply(ay, ay)), multiply(az, az));
    const double distanceSquared = add(add(multiply(dx, dx), multiply(dy, dy)), multiply(dz, dz));
    const double speed = std::sqrt(multiply(
        subtract(std::sqrt(multiply(multiply(distanceSquared, accelerationSquared), 4.0)), multiply(dot, -2.0)), 0.5));
    if (speed < 0.1) {
        p->velocity[0] = p->velocity[1] = p->velocity[2] = 0;
        return 1.0;
    }
    const double quarterAcceleration = multiply(accelerationSquared, 0.25);
    if (-0.1 <= quarterAcceleration && quarterAcceleration <= 0.1) {
        const double distance = add(add(std::abs(dx), std::abs(dy)), std::abs(dz));
        p->velocity[0] = multiply(divide(dx, distance), speed);
        p->velocity[1] = multiply(divide(dy, distance), speed);
        p->velocity[2] = multiply(divide(dz, distance), speed);
    } else {
        const double durationSquared =
            divide(subtract(multiply(speed, speed), dot), add(quarterAcceleration, quarterAcceleration));
        const double duration = std::sqrt(durationSquared);
        p->velocity[0] = divide(subtract(dx, multiply(multiply(durationSquared, ax), 0.5)), duration);
        p->velocity[1] = divide(subtract(dy, multiply(multiply(durationSquared, ay), 0.5)), duration);
        p->velocity[2] = divide(subtract(dz, multiply(multiply(durationSquared, az), 0.5)), duration);
    }
    return speed;
}
