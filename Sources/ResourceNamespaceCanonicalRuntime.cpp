#include "ClawRuntime.hpp"

namespace resource_namespace_canonical {
using claw::Run;
using claw::s32;

struct Frame {
    Run &run;
    uint32_t saved;
    uint32_t outgoing;
    Frame(Run &run, uint32_t descent) : run(run), saved(run.frame), outgoing(run.stackPointer) {
        run.frame -= descent;
        run.stackPointer = 0;
    }
    ~Frame() {
        run.frame = saved;
        run.stackPointer = outgoing;
    }
};

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

uint32_t nested(Run &run, uint32_t descent, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
    Frame frame(run, descent);
    return body(run, function, receiver, arguments.begin());
}

bool allowed(uint8_t byte) {
    return (byte >= 0x20 && byte <= 0x2e) || (byte >= 0x30 && byte <= 0x39) ||
           (byte >= 0x41 && byte <= 0x5a) || (byte >= 0x61 && byte <= 0x7a);
}

uint32_t length(Run &run, uint32_t text) {
    uint32_t count = 0;
    while (run.get8(text + count))
        ++count;
    return count;
}

// 0x4d54f0: table +0x04 array; buckets have stride 0x10 and link +0x08.
uint32_t function_4d54f0(Run &run, uint32_t table, uint32_t index) {
    uint32_t link = run.get(run.get(table + 0x04) + (index << 4) + 0x08);
    return link ? link - 0x04 : 0;
}

// 0x4d54c0: +0x00 is the unsigned bucket count, reloaded each iteration.
uint32_t function_4d54c0(Run &run, uint32_t table) {
    uint32_t slot = run.get(table + 0x04) + 0x08;
    uint32_t visited = 0;
    do {
        uint32_t link = run.get(slot);
        uint32_t node = link ? link - 0x04 : 0;
        ++visited;
        slot += 0x10;
        if (node)
            return node;
        if (!(visited < run.get(table + 0x00)))
            return node;
    } while (true);
}

// 0x4d5350: node +0x04 next, +0x0c owner, +0x10 bucket index.
uint32_t function_4d5350(Run &run, uint32_t node) {
    uint32_t link = run.get(node + 0x04);
    uint32_t result = link ? link - 0x04 : 0;
    if (result)
        return result;
    uint32_t index = run.get(node + 0x10) + 1;
    uint32_t table = run.get(node + 0x0c);
    uint32_t count = run.get(table + 0x00);
    if (index >= count)
        return result;
    uint32_t slot = run.get(table + 0x04) + (index << 4) + 0x08;
    do {
        link = run.get(slot);
        result = link ? link - 0x04 : 0;
        if (result)
            return result;
        ++index;
        slot += 0x10;
    } while (index < count);
    return result;
}

// 0x4b7f50 and 0x4b8140.
uint32_t hashName(Run &run, uint32_t name, uint32_t divisor) {
    if (!name)
        return 0;
    return length(run, name) % divisor;
}

bool exact(Run &run, uint32_t left, uint32_t right) {
    do {
        uint8_t a = run.get8(left);
        uint8_t b = run.get8(right);
        if (a != b)
            return false;
        if (!a)
            return true;
        a = run.get8(left + 1);
        b = run.get8(right + 1);
        if (a != b)
            return false;
        left += 2;
        right += 2;
        if (!a)
            return true;
    } while (true);
}

// 0x4b7f80 / 0x4b8170: node +0x14 payload; payload +0x00 name.
uint32_t findName(Run &run, uint32_t table, uint32_t name, uint32_t folded, uint32_t divisor) {
    if (!name)
        return 0;
    uint32_t node = function_4d54f0(run, table, hashName(run, name, divisor));
    while (node) {
        uint32_t text = run.get(run.get(node + 0x14) + 0x00);
        bool match;
        if (folded) {
            run.stackPointer = run.frame - 0x1c;
            match = run.call(0x4a3cf0, 0, {text, name}) == 0;
            run.stackPointer = 0;
        } else {
            match = exact(run, text, name);
        }
        if (match)
            return run.get(node + 0x14);
        uint32_t link = run.get(node + 0x04);
        node = link ? link - 0x04 : 0;
    }
    return 0;
}

// 0x4b80e0: numeric key stored at payload +0x00.
uint32_t function_4b80e0(Run &run, uint32_t table, uint32_t key) {
    uint32_t node = function_4d54f0(run, table, key % 9);
    while (node) {
        if (run.get(run.get(node + 0x14) + 0x00) == key)
            return run.get(node + 0x14);
        uint32_t link = run.get(node + 0x04);
        node = link ? link - 0x04 : 0;
    }
    return 0;
}

// 0x4b67f0: namespace +0x44 type table; type +0x24 name table.
uint32_t function_4b67f0(Run &run, uint32_t receiver, uint32_t name, uint32_t type) {
    uint32_t payload = function_4b80e0(run, receiver + 0x44, type);
    if (!payload)
        return 0;
    return nested(run, 0x0c, 0x4b7f80, payload + 0x24, {name, 1});
}

// 0x4b68c0: namespace +0x3c child table.
uint32_t function_4b68c0(Run &run, uint32_t receiver, uint32_t name) {
    if (!name)
        return 0;
    return nested(run, 0x0c, 0x4b8170, receiver + 0x3c, {name, 1});
}

// 0x4b7cd0: physical 64-byte segment at entry ESP-0x40.
uint32_t function_4b7cd0(Run &run, uint32_t receiver, uint32_t path) {
    uint32_t size = length(run, path);
    if (s32(size) > 1 && !allowed(run.get8(path)))
        ++path;
    uint32_t local = run.automatic(-0x40);
    uint32_t index = 0;
    uint8_t byte = run.get8(path);
    while (allowed(byte)) {
        run.put8(local + index, byte);
        ++index;
        byte = run.get8(path + index);
    }
    run.put8(local + index, 0);
    uint32_t child = nested(run, 0x58, 0x4b68c0, receiver, {local});
    if (!child)
        return 0;
    byte = run.get8(path + index);
    if (!byte)
        return child;
    while (!allowed(byte)) {
        ++index;
        byte = run.get8(path + index);
        if (!byte)
            return child;
    }
    return nested(run, 0x58, 0x4b7cd0, child, {path + index});
}

// 0x4b7dc0: leaf ESP-0x120 and directory ESP-0x100 intentionally overlap.
uint32_t function_4b7dc0(Run &run, uint32_t receiver, uint32_t path, uint32_t type) {
    uint32_t size = length(run, path);
    if (s32(size) > 1 && !allowed(run.get8(path))) {
        ++path;
        --size;
    }
    uint32_t index = size - 1;
    while (allowed(run.get8(path + index))) {
        --index;
        if (s32(index) < 0)
            return 0;
    }
    if (index == size)
        return 0;
    uint32_t leaf = run.automatic(-0x120);
    uint32_t source = path + index + 1;
    uint32_t bytes = length(run, source) + 1;
    run.put(run.automatic(-0x124), leaf);
    uint32_t copied = 0;
    while (copied + 4 <= bytes) {
        run.put(leaf + copied, run.get(source + copied));
        copied += 4;
    }
    while (copied < bytes) {
        run.put8(leaf + copied, run.get8(source + copied));
        ++copied;
    }
    if (s32(index) <= 1)
        return nested(run, 0x140, 0x4b67f0, receiver, {leaf, type});
    uint32_t directory = run.automatic(-0x100);
    run.stackPointer = run.frame - 0x144;
    run.call(0x4b0a70, 0, {directory, path, index});
    run.stackPointer = 0;
    run.put8(directory + index, 0);
    uint32_t child = nested(run, 0x13c, 0x4b7cd0, receiver, {directory});
    if (!child)
        return 0;
    return nested(run, 0x140, 0x4b67f0, child, {leaf, type});
}

int arity(uint32_t function) {
    switch (function) {
    case 0x4b68e0:
    case 0x4b6920:
    case 0x4b7540:
    case 0x4d5350:
    case 0x4d54c0:
        return 0;
    case 0x4b68c0:
    case 0x4b6900:
    case 0x4b6940:
    case 0x4b6960:
    case 0x4b6980:
    case 0x4b7cd0:
    case 0x4b7f20:
    case 0x4b7f50:
    case 0x4b8060:
    case 0x4b80d0:
    case 0x4b80e0:
    case 0x4b8140:
    case 0x4d54f0:
        return 1;
    case 0x4b67f0:
    case 0x4b7dc0:
    case 0x4b7f00:
    case 0x4b7f80:
    case 0x4b8170:
        return 2;
    default:
        return -1;
    }
}

uint32_t payload(Run &run, uint32_t node) {
    return node ? run.get(node + 0x14) : 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b67f0:
        return function_4b67f0(run, receiver, arguments[0], arguments[1]);
    case 0x4b68c0:
        return function_4b68c0(run, receiver, arguments[0]);
    case 0x4b68e0:
        return payload(run, function_4d54c0(run, receiver + 0x3c));
    case 0x4b6900:
        return payload(run, function_4d5350(run, arguments[0] + 0x24));
    case 0x4b6920:
        return payload(run, function_4d54c0(run, receiver + 0x44));
    case 0x4b6940:
        return payload(run, function_4d5350(run, arguments[0] + 0x04));
    case 0x4b6960:
        return payload(run, function_4d54c0(run, arguments[0] + 0x1c));
    case 0x4b6980:
        return payload(run, function_4d5350(run, arguments[0] + 0x48));
    case 0x4b7540:
        return run.get(receiver + 0x24);
    case 0x4b7cd0:
        return function_4b7cd0(run, receiver, arguments[0]);
    case 0x4b7dc0:
        return function_4b7dc0(run, receiver, arguments[0], arguments[1]);
    case 0x4b7f00:
        return nested(run, 0x0c, 0x4b7dc0, run.get(receiver + 0x24), {arguments[0], arguments[1]});
    case 0x4b7f20:
        return nested(run, 0x08, 0x4b7cd0, run.get(receiver + 0x24), {arguments[0]});
    case 0x4b7f50:
        return hashName(run, arguments[0], 19);
    case 0x4b7f80:
        return findName(run, receiver, arguments[0], arguments[1], 19);
    case 0x4b8060:
        return arguments[0] % 19;
    case 0x4b80d0:
        return arguments[0] % 9;
    case 0x4b80e0:
        return function_4b80e0(run, receiver, arguments[0]);
    case 0x4b8140:
        return hashName(run, arguments[0], 5);
    case 0x4b8170:
        return findName(run, receiver, arguments[0], arguments[1], 5);
    case 0x4d5350:
        return function_4d5350(run, receiver);
    case 0x4d54c0:
        return function_4d54c0(run, receiver);
    case 0x4d54f0:
        return function_4d54f0(run, receiver, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace resource_namespace_canonical

CLAW_MODULE_ENTRY(claw_resource_namespace_canonical_entry, resource_namespace_canonical::arity, resource_namespace_canonical::body)
