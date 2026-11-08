// Level 12 Aquatis crack closure, recovered from original packet instructions.
#include "ClawRuntime.hpp"
namespace {
using claw::Run;
using claw::s32;
int owned(uint32_t function) {
    switch (function) {
    case 0x406520:
    case 0x4068f0:
        return 1;
    case 0x406af0:
    case 0x406b10:
    case 0x406b50:
    case 0x406c40:
    case 0x406cb0:
        return 0;
    default:
        return -1;
    }
}
// Table fields: +0x08/+0x0c signed bounds, +0x10 entries, +0x14 fallback,
// +0x18 stride, +0x1c temporary strings, +0x20 temporary count.
uint32_t lookup(Run &run, uint32_t table, uint32_t key) {
    uint32_t lower = run.get(table + 0x08);
    run.put(table + 0x20, 0);
    if (s32(key) < s32(lower) || s32(key) > s32(run.get(table + 0x0c))) {
        uint32_t found = run.call(0x4db6e0, table, {key, 0});
        if (!found) {
            uint32_t file = run.get(0x544b4c);
            uint32_t line = run.call(0x4db5f0, 0);
            uint32_t reporter = run.get(table + 0x04);
            run.put(0x544b14, line);
            run.call(0x4db4d0, reporter, {table, file, 0x0c});
            return run.get(table + 0x14);
        }
        lower = run.get(table + 0x08);
    }
    return (key - lower) * run.get(table + 0x18) + run.get(table + 0x10);
}
// 0x406520. Dispatch the indexed logic, or inspect the object's RTTI.
uint32_t function_406520(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t key = arguments[0];
    uint32_t entry = lookup(run, 0x534888, key);
    if (run.get(entry)) {
        entry = lookup(run, 0x534888, key);
        run.call(run.get(entry), receiver);
    } else {
        run.call(0x4a36f0, 0, {receiver});
    }
    return 0;
}
// 0x406af0. Clear the Aquatis interrupt flag and advance logic.
uint32_t function_406af0(Run &run, uint32_t receiver) {
    uint32_t boss = run.get(0x534874);
    if (boss) {
        run.put(boss + 0x4ec, run.get(boss + 0x4ec) & 0xfffffffd);
    }
    run.call(0x458530, receiver);
    return 0;
}
// 0x4068f0. Construct the crack logic and acquire its effect resources.
// Object fields: +0x08/+0x0c and +0x28/+0x2c owner; +0x10/+0x30 state;
// +0x48 glow; +0x4c through +0x5c earthquake effects; +0x60/+0x64 and
// +0x68/+0x6c timer start/duration pairs.
uint32_t function_4068f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t owner = arguments[0];
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x08, owner);
    run.put(receiver + 0x0c, owner);
    run.put(receiver + 0x10, run.get(owner + 0x6c));
    run.put(receiver + 0x04, 0);
    run.call(0x4c7fa0, owner, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0x0c), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x28, owner);
    run.put(receiver + 0x2c, owner);
    run.put(receiver + 0x30, run.get(owner + 0x6c));
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x64, 0);
    run.put(receiver + 0x68, 0);
    run.put(receiver + 0x6c, 0);
    run.put(receiver, 0x50b21c);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x523598});
    uint32_t output = run.automatic(0x04);
    run.put(output, 0);
    uint32_t resources = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x2c);
    run.call(0x4f6286, resources + 0x10, {0x523588, output});
    run.put(receiver + 0x48, run.get(output));
    run.put(output, 0);
    resources = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x28);
    run.call(0x4f6286, resources + 0x10, {0x523574, output});
    uint32_t effect = run.get(output);
    run.put(output, 0);
    run.put(receiver + 0x4c, effect);
    resources = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x28);
    run.call(0x4f6286, resources + 0x10, {0x523560, output});
    effect = run.get(output);
    run.put(output, 0);
    run.put(receiver + 0x50, effect);
    resources = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x28);
    run.call(0x4f6286, resources + 0x10, {0x52354c, output});
    effect = run.get(output);
    run.put(output, 0);
    run.put(receiver + 0x54, effect);
    resources = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x28);
    run.call(0x4f6286, resources + 0x10, {0x523538, output});
    run.put(receiver + 0x58, run.get(output));
    resources = run.get(run.get(run.get(receiver + 0x2c) + 0x0c) + 0x28);
    uint32_t finalEffect = run.call(0x4061b0, resources, {0x523524});
    run.put(receiver + 0x5c, finalEffect);
    run.put(run.get(receiver + 0x2c) + 0xd0, 4);
    run.put(run.get(receiver + 0x2c) + 0xd4, 0x1000000);
    uint32_t object = run.get(receiver + 0x2c);
    run.put(object + 0x138, 0x80000000);
    run.put(object + 0x13c, 0);
    run.put(object + 0x140, 0);
    run.put(object + 0x144, 0);
    run.call(0x406240, run.get(receiver + 0x2c));
    object = run.get(receiver + 0x0c);
    run.put(object + 0x128, run.get(object + 0x128) + 0x19);
    object = run.get(receiver + 0x0c);
    run.put(object + 0x130, run.get(object + 0x130) + 0x64);
    function_406af0(run, receiver);
    return receiver;
}
// 0x406b10. Animate unless interrupted.
uint32_t function_406b10(Run &run, uint32_t receiver) {
    uint32_t boss = run.get(0x534874);
    if (boss && (run.get8(boss + 0x4ec) & 2)) {
        function_406af0(run, receiver);
        return 0;
    }
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    return 0;
}
// 0x406b50. Start the earthquake delay if Aquatis is ready.
uint32_t function_406b50(Run &run, uint32_t receiver) {
    uint32_t boss = run.get(0x534874);
    if (!boss || !run.get(boss + 0x4b8) || run.get(boss + 0x4b4) || run.get(boss + 0x4c4) || run.get(boss + 0x4bc)) {
        run.call(0x458530, receiver);
        return 0;
    }
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t delay = run.call(0x4dba00, 0x537668, {0x5234fc});
    run.put(run.get(receiver + 0x10) + 0x1c, delay);
    uint32_t random = run.call(0x4a3050, 0);
    uint32_t index = uint32_t(s32(random) % 5);
    uint32_t effect = run.get(receiver + index * 4 + 0x4c);
    if (effect && run.get(0x532c0c)) {
        uint32_t savedStack = run.stackPointer;
        // PUSH ESI, four argument words, then the CALL return word.
        run.stackPointer = run.frame - 0x18;
        run.call(0x4b45f0, run.get(effect + 0x10), {run.get(0x532c10), 0, 0, 0});
        run.stackPointer = savedStack;
    }
    run.put(receiver + 0x64, 4000);
    run.put(receiver + 0x60, run.get(0x537210));
    run.call(0x486e70, 0, {4000});
    run.put(receiver + 0x6c, 6000);
    run.put(receiver + 0x68, run.get(0x537210));
    run.put(run.get(0x534874) + 0x4c0, 1);
    return 0;
}
// 0x406c40. Animate the delay and transition after its unsigned timer.
uint32_t function_406c40(Run &run, uint32_t receiver) {
    uint32_t boss = run.get(0x534874);
    if (!boss) {
        return 0;
    }
    if (run.get8(boss + 0x4ec) & 2) {
        function_406af0(run, receiver);
        return 0;
    }
    run.call(0x4c82a0, run.get(receiver + 0x2c) + 0x188, {run.get(0x5430c4)});
    if (run.get(0x537210) - run.get(receiver + 0x60) >= run.get(receiver + 0x64)) {
        run.put(run.get(0x534874) + 0x4c0, 0);
        run.put(run.get(0x534874) + 0x4bc, 1);
        run.call(0x458530, receiver);
    }
    return 0;
}
// 0x406cb0. Restart the earthquake after a non-delay state times out.
uint32_t function_406cb0(Run &run, uint32_t receiver) {
    uint32_t key = run.get(run.get(receiver + 0x10) + 0x1c);
    uint32_t entry = lookup(run, 0x537698, key);
    uint32_t count = run.get(0x5376b8);
    uint32_t strings = run.get(0x5376b4);
    while (count) {
        if (strings) {
            run.call(0x4f6439, strings);
        }
        strings += 4;
        --count;
    }
    uint32_t compare = run.call(0x4a3810, 0, {run.get(entry), 0x5234fc});
    if (compare && run.get(0x537210) - run.get(receiver + 0x68) >= run.get(receiver + 0x6c)) {
        uint32_t savedFrame = run.frame;
        // PUSH EBX/EBP/ESI/EDI, then the owned CALL return word.
        run.frame -= 0x14;
        function_406b50(run, receiver);
        run.frame = savedFrame;
    }
    return 0;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x406520:
        return function_406520(run, receiver, arguments);
    case 0x4068f0:
        return function_4068f0(run, receiver, arguments);
    case 0x406af0:
        return function_406af0(run, receiver);
    case 0x406b10:
        return function_406b10(run, receiver);
    case 0x406b50:
        return function_406b50(run, receiver);
    case 0x406c40:
        return function_406c40(run, receiver);
    case 0x406cb0:
        return function_406cb0(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace
CLAW_MODULE_ENTRY(claw_level_twelve_aquatis_crack_01_entry, owned, body)
