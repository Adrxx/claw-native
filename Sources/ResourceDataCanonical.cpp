#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x4b5ff0:
        return 10;
    case 0x4b6120:
    case 0x4b61b0:
    case 0x4b61c0:
    case 0x4b6230:
        return 0;
    case 0x4b7ab0:
        return 3;
    default:
        return -1;
    }
}

uint32_t nameSize(Run &run, uint32_t source) {
    uint32_t count = 0;
    do {
        ++count;
    } while (run.get8(source + count - 1) != 0);
    return count;
}

void copyName(Run &run, uint32_t destination, uint32_t source) {
    uint32_t count = nameSize(run, source);
    uint32_t words = count >> 2;
    for (uint32_t index = 0; index < words; ++index) {
        uint32_t value = run.get(source + index * 4);
        run.put(destination + index * 4, value);
    }
    for (uint32_t index = words * 4; index < count; ++index) {
        uint8_t value = run.get8(source + index);
        run.put8(destination + index, value);
    }
}

// 0x4b5ff0. +0/+0xc names, +4/+8 opaque/type, +0x10 opaque,
// +0x14 byte count, +0x18 cache, +0x1c word count, +0x20 words,
// +0x24 owner, +0x28 file offset, +0x2c zero. Embedded nodes have
// vtables +0x30/+0x48 and back-pointers +0x44/+0x5c.
uint32_t function_004b5ff0(Run &run, uint32_t object, const uint32_t *arguments) {
    uint32_t owner = arguments[0];
    uint32_t primary = arguments[1];
    run.put(object + 0x30, 0x51356c);
    run.put(object + 0x44, 0);
    run.put(object + 0x48, 0x513568);
    run.put(object + 0x5c, 0);
    run.put(object + 0x24, owner);
    if (primary != 0) {
        uint32_t size = nameSize(run, primary);
        uint32_t allocation = run.call(0x4f63ec, 0, {size});
        run.put(object + 0x00, allocation);
        if (allocation != 0) {
            copyName(run, allocation, primary);
        }
    }
    uint32_t secondary = arguments[4];
    run.put(object + 0x04, arguments[2]);
    run.put(object + 0x08, arguments[3]);
    if (secondary == 0) {
        run.put(object + 0x0c, 0);
    } else {
        uint32_t size = nameSize(run, secondary);
        uint32_t allocation = run.call(0x4f63ec, 0, {size});
        run.put(object + 0x0c, allocation);
        if (allocation != 0) {
            copyName(run, allocation, secondary);
        }
    }
    uint32_t source = arguments[9];
    uint32_t count = arguments[8];
    run.put(object + 0x14, arguments[5]);
    run.put(object + 0x28, arguments[6]);
    run.put(object + 0x10, arguments[7]);
    run.put(object + 0x1c, count);
    if (source == 0) {
        run.put(object + 0x20, 0);
    } else {
        uint32_t allocation = run.call(0x4f63ec, 0, {count * 4});
        run.put(object + 0x20, allocation);
        if (allocation != 0) {
            for (uint32_t index = 0; index < count; ++index) {
                uint32_t destination = run.get(object + 0x20);
                uint32_t value = run.get(source + index * 4);
                run.put(destination + index * 4, value);
            }
        }
    }
    run.put(object + 0x18, 0);
    run.put(object + 0x2c, 0);
    run.put(object + 0x5c, object);
    run.put(object + 0x44, object);
    return object;
}

// 0x4b6120.
uint32_t function_004b6120(Run &run, uint32_t object) {
    uint32_t primary = run.get(object + 0x00);
    if (primary != 0) {
        run.call(0x4f6428, 0, {primary});
    }
    uint32_t secondary = run.get(object + 0x0c);
    if (secondary != 0) {
        run.call(0x4f6428, 0, {secondary});
    }
    uint32_t owner = run.get(object + 0x24);
    // Owner +0x20 is its mapped data base.
    if (owner == 0 || run.get(owner + 0x20) == 0) {
        uint32_t cache = run.get(object + 0x18);
        if (cache != 0) {
            run.call(0x4f6428, 0, {cache});
        }
    }
    uint32_t words = run.get(object + 0x20);
    if (words != 0) {
        run.call(0x4f6428, 0, {words});
    }
    run.put(object + 0x00, 0);
    run.put(object + 0x04, 0);
    run.put(object + 0x08, 0);
    run.put(object + 0x0c, 0);
    run.put(object + 0x10, 0);
    run.put(object + 0x14, 0);
    run.put(object + 0x18, 0);
    run.put(object + 0x1c, 0);
    run.put(object + 0x20, 0);
    run.put(object + 0x24, 0);
    run.put(object + 0x28, 0);
    run.put(object + 0x2c, 0);
    run.put(object + 0x5c, 0);
    run.put(object + 0x44, 0);
    return 0;
}

// 0x4b61b0.
uint32_t function_004b61b0(Run &run, uint32_t object) {
    return run.get(run.get(object + 0x08));
}

// 0x4b7ab0. Stream +0x00 vtable, +0x0c CRT FILE pointer.
uint32_t function_004b7ab0(Run &run, uint32_t stream, uint32_t offset, uint32_t count, uint32_t destination) {
    if (count == 0) {
        return 0;
    }
    uint32_t previousStack = run.stackPointer;
    run.stackPointer = run.frame - 0x1c;
    uint32_t seek = run.call(0x4a7840, 0, {run.get(stream + 0x0c), offset, 0});
    while (seek != 0) {
        run.stackPointer = run.frame - 0x10;
        if (run.vcall(stream, 0x08, {}) == 0) {
            run.stackPointer = previousStack;
            return 0;
        }
        run.stackPointer = run.frame - 0x1c;
        seek = run.call(0x4a7840, 0, {run.get(stream + 0x0c), offset, 0});
    }
    run.stackPointer = run.frame - 0x20;
    uint32_t result = run.call(0x4a7260, 0, {destination, 1, count, run.get(stream + 0x0c)});
    while (result != count) {
        run.stackPointer = run.frame - 0x10;
        if (run.vcall(stream, 0x08, {}) == 0) {
            run.stackPointer = previousStack;
            return 0;
        }
        run.stackPointer = run.frame - 0x20;
        result = run.call(0x4a7260, 0, {destination, 1, count, run.get(stream + 0x0c)});
    }
    run.stackPointer = previousStack;
    return result;
}

// 0x4b61c0. Owner +0x0c file base offset and +0x18 stream.
uint32_t function_004b61c0(Run &run, uint32_t object) {
    uint32_t owner = run.get(object + 0x24);
    uint32_t mapped = run.get(owner + 0x20);
    if (mapped != 0) {
        uint32_t offset = run.get(object + 0x28);
        return offset - run.get(owner + 0x0c) + mapped;
    }
    uint32_t cache = run.get(object + 0x18);
    if (cache != 0) {
        return cache;
    }
    uint32_t count = run.get(object + 0x14);
    if (count == 0) {
        return 0;
    }
    uint32_t allocation = run.call(0x4f63ec, 0, {count});
    run.put(object + 0x18, allocation);
    if (allocation == 0) {
        return 0;
    }
    uint32_t offset = run.get(object + 0x28);
    owner = run.get(object + 0x24);
    count = run.get(object + 0x14);
    uint32_t stream = run.get(owner + 0x18);
    uint32_t previousFrame = run.frame;
    run.frame -= 0x14;
    uint32_t result = function_004b7ab0(run, stream, offset, count, allocation);
    run.frame = previousFrame;
    if (result != run.get(object + 0x14)) {
        run.call(0x4f6428, 0, {run.get(object + 0x18)});
        run.put(object + 0x18, 0);
    }
    return run.get(object + 0x18);
}

// 0x4b6230.
uint32_t function_004b6230(Run &run, uint32_t object) {
    uint32_t cache = run.get(object + 0x18);
    if (cache != 0) {
        run.call(0x4f6428, 0, {cache});
        run.put(object + 0x18, 0);
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b5ff0:
        return function_004b5ff0(run, receiver, arguments);
    case 0x4b6120:
        return function_004b6120(run, receiver);
    case 0x4b61b0:
        return function_004b61b0(run, receiver);
    case 0x4b61c0:
        return function_004b61c0(run, receiver);
    case 0x4b6230:
        return function_004b6230(run, receiver);
    case 0x4b7ab0:
        return function_004b7ab0(run, receiver, arguments[0], arguments[1], arguments[2]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_resource_data_canonical_entry, owned, body)
