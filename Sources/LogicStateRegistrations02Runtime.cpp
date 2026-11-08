// Level 1 logic registrations group 2
#include "ClawRuntime.hpp"
#include "LogicStateRegistryCoreRuntime.h"

namespace {

using claw::Run;
using claw::state_registry::registerBinding;

// Parent registration follows the original inline class-name comparison.
bool equalStrings(Run &run, uint32_t first, uint32_t second) {
    for (;;) {
        const auto byte = run.get8(first);
        if (byte != run.get8(second))
            return false;
        if (!byte)
            return true;
        ++first;
        ++second;
    }
}

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x412ae0:
        return 0;
    case 0x412f90:
        return 0;
    case 0x413770:
        return 0;
    case 0x413c90:
        return 0;
    case 0x414310:
        return 0;
    case 0x414f00:
        return 0;
    case 0x415590:
        return 0;
    case 0x421430:
        return 0;
    case 0x431560:
        return 0;
    case 0x431f00:
        return 0;
    case 0x4327b0:
        return 0;
    default:
        return -1;
    }
}

// 0x412ae0. cdecl, no arguments; original return is void.
uint32_t function_412ae0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x52419c, 0x5243ac))
        run.call(0x474060, 0);
    registerBinding(run, 0x534bc8, 0x5236fc, 0x412cb0, 0, 0, 0x412bbb, 0x412c84);
    return 0;
}

// 0x412f90. cdecl, no arguments; original return is void.
uint32_t function_412f90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x52419c, 0x524428))
        run.call(0x474060, 0);
    registerBinding(run, 0x534a88, 0x5236fc, 0x413280, 0, 0, 1, 1);
    registerBinding(run, 0x534a88, 0x524418, 0x413470, 0, 0, 0x413196, 1);
    return 0;
}

// 0x413770. cdecl, no arguments; original return is void.
uint32_t function_413770(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x52419c, 0x524488))
        run.call(0x474060, 0);
    registerBinding(run, 0x534b78, 0x5236fc, 0x413960, 0, 0, 0x41384b, 0x413914);
    return 0;
}

// 0x413c90. cdecl, no arguments; original return is void.
uint32_t function_413c90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x52419c, 0x5244ec))
        run.call(0x474060, 0);
    registerBinding(run, 0x534b50, 0x5236fc, 0x413280, 0, 0, 1, 1);
    registerBinding(run, 0x534b50, 0x524418, 0x413470, 0, 0, 0x413e96, 1);
    return 0;
}

// 0x414310. cdecl, no arguments; original return is void.
uint32_t function_414310(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x534bf8, 0x5234ec, 0x4145f0, 1, 1);
    registerBinding(run, 0x534bf8, 0x524548, 0x4146b0, 1, 1);
    registerBinding(run, 0x534bf8, 0x524538, 0x4148b0, 0, 0, 0x4144b9, 0x414582);
    return 0;
}

// 0x414f00. cdecl, no arguments; original return is void.
uint32_t function_414f00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x534c28, 0x523148, 0x415250, 0, 0, 0x414f9b, 0x415064);
    return 0;
}

// 0x415590. cdecl, no arguments; original return is void.
uint32_t function_415590(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x534c58, 0x523148, 0x4159b0, 0, 0, 1, 1);
    registerBinding(run, 0x534c58, 0x524604, 0x415a60, 0, 0, 0x415758, 1);
    return 0;
}

// 0x421430. cdecl, no arguments; original return is void.
uint32_t function_421430(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x523a5c, 0x524f28))
        run.call(0x44c950, 0);
    registerBinding(run, 0x534ed0, 0x5234ec, 0x421e00, 1, 1);
    registerBinding(run, 0x534ed0, 0x524f1c, 0x422050, 1, 1);
    registerBinding(run, 0x534ed0, 0x524f10, 0x4221b0, 0, 0, 0x421619, 0x4216e2);
    return 0;
}

// 0x431560. cdecl, no arguments; original return is void.
uint32_t function_431560(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x537278, 0x523604, 0x431b10, 0, 0, 1, 1);
    registerBinding(run, 0x537278, 0x526544, 0x431b70, 0, 0, 0x431728, 1);
    return 0;
}

// 0x431f00. cdecl, no arguments; original return is void.
uint32_t function_431f00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x523714, 0x5265fc))
        run.call(0x408690, 0);
    registerBinding(run, 0x5372a8, 0x524418, 0x4324e0, 0, 0, 0x431fdb, 0x4320a4);
    return 0;
}

// 0x4327b0. cdecl, no arguments; original return is void.
uint32_t function_4327b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x5372d8, 0x523604, 0x432c50, 0, 0, 1, 1);
    registerBinding(run, 0x5372d8, 0x52665c, 0x432d50, 0, 0, 0x432978, 1);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x412ae0:
        return function_412ae0(run, receiver, arguments);
    case 0x412f90:
        return function_412f90(run, receiver, arguments);
    case 0x413770:
        return function_413770(run, receiver, arguments);
    case 0x413c90:
        return function_413c90(run, receiver, arguments);
    case 0x414310:
        return function_414310(run, receiver, arguments);
    case 0x414f00:
        return function_414f00(run, receiver, arguments);
    case 0x415590:
        return function_415590(run, receiver, arguments);
    case 0x421430:
        return function_421430(run, receiver, arguments);
    case 0x431560:
        return function_431560(run, receiver, arguments);
    case 0x431f00:
        return function_431f00(run, receiver, arguments);
    case 0x4327b0:
        return function_4327b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_logic_state_registrations_02_entry, owned, body)
