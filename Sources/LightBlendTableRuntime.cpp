// Palette blend table builder 0x4c6d90
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

extern "C" uint32_t claw_player_fade_blend_canonical_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4c6d90:
        return 3;
    default:
        return -1;
    }
}

// 0x4c6d90. thiscall, 3 stack arguments, returns u32.
// Builds a 256 x 256 palette blend table and appends it to the receiver's
// pointer array (array object at receiver + 0x4: data +0x4 of it, i.e.
// receiver + 0x8, count at receiver + 0xc). arguments: palette (4 bytes per
// entry, three colour bytes used), weight of the row entry, weight of the
// column entry. Returns the new table object, or 0 on failure.
uint32_t function_4c6d90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t palette = arguments[0];
    uint32_t weightRow = arguments[1];
    uint32_t weightColumn = arguments[2];
    uint32_t block = run.call(0x4f63ec, 0, {0xc});
    uint32_t table = 0;
    if (block != 0)
        table = run.call(0x4c76d0, block, {});
    if (table == 0)
        return 0;
    uint32_t built = run.call(0x4c76f0, table, {0x10000});
    if (built == 0)
        return 0;
    uint32_t index = run.get(receiver + 0xc);
    run.call(0x4dee30, receiver + 0x4, {index + 1, 0xffffffff});
    uint32_t data = run.get(receiver + 0x8);
    run.put(data + index * 4, table);
    uint32_t cells = run.get(table + 0x8);
    uint32_t divisor = uint32_t(s32(weightRow + weightColumn) / 100);
    uint32_t rowBase = palette + 2;
    for (uint32_t row = 0; row < 0x100; ++row) {
        uint32_t columnBase = palette + 2;
        for (uint32_t column = 0; column < 0x100; ++column) {
            uint32_t channel[3];
            for (uint32_t k = 0; k < 3; ++k) {
                uint32_t rowByte = run.get8(rowBase + k - 2);
                uint32_t columnByte = run.get8(columnBase + k - 2);
                uint32_t rowPart = uint32_t(s32(weightRow * rowByte) / 100);
                uint32_t columnPart = uint32_t(s32(weightColumn * columnByte) / 100);
                uint32_t total = rowPart + columnPart;
                // idiv faults on a zero divisor; the original never survives it.
                if (divisor == 0)
                    run.fail(CLAW_FAULT_HOST, 0x4c6e9b);
                channel[k] = uint32_t(s32(total) / s32(divisor)) & 0xff;
            }
            uint32_t arguments4[4] = {palette, channel[0], channel[1], channel[2]};
            uint32_t nearest = 0;
            if (!claw_player_fade_blend_canonical_entry(0x4c7580, 0, arguments4, 4, &run.host, &nearest))
                run.fail(CLAW_FAULT_HOST, 0x4c7580);
            run.put8(cells + column, nearest & 0xff);
            columnBase += 4;
        }
        rowBase += 4;
        cells += 0x100;
    }
    return table;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4c6d90:
        return function_4c6d90(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_light_blend_table_entry, owned, body)
