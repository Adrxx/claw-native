// Original WWD actor loading and initialization, recovered from the packet.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

// Actor layout: +0x0 vtable, +0x4 id, +0x8 flags, +0xc scene;
// +0x10/+0x14 movement state, +0x20 sentinel, +0x38 invalid index,
// +0x3c scene position policy, +0x40/+0x44 position state, +0x48 default 50,
// +0x4c/+0x50/+0x64 position x/y/z, +0x54..+0x60 first rectangle,
// +0x68 image, +0x6c logic, +0x70..+0x84 child/link state,
// +0x90/+0x94 link state, +0x98/+0x9c saved position, +0xa0 owner,
// +0xac sentinel, +0xc4 invalid index, +0xc8 initialization state,
// +0xd0/+0xd4/+0xd8 properties, +0xdc/+0xe0 default dimensions,
// +0xe8/+0xec/+0xf0 saved x/y/z, +0xf8..+0x114 WWD properties,
// +0x118..+0x144 three rectangles, +0x148/+0x14c WWD properties,
// +0x164 initialization state, +0x168/+0x16c invalid indices,
// +0x170..+0x17c generic state, +0x180 metadata, +0x184 alternate sequence,
// +0x188 animation subobject (table, actor at +0x4, state at +0x8/+0xc).
// Logic layout: +0x0 table, +0x4 id, +0x8 flags, +0xc scene,
// +0x10 callback, +0x14..+0x38 initialized state and WWD properties,
// +0x44/+0x48, +0x64..+0x80, +0xb8/+0xbc/+0xc8/+0xcc,
// +0xf0..+0x10c WWD properties; +0x168/+0x16c initialization state.
// Animation initializer also writes +0x1c enabled and +0x28 raw float speed.
// Plane +0xc scene, +0x30/+0x34 dimensions, +0xb0 actor collection.
// Scene +0x14 logic manager, +0x24 position policy; manager +0x10 resource map.
// CString's data pointer has its length at data-0x8.
int owned(uint32_t function) {
    switch (function) {
    case 0x4d17e0:
        return 1;
    case 0x4c98c0:
        return 3;
    case 0x4c7df0:
        return 4;
    case 0x4c8160:
        return 2;
    case 0x4c81f0:
        return 1;
    case 0x4c9690:
        return 0;
    case 0x4c96c0:
        return 0;
    case 0x4c9780:
        return 3;
    case 0x4c9830:
        return 3;
    case 0x4c9ba0:
        return 0;
    case 0x4c9d40:
        return 4;
    case 0x4d5800:
        return 2;
    default:
        return -1;
    }
}

uint32_t function_4d17e0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c98c0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c7df0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c8160(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c81f0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9690(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c96c0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9780(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9830(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9ba0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4c9d40(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4d5800(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// Select the actual loaded virtual target, dispatching owned entries natively.
uint32_t virtualCall(Run &run, uint32_t receiver, uint32_t slot, std::initializer_list<uint32_t> values) {
    uint32_t target = run.get(run.get(receiver) + slot);
    if (owned(target) >= 0) {
        uint32_t arguments[16] = {};
        uint32_t index = 0;
        for (uint32_t value : values)
            arguments[index++] = value;
        if (index != uint32_t(owned(target)))
            run.fail(CLAW_FAULT_ABI, target);
        return body(run, target, receiver, arguments);
    }
    return run.call(target, receiver, values);
}

// 0x4c9690. Guest fields and store order follow the original disassembly.
uint32_t function_4c9690(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x8, 0x80000000);
    run.put(receiver + 0x20, 0xffffffff);
    return receiver;
}

// 0x4c96c0. Guest fields and store order follow the original disassembly.
uint32_t function_4c96c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0xc, 0);
    run.put(receiver + 0x8, 0);
    run.put(receiver + 0x18, 0);
    return receiver;
}

// 0x4c9780. Guest fields and store order follow the original disassembly.
uint32_t function_4c9780(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x4, arguments[1]);
    run.put(receiver + 0xc, arguments[0]);
    run.put(receiver + 0x8, arguments[2]);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x54, 0x80000000);
    run.put(receiver + 0x0, 0x513888);
    run.put(receiver + 0x3c, 0);
    run.put(receiver + 0x40, 0);
    return receiver;
}

// 0x4c9830. Guest fields and store order follow the original disassembly.
uint32_t function_4c9830(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x4, arguments[1]);
    run.put(receiver + 0xc, arguments[0]);
    run.put(receiver + 0x8, arguments[2]);
    run.put(receiver + 0x0, 0x513740);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0);
    return receiver;
}

// 0x4c9ba0. Guest fields and store order follow the original disassembly.
uint32_t function_4c9ba0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x0, 0x513870);
    run.put(receiver + 0x4, 0);
    run.put(receiver + 0x8, 0);
    run.put(receiver + 0xc, 0);
    return receiver;
}

// 0x4c81f0. Guest fields and store order follow the original disassembly.
uint32_t function_4c81f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x8, 0);
    run.put(receiver + 0x4, arguments[0]);
    run.put(receiver + 0x1c, 1);
    run.put(receiver + 0x28, 0x3f800000);
    return 1;
}

// 0x4c8160. Guest fields and store order follow the original disassembly.
uint32_t function_4c8160(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!arguments[0])
        return 0;
    run.put(receiver + 0x10, arguments[0]);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x24, 0);
    run.put(receiver + 0x2c, 0);
    run.put(receiver + 0x34, 0);
    run.put(receiver + 0x30, 0);
    run.put(receiver + 0x38, 0);
    run.put(receiver + 0x168, 0);
    run.put(receiver + 0x16c, 0);
    run.put(receiver + 0x28, 0);
    run.put(receiver + 0x8, arguments[1]);
    return 1;
}

// 0x4d5800. Guest fields and store order follow the original disassembly.
uint32_t function_4d5800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x4c, arguments[0]);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0);
    uint32_t scene = run.get(receiver + 0xc);
    run.put(receiver + 0x50, arguments[1]);
    run.put(receiver + 0x48, 0x32);
    run.put(receiver + 0x3c, run.get(scene + 0x24));
    return 1;
}

// 0x4c98c0. Guest fields and store order follow the original disassembly.
uint32_t function_4c98c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x8, arguments[2]);
    run.put(receiver + 0x4, arguments[1]);
    run.put(receiver + 0xc, arguments[0]);
    run.put(receiver + 0x20, 0x80000000);
    run.put(receiver + 0x38, 0xffffffff);
    run.put(receiver + 0x54, 0x80000000);
    run.put(receiver + 0x3c, 0);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x94, 0);
    run.put(receiver + 0x90, 0);
    run.put(receiver + 0xa0, 0);
    run.put(receiver + 0xac, 0x80000000);
    run.put(receiver + 0xc4, 0xffffffff);
    run.put(receiver + 0x0, 0x513770);
    run.put(receiver + 0x4c, 0x80000000);
    run.put(receiver + 0x68, 0);
    uint32_t logic = run.call(0x4f63ec, 0, {0x174});
    if (logic) {
        run.put(logic + 0x4, arguments[1]);
        run.put(logic + 0x8, 0);
        run.put(logic + 0xc, arguments[0]);
        run.put(logic + 0x0, 0x513740);
        run.put(logic + 0x10, 0);
        run.put(logic + 0x14, 0);
        run.put(logic + 0x18, 0);
        run.put(logic + 0x1c, 0);
    }
    run.put(receiver + 0x6c, logic);
    run.put(receiver + 0x84, 0);
    run.put(receiver + 0x80, 0);
    run.put(receiver + 0x70, 0);
    run.put(receiver + 0x78, 0);
    return receiver;
}

// 0x4c7df0. Guest fields and store order follow the original disassembly.
uint32_t function_4c7df0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4d5800(run, receiver, arguments);
    run.put(receiver + 0x4c, arguments[0]);
    uint32_t logic = run.get(receiver + 0x6c);
    run.put(receiver + 0x50, arguments[1]);
    run.put(receiver + 0x64, arguments[2]);
    run.put(receiver + 0xf0, arguments[2]);
    run.put(receiver + 0xec, arguments[1]);
    run.put(receiver + 0xdc, 10);
    run.put(receiver + 0xe0, 10);
    run.put(receiver + 0xe8, arguments[0]);
    run.put(receiver + 0xfc, 0);
    run.put(receiver + 0xf8, 0);
    run.put(receiver + 0x10c, 0);
    run.put(receiver + 0x108, 0);
    run.put(receiver + 0x100, 0);
    run.put(receiver + 0x104, 0);
    run.put(receiver + 0x110, 0);
    run.put(receiver + 0x114, 0);
    run.put(receiver + 0x148, 0);
    run.put(receiver + 0x14c, 0);
    run.put(receiver + 0xc8, 0);
    run.put(receiver + 0x164, 0);
    uint32_t flags = run.get(arguments[3] + 0x8);
    uint32_t callback = run.get(arguments[3] + 0x10);
    if (!virtualCall(run, logic, 0x24, {callback, flags}))
        return 0;
    run.put(receiver + 0x70, 0);
    run.put(receiver + 0x78, 0);
    run.put(receiver + 0x74, 0);
    run.put(receiver + 0x7c, 0);
    run.put(receiver + 0xd0, 0);
    run.put(receiver + 0xd4, 0);
    run.put(receiver + 0xd8, 0);
    run.put(receiver + 0x118, 0x80000000);
    run.put(receiver + 0x128, 0x80000000);
    run.put(receiver + 0x138, 0x80000000);
    run.put(receiver + 0xa0, receiver);
    uint32_t x = run.get(receiver + 0x4c);
    uint32_t y = run.get(receiver + 0x50);
    logic = run.get(receiver + 0x6c);
    run.put(receiver + 0x98, x);
    run.put(receiver + 0x9c, y);
    flags = run.get(logic + 0x8);
    if (flags & 1) {
        run.put(receiver + 0x8, run.get(receiver + 0x8) | 0x800000);
        return 1;
    }
    if (flags & 2)
        run.put(receiver + 0x8, run.get(receiver + 0x8) | 0x1000000);
    return 1;
}

// 0x4c9d40. Guest fields and store order follow the original disassembly.
uint32_t function_4c9d40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x180, arguments[3]);
    run.put(receiver + 0x184, 0);
    uint32_t animationArguments[] = {receiver};
    function_4c81f0(run, receiver + 0x188, animationArguments);
    return function_4c7df0(run, receiver, arguments);
}

// The four CString slots and scratch buffer retain their original guest-stack identities.
void destroyStrings(Run &run) {
    run.call(0x4f6584, run.automatic(-0x444));
    run.call(0x4f6584, run.automatic(-0x43c));
    run.call(0x4f6584, run.automatic(-0x440));
    run.call(0x4f6584, run.automatic(-0x438));
}

// 0x4d17e0. Guest fields and store order follow the original disassembly.
uint32_t function_4d17e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t header = arguments[0];
    if (!header)
        return 0;
    uint32_t id = run.get(header);
    uint32_t lengths[4];
    for (uint32_t i = 0; i < 4; ++i)
        lengths[i] = run.get(header + 0x4 + i * 4);
    uint32_t x = run.get(header + 0x14);
    uint32_t y = run.get(header + 0x18);
    uint32_t z = run.get(header + 0x1c);
    uint32_t frame = run.get(header + 0x20);
    uint32_t actor = run.call(0x4f63ec, 0, {0x1b4});
    if (!actor)
        return 0;
    uint32_t constructorArguments[] = {run.get(receiver + 0xc), id, 0};
    function_4c98c0(run, actor, constructorArguments);
    run.put(actor + 0x188, 0x513870);
    run.put(actor + 0x18c, 0);
    run.put(actor + 0x190, 0);
    run.put(actor + 0x194, 0);
    run.put(actor + 0x0, 0x5137f0);
    run.put(actor + 0x168, 0xffffffff);
    run.put(actor + 0x16c, 0xffffffff);
    run.put(actor + 0x174, 0);
    run.put(actor + 0x170, 0);
    run.put(actor + 0x178, 0);
    run.put(actor + 0x17c, 0);
    run.put(actor + 0x180, 0);
    run.put(actor + 0x184, 0);
    uint32_t cursor = header + 0x11c;
    uint32_t buffer = run.automatic(-0x40c);
    const int32_t slots[] = {-0x438, -0x440, -0x43c, -0x444};
    for (uint32_t i = 0; i < 4; ++i) {
        uint32_t length = s32(lengths[i]) > 0 ? lengths[i] : 0;
        uint32_t at = 0;
        for (; at + 4 <= length; at += 4)
            run.put(buffer + at, run.get(cursor + at));
        for (; at < length; ++at)
            run.put8(buffer + at, run.get8(cursor + at));
        cursor += length;
        run.put8(buffer + length, 0);
        run.call(0x4f65f2, run.automatic(slots[i]), {buffer});
    }
    uint32_t consumed = cursor - header;
    if (s32(x) < 0 || s32(x) >= s32(run.get(receiver + 0x30)) || s32(y) < 0 || s32(y) >= s32(run.get(receiver + 0x34))) {
        virtualCall(run, actor, 0x4, {1});
        destroyStrings(run);
        return consumed;
    }
    uint32_t logicName = run.get(run.automatic(-0x440));
    uint32_t metadata = 0;
    if (run.get(logicName - 0x8)) {
        uint32_t output = run.automatic(-0x434);
        run.put(output, 0);
        uint32_t scene = run.get(receiver + 0xc);
        uint32_t manager = run.get(scene + 0x14);
        run.call(0x4f6286, manager + 0x10, {logicName, output});
        metadata = run.get(output);
    }
    if (!metadata) {
        virtualCall(run, actor, 0x4, {1});
        destroyStrings(run);
        return consumed;
    }
    if (!virtualCall(run, actor, 0x28, {x, y, z, metadata})) {
        virtualCall(run, actor, 0x4, {1});
        destroyStrings(run);
        return 0;
    }
    run.put(actor + 0x8, run.get(actor + 0x8) | 0x40000);
    uint32_t logic = run.get(actor + 0x6c);
    if (!logic) {
        virtualCall(run, actor, 0x4, {1});
        destroyStrings(run);
        return 0;
    }
    uint32_t image = run.get(run.automatic(-0x43c));
    if (run.get(image - 0x8)) {
        if (frame == 0xffffffff)
            run.call(0x4c7970, actor, {image});
        else
            run.call(0x4c7900, actor, {image, frame});
    }
    uint32_t animation = run.get(run.automatic(-0x444));
    if (run.get(animation - 0x8)) {
        run.call(0x4c79e0, actor, {animation, 0});
        run.call(0x4c7a40, actor, {run.get(run.automatic(-0x444))});
    }
    uint32_t headerFlags = run.get(header + 0x28);
    run.put(actor + 0x8, run.get(actor + 0x8) | headerFlags);
    run.put(actor + 0x40, run.get(header + 0x2c));
    run.put(logic + 0x28, run.get(header + 0x30));
    run.put(actor + 0xf8, run.get(header + 0x34));
    run.put(actor + 0xfc, run.get(header + 0x38));
    run.put(actor + 0x100, run.get(header + 0x3c));
    run.put(actor + 0x104, run.get(header + 0x40));
    run.put(actor + 0x108, run.get(header + 0x44));
    run.put(actor + 0x10c, run.get(header + 0x48));
    run.put(actor + 0x118, run.get(header + 0x4c));
    run.put(actor + 0x11c, run.get(header + 0x50));
    run.put(actor + 0x120, run.get(header + 0x54));
    run.put(actor + 0x124, run.get(header + 0x58));
    run.put(actor + 0x128, run.get(header + 0x5c));
    run.put(actor + 0x12c, run.get(header + 0x60));
    run.put(actor + 0x130, run.get(header + 0x64));
    run.put(actor + 0x134, run.get(header + 0x68));
    run.put(actor + 0x138, run.get(header + 0x6c));
    run.put(actor + 0x13c, run.get(header + 0x70));
    run.put(actor + 0x140, run.get(header + 0x74));
    run.put(actor + 0x144, run.get(header + 0x78));
    run.put(actor + 0x54, run.get(header + 0x7c));
    run.put(actor + 0x58, run.get(header + 0x80));
    run.put(actor + 0x5c, run.get(header + 0x84));
    run.put(actor + 0x60, run.get(header + 0x88));
    if (!run.get(actor + 0x128) && !run.get(actor + 0x130))
        run.put(actor + 0x128, 0x80000000);
    if (!run.get(actor + 0x118) && !run.get(actor + 0x120))
        run.put(actor + 0x118, 0x80000000);
    if (!run.get(actor + 0x54) && !run.get(actor + 0x5c))
        run.put(actor + 0x54, 0x80000000);
    if (!run.get(actor + 0x138) && !run.get(actor + 0x140))
        run.put(actor + 0x138, 0x80000000);
    run.put(logic + 0xf0, run.get(header + 0x8c));
    run.put(logic + 0xf4, run.get(header + 0x90));
    run.put(logic + 0xf8, run.get(header + 0x94));
    run.put(logic + 0xfc, run.get(header + 0x98));
    run.put(logic + 0x100, run.get(header + 0x9c));
    run.put(logic + 0x104, run.get(header + 0xa0));
    run.put(logic + 0x108, run.get(header + 0xa4));
    run.put(logic + 0x10c, run.get(header + 0xa8));
    run.put(logic + 0x64, run.get(header + 0xac));
    run.put(logic + 0x68, run.get(header + 0xb0));
    run.put(logic + 0x6c, run.get(header + 0xb4));
    run.put(logic + 0x70, run.get(header + 0xb8));
    run.put(logic + 0x74, run.get(header + 0xbc));
    run.put(logic + 0x78, run.get(header + 0xc0));
    run.put(logic + 0x7c, run.get(header + 0xc4));
    run.put(logic + 0x80, run.get(header + 0xc8));
    run.put(logic + 0x2c, run.get(header + 0xcc));
    run.put(logic + 0x34, run.get(header + 0xd0));
    run.put(logic + 0x30, run.get(header + 0xd4));
    run.put(logic + 0x38, run.get(header + 0xd8));
    run.put(actor + 0x148, run.get(header + 0xdc));
    run.put(actor + 0x14c, run.get(header + 0xe0));
    run.put(logic + 0x44, run.get(header + 0xe4));
    run.put(logic + 0x48, run.get(header + 0xe8));
    run.put(logic + 0xb8, run.get(header + 0xec));
    run.put(logic + 0xbc, run.get(header + 0xf0));
    run.put(logic + 0xc8, run.get(header + 0xf4));
    run.put(logic + 0xcc, run.get(header + 0xf8));
    run.put(actor + 0x110, run.get(header + 0xfc));
    run.put(actor + 0x114, run.get(header + 0x100));
    uint32_t field65 = run.get(header + 0x104);
    uint32_t field66 = run.get(header + 0x108);
    run.put(logic + 0x20, field65);
    run.put(logic + 0x24, field66);
    run.put(actor + 0xd0, run.get(header + 0x10c));
    run.put(actor + 0xd4, run.get(header + 0x110));
    uint32_t field69 = run.get(header + 0x114);
    if (field69)
        run.put(actor + 0xdc, field69);
    uint32_t field70 = run.get(header + 0x118);
    if (field70)
        run.put(actor + 0xe0, field70);
    run.call(0x4d51a0, run.get(receiver + 0xb0), {actor});
    destroyStrings(run);
    return consumed;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4d17e0:
        return function_4d17e0(run, receiver, arguments);
    case 0x4c98c0:
        return function_4c98c0(run, receiver, arguments);
    case 0x4c7df0:
        return function_4c7df0(run, receiver, arguments);
    case 0x4c8160:
        return function_4c8160(run, receiver, arguments);
    case 0x4c81f0:
        return function_4c81f0(run, receiver, arguments);
    case 0x4c9690:
        return function_4c9690(run, receiver, arguments);
    case 0x4c96c0:
        return function_4c96c0(run, receiver, arguments);
    case 0x4c9780:
        return function_4c9780(run, receiver, arguments);
    case 0x4c9830:
        return function_4c9830(run, receiver, arguments);
    case 0x4c9ba0:
        return function_4c9ba0(run, receiver, arguments);
    case 0x4c9d40:
        return function_4c9d40(run, receiver, arguments);
    case 0x4d5800:
        return function_4d5800(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_world_object_entry, owned, body)
