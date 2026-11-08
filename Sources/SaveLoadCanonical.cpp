// Original game save-reader, startup and player-record ownership
//
// Canonical translation from the hash-checked packet instructions.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;
using namespace claw::recovered::v10;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x423f00:
        return 0;
    case 0x49a5a0:
        return 4;
    case 0x49a6d0:
        return 1;
    case 0x49a8f0:
        return 0;
    case 0x49a990:
        return 1;
    case 0x49ad50:
        return 0;
    case 0x49adc0:
        return 0;
    case 0x49b840:
        return 1;
    case 0x49b950:
        return 0;
    case 0x49b970:
        return 0;
    case 0x49b9a0:
        return 0;
    case 0x49bdb0:
        return 4;
    case 0x49be50:
        return 1;
    case 0x49bee0:
        return 1;
    case 0x49bf30:
        return 1;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// Each prologue size and outgoing call frame follows the packet's instructions.
struct Frame {
    Run &run;
    uint32_t base;
    Frame(Run &run, uint32_t prologue) : run(run), base(run.frame - prologue) {}
    uint32_t call(uint32_t target, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
        uint32_t saved = run.stackPointer;
        run.stackPointer = base - 4u * (uint32_t(arguments.size()) + 1u);
        uint32_t result = run.call(target, receiver, arguments);
        run.stackPointer = saved;
        return result;
    }
    uint32_t invoke(uint32_t target, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
        uint32_t saved = run.frame;
        run.frame = base - 4u * (uint32_t(arguments.size()) + 1u);
        uint32_t result = body(run, target, receiver, arguments.begin());
        run.frame = saved;
        return result;
    }
};

uint32_t length(Run &run, uint32_t address) {
    uint32_t remaining = 0xffffffffu;
    while (remaining) {
        --remaining;
        if (!run.get8(address++))
            break;
    }
    return ~remaining - 1u;
}

// REP MOVSD followed by REP MOVSB, retaining forward overlap behavior.
void copy(Run &run, uint32_t destination, uint32_t source, uint32_t count) {
    uint32_t words = count >> 2;
    for (uint32_t i = 0; i < words; ++i)
        run.put(destination + i * 4u, run.get(source + i * 4u));
    for (uint32_t i = words * 4u; i < count; ++i)
        run.put8(destination + i, run.get8(source + i));
}

// 0x423f00. Shared base vtable.
uint32_t resetProfileBaseVtable(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    ProfileRecordFields profile{run, receiver};
    profile.vtable(0x50becc);
    return 0;
}

// 0x49a5a0. Payload +0x04, name +0x14, optional strings +0x36/+0x88.
// Optional checks deliberately rescan the name, exactly as the original;
// their copies remain unbounded. Do not infer capacities from those checks.
uint32_t initializeNamedProfile(Run &run, uint32_t receiver, const uint32_t *arguments) {
    Frame frame(run, 0x10);
    if (!arguments[0])
        return 0;
    uint32_t size = length(run, arguments[0]);
    if (s32(size) < 0 || s32(size) >= 0x20)
        return 0;
    if (arguments[1]) {
        size = length(run, arguments[0]);
        if (s32(size) < 0 || s32(size) >= 0x50)
            return 0;
    }
    if (arguments[2]) {
        size = length(run, arguments[0]);
        if (s32(size) < 0 || s32(size) >= 0x50)
            return 0;
    }
    for (uint32_t offset = 0x04; offset < 0x2648; offset += 4)
        run.put(receiver + offset, 0);
    frame.invoke(0x49ad50, receiver);
    frame.invoke(0x49adc0, receiver);
    copy(run, receiver + 0x14, arguments[0], length(run, arguments[0]) + 1u);
    if (arguments[1])
        copy(run, receiver + 0x36, arguments[1], length(run, arguments[1]) + 1u);
    if (arguments[2])
        copy(run, receiver + 0x88, arguments[2], length(run, arguments[2]) + 1u);
    ProfileRecordFields profile{run, receiver};
    if (arguments[3] & 4u) {
        uint32_t flags = profile.flags();
        profile.flags(flags | 4u);
    }
    profile.version(1);
    return 1;
}

// 0x49a6d0. Serialized payload starts four bytes after the receiver.
uint32_t initializeSerializedProfile(Run &run, uint32_t receiver, const uint32_t *arguments) {
    Frame frame(run, 0x08);
    if (!arguments[0])
        return 0;
    uint32_t size = length(run, arguments[0] + 0x10);
    if (s32(size) <= 0 || s32(size) >= 0x20)
        return 0;
    copy(run, receiver + 0x04, arguments[0], 0x2644);
    frame.invoke(0x49a8f0, receiver);
    return 1;
}

// 0x49a8f0. Version +0x08 and three checksum records per level.
uint32_t validateProfileChecksums(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    Frame frame(run, 0x10);
    ProfileRecordFields profile{run, receiver};
    if (profile.version() != 1)
        return 0;
    for (uint32_t i = 0; i < 0x0f; ++i) {
        if (!frame.invoke(0x49a990, 0, {receiver + 0x21c4 + i * 0x44}) ||
            !frame.invoke(0x49a990, 0, {receiver + 0x1780 + i * 0xb0}) ||
            !frame.invoke(0x49a990, 0, {receiver + 0x17c4 + i * 0xb0})) {
            frame.call(0x49a720, receiver);
            return 0;
        }
    }
    return 1;
}

// 0x49a990. Checksum +0x04; ten terms beginning at +0x1c.
// Unsigned products and accumulation preserve original low-32-bit wrap.
uint32_t matchesProfileChecksum(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    if (!arguments[0])
        return 0;
    uint32_t sum = 0;
    for (uint32_t i = 0; i < 10; ++i)
        sum += run.get(arguments[0] + 0x1c + i * 4u) * run.get(0x52d698 + i * 4u);
    ProfileChecksumFields checksumRecord{run, arguments[0]};
    return sum == checksumRecord.checksum();
}

// 0x49ad50. Clear 17 controller words at +0x2604, then set observed slots.
// Slot actions are unproven here; retain the literal slot/value sequence.
uint32_t resetControllerMapping(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    for (uint32_t offset = 0x2604; offset < 0x2648; offset += 4)
        run.put(receiver + offset, 0);
    run.put(receiver + 0x2618, 1);
    run.put(receiver + 0x261c, 2);
    run.put(receiver + 0x2620, 4);
    run.put(receiver + 0x2624, 8);
    run.put(receiver + 0x2628, 0);
    run.put(receiver + 0x262c, 0x10);
    run.put(receiver + 0x2630, 0x20);
    run.put(receiver + 0x2634, 0x40);
    run.put(receiver + 0x2638, 0x80);
    run.put(receiver + 0x263c, 0);
    return 0;
}

// 0x49adc0. Clear 17 keyboard words at +0x25c0, then set observed slots.
// Key codes retain original words; no action-to-slot inference is made.
uint32_t resetKeyboardMapping(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    for (uint32_t offset = 0x25c0; offset < 0x2604; offset += 4)
        run.put(receiver + offset, 0);
    run.put(receiver + 0x25c4, 0x25);
    run.put(receiver + 0x25c8, 0x27);
    run.put(receiver + 0x25cc, 0x26);
    run.put(receiver + 0x25d0, 0x28);
    run.put(receiver + 0x25d4, 0x20);
    run.put(receiver + 0x25d8, 0x11);
    run.put(receiver + 0x25dc, 0x12);
    run.put(receiver + 0x25e0, 0x10);
    run.put(receiver + 0x25e4, 0);
    run.put(receiver + 0x25e8, 0x5a);
    run.put(receiver + 0x25ec, 0x31);
    run.put(receiver + 0x25f0, 0x32);
    run.put(receiver + 0x25f4, 0x33);
    run.put(receiver + 0x25f8, 0x34);
    return 0;
}

// 0x49b840. CString +0x1c; startup directory at entry ESP-0x104.
uint32_t initializeSaveManager(Run &run, uint32_t receiver, const uint32_t *arguments) {
    Frame frame(run, 0x110);
    uint32_t directory = run.automatic(-0x104);
    frame.call(0x4f650f, receiver + 0x1c);
    run.put8(directory, 0);
    if (frame.call(run.get(0x546a28), 0, {0xfe, directory}))
        frame.call(0x4f4f58, 0, {receiver + 0x1c, 0x525f78, directory, arguments[0]});
    run.put8(directory + 0x03, 0);
    if (frame.call(run.get(0x546a2c), 0, {directory}) == 5)
        frame.call(0x4f650f, receiver + 0x1c);
    SaveManagerFields manager{run, receiver};
    uint32_t pathData = manager.pathData();
    if (!run.get(pathData - 0x08)) {
        if (frame.call(run.get(0x546a10), 0, {directory, 0xfe}))
            frame.call(0x4f4f58, 0, {receiver + 0x1c, 0x525f78, directory, arguments[0]});
    }
    pathData = manager.pathData();
    if (!run.get(pathData - 0x08))
        return 0;
    for (uint32_t offset = 0x20; offset < 0x40; offset += 4)
        run.put(receiver + offset, 0);
    if (s32(frame.invoke(0x49b9a0, receiver)) > 0) {
        if (frame.invoke(0x49bee0, receiver, {0x5255e8}))
            return 1;
    }
    return frame.invoke(0x49bdb0, receiver, {0x5255e8, 0x534938, 0x534938, 0}) ? 1u : 0u;
}

// 0x49b950. Clear records and path.
uint32_t clearSaveManager(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    Frame frame(run, 0x04);
    frame.invoke(0x49b970, receiver);
    frame.call(0x4f650f, receiver + 0x1c);
    return 0;
}

// 0x49b970. List head +0x04; node next +0x00 and record +0x08.
uint32_t deleteProfileRecords(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    Frame frame(run, 0x08);
    SaveManagerFields manager{run, receiver};
    uint32_t node = manager.head();
    while (node) {
        ProfileListNodeFields listNode{run, node};
        uint32_t next = listNode.next();
        uint32_t record = listNode.record();
        if (record)
            frame.call(run.get(run.get(record) + 0x04), record, {1});
        node = next;
    }
    frame.call(0x4f5172, receiver);
    return 0;
}

// 0x49b9a0. Header +0x20, checksum +0x24, selection +0x28, count +0x2c.
uint32_t loadProfileRecords(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    Frame frame(run, 0x30);
    uint32_t file = run.automatic(-0x1c);
    frame.call(0x4f72c9, file);
    SaveManagerFields manager{run, receiver};
    uint32_t pathData = manager.pathData();
    if (!frame.call(0x4f7448, file, {pathData, 0, 0})) {
        frame.call(0x4f7369, file);
        return 0;
    }
    uint32_t size = frame.call(0x4f774d, file);
    if (size <= 0x20) {
        frame.call(0x4f7369, file);
        return 0;
    }
    if (!frame.call(0x4f7570, file, {receiver + 0x20, 0x20})) {
        frame.call(0x4f7369, file);
        return 0;
    }
    frame.call(0x49c070, receiver, {receiver + 0x20, 0x20});
    size -= 0x20;
    uint32_t buffer = frame.call(0x4f63ec, 0, {size});
    if (!buffer) {
        frame.call(0x4f7369, file);
        return 0;
    }
    uint32_t count = 0;
    bool success = false;
    if (frame.call(0x4f7570, file, {buffer, size})) {
        frame.call(0x49c070, receiver, {buffer, size});
        uint32_t checksum = frame.call(0x49bf70, 0, {buffer, size});
        if (manager.payloadChecksum() == checksum && (size / 0x2644) * 0x2644 == size) {
            count = size / 0x2644;
            uint32_t declared = manager.recordCount();
            if (count != declared && count >= declared)
                count = declared;
            success = true;
            for (uint32_t i = 0; s32(i) < s32(count); ++i) {
                if (!frame.invoke(0x49be50, receiver, {buffer + i * 0x2644})) {
                    success = false;
                    break;
                }
            }
        }
    }
    frame.call(0x4f6428, 0, {buffer});
    if (success) {
        uint32_t selection = manager.selection();
        uint32_t unknown_0x40 = manager.unknown_0x40();
        if (selection != unknown_0x40) {
            unknown_0x40 = manager.unknown_0x40();
            manager.selection(unknown_0x40);
        }
    }
    frame.call(0x4f7369, file);
    return success ? count : 0u;
}

uint32_t allocateRecord(Run &run, Frame &frame) {
    uint32_t record = frame.call(0x4f63ec, 0, {0x2648});
    if (record) {
        ProfileRecordFields profile{run, record};
        profile.vtable(0x50feac);
        for (uint32_t offset = 0x04; offset < 0x2648; offset += 4)
            run.put(record + offset, 0);
    }
    return record;
}

// 0x49bdb0. Construct a named record and append through the original list.
uint32_t appendNamedProfile(Run &run, uint32_t receiver, const uint32_t *arguments) {
    Frame frame(run, 0x10);
    if (!arguments[0] || frame.invoke(0x49bee0, receiver, {arguments[0]}))
        return 0;
    uint32_t record = allocateRecord(run, frame);
    if (frame.invoke(0x49a5a0, record, {arguments[0], arguments[1], arguments[2], arguments[3]})) {
        frame.call(0x4f51c5, receiver, {record});
        return record;
    }
    if (record)
        frame.call(run.get(run.get(record) + 0x04), record, {1});
    return 0;
}

// 0x49be50. Construct from a serialized payload and append.
uint32_t appendSerializedProfile(Run &run, uint32_t receiver, const uint32_t *arguments) {
    Frame frame(run, 0x10);
    if (!arguments[0] || frame.invoke(0x49bee0, receiver, {arguments[0] + 0x10}))
        return 0;
    uint32_t record = allocateRecord(run, frame);
    if (frame.invoke(0x49a6d0, record, {arguments[0]})) {
        frame.call(0x4f51c5, receiver, {record});
        return record;
    }
    if (record)
        frame.call(run.get(run.get(record) + 0x04), record, {1});
    return 0;
}

// 0x49bee0. Case-insensitive lookup; cache the next link before comparison.
uint32_t findProfileByName(Run &run, uint32_t receiver, const uint32_t *arguments) {
    Frame frame(run, 0x0c);
    if (!arguments[0])
        return 0;
    SaveManagerFields manager{run, receiver};
    uint32_t node = manager.head();
    while (node) {
        ProfileListNodeFields listNode{run, node};
        uint32_t next = listNode.next();
        uint32_t record = listNode.record();
        uint32_t name = record + 0x14;
        if (name && !frame.call(0x4a3cf0, 0, {name, arguments[0]}))
            return record;
        node = next;
    }
    return 0;
}

// 0x49bf30. Remove the matching node before deleting its record.
uint32_t removeProfileRecord(Run &run, uint32_t receiver, const uint32_t *arguments) {
    Frame frame(run, 0x08);
    if (!arguments[0])
        return 0;
    SaveManagerFields manager{run, receiver};
    uint32_t node = manager.head();
    while (node) {
        ProfileListNodeFields listNode{run, node};
        uint32_t next = listNode.next();
        if (listNode.record() == arguments[0]) {
            frame.call(0x4f5212, receiver, {node});
            frame.call(run.get(run.get(arguments[0]) + 0x04), arguments[0], {1});
            break;
        }
        node = next;
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x423f00:
        return resetProfileBaseVtable(run, receiver, arguments);
    case 0x49a5a0:
        return initializeNamedProfile(run, receiver, arguments);
    case 0x49a6d0:
        return initializeSerializedProfile(run, receiver, arguments);
    case 0x49a8f0:
        return validateProfileChecksums(run, receiver, arguments);
    case 0x49a990:
        return matchesProfileChecksum(run, receiver, arguments);
    case 0x49ad50:
        return resetControllerMapping(run, receiver, arguments);
    case 0x49adc0:
        return resetKeyboardMapping(run, receiver, arguments);
    case 0x49b840:
        return initializeSaveManager(run, receiver, arguments);
    case 0x49b950:
        return clearSaveManager(run, receiver, arguments);
    case 0x49b970:
        return deleteProfileRecords(run, receiver, arguments);
    case 0x49b9a0:
        return loadProfileRecords(run, receiver, arguments);
    case 0x49bdb0:
        return appendNamedProfile(run, receiver, arguments);
    case 0x49be50:
        return appendSerializedProfile(run, receiver, arguments);
    case 0x49bee0:
        return findProfileByName(run, receiver, arguments);
    case 0x49bf30:
        return removeProfileRecord(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_save_load_canonical_entry, owned, body)
