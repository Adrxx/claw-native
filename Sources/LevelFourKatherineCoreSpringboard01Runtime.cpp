#include "ClawRuntime.hpp"
namespace {
using claw::Run;
using claw::s32;
int owned(uint32_t function) {
    switch(function) {
    case 0x41e810: return 2;
    case 0x454310: return 0;
    case 0x453d30: case 0x453df0: case 0x4542f0: case 0x4543e0: case 0x4547c0: case 0x4548c0: return 1;
    default: return -1;
    }
}
struct Arithmetic {
    Run &run;
    ClawX87State state{};
    explicit Arithmetic(Run &run) : run(run) {
        state.size = sizeof(state);
        state.version = CLAW_X87_VERSION;
        state.control = 0x023f;
    }
    void op(uint32_t code) {
        run.x87_step(code, state);
    }
    void bits(uint32_t code, uint64_t value) {
        run.x87_step(code, state, {uint32_t(value), uint32_t(value >> 32)});
    }
    void mem(uint32_t code, uint32_t address) {
        bits(code, uint64_t(run.get(address)) | (uint64_t(run.get(address + 4)) << 32));
    }
    void integer(uint32_t value) {
        run.x87_step(CLAW_X87_I32, state, {value});
    }
    void real(double value) {
        uint64_t bitsValue;
        std::memcpy(&bitsValue, &value, sizeof(bitsValue));
        bits(CLAW_X87_F64, bitsValue);
    }
    uint64_t store(bool pop) {
        return run.x87_step(pop ? CLAW_X87_STP_F64 : CLAW_X87_ST_F64, state);
    }
    void store(uint32_t address, bool pop) {
        uint64_t value = store(pop);
        run.put(address, uint32_t(value));
        run.put(address + 4, uint32_t(value >> 32));
    }
    uint32_t convert() {
        state.popCount = 1;
        state.pushCount = 0;
        state.returned = 0;
        state.eax = 0;
        state.edx = 0;
        return run.call_x87_exact(0x4a30e0, 0, state);
    }
};
uint32_t function_453df0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_454310(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_453d30(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    uint32_t behavior = run.get(actor + 0x6c);
    uint32_t command = run.get(behavior + 0x1c);
    if (command == 0) {
        run.put(behavior + 0x1c, 1000);
        uint32_t object = run.call(0x4f63ec, 0, {0x478});
        if (object) {
            uint32_t args[] = {actor};
            uint32_t saved = run.frame;
            run.frame -= 0x1c;
            object = function_453df0(run, object, args);
            run.frame = saved;
        }
        run.vcall(object, 0x10);
        run.put(behavior + 0x18, object);
    } else if (command == 0x1d) {
        run.vcall(run.get(behavior + 0x18), 0x20);
    } else if (command == 0x1e) {
        run.vcall(run.get(behavior + 0x18), 0x1c);
    } else if (command != 1000) {
        run.call(0x4dc870, 0, {run.get(behavior + 0x18)});
    }
    return 1;
}
uint32_t function_453df0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    Arithmetic math(run);
    math.state.popCount = 0;
    math.state.pushCount = 0;
    run.call_x87_exact(0x40e0d0, receiver, math.state, {arguments[0]});
    run.put(receiver + 0x46c, 0);
    run.put(receiver + 0x470, 0);
    run.put(receiver, 0x50e2a4);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x528444});
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x52842c});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x30c, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x52842c});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x308, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x528414});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x310, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x5283fc});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x32c, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x5283fc});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x374, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x5283e4});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x334, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x5283cc});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x338, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x5283b4});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x344, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x52842c});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x34c, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x52839c});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x350, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x528384});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x378, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x52836c});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x37c, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x528354});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x460, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x52833c});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x464, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x528324});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x468, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x52836c});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x380, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x52830c});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x36c, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x5282f0});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x384, value);
    }
    {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {0x5282d4});
        if (!value) value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + 0x388, value);
    }
    run.put(run.automatic(4), 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0x0c) + 0x28) + 0x10, {0x5282b8, run.automatic(4)});
    run.put(receiver + 0x3a4, run.get(run.automatic(4)));
    uint32_t asset = run.call(0x4061b0, run.get(run.get(run.get(receiver + 0x12c) + 0x0c) + 0x28), {0x52829c});
    run.put(receiver + 0x410, asset);
    run.put(receiver + 0x290, 40);
    run.put(receiver + 0x298, 40);
    run.put(receiver + 0x2a0, 40);
    run.put(receiver + 0x2a8, 40);
    run.put(receiver + 0x2b0, 40);
    run.put(receiver + 0x28c, 500);
    run.put(receiver + 0x294, 200);
    run.put(receiver + 0x29c, 200);
    run.put(receiver + 0x2a4, 100);
    run.put(receiver + 0x2ac, 50);
    run.put(receiver + 0x400, 200);
    run.put(receiver + 0x404, 200);
    run.icall(0x546d5c, {receiver + 0x220, 0xffffff51, 0xffffffea, 0xfffffff3, 9});
    run.icall(0x546d5c, {receiver + 0x210, 0xffffffff, 0xffffffff, 1, 1});
    run.icall(0x546d5c, {receiver + 0x250, 0xfffffff1, 0xffffffce, 15, 50});
    run.icall(0x546d5c, {receiver + 0x260, 0xfffffff1, 0xffffffd8, 15, 40});
    run.put(receiver + 0x2bc, 0xffffffc4);
    run.put(receiver + 0x2b4, 0x0);
    run.put(receiver + 0x2b8, 0x0);
    run.put(receiver + 0x2c0, 0xffffffec);
    run.put(receiver + 0x2c4, 0x14);
    run.put(receiver + 0x2c8, 0xfffffff1);
    run.put(receiver + 0x2e4, 0x32);
    math.real(run.getf(0x5262b8));
    math.real(run.getf(0x50e268));
    math.op(CLAW_X87_MULP + 1);
    uint32_t count = math.convert();
    if (count <= 99) count = 99;
    run.put(receiver + 0x2e4, count);
    run.put(run.get(receiver + 0x0c) + 0x10c, 100);
    uint32_t actor = run.get(receiver + 0x0c);
    math.integer(run.get(actor + 0x10c));
    math.real(run.getf(0x5262b4));
    math.op(CLAW_X87_MULP + 1);
    uint32_t health = math.convert();
    run.put(actor + 0x10c, health);
    run.put(run.get(receiver + 0x0c) + 0x104, 10);
    actor = run.get(receiver + 0x0c);
    math.integer(run.get(actor + 0x104));
    math.real(run.getf(0x5262b0));
    math.op(CLAW_X87_MULP + 1);
    uint32_t damage = math.convert();
    run.put(actor + 0x104, damage);
    run.call(0x40f6c0, run.get(receiver + 0x12c), {run.get(receiver + 0x250), run.get(receiver + 0x254), run.get(receiver + 0x258), run.get(receiver + 0x25c)});
    run.call(0x4208b0, run.get(receiver + 0x12c), {0xffffffec, 0xffffffce, 20, 50});
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x50, run.get(actor + 0x50) - 32);
    actor = run.get(receiver + 0x128);
    run.call(0x4cd800, run.get(run.get(actor + 0x0c) + 0x24), {actor, 0});
    run.put(run.get(receiver + 0x128) + 0xcc, 1);
    run.call(0x405060, receiver);
    return receiver;
}
uint32_t function_454310(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}
uint32_t function_4542f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_454310(run, receiver, arguments);
    if (arguments[0] & 1) run.call(0x4f6428, 0, {receiver});
    return receiver;
}
uint32_t record(Run &run, uint32_t index) {
    if (s32(index) < run.gets(0x537988) || s32(index) > run.gets(0x53798c)) {
        if (!run.call(0x4db6e0, 0x537980, {index, 0})) {
            uint32_t diagnostic = run.get(0x544b4c);
            uint32_t code = run.call(0x4db5f0, 0);
            run.put(0x544b14, code);
            run.call(0x4db4d0, run.get(0x537984), {0x537980, diagnostic, 12});
            return run.get(0x537994);
        }
    }
    return (index - run.get(0x537988)) * run.get(0x537998) + run.get(0x537990);
}
uint32_t function_4543e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[0];
    run.put(0x5379a0, 0);
    uint32_t selected = record(run, index);
    if (run.get(selected)) {
        run.put(0x5379a0, 0);
        selected = record(run, index);
        run.call(run.get(selected), receiver);
    } else {
        run.call(0x40e280, receiver, {index});
    }
    return 0;
}
uint32_t function_4547c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t token = arguments[0];
    run.call(0x44d000, receiver, {token});
    int32_t random = s32(run.call(0x4a3050, 0)) % 2;
    if (random == 0 || random == 1) {
        run.put(run.automatic(4), 0);
        run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0x0c) + 0x28) + 0x10, {random == 0 ? 0x52846cu : 0x528484u, run.automatic(4)});
        run.put(receiver + 0x3bc, run.get(run.automatic(4)));
    }
    uint32_t player = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (!run.get(player + 4)) return 0;
    uint32_t facing = run.get(receiver + 0x18c);
    if (!((facing == 3 && run.get(player)) || (facing == 2 && !run.get(player)))) return 0;
    uint32_t animation = run.get(receiver + 0x184);
    if (animation != 3 && animation != 4) return 0;
    if (token == 0x527204 || token == 0x528454 || token == 0x52720c) return 0;
    int32_t distance = run.gets(receiver + 0x3c4);
    if (distance >= 0 && distance < 200 && run.gets(receiver + 0x20) >= 2) {
        run.put(receiver + 0x14, 0x455350);
    }
    return 0;
}
uint32_t stateString(Run &run, uint32_t receiver) {
    uint32_t result = run.call(0x441030, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
    uint32_t entries = run.get(0x5376b4);
    uint32_t count = run.get(0x5376b8);
    while (count--) {
        if (entries) run.call(0x4f6439, entries);
        entries += 4;
    }
    return run.get(result);
}
uint32_t function_4548c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x43e9c0, receiver, {500});
    uint32_t name = stateString(run, receiver);
    if (!run.call(0x4a3810, 0, {name, 0x523204})) {
        run.vcall(receiver, 0x44);
        return 0;
    }
    name = stateString(run, receiver);
    if (!run.call(0x4a3810, 0, {name, 0x523210})) {
        run.vcall(receiver, 0x44);
        return 0;
    }
    int32_t distance = run.gets(receiver + 0x3c4);
    if (distance >= 0 && distance < 500) {
        run.vcall(receiver, 0x9c);
        return 0;
    }
    if (distance >= 500 && distance < 600) {
        run.vcall(receiver, 0x9c);
        return 0;
    }
    uint32_t player = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    run.call(run.get(player + 0x14) ? 0x44f510 : 0x44f3c0, receiver);
    run.vcall(receiver, 0x28, {arguments[0]});
    run.call(0x440e20, receiver, {arguments[0]});
    return 0;
}

uint32_t function_41e810(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    if (run.get(actor + 0xd0) != 2) return 0;
    uint32_t behavior = run.get(actor + 0x6c);
    uint32_t command = run.get(behavior + 0x1c);
    if (command == 0x1c || command == 0x138d || command == 0x138c) return 0;
    uint32_t board = run.get(behavior + 0x14);
    if (!board) return 0;
    run.call(0x41c4e0, 0, {actor, behavior, board});
    run.put(behavior + 0x1c, 4);
    run.call(0x4c79e0, actor, {0x5246a8, 0});
    uint32_t flags = run.get(actor + 0x08) & 0xffffffef;
    run.put(actor + 0xcc, 3);
    run.put(actor + 0x148, 0);
    run.put(actor + 0x14c, 0);
    run.put(actor + 0x08, flags);
    if (run.get(board)) {
        run.call(0x4208b0, actor, {0xffffffea, 0xffffffd3, 15, 52});
    } else {
        run.call(0x4208b0, actor, {0xfffffff1, 0xffffffd3, 22, 52});
    }
    run.call(0x4170b0, 0, {actor, board});
    if (run.get(0x534eac) == 0x26bc) {
        run.putd(0x534de8, -500.0);
    } else {
        uint32_t enabled = run.get(board + 0x114);
        run.putd(0x534de8, -500.0);
        if (enabled) run.put(0x534dec, 0xc07a9000);
    }
    uint64_t initial = uint64_t(run.get(0x50baa8)) | (uint64_t(run.get(0x50baac)) << 32);
    run.put(board + 0x118, 250);
    run.put(board + 0x5c, 0);
    run.put(board + 0x60, run.get(actor + 0x50));
    uint32_t top = run.get(actor + 0x50) - 45;
    run.put(board + 0x10c, 0);
    run.put(board + 0x64, top);
    run.put(0x534dd0, uint32_t(initial));
    run.put(0x534dd4, uint32_t(initial >> 32));
    run.putd(0x534df8, double(run.gets(actor + 0x4c)));
    run.putd(0x534e00, double(run.gets(actor + 0x50)));
    double boardY = double(run.gets(board + 0x64));
    uint64_t yBits;
    std::memcpy(&yBits, &boardY, sizeof(yBits));
    Arithmetic math(run);
    math.state.popCount = 0;
    math.state.pushCount = 1;
    run.call_x87_exact(0x420dd0, 0x534db8, math.state, {run.get(0x534df8), run.get(0x534dfc), uint32_t(yBits), uint32_t(yBits >> 32), 0, 0});
    run.put(board + 0x118, 0);
    run.put(board + 0x5c, 0);
    run.put(board + 0x60, run.get(actor + 0x50));
    run.put(board + 0x64, run.get(actor + 0x50) - arguments[1]);
    uint64_t local10 = 0, local18 = 0, local20 = 0, local28 = 0, local30 = 0, local38 = 0;
    math.integer(run.get(actor + 0x4c));
    math.mem(CLAW_X87_F64, 0x50ba88);
    math.mem(CLAW_X87_F64, 0x534e08);
    math.op(CLAW_X87_XCH_ST + 2);
    math.store(0x534df8, true);
    math.integer(run.get(actor + 0x50));
    math.mem(CLAW_X87_F64, 0x534dc8);
    math.mem(CLAW_X87_F64, 0x534dd0);
    math.op(CLAW_X87_XCH_ST + 5);
    math.op(CLAW_X87_STP_ST + 0);
    math.op(CLAW_X87_XCH_ST + 1);
    math.store(0x534e00, true);
    math.integer(run.get(board + 0x64));
    math.op(CLAW_X87_XCH_ST + 1);
    math.mem(CLAW_X87_MUL_F64, 0x534dc8);
    math.op(CLAW_X87_XCH_ST + 2);
    local18 = math.store(true);
    math.mem(CLAW_X87_SUB_F64, 0x534e00);
    math.bits(CLAW_X87_F64, local18);
    math.op(CLAW_X87_XCH_ST + 4);
    math.mem(CLAW_X87_MUL_F64, 0x534dd0);
    math.mem(CLAW_X87_F64, 0x534dd8);
    math.op(CLAW_X87_XCH_ST + 2);
    local20 = math.store(false);
    math.op(CLAW_X87_XCH_ST + 4);
    math.op(CLAW_X87_CHS);
    local28 = math.store(false);
    math.bits(CLAW_X87_F64, local18);
    math.mem(CLAW_X87_MUL_F64, 0x534dc8);
    math.op(CLAW_X87_CHS);
    math.bits(CLAW_X87_F64, local20);
    math.mem(CLAW_X87_MUL_F64, 0x534dd0);
    math.op(CLAW_X87_SUBP + 1);
    math.bits(CLAW_X87_F64, local28);
    math.mem(CLAW_X87_MUL_F64, 0x534dd8);
    math.op(CLAW_X87_SUBP + 1);
    local38 = math.store(true);
    math.op(CLAW_X87_XCH_ST + 1);
    math.op(CLAW_X87_ADDP + 3);
    math.op(CLAW_X87_XCH_ST + 4);
    math.bits(CLAW_X87_MUL_F64, local18);
    math.bits(CLAW_X87_F64, local38);
    math.op(CLAW_X87_XCH_ST + 2);
    math.mem(CLAW_X87_MUL_F64, 0x534dd8);
    math.op(CLAW_X87_ADDP + 3);
    math.op(CLAW_X87_XCH_ST + 3);
    math.bits(CLAW_X87_MUL_F64, local20);
    math.op(CLAW_X87_XCH_ST + 2);
    local30 = math.store(true);
    math.op(CLAW_X87_XCH_ST + 1);
    math.op(CLAW_X87_ADDP + 2);
    math.op(CLAW_X87_XCH_ST + 2);
    math.bits(CLAW_X87_MUL_F64, local28);
    math.op(CLAW_X87_XCH_ST + 2);
    math.mem(CLAW_X87_MUL_F64, 0x50bac8);
    math.op(CLAW_X87_XCH_ST + 2);
    math.op(CLAW_X87_ADDP + 1);
    math.bits(CLAW_X87_MUL_F64, local30);
    math.mem(CLAW_X87_MUL_F64, 0x50bac0);
    math.op(CLAW_X87_SQRT);
    math.op(CLAW_X87_XCH_ST + 1);
    math.op(CLAW_X87_SUBP + 1);
    math.mem(CLAW_X87_MUL_F64, 0x50bad0);
    math.op(CLAW_X87_SQRT);
    local10 = math.store(false);
    math.mem(CLAW_X87_COMP_F64, 0x513e20);
    if (math.state.status & 0x100) {
        run.putd(0x534de0, 0.0);
        run.putd(0x534de8, 0.0);
        run.putd(0x534df0, 0.0);
        return 0;
    }
    math.bits(CLAW_X87_F64, local30);
    math.mem(CLAW_X87_MUL_F64, 0x50bad8);
    math.mem(CLAW_X87_F64, 0x513e20);
    math.op(CLAW_X87_CHS);
    math.op(CLAW_X87_LD_ST + 1);
    math.op(CLAW_X87_COMPP);
    bool negative = (math.state.status & 0x100) != 0;
    math.mem(CLAW_X87_COM_F64, 0x513e20);
    bool positive = !(math.state.status & 0x4100);
    if (!negative && !positive) {
    math.op(CLAW_X87_STP_ST + 0);
    math.bits(CLAW_X87_F64, local20);
    math.bits(CLAW_X87_F64, local18);
    math.bits(CLAW_X87_F64, local28);
    math.op(CLAW_X87_XCH_ST + 2);
    math.op(CLAW_X87_ABS);
    math.op(CLAW_X87_XCH_ST + 1);
    math.op(CLAW_X87_ABS);
    math.op(CLAW_X87_ADDP + 1);
    math.op(CLAW_X87_XCH_ST + 1);
    math.op(CLAW_X87_ABS);
    math.bits(CLAW_X87_F64, local18);
    math.op(CLAW_X87_XCH_ST + 1);
    math.op(CLAW_X87_ADDP + 2);
    math.bits(CLAW_X87_F64, local20);
    math.bits(CLAW_X87_F64, local28);
    math.op(CLAW_X87_XCH_ST + 2);
    math.op(CLAW_X87_DIV_TO0 + 3);
    math.op(CLAW_X87_XCH_ST + 1);
    math.op(CLAW_X87_DIV_TO0 + 3);
    math.op(CLAW_X87_XCH_ST + 2);
    math.op(CLAW_X87_DIV_TO0 + 3);
    math.op(CLAW_X87_XCH_ST + 1);
    math.bits(CLAW_X87_MUL_F64, local10);
    math.op(CLAW_X87_XCH_ST + 2);
    math.bits(CLAW_X87_MUL_F64, local10);
    math.op(CLAW_X87_XCH_ST + 1);
    math.bits(CLAW_X87_MUL_F64, local10);
    math.op(CLAW_X87_XCH_ST + 2);
    math.store(0x534de0, true);
    } else {
    math.bits(CLAW_X87_F64, local10);
    math.bits(CLAW_X87_MUL_F64, local10);
    math.op(CLAW_X87_XCH_ST + 1);
    math.op(CLAW_X87_ADD_TOI + 0);
    math.op(CLAW_X87_XCH_ST + 1);
    math.bits(CLAW_X87_SUB_F64, local38);
    math.op(CLAW_X87_XCH_ST + 1);
    math.op(CLAW_X87_DIVP + 1);
    math.op(CLAW_X87_LD_ST + 0);
    math.op(CLAW_X87_SQRT);
    math.op(CLAW_X87_LD_ST + 1);
    math.op(CLAW_X87_LD_ST + 2);
    math.op(CLAW_X87_XCH_ST + 1);
    math.mem(CLAW_X87_MUL_F64, 0x534dc8);
    math.op(CLAW_X87_XCH_ST + 2);
    math.op(CLAW_X87_XCH_ST + 3);
    math.op(CLAW_X87_XCH_ST + 1);
    math.mem(CLAW_X87_MUL_F64, 0x534dd0);
    math.op(CLAW_X87_XCH_ST + 1);
    math.mem(CLAW_X87_MUL_F64, 0x534dd8);
    math.op(CLAW_X87_XCH_ST + 2);
    math.mem(CLAW_X87_MUL_F64, 0x50bad0);
    math.op(CLAW_X87_XCH_ST + 1);
    math.mem(CLAW_X87_MUL_F64, 0x50bad0);
    math.op(CLAW_X87_XCH_ST + 1);
    math.bits(CLAW_X87_SUBR_F64, local18);
    math.op(CLAW_X87_XCH_ST + 2);
    math.mem(CLAW_X87_MUL_F64, 0x50bad0);
    math.op(CLAW_X87_XCH_ST + 1);
    math.bits(CLAW_X87_SUBR_F64, local20);
    math.op(CLAW_X87_XCH_ST + 1);
    math.bits(CLAW_X87_SUBR_F64, local28);
    math.op(CLAW_X87_XCH_ST + 2);
    math.op(CLAW_X87_DIV_TO0 + 3);
    math.op(CLAW_X87_XCH_ST + 1);
    math.op(CLAW_X87_DIV_TO0 + 3);
    math.op(CLAW_X87_XCH_ST + 2);
    math.op(CLAW_X87_DIV_TO0 + 3);
    math.op(CLAW_X87_XCH_ST + 1);
    math.store(0x534de0, true);
    math.op(CLAW_X87_XCH_ST + 1);
    }
    math.store(0x534de8, true);
    math.store(0x534df0, true);
    math.op(CLAW_X87_STP_ST + 0);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x41e810:
        return function_41e810(run, receiver, arguments);
    case 0x453d30:
        return function_453d30(run, receiver, arguments);
    case 0x453df0:
        return function_453df0(run, receiver, arguments);
    case 0x4542f0:
        return function_4542f0(run, receiver, arguments);
    case 0x454310:
        return function_454310(run, receiver, arguments);
    case 0x4543e0:
        return function_4543e0(run, receiver, arguments);
    case 0x4547c0:
        return function_4547c0(run, receiver, arguments);
    case 0x4548c0:
        return function_4548c0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_four_katherine_core_springboard_01_entry, owned, body)
