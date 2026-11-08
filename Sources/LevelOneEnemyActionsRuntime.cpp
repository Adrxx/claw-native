#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

struct FP;
int owned(uint32_t function);
uint32_t ownedBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments, FP &fp);

uint32_t dynamicCall(Run &run, FP &fp, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
    if (owned(function) >= 0) {
        if (uint32_t(owned(function)) != arguments.size()) {
            run.fail(CLAW_FAULT_ABI, function);
        }
        return ownedBody(run, function, receiver, arguments.begin(), fp);
    }
    return run.call(function, receiver, arguments);
}

uint32_t dynamicVirtual(Run &run, FP &fp, uint32_t receiver, uint32_t offset, std::initializer_list<uint32_t> arguments = {}) {
    return dynamicCall(run, fp, run.get(run.get(receiver) + offset), receiver, arguments);
}

// Exact x87 stack carried across owned arithmetic and original boundaries.
struct FP {
    ClawX87State state{};
    FP() {
        state.size = sizeof(state);
        state.version = CLAW_X87_VERSION;
        state.control = 0x023f;
    }
    void load(Run &run, double value) {
        uint64_t bits;
        std::memcpy(&bits, &value, 8);
        run.x87_step(CLAW_X87_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    void integer(Run &run, uint32_t value) {
        run.x87_step(CLAW_X87_I32, state, {value});
    }
    void exchange(Run &run, unsigned index) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, index), state);
    }
    void duplicate(Run &run, unsigned index) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, index), state);
    }
    void pop(Run &run) {
        run.x87_step(CLAW_X87_POP, state);
    }
    double store(Run &run) {
        return storeExact(run);
    }
    double storeExact(Run &run) {
        uint64_t bits = run.x87_step(CLAW_X87_STP_F64, state);
        double result;
        std::memcpy(&result, &bits, sizeof(result));
        return result;
    }
    void exchangeExact(Run &run, unsigned index) {
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, index), state);
    }
    void subtractExact(Run &run, double operand) {
        memory(run, CLAW_X87_SUB_F64, operand);
    }
    void memory(Run &run, uint32_t op, double operand) {
        uint64_t bits;
        std::memcpy(&bits, &operand, 8);
        run.x87_step(op, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    void subtract(Run &run, double operand) {
        memory(run, CLAW_X87_SUB_F64, operand);
    }
    void compare(Run &run, double operand, bool popping) {
        memory(run, popping ? CLAW_X87_COMP_F64 : CLAW_X87_COM_F64, operand);
    }
    uint32_t convert(Run &run) {
        state.popCount = 1;
        state.pushCount = 0;
        state.returned = state.eax = state.edx = 0;
        return run.call_x87_exact(0x4a30e0, 0, state);
    }
    void balanced(Run &run, uint32_t target, uint32_t receiver, double input) {
        uint64_t bits;
        std::memcpy(&bits, &input, 8);
        state.popCount = 0;
        state.pushCount = 0;
        state.returned = state.eax = state.edx = 0;
        run.call_x87_exact(target, receiver, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    void producer(Run &run, uint32_t target, uint32_t receiver, double input) {
        uint64_t bits;
        std::memcpy(&bits, &input, 8);
        state.popCount = 0;
        state.pushCount = 1;
        state.returned = state.eax = state.edx = 0;
        run.call_x87_exact(target, receiver, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
};

uint32_t bit(Run &run, uint32_t object, uint32_t index) {
    uint32_t count = run.get(object + 0x2fc);
    if (count <= index) {
        return 0;
    }
    uint32_t address = count <= 0x20 ? object + 0x300 : run.get(object + 0x300);
    return (run.get(address) >> index) & 1;
}

// 0x43e420. Rectangle bounds retain the lower live operands at each ftol.
uint32_t choose(Run &run, uint32_t object, FP &fp) {
    fp.load(run, run.getd(object + 0x68));
    fp.integer(run, run.get(run.get(0x537e88) + 0x4c));
    run.x87_step(CLAW_X87_COMPP, fp.state);
    if (!(fp.state.status & 0x100)) {
        run.put(object + 0x18c, 2);
    }
    fp.load(run, run.getd(object + 0x68));
    fp.integer(run, run.get(run.get(0x537e88) + 0x4c));
    run.x87_step(CLAW_X87_COMPP, fp.state);
    if (fp.state.status & 0x100) {
        run.put(object + 0x18c, 3);
    }
    if (run.get(0x534eac) == 0x26b7 || bit(run, object, 1)) {
        return 0;
    }
    uint32_t setRect = 0;
    for (uint32_t group = 0; group < 5; ++group) {
        uint32_t widthOffset = group == 3 ? 0x2a4 : 0x28c + group * 8;
        double padding = double(run.gets(object + 0x2a4));
        double width = double(run.gets(object + widthOffset));
        if (group == 3) {
            fp.load(run, run.getd(object + 0x70));
            fp.integer(run, run.get(object + 0x2a4));
            fp.memory(run, CLAW_X87_ADD_F64, run.getd(object + 0x98));
            fp.load(run, run.getd(object + 0x68));
            fp.memory(run, CLAW_X87_ADD_F64, padding);
            double upper = fp.store(run);
            fp.compare(run, upper, false);
            if (!(fp.state.status & 0x100)) {
                fp.pop(run);
                fp.load(run, upper);
            }
        } else {
            fp.integer(run, run.get(object + 0x2a4));
            fp.integer(run, run.get(object + widthOffset));
            fp.load(run, run.getd(object + 0x98));
            fp.load(run, run.getd(object + 0x68));
            fp.exchange(run, 3);
            padding = fp.store(run);
            fp.memory(run, CLAW_X87_ADD_F64, padding);
            fp.exchange(run, 1);
            width = fp.store(run);
            fp.exchange(run, 1);
            fp.memory(run, CLAW_X87_ADD_F64, width);
            fp.duplicate(run, 1);
            if (group == 0) {
                fp.exchange(run, 1);
                double upper = fp.store(run);
                fp.compare(run, upper, true);
                if (!(fp.state.status & 0x100)) {
                    fp.pop(run);
                    fp.load(run, upper);
                }
            } else {
                fp.load(run, run.getd(object + 0x70));
                fp.exchange(run, 2);
                double upper = fp.store(run);
                fp.compare(run, upper, true);
                fp.store(run);
                if (!(fp.state.status & 0x100)) {
                    fp.pop(run);
                    fp.load(run, upper);
                }
            }
        }
        fp.load(run, run.getd(object + 0x68));
        fp.load(run, run.getd(object + 0x80));
        fp.subtract(run, padding);
        fp.exchange(run, 1);
        fp.subtract(run, width);
        fp.load(run, run.getd(object + 0x70));
        fp.exchange(run, 1);
        fp.duplicate(run, 2);
        fp.exchange(run, 1);
        double lower = fp.store(run);
        fp.compare(run, lower, true);
        double y = fp.store(run);
        if (fp.state.status & 0x4100) {
            fp.pop(run);
            fp.load(run, lower);
        }
        if (group == 3) {
            fp.exchange(run, 2);
        } else {
            fp.load(run, y);
        }
        uint32_t height = run.get(object + 0x290 + group * 8);
        uint32_t bottom = fp.convert(run) + height;
        if (group != 3) {
            fp.exchange(run, 1);
        }
        uint32_t right = fp.convert(run);
        fp.load(run, y);
        uint32_t top = fp.convert(run) - height;
        uint32_t left = fp.convert(run);
        if (group == 0) {
            setRect = run.get(0x546d5c);
        }
        run.call(setRect, 0, {object + 0x1c0 + group * 0x10, left, top, right, bottom});
    }
    uint32_t contains = run.get(0x546cd4);
    for (uint32_t n = 5; n; --n) {
        uint32_t actor = run.get(0x537e88);
        if (run.call(contains, 0, {object + 0x1c0 + (n - 1) * 0x10, run.get(actor + 0x4c), run.get(actor + 0x50)})) {
            run.put(object + 0x184, n - 1);
            run.put(object + 0x188, 0);
            return 0;
        }
    }
    if (run.get(run.get(object + 0x0c) + 0x38) == 0xffffffff) {
        run.put(object + 0x184, 6);
        run.put(object + 0x188, 0);
    } else if (!run.get(object + 0x188)) {
        run.put(object + 0x3cc, 500);
        run.put(object + 0x3c8, run.get(0x537210));
        run.put(object + 0x188, 1);
    } else if (run.get(0x537210) - run.get(object + 0x3c8) >= run.get(object + 0x3cc)) {
        run.put(object + 0x184, 5);
    }
    return 0;
}

// Position publication after the original motion result producers.
void adjust(Run &run, FP &fp, uint32_t object, uint32_t coordinate, uint32_t integer) {
    fp.integer(run, integer);
    double position = fp.storeExact(run);
    fp.producer(run, coordinate == 0x68 ? 0x420af0 : 0x420b60, object + 0x28, position);
    fp.load(run, run.getd(object + coordinate));
    fp.subtractExact(run, position);
    fp.load(run, position);
    fp.exchangeExact(run, 2);
    run.putd(object + coordinate - 0x18, fp.storeExact(run));
    fp.memory(run, CLAW_X87_SUBR_F64, run.getd(object + coordinate + 0x48));
    fp.exchangeExact(run, 1);
    run.putd(object + coordinate, fp.storeExact(run));
    run.putd(object + coordinate + 0x48, fp.storeExact(run));
}

// 0x4dca10.
uint32_t integrate(Run &run, uint32_t object, FP &fp) {
    fp.load(run, run.getd(object + 0x68));
    run.put(object + 0x118, fp.convert(run));
    fp.load(run, run.getd(object + 0x70));
    run.put(object + 0x11c, fp.convert(run));
    fp.load(run, double(run.get(0x537210)));
    fp.memory(run, CLAW_X87_MUL_F64, run.getd(0x513e48));
    fp.subtractExact(run, run.getd(object + 0x28));
    double elapsed = fp.storeExact(run);
    fp.balanced(run, 0x403b40, object + 0x28, elapsed);
    uint32_t actor = run.get(object + 0x0c);
    if ((run.get8(actor + 0x08) & 0x10) && run.get(actor + 0x80)) {
        run.put(actor + 0x4c, run.get(actor + 0x4c) + run.get(run.get(actor + 0x80) + 0x158));
        fp.integer(run, run.get(run.get(object + 0x0c) + 0x4c));
        run.putd(object + 0x68, fp.storeExact(run));
        actor = run.get(object + 0x0c);
        run.put(actor + 0x50, run.get(actor + 0x50) + run.get(run.get(actor + 0x80) + 0x15c));
        fp.integer(run, run.get(run.get(object + 0x0c) + 0x50));
        run.putd(object + 0x70, fp.storeExact(run));
    }
    actor = run.get(object + 0x0c);
    uint32_t result;
    if (run.get(actor + 0xcc) == 1) {
        uint32_t flags = run.get(object + 0x124);
        uint32_t y = run.get(actor + 0x50);
        fp.load(run, run.getd(object + 0x68));
        uint32_t x = fp.convert(run);
        result = run.call(0x4cbb60, run.get(run.get(actor + 0x0c) + 0x24), {actor, x, y, flags});
        run.put(object + 0x120, result);
        run.put(object + 0x58, 0);
        run.put(object + 0x5c, 0);
    } else {
        run.put(actor + 0x08, run.get(actor + 0x08) & 0xffffffef);
        uint32_t flags = run.get(object + 0x124);
        actor = run.get(object + 0x0c);
        fp.load(run, run.getd(object + 0x70));
        uint32_t y = fp.convert(run);
        fp.load(run, run.getd(object + 0x68));
        uint32_t x = fp.convert(run);
        result = run.call(0x4cbb60, run.get(run.get(actor + 0x0c) + 0x24), {actor, x, y, flags});
        run.put(object + 0x120, result);
    }
    uint32_t x = run.get(run.get(object + 0x0c) + 0x4c);
    fp.load(run, run.getd(object + 0x68));
    if (fp.convert(run) != x) {
        adjust(run, fp, object, 0x68, x);
    }
    uint32_t y = run.get(run.get(object + 0x0c) + 0x50);
    fp.load(run, run.getd(object + 0x70));
    if (fp.convert(run) != y) {
        adjust(run, fp, object, 0x70, y);
    }
    if (run.get(run.get(object + 0x0c) + 0xcc) != 7) {
        uint32_t flags = run.get(object + 0x120);
        if (flags & 0x800000) {
            fp.load(run, run.getd(object + 0x58));
            run.x87_step(CLAW_X87_CHS, fp.state);
            run.putd(object + 0x58, fp.storeExact(run));
        } else if (flags & 0xc0000) {
            fp.integer(run, run.get(object + 0x118));
            run.putd(object + ((flags & 0x40000) ? 0x98 : 0x80), fp.storeExact(run));
            fp.load(run, run.getd(object + 0x50));
            fp.memory(run, CLAW_X87_MUL_F64, run.getd(0x513e50));
            run.putd(object + 0x50, fp.storeExact(run));
        }
    }
    return 0;
}

// 0x43dfa0.
uint32_t motion(Run &run, uint32_t object, FP &fp) {
    integrate(run, object, fp);
    uint32_t state = run.get(run.get(object + 0x0c) + 0xcc);
    if (state != 7 && (run.get(object + 0x120) & 0x100000)) {
        uint32_t text = run.call(0x406020, 0x537698, {run.get(run.get(object + 0x10) + 0x1c)});
        if (!run.call(0x4a3810, 0, {run.get(text), 0x5234f4}) || bit(run, object, 4)) {
            return 0;
        }
        uint32_t mode = run.get(run.get(0x537960) + 0x44);
        if (mode <= 1) {
            dynamicVirtual(run, fp, object, 0x5c, {mode == 0 ? 2u : 3u});
        }
        return 0;
    }
    if (state == 1 && bit(run, object, 3) && !bit(run, object, 2)) {
        double delta = run.get(object + 0xc8) ? 0 : run.getd(object + 0xb0);
        bool corrected = false;
        for (uint32_t side = 0; side < 2 && !corrected; ++side) {
            fp.load(run, delta);
            fp.compare(run, run.getd(0x50dba0), true);
            if (side == 0 && !(fp.state.status & 0x100)) {
                continue;
            }
            if (side == 1 && (fp.state.status & 0x4100)) {
                break;
            }
            uint32_t actor = run.get(object + 0x128);
            uint32_t edge = run.get(run.get(object + 0x0c) + (side ? 0x120 : 0x118));
            uint32_t y = run.get(actor + 0x50) + run.get(actor + 0x124) + 1;
            auto probe = [&](uint32_t row) {
                uint32_t source = run.get(object + 0x128);
                uint32_t x = run.get(run.get(object + 0x12c) + 0x4c) + edge;
                return run.call(0x4207f0, run.get(run.get(source + 0x0c) + 0x24), {x, row});
            };
            bool solid = probe(y) == 1;
            if (!solid) {
                solid = probe(y) == 2;
            }
            if (!solid) {
                solid = probe(y) == 3;
            }
            if (solid && probe(y - 1) == 0) {
                continue;
            }
            fp.integer(run, run.get(object + 0x118));
            run.putd(object + (side ? 0x98 : 0x80), fp.storeExact(run));
            adjust(run, fp, object, 0x68, run.get(object + 0x118));
            adjust(run, fp, object, 0x70, run.get(object + 0x11c));
            corrected = true;
        }
    }
    fp.load(run, run.getd(object + 0x68));
    uint32_t x = fp.convert(run);
    run.put(run.get(object + 0x0c) + 0x4c, x);
    fp.load(run, run.getd(object + 0x70));
    uint32_t y = fp.convert(run);
    run.put(run.get(object + 0x0c) + 0x50, y);
    if (bit(run, object, 0)) {
        uint32_t actor = run.get(object + 0x0c);
        uint32_t target = run.get(0x537e88);
        uint32_t bottom = run.get(target + 0x124) + run.get(target + 0x50);
        fp.integer(run, run.get(actor + 0x124));
        fp.memory(run, CLAW_X87_ADD_F64, run.getd(object + 0x70));
        fp.integer(run, bottom);
        run.x87_step(CLAW_X87_COMPP, fp.state);
        uint32_t action = run.get(object + 0x2d0) + ((fp.state.status & 0x4100) ? 0xfa0 : 0xf3b);
        if (run.get(actor + 0x64) != action) {
            run.put(actor + 0x64, action);
            run.put(actor + 0x08, run.get(actor + 0x08) | 0x20000);
        }
    }
    return 0;
}

// 0x43d490. Registry lookup may publish the literal original return address.
uint32_t dispatch(Run &run, uint32_t object, uint32_t action, FP &fp) {
    auto lookup = [&](uint32_t returnPC) {
        run.put(0x537658, 0);
        uint32_t low = run.get(0x537640);
        if (s32(action) < s32(low) || s32(action) > run.gets(0x537644)) {
            if (!run.call(0x4db6e0, 0x537638, {action, 0})) {
                uint32_t context = run.get(0x544b4c);
                run.put(0x544b14, returnPC);
                run.call(0x4db4d0, run.get(0x53763c), {0x537638, context, 0x0c});
                return run.get(0x53764c);
            }
            low = run.get(0x537640);
        }
        return (action - low) * run.get(0x537650) + run.get(0x537648);
    };
    uint32_t entry = lookup(0x43d4f0);
    if (run.get(entry)) {
        entry = lookup(0x43d56a);
        dynamicCall(run, fp, run.get(entry), object);
    } else {
        run.call(0x4a36f0, 0, {object});
    }
    return 0;
}

int owned(uint32_t function) {
    switch (function) {
    case 0x404fc0:
    case 0x4063b0:
    case 0x43d490:
    case 0x4dc830:
        return 1;
    case 0x43dfa0:
    case 0x43e420:
    case 0x43e9b0:
    case 0x4dca10:
        return 0;
    default:
        return -1;
    }
}

uint32_t ownedBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments, FP &fp) {
    switch (function) {
    // 0x404fc0.
    case 0x404fc0:
        if (!run.get(0x541334)) {
            uint32_t random = run.call(0x4a3050, 0);
            run.put(receiver + 0x3c4, uint32_t(s32(random) % 1001));
        } else {
            run.put(receiver + 0x3c4, 0x1fffffff);
        }
        return choose(run, receiver, fp);
    // 0x4063b0.
    case 0x4063b0:
        if (run.get(receiver + 0x14)) {
            uint32_t callback = run.get(receiver + 0x18);
            if (callback && run.get(run.get(receiver + 0x10) + 0x1c) == run.get(receiver + 0x1c)) {
                dynamicCall(run, fp, callback, receiver);
                run.put(receiver + 0x18, 0);
            }
            dynamicCall(run, fp, run.get(receiver + 0x14), receiver);
            run.put(receiver + 0x14, 0);
            run.put(receiver + 0x1c, 0x3e9);
        }
        return dynamicVirtual(run, fp, receiver, 0x24);
    case 0x43d490:
        return dispatch(run, receiver, arguments[0], fp);
    case 0x43dfa0:
        return motion(run, receiver, fp);
    case 0x43e420:
        return choose(run, receiver, fp);
    // 0x43e9b0.
    case 0x43e9b0:
        return run.call(0x48cf50, 0, {run.get(receiver + 0x0c)});
    // 0x4dc830.
    case 0x4dc830:
        dynamicVirtual(run, fp, run.get(run.get(arguments[0] + 0x6c) + 0x18), 0x14);
        return 1;
    case 0x4dca10:
        return integrate(run, receiver, fp);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

// Query and publish only the outer entry; internal owned calls borrow its state.
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    FP fp;
    if (function == 0x43e9b0) {
        return ownedBody(run, function, receiver, arguments, fp);
    }
    fp.state = run.x87_entry(function);
    uint32_t result = ownedBody(run, function, receiver, arguments, fp);
    run.x87_finish(function, fp.state);
    return result;
}
}
CLAW_MODULE_ENTRY(claw_level_one_enemy_actions_entry, owned, body)
