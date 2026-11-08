// Original v1.0 world file runtime
//
// Canonical translation recovered from the packet disassembly.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4cace0:
        return 3;
    case 0x4cb200:
        return 1;
    case 0x4cb470:
        return 1;
    case 0x4cb5a0:
        return 1;
    case 0x4cb700:
        return 1;
    case 0x4cd660:
        return 3;
    case 0x4cdd10:
        return 1;
    case 0x4cde70:
        return 1;
    case 0x4d2210:
        return 1;
    case 0x4d5330:
        return 1;
    case 0x4d5840:
        return 1;
    case 0x4d5870:
        return 1;
    case 0x4d5c30:
        return 1;
    case 0x4cb670:
        return 2;
    case 0x4cb960:
        return 1;
    case 0x4cdca0:
        return 0;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// REP MOVSD followed by REP MOVSB, retaining forward alias behavior.
void copy(Run &run, uint32_t destination, uint32_t source, uint32_t count) {
    uint32_t words = count >> 2;
    for (uint32_t i = 0; i < words; ++i) {
        run.put(destination, run.get(source));
        destination += 0x04;
        source += 0x04;
    }
    for (uint32_t i = 0; i < (count & 3); ++i) {
        run.put8(destination, run.get8(source));
        ++destination;
        ++source;
    }
}

// Virtual calls may resolve to another owned entry. Its original body must
// never be delegated to the interpreter.
uint32_t invoke(Run &run, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments, uint32_t descent) {
    uint32_t savedFrame = run.frame;
    uint32_t savedStack = run.stackPointer;
    run.stackPointer = run.frame - descent;
    uint32_t result;
    if (owned(function) >= 0) {
        if (uint32_t(owned(function)) != arguments.size())
            run.fail(CLAW_FAULT_ABI, function);
        run.frame = run.stackPointer;
        result = body(run, function, receiver, arguments.begin());
    } else {
        result = run.call(function, receiver, arguments);
    }
    run.frame = savedFrame;
    run.stackPointer = savedStack;
    return result;
}

uint32_t virtualCall(Run &run, uint32_t receiver, uint32_t offset, std::initializer_list<uint32_t> arguments, uint32_t descent) {
    uint32_t function = run.get(run.get(receiver) + offset);
    return invoke(run, function, receiver, arguments, descent);
}

// 0x4cace0. World constructor: three embedded arrays and default settings.
uint32_t function_4cace0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver, 0x50e924);
    run.put(receiver + 0x04, arguments[1]);
    run.put(receiver + 0x08, arguments[2]);
    run.put(receiver + 0x0c, arguments[0]);
    run.call(0x4f58ab, receiver + 0x20, {});
    run.call(0x4f58ab, receiver + 0x34, {});
    run.call(0x4f58ab, receiver + 0x48, {});
    run.put(receiver + 0x64, 0x40);
    run.put(receiver + 0x68, 0x40);
    run.put(receiver + 0xb4, 0xfa);
    run.put(receiver + 0xc0, 0xfa);
    run.put(receiver + 0xb8, 0x3e8);
    run.put(receiver + 0xbc, 0x3e8);
    run.put(receiver, 0x513938);
    run.put(receiver + 0x10, 0x80000000);
    run.put(receiver + 0x5c, 0);
    run.put(receiver + 0x60, 0xffffffff);
    run.put(receiver + 0xac, 0);
    run.put(receiver + 0xb0, 0x1f4);
    run.put(receiver + 0xc4, 0x7d);
    run.put(receiver + 0xc8, 0x640);
    run.put(receiver + 0xcc, 0x4b0);
    run.put(receiver + 0xd0, 0xa00);
    run.put(receiver + 0xd4, 0x780);
    run.put(receiver + 0xd8, 0x300);
    run.put(receiver + 0xdc, 0x240);
    return receiver;
}

// 0x4cb200. Raw world loader; metadata remains in the supplied header.
uint32_t function_4cb200(Run &run, uint32_t receiver, const uint32_t *arguments) {
    virtualCall(run, receiver, 0x44, {}, 0x20);
    uint32_t header = arguments[0];
    uint32_t size = run.get(header);
    if (size > 0x5f4)
        return 0;
    uint32_t temporary = 0;
    uint32_t data = header;
    if (run.get8(header + 0x08) & 2) {
        uint32_t capacity = run.get(header + 0x2e8) + size + 0x20;
        temporary = run.call(0x4f63ec, 0, {capacity + 0x20});
        if (!temporary)
            return 0;
        data = invoke(run, 0x4cd660, receiver, {header, temporary, capacity}, 0x2c);
        if (!data) {
            run.call(0x4f6428, 0, {temporary});
            return 0;
        }
    }
    uint32_t length = 0;
    do {
        ++length;
    } while (run.get8(header + 0x10 + length - 1) != 0);
    copy(run, receiver + 0x6c, header + 0x10, length);
    run.put(receiver + 0x08, run.get(header + 0x08));
    run.put(receiver + 0xac, run.get(header + 0x2ec));
    uint32_t planeHeader = data + run.get(header + 0x2e0);
    bool success = true;
    for (uint32_t i = 0; i < run.get(header + 0x2dc); ++i) {
        uint32_t plane = run.call(0x4cb7b0, receiver, {planeHeader, data, receiver + 0x10});
        if (!plane) {
            success = false;
            break;
        }
        planeHeader += 0xa0;
    }
    if (success && run.get(header + 0x2e4)) {
        uint32_t table = data + run.get(header + 0x2e4);
        uint32_t descriptor = table + 0x20;
        if (!descriptor || !table) {
            success = false;
        } else {
            uint32_t accepted = 0;
            for (uint32_t i = 0; i < run.get(table + 0x08); ++i) {
                uint32_t tile = invoke(run, 0x4cb700, receiver, {descriptor}, 0x24);
                if (!tile) {
                    success = false;
                    break;
                }
                ++accepted;
                descriptor += virtualCall(run, tile, 0x24, {}, 0x20);
                run.call(0x4f582f, receiver + 0x48, {i, tile});
            }
            if (s32(accepted) < 0)
                success = false;
        }
    }
    if (success) {
        uint32_t plane = run.get(receiver + 0x5c);
        double y = double(s32(run.get(header + 0x2d4)));
        double x = double(s32(run.get(header + 0x2d0)));
        if (!(run.get8(plane + 0x08) & 1)) {
            x *= double(run.getf(plane + 0x18));
            y *= double(run.getf(plane + 0x1c));
        }
        run.putf(plane + 0x10, float(x));
        run.putf(plane + 0x14, float(y));
        run.call(0x4d0a60, plane, {});
        plane = run.get(receiver + 0x5c);
        uint32_t cameraX = run.get(plane + 0x84);
        uint32_t cameraY = run.get(plane + 0x88);
        for (uint32_t i = 0; s32(i) < s32(run.get(receiver + 0x3c)); ++i) {
            if (i == run.get(receiver + 0x60))
                continue;
            uint32_t other = run.get(run.get(receiver + 0x38) + i * 4);
            x = double(s32(cameraX));
            y = double(s32(cameraY));
            if (!(run.get8(other + 0x08) & 1)) {
                x *= double(run.getf(other + 0x18));
                y *= double(run.getf(other + 0x1c));
            }
            run.putf(other + 0x10, float(x));
            run.putf(other + 0x14, float(y));
            run.call(0x4d0a60, other, {});
        }
    }
    if (temporary)
        run.call(0x4f6428, 0, {temporary});
    return success ? 1 : 0;
}

// 0x4cb470. Stack-backed MFC file transport and virtual parsing.
uint32_t function_4cb470(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t file = run.automatic(-0x1c);
    invoke(run, 0x4f72c9, file, {}, 0x28);
    uint32_t opened = invoke(run, 0x4f7448, file, {arguments[0], 0, 0}, 0x34);
    if (!opened) {
        invoke(run, 0x4f7369, file, {}, 0x28);
        return 0;
    }
    uint32_t length = invoke(run, 0x4f774d, file, {}, 0x28);
    uint32_t buffer = run.call(0x4f63ec, 0, {length});
    if (!buffer) {
        invoke(run, 0x4f7369, file, {}, 0x28);
        return 0;
    }
    length = invoke(run, 0x4f774d, file, {}, 0x28);
    invoke(run, 0x4f7570, file, {buffer, length}, 0x30);
    uint32_t parsed = virtualCall(run, receiver, 0x38, {buffer}, 0x2c);
    run.call(0x4f6428, 0, {buffer});
    invoke(run, 0x4f7369, file, {}, 0x28);
    return parsed ? 1 : 0;
}

// 0x4cb5a0. Resource lock, virtual parser, unlock.
uint32_t function_4cb5a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t resource = arguments[0];
    uint32_t data = run.call(0x4b61c0, resource, {});
    if (!data)
        return 0;
    uint32_t parsed = virtualCall(run, receiver, 0x38, {data}, 0x10);
    run.call(0x4b6230, resource, {});
    return parsed ? 1 : 0;
}

// 0x4cb700. Descriptor factory; allocation-null still faults like the original.
uint32_t function_4cb700(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t input = arguments[0];
    if (!input)
        return 0;
    uint32_t kind = run.get(input);
    uint32_t size;
    uint32_t vtable;
    if (kind == 1) {
        size = 0x10;
        vtable = 0x513980;
    } else if (kind == 2) {
        size = 0x24;
        vtable = 0x5139c8;
    } else if (kind == 3) {
        size = 0x18;
        vtable = 0x513a10;
    } else {
        return 0;
    }
    uint32_t tile = run.call(0x4f63ec, 0, {size});
    if (tile) {
        run.put(tile, vtable);
        run.put(tile + 0x04, 0);
        if (kind == 3)
            run.put(tile + 0x14, 0);
    }
    uint32_t parsed = virtualCall(run, tile, 0x14, {input}, 0x14);
    if (!parsed) {
        if (tile)
            virtualCall(run, tile, 0x04, {1}, 0x14);
        return 0;
    }
    return tile;
}

// 0x4cd660. Copy header, decode into the body and require exact output length.
uint32_t function_4cd660(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t source = arguments[0];
    uint32_t destination = arguments[1];
    uint32_t capacity = arguments[2];
    if (!source || !destination)
        return 0;
    uint32_t headerSize = run.get(source);
    if (headerSize > 0x5f4)
        return 0;
    if (!(run.get8(source + 0x08) & 2))
        return 0;
    uint32_t decoded = run.get(source + 0x2e8);
    if (!decoded)
        return 0;
    if (decoded > capacity + headerSize)
        return 0;
    run.put(run.automatic(0x08), destination);
    copy(run, destination, source, headerSize);
    headerSize = run.get(source);
    decoded = run.get(source + 0x2e8);
    uint32_t outputCount = run.automatic(0x04);
    run.put(outputCount, capacity - headerSize);
    uint32_t status = invoke(run, 0x4d5fe0, 0, {destination + headerSize, outputCount, source + headerSize, decoded}, 0x24);
    if (status)
        return 0;
    uint32_t actual = run.get(outputCount);
    decoded = run.get(source + 0x2e8);
    destination = run.get(run.automatic(0x08));
    return actual == decoded ? destination : 0;
}

// 0x4cdd10. Deleting destructor wrapper.
uint32_t function_4cdd10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x4cdd30, receiver, {});
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4cde70. Deleting destructor wrapper.
uint32_t function_4cde70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x4cde90, receiver, {});
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4d2210. Deleting destructor wrapper.
uint32_t function_4d2210(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x4d2230, receiver, {});
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4d5330. Deleting destructor wrapper.
uint32_t function_4d5330(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x423f00, receiver, {});
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4d5840. Three sequential descriptor field copies.
uint32_t function_4d5840(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[0];
    run.put(receiver + 0x04, run.get(source + 0x08));
    run.put(receiver + 0x08, run.get(source + 0x0c));
    run.put(receiver + 0x0c, run.get(source + 0x10));
    return 1;
}

// 0x4d5870. Dimensions, height shift count, allocation and payload copy.
uint32_t function_4d5870(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[0];
    uint32_t width = run.get(source + 0x08);
    run.put(receiver + 0x04, width);
    uint32_t height = run.get(source + 0x0c);
    run.put(receiver + 0x08, height);
    run.put(receiver + 0x0c, 0);
    uint32_t count = width * height;
    run.put(receiver + 0x10, count);
    while (s32(height) > 1) {
        uint32_t shift = run.get(receiver + 0x0c);
        height = uint32_t(s32(height) >> 1);
        run.put(receiver + 0x0c, shift + 1);
    }
    if ((1u << (run.get(receiver + 0x0c) & 0x1f)) != width)
        return 0;
    uint32_t bytes = run.call(0x4f63ec, 0, {count});
    run.put(receiver + 0x14, bytes);
    if (!bytes)
        return 0;
    count = run.get(receiver + 0x10);
    copy(run, bytes, source + 0x10, count);
    return 1;
}

// 0x4d5c30. Eight sequential descriptor field copies.
uint32_t function_4d5c30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[0];
    run.put(receiver + 0x04, run.get(source + 0x08));
    run.put(receiver + 0x08, run.get(source + 0x0c));
    run.put(receiver + 0x0c, run.get(source + 0x10));
    run.put(receiver + 0x10, run.get(source + 0x14));
    run.put(receiver + 0x14, run.get(source + 0x18));
    run.put(receiver + 0x18, run.get(source + 0x1c));
    run.put(receiver + 0x1c, run.get(source + 0x20));
    run.put(receiver + 0x20, run.get(source + 0x24));
    return 1;
}

// 0x4cb670. Inclusive local rectangle propagated through a live plane table.
uint32_t function_4cb670(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t width = arguments[0];
    if (s32(width) <= 0)
        return 0;
    uint32_t height = arguments[1];
    if (s32(height) <= 0)
        return 0;
    uint32_t rectangle = run.automatic(-0x10);
    run.put(receiver + 0x10, 0);
    run.put(rectangle, 0);
    run.put(rectangle + 0x0c, height - 1);
    run.put(receiver + 0x14, 0);
    run.put(rectangle + 0x04, 0);
    run.put(rectangle + 0x08, width - 1);
    run.put(receiver + 0x18, width - 1);
    run.put(receiver + 0x1c, height - 1);
    for (uint32_t i = 0; s32(i) < s32(run.get(receiver + 0x3c)); ++i) {
        uint32_t plane = run.get(run.get(receiver + 0x38) + i * 4);
        invoke(run, 0x4d0c50, plane, {rectangle}, 0x24);
    }
    return 1;
}

// 0x4cb960. Supplied rectangle token and sequential copies preserve aliases.
uint32_t function_4cb960(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t rectangle = arguments[0];
    run.put(receiver + 0x10, run.get(rectangle));
    run.put(receiver + 0x14, run.get(rectangle + 0x04));
    run.put(receiver + 0x18, run.get(rectangle + 0x08));
    run.put(receiver + 0x1c, run.get(rectangle + 0x0c));
    for (uint32_t i = 0; s32(i) < s32(run.get(receiver + 0x3c)); ++i) {
        uint32_t plane = run.get(run.get(receiver + 0x38) + i * 4);
        invoke(run, 0x4d0c50, plane, {rectangle}, 0x14);
    }
    return 0;
}

// 0x4cdca0. Selected-plane tail target is outside this family.
uint32_t function_4cdca0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t plane = run.get(receiver + 0x5c);
    if (plane)
        return run.call(0x4d2050, plane, {});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4cace0:
        return function_4cace0(run, receiver, arguments);
    case 0x4cb200:
        return function_4cb200(run, receiver, arguments);
    case 0x4cb470:
        return function_4cb470(run, receiver, arguments);
    case 0x4cb5a0:
        return function_4cb5a0(run, receiver, arguments);
    case 0x4cb700:
        return function_4cb700(run, receiver, arguments);
    case 0x4cd660:
        return function_4cd660(run, receiver, arguments);
    case 0x4cdd10:
        return function_4cdd10(run, receiver, arguments);
    case 0x4cde70:
        return function_4cde70(run, receiver, arguments);
    case 0x4d2210:
        return function_4d2210(run, receiver, arguments);
    case 0x4d5330:
        return function_4d5330(run, receiver, arguments);
    case 0x4d5840:
        return function_4d5840(run, receiver, arguments);
    case 0x4d5870:
        return function_4d5870(run, receiver, arguments);
    case 0x4d5c30:
        return function_4d5c30(run, receiver, arguments);
    case 0x4cb670:
        return function_4cb670(run, receiver, arguments);
    case 0x4cb960:
        return function_4cb960(run, receiver, arguments);
    case 0x4cdca0:
        return function_4cdca0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_world_file_canonical_entry, owned, body)
