#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"
#include "ClawRecoveredNames.h"

extern "C" uint32_t claw_v13_cheat_presentation_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);

namespace {
using claw::Run;
using claw::s32;
using namespace claw::recovered::v13;

int owned(uint32_t function) {
    switch (function) {
    case 0x42a9b0:
    case 0x42c780:
        return 1;
    case 0x42c7a0:
    case 0x4233e0:
        return 2;
    default:
        return -1;
    }
}

// Original game callees see the dispatcher's real outgoing frame. Some
// pass their own stack locals to native services, making its address observable.
uint32_t originalCall(Run &run, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
    uint32_t previous = run.stackPointer;
    run.stackPointer = run.automatic(-0x50 - 4 * int32_t(arguments.size()));
    uint32_t value = run.call(function, receiver, arguments);
    run.stackPointer = previous;
    return value;
}

// 0x4233e0. Text list +0x0c is its signed entry count. Options select
// capacity checking, clearing, and head versus tail insertion.
uint32_t insertAcknowledgementText(Run &run, uint32_t list, const uint32_t *arguments) {
    uint32_t text = arguments[0];
    uint32_t options = arguments[1] & 0xff;
    DispatchTextListFields listFields{run, list};
    if (!text)
        return 0;
    if (!run.get8(text))
        return 0;
    if ((options & AcknowledgementCheckCapacity) && s32(listFields.entryCount()) > 7)
        return 0;
    if (options & AcknowledgementClearFirst)
        run.call(0x4fb719, list);
    if (options & AcknowledgementInsertHead)
        run.call(0x4fb80b, list, {text});
    else
        run.call(0x4fb883, list, {text});
    return 1;
}

// 0x42c780. Application +0x4c owns the acknowledgement text list.
uint32_t displayAcknowledgement(Run &run, uint32_t app, const uint32_t *arguments) {
    uint32_t text = arguments[0];
    DispatchApplicationFields appFields{run, app};
    uint32_t list = appFields.acknowledgements();
    if (!list)
        return 0;
    const uint32_t insertionArguments[] = {text, AcknowledgementClearFirst};
    return insertAcknowledgementText(run, list, insertionArguments);
}

uint32_t acknowledge(Run &run, uint32_t app, uint32_t text) {
    const uint32_t arguments[] = {text};
    return displayAcknowledgement(run, app, arguments);
}

// 0x42c7a0. Formatting uses the original shared output buffer.
uint32_t displayModeAcknowledgement(Run &run, uint32_t app, const uint32_t *arguments) {
    uint32_t name = arguments[0];
    uint32_t enabled = arguments[1];
    uint32_t format = enabled ? 0x52406c : 0x524060;
    run.call(0x4a5b6e, 0, {0x5356a0, format, name});
    acknowledge(run, app, 0x5356a0);
    return 0;
}

void acknowledgeMode(Run &run, uint32_t app, uint32_t name, uint32_t enabled) {
    const uint32_t arguments[] = {name, enabled};
    displayModeAcknowledgement(run, app, arguments);
}

// Resource owner +0x28 is the sound manager. Manager +0x30 disables named
// lookup; +0x10 is its map. Lookup reuses the dispatch argument stack slot.
void soundAcknowledgement(Run &run, uint32_t app, uint32_t name, bool inlined) {
    DispatchApplicationFields appFields{run, app};
    DispatchResourceOwnerFields resources{run, appFields.resources()};
    uint32_t manager = resources.soundManager();
    DispatchSoundManagerFields soundManagerFields{run, manager};
    if (soundManagerFields.namedLookupDisabled())
        return;
    uint32_t out = run.automatic(4);
    run.put(out, 0);
    run.call(0x4fc6b4, manager + 0x10, {name, out});
    uint32_t sound = run.get(out);
    if (!sound)
        return;
    if (!inlined) {
        originalCall(run, 0x421bb0, sound, {run.get(0x530990), 0, 0, 0});
        return;
    }
    uint32_t volume = run.get(0x530990);
    if (!run.get(0x53098c))
        return;
    uint32_t now = run.get(0x5aafdc);
    // Sound +0x14 is last request time, +0x18 its unsigned interval.
    DispatchSoundFields soundFields{run, sound};
    uint32_t elapsedMilliseconds = now - soundFields.lastRequestMilliseconds();
    uint32_t intervalMilliseconds = soundFields.requestIntervalMilliseconds();
    if (elapsedMilliseconds < intervalMilliseconds)
        return;
    soundFields.lastRequestMilliseconds(now);
    run.call(0x4b3da0, soundFields.backend(), {volume, 0, 0, 0});
}

void majorSound(Run &run, uint32_t app, bool inlined = false) {
    soundAcknowledgement(run, app, 0x524034, inlined);
}

void minorSound(Run &run, uint32_t app, bool inlined = false) {
    soundAcknowledgement(run, app, 0x523fa8, inlined);
}

void toggleMode(Run &run, uint32_t app, uint32_t flag, uint32_t text, bool minor, bool inlined = false) {
    run.put(flag, run.get(flag) ^ 1);
    if (minor)
        minorSound(run, app, inlined);
    else
        majorSound(run, app, inlined);
    acknowledgeMode(run, app, text, run.get(flag));
}

void displayBit(Run &run, uint32_t app, uint32_t bit, uint32_t text) {
    run.put(0x535998, run.get(0x535998) ^ bit);
    minorSound(run, app);
    acknowledgeMode(run, app, text, run.get(0x535998) & bit);
}

void postCommand(Run &run, uint32_t app, uint32_t command) {
    // Application +4 is its window wrapper, whose +4 is HWND.
    DispatchApplicationFields appFields{run, app};
    InputWindowFields windowFields{run, appFields.windowOwner()};
    run.icall(0x50c4cc, {windowFields.window(), WindowCommandMessage, command, 0});
}

void presentation(Run &run, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> values) {
    uint32_t arguments[2]{};
    uint32_t count = 0;
    for (uint32_t value : values)
        arguments[count++] = value;
    uint32_t result = 0;
    if (!claw_v13_cheat_presentation_entry(function, receiver, arguments, count, &run.host, &result))
        run.fail(CLAW_FAULT_ABI, function);
}

void powerup(Run &run, uint32_t app, uint32_t kind, uint32_t duration, uint32_t text) {
    originalCall(run, 0x420ee0, 0, {kind, duration});
    majorSound(run, app);
    acknowledge(run, app, text);
}

void refill(Run &run, uint32_t app, uint32_t offset, uint32_t text) {
    uint32_t player = run.get(0x5365d4);
    if (player) {
        // Player +0x7c points to logic, whose +0x14 is inventory state.
        MovementActorFields playerFields{run, player};
        MovementHolderFields holderFields{run, playerFields.logicHolder()};
        uint32_t inventory = holderFields.privateState();
        run.put(inventory + offset, 99);
    }
    majorSound(run, app);
    acknowledge(run, app, text);
}

void tempo(Run &run, uint32_t app, uint32_t text, uint32_t speed, uint32_t transition, bool inlined) {
    DispatchApplicationFields appFields{run, app};
    // Application +0x14 enables music; +0x50 points to its manager.
    if (!appFields.musicEnabled())
        return;
    uint32_t manager = appFields.musicManager();
    if (!manager)
        return;
    DispatchMusicManagerFields musicManagerFields{run, manager};
    uint32_t sequence = musicManagerFields.sequence();
    if (!sequence)
        return;
    if (!originalCall(run, 0x4b55b0, sequence))
        return;
    minorSound(run, app, inlined);
    acknowledge(run, app, text);
    DispatchMusicManagerFields reloadedManagerFields{run, appFields.musicManager()};
    sequence = reloadedManagerFields.sequence();
    if (sequence)
        presentation(run, 0x4b55e0, sequence, {speed, transition});
}

void nextSound(Run &run, uint32_t app) {
    DispatchApplicationFields appFields{run, app};
    uint32_t cursor = run.get(0x53591c);
    if (!cursor) {
        DispatchResourceOwnerFields initialResources{run, appFields.resources()};
        cursor = originalCall(run, 0x4cb0b0, initialResources.soundManager());
        run.put(0x53591c, cursor);
        // Signed remainder matters: nonpositive draws do not advance.
        int32_t advances = s32(run.call(0x4a595b, 0)) % 101;
        while (advances > 0) {
            DispatchResourceOwnerFields advancingResources{run, appFields.resources()};
            cursor = originalCall(run, 0x4cb160, advancingResources.soundManager(), {run.get(0x53591c)});
            run.put(0x53591c, cursor);
            if (!cursor) {
                DispatchResourceOwnerFields wrappedResources{run, appFields.resources()};
                cursor = originalCall(run, 0x4cb0b0, wrappedResources.soundManager());
                run.put(0x53591c, cursor);
            }
            --advances;
        }
        cursor = run.get(0x53591c);
    } else {
        DispatchResourceOwnerFields existingResources{run, appFields.resources()};
        cursor = originalCall(run, 0x4cb160, existingResources.soundManager(), {cursor});
        run.put(0x53591c, cursor);
    }
    if (!cursor) {
        DispatchResourceOwnerFields resetResources{run, appFields.resources()};
        cursor = originalCall(run, 0x4cb0b0, resetResources.soundManager());
        run.put(0x53591c, cursor);
        return;
    }
    uint32_t volume = run.get(0x530990);
    if (!run.get(0x53098c))
        return;
    uint32_t now = run.get(0x5aafdc);
    DispatchSoundFields cursorFields{run, cursor};
    uint32_t elapsedMilliseconds = now - cursorFields.lastRequestMilliseconds();
    uint32_t intervalMilliseconds = cursorFields.requestIntervalMilliseconds();
    if (elapsedMilliseconds < intervalMilliseconds)
        return;
    uint32_t backend = cursorFields.backend();
    cursorFields.lastRequestMilliseconds(now);
    run.call(0x4b3da0, backend, {volume, 0, 0, 0});
}

// 0x42a9b0. State 3 accepts 66 actions selected by the command's low word.
uint32_t dispatchCheatCommand(Run &run, uint32_t app, const uint32_t *arguments) {
    uint32_t command = arguments[0];
    DispatchApplicationFields appFields{run, app};
    // Application +0x2c is its active state; vtable +0x10 returns its id.
    if (run.vcall(appFields.state(), ModeQuerySlot) != CheatDispatchGameplayMode)
        return 0;
    command &= 0xffff;
    switch (command) {
    case 0x8043:
        toggleMode(run, app, 0x53592c, 0x524028, false);
        break;
    case 0x8044: {
        uint32_t player = run.get(0x5365d4);
        if (player) {
            MovementActorFields playerFields{run, player};
            playerFields.health(100);
        }
        majorSound(run, app);
        acknowledge(run, app, 0x523ff8);
        break;
    }
    case 0x8045:
        refill(run, app, 0x70, 0x524004);
        break;
    case 0x8046:
        refill(run, app, 0x74, 0x523fec);
        break;
    case 0x8047: {
        uint32_t value = run.get(0x535930);
        run.put(0x535940, 0);
        run.put(0x535930, value ^ 1);
        majorSound(run, app);
        acknowledgeMode(run, app, 0x52401c, run.get(0x535930));
        break;
    }
    case 0x8049:
        toggleMode(run, app, 0x535934, 0x523fc8, false);
        break;
    case 0x804a:
        toggleMode(run, app, 0x535938, 0x523fb8, false);
        break;
    case 0x804b:
        displayBit(run, app, 0x10, 0x523f64);
        break;
    case 0x804c:
        displayBit(run, app, 4, 0x523f78);
        break;
    case 0x804d:
        displayBit(run, app, 1, 0x523f90);
        break;
    case 0x804e:
        run.put(0x535998, run.get(0x535998) ^ 0x20);
        minorSound(run, app);
        break;
    case 0x804f:
        toggleMode(run, app, 0x53593c, 0x523f50, true);
        break;
    case 0x805b:
        powerup(run, app, 0x26bc, 30000, 0x523f40);
        break;
    case 0x8064:
        originalCall(run, 0x42a5d0, app);
        minorSound(run, app);
        acknowledge(run, app, 0x523ee0);
        break;
    case 0x8065:
        originalCall(run, 0x42a630, app);
        minorSound(run, app);
        acknowledge(run, app, 0x523ec8);
        break;
    case 0x8066:
        originalCall(run, 0x42a670, app);
        minorSound(run, app);
        acknowledge(run, app, 0x523eac);
        break;
    case 0x8068:
        run.put(0x535998, (run.get(0x535998) ^ 0x40) & 0xfffffeff);
        run.call(0x4fcd34, 0x535838);
        run.call(0x4fcd34, 0x535834);
        minorSound(run, app);
        break;
    case 0x806a: {
        uint32_t value = run.get(0x535940);
        run.put(0x535930, 0);
        run.put(0x535940, value ^ 1);
        majorSound(run, app);
        acknowledgeMode(run, app, 0x524010, run.get(0x535940));
        break;
    }
    case 0x806c:
        refill(run, app, 0x78, 0x523fdc);
        break;
    case 0x806e:
        displayBit(run, app, 0x80, 0x523e94);
        break;
    case 0x806f:
        run.put(0x535998, (run.get(0x535998) ^ 0x100) & 0xffffffbf);
        run.call(0x4fcd34, 0x535838);
        minorSound(run, app);
        break;
    case 0x8071:
        toggleMode(run, app, 0x535944, 0x523e58, false);
        break;
    case 0x8072:
        toggleMode(run, app, 0x535948, 0x523e40, false);
        break;
    case 0x8076:
        if (s32(appFields.displayWidth()) <= 0x140) {
            postCommand(run, app, 0x802c);
            acknowledge(run, app, 0x523db8);
        } else if (originalCall(run, 0x429d80, app, {0x140, 200})) {
            acknowledge(run, app, 0x523dd4);
        } else if (originalCall(run, 0x429d80, app, {0x280, 0x1e0})) {
            acknowledge(run, app, 0x523df4);
        } else {
            originalCall(run, 0x429b30, app, {0x8008, 0x403});
        }
        break;
    case 0x8077:
        run.put(0x53599c, 1);
        postCommand(run, app, 0x802a);
        break;
    case 0x8078:
        run.put(0x53599c, 1);
        postCommand(run, app, 0x802b);
        break;
    case 0x8079: {
        postCommand(run, app, 0x802c);
        uint32_t buffer = run.automatic(-0x40);
        run.call(0x4a5b6e, 0, {buffer, 0x523e18, appFields.displayDepth()});
        acknowledge(run, app, buffer);
        break;
    }
    case 0x807a:
    case 0x807b:
        minorSound(run, app);
        acknowledge(run, app, 0x523e6c);
        break;
    case 0x8086:
        if (originalCall(run, 0x42def0, app)) {
            soundAcknowledgement(run, app, 0x523da8, false);
            acknowledge(run, app, 0x523d94);
            if (appFields.musicEnabled()) {
                uint32_t name = run.get(0x535994) ? 0x523d88 : 0x522dc0;
                originalCall(run, 0x4b4ed0, appFields.musicManager(), {name, 1});
            }
        }
        break;
    case 0x8087:
        if (originalCall(run, 0x42e080, app)) {
            minorSound(run, app);
            acknowledge(run, app, 0x523d6c);
        }
        break;
    case 0x8088:
        originalCall(run, 0x42e310, app);
        break;
    case 0x8089:
        originalCall(run, 0x42e410, app);
        break;
    case 0x808a:
        originalCall(run, 0x42e530, app);
        break;
    case 0x808b:
        toggleMode(run, app, 0x5359a0, 0x523d58, false);
        if (run.get(0x5359a0))
            originalCall(run, 0x441df0, 0);
        else
            originalCall(run, 0x441e10, 0);
        break;
    case 0x808d:
        powerup(run, app, 0x26b7, 30000, 0x523f20);
        break;
    case 0x808e:
        powerup(run, app, 0x26bd, 30000, 0x523ef4);
        break;
    case 0x808f: {
        uint32_t state = appFields.state();
        if (state && run.vcall(state, 0x10) == 3) {
            minorSound(run, app);
            originalCall(run, 0x4702c0, state);
        }
        break;
    }
    case 0x8091:
        powerup(run, app, 0x26ba, 20000, 0x523d30);
        break;
    case 0x8092:
        powerup(run, app, 0x26b8, 20000, 0x523d44);
        break;
    case 0x8093:
        powerup(run, app, 0x26b9, 20000, 0x523d14);
        break;
    case 0x809c:
    case 0x809d:
    case 0x809e:
    case 0x809f:
    case 0x80a0:
    case 0x80a1:
    case 0x80a2:
    case 0x80a3:
    case 0x80a4:
    case 0x80a5:
    case 0x80a6:
    case 0x80a7:
    case 0x80a8:
    case 0x80a9: {
        uint32_t level = command - 0x809b;
        if (!originalCall(run, 0x429890, app, {level})) {
            const uint32_t errors[] = {0x407, 0x408, 0x409, 0x40a, 0x4b5, 0x4b6, 0x4b7, 0x4b8, 0x6b2, 0x6b3, 0x6b4, 0x6b5, 0x6b6, 0x6b7};
            originalCall(run, 0x429b30, app, {0x8007, errors[level - 1]});
        }
        break;
    }
    case 0x80aa: {
        uint32_t checkpoint = run.get(0x5360a8);
        DispatchCommandRecordFields checkpointFields{run, checkpoint};
        if (checkpoint &&
            s32(checkpointFields.unknown_0xb4()) > 0 &&
            s32(checkpointFields.unknown_0xb8()) > 0) {
            run.put(0x5282c8, checkpointFields.unknown_0xb4());
            run.put(0x5282cc, checkpointFields.unknown_0xb8());
            postCommand(run, app, 0x805c);
        }
        break;
    }
    case 0x80ad:
        minorSound(run, app);
        acknowledge(run, app, 0x523cfc);
        {
            DispatchStateFields stateFields{run, appFields.state()};
            presentation(run, 0x463c90, 0, {stateFields.paletteOwner()});
        }
        break;
    case 0x80ae:
        nextSound(run, app);
        break;
    case 0x80af:
        tempo(run, app, 0x523ce0, 150, 2500, false);
        break;
    case 0x80b0:
        tempo(run, app, 0x523cc4, 75, 2500, false);
        break;
    case 0x80b1:
        tempo(run, app, 0x523cb0, 100, 1000, true);
        break;
    case 0x80b2:
        toggleMode(run, app, 0x53594c, 0x523c98, false, true);
        break;
    case 0x80b3: {
        uint32_t value = run.get(0x535958);
        run.put(0x53595c, 0);
        run.put(0x535958, value ^ 1);
        minorSound(run, app, true);
        acknowledgeMode(run, app, 0x523c88, run.get(0x535958));
        break;
    }
    case 0x80b4: {
        uint32_t player = run.get(0x5365d4);
        if (player) {
            MovementActorFields playerFields{run, player};
            uint32_t mirrorBits = playerFields.unknown_0x40();
            playerFields.unknown_0x40(mirrorBits ^ 4);
            minorSound(run, app, true);
            acknowledge(run, app, 0x523c70);
        }
        break;
    }
    case 0x80b5:
        toggleMode(run, app, 0x535950, 0x523c64, false, true);
        break;
    case 0x80b6:
        toggleMode(run, app, 0x535954, 0x523c48, false, true);
        break;
    default:
        return 0;
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42a9b0:
        return dispatchCheatCommand(run, receiver, arguments);
    case 0x42c780:
        return displayAcknowledgement(run, receiver, arguments);
    case 0x42c7a0:
        return displayModeAcknowledgement(run, receiver, arguments);
    case 0x4233e0:
        return insertAcknowledgementText(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_v13_cheat_dispatch_entry, owned, body)
