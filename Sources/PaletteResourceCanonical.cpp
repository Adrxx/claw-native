// Original PAL resource and physical palette orchestration
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
    case 0x4bb2a0:
        return 0;
    case 0x4d4810:
        return 0;
    case 0x4d6670:
        return 0;
    case 0x4d6690:
        return 0;
    case 0x4bb870:
        return 0;
    case 0x4bbf60:
        return 0;
    case 0x4bc9b0:
        return 1;
    case 0x4bca10:
        return 1;
    case 0x4d47f0:
        return 1;
    case 0x4bcac0:
        return 2;
    case 0x4bcb40:
        return 2;
    case 0x4d65a0:
        return 2;
    case 0x4d65e0:
        return 2;
    case 0x4b96f0:
        return 2;
    case 0x4d6620:
        return 3;
    case 0x4d4420:
        return 3;
    case 0x4d44f0:
        return 3;
    case 0x4d4570:
        return 3;
    case 0x4bcbc0:
        return 3;
    case 0x4bb100:
        return 3;
    case 0x4bb240:
        return 3;
    case 0x4bb5a0:
        return 4;
    case 0x4bb800:
        return 4;
    case 0x4bb910:
        return 6;
    case 0x4bb990:
        return 6;
    case 0x4d4240:
        return 0;
    case 0x4d45f0:
        return 3;
    case 0x4d46f0:
        return 1;
    default:
        return -1;
    }
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// Each offset is the physical callee-entry ESP observed at its CALL.
uint32_t nested(Run &run, uint32_t function, uint32_t receiver, int32_t offset,
                std::initializer_list<uint32_t> arguments = {}) {
    uint32_t frame = run.frame;
    uint32_t stack = run.stackPointer;
    run.frame = run.automatic(offset);
    run.stackPointer = 0;
    uint32_t result = body(run, function, receiver, arguments.begin());
    run.frame = frame;
    run.stackPointer = stack;
    return result;
}
uint32_t outside(Run &run, uint32_t function, uint32_t receiver, int32_t offset,
                 std::initializer_list<uint32_t> arguments = {}) {
    run.stackPointer = run.automatic(offset);
    return run.call(function, receiver, arguments);
}
uint32_t method(Run &run, uint32_t object, uint32_t slot, int32_t offset,
                std::initializer_list<uint32_t> arguments = {}) {
    uint32_t target = run.get(run.get(object) + slot);
    if (owned(target) >= 0)
        return nested(run, target, object, offset, arguments);
    return outside(run, target, object, offset, arguments);
}
uint32_t com(Run &run, uint32_t object, uint32_t slot, int32_t offset,
             std::initializer_list<uint32_t> arguments) {
    return outside(run, run.get(run.get(object) + slot), 0, offset, arguments);
}
void report(Run &run, uint32_t source, uint32_t line, uint32_t error, int32_t offset) {
    outside(run, 0x4bd260, 0, offset, {source, line, error});
}
void copyName(Run &run, uint32_t destination, uint32_t source) {
    uint32_t count = 1;
    while (run.get8(source + count - 1))
        ++count;
    uint32_t index = 0;
    for (; index + 4 <= count; index += 4)
        run.put(destination + index, run.get(source + index));
    for (; index < count; ++index)
        run.put8(destination + index, run.get8(source + index));
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    // Backend +4 COM palette; +0xc entries; +0x10 backup; +0x18 auxiliary.
    switch (function) {
    // 0x4bb2a0 destroyBackend.
    case 0x4bb2a0: {
        uint32_t entries = run.get(receiver + 0xc);
        run.put(receiver + 0x4, 0);
        run.put(receiver + 0x0, 0);
        run.put(receiver + 0x8, 0);
        if (entries) {
            outside(run, 0x4f6428, 0, -0x10, {entries});
            run.put(receiver + 0xc, 0);
        }
        for (uint32_t offset : {0x10u, 0x18u}) {
            uint32_t pointer = run.get(receiver + offset);
            if (pointer) {
                outside(run, 0x4f6428, 0, -0x10, {pointer});
                run.put(receiver + offset, 0);
            }
        }
        run.put(receiver + 0x34, 0);
        return 0;
    }
    // 0x4d4810 destroyWrapper.
    case 0x4d4810:
        run.put(receiver + 0x0, 0x513d78);
        nested(run, 0x4d6670, receiver, -0x18);
        run.put(receiver + 0x4, 0xffffffff);
        run.put(receiver + 0x8, 0);
        run.put(receiver + 0xc, 0);
        run.put(receiver + 0x0, 0x50becc);
        return 0;
    // 0x4d6670 unloadWrapper; wrapper +0xc context, +0x10 backend.
    case 0x4d6670: {
        uint32_t backend = run.get(receiver + 0x10);
        if (backend) {
            nested(run, 0x4bca10, run.get(run.get(receiver + 0xc) + 0x1c), -0xc, {backend});
            run.put(receiver + 0x10, 0);
        }
        return 0;
    }
    // 0x4d6690 applyWrapper.
    case 0x4d6690: {
        uint32_t display = run.get(run.get(run.get(receiver + 0xc) + 0x4) + 0x10);
        if (run.get(display + 0x18) != 8)
            return 1;
        return nested(run, 0x4b96f0, run.get(display + 0x2c), -0xc, {run.get(receiver + 0x10), 0});
    }
    // 0x4bb870 backupEntries.
    case 0x4bb870: {
        if (!run.get(receiver + 0x10)) {
            uint32_t buffer = outside(run, 0x4f63ec, 0, -0xc, {0x400});
            run.put(receiver + 0x10, buffer);
            if (!buffer)
                return 0;
        }
        uint32_t palette = run.get(receiver + 0x4);
        uint32_t result = com(run, palette, 0x10, -0x1c, {palette, 0, 0, 0x100, run.get(receiver + 0x10)});
        if (result)
            report(run, 0x532500, 0x261, result, -0x14);
        return 0;
    }
    // 0x4bbf60 applySystemPalette.
    case 0x4bbf60: {
        uint32_t dc = outside(run, 0x546910, 0, -0x434, {0x53251c, 0, 0, 0});
        if (!dc)
            return 0;
        uint32_t caps = run.get(0x546894);
        uint32_t size = outside(run, caps, 0, -0x42c, {dc, 0x68});
        uint32_t reserved = outside(run, caps, 0, -0x42c, {dc, 0x6a});
        uint32_t half = uint32_t(s32(reserved) / 2);
        uint32_t local = run.automatic(-0x400);
        run.put16(local - 0x4, 0x300);
        run.put16(local - 0x2, 0x100);
        if (!outside(run, 0x546914, 0, -0x434, {dc, 0, half, local}))
            return 0;
        uint32_t start = size - half;
        uint32_t output = local + (run.get16(local - 0x2) - half) * 4;
        if (!outside(run, 0x546914, 0, -0x434, {dc, start, half, output}))
            return 0;
        outside(run, 0x5468b0, 0, -0x428, {dc});
        uint32_t entries = run.get(receiver + 0xc);
        if (!entries)
            return 0;
        for (uint32_t i = 0; s32(i) < s32(half); ++i) {
            run.put8(entries + i * 4, run.get8(local + i * 4));
            run.put8(entries + i * 4 + 0x1, run.get8(local + i * 4 + 0x1));
            run.put8(entries + i * 4 + 0x2, run.get8(local + i * 4 + 0x2));
        }
        for (uint32_t i = start; s32(i) < s32(size); ++i) {
            run.put8(entries + i * 4, run.get8(local + i * 4));
            run.put8(entries + i * 4 + 0x1, run.get8(local + i * 4 + 0x1));
            run.put8(entries + i * 4 + 0x2, run.get8(local + i * 4 + 0x2));
        }
        uint32_t result = nested(run, 0x4bb800, receiver, -0x434, {0, 0x100, entries, 0});
        if (!result)
            return 1;
        report(run, 0x532500, 0x491, result, -0x430);
        return 0;
    }
    // 0x4bc9b0 registerBackend; manager list embedded at +0x3d4.
    case 0x4bc9b0: {
        uint32_t node = outside(run, 0x4f51c5, receiver + 0x3d4, -0xc, {arguments[0]});
        run.put(arguments[0] + 0x0, node);
        return 0;
    }
    // 0x4bca10 removeBackend.
    case 0x4bca10:
        outside(run, 0x4f5212, receiver + 0x3d4, -0xc, {run.get(arguments[0])});
        if (arguments[0]) {
            nested(run, 0x4bb2a0, arguments[0], -0x8);
            outside(run, 0x4f6428, 0, -0xc, {arguments[0]});
        }
        return 0;
    // 0x4d47f0 deleteWrapper.
    case 0x4d47f0:
        nested(run, 0x4d4810, receiver, -0x8);
        if (arguments[0] & 1)
            outside(run, 0x4f6428, 0, -0xc, {receiver});
        return receiver;
    // 0x4bcac0, 0x4bcb40, 0x4bcbc0 backend factories.
    case 0x4bcac0:
    case 0x4bcb40:
    case 0x4bcbc0: {
        uint32_t backend = outside(run, 0x4f63ec, 0, -0x14, {0x38});
        if (backend) {
            run.put(backend + 0x4, 0);
            run.put(backend + 0x0, 0);
            run.put(backend + 0x8, 0);
            run.put(backend + 0xc, 0);
            run.put(backend + 0x10, 0);
            run.put(backend + 0x34, 0);
            run.put(backend + 0x18, 0);
            run.put(backend + 0x14, 0);
            run.put(backend + 0x2c, 0);
            run.put(backend + 0x30, 0);
        }
        uint32_t success;
        if (function == 0x4bcbc0)
            success = nested(run, 0x4bb5a0, backend, -0x20, {run.get(receiver), arguments[0], arguments[1], arguments[2]});
        else
            success = nested(run, function == 0x4bcac0 ? 0x4bb240 : 0x4bb100, backend, -0x1c, {run.get(receiver), arguments[0], arguments[1]});
        if (!success) {
            if (backend) {
                nested(run, 0x4bb2a0, backend, -0x10);
                outside(run, 0x4f6428, 0, -0x14, {backend});
            }
            return 0;
        }
        nested(run, 0x4bc9b0, receiver, -0x14, {backend});
        return backend;
    }
    // 0x4d65a0, 0x4d65e0, 0x4d6620 wrapper loaders.
    case 0x4d65a0:
    case 0x4d65e0:
    case 0x4d6620: {
        uint32_t manager = run.get(run.get(receiver + 0xc) + 0x1c);
        uint32_t backend;
        uint32_t flags;
        if (function == 0x4d6620) {
            backend = nested(run, 0x4bcbc0, manager, -0x14, {arguments[0], arguments[1], 0x44});
            flags = arguments[2];
        } else {
            backend = nested(run, function == 0x4d65a0 ? 0x4bcac0 : 0x4bcb40, manager, -0x10, {arguments[0], 0x44});
            flags = arguments[1];
        }
        run.put(receiver + 0x10, backend);
        if (!backend)
            return 0;
        if (flags & 1) {
            run.put(receiver + 0x8, run.get(receiver + 0x8) | 1);
            nested(run, 0x4bbf60, backend, -0x8);
        }
        return 1;
    }
    // 0x4b96f0 setDisplayPalette; receiver +8 physical surface.
    case 0x4b96f0: {
        uint32_t palette = run.get(arguments[0] + 0x4);
        uint32_t surface = run.get(receiver + 0x8);
        uint32_t result = com(run, surface, 0x7c, -0xc, {surface, palette});
        if (!result)
            return 1;
        report(run, 0x5324dc, 0x1b8, result, -0x10);
        return 0;
    }
    // 0x4bb100 initializeEntries.
    case 0x4bb100: {
        uint32_t entries = outside(run, 0x4f63ec, 0, -0x10, {0x400});
        run.put(receiver + 0xc, entries);
        for (uint32_t i = 0; i < 0x400; i += 4) {
            uint32_t destination = run.get(receiver + 0xc);
            run.put(destination + i, run.get(arguments[1] + i));
        }
        uint32_t backup = outside(run, 0x4f63ec, 0, -0x10, {0x400});
        run.put(receiver + 0x10, backup);
        uint32_t result = com(run, arguments[0], 0x14, -0x20, {arguments[0], arguments[2], arguments[1], receiver + 0x4, 0});
        if (!result)
            return 1;
        report(run, 0x532500, 0x4b, result, -0x18);
        return 0;
    }
    // 0x4bb240 initializeTriples; 0x4bb5a0 initializePcx.
    case 0x4bb240:
    case 0x4bb5a0: {
        if (function == 0x4bb5a0 && arguments[2] < 0x300)
            return 0;
        uint32_t source = arguments[1];
        uint32_t flags = arguments[2];
        if (function == 0x4bb5a0) {
            source += arguments[2] - 0x300;
            flags = arguments[3];
        }
        uint32_t local = run.automatic(-0x400);
        for (uint32_t i = 0; i < 0x100; ++i) {
            run.put8(local + i * 4, run.get8(source + i * 3));
            run.put8(local + i * 4 + 0x1, run.get8(source + i * 3 + 0x1));
            run.put8(local + i * 4 + 0x2, run.get8(source + i * 3 + 0x2));
            run.put8(local + i * 4 + 0x3, 0);
        }
        return nested(run, 0x4bb100, receiver, -0x41c, {arguments[0], local, flags});
    }
    // 0x4bb800 setEntries.
    case 0x4bb800: {
        uint32_t start = arguments[0];
        uint32_t count = arguments[1];
        if (start < start + count) {
            for (uint32_t i = 0; i < count; ++i) {
                uint32_t destination = run.get(receiver + 0xc);
                run.put(destination + (start + i) * 4, run.get(arguments[2] + i * 4));
            }
        }
        uint32_t holder = run.get(0x541374);
        if (holder) {
            uint32_t interface = run.get(holder);
            com(run, interface, 0x58, -0x20, {interface, 1, 0});
        }
        uint32_t palette = run.get(receiver + 0x4);
        return com(run, palette, 0x18, -0x28, {palette, 0, start, count, arguments[2]});
    }
    // 0x4bb910 fillEntries.
    case 0x4bb910: {
        uint32_t end = arguments[0] + arguments[1];
        for (uint32_t i = arguments[0]; s32(i) < s32(end); ++i) {
            run.put8(run.get(receiver + 0xc) + i * 4, arguments[2]);
            run.put8(run.get(receiver + 0xc) + i * 4 + 0x1, arguments[3]);
            run.put8(run.get(receiver + 0xc) + i * 4 + 0x2, arguments[4]);
        }
        uint32_t palette = run.get(receiver + 0x4);
        uint32_t result = com(run, palette, 0x18, -0x28, {palette, arguments[5], arguments[0], arguments[1], run.get(receiver + 0xc) + arguments[0] * 4});
        if (result)
            report(run, 0x532500, 0x29f, result, -0x20);
        return result;
    }
    // 0x4bb990 fadeEntries.
    case 0x4bb990: {
        uint32_t palette = run.get(receiver + 0x4);
        uint32_t result = com(run, palette, 0x10, -0x40, {palette, 0, 0, 0x100, run.get(receiver + 0xc)});
        if (result)
            report(run, 0x532500, 0x2bc, result, -0x38);
        uint32_t backup = outside(run, 0x4f63ec, 0, -0x30, {0x400});
        for (uint32_t i = 0; i < 0x400; i += 4)
            run.put(backup + i, run.get(run.get(receiver + 0xc) + i));
        uint32_t startTime = outside(run, 0x546df0, 0, -0x2c);
        uint32_t duration = arguments[5];
        uint32_t elapsed = 10;
        uint32_t previous = 9;
        while (elapsed < duration) {
            if (elapsed != previous) {
                for (uint32_t i = arguments[0]; s32(i) < s32(arguments[0] + arguments[1]); ++i) {
                    for (uint32_t channel = 0; channel < 3; ++channel) {
                        uint32_t original = run.get8(backup + i * 4 + channel);
                        uint32_t product = ((arguments[2 + channel] & 0xff) - original) * elapsed;
                        uint32_t value = uint32_t(int64_t(s32(product)) / int64_t(s32(duration))) + original;
                        run.put8(run.get(receiver + 0xc) + i * 4 + channel, value);
                    }
                }
                palette = run.get(receiver + 0x4);
                com(run, palette, 0x18, -0x40, {palette, 0, arguments[0], arguments[1], run.get(receiver + 0xc) + arguments[0] * 4});
            }
            previous = elapsed;
            elapsed = outside(run, 0x546df0, 0, -0x2c) - startTime;
        }
        nested(run, 0x4bb910, receiver, -0x44, {arguments[0], arguments[1], arguments[2], arguments[3], arguments[4], 0});
        outside(run, 0x4f6428, 0, -0x30, {backup});
        return 0;
    }
    // 0x4d4240 ensureSurfaceReady; controller +0x2c surface holder.
    case 0x4d4240: {
        uint32_t holder = run.get(receiver + 0x2c);
        if (!holder)
            return 1;
        uint32_t surface = run.get(holder + 0x8);
        if (surface && !com(run, surface, 0x60, -0xc, {surface}))
            return 1;
        surface = run.get(run.get(receiver + 0x2c) + 0x8);
        return com(run, surface, 0x6c, -0xc, {surface}) == 0;
    }
    // 0x4d4420, 0x4d44f0, 0x4d4570, 0x4d45f0 create/load wrappers.
    case 0x4d4420:
    case 0x4d44f0:
    case 0x4d4570:
    case 0x4d45f0: {
        bool resource = function == 0x4d4420;
        bool pcx = function == 0x4d45f0;
        int32_t base = resource ? -0x60 : pcx ? -0x64 : -0x8;
        uint32_t data = arguments[0];
        uint32_t length = 0;
        if (pcx && outside(run, 0x4b61b0, arguments[0], base - 4) != 0x504358)
            return 0;
        if (resource || pcx) {
            data = outside(run, 0x4b61c0, arguments[0], base - 4);
            if (!data)
                return 0;
            if (pcx)
                length = run.get(arguments[0] + 0x14);
        }
        uint32_t wrapper = outside(run, 0x4f63ec, 0, base - 8, {0x14});
        if (wrapper) {
            uint32_t tag = run.get(receiver + 0x1c);
            uint32_t context = run.get(receiver + 0xc);
            if (resource) {
                run.put(wrapper + 0x8, 0);
                run.put(wrapper + 0x10, 0);
                run.put(wrapper + 0x4, tag);
                run.put(wrapper + 0xc, context);
                run.put(wrapper + 0x0, 0x513d78);
            } else {
                run.put(wrapper + 0x4, tag);
                run.put(wrapper + 0x8, 0);
                run.put(wrapper + 0xc, context);
                run.put(wrapper + 0x0, 0x513d78);
                run.put(wrapper + 0x10, 0);
            }
        }
        uint32_t success;
        if (pcx)
            success = method(run, wrapper, 0x30, base - 0x10, {data, length, arguments[2]});
        else
            success = method(run, wrapper, function == 0x4d4570 ? 0x2c : 0x28, base - 0xc, {data, arguments[2]});
        if (resource)
            outside(run, 0x4b6230, arguments[0], base - 4);
        if (!success) {
            if (wrapper)
                method(run, wrapper, 0x4, base - 8, {1});
            return 0;
        }
        uint32_t name = arguments[1];
        if (resource || pcx) {
            if (!name)
                name = run.get(arguments[0]);
            uint32_t local = run.automatic(-0x50);
            copyName(run, local, name);
            name = local;
        }
        uint32_t slot = outside(run, 0x4f62a8, receiver + 0x10, base - 8, {name});
        run.put(slot, wrapper);
        return wrapper;
    }
    // 0x4d46f0 removeWrapper; original map and CString operations.
    case 0x4d46f0: {
        uint32_t requested = arguments[0];
        if (run.get(receiver + 0x64) == requested)
            run.put(receiver + 0x64, 0);
        uint32_t position = run.automatic(-0x14);
        uint32_t current = run.automatic(-0x10);
        uint32_t string = run.automatic(0x4);
        run.put(current, 0);
        run.put(position, run.get(receiver + 0x1c) ? 0xffffffff : 0);
        outside(run, 0x4f6439, string, -0x20);
        while (run.get(position)) {
            outside(run, 0x4f5e1e, receiver + 0x10, -0x2c, {position, string, current});
            if (run.get(current) == requested) {
                outside(run, 0x4f5db6, receiver + 0x10, -0x24, {run.get(string)});
                if (requested)
                    method(run, requested, 0x4, -0x24, {1});
                outside(run, 0x4f6584, string, -0x20);
                return 1;
            }
        }
        outside(run, 0x4f6584, string, -0x20);
        return 0;
    }
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_palette_resource_canonical_entry, owned, body)
