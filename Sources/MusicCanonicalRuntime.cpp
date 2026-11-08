// Original XMIDI music manager and resource runtime
//
// Translated from the original packet decompile and disassembly.
// Manager fields: +0x1c current, +0x20 playback parameter, +0x28 enabled.
// Resource fields: +0x44 pause, +0x48 loop, +0x4c saved parameter,
// +0x50/+0x54 defaults, +0x58 sequence, +0x5c payload.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b52a0:
        return 3;
    case 0x4b5300:
        return 0;
    case 0x4b5340:
        return 0;
    case 0x4b53f0:
        return 3;
    case 0x4b5470:
        return 1;
    case 0x4b54a0:
        return 1;
    case 0x4b54f0:
        return 2;
    case 0x4b5550:
        return 0;
    case 0x4b5570:
        return 1;
    case 0x4b55a0:
        return 0;
    case 0x4b55b0:
        return 1;
    case 0x4b55d0:
        return 0;
    case 0x4b55e0:
        return 1;
    case 0x4b5650:
        return 0;
    case 0x4b56a0:
        return 0;
    case 0x4b56b0:
        return 1;
    case 0x4b56d0:
        return 0;
    case 0x4b58a0:
        return 3;
    case 0x4b59c0:
        return 2;
    case 0x4b5a40:
        return 0;
    case 0x4b5a80:
        return 2;
    case 0x4b5ad0:
        return 0;
    case 0x4b5b00:
        return 0;
    case 0x4b5b40:
        return 1;
    case 0x4b5b90:
        return 0;
    case 0x4b5bd0:
        return 0;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

struct Frame {
    Run &run;
    uint32_t saved;
    Frame(Run &run, uint32_t depth) : run(run), saved(run.frame) {
        run.frame -= depth;
    }
    ~Frame() {
        run.frame = saved;
    }
};

uint32_t nested(Run &run, uint32_t function, uint32_t receiver, uint32_t depth, std::initializer_list<uint32_t> arguments = {}) {
    Frame frame(run, depth);
    return body(run, function, receiver, arguments.begin());
}

uint32_t outside(Run &run, uint32_t function, uint32_t receiver, uint32_t depth, std::initializer_list<uint32_t> arguments = {}) {
    uint32_t saved = run.stackPointer;
    run.stackPointer = run.frame - depth;
    uint32_t value = run.call(function, receiver, arguments);
    run.stackPointer = saved;
    return value;
}

uint32_t invoke(Run &run, uint32_t function, uint32_t receiver, uint32_t depth, std::initializer_list<uint32_t> arguments = {}) {
    if (owned(function) >= 0)
        return nested(run, function, receiver, depth, arguments);
    return run.call(function, receiver, arguments);
}

uint32_t method(Run &run, uint32_t receiver, uint32_t offset, uint32_t depth, std::initializer_list<uint32_t> arguments = {}) {
    return invoke(run, run.get(run.get(receiver) + offset), receiver, depth, arguments);
}

void copy(Run &run, uint32_t destination, uint32_t source, uint32_t count) {
    uint32_t index = 0;
    for (; index < (count & ~3u); index += 4) {
        run.put(destination + index, run.get(source + index));
    }
    for (; index < count; ++index) {
        run.put8(destination + index, run.get8(source + index));
    }
}

// 0x4b52a0.
uint32_t function_4b52a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.put(receiver + 0x24, arguments[0]);
    run.put(receiver + 0x20, arguments[1]);
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x28, 1);
    run.put(0x541324, arguments[0]);
    if (!arguments[2]) {
        run.icall(0x546e70);
        uint32_t result = run.icall(0x546e74, {0x54131c, 0, 0xffffffff});
        if (!result && run.get(0x54131c))
            return 1;
    }
    run.put(receiver + 0x28, 0);
    return 1;
}

// 0x4b5300.
uint32_t function_4b5300(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    nested(run, 0x4b5340, receiver, 0x8);
    uint32_t current = run.get(receiver + 0x1c);
    if (current)
        method(run, current, 0x30, 0x8);
    nested(run, 0x4b5340, receiver, 0x8);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x1c, 0);
    run.put(0x54131c, 0);
    return run.icall(0x546e68);
}

// 0x4b5340.
uint32_t function_4b5340(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t current = run.get(receiver + 0x1c);
    if (current)
        method(run, current, 0x30, 0x28);
    uint32_t iterator = run.automatic(-0x10);
    uint32_t name = run.automatic(-0x14);
    uint32_t resource = run.automatic(-0x18);
    run.put(iterator, run.get(receiver + 0x0c) ? 0xffffffff : 0);
    while (run.get(iterator)) {
        outside(run, 0x4f6439, name, 0x28);
        run.put(run.automatic(-0x4), 0);
        run.put(resource, 0);
        outside(run, 0x4f5e1e, receiver, 0x34, {iterator, name, resource});
        uint32_t item = run.get(resource);
        if (item)
            method(run, item, 0x4, 0x2c, {1});
        run.put(run.automatic(-0x4), 0xffffffff);
        outside(run, 0x4f6584, name, 0x28);
    }
    outside(run, 0x4f61a1, receiver, 0x28);
    run.put(receiver + 0x1c, 0);
    return 0;
}

// 0x4b53f0.
uint32_t function_4b53f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t resource = run.call(0x4f63ec, 0, {0x60});
    if (resource) {
        run.put(resource + 0x0, 0x513528);
        run.put8(resource + 0x4, 0);
        run.put(resource + 0x44, 0);
        run.put(resource + 0x48, 0);
        run.put(resource + 0x4c, 0);
        run.put(resource + 0x54, 100);
        run.put(resource + 0x50, 100);
        run.put(resource + 0x58, 0);
        run.put(resource + 0x5c, 0);
    }
    if (!method(run, resource, 0x14, 0x1c, {arguments[0], arguments[1], arguments[2]})) {
        if (resource)
            method(run, resource, 0x4, 0x14, {1});
        return 0;
    }
    nested(run, 0x4b5470, receiver, 0x14, {resource});
    return resource;
}

// 0x4b5470.
uint32_t function_4b5470(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t cell = run.call(0x4f62a8, receiver, {arguments[0] + 0x4});
    run.put(cell, arguments[0]);
    if (!run.get(receiver + 0x1c))
        run.put(receiver + 0x1c, arguments[0]);
    return 0;
}

// 0x4b54a0.
uint32_t function_4b54a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!run.get(receiver + 0x20) || !arguments[0] || !run.get8(arguments[0]))
        return 0;
    uint32_t cell = run.automatic(0x4);
    run.put(cell, 0);
    uint32_t found = outside(run, 0x4f6286, receiver, 0xc, {arguments[0], cell});
    return found ? run.get(cell) : 0;
}

// 0x4b54f0.
uint32_t function_4b54f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!run.get(receiver + 0x28))
        return 0;
    uint32_t item = nested(run, 0x4b54a0, receiver, 0x10, {arguments[0]});
    if (!item)
        return 0;
    nested(run, 0x4b5550, receiver, 0xc);
    if (!method(run, item, 0x24, 0x14, {run.get(receiver + 0x20), arguments[1]}))
        return 0;
    run.put(receiver + 0x1c, item);
    return 1;
}

// 0x4b5550.
uint32_t function_4b5550(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t current = run.get(receiver + 0x1c);
    if (current) {
        method(run, current, 0x30, 0x8);
        run.put(receiver + 0x1c, 0);
    }
    return 0;
}

// 0x4b5570.
uint32_t function_4b5570(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t current = run.get(receiver + 0x1c);
    if (!current)
        return 0;
    method(run, current, 0x30, 0x8);
    return method(run, run.get(receiver + 0x1c), 0x24, 0x10, {run.get(receiver + 0x20), arguments[0]});
}

// 0x4b55a0.
uint32_t function_4b55a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t current = run.get(receiver + 0x1c);
    return current ? method(run, current, 0x28, 0) : 0;
}

// 0x4b55b0.
uint32_t function_4b55b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t current = run.get(receiver + 0x1c);
    return current ? method(run, current, 0x2c, 0x8, {arguments[0]}) : 0;
}

// 0x4b55d0.
uint32_t function_4b55d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t current = run.get(receiver + 0x1c);
    return current ? method(run, current, 0x30, 0) : 0;
}

// 0x4b55e0.
uint32_t function_4b55e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t driver = run.get(0x54131c);
    if (!driver)
        return 0;
    uint32_t volume = arguments[0];
    uint32_t scaled = s32(volume) <= 0 ? 0 : (s32(volume) >= 100 ? 127 : volume * 127 / 100);
    run.icall(0x546e6c, {driver, scaled});
    return 1;
}

// 0x4b5650.
uint32_t function_4b5650(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t driver = run.get(0x54131c);
    if (!driver)
        return 100;
    uint32_t volume = run.icall(0x546e8c, {driver});
    if (s32(volume) <= 0)
        return 0;
    if (s32(volume) >= 127)
        return 100;
    return volume * 100 / 127;
}

// 0x4b56a0.
uint32_t function_4b56a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    return run.get(receiver + 0x58) != 0;
}

// 0x4b56b0.
uint32_t function_4b56b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    nested(run, 0x4b56d0, receiver, 0x8);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4b56d0.
uint32_t function_4b56d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.put(receiver + 0x0, 0x513528);
    run.put(run.automatic(-0x10), receiver);
    run.put(run.automatic(-0x4), 0);
    nested(run, 0x4b5a40, receiver, 0x18);
    run.put(receiver + 0x0, 0x50becc);
    return 0;
}

// 0x4b58a0.
uint32_t function_4b58a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!arguments[0] || arguments[1] < 4 || !run.get(0x54131c))
        return 0;
    run.put(0x541320, run.get(0x541320) + 1);
    run.put(receiver + 0x48, 0);
    run.put(receiver + 0x54, 100);
    run.put(receiver + 0x50, 100);
    if (!arguments[2]) {
        run.call(0x4a3920, 0, {receiver + 0x4, 0x53244c, run.get(0x541320)});
    } else {
        uint32_t count = 0;
        do {
            ++count;
        } while (run.get8(arguments[2] + count - 1));
        copy(run, receiver + 0x4, arguments[2], count);
    }
    if (!run.get(receiver + 0x5c)) {
        uint32_t payload = run.call(0x4f63ec, 0, {arguments[1]});
        run.put(receiver + 0x5c, payload);
        if (!payload)
            return 0;
        copy(run, payload, arguments[0], arguments[1]);
    }
    uint32_t sequence = run.icall(0x546e9c, {run.get(0x54131c)});
    uint32_t payload = run.get(receiver + 0x5c);
    run.put(receiver + 0x58, sequence);
    if (run.icall(0x546e98, {sequence, payload, 0}))
        return 1;
    run.icall(0x546e94, {run.get(receiver + 0x58)});
    run.put(receiver + 0x58, 0);
    return 0;
}

// 0x4b59c0.
uint32_t function_4b59c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t info = run.icall(0x546ac8, {run.get(0x541324), arguments[0], 0x532454});
    if (!info)
        return 0;
    uint32_t data = run.icall(0x546acc, {run.get(0x541324), info});
    if (!data)
        return 0;
    uint32_t payload = run.icall(0x546ac4, {data});
    if (!payload)
        return 0;
    uint32_t size = run.icall(0x546a54, {run.get(0x541324), info});
    return method(run, receiver, 0x14, 0x1c, {payload, size, arguments[1]});
}

// 0x4b5a40.
uint32_t function_4b5a40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    method(run, receiver, 0x30, 0x8);
    uint32_t sequence = run.get(receiver + 0x58);
    if (sequence) {
        run.icall(0x546e94, {sequence});
        run.put(receiver + 0x58, 0);
    }
    uint32_t payload = run.get(receiver + 0x5c);
    if (payload) {
        run.call(0x4f6428, 0, {payload});
        run.put(receiver + 0x5c, 0);
    }
    return 0;
}

// 0x4b5a80.
uint32_t function_4b5a80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!method(run, receiver, 0x20, 0x8))
        return 0;
    uint32_t sequence = run.get(receiver + 0x58);
    run.put(receiver + 0x4c, arguments[0]);
    run.put(receiver + 0x48, arguments[1]);
    run.icall(0x546e90, {sequence});
    if (arguments[1])
        run.icall(0x546e88, {run.get(receiver + 0x58), 0});
    run.put(receiver + 0x44, 0);
    return 1;
}

// 0x4b5ad0.
uint32_t function_4b5ad0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!method(run, receiver, 0x20, 0x8))
        return 0;
    run.icall(0x546e78, {run.get(receiver + 0x58)});
    run.put(receiver + 0x44, 0);
    return 1;
}

// 0x4b5b00.
uint32_t function_4b5b00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!method(run, receiver, 0x20, 0x8))
        return 0;
    if (!nested(run, 0x4b5bd0, receiver, 0x8))
        return 0;
    if (!run.get(receiver + 0x44))
        run.icall(0x546e84, {run.get(receiver + 0x58)});
    run.put(receiver + 0x44, run.get(receiver + 0x44) + 1);
    return 1;
}

// 0x4b5b40.
uint32_t function_4b5b40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!method(run, receiver, 0x20, 0x8))
        return 0;
    if (!nested(run, 0x4b5bd0, receiver, 0x8) && s32(run.get(receiver + 0x44)) > 0) {
        run.put(receiver + 0x44, run.get(receiver + 0x44) - 1);
        if (arguments[0])
            run.put(receiver + 0x44, 0);
        if (s32(run.get(receiver + 0x44)) <= 0)
            run.icall(0x546e80, {run.get(receiver + 0x58)});
    }
    return 1;
}

// 0x4b5b90.
uint32_t function_4b5b90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!method(run, receiver, 0x20, 0x8))
        return 0;
    if (nested(run, 0x4b5bd0, receiver, 0x8))
        return 0;
    uint32_t loop = run.get(receiver + 0x48);
    uint32_t saved = run.get(receiver + 0x4c);
    uint32_t target = run.get(run.get(receiver) + 0x24);
    run.put(receiver + 0x44, 0);
    invoke(run, target, receiver, 0x10, {saved, loop});
    return 1;
}

// 0x4b5bd0.
uint32_t function_4b5bd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!method(run, receiver, 0x20, 0x8))
        return 0;
    uint32_t status = run.icall(0x546e7c, {run.get(receiver + 0x58)});
    return status == 4 || status == 0x10;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b52a0:
        return function_4b52a0(run, receiver, arguments);
    case 0x4b5300:
        return function_4b5300(run, receiver, arguments);
    case 0x4b5340:
        return function_4b5340(run, receiver, arguments);
    case 0x4b53f0:
        return function_4b53f0(run, receiver, arguments);
    case 0x4b5470:
        return function_4b5470(run, receiver, arguments);
    case 0x4b54a0:
        return function_4b54a0(run, receiver, arguments);
    case 0x4b54f0:
        return function_4b54f0(run, receiver, arguments);
    case 0x4b5550:
        return function_4b5550(run, receiver, arguments);
    case 0x4b5570:
        return function_4b5570(run, receiver, arguments);
    case 0x4b55a0:
        return function_4b55a0(run, receiver, arguments);
    case 0x4b55b0:
        return function_4b55b0(run, receiver, arguments);
    case 0x4b55d0:
        return function_4b55d0(run, receiver, arguments);
    case 0x4b55e0:
        return function_4b55e0(run, receiver, arguments);
    case 0x4b5650:
        return function_4b5650(run, receiver, arguments);
    case 0x4b56a0:
        return function_4b56a0(run, receiver, arguments);
    case 0x4b56b0:
        return function_4b56b0(run, receiver, arguments);
    case 0x4b56d0:
        return function_4b56d0(run, receiver, arguments);
    case 0x4b58a0:
        return function_4b58a0(run, receiver, arguments);
    case 0x4b59c0:
        return function_4b59c0(run, receiver, arguments);
    case 0x4b5a40:
        return function_4b5a40(run, receiver, arguments);
    case 0x4b5a80:
        return function_4b5a80(run, receiver, arguments);
    case 0x4b5ad0:
        return function_4b5ad0(run, receiver, arguments);
    case 0x4b5b00:
        return function_4b5b00(run, receiver, arguments);
    case 0x4b5b40:
        return function_4b5b40(run, receiver, arguments);
    case 0x4b5b90:
        return function_4b5b90(run, receiver, arguments);
    case 0x4b5bd0:
        return function_4b5bd0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_music_canonical_entry, owned, body)
