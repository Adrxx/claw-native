// Menu Claw actor navigation logic, recovered from 0x45f500.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x45f500:
        return 1;
    default:
        return -1;
    }
}

ClawX87State floatingState() {
    ClawX87State state{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
    return state;
}

void pushDouble(Run &run, ClawX87State &state, double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    run.x87_step(CLAW_X87_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
}

void multiply(Run &run, ClawX87State &state, uint32_t address) {
    uint32_t low = run.get(address);
    uint32_t high = run.get(address + 0x04);
    run.x87_step(CLAW_X87_MUL_F64, state, {low, high});
}

// CW53 arithmetic here produces normal binary64-representable values or zero.
// Retain the sign of zero when assembling the binary64 argument words.
uint64_t doubleBits(const ClawX87Value &value) {
    uint64_t sign = uint64_t(value.signExponent & 0x8000) << 48;
    if (!value.significand) {
        return sign;
    }
    uint64_t exponent = (value.signExponent & 0x7fff) - 16383 + 1023;
    return sign | (exponent << 52) | ((value.significand >> 11) & 0x000fffffffffffffull);
}

uint32_t convert(Run &run, ClawX87State &state) {
    state.popCount = 1;
    state.pushCount = 0;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, state);
}

void decrementTimer(Run &run, uint32_t data) {
    uint32_t timer = run.get(data + 0x130);
    uint32_t delta = run.get(0x53720c);
    run.put(data + 0x130, delta < timer ? timer - delta : 0);
}

// 0x45f500, cdecl(actor), returns u32.
uint32_t function_45f500(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    if (!actor) {
        return 0;
    }
    // Actor: flags +0x40, signed X +0x4c, data +0x6c, animation +0x188.
    uint32_t data = run.get(actor + 0x6c);
    if (!data) {
        return 0;
    }
    // Data: state +0x1c, direction +0x64, target +0x94, timer +0x130,
    // float32 speed +0x160. Targets are the original frame-local constants.
    const uint32_t targets[] = {0xffffffc4, 110, 530, 700};
    uint32_t state = run.get(data + 0x1c);
    if (state == 0) {
        run.put(data + 0x64, 1);
        run.put(data + 0x130, 5000);
        run.put(actor + 0x4c, 0xffffffc4);
        run.put(data + 0x94, 0);
        run.put(data + 0x1c, 9001);
        return 1;
    }
    if (state == 9001) {
        decrementTimer(run, data);
        if (!run.get(data + 0x130)) {
            run.put(data + 0x1c, 9002);
        }
        return 1;
    }
    if (state == 9002) {
        uint32_t chosen = uint32_t(s32(run.call(0x4a3050, 0)) % 4);
        uint32_t old = run.get(data + 0x94);
        if (chosen == old) {
            uint32_t next = chosen + 1;
            chosen = s32(next) < 4 ? next : chosen - 1;
        }
        uint32_t difference = targets[old] - targets[chosen];
        ClawX87State fp = floatingState();
        run.x87_step(CLAW_X87_I32, fp, {difference});
        // FCOM zero preserves TOP, clears C1/C2/C3 and sets C0 on negative.
        fp.status &= ~0x4700u;
        if (s32(difference) < 0) {
            fp.status |= 0x0100;
        } else if (!difference) {
            fp.status |= 0x4000;
        }
        uint32_t distance = difference;
        uint32_t flags;
        if (s32(difference) < 0) {
            run.put(data + 0x64, 1);
            uint32_t converted = convert(run, fp);
            uint32_t sign = s32(converted) < 0 ? 0xffffffffu : 0;
            distance = (converted ^ sign) - sign;
            flags = run.get(actor + 0x40) & ~2u;
            run.x87_step(CLAW_X87_I32, fp, {distance});
        } else {
            run.put(data + 0x64, 0);
            flags = run.get(actor + 0x40) | 2;
        }
        // FLD ST0 duplicates this exact signed integer distance.
        run.x87_step(CLAW_X87_I32, fp, {distance});
        multiply(run, fp, 0x50e8c8);
        run.put(actor + 0x40, flags);
        run.put(data + 0x94, chosen);
        uint32_t duration = convert(run, fp);
        multiply(run, fp, 0x50e8d0);
        double denominator = double(duration);
        uint64_t denominatorBits;
        std::memcpy(&denominatorBits, &denominator, sizeof(denominatorBits));
        run.put(data + 0x130, duration);
        run.put(data + 0x1c, 9003);
        run.x87_step(CLAW_X87_DIV_F64, fp, {uint32_t(denominatorBits), uint32_t(denominatorBits >> 32)});
        uint64_t bits = doubleBits(fp.slots[0]);
        double speed;
        std::memcpy(&speed, &bits, sizeof(speed));
        run.putf(data + 0x160, float(speed));
        return 1;
    }
    if (state == 9003) {
        decrementTimer(run, data);
        uint32_t target = targets[run.get(data + 0x94)];
        uint32_t direction = run.get(data + 0x64);
        uint32_t x = run.get(actor + 0x4c);
        if (direction ? s32(x) < s32(target) : s32(x) > s32(target)) {
            uint32_t delta = run.get(0x53720c);
            ClawX87State fp = floatingState();
            pushDouble(run, fp, double(run.getf(data + 0x160)));
            // FILD unsigned delta; FMULP has the same value/TOP/SW as this
            // memory multiplication, since the integer is exactly binary64.
            uint64_t deltaBits;
            double deltaDouble = double(delta);
            std::memcpy(&deltaBits, &deltaDouble, sizeof(deltaBits));
            run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(deltaBits), uint32_t(deltaBits >> 32)});
            multiply(run, fp, 0x50e8d8);
            run.x87_step(CLAW_X87_ROUND_F64, fp);
            uint64_t bits = doubleBits(fp.slots[0]);
            run.x87_step(CLAW_X87_POP, fp);
            fp.popCount = 0;
            fp.pushCount = 1;
            fp.returned = 0;
            fp.eax = 0;
            fp.edx = 0;
            run.call_x87_exact(0x4a4250, 0, fp, {uint32_t(bits), uint32_t(bits >> 32)});
            uint32_t step = convert(run, fp);
            uint32_t moved = direction ? run.get(actor + 0x4c) + step : run.get(actor + 0x4c) - step;
            run.put(actor + 0x4c, moved);
            if (direction ? s32(moved) >= s32(target) : s32(moved) <= s32(target)) {
                run.put(actor + 0x4c, target);
                run.put(data + 0x130, 0);
            }
        }
        if (!run.get(data + 0x130)) {
            uint32_t random = run.call(0x4a3050, 0);
            uint32_t index = run.get(data + 0x94);
            run.put(data + 0x130, uint32_t(s32(random) % 15001) + 10000);
            if (index == 1) {
                run.put(actor + 0x40, run.get(actor + 0x40) & ~2u);
            } else if (index == 2) {
                run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            }
            run.call(0x4c79e0, actor, {0x529198, 0});
            run.put(data + 0x1c, 9004);
        }
    } else if (state == 9004) {
        decrementTimer(run, data);
        if (!run.get(data + 0x130)) {
            run.call(0x4c79e0, actor, {0x528b20, 0});
            run.put(data + 0x1c, 9002);
        }
    } else if (state != 5) {
        return 1;
    }
    run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x45f500:
        return function_45f500(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_menu_claw_logic_entry, owned, body)
