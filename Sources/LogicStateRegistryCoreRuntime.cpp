// Canonical-memory adaptation of the typed LogicStateRegistry Patricia trie
// and indexed tables. Callback addresses remain registration data.
#include "ClawRuntime.hpp"
#include "LogicStateRegistryCoreRuntime.h"

namespace claw::state_registry {
namespace {
uint32_t length(Run &run, uint32_t key) {
    uint32_t n = 0;
    while (run.get8(key + n))
        ++n;
    return n;
}
bool equal(Run &run, uint32_t first, uint32_t second) {
    for (;;) {
        const auto byte = run.get8(first++);
        if (byte != run.get8(second++))
            return false;
        if (!byte)
            return true;
    }
}
uint32_t bit(Run &run, uint32_t key, uint32_t position) {
    return run.get8(key + uint32_t(s32(position) >> 3)) & (1u << (position & 7));
}
uint32_t diagnostic(Run &run, uint32_t function, uint32_t pc, uint32_t ebp) {
    ClawCompilerContext context{};
    context.size = sizeof(context);
    context.version = CLAW_CONTEXT_VERSION;
    context.inputMask = 0x5c1;
    context.outputMask = 0x5c1;
    context.ebp = ebp;
    context.esp = run.automatic(-0x80);
    context.eip = function;
    context.continuation = pc;
    context.fsHead = 0xffffffff;
    run.put(context.esp, pc);
    return run.context_call(function, context);
}
void error(Run &run, uint32_t table, uint32_t message, uint32_t code,
           uint32_t diagnosticFunction, uint32_t pc, uint32_t ebp) {
    const auto location = diagnostic(run, diagnosticFunction, pc, ebp);
    run.put(0x544b14, location);
    run.call(0x4db4d0, run.get(table + 0x04), {table, message, code});
}
void initializeStrings(Run &run, uint32_t table) {
    uint32_t cell = run.get(table + 0x1c);
    uint32_t count = run.get(table + 0x20);
    while (count--) {
        if (cell)
            run.call(0x4f6439, cell);
        cell += 4;
    }
}
uint32_t index(Run &run, uint32_t table, uint32_t key, uint32_t errorMode) {
    // +8/+c signed bounds, +10 storage, +14 fallback, +18 element width;
    // +1c new region and +20 number of newly created elements.
    run.put(table + 0x20, 0);
    if (s32(key) < run.gets(table + 0x08) || run.gets(table + 0x0c) < s32(key)) {
        if (!grow(run, table, key, 0)) {
            const auto message = run.get(0x544b4c);
            if (errorMode == 1)
                run.call(0x406da0, table, {message, 0x0c});
            else
                error(run, table, message, 0x0c, 0x4db5f0, errorMode, 0);
            return run.get(table + 0x14);
        }
    }
    return (key - run.get(table + 0x08)) * run.get(table + 0x18) + run.get(table + 0x10);
}
}
// 0x4dc690: first unequal byte, then its least significant differing bit.
uint32_t differingBit(Run &run, uint32_t first, uint32_t second) {
    uint32_t position = 0;
    while (run.get8(first) == run.get8(second)) {
        ++first;
        ++second;
        position += 8;
    }
    uint32_t difference = run.get8(first) ^ run.get8(second);
    while (!(difference & 1)) {
        ++position;
        difference >>= 1;
    }
    return position;
}
// 0x4db6e0: grow an indexed table on either side, preserving existing cells.
uint32_t grow(Run &run, uint32_t table, uint32_t key, uint32_t margin) {
    const bool lower = s32(key) < run.gets(table + 0x08);
    const auto target = lower ? key - margin : key + margin;
    const auto count = lower ? run.get(table + 0x0c) - target + 1 : target - run.get(table + 0x08) + 1;
    const auto pointer = run.call(0x4a9070, 0, {run.get(table + 0x10), count * run.get(table + 0x18)});
    if (!pointer) {
        error(run, table, 0x533428, 0x22, 0x4dc680, 0x4db78d, 0);
        return 0;
    }
    if (lower) {
        const auto changed = run.get(table + 0x08) - target;
        const auto oldBytes = (run.get(table + 0x0c) - run.get(table + 0x08) + 1) * run.get(table + 0x18);
        run.put(table + 0x20, changed);
        run.put(table + 0x1c, pointer);
        run.call(0x4a5290, 0, {pointer + changed * run.get(table + 0x18), pointer, oldBytes});
        const auto bytes = run.get(table + 0x20) * run.get(table + 0x18);
        const auto region = run.get(table + 0x1c);
        for (uint32_t i = 0; i < bytes; ++i)
            run.put8(region + i, 0);
        run.put(table + 0x08, target);
    } else {
        const auto oldBytes = (run.get(table + 0x0c) - run.get(table + 0x08) + 1) * run.get(table + 0x18);
        const auto changed = target - run.get(table + 0x0c);
        run.put(table + 0x20, changed);
        run.put(table + 0x1c, pointer + oldBytes);
        const auto bytes = changed * run.get(table + 0x18);
        for (uint32_t i = 0; i < bytes; ++i)
            run.put8(pointer + oldBytes + i, 0);
        run.put(table + 0x0c, target);
    }
    run.put(table + 0x10, pointer);
    return pointer;
}
// 0x4dba00: +18 root, +1c prior, +20 candidate, +24 key bound,
// +28 lookup-miss flag. Node +8 bit position, +c key and +10 value.
uint32_t find(Run &run, uint32_t table, uint32_t key) {
    if (!key) {
        error(run, table, run.get(0x544b3c), 0x16, 0x4dc680, 0x4dba19, 0);
        return 0;
    }
    uint32_t node = run.get(table + 0x18);
    run.put(table + 0x1c, node);
    run.put(table + 0x20, 0);
    run.put(table + 0x28, 1);
    const auto bound = length(run, key) * 8 + 7;
    run.put(table + 0x24, bound);
    if (!node)
        return 0;
    uint32_t position = run.get(node + 0x08);
    for (;;) {
        if (s32(bound) < s32(position)) {
            run.put(table + 0x20, run.get(table + 0x1c));
            return 0;
        }
        node = run.get(run.get(table + 0x1c) + (bit(run, key, position) ? 0x04 : 0x00));
        run.put(table + 0x20, node);
        if (!node)
            return 0;
        if (run.gets(node + 0x08) <= s32(position)) {
            if (equal(run, key, run.get(node + 0x0c))) {
                run.put(table + 0x28, 0);
                return run.get(run.get(table + 0x20) + 0x10);
            }
            return 0;
        }
        run.put(table + 0x1c, node);
        position = run.get(node + 0x08);
    }
}
// 0x4db7f0: insert after a lookup miss; retain the typed Patricia links.
uint32_t insert(Run &run, uint32_t table, uint32_t key, uint32_t value) {
    if (!run.get(table + 0x28)) {
        error(run, table, 0x533438, 0x16, 0x4dc680, 0x4db803, 0);
        return 0;
    }
    uint32_t different = run.get(table + 0x24);
    run.put(table + 0x28, 0);
    run.put(table + 0x24, different - 7);
    if (!key || !value) {
        error(run, table, run.get(0x544b3c), 0x16, 0x4dc680, 0x4db9d5, key);
        return 0;
    }
    if (run.get(table + 0x20))
        different = differingBit(run, key, run.get(run.get(table + 0x20) + 0x0c));
    else
        different -= 8;
    const auto node = run.call(0x4f63ec, 0, {0x14});
    if (node) {
        run.put(node + 0x10, value);
        run.put(node + 0x08, different);
        const auto keyToken = run.call(0x4f63ec, 0, {uint32_t(run.gets(table + 0x24) >> 3) + 1});
        run.put(node + 0x0c, keyToken);
        if (keyToken) {
            const auto bytes = length(run, key) + 1;
            for (uint32_t i = 0; i < bytes; ++i)
                run.put8(keyToken + i, run.get8(key + i));
            const auto direction = bit(run, key, different);
            run.put(node + (direction ? 0x04 : 0x00), node);
            auto parent = run.get(table + 0x1c);
            if (parent) {
                if (run.gets(parent + 0x08) <= s32(different))
                    run.put(parent + (bit(run, key, run.get(parent + 0x08)) ? 0x04 : 0x00), node);
                else {
                    run.put(table + 0x1c, 0);
                    run.put(table + 0x20, run.get(table + 0x18));
                    uint32_t lastDirection = value;
                    uint32_t cursor = run.get(run.get(table + 0x18) + 0x08);
                    while (s32(cursor) <= s32(different)) {
                        parent = run.get(table + 0x20);
                        run.put(table + 0x1c, parent);
                        lastDirection = bit(run, key, run.get(parent + 0x08));
                        const auto next = run.get(parent + (lastDirection ? 0x04 : 0x00));
                        run.put(table + 0x20, next);
                        cursor = run.get(next + 0x08);
                    }
                    parent = run.get(table + 0x1c);
                    if (parent)
                        run.put(parent + (lastDirection ? 0x04 : 0x00), node);
                    else
                        run.put(table + 0x18, node);
                }
            } else
                run.put(table + 0x18, node);
            run.put(node + (direction ? 0x00 : 0x04), run.get(table + 0x20));
            run.put(table + 0x14, run.get(table + 0x14) + 1);
            return value;
        }
    }
    error(run, table, run.get(0x544b4c), 0x0c, 0x4dc680, 0x4db8ab, key);
    return 0;
}
// 0x406020: index and construct each newly exposed CString cell.
uint32_t stringIndex(Run &run, uint32_t table, uint32_t key) {
    const auto slot = index(run, table, key, 0x406072);
    initializeStrings(run, table);
    return slot;
}
uint32_t registerBinding(Run &run, uint32_t table, uint32_t literal, uint32_t callback,
                         uint32_t nameMode, uint32_t tableMode,
                         uint32_t nameErrorMode, uint32_t tableErrorMode) {
    uint32_t id = find(run, 0x537668, literal);
    if (!id) {
        insert(run, 0x537668, literal, run.get(0x52712c));
        id = run.get(0x52712c);
        uint32_t slot;
        if (nameMode == 2)
            slot = stringIndex(run, 0x537698, id);
        else {
            slot = nameMode == 1 ? run.call(0x441030, 0x537698, {id}) : index(run, 0x537698, id, nameErrorMode);
            initializeStrings(run, 0x537698);
        }
        run.call(0x4f66cc, slot, {literal});
        run.put(0x52712c, run.get(0x52712c) + 1);
    }
    const auto cell = tableMode == 1 ? run.call(0x441030, table, {id}) : index(run, table, id, tableErrorMode);
    run.put(cell, callback);
    return id;
}
} // namespace claw::state_registry

namespace {
using claw::Run;
using namespace claw::state_registry;
int owned(uint32_t function) {
    switch (function) {
    case 0x4db6e0:
    case 0x4db7f0:
    case 0x4dc690:
        return 2;
    case 0x4dba00:
    case 0x406020:
        return 1;
    case 0x4036c0:
    case 0x404420:
    case 0x406640:
    case 0x407010:
    case 0x407620:
    case 0x408690:
        return 0;
    default:
        return -1;
    }
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4db6e0:
        return grow(run, receiver, arguments[0], arguments[1]);
    case 0x4db7f0:
        return insert(run, receiver, arguments[0], arguments[1]);
    case 0x4dba00:
        return find(run, receiver, arguments[0]);
    case 0x4dc690:
        return differingBit(run, arguments[0], arguments[1]);
    case 0x406020:
        return stringIndex(run, receiver, arguments[0]);
    // Registration descriptors retain the original order and literal identity.
    case 0x4036c0:
        registerBinding(run, 0x534820, 0x523148, 0x4038d0, 0, 0, 0x40375b, 0x403824);
        return 0;
    case 0x404420: {
        if (!claw::state_registry::equal(run, 0x523274, 0x52327c))
            run.call(0x40e390, 0);
        const uint32_t bindings[][2] = {
            {0x523268, 0x4441b0}, {0x523148, 0x4051a0}, {0x523258, 0x405640},
            {0x52324c, 0x4057a0}, {0x52323c, 0x405540}, {0x523228, 0x4059e0},
            {0x52321c, 0x405440}, {0x523210, 0x405a60}, {0x523204, 0x405a60}
        };
        for (const auto &binding : bindings)
            registerBinding(run, 0x534850, binding[0], binding[1], 1, 1);
        registerBinding(run, 0x534850, 0x5231f8, 0x405df0, 2, 1);
        return 0;
    }
    case 0x406640:
        registerBinding(run, 0x534888, 0x523148, 0x406b10, 0, 0, 1, 1);
        registerBinding(run, 0x534888, 0x5234fc, 0x406c40, 0, 0, 0x406808, 1);
        return 0;
    case 0x407010:
        registerBinding(run, 0x5348b8, 0x523148, 0x458570, 0, 0, 0x4070ab, 0x407174);
        return 0;
    case 0x407620:
        registerBinding(run, 0x5348e8, 0x523604, 0x407cc0, 1, 1);
        registerBinding(run, 0x5348e8, 0x5235f8, 0x407e40, 1, 1);
        registerBinding(run, 0x5348e8, 0x5235f0, 0x407f20, 1, 1);
        registerBinding(run, 0x5348e8, 0x5235e4, 0x42a680, 0, 1, 1);
        return 0;
    case 0x408690:
        if (!claw::state_registry::equal(run, 0x523708, 0x523714))
            run.call(0x474060, 0);
        registerBinding(run, 0x534910, 0x5236fc, 0x4089d0, 0, 0, 0x40876b, 0x408834);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_logic_state_registry_core_entry, owned, body)
