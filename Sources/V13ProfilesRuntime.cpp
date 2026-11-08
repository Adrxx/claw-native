#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"
#include "ClawRecoveredNames.h"

namespace {

using claw::Run;
using namespace claw::recovered::v13;

int owned(uint32_t function) {
    switch (function) {
    case 0x425a20:
    case 0x425a40:
    case 0x42a920:
        return 0;
    case 0x487a70:
        return 4;
    default:
        return -1;
    }
}

// Each route publishes its selector before tail-dispatching the same handler.
// The selector values do not establish names for the destination modes.
uint32_t routeProfile(Run &run, uint32_t receiver, uint32_t route) {
    run.put(ProfileRouteAddress, route);
    return run.vcall(receiver, ProfileRouteHandlerSlot);
}

// 0x425a20. Void guest return; retain the existing ignored callback result.
uint32_t selectProfileRouteOne(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return routeProfile(run, receiver, uint32_t(ProfileRoute::One));
}

// 0x425a40. Void guest return; retain the existing ignored callback result.
uint32_t selectProfileRouteTwo(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return routeProfile(run, receiver, uint32_t(ProfileRoute::Two));
}

// 0x42a920. The second mode query reloads the provider after the first callback.
uint32_t openProfileDialogForAllowedModes(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    ApplicationProfileFields applicationFields{run, receiver};
    uint32_t modeProvider = applicationFields.modeProvider();
    if (run.vcall(modeProvider, ModeQuerySlot) != FirstAllowedProfileMode) {
        modeProvider = applicationFields.modeProvider();
        if (run.vcall(modeProvider, ModeQuerySlot) != SecondAllowedProfileMode) {
            return 0;
        }
    }
    run.call(0x42d710, receiver, {ProfileDialogResourceAddress, ProfileDialogProcedureAddress});
    return 1;
}

// 0x487a70. Both close controls keep the current selection and end with result 1.
uint32_t dispatchProfileDialogMessage(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t window = arguments[0];
    uint32_t message = arguments[1];
    uint32_t command = arguments[2];
    if (message == uint32_t(ProfileDialogMessage::Initialize)) {
        return run.call(0x487b30, 0, {window});
    }
    if (message != uint32_t(ProfileDialogMessage::Command)) {
        return 0;
    }
    uint32_t control = command & 0xffff;
    if (control == uint32_t(ProfileDialogControl::Confirm) || control == uint32_t(ProfileDialogControl::Cancel)) {
        uint32_t application = run.get(ApplicationAddress);
        ApplicationProfileFields applicationFields{run, application};
        uint32_t entrySelection = run.get(ProfileEntrySelectionAddress);
        uint32_t currentSelection = applicationFields.selectedProfile();
        if (entrySelection != currentSelection) {
            run.put(ProfileSelectionChangedAddress, 1);
        }
        run.icall(0x50c478, {window, 1});
        return 1;
    }
    if (control == uint32_t(ProfileDialogControl::Remove)) {
        run.call(0x488140, 0, {window});
        return 1;
    }
    if (control == uint32_t(ProfileDialogControl::Create)) {
        run.call(0x488200, 0, {window});
        return 1;
    }
    if ((command >> 16) == ProfileSelectionNotification) {
        // Keep the full command word: the original pushes ECX, not just CX.
        run.call(0x488050, 0, {window, command});
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x425a20:
        return selectProfileRouteOne(run, receiver, arguments);
    case 0x425a40:
        return selectProfileRouteTwo(run, receiver, arguments);
    case 0x42a920:
        return openProfileDialogForAllowedModes(run, receiver, arguments);
    case 0x487a70:
        return dispatchProfileDialogMessage(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

}

CLAW_MODULE_ENTRY(claw_v13_profiles_entry, owned, body)
