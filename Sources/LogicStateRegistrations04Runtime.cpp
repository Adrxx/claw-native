// Original logic state registrations group 4. Callback tokens are data.
#include "ClawRuntime.hpp"
#include "LogicStateRegistryCoreRuntime.h"

namespace {
using claw::Run;
using claw::state_registry::registerBinding;

bool equalNames(Run &run, uint32_t first, uint32_t second) {
    for (;;) {
        const auto byte = run.get8(first++);
        if (byte != run.get8(second++))
            return false;
        if (!byte)
            return true;
    }
}

int owned(uint32_t function) {
    switch (function) {
    case 0x446780:
    case 0x448970:
    case 0x448f50:
    case 0x4496a0:
    case 0x449e70:
    case 0x44c950:
    case 0x4544f0:
    case 0x455720:
    case 0x455c20:
    case 0x456400:
    case 0x456d30:
        return 0;
    default:
        return -1;
    }
}

// 0x446780. cdecl0 void; preserve literal order and physical index modes.
uint32_t function_446780(Run &run) {
    if (!equalNames(run, 0x527898, 0x5278a0))
        run.call(0x414310, 0);
    registerBinding(run, 0x537788, 0x5234ec, 0x446ca0, 0, 0, 0x1, 0x1);
    registerBinding(run, 0x537788, 0x52788c, 0x446eb0, 0, 0, 0x446986, 0x1);
    return 0;
}

// 0x448970. cdecl0 void; preserve literal order and physical index modes.
uint32_t function_448970(Run &run) {
    registerBinding(run, 0x5377b8, 0x523148, 0x448b50, 0, 0, 0x448a0b, 0x448ad4);
    return 0;
}

// 0x448f50. cdecl0 void; preserve literal order and physical index modes.
uint32_t function_448f50(Run &run) {
    registerBinding(run, 0x5377e8, 0x523604, 0x4492c0, 0, 0, 0x448feb, 0x4490b4);
    return 0;
}

// 0x4496a0. cdecl0 void; preserve literal order and physical index modes.
uint32_t function_4496a0(Run &run) {
    if (!equalNames(run, 0x527898, 0x527b24))
        run.call(0x414310, 0);
    registerBinding(run, 0x537818, 0x5234ec, 0x42a680, 0, 0, 0x44977b, 0x449844);
    return 0;
}

// 0x449e70. cdecl0 void; preserve literal order and physical index modes.
uint32_t function_449e70(Run &run) {
    if (!equalNames(run, 0x52670c, 0x527b98))
        run.call(0x43d5b0, 0);
    registerBinding(run, 0x537848, 0x527b90, 0x44aef0, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537848, 0x527b88, 0x44ade0, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537848, 0x527b7c, 0x44afd0, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537848, 0x527b70, 0x44bc50, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537848, 0x527b60, 0x44b6a0, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537848, 0x5272f0, 0x44b300, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537848, 0x5235f8, 0x44b7e0, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537848, 0x527b54, 0x44b960, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537848, 0x527b48, 0x44bb40, 1, 1, 0x0, 0x0);
    return 0;
}

// 0x44c950. cdecl0 void; preserve literal order and physical index modes.
uint32_t function_44c950(Run &run) {
    if (!equalNames(run, 0x52670c, 0x523a5c))
        run.call(0x43d5b0, 0);
    registerBinding(run, 0x537878, 0x5240e8, 0x44dd30, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537878, 0x5271cc, 0x44de50, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537878, 0x527dac, 0x44e510, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537878, 0x527da0, 0x44ea10, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537878, 0x527d94, 0x44ea60, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537878, 0x527d84, 0x44ec80, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537878, 0x527d78, 0x44ef70, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537878, 0x523148, 0x44f290, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537878, 0x523204, 0x44f490, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537878, 0x523210, 0x44f660, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537878, 0x5234ec, 0x44da20, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537878, 0x527d60, 0x44f800, 2, 1, 0x0, 0x0);
    return 0;
}

// 0x4544f0. cdecl0 void; preserve literal order and physical index modes.
uint32_t function_4544f0(Run &run) {
    if (!equalNames(run, 0x523274, 0x528460))
        run.call(0x40e390, 0);
    registerBinding(run, 0x537980, 0x527204, 0x455230, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537980, 0x528454, 0x4552d0, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537980, 0x5234ec, 0x454a10, 1, 1, 0x0, 0x0);
    registerBinding(run, 0x537980, 0x523148, 0x454c20, 0, 1, 0x1, 0x0);
    return 0;
}

// 0x455720. cdecl0 void; preserve literal order and physical index modes.
uint32_t function_455720(Run &run) {
    registerBinding(run, 0x5379d0, 0x523148, 0x455960, 0, 0, 0x4557bb, 0x455884);
    return 0;
}

// 0x455c20. cdecl0 void; preserve literal order and physical index modes.
uint32_t function_455c20(Run &run) {
    registerBinding(run, 0x537a00, 0x523604, 0x4560a0, 0, 0, 0x1, 0x1);
    registerBinding(run, 0x537a00, 0x528590, 0x456120, 0, 0, 0x455de8, 0x1);
    return 0;
}

// 0x456400. cdecl0 void; preserve literal order and physical index modes.
uint32_t function_456400(Run &run) {
    registerBinding(run, 0x537a30, 0x523604, 0x42a680, 0, 0, 0x1, 0x1);
    registerBinding(run, 0x537a30, 0x5285d0, 0x456a10, 0, 0, 0x4565c8, 0x1);
    return 0;
}

// 0x456d30. cdecl0 void; preserve literal order and physical index modes.
uint32_t function_456d30(Run &run) {
    if (!equalNames(run, 0x523714, 0x528608))
        run.call(0x408690, 0);
    registerBinding(run, 0x537a60, 0x524418, 0x457460, 0, 0, 0x1, 0x1);
    registerBinding(run, 0x537a60, 0x5236fc, 0x4574e0, 0, 0, 0x456f36, 0x1);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    switch (function) {
    case 0x446780:
        return function_446780(run);
    case 0x448970:
        return function_448970(run);
    case 0x448f50:
        return function_448f50(run);
    case 0x4496a0:
        return function_4496a0(run);
    case 0x449e70:
        return function_449e70(run);
    case 0x44c950:
        return function_44c950(run);
    case 0x4544f0:
        return function_4544f0(run);
    case 0x455720:
        return function_455720(run);
    case 0x455c20:
        return function_455c20(run);
    case 0x456400:
        return function_456400(run);
    case 0x456d30:
        return function_456d30(run);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_logic_state_registrations_04_entry, owned, body)
