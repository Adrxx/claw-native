// Persistent checkpoint byte checksum and seeded XOR transform, original v1.0.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::recovered::v10::CheckpointByteGeneratorFields;

// Original v1.0 operands at 0x49bf93, 0x49bfd4, 0x49bf84 and 0x49c047.
constexpr uint32_t ChecksumTableAddress = 0x52d800;
constexpr uint32_t FeedbackPolynomialTableAddress = 0x52d780;
constexpr uint32_t InitialChecksum = 0xffffffffu;
constexpr uint32_t XorGeneratorUpperBound = 0x1000000;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x49bf70:
        return 2;
    case 0x49bfb0:
        return 1;
    case 0x49c000:
        return 0;
    case 0x49c030:
        return 2;
    case 0x49c070:
        return 2;
    default:
        return -1;
    }
}

// 0x49bf70. Table-driven checksum over a byte buffer. Returns 0 for a null
// buffer, otherwise the running value starting at 0xffffffff, xored with the
// table entry (0x52d800) selected by each byte. This is an XOR of table entries,
// not a CRC recurrence using the previous checksum as a table index.
uint32_t checksumCheckpointBytes(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t buffer = arguments[0];
    uint32_t count = arguments[1];
    if (buffer == 0)
        return 0;
    uint32_t value = InitialChecksum;
    uint32_t index = 0;
    if (count == 0)
        return value;
    do {
        uint32_t entry = run.get(ChecksumTableAddress + uint32_t(run.get8(index + buffer)) * 4);
        value = value ^ entry;
        index = index + 1;
    } while (index < count);
    return value;
}

// 0x49bfb0. Selects the feedback polynomial and initializes the shift-register
// state from rand(). The return is the unsigned division quotient, not the state.
uint32_t initializeCheckpointGenerator(Run &run, uint32_t receiver, const uint32_t *arguments) {
    CheckpointByteGeneratorFields generator{run, receiver};
    uint32_t limit = arguments[0];
    uint32_t bits = 0;
    generator.upperBound(limit);
    generator.feedbackBit(2);
    limit = limit >> 1;
    while (limit != 0) {
        uint32_t mask = generator.feedbackBit();
        mask = mask << 1;
        bits = bits + 1;
        generator.feedbackBit(mask);
        limit = limit >> 1;
    }
    [[maybe_unused]] uint32_t polynomial = run.get(FeedbackPolynomialTableAddress + bits * 4);
    generator.polynomial(polynomial);
    uint32_t random = run.call(0x4a3050, 0, {});
    uint32_t divisor = generator.feedbackBit() - 1;
    generator.state(random % divisor + 1);
    return random / divisor;
}

// 0x49c000. Steps until the state is within the unsigned upper bound. The
// feedback bit and bound are entry snapshots; the state is reloaded each step.
uint32_t nextCheckpointKey(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    CheckpointByteGeneratorFields generator{run, receiver};
    uint32_t mask = generator.feedbackBit();
    uint32_t limit = generator.upperBound();
    uint32_t state;
    do {
        state = generator.state();
        state = state << 1;
        generator.state(state);
        if ((state & mask) != 0) {
            uint32_t tap = generator.polynomial();
            generator.state((tap ^ state) | 1);
        }
        state = generator.state();
    } while (state > limit);
    return state - 1;
}

// 0x49c030. Seeds rand() from +0x44, sets up the generator with 0x1000000,
// then xors each byte with the low byte of the next key. A zero byte count still
// seeds and initializes the generator before returning.
uint32_t xorCheckpointBytes(Run &run, uint32_t receiver, const uint32_t *arguments) {
    CheckpointByteGeneratorFields generator{run, receiver};
    uint32_t data = arguments[0];
    uint32_t count = arguments[1];
    [[maybe_unused]] uint32_t seed = generator.seed();
    run.call(0x4a3040, 0, {seed});
    const uint32_t setup[] = {XorGeneratorUpperBound};
    initializeCheckpointGenerator(run, receiver, setup);
    if (count == 0)
        return 0;
    do {
        uint32_t key = nextCheckpointKey(run, receiver, nullptr);
        uint8_t byte = run.get8(data);
        run.put8(data, uint8_t(byte ^ uint8_t(key)));
        data = data + 1;
        count = count - 1;
    } while (count != 0);
    return 0;
}

// 0x49c070. Forwards both arguments to 0x49c030.
uint32_t forwardCheckpointByteTransform(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return xorCheckpointBytes(run, receiver, arguments);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49bf70:
        return checksumCheckpointBytes(run, receiver, arguments);
    case 0x49bfb0:
        return initializeCheckpointGenerator(run, receiver, arguments);
    case 0x49c000:
        return nextCheckpointKey(run, receiver, arguments);
    case 0x49c030:
        return xorCheckpointBytes(run, receiver, arguments);
    case 0x49c070:
        return forwardCheckpointByteTransform(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_super_checkpoint_01_entry, owned, body)
