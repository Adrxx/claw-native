// Original v1.0 player powerup lifecycle, flare frames and attachment messages.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;
using namespace claw::recovered::v10;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x41f990:
        return 5;
    case 0x420070:
        return 2;
    case 0x448400:
        return 1;
    case 0x4ce7b0:
        return 1;
    default:
        return -1;
    }
}

uint32_t sendMessageToAttachmentRange(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t createGlitterMother(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x41f990. cdecl: (player, unused, state, newKind, newAmount). Switches the
// Claw powerup kind and wrapped amount in the original global state,
// swapping the POWERUP and LEVEL music/sound entries of the manager. Rebind
// the application at each original reload after callbacks, preserving order.
uint32_t changePlayerPowerup(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t player = arguments[0];
    uint32_t state = arguments[2];
    uint32_t kind = arguments[3];
    uint32_t amount = arguments[4];
    PowerupPlayerFields playerFields{run, player};
    PowerupStateFields stateFields{run, state};
    PowerupGlobalsFields globals{run, PowerupGlobalsAddress};
    PowerupApplicationFields initialApplication{run, run.get(PowerupApplicationAddress)};
    if (initialApplication.unknown_0x14() != 0 && run.get(PowerupMusicSuppressionAddress) == 0) {
        if (amount == 0 || kind == 0) {
            PowerupApplicationFields musicApplication{run, run.get(PowerupApplicationAddress)};
            uint32_t manager = musicApplication.musicEntries();
            PowerupMusicManagerFields musicManager{run, manager};
            uint32_t current = musicManager.currentEntry();
            uint32_t entry = run.call(0x4b54a0, manager, {PowerupMusicNameAddress});
            if (current == entry && entry != 0) {
                if (run.call(0x4b5bd0, entry, {}) != 0)
                    run.vcall(entry, 0x30, {});
            }
            PowerupApplicationFields reloadedApplication{run, run.get(PowerupApplicationAddress)};
            manager = reloadedApplication.musicEntries();
            entry = run.call(0x4b54a0, manager, {LevelMusicNameAddress});
            if (entry != 0 && current != entry) {
                PowerupApplicationFields targetApplication{run, run.get(PowerupApplicationAddress)};
                uint32_t target = targetApplication.musicEntries();
                PowerupMusicManagerFields targetManager{run, target};
                targetManager.currentEntry(entry);
                if (run.call(0x4b5bd0, entry, {}) == 0)
                    run.vcall(entry, 0x2c, {0});
            }
        } else if (globals.kind() != kind) {
            PowerupApplicationFields pauseApplication{run, run.get(PowerupApplicationAddress)};
            uint32_t manager = pauseApplication.musicEntries();
            uint32_t entry = run.call(0x4b54a0, manager, {LevelMusicNameAddress});
            if (entry != 0) {
                if (run.call(0x4b5bd0, entry, {}) != 0)
                    run.vcall(entry, 0x28, {});
            }
            PowerupApplicationFields selectionApplication{run, run.get(PowerupApplicationAddress)};
            manager = selectionApplication.musicEntries();
            entry = run.call(0x4b54a0, manager, {PowerupMusicNameAddress});
            if (entry != 0) {
                PowerupApplicationFields selectionTargetApplication{run, run.get(PowerupApplicationAddress)};
                uint32_t target = selectionTargetApplication.musicEntries();
                PowerupMusicManagerFields selectionTargetManager{run, target};
                selectionTargetManager.currentEntry(entry);
                PowerupApplicationFields playbackApplication{run, run.get(PowerupApplicationAddress)};
                manager = playbackApplication.musicEntries();
                run.call(0x4b5570, manager, {1});
            }
        }
    }
    if (globals.kind() == kind) {
        // x86 ADD wraps before the unsigned cap comparison; retain both stores.
        uint32_t total = globals.amount() + amount;
        globals.amount(total);
        if (total > MaximumPowerupAmount)
            globals.amount(MaximumPowerupAmount);
        return 1;
    }
    if (s32(kind) > 0)
        run.call(0x4bc110, run.get(PowerupApplicationAddress), {});
    uint32_t previous = globals.kind();
    if (previous == uint32_t(PowerupKind::Unknown0x26b7)) {
        uint32_t object = playerFields.attachmentRange();
        if (object != 0) {
            uint32_t one[1] = {1};
            sendMessageToAttachmentRange(run, object, one);
        }
    } else if (previous == uint32_t(PowerupKind::GlitterMother)) {
        uint32_t record = stateFields.glitterMother();
        if (record != 0) {
            PowerupRemovalFields removalFields{run, record};
            uint32_t flags = removalFields.unknown_0x8();
            removalFields.unknown_0x8(flags | PowerupRemovalMask);
            stateFields.glitterMother(0);
        }
    } else if (previous == uint32_t(PowerupKind::Unknown0x26bd)) {
        uint32_t flags = playerFields.unknown_0xd4();
        playerFields.unknown_0xd4(flags | PlayerPowerupRestoreMask);
        uint32_t object = playerFields.attachmentRange();
        if (object != 0) {
            uint32_t one[1] = {1};
            sendMessageToAttachmentRange(run, object, one);
        }
    }
    globals.kind(kind);
    globals.amount(amount);
    switch (kind) {
    case uint32_t(PowerupKind::Unknown0x26b7):
    case uint32_t(PowerupKind::Unknown0x26bd):
        run.call(0x48c8a0, 0, {0x524d68, 0});
        break;
    case uint32_t(PowerupKind::Unknown0x26b8):
        run.call(0x48c8a0, 0, {0x524d58, 0});
        break;
    case uint32_t(PowerupKind::Unknown0x26b9):
        run.call(0x48c8a0, 0, {0x524d48, 0});
        break;
    case uint32_t(PowerupKind::Unknown0x26ba):
        run.call(0x48c8a0, 0, {0x524d38, 0});
        break;
    case uint32_t(PowerupKind::GlitterMother): {
        uint32_t flare = createGlitterMother(run, 0, &player);
        stateFields.glitterMother(flare);
        break;
    }
    default:
        break;
    }
    return 1;
}

// 0x420070. cdecl: (object, elapsed). Saturating countdown and the original
// five-frame cycle; no catch-up step when elapsed exceeds the countdown.
uint32_t advanceFlareFrame(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t elapsed = arguments[1];
    if (object == 0)
        return 0;
    PowerupGlobalsFields flareGlobals{run, PowerupGlobalsAddress};
    uint32_t timer = flareGlobals.flareCountdown();
    if (elapsed < timer)
        timer = timer - elapsed;
    else
        timer = 0;
    flareGlobals.flareCountdown(timer);
    if (timer == 0) {
        flareGlobals.flareCountdown(FlareFrameInterval);
        uint32_t frame = flareGlobals.flareFrame();
        switch (frame) {
        case 0x34:
            flareGlobals.flareFrame(0x35);
            break;
        case 0x35:
            flareGlobals.flareFrame(0x36);
            break;
        case 0x36:
            flareGlobals.flareFrame(0x37);
            break;
        case 0x65:
            flareGlobals.flareFrame(0x34);
            break;
        default:
            flareGlobals.flareFrame(0x65);
            break;
        }
    }
    PowerupPlayerFields flarePlayer{run, object};
    uint32_t attached = flarePlayer.flareAttachment();
    if (attached == 0)
        return 0;
    PowerupAttachmentFields flareAttachment{run, attached};
    if (flareAttachment.messageTarget() == 0)
        return 0;
    uint32_t target = flareAttachment.messageTarget();
    run.call(0x4c6130, target, {4, 0});
    // Dispatch can replace or clear the sprite, so reload the original slot.
    uint32_t sprite = flareAttachment.messageTarget();
    if (sprite == 0)
        return 0;
    FlareSpriteFields spriteFields{run, sprite};
    uint32_t frame = flareGlobals.flareFrame();
    spriteFields.frame(frame);
    return 0;
}

// 0x448400. cdecl: (owner). Creates the GlitterMother object and links it
// back to its owner at +0x170 of the new object's +0x6c record.
uint32_t createGlitterMother(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t owner = arguments[0];
    if (owner == 0)
        return 0;
    PowerupPlayerFields ownerFields{run, owner};
    uint32_t holder = ownerFields.unknown_0xc();
    GlitterMotherOwnerContextFields ownerContext{run, holder};
    uint32_t creationManager = ownerContext.creationManager();
    uint32_t created = run.call(0x4c8da0, creationManager, {1, 0x64, 0x64, 0, GlitterMotherNameAddress, 0});
    if (created == 0)
        return 0;
    ActorFields createdActor{run, created};
    uint32_t record = createdActor.holder();
    GlitterMotherRecordFields createdRecord{run, record};
    createdRecord.owner(owner);
    return created;
}

// 0x4ce7b0. thiscall: (this, message). Sends the message to the +0x30 target
// of every slot in [+0x64, +0x68] of the table at +0x14; returns the count.
uint32_t sendMessageToAttachmentRange(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t message = arguments[0];
    uint32_t count = 0;
    PowerupAttachmentRangeFields rangeFields{run, receiver};
    // Signed bounds and wrapping index arithmetic match the original.
    uint32_t index = rangeFields.firstIndex();
    uint32_t last = rangeFields.lastIndex();
    if (s32(index) > s32(last))
        return count;
    do {
        uint32_t item;
        uint32_t first = rangeFields.firstIndex();
        if (s32(index) < s32(first) || s32(index) > s32(last))
            item = 0;
        else {
            uint32_t slots = rangeFields.slots();
            item = run.get(slots + index * 4);
        }
        if (item != 0) {
            PowerupAttachmentFields attachment{run, item};
            if (attachment.messageTarget() != 0) {
                uint32_t target = attachment.messageTarget();
                run.call(0x4c6130, target, {message, 0});
                count = count + 1;
            }
        }
        // A callback may change either bound before the next iteration.
        last = rangeFields.lastIndex();
        index = index + 1;
    } while (s32(index) <= s32(last));
    return count;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x41f990:
        return changePlayerPowerup(run, receiver, arguments);
    case 0x420070:
        return advanceFlareFrame(run, receiver, arguments);
    case 0x448400:
        return createGlitterMother(run, receiver, arguments);
    case 0x4ce7b0:
        return sendMessageToAttachmentRange(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_claw_powerups_01_entry, owned, body)
