// Original resource table construction
//
// Canonical translation from the original packet instructions.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b64b0:
        return 1;
    case 0x4b6530:
        return 0;
    case 0x4b6600:
        return 6;
    case 0x4b66d0:
        return 0;
    case 0x4b69a0:
        return 1;
    case 0x4b6a60:
        return 3;
    case 0x4b7170:
        return 1;
    case 0x4b7cc0:
        return 0;
    case 0x4b7f40:
        return 0;
    case 0x4b8050:
        return 0;
    case 0x4b8070:
        return 1;
    case 0x4b80c0:
        return 0;
    case 0x4b8130:
        return 0;
    case 0x4d53a0:
        return 1;
    case 0x4d5410:
        return 0;
    case 0x4d5420:
        return 0;
    case 0x4d5450:
        return 1;
    case 0x4d5490:
        return 1;
    default:
        return -1;
    }
}

uint32_t function_4b64b0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b6530(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b6600(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b66d0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b69a0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b6a60(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b7170(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b7cc0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b7f40(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b8050(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b8070(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b80c0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b8130(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4d53a0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4d5410(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4d5420(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4d5450(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4d5490(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x4b64b0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4b64b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x04, 0x513570); // Embedded hash-node vtable.
    run.put(receiver + 0x18, 0); // Payload pointer.
    const uint32_t count[] = {0x13};
    function_4d53a0(run, receiver + 0x1c, count); // Numeric table.
    function_4d53a0(run, receiver + 0x24, count); // Name table.
    run.put(receiver + 0x00, arguments[0]); // Group key.
    run.put(receiver + 0x18, receiver);
    return receiver;
}

// 0x4b6530. thiscall, 0 stack argument(s), returns void.
uint32_t function_4b6530(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t node = run.call(0x4d54c0, receiver + 0x1c, {});
    while (node) {
        uint32_t next = run.call(0x4d5350, node, {});
        const uint32_t args[] = {node};
        function_4d5490(run, receiver + 0x1c, args);
        node = next;
    }
    node = run.call(0x4d54c0, receiver + 0x24, {});
    while (node) {
        uint32_t next = run.call(0x4d5350, node, {});
        const uint32_t args[] = {node};
        function_4d5490(run, receiver + 0x24, args);
        uint32_t payload = run.get(node + 0x14);
        if (payload) {
            run.call(0x4b6120, payload, {});
            run.call(0x4f6428, 0, {payload});
        }
        node = next;
    }
    run.put(receiver + 0x00, 0);
    run.put(receiver + 0x18, 0);
    function_4d5420(run, receiver + 0x24, nullptr);
    function_4d5420(run, receiver + 0x1c, nullptr);
    return 0;
}

// 0x4b6600. thiscall, 6 stack argument(s), returns u32.
uint32_t function_4b6600(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x24, 0x513574); // Directory hash-node vtable.
    run.put(receiver + 0x38, 0); // Directory payload pointer.
    const uint32_t five[] = {5};
    function_4d53a0(run, receiver + 0x3c, five); // Directory child table.
    const uint32_t nine[] = {9};
    function_4d53a0(run, receiver + 0x44, nine); // Group child table.
    uint32_t length = 0;
    while (run.get8(arguments[2] + length++)) {}
    uint32_t name = run.call(0x4f63ec, 0, {length});
    run.put(receiver + 0x00, name); // Copied name pointer.
    if (name) {
        length = 0;
        while (run.get8(arguments[2] + length++)) {}
        uint32_t offset = 0;
        for (; offset + 4 <= length; offset += 4) {
            run.put(name + offset, run.get(arguments[2] + offset));
        }
        for (; offset < length; ++offset) {
            run.put8(name + offset, run.get8(arguments[2] + offset));
        }
    }
    run.put(receiver + 0x14, arguments[5]); // Timestamp.
    run.put(receiver + 0x08, arguments[4]);
    run.put(receiver + 0x18, arguments[0]); // Root/context.
    run.put(receiver + 0x04, arguments[3]);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x20, 0); // Auxiliary owned pointer.
    run.put(receiver + 0x1c, arguments[1]); // Parent directory.
    run.put(receiver + 0x38, receiver);
    return receiver;
}

// 0x4b66d0. thiscall, 0 stack argument(s), returns void.
uint32_t function_4b66d0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t node = run.call(0x4d54c0, receiver + 0x44, {});
    while (node) {
        uint32_t next = run.call(0x4d5350, node, {});
        const uint32_t args[] = {node};
        function_4d5490(run, receiver + 0x44, args);
        uint32_t payload = run.get(node + 0x14);
        if (payload) {
            function_4b6530(run, payload, nullptr);
            run.call(0x4f6428, 0, {payload});
        }
        node = next;
    }
    node = run.call(0x4d54c0, receiver + 0x3c, {});
    while (node) {
        uint32_t next = run.call(0x4d5350, node, {});
        const uint32_t args[] = {node};
        function_4d5490(run, receiver + 0x3c, args);
        uint32_t payload = run.get(node + 0x14);
        if (payload) {
            function_4b66d0(run, payload, nullptr);
            run.call(0x4f6428, 0, {payload});
        }
        node = next;
    }
    uint32_t name = run.get(receiver + 0x00);
    if (name)
        run.call(0x4f6428, 0, {name});
    uint32_t auxiliary = run.get(receiver + 0x20);
    if (auxiliary)
        run.call(0x4f6428, 0, {auxiliary});
    run.put(receiver + 0x00, 0);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x38, 0);
    function_4d5420(run, receiver + 0x44, nullptr);
    function_4d5420(run, receiver + 0x3c, nullptr);
    return 0;
}

// 0x4b69a0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4b69a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t name = arguments[0];
    if (run.call(0x4b8170, receiver + 0x3c, {name, 1}))
        return 0;
    uint32_t directory = run.call(0x4f63ec, 0, {0x4c});
    if (!directory)
        return 0;
    uint32_t frame = run.frame;
    run.frame = frame - 0x20;
    uint32_t time = function_4b7cc0(run, 0, nullptr);
    run.frame = frame;
    const uint32_t args[] = {run.get(receiver + 0x18), receiver, name, 0, 0, time};
    directory = function_4b6600(run, directory, args);
    if (!directory)
        return 0;
    const uint32_t node[] = {directory + 0x24};
    function_4d5450(run, receiver + 0x3c, node);
    uint32_t root = run.get(receiver + 0x18);
    uint32_t length = 0;
    while (run.get8(name + length))
        ++length;
    if (run.get(root + 0x38) <= length)
        run.put(root + 0x38, length + 1);
    return directory;
}

// 0x4b6a60. thiscall, 3 stack argument(s), returns u32.
uint32_t function_4b6a60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t groupArgs[] = {arguments[2]};
    uint32_t group = function_4b7170(run, receiver, groupArgs);
    const uint32_t keyArgs[] = {arguments[0]};
    if (function_4b8070(run, group + 0x1c, keyArgs))
        return 0;
    uint32_t name = arguments[1];
    if (run.call(0x4b7f80, group + 0x24, {name, 1}))
        return 0;
    uint32_t resource = run.call(0x4f63ec, 0, {0x60});
    if (!resource)
        return 0;
    uint32_t frame = run.frame;
    run.frame = frame - 0x2c;
    uint32_t time = function_4b7cc0(run, 0, nullptr);
    run.frame = frame;
    resource = run.call(0x4b5ff0, resource, {receiver, name, arguments[0], group, 0, 0, 0, time, 0, 0});
    if (!resource)
        return 0;
    const uint32_t numericNode[] = {resource + 0x48};
    function_4d5450(run, group + 0x1c, numericNode);
    const uint32_t nameNode[] = {resource + 0x30};
    function_4d5450(run, group + 0x24, nameNode);
    uint32_t root = run.get(receiver + 0x18);
    uint32_t length = 0;
    while (run.get8(name + length))
        ++length;
    if (run.get(root + 0x3c) <= length)
        run.put(root + 0x3c, length + 1);
    return resource;
}

// 0x4b7170. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4b7170(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t group = run.call(0x4b80e0, receiver + 0x44, {arguments[0]});
    if (group)
        return group;
    group = run.call(0x4f63ec, 0, {0x2c});
    if (!group)
        return 0;
    group = function_4b64b0(run, group, arguments);
    if (!group)
        return 0;
    const uint32_t node[] = {group + 0x04};
    function_4d5450(run, receiver + 0x44, node);
    return group;
}

// 0x4b7cc0. cdecl, 0 stack argument(s), returns u32.
uint32_t function_4b7cc0(Run &run, uint32_t, const uint32_t *) {
    uint32_t previousStackPointer = run.stackPointer;
    run.stackPointer = run.frame - 0x0c; // PUSH ECX, argument and return word.
    uint32_t value = run.call(0x4a3b10, 0, {run.automatic(-4)});
    run.stackPointer = previousStackPointer;
    return value;
}

// 0x4b7f40. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4b7f40(Run &run, uint32_t receiver, const uint32_t *) {
    return run.call(0x4b7f50, 0, {run.get(run.get(receiver + 0x14) + 0x00)});
}

// 0x4b8050. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4b8050(Run &run, uint32_t receiver, const uint32_t *) {
    return run.call(0x4b8060, 0, {run.get(run.get(receiver + 0x14) + 0x04)});
}

// 0x4b8070. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4b8070(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t hash = run.call(0x4b8060, 0, {arguments[0]});
    uint32_t node = run.call(0x4d54f0, receiver, {hash});
    while (node) {
        if (run.get(run.get(node + 0x14) + 0x04) == arguments[0])
            return run.get(node + 0x14);
        uint32_t link = run.get(node + 0x04);
        node = link ? link - 4 : 0;
    }
    return 0;
}

// 0x4b80c0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4b80c0(Run &run, uint32_t receiver, const uint32_t *) {
    return run.call(0x4b80d0, 0, {run.get(run.get(receiver + 0x14) + 0x00)});
}

// 0x4b8130. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4b8130(Run &run, uint32_t receiver, const uint32_t *) {
    return run.call(0x4b8140, 0, {run.get(run.get(receiver + 0x14) + 0x00)});
}

// 0x4d53a0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4d53a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t count = arguments[0];
    run.put(receiver + 0x00, count); // Table bucket count.
    uint32_t base = run.call(0x4f63ec, 0, {count * 0x10 + 4});
    uint32_t array = 0;
    if (base) {
        array = base + 4;
        run.put(base + 0x00, count); // Array allocation count prefix.
        run.call(0x4a4590, 0, {array, 0x10, count, 0x4d5410, 0x4c96b0});
    }
    run.put(receiver + 0x04, array); // Table bucket array.
    return receiver;
}

// 0x4d5410. thiscall, 0 stack argument(s), returns void.
uint32_t function_4d5410(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x08, 0); // Bucket list head.
    run.put(receiver + 0x0c, 0); // Bucket list tail.
    return 0;
}

// 0x4d5420. thiscall, 0 stack argument(s), returns void.
uint32_t function_4d5420(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t array = run.get(receiver + 0x04);
    if (array) {
        uint32_t base = array - 4;
        run.call(0x4a4450, 0, {array, 0x10, run.get(base), 0x4c96b0});
        run.call(0x4f6428, 0, {base});
    }
    return 0;
}

// 0x4d5450. thiscall, 1 stack argument(s), returns void.
uint32_t function_4d5450(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t node = arguments[0];
    uint32_t method = run.get(run.get(node));
    uint32_t hash = 0;
    switch (method) {
    case 0x4b7f40:
        hash = function_4b7f40(run, node, nullptr);
        break;
    case 0x4b8050:
        hash = function_4b8050(run, node, nullptr);
        break;
    case 0x4b80c0:
        hash = function_4b80c0(run, node, nullptr);
        break;
    case 0x4b8130:
        hash = function_4b8130(run, node, nullptr);
        break;
    default:
        hash = run.call(method, node, {});
        break;
    }
    run.put(node + 0x0c, receiver); // Node owner table.
    run.put(node + 0x10, hash); // Node bucket index.
    uint32_t link = node ? node + 4 : 0;
    run.call(0x4b5210, run.get(receiver + 0x04) + hash * 0x10 + 8, {link});
    return 0;
}

// 0x4d5490. thiscall, 1 stack argument(s), returns void.
uint32_t function_4d5490(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t node = arguments[0];
    uint32_t link = node ? node + 4 : 0;
    uint32_t array = run.get(receiver + 0x04);
    uint32_t hash = run.get(node + 0x10);
    run.call(0x4b5270, array + hash * 0x10 + 8, {link});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b64b0:
        return function_4b64b0(run, receiver, arguments);
    case 0x4b6530:
        return function_4b6530(run, receiver, arguments);
    case 0x4b6600:
        return function_4b6600(run, receiver, arguments);
    case 0x4b66d0:
        return function_4b66d0(run, receiver, arguments);
    case 0x4b69a0:
        return function_4b69a0(run, receiver, arguments);
    case 0x4b6a60:
        return function_4b6a60(run, receiver, arguments);
    case 0x4b7170:
        return function_4b7170(run, receiver, arguments);
    case 0x4b7cc0:
        return function_4b7cc0(run, receiver, arguments);
    case 0x4b7f40:
        return function_4b7f40(run, receiver, arguments);
    case 0x4b8050:
        return function_4b8050(run, receiver, arguments);
    case 0x4b8070:
        return function_4b8070(run, receiver, arguments);
    case 0x4b80c0:
        return function_4b80c0(run, receiver, arguments);
    case 0x4b8130:
        return function_4b8130(run, receiver, arguments);
    case 0x4d53a0:
        return function_4d53a0(run, receiver, arguments);
    case 0x4d5410:
        return function_4d5410(run, receiver, arguments);
    case 0x4d5420:
        return function_4d5420(run, receiver, arguments);
    case 0x4d5450:
        return function_4d5450(run, receiver, arguments);
    case 0x4d5490:
        return function_4d5490(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_resource_table_construction_entry, owned, body)
