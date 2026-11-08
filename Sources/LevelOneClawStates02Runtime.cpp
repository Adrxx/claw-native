// Level 1 Claw movement and pose state callbacks batch 2
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;
using claw::recovered::v10::ActorFields;
using claw::recovered::v10::LogicHolderFields;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x41bb70:
        return 3;
    case 0x41c030:
        return 3;
    case 0x41c2b0:
        return 3;
    case 0x41c440:
        return 3;
    case 0x41e790:
        return 1;
    case 0x41f4c0:
        return 3;
    case 0x420480:
        return 0;
    case 0x420bd0:
        return 2;
    case 0x420c40:
        return 2;
    case 0x420d50:
        return 0;
    case 0x417c50:
        return 3;
    case 0x4cd740:
        return 2;
    default:
        return -1;
    }
}

// Fresh empty x87 state at the startup control word.
ClawX87State xstate() {
    ClawX87State state{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
    return state;
}

uint32_t lo_word(uint64_t bits) {
    return static_cast<uint32_t>(bits);
}

uint32_t hi_word(uint64_t bits) {
    return static_cast<uint32_t>(bits >> 32);
}

uint64_t double_bits(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    return bits;
}

// fld qword ptr [address]
void load_mem(Run &run, ClawX87State &fp, uint32_t address) {
    run.x87_step(CLAW_X87_F64, fp, {run.get(address), run.get(address + 0x4)});
}

// fld of a scratch slot held as raw binary64 bits
void load_bits(Run &run, ClawX87State &fp, uint64_t bits) {
    run.x87_step(CLAW_X87_F64, fp, {lo_word(bits), hi_word(bits)});
}

// fild dword: one raw signed word
void load_int(Run &run, ClawX87State &fp, uint32_t value) {
    run.x87_step(CLAW_X87_I32, fp, {value});
}

// An arithmetic or compare step whose binary64 operand is in guest memory.
void step_mem(Run &run, ClawX87State &fp, uint32_t operation, uint32_t address) {
    run.x87_step(operation, fp, {run.get(address), run.get(address + 0x4)});
}

// An arithmetic or compare step whose binary64 operand is a scratch slot.
void step_bits(Run &run, ClawX87State &fp, uint32_t operation, uint64_t bits) {
    run.x87_step(operation, fp, {lo_word(bits), hi_word(bits)});
}

// An arithmetic step whose operand is a binary32 in guest memory (widened exactly).
void step_float(Run &run, ClawX87State &fp, uint32_t operation, uint32_t address) {
    const uint64_t bits = double_bits(static_cast<double>(run.getf(address)));
    run.x87_step(operation, fp, {lo_word(bits), hi_word(bits)});
}

// fstp qword ptr [address]
void store_pop_mem(Run &run, ClawX87State &fp, uint32_t address) {
    const uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(address, lo_word(bits));
    run.put(address + 0x4, hi_word(bits));
}

// A register-form step on ST(index).
void st_form(Run &run, ClawX87State &fp, uint32_t form, uint32_t index) {
    run.x87_step(CLAW_X87_ST(form, index), fp);
}

// Original __ftol (0x4a30e0): pops ST(0) and returns the truncated integer.
uint32_t ftol(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

// Original motionIntegrate (0x403b40) on the integrator block with the scaled frame time.
void integrate_motion(Run &run, ClawX87State &fp) {
    const uint32_t milliseconds = run.get(0x53720c);
    load_bits(run, fp, double_bits(static_cast<double>(milliseconds)));
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x50bab0);
    const uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
    fp.popCount = 0;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    run.call_x87_exact(0x403b40, 0x534db8, fp, {lo_word(bits), hi_word(bits)});
}

// The fractional position carry at 0x534e48 / 0x534e68. Returns the whole-pixel step.
uint32_t carry_step(Run &run, ClawX87State &fp) {
    load_mem(run, fp, 0x534e48);
    const uint32_t first = ftol(run, fp);
    load_int(run, fp, first);
    step_mem(run, fp, CLAW_X87_SUBR_F64, 0x534e48);
    step_mem(run, fp, CLAW_X87_ADD_F64, 0x534e68);
    st_form(run, fp, CLAW_X87_LD_ST, 0);
    step_mem(run, fp, CLAW_X87_ADD_F64, 0x534e48);
    const uint32_t whole = ftol(run, fp);
    st_form(run, fp, CLAW_X87_LD_ST, 0);
    run.put(0x544e88, whole);
    const uint32_t second = ftol(run, fp);
    load_int(run, fp, second);
    st_form(run, fp, CLAW_X87_SUBR_TO0, 1);
    store_pop_mem(run, fp, 0x534e68);
    st_form(run, fp, CLAW_X87_STP_ST, 0);
    return whole;
}

// Complete death notification (shared tail of 0x41c2b0 and 0x41c440).
// Player +0x7c is lives; +0x80 counts deaths; +0x18 latches posting.
void post_end_message(Run &run, uint32_t playerState) {
    const uint32_t manager = run.get(0x5371fc);
    const uint32_t state = run.get(manager + 0x2c);
    const uint32_t mode = run.vcall(state, 0x10);
    if (mode != 4) {
        run.put(playerState + 0x7c, run.get(playerState + 0x7c) - 1);
    }
    if (run.get(0x53722c) != 0) {
        run.put(playerState + 0x7c, run.get(playerState + 0x7c) + 1);
    }
    const uint32_t count = run.get(playerState + 0x80) + 1;
    const uint32_t lives = run.get(playerState + 0x7c);
    run.put(playerState + 0x80, count);
    uint32_t message = 0x803a;
    if (s32(lives) <= 0) {
        message = 0x8006;
    }
    const uint32_t application = run.get(0x5371fc);
    const uint32_t window = run.get(run.get(application + 0x4) + 0x4);
    run.icall(0x546d50, {window, 0x111, message, 0});
    run.put(playerState + 0x18, 1);
}

// Clear two input flag bits of the input object.
void clear_input_flags(Run &run) {
    const uint32_t input = run.get(0x537204);
    run.put(input + 0xc, run.get(input + 0xc) & 0xfdffffff);
    const uint32_t again = run.get(0x537204);
    run.put(again + 0xc, run.get(again + 0xc) & 0xfeffffff);
}

// Release the attached actor through its actor and logic-holder prefixes.
void release_attached(Run &run, uint32_t playerState) {
    const uint32_t attached = run.get(playerState + 0x12c);
    if (attached != 0) {
        ActorFields attachedFields{run, attached};
        const uint32_t holder = attachedFields.holder();
        LogicHolderFields attachedHolderFields{run, holder};
        const uint32_t owner = attachedHolderFields.logic();
        run.call(0x421010, owner, {0x4207a0, 1});
        run.call(0x420fc0, owner + 0x2f4, {0});
        run.put(playerState + 0x12c, 0);
    }
}

// 0x41bb70. cdecl, 3 stack argument(s), returns void.
// Climb animation and vertical motion, with jump/fall/standing transitions.
// Actor +0x4c/+0x50 are pixel positions; +0x148/+0x14c hold signed speed bits.
// Other private offsets remain literal until their layout is established.
uint32_t stepClimbingPose(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t actor = arguments[0x0];
    const uint32_t manager = arguments[0x1];
    LogicHolderFields stateHolderFields{run, manager};
    const uint32_t playerState = arguments[0x2];
    const uint32_t input = run.get(0x537204);
    const uint32_t inputLow = run.get8(input + 0x4);
    const uint32_t xPixels = run.get(actor + 0x4c);
    const uint32_t yPixels = run.get(actor + 0x50);
    if ((inputLow & 1) != 0 && (run.get(input + 0x8) & 0x4000000) == 0) {
        run.call(0x41c4e0, 0, {actor, manager, playerState});
        stateHolderFields.state(4);
        run.call(0x4c79e0, actor, {0x5246a8, 0});
        const uint32_t flags = run.get(actor + 0x8) & 0xffffffef;
        run.put(actor + 0xcc, 3);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(actor + 0x8, flags);
        run.call(0x417050, 0, {actor, playerState});
        run.call(0x4170b0, 0, {actor, playerState});
        if (run.get(0x534eac) == 0x26bc) {
            run.put(0x534de8, 0);
            run.put(0x534dec, 0xc07f4000);
        } else {
            const uint32_t special = run.get(playerState + 0x114);
            run.put(0x534de8, 0);
            run.put(0x534dec, 0xc07f4000);
            if (special != 0) {
                run.put(0x534dec, 0xc07a9000);
            }
        }
        run.put(playerState + 0x118, 0xfa);
        run.put(playerState + 0x5c, 0);
        run.put(playerState + 0x60, run.get(actor + 0x50));
        const uint32_t above = run.get(actor + 0x50) - 0x2d;
        run.put(playerState + 0x10c, 0);
        run.put(playerState + 0x64, above);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0x40a19400);
        ClawX87State fp = xstate();
        load_int(run, fp, run.get(actor + 0x4c));
        store_pop_mem(run, fp, 0x534df8);
        load_int(run, fp, run.get(actor + 0x50));
        const uint32_t xPositionHighWord = run.get(0x534dfc);
        const uint32_t xPositionLowWord = run.get(0x534df8);
        store_pop_mem(run, fp, 0x534e00);
        load_int(run, fp, run.get(playerState + 0x64));
        const uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
        fp.popCount = 0;
        fp.pushCount = 1;
        fp.returned = 0;
        fp.eax = 0;
        fp.edx = 0;
        run.call_x87_exact(0x420dd0, 0x534db8, fp, {xPositionLowWord, xPositionHighWord, lo_word(bits), hi_word(bits), 0, 0});
        st_form(run, fp, CLAW_X87_STP_ST, 0);
        return 0;
    }
    uint32_t flagObject = input;
    if (run.get(playerState + 0x68) == 0) {
        const uint32_t tiles = run.get(run.get(actor + 0xc) + 0x24);
        const uint32_t offset = run.get(actor + 0x11c);
        const uint32_t probe = run.call(0x4207f0, tiles, {xPixels, yPixels + offset});
        uint32_t found = 0;
        if (probe != 3) {
            const uint32_t top = run.get(actor + 0x11c);
            const uint32_t currentY = run.get(actor + 0x50);
            const uint32_t currentX = run.get(actor + 0x4c);
            uint32_t candidate = top + currentY;
            uint32_t remaining = run.get(actor + 0x124) - top;
            const uint32_t before = remaining;
            remaining -= 1;
            if (s32(before) > 0) {
                for (;;) {
                    candidate += 1;
                    const uint32_t hit = run.call(0x4207f0, tiles, {currentX, candidate});
                    if (hit == 3) {
                        found = candidate;
                        break;
                    }
                    const uint32_t previous = remaining;
                    remaining -= 1;
                    if (s32(previous) > 0) {
                        continue;
                    }
                    found = 0;
                    break;
                }
            }
        }
        run.put(playerState + 0x68, found);
        flagObject = run.get(0x537204);
    }
    const uint32_t flags = run.get(flagObject + 0x8);
    bool advanceAnimation = true;
    if ((flags & 0x4000000) != 0) {
        run.put(actor + 0x14c, 0xffffff38);
        if (run.get(0x534eac) == 0x26bc) {
            run.put(actor + 0x14c, 0xffffff06);
        }
        if (run.get(playerState + 0x2c) != 8) {
            run.put(playerState + 0x2c, 8);
            run.call(0x4c79e0, actor, {0x5246c4, 0});
        }
    } else if ((flags & 0x8000000) != 0) {
        run.put(actor + 0x14c, 0xc8);
        if (run.get(0x534eac) == 0x26bc) {
            run.put(actor + 0x14c, 0xfa);
        }
        if (run.get(playerState + 0x2c) != 2) {
            run.put(playerState + 0x2c, 2);
            run.call(0x4c79e0, actor, {0x5247a0, 0});
        }
    } else {
        if (run.get(playerState + 0x2c) != 5) {
            run.put(playerState + 0x2c, 5);
            run.call(0x4c79e0, actor, {0x524790, 0});
        }
        run.put(actor + 0x14c, 0);
    }
    ClawX87State fp = xstate();
    load_int(run, fp, run.get(actor + 0x14c));
    store_pop_mem(run, fp, 0x534de8);
    integrate_motion(run, fp);
    uint32_t advance = 0;
    if (run.get(0x534e58) == 0) {
        advance = carry_step(run, fp);
    }
    const uint32_t map = run.get(run.get(actor + 0xc) + 0x24);
    run.call(0x4cbb60, map, {actor, xPixels, advance + yPixels, 0});
    const uint32_t climbTileY = run.get(playerState + 0x68);
    if (climbTileY != 0) {
        uint32_t depth = run.get(actor + 0x124) - climbTileY;
        depth += run.get(actor + 0x50);
        if (s32(depth) >= 0 && s32(depth) <= 0x78) {
            uint32_t code = 0x17f;
            if (s32(depth) < 0x11) {
                code = 0x185;
            } else if (s32(depth) < 0x22) {
                code = 0x184;
            } else if (s32(depth) < 0x33) {
                code = 0x183;
            } else if (s32(depth) < 0x44) {
                code = 0x182;
            } else if (s32(depth) < 0x55) {
                code = 0x181;
            } else if (s32(depth) < 0x66) {
                code = 0x180;
            }
            run.call(0x4209d0, actor, {code});
            advanceAnimation = false;
        }
    }
    const uint32_t pose = run.get(actor + 0xcc);
    if (pose == 4) {
        const uint32_t kind = run.get(playerState + 0x3c);
        if (kind == 8 || kind == 9 || kind == 0xa || kind == 0x12) {
            const uint32_t sounds = run.get(run.get(actor + 0xc) + 0x2c);
            const uint32_t handle = run.call(0x4061b0, sounds, {0x5246dc});
            run.put(playerState + 0x124, handle);
        } else {
            run.call(0x41c4e0, 0, {actor, manager, playerState});
            run.call(0x4c79e0, actor, {0x5246dc, 0});
        }
        stateHolderFields.state(0x19);
        const uint32_t flagsAfter = run.get(actor + 0x8) & 0xffffffef;
        run.put(actor + 0xcc, 4);
        run.put(actor + 0x148, 0);
        run.put(actor + 0x14c, 0);
        run.put(actor + 0x8, flagsAfter);
        run.call(0x417050, 0, {actor, playerState});
        run.call(0x4170b0, 0, {actor, playerState});
        run.put(playerState + 0x40, 0);
        run.put(0x534de8, 0);
        run.put(0x534dec, 0);
        run.put(0x534dd0, 0);
        run.put(0x534dd4, 0x40a19400);
        return 0;
    }
    if (pose == 1) {
        run.put(playerState + 0xf8, 0x3e8);
        run.call(0x4171d0, 0, {actor, manager, playerState});
        return 0;
    }
    if (advanceAnimation) {
        run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    }
    return 0;
}

// 0x41c030. cdecl, 3 stack argument(s), returns void.
// Apply carrier displacement and horizontal drift, then restore standing
// once animation completion allows it. Repeated reads after calls are deliberate.
uint32_t stepFallingPose(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t actor = arguments[0x0];
    const uint32_t manager = arguments[0x1];
    LogicHolderFields stateHolderFields{run, manager};
    const uint32_t playerState = arguments[0x2];
    uint32_t xPixels = run.get(actor + 0x4c);
    uint32_t yPixels = run.get(actor + 0x50);
    if ((run.get8(actor + 0x8) & 0x10) != 0) {
        const uint32_t carrier = run.get(actor + 0x80);
        if (carrier != 0) {
            xPixels += run.get(carrier + 0x158);
            yPixels += run.get(carrier + 0x15c);
        }
    }
    const uint32_t timer = run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    if (timer == 1) {
        const uint32_t speed = run.get(actor + 0x148);
        if (s32(speed) > 0) {
            // Keep the wrapped product before the unsigned high-half divide idiom.
            const uint32_t product = run.get(0x5430c4) * speed;
            const uint64_t wide = static_cast<uint64_t>(product) * 0x10624dd3u;
            xPixels += hi_word(wide) >> 6;
        } else if (s32(speed) < 0) {
            // Negation also wraps before widening; do not use signed division.
            const uint32_t product = 0u - run.get(0x5430c4) * speed;
            const uint64_t wide = static_cast<uint64_t>(product) * 0x10624dd3u;
            xPixels -= hi_word(wide) >> 6;
        }
    } else {
        run.put(actor + 0x148, 0);
    }
    run.call(0x4cbb60, run.get(run.get(actor + 0xc) + 0x24), {actor, xPixels, yPixels, 8});
    if (run.get(actor + 0xcc) == 4) {
        run.put(actor + 0x8, run.get(actor + 0x8) & 0xffffffef);
    }
    if (run.get(actor + 0x1a4) == 0) {
        return 0;
    }
    if (run.get(actor + 0x19c) != 0) {
        return 0;
    }
    clear_input_flags(run);
    release_attached(run, playerState);
    const uint32_t pending = run.get(playerState + 0x4);
    run.put(playerState + 0x3c, 0);
    run.put(playerState + 0x20, 1);
    if (pending != 0) {
        const uint32_t value = run.get(playerState + 0x124);
        run.put(playerState + 0x4, 0);
        run.call(0x4c8220, actor + 0x188, {value});
        run.put(actor + 0x8, run.get(actor + 0x8) | 0x80);
    }
    stateHolderFields.state(0x18);
    run.call(0x4c79e0, actor, {0x5246d0, 1});
    const uint32_t flags = run.get(actor + 0x8);
    run.put(actor + 0xcc, 1);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(actor + 0x104, 0);
    run.put(actor + 0x8, flags | 0x80);
    if (run.get(playerState) != 0) {
        run.put(actor + 0x128, 0xffffffea);
        run.put(actor + 0x12c, 0xffffffd3);
        run.put(actor + 0x130, 0xf);
    } else {
        run.put(actor + 0x128, 0xfffffff1);
        run.put(actor + 0x12c, 0xffffffd3);
        run.put(actor + 0x130, 0x16);
    }
    run.put(actor + 0x134, 0x34);
    if (run.get(playerState) != 0) {
        run.put(actor + 0x118, 0xfffffff0);
        run.put(actor + 0x11c, 0xffffffcc);
        run.put(actor + 0x120, 0x10);
        run.put(actor + 0x124, 0x3c);
    } else {
        run.call(0x40f6c0, actor, {0xfffffff0, 0xffffffcc, 0x10, 0x3c});
    }
    run.put(playerState + 0xfc, 0x28a);
    run.put(playerState + 0x114, 0x5dc);
    run.put(playerState + 0x120, 0x3a98);
    run.put(playerState + 0x118, 0);
    run.put(0x534e60, 0);
    run.put(0x534e64, 0);
    run.put(0x534e68, 0);
    run.put(0x534e6c, 0);
    run.put(0x534e70, 0);
    run.put(0x534e74, 0);
    run.put(actor + 0x1b0, 0x3f800000);
    return 0;
}

// 0x41c2b0. cdecl, 3 stack argument(s), returns void.
// Falling-death travel uses two separate carry evaluations before notification.
uint32_t stepFallingDeath(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t actor = arguments[0x0];
    const uint32_t playerState = arguments[0x2];
    uint32_t yPixels = run.get(actor + 0x50);
    run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    ClawX87State fp = xstate();
    integrate_motion(run, fp);
    const uint32_t disabled = run.get(0x534e58);
    uint32_t first = 0;
    if (disabled == 0) {
        first = carry_step(run, fp);
    }
    yPixels += first;
    uint32_t second = 0;
    if (disabled == 0) {
        second = carry_step(run, fp);
    }
    const uint32_t total = run.get(playerState + 0x40) + second + 1;
    run.put(playerState + 0x40, total);
    run.put(actor + 0x50, yPixels);
    if (s32(run.get(playerState + 0x40)) > 0x320) {
        if (run.get(playerState + 0x18) == 0) {
            post_end_message(run, playerState);
        }
    }
    return 0;
}

// 0x41c440. cdecl, 3 stack argument(s), returns void.
// Wait for animation completion and the posting latch before notifying death.
uint32_t stepAnimatedDeath(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t actor = arguments[0x0];
    const uint32_t playerState = arguments[0x2];
    run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    if (run.get(actor + 0x1a4) == 0) {
        return 0;
    }
    if (run.get(actor + 0x19c) != 0) {
        return 0;
    }
    if (run.get(playerState + 0x18) != 0) {
        return 0;
    }
    post_end_message(run, playerState);
    return 0;
}

// 0x41e790. cdecl, 1 stack argument(s), returns u32.
// Probe one collision bound, then scan the interval in four-pixel steps.
uint32_t testClearCollisionInterval(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t actor = arguments[0x0];
    if ((run.get8(actor + 0x8) & 0x10) != 0) {
        return 0;
    }
    const uint32_t tiles = run.get(run.get(actor + 0xc) + 0x24);
    if (run.call(0x4cd1c0, tiles, {actor, run.get(actor + 0x120)}) == 0) {
        return 0;
    }
    uint32_t row = run.get(actor + 0x120);
    const uint32_t top = run.get(actor + 0x118);
    row -= 0xc;
    if (s32(row) <= s32(top)) {
        return 0;
    }
    for (;;) {
        if (run.call(0x4cd1c0, tiles, {actor, row}) != 0) {
            return 0;
        }
        row -= 4;
        if (s32(row) > s32(top)) {
            continue;
        }
        break;
    }
    const uint32_t last = run.call(0x4cd1c0, tiles, {actor, top});
    return last == 0 ? 1 : 0;
}

// 0x41f4c0. cdecl, 3 stack argument(s), returns void.
// A held jump consumes player +0x118, clamps target Y at +0x64, and
// recomputes the arc with the original extended-precision x87 sequence.
uint32_t extendHeldJumpArc(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t actor = arguments[0x0];
    const uint32_t playerState = arguments[0x2];
    const uint32_t input = run.get(0x537204);
    if ((run.get8(input + 0x8) & 1) == 0) {
        run.put(playerState + 0x118, 0);
        return 0;
    }
    const uint32_t timer = run.get(playerState + 0x118);
    if (timer == 0) {
        return 0;
    }
    const uint32_t elapsed = run.get(0x5430c4);
    if (elapsed < timer) {
        run.put(playerState + 0x118, timer - elapsed);
    } else {
        run.put(playerState + 0x118, 0);
    }
    ClawX87State fp = xstate();
    uint32_t constant = 0x50bb08;
    if (run.get(0x537220) != 0) {
        run.put(actor + 0x14c, 0xfffffd12);
    } else if (run.get(0x534eac) == 0x26bc) {
        run.put(actor + 0x14c, 0xfffffe0c);
    } else if (run.get(playerState + 0x114) == 0) {
        run.put(actor + 0x14c, 0xfffffe0c);
        constant = 0x50bb0c;
    } else {
        run.put(actor + 0x14c, 0xfffffe57);
        constant = 0x50bb10;
    }
    const uint32_t remaining = 0xfa - run.get(playerState + 0x118);
    load_int(run, fp, run.get(playerState + 0x60));
    load_bits(run, fp, double_bits(static_cast<double>(remaining)));
    step_float(run, fp, CLAW_X87_MUL_F64, constant);
    st_form(run, fp, CLAW_X87_SUBP, 1);
    uint32_t value = ftol(run, fp);
    const uint32_t limit = run.get(playerState + 0x64);
    if (s32(limit) < s32(value)) {
        value = limit;
    }
    run.put(playerState + 0x64, value);
    // Preserve the exact x87 stack and rounding, including binary64 scratch stores.
    // Scratch slots of the original frame: zeroTermBits = zero constant, verticalDeltaBits = dy, negativeDepthBits = -dz,
    // quadraticConstantBits = the quadratic constant term, squaredLengthBits = squared length, rootBits = the root.
    load_int(run, fp, run.get(playerState + 0x64));
    load_mem(run, fp, 0x50ba88);
    load_mem(run, fp, 0x534e08);
    st_form(run, fp, CLAW_X87_XCH_ST, 2);
    step_mem(run, fp, CLAW_X87_SUB_F64, 0x534e00);
    load_mem(run, fp, 0x534dd0);
    load_mem(run, fp, 0x534dc8);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x534dc8);
    st_form(run, fp, CLAW_X87_XCH_ST, 3);
    const uint64_t zeroTermBits = run.x87_step(CLAW_X87_ST_F64, fp);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x534dd0);
    st_form(run, fp, CLAW_X87_XCH_ST, 2);
    const uint64_t verticalDeltaBits = run.x87_step(CLAW_X87_ST_F64, fp);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_bits(run, fp, CLAW_X87_MUL_F64, zeroTermBits);
    load_mem(run, fp, 0x534dd8);
    st_form(run, fp, CLAW_X87_XCH_ST, 5);
    run.x87_step(CLAW_X87_CHS, fp);
    const uint64_t negativeDepthBits = run.x87_step(CLAW_X87_ST_F64, fp);
    load_bits(run, fp, zeroTermBits);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x534dc8);
    run.x87_step(CLAW_X87_CHS, fp);
    load_bits(run, fp, verticalDeltaBits);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x534dd0);
    st_form(run, fp, CLAW_X87_SUBP, 1);
    load_bits(run, fp, negativeDepthBits);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x534dd8);
    st_form(run, fp, CLAW_X87_SUBP, 1);
    const uint64_t quadraticConstantBits = run.x87_step(CLAW_X87_STP_F64, fp);
    st_form(run, fp, CLAW_X87_XCH_ST, 3);
    st_form(run, fp, CLAW_X87_ADDP, 4);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_bits(run, fp, CLAW_X87_MUL_F64, verticalDeltaBits);
    load_bits(run, fp, quadraticConstantBits);
    st_form(run, fp, CLAW_X87_XCH_ST, 5);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x534dd8);
    st_form(run, fp, CLAW_X87_ADDP, 4);
    st_form(run, fp, CLAW_X87_ADDP, 1);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_bits(run, fp, CLAW_X87_MUL_F64, negativeDepthBits);
    st_form(run, fp, CLAW_X87_XCH_ST, 2);
    const uint64_t squaredLengthBits = run.x87_step(CLAW_X87_STP_F64, fp);
    st_form(run, fp, CLAW_X87_XCH_ST, 2);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x50bac8);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    st_form(run, fp, CLAW_X87_ADDP, 2);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_bits(run, fp, CLAW_X87_MUL_F64, squaredLengthBits);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x50bac0);
    run.x87_step(CLAW_X87_SQRT, fp);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    st_form(run, fp, CLAW_X87_SUBP, 1);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x50bad0);
    run.x87_step(CLAW_X87_SQRT, fp);
    const uint64_t rootBits = run.x87_step(CLAW_X87_ST_F64, fp);
    step_mem(run, fp, CLAW_X87_COMP_F64, 0x513e20);
    if ((fp.status & 0x100) != 0) {
        run.put(0x534de0, 0);
        run.put(0x534de4, 0);
        run.put(0x534de8, 0);
        run.put(0x534dec, 0);
        run.put(0x534df0, 0);
        run.put(0x534df4, 0);
        return 0;
    }
    load_bits(run, fp, squaredLengthBits);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x50bad8);
    load_mem(run, fp, 0x513e20);
    run.x87_step(CLAW_X87_CHS, fp);
    st_form(run, fp, CLAW_X87_LD_ST, 1);
    run.x87_step(CLAW_X87_COMPP, fp);
    bool general = (fp.status & 0x100) != 0;
    if (!general) {
        step_mem(run, fp, CLAW_X87_COM_F64, 0x513e20);
        general = (fp.status & 0x4100) == 0;
    }
    if (!general) {
        st_form(run, fp, CLAW_X87_STP_ST, 0);
        load_bits(run, fp, verticalDeltaBits);
        load_bits(run, fp, zeroTermBits);
        load_bits(run, fp, negativeDepthBits);
        st_form(run, fp, CLAW_X87_XCH_ST, 2);
        run.x87_step(CLAW_X87_ABS, fp);
        st_form(run, fp, CLAW_X87_XCH_ST, 1);
        run.x87_step(CLAW_X87_ABS, fp);
        st_form(run, fp, CLAW_X87_ADDP, 1);
        st_form(run, fp, CLAW_X87_XCH_ST, 1);
        run.x87_step(CLAW_X87_ABS, fp);
        load_bits(run, fp, zeroTermBits);
        st_form(run, fp, CLAW_X87_XCH_ST, 1);
        st_form(run, fp, CLAW_X87_ADDP, 2);
        load_bits(run, fp, verticalDeltaBits);
        load_bits(run, fp, negativeDepthBits);
        st_form(run, fp, CLAW_X87_XCH_ST, 2);
        st_form(run, fp, CLAW_X87_DIV_TO0, 3);
        st_form(run, fp, CLAW_X87_XCH_ST, 1);
        st_form(run, fp, CLAW_X87_DIV_TO0, 3);
        st_form(run, fp, CLAW_X87_XCH_ST, 2);
        st_form(run, fp, CLAW_X87_DIV_TO0, 3);
        st_form(run, fp, CLAW_X87_XCH_ST, 1);
        step_bits(run, fp, CLAW_X87_MUL_F64, rootBits);
        st_form(run, fp, CLAW_X87_XCH_ST, 2);
        step_bits(run, fp, CLAW_X87_MUL_F64, rootBits);
        st_form(run, fp, CLAW_X87_XCH_ST, 1);
        step_bits(run, fp, CLAW_X87_MUL_F64, rootBits);
        st_form(run, fp, CLAW_X87_XCH_ST, 2);
        store_pop_mem(run, fp, 0x534de0);
        store_pop_mem(run, fp, 0x534de8);
        store_pop_mem(run, fp, 0x534df0);
        st_form(run, fp, CLAW_X87_STP_ST, 0);
        return 0;
    }
    load_bits(run, fp, rootBits);
    step_bits(run, fp, CLAW_X87_MUL_F64, rootBits);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    st_form(run, fp, CLAW_X87_ADD_TOI, 0);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_bits(run, fp, CLAW_X87_SUB_F64, quadraticConstantBits);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    st_form(run, fp, CLAW_X87_DIVP, 1);
    st_form(run, fp, CLAW_X87_LD_ST, 0);
    run.x87_step(CLAW_X87_SQRT, fp);
    st_form(run, fp, CLAW_X87_LD_ST, 1);
    st_form(run, fp, CLAW_X87_LD_ST, 2);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x534dc8);
    st_form(run, fp, CLAW_X87_XCH_ST, 2);
    st_form(run, fp, CLAW_X87_XCH_ST, 3);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x534dd0);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x534dd8);
    st_form(run, fp, CLAW_X87_XCH_ST, 2);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x50bad0);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x50bad0);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_bits(run, fp, CLAW_X87_SUBR_F64, zeroTermBits);
    st_form(run, fp, CLAW_X87_XCH_ST, 2);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x50bad0);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_bits(run, fp, CLAW_X87_SUBR_F64, verticalDeltaBits);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_bits(run, fp, CLAW_X87_SUBR_F64, negativeDepthBits);
    st_form(run, fp, CLAW_X87_XCH_ST, 2);
    st_form(run, fp, CLAW_X87_DIV_TO0, 3);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    st_form(run, fp, CLAW_X87_DIV_TO0, 3);
    st_form(run, fp, CLAW_X87_XCH_ST, 2);
    st_form(run, fp, CLAW_X87_DIV_TO0, 3);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    store_pop_mem(run, fp, 0x534de0);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    store_pop_mem(run, fp, 0x534de8);
    store_pop_mem(run, fp, 0x534df0);
    st_form(run, fp, CLAW_X87_STP_ST, 0);
    return 0;
}

// 0x420480. cdecl, 0 stack argument(s), returns u32.
// Preserve the signed rand quotient fallback when a negative remainder misses
// the table of CLAW sound names.
uint32_t selectRandomClawSound(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    static const uint32_t names[12] = {0x524eb0, 0x524ea4, 0x524e98, 0x524e8c, 0x524e80, 0x524e70,
                                       0x524e60, 0x524e50, 0x524e40, 0x524e30, 0x524e20, 0x524e10};
    const int32_t value = s32(run.call(0x4a3050, 0));
    const int32_t quotient = value / 12;
    const int32_t remainder = value % 12;
    if (static_cast<uint32_t>(remainder) > 0xb) {
        return static_cast<uint32_t>(quotient);
    }
    return run.call(0x48c8a0, 0, {names[remainder], 0});
}

// 0x420bd0. thiscall, 2 stack argument(s), returns ST(0).
// The exact x87 sequence retains unordered comparisons, signed zero and faults.
// Signed square root of value^2 - (argument - origin) * factor * constant, clamped at zero.
uint32_t evaluateSignedArcSpeed(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t function = 0x420bd0;
    auto fp = run.x87_entry(function);
    load_mem(run, fp, receiver + 0x20);
    step_mem(run, fp, CLAW_X87_COMP_F64, 0x50ba88);
    if ((fp.status & 0x4000) != 0) {
        load_mem(run, fp, receiver + 0x38);
        run.x87_return(function, fp);
        return 0;
    }
    run.x87_step(CLAW_X87_F64, fp, {arguments[0x0], arguments[0x1]});
    step_mem(run, fp, CLAW_X87_SUB_F64, receiver + 0x50);
    load_mem(run, fp, receiver + 0x38);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_mem(run, fp, CLAW_X87_MUL_F64, receiver + 0x20);
    st_form(run, fp, CLAW_X87_LD_ST, 1);
    st_form(run, fp, CLAW_X87_MULP, 2);
    load_mem(run, fp, 0x50ba88);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_mem(run, fp, CLAW_X87_MUL_F64, 0x50bac8);
    st_form(run, fp, CLAW_X87_SUBP, 2);
    st_form(run, fp, CLAW_X87_COMP_ST, 1);
    if ((fp.status & 0x4100) == 0) {
        st_form(run, fp, CLAW_X87_STP_ST, 0);
        load_mem(run, fp, 0x50ba88);
    }
    run.x87_step(CLAW_X87_SQRT, fp);
    load_mem(run, fp, receiver + 0x38);
    step_mem(run, fp, CLAW_X87_COMP_F64, 0x50ba88);
    if ((fp.status & 0x4100) != 0) {
        run.x87_step(CLAW_X87_CHS, fp);
    }
    run.x87_return(function, fp);
    return 0;
}

// 0x420c40. thiscall, 2 stack argument(s), returns void.
// Update the first arc axis and its displacement accumulator. These literal
// offsets differ from the +0x20/+0x38/+0x50 axis used at 0x420bd0.
uint32_t updateFirstArcAxis(Run &run, uint32_t receiver, const uint32_t *arguments) {
    ClawX87State fp = xstate();
    load_mem(run, fp, receiver + 0x18);
    step_mem(run, fp, CLAW_X87_COMP_F64, 0x50ba88);
    if ((fp.status & 0x4000) != 0) {
        load_mem(run, fp, receiver + 0x30);
    } else {
        run.x87_step(CLAW_X87_F64, fp, {arguments[0x0], arguments[0x1]});
        step_mem(run, fp, CLAW_X87_SUB_F64, receiver + 0x48);
        load_mem(run, fp, receiver + 0x30);
        st_form(run, fp, CLAW_X87_XCH_ST, 1);
        step_mem(run, fp, CLAW_X87_MUL_F64, receiver + 0x18);
        st_form(run, fp, CLAW_X87_LD_ST, 1);
        st_form(run, fp, CLAW_X87_MULP, 2);
        load_mem(run, fp, 0x50ba88);
        st_form(run, fp, CLAW_X87_XCH_ST, 1);
        step_mem(run, fp, CLAW_X87_MUL_F64, 0x50bac8);
        st_form(run, fp, CLAW_X87_SUBP, 2);
        st_form(run, fp, CLAW_X87_COMP_ST, 1);
        if ((fp.status & 0x4100) == 0) {
            st_form(run, fp, CLAW_X87_STP_ST, 0);
            load_mem(run, fp, 0x50ba88);
        }
        run.x87_step(CLAW_X87_SQRT, fp);
        load_mem(run, fp, receiver + 0x30);
        step_mem(run, fp, CLAW_X87_COMP_F64, 0x50ba88);
        if ((fp.status & 0x4100) != 0) {
            run.x87_step(CLAW_X87_CHS, fp);
        }
    }
    load_mem(run, fp, receiver + 0x48);
    run.x87_step(CLAW_X87_SUB_F64, fp, {arguments[0x0], arguments[0x1]});
    run.x87_step(CLAW_X87_F64, fp, {arguments[0x0], arguments[0x1]});
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    step_mem(run, fp, CLAW_X87_SUBR_F64, receiver + 0x90);
    st_form(run, fp, CLAW_X87_XCH_ST, 2);
    store_pop_mem(run, fp, receiver + 0x30);
    store_pop_mem(run, fp, receiver + 0x48);
    store_pop_mem(run, fp, receiver + 0x90);
    return 0;
}

// 0x420d50. thiscall, 0 stack argument(s), returns u32.
// Retain repeated truncations and the +0xb0 fractional carry.
uint32_t consumeFirstAxisFraction(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0xa0) != 0) {
        return 0;
    }
    ClawX87State fp = xstate();
    load_mem(run, fp, receiver + 0x90);
    const uint32_t whole = ftol(run, fp);
    load_mem(run, fp, receiver + 0x90);
    load_int(run, fp, whole);
    step_mem(run, fp, CLAW_X87_SUBR_F64, receiver + 0x90);
    step_mem(run, fp, CLAW_X87_ADD_F64, receiver + 0xb0);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    st_form(run, fp, CLAW_X87_LD_ST, 1);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    st_form(run, fp, CLAW_X87_ADD_TO0, 2);
    st_form(run, fp, CLAW_X87_XCH_ST, 1);
    store_pop_mem(run, fp, receiver + 0xb0);
    const uint32_t sum = ftol(run, fp);
    st_form(run, fp, CLAW_X87_STP_ST, 0);
    run.put(0x544e88, sum);
    load_mem(run, fp, receiver + 0xb0);
    const uint32_t rest = ftol(run, fp);
    load_int(run, fp, rest);
    step_mem(run, fp, CLAW_X87_SUBR_F64, receiver + 0xb0);
    store_pop_mem(run, fp, receiver + 0xb0);
    return run.get(0x544e88);
}

// 0x417c50. cdecl, 3 stack argument(s), returns void.
// Detach carried state, select CLAW_SPIKEDEATH, then notify game services.
uint32_t enterSpikeDeath(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t actor = arguments[0x0];
    const uint32_t manager = arguments[0x1];
    LogicHolderFields stateHolderFields{run, manager};
    const uint32_t playerState = arguments[0x2];
    clear_input_flags(run);
    release_attached(run, playerState);
    const uint32_t pending = run.get(playerState + 0x4);
    run.put(playerState + 0x3c, 0);
    run.put(playerState + 0x20, 1);
    if (pending != 0) {
        const uint32_t value = run.get(playerState + 0x124);
        run.put(playerState + 0x4, 0);
        run.call(0x420a10, actor, {value, 0});
        run.put(actor + 0x8, run.get(actor + 0x8) | 0x80);
    }
    stateHolderFields.state(0x138d);
    run.call(0x4c79e0, actor, {0x524708, 1});
    const uint32_t flags = run.get(actor + 0x8);
    run.put(actor + 0xcc, 4);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(actor + 0x8, (flags & 0xffffffef) | 5);
    run.put(actor + 0x48, 0x14);
    run.put(actor + 0x44, 0);
    run.put(actor + 0x10c, 0);
    if (run.get(run.get(0x537960) + 0x44) == 1) {
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
        const uint32_t depth = run.get(actor + 0x50) - run.get(run.get(0x537960) + 0xb0);
        run.call(0x461c40, 0, {run.get(actor + 0xc), run.get(actor + 0x4c), depth, run.get(actor + 0x64) + 2});
    }
    const uint32_t level = run.get(run.get(actor + 0xc) + 0x28);
    if (run.get(level + 0x30) == 0) {
        const uint32_t found = run.automatic(0xc);
        run.put(found, 0);
        run.call(0x4f6286, level + 0x10, {0x5246f8, found});
        const uint32_t object = run.get(found);
        if (object != 0) {
            const uint32_t sound = run.get(0x532c0c);
            const uint32_t sample = run.get(0x532c10);
            if (sound != 0) {
                run.call(0x4b45f0, run.get(object + 0x10), {sample, 0, 0, 0});
            }
        }
    }
    run.call(0x41ebd0, 0);
    run.call(0x4b7aa0, run.get(0x5371fc), {0});
    run.call(0x41f990, 0, {actor, manager, playerState, 0, 0});
    return 0;
}

// 0x4cd740. thiscall, 2 stack argument(s), returns u32.
// Clamp the actor-foot probe, resolve its cell, and dispatch the tile-local point.
uint32_t probeTileBelowActor(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t actor = arguments[0x0];
    uint32_t yPixels = run.get(actor + 0x50);
    const uint32_t offset = run.get(actor + 0x124);
    uint32_t xPixels = run.get(actor + 0x4c);
    yPixels += offset;
    xPixels += arguments[0x1];
    if (s32(xPixels) < 0) {
        xPixels = 0;
    } else {
        const uint32_t limit = run.get(run.get(receiver + 0x5c) + 0x30);
        if (s32(xPixels) >= s32(limit)) {
            xPixels = limit - 1;
        }
    }
    if (s32(yPixels) < 0) {
        yPixels = 0;
    } else {
        const uint32_t limit = run.get(run.get(receiver + 0x5c) + 0x34);
        if (s32(yPixels) >= s32(limit)) {
            yPixels = limit - 1;
        }
    }
    const uint32_t map = run.get(receiver + 0x5c);
    const uint32_t shiftX = run.get(map + 0x8c);
    const uint32_t cellX = static_cast<uint32_t>(s32(xPixels) >> (shiftX & 0x1f));
    const uint32_t shiftY = run.get(map + 0x90);
    const uint32_t cellY = static_cast<uint32_t>(s32(yPixels) >> (shiftY & 0x1f));
    const uint32_t localX = xPixels - (cellX << (shiftX & 0x1f));
    const uint32_t shiftYAgain = run.get(map + 0x90);
    const uint32_t localY = yPixels - (cellY << (shiftYAgain & 0x1f));
    const uint32_t rows = run.get(map + 0x24);
    const uint32_t cells = run.get(map + 0x20);
    const uint32_t index = run.get(rows + cellY * 4) + cellX;
    const uint32_t entry = run.get(cells + index * 4);
    if (entry == 0xeeeeeeee || entry == 0xffffffff) {
        return 0;
    }
    const uint32_t handlers = run.get(receiver + 0x4c);
    const uint32_t object = run.get(handlers + (entry & 0xffff) * 4);
    return run.vcall(object, 0x20, {localX, localY});
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x41bb70:
        return stepClimbingPose(run, receiver, arguments);
    case 0x41c030:
        return stepFallingPose(run, receiver, arguments);
    case 0x41c2b0:
        return stepFallingDeath(run, receiver, arguments);
    case 0x41c440:
        return stepAnimatedDeath(run, receiver, arguments);
    case 0x41e790:
        return testClearCollisionInterval(run, receiver, arguments);
    case 0x41f4c0:
        return extendHeldJumpArc(run, receiver, arguments);
    case 0x420480:
        return selectRandomClawSound(run, receiver, arguments);
    case 0x420bd0:
        return evaluateSignedArcSpeed(run, receiver, arguments);
    case 0x420c40:
        return updateFirstArcAxis(run, receiver, arguments);
    case 0x420d50:
        return consumeFirstAxisFraction(run, receiver, arguments);
    case 0x417c50:
        return enterSpikeDeath(run, receiver, arguments);
    case 0x4cd740:
        return probeTileBelowActor(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_claw_states_02_entry, owned, body)
