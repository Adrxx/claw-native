// Observed Level 1 player actions batch 2
//
// The player's per-frame logic (0x415df0) and the ground, air and pose handlers
// it dispatches to. Written from the disassembly.
//
// Layout notes. Actor: +0x08 flags, +0x0c level, +0x40 flags2, +0x4c/+0x50
// position, +0x6c logic holder, +0x80 motion carrier, +0xcc mode, +0x118..+0x124 and
// +0x128..+0x134 bound boxes, +0x148/+0x14c velocity, +0x188 animation player,
// +0x1b0 speed scale. State: +0x14 player data, +0x1c state id. Player data:
// +0x00 facing, +0x04 attack active, +0x0c latch, +0x3c attack kind.
// Player data +0x12c links a carried actor; this is distinct from the actor's
// +0x80 motion carrier. Both remain guest tokens and keep their original reads.
// Nested linked-actor holder/logic loads retain their original expression shape.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"
#include "ClawRecoveredNames.h"
#include <cmath>
#include <cstring>

namespace {

using claw::Run;
using claw::s32;
using claw::recovered::v10::ActorFields;
using claw::recovered::v10::LogicHolderFields;
using claw::recovered::v10::ActorContextFields;

// These are dispatch identities, not a replacement for the original state ABI.
constexpr uint32_t kCreatePlayerState = 0;
constexpr uint32_t kJumpingPlayerState = 4;
constexpr uint32_t kRespawningPlayerState = 0x17;
constexpr uint32_t kStandingPlayerState = 0x18;
constexpr uint32_t kFallingPlayerState = 0x19;
constexpr uint32_t kCarryingPlayerState = 0x1388;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x40f780:
        return 1;
    case 0x40fe90:
        return 4;
    case 0x415df0:
        return 1;
    case 0x4171d0:
        return 3;
    case 0x417380:
        return 3;
    case 0x417590:
        return 3;
    case 0x417930:
        return 4;
    case 0x418120:
        return 3;
    case 0x4183e0:
        return 3;
    case 0x418b40:
        return 3;
    case 0x419030:
        return 3;
    default:
        return -1;
    }
}

// Entry ESP of a callee relative to the entry ESP of 0x415df0, for a call made
// with three and with four stack arguments.
constexpr int32_t kEntryThree = -0x2c;
constexpr int32_t kEntryFour = -0x30;

uint32_t lowWord(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    return uint32_t(bits);
}

uint32_t highWord(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    return uint32_t(bits >> 32);
}

// The two condition bits of an x87 compare that the code tests: C0 (below or
// unordered) and C3 (equal or unordered).
struct Compare {
    bool below;
    bool equal;
};

Compare compareX87(double left, double right) {
    Compare result;
    bool unordered = std::isnan(left) || std::isnan(right);
    result.below = unordered || left < right;
    result.equal = unordered || left == right;
    return result;
}

// x87 produces the negative quiet NaN for an invalid operation.
double indefinite() {
    uint64_t bits = 0xfff8000000000000ull;
    double value;
    std::memcpy(&value, &bits, 8);
    return value;
}

double fixNaN(double result, double left, double right) {
    if (std::isnan(result) && !std::isnan(left) && !std::isnan(right))
        return indefinite();
    return result;
}

double fadd(double left, double right) {
    double result = left + right;
    return fixNaN(result, left, right);
}

double fsub(double left, double right) {
    double result = left - right;
    return fixNaN(result, left, right);
}

double fmul(double left, double right) {
    double result = left * right;
    return fixNaN(result, left, right);
}

double fdiv(double left, double right) {
    double result = left / right;
    return fixNaN(result, left, right);
}

double fsqrt(double value) {
    if (value < 0.0)
        return indefinite();
    return std::sqrt(value);
}

// Clears the two latch bits in the input state (+0x0c bits 25 and 24).
void clearLatches(Run &run) {
    uint32_t input = run.get(0x537204);
    run.put(input + 0xc, run.get(input + 0xc) & 0xfdffffff);
    input = run.get(0x537204);
    run.put(input + 0xc, run.get(input + 0xc) & 0xfeffffff);
}

// Detaches the linked actor's logic: the plain form that patches the callback
// and releases the logic's queue.
void releaseLinkedInline(Run &run, uint32_t playerData) {
    uint32_t linked = run.get(playerData + 0x12c);
    if (linked == 0)
        return;
    uint32_t logic = run.get(run.get(linked + 0x6c) + 0x18);
    if (s32(run.get(logic + 0x20)) >= 1)
        run.put(logic + 0x14, 0x4207a0);
    run.call(0x420fc0, logic + 0x2f4, {0});
    run.put(playerData + 0x12c, 0);
}

// The same detach through the logic's own method.
void releaseLinkedCall(Run &run, uint32_t playerData) {
    uint32_t linked = run.get(playerData + 0x12c);
    if (linked == 0)
        return;
    uint32_t logic = run.get(run.get(linked + 0x6c) + 0x18);
    run.call(0x421010, logic, {0x4207a0, 1});
    run.call(0x420fc0, logic + 0x2f4, {0});
    run.put(playerData + 0x12c, 0);
}

// Hurt box that depends on the facing: +0x128..+0x130 and the fixed +0x134.
void setFacingBox(Run &run, uint32_t actor, uint32_t facing) {
    if (facing == 0) {
        run.put(actor + 0x128, 0xfffffff1);
        run.put(actor + 0x12c, 0xffffffd3);
        run.put(actor + 0x130, 0x16);
    } else {
        run.put(actor + 0x128, 0xffffffea);
        run.put(actor + 0x12c, 0xffffffd3);
        run.put(actor + 0x130, 0xf);
    }
    run.put(actor + 0x134, 0x34);
}

// Fixed box at +0x118..+0x124.
void setFixedBox(Run &run, uint32_t actor) {
    run.put(actor + 0x118, 0xfffffff0);
    run.put(actor + 0x11c, 0xffffffcc);
    run.put(actor + 0x120, 0x10);
    run.put(actor + 0x124, 0x3c);
}

// Copies the four words at player data +0xd8 into the actor's box at +0x118.
void copyStoredBox(Run &run, uint32_t actor, uint32_t playerData) {
    run.put(actor + 0x118, run.get(playerData + 0xd8));
    run.put(actor + 0x11c, run.get(playerData + 0xdc));
    run.put(actor + 0x120, run.get(playerData + 0xe0));
    run.put(actor + 0x124, run.get(playerData + 0xe4));
}

// Six words after the motion carry at 0x534e60.
void clearMotionCarry(Run &run) {
    run.put(0x534e60, 0);
    run.put(0x534e64, 0);
    run.put(0x534e68, 0);
    run.put(0x534e6c, 0);
    run.put(0x534e70, 0);
    run.put(0x534e74, 0);
}

// Advances the shared motion state by the frame time times a constant.
void advanceMotion(Run &run) {
    uint32_t frameTime = run.get(0x53720c);
    double scale = run.getd(0x50bab0);
    double scaled = fmul(double(frameTime), scale);
    run.call(0x403b40, 0x534db8, {lowWord(scaled), highWord(scaled)});
}

// The C runtime's truncating conversion (0x4a30e0): fistp with round-toward-zero
// to 64 bits, returning the low word. An unrepresentable value stores the
// integer indefinite 0x8000000000000000, whose low word is zero.
uint32_t truncateLow(double value) {
    if (!(value > -9223372036854775808.0 && value < 9223372036854775808.0))
        return 0;
    int64_t whole = int64_t(value);
    return uint32_t(uint64_t(whole));
}

// Splits a motion coordinate into whole and fraction through the original
// truncating conversion three times. Returns the whole part of the stepped
// value, and leaves the new fraction in the carry.
uint32_t splitFraction(Run &run, uint32_t source, uint32_t carry, uint32_t whole) {
    uint32_t first = truncateLow(run.getd(source));
    double truncated = double(s32(first));
    double rest = fsub(run.getd(source), truncated);
    rest = fadd(rest, run.getd(carry));
    double stepped = fadd(rest, run.getd(source));
    uint32_t second = truncateLow(stepped);
    run.put(whole, second);
    uint32_t third = truncateLow(rest);
    double truncatedRest = double(s32(third));
    double fraction = fsub(rest, truncatedRest);
    run.putd(carry, fraction);
    return second;
}

// value = value > amount ? value - amount : 0 (unsigned).
void subtractFloor(Run &run, uint32_t address, uint32_t amount) {
    uint32_t value = run.get(address);
    if (amount < value)
        run.put(address, value - amount);
    else
        run.put(address, 0);
}

bool isFallKind(uint32_t kind) {
    return kind == 8 || kind == 9 || kind == 10 || kind == 0x12;
}

// 0x40f780. thiscall, 1 stack argument. Looks a name up in the level's map.
uint32_t lookupLevelResourceByName(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t local = run.automatic(-4);
    ActorContextFields lookupContext{run, receiver};
    uint32_t owner = lookupContext.actorAlias();
    run.put(local, 0);
    uint32_t level = run.get(owner + 0xc);
    uint32_t map = run.get(level + 0x28);
    run.call(0x4f6286, map + 0x10, {arguments[0], local});
    return run.get(local);
}

// 0x40fe90. thiscall, 4 stack arguments. Stores a rectangle at +0x138.
void setThirdCollisionBox(Run &run, uint32_t receiver, uint32_t left, uint32_t top, uint32_t right, uint32_t bottom) {
    run.put(receiver + 0x138, left);
    run.put(receiver + 0x13c, top);
    run.put(receiver + 0x140, right);
    run.put(receiver + 0x144, bottom);
}

// 0x418120. cdecl. Mirrors the three boxes when the facing is zero.
void faceRightAndMirrorBoxes(Run &run, uint32_t actor, uint32_t state, uint32_t playerData) {
    (void)state;
    if (run.get(playerData) != 0)
        return;
    run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffd);
    uint32_t left = run.get(actor + 0x118);
    if (left != 0x80000000) {
        uint32_t right = run.get(actor + 0x120);
        run.put(actor + 0x118, 0u - right);
        run.put(actor + 0x120, 0u - left);
    }
    left = run.get(actor + 0x128);
    if (left != 0x80000000) {
        uint32_t right = run.get(actor + 0x130);
        run.put(actor + 0x128, 0u - right);
        run.put(actor + 0x130, 0u - left);
    }
    left = run.get(actor + 0x138);
    if (left != 0x80000000) {
        uint32_t right = run.get(actor + 0x140);
        run.put(actor + 0x138, 0u - right);
        run.put(actor + 0x140, 0u - left);
    }
    run.put(playerData, 1);
    run.put(playerData + 0x114, 0x5dc);
}

// 0x4171d0. cdecl. Puts the player into the standing pose.
uint32_t enterStandingPose(Run &run, uint32_t actor, uint32_t state, uint32_t playerData) {
    LogicHolderFields enterStandingPoseHolder{run, state};
    clearLatches(run);
    releaseLinkedInline(run, playerData);
    uint32_t attacking = run.get(playerData + 0x4);
    run.put(playerData + 0x3c, 0);
    run.put(playerData + 0x20, 1);
    if (attacking != 0) {
        uint32_t stored = run.get(playerData + 0x124);
        run.put(playerData + 0x4, 0);
        run.call(0x420a10, actor, {stored, 0});
        run.put(actor + 0x8, run.get(actor + 0x8) | 0x80);
    }
    enterStandingPoseHolder.state(kStandingPlayerState);
    run.call(0x4c79e0, actor, {0x5246d0, 1});
    uint32_t flags = run.get(actor + 0x8);
    run.put(actor + 0xcc, 1);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(actor + 0x104, 0);
    run.put(actor + 0x8, flags | 0x80);
    setFacingBox(run, actor, run.get(playerData));
    uint32_t result = run.get(playerData);
    setFixedBox(run, actor);
    run.put(playerData + 0xfc, 0x28a);
    run.put(playerData + 0x114, 0x5dc);
    run.put(playerData + 0x120, 0x3a98);
    run.put(playerData + 0x118, 0);
    clearMotionCarry(run);
    run.put(actor + 0x1b0, 0x3f800000);
    return result;
}

// 0x417380. cdecl. Resets the standing pose unless the state is 5000.
void resetStandingPose(Run &run, uint32_t actor, uint32_t state, uint32_t playerData, int32_t entry) {
    LogicHolderFields resetStandingPoseHolder{run, state};
    if (resetStandingPoseHolder.state() == kCarryingPlayerState)
        return;
    resetStandingPoseHolder.state(kStandingPlayerState);
    run.put(actor + 0xcc, 1);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    setFacingBox(run, actor, run.get(playerData));
    setFixedBox(run, actor);
    run.put(playerData + 0x114, 0x5dc);
    run.put(playerData + 0xfc, 0x28a);
    run.put(playerData + 0x120, 0x3a98);
    // The out parameter reuses the second argument's slot.
    uint32_t slot = run.automatic(entry + 8);
    uint32_t level = run.get(actor + 0xc);
    run.put(slot, 0);
    uint32_t names = run.get(level + 0x2c);
    run.call(0x4f6286, names + 0x10, {0x5246d0, slot});
    run.put(playerData + 0x124, run.get(slot));
}

// 0x417930. cdecl, 4 stack arguments. Puts the player into the falling pose.
uint32_t enterFallingPose(Run &run, uint32_t actor, uint32_t state, uint32_t playerData, uint32_t keepAnimation, int32_t entry) {
    LogicHolderFields enterFallingPoseHolder{run, state};
    uint32_t kind = run.get(playerData + 0x3c);
    if (isFallKind(kind)) {
        // The out parameter reuses the third argument's slot.
        uint32_t slot = run.automatic(entry + 0xc);
        uint32_t level = run.get(actor + 0xc);
        run.put(slot, 0);
        uint32_t names = run.get(level + 0x2c);
        run.call(0x4f6286, names + 0x10, {0x5246dc, slot});
        run.put(playerData + 0x124, run.get(slot));
    } else {
        clearLatches(run);
        releaseLinkedInline(run, playerData);
        uint32_t attacking = run.get(playerData + 0x4);
        run.put(playerData + 0x20, 1);
        run.put(playerData + 0x3c, 0);
        if (attacking != 0) {
            uint32_t stored = run.get(playerData + 0x124);
            run.put(playerData + 0x4, 0);
            run.call(0x420a10, actor, {stored, 0});
            run.put(actor + 0x8, run.get(actor + 0x8) | 0x80);
        }
        if (keepAnimation == 0)
            run.call(0x4c79e0, actor, {0x5246dc, 0});
    }
    enterFallingPoseHolder.state(kFallingPlayerState);
    uint32_t flags = run.get(actor + 0x8);
    run.put(actor + 0xcc, 4);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(actor + 0x8, flags & 0xffffffef);
    setFacingBox(run, actor, run.get(playerData));
    uint32_t result = run.get(playerData);
    setFixedBox(run, actor);
    run.put(playerData + 0x40, 0);
    run.put(0x534de8, 0);
    run.put(0x534dec, 0);
    run.put(0x534dd0, 0);
    run.put(0x534dd4, 0x40a19400);
    return result;
}

// 0x417590. cdecl. Starts a jump and aims the arc.
void startJumpAndAimArc(Run &run, uint32_t actor, uint32_t state, uint32_t playerData) {
    LogicHolderFields startJumpAndAimArcHolder{run, state};
    clearLatches(run);
    releaseLinkedCall(run, playerData);
    uint32_t attacking = run.get(playerData + 0x4);
    run.put(playerData + 0x3c, 0);
    run.put(playerData + 0x20, 1);
    if (attacking != 0) {
        uint32_t stored = run.get(playerData + 0x124);
        run.put(playerData + 0x4, 0);
        run.call(0x420a10, actor, {stored, 0});
        run.put(actor + 0x8, run.get(actor + 0x8) | 0x80);
    }
    startJumpAndAimArcHolder.state(kJumpingPlayerState);
    run.call(0x4c79e0, actor, {0x5246a8, 0});
    uint32_t flags = run.get(actor + 0x8);
    run.put(actor + 0xcc, 3);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(actor + 0x8, flags & 0xffffffef);
    if (run.get(playerData) == 0)
        run.call(0x4208b0, actor, {0xfffffff1, 0xffffffd3, 0x16, 0x34});
    else
        run.call(0x4208b0, actor, {0xffffffea, 0xffffffd3, 0xf, 0x34});
    run.call(0x40f6c0, actor, {0xfffffff0, 0xffffffcc, 0x10, 0x3c});
    if (run.get(0x534eac) == 0x26bc) {
        run.put(0x534de8, 0);
        run.put(0x534dec, 0xc07f4000);
    } else {
        uint32_t timer = run.get(playerData + 0x114);
        run.put(0x534de8, 0);
        run.put(0x534dec, 0xc07f4000);
        if (timer != 0)
            run.put(0x534dec, 0xc07a9000);
    }
    double constantA = run.getd(0x50baa8);
    run.put(playerData + 0x118, 0xfa);
    run.put(playerData + 0x5c, 0);
    run.put(playerData + 0x60, run.get(actor + 0x50));
    uint32_t top = run.get(actor + 0x50) - 0x2d;
    run.put(playerData + 0x10c, 0);
    run.put(playerData + 0x64, top);
    run.putd(0x534dd0, constantA);
    // The arc: unit vector toward the target and speed from a quadratic.
    double zero = run.getd(0x50ba88);
    double cx = run.getd(0x534e08);
    double xs = double(s32(run.get(actor + 0x4c)));
    run.putd(0x534df8, xs);
    double ys = double(s32(run.get(actor + 0x50)));
    run.putd(0x534e00, ys);
    double target = double(s32(run.get(playerData + 0x64)));
    double ca = run.getd(0x534dc8);
    double cb = run.getd(0x534dd8);
    double caSquared = fmul(ca, ca);
    double dy = fsub(target, run.getd(0x534e00));
    double cbSquared = fmul(cb, cb);
    double zeroSquared = fmul(zero, zero);
    double dyDy = fmul(dy, dy);
    double dx = -cx;
    double dxDx = fmul(dx, dx);
    double sumC = fadd(caSquared, cbSquared);
    double sumY = fadd(zeroSquared, dyDy);
    double d3 = fsub(sumC, run.getd(0x50bab8));
    double sumAll = fadd(sumY, dxDx);
    double e1 = fmul(zero, run.getd(0x534dc8));
    double q = fmul(sumAll, d3);
    double e2 = fmul(dy, run.getd(0x50baa8));
    double q2 = fmul(q, run.getd(0x50bac0));
    double negE1 = -e1;
    double e3 = fmul(dx, run.getd(0x534dd8));
    double w = fsqrt(q2);
    double f1 = fsub(negE1, e2);
    double dd = fsub(f1, e3);
    double ddScaled = fmul(dd, run.getd(0x50bac8));
    double v = fsub(w, ddScaled);
    double vScaled = fmul(v, run.getd(0x50bad0));
    double z = fsqrt(vScaled);
    if (compareX87(z, run.getd(0x513e20)).below) {
        run.put(0x534de0, 0);
        run.put(0x534de4, 0);
        run.put(0x534de8, 0);
        run.put(0x534dec, 0);
        run.put(0x534df0, 0);
        run.put(0x534df4, 0);
        return;
    }
    double d4 = fmul(d3, run.getd(0x50bad8));
    double limit = run.getd(0x513e20);
    double negLimit = -limit;
    bool straight = !compareX87(d4, negLimit).below;
    if (straight) {
        Compare high = compareX87(d4, run.getd(0x513e20));
        straight = high.below || high.equal;
    }
    if (straight) {
        double abs1 = std::fabs(zero);
        double abs2 = std::fabs(dx);
        double sum1 = fadd(abs1, abs2);
        double abs3 = std::fabs(dy);
        double total = fadd(sum1, abs3);
        double r1 = fdiv(zero, total);
        double r2 = fdiv(dy, total);
        double r3 = fdiv(dx, total);
        double o1 = fmul(r1, z);
        double o2 = fmul(r2, z);
        double o3 = fmul(r3, z);
        run.putd(0x534de0, o1);
        run.putd(0x534de8, o2);
        run.putd(0x534df0, o3);
    } else {
        double twice = fadd(d4, d4);
        double zz = fmul(z, z);
        double numerator = fsub(zz, dd);
        double rq = fdiv(numerator, twice);
        double sq = fsqrt(rq);
        double g0 = fmul(rq, run.getd(0x534dc8));
        double g1 = fmul(rq, run.getd(0x534dd8));
        double g2 = fmul(g0, run.getd(0x50bad0));
        double g3 = fmul(rq, run.getd(0x50bae8));
        double h1 = fsub(zero, g2);
        double g4 = fmul(g1, run.getd(0x50bad0));
        double h2 = fsub(dy, g3);
        double h3 = fsub(dx, g4);
        double o1 = fdiv(h1, sq);
        double o2 = fdiv(h2, sq);
        double o3 = fdiv(h3, sq);
        run.putd(0x534de0, o1);
        run.putd(0x534de8, o2);
        run.putd(0x534df0, o3);
    }
}

// Fetches the animation for the falling pose, shared by the fall entries.
void bindFallAnimation(Run &run, uint32_t actor, uint32_t playerData, uint32_t slot) {
    uint32_t level = run.get(actor + 0xc);
    run.put(slot, 0);
    uint32_t names = run.get(level + 0x2c);
    run.call(0x4f6286, names + 0x10, {0x5246dc, slot});
    run.put(playerData + 0x124, run.get(slot));
}

// Collision/carry offsets added to the position when the actor rides something.
void addCarrier(Run &run, uint32_t actor, uint32_t &x, uint32_t &y) {
    if ((run.get8(actor + 0x8) & 0x10) == 0)
        return;
    uint32_t carrier = run.get(actor + 0x80);
    if (carrier == 0)
        return;
    uint32_t carryX = run.get(carrier + 0x158);
    uint32_t carryY = run.get(carrier + 0x15c);
    x += carryX;
    y += carryY;
}

// 0x4183e0. cdecl. Walking right.
void stepWalkingRight(Run &run, uint32_t actor, uint32_t state, uint32_t playerData, int32_t entry) {
    LogicHolderFields stepWalkingRightHolder{run, state};
    uint32_t step = run.get(0x5430c4);
    uint32_t y = run.get(actor + 0x50);
    uint32_t x = run.get(actor + 0x4c);
    uint32_t timer = run.get(playerData + 0x114);
    if (step < timer)
        run.put(playerData + 0x114, timer - step);
    else
        run.put(playerData + 0x114, 0);
    run.put(actor + 0x1b0, 0x3f800000);
    // Keep the original operand storage addressable for custom-session settings.
    uint32_t speed = run.get(0x418432);
    if (run.get(0x534eac) == 0x26bc) {
        speed = run.get(0x418439);
        run.put(actor + 0x1b0, 0x3f4ccccd);
    } else if (run.get(playerData + 0x114) == 0) {
        speed = run.get(0x418452);
        run.put(actor + 0x1b0, 0x3f666666);
    }
    uint32_t velocity = speed + run.get(playerData + 0x84);
    run.put(actor + 0x148, velocity);
    run.putd(0x534de0, double(s32(velocity)));
    advanceMotion(run);
    uint32_t offset = 0;
    if (run.get(0x534e58) == 0)
        offset = splitFraction(run, 0x534e40, 0x534e60, 0x544e8c);
    x += offset;
    addCarrier(run, actor, x, y);
    uint32_t level = run.get(actor + 0xc);
    run.call(0x4cbb60, run.get(level + 0x24), {actor, x, y, 8});
    uint32_t mode = run.get(actor + 0xcc);
    if (mode == 1) {
        clearLatches(run);
        releaseLinkedCall(run, playerData);
        uint32_t attacking = run.get(playerData + 0x4);
        run.put(playerData + 0x3c, 0);
        run.put(playerData + 0x20, 1);
        if (attacking != 0) {
            uint32_t stored = run.get(playerData + 0x124);
            run.put(playerData + 0x4, 0);
            run.call(0x420a10, actor, {stored, 0});
            run.put(actor + 0x8, run.get(actor + 0x8) | 0x80);
        }
        stepWalkingRightHolder.state(kStandingPlayerState);
        run.call(0x4c79e0, actor, {0x5246d0, 1});
        uint32_t flags = run.get(actor + 0x8);
        run.put(actor + 0xcc, 1);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(actor + 0x104, 0);
        run.put(actor + 0x8, flags | 0x80);
        run.call(0x417050, 0, {actor, playerData});
        run.call(0x4170b0, 0, {actor, playerData});
        run.put(playerData + 0xfc, 0x28a);
        run.put(playerData + 0x114, 0x5dc);
        run.put(playerData + 0x120, 0x3a98);
        run.put(playerData + 0x118, 0);
        clearMotionCarry(run);
        run.put(actor + 0x1b0, 0x3f800000);
        return;
    }
    if (mode != 4) {
        run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
        return;
    }
    uint32_t kind = run.get(playerData + 0x3c);
    if (isFallKind(kind)) {
        // The out parameter reuses the second argument's slot.
        bindFallAnimation(run, actor, playerData, run.automatic(entry + 8));
    } else {
        run.call(0x41c4e0, 0, {actor, state, playerData});
        run.call(0x4c79e0, actor, {0x5246dc, 0});
    }
    stepWalkingRightHolder.state(kFallingPlayerState);
    uint32_t flags = run.get(actor + 0x8);
    run.put(actor + 0xcc, 4);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(actor + 0x8, flags & 0xffffffef);
    if (run.get(playerData) == 0)
        run.call(0x4208b0, actor, {0xfffffff1, 0xffffffd3, 0x16, 0x34});
    else
        run.call(0x4208b0, actor, {0xffffffea, 0xffffffd3, 0xf, 0x34});
    run.call(0x4170b0, 0, {actor, playerData});
    run.put(playerData + 0x40, 0);
    run.put(0x534de8, 0);
    run.put(0x534dec, 0);
    run.put(0x534dd0, 0);
    run.put(0x534dd4, 0x40a19400);
}

// 0x418b40. cdecl. Steps a fall and handles the resulting landing mode.
void stepFallingMovement(Run &run, uint32_t actor, uint32_t state, uint32_t playerData, int32_t entry) {
    LogicHolderFields stepFallingMovementHolder{run, state};
    uint32_t input = run.get(0x537204);
    uint32_t y = run.get(actor + 0x50);
    uint32_t x = run.get(actor + 0x4c);
    uint32_t held = run.get(input + 0x8);
    if ((held & 0x2000000) != 0) {
        if (run.get(playerData) == 0) {
            run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffd);
            run.call(0x4060b0, actor, {});
            run.put(playerData, 1);
            run.put(playerData + 0x114, 0x5dc);
        }
        run.put(actor + 0x148, run.get(0x418b9a));
    } else if ((held & 0x1000000) != 0) {
        if (run.get(playerData) != 0) {
            run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            run.call(0x4060b0, actor, {});
            run.put(playerData, 0);
            run.put(playerData + 0x114, 0x5dc);
        }
        run.put(actor + 0x148, run.get(0x418bd0));
    } else {
        run.put(actor + 0x148, 0);
    }
    run.putd(0x534de0, double(s32(run.get(actor + 0x148))));
    advanceMotion(run);
    uint32_t nophysics = run.get(0x534e58);
    uint32_t offsetX = 0;
    if (nophysics == 0)
        offsetX = splitFraction(run, 0x534e40, 0x534e60, 0x544e8c);
    x += offsetX;
    uint32_t offsetY = 0;
    if (nophysics == 0)
        offsetY = splitFraction(run, 0x534e48, 0x534e68, 0x544e88);
    y += offsetY;
    uint32_t flags = run.get(run.get(0x537204) + 0x8);
    uint32_t kind = 0x18;
    if ((flags & 0x4000000) != 0)
        kind = 0x19;
    uint32_t before = run.get(actor + 0x50);
    uint32_t level = run.get(actor + 0xc);
    run.call(0x4cbb60, run.get(level + 0x24), {actor, x, y, kind});
    uint32_t after = run.get(actor + 0x50);
    run.put(playerData + 0x40, run.get(playerData + 0x40) + (after - before));
    uint32_t mode = run.get(actor + 0xcc);
    if (mode == 1) {
        uint32_t sounds = run.get(run.get(actor + 0xc) + 0x28);
        if (run.get(sounds + 0x30) == 0) {
            // The out parameter reuses the first argument's slot.
            uint32_t slot = run.automatic(entry + 4);
            run.put(slot, 0);
            run.call(0x4f6286, sounds + 0x10, {0x524724, slot});
            uint32_t found = run.get(slot);
            if (found != 0)
                run.call(0x4208e0, found, {run.get(0x532c10), 0, 0, 0});
        }
        if (s32(run.get(playerData + 0x40)) >= 1000) {
            run.call(0x41c4e0, 0, {actor, state, playerData});
            stepFallingMovementHolder.state(0x138a);
            run.call(0x4c79e0, actor, {0x524718, 1});
            run.put(actor + 0xcc, 1);
            run.put(actor + 0x148, 0);
            run.put(actor + 0x14c, 0);
            run.put(playerData + 0x114, 0x5dc);
            return;
        }
        uint32_t latest = run.get(run.get(0x537204) + 0x8);
        if ((latest & 0x2000000) != 0) {
            run.call(0x41c4e0, 0, {actor, state, playerData});
            stepFallingMovementHolder.state(8);
            faceRightAndMirrorBoxes(run, actor, state, playerData);
            run.call(0x4c79e0, actor, {0x52469c, 0});
            run.put(actor + 0xcc, 2);
            run.put(actor + 0x148, run.get(0x418432));
        } else if ((latest & 0x1000000) != 0) {
            run.call(0x41c4e0, 0, {actor, state, playerData});
            stepFallingMovementHolder.state(9);
            run.call(0x418080, 0, {actor, state, playerData});
            run.call(0x4c79e0, actor, {0x52469c, 0});
            run.put(actor + 0xcc, 2);
            run.put(actor + 0x148, run.get(0x4187e2));
        } else {
            run.call(0x41c4e0, 0, {actor, state, playerData});
            stepFallingMovementHolder.state(kStandingPlayerState);
            run.call(0x4c79e0, actor, {0x5246d0, 1});
            uint32_t actorFlags = run.get(actor + 0x8);
            run.put(actor + 0xcc, 1);
            run.put(actor + 0x148, 0);
            run.put(actor + 0x14c, 0);
            run.put(actor + 0x104, 0);
            run.put(actor + 0x8, actorFlags | 0x80);
            run.call(0x417050, 0, {actor, playerData});
            run.call(0x4170b0, 0, {actor, playerData});
            run.put(playerData + 0xfc, 0x28a);
            run.put(playerData + 0x114, 0x5dc);
            run.put(playerData + 0x120, 0x3a98);
            run.put(playerData + 0x118, 0);
            clearMotionCarry(run);
            run.put(actor + 0x1b0, 0x3f800000);
            return;
        }
        run.put(actor + 0x14c, 0);
        run.put(playerData + 0xf8, 0);
        clearMotionCarry(run);
        return;
    }
    if (mode == 6) {
        run.call(0x41c4e0, 0, {actor, state, playerData});
        stepFallingMovementHolder.state(0x1b);
        run.call(0x4c79e0, actor, {0x5246c4, 0});
        uint32_t actorFlags = run.get(actor + 0x8);
        run.put(actor + 0xcc, 6);
        run.put(actor + 0x8, actorFlags & 0xffffffef);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(playerData + 0x2c, 0);
        run.put(playerData + 0x68, 0);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0);
        return;
    }
    if (run.get(playerData + 0x4) != 0) {
        run.call(0x41c5a0, 0, {actor, state, playerData});
        return;
    }
    run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    if (s32(run.get(playerData + 0x40)) > 0x258)
        run.call(0x4209d0, actor, {0x191});
}

// 0x419030. cdecl. Standing, idling and lifting.
void stepStandingIdleAndCarry(Run &run, uint32_t actor, uint32_t state, uint32_t playerData, int32_t entry) {
    LogicHolderFields stepStandingIdleAndCarryHolder{run, state};
    if (stepStandingIdleAndCarryHolder.state() == kCarryingPlayerState) {
        uint32_t input = run.get(0x537204);
        uint32_t y = run.get(actor + 0x50);
        uint32_t x = run.get(actor + 0x4c);
        uint32_t held = run.get(input + 0x8);
        if ((held & 0x1000000) != 0 && run.get(playerData + 0x8) != 0) {
            if (run.get(playerData) != 0)
                run.call(0x418080, 0, {actor, state, playerData});
            bool lift = run.get(playerData + 0xc) != 0;
            if (!lift)
                lift = compareX87(run.getd(0x534de0), run.getd(0x50baf0)).equal;
            if (lift) {
                run.call(0x4c79e0, actor, {0x524758, 0});
                run.put(0x534de0, 0);
                run.put(0x534de4, 0xc03e0000);
                run.put(playerData + 0xc, 0);
            }
        } else if ((held & 0x2000000) != 0 && run.get(playerData + 0x8) != 0) {
            if (run.get(playerData) == 0)
                faceRightAndMirrorBoxes(run, actor, state, playerData);
            bool lift = run.get(playerData + 0xc) != 0;
            if (!lift)
                lift = compareX87(run.getd(0x534de0), run.getd(0x50baf8)).equal;
            if (lift) {
                run.call(0x4c79e0, actor, {0x524758, 0});
                run.put(0x534de0, 0);
                run.put(0x534de4, 0x403e0000);
                run.put(playerData + 0xc, 0);
            }
        } else {
            run.put(0x534de0, 0);
            run.put(0x534de4, 0);
        }
        uint32_t player = actor + 0x188;
        uint32_t animation = run.call(0x4c82a0, player, {run.get(0x5430c4)});
        if (animation != 1) {
            advanceMotion(run);
            uint32_t delta = run.call(0x420cd0, 0x534db8, {});
            x += delta;
        }
        addCarrier(run, actor, x, y);
        uint32_t level = run.get(actor + 0xc);
        run.call(0x4cbb60, run.get(level + 0x24), {actor, x, y, 0x18});
        if (run.get(actor + 0xcc) == 4) {
            uint32_t linked = run.get(playerData + 0x12c);
            uint32_t logic = run.get(run.get(linked + 0x6c) + 0x18);
            run.call(0x421010, logic, {0x4207a0, 1});
            Compare against = compareX87(run.getd(0x534de0), run.getd(0x50ba88));
            if (!(against.below || against.equal)) {
                run.put(logic + 0x50, 0);
                run.put(logic + 0x54, 0x406c2000);
            } else {
                Compare again = compareX87(run.getd(0x534de0), run.getd(0x50ba88));
                if (again.below) {
                    run.put(logic + 0x50, 0);
                    run.put(logic + 0x54, 0xc06c2000);
                } else {
                    run.put(logic + 0x50, 0);
                    run.put(logic + 0x54, 0);
                }
            }
            run.call(0x420fc0, logic + 0x2f4, {0});
            run.put(playerData + 0x12c, 0);
            copyStoredBox(run, actor, playerData);
            enterFallingPose(run, actor, state, playerData, 0, entry - 0x2c);
            return;
        }
        bool lift = false;
        if (run.get(player + 0x1c) != 0 && run.get(player + 0x14) == 0 && run.get(playerData + 0x8) == 0) {
            lift = true;
        } else if (run.get(playerData + 0x8) != 0) {
            if (compareX87(run.getd(0x534de0), run.getd(0x50ba88)).equal) {
                lift = true;
            } else if (run.get(playerData + 0xc) == 0) {
                if (compareX87(run.getd(0x534de0), run.getd(0x50ba88)).equal)
                    lift = true;
            }
        }
        if (lift) {
            run.call(0x4c79e0, actor, {0x52474c, 0});
            run.put(playerData + 0x8, 1);
            run.put(playerData + 0xc, 1);
        }
        if (run.get(playerData + 0x8) != 0 && (run.get8(run.get(0x537204) + 0x4) & 0x22) != 0) {
            copyStoredBox(run, actor, playerData);
            run.call(0x41b1f0, 0, {actor, state, playerData});
        }
        uint32_t remaining = run.get(playerData + 0xf0);
        uint32_t step = run.get(0x5430c4);
        if (step < remaining) {
            run.put(playerData + 0xf0, remaining - step);
            return;
        }
        uint32_t holder = run.get(playerData + 0x12c);
        uint32_t holderLogic = run.get(run.get(holder + 0x6c) + 0x18);
        run.call(0x421010, holderLogic, {0x4207a0, 1});
        run.call(0x420fc0, holderLogic + 0x2f4, {0});
        run.put(playerData + 0x12c, 0);
        copyStoredBox(run, actor, playerData);
        enterStandingPose(run, actor, state, playerData);
        return;
    }
    uint32_t kindFlag = 0x18;
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    uint32_t flags = run.get(run.get(0x537204) + 0x8);
    if ((flags & 0x4000000) != 0) {
        kindFlag = 0x19;
        run.put(playerData + 0x120, 0x3a98);
    } else if ((flags & 0x8000000) != 0) {
        kindFlag = 0x1a;
        run.put(playerData + 0x120, 0x3a98);
    }
    uint32_t y = run.get(actor + 0x50);
    uint32_t x = run.get(actor + 0x4c);
    if (run.get(playerData + 0x84) != 0) {
        double zero = run.getd(0x50ba88);
        run.putd(0x534e60, zero);
        run.putd(0x534e68, run.getd(0x50ba88));
        run.putd(0x534e70, run.getd(0x50ba88));
        run.putd(0x534de0, double(s32(run.get(playerData + 0x84))));
        advanceMotion(run);
        uint32_t offset = 0;
        if (run.get(0x534e58) == 0)
            offset = splitFraction(run, 0x534e40, 0x534e60, 0x544e8c);
        x += offset;
    }
    addCarrier(run, actor, x, y);
    uint32_t level = run.get(actor + 0xc);
    run.call(0x4cbb60, run.get(level + 0x24), {actor, x, y, kindFlag});
    uint32_t result = 0;
    uint32_t mode = run.get(actor + 0xcc);
    if (mode == 4) {
        uint32_t kind = run.get(playerData + 0x3c);
        if (isFallKind(kind)) {
            uint32_t found = run.call(0x4061b0, run.get(run.get(actor + 0xc) + 0x2c), {0x5246dc});
            run.put(playerData + 0x124, found);
        } else {
            run.call(0x41c4e0, 0, {actor, state, playerData});
            run.call(0x4c79e0, actor, {0x5246dc, 0});
        }
        stepStandingIdleAndCarryHolder.state(kFallingPlayerState);
        uint32_t actorFlags = run.get(actor + 0x8);
        run.put(actor + 0xcc, 4);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(actor + 0x8, actorFlags & 0xffffffef);
        run.call(0x417050, 0, {actor, playerData});
        run.call(0x4170b0, 0, {actor, playerData});
        run.put(playerData + 0x40, 0);
        run.put(0x534de8, 0);
        run.put(0x534dec, 0);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0x40a19400);
    } else if (mode == 6) {
        run.call(0x41c4e0, 0, {actor, state, playerData});
        stepStandingIdleAndCarryHolder.state(0x1b);
        run.call(0x4c79e0, actor, {0x5246c4, 0});
        uint32_t actorFlags = run.get(actor + 0x8);
        run.put(actor + 0xcc, 6);
        run.put(actor + 0x8, actorFlags & 0xffffffef);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(playerData + 0x2c, 0);
        run.put(playerData + 0x68, 0);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0);
    } else if (run.get(playerData + 0x4) != 0) {
        run.call(0x41c5a0, 0, {actor, state, playerData});
    } else {
        result = run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    }
    uint32_t attacking = run.get(playerData + 0x4);
    bool free = true;
    if (attacking != 0 && run.get(playerData + 0x20) == 0)
        free = false;
    uint32_t inputNow = run.get(0x537204);
    if (free && (run.get8(inputNow + 0xb) & 8) != 0 && run.get(actor + 0xcc) == 1) {
        run.call(0x41c4e0, 0, {actor, state, playerData});
        stepStandingIdleAndCarryHolder.state(0x1a);
        run.call(0x4c79e0, actor, {0x524740, 0});
        run.put(actor + 0xcc, 5);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.call(0x4208b0, actor, {0xfffffff1, 0xa, 0x16, 0x34});
        run.call(0x40f6c0, actor, {0xfffffff0, 0xa, 0x10, 0x3c});
        if (run.get(playerData) == 0)
            run.call(0x4060b0, actor, {});
        run.put(playerData + 0x110, 0x3e8);
    } else if (attacking == 0 && run.get(playerData + 0xf8) == 0 && (run.get(inputNow + 0x8) & 0x4000000) != 0 &&
               run.get(actor + 0xcc) == 1) {
        subtractFloor(run, playerData + 0xfc, run.get(0x5430c4));
        if (run.get(playerData + 0xfc) == 0)
            run.call(0x4197e0, 0, {actor, state, playerData});
    }
    uint32_t idle = run.get(playerData + 0x120);
    if (idle != 0 && run.get(playerData + 0x4) == 0) {
        subtractFloor(run, playerData + 0x120, run.get(0x53720c));
        if (run.get(playerData + 0x120) == 0)
            run.call(0x4c79e0, actor, {0x524734, 1});
    }
    if (result == 0x63)
        run.call(0x420480, 0, {actor, state, playerData});
    if (run.get(actor + 0x1a4) != 0 && run.get(actor + 0x19c) == 0) {
        run.call(0x4c79e0, actor, {0x5246d0, 1});
        run.put(playerData + 0x120, 0x3a98);
    }
}

// Scans the ground ahead and below for an edge. Returns the value the caller
// tests: nonzero when the actor stands at an edge.
uint32_t atEdge(Run &run, uint32_t actor) {
    if ((run.get8(actor + 0x8) & 0x10) != 0)
        return run.call(0x4bb030, 0, {actor});
    uint32_t level = run.get(actor + 0xc);
    uint32_t tiles = run.get(level + 0x24);
    uint32_t right = run.get(actor + 0x120);
    uint32_t hit = run.call(0x4cd1c0, tiles, {actor, right});
    if (hit == 0)
        return 0;
    uint32_t probe = run.get(actor + 0x120) - 0xc;
    uint32_t left = run.get(actor + 0x118);
    if (!(s32(probe) > s32(left)))
        return 0;
    do {
        uint32_t blocked = run.call(0x4cd1c0, tiles, {actor, probe});
        if (blocked != 0)
            return 0;
        probe -= 4;
    } while (s32(probe) > s32(left));
    uint32_t last = run.call(0x4cd1c0, tiles, {actor, left});
    return last == 0 ? 1 : 0;
}

// The jump key is held.
void startJump(Run &run, uint32_t actor, uint32_t state, uint32_t playerData, int32_t entry) {
    LogicHolderFields startJumpHolder{run, state};
    run.call(0x41c4e0, 0, {actor, state, playerData});
    startJumpHolder.state(kJumpingPlayerState);
    run.call(0x4c79e0, actor, {0x5246a8, 0});
    uint32_t flags = run.get(actor + 0x8);
    run.put(actor + 0xcc, 3);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(actor + 0x8, flags & 0xffffffef);
    run.call(0x417050, 0, {actor, playerData});
    run.call(0x4170b0, 0, {actor, playerData});
    if (run.get(0x534eac) == 0x26bc) {
        run.put(0x534de8, 0);
        run.put(0x534dec, 0xc07f4000);
    } else {
        uint32_t timer = run.get(playerData + 0x114);
        run.put(0x534de8, 0);
        run.put(0x534dec, 0xc07f4000);
        if (timer != 0)
            run.put(0x534dec, 0xc07a9000);
    }
    run.put(playerData + 0x118, 0xfa);
    run.put(playerData + 0x5c, 0);
    run.put(playerData + 0x60, run.get(actor + 0x50));
    uint32_t top = run.get(actor + 0x50) - 0x2d;
    run.put(playerData + 0x10c, 0);
    run.put(playerData + 0x64, top);
    run.put(0x534dd0, 0);
    run.put(0x534dd4, 0x40a19400);
    run.putd(0x534df8, double(s32(run.get(actor + 0x4c))));
    double ys = double(s32(run.get(actor + 0x50)));
    uint32_t hi = run.get(0x534dfc);
    uint32_t lo = run.get(0x534df8);
    run.putd(0x534e00, ys);
    double target = double(s32(run.get(playerData + 0x64)));
    run.call(0x420dd0, 0x534db8, {lo, hi, lowWord(target), highWord(target), 0, 0});
    uint32_t x0 = run.get(actor + 0x4c);
    uint32_t y0 = run.get(actor + 0x50);
    run.call(0x41f4c0, 0, {actor, state, playerData});
    uint32_t held = run.get(run.get(0x537204) + 0x8);
    if ((held & 0x2000000) != 0) {
        faceRightAndMirrorBoxes(run, actor, state, playerData);
        run.put(actor + 0x148, run.get(0x41b7e6));
    } else if ((held & 0x1000000) != 0) {
        run.call(0x418080, 0, {actor, state, playerData});
        run.put(actor + 0x148, run.get(0x41b818));
    } else {
        run.put(actor + 0x148, 0);
    }
    uint32_t velocity = run.get(actor + 0x148) + run.get(playerData + 0x84);
    run.put(actor + 0x148, velocity);
    run.putd(0x534de0, double(s32(velocity)));
    advanceMotion(run);
    uint32_t deltaX = run.call(0x420cd0, 0x534db8, {});
    uint32_t x = x0 + deltaX;
    uint32_t deltaY = run.call(0x420d50, 0x534db8, {});
    uint32_t y = y0 + deltaY;
    run.put(playerData + 0x10c, run.get(playerData + 0x10c) + run.get(0x53720c));
    if (!compareX87(run.getd(0x534de8), run.getd(0x50ba88)).below) {
        double apex = double(s32(run.get(playerData + 0x64)));
        run.call(0x420c40, 0x534db8, {lowWord(apex), highWord(apex)});
        y = run.get(playerData + 0x64);
    }
    uint32_t kind = 0;
    if ((run.get(run.get(0x537204) + 0x8) & 0x4000000) != 0)
        kind = 0x11;
    uint32_t apexY = run.get(playerData + 0x64);
    uint32_t before = run.get(actor + 0x50);
    if (s32(y) < s32(apexY))
        y = apexY;
    uint32_t level = run.get(actor + 0xc);
    run.call(0x4cbb60, run.get(level + 0x24), {actor, x, y, kind});
    uint32_t after = run.get(actor + 0x50);
    run.put(playerData + 0x5c, run.get(playerData + 0x5c) + (before - after));
    uint32_t mode = run.get(actor + 0xcc);
    if (mode == 4) {
        enterFallingPose(run, actor, state, playerData, 0, entry + kEntryFour);
        return;
    }
    if (mode == 6) {
        run.call(0x4170f0, 0, {actor, state, playerData});
        return;
    }
    if (run.get(playerData + 0x4) == 0)
        run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    else
        run.call(0x41c5a0, 0, {actor, state, playerData});
    if (s32(run.get(actor + 0x50)) <= s32(run.get(playerData + 0x64)))
        enterFallingPose(run, actor, state, playerData, 1, entry + kEntryFour);
}

// State 0x18: standing on the ground.
void groundState(Run &run, uint32_t actor, uint32_t state, uint32_t playerData, int32_t entry) {
    LogicHolderFields groundStateHolder{run, state};
    uint32_t ready = 1;
    if (run.get(playerData + 0x4) != 0 && run.get(playerData + 0x20) == 0)
        ready = 0;
    uint32_t input = run.get(0x537204);
    if (ready != 0 && (run.get(input + 0x4) & 1) != 0) {
        startJump(run, actor, state, playerData, entry);
        return;
    }
    if (ready != 0) {
        if ((run.get(input + 0x4) & 0x2000000) != 0) {
            run.call(0x41c4e0, 0, {actor, state, playerData});
            groundStateHolder.state(8);
            faceRightAndMirrorBoxes(run, actor, state, playerData);
            run.call(0x4c79e0, actor, {0x52469c, 0});
            run.put(actor + 0xcc, 2);
            run.put(actor + 0x148, run.get(0x418432));
            run.put(actor + 0x14c, 0);
            run.put(playerData + 0xf8, 0);
            clearMotionCarry(run);
            uint32_t y = run.get(actor + 0x50);
            uint32_t x = run.get(actor + 0x4c);
            uint32_t timer = run.get(playerData + 0x114);
            uint32_t step = run.get(0x5430c4);
            if (step < timer)
                run.put(playerData + 0x114, timer - step);
            else
                run.put(playerData + 0x114, 0);
            run.put(actor + 0x1b0, 0x3f800000);
            uint32_t speed = run.get(0x418432);
            if (run.get(0x534eac) == 0x26bc) {
                speed = run.get(0x418439);
                run.put(actor + 0x1b0, 0x3f4ccccd);
            } else if (run.get(playerData + 0x114) == 0) {
                speed = run.get(0x418452);
                run.put(actor + 0x1b0, 0x3f666666);
            }
            uint32_t velocity = speed + run.get(playerData + 0x84);
            run.put(actor + 0x148, velocity);
            run.putd(0x534de0, double(s32(velocity)));
            advanceMotion(run);
            uint32_t delta = run.call(0x420cd0, 0x534db8, {});
            x += delta;
            addCarrier(run, actor, x, y);
            uint32_t level = run.get(actor + 0xc);
            run.call(0x4cbb60, run.get(level + 0x24), {actor, x, y, 8});
            uint32_t mode = run.get(actor + 0xcc);
            if (mode == 1)
                enterStandingPose(run, actor, state, playerData);
            else if (mode == 4)
                enterFallingPose(run, actor, state, playerData, 0, entry + kEntryFour);
            else
                run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
            return;
        }
        if ((run.get(input + 0x4) & 0x1000000) != 0) {
            run.call(0x41c4e0, 0, {actor, state, playerData});
            groundStateHolder.state(9);
            run.call(0x418080, 0, {actor, state, playerData});
            run.call(0x4c79e0, actor, {0x52469c, 0});
            run.put(actor + 0xcc, 2);
            run.put(actor + 0x148, run.get(0x4187e2));
            run.put(actor + 0x14c, 0);
            run.put(playerData + 0xf8, 0);
            clearMotionCarry(run);
            uint32_t y = run.get(actor + 0x50);
            uint32_t x = run.get(actor + 0x4c);
            uint32_t timer = run.get(playerData + 0x114);
            uint32_t frameTime = run.get(0x53720c);
            if (frameTime < timer)
                run.put(playerData + 0x114, timer - frameTime);
            else
                run.put(playerData + 0x114, 0);
            run.put(actor + 0x1b0, 0x3f800000);
            uint32_t speed = run.get(0x4187e2);
            if (run.get(0x534eac) == 0x26bc) {
                speed = run.get(0x4187e9);
                run.put(actor + 0x1b0, 0x3f4ccccd);
            } else if (run.get(playerData + 0x114) == 0) {
                speed = run.get(0x418802);
                run.put(actor + 0x1b0, 0x3f666666);
            }
            uint32_t velocity = speed + run.get(playerData + 0x84);
            run.put(actor + 0x148, velocity);
            run.putd(0x534de0, double(s32(velocity)));
            advanceMotion(run);
            uint32_t delta = run.call(0x420cd0, 0x534db8, {});
            x += delta;
            addCarrier(run, actor, x, y);
            uint32_t level = run.get(actor + 0xc);
            run.call(0x4cbb60, run.get(level + 0x24), {actor, x, y, 8});
            uint32_t mode = run.get(actor + 0xcc);
            if (mode == 1)
                enterStandingPose(run, actor, state, playerData);
            else if (mode == 4)
                enterFallingPose(run, actor, state, playerData, 0, entry + kEntryFour);
            else
                run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
            return;
        }
    }
    uint32_t edge = atEdge(run, actor);
    if (edge == 0) {
        uint32_t falling = run.call(0x41e710, 0, {actor});
        if (falling == 0) {
            run.call(0x41d850, 0, {actor, state, playerData});
            stepStandingIdleAndCarry(run, actor, state, playerData, entry + kEntryThree);
        } else {
            faceRightAndMirrorBoxes(run, actor, state, playerData);
            run.call(0x417480, 0, {actor, state, playerData});
            run.call(0x419c80, 0, {actor, state, playerData});
        }
        return;
    }
    if (run.get(playerData) != 0) {
        run.put(actor + 0x40, run.get(actor + 0x40) | 2);
        run.call(0x4060b0, actor, {});
        run.put(playerData, 0);
        run.put(playerData + 0x114, 0x5dc);
    }
    run.call(0x41c4e0, 0, {actor, state, playerData});
    groundStateHolder.state(0x138e);
    run.call(0x4c79e0, actor, {0x524690, 1});
    run.put(actor + 0xcc, 1);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(playerData + 0x114, 0x5dc);
    uint32_t roll = run.call(0x4a3050, 0, {});
    if (s32(roll) % 100 < 0x2d)
        run.call(0x48c8a0, 0, {0x524684, 0});
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    uint32_t kind = 0x18;
    uint32_t held = run.get(run.get(0x537204) + 0x8);
    if ((held & 0x4000000) != 0)
        kind = 0x19;
    else if ((held & 0x8000000) != 0)
        kind = 0x1a;
    uint32_t flags = run.get8(actor + 0x8);
    uint32_t x = run.get(actor + 0x4c);
    uint32_t y = run.get(actor + 0x50);
    if ((flags & 0x10) != 0) {
        uint32_t carrier = run.get(actor + 0x80);
        if (carrier != 0) {
            x += run.get(carrier + 0x158);
            y += run.get(carrier + 0x15c);
        }
    }
    uint32_t level = run.get(actor + 0xc);
    run.call(0x4cbb60, run.get(level + 0x24), {actor, x, y, kind});
    uint32_t mode = run.get(actor + 0xcc);
    if (mode == 4)
        enterFallingPose(run, actor, state, playerData, 0, entry + kEntryFour);
    else if (mode == 6)
        run.call(0x4170f0, 0, {actor, state, playerData});
    else
        run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    uint32_t result;
    if (run.get(playerData) == 0)
        result = run.call(0x41e790, 0, {actor});
    else
        result = run.call(0x41e710, 0, {actor});
    if (result == 0)
        enterStandingPose(run, actor, state, playerData);
}

// State 0: first frame, builds the player data.
void createPlayer(Run &run, uint32_t actor, uint32_t state) {
    run.put(0x52be14, 0xffffffff);
    run.put(0x52be18, 0xffffffff);
    run.put(state + 0x2c, 0x32);
    uint32_t level = run.get(actor + 0xc);
    uint32_t tiles = run.get(level + 0x24);
    uint32_t grid = run.get(tiles + 0x5c);
    uint32_t width = run.get(grid + 0x30);
    run.put(state + 0x34, 0x32);
    run.put(state + 0x30, width - 0x32);
    level = run.get(actor + 0xc);
    tiles = run.get(level + 0x24);
    grid = run.get(tiles + 0x5c);
    uint32_t height = run.get(grid + 0x34);
    uint32_t existing = run.get(state + 0x14);
    run.put(state + 0x38, height - 0x32);
    if (existing == 0) {
        uint32_t allocated = run.call(0x4f63ec, 0, {0x138});
        run.put(state + 0x14, allocated);
    }
    run.put(0x534ea8, 0);
    run.put(0x534eac, 0);
    uint32_t playerData = run.get(state + 0x14);
    for (uint32_t i = 0; i < 0x4e; ++i)
        run.put(playerData + 4 * i, 0);
    for (uint32_t i = 0; i < 0x4e; ++i)
        run.put(playerData + 4 * i, run.get(0x534c80 + 4 * i));
    run.put(actor + 0x10c, run.get(playerData + 0x48));
    uint32_t stored = run.get(playerData + 0x44);
    level = run.get(actor + 0xc);
    run.put(actor + 0xf8, stored);
    tiles = run.get(level + 0x24);
    grid = run.get(tiles + 0x5c);
    uint32_t startX = run.get(grid + 0x84);
    uint32_t startY = run.get(grid + 0x88);
    run.call(0x4c7900, actor, {0x523734, 0xb});
    run.put(actor + 0x4c, startX);
    run.put(actor + 0x50, startY);
    run.call(0x40f6a0, actor, {0xfa0});
    run.call(0x4c7fa0, actor, {0x522e70});
    uint32_t flags = run.get(actor + 0x8);
    flags = (flags & 0xffffffef) | 0x80;
    run.put(actor + 0x8, flags);
    run.put(actor + 0xd0, 2);
    run.put(actor + 0xd4, 0x1b50544);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(actor + 0xf4, 1);
    run.put(actor + 0x80, 0);
    run.call(0x40f6c0, actor, {0xfffffff0, 0xffffffcc, 0x10, 0x3c});
    run.call(0x4208b0, actor, {0xffffffe7, 0xffffffd3, 0xc, 0x34});
    setThirdCollisionBox(run, actor, 0xfffffff1, 0xffffffd3, 0x16, 0x22);
    level = run.get(actor + 0xc);
    run.call(0x4cd800, run.get(level + 0x24), {actor, 0});
    run.put(playerData, 0);
    run.put(playerData + 0x18, 0);
    run.put(playerData + 0xe8, 0);
    run.put(playerData + 0x2c, 5);
    run.put(playerData + 0x4, 0);
    run.put(playerData + 0x124, 0);
    run.put(playerData + 0x4c, run.get(actor + 0x4c));
    run.put(playerData + 0x50, run.get(actor + 0x50));
    run.put(playerData + 0x110, 0);
    run.put(playerData + 0x130, 0);
    run.put(playerData + 0x134, 0);
    uint32_t guard = run.get(playerData + 0x24);
    run.put(playerData + 0x12c, 0);
    run.put(playerData + 0x124, 0);
    run.put(playerData + 0x128, 0);
    run.put(playerData + 0x84, 0);
    run.put(playerData + 0x11c, 0);
    if (guard == 0) {
        for (uint32_t i = 0; i < 10; ++i)
            run.put(playerData + 0x88 + 4 * i, 0);
    }
    run.put(playerData, 1);
    enterStandingPose(run, actor, state, playerData);
    run.call(0x4060b0, actor, {});
    run.put(playerData, 0);
    faceRightAndMirrorBoxes(run, actor, state, playerData);
    uint32_t engine = run.get(run.get(0x5371fc) + 0x2c);
    if (run.vcall(engine, 0x10, {}) == 4)
        run.put(playerData + 0x7c, 9);
    run.call(0x420a40, 0x534db8, {0, 0, 0, 0, 0, 0, 0, 0, 0, 0x40a19400, 0, 0, 0, 0});
    run.put(0x534e78, 0);
    run.put(0x534e7c, 0x40400000);
    run.put(0x534e80, 0);
    run.put(0x534e84, 0x40400000);
    run.call(0x420ad0, 0x534db8, {0, 0x408f4000});
    run.call(0x4bc110, run.get(0x5371fc), {});
    if (run.get(0x534eb4) == 0) {
        uint32_t table = run.get(actor + 0x170);
        if (table != 0) {
            uint32_t entryObject = run.call(0x40f680, table, {0x17f});
            if (entryObject != 0)
                run.put(entryObject + 0x24, run.get(entryObject + 0x24) + 4);
            entryObject = run.call(0x40f680, table, {0x180});
            if (entryObject != 0)
                run.put(entryObject + 0x24, run.get(entryObject + 0x24) + 8);
            entryObject = run.call(0x40f680, table, {0x181});
            if (entryObject != 0)
                run.put(entryObject + 0x24, run.get(entryObject + 0x24) + 0xc);
            entryObject = run.call(0x40f680, table, {0x182});
            if (entryObject != 0)
                run.put(entryObject + 0x24, run.get(entryObject + 0x24) + 0x10);
            entryObject = run.call(0x40f680, table, {0x183});
            if (entryObject != 0)
                run.put(entryObject + 0x24, run.get(entryObject + 0x24) + 0x28);
            entryObject = run.call(0x40f680, table, {0x184});
            if (entryObject != 0)
                run.put(entryObject + 0x24, run.get(entryObject + 0x24) + 0x36);
            entryObject = run.call(0x40f680, table, {0x185});
            if (entryObject != 0)
                run.put(entryObject + 0x24, run.get(entryObject + 0x24) + 0x3a);
        }
    }
}

// State 0x17: respawn.
void respawnPlayer(Run &run, uint32_t actor, uint32_t state, uint32_t playerData) {
    uint32_t game = run.get(0x5371fc);
    run.put(0x52be14, 0xffffffff);
    run.put(0x52be18, 0xffffffff);
    uint32_t engine = run.get(game + 0x2c);
    uint32_t resumeX = run.get(engine + 0x44);
    uint32_t resumeY = run.get(engine + 0x48);
    run.put(playerData + 0x48, 100);
    run.put(actor + 0x10c, 100);
    if (resumeX == 0xffffffff || resumeY == 0xffffffff) {
        resumeY = run.get(playerData + 0x50);
        resumeX = run.get(playerData + 0x4c);
    }
    run.call(0x4c7900, actor, {0x523734, 0xb});
    run.put(actor + 0x50, resumeY);
    run.put(actor + 0x4c, resumeX);
    run.call(0x40f6a0, actor, {0xfa0});
    uint32_t effects = run.get(actor + 0xd4);
    uint32_t flags = run.get(actor + 0x8);
    uint32_t flags2 = run.get(actor + 0x40);
    run.put(actor + 0xd4, effects | 0x1000004);
    uint32_t level = run.get(actor + 0xc);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(actor + 0x8, flags & 0xffbffffa);
    run.put(actor + 0x40, flags2 & 0xfffffff6);
    run.call(0x4cd800, run.get(level + 0x24), {actor, 0});
    enterStandingPose(run, actor, state, playerData);
    run.put(state + 0x130, 0);
    uint32_t savedX = run.get(playerData + 0x4c);
    run.put(playerData + 0x2c, 5);
    run.put(playerData + 0x124, 0);
    run.put(playerData + 0x4, 0);
    run.put(playerData + 0x18, 0);
    run.put(playerData + 0x1c, 0);
    run.put(playerData + 0x20, 0);
    run.put(playerData + 0x84, 0);
    run.put(playerData + 0x11c, 0);
    if (run.get(actor + 0x4c) != savedX) {
        level = run.get(actor + 0xc);
        run.call(0x420910, run.get(level + 0x28), {0x5246b4});
    }
    uint32_t engineNow = run.get(run.get(0x5371fc) + 0x2c);
    if (run.vcall(engineNow, 0x10, {}) == 4)
        run.put(playerData + 0x7c, 9);
    uint32_t score = run.get(0x53c9f8);
    uint32_t bonus = run.get(0x52c6ec);
    uint32_t floor = run.get(0x52c6e4);
    score += bonus;
    run.put(0x53c9f8, score);
    if (score < floor)
        run.put(0x53c9f8, floor);
    run.call(0x4bc110, run.get(0x5371fc), {});
    run.call(0x41f990, 0, {actor, state, playerData, 0, 0});
    uint32_t notify = run.get(0x5349dc);
    if (notify != 0) {
        uint32_t object = run.get(run.get(notify + 0x6c) + 0x18);
        run.vcall(object, 0xb0, {});
    }
}

// Per-frame tail shared by every state.
void playerTail(Run &run, uint32_t actor, uint32_t state, uint32_t playerData) {
    LogicHolderFields playerTailHolder{run, state};
    uint32_t input = run.get(0x537204);
    if ((run.get8(input + 0x4) & 8) != 0 && run.get(playerData + 0x4) == 0) {
        uint32_t counter = run.get(playerData + 0x30) + 1;
        run.put(playerData + 0x30, counter);
        if (s32(counter) > 3)
            run.put(playerData + 0x30, 1);
        // Every counter value plays the same click.
        uint32_t level = run.get(actor + 0xc);
        run.call(0x420910, run.get(level + 0x28), {0x524678});
    }
    uint32_t timer = run.get(state + 0x130);
    if (timer != 0) {
        uint32_t frameTime = run.get(0x53720c);
        if (frameTime < timer) {
            run.put(state + 0x130, timer - frameTime);
        } else {
            run.put(state + 0x130, 0);
            uint32_t effects = run.get(actor + 0xd4);
            uint32_t flags2 = run.get(actor + 0x40);
            run.put(actor + 0xd4, effects | 0x1000004);
            run.put(actor + 0x40, flags2 & 0xfffffff7);
        }
    }
    subtractFloor(run, playerData + 0xf8, run.get(0x53720c));
    subtractFloor(run, playerData + 0x11c, run.get(0x53720c));
    run.call(0x41fc30, 0, {actor, state, playerData, run.get(0x53720c)});
    uint32_t id = playerTailHolder.state();
    uint32_t x = run.get(actor + 0x4c);
    uint32_t y = run.get(actor + 0x50);
    if (id != 0x138c) {
        uint32_t minX = run.get(state + 0x2c);
        if (s32(x) < s32(minX))
            x = minX;
        uint32_t maxX = run.get(state + 0x30);
        if (s32(x) > s32(maxX))
            x = maxX;
        uint32_t minY = run.get(state + 0x34);
        if (s32(y) < s32(minY))
            y = minY;
        uint32_t maxY = run.get(state + 0x38);
        if (s32(y) > s32(maxY))
            y = maxY;
        run.put(actor + 0x4c, x);
        run.put(actor + 0x50, y);
    }
    uint32_t busy = run.get(0x537230);
    uint32_t flags = run.get(actor + 0x8);
    if (busy == 0) {
        if ((flags & 0x400000) != 0) {
            uint32_t current = playerTailHolder.state();
            if (current != 0x138c && current != 0x138d)
                run.call(0x417c50, 0, {actor, state, playerData});
            flags = run.get(actor + 0x8);
            run.put(actor + 0x8, flags & 0xffbfffff);
        } else if ((flags & 0x10) != 0) {
            uint32_t level = run.get(actor + 0xc);
            uint32_t surface = run.call(0x4cd740, run.get(level + 0x24), {actor, 0});
            if (surface == 4) {
                uint32_t current = playerTailHolder.state();
                if (current != 0x138c && current != 0x138d)
                    run.call(0x417c50, 0, {actor, state, playerData});
            }
        }
    } else {
        run.put(actor + 0x8, flags & 0xffbfffff);
    }
    if (run.get(0x537214) != 0) {
        run.put(actor + 0x10c, 100);
        run.put(playerData + 0x70, 0x63);
        run.put(playerData + 0x74, 0x63);
        run.put(playerData + 0x78, 0x63);
        run.put(playerData + 0x7c, 0xa);
    }
}

// 0x415df0. cdecl. One frame of the player's logic. Always returns 1.
uint32_t dispatchPlayerFrame(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    ActorFields frameActor{run, actor};
    uint32_t state = frameActor.holder();
    LogicHolderFields frameHolder{run, state};
    uint32_t id = frameHolder.state();
    uint32_t playerData = run.get(state + 0x14);
    switch (id) {
    case kCreatePlayerState:
        createPlayer(run, actor, state);
        playerData = run.get(state + 0x14);
        break;
    case kJumpingPlayerState:
        run.call(0x41d850, 0, {actor, state, playerData});
        run.call(0x41b630, 0, {actor, state, playerData});
        break;
    case 8:
    case 9: {
        uint32_t held = run.get(run.get(0x537204) + 0x8);
        if ((held & 0x8000000) != 0) {
            enterStandingPose(run, actor, state, playerData);
            stepStandingIdleAndCarry(run, actor, state, playerData, kEntryThree);
        } else if (id == 8) {
            if ((held & 0x2000000) != 0) {
                stepWalkingRight(run, actor, state, playerData, kEntryThree);
            } else if ((held & 0x1000000) != 0) {
                run.call(0x417dd0, 0, {actor, state, playerData});
                run.call(0x418790, 0, {actor, state, playerData});
            } else {
                enterStandingPose(run, actor, state, playerData);
                stepStandingIdleAndCarry(run, actor, state, playerData, kEntryThree);
            }
        } else {
            if ((held & 0x1000000) != 0) {
                run.call(0x418790, 0, {actor, state, playerData});
            } else if ((held & 0x2000000) != 0) {
                run.call(0x417f20, 0, {actor, state, playerData});
                stepWalkingRight(run, actor, state, playerData, kEntryThree);
            } else {
                enterStandingPose(run, actor, state, playerData);
                stepStandingIdleAndCarry(run, actor, state, playerData, kEntryThree);
            }
        }
        uint32_t busy = run.call(0x41d850, 0, {actor, state, playerData});
        if (busy != 0) {
            resetStandingPose(run, actor, state, playerData, kEntryThree);
        } else {
            uint32_t pressed = run.get(run.get(0x537204) + 0x4);
            if ((pressed & 1) != 0)
                startJumpAndAimArc(run, actor, state, playerData);
        }
        break;
    }
    case kRespawningPlayerState:
        respawnPlayer(run, actor, state, playerData);
        break;
    case kStandingPlayerState:
        groundState(run, actor, state, playerData, 0);
        break;
    case kFallingPlayerState:
        run.call(0x41d850, 0, {actor, state, playerData});
        stepFallingMovement(run, actor, state, playerData, kEntryThree);
        break;
    case 0x1a:
        run.call(0x41d850, 0, {actor, state, playerData});
        run.call(0x419fd0, 0, {actor, state, playerData});
        break;
    case 0x1b:
        run.call(0x41bb70, 0, {actor, state, playerData});
        break;
    case 0x1f:
        run.call(0x41c030, 0, {actor, state, playerData});
        break;
    case kCarryingPlayerState:
        run.call(0x41a850, 0, {actor, state, playerData});
        break;
    case 0x1389:
        run.call(0x41b280, 0, {actor, state, playerData});
        break;
    case 0x138a:
        run.call(0x4198d0, 0, {actor, state, playerData});
        break;
    case 0x138b:
    case 0x138e: {
        uint32_t input = run.get(0x537204);
        if ((run.get8(input + 0x4) & 1) != 0) {
            startJumpAndAimArc(run, actor, state, playerData);
            run.call(0x41b630, 0, {actor, state, playerData});
        } else if (id == 0x138b) {
            run.call(0x41a490, 0, {actor, state, playerData});
        } else {
            uint32_t held = run.get(input + 0x8);
            if ((held & 0x2000000) != 0) {
                run.call(0x417f20, 0, {actor, state, playerData});
                stepWalkingRight(run, actor, state, playerData, kEntryThree);
            } else if ((held & 0x1000000) != 0) {
                run.call(0x417dd0, 0, {actor, state, playerData});
                run.call(0x418790, 0, {actor, state, playerData});
            } else {
                run.call(0x419c80, 0, {actor, state, playerData});
            }
        }
        break;
    }
    case 0x138c:
        run.call(0x41c2b0, 0, {actor, state, playerData});
        break;
    case 0x138d:
        run.call(0x41c440, 0, {actor, state, playerData});
        break;
    case 0x138f:
        run.call(0x4181c0, 0, {actor, state, playerData});
        break;
    case 0x1391:
        run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
        if (run.get(0x53c9c0) == 2)
            enterStandingPose(run, actor, state, playerData);
        break;
    default:
        break;
    }
    playerTail(run, actor, state, playerData);
    return 1;
}

// Internal calls keep the original relative entry ESP for reused stack slots.
// Only external canonical entry adapters begin at relative entry ESP zero.
// Canonical ABI adapter for original entry 0x40fe90.
uint32_t setThirdCollisionBoxEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    setThirdCollisionBox(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3]);
    return 0;
}

// Canonical ABI adapter for original entry 0x4171d0.
uint32_t enterStandingPoseEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return enterStandingPose(run, arguments[0], arguments[1], arguments[2]);
}

// Canonical ABI adapter for original entry 0x417380.
uint32_t resetStandingPoseEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    resetStandingPose(run, arguments[0], arguments[1], arguments[2], 0);
    return 0;
}

// Canonical ABI adapter for original entry 0x417590.
uint32_t startJumpAndAimArcEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    startJumpAndAimArc(run, arguments[0], arguments[1], arguments[2]);
    return 0;
}

// Canonical ABI adapter for original entry 0x417930.
uint32_t enterFallingPoseEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return enterFallingPose(run, arguments[0], arguments[1], arguments[2], arguments[3], 0);
}

// Canonical ABI adapter for original entry 0x418120.
uint32_t faceRightAndMirrorBoxesEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    faceRightAndMirrorBoxes(run, arguments[0], arguments[1], arguments[2]);
    return 0;
}

// Canonical ABI adapter for original entry 0x4183e0.
uint32_t stepWalkingRightEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    stepWalkingRight(run, arguments[0], arguments[1], arguments[2], 0);
    return 0;
}

// Canonical ABI adapter for original entry 0x418b40.
uint32_t stepFallingMovementEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    stepFallingMovement(run, arguments[0], arguments[1], arguments[2], 0);
    return 0;
}

// Canonical ABI adapter for original entry 0x419030.
uint32_t stepStandingIdleAndCarryEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    stepStandingIdleAndCarry(run, arguments[0], arguments[1], arguments[2], 0);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40f780:
        return lookupLevelResourceByName(run, receiver, arguments);
    case 0x40fe90:
        return setThirdCollisionBoxEntry(run, receiver, arguments);
    case 0x415df0:
        return dispatchPlayerFrame(run, receiver, arguments);
    case 0x4171d0:
        return enterStandingPoseEntry(run, receiver, arguments);
    case 0x417380:
        return resetStandingPoseEntry(run, receiver, arguments);
    case 0x417590:
        return startJumpAndAimArcEntry(run, receiver, arguments);
    case 0x417930:
        return enterFallingPoseEntry(run, receiver, arguments);
    case 0x418120:
        return faceRightAndMirrorBoxesEntry(run, receiver, arguments);
    case 0x4183e0:
        return stepWalkingRightEntry(run, receiver, arguments);
    case 0x418b40:
        return stepFallingMovementEntry(run, receiver, arguments);
    case 0x419030:
        return stepStandingIdleAndCarryEntry(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_player_actions_02_entry, owned, body)
