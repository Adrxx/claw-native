// Pause menu command callback and dispatcher
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
    case 0x4505f0:
        return 2;
    case 0x450b50:
        return 2;
    case 0x450e00:
        return 1;
    case 0x450ed0:
        return 1;
    case 0x451230:
        return 1;
    case 0x451410:
        return 1;
    case 0x451530:
        return 1;
    case 0x451660:
        return 1;
    case 0x451210:
        return 0;
    case 0x4519f0:
        return 0;
    case 0x4526f0:
        return 0;
    case 0x42cdf0:
        return 0;
    default:
        return -1;
    }
}

constexpr uint32_t kSelect = 0x5279e4;
constexpr uint32_t kDisable = 0x527a08;
constexpr uint32_t kVoice = 0x527fa8;
constexpr uint32_t kMaster = 0x532c0c;
constexpr uint32_t kVolume = 0x532c10;
constexpr uint32_t kPostSlot = 0x546d50;

// Menu M: +0x4 state A, +0xc B, +0x154 control tree, +0x290 audio dirty flags,
// +0x294 display dirty flags, +0x2a8 flag.
// State A: +0x4 C, +0x30 D. D: +0x28 sound owner E. E: +0x10 string map,
// +0x30 mute word.
//
// `frame` is the entry stack offset of the owned function, relative to the
// entry frame of the run. `held` is how many bytes the original function has
// pushed when it makes an outside call.

// Tracks the callee-entry ESP of the next outside call: the caller's entry
// offset, minus its pushed bytes, the pushed arguments and the return word.
void at(Run &run, int32_t frame, int32_t held, int32_t arguments) {
    int32_t depth = frame - held - 4 * arguments - 4;
    run.stackPointer = uint32_t(int32_t(run.frame) + depth);
}

// Sound owner E reached through M -> A -> D -> E.
uint32_t soundOwner(Run &run, uint32_t menu) {
    uint32_t state = run.get(menu + 0x4);
    uint32_t inner = run.get(state + 0x30);
    return run.get(inner + 0x28);
}

// String-map lookup in E; the out slot is zeroed first. Returns the found value.
uint32_t lookup(Run &run, uint32_t owner, uint32_t key, uint32_t slot, int32_t frame, int32_t held) {
    run.put(slot, 0x0);
    at(run, frame, held, 2);
    run.call(0x4f6286, owner + 0x10, {key, slot});
    return run.get(slot);
}

// Sound block, first flavour: tests the master word itself, then 0x4b45f0.
void soundGated(Run &run, uint32_t menu, uint32_t key, uint32_t slot, int32_t frame, int32_t held) {
    uint32_t owner = soundOwner(run, menu);
    if (run.get(owner + 0x30) != 0)
        return;
    uint32_t found = lookup(run, owner, key, slot, frame, held);
    if (found == 0)
        return;
    if (run.get(kMaster) == 0)
        return;
    uint32_t volume = run.get(kVolume);
    uint32_t object = run.get(found + 0x10);
    at(run, frame, held, 4);
    run.call(0x4b45f0, object, {volume, 0, 0, 0});
}

// Sound block, second flavour: 0x4208e0 tests the master word itself.
void soundPlain(Run &run, uint32_t menu, uint32_t key, uint32_t slot, int32_t frame, int32_t held) {
    uint32_t owner = soundOwner(run, menu);
    if (run.get(owner + 0x30) != 0)
        return;
    uint32_t found = lookup(run, owner, key, slot, frame, held);
    if (found == 0)
        return;
    uint32_t volume = run.get(kVolume);
    at(run, frame, held, 4);
    run.call(0x4208e0, found, {volume, 0, 0, 0});
}

// PostMessageA(hwnd of C, WM_COMMAND, wParam, 0) through the import slot.
void post(Run &run, uint32_t menu, uint32_t wparam, int32_t frame, int32_t held) {
    uint32_t state = run.get(menu + 0x4);
    uint32_t window = run.get(state + 0x4);
    uint32_t handle = run.get(window + 0x4);
    at(run, frame, held, 4);
    run.icall(kPostSlot, {handle, 0x111, wparam, 0});
}

uint32_t function_451660(Run &run, uint32_t menu, uint32_t command, int32_t frame);
uint32_t function_451210(Run &run, uint32_t group, int32_t frame);
uint32_t function_4519f0(Run &run, uint32_t menu, int32_t frame);
uint32_t function_4526f0(Run &run, uint32_t menu, int32_t frame);
uint32_t function_42cdf0(Run &run, uint32_t state, int32_t frame);

// 0x451660. Clears the selection, then runs 0x451680 with the command.
uint32_t function_451660(Run &run, uint32_t menu, uint32_t command, int32_t frame) {
    at(run, frame, 4, 0);
    run.call(0x4dd030, menu + 0x154);
    at(run, frame, 4, 1);
    run.call(0x451680, menu, {command});
    return 0;
}

// 0x451210. If the active word of the callback holder is set, clears it and
// tail-jumps to 0x402520 (entered with the same ESP as this function).
uint32_t function_451210(Run &run, uint32_t group, int32_t frame) {
    if (run.get(group + 0x24) == 0)
        return 0;
    run.put(group + 0x24, 0x0);
    at(run, frame, 0, -1);
    run.call(0x402520, group);
    return 0;
}

// 0x42cdf0. Toggles the display word of the state, calls 0x42ce20, returns it re-read.
uint32_t function_42cdf0(Run &run, uint32_t state, int32_t frame) {
    uint32_t toggled = run.get(state + 0x128) ^ 1;
    run.put(state + 0x128, toggled);
    at(run, frame, 4, 1);
    run.call(0x42ce20, state, {toggled});
    return run.get(state + 0x128);
}

// One control update: string literal -> value via 0x4f65f2 and 0x4529f0, then 0x4de4d0.
// The temporary string slot sits at entry-24 and the saved copy of its address
// at entry-4; the index word below the slot is already pushed.
void applyPair(Run &run, uint32_t control, uint32_t literal, uint32_t index, int32_t frame) {
    uint32_t slot = run.automatic(frame - 24);
    run.put(run.automatic(frame - 4), slot);
    run.put(run.automatic(frame - 20), index);
    at(run, frame, 24, 1);
    run.call(0x4f65f2, slot, {literal});
    uint32_t text = run.get(slot);
    at(run, frame, 20, 1);
    uint32_t value = run.call(0x4529f0, 0, {text});
    at(run, frame, 16, 2);
    run.call(0x4de4d0, control, {value, index});
}

void finishControl(Run &run, uint32_t control, int32_t frame) {
    at(run, frame, 16, 0);
    uint32_t result = run.call(0x4ed050, control);
    at(run, frame, 16, 1);
    run.call(0x4dec60, control, {result});
}

// 0x4519f0. Applies the audio dirty flags to the controls and clears them.
uint32_t function_4519f0(Run &run, uint32_t menu, int32_t frame) {
    uint32_t saved = run.get(menu + 0x290);
    if ((saved & 0x1) != 0) {
        at(run, frame, 16, 1);
        uint32_t found = run.call(0x4dd020, menu + 0x154, {0x5aa1});
        if (found != 0) {
            uint32_t control = found + 0x3c;
            applyPair(run, control, 0x528098, 0, frame);
            applyPair(run, control, 0x528080, 3, frame);
            finishControl(run, control, frame);
        }
    }
    if ((run.get(menu + 0x290) & 0x4) != 0) {
        at(run, frame, 16, 1);
        uint32_t found = run.call(0x4dd020, menu + 0x154, {0x5aa2});
        if (found != 0) {
            uint32_t control = found + 0x3c;
            applyPair(run, control, 0x528068, 0, frame);
            applyPair(run, control, 0x528050, 3, frame);
            applyPair(run, control, 0x528038, 5, frame);
            finishControl(run, control, frame);
        }
    }
    if ((run.get(menu + 0x290) & 0x8) != 0) {
        at(run, frame, 16, 1);
        uint32_t found = run.call(0x4dd020, menu + 0x154, {0x5aa3});
        if (found != 0) {
            uint32_t control = found + 0x3c;
            applyPair(run, control, 0x52801c, 0, frame);
            applyPair(run, control, 0x528000, 3, frame);
            applyPair(run, control, 0x527fe4, 5, frame);
            finishControl(run, control, frame);
        }
    }
    if ((run.get(menu + 0x290) & 0x2) != 0) {
        at(run, frame, 16, 1);
        uint32_t found = run.call(0x4dd020, menu + 0x154, {0x5aa4});
        if (found != 0) {
            uint32_t control = found + 0x3c;
            applyPair(run, control, 0x527fcc, 0, frame);
            applyPair(run, control, 0x527fb4, 3, frame);
            finishControl(run, control, frame);
        }
    }
    run.put(menu + 0x290, 0x0);
    return saved;
}

// 0x4526f0. Applies the display dirty flags to the controls and clears them.
uint32_t function_4526f0(Run &run, uint32_t menu, int32_t frame) {
    uint32_t saved = run.get(menu + 0x294);
    if ((saved & 0x1) != 0) {
        at(run, frame, 16, 1);
        uint32_t found = run.call(0x4dd020, menu + 0x154, {0x5b05});
        if (found != 0) {
            uint32_t control = found + 0x3c;
            applyPair(run, control, 0x528178, 0, frame);
            applyPair(run, control, 0x52815c, 3, frame);
            finishControl(run, control, frame);
        }
    }
    if ((run.get(menu + 0x294) & 0x2) != 0) {
        at(run, frame, 16, 1);
        uint32_t found = run.call(0x4dd020, menu + 0x154, {0x5b07});
        if (found != 0) {
            uint32_t control = found + 0x3c;
            applyPair(run, control, 0x528140, 0, frame);
            applyPair(run, control, 0x528124, 3, frame);
            finishControl(run, control, frame);
        }
    }
    run.put(menu + 0x294, 0x0);
    return saved;
}

// 0x450e00. Handler for 0x59d9..0x59dc.
uint32_t function_450e00(Run &run, uint32_t menu, uint32_t command, int32_t frame) {
    uint32_t slot = run.automatic(frame + 4);
    if (command == 0x59d9) {
        post(run, menu, 0x8090, frame, 4);
        return 1;
    }
    if (command == 0x59da || command == 0x59db) {
        at(run, frame, 4, 3);
        return run.call(0x450c50, menu, {command, 0xffffffff, 1});
    }
    if (command != 0x59dc)
        return 0;
    soundGated(run, menu, kSelect, slot, frame, 4);
    function_451660(run, menu, 0x2710, frame - 12);
    return 1;
}

// 0x450ed0. Handler for 0x5aa1..0x5aa5 (audio options).
uint32_t function_450ed0(Run &run, uint32_t menu, uint32_t command, int32_t frame) {
    uint32_t slot = run.automatic(frame + 4);
    uint32_t ctlbase = menu + 0x154;
    if (command == 0x5aa1) {
        uint32_t holder = run.get(menu + 0xc);
        if (holder != 0) {
            uint32_t middle = run.get(holder + 0x28);
            uint32_t target = run.get(middle + 0x2c);
            if (target != 0) {
                at(run, frame, 12, 0);
                run.call(0x4b4b40, target);
            }
            uint32_t state = run.get(menu + 0x4);
            uint32_t toggled = run.get(state + 0x10) ^ 1;
            run.put(state + 0x10, toggled);
            run.put(kMaster, toggled);
        }
        uint32_t flags = run.get(menu + 0x290) | 0xd;
        run.put(menu + 0x290, flags);
        uint32_t state = run.get(menu + 0x4);
        uint32_t audio = run.get(state + 0x10);
        at(run, frame, 12, 2);
        run.call(0x4dceb0, ctlbase, {0x5aa2, audio});
        at(run, frame, 12, 2);
        run.call(0x4dceb0, ctlbase, {0x5aa3, audio});
        if (audio != 0) {
            uint32_t owner = soundOwner(run, menu);
            if (run.get(owner + 0x30) == 0) {
                at(run, frame, 12, 1);
                uint32_t found = run.call(0x4061b0, owner, {kSelect});
                if (found != 0) {
                    uint32_t volume = run.get(kVolume);
                    at(run, frame, 12, 4);
                    run.call(0x4208e0, found, {volume, 0, 0, 0});
                }
            }
            uint32_t again = run.get(menu + 0x4);
            uint32_t group = run.get(again + 0x5c);
            at(run, frame, 12, 0);
            run.call(0x402570, group);
        }
        function_4519f0(run, menu, frame - 16);
        return 1;
    }
    if (command == 0x5aa2) {
        uint32_t state = run.get(menu + 0x4);
        uint32_t voice = run.get(state + 0x118) ^ 1;
        run.put(state + 0x118, voice);
        soundPlain(run, menu, kSelect, slot, frame, 12);
        uint32_t owner = soundOwner(run, menu);
        uint32_t entry = lookup(run, owner, kVoice, slot, frame, 12);
        uint32_t again = run.get(menu + 0x4);
        if (run.get(again + 0x118) != 0) {
            if (entry != 0) {
                at(run, frame, 12, 0);
                uint32_t playing = run.call(0x4b3e70, run.get(entry + 0x10));
                if (playing == 0) {
                    if (run.get(kMaster) != 0) {
                        at(run, frame, 12, 0);
                        run.call(0x4b3d80, run.get(entry + 0x10));
                    }
                }
            }
        } else {
            if (entry != 0) {
                at(run, frame, 12, 0);
                uint32_t playing = run.call(0x4b3e70, run.get(entry + 0x10));
                if (playing != 0) {
                    at(run, frame, 12, 0);
                    run.call(0x4b3e30, run.get(entry + 0x10));
                }
            }
        }
        uint32_t flags = run.get(menu + 0x290) | 0x4;
        run.put(menu + 0x290, flags);
        function_4519f0(run, menu, frame - 16);
        return 1;
    }
    if (command == 0x5aa3) {
        uint32_t state = run.get(menu + 0x4);
        uint32_t ambient = run.get(state + 0x11c) ^ 1;
        run.put(state + 0x11c, ambient);
        uint32_t again = run.get(menu + 0x4);
        uint32_t group = run.get(again + 0x5c);
        if (ambient == 0) {
            function_451210(run, group, frame - 16);
        } else {
            if (run.get(group + 0x24) == 0) {
                run.put(group + 0x24, 0x1);
                at(run, frame, 12, 0);
                run.call(0x402570, group);
            }
        }
        soundPlain(run, menu, kSelect, slot, frame, 12);
        uint32_t flags = run.get(menu + 0x290) | 0x8;
        run.put(menu + 0x290, flags);
        function_4519f0(run, menu, frame - 16);
        return 1;
    }
    if (command == 0x5aa4) {
        soundPlain(run, menu, kSelect, slot, frame, 12);
        uint32_t state = run.get(menu + 0x4);
        if (run.get(state + 0xc) == 0) {
            uint32_t music = run.get(state + 0x14) ^ 1;
            run.put(state + 0x14, music);
            if (music != 0) {
                uint32_t again = run.get(menu + 0x4);
                uint32_t object = run.get(again + 0x50);
                at(run, frame, 12, 1);
                run.call(0x4b5570, object, {1});
            } else {
                uint32_t again = run.get(menu + 0x4);
                uint32_t object = run.get(again + 0x50);
                at(run, frame, 12, 0);
                run.call(0x4b55a0, object);
            }
        }
        uint32_t flags = run.get(menu + 0x290) | 0x2;
        run.put(menu + 0x290, flags);
        function_4519f0(run, menu, frame - 16);
        return 1;
    }
    if (command == 0x5aa5) {
        soundGated(run, menu, kSelect, slot, frame, 12);
        function_451660(run, menu, 0x4e23, frame - 20);
        return 1;
    }
    return 0;
}

// 0x451230. Handler for 0x5b05..0x5b08 (display options).
uint32_t function_451230(Run &run, uint32_t menu, uint32_t command, int32_t frame) {
    uint32_t slot = run.automatic(frame + 4);
    if (run.get(menu + 0x4) == 0)
        return 0;
    if (command == 0x5b05) {
        soundPlain(run, menu, kSelect, slot, frame, 8);
        uint32_t state = run.get(menu + 0x4);
        function_42cdf0(run, state, frame - 12);
        uint32_t flags = run.get(menu + 0x294) | 0x1;
        run.put(menu + 0x294, flags);
        at(run, frame, 8, 0);
        run.call(0x450380, menu);
        function_4526f0(run, menu, frame - 12);
        return 1;
    }
    if (command == 0x5b06) {
        soundGated(run, menu, kSelect, slot, frame, 8);
        function_4526f0(run, menu, frame - 12);
        return 1;
    }
    if (command == 0x5b07) {
        soundGated(run, menu, kSelect, slot, frame, 8);
        uint32_t state = run.get(menu + 0x4);
        uint32_t movies = run.get(state + 0x120) ^ 1;
        run.put(state + 0x120, movies);
        uint32_t flags = run.get(menu + 0x294) | 0x2;
        run.put(menu + 0x294, flags);
        function_4526f0(run, menu, frame - 12);
        return 1;
    }
    if (command == 0x5b08) {
        soundGated(run, menu, kSelect, slot, frame, 8);
        function_451660(run, menu, 0x4e23, frame - 16);
        return 1;
    }
    return 0;
}

// 0x451410. Handler for 0x55f1..0x55f2.
uint32_t function_451410(Run &run, uint32_t menu, uint32_t command, int32_t frame) {
    uint32_t slot = run.automatic(frame + 4);
    if (command == 0x55f1) {
        soundGated(run, menu, kSelect, slot, frame, 8);
        run.put(menu + 0x2a8, 0x1);
        post(run, menu, 0x8036, frame, 8);
        post(run, menu, 0x8063, frame, 8);
        return 1;
    }
    if (command == 0x55f2) {
        soundGated(run, menu, kSelect, slot, frame, 8);
        function_451660(run, menu, 0x2710, frame - 16);
        return 1;
    }
    return 0;
}

// 0x451530. Handler for 0x5dc1..0x5dc2.
uint32_t function_451530(Run &run, uint32_t menu, uint32_t command, int32_t frame) {
    uint32_t slot = run.automatic(frame + 4);
    if (command == 0x5dc1) {
        soundPlain(run, menu, kSelect, slot, frame, 8);
        post(run, menu, 0x8036, frame, 8);
        uint32_t state = run.get(menu + 0x4);
        uint32_t wparam = 0x8023;
        if (run.get(state + 0x9c) != 0)
            wparam = 0x8006;
        post(run, menu, wparam, frame, 8);
        run.put(menu + 0x2a8, 0x1);
        return 1;
    }
    if (command == 0x5dc2) {
        soundGated(run, menu, kSelect, slot, frame, 8);
        function_451660(run, menu, 0x2710, frame - 16);
        return 1;
    }
    return 0;
}

// 0x450b50. Dispatcher on (command, flag).
uint32_t function_450b50(Run &run, uint32_t menu, uint32_t command, uint32_t flag, int32_t frame) {
    if (flag == 0) {
        uint32_t slot = run.automatic(frame + 8);
        soundGated(run, menu, kDisable, slot, frame, 0);
        return 0;
    }
    if (command >= 0x4e21 && command <= 0x4e25) {
        at(run, frame, 0, 1);
        return run.call(0x450cf0, menu, {command});
    }
    if (command >= 0x55f1 && command <= 0x55f2)
        return function_451410(run, menu, command, frame - 8);
    if (command >= 0x59d9 && command <= 0x59dc)
        return function_450e00(run, menu, command, frame - 8);
    if (command >= 0x5aa1 && command <= 0x5aa5)
        return function_450ed0(run, menu, command, frame - 8);
    if (command >= 0x5b05 && command <= 0x5b08)
        return function_451230(run, menu, command, frame - 8);
    if (command >= 0x5dc1 && command <= 0x5dc2)
        return function_451530(run, menu, command, frame - 8);
    return 0;
}

// 0x4505f0. Callback shim: loads the menu singleton and dispatches.
uint32_t function_4505f0(Run &run, uint32_t command, uint32_t flag) {
    uint32_t menu = run.get(0x53789c);
    return function_450b50(run, menu, command, flag, -12);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4505f0:
        return function_4505f0(run, arguments[0], arguments[1]);
    case 0x450b50:
        return function_450b50(run, receiver, arguments[0], arguments[1], 0);
    case 0x450e00:
        return function_450e00(run, receiver, arguments[0], 0);
    case 0x450ed0:
        return function_450ed0(run, receiver, arguments[0], 0);
    case 0x451230:
        return function_451230(run, receiver, arguments[0], 0);
    case 0x451410:
        return function_451410(run, receiver, arguments[0], 0);
    case 0x451530:
        return function_451530(run, receiver, arguments[0], 0);
    case 0x451660:
        return function_451660(run, receiver, arguments[0], 0);
    case 0x451210:
        return function_451210(run, receiver, 0);
    case 0x4519f0:
        return function_4519f0(run, receiver, 0);
    case 0x4526f0:
        return function_4526f0(run, receiver, 0);
    case 0x42cdf0:
        return function_42cdf0(run, receiver, 0);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_pause_menu_commands_entry, owned, body)
