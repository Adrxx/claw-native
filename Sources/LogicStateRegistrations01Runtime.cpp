// Level 1 logic registrations group 1
#include "ClawRuntime.hpp"
#include "LogicStateRegistryCoreRuntime.h"

namespace {

using claw::Run;
using claw::state_registry::registerBinding;

// Parent registration is conditional on the inline class-name comparison.
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
    case 0x4092d0:
        return 0;
    case 0x40a150:
        return 0;
    case 0x40e390:
        return 0;
    case 0x40ed00:
        return 0;
    case 0x40fc50:
        return 0;
    case 0x410b90:
        return 0;
    case 0x411140:
        return 0;
    case 0x4115f0:
        return 0;
    case 0x411aa0:
        return 0;
    case 0x411f80:
        return 0;
    case 0x412570:
        return 0;
    default:
        return -1;
    }
}

// 0x4092d0. cdecl, no arguments; original return is void.
uint32_t function_4092d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x534948, 0x523604, 0x4096b0, 0, 0, 0x40936b, 0x409434);
    return 0;
}

// 0x40a150. cdecl, no arguments; original return is void.
uint32_t function_40a150(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x523a5c, 0x523a68))
        run.call(0x44c950, 0);
    registerBinding(run, 0x534978, 0x523148, 0x435130, 1, 1);
    registerBinding(run, 0x534978, 0x5234ec, 0x40a490, 1, 1);
    registerBinding(run, 0x534978, 0x523a50, 0x40a690, 1, 1);
    registerBinding(run, 0x534978, 0x523a48, 0x40a7f0, 1, 1);
    registerBinding(run, 0x534978, 0x523a3c, 0x40aa70, 1, 1);
    return 0;
}

// 0x40e390. cdecl, no arguments; original return is void.
uint32_t function_40e390(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x523a5c, 0x523274))
        run.call(0x44c950, 0);
    registerBinding(run, 0x5349b8, 0x523268, 0x40e580, 0, 0, 0x40e46b, 0x40e534);
    return 0;
}

// 0x40ed00. cdecl, no arguments; original return is void.
uint32_t function_40ed00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x5349e0, 0x5240e8, 0x40f200, 1, 1);
    registerBinding(run, 0x5349e0, 0x5236fc, 0x40f010, 1, 1);
    registerBinding(run, 0x5349e0, 0x5234f4, 0x40f400, 0, 0, 0x40eea9, 0x40ef72);
    return 0;
}

// 0x40fc50. cdecl, no arguments; original return is void.
uint32_t function_40fc50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    registerBinding(run, 0x534a10, 0x523148, 0x40fde0, 0, 0, 0x40fceb, 0x40fdb4);
    return 0;
}

// 0x410b90. cdecl, no arguments; original return is void.
uint32_t function_410b90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x52419c, 0x5241a4))
        run.call(0x474060, 0);
    registerBinding(run, 0x534ab0, 0x5236fc, 0x410d60, 0, 0, 0x410c6b, 0x410d34);
    return 0;
}

// 0x411140. cdecl, no arguments; original return is void.
uint32_t function_411140(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x52419c, 0x524200))
        run.call(0x474060, 0);
    registerBinding(run, 0x534ba0, 0x5236fc, 0x411310, 0, 0, 0x41121b, 0x4112e4);
    return 0;
}

// 0x4115f0. cdecl, no arguments; original return is void.
uint32_t function_4115f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x52419c, 0x524264))
        run.call(0x474060, 0);
    registerBinding(run, 0x534a38, 0x5236fc, 0x4117c0, 0, 0, 0x4116cb, 0x411794);
    return 0;
}

// 0x411aa0. cdecl, no arguments; original return is void.
uint32_t function_411aa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x52419c, 0x5242c0))
        run.call(0x474060, 0);
    registerBinding(run, 0x534b00, 0x5236fc, 0x411c70, 0, 0, 0x411b7b, 0x411c44);
    return 0;
}

// 0x411f80. cdecl, no arguments; original return is void.
uint32_t function_411f80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x52419c, 0x524308))
        run.call(0x474060, 0);
    registerBinding(run, 0x534ad8, 0x5236fc, 0x412150, 0, 0, 0x41205b, 0x412124);
    return 0;
}

// 0x412570. cdecl, no arguments; original return is void.
uint32_t function_412570(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!equalStrings(run, 0x52419c, 0x524354))
        run.call(0x474060, 0);
    registerBinding(run, 0x534b28, 0x5236fc, 0x412740, 0, 0, 0x41264b, 0x412714);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4092d0:
        return function_4092d0(run, receiver, arguments);
    case 0x40a150:
        return function_40a150(run, receiver, arguments);
    case 0x40e390:
        return function_40e390(run, receiver, arguments);
    case 0x40ed00:
        return function_40ed00(run, receiver, arguments);
    case 0x40fc50:
        return function_40fc50(run, receiver, arguments);
    case 0x410b90:
        return function_410b90(run, receiver, arguments);
    case 0x411140:
        return function_411140(run, receiver, arguments);
    case 0x4115f0:
        return function_4115f0(run, receiver, arguments);
    case 0x411aa0:
        return function_411aa0(run, receiver, arguments);
    case 0x411f80:
        return function_411f80(run, receiver, arguments);
    case 0x412570:
        return function_412570(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_logic_state_registrations_01_entry, owned, body)
