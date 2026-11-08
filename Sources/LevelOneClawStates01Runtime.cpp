// Level 1 Claw movement and pose state callbacks batch 1
//
// Canonical v1.0 callbacks. Guest tokens, service order and arithmetic remain
// faithful to the original entries identified beside each behavior-named body.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"
#include "ClawRecoveredNames.h"

namespace {

using claw::Run;
using claw::s32;
using claw::recovered::v10::ActorFields;
using claw::recovered::v10::LogicHolderFields;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4170f0:
        return 3;
    case 0x417480:
        return 3;
    case 0x417dd0:
        return 3;
    case 0x417f20:
        return 3;
    case 0x418790:
        return 3;
    case 0x4197e0:
        return 3;
    case 0x4198d0:
        return 3;
    case 0x419c80:
        return 3;
    case 0x419fd0:
        return 3;
    case 0x41a490:
        return 3;
    default:
        return -1;
    }
}


// Guest addresses used by several functions.
constexpr uint32_t kInputObjectPointerAddress = 0x537204;   // pointer to the input-flag object
constexpr uint32_t kFrameMillisecondsAddress = 0x53720c;        // frame time
constexpr uint32_t kAnimationMillisecondsAddress = 0x5430c4;         // animation time step
constexpr uint32_t kMovementIntegratorAddress = 0x534db8;     // physics integrator block
constexpr uint32_t kClearLiftCallback = 0x4207a0;

// Clear two latched bits of the input-flag object's word at +0xc, reloading the pointer in between.
void clearDirectionalInputLatches(Run &run) {
    uint32_t inputObjectToken = run.get(kInputObjectPointerAddress);
    uint32_t latched = run.get(inputObjectToken + 0xc);
    latched = latched & 0xfdffffff;
    run.put(inputObjectToken + 0xc, latched);
    inputObjectToken = run.get(kInputObjectPointerAddress);
    latched = run.get(inputObjectToken + 0xc);
    latched = latched & 0xfeffffff;
    run.put(inputObjectToken + 0xc, latched);
}

// Drop the effect object held at state+0x12c, releasing it with the plain destructor call.
void releaseHeldEffect(Run &run, uint32_t playerStateToken) {
    const uint32_t held = run.get(playerStateToken + 0x12c);
    if (held == 0)
        return;
    ActorFields heldActorFields{run, held};
    const uint32_t table = heldActorFields.holder();
    LogicHolderFields effectHolderFields{run, table};
    const uint32_t effect = effectHolderFields.logic();
    if (run.gets(effect + 0x20) > 0)
        run.put(effect + 0x14, kClearLiftCallback);
    run.call(0x420fc0, effect + 0x2f4, {0});
    run.put(playerStateToken + 0x12c, 0);
}

// Drop the effect object held at state+0x12c, marking its list entry instead of destroying it.
void markHeldEffectForRelease(Run &run, uint32_t playerStateToken) {
    const uint32_t held = run.get(playerStateToken + 0x12c);
    if (held == 0)
        return;
    ActorFields heldActorFields{run, held};
    const uint32_t table = heldActorFields.holder();
    LogicHolderFields effectHolderFields{run, table};
    const uint32_t effect = effectHolderFields.logic();
    if (run.gets(effect + 0x20) > 0)
        run.put(effect + 0x14, kClearLiftCallback);
    const uint32_t list = effect + 0x2f4;
    const uint32_t count = run.get(effect + 0x2fc);
    if (count == 0) {
        run.call(0x4dbd20, list, {0});
    } else {
        uint32_t cell = list + 0xc;
        if (count > 0x20)
            cell = run.get(list + 0xc);
        const uint32_t bits = run.get(cell);
        run.put(cell, bits | 1);
    }
    run.put(playerStateToken + 0x12c, 0);
}

// Drop the effect object held at state+0x12c, first restoring its lift callback (0x421010).
void resetAndReleaseHeldEffect(Run &run, uint32_t playerStateToken) {
    const uint32_t held = run.get(playerStateToken + 0x12c);
    if (held == 0)
        return;
    ActorFields heldActorFields{run, held};
    const uint32_t table = heldActorFields.holder();
    LogicHolderFields effectHolderFields{run, table};
    const uint32_t effect = effectHolderFields.logic();
    run.call(0x421010, effect, {kClearLiftCallback, 1});
    run.call(0x420fc0, effect + 0x2f4, {0});
    run.put(playerStateToken + 0x12c, 0);
}

// Keep the existing signed 64-bit truncation and low-word result, including its
// invalid-range behavior; this readability pass does not change floating point.
uint32_t truncateToLowWord(double value) {
    if (!(value > -9223372036854775808.0 && value < 9223372036854775808.0))
        return 0;
    const int64_t whole = static_cast<int64_t>(value);
    return static_cast<uint32_t>(whole);
}

// 0x4170f0. cdecl, 3 stack argument(s), returns void.
uint32_t enterClimbingPose(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t playerActorToken = arguments[0];
    const uint32_t holderToken = arguments[1];
    LogicHolderFields holderFields{run, holderToken};
    const uint32_t playerStateToken = arguments[2];
    clearDirectionalInputLatches(run);
    releaseHeldEffect(run, playerStateToken);
    const uint32_t pendingAnimation = run.get(playerStateToken + 4);
    run.put(playerStateToken + 0x20, 1);
    run.put(playerStateToken + 0x3c, 0);
    if (pendingAnimation != 0) {
        const uint32_t animationToken = run.get(playerStateToken + 0x124);
        run.put(playerStateToken + 4, 0);
        run.call(0x4c8220, playerActorToken + 0x188, {animationToken});
        const uint32_t actorFlags = run.get(playerActorToken + 8);
        run.put(playerActorToken + 8, actorFlags | 0x80);
    }
    holderFields.state(0x1b);
    run.call(0x4c79e0, playerActorToken, {0x5246c4, 0});
    const uint32_t actorFlags = run.get(playerActorToken + 8);
    run.put(playerActorToken + 0xcc, 6);
    run.put(playerActorToken + 0x148, 0);
    run.put(playerActorToken + 0x14c, 0);
    run.put(playerActorToken + 8, actorFlags & 0xffffffef);
    run.put(playerStateToken + 0x2c, 0);
    run.put(playerStateToken + 0x68, 0);
    run.put(0x534dd0, 0);
    run.put(0x534dd4, 0);
    return 0;
}

// 0x417480. cdecl, 3 stack argument(s), returns u32.
uint32_t enterTeeteringPose(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t playerActorToken = arguments[0];
    const uint32_t holderToken = arguments[1];
    LogicHolderFields holderFields{run, holderToken};
    const uint32_t playerStateToken = arguments[2];
    clearDirectionalInputLatches(run);
    markHeldEffectForRelease(run, playerStateToken);
    const uint32_t pendingAnimation = run.get(playerStateToken + 4);
    run.put(playerStateToken + 0x3c, 0);
    run.put(playerStateToken + 0x20, 1);
    if (pendingAnimation != 0) {
        const uint32_t animationToken = run.get(playerStateToken + 0x124);
        run.put(playerStateToken + 4, 0);
        run.call(0x420a10, playerActorToken, {animationToken, 0});
        const uint32_t actorFlags = run.get(playerActorToken + 8);
        run.put(playerActorToken + 8, actorFlags | 0x80);
    }
    holderFields.state(0x138e);
    run.call(0x4c79e0, playerActorToken, {0x524690, 1});
    run.put(playerActorToken + 0xcc, 1);
    run.put(playerActorToken + 0x148, 0);
    run.put(playerActorToken + 0x14c, 0);
    run.put(playerStateToken + 0x114, 0x5dc);
    const uint32_t randomRoll = run.call(0x4a3050, 0, {});
    const int32_t signedRandomRoll = claw::s32(randomRoll);
    uint32_t result = static_cast<uint32_t>(signedRandomRoll / 100);
    const int32_t remainder = signedRandomRoll % 100;
    if (remainder < 0x2d)
        result = run.call(0x48c8a0, 0, {0x524684, 0});
    return result;
}

// The two walk entries retain their distinct store/call order and facing changes.
// 0x417dd0. cdecl, 3 stack argument(s), returns void.
uint32_t enterWalkingLeft(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t playerActorToken = arguments[0];
    const uint32_t holderToken = arguments[1];
    LogicHolderFields holderFields{run, holderToken};
    const uint32_t playerStateToken = arguments[2];
    clearDirectionalInputLatches(run);
    releaseHeldEffect(run, playerStateToken);
    const uint32_t pendingAnimation = run.get(playerStateToken + 4);
    run.put(playerStateToken + 0x20, 1);
    run.put(playerStateToken + 0x3c, 0);
    if (pendingAnimation != 0) {
        const uint32_t animationToken = run.get(playerStateToken + 0x124);
        run.put(playerStateToken + 4, 0);
        run.call(0x4c8220, playerActorToken + 0x188, {animationToken});
        const uint32_t actorFlags = run.get(playerActorToken + 8);
        run.put(playerActorToken + 8, actorFlags | 0x80);
    }
    holderFields.state(9);
    const uint32_t facingRight = run.get(playerStateToken);
    if (facingRight != 0) {
        const uint32_t motionFlags = run.get(playerActorToken + 0x40);
        const uint32_t left = run.get(playerActorToken + 0x118);
        run.put(playerActorToken + 0x40, motionFlags | 2);
        if (left != 0x80000000) {
            const uint32_t right = run.get(playerActorToken + 0x120);
            run.put(playerActorToken + 0x118, 0u - right);
            run.put(playerActorToken + 0x120, 0u - left);
        }
        run.call(0x406150, playerActorToken, {});
        run.call(0x406180, playerActorToken, {});
        run.put(playerStateToken, 0);
        run.put(playerStateToken + 0x114, 0x5dc);
    }
    run.call(0x4c79e0, playerActorToken, {0x52469c, 0});
    run.put(playerActorToken + 0xcc, 2);
    run.put(playerActorToken + 0x148, run.get(0x4187e2));
    run.put(playerActorToken + 0x14c, 0);
    run.put(playerStateToken + 0xf8, 0);
    run.put(0x534e60, 0);
    run.put(0x534e64, 0);
    run.put(0x534e68, 0);
    run.put(0x534e6c, 0);
    run.put(0x534e70, 0);
    run.put(0x534e74, 0);
    return 0;
}

// 0x417f20. cdecl, 3 stack argument(s), returns void.
uint32_t enterWalkingRight(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t playerActorToken = arguments[0];
    const uint32_t holderToken = arguments[1];
    LogicHolderFields holderFields{run, holderToken};
    const uint32_t playerStateToken = arguments[2];
    clearDirectionalInputLatches(run);
    releaseHeldEffect(run, playerStateToken);
    const uint32_t pendingAnimation = run.get(playerStateToken + 4);
    run.put(playerStateToken + 0x3c, 0);
    run.put(playerStateToken + 0x20, 1);
    if (pendingAnimation != 0) {
        const uint32_t animationToken = run.get(playerStateToken + 0x124);
        run.put(playerStateToken + 4, 0);
        run.call(0x4c8220, playerActorToken + 0x188, {animationToken});
        const uint32_t actorFlags = run.get(playerActorToken + 8);
        run.put(playerActorToken + 8, actorFlags | 0x80);
    }
    holderFields.state(8);
    const uint32_t facingRight = run.get(playerStateToken);
    if (facingRight == 0) {
        const uint32_t motionFlags = run.get(playerActorToken + 0x40);
        const uint32_t left = run.get(playerActorToken + 0x118);
        run.put(playerActorToken + 0x40, motionFlags & 0xfffffffd);
        if (left != 0x80000000) {
            const uint32_t right = run.get(playerActorToken + 0x120);
            run.put(playerActorToken + 0x118, 0u - right);
            run.put(playerActorToken + 0x120, 0u - left);
        }
        run.call(0x406150, playerActorToken, {});
        run.call(0x406180, playerActorToken, {});
        run.put(playerStateToken, 1);
        run.put(playerStateToken + 0x114, 0x5dc);
    }
    run.call(0x4c79e0, playerActorToken, {0x52469c, 0});
    run.put(playerActorToken + 0xcc, 2);
    run.put(playerActorToken + 0x148, run.get(0x418432));
    run.put(playerActorToken + 0x14c, 0);
    run.put(playerStateToken + 0xf8, 0);
    run.put(0x534e60, 0);
    run.put(0x534e64, 0);
    run.put(0x534e68, 0);
    run.put(0x534e6c, 0);
    run.put(0x534e70, 0);
    run.put(0x534e74, 0);
    return 0;
}

// Animation name strings: 0x5246dc CLAW_FALL, 0x5246d0 CLAW_STAND, 0x5246c4 CLAW_CLIMB, 0x52469c CLAW_WALK.

// Pack a double into the two stack words a double argument occupies.
void splitBinary64Argument(double value, uint32_t &low, uint32_t &high) {
    uint64_t bits = 0;
    std::memcpy(&bits, &value, 8);
    low = static_cast<uint32_t>(bits);
    high = static_cast<uint32_t>(bits >> 32);
}

// Hit box of the standing or falling pose, chosen by the facing word at state+0.
void setStandingOrFallingBounds(Run &run, uint32_t playerActorToken, uint32_t playerStateToken) {
    const uint32_t facingRight = run.get(playerStateToken);
    if (facingRight != 0) {
        run.call(0x4208b0, playerActorToken, {0xffffffea, 0xffffffd3, 0xf, 0x34});
    } else {
        run.call(0x4208b0, playerActorToken, {0xfffffff1, 0xffffffd3, 0x16, 0x34});
    }
}

// Zero the six words of scratch at 0x534e60..0x534e77.
void clearMovementRemainders(Run &run) {
    run.put(0x534e60, 0);
    run.put(0x534e64, 0);
    run.put(0x534e68, 0);
    run.put(0x534e6c, 0);
    run.put(0x534e70, 0);
    run.put(0x534e74, 0);
}

// Integrate the integrator block over one frame, then split the position at 0x534e40 into a whole
// part (returned) and a fraction kept at 0x534e60. Returns 0 when 0x534e58 disables the split.
uint32_t takeIntegratedPositionStep(Run &run) {
    const uint32_t disabled = run.get(0x534e58);
    if (disabled != 0)
        return 0;
    const double position = run.getd(0x534e40);
    const uint32_t whole = truncateToLowWord(position);
    const double rest = run.getd(0x534e40) - static_cast<double>(claw::s32(whole));
    const double carried = rest + run.getd(0x534e60);
    const double shifted = carried + run.getd(0x534e40);
    const uint32_t shifted_whole = truncateToLowWord(shifted);
    run.put(0x544e8c, shifted_whole);
    const uint32_t carried_whole = truncateToLowWord(carried);
    const double fraction = carried - static_cast<double>(claw::s32(carried_whole));
    run.putd(0x534e60, fraction);
    return run.get(0x544e8c);
}

// Feed the integrator one frame step.
void stepMovementIntegrator(Run &run) {
    const uint32_t frameMilliseconds = run.get(kFrameMillisecondsAddress);
    const double scaled = static_cast<double>(frameMilliseconds) * run.getd(0x50bab0);
    uint32_t low = 0;
    uint32_t high = 0;
    splitBinary64Argument(scaled, low, high);
    run.call(0x403b40, kMovementIntegratorAddress, {low, high});
}

// Falling-pose entry shared by several callbacks: start CLAW_FALL, either through the animation
// map (when the previous kind asks for it, `slot` is the argument slot used as its out value) or
// through the generic reset.
void beginFallingAnimation(Run &run, uint32_t playerActorToken, uint32_t holderToken, uint32_t playerStateToken, uint32_t slot) {
    const uint32_t kind = run.get(playerStateToken + 0x3c);
    if (kind == 8 || kind == 9 || kind == 10 || kind == 0x12) {
        const uint32_t actorOwnerToken = run.get(playerActorToken + 0xc);
        const uint32_t sets = run.get(actorOwnerToken + 0x2c);
        run.put(slot, 0);
        run.call(0x4f6286, sets + 0x10, {0x5246dc, slot});
        const uint32_t animationToken = run.get(slot);
        run.put(playerStateToken + 0x124, animationToken);
    } else {
        run.call(0x41c4e0, 0, {playerActorToken, holderToken, playerStateToken});
        run.call(0x4c79e0, playerActorToken, {0x5246dc, 0});
    }
}

// Common tail of the falling entry: take the fall pose, keep the state record in step.
void publishFallingPose(Run &run, uint32_t playerActorToken, uint32_t holderToken) {
    LogicHolderFields holderFields{run, holderToken};
    holderFields.state(0x19);
    const uint32_t actorFlags = run.get(playerActorToken + 8);
    run.put(playerActorToken + 0xcc, 4);
    run.put(playerActorToken + 0x148, 0);
    run.put(playerActorToken + 0x14c, 0);
    run.put(playerActorToken + 8, actorFlags & 0xffffffef);
}

void resetFallingIntegratorGlobals(Run &run) {
    run.put(0x534de8, 0);
    run.put(0x534dec, 0);
    run.put(0x534dd0, 0);
    run.put(0x534dd4, 0x40a19400);
}

// 0x418790. cdecl, 3 stack argument(s), returns void.
uint32_t updateWalkingLeftPose(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t playerActorToken = arguments[0];
    const uint32_t holderToken = arguments[1];
    LogicHolderFields holderFields{run, holderToken};
    const uint32_t playerStateToken = arguments[2];
    const uint32_t frameMilliseconds = run.get(kFrameMillisecondsAddress);
    uint32_t positionX = run.get(playerActorToken + 0x4c);
    uint32_t positionY = run.get(playerActorToken + 0x50);
    const uint32_t walkingCountdownMilliseconds = run.get(playerStateToken + 0x114);
    if (frameMilliseconds < walkingCountdownMilliseconds) {
        run.put(playerStateToken + 0x114, walkingCountdownMilliseconds - frameMilliseconds);
    } else {
        run.put(playerStateToken + 0x114, 0);
    }
    run.put(playerActorToken + 0x1b0, 0x3f800000);
    const uint32_t weapon = run.get(0x534eac);
    // Keep the original operand storage addressable for custom-session settings.
    uint32_t horizontalStepInput = run.get(0x4187e2);
    if (weapon == 0x26bc) {
        horizontalStepInput = run.get(0x4187e9);
        run.put(playerActorToken + 0x1b0, 0x3f4ccccd);
    } else if (run.get(playerStateToken + 0x114) == 0) {
        horizontalStepInput = run.get(0x418802);
        run.put(playerActorToken + 0x1b0, 0x3f666666);
    }
    horizontalStepInput = horizontalStepInput + run.get(playerStateToken + 0x84);
    run.put(playerActorToken + 0x148, horizontalStepInput);
    run.putd(0x534de0, static_cast<double>(claw::s32(horizontalStepInput)));
    stepMovementIntegrator(run);
    const uint32_t whole = takeIntegratedPositionStep(run);
    positionX = positionX + whole;
    const uint8_t actorFlagsLowByte = run.get8(playerActorToken + 8);
    if ((actorFlagsLowByte & 0x10) != 0) {
        const uint32_t carrierActorToken = run.get(playerActorToken + 0x80);
        if (carrierActorToken != 0) {
            positionX = positionX + run.get(carrierActorToken + 0x158);
            positionY = positionY + run.get(carrierActorToken + 0x15c);
        }
    }
    const uint32_t actorOwnerToken = run.get(playerActorToken + 0xc);
    const uint32_t worldPlaneToken = run.get(actorOwnerToken + 0x24);
    run.call(0x4cbb60, worldPlaneToken, {playerActorToken, positionX, positionY, 8});
    const uint32_t pose = run.get(playerActorToken + 0xcc);
    if (pose != 1) {
        if (pose != 4) {
            run.call(0x4c82a0, playerActorToken + 0x188, {run.get(kAnimationMillisecondsAddress)});
            return 0;
        }
        beginFallingAnimation(run, playerActorToken, holderToken, playerStateToken, run.automatic(8));
        publishFallingPose(run, playerActorToken, holderToken);
        setStandingOrFallingBounds(run, playerActorToken, playerStateToken);
        run.call(0x4170b0, 0, {playerActorToken, playerStateToken});
        run.put(playerStateToken + 0x40, 0);
        resetFallingIntegratorGlobals(run);
        return 0;
    }
    clearDirectionalInputLatches(run);
    resetAndReleaseHeldEffect(run, playerStateToken);
    const uint32_t pendingAnimation = run.get(playerStateToken + 4);
    run.put(playerStateToken + 0x3c, 0);
    run.put(playerStateToken + 0x20, 1);
    if (pendingAnimation != 0) {
        const uint32_t animationToken = run.get(playerStateToken + 0x124);
        run.put(playerStateToken + 4, 0);
        run.call(0x420a10, playerActorToken, {animationToken, 0});
        const uint32_t actorFlags = run.get(playerActorToken + 8);
        run.put(playerActorToken + 8, actorFlags | 0x80);
    }
    holderFields.state(0x18);
    run.call(0x4c79e0, playerActorToken, {0x5246d0, 1});
    const uint32_t actorFlags = run.get(playerActorToken + 8);
    run.put(playerActorToken + 0xcc, 1);
    run.put(playerActorToken + 0x148, 0);
    run.put(playerActorToken + 0x14c, 0);
    run.put(playerActorToken + 0x104, 0);
    run.put(playerActorToken + 8, actorFlags | 0x80);
    run.call(0x417050, 0, {playerActorToken, playerStateToken});
    run.call(0x4170b0, 0, {playerActorToken, playerStateToken});
    run.put(playerStateToken + 0xfc, 0x28a);
    run.put(playerStateToken + 0x114, 0x5dc);
    run.put(playerStateToken + 0x120, 0x3a98);
    run.put(playerStateToken + 0x118, 0);
    clearMovementRemainders(run);
    run.put(playerActorToken + 0x1b0, 0x3f800000);
    return 0;
}

// 0x4197e0. cdecl, 3 stack argument(s), returns void.
uint32_t enterLookingUpPose(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t playerActorToken = arguments[0];
    const uint32_t holderToken = arguments[1];
    LogicHolderFields holderFields{run, holderToken};
    const uint32_t playerStateToken = arguments[2];
    clearDirectionalInputLatches(run);
    markHeldEffectForRelease(run, playerStateToken);
    const uint32_t pendingAnimation = run.get(playerStateToken + 4);
    run.put(playerStateToken + 0x3c, 0);
    run.put(playerStateToken + 0x20, 1);
    if (pendingAnimation != 0) {
        const uint32_t animationToken = run.get(playerStateToken + 0x124);
        run.put(playerStateToken + 4, 0);
        run.call(0x420a10, playerActorToken, {animationToken, 0});
        const uint32_t actorFlags = run.get(playerActorToken + 8);
        run.put(playerActorToken + 8, actorFlags | 0x80);
    }
    holderFields.state(0x138b);
    run.call(0x4c79e0, playerActorToken, {0x524768, 0});
    run.put(playerActorToken + 0xcc, 1);
    run.put(playerActorToken + 0x148, 0);
    run.put(playerActorToken + 0x14c, 0);
    run.put(playerStateToken + 0x110, 0xfa);
    return 0;
}

// 0x4198d0. cdecl, 3 stack argument(s), returns void.
uint32_t updateStationaryPoseAfterAnimation(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t playerActorToken = arguments[0];
    const uint32_t holderToken = arguments[1];
    LogicHolderFields holderFields{run, holderToken};
    const uint32_t playerStateToken = arguments[2];
    const uint8_t actorFlagsLowByte = run.get8(playerActorToken + 8);
    uint32_t positionX = run.get(playerActorToken + 0x4c);
    uint32_t positionY = run.get(playerActorToken + 0x50);
    run.put(playerActorToken + 0x148, 0);
    run.put(playerActorToken + 0x14c, 0);
    if ((actorFlagsLowByte & 0x10) != 0) {
        const uint32_t carrierActorToken = run.get(playerActorToken + 0x80);
        if (carrierActorToken != 0) {
            positionX = positionX + run.get(carrierActorToken + 0x158);
            positionY = positionY + run.get(carrierActorToken + 0x15c);
        }
    }
    const uint32_t actorOwnerToken = run.get(playerActorToken + 0xc);
    const uint32_t worldPlaneToken = run.get(actorOwnerToken + 0x24);
    run.call(0x4cbb60, worldPlaneToken, {playerActorToken, positionX, positionY, 0x18});
    const uint32_t pose = run.get(playerActorToken + 0xcc);
    if (pose == 4) {
        beginFallingAnimation(run, playerActorToken, holderToken, playerStateToken, run.automatic(12));
        publishFallingPose(run, playerActorToken, holderToken);
        run.call(0x417050, 0, {playerActorToken, playerStateToken});
        run.call(0x4170b0, 0, {playerActorToken, playerStateToken});
        run.put(playerStateToken + 0x40, 0);
        resetFallingIntegratorGlobals(run);
        return 0;
    }
    if (pose == 6) {
        run.call(0x41c4e0, 0, {playerActorToken, holderToken, playerStateToken});
        holderFields.state(0x1b);
        run.call(0x4c79e0, playerActorToken, {0x5246c4, 0});
        const uint32_t actorFlags = run.get(playerActorToken + 8);
        run.put(playerActorToken + 0xcc, 6);
        run.put(playerActorToken + 0x148, 0);
        run.put(playerActorToken + 0x14c, 0);
        run.put(playerActorToken + 8, actorFlags & 0xffffffef);
        run.put(playerStateToken + 0x2c, 0);
        run.put(playerStateToken + 0x68, 0);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0);
        return 0;
    }
    run.call(0x4c82a0, playerActorToken + 0x188, {run.get(kAnimationMillisecondsAddress)});
    const uint32_t animationFinished = run.get(playerActorToken + 0x1a4);
    if (animationFinished == 0)
        return 0;
    const uint32_t animationLoops = run.get(playerActorToken + 0x19c);
    if (animationLoops != 0)
        return 0;
    const uint32_t inputObjectToken = run.get(kInputObjectPointerAddress);
    const uint32_t held = run.get(inputObjectToken + 8);
    if ((held & 0x2000000) != 0) {
        run.call(0x41c4e0, 0, {playerActorToken, holderToken, playerStateToken});
        holderFields.state(8);
        if (run.get(playerStateToken) == 0) {
            const uint32_t motionFlags = run.get(playerActorToken + 0x40);
            run.put(playerActorToken + 0x40, motionFlags & 0xfffffffd);
            run.call(0x4060b0, playerActorToken, {});
            run.put(playerStateToken, 1);
            run.put(playerStateToken + 0x114, 0x5dc);
        }
        run.call(0x4c79e0, playerActorToken, {0x52469c, 0});
        run.put(playerActorToken + 0xcc, 2);
        run.put(playerActorToken + 0x148, run.get(0x418432));
    } else if ((held & 0x1000000) != 0) {
        run.call(0x41c4e0, 0, {playerActorToken, holderToken, playerStateToken});
        holderFields.state(9);
        if (run.get(playerStateToken) != 0) {
            const uint32_t motionFlags = run.get(playerActorToken + 0x40);
            run.put(playerActorToken + 0x40, motionFlags | 2);
            run.call(0x4060b0, playerActorToken, {});
            run.put(playerStateToken, 0);
            run.put(playerStateToken + 0x114, 0x5dc);
        }
        run.call(0x4c79e0, playerActorToken, {0x52469c, 0});
        run.put(playerActorToken + 0xcc, 2);
        run.put(playerActorToken + 0x148, run.get(0x4187e2));
    } else {
        run.call(0x41c4e0, 0, {playerActorToken, holderToken, playerStateToken});
        holderFields.state(0x18);
        run.call(0x4c79e0, playerActorToken, {0x5246d0, 1});
        const uint32_t actorFlags = run.get(playerActorToken + 8);
        run.put(playerActorToken + 0xcc, 1);
        run.put(playerActorToken + 0x148, 0);
        run.put(playerActorToken + 0x14c, 0);
        run.put(playerActorToken + 0x104, 0);
        run.put(playerActorToken + 8, actorFlags | 0x80);
        run.call(0x417050, 0, {playerActorToken, playerStateToken});
        run.call(0x4170b0, 0, {playerActorToken, playerStateToken});
        run.put(playerStateToken + 0xfc, 0x28a);
        run.put(playerStateToken + 0x114, 0x5dc);
        run.put(playerStateToken + 0x120, 0x3a98);
        run.put(playerStateToken + 0x118, 0);
        clearMovementRemainders(run);
        run.put(playerActorToken + 0x1b0, 0x3f800000);
        return 0;
    }
    run.put(playerActorToken + 0x14c, 0);
    run.put(playerStateToken + 0xf8, 0);
    clearMovementRemainders(run);
    return 0;
}

// 0x419c80. cdecl, 3 stack argument(s), returns void.
uint32_t updateStandingInputAndSupport(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t playerActorToken = arguments[0];
    const uint32_t holderToken = arguments[1];
    LogicHolderFields holderFields{run, holderToken};
    const uint32_t playerStateToken = arguments[2];
    run.put(playerActorToken + 0x148, 0);
    run.put(playerActorToken + 0x14c, 0);
    const uint32_t inputObjectToken = run.get(kInputObjectPointerAddress);
    const uint32_t held = run.get(inputObjectToken + 8);
    uint32_t layer = 0x18;
    if ((held & 0x4000000) != 0) {
        layer = 0x19;
    } else if ((held & 0x8000000) != 0) {
        layer = 0x1a;
    }
    const uint8_t actorFlagsLowByte = run.get8(playerActorToken + 8);
    uint32_t positionX = run.get(playerActorToken + 0x4c);
    uint32_t positionY = run.get(playerActorToken + 0x50);
    if ((actorFlagsLowByte & 0x10) != 0) {
        const uint32_t carrierActorToken = run.get(playerActorToken + 0x80);
        if (carrierActorToken != 0) {
            positionX = positionX + run.get(carrierActorToken + 0x158);
            positionY = positionY + run.get(carrierActorToken + 0x15c);
        }
    }
    const uint32_t actorOwnerToken = run.get(playerActorToken + 0xc);
    const uint32_t worldPlaneToken = run.get(actorOwnerToken + 0x24);
    run.call(0x4cbb60, worldPlaneToken, {playerActorToken, positionX, positionY, layer});
    const uint32_t pose = run.get(playerActorToken + 0xcc);
    if (pose == 4) {
        beginFallingAnimation(run, playerActorToken, holderToken, playerStateToken, run.automatic(4));
        publishFallingPose(run, playerActorToken, holderToken);
        run.call(0x417050, 0, {playerActorToken, playerStateToken});
        run.call(0x4170b0, 0, {playerActorToken, playerStateToken});
        run.put(playerStateToken + 0x40, 0);
        resetFallingIntegratorGlobals(run);
    } else if (pose == 6) {
        run.call(0x41c4e0, 0, {playerActorToken, holderToken, playerStateToken});
        holderFields.state(0x1b);
        run.call(0x4c79e0, playerActorToken, {0x5246c4, 0});
        const uint32_t actorFlags = run.get(playerActorToken + 8);
        run.put(playerActorToken + 0xcc, 6);
        run.put(playerActorToken + 0x148, 0);
        run.put(playerActorToken + 0x14c, 0);
        run.put(playerActorToken + 8, actorFlags & 0xffffffef);
        run.put(playerStateToken + 0x2c, 0);
        run.put(playerStateToken + 0x68, 0);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0);
    } else {
        run.call(0x4c82a0, playerActorToken + 0x188, {run.get(kAnimationMillisecondsAddress)});
    }
    const uint32_t facingRight = run.get(playerStateToken);
    if (facingRight == 0) {
        const uint32_t busy = run.call(0x41e790, 0, {playerActorToken});
        if (busy == 0)
            run.call(0x4171d0, 0, {playerActorToken, holderToken, playerStateToken});
        return 0;
    }
    uint32_t blocked = 0;
    const uint8_t currentActorFlagsLowByte = run.get8(playerActorToken + 8);
    if ((currentActorFlagsLowByte & 0x10) != 0) {
        blocked = run.call(0x4bb030, 0, {playerActorToken});
    } else {
        const uint32_t reloadedActorOwnerToken = run.get(playerActorToken + 0xc);
        const uint32_t tiles = run.get(reloadedActorOwnerToken + 0x24);
        const uint32_t first = run.get(playerActorToken + 0x118);
        const uint32_t probe = run.call(0x4cd1c0, tiles, {playerActorToken, first});
        if (probe != 0) {
            uint32_t cursor = run.get(playerActorToken + 0x118);
            const uint32_t limit = run.get(playerActorToken + 0x120);
            cursor = cursor + 0xc;
            if (claw::s32(cursor) < claw::s32(limit)) {
                bool clear_all = true;
                while (true) {
                    const uint32_t cell = run.call(0x4cd1c0, tiles, {playerActorToken, cursor});
                    if (cell != 0) {
                        clear_all = false;
                        break;
                    }
                    cursor = cursor + 4;
                    if (!(claw::s32(cursor) < claw::s32(limit)))
                        break;
                }
                if (clear_all) {
                    const uint32_t last = run.call(0x4cd1c0, tiles, {playerActorToken, limit});
                    blocked = last == 0 ? 1 : 0;
                }
            }
        }
    }
    if (blocked != 0)
        return 0;
    run.call(0x41c4e0, 0, {playerActorToken, holderToken, playerStateToken});
    holderFields.state(0x18);
    run.call(0x4c79e0, playerActorToken, {0x5246d0, 1});
    const uint32_t actorFlags = run.get(playerActorToken + 8);
    run.put(playerActorToken + 0xcc, 1);
    run.put(playerActorToken + 0x148, 0);
    run.put(playerActorToken + 0x14c, 0);
    run.put(playerActorToken + 0x104, 0);
    run.put(playerActorToken + 8, actorFlags | 0x80);
    setStandingOrFallingBounds(run, playerActorToken, playerStateToken);
    run.call(0x4170b0, 0, {playerActorToken, playerStateToken});
    run.put(playerStateToken + 0xfc, 0x28a);
    run.put(playerStateToken + 0x114, 0x5dc);
    run.put(playerStateToken + 0x120, 0x3a98);
    run.put(playerStateToken + 0x118, 0);
    clearMovementRemainders(run);
    run.put(playerActorToken + 0x1b0, 0x3f800000);
    return 0;
}

// 0x419fd0. cdecl, 3 stack argument(s), returns void.
uint32_t updateActionPoseAndDirection(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t playerActorToken = arguments[0];
    const uint32_t holderToken = arguments[1];
    const uint32_t playerStateToken = arguments[2];
    const uint32_t animationMilliseconds = run.get(kAnimationMillisecondsAddress);
    const uint32_t poseCountdownMilliseconds = run.get(playerStateToken + 0x110);
    if (animationMilliseconds < poseCountdownMilliseconds) {
        run.put(playerStateToken + 0x110, poseCountdownMilliseconds - animationMilliseconds);
    } else {
        run.put(playerStateToken + 0x110, 0);
    }
    const uint8_t actorFlagsLowByte = run.get8(playerActorToken + 8);
    uint32_t positionX = run.get(playerActorToken + 0x4c);
    uint32_t positionY = run.get(playerActorToken + 0x50);
    run.put(playerActorToken + 0x148, 0);
    run.put(playerActorToken + 0x14c, 0);
    if ((actorFlagsLowByte & 0x10) != 0) {
        const uint32_t carrierActorToken = run.get(playerActorToken + 0x80);
        if (carrierActorToken != 0) {
            positionX = positionX + run.get(carrierActorToken + 0x158);
            positionY = positionY + run.get(carrierActorToken + 0x15c);
        }
    }
    const uint32_t additionalHorizontalStepInput = run.get(playerStateToken + 0x84);
    if (additionalHorizontalStepInput != 0) {
        run.putd(0x534e60, run.getd(0x50ba88));
        run.putd(0x534e68, run.getd(0x50ba88));
        run.putd(0x534e70, run.getd(0x50ba88));
        run.putd(0x534de0, static_cast<double>(claw::s32(run.get(playerStateToken + 0x84))));
        stepMovementIntegrator(run);
        positionX = positionX + takeIntegratedPositionStep(run);
    }
    const uint32_t actorOwnerToken = run.get(playerActorToken + 0xc);
    const uint32_t worldPlaneToken = run.get(actorOwnerToken + 0x24);
    run.call(0x4cbb60, worldPlaneToken, {playerActorToken, positionX, positionY, 8});
    const uint32_t pose = run.get(playerActorToken + 0xcc);
    if (pose == 4) {
        beginFallingAnimation(run, playerActorToken, holderToken, playerStateToken, run.automatic(12));
        publishFallingPose(run, playerActorToken, holderToken);
        run.call(0x417050, 0, {playerActorToken, playerStateToken});
        run.call(0x4170b0, 0, {playerActorToken, playerStateToken});
        run.put(playerStateToken + 0x40, 0);
        resetFallingIntegratorGlobals(run);
    } else if (run.get(playerStateToken + 4) == 0) {
        run.call(0x4c82a0, playerActorToken + 0x188, {run.get(kAnimationMillisecondsAddress)});
    } else {
        const uint32_t result = run.call(0x4c82a0, playerActorToken + 0x188, {run.get(kAnimationMillisecondsAddress)});
        const uint32_t animationFinished = run.get(playerActorToken + 0x1a4);
        const uint32_t animationLoops = run.get(playerActorToken + 0x19c);
        if (animationFinished != 0 && animationLoops == 0) {
            run.call(0x41c4e0, 0, {playerActorToken, holderToken, playerStateToken});
        } else {
            if (run.get(playerStateToken + 0x1c) != 0)
                run.put(playerStateToken + 0x20, 1);
            const uint32_t actorFlags = run.get(playerActorToken + 8);
            run.put(playerActorToken + 8, actorFlags | 0x80);
            const uint32_t phase = result - 1;
            if (phase <= 4) {
                switch (result) {
                case 1:
                    run.put(playerActorToken + 8, (actorFlags | 0x80) & 0xffffff7f);
                    run.put(playerStateToken + 0x1c, 1);
                    break;
                case 2: {
                    run.put(playerStateToken + 0x1c, 1);
                    if (run.get(playerStateToken + 0x10) == 0) {
                        const uint32_t mode = run.get(playerStateToken + 0x30);
                        run.put(playerStateToken + 0x10, 1);
                        if (mode == 1) {
                            run.call(0x41c9f0, 0, {playerActorToken, holderToken, playerStateToken});
                        } else if (mode == 2) {
                            run.call(0x41cab0, 0, {playerActorToken, holderToken, playerStateToken});
                        } else if (mode == 3) {
                            run.call(0x41cb80, 0, {playerActorToken, holderToken, playerStateToken});
                        }
                    }
                    break;
                }
                case 3: {
                    const uint32_t inputObjectToken = run.get(kInputObjectPointerAddress);
                    const uint32_t buttons = run.get(inputObjectToken + 4);
                    bool pressed = false;
                    if ((buttons & 4) != 0) {
                        pressed = true;
                    } else {
                        const uint32_t mode = run.get(playerStateToken + 0x30);
                        if (mode == 1 && (buttons & 0x40) != 0) {
                            pressed = true;
                        } else if (mode == 2 && (buttons & 0x80) != 0) {
                            pressed = true;
                        }
                    }
                    if (pressed) {
                        bool allowed = true;
                        if (run.get(playerStateToken + 0x30) == 1) {
                            const int32_t charges = run.gets(playerStateToken + 0x70);
                            if (charges <= 0)
                                allowed = false;
                        }
                        if (allowed) {
                            const uint32_t count = run.get(playerStateToken + 0xe8);
                            const uint32_t sound = run.get(playerStateToken + 0x6c);
                            run.put(playerStateToken + 0xe8, count + 1);
                            run.put(playerStateToken + 0x10, 0);
                            run.call(0x420970, playerActorToken + 0x188, {sound});
                        }
                    }
                    break;
                }
                case 4: {
                    const uint32_t inputObjectToken = run.get(kInputObjectPointerAddress);
                    const uint32_t held = run.get(inputObjectToken + 8);
                    if ((held & 4) == 0 && (held & 0x100) == 0) {
                        const uint32_t low = run.get(playerStateToken + 0x104);
                        const uint32_t high = run.get(playerStateToken + 0x100);
                        uint32_t chosen = low;
                        if (high > low)
                            chosen = high;
                        const uint32_t animationToken = run.get(playerStateToken + 0x128);
                        run.put(playerStateToken + 0x100, chosen);
                        run.call(0x420a10, playerActorToken, {animationToken, 0});
                    } else {
                        const uint32_t frameMilliseconds = run.get(kFrameMillisecondsAddress);
                        const uint32_t heldMilliseconds = run.get(playerStateToken + 0x100);
                        const uint32_t totalHeldMilliseconds = heldMilliseconds + frameMilliseconds;
                        const uint32_t limit = run.get(playerStateToken + 0x108);
                        run.put(playerStateToken + 0x100, totalHeldMilliseconds);
                        if (totalHeldMilliseconds >= limit) {
                            const uint32_t animationToken = run.get(playerStateToken + 0x128);
                            run.put(playerStateToken + 0x100, limit);
                            run.call(0x420a10, playerActorToken, {animationToken, 0});
                        }
                    }
                    break;
                }
                case 5: {
                    run.put(playerStateToken + 0x1c, 1);
                    run.call(0x41cc60, 0, {playerActorToken, holderToken, playerStateToken});
                    break;
                }
                default:
                    break;
                }
            }
        }
    }
    bool settled = true;
    if (run.get(playerStateToken + 4) != 0) {
        if (run.get(playerStateToken + 0x20) == 0)
            settled = false;
    }
    const uint32_t inputObjectToken = run.get(kInputObjectPointerAddress);
    if (settled) {
        const uint32_t held = run.get(inputObjectToken + 8);
        if ((held & 0x8000000) == 0) {
            if (run.get(playerActorToken + 0xcc) == 5) {
                run.call(0x4171d0, 0, {playerActorToken, holderToken, playerStateToken});
                return 0;
            }
        }
    }
    if (settled) {
        if (run.get(playerStateToken) != 0 && (run.get(inputObjectToken + 8) & 0x1000000) != 0) {
            const uint32_t motionFlags = run.get(playerActorToken + 0x40);
            run.put(playerActorToken + 0x40, motionFlags | 2);
            run.call(0x4060b0, playerActorToken, {});
            run.put(playerStateToken, 0);
            run.put(playerStateToken + 0x114, 0x5dc);
            return 0;
        }
        if (run.get(playerStateToken) == 0 && (run.get(inputObjectToken + 8) & 0x2000000) != 0)
            run.call(0x418120, 0, {playerActorToken, holderToken, playerStateToken});
    }
    return 0;
}

// 0x41a490. cdecl, 3 stack argument(s), returns void.
uint32_t updateStandingPoseOnInputRelease(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t playerActorToken = arguments[0];
    const uint32_t holderToken = arguments[1];
    LogicHolderFields holderFields{run, holderToken};
    const uint32_t playerStateToken = arguments[2];
    const uint32_t animationMilliseconds = run.get(kAnimationMillisecondsAddress);
    const uint32_t poseCountdownMilliseconds = run.get(playerStateToken + 0x110);
    if (animationMilliseconds < poseCountdownMilliseconds) {
        run.put(playerStateToken + 0x110, poseCountdownMilliseconds - animationMilliseconds);
    } else {
        run.put(playerStateToken + 0x110, 0);
    }
    const uint8_t actorFlagsLowByte = run.get8(playerActorToken + 8);
    uint32_t positionX = run.get(playerActorToken + 0x4c);
    uint32_t positionY = run.get(playerActorToken + 0x50);
    if ((actorFlagsLowByte & 0x10) != 0) {
        const uint32_t carrierActorToken = run.get(playerActorToken + 0x80);
        if (carrierActorToken != 0) {
            positionX = positionX + run.get(carrierActorToken + 0x158);
            positionY = positionY + run.get(carrierActorToken + 0x15c);
        }
    }
    const uint32_t additionalHorizontalStepInput = run.get(playerStateToken + 0x84);
    if (additionalHorizontalStepInput != 0) {
        run.putd(0x534e60, run.getd(0x50ba88));
        run.putd(0x534e68, run.getd(0x50ba88));
        run.putd(0x534e70, run.getd(0x50ba88));
        run.putd(0x534de0, static_cast<double>(claw::s32(run.get(playerStateToken + 0x84))));
        stepMovementIntegrator(run);
        positionX = positionX + takeIntegratedPositionStep(run);
    }
    const uint32_t actorOwnerToken = run.get(playerActorToken + 0xc);
    const uint32_t worldPlaneToken = run.get(actorOwnerToken + 0x24);
    run.call(0x4cbb60, worldPlaneToken, {playerActorToken, positionX, positionY, 8});
    const uint32_t pose = run.get(playerActorToken + 0xcc);
    if (pose == 4) {
        beginFallingAnimation(run, playerActorToken, holderToken, playerStateToken, run.automatic(12));
        publishFallingPose(run, playerActorToken, holderToken);
        setStandingOrFallingBounds(run, playerActorToken, playerStateToken);
        run.call(0x4170b0, 0, {playerActorToken, playerStateToken});
        run.put(playerStateToken + 0x40, 0);
        resetFallingIntegratorGlobals(run);
    } else {
        run.call(0x4c82a0, playerActorToken + 0x188, {run.get(kAnimationMillisecondsAddress)});
    }
    const uint32_t inputObjectToken = run.get(kInputObjectPointerAddress);
    const uint32_t held = run.get(inputObjectToken + 8);
    if ((held & 0x4000000) != 0)
        return 0;
    if (run.get(playerActorToken + 0xcc) != 1)
        return 0;
    clearDirectionalInputLatches(run);
    resetAndReleaseHeldEffect(run, playerStateToken);
    const uint32_t pendingAnimation = run.get(playerStateToken + 4);
    run.put(playerStateToken + 0x3c, 0);
    run.put(playerStateToken + 0x20, 1);
    if (pendingAnimation != 0) {
        const uint32_t animationToken = run.get(playerStateToken + 0x124);
        run.put(playerStateToken + 4, 0);
        run.call(0x420a10, playerActorToken, {animationToken, 0});
        const uint32_t actorFlags = run.get(playerActorToken + 8);
        run.put(playerActorToken + 8, actorFlags | 0x80);
    }
    holderFields.state(0x18);
    run.call(0x4c79e0, playerActorToken, {0x5246d0, 1});
    const uint32_t actorFlags = run.get(playerActorToken + 8);
    run.put(playerActorToken + 0xcc, 1);
    run.put(playerActorToken + 0x148, 0);
    run.put(playerActorToken + 0x14c, 0);
    run.put(playerActorToken + 0x104, 0);
    run.put(playerActorToken + 8, actorFlags | 0x80);
    setStandingOrFallingBounds(run, playerActorToken, playerStateToken);
    run.call(0x40f6c0, playerActorToken, {0xfffffff0, 0xffffffcc, 0x10, 0x3c});
    run.put(playerStateToken + 0xfc, 0x28a);
    run.put(playerStateToken + 0x114, 0x5dc);
    run.put(playerStateToken + 0x120, 0x3a98);
    run.put(playerStateToken + 0x118, 0);
    clearMovementRemainders(run);
    run.put(playerActorToken + 0x1b0, 0x3f800000);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4170f0:
        return enterClimbingPose(run, receiver, arguments);
    case 0x417480:
        return enterTeeteringPose(run, receiver, arguments);
    case 0x417dd0:
        return enterWalkingLeft(run, receiver, arguments);
    case 0x417f20:
        return enterWalkingRight(run, receiver, arguments);
    case 0x418790:
        return updateWalkingLeftPose(run, receiver, arguments);
    case 0x4197e0:
        return enterLookingUpPose(run, receiver, arguments);
    case 0x4198d0:
        return updateStationaryPoseAfterAnimation(run, receiver, arguments);
    case 0x419c80:
        return updateStandingInputAndSupport(run, receiver, arguments);
    case 0x419fd0:
        return updateActionPoseAndDirection(run, receiver, arguments);
    case 0x41a490:
        return updateStandingPoseOnInputRelease(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_claw_states_01_entry, owned, body)
