#include "ClawRuntime.hpp"
#include "AudioEvents.h"

namespace {

using claw::Run;
using claw::s32;

struct OwnedFrame {
    Run &run;
    uint32_t frame;
    uint32_t stackPointer;

    OwnedFrame(Run &run, uint32_t entry) : run(run), frame(run.frame), stackPointer(run.stackPointer) {
        run.frame = entry;
    }

    ~OwnedFrame() {
        run.frame = frame;
        run.stackPointer = stackPointer;
    }
};

int owned(uint32_t function) {
    switch (function) {
    case 0x4208e0:
    case 0x4b45f0:
    case 0x4c88e0:
        return 4;
    case 0x420910:
    case 0x4b3b90:
        return 1;
    case 0x48c820:
    case 0x48c8a0:
        return 2;
    default:
        return -1;
    }
}

// 0x4b45f0. Pool +0x10 is its manager; manager +0x78 enables playback.
uint32_t function_004b45f0(Run &run, uint32_t pool, uint32_t volume,
                           uint32_t pan, uint32_t pitch, uint32_t looping) {
    uint32_t manager = run.get(pool + 0x10);
    if (!run.get(manager + 0x78))
        return 0;
    run.stackPointer = run.frame - 0x0c;
    uint32_t voice = run.call(0x4b4430, pool);
    if (!voice)
        return 0;
    uint32_t success = 1;
    run.stackPointer = run.frame - 0x10;
    if (!run.call(0x4b3f40, voice, {volume}))
        success = 0;
    if (!run.call(0x4b4110, voice, {pan}))
        success = 0;
    if (!run.call(0x4b41b0, voice, {pitch}))
        success = 0;
    run.call(0x4b3ec0, voice, {looping});
    run.stackPointer = run.frame - 0x0c;
    if (!run.call(0x4b3d80, voice))
        success = 0;
    return success;
}

// 0x4208e0. Sound +0x10 is its pool.
uint32_t function_004208e0(Run &run, uint32_t sound, const uint32_t *arguments) {
    if (!run.get(0x532c0c))
        return 0;
    OwnedFrame frame(run, run.frame - 0x14);
    return function_004b45f0(run, run.get(sound + 0x10), arguments[0],
                           arguments[1], arguments[2], arguments[3]);
}

// 0x420910. Player +0x30 disables sound; +0x10 is the embedded map.
uint32_t function_00420910(Run &run, uint32_t player, uint32_t name) {
    if (run.get(player + 0x30))
        return 0;
    uint32_t output = run.automatic(-4);
    run.put(output, 0);
    run.stackPointer = run.frame - 0x10;
    run.call(0x4f6286, player + 0x10, {name, output});
    uint32_t sound = run.get(output);
    if (!sound)
        return 0;
    uint32_t manager = run.get(0x532c0c);
    uint32_t master = run.get(0x532c10);
    if (!manager)
        return 0;
    OwnedFrame frame(run, run.frame - 0x18);
    return function_004b45f0(run, run.get(sound + 0x10), master, 0, 0, 0);
}

// 0x48c820. Actor +0x6c is state; +0x184 holds pending speech.
// State +0x1c is its kind. The global actor is reloaded after the sound store.
uint32_t function_0048c820(Run &run, uint32_t sound, uint32_t force) {
    if (!sound)
        return 0;
    uint32_t actor = run.get(0x53c9a4);
    if (!actor)
        return 0;
    if (!force && run.get(0x53c9a0))
        return 0;
    if (!run.get(actor + 0x6c))
        return 0;
    if (!force) {
        uint32_t other = run.get(0x537e88);
        if (other) {
            uint32_t kind = run.get(run.get(other + 0x6c) + 0x1c);
            if (kind == 0x1c || kind == 0x138d || kind == 0x138c)
                return 0;
        }
    }
    run.put(actor + 0x184, sound);
    uint32_t state = run.get(run.get(0x53c9a4) + 0x6c);
    run.put(state + 0x1c, 0x3e9);
    return 1;
}

// 0x48c8a0. Actor +0x0c is scene, scene +0x28 is the player.
uint32_t function_0048c8a0(Run &run, uint32_t name, uint32_t force) {
    if (!name)
        return 0;
    uint32_t actor = run.get(0x53c9a4);
    if (!actor)
        return 0;
    uint32_t scene = run.get(actor + 0x0c);
    uint32_t output = run.automatic(4);
    uint32_t player = run.get(scene + 0x28);
    run.put(output, 0);
    run.stackPointer = run.frame - 0x0c;
    run.call(0x4f6286, player + 0x10, {name, output});
    uint32_t sound = run.get(output);
    if (!sound)
        return 0;
    force = run.get(run.automatic(8));
    OwnedFrame frame(run, run.frame - 0x0c);
    return function_0048c820(run, sound, force);
}

// 0x4b3b90. Elected finite-domain portable attenuation table.
uint32_t function_004b3b90(Run &run, uint32_t volume) {
    if (volume > 100)
        run.fail(CLAW_FAULT_ABI, 0x4b3b90);
    return uint32_t(claw_audio_volume_table_value(volume));
}

// 0x4c88e0. Sound +0x0c is scene. Scene +0x24 -> world +0x5c ->
// plane +0x84 provides reference; scene +4 -> wrapper +0x10 ->
// dimensions +0x10 provides width. Sound +0x10 is its playback pool.
uint32_t function_004c88e0(Run &run, uint32_t sound, uint32_t source,
                           uint32_t reference, uint32_t clamp, uint32_t distance) {
    if (!run.get(0x532c0c))
        return 0;
    if (s32(reference) <= 0) {
        uint32_t scene = run.get(sound + 0x0c);
        uint32_t world = run.get(scene + 0x24);
        uint32_t plane = run.get(world + 0x5c);
        reference = run.get(plane + 0x84);
    }
    if (s32(clamp) <= 0) {
        uint32_t scene = run.get(sound + 0x0c);
        uint32_t wrapper = run.get(scene + 0x04);
        uint32_t dimensions = run.get(wrapper + 0x10);
        clamp = run.get(dimensions + 0x10) << 2;
    }
    if (s32(distance) <= 0) {
        uint32_t scene = run.get(sound + 0x0c);
        uint32_t wrapper = run.get(scene + 0x04);
        uint32_t dimensions = run.get(wrapper + 0x10);
        distance = uint32_t(s32(run.get(dimensions + 0x10)) / 3);
    }
    uint32_t offset = source - reference;
    if (s32(offset) >= 0) {
        if (s32(offset) >= s32(clamp) || s32(offset) >= s32(distance))
            offset = s32(clamp) < s32(distance) ? clamp : distance;
    } else {
        uint32_t magnitude = 0u - offset;
        if (s32(magnitude) >= s32(clamp) || s32(magnitude) >= s32(distance))
            offset = 0u - (s32(clamp) < s32(distance) ? clamp : distance);
    }
    uint32_t numerator = offset * 100u;
    uint32_t master = run.get(0x532c10);
    if (!distance || (numerator == 0x80000000u && distance == 0xffffffffu))
        run.fail(CLAW_FAULT_ABI, 0x4c898c);
    uint32_t pan = uint32_t(s32(numerator) / s32(distance));
    uint32_t volume = 100;
    if (master != 100) {
        // Original x87 precision is 53 bits; retain both rounded multiplies.
        volatile double scaled = double(s32(run.get(0x532c10))) * double(run.getf(0x513768));
        volatile double result = 100.0 * scaled;
        volume = uint32_t(int64_t(result));
    }
    OwnedFrame frame(run, run.frame - 0x24);
    return function_004b45f0(run, run.get(sound + 0x10), volume, pan, 0, 0);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4208e0:
        return function_004208e0(run, receiver, arguments);
    case 0x420910:
        return function_00420910(run, receiver, arguments[0]);
    case 0x48c820:
        return function_0048c820(run, arguments[0], arguments[1]);
    case 0x48c8a0:
        return function_0048c8a0(run, arguments[0], arguments[1]);
    case 0x4b3b90:
        return function_004b3b90(run, arguments[0]);
    case 0x4b45f0:
        return function_004b45f0(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3]);
    case 0x4c88e0:
        return function_004c88e0(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_audio_events_entry, owned, body)
