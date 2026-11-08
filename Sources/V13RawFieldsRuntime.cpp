#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {
using claw::Run;
using namespace claw::recovered::v13;

int owned(uint32_t function) {
    switch (function) {
    case 0x4c7ab0:
    case 0x4c7f10:
    case 0x4d6680:
    case 0x4d6aa0:
        return 1;
    case 0x4d7010:
        return 2;
    default:
        return -1;
    }
}

void zeroBuffer(Run &run, uint32_t buffer) {
    for (uint32_t i = 0; i < RawStreamNameBytes; i += 0x04)
        run.put(buffer + i, 0);
}

void copyString(Run &run, uint32_t destination, uint32_t source) {
    uint32_t length = 0;
    while (run.get8(source + length++)) {}
    uint32_t i = 0;
    for (; i + 0x04 <= length; i += 0x04)
        run.put(destination + i, run.get(source + i));
    for (; i < length; ++i)
        run.put8(destination + i, run.get8(source + i));
}

// 0x4d7010. The map starts at +0x10; +0x1c is its count.
// The value's +0x10 identity is compared, rather than its pointer.
uint32_t copyRegistryNameAtFrame(Run &run, uint32_t object, uint32_t result, uint32_t value, uint32_t frame) {
    uint32_t name = frame - 0x1c;
    uint32_t item = frame - 0x18;
    uint32_t position = frame - 0x14;
    RawNameRegistryFields registry{run, object};
    run.put(position, registry.entryCount() ? 0xffffffffu : 0);
    run.put(position + 0x04, 0);
    run.put(item, 0);
    run.put(name, run.get(RawStreamEmptyStringAddress));
    run.put(frame - 0x04, 1);
    bool found = false;
    while (run.get(position)) {
        run.stackPointer = frame - 0x38;
        run.call(0x4fc525, object + uint32_t(offsetof(RawNameRegistryPrefixLayout, nameMapPrefix)), {position, name, item});
        uint32_t candidate = run.get(item);
        RawRegistryValueFields candidateFields{run, candidate};
        RawRegistryValueFields valueFields{run, value};
        if (candidate) {
            uint32_t candidateIdentity = candidateFields.lookupIdentity();
            uint32_t valueIdentity = valueFields.lookupIdentity();
            if (candidateIdentity == valueIdentity) {
                run.stackPointer = frame - 0x30;
                run.call(0x4fcb1e, result, {name});
                run.put(position + 0x04, 1);
                found = true;
                break;
            }
        }
    }
    if (!found) {
        uint32_t empty = frame + 0x08;
        run.put(empty, run.get(RawStreamEmptyStringAddress));
        run.put8(frame - 0x04, 2);
        run.stackPointer = frame - 0x30;
        run.call(0x4fcb1e, result, {empty});
        run.put(position + 0x04, 1);
        run.put8(frame - 0x04, 1);
        run.stackPointer = frame - 0x2c;
        run.call(0x4fcda9, empty);
    }
    run.put8(frame - 0x04, 0);
    run.stackPointer = frame - 0x2c;
    run.call(0x4fcda9, name);
    return result;
}

// Raw actor field order, excluding the leading name and trailing logic names.
void transferActorFieldRegions(Run &run, uint32_t object, uint32_t stream, uint32_t slot) {
    for (uint32_t offset = uint32_t(offsetof(RawActorStreamLayout, unknown_0xe4)); offset <= 0x130; offset += 0x04)
        run.vcall(stream, slot, {object + offset, 0x04});
    for (uint32_t offset = uint32_t(offsetof(RawActorStreamLayout, unknown_0x134)); offset <= 0x154; offset += 0x10)
        run.vcall(stream, slot, {object + offset, 0x10});
    for (uint32_t offset = uint32_t(offsetof(RawActorStreamLayout, unknown_0x164)); offset <= 0x180; offset += 0x04)
        run.vcall(stream, slot, {object + offset, 0x04});
    run.vcall(stream, slot, {object + uint32_t(offsetof(RawActorStreamLayout, unknown_0x10)), 0x04});
    run.vcall(stream, slot, {object + uint32_t(offsetof(RawActorStreamLayout, unknown_0x14)), 0x04});
    run.vcall(stream, slot, {object + uint32_t(offsetof(RawActorStreamLayout, unknown_0x18)), 0x24});
    for (uint32_t offset : {
             uint32_t(offsetof(RawActorStreamLayout, unknown_0x40)),
             uint32_t(offsetof(RawActorStreamLayout, unknown_0x44)),
             uint32_t(offsetof(RawActorStreamLayout, unknown_0x48)),
             uint32_t(offsetof(RawActorStreamLayout, unknown_0x50)),
             uint32_t(offsetof(RawActorStreamLayout, unknown_0x54)),
             uint32_t(offsetof(RawActorStreamLayout, unknown_0x58))})
        run.vcall(stream, slot, {object + offset, 0x04});
    run.vcall(stream, slot, {object + uint32_t(offsetof(RawActorStreamLayout, unknown_0x64)), 0x10});
    run.vcall(stream, slot, {object + uint32_t(offsetof(RawActorStreamLayout, unknown_0x4)), 0x04});
    run.vcall(stream, slot, {object + uint32_t(offsetof(RawActorStreamLayout, unknown_0x8)), 0x04});
    run.vcall(stream, slot, {object + uint32_t(offsetof(RawActorStreamLayout, serializedPeerIdentity)), 0x04});
}

// 0x4c7ab0. +0xb8 fixed header, +0xdc actor name; +0x80/+0x88/+0x90 logic references.
uint32_t writeRawActorFields(Run &run, uint32_t object, const uint32_t *arguments) {
    uint32_t stream = arguments[0];
    RawActorStreamFields actorFields{run, object};
    if (!stream)
        return 0;
    uint32_t frame = run.frame;
    uint32_t buffer = run.automatic(-0x80);
    uint32_t temporary = run.automatic(-0x84);
    run.stackPointer = frame - 0xa0;
    run.vcall(stream, RawStreamWriteSlot, {object + uint32_t(offsetof(RawActorStreamLayout, fixedHeader)), 0x24});
    zeroBuffer(run, buffer);
    copyString(run, buffer, actorFields.name());
    run.vcall(stream, RawStreamWriteSlot, {buffer, RawStreamNameBytes});
    transferActorFieldRegions(run, object, stream, RawStreamWriteSlot);
    // Keep each binding read after clearing its buffer and after previous stream calls.
    for (uint32_t binding = 0; binding < 3; ++binding) {
        zeroBuffer(run, buffer);
        uint32_t value;
        switch (binding) {
        case 0:
            value = actorFields.binding0();
            break;
        case 1:
            value = actorFields.binding1();
            break;
        default:
            value = actorFields.binding2();
            break;
        }
        if (value) {
            uint32_t scene = actorFields.scene();
            ContactSceneFields sceneFields{run, scene};
            uint32_t map = sceneFields.registry();
            copyRegistryNameAtFrame(run, map, temporary, value, frame - 0xa0);
            copyString(run, buffer, run.get(temporary));
            run.stackPointer = frame - 0x98;
            run.call(0x4fcda9, temporary);
        }
        run.stackPointer = frame - 0xa0;
        run.vcall(stream, RawStreamWriteSlot, {buffer, RawStreamNameBytes});
    }
    return 1;
}

// 0x4c7f10. Stream input uses the same original -0x80 buffer each time.
uint32_t readRawActorFields(Run &run, uint32_t object, const uint32_t *arguments) {
    uint32_t stream = arguments[0];
    RawActorStreamFields actorFields{run, object};
    if (!stream)
        return 0;
    uint32_t frame = run.frame;
    uint32_t buffer = run.automatic(-0x80);
    uint32_t temporary = run.automatic(-0x84);
    run.stackPointer = frame - 0x9c;
    run.vcall(stream, RawStreamReadSlot, {object + uint32_t(offsetof(RawActorStreamLayout, fixedHeader)), 0x24});
    run.vcall(stream, RawStreamReadSlot, {buffer, RawStreamNameBytes});
    run.stackPointer = frame - 0x98;
    run.call(0x4fcee6, object + uint32_t(offsetof(RawActorStreamLayout, name)), {buffer});
    run.stackPointer = frame - 0x9c;
    transferActorFieldRegions(run, object, stream, RawStreamReadSlot);
    for (uint32_t setter : {0x4c7690u, 0x4c7770u, 0x4c7850u}) {
        run.vcall(stream, RawStreamReadSlot, {buffer, RawStreamNameBytes});
        uint32_t length = 0;
        while (run.get8(buffer + length++)) {}
        if (length != 1) {
            run.put(temporary, 0);
            uint32_t scene = actorFields.scene();
            ContactSceneFields sceneFields{run, scene};
            uint32_t map = sceneFields.registry();
            run.call(0x4fc6b4, map + uint32_t(offsetof(RawNameRegistryPrefixLayout, nameMapPrefix)), {buffer, temporary});
            run.stackPointer = frame - 0x98;
            uint32_t success = run.call(setter, object, {run.get(temporary)});
            if (!success)
                return 0;
        }
        run.stackPointer = frame - 0x9c;
    }
    return 1;
}

// Logic field order: scalar prefix, six 16-byte blocks, scalar suffix and payload byte count.
void transferLogicFieldRegions(Run &run, uint32_t object, uint32_t stream, uint32_t slot) {
    for (uint32_t offset = uint32_t(offsetof(RawLogicStreamLayout, unknown_0x1c)); offset <= 0xcc; offset += 0x04)
        run.vcall(stream, slot, {object + offset, 0x04});
    for (uint32_t offset = uint32_t(offsetof(RawLogicStreamLayout, unknown_0xd0)); offset <= 0x120; offset += 0x10)
        run.vcall(stream, slot, {object + offset, 0x10});
    for (uint32_t offset = uint32_t(offsetof(RawLogicStreamLayout, unknown_0x130)); offset <= 0x164; offset += 0x04)
        run.vcall(stream, slot, {object + offset, 0x04});
    run.vcall(stream, slot, {object + uint32_t(offsetof(RawLogicStreamLayout, serializedPeerIdentity)), 0x04});
    run.vcall(stream, slot, {object + uint32_t(offsetof(RawLogicStreamLayout, payloadByteCount)), 0x04});
}

// 0x4d6680. +0x14 optional payload pointer.
uint32_t writeRawLogicFields(Run &run, uint32_t object, const uint32_t *arguments) {
    uint32_t stream = arguments[0];
    RawLogicStreamFields logic{run, object};
    if (!stream)
        return 0;
    run.stackPointer = run.frame - 0x18;
    transferLogicFieldRegions(run, object, stream, RawStreamWriteSlot);
    uint32_t payload = logic.payload();
    if (payload) {
        uint32_t count = logic.payloadByteCount();
        if (count)
            run.vcall(stream, RawStreamWriteSlot, {payload, count});
    }
    return 1;
}

// 0x4d6aa0. Allocation may change the count; reload before publishing the payload.
uint32_t readRawLogicFields(Run &run, uint32_t object, const uint32_t *arguments) {
    uint32_t stream = arguments[0];
    RawLogicStreamFields logic{run, object};
    if (!stream)
        return 0;
    run.stackPointer = run.frame - 0x18;
    transferLogicFieldRegions(run, object, stream, RawStreamReadSlot);
    uint32_t count = logic.payloadByteCount();
    if (count) {
        run.stackPointer = run.frame - 0x14;
        uint32_t payload = run.call(0x4fcaea, 0, {count});
        count = logic.payloadByteCount();
        logic.payload(payload);
        run.stackPointer = run.frame - 0x18;
        run.vcall(stream, RawStreamReadSlot, {payload, count});
    }
    return 1;
}

// 0x4d7010. The caller supplies the destination CString and lookup value.
uint32_t copyRegistryNameForIdentity(Run &run, uint32_t object, const uint32_t *arguments) {
    return copyRegistryNameAtFrame(run, object, arguments[0], arguments[1], run.frame);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4c7ab0:
        return writeRawActorFields(run, receiver, arguments);
    case 0x4c7f10:
        return readRawActorFields(run, receiver, arguments);
    case 0x4d6680:
        return writeRawLogicFields(run, receiver, arguments);
    case 0x4d6aa0:
        return readRawLogicFields(run, receiver, arguments);
    case 0x4d7010:
        return copyRegistryNameForIdentity(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_v13_raw_fields_entry, owned, body)
