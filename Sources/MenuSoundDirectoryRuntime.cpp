#include "ClawRuntime.hpp"

namespace {

using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x4ca440:
        return 3;
    default:
        return -1;
    }
}

struct RecursiveFrame {
    Run &run;
    uint32_t parentFrame;
    uint32_t parentStackPointer;

    RecursiveFrame(Run &run, uint32_t frame)
        : run(run), parentFrame(run.frame), parentStackPointer(run.stackPointer) {
        run.frame = frame;
        run.stackPointer = frame;
    }

    ~RecursiveFrame() {
        run.frame = parentFrame;
        run.stackPointer = parentStackPointer;
    }
};

void copyName(Run &run, uint32_t destination, uint32_t source) {
    uint32_t length = 0;
    do {
        ++length;
    } while (run.get8(source + length - 1) != 0);
    uint32_t offset = 0;
    for (; offset + 4 <= length; offset += 4) {
        run.put(destination + offset, run.get(source + offset));
    }
    for (; offset < length; ++offset) {
        run.put8(destination + offset, run.get8(source + offset));
    }
}

// 0x4ca440. Recursively loads WAV resources into the manager's CString map.
uint32_t loadSoundDirectory(Run &run, uint32_t manager, uint32_t directory,
                           uint32_t prefix, uint32_t separator) {
    // Manager +0x30 disables loading; +0x10 is the CString map.
    if (run.get(manager + 0x30) != 0) {
        return 0;
    }
    uint32_t count = 0;
    run.stackPointer = run.frame - 0x28;
    uint32_t name = run.call(0x4f63ec, 0, {0x100});
    if (name == 0) {
        return 0;
    }
    run.put8(name, 0);
    run.stackPointer = run.frame - 0x24;
    uint32_t child = run.call(0x4b68e0, directory, {});
    while (child != 0) {
        // Directory and resource objects keep their name pointer at +0x00.
        if (prefix != 0 && run.get8(prefix) != 0) {
            uint32_t childName = run.get(child + 0x00);
            run.stackPointer = run.frame - 0x38;
            run.call(0x4a3920, 0, {name, 0x532c14, prefix, separator, childName});
        } else {
            copyName(run, name, run.get(child + 0x00));
        }
        uint32_t descendantCount = 0;
        {
            RecursiveFrame frame(run, run.frame - 0x30);
            descendantCount = loadSoundDirectory(run, manager, child, name, separator);
        }
        count += descendantCount;
        run.stackPointer = run.frame - 0x28;
        child = run.call(0x4b6900, directory, {child});
    }
    run.stackPointer = run.frame - 0x24;
    uint32_t group = run.call(0x4b6920, directory, {});
    while (group != 0) {
        run.stackPointer = run.frame - 0x28;
        uint32_t entry = run.call(0x4b6960, directory, {group});
        while (entry != 0) {
            run.stackPointer = run.frame - 0x24;
            uint32_t type = run.call(0x4b61b0, entry, {});
            if (type == 0x574156) {
                if (prefix != 0 && run.get8(prefix) != 0) {
                    uint32_t entryName = run.get(entry + 0x00);
                    run.stackPointer = run.frame - 0x38;
                    run.call(0x4a3920, 0, {name, 0x532c14, prefix, separator, entryName});
                } else {
                    copyName(run, name, run.get(entry + 0x00));
                }
                uint32_t lookupOutput = run.automatic(-4);
                run.put(lookupOutput, 0);
                run.stackPointer = run.frame - 0x2c;
                run.call(0x4f6286, manager + 0x10, {name, lookupOutput});
                if (run.get(lookupOutput) == 0) {
                    run.stackPointer = run.frame - 0x2c;
                    uint32_t created = run.call(0x4ca3b0, manager, {name, entry});
                    if (created != 0) {
                        ++count;
                    }
                }
            }
            run.stackPointer = run.frame - 0x28;
            entry = run.call(0x4b6980, directory, {entry});
        }
        run.stackPointer = run.frame - 0x28;
        group = run.call(0x4b6940, directory, {group});
    }
    run.stackPointer = run.frame - 0x28;
    run.call(0x4f6428, 0, {name});
    return count;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4ca440:
        return loadSoundDirectory(run, receiver, arguments[0], arguments[1], arguments[2]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_sound_directory_entry, owned, body)
