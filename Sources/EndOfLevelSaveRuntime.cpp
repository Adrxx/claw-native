// End-of-level save path entry
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
    case 0x49bbc0:
        return 0;
    default:
        return -1;
    }
}

// Models the pushes of one call: the callee-entry ESP is the body's ESP after
// its prologue (entry - 0x34), minus the stack arguments and the return word.
void enter(Run &run, uint32_t argumentCount) {
    run.stackPointer = run.frame - 0x34 - 4 * argumentCount - 4;
}

// Releases the local file object, as the original does on every path after it
// was constructed.
void destroyFile(Run &run, uint32_t file) {
    enter(run, 0);
    run.call(0x4f7369, file);
}

// 0x49bbc0. Writes the end-of-level save: opens the save file (the name is the
// string at +0x1c) twice, serializes the manager's list of 0x2644-byte records
// into one buffer, checksums it, stamps the header at +0x20 and writes the
// encrypted header and records. Returns the record count, or 0 on any failure.
uint32_t function_49bbc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t manager = receiver;
    uint32_t name = run.get(manager + 0x1c);
    if (run.get(name - 8) == 0)
        return 0;
    uint32_t count = run.get(manager + 0xc);
    if (s32(count) <= 0)
        return 0;
    uint32_t file = run.automatic(-0x1c);
    enter(run, 0);
    run.call(0x4f72c9, file);
    enter(run, 3);
    if (!run.call(0x4f7448, file, {run.get(manager + 0x1c), 0x1000, 0})) {
        destroyFile(run, file);
        return 0;
    }
    enter(run, 0);
    run.call(0x4f766e, file);
    enter(run, 3);
    if (!run.call(0x4f7448, file, {run.get(manager + 0x1c), 1, 0})) {
        destroyFile(run, file);
        return 0;
    }
    count = run.get(manager + 0xc);
    uint32_t size = count * 0x2644;
    enter(run, 1);
    uint32_t buffer = run.call(0x4f63ec, 0, {size});
    if (!buffer) {
        destroyFile(run, file);
        return 0;
    }
    uint32_t destination = buffer;
    uint32_t node = run.get(manager + 0x4);
    while (node) {
        uint32_t next = run.get(node);
        uint32_t source = run.get(node + 0x8) + 4;
        for (uint32_t i = 0; i < 0x991; ++i)
            run.put(destination + 4 * i, run.get(source + 4 * i));
        destination += 0x2644;
        node = next;
    }
    enter(run, 2);
    uint32_t checksum = run.call(0x49bf70, manager, {buffer, size});
    run.put(manager + 0x24, checksum);
    run.put(manager + 0x2c, run.get(manager + 0xc));
    run.put(manager + 0x28, run.get(manager + 0x40));
    enter(run, 2);
    run.call(0x49c030, manager, {manager + 0x20, 0x20});
    enter(run, 2);
    run.call(0x49c030, manager, {buffer, size});
    enter(run, 2);
    run.call(0x4f75aa, file, {manager + 0x20, 0x20});
    enter(run, 2);
    run.call(0x4f75aa, file, {buffer, size});
    enter(run, 2);
    run.call(0x49c070, manager, {manager + 0x20, 0x20});
    enter(run, 1);
    enter(run, 1);
    run.call(0x4f6428, 0, {buffer});
    destroyFile(run, file);
    return count;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49bbc0:
        return function_49bbc0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_end_of_level_save_entry, owned, body)
