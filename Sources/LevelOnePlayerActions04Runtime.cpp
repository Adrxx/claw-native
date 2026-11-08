// Observed Level 1 player actions batch 4
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4207b0:
        return 2;
    case 0x4207f0:
        return 2;
    case 0x4208b0:
        return 4;
    case 0x420a40:
        return 14;
    case 0x420ad0:
        return 2;
    case 0x420cd0:
        return 0;
    case 0x420fc0:
        return 1;
    case 0x4c9e30:
        return 1;
    case 0x4dc870:
        return 1;
    default:
        return -1;
    }
}

// 0x4207b0. cdecl: random integer in [low, high] using the C runtime rand.
uint32_t chooseRandomInteger(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t low = arguments[0];
    uint32_t high = arguments[1];
    // Keep 32-bit wrap before signed IDIV; a wrapped zero span selects an endpoint.
    uint32_t inclusiveSpan = high - low + 1;
    if (inclusiveSpan == 0) {
        uint32_t randomBits = run.call(0x4a3050, 0);
        if ((randomBits & 1) != 0) {
            return low;
        }
        return high;
    }
    uint32_t randomValue = run.call(0x4a3050, 0);
    int64_t remainder = int64_t(s32(randomValue)) % int64_t(s32(inclusiveSpan));
    return uint32_t(remainder) + low;
}

// 0x4207f0. thiscall: clamp a point to the plane and ask the tile's object (virtual +0x20).
uint32_t queryClampedTileObject(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // This service has its own layout: +0x5c plane, +0x4c tile-object table.
    // No established shared-prefix field is accessed here.
    uint32_t tileQuery = receiver;
    uint32_t x = arguments[0];
    uint32_t y = arguments[1];
    if (s32(x) < 0) {
        x = 0;
    } else {
        uint32_t plane = run.get(tileQuery + 0x5c);
        uint32_t axisLimit = run.get(plane + 0x30);
        if (!(s32(x) < s32(axisLimit))) {
            x = axisLimit - 1;
        }
    }
    if (s32(y) < 0) {
        y = 0;
    } else {
        uint32_t plane = run.get(tileQuery + 0x5c);
        uint32_t axisLimit = run.get(plane + 0x34);
        if (!(s32(y) < s32(axisLimit))) {
            y = axisLimit - 1;
        }
    }
    // Plane: +0x30/+0x34 extents, +0x8c/+0x90 cell shifts,
    // +0x24 row offsets and +0x20 encoded cells. Preserve every reload.
    uint32_t plane = run.get(tileQuery + 0x5c);
    uint32_t shiftX = run.get(plane + 0x8c);
    uint32_t cellX = uint32_t(s32(x) >> (shiftX & 31));
    uint32_t shiftY = run.get(plane + 0x90);
    uint32_t cellY = uint32_t(s32(y) >> (shiftY & 31));
    uint32_t baseX = cellX << (shiftX & 31);
    uint32_t reloadedShiftY = run.get(plane + 0x90);
    uint32_t localX = x - baseX;
    uint32_t baseY = cellY << (reloadedShiftY & 31);
    uint32_t rowOffsets = run.get(plane + 0x24);
    uint32_t cellIndex = run.get(rowOffsets + cellY * 4) + cellX;
    uint32_t cells = run.get(plane + 0x20);
    uint32_t localY = y - baseY;
    uint32_t cell = run.get(cells + cellIndex * 4);
    if (cell == 0xeeeeeeee) {
        return 0;
    }
    if (cell == 0xffffffff) {
        return 0;
    }
    uint32_t tileObjects = run.get(tileQuery + 0x4c);
    uint32_t tileObject = run.get(tileObjects + (cell & 0xffff) * 4);
    return run.vcall(tileObject, 0x20, {localX, localY});
}

// 0x4208b0. thiscall: store four words.
uint32_t storeUnknownWords128To134(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Four opaque words; their gameplay meaning is not established by this setter.
    run.put(receiver + 0x128, arguments[0]);
    run.put(receiver + 0x12c, arguments[1]);
    run.put(receiver + 0x130, arguments[2]);
    run.put(receiver + 0x134, arguments[3]);
    return 0;
}

// 0x420a40. thiscall: initialise a record from fourteen arguments, returns 1.
uint32_t initializeOpaqueServiceRecord(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // This initializer establishes offsets without establishing field meaning.
    // Keep the interleaved
    // argument and zero stores in original order for partial-write faults.
    uint32_t record = receiver;
    run.put(record + 0x28, arguments[0]);
    run.put(record + 0x2c, arguments[1]);
    run.put(record + 0x30, arguments[2]);
    run.put(record + 0x34, arguments[3]);
    run.put(record + 0x38, arguments[4]);
    run.put(record + 0x3c, arguments[5]);
    run.put(record + 0x10, arguments[6]);
    run.put(record + 0x14, arguments[7]);
    run.put(record + 0x18, arguments[8]);
    run.put(record + 0x40, 0);
    run.put(record + 0x48, 0);
    run.put(record + 0x50, 0);
    run.put(record + 0x0, 0);
    run.put(record + 0x44, 0);
    run.put(record + 0x4c, 0);
    run.put(record + 0x54, 0);
    run.put(record + 0x1c, arguments[9]);
    run.put(record + 0x4, 0);
    run.put(record + 0x20, arguments[10]);
    run.put(record + 0x24, arguments[11]);
    run.put(record + 0x8, arguments[12]);
    run.put(record + 0xc, arguments[13]);
    return 1;
}

// 0x420ad0. thiscall: store one binary64 (loaded through the x87 stack) three times.
uint32_t storeQuietedBinary64Triplet(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t low = arguments[0];
    uint32_t high = arguments[1];
    // FLD m64 quiets a signaling NaN. Preserve the low/high word stores
    // to +0xd8, +0xe0 and +0xe8 rather than changing their access widths.
    if ((high & 0x7ff00000) == 0x7ff00000) {
        if (((high & 0x000fffff) | low) != 0) {
            high = high | 0x00080000;
        }
    }
    run.put(receiver + 0xd8, low);
    run.put(receiver + 0xdc, high);
    run.put(receiver + 0xe0, low);
    run.put(receiver + 0xe4, high);
    run.put(receiver + 0xe8, low);
    run.put(receiver + 0xec, high);
    return 0;
}

// Fresh empty x87 state at the startup control word.
void resetX87State(ClawX87State &state) {
    state = ClawX87State{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
}

// Original __ftol (0x4a30e0) on the live stack: pops one value, returns the truncated integer.
uint32_t truncateX87ToInteger(Run &run, ClawX87State &state) {
    state.popCount = 1;
    state.pushCount = 0;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, state);
}

// 0x420cd0. fastcall(ecx = object): advance the fractional accumulator, return the whole steps.
uint32_t advanceFractionalSteps(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // Separate stepper layout: +0xa0 disables stepping, +0x88 is the binary64
    // step and +0xa8 its fractional accumulator. Keep the exact x87 boundaries
    // and repeated reads; replacing them with a host integer cast changes rounding.
    uint32_t stepper = receiver;
    if (run.get(stepper + 0xa0) != 0) {
        return 0;
    }
    ClawX87State stepState;
    resetX87State(stepState);
    run.x87_step(CLAW_X87_F64, stepState, {run.get(stepper + 0x88), run.get(stepper + 0x8c)});
    uint32_t wholeStep = truncateX87ToInteger(run, stepState);
    double stepValue = run.getd(stepper + 0x88);
    double fractionalStep = stepValue - double(s32(wholeStep));
    double accumulatedFraction = fractionalStep + run.getd(stepper + 0xa8);
    run.putd(stepper + 0xa8, accumulatedFraction);
    ClawX87State totalState;
    resetX87State(totalState);
    run.x87_step(CLAW_X87_F64, totalState, {run.get(stepper + 0xa8), run.get(stepper + 0xac)});
    run.x87_step(CLAW_X87_F64, totalState, {run.get(stepper + 0x88), run.get(stepper + 0x8c)});
    run.x87_step(CLAW_X87_ADD_ST1, totalState);
    uint32_t totalSteps = truncateX87ToInteger(run, totalState);
    run.put(0x544e8c, totalSteps);
    ClawX87State remainderState;
    resetX87State(remainderState);
    run.x87_step(CLAW_X87_F64, remainderState, {run.get(stepper + 0xa8), run.get(stepper + 0xac)});
    uint32_t wholeAccumulator = truncateX87ToInteger(run, remainderState);
    double accumulator = run.getd(stepper + 0xa8);
    double fractionLeft = accumulator - double(s32(wholeAccumulator));
    run.putd(stepper + 0xa8, fractionLeft);
    return run.get(0x544e8c);
}

// 0x420fc0. thiscall: set one bit of a bit set, growing it when out of range.
uint32_t setBitWithGrowth(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Bit-set layout: +0x8 bit count; +0xc inline word for at most 32 bits,
    // otherwise a storage token. The grow path delegates without a second store.
    uint32_t bitIndex = arguments[0];
    uint32_t bitCount = run.get(receiver + 0x8);
    if (bitIndex >= bitCount) {
        run.call(0x4dbd20, receiver, {bitIndex});
        return 0;
    }
    uint32_t storage = 0;
    if (bitCount > 0x20) {
        storage = run.get(receiver + 0xc);
    } else {
        storage = receiver + 0xc;
    }
    uint32_t wordToken = storage + (bitIndex >> 5) * 4;
    uint32_t wordValue = run.get(wordToken);
    wordValue = wordValue | (uint32_t(1) << (bitIndex & 0x1f));
    run.put(wordToken, wordValue);
    return 0;
}

// 0x4c9e30. stdcall, ret 4: does nothing (EAX untouched).
uint32_t ignoreSingleArgumentCallback(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0;
}

// Slot address in the table at 0x537698 for an index, growing the table when out of range.
uint32_t lookupGrowingTableSlot(Run &run, uint32_t index) {
    // Global table: signed index bounds +0x8/+0xc, data +0x10, fallback +0x14,
    // element width +0x18, pending storage +0x1c and pending count +0x20.
    uint32_t firstIndex = run.get(0x5376a0);
    run.put(0x5376b8, 0);
    uint32_t slot = 0;
    if (s32(index) < s32(firstIndex) || s32(index) > s32(run.get(0x5376a4))) {
        uint32_t grownTable = run.call(0x4db6e0, 0x537698, {index, 0});
        if (grownTable == 0) {
            uint32_t fallbackContext = run.get(0x544b4c);
            uint32_t fallbackResult = run.call(0x4db5f0, 0);
            run.put(0x544b14, fallbackResult);
            run.call(0x4db4d0, run.get(0x53769c), {0x537698, fallbackContext, 0xc});
            slot = run.get(0x5376ac);
        } else {
            uint32_t reloadedFirstIndex = run.get(0x5376a0);
            slot = (index - reloadedFirstIndex) * run.get(0x5376b0) + run.get(0x5376a8);
        }
    } else {
        slot = (index - firstIndex) * run.get(0x5376b0) + run.get(0x5376a8);
    }
    return slot;
}

// Run the 0x4f6439 initialiser over each pending element of the table.
void initializePendingTableElements(Run &run) {
    uint32_t pendingCount = run.get(0x5376b8);
    uint32_t elementToken = run.get(0x5376b4);
    while (pendingCount != 0) {
        if (elementToken != 0) {
            run.call(0x4f6439, elementToken);
        }
        elementToken = elementToken + 4;
        pendingCount = pendingCount - 1;
    }
}

// 0x4dc870. cdecl: look up a table entry for an object, hand it to the object's virtual methods.
uint32_t dispatchObjectTableEntry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Object-specific +0x10 points to an index record (+0x1c). Reload the
    // table slot and vtable after callbacks because those calls may change them.
    uint32_t objectToken = arguments[0];
    uint32_t tableIndex = run.get(run.get(objectToken + 0x10) + 0x1c);
    uint32_t slotToken = lookupGrowingTableSlot(run, tableIndex);
    initializePendingTableElements(run);
    uint32_t vtable = run.get(objectToken);
    uint32_t valueBeforeIndexCallback = run.call(0x4f6974, slotToken, {0});
    run.call(run.get(vtable + 4), objectToken, {valueBeforeIndexCallback});
    run.vcall(objectToken, 8, {tableIndex});
    slotToken = lookupGrowingTableSlot(run, tableIndex);
    initializePendingTableElements(run);
    vtable = run.get(objectToken);
    uint32_t valueAfterIndexCallback = run.call(0x4f6974, slotToken, {0});
    run.call(run.get(vtable + 0xc), objectToken, {valueAfterIndexCallback});
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4207b0:
        return chooseRandomInteger(run, receiver, arguments);
    case 0x4207f0:
        return queryClampedTileObject(run, receiver, arguments);
    case 0x4208b0:
        return storeUnknownWords128To134(run, receiver, arguments);
    case 0x420a40:
        return initializeOpaqueServiceRecord(run, receiver, arguments);
    case 0x420ad0:
        return storeQuietedBinary64Triplet(run, receiver, arguments);
    case 0x420cd0:
        return advanceFractionalSteps(run, receiver, arguments);
    case 0x420fc0:
        return setBitWithGrowth(run, receiver, arguments);
    case 0x4c9e30:
        return ignoreSingleArgumentCallback(run, receiver, arguments);
    case 0x4dc870:
        return dispatchObjectTableEntry(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_player_actions_04_entry, owned, body)
