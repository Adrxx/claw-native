// Original v1.0 actor dispatch and geometry entries.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x402ca0:
    case 0x402cc0:
    case 0x402e20:
    case 0x4061b0:
    case 0x4061e0:
    case 0x4062e0:
        return 1;
    case 0x403b40:
        return 2;
    case 0x405000:
    case 0x4060b0:
    case 0x406290:
        return 0;
    default:
        return -1;
    }
}

// 0x402cc0. Actor +0x6c is its dispatch state, +0x184 its sound descriptor.
uint32_t function_402cc0(Run &run, uint32_t actor) {
    uint32_t state = run.get(actor + 0x6c);
    if (run.get(state + 0x1c) == 0) {
        uint32_t flags = run.get(actor + 0x08) | 1;
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
        run.put(actor + 0x08, flags);
        if (run.get(state + 0x10) == 0x402ca0)
            flags |= 2;
        else
            flags &= ~2u;
        uint32_t sound = run.get(actor + 0x184);
        run.put(actor + 0x08, flags);
        if (sound && run.get(0x5371fc)) {
            uint32_t rect = run.automatic(-0x10);
            run.icall(0x546d58, {rect, actor + 0x128});
            uint32_t left = run.get(state + 0x2c);
            if (s32(left) > 0 || s32(run.get(state + 0x30)) > 0)
                run.icall(0x546d5c, {rect, left, run.get(state + 0x34), run.get(state + 0x30), run.get(state + 0x38)});
            uint32_t manager = run.get(run.get(0x5371fc) + 0x5c);
            if (manager) {
                uint32_t result;
                uint32_t height = run.get(actor + 0x11c);
                if (s32(height) > 0)
                    result = run.call(0x402400, manager, {run.get(sound + 0x10), 100, rect, run.get(actor + 0x104), run.get(actor + 0x118), height, run.get(actor + 0x120), run.get(actor + 0x124), 0});
                else
                    result = run.call(0x4022f0, manager, {run.get(sound + 0x10), 100, rect, run.get(actor + 0x104), 0});
                if (result && s32(run.get(actor + 0x13c)) > 0) {
                    run.put(result + 0x28, run.get(actor + 0x138));
                    run.put(result + 0x2c, run.get(actor + 0x13c));
                    run.put(result + 0x30, run.get(actor + 0x140));
                    run.put(result + 0x34, run.get(actor + 0x144));
                }
            }
        }
        run.put(actor + 0x08, run.get(actor + 0x08) | 0x10000);
        run.put(state + 0x1c, 5);
    }
    return 1;
}

// 0x402ca0. The nested cdecl call has an entry frame eight bytes lower.
uint32_t function_402ca0(Run &run, uint32_t actor) {
    run.put(0x534810, 1);
    uint32_t frame = run.frame;
    run.frame -= 0x08;
    uint32_t result = function_402cc0(run, actor);
    run.frame = frame;
    return result;
}

// 0x402e20. State +0x168 retains the point-sound instance.
uint32_t function_402e20(Run &run, uint32_t actor) {
    uint32_t state = run.get(actor + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase == 0) {
        uint32_t flags = (run.get(actor + 0x08) & ~2u) | 0x100001;
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
        run.put(actor + 0x08, flags);
        run.put(state + 0x168, 0);
        uint32_t sound = run.get(actor + 0x184);
        if (sound && run.get(0x5371fc)) {
            uint32_t manager = run.get(run.get(0x5371fc) + 0x5c);
            if (manager) {
                uint32_t point = run.automatic(-0x08);
                run.put(point, run.get(actor + 0x4c));
                run.put(point + 0x04, run.get(actor + 0x50));
                uint32_t instance = run.call(0x402370, manager, {run.get(sound + 0x10), 100, point, run.get(actor + 0x104), 0});
                if (instance)
                    run.put(state + 0x168, instance);
            }
        }
        run.put(state + 0x1c, 5);
    } else if (phase == 0x1e) {
        uint32_t instance = run.get(state + 0x168);
        if (instance) {
            uint32_t manager = run.get(run.get(0x5371fc) + 0x5c);
            uint32_t channel = run.get(instance + 0x04);
            if (channel) {
                run.call(0x4b3e30, channel, {});
                run.put(instance + 0x14, 0);
            }
            uint32_t node = run.get(instance + 0x3c);
            if (node) {
                run.call(0x4f5212, manager + 0x08, {node});
                run.vcall(instance, 0x00, {1});
            }
            run.put(state + 0x168, 0);
            run.put(state + 0x1c, 0);
        }
    }
    return 1;
}

// Exact instructions carry the inherited status and lower live registers.
struct PhysicsFP {
    Run &run;
    ClawX87State &state;

    void step(uint32_t operation) {
        run.x87_step(operation, state);
    }
    void memory(uint32_t operation, uint32_t address) {
        run.x87_step(operation, state, {run.get(address), run.get(address + 0x04)});
    }
    void load(uint32_t address) {
        memory(CLAW_X87_F64, address);
    }
    uint64_t stored(bool pop) {
        return run.x87_step(pop ? CLAW_X87_STP_F64 : CLAW_X87_ST_F64, state);
    }
    void store(uint32_t address, bool pop) {
        uint64_t bits = stored(pop);
        run.put(address, uint32_t(bits));
        run.put(address + 0x04, uint32_t(bits >> 32));
    }
    void reg(uint32_t operation, uint32_t index) {
        step(CLAW_X87_ST(operation, index));
    }
    bool condition(uint32_t mask) const {
        return (state.status & mask) != 0;
    }
    void nonnegativeRoot(uint32_t velocity) {
        if (!condition(0x4100)) {
            step(CLAW_X87_POP);
            load(0x50b098);
        }
        step(CLAW_X87_SQRT);
        load(velocity);
        memory(CLAW_X87_COMP_F64, 0x50b098);
        if (condition(0x4100)) {
            step(CLAW_X87_CHS);
        }
    }
};

// 0x403b5d, 0x403d71 and 0x403f85: three parallel axes. The
// first two retain delta time below their temporaries; the last consumes it.
void axis(Run &run, PhysicsFP &fp, uint32_t object, uint32_t offset) {
    const uint32_t a = object + offset;
    fp.reg(CLAW_X87_LD_ST, 0);
    fp.memory(CLAW_X87_MUL_F64, a + 0x10);
    uint64_t increment = fp.stored(false);
    fp.memory(CLAW_X87_MUL_F64, 0x50b090);
    fp.memory(CLAW_X87_SUBR_F64, a + 0x28);
    fp.reg(offset == 0x10 ? CLAW_X87_MULP : CLAW_X87_MUL_TO0, 1);
    fp.memory(CLAW_X87_COM_F64, a + 0xc0);
    fp.store(a + 0x88, false);
    bool clamp = !fp.condition(0x4100);
    if (clamp) {
        fp.step(CLAW_X87_POP);
        fp.load(a + 0xc0);
    } else {
        fp.load(a + 0xc0);
        fp.step(CLAW_X87_CHS);
        fp.reg(CLAW_X87_XCH_ST, 1);
        fp.reg(CLAW_X87_COMP_ST, 1);
        clamp = fp.condition(0x0100);
    }
    if (clamp) {
        fp.load(a + 0x10);
        fp.memory(CLAW_X87_COMP_F64, 0x50b098);
        fp.reg(CLAW_X87_LD_ST, 0);
        fp.memory(CLAW_X87_ADD_F64, a + 0x40);
        fp.reg(CLAW_X87_XCH_ST, 1);
        fp.store(a + 0x88, true);
        if (fp.condition(0x4000)) {
            fp.step(CLAW_X87_POP);
            fp.load(a + 0x28);
            fp.store(a + 0x28, true);
        } else {
            fp.memory(CLAW_X87_SUB_F64, a + 0x40);
            fp.load(a + 0x28);
            fp.load(0x50b098);
            fp.reg(CLAW_X87_XCH_ST, 2);
            fp.memory(CLAW_X87_MUL_F64, a + 0x10);
            fp.reg(CLAW_X87_LD_ST, 1);
            fp.reg(CLAW_X87_MULP, 2);
            fp.memory(CLAW_X87_MUL_F64, 0x50b0a0);
            fp.reg(CLAW_X87_SUBP, 1);
            fp.reg(CLAW_X87_XCH_ST, 1);
            fp.reg(CLAW_X87_COMP_ST, 1);
            fp.nonnegativeRoot(a + 0x28);
            fp.store(a + 0x28, true);
        }
    } else {
        fp.step(CLAW_X87_POP);
    }
    // The middle axis loads displacement first; preserve operand order.
    fp.load(a + (offset == 0x08 ? 0x88 : 0x40));
    fp.memory(CLAW_X87_ADD_F64, a + (offset == 0x08 ? 0x40 : 0x88));
    fp.load(a + 0x40);
    fp.reg(CLAW_X87_XCH_ST, 1);
    fp.store(a + 0x40, false);
    fp.memory(CLAW_X87_COM_F64, a + 0x70);
    uint32_t boundary = 0;
    if (!fp.condition(0x4100)) {
        boundary = 0x70;
    } else {
        fp.memory(CLAW_X87_COM_F64, a + 0x58);
        if (fp.condition(0x0100)) {
            boundary = 0x58;
        }
    }
    if (boundary) {
        fp.load(a + 0x10);
        fp.memory(CLAW_X87_COMP_F64, 0x50b098);
        fp.load(a + boundary);
        if (fp.condition(0x4000)) {
            fp.step(CLAW_X87_POP);
            fp.step(CLAW_X87_POP);
            fp.load(a + 0x28);
        } else {
            fp.reg(CLAW_X87_SUB_TO0, 1);
            fp.load(a + 0x28);
            fp.load(0x50b098);
            fp.reg(CLAW_X87_XCH_ST, 2);
            fp.memory(CLAW_X87_MUL_F64, a + 0x10);
            fp.reg(CLAW_X87_XCH_ST, 1);
            fp.reg(CLAW_X87_STP_ST, 3);
            fp.reg(CLAW_X87_LD_ST, 2);
            fp.reg(CLAW_X87_MULP, 3);
            fp.memory(CLAW_X87_MUL_F64, 0x50b0a0);
            fp.reg(CLAW_X87_SUBP, 2);
            fp.reg(CLAW_X87_COMP_ST, 1);
            fp.nonnegativeRoot(a + 0x28);
        }
        fp.load(a + boundary);
        const uint32_t low = run.get(a + boundary);
        const uint32_t high = run.get(a + boundary + 0x04);
        fp.reg(CLAW_X87_SUB_TO0, 2);
        fp.reg(CLAW_X87_XCH_ST, 1);
        fp.store(a + 0x28, true);
        run.put(a + 0x40, low);
        run.put(a + 0x44, high);
        fp.store(a + 0x88, true);
        fp.step(CLAW_X87_POP);
    } else {
        fp.step(CLAW_X87_POP);
        fp.step(CLAW_X87_POP);
        run.x87_step(CLAW_X87_F64, fp.state, {uint32_t(increment), uint32_t(increment >> 32)});
        fp.memory(CLAW_X87_ADD_F64, a + 0x28);
        fp.store(a + 0x28, true);
    }
    fp.load(a + 0x28);
    fp.memory(CLAW_X87_COMP_F64, a + 0xd8);
    if (!fp.condition(0x4100)) {
        const uint32_t low = run.get(a + 0xd8);
        const uint32_t high = run.get(a + 0xdc);
        run.put(a + 0x28, low);
        run.put(a + 0x2c, high);
    }
}

// 0x403b40. +0xa0 disables integration after the clock stores.
uint32_t function_403b40(Run &run, uint32_t object, const uint32_t *arguments) {
    auto state = run.x87_entry(0x403b40);
    PhysicsFP fp{run, state};
    run.x87_step(CLAW_X87_F64, state, {arguments[0], arguments[1]});
    const uint32_t disabled = run.get(object + 0xa0);
    fp.reg(CLAW_X87_LD_ST, 0);
    fp.memory(CLAW_X87_ADD_F64, object);
    fp.reg(CLAW_X87_LD_ST, 1);
    fp.store(object + 0x08, true);
    fp.store(object, true);
    if (disabled) {
        fp.step(CLAW_X87_POP);
    } else {
        axis(run, fp, object, 0x00);
        axis(run, fp, object, 0x08);
        axis(run, fp, object, 0x10);
    }
    run.x87_finish(0x403b40, state);
    return 0;
}

// 0x405000. +0x0c points to the rectangle owner, +0x12c to flags.
uint32_t function_405000(Run &run, uint32_t actor) {
    uint32_t destination = run.get(actor + 0x0c) + 0x138;
    run.put(destination, run.get(actor + 0x210));
    run.put(destination + 0x04, run.get(actor + 0x214));
    run.put(destination + 0x08, run.get(actor + 0x218));
    run.put(destination + 0x0c, run.get(actor + 0x21c));
    if (run.get8(run.get(actor + 0x12c) + 0x40) & 2) {
        uint32_t owner = run.get(actor + 0x0c);
        uint32_t right = run.get(owner + 0x140);
        uint32_t left = run.get(owner + 0x138);
        run.put(owner + 0x138, 0u - right);
        run.put(run.get(actor + 0x0c) + 0x140, 0u - left);
    }
    return 0;
}

// 0x4060b0. Three rectangles use INT_MIN left as their absent sentinel.
uint32_t function_4060b0(Run &run, uint32_t actor) {
    for (uint32_t offset : {0x118u, 0x128u, 0x138u}) {
        uint32_t left = run.get(actor + offset);
        if (left != 0x80000000) {
            uint32_t right = run.get(actor + offset + 0x08);
            run.put(actor + offset, 0u - right);
            run.put(actor + offset + 0x08, 0u - left);
        }
    }
    return 0;
}

// 0x4061b0. Local result is four bytes below entry ESP.
uint32_t function_4061b0(Run &run, uint32_t actor, uint32_t key) {
    uint32_t result = run.automatic(-0x04);
    run.put(result, 0);
    run.call(0x4f6286, actor + 0x10, {key, result});
    return run.get(result);
}

// 0x4061e0. Reload sprite +0x174 after every output store to preserve aliasing.
uint32_t function_4061e0(Run &run, uint32_t actor, uint32_t output) {
    uint32_t sprite = run.get(actor + 0x174);
    if (!sprite)
        return 0;
    uint32_t left = run.get(sprite + 0x18);
    run.put(output, run.get(sprite + 0x20) - left);
    sprite = run.get(actor + 0x174);
    uint32_t top = run.get(sprite + 0x1c);
    run.put(output + 0x04, run.get(sprite + 0x24) - top);
    sprite = run.get(actor + 0x174);
    left = run.get(sprite + 0x18);
    run.put(output + 0x08, run.get(sprite + 0x20) + left - 1);
    sprite = run.get(actor + 0x174);
    top = run.get(sprite + 0x1c);
    run.put(output + 0x0c, run.get(sprite + 0x24) + top - 1);
    return 1;
}

// 0x406290. This variant keeps its initial sprite pointer across stores.
uint32_t function_406290(Run &run, uint32_t actor) {
    uint32_t sprite = run.get(actor + 0x174);
    if (sprite) {
        run.put(actor + 0x118, run.get(sprite + 0x20) - run.get(sprite + 0x18));
        run.put(actor + 0x11c, run.get(sprite + 0x24) - run.get(sprite + 0x1c));
        run.put(actor + 0x120, run.get(sprite + 0x18) + run.get(sprite + 0x20) - 1);
        run.put(actor + 0x124, run.get(sprite + 0x24) + run.get(sprite + 0x1c) - 1);
    }
    return 0;
}

// 0x4062e0. Shared lookup follows actor +0x04, +0x0c, +0x2c.
uint32_t function_4062e0(Run &run, uint32_t actor, uint32_t key) {
    uint32_t result = run.automatic(-0x04);
    uint32_t owner = run.get(actor + 0x04);
    run.put(result, 0);
    uint32_t table = run.get(run.get(owner + 0x0c) + 0x2c) + 0x10;
    run.call(0x4f6286, table, {key, result});
    return run.get(result);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x402ca0:
        return function_402ca0(run, arguments[0]);
    case 0x402cc0:
        return function_402cc0(run, arguments[0]);
    case 0x402e20:
        return function_402e20(run, arguments[0]);
    case 0x403b40:
        return function_403b40(run, receiver, arguments);
    case 0x405000:
        return function_405000(run, receiver);
    case 0x4060b0:
        return function_4060b0(run, receiver);
    case 0x4061b0:
        return function_4061b0(run, receiver, arguments[0]);
    case 0x4061e0:
        return function_4061e0(run, receiver, arguments[0]);
    case 0x406290:
        return function_406290(run, receiver);
    case 0x4062e0:
        return function_4062e0(run, receiver, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_one_actor_dispatch_01_entry, owned, body)
