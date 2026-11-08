// v1.3 gameplay attack setup, damage, inventory state and attack bounds.
// Keep signed, byte, nested and read-modify-write transports literal: their
// original width, access order and legacy mutation sites remain visible.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {
using claw::Run;
using claw::s32;
using namespace claw::recovered::v13;

int owned(uint32_t function) {
    return function == 0x41f270 ? 4 : -1;
}

// Attack rectangle is object +0x154..0x160; damage is +0x120.
void rectangle(Run &run, uint32_t object, uint32_t left, uint32_t top, uint32_t right, uint32_t bottom, uint32_t damage) {
    AttackActorFields objectFields{run, object};
    objectFields.attackLeft(left);
    objectFields.attackTop(top);
    objectFields.attackRight(right);
    objectFields.attackBottom(bottom);
    objectFields.damage(damage);
}

void difficultyDamage(Run &run, uint32_t object, uint32_t powerDamage, uint32_t easyDamage) {
    AttackActorFields objectFields{run, object};
    if (run.get(0x532d34) == 0x26bc)
        objectFields.damage(powerDamage);
    if (run.get(0x535990) != 0)
        objectFields.damage(easyDamage);
}

// 0x41f270, four cdecl arguments: object, logic, attack state, attack id.
uint32_t setupAttackAndBounds(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    AttackActorFields objectFields{run, object};
    uint32_t logic = arguments[1];
    uint32_t state = arguments[2];
    AttackPrivateFields stateFields{run, state};
    uint32_t attack = arguments[3];
    // State +0xe8 sequence, +0x04 active, +0x1c delayed animation,
    // +0x20 cancelled, +0x120 literal budget (units unproven),
    // +0x124 saved animation, +0x3c id.
    run.put(state + 0xe8, run.get(state + 0xe8) + 1);
    stateFields.active(1);
    stateFields.animationPending(0);
    stateFields.cancelled(0);
    uint32_t savedAnimation = objectFields.savedAnimationSource();
    stateFields.unknown_0x120(15000);
    stateFields.savedAnimation(savedAnimation);
    stateFields.attackId(attack);
    switch (attack) {
    case 1:
    case 7:
    case 8: {
        uint32_t animation = attack == 1 ? 0x522ad8 : attack == 7 ? 0x522afc : 0x522ab4;
        run.stackPointer = run.frame - 0x1c;
        run.call(0x4c6e40, object, {animation, 0});
        rectangle(run, object, 0x1e, attack == 7 ? 0x13 : 0xfffffffe, attack == 7 ? 0x69 : 0x70, attack == 7 ? 0x25 : 0x13, attack == 7 ? 2 : 5);
        uint32_t powerup = run.get(0x532d34);
        if (powerup == 0x26b8 || powerup == 0x26b9 || powerup == 0x26ba || powerup == 0x26bb) {
            uint32_t powered = attack == 1 ? 0x522ac4 : attack == 7 ? 0x522ae4 : 0x522a9c;
            run.stackPointer = run.frame - 0x1c;
            run.call(0x4c6e40, object, {powered, 0});
        }
        difficultyDamage(run, object, attack == 7 ? 4 : 10, attack == 7 ? 10 : 20);
        // +0x14 and +0x54/+0x58 remain unknown in this bounded owner view.
        stateFields.unknown_0x14(0);
        stateFields.unknown_0x54(attack == 8 ? 0x4b : 0x5f);
        stateFields.unknown_0x58(attack == 1 ? 0x0f : attack == 7 ? 0x19 : 10);
        break;
    }
    case 3:
    case 4:
    case 13: {
        uint32_t animation = attack == 3 ? 0x5228e4 : attack == 4 ? 0x5228f0 : 0x5228d8;
        run.stackPointer = run.frame - 0x1c;
        run.call(0x4c6e40, object, {animation, 0});
        rectangle(run, object, 0, attack == 4 ? 0xffffffed : 0xfffffffe, 0x38, 0x13, 5);
        difficultyDamage(run, object, 10, 20);
        stateFields.unknown_0x14(attack == 4 ? 1 : 0);
        break;
    }
    case 5:
    case 6:
    case 9:
    case 10:
    case 12:
    case 14:
    case 15:
    case 16:
    case 18: {
        uint32_t animation = 0;
        uint32_t x = 0;
        uint32_t y = 0;
        uint32_t weapon = 1;
        // State +0x70 pistol ammunition, +0x74 magic, +0x78 dynamite.
        if (attack == 5) {
            if (run.gets(state + 0x70) > 0) {
                run.stackPointer = run.frame - 0x14;
                if (s32(run.call(0x4a595b, 0)) % 100 < 30) {
                    run.stackPointer = run.frame - 0x1c;
                    run.call(0x48fb00, 0, {0x522a90, 0});
                }
                animation = 0x522a84;
            } else {
                animation = 0x522a70;
            }
            x = 0x47;
            y = 0xffffffeb;
            weapon = 2;
        } else if (attack == 9 || attack == 14) {
            animation = run.gets(state + 0x70) > 0 ? (attack == 9 ? 0x522a38 : 0x522a60) : (attack == 9 ? 0x522a20 : 0x522a48);
            x = 0x47;
            y = attack == 9 ? 0xffffffeb : 0x17;
            weapon = attack == 9 ? 1 : 2;
        } else if (attack == 6 || attack == 10 || attack == 15) {
            bool available = run.gets(state + 0x74) > 0;
            animation = attack == 6 ? (available ? 0x5229f0 : 0x5229e0) : attack == 10 ? (available ? 0x5229d0 : 0x5229bc) : (available ? 0x522a10 : 0x5229fc);
            x = attack == 6 ? 0x36 : attack == 10 ? 0x4b : 0x44;
            y = attack == 15 ? 0x18 : 0xfffffff8;
            weapon = attack == 15 ? 0 : 1;
        } else {
            bool available = run.gets(state + 0x78) > 0;
            if (available && attack != 18) {
                run.stackPointer = run.frame - 0x14;
                if (s32(run.call(0x4a595b, 0)) % 100 < (attack == 16 ? 35 : 25)) {
                    run.stackPointer = run.frame - 0x1c;
                    run.call(0x48fb00, 0, {0x5229b0, 0});
                }
            }
            animation = attack == 12 ? (available ? 0x522954 : 0x522940) : attack == 16 ? (available ? 0x522998 : 0x522980) : (available ? 0x522918 : 0x522900);
            x = 0x3c;
            y = attack == 12 ? 0xfffffff8 : attack == 16 ? 0x0c : 0xfffffff0;
        }
        run.stackPointer = run.frame - 0x1c;
        run.call(0x4c6e40, object, {animation, 0});
        // +0x10 is cleared here; +0x6c selects the weapon mode.
        stateFields.unknown_0x10(0);
        stateFields.unknown_0x54(x);
        stateFields.unknown_0x58(y);
        stateFields.weaponMode(weapon);
        stateFields.unknown_0x14(0);
        if (attack == 12 || attack == 16 || attack == 18) {
            // Keep the dynamite-path literals at +0x100..+0x108; this entry
            // alone does not establish their units or later arithmetic.
            stateFields.unknown_0x100(attack == 18 ? 500 : 0);
            stateFields.unknown_0x104(50);
            stateFields.unknown_0x108(2000);
            if (attack != 18) {
                uint32_t output = run.automatic(0x0c);
                run.put(output, 0);
                uint32_t map = run.get(run.get(object + 0x0c) + 0x2c) + 0x10;
                run.stackPointer = run.frame - 0x1c;
                run.call(0x4fc6b4, map, {attack == 12 ? 0x52292cU : 0x522968U, output});
                uint32_t nextAnimation = run.get(output);
                stateFields.animationPending(1);
                stateFields.nextAnimation(nextAnimation);
            }
        }
        break;
    }
    case 11: {
        stateFields.active(0);
        stateFields.attackId(0);
        uint32_t output = run.automatic(0x0c);
        run.put(output, 0);
        run.stackPointer = run.frame - 0x24;
        uint32_t distance = run.call(0x41eb30, 0, {object, logic, state, output});
        if (s32(distance) < 64) {
            uint32_t candidate = run.get(output);
            if (candidate && (run.get8(candidate + 0x180) & 1)) {
                run.stackPointer = run.frame - 0x24;
                if (run.call(0x41fa90, 0, {object, logic, state, candidate}) != 0) {
                    run.stackPointer = run.frame - 0x24;
                    run.call(0x41f030, 0, {object, logic, state, run.get(output)});
                }
            }
        }
        break;
    }
    default: {
        uint32_t player = run.get(0x535918);
        run.put(player + 0x0c, run.get(player + 0x0c) & 0xfdffffff);
        player = run.get(0x535918);
        run.put(player + 0x0c, run.get(player + 0x0c) & 0xfeffffff);
        // State +0x12c held object, whose +0x7c/+0x18 lead to logic.
        uint32_t held = stateFields.heldActor();
        if (held != 0) {
            uint32_t heldLogic = run.get(run.get(held + 0x7c) + 0x18);
            if (run.gets(heldLogic + 0x2c) >= 1)
                run.put(heldLogic + 0x04, 0x421a80);
            uint32_t count = run.get(heldLogic + 0x324);
            if (count == 0) {
                run.stackPointer = run.frame - 0x18;
                run.call(0x4dea70, heldLogic + 0x31c, {0});
            } else {
                uint32_t vector = count <= 0x20 ? heldLogic + 0x328 : run.get(heldLogic + 0x328);
                run.put(vector, run.get(vector) | 1);
            }
            stateFields.heldActor(0);
        }
        uint32_t active = stateFields.active();
        stateFields.attackId(0);
        stateFields.cancelled(1);
        if (active != 0) {
            uint32_t animation = stateFields.savedAnimation();
            stateFields.active(0);
            run.stackPointer = run.frame - 0x18;
            run.call(0x4c84c0, object + 0x1a0, {animation});
            run.put(object + 0x08, run.get(object + 0x08) | 0x80);
        }
        break;
    }
    }
    // Roids wins over Wimp. These damage overrides precede long range and facing.
    if (run.get(0x535930) != 0) {
        objectFields.damage(100);
    } else if (run.get(0x535940) != 0) {
        objectFields.damage(0);
    }
    // Add 320 modulo 2^32 after every switch path, including stale bounds.
    // Preserve this before mirroring; INT_MIN suppresses only the mirror.
    if (run.get(0x53594c) != 0)
        run.put(object + 0x15c, run.get(object + 0x15c) + 0x140);
    if (stateFields.facing() == 0) {
        uint32_t left = objectFields.attackLeft();
        if (left != 0x80000000) {
            uint32_t right = objectFields.attackRight();
            objectFields.attackLeft(0U - right);
            objectFields.attackRight(0U - left);
        }
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    if (function == 0x41f270)
        switch (function) {
        case 0x41f270: return setupAttackAndBounds(run, receiver, arguments);
        }
    run.fail(CLAW_FAULT_ABI, function);
}
}
CLAW_MODULE_ENTRY(claw_v13_cheat_attack_entry, owned, body)
