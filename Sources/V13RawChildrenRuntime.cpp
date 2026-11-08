// v1.3 raw enemy child serializers and numeric field traversal
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using namespace claw::recovered::v13;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4df6f0:
        return 4;
    case 0x4df240:
        return 4;
    case 0x4dd9e0:
        return 2;
    case 0x4ddc10:
        return 2;
    default:
        return -1;
    }
}

// 0x4dd9e0 and 0x4ddc10 traverse numeric values in their original order.
uint32_t transferChildNumericFields(Run &run, uint32_t stream, uint32_t block, bool reading) {
    RawChildNumericFields numericFields{run, block};
    // Twenty-nine binary64 operands and one signed DWORD, with three skipped
    // binary64 slots. The writer reads high before low, without conversion.
    for (uint32_t offset = 0x00; offset <= 0x100; offset += 0x08) {
        if (offset >= 0x58 && offset <= 0x68)
            continue;
        if (offset == 0xb8) {
            if (reading)
                run.call(0x4f8ed3, stream, {block + uint32_t(offsetof(RawChildNumericLayout, signedIntegerBits))});
            else {
                uint32_t integerBits = numericFields.signedIntegerBits();
                run.call(0x4f8d00, stream, {integerBits});
            }
            continue;
        }
        if (reading) {
            run.call(0x4f8f70, stream, {block + offset});
        } else {
            RawChildDoubleWords words{run, block + offset};
            uint32_t high = words.high();
            uint32_t low = words.low();
            run.call(0x4f8db1, stream, {low, high});
        }
    }
    return stream;
}

// 0x4dd9e0: insert raw numeric operands into the output stream.
uint32_t writeChildNumericFields(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return transferChildNumericFields(run, arguments[0], arguments[1], false);
}

// 0x4ddc10: extract into the same ordered destinations.
uint32_t readChildNumericFields(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return transferChildNumericFields(run, arguments[0], arguments[1], true);
}

// The temporary stream starts at entry ESP-0x15c, with its separate
// formatted-length local at -0x160 and output bytes at -0x100.
void transferChildFields(Run &run, uint32_t receiver, const uint32_t *arguments, bool derived) {
    uint32_t stream = arguments[0];
    uint32_t operation = arguments[1];
    uint32_t length = run.automatic(-0x160);
    uint32_t temporary = run.automatic(-0x15c);
    RawChildBaseFields childFields{run, receiver};
    uint32_t block = receiver + uint32_t(derived ? offsetof(RawChildDerivedLayout, numeric) : offsetof(RawChildBaseLayout, bitset));
    if (operation == uint32_t(SerializationOperation::WriteFields)) {
        run.call(0x4f9463, temporary, {run.automatic(-0x100), 0x100, 2, 1});
        if (derived)
            transferChildNumericFields(run, temporary, block, false);
        else
            run.call(0x4fa4f0, 0, {temporary, block});
        // Native stream virtual-base lookup; re-evaluate after the callback.
        uint32_t buffer = run.get(temporary + run.get(run.get(temporary) + 0x04) + 0x04);
        uint32_t end = run.get(buffer + 0x1c);
        uint32_t begin = run.get(buffer + 0x18);
        run.put(length, end < begin ? 0 : end - begin);
        run.vcall(stream, RawStreamWriteSlot, {length, 4});
        buffer = run.get(temporary + run.get(run.get(temporary) + 0x04) + 0x04);
        uint32_t bytes = run.call(0x4f90c7, buffer);
        run.vcall(stream, RawStreamWriteSlot, {bytes, run.get(length)});
        if (derived) {
            for (uint32_t offset = uint32_t(offsetof(RawChildDerivedLayout, unknown_0x140)); offset <= uint32_t(offsetof(RawChildDerivedLayout, unknown_0x14c)); offset += 0x04)
                run.vcall(stream, RawStreamWriteSlot, {receiver + offset, 4});
        } else {
            run.vcall(stream, RawStreamWriteSlot, {receiver + uint32_t(offsetof(RawChildBaseLayout, unknown_0x28)), 4});
            run.vcall(stream, RawStreamWriteSlot, {receiver + uint32_t(offsetof(RawChildBaseLayout, unknown_0x2c)), 4});
            run.vcall(stream, RawStreamWriteSlot, {RawChildUnknownGlobalAddress, 4});
            run.vcall(stream, RawStreamWriteSlot, {receiver + uint32_t(offsetof(RawChildBaseLayout, unknown_0x30)), 4});
        }
        run.call(0x4f9511, temporary + 0x08);
        run.call(0x4f959e, temporary + 0x08);
    } else if (operation == uint32_t(SerializationOperation::ReadFields)) {
        run.vcall(stream, RawStreamReadSlot, {length, 4});
        uint32_t bytes = run.call(0x4fcaea, 0, {run.get(length)});
        run.vcall(stream, RawStreamReadSlot, {bytes, run.get(length)});
        run.call(0x4f9398, temporary, {bytes, run.get(length), 1});
        if (derived)
            transferChildNumericFields(run, temporary, block, true);
        else
            run.call(0x4fa5a0, 0, {temporary, block});
        run.call(0x4fcb13, 0, {bytes});
        if (derived) {
            for (uint32_t offset = uint32_t(offsetof(RawChildDerivedLayout, unknown_0x140)); offset <= uint32_t(offsetof(RawChildDerivedLayout, unknown_0x14c)); offset += 0x04)
                run.vcall(stream, RawStreamReadSlot, {receiver + offset, 4});
        } else {
            run.vcall(stream, RawStreamReadSlot, {receiver + uint32_t(offsetof(RawChildBaseLayout, unknown_0x28)), 4});
            run.vcall(stream, RawStreamReadSlot, {receiver + uint32_t(offsetof(RawChildBaseLayout, unknown_0x2c)), 4});
            run.vcall(stream, RawStreamReadSlot, {RawChildUnknownGlobalAddress, 4});
            run.vcall(stream, RawStreamReadSlot, {receiver + uint32_t(offsetof(RawChildBaseLayout, unknown_0x30)), 4});
            childFields.owner(arguments[3]);
            childFields.ownerAlias(arguments[3]);
            RawChildOwnerFields ownerFields{run, arguments[3]};
            uint32_t ownerValue = ownerFields.unknown_0x7c();
            childFields.unknown_0x4(0);
            childFields.ownerWord(ownerValue);
            childFields.unknown_0x8(0);
            childFields.unknown_0x28(RawChildRestoredWord);
        }
        run.call(0x4f9425, temporary + 0x0c);
        run.call(0x4f959e, temporary + 0x0c);
    }
}

// 0x4df240. Base serializer restores its owner links after reading.
uint32_t serializeBaseChild(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!arguments[0])
        return 0;
    transferChildFields(run, receiver, arguments, false);
    return 1;
}

// 0x4df6f0. Derived serializer always delegates to the base serializer.
uint32_t serializeDerivedChild(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!arguments[0])
        return 0;
    transferChildFields(run, receiver, arguments, true);
    // The nested base call has its own original stack locals.
    uint32_t frame = run.frame;
    run.frame -= 0x180;
    uint32_t result = serializeBaseChild(run, receiver, arguments);
    run.frame = frame;
    return result != 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4df6f0:
        return serializeDerivedChild(run, receiver, arguments);
    case 0x4df240:
        return serializeBaseChild(run, receiver, arguments);
    case 0x4dd9e0:
        return writeChildNumericFields(run, receiver, arguments);
    case 0x4ddc10:
        return readChildNumericFields(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_v13_raw_children_entry, owned, body)
