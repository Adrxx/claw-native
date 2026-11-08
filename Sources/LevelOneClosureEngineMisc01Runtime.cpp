// Level 1 closure: message drawing, single-frame message, timer, music and registry helpers
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
    case 0x4226b0:
        return 4;
    case 0x491970:
        return 1;
    case 0x490c00:
        return 0;
    case 0x4b5720:
        return 2;
    case 0x4b3d50:
        return 1;
    case 0x4db6a0:
        return 1;
    case 0x4dbd00:
        return 1;
    default:
        return -1;
    }
}

// Appends the NUL-terminated string at `source` to the one at `destination`.
void appendString(Run &run, uint32_t destination, uint32_t source) {
    uint32_t length = 0;
    while (run.get8(source + length) != 0)
        ++length;
    length += 1;
    uint32_t end = destination;
    while (run.get8(end) != 0)
        ++end;
    for (uint32_t i = 0; i < length; ++i)
        run.put8(end + i, run.get8(source + i));
}

// 0x4226b0. Draws the first `count` messages of a list into the DC, joined by
// the separator string, through one DrawTextA call.
// Fields: +0x04 first list node, +0x0c node count, +0x34 font.
// Node: +0x00 next node, +0x08 CString.
uint32_t function_4226b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t count = arguments[0];
    uint32_t dc = arguments[1];
    uint32_t rect = arguments[2];
    uint32_t format = arguments[3];
    if (dc == 0)
        return 0;
    uint32_t total = run.get(receiver + 0x0c);
    if (s32(total) < 1)
        return 0;
    if (s32(count) < s32(total))
        total = count;
    else
        total = run.get(receiver + 0x0c);
    if (s32(total) < 1)
        return 0;
    uint32_t index = 0;
    run.put8(0x534ef8, 0);
    uint32_t node = run.get(receiver + 0x04);
    uint32_t local = run.automatic(-8);
    if (s32(total) > 0) {
        do {
            if (node != 0) {
                uint32_t next = run.get(node);
                run.call(0x4f6449, local, {node + 8});
                appendString(run, 0x534ef8, run.get(local));
                if (s32(index) < s32(total - 1))
                    appendString(run, 0x534ef8, 0x5250d8);
                run.call(0x4f6584, local);
                node = next;
            }
            ++index;
        } while (s32(index) < s32(total));
    }
    uint32_t oldFont = 0;
    uint32_t font = run.get(receiver + 0x34);
    if (font != 0)
        oldFont = run.icall(0x54691c, {dc, font});
    uint32_t length = 0;
    while (run.get8(0x534ef8 + length) != 0)
        ++length;
    run.icall(0x546d30, {dc, 0x534ef8, length, rect, format});
    if (oldFont != 0)
        run.icall(0x54691c, {dc, oldFont});
    return 1;
}

// 0x491970. cdecl. +0x6c state block (+0x1c phase), +0x04 / +0x08 flags.
uint32_t function_491970(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t phase = run.get(run.get(object + 0x6c) + 0x1c);
    if (phase == 0) {
        run.put(run.get(object + 0x6c) + 0x1c, 5);
        run.call(0x4c7900, object, {0x52c8a4, run.get(object + 0x04)});
        uint32_t centerY = uint32_t(s32(run.get(0x5370d4) - run.get(0x5370cc)) / 2) + run.get(0x5370cc);
        uint32_t centerX = uint32_t(s32(run.get(0x5370d0) - run.get(0x5370c8)) / 2) + run.get(0x5370c8);
        run.put(object + 0x50, centerY);
        run.put(object + 0x4c, centerX);
    } else if (phase == 5) {
        run.put(object + 0x08, run.get(object + 0x08) | 0x10000);
    }
    return 1;
}

// 0x490c00. Calls a virtual method of an object two levels down the owner
// chain, then marks the owner and the object.
uint32_t function_490c00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t owner = run.get(receiver + 0x24);
    uint32_t target = run.get(run.get(owner + 0x0c) + 0x0c);
    uint32_t last = run.get(owner + 0x174);
    uint32_t second = run.get(owner + 0x50);
    uint32_t first = run.get(owner + 0x4c);
    run.call(run.get(run.get(target) + 0x28), target, {first, second, last});
    owner = run.get(receiver + 0x24);
    run.put(owner + 0x40, run.get(owner + 0x40) | 1);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x1c, 1);
    return 0;
}

// 0x4b5720. Loads a file whole into +0x5c and hands it to virtual +0x14;
// falls back to virtual +0x3c when 0x4a3990 on the name finds no match.
uint32_t function_4b5720(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t name = arguments[0];
    uint32_t extra = arguments[1];
    uint32_t file = run.automatic(-28);
    if (run.call(0x4a3990, 0, {name, 0x5263e4}) == 0)
        return run.vcall(receiver, 0x3c, {name, extra});
    run.call(0x4f72c9, file);
    if (run.call(0x4f7448, file, {name, 0, 0}) == 0) {
        run.call(0x4f7369, file);
        return 0;
    }
    uint32_t length = run.call(0x4f774d, file);
    if (length < 4) {
        run.call(0x4f7369, file);
        return 0;
    }
    uint32_t buffer = run.call(0x4f63ec, 0, {length});
    run.put(receiver + 0x5c, buffer);
    if (buffer == 0) {
        run.call(0x4f7369, file);
        return 0;
    }
    if (run.call(0x4f7570, file, {buffer, length}) != length) {
        run.call(0x4f7369, file);
        return 0;
    }
    uint32_t data = run.get(receiver + 0x5c);
    uint32_t result = run.vcall(receiver, 0x14, {data, length, extra});
    run.call(0x4f7369, file);
    return result;
}

// 0x4b3d50, 0x4db6a0, 0x4dbd00. Scalar deleting destructors.
uint32_t deletingDestructor(Run &run, uint32_t destructor, uint32_t receiver, uint32_t flags) {
    run.call(destructor, receiver);
    if ((flags & 1) != 0)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

uint32_t function_4b3d50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return deletingDestructor(run, 0x4b3d70, receiver, arguments[0]);
}

uint32_t function_4db6a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return deletingDestructor(run, 0x4db6c0, receiver, arguments[0]);
}

uint32_t function_4dbd00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return deletingDestructor(run, 0x4dbcd0, receiver, arguments[0]);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4226b0:
        return function_4226b0(run, receiver, arguments);
    case 0x491970:
        return function_491970(run, receiver, arguments);
    case 0x490c00:
        return function_490c00(run, receiver, arguments);
    case 0x4b5720:
        return function_4b5720(run, receiver, arguments);
    case 0x4b3d50:
        return function_4b3d50(run, receiver, arguments);
    case 0x4db6a0:
        return function_4db6a0(run, receiver, arguments);
    case 0x4dbd00:
        return function_4dbd00(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_closure_engine_misc_01_entry, owned, body)
