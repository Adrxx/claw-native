// Level 1 HUD frames and number group entries
//
// Recovered v1.0 behavior; original addresses remain in the dispatch below.
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
    case 0x490590:
        return 8;
    case 0x490760:
        return 7;
    case 0x4908b0:
        return 1;
    case 0x490c40:
        return 0;
    case 0x490c50:
        return 1;
    case 0x490f80:
        return 1;
    case 0x4912a0:
        return 1;
    case 0x491540:
        return 1;
    default:
        return -1;
    }
}


// Global data used by the HUD frames: 0x5371fc game state (+0x68 current frame,
// +0x6c hold count), 0x5370c8/0x5370d0 horizontal bounds, 0x5370cc/0x5370d4
// vertical bounds, 0x537e88 player actor, 0x5430c4 tick length.
constexpr uint32_t kGameState = 0x5371fc;
constexpr uint32_t kLeft = 0x5370c8;
constexpr uint32_t kTop = 0x5370cc;
constexpr uint32_t kRight = 0x5370d0;
constexpr uint32_t kBottom = 0x5370d4;
constexpr uint32_t kPlayer = 0x537e88;
constexpr uint32_t kTick = 0x5430c4;
constexpr uint32_t kNoValue = 0xffffcfc7;

enum DigitMode { kDigitImages = 0, kDigitMethod = 1, kDigitSetCall = 2 };

uint32_t initializeHudNumberDigits(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t bindHudActorToScreenAnchor(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t constructHudNumberGroup(Run &run, uint32_t receiver, const uint32_t *arguments);

// Half of a signed difference, rounded toward zero (cdq, sub, sar).
uint32_t halfDifference(uint32_t high, uint32_t low) {
    return uint32_t(s32(high - low) / 2);
}

// Horizontal placement into target+0x4c: mode 1 left edge, 2 right edge, 3 centre.
void placeHorizontal(Run &run, uint32_t target, uint32_t mode, uint32_t offset) {
    if (mode == 1) {
        run.put(target + 0x4c, offset + run.get(kLeft));
    } else if (mode == 2) {
        run.put(target + 0x4c, offset + run.get(kRight));
    } else if (mode == 3) {
        uint32_t right = run.get(kRight);
        uint32_t left = run.get(kLeft);
        run.put(target + 0x4c, halfDifference(right, left) + offset + left);
    }
}

// Vertical placement into target+0x50: mode 3 centre, 4 top edge, 5 bottom edge.
void placeVertical(Run &run, uint32_t target, uint32_t mode, uint32_t offset) {
    if (mode == 3) {
        uint32_t bottom = run.get(kBottom);
        uint32_t top = run.get(kTop);
        run.put(target + 0x50, halfDifference(bottom, top) + offset + top);
    } else if (mode == 4) {
        run.put(target + 0x50, offset + run.get(kTop));
    } else if (mode == 5) {
        run.put(target + 0x50, offset + run.get(kBottom));
    }
}

// Binder group fields: +4 horizontal mode, +8 horizontal offset, +0xc vertical
// mode, +0x10 vertical offset, +0x14 start frame, +0x18 last frame, +0x24 actor.
void placeGroup(Run &run, uint32_t group) {
    placeHorizontal(run, run.get(group + 0x24), run.get(group + 4), run.get(group + 8));
    placeVertical(run, run.get(group + 0x24), run.get(group + 0xc), run.get(group + 0x10));
}

// The activation the group performs once its start frame arrives, through the
// actor's world widget (0x490760 and WeaponFrame).
void activateGroup(Run &run, uint32_t group, uint32_t frame) {
    uint32_t actor = run.get(group + 0x24);
    run.put(group + 0x14, frame);
    uint32_t image = run.get(actor + 0x174);
    uint32_t y = run.get(actor + 0x50);
    uint32_t x = run.get(actor + 0x4c);
    uint32_t widget = run.get(run.get(actor + 0xc) + 0xc);
    run.vcall(widget, 0x28, {x, y, image});
    actor = run.get(group + 0x24);
    run.put(actor + 0x40, run.get(actor + 0x40) | 1);
    run.put(group + 0x20, 0);
    run.put(group + 0x1c, 1);
}

// Shared frame prologue of the per-frame layout. Returns false when the
// caller must skip the rest of the layout.
bool beginLayout(Run &run, uint32_t group, uint32_t &frame) {
    uint32_t state = run.get(kGameState);
    uint32_t current = run.get(group + 0x14);
    frame = run.get(state + 0x68);
    if (current == frame) {
        if (s32(run.get(state + 0x6c)) <= 0)
            return false;
    }
    uint32_t last = run.get(group + 0x18);
    run.put(group + 0x14, frame);
    if (s32(frame) > s32(last))
        return false;
    return true;
}

// Layout used by Score, Health, Lives and Timer: place, then run 0x490c00 at
// the start frame.
void layoutGroup(Run &run, uint32_t group) {
    uint32_t frame = 0;
    if (!beginLayout(run, group, frame))
        return;
    placeGroup(run, group);
    if (run.get(group + 0x14) == 0) {
        run.put(group + 0x14, frame);
        run.call(0x490c00, group, {});
    }
}

// Layout used by WeaponFrame: place, then activate through the world widget.
void layoutGroupWidget(Run &run, uint32_t group) {
    uint32_t frame = 0;
    if (!beginLayout(run, group, frame))
        return;
    placeGroup(run, group);
    if (run.get(group + 0x14) == 0)
        activateGroup(run, group, frame);
}

// Allocates a 0x60 byte binder group (vtable pointers at +0 and +0x28).
uint32_t allocateGroup(Run &run) {
    uint32_t group = run.call(0x4f63ec, 0, {0x60});
    if (!group)
        return 0;
    run.put(group + 0x28, 0x50b5cc);
    run.put(group, 0x50b5c4);
    return group;
}

// Same allocation, for the frames that run the number group constructor.
uint32_t allocateConstructedGroup(Run &run) {
    uint32_t group = run.call(0x4f63ec, 0, {0x60});
    if (!group)
        return 0;
    run.put(group, 0x50b014);
    constructHudNumberGroup(run, group + 0x28, nullptr);
    run.put(group, 0x50b5c4);
    return group;
}

void bindGroup(Run &run, uint32_t group, uint32_t actor, uint32_t horizontalMode, uint32_t horizontalOffset,
               uint32_t verticalOffset, uint32_t verticalReference) {
    const uint32_t arguments[7] = {actor, run.get(run.get(kGameState) + 0x68), 0x63, horizontalMode,
                                   horizontalOffset, verticalOffset, verticalReference};
    bindHudActorToScreenAnchor(run, group, arguments);
}

void initGroup(Run &run, uint32_t group, uint32_t manager, uint32_t actor, uint32_t value, uint32_t count,
               uint32_t step, uint32_t offset, uint32_t extra, uint32_t name) {
    const uint32_t arguments[8] = {manager, actor, value, count, step, offset, extra, name};
    initializeHudNumberDigits(run, group + 0x28, arguments);
}

// Points the digit actors at the images for the last `count` characters of the
// decimal text in `buffer`. count is read from owner+countOffset, the digit
// actors from the list at owner+listOffset.
void setDigits(Run &run, uint32_t owner, uint32_t countOffset, uint32_t listOffset, uint32_t buffer, DigitMode mode) {
    uint32_t length = 0;
    while (run.get8(buffer + length) != 0)
        ++length;
    uint32_t count = run.get(owner + countOffset);
    if (s32(count) <= 0)
        return;
    uint32_t text = buffer + length - count;
    uint32_t list = owner + listOffset;
    uint32_t index = 0;
    do {
        uint32_t digit = run.get(list);
        uint32_t value = uint32_t(int32_t(int8_t(run.get8(text)))) - 0x30;
        uint32_t images = run.get(digit + 0x170);
        if (mode == kDigitMethod) {
            run.call(0x4209d0, digit, {value});
        } else if (mode == kDigitSetCall) {
            if (images) {
                uint32_t image = run.call(0x40f680, images, {value});
                run.put(digit + 0x174, image);
                run.put(digit + 0x16c, value);
            }
        } else if (images) {
            uint32_t image = 0;
            if (!(s32(value) < s32(run.get(images + 0x64)) || s32(value) > s32(run.get(images + 0x68))))
                image = run.get(run.get(images + 0x14) + value * 4);
            run.put(digit + 0x174, image);
            run.put(digit + 0x16c, value);
        }
        text += 1;
        index += 1;
        list += 4;
        ActorFields digitFields{run, digit};
        run.put(digitFields.holder() + 0x68, 0xffffffff);
    } while (s32(index) < s32(run.get(owner + countOffset)));
}

// Formats `value` as "%010i" into the stack buffer at `bufferOffset` and
// refreshes the digit actors of `group`.
void showNumber(Run &run, uint32_t group, uint32_t value, int32_t bufferOffset, DigitMode mode,
                uint32_t countOffset = 0x30, uint32_t listOffset = 0x34) {
    uint32_t buffer = run.automatic(bufferOffset);
    run.call(0x4a3920, 0, {buffer, 0x52c6f8, value});
    setDigits(run, group, countOffset, listOffset, buffer, mode);
}

// 0x490590. Builds the digit actors of a number group: one "StatusNumberDigit"
// per digit (at most ten), each bound through 0x490760, then shows the initial
// value. Arguments: manager, actor, value, digit count, step, first offset,
// second offset, name.
uint32_t initializeHudNumberDigits(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t manager = arguments[0];
    uint32_t actor = arguments[1];
    uint32_t value = arguments[2];
    uint32_t count = arguments[3];
    uint32_t step = arguments[4];
    uint32_t position = arguments[5];
    uint32_t offset = arguments[6];
    uint32_t name = arguments[7];
    ActorFields actorFields{run, actor};
    LogicHolderFields holder{run, actorFields.holder()};
    if (holder.logic() == 0)
        return 0;
    if (s32(count) >= 10)
        count = 10;
    run.put(receiver + 8, count);
    LogicHolderFields currentHolder{run, actorFields.holder()};
    uint32_t template_ = currentHolder.logic();
    uint32_t built = 0;
    if (s32(count) > 0) {
        uint32_t slot = receiver + 0xc;
        do {
            uint32_t digit = run.call(0x4d3e50, manager, {0, 0, 0, run.get(actor + 0x64) + 1, 0x522994, 0});
            if (!digit)
                return 0;
            run.put(slot, digit);
            ActorFields digitFields{run, digit};
            LogicHolderFields digitHolder{run, digitFields.holder()};
            if (!digitHolder)
                return 0;
            run.call(0x4c7970, digit, {name});
            uint32_t group = allocateGroup(run);
            const uint32_t bindArguments[7] = {digit, run.get(template_ + 0x14), run.get(template_ + 0x18),
                                               run.get(template_ + 4), position, run.get(template_ + 0xc),
                                               run.get(template_ + 0x10) + offset};
            bindHudActorToScreenAnchor(run, group, bindArguments);
            digitHolder.logic(group);
            position = position + step;
            built += 1;
            slot += 4;
        } while (s32(built) < s32(run.get(receiver + 8)));
    }
    run.put(receiver + 4, kNoValue);
    if (value != kNoValue) {
        run.put(receiver + 4, value);
        showNumber(run, receiver, value, -0x10, kDigitImages, 8, 0xc);
    }
    return 1;
}

// 0x490760. Stores the binding of an actor to a screen anchor into the group
// and, when the start frame has arrived, places the actor and activates it.
// Arguments: actor, start frame, last frame, horizontal mode, horizontal
// offset, vertical mode, vertical offset.
uint32_t bindHudActorToScreenAnchor(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    uint32_t first = arguments[1];
    uint32_t last = arguments[2];
    uint32_t horizontalMode = arguments[3];
    uint32_t horizontalOffset = arguments[4];
    run.put(receiver + 0xc, arguments[5]);
    run.put(receiver + 0x10, arguments[6]);
    run.put(receiver + 0x24, actor);
    run.put(receiver + 4, horizontalMode);
    run.put(receiver + 8, horizontalOffset);
    run.put(receiver + 0x18, last);
    run.put(receiver + 0x20, 1);
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x5c, kNoValue);
    run.put(receiver + 0x14, 0xffffff9d);
    if (first == 0xffffff9d) {
        if (s32(run.get(run.get(kGameState) + 0x6c)) <= 0)
            return 1;
    }
    run.put(receiver + 0x14, first);
    if (s32(first) > s32(last))
        return 1;
    placeHorizontal(run, actor, horizontalMode, horizontalOffset);
    placeVertical(run, run.get(receiver + 0x24), run.get(receiver + 0xc), run.get(receiver + 0x10));
    if (run.get(receiver + 0x14) == 0)
        activateGroup(run, receiver, first);
    return 1;
}

// 0x4908b0. Score display frame: builds the treasure counter on the first call
// and afterwards keeps its digits and the extra-life threshold current.
uint32_t updateScoreHudFrame(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    ActorFields actorFields{run, actor};
    LogicHolderFields holder{run, actorFields.holder()};
    uint32_t state = holder.state();
    if (state == 0) {
        uint32_t offset = 0;
        run.call(0x4c7970, actor, {0x52c734});
        run.call(0x4c79e0, actor, {0x52c71c, 0});
        run.put(actor + 0xfc, 1000000);
        run.put(actor + 8, run.get(actor + 8) | 1);
        uint32_t score = run.get(0x534cc4);
        uint32_t image = run.get(actor + 0x174);
        run.put(actor + 0xfc, (uint32_t(s32(score) / 1000000) + 1) * 1000000);
        if (image)
            offset = run.get(image + 0x18) - run.get(image + 0x20);
        uint32_t group = allocateConstructedGroup(run);
        bindGroup(run, group, actor, 1, offset, 4, 0xf);
        holder.logic(group);
        initGroup(run, group, run.get(0x53c9fc), actor, run.get(0x534cc4), 8, 0xb, 0x24, 0, 0x52c700);
        holder.state(5);
        return 1;
    }
    if (state != 5)
        return 1;
    run.call(0x4c82a0, actor + 0x188, {run.get(kTick)});
    uint32_t group = holder.logic();
    if (!group)
        return 1;
    layoutGroup(run, group);
    uint32_t player = run.get(kPlayer);
    if (!player)
        return 1;
    uint32_t score = run.get(player + 0xf8);
    if (run.get(group + 0x2c) != score) {
        run.put(group + 0x2c, score);
        showNumber(run, group, score, -0x1c, kDigitMethod);
        player = run.get(kPlayer);
    }
    if (s32(run.get(group + 0x2c)) < s32(run.get(actor + 0xfc)))
        return 1;
    ActorFields playerFields{run, player};
    uint32_t stats = run.get(playerFields.holder() + 0x14);
    if (s32(run.get(stats + 0x7c)) < 10) {
        uint32_t table = run.get(run.get(actor + 0xc) + 0x28);
        if (run.get(table + 0x30) == 0) {
            uint32_t found = run.automatic(4);
            run.put(found, 0);
            run.call(0x4f6286, table + 0x10, {0x52a2b8, found});
            uint32_t sound = run.get(found);
            if (sound) {
                uint32_t enabled = run.get(0x532c0c);
                uint32_t id = run.get(0x532c10);
                if (enabled) {
                    // Callee-entry ESP of the original CALL: entry ESP less 0x30 of frame,
                    // 0x10 of arguments and the return word.
                    run.stackPointer = run.frame - 0x44;
                    run.call(0x4b45f0, run.get(sound + 0x10), {id, 0, 0, 0});
                    run.stackPointer = 0;
                }
            }
        }
        run.put(stats + 0x7c, run.get(stats + 0x7c) + 1);
    }
    run.put(actor + 0xfc, run.get(actor + 0xfc) + 1000000);
    return 1;
}

// 0x490c40. Number group constructor: stores the group vtable.
uint32_t constructHudNumberGroup(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver, 0x50b5cc);
    return 0;
}

// 0x490c50. Health display frame: builds the heart and its number on the first
// call; afterwards updates the digits and animates the heart.
uint32_t updateHealthHudFrame(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    ActorFields actorFields{run, actor};
    LogicHolderFields holder{run, actorFields.holder()};
    uint32_t state = holder.state();
    if (state == 0) {
        uint32_t offset = 0;
        uint32_t player = run.get(kPlayer);
        if (!player)
            return 0;
        ActorFields playerFields{run, player};
        uint32_t stats = run.get(playerFields.holder() + 0x14);
        if (!stats)
            return 0;
        run.put(holder + 0x168, stats);
        run.call(0x4c7970, actor, {0x52c774});
        uint32_t image = run.get(actor + 0x174);
        run.put(actor + 8, run.get(actor + 8) | 1);
        if (image)
            offset = 3 - run.get(image + 0x20) - run.get(image + 0x18);
        uint32_t group = allocateGroup(run);
        bindGroup(run, group, actor, 2, offset, 4, 0xf);
        holder.logic(group);
        initGroup(run, group, run.get(0x53c9fc), actor, run.get(0x534cc8), 3, 0xb, 0xffffffcc, 0xffffffff, 0x52c754);
        holder.state(5);
        run.put(holder + 0x130, 0);
        return 1;
    }
    if (state != 5)
        return 1;
    uint32_t group = holder.logic();
    if (!group)
        return 1;
    layoutGroup(run, group);
    uint32_t player = run.get(kPlayer);
    if (player) {
        uint32_t health = run.get(player + 0x10c);
        if (run.get(group + 0x2c) != health) {
            run.put(group + 0x2c, health);
            showNumber(run, group, health, -0x10, kDigitMethod);
        }
    }
    // 0x490dd3-0x490df7: unsigned countdown in the units of 0x5430c4.
    // The producer of that clock is outside this family, so no physical unit is assumed.
    uint32_t heartFrameRemainingTicks = run.get(holder + 0x130);
    uint32_t frameTickDelta = run.get(kTick);
    if (frameTickDelta < heartFrameRemainingTicks)
        run.put(holder + 0x130, heartFrameRemainingTicks - frameTickDelta);
    else
        run.put(holder + 0x130, 0);
    if (run.get(holder + 0x130) != 0)
        return 1;
    // 0x490e0b-0x490e1a: preserve the 32-bit shift/subtraction wrap on reload.
    run.put(holder + 0x130, 300 - (run.get(run.get(kPlayer) + 0x10c) << 1));
    uint32_t images = run.get(actor + 0x170);
    if (!images)
        return 1;
    uint32_t frame = run.get(actor + 0x16c) + 1;
    run.put(actor + 0x16c, frame);
    uint32_t image = 0;
    if (!(s32(frame) < s32(run.get(images + 0x64)) || s32(frame) > s32(run.get(images + 0x68))))
        image = run.get(run.get(images + 0x14) + frame * 4);
    run.put(actor + 0x174, image);
    if (image != 0)
        return 1;
    uint32_t first = run.get(images + 0x64);
    run.put(actor + 0x16c, first);
    uint32_t firstAgain = run.get(images + 0x64);
    if (s32(first) < s32(firstAgain) || s32(first) > s32(run.get(images + 0x68))) {
        run.put(actor + 0x174, 0);
        return 1;
    }
    image = run.get(run.get(images + 0x14) + first * 4);
    run.put(actor + 0x174, image);
    return 1;
}

// 0x490f80. Weapon display frame: builds the pistol icon and its ammunition
// number; afterwards swaps the icon with the selected weapon and shows the
// ammunition of that weapon.
uint32_t updateWeaponHudFrame(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    ActorFields actorFields{run, actor};
    LogicHolderFields holder{run, actorFields.holder()};
    uint32_t state = holder.state();
    if (state == 0) {
        uint32_t offset = 0;
        uint32_t player = run.get(kPlayer);
        if (!player)
            return 0;
        ActorFields playerFields{run, player};
        uint32_t stats = run.get(playerFields.holder() + 0x14);
        if (!stats)
            return 0;
        run.put(holder + 0x168, stats);
        run.call(0x4c7970, actor, {0x52c7c4});
        uint32_t image = run.get(actor + 0x174);
        run.put(actor + 8, run.get(actor + 8) | 1);
        if (image)
            offset = 1 - run.get(image + 0x18) - run.get(image + 0x20);
        uint32_t group = allocateGroup(run);
        bindGroup(run, group, actor, 2, offset, 4, 0x2e);
        holder.logic(group);
        initGroup(run, group, run.get(0x53c9fc), actor, 0x63, 2, 8, 0xffffffd6, 0, 0x52c790);
        holder.state(5);
        return 1;
    }
    if (state != 5)
        return 1;
    uint32_t group = holder.logic();
    if (!group)
        return 1;
    uint32_t stats = run.get(holder + 0x168);
    if (!stats)
        return 1;
    if (run.get(group + 0x5c) != run.get(stats + 0x30)) {
        run.put(group + 0x5c, run.get(stats + 0x30));
        uint32_t weapon = run.get(stats + 0x30);
        if (weapon == 1) {
            run.call(0x4c7970, actor, {0x52c7c4});
            run.call(0x4c79e0, actor, {0x52c7ac, 0});
        } else if (weapon == 2) {
            run.call(0x4c7970, actor, {0x52c7fc});
            run.call(0x4c79e0, actor, {0x52c7e4, 0});
        } else if (weapon == 3) {
            run.call(0x4c7970, actor, {0x52c834});
            run.call(0x4c79e0, actor, {0x52c81c, 0});
        }
    }
    uint32_t weapon = run.get(stats + 0x30);
    uint32_t shown = actor;
    if (weapon == 1)
        shown = run.get(stats + 0x70);
    else if (weapon == 2)
        shown = run.get(stats + 0x74);
    else if (weapon == 3)
        shown = run.get(stats + 0x78);
    layoutGroupWidget(run, group);
    if (run.get(group + 0x2c) != shown) {
        run.put(group + 0x2c, shown);
        showNumber(run, group, shown, -0x10, kDigitImages);
        actor = arguments[0];
    }
    run.call(0x4c82a0, actor + 0x188, {run.get(kTick)});
    return 1;
}

// 0x4912a0. Lives display frame: builds the head icon and the lives number
// (or retires the frame when the world widget reports mode 4); afterwards
// shows the spare lives, one fewer than the player holds.
uint32_t updateLivesHudFrame(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    ActorFields actorFields{run, actor};
    LogicHolderFields holder{run, actorFields.holder()};
    uint32_t state = holder.state();
    if (state == 0) {
        uint32_t offset = 0;
        run.call(0x4c7970, actor, {0x52c86c});
        run.call(0x4c79e0, actor, {0x52c854, 0});
        run.put(actor + 8, run.get(actor + 8) | 1);
        uint32_t mode = run.vcall(run.get(run.get(kGameState) + 0x2c), 0x10, {});
        if (mode == 4) {
            holder.state(0xb);
            run.put(actor + 0x40, run.get(actor + 0x40) | 1);
            return 1;
        }
        uint32_t image = run.get(actor + 0x174);
        if (image)
            offset = 3 - run.get(image + 0x20) - run.get(image + 0x18);
        uint32_t group = allocateGroup(run);
        bindGroup(run, group, actor, 2, offset, 4, 0x48);
        holder.logic(group);
        initGroup(run, group, run.get(0x53c9fc), actor, 9, 1, 8, 0xffffffe0, 1, 0x52c790);
        holder.state(5);
        return 1;
    }
    if (state != 5)
        return 1;
    run.call(0x4c82a0, actor + 0x188, {run.get(kTick)});
    uint32_t group = holder.logic();
    if (!group)
        return 1;
    layoutGroup(run, group);
    uint32_t player = run.get(kPlayer);
    if (!player)
        return 1;
    ActorFields playerFields{run, player};
    uint32_t lives = run.get(run.get(playerFields.holder() + 0x14) + 0x7c) - 1;
    if (s32(lives) < 0)
        lives = 0;
    if (run.get(group + 0x2c) == lives)
        return 1;
    run.put(group + 0x2c, lives);
    showNumber(run, group, lives, -0x10, kDigitImages);
    return 1;
}

// Sets or clears bit 0 of the flags at +0x40 of every digit actor of a group.
void markDigits(Run &run, uint32_t owner, uint32_t countOffset, uint32_t listOffset, bool set) {
    uint32_t count = run.get(owner + countOffset);
    if (s32(count) <= 0)
        return;
    uint32_t list = owner + listOffset;
    uint32_t index = 0;
    do {
        uint32_t digit = run.get(list);
        list += 4;
        index += 1;
        if (set)
            run.put(digit + 0x40, run.get(digit + 0x40) | 1);
        else
            run.put(digit + 0x40, run.get(digit + 0x40) & 0xfffffffe);
    } while (s32(index) < s32(run.get(owner + countOffset)));
}

// 0x491540. Stopwatch frame: builds the stopwatch and its three digits on the
// first call; afterwards hides them while no time is running, otherwise shows
// the elapsed whole seconds.
uint32_t updateStopwatchHudFrame(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    ActorFields actorFields{run, actor};
    LogicHolderFields holder{run, actorFields.holder()};
    uint32_t state = holder.state();
    if (state == 0) {
        uint32_t offset = 0;
        run.call(0x4c7970, actor, {0x52c888});
        run.call(0x4c79e0, actor, {0x5240d8, 0});
        uint32_t flags = run.get(actor + 8);
        uint32_t visible = run.get(actor + 0x40);
        uint32_t image = run.get(actor + 0x174);
        run.put(actor + 8, flags | 1);
        run.put(actor + 0x40, visible | 1);
        if (image)
            offset = run.get(image + 0x18) - run.get(image + 0x20);
        uint32_t group = allocateConstructedGroup(run);
        bindGroup(run, group, actor, 1, offset, 4, 0x30);
        holder.logic(group);
        initGroup(run, group, run.get(0x53c9fc), actor, 0, 3, 0xb, 0x24, 1, 0x52c700);
        markDigits(run, group + 0x28, 8, 0xc, true);
        holder.state(5);
        return 1;
    }
    if (state != 5)
        return 1;
    uint32_t group = holder.logic();
    if (!group)
        return 1;
    uint32_t milliseconds = run.get(0x534ea8);
    if (milliseconds == 0) {
        if (run.get(actor + 0x40) & 1)
            return 1;
        uint32_t player = run.get(kPlayer);
        if (player) {
            ActorFields playerFields{run, player};
            uint32_t stats = run.get(playerFields.holder() + 0x14);
            if (run.get(stats + 0x18) == 0)
                run.call(0x4bc110, run.get(kGameState), {});
        }
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
        markDigits(run, group, 0x30, 0x34, true);
        return 1;
    }
    run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffe);
    markDigits(run, group, 0x30, 0x34, false);
    run.call(0x4c82a0, actor + 0x188, {run.get(kTick)});
    layoutGroup(run, group);
    // 0x4916f4-0x491702 uses unsigned MUL high-half >> 6, exactly u32 / 1000.
    // Re-read after animation/layout callbacks; milliseconds/seconds retain the
    // existing display-scale names, without proving the clock producer here.
    uint32_t seconds = run.get(0x534ea8) / 1000;
    if (run.get(group + 0x2c) == seconds)
        return 1;
    run.put(group + 0x2c, seconds);
    showNumber(run, group, seconds, -0x1c, kDigitSetCall);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x490590:
        return initializeHudNumberDigits(run, receiver, arguments);
    case 0x490760:
        return bindHudActorToScreenAnchor(run, receiver, arguments);
    case 0x4908b0:
        return updateScoreHudFrame(run, receiver, arguments);
    case 0x490c40:
        return constructHudNumberGroup(run, receiver, arguments);
    case 0x490c50:
        return updateHealthHudFrame(run, receiver, arguments);
    case 0x490f80:
        return updateWeaponHudFrame(run, receiver, arguments);
    case 0x4912a0:
        return updateLivesHudFrame(run, receiver, arguments);
    case 0x491540:
        return updateStopwatchHudFrame(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_hud_timers_01_entry, owned, body)
