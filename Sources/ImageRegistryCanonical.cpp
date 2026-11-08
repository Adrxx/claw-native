// Image and ANI registry operations recovered from the v1.0 packet.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4cdff0:
        return 2;
    case 0x4ce0d0:
        return 3;
    case 0x4ce250:
        return 1;
    case 0x4ce270:
        return 0;
    case 0x4ce2d0:
        return 0;
    case 0x4ce320:
        return 3;
    case 0x4ce480:
        return 4;
    case 0x4ce530:
        return 4;
    case 0x4ce5e0:
        return 1;
    case 0x4ce670:
        return 1;
    case 0x4ce770:
        return 3;
    case 0x4cf1f0:
        return 2;
    case 0x4cf230:
        return 1;
    case 0x4cfaa0:
        return 4;
    case 0x4cfba0:
        return 4;
    case 0x4cfca0:
        return 5;
    case 0x4cfdb0:
        return 5;
    case 0x4cfec0:
        return 4;
    case 0x4cfee0:
        return 4;
    case 0x4cff00:
        return 5;
    case 0x4cff20:
        return 5;
    case 0x4cff40:
        return 3;
    case 0x4d0120:
        return 3;
    case 0x4d02f0:
        return 1;
    case 0x4d0310:
        return 0;
    case 0x4d0380:
        return 1;
    case 0x4d2380:
        return 2;
    case 0x4d6070:
        return 3;
    case 0x4d61b0:
        return 3;
    case 0x4d6210:
        return 0;
    case 0x4d6260:
        return 1;
    case 0x4d6280:
        return 0;
    case 0x4d76e0:
        return 2;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// A call envelope uses the physical callee entry ESP from the assembly.
// Owned targets enter native bodies directly, including fixed vtable targets.
uint32_t invoke(Run &run, int32_t offset, uint32_t function, uint32_t receiver,
                std::initializer_list<uint32_t> arguments = {}) {
    uint32_t savedFrame = run.frame;
    uint32_t savedStack = run.stackPointer;
    uint32_t entry = run.automatic(offset);
    if (owned(function) < 0) {
        run.stackPointer = entry;
        uint32_t result = run.call(function, receiver, arguments);
        run.stackPointer = savedStack;
        return result;
    }
    uint32_t values[16]{};
    uint32_t index = 0;
    for (uint32_t argument : arguments) {
        values[index] = argument;
        run.put(entry + 0x4 + index * 4, argument);
        ++index;
    }
    run.frame = entry;
    run.stackPointer = 0;
    uint32_t result = body(run, function, receiver, values);
    run.frame = savedFrame;
    run.stackPointer = savedStack;
    return result;
}

uint32_t virtualCall(Run &run, int32_t offset, uint32_t object, uint32_t slot,
                     std::initializer_list<uint32_t> arguments = {}) {
    uint32_t function = run.get(run.get(object) + slot);
    return invoke(run, offset, function, object, arguments);
}

void path(Run &run, int32_t offset, uint32_t output, uint32_t prefix,
          uint32_t separator, uint32_t name) {
    if (prefix && run.get8(prefix)) {
        invoke(run, offset, 0x4a3920, 0, {output, 0x532c14, prefix, separator, name});
    } else {
        uint32_t count = 0;
        do {
            uint8_t byte = run.get8(name + count);
            run.put8(output + count, byte);
            ++count;
            if (!byte)
                break;
        } while (true);
    }
}

uint32_t number(Run &run, int32_t offset, uint32_t name) {
    while (true) {
        uint8_t byte = run.get8(name);
        if (!byte || (byte >= '0' && byte <= '9'))
            break;
        ++name;
    }
    return invoke(run, offset, 0x4a3ce0, 0, {name});
}

// 0x4d6280. Original v1.0 entry.
uint32_t function_004d6280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0xc, 0xffff);
    run.put(receiver + 0x0, 0x50becc);
    return 0;
}

// 0x4ce250. Original v1.0 entry.
uint32_t function_004ce250(Run &run, uint32_t receiver, const uint32_t *arguments) {
    invoke(run, -0x8, 0x4ce270, receiver);
    if (arguments[0] & 1)
        invoke(run, -0xc, 0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4d02f0. Original v1.0 entry.
uint32_t function_004d02f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    invoke(run, -0x8, 0x4d0310, receiver);
    if (arguments[0] & 1)
        invoke(run, -0xc, 0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4d6260. Original v1.0 entry.
uint32_t function_004d6260(Run &run, uint32_t receiver, const uint32_t *arguments) {
    invoke(run, -0x8, 0x4d6280, receiver);
    if (arguments[0] & 1)
        invoke(run, -0xc, 0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4ce270. Original v1.0 entry.
uint32_t function_004ce270(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x0, 0x513a58);
    invoke(run, -0x18, 0x4d6210, receiver);
    invoke(run, -0x18, 0x4f58de, receiver + 0x8);
    run.put(receiver + 0x0, 0x50becc);
    return 0;
}

// 0x4d0310. Original v1.0 entry.
uint32_t function_004d0310(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x0, 0x513cf8);
    invoke(run, -0x18, 0x4ce2d0, receiver);
    invoke(run, -0x18, 0x4f58de, receiver + 0x10);
    run.put(receiver + 0x4, 0xffffffff);
    run.put(receiver + 0x8, 0);
    run.put(receiver + 0xc, 0);
    run.put(receiver + 0x0, 0x50becc);
    return 0;
}

// 0x4ce2d0. Original v1.0 entry.
uint32_t function_004ce2d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t index = 0;
    while (s32(index) < s32(run.get(receiver + 0x18))) {
        uint32_t item = run.get(run.get(receiver + 0x14) + index * 4);
        if (item)
            virtualCall(run, -0x10, item, 0x4, {1});
        ++index;
    }
    invoke(run, -0x14, 0x4f5915, receiver + 0x10, {0, 0xffffffff});
    run.put(receiver + 0x64, 99999);
    run.put(receiver + 0x68, 0);
    return 0;
}

// 0x4d6210. Original v1.0 entry.
uint32_t function_004d6210(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t index = 0;
    while (s32(index) < s32(run.get(receiver + 0x10))) {
        uint32_t item = run.get(run.get(receiver + 0xc) + index * 4);
        if (item)
            virtualCall(run, -0x10, item, 0x4, {1});
        ++index;
    }
    uint32_t name = run.get(receiver + 0x1c);
    if (name) {
        invoke(run, -0x10, 0x4f6428, 0, {name});
        run.put(receiver + 0x1c, 0);
    }
    invoke(run, -0x14, 0x4f5915, receiver + 0x8, {0, 0xffffffff});
    return 0;
}

// 0x4d0380. Original v1.0 entry.
uint32_t function_004d0380(Run &run, uint32_t receiver, const uint32_t *arguments) {
    invoke(run, -0x14, 0x4b0a70, 0, {receiver + 0x24, arguments[0], 0x3f});
    run.put8(receiver + 0x63, 0);
    return 1;
}

// 0x4d76e0. Original v1.0 entry.
uint32_t function_004d76e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[1];
    run.put16(receiver + 0x4, run.get16(source));
    run.put(receiver + 0x8, uint32_t(int32_t(int16_t(run.get16(source + 0x2)))));
    run.put(receiver + 0xc, uint32_t(int32_t(int16_t(run.get16(source + 0x4)))));
    run.put(receiver + 0x10, uint32_t(int32_t(int16_t(run.get16(source + 0x6)))));
    run.put(receiver + 0x14, uint32_t(int32_t(int16_t(run.get16(source + 0x8)))));
    run.put(receiver + 0x18, uint32_t(int32_t(int16_t(run.get16(source + 0xa)))));
    run.put(receiver + 0x1c, uint32_t(int32_t(int16_t(run.get16(source + 0xc)))));
    run.put(receiver + 0x20, uint32_t(int32_t(int16_t(run.get16(source + 0xe)))));
    run.put(receiver + 0x24, uint32_t(int32_t(int16_t(run.get16(source + 0x10)))));
    uint16_t last = run.get16(source + 0x12);
    run.put(receiver + 0x2c, 0);
    run.put16(receiver + 0x28, last);
    run.put(0x543174, 0);
    if (run.get8(receiver + 0x4) & 2) {
        uint32_t length = 0;
        do {
            ++length;
        } while (run.get8(source + 0x14 + length - 1));
        run.put(0x543174, length);
        if (arguments[0]) {
            uint32_t output = run.automatic(0x8);
            run.put(output, 0);
            invoke(run, -0x14, 0x4f6286, arguments[0] + 0x10, {source + 0x14, output});
            run.put(receiver + 0x2c, run.get(output));
        }
    }
    return 1;
}

// 0x4d6070. Original v1.0 entry.
uint32_t function_004d6070(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t binary = arguments[1];
    uint32_t source = binary + 0x20;
    run.put(receiver + 0x4, arguments[2]);
    run.put(receiver + 0x4, run.get(binary + 0x8) | arguments[2]);
    uint32_t length = run.get(binary + 0x10);
    if (length) {
        uint32_t allocation = invoke(run, -0x18, 0x4f63ec, 0, {length + 2});
        run.put(receiver + 0x1c, allocation);
        uint32_t copied = 0;
        while (copied < run.get(binary + 0x10)) {
            uint32_t destination = run.get(receiver + 0x1c);
            uint8_t byte = run.get8(source);
            ++source;
            run.put8(destination + copied, byte);
            ++copied;
        }
        run.put8(run.get(receiver + 0x1c) + copied, 0);
    } else {
        run.put(receiver + 0x1c, 0);
    }
    uint32_t parsed = 0;
    run.put(run.automatic(0xc), 0);
    while (s32(parsed) < s32(run.get(binary + 0xc))) {
        uint32_t record = invoke(run, -0x18, 0x4f63ec, 0, {0x30});
        if (record) {
            run.put(record + 0x0, 0x513df8);
            run.put(record + 0xc, 0xffff);
        }
        uint32_t result = invoke(run, -0x1c, 0x4d76e0, record, {arguments[0], source});
        if (!result) {
            if (record)
                virtualCall(run, -0x18, record, 0x4, {1});
            uint32_t index = 0;
            while (s32(index) < s32(run.get(receiver + 0x10))) {
                uint32_t item = run.get(run.get(receiver + 0xc) + index * 4);
                if (item)
                    virtualCall(run, -0x18, item, 0x4, {1});
                ++index;
            }
            uint32_t name = run.get(receiver + 0x1c);
            if (name) {
                invoke(run, -0x18, 0x4f6428, 0, {name});
                run.put(receiver + 0x1c, 0);
            }
            invoke(run, -0x1c, 0x4f5915, receiver + 0x8, {0, 0xffffffff});
            return 0;
        }
        invoke(run, -0x1c, 0x4f582f, receiver + 0x8, {run.get(receiver + 0x10), record});
        source += run.get(0x543174) + 0x14;
        ++parsed;
        run.put(run.automatic(0xc), parsed);
    }
    return 1;
}

// 0x4d61b0. Original v1.0 entry.
uint32_t function_004d61b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t resource = arguments[1];
    if (invoke(run, -0xc, 0x4b61b0, resource) != 0x414e49)
        return 0;
    run.put(receiver + 0x4, arguments[2]);
    uint32_t binary = invoke(run, -0xc, 0x4b61c0, resource);
    if (!binary)
        return 0;
    uint32_t result = invoke(run, -0x18, 0x4d6070, receiver, {arguments[0], binary, 0});
    invoke(run, -0xc, 0x4b6230, resource);
    return result;
}

// 0x4d2380. Original v1.0 entry.
uint32_t function_004d2380(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t resource = arguments[0];
    uint32_t type = invoke(run, -0x10, 0x4b61b0, resource);
    uint32_t decoder;
    if (type == 0x424d50)
        decoder = 1;
    else if (type == 0x504358)
        decoder = 2;
    else if (type == 0x524944)
        decoder = 3;
    else if (type == 0x504944)
        decoder = 4;
    else
        return 0;
    uint32_t binary = invoke(run, -0x10, 0x4b61c0, resource);
    if (!binary)
        return 0;
    uint32_t result = virtualCall(run, -0x20, receiver, 0x28, {binary, decoder, run.get(resource + 0x14), arguments[1]});
    invoke(run, -0x10, 0x4b6230, resource);
    return result;
}

// 0x4cdff0. Original v1.0 entry.
uint32_t function_004cdff0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t sequence = invoke(run, -0x20, 0x4f63ec, 0, {0x20});
    if (!sequence)
        return 0;
    run.put(sequence + 0x0, 0x50becc);
    invoke(run, -0x1c, 0x4f58ab, sequence + 0x8);
    run.put(sequence + 0x0, 0x513a58);
    run.put(sequence + 0x4, 0);
    run.put(sequence + 0x1c, 0);
    uint32_t parent = run.get(run.get(receiver + 0xc) + 0x28);
    if (!invoke(run, -0x28, 0x4d61b0, sequence, {parent, arguments[1], 0})) {
        virtualCall(run, -0x20, sequence, 0x4, {1});
        return 0;
    }
    uint32_t slot = invoke(run, -0x20, 0x4f62a8, receiver + 0x10, {arguments[0]});
    run.put(slot, sequence);
    return sequence;
}

// 0x4ce320. Original v1.0 entry.
uint32_t function_004ce320(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[1];
    if (s32(index) < s32(run.get(receiver + 0x18)) && run.get(run.get(receiver + 0x14) + index * 4))
        return 0;
    uint32_t image = invoke(run, -0x18, 0x4f63ec, 0, {0x34});
    if (image) {
        uint32_t parent = run.get(receiver + 0xc);
        run.put(image + 0x4, index);
        run.put(image + 0x8, 0);
        run.put(image + 0xc, parent);
        run.put(image + 0x0, 0x513a70);
        run.put(image + 0x10, 0);
        run.put(image + 0x14, 0);
        run.put(image + 0x2c, 0);
        run.put(image + 0x30, 0);
    }
    if (!virtualCall(run, -0x1c, image, 0x2c, {arguments[0], arguments[2]})) {
        if (image)
            virtualCall(run, -0x18, image, 0x4, {1});
        return 0;
    }
    invoke(run, -0x1c, 0x4f582f, receiver + 0x10, {index, image});
    if (s32(index) < s32(run.get(receiver + 0x64)))
        run.put(receiver + 0x64, index);
    if (s32(index) > s32(run.get(receiver + 0x68)))
        run.put(receiver + 0x68, index);
    return image;
}

// 0x4ce480. Original v1.0 entry.
uint32_t function_004ce480(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[2];
    if (s32(index) < s32(run.get(receiver + 0x18)) && run.get(run.get(receiver + 0x14) + index * 4))
        return 0;
    uint32_t image = invoke(run, -0x18, 0x4f63ec, 0, {0x34});
    if (image) {
        uint32_t parent = run.get(receiver + 0xc);
        run.put(image + 0x4, index);
        run.put(image + 0x8, 0);
        run.put(image + 0xc, parent);
        run.put(image + 0x0, 0x513a70);
        run.put(image + 0x10, 0);
        run.put(image + 0x14, 0);
        run.put(image + 0x2c, 0);
        run.put(image + 0x30, 0);
    }
    if (!virtualCall(run, -0x24, image, 0x28, {arguments[0], arguments[1], arguments[3], 1})) {
        if (image)
            virtualCall(run, -0x18, image, 0x4, {1});
        return 0;
    }
    invoke(run, -0x1c, 0x4f582f, receiver + 0x10, {index, image});
    if (s32(index) < s32(run.get(receiver + 0x64)))
        run.put(receiver + 0x64, index);
    if (s32(index) > s32(run.get(receiver + 0x68)))
        run.put(receiver + 0x68, index);
    return image;
}

// 0x4ce530. Original v1.0 entry.
uint32_t function_004ce530(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[2];
    if (s32(index) < s32(run.get(receiver + 0x18)) && run.get(run.get(receiver + 0x14) + index * 4))
        return 0;
    uint32_t image = invoke(run, -0x18, 0x4f63ec, 0, {0x34});
    if (image) {
        uint32_t parent = run.get(receiver + 0xc);
        run.put(image + 0x4, index);
        run.put(image + 0x8, 0);
        run.put(image + 0xc, parent);
        run.put(image + 0x0, 0x513a70);
        run.put(image + 0x10, 0);
        run.put(image + 0x14, 0);
        run.put(image + 0x2c, 0);
        run.put(image + 0x30, 0);
    }
    if (!virtualCall(run, -0x20, image, 0x24, {arguments[0], arguments[1], arguments[3]})) {
        if (image)
            virtualCall(run, -0x18, image, 0x4, {1});
        return 0;
    }
    invoke(run, -0x1c, 0x4f582f, receiver + 0x10, {index, image});
    if (s32(index) < s32(run.get(receiver + 0x64)))
        run.put(receiver + 0x64, index);
    if (s32(index) > s32(run.get(receiver + 0x68)))
        run.put(receiver + 0x68, index);
    return image;
}

// 0x4ce770. Original v1.0 entry.
uint32_t function_004ce770(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[1];
    if (s32(index) < s32(run.get(receiver + 0x64)) || s32(index) > s32(run.get(receiver + 0x68)))
        return 0;
    uint32_t image = run.get(run.get(receiver + 0x14) + index * 4);
    if (!image)
        return 0;
    return virtualCall(run, -0xc, image, 0x34, {arguments[0], arguments[2]}) != 0;
}

// 0x4cf230. Original v1.0 entry.
uint32_t function_004cf230(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t output = run.automatic(-0x4);
    run.put(output, 0);
    invoke(run, -0x1c, 0x4f6286, receiver + 0x10, {arguments[0], output});
    uint32_t value = run.get(output);
    if (value) {
        invoke(run, -0x18, 0x4f5db6, receiver + 0x10, {arguments[0]});
        virtualCall(run, -0x18, value, 0x4, {1});
    }
    return 0;
}

// 0x4cf1f0. Original v1.0 entry.
uint32_t function_004cf1f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t directory = invoke(run, -0xc, 0x4b7540, arguments[0]);
    uint32_t found = invoke(run, -0xc, 0x4b68c0, directory, {arguments[1]});
    if (!found)
        return 0;
    return virtualCall(run, -0x14, receiver, 0x48, {found, 0x534938, 0x523728});
}

// 0x4cfaa0. Original v1.0 entry.
uint32_t function_004cfaa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t output = run.automatic(-0x14);
    uint32_t key = arguments[1];
    run.put(output, 0);
    invoke(run, -0x30, 0x4f6286, receiver + 0x10, {key, output});
    uint32_t group = run.get(output);
    if (!group) {
        group = invoke(run, -0x2c, 0x4f63ec, 0, {0x6c});
        if (group) {
            uint32_t type = run.get(receiver + 0x1c);
            uint32_t parent = run.get(receiver + 0xc);
            run.put(group + 0x0, 0x50e924);
            run.put(group + 0x4, type);
            run.put(group + 0x8, 0);
            run.put(group + 0xc, parent);
            invoke(run, -0x28, 0x4f58ab, group + 0x10);
            run.put(group + 0x0, 0x513cf8);
            run.put(group + 0x64, 99999);
            run.put(group + 0x68, 0);
        }
        run.put(output, group);
        if (!virtualCall(run, -0x2c, group, 0x24, {key})) {
            group = run.get(output);
            if (group)
                virtualCall(run, -0x2c, group, 0x4, {1});
            return 0;
        }
        group = run.get(output);
        uint32_t valueSlot = invoke(run, -0x2c, 0x4f62a8, receiver + 0x10, {key});
        run.put(valueSlot, group);
        group = run.get(output);
    }
    return virtualCall(run, -0x34, group, 0x38, {arguments[0], arguments[2], arguments[3]});
}

// 0x4cfba0. Original v1.0 entry.
uint32_t function_004cfba0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t output = run.automatic(-0x14);
    uint32_t key = arguments[1];
    run.put(output, 0);
    invoke(run, -0x30, 0x4f6286, receiver + 0x10, {key, output});
    uint32_t group = run.get(output);
    if (!group) {
        group = invoke(run, -0x2c, 0x4f63ec, 0, {0x6c});
        if (group) {
            uint32_t type = run.get(receiver + 0x1c);
            uint32_t parent = run.get(receiver + 0xc);
            run.put(group + 0x0, 0x50e924);
            run.put(group + 0x4, type);
            run.put(group + 0x8, 0);
            run.put(group + 0xc, parent);
            invoke(run, -0x28, 0x4f58ab, group + 0x10);
            run.put(group + 0x0, 0x513cf8);
            run.put(group + 0x64, 99999);
            run.put(group + 0x68, 0);
        }
        run.put(output, group);
        if (!virtualCall(run, -0x2c, group, 0x24, {key})) {
            group = run.get(output);
            if (group)
                virtualCall(run, -0x2c, group, 0x4, {1});
            return 0;
        }
        group = run.get(output);
        uint32_t valueSlot = invoke(run, -0x2c, 0x4f62a8, receiver + 0x10, {key});
        run.put(valueSlot, group);
        group = run.get(output);
    }
    return virtualCall(run, -0x34, group, 0x34, {arguments[0], arguments[2], arguments[3]});
}

// 0x4cfca0. Original v1.0 entry.
uint32_t function_004cfca0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t output = run.automatic(-0x14);
    uint32_t key = arguments[2];
    run.put(output, 0);
    invoke(run, -0x30, 0x4f6286, receiver + 0x10, {key, output});
    uint32_t group = run.get(output);
    if (!group) {
        group = invoke(run, -0x2c, 0x4f63ec, 0, {0x6c});
        if (group) {
            uint32_t type = run.get(receiver + 0x1c);
            uint32_t parent = run.get(receiver + 0xc);
            run.put(group + 0x0, 0x50e924);
            run.put(group + 0x4, type);
            run.put(group + 0x8, 0);
            run.put(group + 0xc, parent);
            invoke(run, -0x28, 0x4f58ab, group + 0x10);
            run.put(group + 0x0, 0x513cf8);
            run.put(group + 0x64, 99999);
            run.put(group + 0x68, 0);
        }
        run.put(output, group);
        if (!virtualCall(run, -0x2c, group, 0x24, {key})) {
            group = run.get(output);
            if (group)
                virtualCall(run, -0x2c, group, 0x4, {1});
            return 0;
        }
        group = run.get(output);
        uint32_t valueSlot = invoke(run, -0x2c, 0x4f62a8, receiver + 0x10, {key});
        run.put(valueSlot, group);
        group = run.get(output);
    }
    return virtualCall(run, -0x38, group, 0x30, {arguments[0], arguments[1], arguments[3], arguments[4]});
}

// 0x4cfdb0. Original v1.0 entry.
uint32_t function_004cfdb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t output = run.automatic(-0x14);
    uint32_t key = arguments[2];
    run.put(output, 0);
    invoke(run, -0x30, 0x4f6286, receiver + 0x10, {key, output});
    uint32_t group = run.get(output);
    if (!group) {
        group = invoke(run, -0x2c, 0x4f63ec, 0, {0x6c});
        if (group) {
            uint32_t type = run.get(receiver + 0x1c);
            uint32_t parent = run.get(receiver + 0xc);
            run.put(group + 0x0, 0x50e924);
            run.put(group + 0x4, type);
            run.put(group + 0x8, 0);
            run.put(group + 0xc, parent);
            invoke(run, -0x28, 0x4f58ab, group + 0x10);
            run.put(group + 0x0, 0x513cf8);
            run.put(group + 0x64, 99999);
            run.put(group + 0x68, 0);
        }
        run.put(output, group);
        if (!virtualCall(run, -0x2c, group, 0x24, {key})) {
            group = run.get(output);
            if (group)
                virtualCall(run, -0x2c, group, 0x4, {1});
            return 0;
        }
        group = run.get(output);
        uint32_t valueSlot = invoke(run, -0x2c, 0x4f62a8, receiver + 0x10, {key});
        run.put(valueSlot, group);
        group = run.get(output);
    }
    return virtualCall(run, -0x38, group, 0x2c, {arguments[0], arguments[1], arguments[3], arguments[4]});
}

// 0x4cfec0. Original v1.0 entry.
uint32_t function_004cfec0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    virtualCall(run, -0x10, arguments[1], 0x34, {arguments[0], arguments[2], arguments[3]});
    return 0;
}

// 0x4cfee0. Original v1.0 entry.
uint32_t function_004cfee0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    virtualCall(run, -0x10, arguments[1], 0x38, {arguments[0], arguments[2], arguments[3]});
    return 0;
}

// 0x4cff00. Original v1.0 entry.
uint32_t function_004cff00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    virtualCall(run, -0x14, arguments[2], 0x30, {arguments[0], arguments[1], arguments[3], arguments[4]});
    return 0;
}

// 0x4cff20. Original v1.0 entry.
uint32_t function_004cff20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    virtualCall(run, -0x14, arguments[2], 0x2c, {arguments[0], arguments[1], arguments[3], arguments[4]});
    return 0;
}

// 0x4ce0d0. Original v1.0 entry.
uint32_t function_004ce0d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t buffer = invoke(run, -0x18, 0x4f63ec, 0, {0x100});
    if (!buffer)
        return 0;
    run.put8(buffer, 0);
    uint32_t total = 0;
    uint32_t directory = arguments[0];
    uint32_t child = invoke(run, -0x20, 0x4b68e0, directory);
    while (child) {
        path(run, -0x34, buffer, arguments[1], arguments[2], run.get(child));
        total += invoke(run, -0x2c, 0x4ce0d0, receiver, {child, buffer, arguments[2]});
        child = invoke(run, -0x24, 0x4b6900, directory, {child});
    }
    uint32_t type = invoke(run, -0x20, 0x4b6920, directory);
    while (type) {
        uint32_t resource = invoke(run, -0x24, 0x4b6960, directory, {type});
        while (resource) {
            if (invoke(run, -0x20, 0x4b61b0, resource) == 0x414e49) {
                path(run, -0x34, buffer, arguments[1], arguments[2], run.get(resource));
                if (invoke(run, -0x28, 0x4cdff0, receiver, {buffer, resource}))
                    ++total;
            }
            resource = invoke(run, -0x24, 0x4b6980, directory, {resource});
        }
        type = invoke(run, -0x24, 0x4b6940, directory, {type});
    }
    invoke(run, -0x24, 0x4f6428, 0, {buffer});
    return total;
}

// 0x4ce5e0. Original v1.0 entry.
uint32_t function_004ce5e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t directory = arguments[0];
    uint32_t total = 0;
    uint32_t type = invoke(run, -0x14, 0x4b6920, directory);
    while (type) {
        uint32_t resource = invoke(run, -0x1c, 0x4b6960, directory, {type});
        while (resource) {
            uint32_t index = number(run, -0x1c, run.get(resource));
            if (virtualCall(run, -0x24, receiver, 0x38, {resource, index, 1}))
                ++total;
            resource = invoke(run, -0x1c, 0x4b6980, directory, {resource});
        }
        type = invoke(run, -0x1c, 0x4b6940, directory, {type});
    }
    return total;
}

// 0x4ce670. Original v1.0 entry.
uint32_t function_004ce670(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t previous = 0;
    uint32_t size = run.get(receiver + 0x18);
    if (s32(size) > 0) {
        uint32_t minimum = run.get(receiver + 0x64);
        for (uint32_t index = 0; s32(index) < s32(size); ++index) {
            uint32_t item = 0;
            if (s32(index) >= s32(minimum) && s32(index) <= s32(run.get(receiver + 0x68)))
                item = run.get(run.get(receiver + 0x14) + index * 4);
            if (item)
                ++previous;
        }
    }
    uint32_t total = 0;
    uint32_t directory = arguments[0];
    uint32_t type = invoke(run, -0x1c, 0x4b6920, directory);
    while (type) {
        uint32_t resource = invoke(run, -0x20, 0x4b6960, directory, {type});
        while (resource) {
            uint32_t format = invoke(run, -0x1c, 0x4b61b0, resource);
            if (format == 0x504358 || format == 0x424d50 || format == 0x524944 || format == 0x504944) {
                uint32_t index = number(run, -0x20, run.get(resource));
                if (!virtualCall(run, -0x28, receiver, 0x40, {resource, index, 1}))
                    return 0xffffffff;
                ++total;
            }
            resource = invoke(run, -0x20, 0x4b6980, directory, {resource});
        }
        type = invoke(run, -0x20, 0x4b6940, directory, {type});
    }
    if (s32(total) < s32(previous))
        return 0xffffffff;
    return total;
}

// 0x4cff40. Original v1.0 entry.
uint32_t function_004cff40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t buffer = invoke(run, -0x2c, 0x4f63ec, 0, {0x100});
    if (!buffer)
        return 0;
    uint32_t total = 0;
    run.put8(buffer, 0);
    uint32_t child = invoke(run, -0x28, 0x4b68e0, arguments[0]);
    while (child) {
        path(run, -0x3c, buffer, arguments[1], arguments[2], run.get(child));
        total += virtualCall(run, -0x34, receiver, 0x48, {child, buffer, arguments[2]});
        child = invoke(run, -0x2c, 0x4b6900, arguments[0], {child});
    }
    uint32_t prefix = arguments[1];
    if (prefix && run.get8(prefix)) {
        uint32_t output = run.automatic(0xc);
        run.put(output, 0);
        invoke(run, -0x30, 0x4f6286, receiver + 0x10, {prefix, output});
        uint32_t group = run.get(output);
        if (!group) {
            group = invoke(run, -0x2c, 0x4f63ec, 0, {0x6c});
            if (group) {
                uint32_t type = run.get(receiver + 0x1c);
                uint32_t parent = run.get(receiver + 0xc);
                run.put(group + 0x0, 0x50e924);
                run.put(group + 0x4, type);
                run.put(group + 0x8, 0);
                run.put(group + 0xc, parent);
                invoke(run, -0x28, 0x4f58ab, group + 0x10);
                run.put(group + 0x0, 0x513cf8);
                run.put(group + 0x64, 99999);
                run.put(group + 0x68, 0);
            }
            run.put(output, group);
            if (!virtualCall(run, -0x2c, group, 0x24, {prefix})) {
                group = run.get(output);
                if (group)
                    virtualCall(run, -0x2c, group, 0x4, {1});
                return 0;
            }
            group = run.get(output);
            uint32_t slot = invoke(run, -0x2c, 0x4f62a8, receiver + 0x10, {prefix});
            run.put(slot, group);
            group = run.get(output);
        }
        virtualCall(run, -0x2c, group, 0x28, {arguments[0]});
        if (run.get(run.get(output) + 0x18))
            ++total;
        else
            virtualCall(run, -0x2c, receiver, 0x54, {prefix});
    }
    invoke(run, -0x2c, 0x4f6428, 0, {buffer});
    return total;
}

// 0x4d0120. Original v1.0 entry.
uint32_t function_004d0120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t buffer = invoke(run, -0x20, 0x4f63ec, 0, {0x100});
    uint32_t directory = arguments[0];
    uint32_t total = 0;
    uint32_t child = invoke(run, -0x1c, 0x4b68e0, directory);
    while (child) {
        path(run, -0x30, buffer, arguments[1], arguments[2], run.get(child));
        uint32_t result = virtualCall(run, -0x28, receiver, 0x4c, {child, buffer, arguments[2]});
        if (s32(result) < 0) {
            invoke(run, -0x20, 0x4f6428, 0, {buffer});
            return 0xffffffff;
        }
        total += result;
        child = invoke(run, -0x20, 0x4b6900, directory, {child});
    }
    uint32_t prefix = arguments[1];
    if (prefix && run.get8(prefix)) {
        uint32_t output = run.automatic(0x4);
        run.put(output, 0);
        invoke(run, -0x24, 0x4f6286, receiver + 0x10, {prefix, output});
        uint32_t group = run.get(output);
        if (group) {
            uint32_t result = virtualCall(run, -0x20, group, 0x3c, {directory});
            if (result == 0xffffffff) {
                invoke(run, -0x20, 0x4f6428, 0, {buffer});
                return 0xffffffff;
            }
            if (s32(run.get(run.get(output) + 0x18)) > 0)
                ++total;
        }
    }
    invoke(run, -0x20, 0x4f6428, 0, {buffer});
    return total;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4cdff0:
        return function_004cdff0(run, receiver, arguments);
    case 0x4ce0d0:
        return function_004ce0d0(run, receiver, arguments);
    case 0x4ce250:
        return function_004ce250(run, receiver, arguments);
    case 0x4ce270:
        return function_004ce270(run, receiver, arguments);
    case 0x4ce2d0:
        return function_004ce2d0(run, receiver, arguments);
    case 0x4ce320:
        return function_004ce320(run, receiver, arguments);
    case 0x4ce480:
        return function_004ce480(run, receiver, arguments);
    case 0x4ce530:
        return function_004ce530(run, receiver, arguments);
    case 0x4ce5e0:
        return function_004ce5e0(run, receiver, arguments);
    case 0x4ce670:
        return function_004ce670(run, receiver, arguments);
    case 0x4ce770:
        return function_004ce770(run, receiver, arguments);
    case 0x4cf1f0:
        return function_004cf1f0(run, receiver, arguments);
    case 0x4cf230:
        return function_004cf230(run, receiver, arguments);
    case 0x4cfaa0:
        return function_004cfaa0(run, receiver, arguments);
    case 0x4cfba0:
        return function_004cfba0(run, receiver, arguments);
    case 0x4cfca0:
        return function_004cfca0(run, receiver, arguments);
    case 0x4cfdb0:
        return function_004cfdb0(run, receiver, arguments);
    case 0x4cfec0:
        return function_004cfec0(run, receiver, arguments);
    case 0x4cfee0:
        return function_004cfee0(run, receiver, arguments);
    case 0x4cff00:
        return function_004cff00(run, receiver, arguments);
    case 0x4cff20:
        return function_004cff20(run, receiver, arguments);
    case 0x4cff40:
        return function_004cff40(run, receiver, arguments);
    case 0x4d0120:
        return function_004d0120(run, receiver, arguments);
    case 0x4d02f0:
        return function_004d02f0(run, receiver, arguments);
    case 0x4d0310:
        return function_004d0310(run, receiver, arguments);
    case 0x4d0380:
        return function_004d0380(run, receiver, arguments);
    case 0x4d2380:
        return function_004d2380(run, receiver, arguments);
    case 0x4d6070:
        return function_004d6070(run, receiver, arguments);
    case 0x4d61b0:
        return function_004d61b0(run, receiver, arguments);
    case 0x4d6210:
        return function_004d6210(run, receiver, arguments);
    case 0x4d6260:
        return function_004d6260(run, receiver, arguments);
    case 0x4d6280:
        return function_004d6280(run, receiver, arguments);
    case 0x4d76e0:
        return function_004d76e0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_image_registry_canonical_entry, owned, body)
