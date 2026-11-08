// Source image resource lifecycle, recovered from the original v1.0 bodies.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4bf680: return 4;
    case 0x4bfc20: return 0;
    case 0x4ce8e0: return 1;
    case 0x4ce900: return 0;
    case 0x4d2540: return 3;
    case 0x4d26c0: return 0;
    case 0x4d2790: return 1;
    case 0x4d27a0: return 2;
    case 0x4d56d0: return 0;
    default: return -1;
    }
}

// Offsets below include the return word, arguments and actual saved registers.
uint32_t callAt(Run &run, int32_t offset, uint32_t function, uint32_t receiver,
                std::initializer_list<uint32_t> arguments = {}) {
    run.stackPointer = run.automatic(offset);
    return run.call(function, receiver, arguments);
}

struct Frame {
    Run &run;
    uint32_t saved;
    uint32_t outgoing;
    Frame(Run &run, int32_t offset) : run(run), saved(run.frame), outgoing(run.stackPointer) {
        run.frame = run.automatic(offset);
        run.stackPointer = 0;
    }
    ~Frame() {
        run.frame = saved;
        run.stackPointer = outgoing;
    }
};

// 0x4bf680. Surface +0x18 width, +0x14 height; PID +4 flags, +8/+0xc dimensions.
uint32_t loadPID(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t manager = arguments[0];
    uint32_t data = arguments[1];
    uint32_t flags = run.get(data + 0x04);
    uint32_t width = run.get(data + 0x08);
    uint32_t height = run.get(data + 0x0c);
    if ((width & 3) || run.get(receiver + 0x18) != width || run.get(receiver + 0x14) != height)
        return 0;
    // Manager +0x878 palette validity, +0x478 palette, +0x474 depth.
    uint32_t valid = run.get(manager + 0x878);
    uint32_t palette = valid ? manager + 0x478 : 0;
    uint32_t depth = run.get(manager + 0x474);
    bool convert = depth != 8;
    if (flags & 0x80) {
        if (arguments[2] <= 0x300)
            return 0;
        uint32_t source = data + arguments[2] - 0x300;
        for (uint32_t i = 0; i < 0x100; ++i) {
            run.put8(0x5423b0 + i * 4, run.get8(source++));
            run.put8(0x5423b1 + i * 4, run.get8(source++));
            run.put8(0x5423b2 + i * 4, run.get8(source++));
            run.put8(0x5423b3 + i * 4, 0);
        }
        palette = 0x5423b0;
    } else if (convert) {
        if (!palette)
            return 0;
        if (depth == 8 && !valid)
            return 0;
    }
    uint32_t temporary = 0;
    if (!convert) {
        if (!callAt(run, -0x24, 0x4babe0, receiver, {data + 0x20}))
            return 0;
    } else {
        temporary = callAt(run, -0x24, 0x4f63ec, 0, {width * height});
        if (!temporary)
            return 0;
        if (!callAt(run, -0x30, 0x4bef50, receiver, {temporary, data + 0x20, width, height})) {
            callAt(run, -0x24, 0x4f6428, 0, {temporary});
            return 0;
        }
    }
    if (convert && !callAt(run, -0x30, 0x4b9e90, receiver, {temporary, 8, palette, 1})) {
        callAt(run, -0x24, 0x4f6428, 0, {temporary});
        return 0;
    }
    if (temporary)
        callAt(run, -0x24, 0x4f6428, 0, {temporary});
    if (flags & 1)
        callAt(run, -0x24, 0x4b9990, receiver, {arguments[3]});
    return 1;
}

// 0x4bfc20. ImageBuffer +0xc and +0x20 own separate allocations.
void destroyBuffer(Run &run, uint32_t receiver) {
    uint32_t allocation = run.get(receiver + 0x0c);
    if (allocation)
        callAt(run, -0x0c, 0x4f6428, 0, {allocation});
    allocation = run.get(receiver + 0x20);
    if (allocation)
        callAt(run, -0x0c, 0x4f6428, 0, {allocation});
}

// 0x4d26c0. Resource +0xc manager, +0x2c surface, +0x30 buffer.
void releaseSurface(Run &run, uint32_t receiver) {
    uint32_t surface = run.get(receiver + 0x2c);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x14, 0);
    if (surface) {
        callAt(run, -0x14, 0x4bc4f0, run.get(run.get(receiver + 0x0c) + 0x1c), {surface});
        run.put(receiver + 0x2c, 0);
    }
    uint32_t buffer = run.get(receiver + 0x30);
    if (buffer) {
        {
            Frame frame(run, -0x10);
            destroyBuffer(run, buffer);
        }
        callAt(run, -0x14, 0x4f6428, 0, {buffer});
        run.put(receiver + 0x30, 0);
    }
}

// 0x4ce900. Resource +0 vtable, +4 identifier, +8 state.
void destroyResource(Run &run, uint32_t receiver) {
    run.put(receiver + 0x00, 0x513a70);
    {
        Frame frame(run, -0x18);
        releaseSurface(run, receiver);
    }
    run.put(receiver + 0x04, 0xffffffff);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x00, 0x50becc);
}

// 0x4ce8e0.
uint32_t deletingDestructor(Run &run, uint32_t receiver, const uint32_t *arguments) {
    {
        Frame frame(run, -0x08);
        destroyResource(run, receiver);
    }
    if (arguments[0] & 1)
        callAt(run, -0x0c, 0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4d2540. Resource +0x18/+0x1c half sizes; +0x28 flags, +0x20/+0x24 origins.
uint32_t createSurface(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t key = arguments[2] ? run.get(0x543170) : 0xffffffff;
    uint32_t flags = run.get(0x54316c) ? 0x800 : 0;
    uint32_t surface = callAt(run, -0x1c, 0x4bc670, run.get(run.get(receiver + 0x0c) + 0x1c),
                              {arguments[0], arguments[1], 0, flags, key});
    run.put(receiver + 0x2c, surface);
    if (!surface)
        return 0;
    uint32_t width = run.get(surface + 0x18);
    run.put(receiver + 0x10, width);
    uint32_t height = run.get(surface + 0x14);
    run.put(receiver + 0x14, height);
    run.put(receiver + 0x18, uint32_t(s32(width) >> 1));
    run.put(receiver + 0x1c, uint32_t(s32(height) >> 1));
    // Surface +0xb8 color-key status.
    run.put(receiver + 0x28, run.get(surface + 0xb8) ? 0x11 : 0x10);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x24, 0);
    return 1;
}

// 0x4d2790. The incoming argument is unused.
void flip(Run &run, uint32_t receiver) {
    uint32_t surface = run.get(receiver + 0x2c);
    if (surface)
        callAt(run, -0x04, 0x4b99d0, surface);
}

// 0x4d27a0. Surface +8 COM interface; resource-entry +0x14 byte count.
uint32_t restoreFromResource(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t surface = run.get(receiver + 0x2c);
    if (!surface)
        return 1;
    uint32_t interface = run.get(surface + 0x08);
    if (interface && !callAt(run, -0x14, run.get(run.get(interface) + 0x60), 0, {interface}))
        return 1;
    interface = run.get(run.get(receiver + 0x2c) + 0x08);
    if (callAt(run, -0x14, run.get(run.get(interface) + 0x6c), 0, {interface})) {
        callAt(run, -0x10, run.get(run.get(receiver) + 0x1c), receiver);
        return callAt(run, -0x18, run.get(run.get(receiver) + 0x2c), receiver, {arguments[0], arguments[1]});
    }
    uint32_t entry = arguments[0];
    uint32_t tag = callAt(run, -0x10, 0x4b61b0, entry);
    uint32_t kind;
    if (tag <= 0x504358) {
        if (tag == 0x504358)
            kind = 2;
        else if (tag == 0x424d50)
            kind = 1;
        else
            return 0;
    } else if (tag == 0x504944) {
        kind = 4;
    } else if (tag == 0x524944) {
        kind = 3;
    } else {
        return 0;
    }
    uint32_t bytes = callAt(run, -0x10, 0x4b61c0, entry);
    if (!bytes)
        return 0;
    uint32_t size = run.get(entry + 0x14);
    if (!size)
        return 0;
    uint32_t key = run.get(0x543170);
    uint32_t manager = run.get(run.get(receiver + 0x0c) + 0x1c);
    return callAt(run, -0x24, 0x4b95b0, run.get(receiver + 0x2c), {manager, bytes, kind, size, key});
}

// 0x4d56d0. Retry Restore once, reloading both nested pointers after each call.
uint32_t retryRestore(Run &run, uint32_t receiver) {
    uint32_t surface = run.get(receiver + 0x2c);
    if (!surface)
        return 1;
    uint32_t interface = run.get(surface + 0x08);
    if (interface && !callAt(run, -0x0c, run.get(run.get(interface) + 0x60), 0, {interface}))
        return 1;
    interface = run.get(run.get(receiver + 0x2c) + 0x08);
    if (!callAt(run, -0x0c, run.get(run.get(interface) + 0x6c), 0, {interface}))
        return 1;
    interface = run.get(run.get(receiver + 0x2c) + 0x08);
    if (!callAt(run, -0x0c, run.get(run.get(interface) + 0x6c), 0, {interface}))
        return 1;
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4bf680:
        return loadPID(run, receiver, arguments);
    case 0x4bfc20:
        destroyBuffer(run, receiver);
        return 0;
    case 0x4ce8e0:
        return deletingDestructor(run, receiver, arguments);
    case 0x4ce900:
        destroyResource(run, receiver);
        return 0;
    case 0x4d2540:
        return createSurface(run, receiver, arguments);
    case 0x4d26c0:
        releaseSurface(run, receiver);
        return 0;
    case 0x4d2790:
        flip(run, receiver);
        return 0;
    case 0x4d27a0:
        return restoreFromResource(run, receiver, arguments);
    case 0x4d56d0:
        return retryRestore(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_image_resource_lifecycle_canonical_entry, owned, body)
