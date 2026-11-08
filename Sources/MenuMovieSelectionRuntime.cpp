// Menu movie archive availability, eligibility and sequence selection.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x42b5d0:
    case 0x42c0a0:
        return 0;
    case 0x42c280:
        return 1;
    default:
        return -1;
    }
}

// 0x42c0a0. Application +0x100 is the archive path.
uint32_t function_42c0a0(Run &run, uint32_t receiver, const uint32_t *) {
    run.stackPointer = run.frame - 0x08;
    return run.call(0x48c190, 0, {run.get(receiver + 0x100)});
}

// 0x42c280. Application +0x64 is the player; cache flags bit zero permits playback.
uint32_t function_42c280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!run.get(receiver + 0x64))
        return 0;
    uint32_t entry = run.frame;
    run.frame = entry - 0x08;
    uint32_t available = function_42c0a0(run, receiver, nullptr);
    run.frame = entry;
    if (!available)
        return 0;
    uint32_t level = arguments[0];
    uint32_t player = run.get(receiver + 0x64);
    if (!level)
        return 1;
    run.stackPointer = entry - 0x10;
    uint32_t record = run.call(0x49ae60, player, {level, 3});
    if (!record)
        return 0;
    if (!(run.get(record + 0x00) & 1))
        return 0;
    return 1;
}

// 0x42b5d0. The media receiver, archive and list share the original automatic region.
uint32_t function_42b5d0(Run &run, uint32_t receiver, const uint32_t *) {
    const uint32_t locals = run.automatic(-0x86c0);
    run.stackPointer = locals - 0x08;
    if (!run.call(0x48c190, 0, {run.get(receiver + 0x100)}))
        return 0;
    const uint32_t media = locals + 0x1c;
    const uint32_t archive = locals + 0x550;
    const uint32_t list = locals + 0x869c;
    run.stackPointer = locals - 0x04;
    run.call(0x42b4b0, archive);
    run.call(0x42d4a0, list);
    run.put(locals + 0x1c, 0);
    run.put(locals + 0x20, 0);
    run.put(locals + 0x2c, 0);
    run.put(locals + 0x30, 0);
    run.put(locals + 0x34, 0);
    run.put(locals + 0x38, 0);
    run.put(locals + 0x28, 0);
    run.put(locals + 0x3c, 0);
    run.put(locals + 0x51c, 0);
    run.put(locals + 0x524, 0);
    run.put(locals + 0x534, 0);
    run.put(locals + 0x538, 0);
    run.put(locals + 0x544, 0);
    run.put(locals + 0x53c, 0);
    run.put(locals + 0x540, 0);
    run.put(locals + 0x548, 0);
    run.put(locals + 0x520, 0);
    run.put(locals + 0x54c, 0);
    run.put(locals + 0x518, 0);
    // Application +0x30 is the scene. Its display chain supplies the descriptor.
    uint32_t scene = run.get(receiver + 0x30);
    uint32_t owner = run.get(scene + 0x04);
    uint32_t display = run.get(owner + 0x10);
    uint32_t holder = run.get(scene + 0x1c);
    uint32_t secondary = run.get(scene + 0x20);
    uint32_t surface = run.get(holder + 0x00);
    uint32_t descriptor = run.get(display + 0x2c);
    uint32_t extra = 0;
    if (secondary)
        extra = run.get(secondary + 0x14);
    if (!descriptor || !surface) {
        run.call(0x4f0120, media);
        run.call(0x42d4c0, list);
        run.call(0x4efcd0, archive);
        run.call(0x4f57f8, locals + 0x688);
        run.call(0x4f7369, locals + 0x674);
        return 0;
    }
    // Descriptor +8 is the second surface; +0xc..+0x77 is a by-value 27-word description.
    uint32_t secondSurface = run.get(descriptor + 0x08);
    uint32_t words[27];
    for (uint32_t i = 0; i < 27; ++i)
        words[i] = run.get(descriptor + 0x0c + i * 4);
    uint32_t window = run.get(receiver + 0x04);
    uint32_t hwnd = run.get(window + 0x04);
    run.stackPointer = locals - 0x80;
    uint32_t initialized = run.call(0x4f0000, media, {
        hwnd, surface, secondSurface,
        words[0], words[1], words[2], words[3], words[4], words[5], words[6], words[7], words[8],
        words[9], words[10], words[11], words[12], words[13], words[14], words[15], words[16], words[17],
        words[18], words[19], words[20], words[21], words[22], words[23], words[24], words[25], words[26], extra});
    uint32_t result = 0;
    if (initialized) {
        // Application +0x120 is normalized once for every enqueue in this sequence.
        uint32_t option = run.get(receiver + 0x120) != 0;
        run.stackPointer = locals - 0x28;
        run.call(0x4f10d0, media, {run.get(receiver + 0x100), 2, 0, option, 0, 0, 0x111, 1, 0});
        uint32_t level = 2;
        for (uint32_t table = 0x52552c; s32(table) < s32(0x525560); table += 4) {
            uint32_t movie = run.get(table);
            if (s32(movie) > 0) {
                uint32_t argument = level;
                uint32_t entry = run.frame;
                run.frame = locals - 0x08;
                uint32_t eligible = function_42c280(run, receiver, &argument);
                run.frame = entry;
                if (!eligible)
                    break;
                run.stackPointer = locals - 0x28;
                run.call(0x4f10d0, media, {run.get(receiver + 0x100), movie, 0, option, 0, 0, 0x111, 1, 0});
            }
            ++level;
        }
        run.stackPointer = locals - 0x08;
        run.call(0x4f1500, media, {1});
        result = 1;
    }
    run.stackPointer = locals - 0x04;
    run.call(0x4f1490, media);
    run.call(0x4f0120, media);
    run.call(0x4f0120, media);
    // Inline list destructor restores each base vtable around the buffer release.
    run.put(list + 0x00, 0x50c364);
    uint32_t buffer = run.get(list + 0x04);
    if (buffer) {
        run.stackPointer = locals - 0x08;
        run.call(0x4f6428, 0, {buffer});
    }
    run.stackPointer = locals - 0x04;
    run.put(list + 0x00, 0x50becc);
    run.call(0x4efcd0, archive);
    run.call(0x4f57f8, locals + 0x688);
    run.call(0x4f7369, locals + 0x674);
    return result;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42b5d0:
        return function_42b5d0(run, receiver, arguments);
    case 0x42c0a0:
        return function_42c0a0(run, receiver, arguments);
    case 0x42c280:
        return function_42c280(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_movie_selection_entry, owned, body)
