// Level 1 closure: Human enemy, Officer, Wolvington-shared and rope helpers
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"
#include <cmath>
#include <cstdint>

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x440350:
        return 0;
    case 0x440710:
        return 0;
    case 0x440c70:
        return 0;
    case 0x44c7c0:
        return 1;
    case 0x44e120:
        return 0;
    case 0x44f1b0:
        return 0;
    case 0x44f6e0:
        return 0;
    case 0x409f00:
        return 0;
    case 0x463310:
        return 0;
    case 0x4041a0:
        return 1;
    case 0x4041b0:
        return 1;
    default:
        return -1;
    }
}

// Shared tail of 0x440350 and 0x440710: moves the saved position at +0x270
// into the animation owner, re-targets the animation and returns 0.
// Fields of the enemy: +0x0c owner, +0x20 state, +0x12c animation owner,
// +0x134 current frame, +0x270..+0x27c saved vector and offset,
// +0x344 animation set.
uint32_t finishStep(Run &run, uint32_t enemy, uint32_t savedA, uint32_t savedB, uint32_t savedC, uint32_t savedD) {
    uint32_t owner = run.get(enemy + 0x0c);
    uint32_t ownerValue = run.get(owner + 0x124);
    uint32_t delta = ownerValue - savedD;
    uint32_t ownerField = run.get(owner + 0x50);
    run.put(owner + 0x50, ownerField + delta);
    uint32_t anim = run.get(enemy + 0x12c);
    run.put(anim + 0x118, savedA);
    run.put(anim + 0x11c, savedB);
    run.put(anim + 0x120, savedC);
    run.put(anim + 0x124, savedD);
    anim = run.get(enemy + 0x12c);
    run.put(anim + 0xd0, 4);
    anim = run.get(enemy + 0x12c);
    uint32_t flags = run.get(anim + 0x08);
    run.put(anim + 0x08, flags & 0xfffffffb);
    anim = run.get(enemy + 0x12c);
    uint32_t set = run.get(enemy + 0x344);
    uint32_t frame = run.get(anim + 0x190);
    run.put(enemy + 0x134, frame);
    run.call(0x4c8220, anim + 0x188, {set});
    uint32_t global = run.get(0x5430c4);
    run.call(0x4c82a0, anim + 0x188, {global});
    return 0;
}

// 0x440350. Sets state 2, clears bit 1 of the animation owner's flags, zeroes
// +0x50/+0x54 and applies the saved vector.
uint32_t function_440350(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x20, 2);
    uint32_t anim = run.get(receiver + 0x12c);
    uint32_t flags = run.get(anim + 0x08);
    run.put(anim + 0x08, flags & 0xfffffffd);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    uint32_t savedA = run.get(receiver + 0x270);
    uint32_t savedB = run.get(receiver + 0x274);
    uint32_t savedC = run.get(receiver + 0x278);
    uint32_t savedD = run.get(receiver + 0x27c);
    return finishStep(run, receiver, savedA, savedB, savedC, savedD);
}

// 0x440710. Like 0x440350 but sets owner +0xcc to 8 instead of clearing +0x50/+0x54.
uint32_t function_440710(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x20, 2);
    uint32_t anim = run.get(receiver + 0x12c);
    uint32_t flags = run.get(anim + 0x08);
    run.put(anim + 0x08, flags & 0xfffffffd);
    uint32_t owner = run.get(receiver + 0x0c);
    run.put(owner + 0xcc, 8);
    uint32_t savedA = run.get(receiver + 0x270);
    uint32_t savedB = run.get(receiver + 0x274);
    uint32_t savedC = run.get(receiver + 0x278);
    uint32_t savedD = run.get(receiver + 0x27c);
    return finishStep(run, receiver, savedA, savedB, savedC, savedD);
}

// 0x440c70. Sets state 2 and clears bit 2 of the animation owner's flags.
uint32_t function_440c70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x20, 2);
    uint32_t anim = run.get(receiver + 0x12c);
    uint32_t flags = run.get(anim + 0x08);
    run.put(anim + 0x08, flags & 0xfffffffb);
    return 0;
}

uint32_t function_409f00(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x44c7c0. Scalar deleting destructor: runs 0x409f00, frees when bit 0 is set.
uint32_t function_44c7c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_409f00(run, receiver, arguments);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// x87 FTOL as 0x4a30e0 does it: truncate toward zero through a 64-bit store,
// keep the low word. Out-of-range and NaN give the integer indefinite.
uint32_t truncate(double value) {
    if (!(value > -9223372036854775808.0 && value < 9223372036854775808.0))
        return 0;
    int64_t whole = int64_t(value);
    return uint32_t(uint64_t(whole));
}

// Common prefix of the idle and claw handlers: flips the animation owner's
// +0x138/+0x140 pair when it is not yet flipped (mode 2), else runs 0x406310.
void orientAnimation(Run &run, uint32_t enemy) {
    uint32_t anim = enemy + 0x128;
    uint32_t mode = run.get(enemy + 0x18c);
    if (mode != 2) {
        run.call(0x406310, anim);
        return;
    }
    uint32_t owner = run.get(anim + 0x04);
    uint32_t flags = run.get(owner + 0x40);
    if (flags & 2)
        return;
    uint32_t first = run.get(anim + 0x10);
    uint32_t second = run.get(anim + 0x18);
    run.put(anim + 0x10, 0 - second);
    run.put(anim + 0x18, 0 - first);
    flags = run.get(owner + 0x40);
    run.put(owner + 0x40, flags | 2);
    owner = run.get(anim + 0x04);
    run.call(0x4060b0, owner);
}

// 0x44e120. Claw-jump aim: far from the player it requests removal through
// virtual slot 0x48; near it computes a launch velocity at +0x50..+0x67.
uint32_t function_44e120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t player = run.get(0x537e88);
    uint32_t playerY = run.get(player + 0x50);
    uint32_t playerX = run.get(player + 0x4c);
    double positionX = run.getd(receiver + 0x68);
    uint32_t cellX = truncate(positionX);
    double positionY = run.getd(receiver + 0x70);
    uint32_t cellY = truncate(positionY);
    uint32_t dx = cellX - playerX;
    uint32_t dy = cellY - playerY;
    uint32_t distance = dx * dx + dy * dy;
    if (s32(distance) > 0xf424) {
        uint32_t count = run.get(receiver + 0x2fc);
        if (count <= 2) {
            run.call(0x4dbd20, receiver + 0x2f4, {2});
            run.vcall(receiver, 0x48);
            return 0;
        }
        if (count > 0x20) {
            uint32_t pointer = run.get(receiver + 0x300);
            uint32_t bits = run.get(pointer);
            run.put(pointer, bits | 4);
            run.vcall(receiver, 0x48);
            return 0;
        }
        uint32_t bits = run.get(receiver + 0x300);
        run.put(receiver + 0x300, bits | 4);
        run.vcall(receiver, 0x48);
        return 0;
    }
    orientAnimation(run, receiver);
    uint32_t owner = run.get(receiver + 0x0c);
    run.put(owner + 0xcc, 8);
    uint32_t level = run.get(receiver + 0x10);
    uint32_t state = run.get(level + 0x1c);
    run.put(receiver + 0x24, state);
    uint32_t newState = run.call(0x4dba00, 0x537668, {0x527dac});
    level = run.get(receiver + 0x10);
    run.put(level + 0x1c, newState);
    uint32_t anim = run.get(receiver + 0x12c);
    uint32_t set = run.get(receiver + 0x33c);
    uint32_t frame = run.get(anim + 0x190);
    run.put(receiver + 0x134, frame);
    run.call(0x4c8220, anim + 0x188, {set});
    uint32_t constantA = run.get(0x513e10);
    uint32_t constantB = run.get(0x513e14);
    run.put(receiver + 0x80, constantA);
    run.put(receiver + 0x84, constantB);
    uint32_t constantC = run.get(0x513e18);
    uint32_t constantD = run.get(0x513e1c);
    run.put(receiver + 0x98, constantC);
    run.put(receiver + 0x9c, constantD);
    constantA = run.get(0x513e10);
    constantB = run.get(0x513e14);
    run.put(receiver + 0x88, constantA);
    run.put(receiver + 0x8c, constantB);
    constantC = run.get(0x513e18);
    constantD = run.get(0x513e1c);
    run.put(receiver + 0xa0, constantC);
    run.put(receiver + 0xa4, constantD);
    constantA = run.get(0x513e10);
    constantB = run.get(0x513e14);
    run.put(receiver + 0x90, constantA);
    run.put(receiver + 0x94, constantB);
    constantC = run.get(0x513e18);
    constantD = run.get(0x513e1c);
    run.put(receiver + 0xa8, constantC);
    run.put(receiver + 0xac, constantD);
    uint32_t sound = run.get(receiver + 0x40c);
    if (sound != 0) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t cue = run.get(0x532c10);
        if (enabled != 0) {
            uint32_t target = run.get(sound + 0x10);
            run.call(0x4b45f0, target, {cue, 0, 0, 0});
        }
    }
    player = run.get(0x537e88);
    double playerYValue = double(run.gets(player + 0x50));
    double playerXValue = double(run.gets(player + 0x4c));
    double diffX = playerXValue - run.getd(receiver + 0x68);
    double diffY = playerYValue - run.getd(receiver + 0x70);
    double velocityX = run.getd(receiver + 0x38);
    double velocityY = run.getd(receiver + 0x40);
    double velocityZ = run.getd(receiver + 0x48);
    double diffZ = -run.getd(receiver + 0x78);
    double dotX = velocityX * diffX;
    dotX = -dotX;
    double dotY = velocityY * diffY;
    double dot = dotX - dotY;
    double dotZ = velocityZ * diffZ;
    dot = dot - dotZ;
    double speedX = velocityX * velocityX;
    double speedY = velocityY * velocityY;
    double speed = speedX + speedY;
    double speedZ = velocityZ * velocityZ;
    speed = speed + speedZ;
    double squareX = diffX * diffX;
    double squareY = diffY * diffY;
    double squareZ = diffZ * diffZ;
    double squareXY = squareX + squareY;
    double squareSum = squareXY + squareZ;
    double dotScaled = dot * run.getd(0x50e0d0);
    double product = squareSum * speed;
    product = product * run.getd(0x50e0c8);
    double root = std::sqrt(product);
    double inner = root - dotScaled;
    inner = inner * run.getd(0x50e0d8);
    double magnitude = std::sqrt(inner);
    double threshold = run.getd(0x513e20);
    if (!(magnitude >= threshold)) {
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x60, 0);
        run.put(receiver + 0x54, 0);
        run.put(receiver + 0x5c, 0);
        run.put(receiver + 0x64, 0);
        return 0;
    }
    double speedScaled = speed * run.getd(0x50e0e0);
    double negativeThreshold = -threshold;
    if (!(speedScaled < negativeThreshold) && !(speedScaled > threshold) && speedScaled == speedScaled) {
        double absY = std::fabs(diffY);
        double absX = std::fabs(diffX);
        double sum = absY + absX;
        double absZ = std::fabs(diffZ);
        sum = sum + absZ;
        double outX = diffX / sum;
        double outY = diffY / sum;
        double outZ = diffZ / sum;
        outX = outX * magnitude;
        outY = outY * magnitude;
        outZ = outZ * magnitude;
        run.putd(receiver + 0x50, outX);
        run.putd(receiver + 0x58, outY);
        run.putd(receiver + 0x60, outZ);
        return 0;
    }
    double magnitudeSquared = magnitude * magnitude;
    double numerator = magnitudeSquared - dot;
    double denominator = speedScaled + speedScaled;
    double ratio = numerator / denominator;
    double ratioRoot = std::sqrt(ratio);
    double stepX = ratio * velocityX;
    double stepY = ratio * velocityY;
    double stepZ = ratio * velocityZ;
    stepX = stepX * run.getd(0x50e0d8);
    stepY = stepY * run.getd(0x50e0d8);
    stepZ = stepZ * run.getd(0x50e0d8);
    double aimX = diffX - stepX;
    double aimY = diffY - stepY;
    double aimZ = diffZ - stepZ;
    aimX = aimX / ratioRoot;
    aimY = aimY / ratioRoot;
    aimZ = aimZ / ratioRoot;
    run.putd(receiver + 0x50, aimX);
    run.putd(receiver + 0x58, aimY);
    run.putd(receiver + 0x60, aimZ);
    return 0;
}

// 0x44f1b0. Idle entry: orients, zeroes +0x50/+0x54, switches to the LS_IDLE
// state and sometimes plays a voice line.
uint32_t function_44f1b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    orientAnimation(run, receiver);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    uint32_t level = run.get(receiver + 0x10);
    uint32_t state = run.get(level + 0x1c);
    run.put(receiver + 0x24, state);
    uint32_t newState = run.call(0x4dba00, 0x537668, {0x523148});
    level = run.get(receiver + 0x10);
    run.put(level + 0x1c, newState);
    uint32_t value = run.call(0x4a3050, 0);
    int32_t remainder = s32(value) % 100;
    if (remainder < 0x21) {
        uint32_t anim = run.get(receiver + 0x12c);
        uint32_t cue = run.get(receiver + 0x420);
        uint32_t marker = run.get(anim + 0x38);
        if (marker != 0xffffffff) {
            uint32_t owner = run.get(receiver + 0x0c);
            run.call(0x48ce40, 0, {owner, cue, 0});
        }
    }
    uint32_t anim = run.get(receiver + 0x12c);
    uint32_t set = run.get(receiver + 0x350);
    uint32_t frame = run.get(anim + 0x190);
    run.put(receiver + 0x134, frame);
    run.call(0x4c8220, anim + 0x188, {set});
    run.put(receiver + 0x43c, 0x7d0);
    uint32_t global = run.get(0x537210);
    run.put(receiver + 0x438, global);
    return 0;
}

// 0x44f6e0. Springboard jump: picks a direction by rand, solves the vertical
// speed from +0x40, +0x58 and +0x70.
uint32_t function_44f6e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t level = run.get(receiver + 0x10);
    uint32_t state = run.get(level + 0x1c);
    run.put(receiver + 0x24, state);
    uint32_t newState = run.call(0x4dba00, 0x537668, {0x527d60});
    level = run.get(receiver + 0x10);
    run.put(level + 0x1c, newState);
    run.put(receiver + 0x448, 0);
    uint32_t value = run.call(0x4a3050, 0);
    run.put(receiver + 0x50, 0);
    int32_t remainder = s32(value) % 100;
    if (remainder < 0x32)
        run.put(receiver + 0x54, 0x40590000);
    else
        run.put(receiver + 0x54, 0xc0590000);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x5c, 0xc0977000);
    double position = run.getd(receiver + 0x70);
    double lifted = position - run.getd(0x50e118);
    double gravity = run.getd(receiver + 0x40);
    double zero = run.getd(0x50e100);
    double result;
    if (!(gravity < zero) && !(gravity > zero)) {
        result = run.getd(receiver + 0x58);
    } else {
        double rise = lifted - run.getd(receiver + 0x70);
        double drive = rise * run.getd(receiver + 0x40);
        double speed = run.getd(receiver + 0x58);
        double speedSquared = speed * speed;
        drive = drive * run.getd(0x50e0d0);
        double discriminant = speedSquared - drive;
        zero = run.getd(0x50e100);
        if (zero > discriminant)
            discriminant = zero;
        double root = std::sqrt(discriminant);
        double speedAgain = run.getd(receiver + 0x58);
        zero = run.getd(0x50e100);
        if (!(speedAgain > zero))
            root = -root;
        result = root;
    }
    run.putd(receiver + 0x58, result);
    run.put(receiver + 0xb8, 0);
    run.put(receiver + 0xbc, 0xbff00000);
    run.putd(receiver + 0x70, lifted);
    uint32_t anim = run.get(receiver + 0x12c);
    uint32_t flags = run.get(anim + 0x08);
    run.put(anim + 0x08, flags & 0xffffffef);
    uint32_t owner = run.get(receiver + 0x0c);
    run.put(owner + 0xcc, 8);
    anim = run.get(receiver + 0x12c);
    uint32_t set = run.get(receiver + 0x33c);
    uint32_t frame = run.get(anim + 0x190);
    run.put(receiver + 0x134, frame);
    run.call(0x4c8220, anim + 0x188, {set});
    return 0;
}

// 0x409f00. Destructor: restores the base vtable around the member cleanups
// and releases the two string members at +0x1a4 and +0x1a8.
uint32_t function_409f00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}

// 0x463310. Picks one of two officer names by rand, looks it up through
// 0x4f6286 and stores the result at +0x410 before running 0x44df10.
uint32_t function_463310(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t value = run.call(0x4a3050, 0);
    int32_t remainder = s32(value) % 100;
    uint32_t local = run.automatic(-4);
    uint32_t name = 0x5298a0;
    if (remainder < 0x32)
        name = 0x529694;
    uint32_t anim = run.get(receiver + 0x12c);
    uint32_t table = run.get(anim + 0x0c);
    run.put(local, 0);
    table = run.get(table + 0x28);
    run.call(0x4f6286, table + 0x10, {name, local});
    uint32_t found = run.get(local);
    run.put(receiver + 0x410, found);
    run.call(0x44df10, receiver);
    return 0;
}

// 0x4041a0. Calls 0x4a36f0 (cdecl) with the object; the stack argument is ignored.
uint32_t function_4041a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.call(0x4a36f0, 0, {receiver});
    return 0;
}

// 0x4041b0. Runs the token's two callbacks: +0x18 only while the level state
// at +0x10->+0x1c equals +0x1c, then +0x14, and resets the token.
uint32_t function_4041b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t first = run.get(receiver + 0x14);
    if (first == 0)
        return 0;
    uint32_t second = run.get(receiver + 0x18);
    if (second != 0) {
        uint32_t level = run.get(receiver + 0x10);
        uint32_t levelState = run.get(level + 0x1c);
        uint32_t tokenState = run.get(receiver + 0x1c);
        if (levelState == tokenState) {
            run.call(second, receiver);
            run.put(receiver + 0x18, 0);
        }
    }
    uint32_t callback = run.get(receiver + 0x14);
    run.call(callback, receiver);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x1c, 0x3e9);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x440350:
        return function_440350(run, receiver, arguments);
    case 0x440710:
        return function_440710(run, receiver, arguments);
    case 0x440c70:
        return function_440c70(run, receiver, arguments);
    case 0x44c7c0:
        return function_44c7c0(run, receiver, arguments);
    case 0x44e120:
        return function_44e120(run, receiver, arguments);
    case 0x44f1b0:
        return function_44f1b0(run, receiver, arguments);
    case 0x44f6e0:
        return function_44f6e0(run, receiver, arguments);
    case 0x409f00:
        return function_409f00(run, receiver, arguments);
    case 0x463310:
        return function_463310(run, receiver, arguments);
    case 0x4041a0:
        return function_4041a0(run, receiver, arguments);
    case 0x4041b0:
        return function_4041b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_closure_enemies_01_entry, owned, body)
