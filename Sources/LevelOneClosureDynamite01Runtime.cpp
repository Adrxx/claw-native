// Level 1 player projectile and dynamite helpers
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
    case 0x408510:
        return 0;
    case 0x408580:
        return 1;
    case 0x408860:
        return 0;
    case 0x408870:
        return 0;
    case 0x43ad20:
        return 1;
    case 0x43b120:
        return 0;
    case 0x43b160:
        return 0;
    case 0x43b1a0:
        return 0;
    case 0x43b1e0:
        return 0;
    case 0x43b210:
        return 0;
    default:
        return -1;
    }
}

// Shared by 0x408580 and 0x43ad20. A handler table object `table` holds:
// +0x04 owner, +0x08 lowest index, +0x0c highest index, +0x10 entries,
// +0x14 default entry, +0x18 entry stride, +0x20 lookup flag.
// Returns the address of the entry for `index`, growing the table when needed.
uint32_t tableEntry(Run &run, uint32_t table, uint32_t index, uint32_t &low) {
    uint32_t entry = 0;
    low = run.get(table + 0x08);
    run.put(table + 0x20, 0);
    bool outside = false;
    if (s32(index) < s32(low))
        outside = true;
    else if (s32(index) > s32(run.get(table + 0x0c)))
        outside = true;
    if (outside) {
        uint32_t found = run.call(0x4db6e0, table, {index, 0});
        // The grow helper only returns zero after the original has already faulted
        // inside it (realloc failure), so no normal-return path reaches here.
        if (found == 0)
            run.fail(CLAW_FAULT_ABI, 0x4db6e0);
        low = run.get(table + 0x08);
    }
    entry = index - low;
    uint32_t base = run.get(table + 0x10);
    entry = uint32_t(s32(entry) * s32(run.get(table + 0x18)));
    entry = entry + base;
    return entry;
}

// Second lookup and the dispatch through the table entry.
void tableDispatch(Run &run, uint32_t table, uint32_t self, uint32_t index, uint32_t low) {
    run.put(table + 0x20, 0);
    bool outside = false;
    if (s32(index) < s32(low))
        outside = true;
    else if (s32(index) > s32(run.get(table + 0x0c)))
        outside = true;
    if (outside) {
        uint32_t found = run.call(0x4db6e0, table, {index, 0});
        // The grow helper only returns zero after the original has already faulted
        // inside it (realloc failure), so no normal-return path reaches here.
        if (found == 0)
            run.fail(CLAW_FAULT_ABI, 0x4db6e0);
        low = run.get(table + 0x08);
    }
    uint32_t entry = index - low;
    uint32_t base = run.get(table + 0x10);
    entry = uint32_t(s32(entry) * s32(run.get(table + 0x18)));
    entry = entry + base;
    run.call(run.get(entry), self, {});
}

// 0x408510. thiscall, 0 stack argument(s), returns void.
// Sets flag 0x10000 in the flags word at +8 of the object at +0x12c.
uint32_t function_408510(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t inner = run.get(receiver + 0x12c);
    uint32_t flags = run.get(inner + 0x08);
    run.put(inner + 0x08, flags | 0x10000);
    return 0;
}

// 0x408580. thiscall, 1 stack argument(s), returns void.
// Looks up index in the table at 0x534910; with an empty entry it calls 0x473f40.
uint32_t function_408580(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[0];
    uint32_t low = 0;
    uint32_t entry = tableEntry(run, 0x534910, index, low);
    if (run.get(entry) != 0) {
        tableDispatch(run, 0x534910, receiver, index, low);
        return 0;
    }
    run.call(0x473f40, receiver, {index});
    return 0;
}

// 0x408860. thiscall, 0 stack argument(s), returns void.
// Tail jump through virtual slot +0x28.
uint32_t function_408860(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.vcall(receiver, 0x28, {});
    return 0;
}

// 0x408870. thiscall, 0 stack argument(s), returns u32.
// Object fields: +0x08 owner, +0x10 animation owner, +0x68 / +0x70 doubles
// (x / y position), +0x12c sprite, +0x150 and +0x168 frame values.
uint32_t function_408870(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t frameValue = run.get(receiver + 0x150);
    uint32_t spriteField = run.get(sprite + 0x190);
    run.put(receiver + 0x134, spriteField);
    run.call(0x4c8220, sprite + 0x188, {frameValue});
    uint32_t owner = run.get(receiver + 0x0c);
    run.put(owner + 0xcc, 8);
    sprite = run.get(receiver + 0x12c);
    uint32_t spriteFlags = run.get(sprite + 0x08);
    spriteFlags = spriteFlags | 2;
    run.put(sprite + 0x08, spriteFlags);
    uint32_t animation = run.get(receiver + 0x10);
    uint32_t oldState = run.get(animation + 0x1c);
    run.put(receiver + 0x24, oldState);
    uint32_t newState = run.call(0x4dba00, 0x537668, {0x5236fc});
    animation = run.get(receiver + 0x10);
    run.put(animation + 0x1c, newState);
    uint32_t world = run.get(receiver + 0x08);
    double positionY = run.getd(receiver + 0x70);
    uint32_t level = run.get(world + 0x0c);
    uint32_t plane = run.get(level + 0x24);
    uint32_t tileY = run.call_x87(0x4a30e0, 0, positionY, {});
    uint32_t offsetY = run.get(world + 0x124);
    uint32_t pixelY = tileY + offsetY;
    double positionX = run.getd(receiver + 0x68);
    uint32_t pixelX = run.call_x87(0x4a30e0, 0, positionX, {});
    if (s32(pixelX) < 0) {
        pixelX = 0;
    } else {
        uint32_t tiles = run.get(plane + 0x5c);
        uint32_t limit = run.get(tiles + 0x30);
        if (s32(pixelX) >= s32(limit))
            pixelX = limit - 1;
    }
    if (s32(pixelY) < 0) {
        pixelY = 0;
    } else {
        uint32_t tiles = run.get(plane + 0x5c);
        uint32_t limit = run.get(tiles + 0x34);
        if (s32(pixelY) >= s32(limit))
            pixelY = limit - 1;
    }
    uint32_t tiles = run.get(plane + 0x5c);
    uint32_t cellX = pixelX;
    uint32_t cellY = pixelY;
    uint32_t shift = run.get(tiles + 0x8c);
    cellX = uint32_t(s32(cellX) >> (shift & 0x1f));
    shift = run.get(tiles + 0x90);
    cellY = uint32_t(s32(cellY) >> (shift & 0x1f));
    shift = run.get(tiles + 0x8c);
    uint32_t savedCellY = cellY;
    uint32_t scaledX = cellX << (shift & 0x1f);
    shift = run.get(tiles + 0x90);
    uint32_t localX = pixelX - scaledX;
    uint32_t scaledY = savedCellY << (shift & 0x1f);
    uint32_t rows = run.get(tiles + 0x24);
    uint32_t localY = pixelY - scaledY;
    uint32_t rowStart = run.get(rows + savedCellY * 4);
    uint32_t cells = run.get(tiles + 0x20);
    uint32_t cellIndex = rowStart + cellX;
    uint32_t cell = run.get(cells + cellIndex * 4);
    uint32_t hit = 0;
    if (cell != 0xeeeeeeee && cell != 0xffffffff) {
        uint32_t tileTable = run.get(plane + 0x4c);
        uint32_t tile = run.get(tileTable + (cell & 0xffff) * 4);
        hit = run.vcall(tile, 0x20, {localX, localY});
    }
    if (hit == 1)
        run.vcall(receiver, 0x3c, {});
    uint32_t value = run.get(receiver + 0x168);
    run.put(receiver + 0x164, value);
    uint32_t global = run.get(0x537210);
    run.put(receiver + 0x160, global);
    return 0;
}

// 0x43ad20. thiscall, 1 stack argument(s), returns void.
// Same as 0x408580 over the table at 0x5375d8, falling back to 0x408580.
uint32_t function_43ad20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[0];
    uint32_t low = 0;
    uint32_t entry = tableEntry(run, 0x5375d8, index, low);
    if (run.get(entry) != 0) {
        tableDispatch(run, 0x5375d8, receiver, index, low);
        return 0;
    }
    uint32_t fallback[1] = {index};
    function_408580(run, receiver, fallback);
    return 0;
}

// 0x43b120. thiscall, 0 stack argument(s), returns void.
uint32_t function_43b120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t current = run.get(sprite + 0x190);
    uint32_t expected = run.get(receiver + 0x174);
    if (current == expected)
        return 0;
    sprite = run.get(receiver + 0x12c);
    uint32_t frameValue = run.get(receiver + 0x178);
    uint32_t spriteField = run.get(sprite + 0x190);
    run.put(receiver + 0x134, spriteField);
    run.call(0x4c8220, sprite + 0x188, {frameValue});
    return 0;
}

// 0x43b160. thiscall, 0 stack argument(s), returns void.
uint32_t function_43b160(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0xc8, 1);
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t current = run.get(sprite + 0x190);
    uint32_t expected = run.get(receiver + 0x174);
    if (current == expected)
        return 0;
    sprite = run.get(receiver + 0x12c);
    uint32_t spriteField = run.get(sprite + 0x190);
    run.put(receiver + 0x134, spriteField);
    run.call(0x4c8220, sprite + 0x188, {0});
    return 0;
}

// 0x43b1a0. thiscall, 0 stack argument(s), returns void.
uint32_t function_43b1a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0xc8, 1);
    uint32_t linked = run.get(receiver + 0x17c);
    if (linked != 0) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t sound = run.get(0x532c10);
        if (enabled != 0) {
            uint32_t target = run.get(linked + 0x10);
            run.call(0x4b45f0, target, {sound, 0, 0, 0});
        }
    }
    run.vcall(receiver, 0x2c, {});
    return 0;
}

// 0x43b1e0. thiscall, 0 stack argument(s), returns void.
uint32_t function_43b1e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t owner = run.get(receiver + 0x0c);
    if (run.get(owner + 0x64) != 0x2134) {
        run.put(owner + 0x64, 0x2134);
        uint32_t flags = run.get(owner + 0x08);
        run.put(owner + 0x08, flags | 0x20000);
    }
    run.put(receiver + 0xc8, 1);
    return 0;
}

// 0x43b210. thiscall, 0 stack argument(s), returns u32.
uint32_t function_43b210(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t sprite = run.get(receiver + 0x12c);
    run.call(0x4c7970, sprite, {0x526f50});
    uint32_t animation = run.get(receiver + 0x10);
    uint32_t oldState = run.get(animation + 0x1c);
    run.put(receiver + 0x24, oldState);
    uint32_t newState = run.call(0x4dba00, 0x537668, {0x524418});
    animation = run.get(receiver + 0x10);
    run.put(animation + 0x1c, newState);
    sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0xd0, 0x1000000);
    sprite = run.get(receiver + 0x12c);
    uint32_t frameValue = run.get(receiver + 0x174);
    uint32_t spriteField = run.get(sprite + 0x190);
    run.put(receiver + 0x134, spriteField);
    run.call(0x4c8220, sprite + 0x188, {frameValue});
    run.put(receiver + 0x180, 0);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x408510:
        return function_408510(run, receiver, arguments);
    case 0x408580:
        return function_408580(run, receiver, arguments);
    case 0x408860:
        return function_408860(run, receiver, arguments);
    case 0x408870:
        return function_408870(run, receiver, arguments);
    case 0x43ad20:
        return function_43ad20(run, receiver, arguments);
    case 0x43b120:
        return function_43b120(run, receiver, arguments);
    case 0x43b160:
        return function_43b160(run, receiver, arguments);
    case 0x43b1a0:
        return function_43b1a0(run, receiver, arguments);
    case 0x43b1e0:
        return function_43b1e0(run, receiver, arguments);
    case 0x43b210:
        return function_43b210(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_closure_dynamite_01_entry, owned, body)
