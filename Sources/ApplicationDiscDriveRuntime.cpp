// Original application disc-drive discovery
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x42b020:
        return 0;
    default:
        return -1;
    }
}

// 0x42b020. thiscall, 0 stack argument(s), returns u32.
uint32_t function_42b020(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // Application +0xd0 is the attempted flag; +0xcc is the cached drive byte.
    uint32_t eax = run.get(receiver + 0xd0);
    if (eax != 0)
        return (eax & 0xffffff00u) | run.get8(receiver + 0xcc);
    // Application +0x38 holds the configuration object.
    uint32_t configuration = run.get(receiver + 0x38);
    run.put(receiver + 0xd0, 1);
    uint32_t size = run.automatic(-0x124);
    uint32_t configuredDrive = run.automatic(-0x120);
    uint32_t directory = run.automatic(-0x100);
    if (configuration != 0) {
        run.put(size, 30);
        run.put8(configuredDrive, 0);
        run.stackPointer = run.automatic(-0x148);
        eax = run.call(0x4b5e90, configuration, {0x525ec4, configuredDrive, size, 0});
        if (eax != 0) {
            uint32_t drive = run.get8(configuredDrive);
            eax = (eax & 0xffffff00u) | drive;
            if (drive > 0x14 && drive < 0x80) {
                run.put8(receiver + 0xcc, uint8_t(drive));
                return eax;
            }
        }
    }
    run.stackPointer = run.automatic(-0x140);
    run.icall(0x546a28, {255, directory});
    run.put8(directory + 3, 0);
    run.stackPointer = run.automatic(-0x13c);
    eax = run.icall(0x546a2c, {directory});
    if (eax == 5) {
        uint8_t drive = run.get8(directory);
        eax &= 0xffffff00u;
        run.put8(receiver + 0xcc, drive);
        run.put8(receiver + 0xcc, 0);
        return eax;
    }
    uint32_t drive = 0x41;
    for (uint32_t index = 0; index < 26; ++index) {
        run.stackPointer = run.automatic(-0x144);
        run.call(0x4a3920, 0, {directory, 0x524f08, drive});
        run.stackPointer = run.automatic(-0x13c);
        eax = run.icall(0x546a2c, {directory});
        if (eax == 5) {
            run.put8(receiver + 0xcc, uint8_t(drive));
            return (eax & 0xffffff00u) | drive;
        }
        ++drive;
    }
    run.put8(receiver + 0xcc, 0);
    return eax & 0xffffff00u;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42b020:
        return function_42b020(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_application_disc_drive_entry, owned, body)
