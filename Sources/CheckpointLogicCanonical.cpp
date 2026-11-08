// Original checkpoint actor and save publication
// Ordinary checkpoints publish a respawn position; super checkpoints additionally
// publish persistent records through the save cache. Original v1.0 addresses and
// the exported transport ABI remain the dispatch identities.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;
using claw::recovered::v10::ActorFields;
using claw::recovered::v10::LogicHolderFields;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x40af90:
        return 0;
    case 0x422ef0:
        return 1;
    case 0x422ff0:
        return 1;
    case 0x423060:
        return 1;
    case 0x4231a0:
        return 1;
    case 0x4232c0:
        return 1;
    case 0x4232e0:
        return 1;
    case 0x46d620:
        return 3;
    case 0x49a720:
        return 0;
    case 0x49a800:
        return 2;
    case 0x49a860:
        return 3;
    case 0x49a9d0:
        return 3;
    case 0x49aa40:
        return 1;
    case 0x49ae60:
        return 2;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// Explicit original CALL frames preserve aliases of incoming arguments and locals.
uint32_t child(Run &run, int32_t offset, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments) {
    uint32_t frame = run.frame;
    uint32_t stack = run.stackPointer;
    run.frame = run.automatic(offset);
    uint32_t values[16]{};
    uint32_t index = 0;
    for (uint32_t value : arguments) {
        values[index] = value;
        run.put(run.frame + 0x4 + index * 4, value);
        ++index;
    }
    uint32_t result = body(run, function, receiver, values);
    run.frame = frame;
    run.stackPointer = stack;
    return result;
}

uint32_t outside(Run &run, int32_t offset, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
    uint32_t saved = run.stackPointer;
    run.stackPointer = run.automatic(offset);
    uint32_t result = run.call(function, receiver, arguments);
    run.stackPointer = saved;
    return result;
}

// Actor +0x6c is the established holder prefix; holder +0x1c is its state.
// The remaining checkpoint observations stay literal: actor +0x8 flags,
// +0x174 sprite, +0xd0/+0xd8 collision modes, +0x138..+0x144 rectangle,
// +0x188 animation, +0x19c countdown and +0x1a4 finished marker.
// Shared by 0x422ef0 and 0x423060: state 0 initializes the interaction,
// state 5 waits for activation, state 6 rises and state 1 waves.
uint32_t tickCheckpointActor(Run &run, uint32_t actor, bool isSuperCheckpoint) {
    ActorFields tickActorFields{run, actor};
    uint32_t holderToken = tickActorFields.holder();
    LogicHolderFields tickHolderFields{run, holderToken};
    uint32_t state = tickHolderFields.state();
    if (state == 0) {
        if (isSuperCheckpoint && run.get(0x536f00)) {
            run.put(0x536f00, 0);
            tickHolderFields.state(5);
            run.put(actor + 0x8, run.get(actor + 0x8) | 0x10000);
            return 1;
        }
        uint32_t flags = run.get(actor + 0x8);
        uint32_t sprite = run.get(actor + 0x174);
        run.put(actor + 0xd0, 0x800);
        run.put(actor + 0x8, flags | 4);
        run.put(actor + 0xd8, 2);
        if (sprite) {
            run.put(actor + 0x138, run.get(sprite + 0x20) - run.get(sprite + 0x18));
            run.put(actor + 0x13c, run.get(sprite + 0x24) - run.get(sprite + 0x1c));
            run.put(actor + 0x140, run.get(sprite + 0x20) + run.get(sprite + 0x18) - 1);
            run.put(actor + 0x144, run.get(sprite + 0x24) + run.get(sprite + 0x1c) - 1);
        }
        outside(run, -0x14, 0x4c8060, actor, {isSuperCheckpoint ? 0x5227e0u : 0x522838u});
        if (isSuperCheckpoint) {
            run.put(actor + 0x13c, run.get(actor + 0x13c) - 0x40);
        }
        tickHolderFields.state(5);
    } else if (state == 1 || state == 6) {
        outside(run, -0x14, 0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
        if (state == 6 && run.get(actor + 0x1a4) && !run.get(actor + 0x19c)) {
            outside(run, -0x18, 0x4c79e0, actor, {0x525378, 0});
            tickHolderFields.state(1);
        }
    }
    return 1;
}

// 0x40af90.
uint32_t checkpointType(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    (void)run;
    return 3;
}

// 0x422ef0.
uint32_t checkpointTick(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return tickCheckpointActor(run, arguments[0], false);
}

// 0x422ff0. Ordinary death-respawn position lives at player +0x44/+0x48.
// Retain the holder snapshot across animation lookup, then reload actor flags.
uint32_t checkpointActivate(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    uint32_t player = run.get(run.get(0x5371fc) + 0x2c);
    ActorFields activationActorFields{run, actor};
    uint32_t holderToken = activationActorFields.holder();
    LogicHolderFields activationHolderFields{run, holderToken};
    run.put(player + 0x44, run.get(actor + 0x4c));
    run.put(run.get(run.get(0x5371fc) + 0x2c) + 0x48, run.get(actor + 0x50) - 0x20);
    outside(run, -0x14, 0x4c79e0, actor, {0x525390, 0});
    run.put(actor + 0x8, run.get(actor + 0x8) | 1);
    activationHolderFields.state(6);
    run.put(0x53c9f8, run.get(0x53c9f8) + run.get(0x52c6e8));
    return 1;
}

// 0x423060.
uint32_t superCheckpointTick(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return tickCheckpointActor(run, arguments[0], true);
}

// 0x4231a0. First perform ordinary activation, then attempt persistent saving.
// Application +0x48 is cheats, +0x60 save owner and +0xc0 level name.
// Re-read the actor holder after the type callback and the application after
// each save/message callback. Keep those reloads at their original access points.
uint32_t superCheckpointActivate(Run &run, uint32_t receiver, const uint32_t *arguments) {
    checkpointActivate(run, receiver, arguments);
    uint32_t player = run.get(run.get(0x5371fc) + 0x2c);
    uint32_t playerType = outside(run, -0xc, run.get(run.get(player) + 0x10), player);
    if (playerType != 3) {
        return 1;
    }
    uint32_t application = run.get(0x5371fc);
    if (run.get(run.get(application + 0xc0) - 0x8)) {
        return 1;
    }
    ActorFields superActorFields{run, arguments[0]};
    uint32_t callbackHolderToken = superActorFields.holder();
    uint32_t callback = run.get(callbackHolderToken + 0x10);
    uint32_t checkpointKind;
    if (callback == 0x4232c0) {
        checkpointKind = 1;
    } else if (callback == 0x4232e0) {
        checkpointKind = 2;
    } else {
        return 1;
    }
    if (run.get(run.get(application + 0x48) + 0x128)) {
        outside(run, -0x10, 0x42af70, application, {0x5253c4});
        return 1;
    }
    uint32_t liveActor = run.get(0x537e88);
    uint32_t result = child(run, -0x18, 0x46d620, run.get(application + 0x2c), {run.get(liveActor + 0x4c), run.get(liveActor + 0x50), checkpointKind});
    if (result) {
        outside(run, -0xc, 0x49bbc0, run.get(run.get(0x5371fc) + 0x60));
        outside(run, -0x10, 0x42af70, run.get(0x5371fc), {0x5253a8});
        outside(run, -0xc, 0x42abf0, run.get(0x5371fc));
    }
    return 1;
}

// 0x4232c0.
uint32_t superCheckpointOneTick(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    run.put(0x536efc, 1);
    return child(run, -0x8, 0x423060, 0, {arguments[0]});
}

// 0x4232e0.
uint32_t superCheckpointTwoTick(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    run.put(0x536efc, 2);
    return child(run, -0x8, 0x423060, 0, {arguments[0]});
}

// 0x46d620. Player +0x258 inhibits publication; +0x168 is a flags byte,
// +0x164 accumulated elapsed time and +0x14 level. A positive signed x or y
// selects a persistent super checkpoint; nonpositive coordinates select level
// completion (kind 3), including overwriting the actual third argument slot.
// Live actor is a snapshot, but flags and level are reloaded after date calls.
uint32_t publishCheckpoint(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (run.get(receiver + 0x258)) {
        return 0;
    }
    uint32_t liveActor = run.get(0x537e88);
    bool checkpoint = s32(arguments[0]) > 0 || s32(arguments[1]) > 0;
    run.put(run.automatic(-0xb4), checkpoint ? 1 : 0);
    uint32_t checkpointKind = arguments[2];
    if (!checkpoint) {
        checkpointKind = 3;
        run.put(run.automatic(0xc), 3);
    } else {
        if (!liveActor || (checkpointKind != 1 && checkpointKind != 2)) {
            return 0;
        }
        if (run.get8(receiver + 0x168) & 1) {
            return 0;
        }
        if (run.get(run.get(run.get(receiver + 0x4) + 0x48) + 0x128)) {
            return 0;
        }
    }
    uint32_t profileCache = run.get(run.get(receiver + 0x4) + 0x64);
    if (!profileCache) {
        return 0;
    }
    // Keep guest stack storage: the record, embedded scores and incoming kind
    // slot can alias original callees, so host-side structs would change behavior.
    uint32_t checkpointRecordToken = run.automatic(-0xb0);
    uint32_t levelScoreToken = run.automatic(-0x60);
    for (uint32_t index = 0; index < 0x2c; ++index) {
        run.put(checkpointRecordToken + index * 4, 0);
    }
    uint32_t totalElapsed;
    uint32_t collectibleCounts;
    if (checkpoint) {
        ActorFields liveActorFields{run, liveActor};
        uint32_t liveHolderToken = liveActorFields.holder();
        uint32_t state = run.get(liveHolderToken + 0x14);
        if (!state) {
            return 0;
        }
        run.put(checkpointRecordToken + 0x4, arguments[0]);
        run.put(checkpointRecordToken + 0x8, arguments[1]);
        totalElapsed = run.get(receiver + 0x164);
        run.put(checkpointRecordToken + 0x94, run.get(liveActor + 0x10c));
        run.put(checkpointRecordToken + 0x98, run.get(state + 0x70));
        run.put(checkpointRecordToken + 0x9c, run.get(state + 0x74));
        run.put(checkpointRecordToken + 0xa0, run.get(state + 0x78));
        run.put(checkpointRecordToken + 0xa4, run.get(state + 0x7c));
        uint32_t levelElapsed = run.get(0x537210);
        totalElapsed += levelElapsed;
        child(run, -0xd4, 0x49a9d0, 0, {levelScoreToken, state + 0x88, levelElapsed});
        collectibleCounts = state + 0xb0;
    } else {
        run.put(checkpointRecordToken, run.get(checkpointRecordToken) | 1);
        run.put(checkpointRecordToken + 0x4, 0);
        run.put(checkpointRecordToken + 0x8, 0);
        run.put(checkpointRecordToken + 0x9c, run.get(0x534cf4));
        run.put(checkpointRecordToken + 0x94, run.get(0x534cc8));
        run.put(checkpointRecordToken + 0x98, run.get(0x534cf0));
        totalElapsed = run.get(receiver + 0x164);
        run.put(checkpointRecordToken + 0xa0, run.get(0x534cf8));
        run.put(checkpointRecordToken + 0xa4, run.get(0x534cfc));
        uint32_t levelElapsed = run.get(receiver + 0x164 + run.get(receiver + 0x14) * 0x10);
        child(run, -0xd4, 0x49a9d0, 0, {levelScoreToken, 0x534d08, levelElapsed});
        collectibleCounts = 0x534d30;
    }
    child(run, -0xd4, 0x49a9d0, 0, {checkpointRecordToken + 0xc, collectibleCounts, totalElapsed});
    checkpointKind = run.get(run.automatic(0xc));
    if (!(run.get8(receiver + 0x168) & 1)) {
        child(run, -0xd4, 0x49a860, profileCache, {run.get(receiver + 0x14), checkpointRecordToken, checkpointKind});
        if (!checkpoint) {
            child(run, -0xd0, 0x49a800, profileCache, {run.get(receiver + 0x14), levelScoreToken});
            child(run, -0xd0, 0x49a800, profileCache, {0, checkpointRecordToken + 0xc});
        }
    } else if (!checkpoint) {
        uint32_t destination = child(run, -0xd0, 0x49ae60, profileCache, {run.get(receiver + 0x14), checkpointKind});
        if (destination) {
            run.put(destination, run.get(destination) | 1);
        }
    }
    return 1;
}

// 0x49ae60. Cache checkpoint blocks contain fifteen 0xb0-byte records each.
// Kind 1 starts at +0x2d4, kind 2 at +0xd24, completion at +0x1774.
// This computes wrapped guest addresses without dereferencing the receiver.
uint32_t checkpointRecord(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    uint32_t level = arguments[0];
    uint32_t checkpointKind = arguments[1];
    if (s32(level) < 0 || s32(level) >= 15) {
        return 0;
    }
    if (checkpointKind == 1) {
        return receiver + level * 0xb0 + 0x2d4;
    }
    if (checkpointKind == 2) {
        return receiver + level * 0xb0 + 0xd24;
    }
    if (checkpointKind == 3) {
        return receiver + level * 0xb0 + 0x1774;
    }
    return 0;
}

// 0x49a720. Reset each record while retaining its completion bit.
// Per-level scores at cache +0x21c4 have stride 0x44.
uint32_t resetCheckpointCache(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    for (uint32_t level = 0; level < 15; ++level) {
        for (uint32_t checkpointKind = 1; checkpointKind <= 3; ++checkpointKind) {
            uint32_t destination = child(run, -0x20, 0x49ae60, receiver, {level, checkpointKind});
            if (destination) {
                uint32_t retained = run.get(destination) & 1;
                run.put(run.automatic(-0x4), retained);
                for (uint32_t index = 0; index < 0x2c; ++index) {
                    run.put(destination + index * 4, 0);
                }
                if (retained) {
                    run.put(destination, run.get(destination) | 1);
                }
                run.put(destination, run.get(destination) | (0x8u << checkpointKind));
            }
        }
        for (uint32_t index = 0; index < 0x11; ++index) {
            run.put(receiver + 0x21c4 + level * 0x44 + index * 4, 0);
        }
    }
    return 0;
}

// 0x49a800. Score +0x4 is the unsigned weighted total; +0x8 is elapsed time.
// A greater total wins; equal totals accept an equal or shorter elapsed time. The copy
// remains a forward word copy so overlapping source/destination stays observable.
uint32_t publishBestScore(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t level = arguments[0];
    uint32_t source = arguments[1];
    if (s32(level) < 0 || s32(level) >= 15 || !source) {
        return 0;
    }
    uint32_t destination = receiver + level * 0x44 + 0x21c4;
    if (!destination) {
        return 0;
    }
    uint32_t oldScore = run.get(destination + 0x4);
    uint32_t newScore = run.get(source + 0x4);
    if (oldScore > newScore) {
        return 0;
    }
    if (oldScore == newScore && run.get(destination + 0x8) < run.get(source + 0x8)) {
        return 0;
    }
    for (uint32_t index = 0; index < 0x11; ++index) {
        run.put(destination + index * 4, run.get(source + index * 4));
    }
    return 1;
}

// 0x49a860. Forward word copy deliberately preserves overlapping input behavior.
uint32_t publishCheckpointRecord(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t level = arguments[0];
    uint32_t source = arguments[1];
    uint32_t checkpointKind = arguments[2];
    if (s32(level) < 0 || s32(level) >= 15 || !source || (checkpointKind != 1 && checkpointKind != 2 && checkpointKind != 3)) {
        return 0;
    }
    uint32_t destination = child(run, -0x18, 0x49ae60, receiver, {level, checkpointKind});
    if (!destination) {
        return 0;
    }
    for (uint32_t index = 0; index < 0x2c; ++index) {
        run.put(destination + index * 4, run.get(source + index * 4));
    }
    uint32_t flags = (run.get(destination) & 0xffffff8f) | 2;
    run.put(destination, flags);
    run.put(destination, flags | (0x8u << checkpointKind));
    return 1;
}

// 0x49a9d0. Score +0x1c..+0x40 stores the ten collectible counts.
// Copy before weighting; uint32_t multiply/add deliberately retains wraparound.
uint32_t buildScoreRecord(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t destination = arguments[0];
    uint32_t source = arguments[1];
    if (!destination || !source) {
        return 0;
    }
    run.put(destination + 0x8, arguments[2]);
    for (uint32_t index = 0; index < 10; ++index) {
        run.put(destination + 0x1c + index * 4, run.get(source + index * 4));
    }
    uint32_t score = 0;
    for (uint32_t index = 0; index < 10; ++index) {
        score += run.get(destination + 0x1c + index * 4) * run.get(0x52d698 + index * 4);
    }
    run.put(destination + 0x4, score);
    child(run, -0x14, 0x49aa40, 0, {destination});
    return 1;
}

// 0x49aa40. The original time wrapper writes the incoming argument slot itself.
// Preserve all three localtime calls and read each returned calendar separately;
// score +0xc/+0x10/+0x14 stores month/day/year, respectively.
uint32_t stampScoreDate(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t destination = arguments[0];
    if (!destination) {
        return 0;
    }
    uint32_t timeSlot = run.automatic(0x4);
    outside(run, -0xc, 0x4f504f, 0, {timeSlot});
    uint32_t calendarToken = outside(run, -0xc, 0x4f5062, timeSlot, {0});
    run.put(destination + 0xc, run.get(calendarToken + 0x10) + 1);
    calendarToken = outside(run, -0xc, 0x4f5062, timeSlot, {0});
    run.put(destination + 0x10, run.get(calendarToken + 0xc));
    calendarToken = outside(run, -0xc, 0x4f5062, timeSlot, {0});
    run.put(destination + 0x14, run.get(calendarToken + 0x14) + 1900);
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40af90:
        return checkpointType(run, receiver, arguments);
    case 0x422ef0:
        return checkpointTick(run, receiver, arguments);
    case 0x422ff0:
        return checkpointActivate(run, receiver, arguments);
    case 0x423060:
        return superCheckpointTick(run, receiver, arguments);
    case 0x4231a0:
        return superCheckpointActivate(run, receiver, arguments);
    case 0x4232c0:
        return superCheckpointOneTick(run, receiver, arguments);
    case 0x4232e0:
        return superCheckpointTwoTick(run, receiver, arguments);
    case 0x46d620:
        return publishCheckpoint(run, receiver, arguments);
    case 0x49a720:
        return resetCheckpointCache(run, receiver, arguments);
    case 0x49a800:
        return publishBestScore(run, receiver, arguments);
    case 0x49a860:
        return publishCheckpointRecord(run, receiver, arguments);
    case 0x49a9d0:
        return buildScoreRecord(run, receiver, arguments);
    case 0x49aa40:
        return stampScoreDate(run, receiver, arguments);
    case 0x49ae60:
        return checkpointRecord(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_checkpoint_logic_entry, owned, body)
