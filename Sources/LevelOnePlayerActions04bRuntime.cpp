// v1.0 component-root and displacement-triplet helpers (0x420af0, 0x420b60, 0x420dd0).
// x87 primitives retain extended intermediates, status comparisons and the
// original binary64 spill points; host floating-point formulas would change them.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"
#include "ClawRecoveredNames.h"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x420af0:
        return 2;
    case 0x420b60:
        return 2;
    case 0x420dd0:
        return 6;
    default:
        return -1;
    }
}

uint32_t lowBinary64Word(uint64_t bits) {
    return static_cast<uint32_t>(bits);
}

uint32_t highBinary64Word(uint64_t bits) {
    return static_cast<uint32_t>(bits >> 32);
}

// Push a binary64 value read as low/high guest words in the original order.
void pushGuestBinary64(Run &run, ClawX87State &x87State, uint32_t address) {
    run.x87_step(CLAW_X87_F64, x87State, {run.get(address), run.get(address + 0x4)});
}

// Reload an original binary64 scratch spill without host floating-point conversion.
void pushBinary64Bits(Run &run, ClawX87State &x87State, uint64_t bits) {
    run.x87_step(CLAW_X87_F64, x87State, {lowBinary64Word(bits), highBinary64Word(bits)});
}

// An arithmetic or compare step whose binary64 operand is in guest memory.
void stepGuestBinary64(Run &run, ClawX87State &x87State, uint32_t operation, uint32_t address) {
    run.x87_step(operation, x87State, {run.get(address), run.get(address + 0x4)});
}

// An arithmetic or compare step whose binary64 operand is a scratch slot.
void stepBinary64Bits(Run &run, ClawX87State &x87State, uint32_t operation, uint64_t bits) {
    run.x87_step(operation, x87State, {lowBinary64Word(bits), highBinary64Word(bits)});
}

// Round/pop at the original binary64 store point, then publish low/high words.
void storePopGuestBinary64(Run &run, ClawX87State &x87State, uint32_t address) {
    const uint64_t bits = run.x87_step(CLAW_X87_STP_F64, x87State);
    run.put(address, lowBinary64Word(bits));
    run.put(address + 0x4, highBinary64Word(bits));
}

// Shared body of 0x420af0 and 0x420b60: a signed square root of
// value^2 - (argument - origin) * factor * constant, clamped at zero.
// factor at +factorOffset, value at +valueOffset, origin at +originOffset.
// Retain the status-bit tests: ordered host comparisons would alter NaN paths.
// No physical units or complete receiver layout are established by these helpers.
void returnSignedComponentRoot(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments,
                 uint32_t factorOffset, uint32_t valueOffset, uint32_t originOffset) {
    auto x87State = run.x87_entry(function);
    pushGuestBinary64(run, x87State, receiver + factorOffset);
    stepGuestBinary64(run, x87State, CLAW_X87_COMP_F64, 0x50ba88);
    if (x87State.status & 0x4000) {
        pushGuestBinary64(run, x87State, receiver + valueOffset);
        run.x87_return(function, x87State);
        return;
    }
    run.x87_step(CLAW_X87_F64, x87State, {arguments[0], arguments[1]});
    stepGuestBinary64(run, x87State, CLAW_X87_SUB_F64, receiver + originOffset);
    pushGuestBinary64(run, x87State, receiver + valueOffset);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepGuestBinary64(run, x87State, CLAW_X87_MUL_F64, receiver + factorOffset);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_MULP, 2), x87State);
    pushGuestBinary64(run, x87State, 0x50ba88);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepGuestBinary64(run, x87State, CLAW_X87_MUL_F64, 0x50bac8);
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 2), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_COMP_ST, 1), x87State);
    if ((x87State.status & 0x4100) == 0) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), x87State);
        pushGuestBinary64(run, x87State, 0x50ba88);
    }
    run.x87_step(CLAW_X87_SQRT, x87State);
    pushGuestBinary64(run, x87State, receiver + valueOffset);
    stepGuestBinary64(run, x87State, CLAW_X87_COMP_F64, 0x50ba88);
    if (x87State.status & 0x4100) {
        run.x87_step(CLAW_X87_CHS, x87State);
    }
    run.x87_return(function, x87State);
}

// 0x420af0. thiscall, 2 stack argument(s), returns ST(0).
uint32_t solveFirstComponentRoot(Run &run, uint32_t receiver, const uint32_t *arguments) {
    returnSignedComponentRoot(run, 0x420af0, receiver, arguments, 0x10, 0x28, 0x40);
    return 0;
}

// 0x420b60. thiscall, 2 stack argument(s), returns ST(0).
uint32_t solveSecondComponentRoot(Run &run, uint32_t receiver, const uint32_t *arguments) {
    returnSignedComponentRoot(run, 0x420b60, receiver, arguments, 0x18, 0x30, 0x48);
    return 0;
}

// 0x420dd0. thiscall, 6 stack argument(s), returns ST(0).
uint32_t solveDisplacementTriplet(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t function = 0x420dd0;
    auto x87State = run.x87_entry(function);
    // Raw binary64 scratch spills: deltas at original frame +0x2c/+0x34/+0x3c,
    // factors at +0/+8/+0x10, negative dot product at +0x20 and factor squared
    // length at +0x18. Spills round while the retained x87 operands stay extended.
    uint64_t deltaXBits = 0;
    uint64_t deltaYBits = 0;
    uint64_t deltaZBits = 0;
    uint64_t factorXBits = 0;
    uint64_t factorYBits = 0;
    uint64_t factorZBits = 0;
    uint64_t negativeDotBits = 0;
    uint64_t factorSquaredLengthBits = 0;
    run.x87_step(CLAW_X87_F64, x87State, {arguments[0x2], arguments[0x3]});
    run.x87_step(CLAW_X87_F64, x87State, {arguments[0x0], arguments[0x1]});
    stepGuestBinary64(run, x87State, CLAW_X87_SUB_F64, receiver + 0x40);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepGuestBinary64(run, x87State, CLAW_X87_SUB_F64, receiver + 0x48);
    pushGuestBinary64(run, x87State, receiver + 0x10);
    pushGuestBinary64(run, x87State, receiver + 0x18);
    run.x87_step(CLAW_X87_F64, x87State, {arguments[0x4], arguments[0x5]});
    stepGuestBinary64(run, x87State, CLAW_X87_SUB_F64, receiver + 0x50);
    pushGuestBinary64(run, x87State, receiver + 0x20);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5), x87State);
    deltaXBits = run.x87_step(CLAW_X87_ST_F64, x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), x87State);
    deltaYBits = run.x87_step(CLAW_X87_ST_F64, x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    deltaZBits = run.x87_step(CLAW_X87_ST_F64, x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), x87State);
    factorXBits = run.x87_step(CLAW_X87_ST_F64, x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
    factorYBits = run.x87_step(CLAW_X87_ST_F64, x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5), x87State);
    factorZBits = run.x87_step(CLAW_X87_ST_F64, x87State);
    pushBinary64Bits(run, x87State, factorXBits);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, deltaXBits);
    run.x87_step(CLAW_X87_CHS, x87State);
    pushBinary64Bits(run, x87State, factorYBits);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, deltaYBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), x87State);
    pushBinary64Bits(run, x87State, factorZBits);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, deltaZBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), x87State);
    negativeDotBits = run.x87_step(CLAW_X87_STP_F64, x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, factorXBits);
    pushBinary64Bits(run, x87State, negativeDotBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 6), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, factorYBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, factorZBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, deltaXBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    factorSquaredLengthBits = run.x87_step(CLAW_X87_STP_F64, x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, deltaYBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, deltaZBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
    stepGuestBinary64(run, x87State, CLAW_X87_MUL_F64, 0x50bac8);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, factorSquaredLengthBits);
    stepGuestBinary64(run, x87State, CLAW_X87_MUL_F64, 0x50bac0);
    run.x87_step(CLAW_X87_SQRT, x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), x87State);
    stepGuestBinary64(run, x87State, CLAW_X87_MUL_F64, 0x50bad0);
    run.x87_step(CLAW_X87_SQRT, x87State);
    stepGuestBinary64(run, x87State, CLAW_X87_COM_F64, 0x513e20);
    if (x87State.status & 0x100) {
        // C0 set (below or unordered): clear both words of each output component.
        // Keep the original low-words-first store order, including fault prefixes.
        run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), x87State);
        pushGuestBinary64(run, x87State, 0x50bb20);
        run.put(receiver + 0x28, 0);
        run.put(receiver + 0x30, 0);
        run.put(receiver + 0x38, 0);
        run.put(receiver + 0x2c, 0);
        run.put(receiver + 0x34, 0);
        run.put(receiver + 0x3c, 0);
        run.x87_return(function, x87State);
        return 0;
    }
    pushBinary64Bits(run, x87State, factorSquaredLengthBits);
    stepGuestBinary64(run, x87State, CLAW_X87_MUL_F64, 0x50bad8);
    pushGuestBinary64(run, x87State, 0x513e20);
    run.x87_step(CLAW_X87_CHS, x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), x87State);
    run.x87_step(CLAW_X87_COMPP, x87State);
    bool useGeneralSolution = (x87State.status & 0x100) != 0;
    if (!useGeneralSolution) {
        stepGuestBinary64(run, x87State, CLAW_X87_COM_F64, 0x513e20);
        useGeneralSolution = (x87State.status & 0x4100) == 0;
    }
    if (!useGeneralSolution) {
        // Near-zero factor norm uses absolute-sum normalization of the deltas.
        run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), x87State);
        pushBinary64Bits(run, x87State, deltaXBits);
        pushBinary64Bits(run, x87State, deltaYBits);
        pushBinary64Bits(run, x87State, deltaZBits);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
        run.x87_step(CLAW_X87_ABS, x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
        run.x87_step(CLAW_X87_ABS, x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
        run.x87_step(CLAW_X87_ABS, x87State);
        pushBinary64Bits(run, x87State, deltaXBits);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), x87State);
        pushBinary64Bits(run, x87State, deltaYBits);
        pushBinary64Bits(run, x87State, deltaZBits);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 4), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 4), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 4), x87State);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
        storePopGuestBinary64(run, x87State, receiver + 0x28);
        storePopGuestBinary64(run, x87State, receiver + 0x30);
        storePopGuestBinary64(run, x87State, receiver + 0x38);
        run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), x87State);
        run.x87_return(function, x87State);
        return 0;
    }
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_MUL_TO0, 2), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_ADD_TOI, 0), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_SUB_F64, negativeDotBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIVP, 1), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), x87State);
    run.x87_step(CLAW_X87_SQRT, x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 2), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, factorXBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, factorYBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_MUL_F64, factorZBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
    stepGuestBinary64(run, x87State, CLAW_X87_MUL_F64, 0x50bad0);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepGuestBinary64(run, x87State, CLAW_X87_MUL_F64, 0x50bad0);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_SUBR_F64, deltaXBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
    stepGuestBinary64(run, x87State, CLAW_X87_MUL_F64, 0x50bad0);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_SUBR_F64, deltaYBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    stepBinary64Bits(run, x87State, CLAW_X87_SUBR_F64, deltaZBits);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), x87State);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    storePopGuestBinary64(run, x87State, receiver + 0x28);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), x87State);
    storePopGuestBinary64(run, x87State, receiver + 0x30);
    storePopGuestBinary64(run, x87State, receiver + 0x38);
    run.x87_step(CLAW_X87_ST(CLAW_X87_STP_ST, 0), x87State);
    run.x87_return(function, x87State);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x420af0:
        return solveFirstComponentRoot(run, receiver, arguments);
    case 0x420b60:
        return solveSecondComponentRoot(run, receiver, arguments);
    case 0x420dd0:
        return solveDisplacementTriplet(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_player_actions_04b_entry, owned, body)
