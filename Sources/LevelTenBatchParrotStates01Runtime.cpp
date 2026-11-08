// Level 10 parrot state transitions, recovered from the v1.0 packet.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x467b50:
    case 0x467c60:
        return 1;
    case 0x467ae0:
    case 0x467bf0:
    case 0x467c90:
    case 0x467e30:
        return 0;
    default:
        return -1;
    }
}

// 0x467b50. +0x42c next state, +0x12c sprite, +0x10 state holder.
uint32_t enterHit(Run &run, uint32_t receiver, uint32_t next) {
    run.put(receiver + 0x42c, next);
    const uint32_t sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 1u);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x5c, 0);
    run.put(receiver + 0x64, 0);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    const uint32_t state = run.call(0x4dba00, 0x537668, {0x529bb8});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    const uint32_t sound = run.get(receiver + 0x418);
    if (sound != 0 && run.get(0x532c0c) != 0) {
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
    const uint32_t currentSprite = run.get(receiver + 0x12c);
    const uint32_t animation = run.get(receiver + 0x414);
    run.put(receiver + 0x134, run.get(currentSprite + 0x190));
    run.call(0x4c8220, currentSprite + 0x188, {animation});
    return 0;
}

// 0x467ae0. +0x19c observed player state, +0x430 hit count.
uint32_t checkHit(Run &run, uint32_t receiver) {
    const uint32_t playerState = run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0xe8);
    if (playerState == run.get(receiver + 0x19c)) {
        return 0;
    }
    run.put(receiver + 0x19c, playerState);
    run.call(0x440e20, receiver, {run.get(run.get(receiver + 0xc) + 0x74)});
    const uint32_t hits = run.get(receiver + 0x430) + 1u;
    run.put(receiver + 0x430, hits);
    enterHit(run, receiver, s32(hits) >= 3 ? 2u : 0u);
    return 1;
}

// 0x467c60. States zero and two enter game-owned peers; all others dispatch.
void resumeState(Run &run, uint32_t receiver, uint32_t state) {
    if (state == 0) {
        run.call(0x466580, receiver);
    } else if (state == 1) {
        run.vcall(receiver, 0x48);
    } else if (state == 2) {
        run.call(0x4672d0, receiver);
    } else {
        run.vcall(receiver, 0x48);
    }
}

// 0x467bf0. +0x134 saved animation, +0x42c pending state.
uint32_t updateHit(Run &run, uint32_t receiver) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    const uint32_t animation = run.get(receiver + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) != 0 && run.get(animation + 0x14) == 0) {
        resumeState(run, receiver, run.get(receiver + 0x42c));
        const uint32_t sprite = run.get(receiver + 0x12c);
        const uint32_t saved = run.get(receiver + 0x134);
        run.put(receiver + 0x134, run.get(sprite + 0x190));
        run.call(0x4c8220, sprite + 0x188, {saved});
    }
    return 0;
}

ClawX87State emptyFP() {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    return fp;
}

void memoryFP(Run &run, ClawX87State &fp, uint32_t op, uint32_t address) {
    const uint32_t low = run.get(address);
    const uint32_t high = run.get(address + 0x4);
    run.x87_step(op, fp, {low, high});
}

double popDouble(Run &run, ClawX87State &fp) {
    const uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
    double value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

// The horizontal/vertical velocity calculation in 0x467c90, retaining each
// instruction's extended intermediate and ordered compare status.
void velocityFP(Run &run, ClawX87State &fp, uint32_t object, uint32_t positionOffset,
                uint32_t accelerationOffset, uint32_t velocityOffset, bool compared) {
    if (!compared) {
        memoryFP(run, fp, CLAW_X87_F64, object + accelerationOffset);
        memoryFP(run, fp, CLAW_X87_COMP_F64, 0x50ebf8);
    }
    if (fp.status & 0x4000) {
        run.x87_step(CLAW_X87_POP, fp);
        memoryFP(run, fp, CLAW_X87_F64, object + velocityOffset);
    } else {
        memoryFP(run, fp, CLAW_X87_SUB_F64, object + positionOffset);
        memoryFP(run, fp, CLAW_X87_F64, object + velocityOffset);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        memoryFP(run, fp, CLAW_X87_MUL_F64, object + accelerationOffset);
        run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_MULP, 2), fp);
        memoryFP(run, fp, CLAW_X87_F64, 0x50ebf8);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        memoryFP(run, fp, CLAW_X87_MUL_F64, 0x50ec50);
        run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 2), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_COMP_ST, 1), fp);
        if (!(fp.status & 0x4100)) {
            run.x87_step(CLAW_X87_POP, fp);
            memoryFP(run, fp, CLAW_X87_F64, 0x50ebf8);
        }
        run.x87_step(CLAW_X87_SQRT, fp);
        memoryFP(run, fp, CLAW_X87_F64, object + velocityOffset);
        memoryFP(run, fp, CLAW_X87_COMP_F64, 0x50ebf8);
        if (fp.status & 0x4100) {
            run.x87_step(CLAW_X87_CHS, fp);
        }
    }
}

// 0x467c90. +0xb0/+0xb8 carried displacement, +0xc8 suppress flag.
void releaseCarried(Run &run, uint32_t receiver) {
    run.call(0x43dfa0, receiver);
    const uint32_t nameSlot = run.call(0x441030, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
    uint32_t item = run.get(0x5376b4);
    uint32_t count = run.get(0x5376b8);
    while (count != 0) {
        if (item != 0) {
            run.call(0x4f6439, item);
        }
        item += 4u;
        --count;
    }
    if (run.call(0x4a3810, 0, {run.get(nameSlot), 0x529bc8}) != 0) {
        return;
    }
    auto fp = emptyFP();
    memoryFP(run, fp, CLAW_X87_F64, run.get(receiver + 0xc8) ? 0x50ebf8 : receiver + 0xb8);
    memoryFP(run, fp, CLAW_X87_F64, run.get(receiver + 0xc8) ? 0x50ebf8 : receiver + 0xb0);
    const uint32_t carried = run.get(0x537b14);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), fp);
    run.put(run.get(carried + 0xc) + 0xcc, 7);
    run.put(carried + 0x40, 0);
    run.put(carried + 0x44, 0);
    memoryFP(run, fp, CLAW_X87_ADD_F64, carried + 0x68);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), fp);
    velocityFP(run, fp, carried, 0x68, 0x38, 0x50, false);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 3), fp);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.putd(carried + 0x50, popDouble(run, fp));
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.putd(carried + 0x68, popDouble(run, fp));
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    run.putd(carried + 0xb0, popDouble(run, fp));
    memoryFP(run, fp, CLAW_X87_F64, carried + 0x40);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    memoryFP(run, fp, CLAW_X87_ADD_F64, carried + 0x70);
    run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
    memoryFP(run, fp, CLAW_X87_COMP_F64, 0x50ebf8);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), fp);
    velocityFP(run, fp, carried, 0x70, 0x40, 0x58, true);
    run.putd(carried + 0x58, popDouble(run, fp));
    run.putd(carried + 0x70, popDouble(run, fp));
    run.putd(carried + 0xb8, popDouble(run, fp));
    run.vcall(carried, 0x24);
}

// 0x467e30. Restore integer spawn coordinates and reset the parrot.
void reset(Run &run, uint32_t receiver) {
    run.putd(receiver + 0x68, double(run.gets(receiver + 0x434)));
    run.putd(receiver + 0x70, double(run.gets(receiver + 0x438)));
    run.put(run.get(receiver + 0xc) + 0x10c, 100);
    const uint32_t definition = run.get(receiver + 0xc);
    const double speed = double(run.gets(definition + 0x10c)) * double(run.getf(0x5262b4));
    const uint32_t converted = run.call_x87(0x4a30e0, 0, speed);
    run.put(definition + 0x10c, converted);
    run.put(receiver + 0x430, 0);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0);
    run.put(receiver + 0x2ec, run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0x80));
    run.call(0x466580, receiver);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x467ae0:
        return checkHit(run, receiver);
    case 0x467b50:
        return enterHit(run, receiver, arguments[0]);
    case 0x467bf0:
        return updateHit(run, receiver);
    case 0x467c60:
        resumeState(run, receiver, arguments[0]);
        return 0;
    case 0x467c90:
        releaseCarried(run, receiver);
        return 0;
    case 0x467e30:
        reset(run, receiver);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_ten_batch_parrot_states_01_entry, owned, body)
