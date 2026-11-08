// v1.3 gameplay keyboard cheat recognition and command posting
//
// Recovered against the pinned v1.3 keyboard input packet.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;
using namespace claw::recovered::v13;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x424380:
        return 2;
    case 0x46ddc0:
        return 2;
    default:
        return -1;
    }
}

// 0x424380. thiscall, 2 stack argument(s), returns void.
uint32_t processCheatKey(Run &run, uint32_t receiver, const uint32_t *arguments,
                         int32_t outputOffset) {
    CheatRecognizerFields cheat{run, receiver};
    CheatTextByteFields text{run, receiver};
    const uint32_t key = arguments[0];
    // Cheat object: +0x00 window, +0x04 dictionary, +0x20 encoded text,
    // +0x120 signed text length, +0x124 last input time, +0x128 cheated flag.
    if (s32(key) < 0x30 || s32(key) > 0x5a) {
        text.encodedText(0);
        cheat.length(0);
        return 0;
    }
    const uint32_t nowMilliseconds = arguments[1];
    // Timeout addition wraps before an unsigned comparison; lengths stay signed.
    if (cheat.lastInputMilliseconds() + 0x5dc < nowMilliseconds || s32(cheat.length()) > 200) {
        text.encodedText(0);
        cheat.length(0);
    }
    cheat.lastInputMilliseconds(nowMilliseconds);
    // Indexed byte accesses retain the checked encodedText offset (0x20).
    run.put8(receiver + 0x20 + cheat.length(), uint8_t(key + 0x11));
    const uint32_t length = cheat.length() + 1;
    cheat.length(length);
    run.put8(receiver + 0x20 + length, 0);
    if (s32(cheat.length()) < 5) {
        return 0;
    }
    // The map output occupies the now-dead key argument stack slot.
    const uint32_t output = run.automatic(outputOffset);
    run.put(output, 0);
    // Embedded dictionary at checked +0x04; encodedText starts at checked +0x20.
    if (!run.call(0x4fc6b4, receiver + 0x04, {receiver + 0x20, output})) {
        return 0;
    }
    const uint32_t entry = run.get(output);
    if (!entry) {
        return 0;
    }
    // Command entry: +0x00 signed command identifier, +0x04 flag byte.
    CheatCommandFields commandEntry{run, entry};
    CheatCommandByteFields commandBytes{run, entry};
    const uint32_t command = commandEntry.command();
    if (s32(command) <= 0) {
        return 0;
    }
    const uint32_t window = cheat.window();
    run.icall(0x50c4cc, {window, 0x111, command, 0});
    // Posting can mutate the flags; retain this byte read after the call.
    if (!(commandBytes.flags() & 1)) {
        cheat.cheated(1);
    }
    cheat.length(0);
    text.encodedText(0);
    return 0;
}

// Canonical direct entry uses the original dead key-argument output slot.
uint32_t recognizeCheatKey(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return processCheatKey(run, receiver, arguments, 0x04);
}

// 0x46ddc0. thiscall, 2 stack argument(s), returns u32.
uint32_t handleGameplayKeyDown(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Input receiver: +0x04 application. Application: +0x0c paused,
    // +0x48 cheat recognizer, +0x04 window owner with HWND at +0x04.
    GameplayInputFields inputReceiver{run, receiver};
    const uint32_t app = inputReceiver.application();
    InputApplicationFields application{run, app};
    if (!application.paused()) {
        const uint32_t key = arguments[0];
        const uint32_t input[] = {key, run.get(GameplayInputTimeAddress)};
        const uint32_t recognizer = application.cheatRecognizer();
        processCheatKey(run, recognizer, input, -0x10);
        if (key == GameplayEscapeKey) {
            // The recognizer can change the application; reload it here.
            const uint32_t currentApp = inputReceiver.application();
            InputApplicationFields currentApplication{run, currentApp};
            const uint32_t window = currentApplication.windowOwner();
            InputWindowFields windowOwner{run, window};
            const uint32_t windowHandle = windowOwner.window();
            run.icall(0x50c4cc, {windowHandle, WindowCommandMessage, GameplayPauseCommand, 0});
        }
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x424380:
        return recognizeCheatKey(run, receiver, arguments);
    case 0x46ddc0:
        return handleGameplayKeyDown(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_v13_cheat_input_entry, owned, body)
