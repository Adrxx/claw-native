// Level 1 timer and checkpoint state: timed HUD positioning and actor lists.
// Original v1.0 entry addresses remain in the comments and dispatch below.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;
using claw::recovered::v10::ActorFields;
using claw::recovered::v10::LogicHolderFields;
using claw::recovered::v10::ActorStorageSceneFields;
using claw::recovered::v10::ActorContainerFields;
using claw::recovered::v10::ActorListNodeFields;
using claw::recovered::v10::ActorStorageFields;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4919f0:
        return 1;
    case 0x491ed0:
        return 1;
    case 0x4c8e00:
        return 6;
    case 0x4c8f60:
        return 6;
    case 0x4d3ca0:
        return 6;
    case 0x4d3e50:
        return 6;
    case 0x4d3ef0:
        return 0;
    case 0x4d3f20:
        return 1;
    default:
        return -1;
    }
}

// Preserve the original cdq/sub/sar sequence: subtract in 32 bits before
// interpreting the wrapped difference as signed. Negative odd values round
// toward zero; replacing the whole bounds expression with signed subtraction
// could introduce overflow that the original does not have.
uint32_t halveWrappedSignedDifference(uint32_t difference) {
    uint32_t sign = 0;
    if (s32(difference) < 0)
        sign = 0xffffffff;
    uint32_t adjusted = difference - sign;
    uint32_t halved = uint32_t(s32(adjusted) >> 1);
    return halved;
}

// 0x4919f0. cdecl(owner), always returns 1. State 0 activates the owner;
// state 5 positions its target against the four bounds at 0x5370c8..0x5370d4.
// The frame-state fields below have no shared checked layout yet. Keep their
// accesses literal, in original order: +0x04/+0x0c axis modes, +0x08/+0x10 offsets,
// +0x14 last tick,
// +0x18 last allowed tick, +0x24 target token. The tick unit and fields +0x1c,
// +0x20 remain unproven; clock+0x6c is only a signed same-tick refresh test.
uint32_t updateTimedFramePosition(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t ownerToken = arguments[0];
    ActorFields ownerFields{run, ownerToken};
    ActorStorageFields ownerStorageFields{run, ownerToken};
    uint32_t holderToken = ownerFields.holder();
    LogicHolderFields holderFields{run, holderToken};
    uint32_t logicState = holderFields.state();
    if (logicState == 0) {
        uint32_t flags = ownerStorageFields.flags();
        flags |= 1;
        ownerStorageFields.flags(flags);
        holderFields.state(5);
        return 1;
    }
    if (logicState != 5)
        return 1;
    uint32_t frameStateToken = holderFields.logic();
    if (frameStateToken == 0)
        return 1;
    uint32_t clockToken = run.get(0x5371fc);
    uint32_t lastTick = run.get(frameStateToken + 0x14);
    uint32_t currentTick = run.get(clockToken + 0x68);
    if (lastTick == currentTick) {
        uint32_t unknown_0x6c = run.get(clockToken + 0x6c);
        if (s32(unknown_0x6c) <= 0)
            return 1;
    }
    uint32_t lastAllowedTick = run.get(frameStateToken + 0x18);
    run.put(frameStateToken + 0x14, currentTick);
    if (s32(currentTick) > s32(lastAllowedTick))
        return 1;
    uint32_t xMode = run.get(frameStateToken + 0x04);
    if (xMode == 1) {
        uint32_t value = run.get(frameStateToken + 0x08);
        uint32_t bound = run.get(0x5370c8);
        value += bound;
        uint32_t targetToken = run.get(frameStateToken + 0x24);
        run.put(targetToken + 0x4c, value);
    } else if (xMode == 2) {
        uint32_t value = run.get(frameStateToken + 0x08);
        uint32_t bound = run.get(0x5370d0);
        value += bound;
        uint32_t targetToken = run.get(frameStateToken + 0x24);
        run.put(targetToken + 0x4c, value);
    } else if (xMode == 3) {
        uint32_t high = run.get(0x5370d0);
        uint32_t low = run.get(0x5370c8);
        uint32_t value = halveWrappedSignedDifference(high - low);
        uint32_t offset = run.get(frameStateToken + 0x08);
        value += offset;
        value += low;
        uint32_t targetToken = run.get(frameStateToken + 0x24);
        run.put(targetToken + 0x4c, value);
    }
    uint32_t yMode = run.get(frameStateToken + 0x0c);
    if (yMode == 3) {
        uint32_t high = run.get(0x5370d4);
        uint32_t low = run.get(0x5370cc);
        uint32_t value = halveWrappedSignedDifference(high - low);
        uint32_t offset = run.get(frameStateToken + 0x10);
        value += offset;
        value += low;
        uint32_t targetToken = run.get(frameStateToken + 0x24);
        run.put(targetToken + 0x50, value);
    } else if (yMode == 4) {
        uint32_t value = run.get(frameStateToken + 0x10);
        uint32_t bound = run.get(0x5370cc);
        value += bound;
        uint32_t targetToken = run.get(frameStateToken + 0x24);
        run.put(targetToken + 0x50, value);
    } else if (yMode == 5) {
        uint32_t value = run.get(frameStateToken + 0x10);
        uint32_t bound = run.get(0x5370d4);
        value += bound;
        uint32_t targetToken = run.get(frameStateToken + 0x24);
        run.put(targetToken + 0x50, value);
    }
    // Reload rather than reuse currentTick: guest accesses may alias this field.
    uint32_t publishedTick = run.get(frameStateToken + 0x14);
    if (publishedTick != 0)
        return 1;
    uint32_t targetToken = run.get(frameStateToken + 0x24);
    run.put(frameStateToken + 0x14, currentTick);
    uint32_t servicesToken = run.get(targetToken + 0x0c);
    uint32_t unknown_0x174 = run.get(targetToken + 0x174);
    uint32_t positionSinkToken = run.get(servicesToken + 0x0c);
    uint32_t y = run.get(targetToken + 0x50);
    uint32_t x = run.get(targetToken + 0x4c);
    run.vcall(positionSinkToken, 0x28, {x, y, unknown_0x174});
    // The position callback can replace the target; use its current token.
    targetToken = run.get(frameStateToken + 0x24);
    uint32_t targetFlags = run.get(targetToken + 0x40);
    targetFlags |= 1;
    run.put(targetToken + 0x40, targetFlags);
    run.put(frameStateToken + 0x20, 0);
    run.put(frameStateToken + 0x1c, 1);
    return 1;
}

// 0x4d3ca0. thiscall, 6 stack arguments, returns the new object or 0.
// Object: +0x08 flags, +0x68 list node, +0x6c sub-object, +0x188 helper.
// this: +0x0c owner services, +0x1b4 list, +0x1b8 list head. The private
// initialized words +0x168..+0x184 retain raw offsets: their meanings are unknown.
uint32_t createAndAppendActor(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actorToken = run.call(0x4f63ec, 0, {0x1b4});
    ActorFields actorFields{run, actorToken};
    ActorStorageFields actorStorageFields{run, actorToken};
    ActorContainerFields containerFields{run, receiver};
    uint32_t holderToken = 0;
    if (actorToken != 0) {
        uint32_t servicesToken = containerFields.scene();
        run.call(0x4c9780, actorToken, {servicesToken, arguments[0], arguments[5]});
        run.call(0x4c96c0, actorToken + 0x88);
        run.call(0x4c9690, actorToken + 0xa4);
        run.put(actorToken, 0x513770);
        actorStorageFields.unknown_0x4c(0x80000000);
        actorStorageFields.listNode(0);
        holderToken = run.call(0x4f63ec, 0, {0x174});
        if (holderToken != 0)
            holderToken = run.call(0x4c9830, holderToken, {servicesToken, arguments[0], 0});
        actorFields.holder(holderToken);
        actorStorageFields.unknown_0x84(0);
        actorStorageFields.unknown_0x80(0);
        actorStorageFields.secondaryHolder(0);
        actorStorageFields.contactHolder(0);
        run.call(0x4c9ba0, actorToken + 0x188);
        run.put(actorToken, 0x5137f0);
        run.put(actorToken + 0x168, 0xffffffff);
        run.put(actorToken + 0x16c, 0xffffffff);
        run.put(actorToken + 0x174, 0);
        run.put(actorToken + 0x170, 0);
        run.put(actorToken + 0x178, 0);
        run.put(actorToken + 0x17c, 0);
        run.put(actorToken + 0x180, 0);
        run.put(actorToken + 0x184, 0);
    }
    if (actorToken == 0)
        return 0;
    uint32_t initialized = run.vcall(actorToken, 0x28, {arguments[1], arguments[2], arguments[3], arguments[4]});
    if (initialized == 0) {
        run.vcall(actorToken, 0x04, {1});
        return 0;
    }
    uint32_t listNodeToken = run.call(0x4f51c5, receiver + 0x1b4, {actorToken});
    if (listNodeToken == 0) {
        run.vcall(actorToken, 0x04, {1});
        return 0;
    }
    actorStorageFields.listNode(listNodeToken);
    uint32_t flags = actorStorageFields.flags();
    if ((flags & 0x200000) != 0) {
        uint32_t callbackHolderToken = actorFields.holder();
        uint32_t methodToken = run.get(callbackHolderToken + 0x10);
        run.call(methodToken, 0, {actorToken});
    }
    return actorToken;
}

// 0x4d3e50. thiscall, 6 stack arguments. Looks argument 5 up in a map. EAX is 0
// when nothing is found, otherwise the result of 0x4d3ca0 (the object or 0).
uint32_t lookupAndAppendActor(Run &run, uint32_t receiver, const uint32_t *arguments) {
    ActorContainerFields containerFields{run, receiver};
    uint32_t lookupResultToken = run.automatic(-4);
    uint32_t servicesToken = containerFields.scene();
    ActorStorageSceneFields sceneFields{run, servicesToken};
    uint32_t resourceMapToken = sceneFields.registry();
    resourceMapToken += 0x10;
    run.put(lookupResultToken, 0);
    run.call(0x4f6286, resourceMapToken, {arguments[4], lookupResultToken});
    uint32_t resourceToken = run.get(lookupResultToken);
    if (resourceToken == 0)
        return 0;
    uint32_t createArguments[6] = {arguments[0], arguments[1], arguments[2], arguments[3], resourceToken, arguments[5]};
    uint32_t result = createAndAppendActor(run, receiver, createArguments);
    return result;
}

// 0x4c8e00. thiscall, 6 stack arguments, returns the new object or 0.
// this: +0x0c owner services, +0x10 list, +0x14 list head. Object is 0x1d0 bytes.
uint32_t createDepthSortedActor(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actorToken = run.call(0x4f63ec, 0, {0x1d0});
    ActorFields actorFields{run, actorToken};
    ActorStorageFields actorStorageFields{run, actorToken};
    ActorContainerFields containerFields{run, receiver};
    if (actorToken != 0) {
        uint32_t servicesToken = containerFields.scene();
        run.call(0x4c98c0, actorToken, {servicesToken, arguments[0], arguments[5]});
        run.put(actorToken + 0x188, 0x513870);
        run.put(actorToken + 0x18c, 0);
        run.put(actorToken + 0x190, 0);
        run.put(actorToken + 0x194, 0);
        run.put(actorToken, 0x5137f0);
        run.put(actorToken + 0x168, 0xffffffff);
        run.put(actorToken + 0x16c, 0xffffffff);
        run.put(actorToken + 0x174, 0);
        run.put(actorToken + 0x170, 0);
        run.put(actorToken + 0x178, 0);
        run.put(actorToken + 0x17c, 0);
        run.put(actorToken + 0x180, 0);
        run.put(actorToken + 0x184, 0);
        run.call(0x4f5620, actorToken + 0x1b4, {0x0a});
        run.put(actorToken, 0x513830);
    }
    // A null allocation faults on this read in the original too.
    uint32_t vtableToken = run.get(actorToken);
    uint32_t methodToken = run.get(vtableToken + 0x28);
    uint32_t initialized = run.call(methodToken, actorToken, {arguments[1], arguments[2], arguments[3], arguments[4]});
    if (initialized == 0) {
        if (actorToken != 0)
            run.vcall(actorToken, 0x04, {1});
        return 0;
    }
    uint32_t listNodeToken = containerFields.head();
    uint32_t depth = actorStorageFields.depth();
    bool inserted = false;
    while (listNodeToken != 0) {
        uint32_t currentNodeToken = listNodeToken;
        ActorListNodeFields nodeFields{run, currentNodeToken};
        listNodeToken = run.get(currentNodeToken);
        uint32_t listedActorToken = nodeFields.actor();
        ActorStorageFields listedStorageFields{run, listedActorToken};
        uint32_t itemDepth = listedStorageFields.depth();
        if (s32(itemDepth) <= s32(depth))
            continue;
        uint32_t itemFlags = run.get8(listedActorToken + 0x0a);
        if ((itemFlags & 2) != 0)
            continue;
        uint32_t createdNodeToken = run.call(0x4f572a, receiver + 0x10, {currentNodeToken, actorToken});
        actorStorageFields.listNode(createdNodeToken);
        inserted = true;
        break;
    }
    if (!inserted) {
        uint32_t createdNodeToken = run.call(0x4f51c5, receiver + 0x10, {actorToken});
        actorStorageFields.listNode(createdNodeToken);
    }
    uint32_t flags = arguments[5];
    if ((flags & 0x200000) != 0) {
        uint32_t holderToken = actorFields.holder();
        uint32_t logicCallbackToken = run.get(holderToken + 0x10);
        run.call(logicCallbackToken, 0, {actorToken});
    }
    return actorToken;
}

// 0x4c8f60. thiscall, 6 stack arguments. Same lookup as 0x4d3e50; EAX is 0 when
// nothing is found, otherwise the result of 0x4c8e00.
uint32_t lookupAndCreateDepthSortedActor(Run &run, uint32_t receiver, const uint32_t *arguments) {
    ActorContainerFields containerFields{run, receiver};
    uint32_t lookupResultToken = run.automatic(-4);
    uint32_t servicesToken = containerFields.scene();
    ActorStorageSceneFields sceneFields{run, servicesToken};
    uint32_t resourceMapToken = sceneFields.registry();
    resourceMapToken += 0x10;
    run.put(lookupResultToken, 0);
    run.call(0x4f6286, resourceMapToken, {arguments[4], lookupResultToken});
    uint32_t resourceToken = run.get(lookupResultToken);
    if (resourceToken == 0)
        return 0;
    uint32_t createArguments[6] = {arguments[0], arguments[1], arguments[2], arguments[3], resourceToken, arguments[5]};
    uint32_t result = createDepthSortedActor(run, receiver, createArguments);
    return result;
}

// 0x4d3ef0. thiscall, 0 stack arguments. Calls the method at +0x10 of each
// listed actor's logic holder and returns the number of callbacks made. The
// next node is read before the callback, which can mutate the current actor.
uint32_t callListedActorLogic(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t listNodeToken = run.get(receiver + 0x1b8);
    uint32_t count = 0;
    while (listNodeToken != 0) {
        uint32_t currentNodeToken = listNodeToken;
        ActorListNodeFields nodeFields{run, currentNodeToken};
        listNodeToken = run.get(currentNodeToken);
        uint32_t actorToken = nodeFields.actor();
        ActorFields listedActorFields{run, actorToken};
        uint32_t holderToken = listedActorFields.holder();
        uint32_t methodToken = run.get(holderToken + 0x10);
        run.call(methodToken, 0, {actorToken});
        count += 1;
    }
    return count;
}

// 0x4d3f20. thiscall, 1 stack argument, returns void. Calls virtual +0x2c of
// every listed item, thiscall with ECX = the item, passing the argument.
uint32_t broadcastListedActorVirtual2c(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t listNodeToken = run.get(receiver + 0x1b8);
    if (listNodeToken == 0)
        return 0;
    uint32_t value = arguments[0];
    do {
        uint32_t currentNodeToken = listNodeToken;
        ActorListNodeFields nodeFields{run, currentNodeToken};
        listNodeToken = run.get(currentNodeToken);
        uint32_t actorToken = nodeFields.actor();
        uint32_t vtableToken = run.get(actorToken);
        uint32_t methodToken = run.get(vtableToken + 0x2c);
        run.call(methodToken, actorToken, {value});
    } while (listNodeToken != 0);
    return 0;
}

// 0x491ed0. cdecl(owner), always returns 1. State 0 appends the original
// ScoreFrame, WeaponFrame, HealthFrame, LivesFrame and TimerFrame resources
// in that order. State 5 invokes the listed actors' logic callbacks.
uint32_t initializeOrTickHudFrames(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t ownerToken = arguments[0];
    ActorFields ownerFields{run, ownerToken};
    ActorStorageFields ownerStorageFields{run, ownerToken};
    uint32_t holderToken = ownerFields.holder();
    LogicHolderFields holderFields{run, holderToken};
    uint32_t logicState = holderFields.state();
    if (logicState == 0) {
        run.put(0x53c9fc, ownerToken);
        uint32_t flags = ownerStorageFields.flags();
        flags |= 1;
        ownerStorageFields.flags(flags);
        holderFields.state(5);
        uint32_t scoreFrameArguments[6] = {0, 0, 0, 0x270e, 0x5229d8, 0};
        lookupAndAppendActor(run, ownerToken, scoreFrameArguments);
        uint32_t weaponFrameArguments[6] = {0, 0, 0, 0x270f, 0x5229cc, 0};
        lookupAndAppendActor(run, ownerToken, weaponFrameArguments);
        uint32_t healthFrameArguments[6] = {0, 0, 0, 0x270f, 0x5229c0, 0};
        lookupAndAppendActor(run, ownerToken, healthFrameArguments);
        uint32_t livesFrameArguments[6] = {0, 0, 0, 0x270f, 0x5229b4, 0};
        lookupAndAppendActor(run, ownerToken, livesFrameArguments);
        uint32_t timerFrameArguments[6] = {0, 0, 0, 0x270f, 0x5229a8, 0x200000};
        lookupAndAppendActor(run, ownerToken, timerFrameArguments);
        return 1;
    }
    if (logicState == 5)
        callListedActorLogic(run, ownerToken, nullptr);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4919f0:
        return updateTimedFramePosition(run, receiver, arguments);
    case 0x491ed0:
        return initializeOrTickHudFrames(run, receiver, arguments);
    case 0x4c8e00:
        return createDepthSortedActor(run, receiver, arguments);
    case 0x4c8f60:
        return lookupAndCreateDepthSortedActor(run, receiver, arguments);
    case 0x4d3ca0:
        return createAndAppendActor(run, receiver, arguments);
    case 0x4d3e50:
        return lookupAndAppendActor(run, receiver, arguments);
    case 0x4d3ef0:
        return callListedActorLogic(run, receiver, arguments);
    case 0x4d3f20:
        return broadcastListedActorVirtual2c(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_timers_checkpoints_02_entry, owned, body)
