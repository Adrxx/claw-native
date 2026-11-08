// Menu sound entry constructor and cleanup.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x4ca3b0:
        return 2;
    case 0x4ca670:
        return 1;
    case 0x4ca690:
        return 0;
    default:
        return -1;
    }
}

// Restore the parent's explicit call-frame tracking after an owned child.
struct OwnedFrame {
    Run &run;
    uint32_t frame;
    uint32_t stackPointer;
    OwnedFrame(Run &run, uint32_t entry) : run(run), frame(run.frame), stackPointer(run.stackPointer) {
        run.frame = entry;
        run.stackPointer = 0;
    }
    ~OwnedFrame() {
        run.frame = frame;
        run.stackPointer = stackPointer;
    }
};

// 0x4ca690. Sound +0x00 vtable, +0x04 owner/id, +0x08 base state,
// +0x0c scene, +0x10 audio resource (modified only by the external unload).
void destroySoundEntry(Run &run, uint32_t sound) {
    run.put(sound + 0x00, 0x5138b0);
    run.stackPointer = run.frame - 0x18;
    run.call(0x4c88b0, sound, {});
    run.put(sound + 0x04, 0xffffffff);
    run.put(sound + 0x08, 0);
    run.put(sound + 0x0c, 0);
    run.put(sound + 0x00, 0x50becc);
}

// 0x4ca670. Scalar deleting destructor returns its original receiver.
uint32_t deleteSoundEntry(Run &run, uint32_t sound, uint32_t flags) {
    {
        OwnedFrame child(run, run.frame - 0x08);
        destroySoundEntry(run, sound);
    }
    if ((flags & 1) != 0) {
        run.stackPointer = run.frame - 0x0c;
        run.call(0x4f6428, 0, {sound});
    }
    return sound;
}

// 0x4ca3b0. Manager +0x30 disables loading; +0x1c is owner/id,
// +0x0c is scene and +0x10 begins the embedded name dictionary.
uint32_t createSoundEntry(Run &run, uint32_t manager, const uint32_t *arguments) {
    if (run.get(manager + 0x30) != 0) {
        return 0;
    }
    run.stackPointer = run.frame - 0x10;
    uint32_t sound = run.call(0x4f63ec, 0, {0x14});
    if (sound == 0) {
        return 0;
    }
    uint32_t owner = run.get(manager + 0x1c);
    uint32_t scene = run.get(manager + 0x0c);
    run.put(sound + 0x04, owner);
    run.put(sound + 0x08, 0);
    run.put(sound + 0x0c, scene);
    run.put(sound + 0x00, 0x5138b0);
    run.put(sound + 0x10, 0);
    run.stackPointer = run.frame - 0x10;
    if (run.call(0x4c8850, sound, {arguments[1]}) == 0) {
        uint32_t target = run.get(run.get(sound + 0x00) + 0x04);
        if (target == 0x4ca670) {
            OwnedFrame child(run, run.frame - 0x10);
            deleteSoundEntry(run, sound, 1);
        } else {
            run.stackPointer = run.frame - 0x10;
            run.call(target, sound, {1});
        }
        return 0;
    }
    run.stackPointer = run.frame - 0x10;
    uint32_t cell = run.call(0x4f62a8, manager + 0x10, {arguments[0]});
    run.put(cell, sound);
    return sound;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4ca3b0:
        return createSoundEntry(run, receiver, arguments);
    case 0x4ca670:
        return deleteSoundEntry(run, receiver, arguments[0]);
    case 0x4ca690:
        destroySoundEntry(run, receiver);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_sound_entry_entry, owned, body)
