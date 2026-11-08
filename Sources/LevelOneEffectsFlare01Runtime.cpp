// Level 1 Flare effect
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x457f00:
        return 1;
    case 0x458120:
        return 1;
    case 0x4581c0:
        return 0;
    case 0x458530:
        return 0;
    case 0x458570:
        return 0;
    case 0x4ce850:
        return 1;
    default:
        return -1;
    }
}

uint32_t function_458120(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_458530(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4ce850(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x457f00. cdecl, 1 stack argument(s), returns u32.
uint32_t function_457f00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // arguments[0] is the actor; +0x6c is its logic record, whose +0x18 holds the effect object and +0x1c the state.
    uint32_t actor = arguments[0];
    uint32_t record = run.get(actor + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state == 0x1d) {
        uint32_t object = run.get(record + 0x18);
        run.vcall(object, 0x20, {});
        return 1;
    }
    if (state == 0x1e) {
        uint32_t object = run.get(record + 0x18);
        run.vcall(object, 0x1c, {});
        return 1;
    }
    if (state == 0x3e8)
        return 1;
    if (state != 0) {
        run.call(0x4dc870, 0, {run.get(record + 0x18)});
        return 1;
    }
    run.put(record + 0x1c, 0x3e8);
    uint32_t object = run.call(0x4f63ec, 0, {0x4c});
    if (object) {
        function_458120(run, object, &actor);
        run.put(object + 0x0, 0x50e6fc);
        run.call(0x4c7970, run.get(object + 0x2c), {0x5286e8});
        uint32_t outer = run.get(object + 0x2c);
        uint32_t middle = run.get(outer + 0xc);
        uint32_t table = run.get(middle + 0x2c);
        uint32_t result = run.automatic(4);
        run.put(result, 0);
        run.call(0x4f6286, table + 0x10, {0x5286e8, result});
        run.put(object + 0x48, run.get(result));
    }
    run.vcall(object, 0x10, {});
    run.put(record + 0x18, object);
    return 1;
}

// 0x458120. thiscall, 1 stack argument(s), returns u32.
uint32_t function_458120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // this: +0x8/+0xc/+0x28/+0x2c actor, +0x10/+0x30 actor logic record, +0x1c/+0x20 state fields.
    uint32_t actor = arguments[0];
    run.put(receiver + 0x0, 0x50b064);
    run.put(receiver + 0x8, actor);
    run.put(receiver + 0xc, actor);
    run.put(receiver + 0x10, run.get(actor + 0x6c));
    run.put(receiver + 0x4, 0);
    run.call(0x4c7fa0, actor, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0xc), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x28, actor);
    run.put(receiver + 0x2c, actor);
    run.put(receiver + 0x30, run.get(actor + 0x6c));
    run.put(receiver + 0x0, 0x50e74c);
    return receiver;
}

// 0x4581c0. thiscall, 0 stack argument(s), returns void.
uint32_t function_4581c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // this+0x2c actor; +0x170 its attached object, +0xd0 flag, +0x188 sub-object, +0x190 value; this+0x48 saved id.
    uint32_t actor = run.get(receiver + 0x2c);
    uint32_t attached = run.get(actor + 0x170);
    run.put(actor + 0xd0, 1);
    if (attached) {
        run.call(0x4ce7b0, attached, {2});
        uint32_t global = run.get(0x5371fc);
        uint32_t value = run.get(run.get(global + 0x2c) + 0x768);
        function_4ce850(run, attached, &value);
    }
    actor = run.get(receiver + 0x2c);
    uint32_t id = run.get(receiver + 0x48);
    run.put(receiver + 0x34, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {id});
    function_458530(run, receiver, arguments);
    return 0;
}

// 0x458530. thiscall, 0 stack argument(s), returns u32.
uint32_t function_458530(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // this+0x10 logic record (+0x1c state), this+0x24 saved state, this+0x2c actor, this+0x48 id.
    uint32_t record = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(record + 0x1c));
    uint32_t idle = run.call(0x4dba00, 0x537668, {0x523148});
    record = run.get(receiver + 0x10);
    run.put(record + 0x1c, idle);
    uint32_t actor = run.get(receiver + 0x2c);
    uint32_t id = run.get(receiver + 0x48);
    run.put(receiver + 0x34, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {id});
    return 0;
}

// 0x458570. thiscall, 0 stack argument(s), returns u32.
uint32_t function_458570(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t actor = run.get(receiver + 0x2c);
    run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    return 0;
}

// 0x4ce850. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4ce850(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // this: +0x14 item table, +0x64 first index, +0x68 last index; item +0x30 holds a record whose +0x1c is set.
    uint32_t value = arguments[0];
    if (!value)
        return 0;
    uint32_t index = run.get(receiver + 0x64);
    uint32_t last = run.get(receiver + 0x68);
    uint32_t count = 0;
    while (s32(index) <= s32(last)) {
        uint32_t item;
        if (s32(index) < s32(run.get(receiver + 0x64)) || s32(index) > s32(last))
            item = 0;
        else
            item = run.get(run.get(receiver + 0x14) + index * 4);
        if (item) {
            uint32_t record = run.get(item + 0x30);
            if (record) {
                run.put(record + 0x1c, value);
                count = count + 1;
            }
        }
        last = run.get(receiver + 0x68);
        index = index + 1;
    }
    return count;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x457f00:
        return function_457f00(run, receiver, arguments);
    case 0x458120:
        return function_458120(run, receiver, arguments);
    case 0x4581c0:
        return function_4581c0(run, receiver, arguments);
    case 0x458530:
        return function_458530(run, receiver, arguments);
    case 0x458570:
        return function_458570(run, receiver, arguments);
    case 0x4ce850:
        return function_4ce850(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_effects_flare_01_entry, owned, body)
