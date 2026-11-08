// Level 1 frame and resource entries batch 1
//
// Recovered from the six original disassemblies in the family packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4d2140:
        return 0;
    case 0x4d3c40:
        return 4;
    case 0x4d4870:
        return 1;
    case 0x4d4c70:
        return 1;
    case 0x4d51f0:
        return 1;
    case 0x4d5240:
        return 2;
    default:
        return -1;
    }
}

// 0x4d2140. Receiver +0x0c owns display/resources; +0x144 is the color index.
uint32_t function_4d2140(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t owner = run.get(receiver + 0x0c);
    uint32_t display = run.get(run.get(owner + 0x04) + 0x10);
    uint32_t depth = run.get(display + 0x18);
    if (depth == 8)
        return 0;
    if (depth != 16)
        return 0;
    uint32_t index = run.get(receiver + 0x144);
    if (s32(index) < 0)
        return 0;
    if (s32(index) > 255)
        return 0;
    uint32_t resource = run.get(run.get(owner + 0x18) + 0x64);
    if (!resource)
        return 0;
    uint32_t palette = run.get(run.get(resource + 0x10) + 0x0c);
    if (!palette)
        return 0;
    uint32_t first = uint32_t(run.get8(palette + index * 4)) >> (run.get8(0x541368) & 31);
    uint32_t firstShift = run.get(0x54135c) & 31;
    uint32_t second = uint32_t(run.get8(palette + index * 4 + 0x01)) >> (run.get8(0x54136c) & 31);
    uint32_t secondShift = run.get(0x541360) & 31;
    uint32_t third = uint32_t(run.get8(palette + index * 4 + 0x02)) >> (run.get8(0x541370) & 31);
    run.put(receiver + 0x144, ((first << firstShift) | (second << secondShift) | third) & 0xffff);
    return 0;
}

// 0x4d3c40. Attached-list head +0x1b8; node +0x00 next, +0x08 object.
uint32_t function_4d3c40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t node = run.get(receiver + 0x1b8);
    while (node) {
        uint32_t next = run.get(node + 0x00);
        uint32_t object = run.get(node + 0x08);
        if (object)
            run.vcall(object, 0x04, {1});
        node = next;
    }
    run.call(0x4f5172, receiver + 0x1b4);
    uint32_t result = run.call(0x4c7df0, receiver, {arguments[0], arguments[1], arguments[2], arguments[3]});
    return result != 0;
}

// 0x4d4870. Member +0x18 actor, actor +0x0c parent, parent +0x08 scene.
uint32_t function_4d4870(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t actor = run.get(arguments[0] + 0x18);
    uint32_t scene = run.get(run.get(actor + 0x0c) + 0x08);
    run.call(0x4c9320, scene, {actor});
    return 0;
}

// 0x4d4c70. Receiver +0x00 scene; actor +0x08 flags, +0x6c template.
uint32_t function_4d4c70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t iterator = run.automatic(-0x50);
    run.put(iterator + 0x00, 0x513de0);
    run.put(iterator + 0x04, 0);
    run.put(iterator + 0x08, 0);
    uint32_t grid = arguments[0];
    uint32_t count = 0;
    uint32_t member = run.call(0x4f4860, iterator, {grid, 0});
    while (member) {
        uint32_t actor = run.get(member + 0x18);
        if ((run.get8(actor + 0x08) & 2) || (run.get8(run.get(actor + 0x6c) + 0x08) & 4)) {
            run.call(0x4c9320, run.get(receiver + 0x00), {actor});
            run.call(0x4f4680, grid, {member});
            ++count;
        }
        member = run.call(0x4f49c0, iterator);
    }
    return count;
}

// 0x4d5240. Iterator local +0x00 vtable, +0x04 grid, +0x08 current.
uint32_t function_4d5240(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t iterator = run.automatic(-0x50);
    run.put(iterator + 0x00, 0x513de0);
    run.put(iterator + 0x04, 0);
    run.put(iterator + 0x08, 0);
    uint32_t count = 0;
    uint32_t member = run.call(0x4f4860, iterator, {arguments[0], 0});
    uint32_t callback = arguments[1];
    while (member) {
        run.call(callback, 0, {run.get(member + 0x18)});
        ++count;
        member = run.call(0x4f49c0, iterator);
    }
    return count;
}

// 0x4d51f0. Receiver +0x04, +0x08 and +0x0c hold successive grids.
uint32_t function_4d51f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t callback = arguments[0];
    if (!callback)
        return 0;
    uint32_t first[] = {run.get(receiver + 0x04), callback};
    uint32_t count = function_4d5240(run, 0, first);
    uint32_t second[] = {run.get(receiver + 0x08), callback};
    count += function_4d5240(run, 0, second);
    uint32_t third[] = {run.get(receiver + 0x0c), callback};
    count += function_4d5240(run, 0, third);
    return count;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4d2140:
        return function_4d2140(run, receiver, arguments);
    case 0x4d3c40:
        return function_4d3c40(run, receiver, arguments);
    case 0x4d4870:
        return function_4d4870(run, receiver, arguments);
    case 0x4d4c70:
        return function_4d4c70(run, receiver, arguments);
    case 0x4d51f0:
        return function_4d51f0(run, receiver, arguments);
    case 0x4d5240:
        return function_4d5240(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_frame_resources_01_entry, owned, body)
