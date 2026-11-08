// v1.3 sliding and crumbling peg callbacks.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4a0f30:
    case 0x4a1230:
    case 0x4a1430:
    case 0x4a2080:
        return 1;
    default:
        return -1;
    }
}

uint32_t callAt(Run &run, uint32_t saved, uint32_t function, uint32_t receiver,
                std::initializer_list<uint32_t> arguments = {}) {
    run.stackPointer = run.frame - saved - 4u * uint32_t(arguments.size()) - 4u;
    return run.call(function, receiver, arguments);
}

// +0x194 animation, +0x190 frame, +0x198 frame data.
void selectFrame(Run &run, uint32_t object, uint32_t offset, uint32_t saved) {
    uint32_t animation = run.get(object + 0x194);
    if (!animation)
        return;
    uint32_t frame = run.get(animation + offset);
    run.put(object + 0x190, frame);
    uint32_t data = callAt(run, saved, 0x40fbe0, animation, {frame});
    run.put(object + 0x198, data);
}

// +0x144..0x150 collision rectangle, copied from the level defaults.
void rectangle(Run &run, uint32_t object, uint32_t offset) {
    uint32_t defaults = run.get(0x5360a8) + offset;
    run.put(object + 0x144, run.get(defaults));
    run.put(object + 0x148, run.get(defaults + 0x04));
    run.put(object + 0x14c, run.get(defaults + 0x08));
    run.put(object + 0x150, run.get(defaults + 0x0c));
    run.put(object + 0x150, run.get(object + 0x150) + 0x20);
}

// +0x74 activation distance, +0x08 object flags.
void activationDistance(Run &run, uint32_t object) {
    if (run.get(object + 0x74) == 0) {
        run.put(object + 0x74, 2000);
        run.put(object + 0x08, run.get(object + 0x08) | 0x20000);
    }
}

void midpoint(Run &run, uint32_t object, uint32_t logic) {
    uint32_t animation = run.get(object + 0x194);
    if (animation) {
        uint32_t sum = run.get(animation + 0x68) + run.get(animation + 0x64);
        run.put(logic + 0x64, uint32_t(s32(sum) / 2));
    }
}

void slideSound(Run &run, uint32_t object) {
    uint32_t position = run.get(object + 0x5c);
    uint32_t audio = run.get(run.get(object + 0x0c) + 0x28);
    callAt(run, 0x10, 0x4cb050, audio, {0x526d84, position, 0, 0});
}

// +0x1a0 animation progression; +0x1c8 completed, +0x1c0 active.
void updateAnimation(Run &run, uint32_t object, uint32_t logic, uint32_t category, uint32_t saved) {
    callAt(run, saved, 0x4c8550, object + 0x1a0, {run.get(0x5aafd8)});
    if (run.get(object + 0x190) == run.get(logic + 0x64))
        run.put(object + 0xe8, category);
}

bool completed(Run &run, uint32_t object) {
    return run.get(object + 0x1c8) != 0 && run.get(object + 0x1c0) == 0;
}

// 0x4a0f30. SlidingElevator; cheat Easy is distinct from profile Easy.
uint32_t function_4a0f30(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t logic = run.get(object + 0x7c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        selectFrame(run, object, 0x68, 0x10);
        run.put(object + 0xe8, 0x80);
        run.put(object + 0x08, run.get(object + 0x08) | 1);
        callAt(run, 0x10, 0x4c6e40, object, {0x52c1bc, 0});
        run.put(object + 0x174, 0);
        run.put(object + 0x178, 0);
        selectFrame(run, object, 0x64, 0x10);
        activationDistance(run, object);
        rectangle(run, object, 0x58);
        if (run.get(object + 0x164) == 0)
            run.put(object + 0x164, 2000);
        run.put(object + 0xe8, 1);
        callAt(run, 0x10, 0x4c6e40, object, {0x52c1ac, 0});
        run.put(logic + 0x1c, 0x3ec);
        uint32_t delay = run.get(object + 0x164);
        if (delay == 0xffffffff) {
            uint32_t random = callAt(run, 0x10, 0x4a595b, 0);
            run.put(logic + 0x20, uint32_t(s32(random) % 3001));
        } else if (s32(delay) > 0) {
            run.put(logic + 0x20, delay);
        }
        midpoint(run, object, logic);
    } else if (state == 0x3ea || state == 0x3ec) {
        slideSound(run, object);
        run.put(logic + 0x1c, state == 0x3ea ? 0x3ed : 0x3eb);
    } else if (state == 0x3eb) {
        updateAnimation(run, object, logic, 1, 0x10);
        if (completed(run, object)) {
            run.put(object + 0xe8, 1);
            callAt(run, 0x10, 0x4c6e40, object, {0x52c1bc, 0});
            uint32_t delay = run.get(object + 0x164);
            if (delay == 0xffffffff) {
                uint32_t random = callAt(run, 0x10, 0x4a595b, 0);
                run.put(logic + 0x1c, 0x3ea);
                run.put(logic + 0x20, uint32_t(s32(random) % 2001) + 500);
            } else {
                run.put(logic + 0x20, delay);
                run.put(logic + 0x1c, 0x3ea);
            }
        }
    } else if (state == 0x3ed) {
        updateAnimation(run, object, logic, 0x80, 0x10);
        if (completed(run, object)) {
            run.put(object + 0xe8, 0x80);
            if (run.get(0x535950) != 0)
                return 1;
            callAt(run, 0x10, 0x4c6e40, object, {0x52c1ac, 0});
            uint32_t delay = run.get(object + 0x164);
            if (delay == 0xffffffff) {
                uint32_t random = callAt(run, 0x10, 0x4a595b, 0);
                run.put(logic + 0x20, uint32_t(s32(random) % 2001) + 500);
            } else {
                run.put(logic + 0x20, delay);
            }
            run.put(logic + 0x1c, 0x3ec);
            if (run.get(object + 0x164) == 0xfffffffe)
                run.put(logic + 0x1c, 5);
        }
    }
    return 1;
}

// 0x4a1230 and 0x4a1430 share initialization and standing/event initiation.
uint32_t crumble(Run &run, uint32_t object, bool respawning) {
    uint32_t logic = run.get(object + 0x7c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        selectFrame(run, object, 0x64, 0x0c);
        run.put(object + 0xe8, 0x80);
        run.put(object + 0x08, run.get(object + 0x08) | 1);
        callAt(run, 0x0c, 0x4c6e40, object, {0x52c1ac, 0});
        run.put(object + 0x174, 0);
        run.put(object + 0x178, 0);
        uint32_t defaults = run.get(0x5360a8) + 0x78;
        run.put(object + 0x144, run.get(defaults));
        run.put(object + 0x148, run.get(defaults + 0x04));
        run.put(object + 0x14c, run.get(defaults + 0x08));
        uint32_t bottom = run.get(defaults + 0x0c);
        if (respawning)
            run.put(object + 0x40, run.get(object + 0x40) & 0xfffffffe);
        run.put(object + 0x150, bottom);
        run.put(object + 0x150, run.get(object + 0x150) + 0x20);
        run.put(object + 0x180, run.get(object + 0x180) | 0x8000);
        activationDistance(run, object);
        if (run.get(object + 0x164) == 0)
            run.put(object + 0x164, 25);
        if (respawning && run.get(object + 0x12c) == 0)
            run.put(object + 0x12c, 4);
        run.put(logic + 0x1c, 5);
        midpoint(run, object, logic);
    } else if (state == 5 || state == 0x457) {
        if (run.get(0x535950) != 0)
            return 1;
        if (state == 5) {
            uint32_t player = run.get(0x5365d4);
            if (!(run.get8(player + 0x08) & 0x10))
                return 1;
            if (run.get(player + 0x98) != object)
                return 1;
        }
        uint32_t delay = run.get(object + 0x164);
        run.put(logic + 0x1c, 0x3ea);
        run.put(logic + 0x20, delay);
    } else if (state == 0x3ea) {
        uint32_t audio = run.get(run.get(object + 0x0c) + 0x28);
        if (run.get(audio + 0x30) == 0) {
            uint32_t local = run.automatic(0x04);
            run.put(local, 0);
            callAt(run, 0x0c, 0x4fc6b4, audio + 0x10, {0x52c1cc, local});
            uint32_t sound = run.get(local);
            if (sound)
                callAt(run, 0x0c, 0x421bb0, sound, {run.get(0x530990), 0, 0, 0});
        }
        run.put(logic + 0x1c, 0x3ed);
    } else if (state == 0x3ed) {
        updateAnimation(run, object, logic, 1, 0x0c);
        if (completed(run, object)) {
            if (respawning) {
                run.put(object + 0x40, run.get(object + 0x40) | 1);
                run.put(logic + 0x1c, 0x17);
                uint32_t playerLogic = run.get(run.get(0x5365d4) + 0x7c);
                uint32_t progress = run.get(run.get(playerLogic + 0x14) + 0x80);
                run.put(logic + 0x64, progress);
            } else {
                run.put(object + 0x08, run.get(object + 0x08) | 0x10000);
            }
        }
    } else if (respawning && state == 0x17) {
        uint32_t playerLogic = run.get(run.get(0x5365d4) + 0x7c);
        uint32_t progress = run.get(run.get(playerLogic + 0x14) + 0x80);
        if (s32(run.get(logic + 0x64)) < s32(progress))
            run.put(logic + 0x1c, 0);
    }
    return 1;
}

uint32_t function_4a1230(Run &run, uint32_t, const uint32_t *arguments) {
    return crumble(run, arguments[0], false);
}

uint32_t function_4a1430(Run &run, uint32_t, const uint32_t *arguments) {
    return crumble(run, arguments[0], true);
}

// 0x4a2080. TogglePeg's profile Easy initialization remains independent.
uint32_t function_4a2080(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t logic = run.get(object + 0x7c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        run.put(object + 0x174, 0);
        run.put(object + 0x178, 0);
        selectFrame(run, object, 0x64, 0x10);
        uint32_t flags = run.get(object + 0x08) | 1;
        run.put(object + 0xe8, 0x80);
        run.put(object + 0x08, flags);
        rectangle(run, object, 0x58);
        if (run.get(object + 0x74) == 0) {
            run.put(object + 0x74, 2000);
            run.put(object + 0x08, flags | 0x20000);
        }
        uint32_t callback = run.get(logic + 0x10);
        if (callback == 0x4a2350)
            run.put(logic + 0xbc, 750);
        else if (callback == 0x4a2370)
            run.put(logic + 0xbc, 1500);
        else if (callback == 0x4a2390)
            run.put(logic + 0xbc, 2250);
        callAt(run, 0x10, 0x4a2010, 0, {object, logic});
        run.put(logic + 0x1c, 0x3ee);
        midpoint(run, object, logic);
        if (run.get(0x535990) != 0 || run.get(object + 0x124) == 1)
            run.put(logic + 0x1c, 5);
    } else if (state == 0x3ea) {
        slideSound(run, object);
        run.put(logic + 0x1c, 0x3ed);
    } else if (state == 0x3ec) {
        run.put(object + 0xe8, 1);
        callAt(run, 0x10, 0x4c6e40, object, {0x52c1ac, 0});
        slideSound(run, object);
        run.put(logic + 0x1c, 0x3eb);
    } else if (state == 0x3eb) {
        updateAnimation(run, object, logic, 1, 0x10);
        if (completed(run, object)) {
            run.put(object + 0xe8, 1);
            callAt(run, 0x10, 0x4c6e40, object, {0x52c1bc, 0});
            run.put(logic + 0x1c, 0x3ef);
        }
    } else if (state == 0x3ed) {
        updateAnimation(run, object, logic, 0x80, 0x10);
        if (completed(run, object)) {
            run.put(object + 0xe8, 0x80);
            if (run.get(0x535950) != 0)
                return 1;
            callAt(run, 0x10, 0x4c6e40, object, {0x52c1ac, 0});
            run.put(logic + 0x1c, 0x3ee);
        }
    } else if (state == 0x3ee || state == 0x3ef) {
        uint32_t interval = callAt(run, 0x10, 0x4a2050, 0, {object, logic, run.get(0x535928)});
        if (state == 0x3ee && interval == 0)
            run.put(logic + 0x1c, 0x3ec);
        if (state == 0x3ef && interval != 0)
            run.put(logic + 0x1c, 0x3ea);
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4a0f30:
        return function_4a0f30(run, receiver, arguments);
    case 0x4a1230:
        return function_4a1230(run, receiver, arguments);
    case 0x4a1430:
        return function_4a1430(run, receiver, arguments);
    case 0x4a2080:
        return function_4a2080(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_v13_cheat_pegs_entry, owned, body)
