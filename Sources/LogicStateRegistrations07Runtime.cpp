// Level 1 logic state registrations group 7
// Callback addresses remain data; parent registrations retain their original boundary.
#include "ClawRuntime.hpp"
#include "LogicStateRegistryCoreRuntime.h"

namespace {

using claw::Run;
using claw::state_registry::registerBinding;

bool equal(Run &run, uint32_t first, uint32_t second) {
    for (;;) {
        const uint8_t byte = run.get8(first++);
        if (byte != run.get8(second++))
            return false;
        if (!byte)
            return true;
    }
}

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x488b00:
        return 0;
    case 0x489210:
        return 0;
    case 0x489960:
        return 0;
    case 0x48b1d0:
        return 0;
    case 0x48e6e0:
        return 0;
    case 0x4924f0:
        return 0;
    case 0x4940e0:
        return 0;
    case 0x497240:
        return 0;
    case 0x4982e0:
        return 0;
    case 0x49f2e0:
        return 0;
    case 0x4a0340:
        return 0;
    default:
        return -1;
    }
}

// 0x488b00. cdecl, 0 stack argument(s), returns void (normalized to zero).
uint32_t function_488b00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x53c2a0, 0x529a48, 0x488cd0, 0, 0, 0x488b9b, 0x488c64);
    return 0;
}

// 0x489210. cdecl, 0 stack argument(s), returns void (normalized to zero).
uint32_t function_489210(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x53c2c8, 0x523148, 0x489530, 1, 1);
    registerBinding(run, 0x53c2c8, 0x52c024, 0x489680, 1, 1);
    registerBinding(run, 0x53c2c8, 0x529a48, 0x489600, 0, 0, 0x4893b9, 0x489482);
    return 0;
}

// 0x489960. cdecl, 0 stack argument(s), returns void (normalized to zero).
uint32_t function_489960(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x523a5c, 0x52c03c))
        run.call(0x44c950, 0);
    registerBinding(run, 0x53c2f8, 0x5234ec, 0x48a2e0, 0, 0, 1, 1);
    registerBinding(run, 0x53c2f8, 0x52c030, 0x48a590, 0, 0, 0x489b66, 1);
    return 0;
}

// 0x48b1d0. cdecl, 0 stack argument(s), returns void (normalized to zero).
uint32_t function_48b1d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x523a5c, 0x52c47c))
        run.call(0x44c950, 0);
    registerBinding(run, 0x53c328, 0x5234ec, 0x48b4b0, 1, 1);
    registerBinding(run, 0x53c328, 0x523148, 0x48b730, 1, 1);
    registerBinding(run, 0x53c328, 0x524548, 0x48ba00, 0, 0, 0x48b3b9, 0x48b482);
    return 0;
}

// 0x48e6e0. cdecl, 0 stack argument(s), returns void (normalized to zero).
uint32_t function_48e6e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x53c9d0, 0x523604, 0x48ed70, 1, 1);
    registerBinding(run, 0x53c9d0, 0x527278, 0x48ee10, 1, 1);
    registerBinding(run, 0x53c9d0, 0x5235f8, 0x48eee0, 1, 1);
    registerBinding(run, 0x53c9d0, 0x5235f0, 0x48ef90, 1, 1);
    registerBinding(run, 0x53c9d0, 0x52726c, 0x48f040, 1, 1);
    return 0;
}

// 0x4924f0. cdecl, 0 stack argument(s), returns void (normalized to zero).
uint32_t function_4924f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x52670c, 0x52c900))
        run.call(0x43d5b0, 0);
    registerBinding(run, 0x53ca08, 0x523148, 0x492ec0, 1, 1);
    registerBinding(run, 0x53ca08, 0x52720c, 0x493030, 1, 1);
    registerBinding(run, 0x53ca08, 0x5234f4, 0x493550, 1, 1);
    registerBinding(run, 0x53ca08, 0x52c8f4, 0x493680, 1, 1);
    registerBinding(run, 0x53ca08, 0x52323c, 0x493200, 1, 1);
    registerBinding(run, 0x53ca08, 0x52c8e4, 0x493890, 1, 1);
    registerBinding(run, 0x53ca08, 0x52c8d8, 0x4939a0, 1, 1);
    return 0;
}

// 0x4940e0. cdecl, 0 stack argument(s), returns void (normalized to zero).
uint32_t function_4940e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x523a5c, 0x52caa4))
        run.call(0x44c950, 0);
    registerBinding(run, 0x53ca40, 0x5234ec, 0x494d40, 1, 1);
    registerBinding(run, 0x53ca40, 0x52ca98, 0x495940, 1, 1);
    registerBinding(run, 0x53ca40, 0x52b3a4, 0x4954f0, 1, 1);
    registerBinding(run, 0x53ca40, 0x52ca88, 0x495280, 1, 1);
    registerBinding(run, 0x53ca40, 0x52ca78, 0x495710, 1, 1);
    registerBinding(run, 0x53ca40, 0x526a38, 0x495ba0, 1, 1);
    return 0;
}

// 0x497240. cdecl, 0 stack argument(s), returns void (normalized to zero).
uint32_t function_497240(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x523a5c, 0x52d470))
        run.call(0x44c950, 0);
    registerBinding(run, 0x53ca70, 0x5234ec, 0x497750, 1, 1);
    registerBinding(run, 0x53ca70, 0x523148, 0x4979b0, 1, 1);
    registerBinding(run, 0x53ca70, 0x52d464, 0x497a50, 1, 1);
    registerBinding(run, 0x53ca70, 0x526a38, 0x483dc0, 0, 1, 1);
    return 0;
}

// 0x4982e0. cdecl, 0 stack argument(s), returns void (normalized to zero).
uint32_t function_4982e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x53caa0, 0x524548, 0x4985f0, 1, 1);
    registerBinding(run, 0x53caa0, 0x529a48, 0x4988f0, 1, 1);
    registerBinding(run, 0x53caa0, 0x523148, 0x42a680, 0, 0, 0x498489, 0x498552);
    return 0;
}

// 0x49f2e0. cdecl, 0 stack argument(s), returns void (normalized to zero).
uint32_t function_49f2e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x53ec00, 0x52ddbc, 0x49f7e0, 0, 0, 0x49f37b, 0x49f444);
    return 0;
}

// 0x4a0340. cdecl, 0 stack argument(s), returns void (normalized to zero).
uint32_t function_4a0340(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x523274, 0x52e0ec))
        run.call(0x40e390, 0);
    registerBinding(run, 0x53ec68, 0x5234ec, 0x4a0960, 1, 1);
    registerBinding(run, 0x53ec68, 0x52e0e0, 0x4a0ae0, 1, 1);
    registerBinding(run, 0x53ec68, 0x52e0d4, 0x4a0cf0, 1, 1);
    registerBinding(run, 0x53ec68, 0x52e0c4, 0x4a0f40, 1, 1);
    registerBinding(run, 0x53ec68, 0x52e0b4, 0x4a1020, 1, 1);
    registerBinding(run, 0x53ec68, 0x52e0a4, 0x4a10f0, 1, 1);
    registerBinding(run, 0x53ec68, 0x527d94, 0x4a1250, 1, 1);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x488b00:
        return function_488b00(run, receiver, arguments);
    case 0x489210:
        return function_489210(run, receiver, arguments);
    case 0x489960:
        return function_489960(run, receiver, arguments);
    case 0x48b1d0:
        return function_48b1d0(run, receiver, arguments);
    case 0x48e6e0:
        return function_48e6e0(run, receiver, arguments);
    case 0x4924f0:
        return function_4924f0(run, receiver, arguments);
    case 0x4940e0:
        return function_4940e0(run, receiver, arguments);
    case 0x497240:
        return function_497240(run, receiver, arguments);
    case 0x4982e0:
        return function_4982e0(run, receiver, arguments);
    case 0x49f2e0:
        return function_49f2e0(run, receiver, arguments);
    case 0x4a0340:
        return function_4a0340(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_logic_state_registrations_07_entry, owned, body)
