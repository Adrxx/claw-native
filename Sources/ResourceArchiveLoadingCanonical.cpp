#include "ClawRuntime.hpp"

namespace {
using claw::Run;

// Scope an owned nested activation at its actual x86 entry stack pointer.
struct Frame {
    Run &run;
    uint32_t saved;
    Frame(Run &run, int32_t delta) : run(run), saved(run.frame) {
        run.frame = run.automatic(delta);
    }
    ~Frame() {
        run.frame = saved;
    }
};
uint32_t callAt(Run &run, int32_t delta, uint32_t target, uint32_t receiver,
                std::initializer_list<uint32_t> args = {}) {
    run.stackPointer = run.automatic(delta);
    return run.call(target, receiver, args);
}
uint32_t terminatedSize(Run &run, uint32_t text) {
    uint32_t size = 0;
    do {
        ++size;
    } while (run.get8(text + size - 1) != 0);
    return size;
}

// 0x4b7bd0. +0x0c file token; +0x20 read-only flag; vtable +0x08 retry.
uint32_t openFile(Run &run, uint32_t self, uint32_t path, uint32_t readOnly, uint32_t create) {
    for (;;) {
        if (create && readOnly)
            return 0;
        uint32_t mode = create ? 0x5324d0 : (readOnly ? 0x532298 : 0x5324cc);
        uint32_t file = callAt(run, -28, 0x4f1d90, 0, {path, mode});
        run.put(self + 0x0c, file);
        if (file)
            break;
        uint32_t retry = run.get(run.get(self) + 0x08);
        if (!callAt(run, -20, retry, self))
            return 0;
        if (run.get(self + 0x0c))
            break;
    }
    run.put(self + 0x20, readOnly);
    return 1;
}
// 0x4b7c40 and 0x4b7c80. Successful CRT calls leave the file token intact.
uint32_t fileOperation(Run &run, uint32_t self, uint32_t target) {
    if (!run.get(self + 0x0c))
        return 0;
    for (;;) {
        if (!callAt(run, -12, target, 0, {run.get(self + 0x0c)}))
            return 1;
        uint32_t retry = run.get(run.get(self) + 0x08);
        if (!callAt(run, -8, retry, self))
            return 0;
    }
}
// 0x4b7210. Controller constructor deliberately does not initialize +0x14/+0x18.
uint32_t construct(Run &run, uint32_t self) {
    run.put(self + 0x00, 0x513578);
    run.put(self + 0x08, 0);
    run.put(self + 0x0c, 0);
    run.put(self + 0x10, 0);
    run.put(self + 0x1c, 0);
    run.put(self + 0x20, 1);
    run.put(self + 0x24, 0);
    run.put(self + 0x28, 0);
    run.put(self + 0x2c, 0);
    run.put(self + 0x30, 0);
    run.put(self + 0x34, 0);
    run.put(self + 0x38, 0);
    run.put(self + 0x3c, 0);
    run.put(self + 0x40, 0);
    run.put(self + 0x04, 1);
    run.put(self + 0x44, 0);
    return self;
}
// 0x4b6ed0. Directory +0x18 controller, +0x3c child list,
// +0x10 total resource length, +0x0c minimum resource offset.
uint32_t loadDirectory(Run &run, uint32_t self, uint32_t offset, uint32_t size) {
    run.put(self + 0x10, 0);
    run.put(self + 0x0c, 0xffffffff);
    uint32_t buffer = callAt(run, -76, 0x4f63ec, 0, {size});
    if (!buffer)
        return 0;
    if (callAt(run, -84, 0x4b7ab0, run.get(self + 0x18), {offset, size, buffer}) != size) {
        callAt(run, -76, 0x4f6428, 0, {buffer});
        return 0;
    }
    uint32_t cursor = buffer;
    uint32_t end = buffer + size;
    while (cursor < end) {
        if (run.get(cursor) == 1) {
            uint32_t first = run.get(cursor + 0x04);
            uint32_t second = run.get(cursor + 0x08);
            uint32_t third = run.get(cursor + 0x0c);
            uint32_t name = cursor + 0x10;
            cursor = name + terminatedSize(run, name);
            uint32_t object = callAt(run, -76, 0x4f63ec, 0, {0x4c});
            if (object)
                object = callAt(run, -96, 0x4b6600, object, {run.get(self + 0x18), self, name, first, second, third});
            callAt(run, -76, 0x4d5450, self + 0x3c, {object + 0x24});
        } else {
            uint32_t first = run.get(cursor + 0x04);
            uint32_t second = run.get(cursor + 0x08);
            uint32_t third = run.get(cursor + 0x0c);
            uint32_t fourth = run.get(cursor + 0x10);
            uint32_t tagValue = run.get(cursor + 0x14);
            uint32_t count = run.get(cursor + 0x18);
            uint32_t name = cursor + 0x1c;
            uint32_t metadata = name + terminatedSize(run, name);
            cursor = metadata + terminatedSize(run, metadata);
            if (!run.get8(metadata))
                metadata = 0;
            uint32_t auxiliary = 0;
            if (count) {
                auxiliary = callAt(run, -76, 0x4f63ec, 0, {count * 4});
                for (uint32_t i = 0; i < count; ++i) {
                    run.put(auxiliary + i * 4, run.get(cursor));
                    cursor += 4;
                }
            }
            uint32_t tag = callAt(run, -76, 0x4b7170, self, {tagValue});
            uint32_t object = callAt(run, -76, 0x4f63ec, 0, {0x60});
            if (object)
                object = callAt(run, -112, 0x4b5ff0, object, {self, name, fourth, tag, metadata, second, first, third, count, auxiliary});
            callAt(run, -76, 0x4d5450, tag + 0x1c, {object + 0x48});
            callAt(run, -76, 0x4d5450, tag + 0x24, {object + 0x30});
            run.put(self + 0x10, run.get(self + 0x10) + run.get(object + 0x14));
            if (run.get(object + 0x28) < run.get(self + 0x0c))
                run.put(self + 0x0c, run.get(object + 0x28));
            if (auxiliary)
                callAt(run, -76, 0x4f6428, 0, {auxiliary});
        }
    }
    callAt(run, -76, 0x4f6428, 0, {buffer});
    return 1;
}
// 0x4b6b60. Recursive loading accumulates failure while visiting all siblings.
uint32_t loadTree(Run &run, uint32_t self, uint32_t offset, uint32_t size) {
    if (!size)
        return 1;
    {
        Frame frame(run, -20);
        if (!loadDirectory(run, self, offset, size))
            return 0;
    }
    uint32_t result = 1;
    uint32_t node = callAt(run, -12, 0x4d54c0, self + 0x3c);
    while (node) {
        uint32_t child = run.get(node + 0x14);
        uint32_t childSize = run.get(child + 0x08);
        uint32_t childOffset = run.get(child + 0x04);
        {
            Frame frame(run, -20);
            if (!loadTree(run, child, childOffset, childSize))
                result = 0;
        }
        node = callAt(run, -12, 0x4d5350, node);
    }
    return result;
}
// 0x4b72e0. Header is an unaligned original stack buffer at entry ESP - 184.
uint32_t openArchive(Run &run, uint32_t self, uint32_t path, uint32_t readOnly, uint32_t create) {
    run.put(self + 0x20, readOnly);
    uint32_t allocated = callAt(run, -212, 0x4f63ec, 0, {terminatedSize(run, path)});
    run.put(self + 0x44, allocated);
    uint32_t length = terminatedSize(run, path);
    for (uint32_t i = 0; i < length; ++i)
        run.put8(allocated + i, run.get8(path + i));
    {
        Frame frame(run, -220);
        if (!openFile(run, self, path, readOnly, create))
            return 0;
    }
    run.put(self + 0x08, 1);
    if (create) {
        run.put(self + 0x1c, 0xa8);
        run.put(self + 0x2c, 1);
        uint32_t root = callAt(run, -212, 0x4f63ec, 0, {0x4c});
        if (root) {
            uint32_t time = callAt(run, -208, 0x4b7cc0, self);
            root = callAt(run, -232, 0x4b6600, root, {self, 0, 0x534938, 0, 0, time});
        }
        run.put(self + 0x24, root);
    } else {
        uint32_t header = run.automatic(-184);
        callAt(run, -220, 0x4b7ab0, self, {0, 0xa8, header});
        run.put(self + 0x10, run.get(header + 0x83));
        run.put(self + 0x1c, run.get(header + 0x8f));
        run.put(self + 0x28, run.get(header + 0x93));
        run.put(self + 0x14, run.get(header + 0x87));
        run.put(self + 0x18, run.get(header + 0x8b));
        run.put(self + 0x38, run.get(header + 0x9b));
        run.put(self + 0x30, run.get(header + 0x7f));
        run.put(self + 0x34, run.get(header + 0x97));
        run.put(self + 0x3c, run.get(header + 0x9f));
        run.put(self + 0x40, run.get(header + 0xa3));
        run.put(self + 0x04, run.get8(header + 0xa7));
        uint32_t root = callAt(run, -212, 0x4f63ec, 0, {0x4c});
        if (root)
            root = callAt(run, -232, 0x4b6600, root, {self, 0, 0x534938, run.get(self + 0x10), run.get(self + 0x14), run.get(self + 0x18)});
        uint32_t size = run.get(self + 0x14);
        uint32_t offset = run.get(self + 0x10);
        run.put(self + 0x24, root);
        Frame frame(run, -216);
        loadTree(run, root, offset, size);
    }
    return 1;
}
// 0x4b74d0. +0x24 root; +0x44 allocated archive path; +0x08 open flag.
uint32_t closeArchive(Run &run, uint32_t self, uint32_t compact) {
    if (!run.get(self + 0x20))
        callAt(run, -16, 0x4b7550, self);
    uint32_t result;
    if (compact) {
        result = callAt(run, -16, 0x4b76b0, self);
    } else {
        Frame frame(run, -16);
        result = fileOperation(run, self, 0x4a7ae0);
    }
    uint32_t root = run.get(self + 0x24);
    if (root) {
        callAt(run, -16, 0x4b66d0, root);
        callAt(run, -20, 0x4f6428, 0, {root});
        run.put(self + 0x24, 0);
    }
    uint32_t path = run.get(self + 0x44);
    if (path) {
        callAt(run, -20, 0x4f6428, 0, {path});
        run.put(self + 0x44, 0);
    }
    run.put(self + 0x08, 0);
    return result;
}
// 0x4b7250. Destructor resets controller, including fields left by constructor.
uint32_t destroy(Run &run, uint32_t self) {
    uint32_t open = run.get(self + 0x08);
    run.put(self + 0x00, 0x513578);
    if (open) {
        Frame frame(run, -20);
        closeArchive(run, self, 0);
    }
    if (run.get(self + 0x0c)) {
        Frame frame(run, -16);
        fileOperation(run, self, 0x4a7ae0);
    }
    uint32_t root = run.get(self + 0x24);
    if (root) {
        callAt(run, -16, 0x4b66d0, root);
        callAt(run, -20, 0x4f6428, 0, {root});
        run.put(self + 0x24, 0);
    }
    uint32_t path = run.get(self + 0x44);
    if (path) {
        callAt(run, -20, 0x4f6428, 0, {path});
        run.put(self + 0x44, 0);
    }
    run.put(self + 0x08, 0);
    run.put(self + 0x0c, 0);
    run.put(self + 0x10, 0);
    run.put(self + 0x14, 0);
    run.put(self + 0x18, 0);
    run.put(self + 0x1c, 0);
    run.put(self + 0x24, 0);
    run.put(self + 0x28, 0);
    run.put(self + 0x2c, 0);
    run.put(self + 0x34, 0);
    run.put(self + 0x38, 0);
    run.put(self + 0x3c, 0);
    run.put(self + 0x40, 0);
    run.put(self + 0x44, 0);
    run.put(self + 0x20, 1);
    run.put(self + 0x30, 1);
    run.put(self + 0x04, 1);
    return 0;
}
int owned(uint32_t function) {
    switch (function) {
    case 0x4b6b60:
    case 0x4b6ed0:
        return 2;
    case 0x4b72e0:
    case 0x4b7bd0:
        return 3;
    case 0x4b74d0:
        return 1;
    case 0x4b7210:
    case 0x4b7250:
    case 0x4b7c40:
    case 0x4b7c80:
        return 0;
    default:
        return -1;
    }
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *args) {
    switch (function) {
    case 0x4b6b60:
        return loadTree(run, receiver, args[0], args[1]);
    case 0x4b6ed0:
        return loadDirectory(run, receiver, args[0], args[1]);
    case 0x4b7210:
        return construct(run, receiver);
    case 0x4b7250:
        return destroy(run, receiver);
    case 0x4b72e0:
        return openArchive(run, receiver, args[0], args[1], args[2]);
    case 0x4b74d0:
        return closeArchive(run, receiver, args[0]);
    case 0x4b7bd0:
        return openFile(run, receiver, args[0], args[1], args[2]);
    case 0x4b7c40:
        return fileOperation(run, receiver, 0x4a7ae0);
    case 0x4b7c80:
        return fileOperation(run, receiver, 0x4a7920);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_resource_archive_loading_canonical_entry, owned, body)
