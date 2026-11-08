// Original application player-cache publication and change-player dialog
//
// Recovered game decisions and explicit guest frames from the original packet.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;
using namespace claw::recovered::v10;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x42bb00:
        return 2;
    case 0x42bbb0:
        return 0;
    case 0x42bbd0:
        return 0;
    case 0x42bbe0:
        return 0;
    case 0x42bbf0:
        return 0;
    case 0x42bf90:
        return 1;
    case 0x430ac0:
        return 1;
    case 0x49b050:
        return 1;
    case 0x49b0c0:
        return 1;
    case 0x49b730:
        return 4;
    case 0x49c090:
        return 3;
    default:
        return -1;
    }
}

// Two ten-word blocks are copied in original read/store order, including overlap.
// The words have no proven individual meaning and retain their byte-offset names.
// 0x430ac0
uint32_t copyPlayerCacheWords(Run &run, uint32_t receiver, uint32_t player) {
    if (!player || !(player + 0x2604))
        return 0;
    PlayerCacheFields cacheFields{run, receiver};
    ProfileCacheRecordFields playerFields{run, player};
    [[maybe_unused]] uint32_t word_10 = playerFields.unknown_0x2618();
    cacheFields.unknown_0x10(word_10);
    [[maybe_unused]] uint32_t word_14 = playerFields.unknown_0x261c();
    cacheFields.unknown_0x14(word_14);
    [[maybe_unused]] uint32_t word_18 = playerFields.unknown_0x2620();
    cacheFields.unknown_0x18(word_18);
    [[maybe_unused]] uint32_t word_1c = playerFields.unknown_0x2624();
    cacheFields.unknown_0x1c(word_1c);
    [[maybe_unused]] uint32_t word_20 = playerFields.unknown_0x2628();
    cacheFields.unknown_0x20(word_20);
    [[maybe_unused]] uint32_t word_24 = playerFields.unknown_0x262c();
    cacheFields.unknown_0x24(word_24);
    [[maybe_unused]] uint32_t word_28 = playerFields.unknown_0x2630();
    cacheFields.unknown_0x28(word_28);
    [[maybe_unused]] uint32_t word_2c = playerFields.unknown_0x2634();
    cacheFields.unknown_0x2c(word_2c);
    [[maybe_unused]] uint32_t word_30 = playerFields.unknown_0x2638();
    cacheFields.unknown_0x30(word_30);
    [[maybe_unused]] uint32_t word_34 = playerFields.unknown_0x263c();
    cacheFields.unknown_0x34(word_34);
    if (!(player + 0x25c0))
        return 0;
    [[maybe_unused]] uint32_t word_48 = playerFields.unknown_0x25d4();
    cacheFields.unknown_0x48(word_48);
    [[maybe_unused]] uint32_t word_4c = playerFields.unknown_0x25d8();
    cacheFields.unknown_0x4c(word_4c);
    [[maybe_unused]] uint32_t word_50 = playerFields.unknown_0x25dc();
    cacheFields.unknown_0x50(word_50);
    [[maybe_unused]] uint32_t word_54 = playerFields.unknown_0x25e0();
    cacheFields.unknown_0x54(word_54);
    [[maybe_unused]] uint32_t word_58 = playerFields.unknown_0x25e4();
    cacheFields.unknown_0x58(word_58);
    [[maybe_unused]] uint32_t word_5c = playerFields.unknown_0x25e8();
    cacheFields.unknown_0x5c(word_5c);
    [[maybe_unused]] uint32_t word_60 = playerFields.unknown_0x25ec();
    cacheFields.unknown_0x60(word_60);
    [[maybe_unused]] uint32_t word_64 = playerFields.unknown_0x25f0();
    cacheFields.unknown_0x64(word_64);
    [[maybe_unused]] uint32_t word_68 = playerFields.unknown_0x25f4();
    cacheFields.unknown_0x68(word_68);
    [[maybe_unused]] uint32_t word_6c = playerFields.unknown_0x25f8();
    cacheFields.unknown_0x6c(word_6c);
    return 1;
}
// 0x42bf90. Application +0x64 is the current player.
uint32_t publishApplicationPlayer(Run &run, uint32_t receiver, uint32_t player) {
    ApplicationPlayerFields applicationFields{run, receiver};
    run.put(0x53725c, 0);
    applicationFields.currentPlayer(player);
    if (player) {
        uint32_t cache = run.get(0x537204);
        if (cache)
            copyPlayerCacheWords(run, cache, player);
        [[maybe_unused]] uint32_t publishedPlayer = applicationFields.currentPlayer();
        run.put(0x53725c, (run.get8(publishedPlayer + 0x04) & 4) >> 2);
    }
    return 0;
}
// 0x49b050
uint32_t displayApplicationPlayerName(Run &run, uint32_t hwnd) {
    if (!hwnd)
        return 0;
    uint32_t app = run.get(0x5371fc);
    ApplicationPlayerFields applicationFields{run, app};
    uint32_t player = applicationFields.currentPlayer();
    uint32_t name = player + 0x14;
    if (!player) {
        uint32_t playerManager = applicationFields.playerManager();
        player = run.call(0x49bee0, playerManager, {0x5255e8});
        publishApplicationPlayer(run, run.get(0x5371fc), player);
        name = 0x5255e8;
    }
    run.icall(0x546d3c, {hwnd, 0x441, name});
    return 1;
}
// 0x49b0c0
uint32_t publishPlayerListSelection(Run &run, uint32_t hwnd, uint32_t buffer) {
    if (!hwnd)
        return 0;
    uint32_t choice = run.icall(0x546d44, {hwnd, 0x188, 0, 0});
    if (choice == 0xffffffff)
        return 0;
    run.put8(buffer, 0);
    if (run.icall(0x546d44, {hwnd, 0x189, choice, buffer}) == 0xffffffff)
        return 0;
    uint32_t app = run.get(0x5371fc);
    ApplicationPlayerFields applicationFields{run, app};
    uint32_t playerManager = applicationFields.playerManager();
    uint32_t player = run.call(0x49bee0, playerManager, {buffer});
    if (!player)
        return 0;
    publishApplicationPlayer(run, run.get(0x5371fc), player);
    return 1;
}
// 0x49c090. Manager +4 is head, +0xc is signed count; node +8 is player.
uint32_t fillPlayerList(Run &run, uint32_t receiver, uint32_t hwnd, uint32_t player, uint32_t filter) {
    if (!hwnd)
        return 0;
    run.icall(0x546d44, {hwnd, 0x184, 0, 0});
    PlayerListManagerFields managerFields{run, receiver};
    if (s32(managerFields.count()) <= 0)
        return 0;
    uint32_t node = managerFields.head();
    uint32_t count = 0;
    while (node) {
        ProfileListNodeFields nodeFields{run, node};
        uint32_t next = nodeFields.next();
        uint32_t item = nodeFields.record();
        if (filter && !run.call(0x4a3cf0, 0, {item + 0x14, 0x5255e8}))
            item = 0;
        if (item && run.icall(0x546d44, {hwnd, 0x180, 0, item + 0x14}) != 0xffffffff)
            ++count;
        node = next;
    }
    if (player) {
        uint32_t index = run.icall(0x546d44, {hwnd, 0x18f, 0, player + 0x14});
        if (index != 0xffffffff)
            run.icall(0x546d44, {hwnd, 0x186, index, 0});
    }
    return count;
}
void push(Run &run, ClawSourceContext &cpu, uint32_t value);
uint32_t pop(Run &run, ClawSourceContext &cpu);
uint32_t physicalCall(Run &run, ClawSourceContext &cpu, uint32_t function, uint32_t receiver, uint32_t rpc, std::initializer_list<uint32_t> arguments, uint32_t popBytes) {
    for (auto i = arguments.end(); i != arguments.begin();) {
        --i;
        push(run, cpu, *i);
    }
    push(run, cpu, rpc);
    return run.callback_call(function, receiver, rpc, arguments, popBytes);
}
void publishApplicationPlayerWithCPU(Run &run, ClawSourceContext &cpu, uint32_t player) {
    push(run, cpu, cpu.esi);
    cpu.esi = cpu.ecx;
    run.put(0x53725c, 0);
    ApplicationPlayerFields applicationForStore{run, cpu.esi};
    applicationForStore.currentPlayer(player);
    if (player) {
        cpu.ecx = run.get(0x537204);
        if (cpu.ecx) {
            push(run, cpu, player);
            push(run, cpu, 0x42bfb8);
            push(run, cpu, cpu.esi);
            copyPlayerCacheWords(run, cpu.ecx, player);
            cpu.esi = pop(run, cpu);
            pop(run, cpu);
            cpu.esp += 4;
        }
        ApplicationPlayerFields applicationAfterCopy{run, cpu.esi};
        cpu.eax = applicationAfterCopy.currentPlayer();
        cpu.ecx = (run.get8(cpu.eax + 0x04) & 4) >> 2;
        run.put(0x53725c, cpu.ecx);
    }
    cpu.esi = pop(run, cpu);
}
void displayApplicationPlayerNameWithCPU(Run &run, ClawSourceContext &cpu, uint32_t hwnd) {
    push(run, cpu, cpu.esi);
    cpu.esi = hwnd;
    if (hwnd) {
        cpu.ecx = run.get(0x5371fc);
        ApplicationPlayerFields applicationForDisplay{run, cpu.ecx};
        cpu.eax = applicationForDisplay.currentPlayer();
        if (cpu.eax) {
            cpu.eax += 0x14;
            physicalCall(run, cpu, run.get(0x546d3c), 0, 0x49b07a, {hwnd, 0x441, cpu.eax}, 12);
        } else {
            cpu.ecx = applicationForDisplay.playerManager();
            physicalCall(run, cpu, 0x49bee0, cpu.ecx, 0x49b08e, {0x5255e8}, 4);
            cpu.ecx = run.get(0x5371fc);
            push(run, cpu, cpu.eax);
            push(run, cpu, 0x49b09a);
            publishApplicationPlayerWithCPU(run, cpu, cpu.eax);
            pop(run, cpu);
            cpu.esp += 4;
            physicalCall(run, cpu, run.get(0x546d3c), 0, 0x49b0ab, {hwnd, 0x441, 0x5255e8}, 12);
        }
        cpu.eax = 1;
    } else {
        cpu.eax = 0;
    }
    cpu.esi = pop(run, cpu);
}
// ADD sets the complete arithmetic flag group before physical list insertion.
uint32_t addCPU(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    uint32_t value = left + right;
    uint32_t low = value & 0xff;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    cpu.eflags = (cpu.eflags & ~0x8d5u) | 2u |
        (value < left ? 1u : 0u) | (!(low & 1) ? 4u : 0u) |
        ((left ^ right ^ value) & 0x10u) | (!value ? 0x40u : 0u) |
        ((value >> 24) & 0x80u) | ((~(left ^ right) & (left ^ value) & 0x80000000u) ? 0x800u : 0u);
    return value;
}
void fillPlayerListWithCPU(Run &run, ClawSourceContext &cpu, uint32_t hwnd, uint32_t selectedPlayer) {
    push(run, cpu, cpu.ebx);
    cpu.ebx = hwnd;
    push(run, cpu, cpu.ebp);
    push(run, cpu, cpu.esi);
    push(run, cpu, cpu.edi);
    cpu.esi = cpu.ecx;
    if (hwnd) {
        cpu.ebp = run.get(0x546d44);
        physicalCall(run, cpu, cpu.ebp, 0, 0x49c0b9, {hwnd, 0x184, 0, 0}, 16);
        PlayerListManagerFields managerAfterReset{run, cpu.esi};
        cpu.eax = managerAfterReset.count();
        if (s32(cpu.eax) > 0) {
            cpu.edi = managerAfterReset.head();
            run.put(cpu.esp + 0x14, 0);
            while (cpu.edi) {
                cpu.eax = cpu.edi;
                ProfileListNodeFields nodeForNext{run, cpu.edi};
                cpu.edi = nodeForNext.next();
                ProfileListNodeFields nodeForRecord{run, cpu.eax};
                cpu.esi = nodeForRecord.record();
                cpu.eax = 0;
                if (cpu.esi) {
                    cpu.esi = addCPU(cpu, cpu.esi, 0x14);
                    physicalCall(run, cpu, cpu.ebp, 0, 0x49c110, {hwnd, 0x180, 0, cpu.esi}, 16);
                    if (cpu.eax != 0xffffffff)
                        run.put(cpu.esp + 0x14, run.get(cpu.esp + 0x14) + 1);
                }
            }
            cpu.eax = selectedPlayer;
            if (cpu.eax) {
                cpu.eax += 0x14;
                physicalCall(run, cpu, cpu.ebp, 0, 0x49c133, {hwnd, 0x18f, 0, cpu.eax}, 16);
                if (cpu.eax != 0xffffffff)
                    physicalCall(run, cpu, cpu.ebp, 0, 0x49c143, {hwnd, 0x186, cpu.eax, 0}, 16);
            }
            cpu.eax = run.get(cpu.esp + 0x14);
        } else {
            cpu.eax = 0;
        }
    } else {
        cpu.eax = 0;
    }
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
    cpu.ebp = pop(run, cpu);
    cpu.ebx = pop(run, cpu);
}
void publishPlayerListSelectionWithCPU(Run &run, ClawSourceContext &cpu, uint32_t hwnd) {
    cpu.esp -= 0x100;
    push(run, cpu, cpu.esi);
    cpu.esi = hwnd;
    push(run, cpu, cpu.edi);
    cpu.eax = 0;
    if (hwnd) {
        cpu.edi = run.get(0x546d44);
        physicalCall(run, cpu, cpu.edi, 0, 0x49b0f0, {hwnd, 0x188, 0, 0}, 16);
        if (cpu.eax != 0xffffffff) {
            cpu.ecx = cpu.esp + 0x08;
            run.put8(cpu.ecx, 0);
            physicalCall(run, cpu, cpu.edi, 0, 0x49b113, {hwnd, 0x189, cpu.eax, cpu.ecx}, 16);
            if (cpu.eax != 0xffffffff) {
                cpu.eax = run.get(0x5371fc);
                cpu.edx = cpu.esp + 0x08;
                ApplicationPlayerFields applicationForLookup{run, cpu.eax};
                cpu.ecx = applicationForLookup.playerManager();
                physicalCall(run, cpu, 0x49bee0, cpu.ecx, 0x49b135, {cpu.edx}, 4);
                if (cpu.eax) {
                    cpu.ecx = run.get(0x5371fc);
                    push(run, cpu, cpu.eax);
                    push(run, cpu, 0x49b14e);
                    publishApplicationPlayerWithCPU(run, cpu, cpu.eax);
                    pop(run, cpu);
                    cpu.esp += 4;
                    cpu.eax = 1;
                }
            } else {
                cpu.eax = 0;
            }
        } else {
            cpu.eax = 0;
        }
    }
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
    cpu.esp += 0x100;
}
uint32_t changePlayerDialogWithCPU(Run &run, const uint32_t *arguments) {
    auto &cpu = run.callback_cpu();
    uint32_t hwnd = arguments[0];
    cpu.eax = arguments[1] - 0x110;
    push(run, cpu, cpu.esi);
    if (arguments[1] == 0x110) {
        cpu.esi = hwnd;
        physicalCall(run, cpu, run.get(0x546d40), 0, 0x49b7dd, {hwnd, 0x43b}, 8);
        cpu.ecx = run.get(0x5371fc);
        run.put(0x53ebec, cpu.eax);
        ApplicationPlayerFields applicationForInitialize{run, cpu.ecx};
        if (cpu.ecx && applicationForInitialize.playerManager()) {
            cpu.edx = applicationForInitialize.currentPlayer();
            run.put(0x53ebe0, cpu.edx);
            cpu.ecx = applicationForInitialize.playerManager();
            uint32_t list = cpu.eax;
            uint32_t player = cpu.edx;
            push(run, cpu, 0);
            push(run, cpu, player);
            push(run, cpu, list);
            push(run, cpu, 0x49b82b);
            fillPlayerListWithCPU(run, cpu, list, player);
            pop(run, cpu);
            cpu.esp += 12;
            push(run, cpu, cpu.esi);
            push(run, cpu, 0x49b831);
            displayApplicationPlayerNameWithCPU(run, cpu, cpu.esi);
            pop(run, cpu);
            cpu.esp += 4;
        } else {
            physicalCall(run, cpu, run.get(0x546d34), 0, cpu.ecx ? 0x49b80d : 0x49b7f4, {hwnd, 0}, 8);
        }
        cpu.eax = 1;
    } else if (arguments[1] == 0x111) {
        cpu.eax = arguments[2];
        bool accept = cpu.eax == 1;
        bool cancel = cpu.eax == 2;
        if (!accept && !cancel) {
            cpu.ecx = run.get(0x53ebec);
            accept = cpu.ecx && arguments[3] == cpu.ecx && (cpu.eax >> 16) == 2;
        }
        if (accept) {
            uint32_t list = run.get(0x53ebec);
            if (arguments[2] == 1)
                cpu.eax = list;
            push(run, cpu, list);
            push(run, cpu, arguments[2] == 1 ? 0x49b75b : 0x49b7ae);
            publishPlayerListSelectionWithCPU(run, cpu, list);
            pop(run, cpu);
            cpu.esp += 4;
            if (arguments[2] == 1)
                cpu.ecx = hwnd;
            else
                cpu.eax = hwnd;
            physicalCall(run, cpu, run.get(0x546d34), 0, arguments[2] == 1 ? 0x49b76b : 0x49b7be, {hwnd, 0}, 8);
            cpu.eax = 1;
        } else if (cancel) {
            cpu.edx = hwnd;
            physicalCall(run, cpu, run.get(0x546d34), 0, 0x49b786, {hwnd, 0}, 8);
            cpu.eax = 1;
        } else {
            cpu.eax = 0;
        }
    } else {
        cpu.eax = 0;
    }
    cpu.esi = pop(run, cpu);
    return cpu.eax;
}

// 0x49b730
uint32_t handleChangePlayerDialog(Run &run, const uint32_t *arguments) {
    uint32_t hwnd = arguments[0];
    uint32_t message = arguments[1];
    uint32_t command = arguments[2];
    if (message == 0x110) {
        uint32_t list = run.icall(0x546d40, {hwnd, 0x43b});
        uint32_t app = run.get(0x5371fc);
        run.put(0x53ebec, list);
        ApplicationPlayerFields applicationForDialog{run, app};
        if (!app || !applicationForDialog.playerManager()) {
            run.icall(0x546d34, {hwnd, 0});
            return 1;
        }
        uint32_t player = applicationForDialog.currentPlayer();
        run.put(0x53ebe0, player);
        uint32_t playerManager = applicationForDialog.playerManager();
        fillPlayerList(run, playerManager, list, player, 0);
        displayApplicationPlayerName(run, hwnd);
        return 1;
    }
    if (message == 0x111) {
        if (command == 2) {
            run.icall(0x546d34, {hwnd, 0});
            return 1;
        }
        uint32_t list = run.get(0x53ebec);
        if (command == 1 || (list && arguments[3] == list && (command >> 16) == 2)) {
            publishPlayerListSelection(run, list, run.automatic(-0x10c));
            run.icall(0x546d34, {hwnd, 0});
            return 1;
        }
    }
    return 0;
}
// 0x42bb00. Application +0x30 scene, +4 window owner, +8 module owner.
uint32_t showApplicationDialog(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!arguments[0] || !arguments[1])
        return 0;
    ApplicationPlayerFields applicationForModal{run, receiver};
    if (applicationForModal.scene()) {
        uint32_t sceneForSurface = applicationForModal.scene();
        uint32_t surface = run.get(sceneForSurface + 0x04);
        run.call(0x4ca9e0, surface, {run.get(surface + 0x14)});
        uint32_t sceneAfterPrepare = applicationForModal.scene();
        uint32_t com = run.get(run.get(sceneAfterPrepare + 0x1c));
        run.call(run.get(run.get(com) + 0x28), 0, {com});
    }
    uint32_t saved = run.icall(0x546d54, {1});
    while (s32(run.icall(0x546d54, {1})) < 0) {}
    uint32_t moduleOwner = applicationForModal.moduleOwner();
    uint32_t moduleHandle = run.get(moduleOwner + 0x0c);
    [[maybe_unused]] uint32_t windowOwner = applicationForModal.windowOwner();
    uint32_t windowHandle = run.get(windowOwner + 0x04);
    uint32_t result = run.icall(0x546d2c, {moduleHandle, arguments[0], windowHandle, arguments[1], 0});
    if (s32(saved) <= 0) {
        while (s32(run.icall(0x546d54, {0})) >= 0) {}
    }
    run.call(0x42abf0, receiver);
    return result;
}
uint32_t postPlayerCommand(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    ApplicationPlayerFields applicationForCommand{run, receiver};
    [[maybe_unused]] uint32_t windowOwner = applicationForCommand.windowOwner();
    return run.icall(0x546d50, {run.get(windowOwner + 0x04), 0x111, 0x8090, 5});
}
uint32_t showChangePlayer(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t dialogArguments[] = {0x525f30, 0x49b730};
    return showApplicationDialog(run, receiver, dialogArguments);
}
uint32_t showPlayerInfo(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t dialogArguments[] = {0x525f3c, 0x49b160};
    return showApplicationDialog(run, receiver, dialogArguments);
}
uint32_t showRemovePlayer(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    ApplicationPlayerFields applicationForRemoval{run, receiver};
    if (applicationForRemoval.currentPlayer()) {
        uint32_t playerManager = applicationForRemoval.playerManager();
        PlayerListManagerFields removalManager{run, playerManager};
        if (s32(removalManager.count()) > 1) {
            uint32_t dialogArguments[] = {0x525f48, 0x49b630};
            if (s32(showApplicationDialog(run, receiver, dialogArguments)) > 0) {
                [[maybe_unused]] uint32_t windowOwner = applicationForRemoval.windowOwner();
                run.icall(0x546d50, {run.get(windowOwner + 0x04), 0x111, 0x8090, 6});
            }
        }
    }
    return 0;
}
uint32_t publishPlayer(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return publishApplicationPlayer(run, receiver, arguments[0]);
}
uint32_t copyPlayerCache(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return copyPlayerCacheWords(run, receiver, arguments[0]);
}
uint32_t displayCurrentPlayer(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return displayApplicationPlayerName(run, arguments[0]);
}
uint32_t publishSelectedPlayer(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return publishPlayerListSelection(run, arguments[0], run.automatic(-0x100));
}
uint32_t changePlayerDialogProc(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return run.host.callbackCPU ? changePlayerDialogWithCPU(run, arguments) : handleChangePlayerDialog(run, arguments);
}
uint32_t populatePlayerList(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return fillPlayerList(run, receiver, arguments[0], arguments[1], arguments[2]);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42bb00:
        return showApplicationDialog(run, receiver, arguments);
    case 0x42bbb0:
        return postPlayerCommand(run, receiver, arguments);
    case 0x42bbd0:
        return showChangePlayer(run, receiver, arguments);
    case 0x42bbe0:
        return showPlayerInfo(run, receiver, arguments);
    case 0x42bbf0:
        return showRemovePlayer(run, receiver, arguments);
    case 0x42bf90:
        return publishPlayer(run, receiver, arguments);
    case 0x430ac0:
        return copyPlayerCache(run, receiver, arguments);
    case 0x49b050:
        return displayCurrentPlayer(run, receiver, arguments);
    case 0x49b0c0:
        return publishSelectedPlayer(run, receiver, arguments);
    case 0x49b730:
        return changePlayerDialogProc(run, receiver, arguments);
    case 0x49c090:
        return populatePlayerList(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

// Source variants retain the physical guest frames used by synchronous dialogs.
// Stack slots, return PCs, byte-sized profile flags, name-address arithmetic and
// physical platform-owner offsets stay literal; no native record is materialized.
void push(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}
uint32_t pop(Run &run, ClawSourceContext &cpu) {
    uint32_t value = run.get(cpu.esp);
    cpu.esp += 4;
    return value;
}
void sourceCall(Run &run, ClawSourceContext &cpu, uint32_t function, uint32_t receiver, uint32_t returnPC, std::initializer_list<uint32_t> arguments, uint32_t popBytes, bool whole = false) {
    (void)receiver;
    (void)popBytes;
    for (auto i = arguments.end(); i != arguments.begin();) {
        --i;
        push(run, cpu, *i);
    }
    push(run, cpu, returnPC);
    auto child = cpu;
    child.inputMask = 0x7ff;
    child.outputMask = whole ? 0x5f3 : 0x7ff;
    child.preserveMask = 0x472;
    child.eip = function;
    run.source_call(function, receiver, returnPC, child, arguments, 0, popBytes);
    cpu.eax = child.eax;
    cpu.ebx = child.ebx;
    cpu.ecx = child.ecx;
    cpu.edx = child.edx;
    cpu.esi = child.esi;
    cpu.edi = child.edi;
    cpu.ebp = child.ebp;
    cpu.esp = child.esp;
    cpu.eip = child.eip;
    cpu.eflags = child.eflags;
    cpu.fsHead = child.fsHead;
}
// 0x42bb00, physical stack and CPU body.
uint32_t showApplicationDialogWithCPU(Run &run, ClawSourceContext &cpu) {
    cpu.eax = run.get(cpu.esp + 0x04);
    push(run, cpu, cpu.ebx);
    push(run, cpu, cpu.ebp);
    push(run, cpu, cpu.esi);
    push(run, cpu, cpu.edi);
    cpu.edi = cpu.ecx;
    bool valid = cpu.eax != 0;
    if (valid) {
        cpu.ebp = run.get(cpu.esp + 0x18);
        valid = cpu.ebp != 0;
    }
    if (valid) {
        ApplicationPlayerFields applicationForScene{run, cpu.edi};
        cpu.eax = applicationForScene.scene();
        if (cpu.eax) {
            cpu.ecx = run.get(cpu.eax + 0x04);
            cpu.eax = run.get(cpu.ecx + 0x14);
            sourceCall(run, cpu, 0x4ca9e0, cpu.ecx, 0x42bb3b, {cpu.eax}, 4, true);
            ApplicationPlayerFields applicationAfterPrepare{run, cpu.edi};
            cpu.ecx = applicationAfterPrepare.scene();
            cpu.eax = run.get(cpu.ecx + 0x1c);
            cpu.eax = run.get(cpu.eax);
            cpu.edx = run.get(cpu.eax);
            sourceCall(run, cpu, run.get(cpu.edx + 0x28), 0, 0x42bb49, {cpu.eax}, 4);
        }
        cpu.esi = run.get(0x546d54);
        sourceCall(run, cpu, cpu.esi, 0, 0x42bb53, {1}, 4);
        cpu.ebx = cpu.eax;
        sourceCall(run, cpu, cpu.esi, 0, 0x42bb59, {1}, 4);
        while (s32(cpu.eax) < 0)
            sourceCall(run, cpu, cpu.esi, 0, 0x42bb61, {1}, 4);
        ApplicationPlayerFields applicationForWindow{run, cpu.edi};
        cpu.eax = applicationForWindow.windowOwner();
        cpu.edx = run.get(cpu.esp + 0x14);
        uint32_t hwnd = run.get(cpu.eax + 0x04);
        ApplicationPlayerFields applicationForModule{run, cpu.edi};
        cpu.eax = applicationForModule.moduleOwner();
        cpu.ecx = run.get(cpu.eax + 0x0c);
        sourceCall(run, cpu, run.get(0x546d2c), 0, 0x42bb81, {cpu.ecx, cpu.edx, hwnd, cpu.ebp, 0}, 20);
        cpu.ebp = cpu.eax;
        if (s32(cpu.ebx) <= 0) {
            sourceCall(run, cpu, cpu.esi, 0, 0x42bb8b, {0}, 4);
            while (s32(cpu.eax) >= 0)
                sourceCall(run, cpu, cpu.esi, 0, 0x42bb93, {0}, 4);
        }
        cpu.ecx = cpu.edi;
        sourceCall(run, cpu, 0x42abf0, cpu.ecx, 0x42bb9e, {}, 0, true);
        cpu.edi = pop(run, cpu);
        cpu.eax = cpu.ebp;
        cpu.esi = pop(run, cpu);
        cpu.ebp = pop(run, cpu);
        cpu.ebx = pop(run, cpu);
    } else {
        cpu.eax = 0;
        cpu.edi = pop(run, cpu);
        cpu.esi = pop(run, cpu);
        cpu.ebp = pop(run, cpu);
        cpu.ebx = pop(run, cpu);
    }
    return cpu.eax;
}
void callApplicationDialogWithCPU(Run &run, ClawSourceContext &cpu, uint32_t name, uint32_t callback, uint32_t returnPC) {
    push(run, cpu, callback);
    push(run, cpu, name);
    push(run, cpu, returnPC);
    showApplicationDialogWithCPU(run, cpu);
    cpu.eip = pop(run, cpu);
    cpu.esp += 8;
}
uint32_t sourceBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    auto &cpu = run.source();
    switch (function) {
    case 0x42bb00: {
        uint32_t result = showApplicationDialogWithCPU(run, cpu);
        return result;
    }
    case 0x42bbd0:
        callApplicationDialogWithCPU(run, cpu, 0x525f30, 0x49b730, 0x42bbdf);
        return cpu.eax;
    case 0x42bbe0:
        callApplicationDialogWithCPU(run, cpu, 0x525f3c, 0x49b160, 0x42bbef);
        return cpu.eax;
    case 0x42bbf0: {
        push(run, cpu, cpu.esi);
        cpu.esi = cpu.ecx;
        ApplicationPlayerFields applicationForSourceRemoval{run, cpu.esi};
        cpu.eax = applicationForSourceRemoval.currentPlayer();
        if (cpu.eax) {
            cpu.eax = applicationForSourceRemoval.playerManager();
            PlayerListManagerFields sourceRemovalManager{run, cpu.eax};
            if (s32(sourceRemovalManager.count()) > 1) {
                cpu.ecx = cpu.esi;
                callApplicationDialogWithCPU(run, cpu, 0x525f48, 0x49b630, 0x42bc14);
                if (s32(cpu.eax) > 0) {
                    ApplicationPlayerFields applicationAfterRemoval{run, cpu.esi};
                    cpu.ecx = applicationAfterRemoval.windowOwner();
                    cpu.edx = run.get(cpu.ecx + 0x04);
                    sourceCall(run, cpu, run.get(0x546d50), 0, 0x42bc31, {cpu.edx, 0x111, 0x8090, 6}, 16);
                }
            }
        }
        cpu.esi = pop(run, cpu);
        return cpu.eax;
    }
    default:
        return body(run, function, receiver, arguments);
    }
}
bool optional(uint32_t) {
    return true;
}
ClawSourceContract contract(uint32_t function) {
    switch (function) {
    case 0x42bb00:
        return {0x7ff, 0x5f3, 0x472, 8};
    case 0x42bbd0:
    case 0x42bbe0:
    case 0x42bbf0:
        return {0x7ff, 0x5f3, 0x472, 0};
    default:
        return {};
    }
}

} // namespace

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_player_cache_application_canonical_entry, owned, contract, optional, body, sourceBody)
