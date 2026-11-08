// Downstream archive and interface behavior, compared with retail v1.0.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4b6bd0:
    case 0x4b7950:
        return 2;
    case 0x4b7b40:
    case 0x4bc990:
        return 3;
    case 0x4cf010:
    case 0x4deda0:
    case 0x4e2110:
        return 1;
    case 0x4dea30:
        return 4;
    default:
        return -1;
    }
}

// 0x4b6bd0. Directory +0x18 is its archive, +0x3c its child tree.
uint32_t layoutRecursive(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t success = 1;
    run.stackPointer = run.automatic(-0x10);
    uint32_t node = run.call(0x4d54c0, receiver + 0x3c);
    while (node) {
        const uint32_t child = run.get(node + 0x14);
        const uint32_t childArguments[] = {child + 0x4, child + 0x8};
        const uint32_t parentFrame = run.frame;
        run.frame = run.automatic(-0x18);
        const uint32_t childResult = layoutRecursive(run, child, childArguments);
        run.frame = parentFrame;
        if (!childResult) {
            success = 0;
            break;
        }
        run.stackPointer = run.automatic(-0x10);
        node = run.call(0x4d5350, node);
    }
    // The archive cursor is reloaded on both sides of serialization.
    run.put(arguments[0], run.get(run.get(receiver + 0x18) + 0x1c));
    const uint32_t cursor = run.get(run.get(receiver + 0x18) + 0x1c);
    run.stackPointer = run.automatic(-0x18);
    if (!run.call(0x4b6c50, receiver, {cursor, arguments[1]})) {
        return 0;
    }
    const uint32_t archive = run.get(receiver + 0x18);
    const uint32_t size = run.get(arguments[1]);
    run.put(archive + 0x1c, run.get(archive + 0x1c) + size);
    return success;
}

// 0x4b7950. Recursively copy directory records, file bytes and metadata.
uint32_t copyRecursive(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t destination = arguments[0];
    const uint32_t source = arguments[1];
    run.stackPointer = run.automatic(-0x18);
    uint32_t child = run.call(0x4b68e0, source);
    while (child) {
        const uint32_t name = run.get(child);
        run.stackPointer = run.automatic(-0x1c);
        const uint32_t copied = run.call(0x4b69a0, destination, {name});
        const uint32_t childArguments[] = {copied, child};
        const uint32_t parentFrame = run.frame;
        run.frame = run.automatic(-0x20);
        copyRecursive(run, receiver, childArguments);
        run.frame = parentFrame;
        run.put(copied + 0x14, run.get(child + 0x14));
        run.stackPointer = run.automatic(-0x1c);
        child = run.call(0x4b6900, source, {child});
    }
    run.stackPointer = run.automatic(-0x18);
    uint32_t bucket = run.call(0x4b6920, source);
    while (bucket) {
        run.stackPointer = run.automatic(-0x1c);
        uint32_t file = run.call(0x4b6960, source, {bucket});
        while (file) {
            const uint32_t name = run.get(file);
            const uint32_t type = run.get(file + 0x4);
            run.stackPointer = run.automatic(-0x18);
            const uint32_t flags = run.call(0x4b61b0, file);
            run.stackPointer = run.automatic(-0x24);
            const uint32_t copy = run.call(0x4b6a60, destination, {type, name, flags});
            run.stackPointer = run.automatic(-0x1c);
            uint32_t target = run.call(0x4b6260, copy, {run.get(file + 0x14)});
            if (run.get(file + 0x14)) {
                run.stackPointer = run.automatic(-0x18);
                uint32_t bytes = run.call(0x4b61c0, file);
                const uint32_t count = run.get(file + 0x14);
                for (uint32_t index = 0; index < (count >> 2); ++index) {
                    run.put(target, run.get(bytes));
                    target += 4;
                    bytes += 4;
                }
                for (uint32_t index = 0; index < (count & 3); ++index) {
                    run.put8(target, run.get8(bytes));
                    ++target;
                    ++bytes;
                }
                run.stackPointer = run.automatic(-0x18);
                run.call(0x4b63e0, copy);
            }
            uint32_t index = run.get(file + 0x1c);
            if (index) {
                run.stackPointer = run.automatic(-0x20);
                run.call(0x4b62d0, copy, {index, run.get(run.get(file + 0x20) + index * 4)});
                while (index) {
                    const uint32_t table = run.get(file + 0x20);
                    --index;
                    run.stackPointer = run.automatic(-0x20);
                    run.call(0x4b62d0, copy, {index, run.get(table + index * 4)});
                }
            }
            run.put(copy + 0x10, run.get(file + 0x10));
            run.stackPointer = run.automatic(-0x1c);
            run.call(0x4b6350, copy, {run.get(file + 0xc)});
            run.stackPointer = run.automatic(-0x1c);
            file = run.call(0x4b6980, source, {file});
        }
        run.stackPointer = run.automatic(-0x1c);
        bucket = run.call(0x4b6940, source, {bucket});
    }
    return 0;
}

// 0x4b7b40. Receiver +0xc is the current FILE, virtual +8 asks to retry.
uint32_t writeRetry(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t count = arguments[1];
    if (!count) {
        return 0;
    }
    run.stackPointer = run.automatic(-0x1c);
    uint32_t seek = run.call(0x4a7840, 0, {run.get(receiver + 0xc), arguments[0], 0});
    while (seek) {
        run.stackPointer = run.automatic(-0x10);
        if (!run.vcall(receiver, 0x8)) {
            return 0;
        }
        run.stackPointer = run.automatic(-0x1c);
        seek = run.call(0x4a7840, 0, {run.get(receiver + 0xc), arguments[0], 0});
    }
    run.stackPointer = run.automatic(-0x20);
    uint32_t written = run.call(0x4a73e0, 0, {arguments[2], 1, count, run.get(receiver + 0xc)});
    while (written != count) {
        run.stackPointer = run.automatic(-0x10);
        if (!run.vcall(receiver, 0x8)) {
            return 0;
        }
        run.stackPointer = run.automatic(-0x20);
        written = run.call(0x4a73e0, 0, {arguments[2], 1, count, run.get(receiver + 0xc)});
    }
    return written;
}

// 0x4bc990. The load flags always include bits 0x840.
uint32_t loadMasked(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.stackPointer = run.automatic(-0x10);
    return run.call(0x4bc740, receiver, {arguments[0], arguments[1] | 0x840, arguments[2]});
}

// 0x4cf010. Preserve the deterministic EAX of the global setter.
uint32_t setSurface(Run &run, const uint32_t *arguments) {
    run.stackPointer = run.automatic(-0x8);
    return run.call(0x4bd090, 0, {arguments[0]});
}

// 0x4dea30. All temporary CString arguments are actual by-value stack slots.
uint32_t centeredLabel(Run &run, const uint32_t *arguments) {
    const uint32_t label = run.automatic(-0x1c);
    const uint32_t size = run.automatic(-0x14);
    const uint32_t sourceString = run.automatic(0x4);
    const uint32_t measureString = run.automatic(-0x2c);
    const uint32_t drawString = run.automatic(-0x3c);
    run.put(sourceString, arguments[0]);
    run.stackPointer = run.automatic(-0x2c);
    run.call(0x4df6c0, label);
    run.stackPointer = run.automatic(-0x30);
    run.call(0x4df6d0, label, {arguments[2]});
    run.stackPointer = run.automatic(-0x34);
    run.call(0x4f6449, measureString, {sourceString});
    run.stackPointer = run.automatic(-0x34);
    run.call(0x4dfde0, label, {size, run.get(measureString)});
    const uint32_t target = arguments[1];
    const uint32_t x = uint32_t(s32(run.get(target + 0x18)) / 2) - uint32_t(s32(run.get(size)) / 2);
    const uint32_t y = uint32_t(s32(run.get(target + 0x14)) / 2) - uint32_t(s32(run.get(size + 0x4)) / 2);
    run.stackPointer = run.automatic(-0x30);
    run.call(0x4df6e0, label, {0});
    run.stackPointer = run.automatic(-0x44);
    run.call(0x4f6449, drawString, {sourceString});
    run.stackPointer = run.automatic(-0x40);
    run.call(0x4df6f0, label, {run.get(drawString), target, x + 1, y + 1, 1});
    run.stackPointer = run.automatic(-0x30);
    run.call(0x4df6e0, label, {arguments[3]});
    run.stackPointer = run.automatic(-0x44);
    run.call(0x4f6449, drawString, {sourceString});
    run.stackPointer = run.automatic(-0x40);
    run.call(0x4df6f0, label, {run.get(drawString), target, x, y, 1});
    run.stackPointer = run.automatic(-0x2c);
    run.call(0x4bc110, label);
    run.stackPointer = run.automatic(-0x2c);
    run.call(0x4f6584, sourceString);
    return 0;
}

// 0x4deda0. Slots +4 stores an unchecked pointer; index arithmetic wraps.
uint32_t imageSlot(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return run.get(receiver + 0x4) + arguments[0] * 4;
}

// 0x4e2110. Record count and IDs are WORDs, compared to the full argument.
uint32_t dialogRecord(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t count = run.get16(receiver + 0x14);
    if (!count) {
        return 0;
    }
    const uint32_t base = run.get(receiver + 0x3c);
    for (uint32_t index = 0; index < count; ++index) {
        if (run.get16(base + index * 0x5c + 0x10) == arguments[0]) {
            return base + index * 0x5c;
        }
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b6bd0:
        return layoutRecursive(run, receiver, arguments);
    case 0x4b7950:
        return copyRecursive(run, receiver, arguments);
    case 0x4b7b40:
        return writeRetry(run, receiver, arguments);
    case 0x4bc990:
        return loadMasked(run, receiver, arguments);
    case 0x4cf010:
        return setSurface(run, arguments);
    case 0x4dea30:
        return centeredLabel(run, arguments);
    case 0x4deda0:
        return imageSlot(run, receiver, arguments);
    case 0x4e2110:
        return dialogRecord(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_call_closure_downstream_interface_entry, owned, body)
