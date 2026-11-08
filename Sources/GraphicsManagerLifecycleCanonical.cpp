// Original graphics-manager lifecycle, recovered from the original packet.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4bc220: return 6;
    case 0x4bc400:
    case 0x4bc5f0: return 1;
    case 0x4bcda0:
    case 0x4bcde0: return 2;
    case 0x4bd1c0: return 3;
    case 0x4b9540:
    case 0x4bc120:
    case 0x4bc1b0:
    case 0x4bc4b0:
    case 0x4bc610:
    case 0x4bc9d0:
    case 0x4bcc50:
    case 0x4bd0c0: return 0;
    default: return -1;
    }
}

// Owned calls with address-taking locals retain the original nested frame.
struct NestedFrame {
    Run &run;
    uint32_t saved;
    NestedFrame(Run &run, uint32_t bytes) : run(run), saved(run.frame) {
        run.frame -= bytes;
    }
    ~NestedFrame() {
        run.frame = saved;
    }
};

void report(Run &run, uint32_t file, uint32_t line, uint32_t error) {
    run.call(0x4bd260, 0, {file, line, error});
}

// 0x4b9540. Surface +0x94 data, +0x98 count; +0x08 COM surface,
// +0x78 borrowed flag, +0xb4 cached state.
uint32_t surfaceRelease(Run &run, uint32_t receiver) {
    uint32_t index = 0;
    if (run.get(receiver + 0x98) != 0) {
        do {
            uint32_t element = run.get(run.get(receiver + 0x94) + index * 4);
            if (element != 0) {
                run.call(run.get(run.get(element)), element, {1});
            }
            uint32_t count = run.get(receiver + 0x98);
            ++index;
            if (index >= count) {
                break;
            }
        } while (true);
    }
    run.call(0x4f5915, receiver + 0x90, {0, 0xffffffff});
    uint32_t surface = run.get(receiver + 0x08);
    if (surface != 0) {
        if ((run.get8(receiver + 0x78) & 1) == 0) {
            run.call(run.get(run.get(surface) + 0x08), 0, {surface});
        }
        run.put(receiver + 0x08, 0);
    }
    run.put(receiver + 0xb4, 0);
    return 0;
}

// 0x4bc120. Manager embedded lists +0x3b8/+0x3d4, array +0x3f0;
// +0x470 hardware, +0x474 depth, +0x878/+0x87c state, +0x880 error.
uint32_t managerConstruct(Run &run, uint32_t receiver) {
    run.call(0x4f5133, receiver + 0x3b8, {10});
    run.call(0x4f5133, receiver + 0x3d4, {10});
    run.call(0x4f54ea, receiver + 0x3f0);
    run.put(receiver, 0);
    run.put(receiver + 0x470, 0);
    run.put(receiver + 0x474, 0);
    run.put(receiver + 0x878, 0);
    run.put(receiver + 0x87c, 0);
    run.put(receiver + 0x880, 0);
    return receiver;
}

// 0x4bc4b0. Head +0x3bc; node next +0, payload +8.
uint32_t surfaceListRelease(Run &run, uint32_t receiver) {
    uint32_t node = run.get(receiver + 0x3bc);
    while (node != 0) {
        uint32_t next = run.get(node);
        uint32_t payload = run.get(node + 0x08);
        node = next;
        if (payload != 0) {
            run.call(run.get(run.get(payload)), payload, {1});
        }
    }
    run.call(0x4f5172, receiver + 0x3b8);
    return 0;
}

// 0x4bc9d0. Palette list head +0x3d8.
uint32_t paletteListRelease(Run &run, uint32_t receiver) {
    uint32_t node = run.get(receiver + 0x3d8);
    while (node != 0) {
        uint32_t next = run.get(node);
        uint32_t payload = run.get(node + 0x08);
        node = next;
        if (payload != 0) {
            run.call(0x4bb2a0, payload);
            run.call(0x4f6428, 0, {payload});
        }
    }
    run.call(0x4f5172, receiver + 0x3d4);
    return 0;
}

// 0x4bc400. Mode array data +0x3f4 and signed count +0x3f8.
uint32_t managerRelease(Run &run, uint32_t receiver, uint32_t restore) {
    if (restore != 0) {
        uint32_t interface = run.get(receiver);
        if (interface != 0) {
            run.call(run.get(run.get(interface) + 0x4c), 0, {interface});
        }
    }
    uint32_t index = 0;
    if (run.gets(receiver + 0x3f8) > 0) {
        do {
            run.call(0x4f6428, 0, {run.get(run.get(receiver + 0x3f4) + index * 4)});
            uint32_t count = run.get(receiver + 0x3f8);
            ++index;
            if (s32(index) >= s32(count)) {
                break;
            }
        } while (true);
    }
    run.call(0x4f5915, receiver + 0x3f0, {0, 0xffffffff});
    surfaceListRelease(run, receiver);
    paletteListRelease(run, receiver);
    run.put(0x541374, 0);
    uint32_t interface = run.get(receiver);
    if (interface != 0) {
        run.call(run.get(run.get(interface) + 0x08), 0, {interface});
        run.put(receiver, 0);
    }
    run.put(receiver + 0x470, 0);
    return 0;
}

// 0x4bc1b0.
uint32_t managerDestroy(Run &run, uint32_t receiver) {
    managerRelease(run, receiver, 1);
    run.call(0x4f551d, receiver + 0x3f0);
    run.call(0x4f5192, receiver + 0x3d4);
    run.call(0x4f5192, receiver + 0x3b8);
    return 0;
}

// 0x4bc610.
uint32_t surfaceDestroy(Run &run, uint32_t receiver) {
    run.put(receiver, 0x513588);
    surfaceRelease(run, receiver);
    run.call(0x4f551d, receiver + 0x90);
    return 0;
}

// 0x4bc5f0.
uint32_t surfaceDeletingDestroy(Run &run, uint32_t receiver, uint32_t flags) {
    surfaceDestroy(run, receiver);
    if ((flags & 1) != 0) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x4bcde0. Descriptors compare width +0xc, height +8, depth +0x54.
uint32_t modeGreater(Run &run, uint32_t first, uint32_t second) {
    uint32_t a = run.get(first + 0x0c);
    uint32_t b = run.get(second + 0x0c);
    if (a > b) {
        return 1;
    }
    if (a < b) {
        return 0;
    }
    a = run.get(first + 0x08);
    b = run.get(second + 0x08);
    if (a > b) {
        return 1;
    }
    if (a < b) {
        return 0;
    }
    return run.get(first + 0x54) > run.get(second + 0x54);
}

// 0x4bcda0. The global CArray receives a full copied descriptor.
uint32_t enumerationCallback(Run &run, uint32_t descriptor) {
    uint32_t copy = run.call(0x4f63ec, 0, {0x6c});
    for (uint32_t offset = 0; offset < 0x6c; offset += 4) {
        run.put(copy + offset, run.get(descriptor + offset));
    }
    run.call(0x4f582f, 0x541378, {run.get(0x541380), copy});
    return 1;
}

// 0x4bcc50. EnumDisplayModes invokes 0x4bcda0 physically through COM;
// transfer ownership of its descriptors, then selection-sort the pointer array.
uint32_t enumerateAndSortModes(Run &run, uint32_t receiver) {
    uint32_t index = 0;
    if (run.gets(receiver + 0x3f8) > 0) {
        do {
            run.call(0x4f6428, 0, {run.get(run.get(receiver + 0x3f4) + index * 4)});
            uint32_t count = run.get(receiver + 0x3f8);
            ++index;
            if (s32(index) >= s32(count)) {
                break;
            }
        } while (true);
    }
    run.call(0x4f5915, receiver + 0x3f0, {0, 0xffffffff});
    run.call(0x4f5915, 0x541378, {0, 0xffffffff});
    uint32_t interface = run.get(receiver);
    uint32_t error = run.call(run.get(run.get(interface) + 0x20), 0, {interface, 0, 0, 0, 0x4bcda0});
    if (error != 0) {
        report(run, 0x532524, 0x4a3, error);
    }
    index = 0;
    if (run.gets(0x541380) > 0) {
        do {
            uint32_t data = run.get(0x54137c);
            uint32_t count = run.get(receiver + 0x3f8);
            uint32_t descriptor = run.get(data + index * 4);
            run.call(0x4f582f, receiver + 0x3f0, {count, descriptor});
            uint32_t globalCount = run.get(0x541380);
            ++index;
            if (s32(index) >= s32(globalCount)) {
                break;
            }
        } while (true);
    }
    run.call(0x4f5915, 0x541378, {0, 0xffffffff});
    uint32_t count = run.get(receiver + 0x3f8);
    if (s32(count) > 1 && s32(count - 1) > 0) {
        for (uint32_t outer = 0; s32(outer) < s32(count - 1); ++outer) {
            for (uint32_t inner = outer + 1; s32(inner) < s32(count); ++inner) {
                uint32_t data = run.get(receiver + 0x3f4);
                uint32_t second = run.get(data + inner * 4);
                uint32_t first = run.get(data + outer * 4);
                if (modeGreater(run, first, second) != 0) {
                    run.put(run.get(receiver + 0x3f4) + outer * 4, second);
                    run.put(run.get(receiver + 0x3f4) + inner * 4, first);
                }
            }
        }
    }
    return 0;
}

// 0x4bd0c0. Descriptor masks +0x58/+0x5c/+0x60 produce
// first-set-bit globals and eight-minus-popcount globals.
uint32_t updatePixelMasks(Run &run, uint32_t receiver) {
    uint32_t descriptor = run.automatic(-0x6c);
    for (uint32_t offset = 0; offset < 0x6c; offset += 4) {
        run.put(descriptor + offset, 0);
    }
    uint32_t interface = run.get(receiver);
    run.put(descriptor, 0x6c);
    uint32_t error = run.call(run.get(run.get(interface) + 0x30), 0, {interface, descriptor});
    if (error != 0) {
        report(run, 0x532524, 0x7b8, error);
        return 0;
    }
    for (uint32_t channel = 0; channel < 3; ++channel) {
        uint32_t mask = run.get(descriptor + 0x58 + channel * 4);
        uint32_t first = 0xffffffff;
        uint32_t count = 0;
        for (uint32_t bit = 0; bit < 32; ++bit) {
            if ((mask & 1) == 1) {
                if (first == 0xffffffff) {
                    first = bit;
                }
                ++count;
            }
            mask >>= 1;
        }
        run.put(0x54135c + channel * 4, first);
        run.put(0x541368 + channel * 4, 8 - count);
    }
    return 1;
}

// 0x4bd1c0.
uint32_t setDisplayMode(Run &run, uint32_t receiver, uint32_t width, uint32_t height, uint32_t depth) {
    uint32_t interface = run.get(receiver);
    uint32_t error = run.call(run.get(run.get(interface) + 0x54), 0, {interface, width, height, depth});
    if (error != 0) {
        report(run, 0x532524, 0x829, error);
        if (run.get(receiver + 0x880) == 0) {
            run.put(receiver + 0x880, 0x3ec);
        }
        return error;
    }
    uint32_t updated;
    {
        NestedFrame frame(run, 0x0c);
        updated = updatePixelMasks(run, receiver);
    }
    if (updated == 0) {
        error = 0x80004005;
        if (run.get(receiver + 0x880) == 0) {
            run.put(receiver + 0x880, 0x3ed);
        }
    }
    return error;
}

// 0x4bc220. Arguments: HWND, GUID, width, height, depth, coop flags.
uint32_t managerInitialize(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x878, 0);
    run.put(receiver + 0x87c, 0);
    uint32_t interface = run.get(0x541398);
    if (interface == 0) {
        uint32_t error = run.call(0x4f4486, 0, {arguments[1], receiver, 0});
        if (error != 0) {
            report(run, 0x532524, 0x87, error);
            if (run.get(receiver + 0x880) == 0) {
                run.put(receiver + 0x880, 0x3e9);
            }
            return 0;
        }
    } else {
        run.put(receiver, interface);
    }
    interface = run.get(receiver);
    uint32_t error = run.call(run.get(run.get(interface) + 0x50), 0, {interface, arguments[0], arguments[5]});
    if (error != 0) {
        report(run, 0x532534, 0x119, error);
        if (run.get(receiver + 0x880) == 0) {
            run.put(receiver + 0x880, 0x3ea);
        }
        return 0;
    }
    for (uint32_t offset = 0; offset < 0x13c; offset += 4) {
        run.put(receiver + 0x04 + offset, 0);
    }
    for (uint32_t offset = 0; offset < 0x13c; offset += 4) {
        run.put(receiver + 0x140 + offset, 0);
    }
    interface = run.get(receiver);
    run.put(receiver + 0x04, 0x13c);
    run.put(receiver + 0x140, 0x13c);
    error = run.call(run.get(run.get(interface) + 0x2c), 0, {interface, receiver + 0x04, receiver + 0x140});
    if (error != 0) {
        report(run, 0x532524, 0xa4, error);
    }
    run.put(receiver + 0x470, run.get(receiver + 0x08) & 0x08000000);
    enumerateAndSortModes(run, receiver);
    uint32_t depth = arguments[4];
    if (s32(arguments[2]) > 0 && s32(arguments[3]) > 0) {
        {
            NestedFrame frame(run, 0x88);
            error = setDisplayMode(run, receiver, arguments[2], arguments[3], depth);
        }
        if (error != 0) {
            report(run, 0x532524, 0xb9, error);
            if (run.get(receiver + 0x880) == 0) {
                run.put(receiver + 0x880, 0x3ec);
            }
            return 0;
        }
        run.put(receiver + 0x474, depth);
    }
    if (depth == 0) {
        uint32_t descriptor = run.automatic(-0x6c);
        for (uint32_t offset = 0; offset < 0x6c; offset += 4) {
            run.put(descriptor + offset, 0);
        }
        interface = run.get(receiver);
        run.put(descriptor, 0x6c);
        error = run.call(run.get(run.get(interface) + 0x30), 0, {interface, descriptor});
        if (error == 0) {
            run.put(receiver + 0x474, run.get(descriptor + 0x54));
        }
    }
    run.put(0x541374, receiver);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b9540: return surfaceRelease(run, receiver);
    case 0x4bc120: return managerConstruct(run, receiver);
    case 0x4bc1b0: return managerDestroy(run, receiver);
    case 0x4bc220: return managerInitialize(run, receiver, arguments);
    case 0x4bc400: return managerRelease(run, receiver, arguments[0]);
    case 0x4bc4b0: return surfaceListRelease(run, receiver);
    case 0x4bc5f0: return surfaceDeletingDestroy(run, receiver, arguments[0]);
    case 0x4bc610: return surfaceDestroy(run, receiver);
    case 0x4bc9d0: return paletteListRelease(run, receiver);
    case 0x4bcc50: return enumerateAndSortModes(run, receiver);
    case 0x4bcda0: return enumerationCallback(run, arguments[0]);
    case 0x4bcde0: return modeGreater(run, arguments[0], arguments[1]);
    case 0x4bd0c0: return updatePixelMasks(run, receiver);
    case 0x4bd1c0: return setDisplayMode(run, receiver, arguments[0], arguments[1], arguments[2]);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_graphics_manager_lifecycle_canonical_entry, owned, body)
