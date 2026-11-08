// Raux state callbacks and home selection, recovered from original v1.0.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x47f020:
    case 0x47f0c0:
    case 0x47f160:
    case 0x47f290:
    case 0x47f600:
    case 0x47f680:
    case 0x47f6b0:
        return 0;
    default:
        return -1;
    }
}

// Local binary64 spills and exact x87 primitives preserve the original's
// arithmetic order and its explicit intermediate rounding points.
struct Arithmetic {
    Run &run;
    ClawX87State fp{};
    explicit Arithmetic(Run &run) : run(run) {
        fp.size = sizeof(fp);
        fp.version = CLAW_X87_VERSION;
        fp.control = 0x023f;
    }
    void op(uint32_t code) {
        run.x87_step(code, fp);
    }
    void memory(uint32_t code, uint64_t bits) {
        run.x87_step(code, fp, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    void load(uint64_t bits) {
        memory(CLAW_X87_F64, bits);
    }
    void field(uint32_t address) {
        load(run.load<uint64_t>(address));
    }
    uint64_t spill(bool pop = false) {
        return run.x87_step(pop ? CLAW_X87_STP_F64 : CLAW_X87_ST_F64, fp);
    }
    void swap(uint32_t index) {
        op(CLAW_X87_XCH_ST + index);
    }
    void duplicate(uint32_t index) {
        op(CLAW_X87_LD_ST + index);
    }
    void multiply(uint64_t bits) {
        memory(CLAW_X87_MUL_F64, bits);
    }
    void addpop(uint32_t index) {
        op(CLAW_X87_ADDP + index);
    }
    void subpop() {
        op(CLAW_X87_SUBP + 1);
    }
};

// +0x0c world state, +0x10 animation identity, +0x12c sprite,
// +0x24 previous identity, +0x134 previous sprite frame, +0x470 idle start.
// 0x47f020.
uint32_t function_47f020(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t identity = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(receiver + 0x10) + 0x1c, identity);
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t sequence = run.get(receiver + 0x350);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {sequence});
    if (run.gets(receiver + 0x3c4) >= 0 && run.gets(receiver + 0x3c4) < 500) {
        run.call(0x48ceb0, 0, {run.get(receiver + 0x0c), 0x52b338, 0});
    }
    run.put(receiver + 0x474, 4000);
    run.put(receiver + 0x470, run.get(0x537210));
    return 0;
}

// 0x47f0c0. +0x184 mode; +0x474 idle interval.
uint32_t function_47f0c0(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t mode = run.get(receiver + 0x184);
    if (mode == 3 || mode == 4) {
        run.vcall(receiver, 0x44);
    } else if (mode <= 6) {
        if (run.get(0x537210) - run.get(receiver + 0x470) >= run.get(receiver + 0x474)) {
            if (!run.get(0x541334)) {
                if (s32(run.call(0x4a3050, 0)) % 100 < 5) {
                    run.call(0x44edd0, receiver);
                }
            }
        }
    }
    return 0;
}

// 0x47f290. +0x80 and +0x98 horizontal bounds; +0x128 target,
// +0x38/+0x40/+0x48 acceleration, +0x68/+0x70/+0x78 position.
uint32_t function_47f290(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(run.get(receiver + 0x0c) + 0xcc) != 1) {
        return 0;
    }
    Arithmetic conversion(run);
    auto convert = [&](uint32_t address) {
        conversion.field(address);
        conversion.fp.popCount = 1;
        conversion.fp.pushCount = 0;
        conversion.fp.returned = 0;
        conversion.fp.eax = 0;
        conversion.fp.edx = 0;
        return run.call_x87_exact(0x4a30e0, 0, conversion.fp);
    };
    uint32_t x;
    if (run.get(receiver + 0x18c) == 3) {
        x = convert(receiver + 0x80) + 0x14;
    } else {
        x = convert(receiver + 0x98) - 0x14;
    }
    double xd = double(s32(x));
    if (!(xd >= run.getd(receiver + 0x80))) {
        return 0;
    }
    if (xd > run.getd(receiver + 0x98)) {
        return 0;
    }
    uint32_t target = run.get(receiver + 0x128);
    uint32_t y = run.get(target + 0x124) + run.get(target + 0x50) + 1;
    auto tile = [&](uint32_t yy) {
        return run.call(0x4207f0, run.get(run.get(run.get(receiver + 0x128) + 0x0c) + 0x24), {x, yy});
    };
    if (tile(y) != 1 && tile(y) != 2 && tile(y) != 3) {
        return 0;
    }
    if (tile(y - 1)) {
        return 0;
    }
    Arithmetic a(run);
    uint64_t xbits;
    std::memcpy(&xbits, &xd, sizeof(xbits));
    a.load(xbits);
    uint32_t player = run.get(0x537e88);
    a.run.x87_step(CLAW_X87_I32, a.fp, {run.get(player + 0x124) + run.get(player + 0x50)});
    a.swap(1);
    a.memory(CLAW_X87_SUB_F64, run.load<uint64_t>(receiver + 0x68));
    a.field(receiver + 0x38);
    a.field(receiver + 0x40);
    a.swap(3);
    a.memory(CLAW_X87_SUB_F64, run.load<uint64_t>(receiver + 0x70));
    a.field(receiver + 0x78);
    a.field(receiver + 0x48);
    a.swap(4);
    uint64_t dx = a.spill();
    a.swap(2);
    uint64_t dy = a.spill();
    a.swap(1);
    a.op(CLAW_X87_CHS);
    uint64_t dz = a.spill();
    a.swap(3);
    uint64_t ax = a.spill();
    a.swap(5);
    uint64_t ay = a.spill();
    a.swap(4);
    uint64_t az = a.spill();
    a.load(ax);
    a.multiply(dx);
    a.op(CLAW_X87_CHS);
    a.load(ay);
    a.multiply(dy);
    a.subpop();
    a.load(az);
    a.multiply(dz);
    a.subpop();
    uint64_t dot = a.spill(true);
    a.swap(5);
    a.multiply(ax);
    a.load(dot);
    a.swap(5);
    a.multiply(ay);
    a.addpop(1);
    a.swap(5);
    a.multiply(az);
    a.addpop(5);
    a.swap(1);
    a.multiply(dx);
    a.swap(4);
    uint64_t square = a.spill(true);
    a.multiply(dy);
    a.swap(1);
    a.multiply(dz);
    a.swap(1);
    a.addpop(3);
    a.swap(1);
    a.multiply(run.load<uint64_t>(0x50f188));
    a.swap(1);
    a.addpop(2);
    a.swap(1);
    a.multiply(square);
    a.multiply(run.load<uint64_t>(0x50f180));
    a.op(CLAW_X87_SQRT);
    a.swap(1);
    a.subpop();
    a.multiply(run.load<uint64_t>(0x50f190));
    a.op(CLAW_X87_SQRT);
    uint64_t speed = a.spill();
    a.memory(CLAW_X87_COMP_F64, run.load<uint64_t>(0x513e20));
    if (a.fp.status & 0x100) {
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x60, 0);
        run.put(receiver + 0x54, 0);
        run.put(receiver + 0x5c, 0);
        run.put(receiver + 0x64, 0);
    } else {
        a.load(square);
        a.multiply(run.load<uint64_t>(0x50f198));
        a.field(0x513e20);
        a.op(CLAW_X87_CHS);
        a.duplicate(1);
        a.op(CLAW_X87_COMPP);
        bool general = (a.fp.status & 0x100) != 0;
        if (!general) {
            a.memory(CLAW_X87_COM_F64, run.load<uint64_t>(0x513e20));
            general = (a.fp.status & 0x4100) == 0;
        }
        if (!general) {
            a.op(CLAW_X87_POP);
            a.load(dy);
            a.load(dx);
            a.load(dz);
            a.swap(2);
            a.op(CLAW_X87_ABS);
            a.swap(1);
            a.op(CLAW_X87_ABS);
            a.addpop(1);
            a.swap(1);
            a.op(CLAW_X87_ABS);
            a.load(dx);
            a.swap(1);
            a.addpop(2);
            a.load(dy);
            a.load(dz);
            a.swap(2);
            a.op(CLAW_X87_DIV_TO0 + 3);
            a.swap(1);
            a.op(CLAW_X87_DIV_TO0 + 3);
            a.swap(2);
            a.op(CLAW_X87_DIV_TO0 + 3);
            a.swap(1);
            a.multiply(speed);
            a.swap(2);
            a.multiply(speed);
            a.swap(1);
            a.multiply(speed);
            a.swap(2);
            run.store<uint64_t>(receiver + 0x50, a.spill(true));
        } else {
            a.load(speed);
            a.multiply(speed);
            a.swap(1);
            a.op(CLAW_X87_ADD_TO0);
            a.swap(1);
            a.memory(CLAW_X87_SUB_F64, dot);
            a.swap(1);
            a.op(CLAW_X87_DIVP + 1);
            a.duplicate(0);
            a.op(CLAW_X87_SQRT);
            a.duplicate(1);
            a.duplicate(2);
            a.swap(1);
            a.multiply(ax);
            a.swap(2);
            a.swap(3);
            a.swap(1);
            a.multiply(ay);
            a.swap(1);
            a.multiply(az);
            a.swap(2);
            a.multiply(run.load<uint64_t>(0x50f190));
            a.swap(1);
            a.multiply(run.load<uint64_t>(0x50f190));
            a.swap(1);
            a.memory(CLAW_X87_SUBR_F64, dx);
            a.swap(2);
            a.multiply(run.load<uint64_t>(0x50f190));
            a.swap(1);
            a.memory(CLAW_X87_SUBR_F64, dy);
            a.swap(1);
            a.memory(CLAW_X87_SUBR_F64, dz);
            a.swap(2);
            a.op(CLAW_X87_DIV_TO0 + 3);
            a.swap(1);
            a.op(CLAW_X87_DIV_TO0 + 3);
            a.swap(2);
            a.op(CLAW_X87_DIV_TO0 + 3);
            a.swap(1);
            run.store<uint64_t>(receiver + 0x50, a.spill(true));
            a.swap(1);
        }
        run.store<uint64_t>(receiver + 0x58, a.spill(true));
        run.store<uint64_t>(receiver + 0x60, a.spill(true));
        a.op(CLAW_X87_POP);
    }
    run.put(receiver + 0x18, 0x43f720);
    run.put(receiver + 0x20, 1);
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x08, run.get(sprite + 0x08) | 4);
    if (run.get(receiver + 0x18c) == 2) {
        run.call(0x4357a0, receiver + 0x128);
    } else {
        run.call(0x406310, receiver + 0x128);
    }
    run.put(run.get(receiver + 0x0c) + 0xcc, 8);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t identity = run.call(0x4dba00, 0x537668, {0x52874c});
    run.put(run.get(receiver + 0x10) + 0x1c, identity);
    sprite = run.get(receiver + 0x12c);
    uint32_t sequence = run.get(receiver + 0x33c);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {sequence});
    return 0;
}

// 0x47f160. +0x18c facing, +0x138/+0x140 horizontal bounds,
// sprite +0x40 mirror flags, +0x2e4 action threshold.
uint32_t function_47f160(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t sprite = run.get(receiver + 0x12c);
    bool left = run.get(receiver + 0x18c) == 2;
    if (left != bool(run.get8(sprite + 0x40) & 2)) {
        uint32_t old = run.get(receiver + 0x138);
        run.put(receiver + 0x138, 0u - run.get(receiver + 0x140));
        run.put(receiver + 0x140, 0u - old);
        uint32_t flags = run.get(sprite + 0x40);
        run.put(sprite + 0x40, left ? flags | 2 : flags & ~2u);
        sprite = run.get(receiver + 0x12c);
        run.call(0x406120, sprite);
        run.call(0x406150, sprite);
        run.call(0x406180, sprite);
    }
    int32_t random = s32(run.call(0x4a3050, 0)) % 0x79;
    uint32_t mode = run.get(receiver + 0x184);
    if (mode == 2) {
        if (random < 0x14) {
            function_47f290(run, receiver, arguments);
        }
    } else if (mode == 3) {
        uint32_t threshold = run.get(receiver + 0x2e4);
        if (random < s32(threshold)) {
            run.vcall(receiver, 0x58);
        } else if (random < s32(threshold + 0x14)) {
            run.vcall(receiver, 0x68);
        }
    } else if (mode == 4) {
        if (s32(run.call(0x4a3050, 0)) % 100 < 0x32) {
            run.vcall(receiver, 0x64);
        } else {
            run.vcall(receiver, 0x58);
        }
    }
    run.call(0x44da20, receiver);
    return 0;
}

// 0x47f600. world +0x138 attack rectangle, world +0xcc motion state.
uint32_t function_47f600(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    run.icall(0x546d5c, {run.get(receiver + 0x0c) + 0x138, uint32_t(-14), 1, 9, 0x27});
    if (run.get8(run.get(receiver + 0x12c) + 0x40) & 2) {
        uint32_t world = run.get(receiver + 0x0c);
        uint32_t old = run.get(world + 0x138);
        run.put(world + 0x138, 0u - run.get(world + 0x140));
        run.put(run.get(receiver + 0x0c) + 0x140, 0u - old);
    }
    if (run.get(run.get(receiver + 0x0c) + 0xcc) == 1) {
        run.call(0x43f720, receiver);
        run.vcall(receiver, 0x44);
    }
    return 0;
}

// 0x47f680. sprite +0x1a4 finished, +0x19c current frame.
uint32_t function_47f680(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x44f660, receiver);
    uint32_t sprite = run.get(receiver + 0x12c);
    if (run.get(sprite + 0x1a4) && !run.get(sprite + 0x19c)) {
        run.vcall(receiver, 0x58);
    }
    return 0;
}

// 0x47f6b0.
uint32_t function_47f6b0(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x44f490, receiver);
    uint32_t sprite = run.get(receiver + 0x12c);
    if (run.get(sprite + 0x1a4) && !run.get(sprite + 0x19c)) {
        run.vcall(receiver, 0x58);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x47f020:
        return function_47f020(run, receiver, arguments);
    case 0x47f0c0:
        return function_47f0c0(run, receiver, arguments);
    case 0x47f160:
        return function_47f160(run, receiver, arguments);
    case 0x47f290:
        return function_47f290(run, receiver, arguments);
    case 0x47f600:
        return function_47f600(run, receiver, arguments);
    case 0x47f680:
        return function_47f680(run, receiver, arguments);
    case 0x47f6b0:
        return function_47f6b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_raux_states_entry, owned, body)
