// Original application registry configuration reads
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b5c50:
        return 6;
    case 0x4b5fb0:
        return 3;
    case 0x4b5db0:
        return 1;
    case 0x4b5e90:
        return 4;
    case 0x4b5f30:
        return 2;
    default:
        return -1;
    }
}

// Forward string copies use the original word transfers followed by byte tails.
uint32_t stringBytes(Run &run, uint32_t source) {
    uint32_t count = 0;
    do {
        ++count;
    } while (run.get8(source + count - 1) != 0);
    return count;
}

void copyString(Run &run, uint32_t destination, uint32_t source) {
    uint32_t count = stringBytes(run, source);
    uint32_t offset = 0;
    for (; offset < (count & ~3u); offset += 4)
        run.put(destination + offset, run.get(source + offset));
    for (; offset < count; ++offset)
        run.put8(destination + offset, run.get8(source + offset));
}

// 0x4b5fb0. stdcall/3; disposition overwrites its incoming output-pointer slot.
uint32_t createKey(Run &run, uint32_t parent, uint32_t name, uint32_t output) {
    uint32_t disposition = run.automatic(12);
    run.put(disposition, output);
    run.stackPointer = run.frame - 40;
    uint32_t status = run.icall(0x546834, {parent, name, 0, 0x534938, 0, 0xf003f, 0, output, disposition});
    return status == 0 ? 1 : 0;
}

uint32_t nestedCreate(Run &run, uint32_t entry, uint32_t parent, uint32_t name, uint32_t output) {
    uint32_t savedFrame = run.frame;
    uint32_t savedStack = run.stackPointer;
    run.frame = entry;
    uint32_t result = createKey(run, parent, name, output);
    run.frame = savedFrame;
    run.stackPointer = savedStack;
    return result;
}

// 0x4b5db0. +0 initialized flag, +0x14 version key, +0x18 selected key.
uint32_t selectKey(Run &run, uint32_t receiver, uint32_t name) {
    if (!run.get(receiver))
        return 0;
    if (!name) {
        run.put(receiver + 0x18, run.get(receiver + 0x14));
        return 1;
    }
    return nestedCreate(run, run.frame - 16, run.get(receiver + 0x14), name, receiver + 0x18);
}

// 0x4b5c50. +0x1c product text, +0x11c selection text, +4 borrowed root.
uint32_t function_4b5c50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t selection = arguments[3];
    copyString(run, receiver + 0x1c, arguments[1]);
    if (selection)
        copyString(run, receiver + 0x11c, selection);
    else
        run.put8(receiver + 0x11c, 0);
    run.put(receiver + 4, arguments[4]);
    uint32_t softwareTail = run.get(0x532478);
    uint32_t softwareHead = run.get(0x532474);
    run.put(run.automatic(-8), softwareTail);
    run.put(run.automatic(-12), softwareHead);
    run.put8(run.automatic(-4), run.get8(0x53247c));
    uint32_t base = arguments[5] ? arguments[5] : run.automatic(-12);
    uint32_t entry = run.frame - 44;
    // +8 base key, +0xc company key, +0x10 product key.
    if (!nestedCreate(run, entry, arguments[4], base, receiver + 8))
        return 0;
    if (!nestedCreate(run, entry, run.get(receiver + 8), arguments[0], receiver + 0xc))
        return 0;
    if (!nestedCreate(run, entry, run.get(receiver + 0xc), arguments[1], receiver + 0x10))
        return 0;
    if (!nestedCreate(run, entry, run.get(receiver + 0x10), arguments[2], receiver + 0x14))
        return 0;
    run.put(receiver, 1);
    uint32_t savedFrame = run.frame;
    run.frame -= 36;
    uint32_t result = selectKey(run, receiver, selection);
    run.frame = savedFrame;
    if (result)
        return 1;
    run.put(receiver, 0);
    return 0;
}

// 0x4b5fb0.
uint32_t function_4b5fb0(Run &run, uint32_t, const uint32_t *arguments) {
    return createKey(run, arguments[0], arguments[1], arguments[2]);
}

// 0x4b5db0.
uint32_t function_4b5db0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return selectKey(run, receiver, arguments[0]);
}

// 0x4b5e90. Incoming third argument is reused as the query type output.
uint32_t function_4b5e90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t destination = arguments[1];
    uint32_t length = arguments[2];
    if (run.get(receiver) && arguments[0] && destination && run.get(length)) {
        run.stackPointer = run.frame - 44;
        uint32_t status = run.icall(0x54682c, {run.get(receiver + 0x18), arguments[0], 0, run.automatic(12), destination, length});
        if (!status && run.get(run.automatic(12)) == 1)
            return destination;
    }
    uint32_t fallback = arguments[3];
    if (!fallback) {
        run.put(length, 0);
        return 0;
    }
    copyString(run, destination, fallback);
    run.put(length, stringBytes(run, destination) - 1);
    return destination;
}

// 0x4b5f30. Locals -8 type, -4 data; incoming name slot becomes capacity.
uint32_t function_4b5f30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (run.get(receiver) && arguments[0]) {
        run.put(run.automatic(4), 4);
        run.stackPointer = run.frame - 36;
        uint32_t status = run.icall(0x54682c, {run.get(receiver + 0x18), arguments[0], 0, run.automatic(-8), run.automatic(-4), run.automatic(4)});
        if (!status && run.get(run.automatic(-8)) == 4)
            return run.get(run.automatic(-4));
    }
    return arguments[1];
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b5c50:
        return function_4b5c50(run, receiver, arguments);
    case 0x4b5fb0:
        return function_4b5fb0(run, receiver, arguments);
    case 0x4b5db0:
        return function_4b5db0(run, receiver, arguments);
    case 0x4b5e90:
        return function_4b5e90(run, receiver, arguments);
    case 0x4b5f30:
        return function_4b5f30(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_application_configuration_entry, owned, body)
