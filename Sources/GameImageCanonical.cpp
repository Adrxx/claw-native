// Original v1.0 raw game image runtime
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
    case 0x4b9180:
        return 5;
    case 0x4b9380:
        return 1;
    case 0x4b9730:
        return 1;
    case 0x4b9990:
        return 1;
    case 0x4bb0e0:
        return 0;
    case 0x4bc490:
        return 1;
    case 0x4bc520:
        return 5;
    case 0x4bf310:
        return 5;
    case 0x4bf9c0:
        return 6;
    case 0x4bfbf0:
        return 0;
    case 0x4bfc50:
        return 3;
    case 0x4c6130:
        return 2;
    case 0x4ce3d0:
        return 3;
    case 0x4d22f0:
        return 2;
    case 0x4d2410:
        return 4;
    case 0x4d25e0:
        return 2;
    case 0x4d2890:
        return 2;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// Retain the original nested entry frame for guest-addressed automatic objects.
uint32_t invoke(Run &run, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> args, int32_t offset) {
    uint32_t frame = run.frame;
    run.frame += uint32_t(offset);
    uint32_t result;
    if (owned(function) >= 0)
        result = body(run, function, receiver, args.begin());
    else
        result = run.call(function, receiver, args);
    run.frame = frame;
    return result;
}

// 0x4b9180. Surface descriptor at +0x0c, display format +0x474.
uint32_t function_4b9180(Run &run, uint32_t receiver, const uint32_t *a) {
    for (uint32_t i = 0x0c; i < 0x78; i += 4)
        run.put(receiver + i, 0);
    run.put(receiver + 0x74, a[4]);
    run.put(receiver + 0x14, a[2]);
    run.put(receiver + 0x18, a[1]);
    run.put(receiver + 0x0c, 0x6c);
    run.put(receiver + 0x10, 7);
    if (a[3] && a[3] != run.get(a[0] + 0x474)) {
        run.put(receiver + 0x10, 0x1007);
        run.put(receiver + 0x54, 0x20);
        run.put(receiver + 0x60, a[3]);
    }
    return invoke(run, run.get(run.get(receiver) + 0x20), receiver, {a[0]}, -0x10);
}

// 0x4b9380. +0x08 COM surface; +0xa4 format, +0xa8 row bytes, +0xac pixel bytes.
uint32_t function_4b9380(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t interface = run.get(a[0]);
    if (!interface)
        return 0;
    uint32_t result = run.call(run.get(run.get(interface) + 0x18), 0, {interface, receiver + 0x0c, receiver + 0x08, 0});
    if (result) {
        run.call(0x4bd260, 0, {0x5324dc, 0xd2, result});
        return 0;
    }
    for (uint32_t i = 0x0c; i < 0x78; i += 4)
        run.put(receiver + i, 0);
    interface = run.get(receiver + 0x08);
    run.put(receiver + 0x0c, 0x6c);
    result = run.call(run.get(run.get(interface) + 0x58), 0, {interface, receiver + 0x0c});
    if (result)
        run.call(0x4bd260, 0, {0x5324dc, 0xe1, result});
    uint32_t format = run.get(receiver + 0x60);
    run.put(receiver + 0xb8, 0);
    run.put(receiver + 0xa4, format);
    uint32_t width = run.get(receiver + 0x18);
    uint32_t bytes = format == 0x10 ? 2 : format == 0x18 ? 3 : format == 0x20 ? 4 : 1;
    run.put(receiver + 0xa8, width * bytes);
    run.put(receiver + 0xac, bytes);
    uint32_t pitch = run.get(receiver + 0x1c) / run.get(receiver + 0xac);
    run.put(receiver + 0x7c, 0);
    run.put(receiver + 0x80, 0);
    run.put(receiver + 0x84, width);
    run.put(receiver + 0xb0, pitch);
    uint32_t height = run.get(receiver + 0x14);
    run.put(receiver + 0x88, height);
    run.put(receiver + 0x8c, height * run.get(receiver + 0xa8));
    return 1;
}

// 0x4b9730. Lock descriptor +0x0c and pixel pointer +0x30.
uint32_t function_4b9730(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t interface = run.get(receiver + 0x08);
    uint32_t result = run.call(run.get(run.get(interface) + 0x64), 0, {interface, a[0], receiver + 0x0c, 1, 0});
    if (!result)
        return run.get(receiver + 0x30);
    if (result == 0x887601c2) {
        if (!invoke(run, run.get(run.get(receiver) + 0x1c), receiver, {}, -0x0c))
            return 0;
        interface = run.get(receiver + 0x08);
        result = run.call(run.get(run.get(interface) + 0x64), 0, {interface, 0, receiver + 0x0c, 1, 0});
        if (!result)
            return run.get(receiver + 0x30);
        run.call(0x4bd260, 0, {0x5324dc, 0x1e9, result});
    } else {
        run.call(0x4bd260, 0, {0x5324dc, 0x1ef, result});
    }
    return 0;
}

// 0x4b9990. +0xb8 records whether the key is enabled.
uint32_t function_4b9990(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t pair = run.automatic(-8);
    run.put(pair, a[0]);
    run.put(pair + 0x04, a[0]);
    run.put(receiver + 0xb8, a[0] == 0xffffffff ? 0 : 1);
    run.call(0x4b9950, receiver, {8, pair});
    return 0;
}

// 0x4bb0e0. Unlock is a physical void effect even for a nonzero HRESULT.
uint32_t function_4bb0e0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t interface = run.get(receiver + 0x08);
    run.call(run.get(run.get(interface) + 0x80), 0, {interface, 0});
    return 0;
}

// 0x4bc490. Display list +0x3b8, object list-node link +0x04.
uint32_t function_4bc490(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t node = run.call(0x4f51c5, receiver + 0x3b8, {a[0]});
    run.put(a[0] + 0x04, node);
    return 0;
}

// 0x4bc520. Construct, decode, then attach a surface to its display list.
uint32_t function_4bc520(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t surface = run.call(0x4f63ec, 0, {0xbc});
    if (surface) {
        run.call(0x4f54ea, surface + 0x90);
        run.put(surface + 0x08, 0);
        run.put(surface + 0x04, 0);
        run.put(surface + 0x78, 0);
        run.put(surface + 0xa4, 0);
        run.put(surface + 0xb4, 0);
        run.put(surface, 0x513690);
    }
    uint32_t method = run.get(run.get(surface) + 0x24);
    if (!invoke(run, method, surface, {receiver, a[0], a[1], a[2], a[3], a[4]}, -0x38)) {
        if (surface)
            invoke(run, run.get(run.get(surface)), surface, {1}, -0x24);
        return 0;
    }
    invoke(run, 0x4bc490, receiver, {surface}, -0x24);
    return surface;
}

// 0x4bf310. Decode PID image data and optionally convert its indexed palette.
uint32_t function_4bf310(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t flags = run.get(a[1] + 0x04);
    uint32_t width = run.get(a[1] + 0x08);
    uint32_t height = run.get(a[1] + 0x0c);
    if (width & 3)
        return 0;
    uint32_t createFlags = a[3];
    if (flags & 4)
        createFlags = (createFlags & 0xffffbfff) | 0x800;
    else if (flags & 2)
        createFlags &= 0xfffff7ff;
    uint32_t active = run.get(a[0] + 0x878);
    uint32_t palette = active ? a[0] + 0x478 : 0;
    uint32_t format = run.get(a[0] + 0x474);
    bool convert = format != 8;
    if (flags & 0x80) {
        if (a[2] <= 0x300)
            return 0;
        uint32_t source = a[1] + a[2] - 0x300;
        for (uint32_t i = 0; i < 0x100; ++i) {
            run.put8(0x5427b0 + i * 4, run.get8(source++));
            run.put8(0x5427b1 + i * 4, run.get8(source++));
            run.put8(0x5427b2 + i * 4, run.get8(source++));
            run.put8(0x5427b3 + i * 4, 0);
        }
        palette = 0x5427b0;
    } else if (convert) {
        if (!palette)
            return 0;
        if (convert && format == 8 && !active)
            return 0;
    }
    if (!invoke(run, 0x4b9180, receiver, {a[0], width, height, 0, createFlags}, -0x38))
        return 0;
    uint32_t buffer = 0;
    if (convert) {
        buffer = run.call(0x4f63ec, 0, {height * width});
        if (!buffer)
            return 0;
        if (!run.call(0x4bef50, receiver, {buffer, a[1] + 0x20, width, height})) {
            run.call(0x4f6428, 0, {buffer});
            return 0;
        }
    } else if (!run.call(0x4babe0, receiver, {a[1] + 0x20})) {
        return 0;
    }
    if (convert && !run.call(0x4b9e90, receiver, {buffer, 8, palette, 1})) {
        run.call(0x4f6428, 0, {buffer});
        return 0;
    }
    if (buffer)
        run.call(0x4f6428, 0, {buffer});
    if (flags & 1)
        invoke(run, 0x4b9990, receiver, {a[4]}, -0x28);
    return 1;
}

// 0x4bf9c0. Dispatch BMP, PCX, or PID decode.
uint32_t function_4bf9c0(Run &run, uint32_t receiver, const uint32_t *a) {
    if (!a[3])
        return 0;
    uint32_t result;
    if (a[2] == 1 || a[2] == 2)
        result = run.call(a[2] == 1 ? 0x4bdad0 : 0x4be810, receiver, {a[0], a[1], a[3], a[4] | 0x40});
    else if (a[2] == 4)
        result = invoke(run, 0x4bf310, receiver, {a[0], a[1], a[3], a[4] | 0x40, a[5]}, -0x24);
    else
        return 0;
    if (!result)
        return 0;
    if (a[5] != 0xffffffff && a[2] != 4)
        invoke(run, 0x4b9990, receiver, {a[5]}, -0x14);
    return 1;
}

// 0x4bfbf0. Light image constructor, preserving dimensions +0x04/+0x08.
uint32_t function_4bfbf0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x14, 1);
    run.put(receiver + 0x18, 0x80);
    run.put(receiver, 0);
    run.put(receiver + 0x20, 0);
    run.put8(receiver + 0x24, 1);
    return receiver;
}

// 0x4bfc50. Light-image encoded data +0x0c, size +0x10, palette +0x20.
uint32_t function_4bfc50(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t size = a[1] - 0x20;
    uint32_t format = a[2] & 0xff;
    run.put(receiver + 0x10, size);
    if (format != 8 && format != 0x10)
        return 0;
    if ((run.get8(a[0] + 0x04) & 0x80) && format == 0x10) {
        run.put(receiver + 0x10, size - 0x300);
        uint32_t old = run.get(receiver + 0x20);
        if (old)
            run.call(0x4f6428, 0, {old});
        uint32_t palette = run.call(0x4f63ec, 0, {0x400});
        run.put(receiver + 0x20, palette);
        for (uint32_t i = 0; i < 0x100; ++i) {
            uint32_t source = a[0] + run.get(receiver + 0x10) + 0x20 + i * 3;
            uint32_t destination = run.get(receiver + 0x20) + i * 4;
            run.put8(destination, run.get8(source));
            source = a[0] + run.get(receiver + 0x10) + 0x21 + i * 3;
            destination = run.get(receiver + 0x20) + i * 4 + 1;
            run.put8(destination, run.get8(source));
            source = a[0] + run.get(receiver + 0x10) + 0x22 + i * 3;
            destination = run.get(receiver + 0x20) + i * 4 + 2;
            run.put8(destination, run.get8(source));
        }
        run.put8(receiver + 0x24, 2);
    } else {
        run.put8(receiver + 0x24, 1);
    }
    uint32_t width = run.get(a[0] + 0x08);
    uint32_t height = run.get(a[0] + 0x0c);
    run.put(receiver + 0x04, width);
    uint32_t old = run.get(receiver + 0x0c);
    run.put(receiver + 0x08, height);
    if (old)
        run.call(0x4f6428, 0, {old});
    uint32_t destination = run.call(0x4f63ec, 0, {run.get(receiver + 0x10)});
    size = run.get(receiver + 0x10);
    run.put(receiver + 0x0c, destination);
    uint32_t source = a[0] + 0x20;
    for (uint32_t i = 0; i < (size >> 2); ++i) {
        run.put(destination, run.get(source));
        source += 4;
        destination += 4;
    }
    for (uint32_t i = 0; i < (size & 3); ++i)
        run.put8(destination++, run.get8(source++));
    if (run.get8(receiver + 0x24) == 2) {
        uint32_t converted = run.call(0x4bfd80, receiver, {run.get(receiver + 0x0c)});
        run.call(0x4f6428, 0, {run.get(receiver + 0x0c)});
        uint32_t palette = run.get(receiver + 0x20);
        run.put(receiver + 0x0c, converted);
        run.call(0x4f6428, 0, {palette});
        run.put(receiver + 0x20, 0);
    }
    return 1;
}

// 0x4c6130. Mode +0x14, mode parameter +0x1c.
uint32_t function_4c6130(Run &run, uint32_t receiver, const uint32_t *a) {
    run.put(receiver + 0x14, a[0]);
    uint32_t value = a[1];
    if (!value) {
        uint32_t global;
        switch (a[0]) {
        case 2:
            global = 0x5430b0;
            break;
        case 4:
            global = 0x5430b4;
            break;
        case 8:
            global = 0x5430b8;
            break;
        case 0x32:
            global = 0x5430bc;
            break;
        default:
            return 0;
        }
        value = run.get(global);
    }
    run.put(receiver + 0x1c, value);
    return 0;
}

// 0x4ce3d0. Indexed image collection, signed bounds +0x64/+0x68.
uint32_t function_4ce3d0(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t index = a[1];
    if (s32(index) < run.gets(receiver + 0x18) && run.get(run.get(receiver + 0x14) + index * 4))
        return 0;
    uint32_t image = run.call(0x4f63ec, 0, {0x34});
    if (image) {
        uint32_t context = run.get(receiver + 0x0c);
        run.put(image + 0x04, index);
        run.put(image + 0x08, 0);
        run.put(image + 0x0c, context);
        run.put(image, 0x513a70);
        run.put(image + 0x10, 0);
        run.put(image + 0x14, 0);
        run.put(image + 0x2c, 0);
        run.put(image + 0x30, 0);
    }
    if (!invoke(run, run.get(run.get(image) + 0x30), image, {a[0], a[2]}, -0x1c)) {
        if (image)
            invoke(run, run.get(run.get(image) + 0x04), image, {1}, -0x18);
        return 0;
    }
    run.call(0x4f582f, receiver + 0x10, {index, image});
    if (s32(index) < run.gets(receiver + 0x64))
        run.put(receiver + 0x64, index);
    if (s32(index) > run.gets(receiver + 0x68))
        run.put(receiver + 0x68, index);
    return image;
}

// 0x4d22f0. Resource-backed surface dimensions and rendering flags.
uint32_t function_4d22f0(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t key = a[1] ? run.get(0x543170) : 0xffffffff;
    uint32_t flags = run.get(0x54316c) ? 0x800 : 0;
    uint32_t savedStack = run.stackPointer;
    run.stackPointer = run.automatic(-0x14);
    uint32_t surface = run.call(0x4bc740, run.get(run.get(receiver + 0x0c) + 0x1c), {a[0], flags, key});
    run.stackPointer = savedStack;
    run.put(receiver + 0x2c, surface);
    if (!surface)
        return 0;
    uint32_t width = run.get(surface + 0x18);
    run.put(receiver + 0x10, width);
    uint32_t height = run.get(surface + 0x14);
    run.put(receiver + 0x14, height);
    run.put(receiver + 0x18, uint32_t(s32(width) >> 1));
    run.put(receiver + 0x1c, uint32_t(s32(height) >> 1));
    run.put(receiver + 0x28, run.get(surface + 0xb8) ? 0x11 : 0x10);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x24, 0);
    return 1;
}

// 0x4d2410. Select ordinary or light-image loading.
uint32_t function_4d2410(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t kind = a[1];
    if (kind != 1 && kind != 2 && kind != 3 && kind != 4)
        return 0;
    if (kind == 4 && (run.get8(a[0] + 0x04) & 0x20)) {
        if (!invoke(run, 0x4d25e0, receiver, {a[0], a[2]}, -0x18))
            return 0;
        uint32_t light = run.get(receiver + 0x30);
        if (light && (run.get8(a[0] + 0x04) & 0x40))
            invoke(run, 0x4c6130, light, {2, 0}, -0x18);
        return 1;
    }
    uint32_t key = a[3] ? run.get(0x543170) : 0xffffffff;
    if (kind == 3 || kind == 4) {
        uint32_t y = run.get(a[0] + 0x14);
        uint32_t x = run.get(a[0] + 0x10);
        run.put(receiver + 0x20, x);
        run.put(receiver + 0x24, y);
    } else {
        run.put(receiver + 0x20, 0);
        run.put(receiver + 0x24, 0);
    }
    uint32_t flags = run.get(0x54316c) ? 0x800 : 0;
    uint32_t surface = invoke(run, 0x4bc520, run.get(run.get(receiver + 0x0c) + 0x1c), {a[0], kind, a[2], flags, key}, -0x24);
    run.put(receiver + 0x2c, surface);
    if (!surface)
        return 0;
    uint32_t width = run.get(surface + 0x18);
    run.put(receiver + 0x10, width);
    uint32_t height = run.get(surface + 0x14);
    run.put(receiver + 0x14, height);
    run.put(receiver + 0x18, uint32_t(s32(width) >> 1));
    run.put(receiver + 0x1c, uint32_t(s32(height) >> 1));
    run.put(receiver + 0x28, run.get(surface + 0xb8) ? 0x11 : 0x10);
    return 1;
}

// 0x4d25e0. Context format chain and owned light object at +0x30.
uint32_t function_4d25e0(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t light = run.call(0x4f63ec, 0, {0x28});
    if (light)
        light = invoke(run, 0x4bfbf0, light, {}, -0x1c);
    run.put(receiver + 0x30, light);
    if (!light)
        return 0;
    uint32_t format = run.get(run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x10) + 0x18);
    if (!invoke(run, 0x4bfc50, light, {a[0], a[1], format}, -0x28))
        return 0;
    uint32_t current = run.get(receiver + 0x30);
    uint32_t width = run.get(current + 0x04);
    run.put(receiver + 0x10, width);
    uint32_t height = run.get(current + 0x08);
    run.put(receiver + 0x14, height);
    run.put(receiver + 0x28, 0x11);
    run.put(receiver + 0x18, uint32_t(s32(width) >> 1));
    run.put(receiver + 0x1c, uint32_t(s32(height) >> 1));
    run.put(receiver + 0x20, run.get(a[0] + 0x10));
    run.put(receiver + 0x24, run.get(a[0] + 0x14));
    return 1;
}

// 0x4d2890. Actor position, clipping, blink, and surface drawing.
uint32_t function_4d2890(Run &run, uint32_t receiver, const uint32_t *a) {
    uint32_t actor = a[0];
    uint32_t target = a[1];
    uint32_t flags = run.get(actor + 0x40);
    if (flags & 1) {
        run.put(actor + 0x38, 0xffffffff);
        return 0;
    }
    if (flags & 8) {
        uint32_t count = run.get(actor + 0x44);
        uint32_t delta = run.get(0x5430c4);
        if (delta >= count) {
            run.put(actor + 0x44, run.get(actor + 0x48));
            run.put(actor + 0x40, flags ^ 0x10000000);
        } else {
            run.put(actor + 0x44, count - delta);
        }
        flags = run.get(actor + 0x40);
        if (!(flags & 0x10000000)) {
            run.put(actor + 0x38, 0xffffffff);
            return 0;
        }
    }
    uint32_t delegate = 0;
    if (flags & 2)
        delegate = flags & 4 ? (run.get(receiver + 0x30) ? 0x4d3550 : 0x4d2bb0) : (run.get(receiver + 0x30) ? 0x4d3790 : 0x4d2e10);
    else if (flags & 4)
        delegate = run.get(receiver + 0x30) ? 0x4d3a00 : 0x4d3080;
    else if (run.get(receiver + 0x30))
        delegate = 0x4d32e0;
    if (delegate) {
        run.call(delegate, receiver, {actor, target});
        return 0;
    }
    uint32_t xToken = run.automatic(-0x4c);
    uint32_t yToken = run.automatic(-0x48);
    uint32_t x = run.get(receiver + 0x20) + run.get(actor + 0x10) + run.get(actor + 0x4c) - run.get(receiver + 0x18);
    uint32_t y = run.get(receiver + 0x24) + run.get(actor + 0x14) + run.get(actor + 0x50) - run.get(receiver + 0x1c);
    run.put(xToken, x);
    run.put(yToken, y);
    if (run.get(actor + 0x08) & 0x40000) {
        run.call(0x4c96d0, run.get(run.get(actor + 0x3c) + 0x5c), {xToken, yToken});
        x = run.get(xToken);
        y = run.get(yToken);
    }
    uint32_t left = x;
    uint32_t top = y;
    uint32_t right = run.get(receiver + 0x10) + x - 1;
    uint32_t bottom = run.get(receiver + 0x14) + y - 1;
    uint32_t rightToken = run.automatic(-0x38);
    uint32_t leftToken = run.automatic(-0x40);
    uint32_t bottomToken = run.automatic(-0x34);
    run.put(leftToken, left);
    run.put(rightToken, right);
    run.put(bottomToken, bottom);
    if (run.get(actor + 0x08) & 0x40000) {
        uint32_t viewport = run.get(run.get(receiver + 0x0c) + 0x24) + 0x10;
        uint32_t source = run.automatic(-0x30);
        uint32_t clip = run.automatic(-0x20);
        for (uint32_t i = 0; i < 0x10; i += 4)
            run.put(source + i, run.get(viewport + i));
        run.icall(0x546d58, {clip, source});
        x = run.get(xToken);
        if (s32(x) < run.gets(clip))
            run.put(leftToken, run.get(leftToken) + run.get(clip) - x);
        if (s32(right) > run.gets(clip + 0x08))
            run.put(rightToken, run.get(clip + 0x08));
        y = run.get(yToken);
        if (s32(y) < run.gets(clip + 0x04))
            top += run.get(clip + 0x04) - y;
        if (s32(bottom) > run.gets(clip + 0x0c))
            run.put(bottomToken, run.get(clip + 0x0c));
    } else {
        uint32_t clipLeft = run.get(actor + 0x54);
        if (clipLeft == 0x80000000) {
            if (s32(x) < 0)
                run.put(leftToken, 0);
            uint32_t width = run.get(target + 0x10);
            if (s32(right) >= s32(width))
                run.put(rightToken, width - 1);
            if (s32(y) < 0)
                top = 0;
            uint32_t height = run.get(target + 0x14);
            if (s32(bottom) >= s32(height))
                run.put(bottomToken, height - 1);
        } else {
            if (s32(x) < s32(clipLeft))
                run.put(leftToken, clipLeft);
            if (s32(right) > run.gets(actor + 0x5c))
                run.put(rightToken, run.get(actor + 0x5c));
            if (s32(y) < run.gets(actor + 0x58))
                top = run.get(actor + 0x58);
            if (s32(bottom) > run.gets(actor + 0x60))
                run.put(bottomToken, run.get(actor + 0x60));
        }
    }
    left = run.get(leftToken);
    right = run.get(rightToken);
    bottom = run.get(bottomToken);
    uint32_t width = right - left + 1;
    uint32_t height = bottom - top + 1;
    if (s32(width) <= 0 || s32(height) <= 0) {
        run.put(actor + 0x38, 0xffffffff);
        return 0;
    }
    uint32_t rectangle = run.automatic(-0x10);
    run.put(rectangle + 0x04, top - y);
    run.put(rectangle, left - x);
    run.put(rectangle + 0x0c, top - y + height);
    run.put(rectangle + 0x08, left - x + width);
    run.call(0x4b9d80, run.get(target + 0x2c), {left, top, run.get(receiver + 0x2c), rectangle, run.get(receiver + 0x28)});
    left = run.get(leftToken);
    bottom = run.get(bottomToken);
    run.put(actor + 0x18, left);
    run.put(actor + 0x20, left);
    right = run.get(rightToken);
    run.put(actor + 0x1c, top);
    run.put(actor + 0x30, width);
    run.put(actor + 0x24, top);
    run.put(actor + 0x34, height);
    run.put(actor + 0x38, 0);
    run.put(actor + 0x28, right);
    run.put(actor + 0x2c, bottom);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b9180:
        return function_4b9180(run, receiver, arguments);
    case 0x4b9380:
        return function_4b9380(run, receiver, arguments);
    case 0x4b9730:
        return function_4b9730(run, receiver, arguments);
    case 0x4b9990:
        return function_4b9990(run, receiver, arguments);
    case 0x4bb0e0:
        return function_4bb0e0(run, receiver, arguments);
    case 0x4bc490:
        return function_4bc490(run, receiver, arguments);
    case 0x4bc520:
        return function_4bc520(run, receiver, arguments);
    case 0x4bf310:
        return function_4bf310(run, receiver, arguments);
    case 0x4bf9c0:
        return function_4bf9c0(run, receiver, arguments);
    case 0x4bfbf0:
        return function_4bfbf0(run, receiver, arguments);
    case 0x4bfc50:
        return function_4bfc50(run, receiver, arguments);
    case 0x4c6130:
        return function_4c6130(run, receiver, arguments);
    case 0x4ce3d0:
        return function_4ce3d0(run, receiver, arguments);
    case 0x4d22f0:
        return function_4d22f0(run, receiver, arguments);
    case 0x4d2410:
        return function_4d2410(run, receiver, arguments);
    case 0x4d25e0:
        return function_4d25e0(run, receiver, arguments);
    case 0x4d2890:
        return function_4d2890(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_game_image_canonical_entry, owned, body)
