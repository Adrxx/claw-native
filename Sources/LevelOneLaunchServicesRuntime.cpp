// Level one launch and scene services
//
// Recovered from the original instruction bodies in the family packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x422980:
        return 3;
    case 0x4229c0:
        return 0;
    case 0x429b70:
        return 1;
    case 0x42c060:
        return 0;
    case 0x46bb80:
        return 0;
    case 0x46db30:
        return 0;
    case 0x46dff0:
        return 1;
    case 0x46e100:
        return 0;
    case 0x46f040:
        return 0;
    case 0x48f1e0:
        return 5;
    case 0x48f370:
        return 5;
    case 0x48f3e0:
        return 5;
    default:
        return -1;
    }
}

// 0x422980. thiscall, 3 stack argument(s), returns void.
uint32_t function_422980(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.stackPointer = run.frame - 0x10;
    uint32_t node = run.call(0x4f63ec, 0, {8});
    if (node) {
        run.put(node + 0x04, arguments[2]); // Action flag.
        run.put(node, arguments[1]); // Command identifier.
        run.stackPointer = run.frame - 0x10;
        uint32_t slot = run.call(0x4f62a8, receiver + 0x04, {arguments[0]});
        run.put(slot, node);
    }
    return 0;
}

// 0x4229c0. thiscall, 0 stack argument(s), returns void.
uint32_t function_4229c0(Run &run, uint32_t receiver, const uint32_t *) {
    const uint32_t entries[][3] = {
        {0x525370, 0x8044, 0},
        {0x525368, 0x8043, 0},
        {0x52535c, 0x8045, 0},
        {0x525350, 0x8046, 0},
        {0x525348, 0x8047, 0},
        {0x525338, 0x8049, 0},
        {0x52532c, 0x804a, 0},
        {0x52531c, 0x804f, 0},
        {0x525314, 0x805b, 0},
        {0x525308, 0x8064, 0},
        {0x5252fc, 0x8065, 0},
        {0x5252f0, 0x8066, 0},
        {0x5252e8, 0x806a, 0},
        {0x5252dc, 0x806c, 0},
        {0x5252cc, 0x8071, 0},
        {0x5252c4, 0x8076, 0},
        {0x5252b8, 0x8077, 0},
        {0x5252ac, 0x8078, 0},
        {0x5252a0, 0x8079, 0},
        {0x525294, 0x808b, 0},
        {0x525288, 0x808d, 0},
        {0x525280, 0x808e, 0},
        {0x525274, 0x8091, 0},
        {0x525268, 0x8092, 0},
        {0x52525c, 0x8093, 0},
        {0x52524c, 0x809c, 0},
        {0x525240, 0x809d, 0},
        {0x525230, 0x809e, 0},
        {0x525224, 0x809f, 0},
        {0x525218, 0x80a0, 0},
        {0x52520c, 0x80a1, 0},
        {0x5251fc, 0x80a2, 0},
        {0x5251f0, 0x80a3, 0},
        {0x5251e4, 0x80a4, 0},
        {0x5251d8, 0x80a5, 0},
        {0x5251cc, 0x80a6, 0},
        {0x5251b8, 0x80a7, 0},
        {0x5251ac, 0x80a8, 0},
        {0x52519c, 0x80a9, 0},
        {0x525190, 0x800e, 0},
        {0x525184, 0x800f, 0},
        {0x525178, 0x80aa, 0},
        {0x525170, 0x804b, 1},
        {0x525168, 0x804c, 1},
        {0x52515c, 0x804d, 1},
        {0x525150, 0x804e, 1},
        {0x525144, 0x806e, 1},
        {0x525138, 0x807a, 1},
        {0x525130, 0x807b, 1},
        {0x525128, 0x8086, 1},
        {0x525120, 0x8086, 1},
        {0x525114, 0x8086, 1},
        {0x52510c, 0x8086, 1},
        {0x525100, 0x8087, 1},
        {0x5250f4, 0x8088, 1},
        {0x5250e8, 0x8089, 1},
        {0x5250dc, 0x808a, 1},
    };
    uint32_t savedFrame = run.frame;
    for (const auto &entry : entries) {
        run.frame = savedFrame - 0x14;
        function_422980(run, receiver, entry);
    }
    run.frame = savedFrame;
    return 0;
}

// 0x429b70. thiscall, 1 stack argument(s), returns u32.
uint32_t function_429b70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.stackPointer = run.frame - 0x10;
    if (run.vcall(run.get(receiver + 0x2c), 0x10) != 3) {
        run.stackPointer = run.frame - 0x20;
        return run.call(0x428c40, receiver, {3, arguments[0], 0, 0});
    }
    uint32_t owner = run.get(receiver + 0x2c); // Current scene owner.
    uint32_t table = run.get(owner);
    run.stackPointer = run.frame - 0x10;
    uint32_t mode = run.call(run.get(table + 0x10), owner);
    run.stackPointer = run.frame - 0x14;
    run.call(run.get(table + 0x28), run.get(receiver + 0x2c), {mode});
    run.stackPointer = run.frame - 0x18;
    if (!run.call(0x46aeb0, owner, {arguments[0], 1}))
        return 0;
    uint32_t current = run.get(receiver + 0x2c);
    table = run.get(current);
    run.stackPointer = run.frame - 0x10;
    mode = run.call(run.get(table + 0x10), current);
    run.stackPointer = run.frame - 0x14;
    run.call(run.get(table + 0x24), run.get(receiver + 0x2c), {mode});
    return 1;
}

// 0x42c060. thiscall, 0 stack argument(s), returns void.
uint32_t function_42c060(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t index = 0;
    while (s32(index) < run.gets(receiver + 0xe4)) { // Object vector count.
        uint32_t object = run.get(run.get(receiver + 0xe0) + index * 4); // Object vector data.
        if (object) {
            run.stackPointer = run.frame - 0x10;
            run.vcall(object, 0x00, {1});
        }
        ++index;
    }
    run.stackPointer = run.frame - 0x14;
    run.call(0x4f5915, receiver + 0xdc, {0, 0xffffffff}); // Object vector container.
    return 0;
}

// 0x46bb80. thiscall, 0 stack argument(s), returns void.
uint32_t function_46bb80(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t application = run.get(receiver + 0x04);
    uint32_t layout = run.get(application + 0x38); // Layout resource directory.
    if (layout) {
        run.stackPointer = run.frame - 0x10;
        run.call(0x42a000, application, {0});
        run.stackPointer = run.frame - 0x14;
        uint32_t status = run.call(0x4b5f30, layout, {0x5258a8, 10});
        run.stackPointer = run.frame - 0x18;
        run.call(0x429ed0, run.get(receiver + 0x04), {status, 1, 0});
    }
    return 0;
}

// 0x46db30. thiscall, 0 stack argument(s), returns u32.
uint32_t function_46db30(Run &run, uint32_t receiver, const uint32_t *) {
    if (!run.get(receiver + 0x2c))
        return 0;
    for (uint32_t index = 0; index < 0x100; ++index)
        run.put8(receiver + 0x260 + index, uint8_t(index)); // Palette remap table.
    uint32_t palette = run.get(run.get(run.get(receiver + 0x2c) + 0x10) + 0x0c);
    if (!palette)
        return 0;
    for (uint32_t index = 1; index < 0xff; ++index) {
        if (index == 10)
            index = 0xf5;
        uint32_t red = run.get8(palette + index * 4);
        uint32_t green = run.get8(palette + index * 4 + 0x01);
        uint32_t blue = run.get8(palette + index * 4 + 0x02);
        auto distance = [&](uint32_t candidate) {
            uint32_t dr = red - run.get8(palette + candidate * 4);
            uint32_t dg = green - run.get8(palette + candidate * 4 + 0x01);
            uint32_t db = blue - run.get8(palette + candidate * 4 + 0x02);
            return dr * dr + dg * dg + db * db;
        };
        uint32_t best = 0x0b;
        uint32_t bestDistance = distance(best);
        for (uint32_t candidate = 0x0b; candidate < 0xf5; ++candidate) {
            uint32_t candidateDistance = distance(candidate);
            if (s32(candidateDistance) < s32(bestDistance)) {
                best = candidate;
                bestDistance = candidateDistance;
                if (!candidateDistance)
                    break;
            }
        }
        run.put8(receiver + 0x260 + index, uint8_t(best));
    }
    return 1;
}

// 0x46dff0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_46dff0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t percent = arguments[0];
    if (s32(percent) < 1)
        return 0;
    if (s32(percent) > 100)
        percent = 100;
    uint32_t rect = run.automatic(-0x10);
    run.put(rect, 0xe5);
    run.put(rect + 0x04, 0x15b);
    run.put(rect + 0x08, 0x19a);
    run.put(rect + 0x0c, 0x166);
    if (percent < 100) {
        double operand = double(s32(percent)) * double(run.getf(0x50edc8));
        operand *= double(run.getf(0x50edcc));
        run.stackPointer = run.frame - 0x18;
        uint32_t converted = run.call_x87(0x4a30e0, 0, operand);
        run.put(rect + 0x08, 0xe5 - converted);
    }
    uint32_t depth = run.get(run.get(receiver + 0x04) + 0x78); // Display pixel depth.
    uint32_t color = 100;
    if (depth == 8)
        color = 0xf9;
    else if (depth == 16)
        color = ((0xffu >> (run.get(0x541368) & 31)) << (run.get(0x54135c) & 31)) & 0xffff;
    else if (depth == 24)
        color = 0xff;
    uint32_t display = run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x10);
    if (!display)
        return 0;
    uint32_t surface = run.get(display + 0x2c);
    if (!surface)
        return 0;
    run.stackPointer = run.frame - 0x20;
    return run.call(0x4b9830, surface, {rect, color});
}

// 0x46e100. thiscall, 0 stack argument(s), returns u32.
uint32_t function_46e100(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t rect = run.automatic(-0x10);
    run.put(rect, 0xe5);
    run.put(rect + 0x04, 0x15b);
    run.put(rect + 0x08, 0x19a);
    run.put(rect + 0x0c, 0x166);
    uint32_t display = run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x10);
    if (!display)
        return 0;
    uint32_t surface = run.get(display + 0x2c);
    if (!surface)
        return 0;
    run.stackPointer = run.frame - 0x1c;
    return run.call(0x4b9830, surface, {rect, 0});
}

// 0x46f040. thiscall, 0 stack argument(s), returns void.
uint32_t function_46f040(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t application = run.get(receiver + 0x04);
    if (!run.get(run.get(application + 0xc0) - 0x08)) // Current scene path CString length.
        return 0;
    uint32_t path = run.automatic(-0x28);
    uint32_t title = run.automatic(-0x24);
    run.stackPointer = run.frame - 0x3c;
    run.call(0x46a840, application, {path});
    if (run.get(run.get(path) - 0x08)) {
        uint32_t temporary = run.automatic(-0x38);
        run.stackPointer = run.frame - 0x40;
        run.call(0x4f6449, temporary, {path});
        run.stackPointer = run.frame - 0x40;
        run.call(0x4373d0, 0, {title, run.get(temporary)});
        if (run.get(run.get(title) - 0x08)) {
            uint32_t surface = run.get(run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x10) + 0x2c);
            if (surface) {
                uint32_t dc = run.automatic(-0x2c);
                run.put(dc, 0);
                uint32_t interface = run.get(surface + 0x08);
                run.stackPointer = run.frame - 0x40;
                uint32_t status = run.call(run.get(run.get(interface) + 0x44), 0, {interface, dc});
                if (status == 0x8876021c) {
                    run.stackPointer = run.frame - 0x3c;
                    run.call(0x4b8960, 0, {0xfa});
                    interface = run.get(surface + 0x08);
                    run.stackPointer = run.frame - 0x40;
                    run.call(run.get(run.get(interface) + 0x44), 0, {interface, dc});
                }
                if (run.get(dc)) {
                    run.stackPointer = run.frame - 0x40;
                    run.icall(0x546888, {run.get(dc), 1});
                    run.stackPointer = run.frame - 0x40;
                    run.icall(0x546880, {run.get(dc), 0xffffff});
                    run.stackPointer = run.frame - 0x44;
                    run.call(0x4a3920, 0, {0x537c88, 0x52a0d0, run.get(title)});
                    uint32_t rect = run.automatic(-0x1c);
                    run.put(rect, 0);
                    run.put(rect + 0x04, 0x1bd);
                    run.put(rect + 0x08, 0x27f);
                    run.put(rect + 0x0c, 0x1db);
                    run.stackPointer = run.frame - 0x4c;
                    run.icall(0x546d30, {run.get(dc), 0x537c88, 0xffffffff, rect, 0x21});
                    interface = run.get(surface + 0x08);
                    run.stackPointer = run.frame - 0x40;
                    run.call(run.get(run.get(interface) + 0x68), 0, {interface, run.get(dc)});
                }
            }
        }
        run.stackPointer = run.frame - 0x38;
        run.call(0x4f6584, title);
    }
    run.stackPointer = run.frame - 0x38;
    run.call(0x4f6584, path);
    return 0;
}

// 0x48f1e0. thiscall, 5 stack argument(s), returns u32.
uint32_t function_48f1e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!run.get(receiver + 0x0c) || !run.get(receiver + 0x08) || !run.get(receiver + 0x20))
        return 0;
    uint32_t path = run.automatic(-0x80);
    uint32_t name = run.automatic(-0x40);
    run.stackPointer = run.frame - 0xa0;
    run.call(0x4a3920, 0, {path, 0x528e54, arguments[0]});
    run.stackPointer = run.frame - 0x9c;
    uint32_t resource = run.call(0x4b7dc0, run.get(receiver + 0x20), {path, 0x504358});
    if (!resource)
        return 0;
    if (arguments[1]) {
        uint32_t length = 0;
        do {
            ++length;
        } while (run.get8(arguments[0] + length - 1));
        uint32_t index = 0;
        for (; index + 4 <= length; index += 4)
            run.put(name + index, run.get(arguments[0] + index));
        for (; index < length; ++index)
            run.put8(name + index, run.get8(arguments[0] + index));
        uint32_t manager = run.get(run.get(receiver + 0x0c) + 0x18);
        run.stackPointer = run.frame - 0xa0;
        uint32_t scene = run.vcall(manager, 0x30, {resource, name, uint32_t(arguments[4] != 0)});
        run.put(receiver + 0x2c, scene); // Loaded scene.
        if (!scene)
            return 0;
        uint32_t display = run.get(run.get(receiver + 0x0c) + 0x04);
        run.stackPointer = run.frame - 0x98;
        run.call(0x4b97c0, run.get(run.get(display + 0x14) + 0x2c), {0});
        run.stackPointer = run.frame - 0x98;
        run.call(0x4b98b0, run.get(run.get(display + 0x10) + 0x2c), {0});
        scene = run.get(receiver + 0x2c);
        run.put(run.get(run.get(receiver + 0x0c) + 0x18) + 0x64, scene); // Manager active scene.
        run.stackPointer = run.frame - 0x94;
        run.vcall(scene, 0x34);
        if (arguments[2] || arguments[3]) {
            run.stackPointer = run.frame - 0x94;
            run.call(0x4bb870, run.get(run.get(receiver + 0x2c) + 0x10));
            run.stackPointer = run.frame - 0xac;
            run.call(0x4bb910, run.get(run.get(receiver + 0x2c) + 0x10), {0, 0x100, 0, 0, 0, 0});
        }
    }
    run.stackPointer = run.frame - 0x9c;
    return uint32_t(run.call(0x4ca900, run.get(run.get(receiver + 0x0c) + 0x04), {resource, 1}) != 0);
}

// 0x48f370. thiscall, 5 stack argument(s), returns u32.
uint32_t function_48f370(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!run.get(receiver + 0x0c) || !run.get(receiver + 0x08) || !run.get(receiver + 0x20))
        return 0;
    uint32_t surface = run.get(run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x10) + 0x2c);
    run.stackPointer = run.frame - 0xc;
    run.call(0x4b98b0, surface, {0});
    if (arguments[2]) {
        uint32_t scene = run.get(receiver + 0x2c);
        if (scene) {
            uint32_t palette = run.get(scene + 0x10);
            run.stackPointer = run.frame - 0x18;
            run.call(0x4bbd90, palette, {0, 0x100, run.get(palette + 0x10), 0x2ee});
        }
    }
    return 1;
}

// 0x48f3e0. thiscall, 5 stack argument(s), returns u32.
uint32_t function_48f3e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!run.get(receiver + 0x0c) || !run.get(receiver + 0x08) || !run.get(receiver + 0x20))
        return 0;
    uint32_t savedFrame = run.frame;
    run.frame -= 0x28;
    uint32_t value = function_48f1e0(run, receiver, arguments);
    run.frame = savedFrame;
    if (!value)
        return 0;
    run.frame -= 0x28;
    value = function_48f370(run, receiver, arguments);
    run.frame = savedFrame;
    return uint32_t(value != 0);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x422980:
        return function_422980(run, receiver, arguments);
    case 0x4229c0:
        return function_4229c0(run, receiver, arguments);
    case 0x429b70:
        return function_429b70(run, receiver, arguments);
    case 0x42c060:
        return function_42c060(run, receiver, arguments);
    case 0x46bb80:
        return function_46bb80(run, receiver, arguments);
    case 0x46db30:
        return function_46db30(run, receiver, arguments);
    case 0x46dff0:
        return function_46dff0(run, receiver, arguments);
    case 0x46e100:
        return function_46e100(run, receiver, arguments);
    case 0x46f040:
        return function_46f040(run, receiver, arguments);
    case 0x48f1e0:
        return function_48f1e0(run, receiver, arguments);
    case 0x48f370:
        return function_48f370(run, receiver, arguments);
    case 0x48f3e0:
        return function_48f3e0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_launch_services_entry, owned, body)
