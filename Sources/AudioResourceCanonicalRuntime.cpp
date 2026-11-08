// Original audio resource metadata and voice pool.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x4b3cb0: return 2;
    case 0x4b4200: return 2;
    case 0x4b42e0: return 1;
    case 0x4b4430: return 0;
    case 0x4b46b0: return 3;
    case 0x4b48b0: return 3;
    case 0x4b4e30: return 4;
    case 0x4b5240: return 1;
    default: return -1;
    }
}

struct Frame {
    Run &run;
    uint32_t parent;
    uint32_t previousSP;
    Frame(Run &run, int32_t delta) : run(run), parent(run.frame), previousSP(run.stackPointer) {
        run.frame = run.automatic(delta);
    }
    ~Frame() {
        run.frame = parent;
        run.stackPointer = previousSP;
    }
};

uint32_t outward(Run &run, int32_t offset, uint32_t target, uint32_t receiver,
                 std::initializer_list<uint32_t> arguments) {
    run.stackPointer = run.automatic(offset);
    return run.call(target, receiver, arguments);
}

void report(Run &run, int32_t offset, uint32_t line) {
    outward(run, offset, 0x4b4ed0, 0, {0x53228c, line, 1});
}

// 0x4b3cb0. Buffer: +0xc COM interface, +0x10 manager, +0x14 state,
// +0x18 frequency, +0x1c pan, +0x20 volume, +0x24 initial frequency, +0x28 duration.
uint32_t function_4b3cb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t interface = arguments[0];
    run.put(receiver + 0x10, arguments[1]);
    run.put(receiver + 0x00, 0x513508);
    run.put(receiver + 0x0c, interface);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x28, 0);
    if (interface) {
        uint32_t result = outward(run, -0x18, run.get(run.get(interface) + 0x20), 0, {interface, receiver + 0x18});
        if (result != 0) {
            report(run, -0x1c, 0x46);
        }
        run.put(receiver + 0x24, run.get(receiver + 0x18));
        result = outward(run, -0x18, run.get(run.get(interface) + 0x1c), 0, {interface, receiver + 0x1c});
        if (result != 0) {
            report(run, -0x1c, 0x4a);
        }
        result = outward(run, -0x18, run.get(run.get(interface) + 0x18), 0, {interface, receiver + 0x20});
        if (result != 0) {
            report(run, -0x1c, 0x4d);
        }
    }
    return receiver;
}

// 0x4b4200. Resource: +0x30 list head, +0x34 list tail.
uint32_t function_4b4200(Run &run, uint32_t receiver, const uint32_t *arguments) {
    {
        Frame child(run, -0x18);
        function_4b3cb0(run, receiver, arguments);
    }
    run.put(receiver + 0x30, 0);
    run.put(receiver + 0x34, 0);
    run.put(receiver + 0x10, arguments[1]);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x00, 0x51350c);
    run.put(receiver + 0x0c, arguments[0]);
    return receiver;
}

// 0x4b46b0. Voice: +0x30 mode, +0x34 owning resource.
uint32_t function_4b46b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    {
        Frame child(run, -0x10);
        function_4b3cb0(run, receiver, arguments);
    }
    run.put(receiver + 0x00, 0x513510);
    run.put(receiver + 0x34, arguments[2]);
    run.put(receiver + 0x30, 1);
    return receiver;
}

// 0x4b42e0. Manager +0x78 enables audio; +0x14 holds its DirectSound interface.
uint32_t function_4b42e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (run.get(run.get(receiver + 0x10) + 0x78) == 0) {
        return 0;
    }
    uint32_t voice = outward(run, -0x20, 0x4f63ec, 0, {0x38});
    if (voice) {
        uint32_t constructor[] = {run.get(receiver + 0x0c), run.get(receiver + 0x10), receiver};
        Frame child(run, -0x28);
        function_4b46b0(run, voice, constructor);
    }
    if (voice == 0) {
        return 0;
    }
    uint32_t interface = run.get(run.get(receiver + 0x10) + 0x14);
    uint32_t buffer = run.get(receiver + 0x0c);
    uint32_t result = outward(run, -0x28, run.get(run.get(interface) + 0x14), 0, {interface, buffer, voice + 0x0c});
    if (result != 0) {
        report(run, -0x28, 0x179);
        return 0;
    }
    outward(run, -0x20, 0x4b5210, receiver + 0x30, {voice + 0x04});
    run.put(voice + 0x30, arguments[0]);
    return voice;
}

// 0x4b5240. Intrusive list nodes: +0x0 next, +0x4 previous.
uint32_t function_4b5240(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t node = arguments[0];
    run.put(node + 0x00, 0);
    run.put(node + 0x04, run.get(receiver + 0x04));
    uint32_t tail = run.get(receiver + 0x04);
    if (tail != 0) {
        run.put(tail + 0x00, node);
        run.put(receiver + 0x04, node);
        return 0;
    }
    run.put(receiver + 0x00, node);
    run.put(receiver + 0x04, node);
    return 0;
}

// 0x4b4430. Finds an idle enabled voice, restores its parameters and rotates it.
uint32_t function_4b4430(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(run.get(receiver + 0x10) + 0x78) == 0) {
        return 0;
    }
    uint32_t head = run.get(receiver + 0x30);
    uint32_t voice = head ? head - 0x04 : 0;
    while (voice) {
        if (run.get(voice + 0x30) != 0) {
            if (outward(run, -0x10, 0x4b3e70, voice, {}) == 0) {
                break;
            }
        }
        uint32_t next = run.get(voice + 0x04);
        voice = next ? next - 0x04 : 0;
    }
    if (voice) {
        outward(run, -0x14, 0x4b3ef0, voice, {run.get(receiver + 0x20)});
        outward(run, -0x14, 0x4b40c0, voice, {run.get(receiver + 0x1c)});
        outward(run, -0x14, 0x4b4160, voice, {run.get(receiver + 0x18)});
    } else {
        uint32_t mode[] = {1};
        Frame child(run, -0x14);
        voice = function_4b42e0(run, receiver, mode);
    }
    uint32_t node = voice ? voice + 0x04 : 0;
    outward(run, -0x14, 0x4b5270, receiver + 0x30, {node});
    {
        uint32_t append[] = {node};
        Frame child(run, -0x14);
        function_4b5240(run, receiver + 0x30, append);
    }
    return voice;
}

// 0x4b48b0. Builds the source WAVEFORMAT and DirectSound descriptor in their
// original guest stack slots; COM writes the buffer into the second argument.
uint32_t function_4b48b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t size = arguments[1];
    if (size == 0) {
        return 0;
    }
    uint32_t format = arguments[0];
    if (format == 0) {
        return 0;
    }
    if (run.get(receiver + 0x78) == 0) {
        return 0;
    }
    if (run.get16(format) != 1) {
        return 0;
    }
    uint32_t localFormat = run.automatic(-0x34);
    uint32_t descriptor = run.automatic(-0x20);
    uint32_t output = run.automatic(0x08);
    run.put(localFormat + 0x00, run.get(format + 0x00));
    run.put(localFormat + 0x04, run.get(format + 0x04));
    run.put(localFormat + 0x08, run.get(format + 0x08));
    run.put(descriptor + 0x00, 0);
    run.put(descriptor + 0x04, 0);
    run.put(localFormat + 0x0c, run.get(format + 0x0c));
    uint16_t bits = run.get16(format + 0x10);
    run.put(descriptor + 0x08, 0);
    run.put(descriptor + 0x0c, 0);
    run.put(descriptor + 0x10, 0);
    run.put(descriptor + 0x10, localFormat);
    run.put16(localFormat + 0x10, bits);
    uint32_t interface = run.get(receiver + 0x14);
    run.put16(localFormat + 0x10, 0);
    run.put(descriptor + 0x00, 0x14);
    run.put(descriptor + 0x04, 0xe0);
    run.put(descriptor + 0x08, size);
    run.put(output, size);
    uint32_t result = outward(run, -0x58, run.get(run.get(interface) + 0x0c), 0, {interface, descriptor, output, 0});
    if (result != 0) {
        report(run, -0x54, 0x2d6);
        return 0;
    }
    if (run.get(output) == 0) {
        return 0;
    }
    uint32_t resource = outward(run, -0x4c, 0x4f63ec, 0, {0x38});
    if (resource) {
        uint32_t constructor[] = {run.get(output), receiver};
        Frame child(run, -0x50);
        function_4b4200(run, resource, constructor);
    }
    uint32_t node = resource ? resource + 0x04 : 0;
    outward(run, -0x4c, 0x4b5210, receiver + 0x04, {node});
    uint32_t duration = (size * 1000u) / run.get(format + 0x08);
    run.put(resource + 0x2c, size);
    run.put(resource + 0x28, duration);
    return resource;
}

// 0x4b4e30. Bounded RIFF walk, including odd-sized chunk padding.
uint32_t function_4b4e30(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t riff = arguments[0];
    uint32_t size = run.get(riff + 0x04);
    uint32_t wave = run.get(riff + 0x08);
    uint32_t chunk = riff + 0x0c;
    uint32_t end = size + chunk - 0x04;
    if (run.get(riff) != 0x46464952 || wave != 0x45564157) {
        return 0;
    }
    run.put(arguments[1], 0);
    run.put(arguments[2], 0);
    while (chunk < end) {
        uint32_t kind = run.get(chunk + 0x00);
        uint32_t length = run.get(chunk + 0x04);
        chunk += 0x08;
        if (kind == 0x20746d66) {
            run.put(arguments[1], chunk);
        } else if (kind == 0x61746164) {
            run.put(arguments[2], chunk);
            run.put(arguments[3], length);
            return run.get(arguments[1]) != 0;
        }
        chunk += (length + 1) & 0xfffffffeu;
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b3cb0: return function_4b3cb0(run, receiver, arguments);
    case 0x4b4200: return function_4b4200(run, receiver, arguments);
    case 0x4b42e0: return function_4b42e0(run, receiver, arguments);
    case 0x4b4430: return function_4b4430(run, receiver, arguments);
    case 0x4b46b0: return function_4b46b0(run, receiver, arguments);
    case 0x4b48b0: return function_4b48b0(run, receiver, arguments);
    case 0x4b4e30: return function_4b4e30(run, receiver, arguments);
    case 0x4b5240: return function_4b5240(run, receiver, arguments);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace
CLAW_MODULE_ENTRY(claw_audio_resource_entry, owned, body)
