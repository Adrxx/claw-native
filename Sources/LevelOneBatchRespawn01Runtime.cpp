// Level 1 respawn controller and command siblings
//
// Recovered from the decompile and disassembly of the owned functions.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"
#include "ClawRecoveredNames.h"

namespace {

using claw::Run;
using claw::s32;
using claw::recovered::v10::ActorFields;
using claw::recovered::v10::LogicHolderFields;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x46be40:
        return 0;
    case 0x46c110:
        return 0;
    case 0x46e2d0:
        return 0;
    case 0x46f1c0:
        return 0;
    case 0x46f1d0:
        return 0;
    case 0x42d5c0:
        return 2;
    default:
        return -1;
    }
}

// Original global 0x537e88 holds the active player actor token.
// Coordinate arithmetic stays uint32_t for original 32-bit wrap; s32 is
// used only at the original signed comparisons.
const uint32_t kPlayerActorAddress = 0x537e88;

// The remaining literal fields belong to family-private records whose shared
// layouts are not yet established. Here receiver +0x4 is the application,
// +0xc the world, +0x2c an unknown eligibility gate, and +0x44 an unknown
// selector. World +0x24 owns the camera record at +0x5c; it is distinct from
// the active player actor at kPlayerActorAddress. Keep those token roles apart.

// Wrap a horizontal coordinate into a rectangle record. Record fields: +0x30
// horizontal period, +0x40 and +0x48 horizontal bounds.
uint32_t wrapX(Run &run, uint32_t rect, uint32_t value) {
    uint32_t period = run.get(rect + 0x30);
    if (s32(value) >= 0) {
        if (s32(value) >= s32(period))
            value = value - period;
    } else {
        value = value + period;
    }
    uint32_t high = run.get(rect + 0x48);
    if (s32(high) < s32(period))
        return value;
    if (s32(value) >= s32(run.get(rect + 0x40)))
        return value;
    high = high - period;
    if (s32(value) > s32(high))
        return value;
    return value + period;
}

// Vertical counterpart of wrapX. Fields: +0x34 period, +0x44 and +0x4c bounds.
uint32_t wrapY(Run &run, uint32_t rect, uint32_t value) {
    uint32_t period = run.get(rect + 0x34);
    if (s32(value) >= 0) {
        if (s32(value) >= s32(period))
            value = value - period;
    } else {
        value = value + period;
    }
    uint32_t high = run.get(rect + 0x4c);
    if (s32(high) < s32(period))
        return value;
    if (s32(value) >= s32(run.get(rect + 0x44)))
        return value;
    high = high - period;
    if (s32(value) > s32(high))
        return value;
    return value + period;
}

// Calls the method stored at +0x10 of the object at [state + 0x6c] as a cdecl
// function with the state pointer as its only argument.
void callStateHook(Run &run) {
    uint32_t state = run.get(kPlayerActorAddress);
    ActorFields playerFields{run, state};
    uint32_t object = playerFields.holder();
    uint32_t method = run.get(object + 0x10);
    run.call(method, 0, {state});
}

// 0x46e2d0. thiscall, 0 stack argument(s), returns void. Walks a list under
// [[receiver + 0xc] + 8] + 0x14 and flags entries, then runs a callback pass
// over the object at +0xb0 of the record at +0x5c.
uint32_t markRespawnActorsAndVisitCameraChildren(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t world = run.get(receiver + 0xc);
    if (world == 0)
        return 0;
    uint32_t holder = run.get(world + 0x8) + 0x10;
    if (holder == 0)
        return 0;
    uint32_t node = run.get(holder + 0x4);
    while (node != 0) {
        uint32_t item = run.get(node + 0x8);
        node = run.get(node);
        if (item != 0) {
            if ((run.get(item + 0x164) & 0x2000) != 0) {
                uint32_t flags = run.get(item + 0x8);
                run.put(item + 0x8, flags | 0x10000);
            }
        }
    }
    uint32_t level = run.get(receiver + 0xc);
    uint32_t actor = run.get(level + 0x24);
    if (actor == 0)
        return 0;
    uint32_t record = run.get(actor + 0x5c);
    if (record == 0)
        return 0;
    uint32_t target = run.get(record + 0xb0);
    if (target == 0)
        return 0;
    run.call(0x4d51f0, target, {0x46e340});
    return 0;
}

// 0x46f1c0. Tail call to 0x4d1fd0 on the object at +0x5c, else 0.
uint32_t callCameraCommand4d1fd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = run.get(receiver + 0x5c);
    if (object == 0)
        return 0;
    return run.call(0x4d1fd0, object, {});
}

// 0x46f1d0. Tail call to 0x4d2000 on the object at +0x5c, else 0.
uint32_t callCameraCommand4d2000(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = run.get(receiver + 0x5c);
    if (object == 0)
        return 0;
    return run.call(0x4d2000, object, {});
}

// 0x42d5c0. thiscall, 2 stack arguments. Stores two signed integers as floats
// at +0x10 and +0x14, scaled by +0x18 and +0x1c unless bit 0 of +0x8 is set,
// then calls 0x4d0a60.
uint32_t setScaledCameraPosition(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t flags = run.get8(receiver + 0x8);
    // Preserve the original signed-int conversion and multiplication order;
    // the float stores are the rounding boundaries of the existing translation.
    double second = double(s32(arguments[1]));
    double first = double(s32(arguments[0]));
    if ((flags & 1) == 0) {
        first = first * double(run.getf(receiver + 0x18));
        second = second * double(run.getf(receiver + 0x1c));
    }
    run.putf(receiver + 0x10, float(first));
    run.putf(receiver + 0x14, float(second));
    run.call(0x4d0a60, receiver, {});
    return 0;
}

// The actor record at [[receiver + 0xc] + 0x24].
uint32_t cameraOwnerOf(Run &run, uint32_t receiver) {
    uint32_t world = run.get(receiver + 0xc);
    return run.get(world + 0x24);
}

// Calls 0x4d2000 then 0x4d1fd0 on the object at +0x5c of the actor, each time
// re-reading the chain and skipping when it is zero.
void restartCameraRecord(Run &run, uint32_t receiver) {
    uint32_t object = run.get(cameraOwnerOf(run, receiver) + 0x5c);
    if (object != 0)
        run.call(0x4d2000, object, {});
    object = run.get(cameraOwnerOf(run, receiver) + 0x5c);
    if (object != 0)
        run.call(0x4d1fd0, object, {});
}

// Virtual call 0x24 with argument 1 on the object at [world + 8].
void notifyWorldSlot24(Run &run, uint32_t receiver) {
    uint32_t world = run.get(receiver + 0xc);
    uint32_t object = run.get(world + 0x8);
    run.vcall(object, 0x24, {1});
}

// Calls 0x4cb9b0 on the actor, then virtual call 0x34 on [world + 0xc].
void refreshView(Run &run, uint32_t receiver) {
    uint32_t world = run.get(receiver + 0xc);
    uint32_t sink = run.get(world + 0x8);
    uint32_t screen = run.get(world + 0x4);
    uint32_t actor = run.get(world + 0x24);
    uint32_t width = run.get(screen + 0x14);
    run.call(0x4cb9b0, actor, {width, sink});
    world = run.get(receiver + 0xc);
    uint32_t renderer = run.get(world + 0xc);
    screen = run.get(world + 0x4);
    uint32_t height = run.get(screen + 0x18);
    width = run.get(screen + 0x14);
    run.vcall(renderer, 0x34, {width, height});
}

// Starts the named effect on the world object at +0x28 when it is idle.
void startEffect(Run &run, uint32_t world, uint32_t name) {
    uint32_t manager = run.get(world + 0x28);
    if (run.get(manager + 0x30) != 0)
        return;
    uint32_t effect = run.call(0x4061b0, manager, {name});
    if (effect == 0)
        return;
    uint32_t clock = run.get(0x532c10);
    run.call(0x4208e0, effect, {clock, 0, 0, 0});
}

// 0x46be40. thiscall, 0 stack argument(s), returns u32. Respawn: positions the
// camera from the player (offset +0x37 / +0x1e), restarts the actor records
// and refreshes the view, then (when a camera record exists) places a second
// effect.
uint32_t respawnWithCircleFade(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(kPlayerActorAddress) == 0)
        return 0;
    if (run.get(receiver + 0x2c) == 0)
        return 0;
    run.call(0x42d420, run.get(receiver + 0x4), {});
    uint32_t world = run.get(receiver + 0xc);
    uint32_t camera = run.get(run.get(world + 0x24) + 0x5c);
    if (camera != 0) {
        uint32_t state = run.get(kPlayerActorAddress);
        uint32_t y = run.get(state + 0x50);
        uint8_t facing = run.get8(state + 0x40);
        uint32_t x = run.get(state + 0x4c);
        y = y + 0x37;
        if ((facing & 2) != 0)
            x = x - 0x1e;
        else
            x = x + 0x1e;
        uint32_t flags = run.get(camera + 0x8);
        if ((flags & 4) != 0)
            x = wrapX(run, camera, x);
        if ((flags & 8) != 0)
            y = wrapY(run, camera, y);
        uint32_t dx = run.get(camera + 0x50) - run.get(camera + 0x40);
        x = x + dx;
        uint32_t dy = run.get(camera + 0x54) - run.get(camera + 0x44);
        y = y + dy;
        uint32_t screen = run.get(receiver + 0x4);
        uint32_t limitX = run.get(screen + 0x7c);
        uint32_t limitY = run.get(screen + 0x80);
        if (s32(x) >= s32(limitX))
            x = limitX - 0x20;
        if (s32(y) >= s32(limitY))
            y = limitY - 0x20;
        if (s32(x) <= 0)
            x = 0x20;
        if (s32(y) <= 0)
            y = 0x20;
        startEffect(run, world, 0x52a00c);
        run.call(0x48fae0, receiver, {x, y, 0x4e2, 0});
    }
    uint32_t state = run.get(kPlayerActorAddress);
    ActorFields playerFields{run, state};
    uint32_t hook = playerFields.holder();
    LogicHolderFields playerHolderFields{run, hook};
    playerHolderFields.state(0x17);
    // The original reloads the global before dispatch; retain the extra read.
    state = run.get(kPlayerActorAddress);
    callStateHook(run);
    markRespawnActorsAndVisitCameraChildren(run, receiver, nullptr);
    callCameraCommand4d2000(run, cameraOwnerOf(run, receiver), nullptr);
    callCameraCommand4d1fd0(run, cameraOwnerOf(run, receiver), nullptr);
    notifyWorldSlot24(run, receiver);
    restartCameraRecord(run, receiver);
    notifyWorldSlot24(run, receiver);
    refreshView(run, receiver);
    if (camera != 0) {
        uint32_t state2 = run.get(kPlayerActorAddress);
        uint32_t flags = run.get(camera + 0x8);
        uint32_t y = run.get(state2 + 0x50);
        uint32_t x = run.get(state2 + 0x4c);
        y = y - 0x20;
        if ((flags & 4) != 0)
            x = wrapX(run, camera, x);
        if ((flags & 8) != 0)
            y = wrapY(run, camera, y);
        uint32_t dx = run.get(camera + 0x50) - run.get(camera + 0x40);
        x = x + dx;
        uint32_t dy = run.get(camera + 0x54) - run.get(camera + 0x44);
        y = y + dy;
        if (run.get(receiver + 0x44) == 0xffffffffu)
            startEffect(run, run.get(receiver + 0xc), 0x5246b4);
        run.call(0x48fbe0, receiver, {x, y, 0x3e8, 0x1f4});
    }
    run.call(0x42d440, run.get(receiver + 0x4), {});
    run.call(0x42abf0, run.get(receiver + 0x4), {});
    return 1;
}

// 0x46c110. thiscall, 0 stack argument(s), returns u32. Repositions the actor
// records from the state's object at +0x14 of [state + 0x6c], bumps a counter
// at +0x80 and restarts the actor.
uint32_t restartFromSavedPlayerPosition(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t state = run.get(kPlayerActorAddress);
    if (state == 0)
        return 0;
    ActorFields playerFields{run, state};
    if (playerFields.holder() == 0)
        return 0;
    uint32_t sourceHolder = playerFields.holder();
    // +0x14 supplies the saved player record, not the holder logic at +0x18.
    uint32_t source = run.get(sourceHolder + 0x14);
    if (source == 0)
        return 0;
    if (run.get(run.get(receiver + 0x4) + 0x9c) != 0)
        run.put(0x534eb4, 1);
    uint32_t actor = run.get(run.get(receiver + 0xc) + 0x24);
    uint32_t px = run.get(source + 0x4c);
    uint32_t py = run.get(source + 0x50);
    uint32_t main = run.get(actor + 0x5c);
    uint32_t cameraPositionArguments[2] = {px, py};
    setScaledCameraPosition(run, main, cameraPositionArguments);
    main = run.get(actor + 0x5c);
    uint32_t savedX = run.get(main + 0x84);
    uint32_t savedY = run.get(main + 0x88);
    uint32_t index = 0;
    if (s32(run.get(actor + 0x3c)) > 0) {
        do {
            if (index != run.get(actor + 0x60)) {
                uint32_t list = run.get(actor + 0x38);
                uint32_t entry = run.get(list + index * 4);
                uint32_t entryArgs[2] = {savedX, savedY};
                setScaledCameraPosition(run, entry, entryArgs);
            }
            index = index + 1;
        } while (s32(index) < s32(run.get(actor + 0x3c)));
    }
    // Preserve the saved counter across both player-state callbacks.
    uint32_t counter = run.get(source + 0x80);
    run.call(0x415ce0, 0, {});
    run.call(0x46c790, receiver, {});
    state = run.get(kPlayerActorAddress);
    ActorFields resetPlayerFields{run, state};
    uint32_t hook = resetPlayerFields.holder();
    LogicHolderFields resetHolderFields{run, hook};
    resetHolderFields.state(0);
    // The original reloads the global before dispatch; retain the extra read.
    state = run.get(kPlayerActorAddress);
    callStateHook(run);
    state = run.get(kPlayerActorAddress);
    ActorFields restartedPlayerFields{run, state};
    hook = restartedPlayerFields.holder();
    LogicHolderFields restartedHolderFields{run, hook};
    restartedHolderFields.state(0x17);
    // The original reloads the global before dispatch; retain the extra read.
    state = run.get(kPlayerActorAddress);
    callStateHook(run);
    run.put(source + 0x80, counter + 1);
    restartCameraRecord(run, receiver);
    notifyWorldSlot24(run, receiver);
    restartCameraRecord(run, receiver);
    notifyWorldSlot24(run, receiver);
    refreshView(run, receiver);
    run.call(0x42abf0, run.get(receiver + 0x4), {});
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x46be40:
        return respawnWithCircleFade(run, receiver, arguments);
    case 0x46c110:
        return restartFromSavedPlayerPosition(run, receiver, arguments);
    case 0x46e2d0:
        return markRespawnActorsAndVisitCameraChildren(run, receiver, arguments);
    case 0x46f1c0:
        return callCameraCommand4d1fd0(run, receiver, arguments);
    case 0x46f1d0:
        return callCameraCommand4d2000(run, receiver, arguments);
    case 0x42d5c0:
        return setScaledCameraPosition(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_respawn_01_entry, owned, body)
