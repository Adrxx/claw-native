// End-of-level application state stack pop and level advance
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
    case 0x429ac0:
        return 0;
    case 0x429be0:
        return 0;
    default:
        return -1;
    }
}

// 0x429ac0. Switches the application to the next state object. Application
// fields: +0x08 owner object, +0x2c current state object. A state object's
// vtable slots used here: +0x10 id, +0x28 leave, +0x24 enter, +0x1c start.
uint32_t function_429ac0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t self = receiver;
    uint32_t vtable = run.get(self);
    uint32_t ready = run.call(run.get(vtable + 0xc), self);
    if (ready == 0)
        return 0;
    uint32_t next = run.call(0x42bfd0, self);
    if (next == 0)
        return 0;
    uint32_t current = run.get(self + 0x2c);
    if (current == next)
        return 0;
    uint32_t carried = 0;
    if (current != 0) {
        uint32_t currentTable = run.get(current);
        carried = run.call(run.get(currentTable + 0x10), current);
        uint32_t nextTable = run.get(next);
        uint32_t oldObject = run.get(self + 0x2c);
        uint32_t oldTable = run.get(oldObject);
        uint32_t nextId = run.call(run.get(nextTable + 0x10), next);
        uint32_t leaving = run.get(self + 0x2c);
        run.call(run.get(oldTable + 0x28), leaving, {nextId});
        uint32_t doomed = run.get(self + 0x2c);
        if (doomed != 0) {
            uint32_t doomedTable = run.get(doomed);
            run.call(run.get(doomedTable + 0x0), doomed, {1});
        }
        run.put(self + 0x2c, 0);
    }
    run.put(self + 0x2c, next);
    run.call(0x42c010, self, {next});
    uint32_t entering = run.get(self + 0x2c);
    uint32_t enteringTable = run.get(entering);
    uint32_t entered = run.call(run.get(enteringTable + 0x24), entering, {carried});
    if (entered == 0) {
        uint32_t started = run.get(self + 0x2c);
        uint32_t startedTable = run.get(started);
        uint32_t result = run.call(run.get(startedTable + 0x1c), started);
        if (result == 0)
            return 0;
    }
    uint32_t owner = run.get(self + 0x08);
    run.put(owner + 0x244, 1);
    run.call(0x42abf0, self);
    return 1;
}

// 0x429be0. When the current state's id is 3, advances to the next level
// (wrapping 1..14) by trying the level loader, at most 14 times; posts a
// command message when the walk returns to the starting level. Fields:
// +0x04 window owner (+0x04 window handle), +0x2c state object (+0x14 level
// number), +0xc0 embedded object.
uint32_t function_429be0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t self = receiver;
    uint32_t state = run.get(self + 0x2c);
    uint32_t stateTable = run.get(state);
    uint32_t id = run.call(run.get(stateTable + 0x10), state);
    if (id != 3)
        return 0;
    run.call(0x4f650f, self + 0xc0);
    uint32_t object = run.get(self + 0x2c);
    uint32_t start = run.get(object + 0x14);
    uint32_t counter = 0xd;
    uint32_t level = start + 1;
    while (true) {
        if (s32(level) > 0xe)
            level = 1;
        if (level == start) {
            uint32_t owner = run.get(self + 0x04);
            uint32_t window = run.get(owner + 0x04);
            run.icall(0x546d50, {window, 0x111, 0x8006, 0});
            return 0;
        }
        uint32_t table = run.get(object);
        uint32_t objectId = run.call(run.get(table + 0x10), object);
        run.call(run.get(table + 0x28), object, {objectId});
        uint32_t loaded = run.call(0x46aeb0, object, {level, 1});
        if (loaded != 0) {
            uint32_t table2 = run.get(object);
            uint32_t id2 = run.call(run.get(table2 + 0x10), object);
            run.call(run.get(table2 + 0x24), object, {id2});
            return 1;
        }
        level = level + 1;
        uint32_t before = counter;
        counter = counter - 1;
        if (s32(before) <= 0)
            break;
    }
    run.call(0x429e10, self, {0x8007, 0x401});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x429ac0:
        return function_429ac0(run, receiver, arguments);
    case 0x429be0:
        return function_429be0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_end_of_level_state_stack_entry, owned, body)
