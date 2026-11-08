// Level 2 raux shared entries
//
// Recovered from the original packet; movement arithmetic uses exact x87 steps.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x404e40:
        return 0;
    case 0x405060:
        return 0;
    case 0x40e0d0:
        return 1;
    case 0x40e190:
        return 1;
    case 0x40e280:
        return 1;
    case 0x40e560:
        return 0;
    case 0x40e580:
        return 0;
    case 0x40e660:
        return 1;
    case 0x420590:
        return 0;
    case 0x44e620:
        return 0;
    case 0x455350:
        return 0;
    case 0x4a07e0:
        return 1;
    default:
        return -1;
    }
}

// 0x404e40. thiscall, 0 stack argument(s), returns void.
uint32_t function_404e40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x0, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver + 0x0, 0x50b014);
    return 0;
}

// 0x405060. thiscall, 0 stack argument(s), returns u32.
uint32_t function_405060(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523268});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x350);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    return 0;
}

// 0x40e0d0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_40e0d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    auto fp = run.x87_entry(0x40e0d0);
    fp.popCount = 0;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    run.call_x87_exact(0x44c000, receiver, fp, {arguments[0]});
    run.put(receiver + 0x0, 0x50b5d4);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t output = run.automatic(0x4);
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(actor + 0xc) + 0x28) + 0x10, {0x524098, output});
    run.put(receiver + 0x458, run.get(output));
    uint32_t root = run.get(receiver + 0xc);
    run.put(root + 0x8, run.get(root + 0x8) | 0x80000);
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 2);
    run.put(0x5349dc, run.get(receiver + 0xc));
    root = run.get(receiver + 0xc);
    run.put(receiver + 0x45c, 0);
    run.put(receiver + 0x450, run.get(root + 0x4c));
    run.put(receiver + 0x454, run.get(root + 0x50));
    run.x87_finish(0x40e0d0, fp);
    return receiver;
}

// 0x40e190. thiscall, 1 stack argument(s), returns u32.
uint32_t function_40e190(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_404e40(run, receiver, nullptr);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x40e280. thiscall, 1 stack argument(s), returns void.
uint32_t function_40e280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t event = arguments[0];
    uint32_t minimum = run.get(0x5349c0);
    run.put(0x5349d8, 0);
    uint32_t record;
    if (s32(event) < s32(minimum) || s32(event) > run.gets(0x5349c4)) {
        if (!run.call(0x4db6e0, 0x5349b8, {event, 0})) {
            uint32_t error = run.get(0x544b4c);
            uint32_t pc = run.call(0x4db5f0, 0);
            uint32_t handler = run.get(0x5349bc);
            run.put(0x544b14, pc);
            run.call(0x4db4d0, handler, {0x5349b8, error, 0xc});
            record = run.get(0x5349cc);
            minimum = run.get(0x5349c0);
        } else {
            minimum = run.get(0x5349c0);
            record = run.get(0x5349c8) + (event - minimum) * run.get(0x5349d0);
        }
    } else {
        record = run.get(0x5349c8) + (event - minimum) * run.get(0x5349d0);
    }
    if (!run.get(record)) {
        run.call(0x44c840, receiver, {event});
        return 0;
    }
    run.put(0x5349d8, 0);
    if (s32(event) < s32(minimum) || s32(event) > run.gets(0x5349c4)) {
        if (!run.call(0x4db6e0, 0x5349b8, {event, 0})) {
            uint32_t error = run.get(0x544b4c);
            uint32_t pc = run.call(0x4db5f0, 0);
            uint32_t handler = run.get(0x5349bc);
            run.put(0x544b14, pc);
            run.call(0x4db4d0, handler, {0x5349b8, error, 0xc});
            run.call(run.get(run.get(0x5349cc)), receiver);
            return 0;
        }
        minimum = run.get(0x5349c0);
    }
    record = run.get(0x5349c8) + (event - minimum) * run.get(0x5349d0);
    run.call(run.get(record), receiver);
    return 0;
}

// 0x40e560. thiscall, 0 stack argument(s), returns void.
uint32_t function_40e560(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.putd(receiver + 0x68, double(run.gets(receiver + 0x450)));
    run.putd(receiver + 0x70, double(run.gets(receiver + 0x454)));
    return 0;
}

// 0x40e580. thiscall, 0 stack argument(s), returns u32.
uint32_t function_40e580(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t tick = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {tick});
    if (run.get(0x53c9c0) == 2)
        run.vcall(receiver, 0x48);
    return 0;
}

uint32_t function_420590(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x40e660. thiscall, 1 stack argument(s), returns u32.
uint32_t function_40e660(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x44e0c0, receiver, {arguments[0]});
    if (run.gets(run.get(0x537e88) + 0x10c) > 0) {
        function_420590(run, 0, nullptr);
        run.call(0x40e5c0, receiver);
    }
    return 0;
}

// 0x420590. cdecl, 0 stack argument(s), returns void.
uint32_t function_420590(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    (void)receiver;
    uint32_t manager = run.get(0x537e88);
    if (manager) {
        uint32_t actor = run.get(manager + 0x6c);
        if (actor)
            run.put(actor + 0x1c, 0x1392);
    }
    return 0;
}

// 0x44e620. thiscall, 0 stack argument(s), returns u32.
uint32_t function_44e620(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    uint64_t local_10 = 0;
    uint64_t local_18 = 0;
    uint64_t local_20 = 0;
    uint64_t local_28 = 0;
    uint64_t local_30 = 0;
    uint64_t local_38 = 0;
    uint64_t local_40 = 0;
    uint64_t local_48 = 0;
    uint64_t local_50 = 0;
    uint64_t stored = 0;
    // Movement mode, position and the mode-specific destination limit.
    bool modeThree = run.get(receiver + 0x18c) == 3;
    run.x87_step(CLAW_X87_F64, fp, {run.get(receiver + 0x68), run.get(receiver + 0x6c)});
    if (modeThree) {
        run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(0x50e0f0), run.get(0x50e0f0 + 0x4)});
        run.x87_step(CLAW_X87_F64, fp, {run.get(receiver + 0x98), run.get(receiver + 0x98 + 0x4)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        local_10 = run.x87_step(CLAW_X87_ST_F64, fp);
        run.x87_step(CLAW_X87_COMPP, fp);
        if (!(fp.status & 0x4100))
            return 0;
    } else {
        run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(0x50e0f8), run.get(0x50e0f8 + 0x4)});
        run.x87_step(CLAW_X87_F64, fp, {run.get(receiver + 0x80), run.get(receiver + 0x80 + 0x4)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        local_10 = run.x87_step(CLAW_X87_ST_F64, fp);
        run.x87_step(CLAW_X87_COMPP, fp);
        if (fp.status & 0x100)
            return 0;
    }
    run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_10), uint32_t(local_10 >> 32)});
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    uint32_t x = run.call_x87_exact(0x4a30e0, 0, fp);
    uint32_t root = run.get(receiver + 0x128);
    uint32_t y = run.get(root + 0x124) + run.get(root + 0x50) + 1;
    uint32_t tile = run.call(0x4207f0, run.get(run.get(root + 0xc) + 0x24), {x, y});
    if (tile != 1) {
        tile = run.call(0x4207f0, run.get(run.get(run.get(receiver + 0x128) + 0xc) + 0x24), {x, y});
        if (tile != 2) {
            tile = run.call(0x4207f0, run.get(run.get(run.get(receiver + 0x128) + 0xc) + 0x24), {x, y});
            if (tile != 3)
                return 0;
        }
    }
    --y;
    tile = run.call(0x4207f0, run.get(run.get(run.get(receiver + 0x128) + 0xc) + 0x24), {x, y});
    if (tile)
        return 0;
    if (modeThree) {
        // Preserve each extended intermediate and each explicit rounded store.
        run.x87_step(CLAW_X87_F64, fp, {run.get(receiver + 0x70), run.get(receiver + 0x70 + 0x4)});
        run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_10), uint32_t(local_10 >> 32)});
        run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(receiver + 0x68), run.get(receiver + 0x68 + 0x4)});
        run.x87_step(CLAW_X87_F64, fp, {run.get(receiver + 0x38), run.get(receiver + 0x38 + 0x4)});
        run.x87_step(CLAW_X87_F64, fp, {run.get(receiver + 0x40), run.get(receiver + 0x40 + 0x4)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
        run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(receiver + 0x70), run.get(receiver + 0x70 + 0x4)});
        run.x87_step(CLAW_X87_F64, fp, {run.get(receiver + 0x78), run.get(receiver + 0x78 + 0x4)});
        run.x87_step(CLAW_X87_F64, fp, {run.get(receiver + 0x48), run.get(receiver + 0x48 + 0x4)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
        local_18 = run.x87_step(CLAW_X87_ST_F64, fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
        local_20 = run.x87_step(CLAW_X87_ST_F64, fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_CHS, fp);
        local_28 = run.x87_step(CLAW_X87_ST_F64, fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
        local_30 = run.x87_step(CLAW_X87_ST_F64, fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5), fp);
        local_38 = run.x87_step(CLAW_X87_ST_F64, fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
        local_40 = run.x87_step(CLAW_X87_ST_F64, fp);
        run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_30), uint32_t(local_30 >> 32)});
        run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_18), uint32_t(local_18 >> 32)});
        run.x87_step(CLAW_X87_CHS, fp);
        run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_38), uint32_t(local_38 >> 32)});
        run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_20), uint32_t(local_20 >> 32)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
        run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_40), uint32_t(local_40 >> 32)});
        run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_28), uint32_t(local_28 >> 32)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
        local_50 = run.x87_step(CLAW_X87_STP_F64, fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5), fp);
        run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_30), uint32_t(local_30 >> 32)});
        run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_50), uint32_t(local_50 >> 32)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5), fp);
        run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_38), uint32_t(local_38 >> 32)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 5), fp);
        run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_40), uint32_t(local_40 >> 32)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 5), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_18), uint32_t(local_18 >> 32)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 4), fp);
        local_48 = run.x87_step(CLAW_X87_STP_F64, fp);
        run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_20), uint32_t(local_20 >> 32)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_28), uint32_t(local_28 >> 32)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 3), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50e0d0), run.get(0x50e0d0 + 0x4)});
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_48), uint32_t(local_48 >> 32)});
        run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50e0c8), run.get(0x50e0c8 + 0x4)});
        run.x87_step(CLAW_X87_SQRT, fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
        run.x87_step(CLAW_X87_ST(CLAW_X87_SUBP, 1), fp);
        run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50e0d8), run.get(0x50e0d8 + 0x4)});
        run.x87_step(CLAW_X87_SQRT, fp);
        local_10 = run.x87_step(CLAW_X87_ST_F64, fp);
        run.x87_step(CLAW_X87_COMP_F64, fp, {run.get(0x513e20), run.get(0x513e20 + 0x4)});
        if (fp.status & 0x100) {
            run.put(receiver + 0x50, 0);
            run.put(receiver + 0x58, 0);
            run.put(receiver + 0x60, 0);
            run.put(receiver + 0x54, 0);
            run.put(receiver + 0x5c, 0);
            run.put(receiver + 0x64, 0);
        } else {
            run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_48), uint32_t(local_48 >> 32)});
            run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50e0e0), run.get(0x50e0e0 + 0x4)});
            run.x87_step(CLAW_X87_F64, fp, {run.get(0x513e20), run.get(0x513e20 + 0x4)});
            run.x87_step(CLAW_X87_CHS, fp);
            run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), fp);
            run.x87_step(CLAW_X87_COMPP, fp);
            bool quadratic = (fp.status & 0x100) != 0;
            if (!quadratic) {
                run.x87_step(CLAW_X87_COM_F64, fp, {run.get(0x513e20), run.get(0x513e20 + 0x4)});
                quadratic = !(fp.status & 0x4100);
            }
            if (quadratic) {
                run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_10), uint32_t(local_10 >> 32)});
                run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_10), uint32_t(local_10 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_ADD_TO0, 0), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_SUB_F64, fp, {uint32_t(local_50), uint32_t(local_50 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_DIVP, 1), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), fp);
                run.x87_step(CLAW_X87_SQRT, fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 1), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 2), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_30), uint32_t(local_30 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 3), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_38), uint32_t(local_38 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_40), uint32_t(local_40 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
                run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50e0d8), run.get(0x50e0d8 + 0x4)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50e0d8), run.get(0x50e0d8 + 0x4)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_SUBR_F64, fp, {uint32_t(local_18), uint32_t(local_18 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
                run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50e0d8), run.get(0x50e0d8 + 0x4)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_SUBR_F64, fp, {uint32_t(local_20), uint32_t(local_20 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_SUBR_F64, fp, {uint32_t(local_28), uint32_t(local_28 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                stored = run.x87_step(CLAW_X87_STP_F64, fp);
                run.put(receiver + 0x50, uint32_t(stored));
                run.put(receiver + 0x50 + 0x4, uint32_t(stored >> 32));
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                stored = run.x87_step(CLAW_X87_STP_F64, fp);
                run.put(receiver + 0x58, uint32_t(stored));
                run.put(receiver + 0x58 + 0x4, uint32_t(stored >> 32));
                stored = run.x87_step(CLAW_X87_STP_F64, fp);
                run.put(receiver + 0x60, uint32_t(stored));
                run.put(receiver + 0x60 + 0x4, uint32_t(stored >> 32));
            } else {
                run.x87_step(CLAW_X87_POP, fp);
                run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_20), uint32_t(local_20 >> 32)});
                run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_18), uint32_t(local_18 >> 32)});
                run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_28), uint32_t(local_28 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
                run.x87_step(CLAW_X87_ABS, fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_ABS, fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 1), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_ABS, fp);
                run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_18), uint32_t(local_18 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_ADDP, 2), fp);
                run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_20), uint32_t(local_20 >> 32)});
                run.x87_step(CLAW_X87_F64, fp, {uint32_t(local_28), uint32_t(local_28 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_DIV_TO0, 3), fp);
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_10), uint32_t(local_10 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
                run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_10), uint32_t(local_10 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 1), fp);
                run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(local_10), uint32_t(local_10 >> 32)});
                run.x87_step(CLAW_X87_ST(CLAW_X87_XCH_ST, 2), fp);
                stored = run.x87_step(CLAW_X87_STP_F64, fp);
                run.put(receiver + 0x50, uint32_t(stored));
                run.put(receiver + 0x50 + 0x4, uint32_t(stored >> 32));
                stored = run.x87_step(CLAW_X87_STP_F64, fp);
                run.put(receiver + 0x58, uint32_t(stored));
                run.put(receiver + 0x58 + 0x4, uint32_t(stored >> 32));
                stored = run.x87_step(CLAW_X87_STP_F64, fp);
                run.put(receiver + 0x60, uint32_t(stored));
                run.put(receiver + 0x60 + 0x4, uint32_t(stored >> 32));
            }
            run.x87_step(CLAW_X87_POP, fp);
        }
    } else {
        // Original solver receives the rounded destination, current Y and zero Z.
        uint32_t yLow = run.get(receiver + 0x70);
        uint32_t yHigh = run.get(receiver + 0x74);
        fp.popCount = 0;
        fp.pushCount = 1;
        fp.returned = 0;
        fp.eax = 0;
        fp.edx = 0;
        run.call_x87_exact(0x420dd0, receiver + 0x28, fp, {uint32_t(local_10), uint32_t(local_10 >> 32), yLow, yHigh, 0, 0});
        run.x87_step(CLAW_X87_POP, fp);
    }
    // Save the previous state and animation after selecting jump-back movement.
    uint32_t mode = run.get(receiver + 0x18c);
    run.put(receiver + 0x20, 1);
    if (mode == 2)
        run.call(0x4357a0, receiver + 0x128);
    else
        run.call(0x406310, receiver + 0x128);
    uint32_t sound = run.get(receiver + 0x40c);
    if (sound)
        run.call(0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
    run.put(run.get(receiver + 0xc) + 0xcc, 8);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x527da0});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 4);
    actor = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x340);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    return 0;
}

// 0x455350. thiscall, 0 stack argument(s), returns void.
uint32_t function_455350(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.vcall(receiver, 0x60);
    return 0;
}

// 0x4a07e0. thiscall, 1 stack argument(s), returns void.
uint32_t function_4a07e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    run.put(object + 0x8, run.get(object + 0x8) | 0x10000);
    run.vcall(receiver, 0x9c);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x404e40:
        return function_404e40(run, receiver, arguments);
    case 0x405060:
        return function_405060(run, receiver, arguments);
    case 0x40e0d0:
        return function_40e0d0(run, receiver, arguments);
    case 0x40e190:
        return function_40e190(run, receiver, arguments);
    case 0x40e280:
        return function_40e280(run, receiver, arguments);
    case 0x40e560:
        return function_40e560(run, receiver, arguments);
    case 0x40e580:
        return function_40e580(run, receiver, arguments);
    case 0x40e660:
        return function_40e660(run, receiver, arguments);
    case 0x420590:
        return function_420590(run, receiver, arguments);
    case 0x44e620:
        return function_44e620(run, receiver, arguments);
    case 0x455350:
        return function_455350(run, receiver, arguments);
    case 0x4a07e0:
        return function_4a07e0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_two_raux_shared_entry, owned, body)
