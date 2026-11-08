// Level 1 shared enemy base virtual slots (hit, contact, damage handlers)
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"
#include <cmath>

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x44df60:
        return 0;
    case 0x44cfd0:
        return 0;
    case 0x44d460:
        return 1;
    case 0x44d570:
        return 1;
    case 0x44d5a0:
        return 1;
    case 0x44d700:
        return 1;
    case 0x44d730:
        return 1;
    case 0x44d760:
        return 1;
    case 0x44d9f0:
        return 0;
    case 0x43e9c0:
        return 1;
    case 0x43e9e0:
        return 0;
    case 0x44f3c0:
        return 0;
    case 0x440e20:
        return 1;
    default:
        return -1;
    }
}

uint32_t function_43e9c0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_43e9e0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_44f3c0(Run &run, uint32_t receiver, const uint32_t *arguments);
void function_440e20(Run &run, uint32_t receiver, const uint32_t *arguments);

// Low 32 bits of the original's truncating double to 64-bit conversion (0x4a30e0).
// Out of range and NaN inputs give the integer indefinite value, whose low word is 0.
uint32_t truncateLow(double value) {
    if (!(value >= -9223372036854775808.0))
        return 0;
    if (!(value < 9223372036854775808.0))
        return 0;
    int64_t whole = static_cast<int64_t>(value);
    return static_cast<uint32_t>(whole);
}

// 0x44df60. Picks the death animation name from the registry by the damage kind
// at [[[this+0xc]+0x74]+0x164] (+0x12c actor owner, +0x374 animation result).
uint32_t function_44df60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t flags = run.get(run.get(run.get(receiver + 0xc) + 0x74) + 0x164);
    uint32_t localHigh = run.automatic(-4);
    uint32_t localLow = run.automatic(-8);
    if ((flags & 0x40000) != 0) {
        uint32_t owner = run.get(run.get(receiver + 0x12c) + 0xc);
        run.put(localLow, 0);
        uint32_t table = run.get(owner + 0x2c) + 0x10;
        run.call(0x4f6286, table, {0x527e50, localLow});
        uint32_t found = run.get(localLow);
        if (found == 0) {
            uint32_t owner2 = run.get(run.get(receiver + 0x12c) + 0xc);
            uint32_t table2 = run.get(owner2 + 0x2c);
            uint32_t fallback = run.call(0x4061b0, table2, {0x5234b4});
            run.put(receiver + 0x374, fallback);
            function_43e9e0(run, receiver, nullptr);
            return 0;
        }
        run.put(receiver + 0x374, found);
        function_43e9e0(run, receiver, nullptr);
        return 0;
    }
    if ((flags & 0x80000) != 0) {
        uint32_t owner = run.get(run.get(receiver + 0x12c) + 0xc);
        run.put(localLow, 0);
        uint32_t table = run.get(owner + 0x2c) + 0x10;
        run.call(0x4f6286, table, {0x527e40, localLow});
        uint32_t found = run.get(localLow);
        if (found != 0) {
            run.put(receiver + 0x374, found);
            function_43e9e0(run, receiver, nullptr);
            return 0;
        }
        uint32_t owner2 = run.get(run.get(receiver + 0x12c) + 0xc);
        run.put(localHigh, found);
        uint32_t table2 = run.get(owner2 + 0x2c) + 0x10;
        run.call(0x4f6286, table2, {0x5234b4, localHigh});
        uint32_t fallback = run.get(localHigh);
        run.put(receiver + 0x374, fallback);
        function_43e9e0(run, receiver, nullptr);
        return 0;
    }
    if ((flags & 0x100000) != 0) {
        uint32_t owner = run.get(run.get(receiver + 0x12c) + 0xc);
        run.put(localHigh, 0);
        uint32_t table = run.get(owner + 0x2c) + 0x10;
        run.call(0x4f6286, table, {0x527e50, localHigh});
        uint32_t found = run.get(localHigh);
        if (found == 0) {
            uint32_t owner2 = run.get(run.get(receiver + 0x12c) + 0xc);
            run.put(localLow, found);
            uint32_t table2 = run.get(owner2 + 0x2c) + 0x10;
            run.call(0x4f6286, table2, {0x5234b4, localLow});
            found = run.get(localLow);
        }
        run.put(receiver + 0x374, found);
    }
    function_43e9e0(run, receiver, nullptr);
    return 0;
}

// 0x44cfd0. Releases the attached effect: marks it finished (+8 |= 0x10000)
// and clears the reference at this+0x44c.
uint32_t function_44cfd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x43e9b0, receiver, {});
    uint32_t effect = run.get(receiver + 0x44c);
    if (effect == 0)
        return 0;
    uint32_t flags = run.get(effect + 8);
    flags = flags | 0x10000;
    run.put(effect + 8, flags);
    run.put(receiver + 0x44c, 0);
    return 0;
}

// Runs the 0x4f6439 constructor-style call over every entry of the table list
// (0x5376b4 pointer, 0x5376b8 count), skipping null pointers.
void touchTableList(Run &run) {
    uint32_t cursor = run.get(0x5376b4);
    uint32_t count = run.get(0x5376b8);
    if (count == 0)
        return;
    uint32_t remaining = count;
    do {
        if (cursor != 0)
            run.call(0x4f6439, cursor, {});
        cursor = cursor + 4;
        remaining = remaining - 1;
    } while (remaining != 0);
}

// Looks up the current hit state name through the table at 0x537698 and
// compares it with `name`. Returns true when equal.
bool hitStateIs(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t state = run.get(receiver + 0x10);
    uint32_t key = run.get(state + 0x1c);
    uint32_t record = run.call(0x441030, 0x537698, {key});
    touchTableList(run);
    uint32_t text = run.get(record);
    uint32_t compared = run.call(0x4a3810, 0, {text, name});
    return compared == 0;
}

// 0x44d460. Hit handler: if the current state is LS_HITLOW or LS_HITHIGH it
// dispatches slot 0x44, otherwise it takes the hit (slot 0x28, burst, delay).
void function_44d460(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t hit = arguments[0];
    if (hitStateIs(run, receiver, 0x523204)) {
        run.vcall(receiver, 0x44, {});
        return;
    }
    if (hitStateIs(run, receiver, 0x523210)) {
        run.vcall(receiver, 0x44, {});
        return;
    }
    run.vcall(receiver, 0x28, {hit});
    uint32_t burstArguments[1] = {hit};
    function_440e20(run, receiver, burstArguments);
    uint32_t delayArguments[1] = {0x12c};
    function_43e9c0(run, receiver, delayArguments);
    uint32_t world = run.get(0x537e88);
    uint32_t level = run.get(world + 0x6c);
    uint32_t player = run.get(level + 0x14);
    uint32_t mode = run.get(player + 0x14);
    if (mode != 0) {
        run.call(0x44f510, receiver, {});
        return;
    }
    function_44f3c0(run, receiver, nullptr);
}

// 0x44d570. Contact handler: hit slot, burst, mark the hit finished, hit-low state.
void function_44d570(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t hit = arguments[0];
    run.vcall(receiver, 0x28, {hit});
    uint32_t burstArguments[1] = {hit};
    function_440e20(run, receiver, burstArguments);
    uint32_t flags = run.get(hit + 8);
    flags = flags | 0x10000;
    run.put(hit + 8, flags);
    function_44f3c0(run, receiver, nullptr);
}

// Starts the sword explosion effect (+0x44c) from the owner at +0x12c and the
// scene at +0x130, then names its two animations.
void startExplosion(Run &run, uint32_t receiver, uint32_t spriteName, uint32_t animationName) {
    uint32_t owner = run.get(receiver + 0x12c);
    uint32_t z = run.get(owner + 0x64);
    uint32_t y = run.get(owner + 0x50);
    uint32_t x = run.get(owner + 0x4c);
    z = z + 0x2135;
    uint32_t scene = run.get(receiver + 0x130);
    uint32_t sceneContext = run.get(scene + 0xc);
    uint32_t factory = run.get(sceneContext + 8);
    uint32_t effect = run.call(0x4c8da0, factory, {0, x, y, z, 0x522648, 0x40000});
    run.put(receiver + 0x44c, effect);
    run.call(0x4c7970, effect, {spriteName});
    uint32_t current = run.get(receiver + 0x44c);
    run.call(0x4c79e0, current, {animationName, 0});
    uint32_t held = run.get(receiver + 0x44c);
    uint32_t flags = run.get(held + 8);
    flags = flags | 2;
    run.put(held + 8, flags);
}

// 0x44d5a0. Explosion hit handler: hit slot, burst, hit-low state, then
// attaches the effect matching the active sword power (0x534eac).
void function_44d5a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t hit = arguments[0];
    run.vcall(receiver, 0x28, {hit});
    uint32_t burstArguments[1] = {hit};
    function_440e20(run, receiver, burstArguments);
    function_44f3c0(run, receiver, nullptr);
    if (run.get(receiver + 0x44c) != 0)
        return;
    uint32_t power = run.get(0x534eac);
    if (power == 0x26b8) {
        startExplosion(run, receiver, 0x527dd4, 0x527dbc);
        return;
    }
    if (power == 0x26b9) {
        startExplosion(run, receiver, 0x527e00, 0x527de8);
        return;
    }
    if (power == 0x26ba)
        startExplosion(run, receiver, 0x527e30, 0x527e18);
}

// 0x44d700. Plain hit handler: hit slot, burst, hit-low state.
void function_44d700(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t hit = arguments[0];
    run.vcall(receiver, 0x28, {hit});
    uint32_t burstArguments[1] = {hit};
    function_440e20(run, receiver, burstArguments);
    function_44f3c0(run, receiver, nullptr);
}

// 0x44d730. Stun hit handler: as the plain one with a 2000 tick delay.
void function_44d730(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t hit = arguments[0];
    run.vcall(receiver, 0x28, {hit});
    uint32_t burstArguments[1] = {hit};
    function_440e20(run, receiver, burstArguments);
    uint32_t delayArguments[1] = {2000};
    function_43e9c0(run, receiver, delayArguments);
    function_44f3c0(run, receiver, nullptr);
}

// 0x44d760. Aims a shot at the target (argument +0x6c: +0x2c x, +0x34 y).
// this: +0x38/+0x40/+0x48 velocity, +0x68/+0x70/+0x78 position, +0x50.. result.
// All arithmetic is binary64 in the original's evaluation order.
void function_44d760(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t target = arguments[0];
    uint32_t low = run.get(0x513e10);
    uint32_t high = run.get(0x513e14);
    run.put(receiver + 0x80, low);
    run.put(receiver + 0x84, high);
    uint32_t lowB = run.get(0x513e18);
    uint32_t highB = run.get(0x513e1c);
    run.put(receiver + 0x98, lowB);
    run.put(receiver + 0x9c, highB);
    low = run.get(0x513e10);
    high = run.get(0x513e14);
    run.put(receiver + 0x88, low);
    run.put(receiver + 0x8c, high);
    lowB = run.get(0x513e18);
    highB = run.get(0x513e1c);
    run.put(receiver + 0xa0, lowB);
    run.put(receiver + 0xa4, highB);
    low = run.get(0x513e10);
    high = run.get(0x513e14);
    run.put(receiver + 0x90, low);
    run.put(receiver + 0x94, high);
    lowB = run.get(0x513e18);
    highB = run.get(0x513e1c);
    run.put(receiver + 0xa8, lowB);
    run.put(receiver + 0xac, highB);
    run.vcall(receiver, 0x60, {});
    uint32_t inner = run.get(target + 0x6c);
    double targetX = static_cast<double>(run.gets(inner + 0x2c));
    double targetY = static_cast<double>(run.gets(inner + 0x34));
    double v0 = run.getd(receiver + 0x38);
    double v1 = run.getd(receiver + 0x40);
    double r0 = targetX - run.getd(receiver + 0x68);
    double r1 = targetY - run.getd(receiver + 0x70);
    double z = run.getd(receiver + 0x78);
    double v2 = run.getd(receiver + 0x48);
    double r2 = -z;
    double product0 = v0 * r0;
    double negated = -product0;
    double product1 = v1 * r1;
    double partial = negated - product1;
    double product2 = v2 * r2;
    double dot = partial - product2;
    double square0 = v0 * v0;
    double square1 = v1 * v1;
    double sum01 = square0 + square1;
    double square2 = v2 * v2;
    double speedSquared = sum01 + square2;
    double rSquare0 = r0 * r0;
    double rSquare1 = r1 * r1;
    double rSquare2 = r2 * r2;
    double rSum01 = rSquare0 + rSquare1;
    double dotScaled = dot * run.getd(0x50e0d0);
    double distanceSquared = rSum01 + rSquare2;
    double product = distanceSquared * speedSquared;
    double scaled = product * run.getd(0x50e0c8);
    double root = std::sqrt(scaled);
    double difference = root - dotScaled;
    double halved = difference * run.getd(0x50e0d8);
    double distance = std::sqrt(halved);
    if (!(distance >= run.getd(0x513e20))) {
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x60, 0);
        run.put(receiver + 0x54, 0);
        run.put(receiver + 0x5c, 0);
        run.put(receiver + 0x64, 0);
        return;
    }
    double threshold = speedSquared * run.getd(0x50e0e0);
    double epsilon = run.getd(0x513e20);
    double negativeEpsilon = -epsilon;
    bool aboveLower = threshold >= negativeEpsilon;
    bool belowUpper = threshold <= run.getd(0x513e20);
    if (aboveLower && belowUpper) {
        double abs1 = std::fabs(r1);
        double abs0 = std::fabs(r0);
        double absSum = abs1 + abs0;
        double abs2 = std::fabs(r2);
        double length = absSum + abs2;
        double q0 = r0 / length;
        double q1 = r1 / length;
        double q2 = r2 / length;
        double p0 = q0 * distance;
        double p1 = q1 * distance;
        double p2 = q2 * distance;
        run.putd(receiver + 0x50, p0);
        run.putd(receiver + 0x58, p1);
        run.putd(receiver + 0x60, p2);
        return;
    }
    double squaredDistance = distance * distance;
    double doubled = threshold + threshold;
    double numerator = squaredDistance - dot;
    double quotient = numerator / doubled;
    double root2 = std::sqrt(quotient);
    double qv0 = quotient * v0;
    double qv1 = quotient * v1;
    double qv2 = quotient * v2;
    double m0 = qv0 * run.getd(0x50e0d8);
    double m1 = qv1 * run.getd(0x50e0d8);
    double n0 = r0 - m0;
    double m2 = qv2 * run.getd(0x50e0d8);
    double n1 = r1 - m1;
    double n2 = r2 - m2;
    double o0 = n0 / root2;
    double o1 = n1 / root2;
    double o2 = n2 / root2;
    run.putd(receiver + 0x50, o0);
    run.putd(receiver + 0x58, o1);
    run.putd(receiver + 0x60, o2);
}

// 0x44d9f0. Enters the LS_HOME state: clears the velocity and remembers the old state.
uint32_t function_44d9f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    uint32_t state = run.get(receiver + 0x10);
    uint32_t previous = run.get(state + 0x1c);
    run.put(receiver + 0x24, previous);
    uint32_t next = run.call(0x4dba00, 0x537668, {0x5234ec});
    uint32_t state2 = run.get(receiver + 0x10);
    run.put(state2 + 0x1c, next);
    return 0;
}

// 0x43e9c0. Arms a delay: this+0x3d4 = ticks, this+0x3d0 = current time (0x537210).
uint32_t function_43e9c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x3d4, arguments[0]);
    uint32_t now = run.get(0x537210);
    run.put(receiver + 0x3d0, now);
    return 0;
}

// 0x43e9e0. Polls the player's current damage kind and dispatches the matching slot
// once the delay (this+0x3d0 / 0x3d4) has passed. Returns 1 if it dispatched.
uint32_t function_43e9e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t world = run.get(0x537e88);
    uint32_t level = run.get(world + 0x6c);
    uint32_t player = run.get(level + 0x14);
    uint32_t current = run.get(player + 0xe8);
    uint32_t last = run.get(receiver + 0x19c);
    if (current == last)
        return 0;
    run.put(receiver + 0x19c, current);
    uint32_t now = run.get(0x537210);
    uint32_t started = run.get(receiver + 0x3d0);
    uint32_t delay = run.get(receiver + 0x3d4);
    uint32_t elapsed = now - started;
    if (elapsed < delay)
        return 0;
    uint32_t owner = run.get(receiver + 0xc);
    uint32_t hit = run.get(owner + 0x74);
    uint32_t kind = run.get(hit + 0xd0);
    if (kind <= 0x10) {
        if (kind == 0x10)
            run.vcall(receiver, 0x38, {hit});
        else if (kind == 2)
            run.vcall(receiver, 0x2c, {hit});
    } else if (kind <= 0x1000) {
        if (kind == 0x1000)
            run.vcall(receiver, 0x40, {hit});
        else if (kind == 0x20)
            run.vcall(receiver, 0x30, {hit});
    } else if (kind == 0x1000000) {
        run.vcall(receiver, 0x3c, {hit});
    } else if (kind == 0x2000000) {
        run.vcall(receiver, 0x34, {hit});
    }
    uint32_t owner2 = run.get(receiver + 0xc);
    uint32_t health = run.get(owner2 + 0x10c);
    if (s32(health) <= 0)
        run.vcall(receiver, 0x5c, {0});
    return 1;
}

// 0x44f3c0. Enters the LS_HITLOW state: remembers the old state, restarts the
// animation, ends any attached effects and sets the vertical speed by direction.
uint32_t function_44f3c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t state = run.get(receiver + 0x10);
    run.put(receiver + 0x20, 1);
    uint32_t previous = run.get(state + 0x1c);
    run.put(receiver + 0x24, previous);
    uint32_t next = run.call(0x4dba00, 0x537668, {0x523204});
    uint32_t state2 = run.get(receiver + 0x10);
    run.put(state2 + 0x1c, next);
    uint32_t owner = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x334);
    uint32_t frame = run.get(owner + 0x190);
    run.put(receiver + 0x134, frame);
    run.call(0x4c8220, owner + 0x188, {animation});
    uint32_t effectA = run.get(receiver + 0x414);
    if (effectA != 0) {
        if (run.get(0x532c0c) != 0) {
            uint32_t argument = run.get(0x532c10);
            uint32_t target = run.get(effectA + 0x10);
            run.call(0x4b45f0, target, {argument, 0, 0, 0});
        }
    }
    uint32_t effectB = run.get(receiver + 0x41c);
    if (effectB != 0) {
        if (run.get(0x532c0c) != 0) {
            uint32_t argument = run.get(0x532c10);
            uint32_t target = run.get(effectB + 0x10);
            run.call(0x4b45f0, target, {argument, 0, 0, 0});
        }
    }
    uint32_t direction = run.get(receiver + 0x18c);
    run.put(receiver + 0x50, 0);
    if (direction == 3) {
        run.put(receiver + 0x54, 0x40690000);
        return 0;
    }
    run.put(receiver + 0x54, 0xc0690000);
    return 0;
}

// 0x440e20. Spawns a hit burst near the hit position (this+0x68/+0x70 truncated),
// optionally clamped by the hit descriptor, with +-4 pixel random jitter.
void function_440e20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t hit = arguments[0];
    double positionX = run.getd(receiver + 0x68);
    uint32_t truncatedX = truncateLow(positionX);
    double positionY = run.getd(receiver + 0x70);
    uint32_t truncatedY = truncateLow(positionY);
    uint32_t y = truncatedY;
    if (run.get(hit + 0x138) != 0x80000000) {
        uint32_t first = run.get(hit + 0x13c);
        uint32_t second = run.get(hit + 0x144);
        uint32_t sum = first + second;
        uint32_t sign = s32(sum) < 0 ? 0xffffffffu : 0u;
        uint32_t adjusted = sum - sign;
        y = static_cast<uint32_t>(s32(adjusted) >> 1);
        uint32_t base = run.get(hit + 0x50);
        uint32_t owner = run.get(receiver + 0xc);
        y = y + base;
        uint32_t low = run.get(owner + 0x12c) + truncatedY;
        if (!(s32(y) > s32(low)))
            y = low;
        uint32_t high = run.get(owner + 0x134) + truncatedY;
        if (!(s32(y) < s32(high)))
            y = high;
    }
    uint32_t owner = run.get(receiver + 0xc);
    uint32_t z = run.get(owner + 0x64);
    uint32_t randomY = run.call(0x4a3050, 0, {});
    uint32_t offsetY = static_cast<uint32_t>(s32(randomY) % 9) - 4;
    uint32_t randomX = run.call(0x4a3050, 0, {});
    owner = run.get(receiver + 0xc);
    uint32_t offsetX = static_cast<uint32_t>(s32(randomX) % 9) - 4;
    uint32_t service = run.get(owner + 0xc);
    z = z + 0x2135;
    y = y + offsetY;
    uint32_t x = truncatedX + offsetX;
    run.call(0x461a00, 0, {service, x, y, z, 0, owner});
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x44df60:
        return function_44df60(run, receiver, arguments);
    case 0x44cfd0:
        return function_44cfd0(run, receiver, arguments);
    case 0x44d460:
        function_44d460(run, receiver, arguments);
        return 0;
    case 0x44d570:
        function_44d570(run, receiver, arguments);
        return 0;
    case 0x44d5a0:
        function_44d5a0(run, receiver, arguments);
        return 0;
    case 0x44d700:
        function_44d700(run, receiver, arguments);
        return 0;
    case 0x44d730:
        function_44d730(run, receiver, arguments);
        return 0;
    case 0x44d760:
        function_44d760(run, receiver, arguments);
        return 0;
    case 0x44d9f0:
        return function_44d9f0(run, receiver, arguments);
    case 0x43e9c0:
        return function_43e9c0(run, receiver, arguments);
    case 0x43e9e0:
        return function_43e9e0(run, receiver, arguments);
    case 0x44f3c0:
        return function_44f3c0(run, receiver, arguments);
    case 0x440e20:
        function_440e20(run, receiver, arguments);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_enemy_base_virtuals_01_entry, owned, body)
