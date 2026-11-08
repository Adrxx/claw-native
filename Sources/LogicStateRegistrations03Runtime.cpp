// Original logic state registrations, group 3. Literals and callback tokens
// retain their original identities and binding order.
#include "ClawRuntime.hpp"
#include "LogicStateRegistryCoreRuntime.h"

namespace {
using claw::Run;
using claw::s32;
using claw::state_registry::registerBinding;

int owned(uint32_t function) {
    switch (function) {
    case 0x433be0:
    case 0x434a60:
    case 0x438210:
    case 0x43ae30:
    case 0x43cee0:
    case 0x43d5b0:
    case 0x4413f0:
    case 0x441e10:
    case 0x4434c0:
    case 0x445c00:
        return 0;
    case 0x441030:
        return 1;
    default:
        return -1;
    }
}

bool equal(Run &run, uint32_t first, uint32_t second) {
    for (;;) {
        const auto byte = run.get8(first++);
        if (byte != run.get8(second++))
            return false;
        if (!byte)
            return true;
    }
}

// 0x441030. Indexed array +08/+0c signed bounds, +10 storage, +14
// fallback cell, +18 element width, +20 count of newly exposed elements.
uint32_t index(Run &run, uint32_t table, uint32_t key) {
    run.put(table + 0x20, 0);
    if (s32(key) < run.gets(table + 0x08) || s32(key) > run.gets(table + 0x0c)) {
        if (!claw::state_registry::grow(run, table, key, 0)) {
            const auto message = run.get(0x544b4c);
            ClawCompilerContext context{};
            context.size = sizeof(context);
            context.version = CLAW_CONTEXT_VERSION;
            context.inputMask = 0x5c1;
            context.outputMask = 0x5c1;
            context.esp = run.automatic(-0x80);
            context.eip = 0x4db5f0;
            context.continuation = 0x44108b;
            context.fsHead = 0xffffffff;
            run.put(context.esp, 0x44108b);
            const auto location = run.context_call(0x4db5f0, context);
            run.put(0x544b14, location);
            run.call(0x4db4d0, run.get(table + 0x04), {table, message, 0x0c});
            return run.get(table + 0x14);
        }
    }
    return (key - run.get(table + 0x08)) * run.get(table + 0x18) + run.get(table + 0x10);
}

// 0x43d5b0. CEnemy base bindings; its final name lookup uses 406020.
void enemy(Run &run) {
    const uint32_t bindings[][2] = {
        {0x5236fc, 0x43edd0},
        {0x52720c, 0x43f030},
        {0x5234f4, 0x43f450},
        {0x527204, 0x43f6e0},
        {0x5271f4, 0x43fd10},
        {0x5271e4, 0x43fdc0},
        {0x5240e8, 0x43ff60},
        {0x524418, 0x440070},
        {0x5271d8, 0x4405b0},
        {0x5271cc, 0x440260},
        {0x5271c0, 0x43f540},
        {0x5271b4, 0x440a50},
        {0x5271a8, 0x43f980},
        {0x527198, 0x43fc20},
        {0x527188, 0x440be0},
        {0x52717c, 0x440d50},
        {0x527170, 0x440870},
        {0x5234ec, 0x4bb030}
    };
    for (const auto &binding : bindings)
        registerBinding(run, 0x537638, binding[0], binding[1], 0, 0, 0x44108b, 0x44108b);
    registerBinding(run, 0x537638, 0x523148, 0x4bb030, 2, 0, 0, 0x44108b);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    // 0x433be0. CCrate inherits CEnemy before overriding damage/fall.
    case 0x433be0:
        if (!equal(run, 0x52670c, 0x526714))
            enemy(run);
        registerBinding(run, 0x537308, 0x526700, 0x434180, 0, 0, 1, 1);
        registerBinding(run, 0x537308, 0x5266f8, 0x434170, 0, 0, 0x433de6, 1);
        return 0;
    // 0x434a60. CCrazyHook inherits CHumanEnemy.
    case 0x434a60:
        if (!equal(run, 0x523a5c, 0x526a44))
            run.call(0x44c950, 0);
        registerBinding(run, 0x537338, 0x523148, 0x435130, 0, 0, 0x44108b, 0x44108b);
        registerBinding(run, 0x537338, 0x5234ec, 0x434eb0, 0, 0, 0x44108b, 0x44108b);
        registerBinding(run, 0x537338, 0x526a38, 0x483dc0, 0, 0, 0x44108b, 0x44108b);
        registerBinding(run, 0x537338, 0x526a2c, 0x435600, 0, 0, 1, 0x44108b);
        return 0;
    // 0x438210. CCutThroat inherits CHumanEnemy.
    case 0x438210:
        if (!equal(run, 0x523a5c, 0x526d44))
            run.call(0x44c950, 0);
        registerBinding(run, 0x537598, 0x5234ec, 0x4386d0, 0, 0, 0x44108b, 0x44108b);
        registerBinding(run, 0x537598, 0x523148, 0x4385b0, 0, 0, 0x44108b, 0x44108b);
        registerBinding(run, 0x537598, 0x524548, 0x438a90, 0, 0, 0x4383f9, 0x4384c2);
        return 0;
    // 0x43ae30. CDynamite inherits CArchingProjectile.
    case 0x43ae30:
        if (!equal(run, 0x523714, 0x526f8c))
            run.call(0x408690, 0);
        registerBinding(run, 0x5375d8, 0x524418, 0x43b290, 0, 0, 1, 1);
        registerBinding(run, 0x5375d8, 0x5236fc, 0x43b320, 0, 0, 0x43b036, 1);
        return 0;
    // 0x43cee0.
    case 0x43cee0:
        registerBinding(run, 0x537608, 0x523148, 0x43d070, 0, 0, 0x43cf7b, 0x43d044);
        return 0;
    case 0x43d5b0:
        enemy(run);
        return 0;
    case 0x441030:
        return index(run, receiver, arguments[0]);
    // 0x4413f0.
    case 0x4413f0: {
        const uint32_t bindings[][2] = {
            {0x523604, 0x4419b0},
            {0x527278, 0x441a20},
            {0x5235f8, 0x441ae0},
            {0x5235f0, 0x441b00},
            {0x52726c, 0x441b90}
        };
        for (const auto &binding : bindings)
            registerBinding(run, 0x5376c8, binding[0], binding[1], 0, 0, 0x44108b, 0x44108b);
        return 0;
    }
    // 0x441e10.
    case 0x441e10:
        if (!equal(run, 0x52670c, 0x5272fc))
            enemy(run);
        registerBinding(run, 0x5376f8, 0x523604, 0x442640, 0, 0, 0x44108b, 0x44108b);
        registerBinding(run, 0x5376f8, 0x5272f0, 0x442d80, 0, 0, 0x44108b, 0x44108b);
        registerBinding(run, 0x5376f8, 0x5272e0, 0x442b00, 0, 0, 0x44108b, 0x44108b);
        registerBinding(run, 0x5376f8, 0x5272d0, 0x442f70, 0, 0, 1, 0x44108b);
        return 0;
    // 0x4434c0. CGabriel inherits the enemy startup behavior.
    case 0x4434c0: {
        if (!equal(run, 0x523274, 0x527480))
            run.call(0x40e390, 0);
        const uint32_t bindings[][2] = {
            {0x523268, 0x4441b0},
            {0x523148, 0x4442c0},
            {0x52746c, 0x4445d0},
            {0x52745c, 0x444760},
            {0x52744c, 0x444960},
            {0x52743c, 0x444b70},
            {0x527430, 0x444d00},
            {0x5231f8, 0x445090},
            {0x527424, 0x4455b0},
            {0x527418, 0x445660}
        };
        for (const auto &binding : bindings)
            registerBinding(run, 0x537728, binding[0], binding[1], 0, 0, 0x44108b, 0x44108b);
        registerBinding(run, 0x537728, 0x52740c, 0x445720, 2, 0, 0, 0x44108b);
        return 0;
    }
    // 0x445c00. CGabrielBomb inherits CArchingProjectile.
    case 0x445c00:
        if (!equal(run, 0x523714, 0x527798))
            run.call(0x408690, 0);
        registerBinding(run, 0x537758, 0x524418, 0x4463f0, 0, 0, 1, 1);
        registerBinding(run, 0x537758, 0x5236fc, 0x446490, 0, 0, 0x445e06, 1);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_logic_state_registrations_03_entry, owned, body)
