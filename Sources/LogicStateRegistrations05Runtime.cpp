// Original logic state registrations group 5
// Registration wrappers preserve original order and callback identities.
#include "ClawRuntime.hpp"
#include "LogicStateRegistryCoreRuntime.h"

namespace {

using claw::Run;
using claw::state_registry::registerBinding;

// The original parent check compares guest strings, including their terminator.
bool equal(Run &run, uint32_t first, uint32_t second) {
    for (;;) {
        const auto byte = run.get8(first++);
        if (byte != run.get8(second++))
            return false;
        if (!byte)
            return true;
    }
}

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x457860:
        return 0;
    case 0x4583a0:
        return 0;
    case 0x4588b0:
        return 0;
    case 0x45a520:
        return 0;
    case 0x460820:
        return 0;
    case 0x462c00:
        return 0;
    case 0x463c50:
        return 0;
    case 0x4652c0:
        return 0;
    case 0x465ec0:
        return 0;
    case 0x468be0:
        return 0;
    case 0x46f7b0:
        return 0;
    default:
        return -1;
    }
}

// 0x457860. cdecl, 0 stack argument(s), void result normalized to zero.
uint32_t function_457860(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x537a90, 0x523604, 0x457d60, 0, 0, 1, 1);
    registerBinding(run, 0x537a90, 0x5235f8, 0x457de0, 0, 0, 0x457a28, 1);
    return 0;
}

// 0x4583a0. cdecl, 0 stack argument(s), void result normalized to zero.
uint32_t function_4583a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x537ac0, 0x523148, 0x458570, 0, 0, 0x45843b, 0x458504);
    return 0;
}

// 0x4588b0. cdecl, 0 stack argument(s), void result normalized to zero.
uint32_t function_4588b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x523274, 0x52876c))
        run.call(0x40e390, 0);
    registerBinding(run, 0x537af0, 0x523268, 0x459440, 1, 1);
    registerBinding(run, 0x537af0, 0x5234ec, 0x4596a0, 1, 1);
    registerBinding(run, 0x537af0, 0x528758, 0x4599b0, 1, 1);
    registerBinding(run, 0x537af0, 0x523148, 0x459b70, 1, 1);
    registerBinding(run, 0x537af0, 0x52874c, 0x47f600, 1, 1);
    registerBinding(run, 0x537af0, 0x523210, 0x47f680, 1, 1);
    registerBinding(run, 0x537af0, 0x523204, 0x47f6b0, 1, 1);
    registerBinding(run, 0x537af0, 0x524548, 0x45a0b0, 1, 1);
    return 0;
}

// 0x45a520. cdecl, 0 stack argument(s), void result normalized to zero.
uint32_t function_45a520(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x537b20, 0x523604, 0x45a980, 1, 1);
    registerBinding(run, 0x537b20, 0x528a14, 0x45aae0, 1, 1);
    registerBinding(run, 0x537b20, 0x528a08, 0x45aa40, 0, 0, 0x45a6c9, 0x45a792);
    return 0;
}

// 0x460820. cdecl, 0 stack argument(s), void result normalized to zero.
uint32_t function_460820(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x523a5c, 0x5294d4))
        run.call(0x44c950, 0);
    registerBinding(run, 0x537b68, 0x523148, 0x460ea0, 1, 1);
    registerBinding(run, 0x537b68, 0x5234ec, 0x460c50, 1, 1);
    registerBinding(run, 0x537b68, 0x524548, 0x4614c0, 1, 1);
    registerBinding(run, 0x537b68, 0x526a38, 0x483dc0, 0, 1, 1);
    return 0;
}

// 0x462c00. cdecl, 0 stack argument(s), void result normalized to zero.
uint32_t function_462c00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x523a5c, 0x529864))
        run.call(0x44c950, 0);
    registerBinding(run, 0x537ba0, 0x5234ec, 0x463020, 0, 0, 1, 1);
    registerBinding(run, 0x537ba0, 0x523148, 0x4631e0, 0, 0, 0x462e06, 1);
    return 0;
}

// 0x463c50. cdecl, 0 stack argument(s), void result normalized to zero.
uint32_t function_463c50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x523274, 0x529a50))
        run.call(0x40e390, 0);
    registerBinding(run, 0x537bd0, 0x5234ec, 0x464930, 1, 1);
    registerBinding(run, 0x537bd0, 0x523148, 0x464770, 1, 1);
    registerBinding(run, 0x537bd0, 0x5234f4, 0x464b90, 1, 1);
    registerBinding(run, 0x537bd0, 0x529a48, 0x42a680, 1, 1);
    registerBinding(run, 0x537bd0, 0x529a38, 0x464cc0, 1, 1);
    registerBinding(run, 0x537bd0, 0x529a24, 0x4645c0, 1, 1);
    return 0;
}

// 0x4652c0. cdecl, 0 stack argument(s), void result normalized to zero.
uint32_t function_4652c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x537c00, 0x523148, 0x458570, 0, 0, 0x46535b, 0x465424);
    return 0;
}

// 0x465ec0. cdecl, 0 stack argument(s), void result normalized to zero.
uint32_t function_465ec0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x52670c, 0x529c14))
        run.call(0x43d5b0, 0);
    registerBinding(run, 0x537c30, 0x523148, 0x4664d0, 1, 1);
    registerBinding(run, 0x537c30, 0x529c08, 0x466790, 1, 1);
    registerBinding(run, 0x537c30, 0x529bf8, 0x466e40, 1, 1);
    registerBinding(run, 0x537c30, 0x52720c, 0x467280, 1, 1);
    registerBinding(run, 0x537c30, 0x529be8, 0x467470, 1, 1);
    registerBinding(run, 0x537c30, 0x529bd8, 0x467700, 1, 1);
    registerBinding(run, 0x537c30, 0x529bc8, 0x4679a0, 1, 1);
    registerBinding(run, 0x537c30, 0x529bb8, 0x467bf0, 1, 1);
    registerBinding(run, 0x537c30, 0x5234f4, 0x43f450, 1, 1);
    return 0;
}

// 0x468be0. cdecl, 0 stack argument(s), void result normalized to zero.
uint32_t function_468be0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x523a5c, 0x529c8c))
        run.call(0x44c950, 0);
    registerBinding(run, 0x537c60, 0x5234ec, 0x469570, 1, 1);
    registerBinding(run, 0x537c60, 0x529c7c, 0x469e20, 1, 1);
    registerBinding(run, 0x537c60, 0x529c6c, 0x46a1c0, 1, 1);
    registerBinding(run, 0x537c60, 0x524548, 0x469a40, 0, 1, 1);
    return 0;
}

// 0x46f7b0. cdecl, 0 stack argument(s), void result normalized to zero.
uint32_t function_46f7b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equal(run, 0x52670c, 0x52a184))
        run.call(0x43d5b0, 0);
    registerBinding(run, 0x537ea0, 0x524418, 0x46fa90, 1, 1);
    registerBinding(run, 0x537ea0, 0x5271cc, 0x46fc20, 1, 1);
    registerBinding(run, 0x537ea0, 0x5271b4, 0x46fc20, 0, 0, 0x46f999, 0x46fa62);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x457860:
        return function_457860(run, receiver, arguments);
    case 0x4583a0:
        return function_4583a0(run, receiver, arguments);
    case 0x4588b0:
        return function_4588b0(run, receiver, arguments);
    case 0x45a520:
        return function_45a520(run, receiver, arguments);
    case 0x460820:
        return function_460820(run, receiver, arguments);
    case 0x462c00:
        return function_462c00(run, receiver, arguments);
    case 0x463c50:
        return function_463c50(run, receiver, arguments);
    case 0x4652c0:
        return function_4652c0(run, receiver, arguments);
    case 0x465ec0:
        return function_465ec0(run, receiver, arguments);
    case 0x468be0:
        return function_468be0(run, receiver, arguments);
    case 0x46f7b0:
        return function_46f7b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_logic_state_registrations_05_entry, owned, body)
