#include "ClawRuntime.hpp"
#include <cmath>
#include <algorithm>

namespace {
using claw::Run;
using claw::s32;

// Each nested owned activation retains the original location of addressed locals.
struct Activation {
    Run &run;
    uint32_t frame;
    uint32_t outgoing;
    Activation(Run &run, uint32_t entry, uint32_t depth) : run(run), frame(run.frame), outgoing(run.stackPointer) {
        run.frame = entry;
        run.stackPointer = entry - depth - 0x80;
    }
    ~Activation() {
        run.frame = frame;
        run.stackPointer = outgoing;
    }
};
uint32_t at(Run &run, uint32_t depth, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
    uint32_t outgoing = run.stackPointer;
    run.stackPointer = run.frame - depth - uint32_t(arguments.size() + 1) * 4;
    uint32_t result = run.call(function, receiver, arguments);
    run.stackPointer = outgoing;
    return result;
}
uint32_t virtualAt(Run &run, uint32_t depth, uint32_t receiver, uint32_t slot, std::initializer_list<uint32_t> arguments = {}) {
    return at(run, depth, run.get(run.get(receiver) + slot), receiver, arguments);
}
ClawX87State state() {
    ClawX87State value{};
    value.size = sizeof(value);
    value.version = CLAW_X87_VERSION;
    value.control = 0x023f;
    return value;
}
void arithmetic(Run &run, ClawX87State &value, uint32_t op, double operand) {
    uint64_t bits;
    std::memcpy(&bits, &operand, 8);
    run.x87_step(op, value, {uint32_t(bits), uint32_t(bits >> 32)});
}
uint32_t convert(Run &run, ClawX87State &value) {
    value.popCount = 1;
    value.pushCount = 0;
    value.returned = 0;
    value.eax = 0;
    value.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, value);
}
uint32_t radiusExtent(Run &run, uint32_t radius) {
    auto value = state();
    run.x87_step(CLAW_X87_I32, value, {radius});
    arithmetic(run, value, CLAW_X87_MUL_F64, run.getd(0x514288));
    return convert(run, value);
}
// FSIN executes at 53-bit precision here; preserve the raw stack and lower denominator.
void sine(ClawX87State &value) {
    auto &raw = value.slots[0];
    double operand = std::ldexp(double(raw.significand), int(raw.signExponent & 0x7fff) - 16383 - 63);
    if (raw.signExponent & 0x8000)
        operand = -operand;
    double result = std::sin(operand);
    uint64_t bits;
    std::memcpy(&bits, &result, 8);
    uint32_t exponent = uint32_t((bits >> 52) & 0x7ff);
    raw.signExponent = uint32_t(bits >> 63) << 15;
    raw.significand = 0;
    if (exponent) {
        raw.signExponent |= exponent + 16383 - 1023;
        raw.significand = ((bits & 0xfffffffffffffull) | 0x10000000000000ull) << 11;
    }
}
// Optional, checked row view. A range crossing allocations falls back to the
// original individual accesses; no view survives a call or a row operation.
uint8_t *rowSpan(Run &run, uint32_t token, uint64_t count) {
    if (!count || count > 0xffffffffu || uint64_t(token) + count > 0x100000000ull)
        return nullptr;
    uint8_t *memory = run.host.bytes ? run.host.bytes(run.host.user, token, uint32_t(count)) : nullptr;
    run.check_guest();
    return memory;
}
bool rowBudget(Run &run, uint64_t count) {
    if (run.host.remainingOperations)
        return count <= *run.host.remainingOperations;
    uint64_t limit = run.host.maximumOperations ? run.host.maximumOperations : 200000000u;
    return run.operations <= limit && count <= limit - run.operations;
}
// rowBudget proved that every scalar access fits. No callbacks occur during
// row work, so account for exactly those accesses without a per-byte tick loop.
void rowTicks(Run &run, uint64_t count) {
    if (run.host.remainingOperations)
        *run.host.remainingOperations -= count;
    run.operations += count;
}
uint32_t rowField(const uint8_t *fields, uint32_t offset) {
    uint32_t value;
    std::memcpy(&value, fields + offset, 4);
    return value;
}
bool overlaps(const uint8_t *left, uint64_t leftCount, const uint8_t *right, uint64_t rightCount) {
    uintptr_t a = reinterpret_cast<uintptr_t>(left);
    uintptr_t b = reinterpret_cast<uintptr_t>(right);
    return a <= b ? uint64_t(b - a) < leftCount : uint64_t(a - b) < rightCount;
}
void bytes(Run &run, uint32_t destination, uint32_t source, uint32_t count) {
    if (s32(count) <= 0)
        return;
    auto from = rowSpan(run, source, count);
    auto to = rowSpan(run, destination, count);
    if (from && to && rowBudget(run, uint64_t(count) * 2)) {
        if (!overlaps(to, count, from, count)) {
            std::memcpy(to, from, count);
        } else {
            // Forward copy intentionally propagates bytes on overlapping rows.
            for (uint32_t i = 0; i < count; ++i)
                to[i] = from[i];
        }
        rowTicks(run, uint64_t(count) * 2);
        return;
    }
    for (uint32_t i = 0; s32(i) < s32(count); ++i)
        run.put8(destination + i, run.get8(source + i));
}
void zero(Run &run, uint32_t destination, uint32_t count) {
    if (s32(count) <= 0)
        return;
    auto to = rowSpan(run, destination, count);
    uint32_t words = count >> 2;
    uint64_t ticks = uint64_t(words) + (count & 3);
    if (to && rowBudget(run, ticks)) {
        std::memset(to, 0, count);
        rowTicks(run, ticks);
        return;
    }
    for (uint32_t i = 0; i < words; ++i)
        run.put(destination + i * 4, 0);
    for (uint32_t i = words * 4; i < count; ++i)
        run.put8(destination + i, 0);
}

// 0x4c7730. Palette table length and bytes are reloaded after stream/allocation calls.
uint32_t readStream(Run &run, uint32_t table, uint32_t stream) {
    run.vcall(stream, 0x3c, {table + 0x04, 4});
    if (!run.call(0x4c76f0, table, {run.get(table + 0x04)}))
        return 0;
    run.vcall(stream, 0x3c, {run.get(table + 0x08), run.get(table + 0x04)});
    run.put(table + 0x00, 1);
    return 1;
}
// 0x4c7850. The original 40-byte CMemFile occupies entry ESP-0x34.
uint32_t tableBytes(Run &run, uint32_t table, uint32_t data, uint32_t length) {
    Activation activation(run, run.frame, 0x3c);
    uint32_t stream = run.automatic(-0x34);
    run.call(0x4ff5f9, stream, {0x400});
    run.call(0x4ff645, stream, {data, length, 0});
    uint32_t result = readStream(run, table, stream);
    run.put(table + 0x00, result);
    run.call(0x4ff682, stream);
    return result;
}
// 0x4c7360. Manager array: +8 storage, +0xc size, +0x10 capacity, +0x14 growth.
uint32_t paletteBytes(Run &run, uint32_t manager, uint32_t data, uint32_t length) {
    Activation activation(run, run.frame, 0x2c);
    uint32_t table = run.call(0x4f63ec, 0, {0x0c});
    if (table)
        table = run.call(0x4c76d0, table);
    uint32_t count = run.get(manager + 0x0c);
    uint32_t array = run.get(manager + 0x08);
    uint32_t next = count + 1;
    if (!next) {
        if (array) {
            run.call(0x4f6428, 0, {array});
            run.put(manager + 0x08, 0);
        }
        run.put(manager + 0x10, 0);
        run.put(manager + 0x0c, 0);
    } else if (!array) {
        array = run.call(0x4f63ec, 0, {next * 4});
        run.put(manager + 0x08, array);
        zero(run, array, next * 4);
        run.put(manager + 0x10, next);
        run.put(manager + 0x0c, next);
    } else if (s32(next) > run.gets(manager + 0x10)) {
        uint32_t growth = run.get(manager + 0x14);
        if (!growth)
            growth = uint32_t(std::clamp(s32(count) / 8, 4, 1024));
        uint32_t capacity = growth + run.get(manager + 0x10);
        if (s32(next) >= s32(capacity))
            capacity = next;
        uint32_t replacement = run.call(0x4f63ec, 0, {capacity * 4});
        uint32_t oldCount = run.get(manager + 0x0c);
        uint32_t oldArray = run.get(manager + 0x08);
        for (uint32_t i = 0; i < ((oldCount * 4) >> 2); ++i)
            run.put(replacement + i * 4, run.get(oldArray + i * 4));
        uint32_t current = run.get(manager + 0x0c);
        for (uint32_t i = 0; i != next - current; ++i)
            run.put(replacement + (current + i) * 4, 0);
        run.call(0x4f6428, 0, {run.get(manager + 0x08)});
        run.put(manager + 0x08, replacement);
        run.put(manager + 0x0c, next);
        run.put(manager + 0x10, capacity);
    } else {
        if (s32(next) > s32(count)) {
            for (uint32_t i = 0; i != next - count; ++i)
                run.put(array + (count + i) * 4, 0);
        }
        run.put(manager + 0x0c, next);
    }
    run.put(run.get(manager + 0x08) + count * 4, table);
    uint32_t loaded;
    {
        Activation child(run, run.frame - 0x38, 0x3c);
        loaded = tableBytes(run, table, data, length);
    }
    if (!loaded) {
        run.call(0x4c7510, manager, {table});
        table = 0;
    }
    return table;
}
// 0x42a4f0. Application fields: +0x34 resources, +0x58 palettes, +0x8c cached table.
uint32_t rollerPalette(Run &run, uint32_t application) {
    Activation activation(run, run.frame, 0x0c);
    if (!run.vcall(application, 0x0c))
        return 0;
    if (!run.get(application + 0x58))
        return 0;
    uint32_t result = run.get(application + 0x8c);
    if (result)
        return result;
    uint32_t resources = run.get(application + 0x34);
    if (!resources)
        return 0;
    uint32_t resource = run.call(0x4b7f00, resources, {0x525e38, 0x434c54});
    if (!resource)
        return 0;
    uint32_t length = run.get(resource + 0x14);
    uint32_t data = run.call(0x4b61c0, resource);
    if (!data)
        return 0;
    {
        Activation child(run, run.frame - 0x18, 0x2c);
        result = paletteBytes(run, run.get(application + 0x58), data, length);
    }
    run.put(application + 0x8c, result);
    run.call(0x4b6230, resource);
    return run.get(application + 0x8c);
}
// 0x4ecb40. 44-byte init record, CString at +0x24.
uint32_t initRecord(Run &run, uint32_t record) {
    run.call(0x4ecb30, record);
    run.call(0x4f6439, record + 0x24);
    run.put(record + 0x00, 1);
    run.put(record + 0x04, 0);
    run.put(record + 0x08, 0);
    run.put(record + 0x0c, 0);
    run.put(record + 0x10, 50);
    run.put(record + 0x14, 1);
    run.put(record + 0x18, 1);
    run.put(record + 0x1c, 0);
    run.put(record + 0x20, 0);
    run.call(0x4f66cc, record + 0x24, {0x534938});
    run.put(record + 0x28, 0);
    return record;
}
// 0x4b9c50. Surface COM +8 and persistent RECT +0x7c.
uint32_t copySurface(Run &run, uint32_t destination, uint32_t source) {
    uint32_t target = run.get(destination + 0x08);
    uint32_t result = run.call(run.get(run.get(target) + 0x14), 0, {target, destination + 0x7c, run.get(source + 0x08), source + 0x7c, 0x1000000, 0});
    if (result == 0x887601c2) {
        if (!run.vcall(destination, 0x1c))
            return result;
        target = run.get(destination + 0x08);
        result = run.call(run.get(run.get(target) + 0x14), 0, {target, destination + 0x7c, run.get(source + 0x08), source + 0x7c, 0x1000000, 0});
    }
    if (result)
        run.call(0x4bd260, 0, {0x5324dc, 0x46a, result});
    return result;
}
// 0x4ee880, 0x4ee8e0 and 0x4ee8c0. Fader allocation fields retain their released values.
uint32_t construct(Run &run, uint32_t fader) {
    run.call(0x4ec8d0, fader);
    run.put(fader + 0x00, 0x514270);
    run.put(fader + 0x478, 0);
    run.put(fader + 0x44, 0);
    run.put(fader + 0x48, 0);
    run.put(fader + 0x4c, 0);
    run.put(fader + 0x488, 0);
    run.put(fader + 0x48c, 0);
    run.put(fader + 0x20, 0);
    return fader;
}
void destroy(Run &run, uint32_t fader) {
    run.put(fader + 0x00, 0x514270);
    uint32_t pointer = run.get(fader + 0x478);
    if (pointer)
        run.call(0x4f6428, 0, {pointer});
    pointer = run.get(fader + 0x44);
    if (pointer)
        run.call(0x4f6428, 0, {pointer});
    pointer = run.get(fader + 0x48);
    if (pointer)
        run.call(0x4f6428, 0, {pointer});
    pointer = run.get(fader + 0x4c);
    if (pointer)
        run.call(0x4f6428, 0, {pointer});
    pointer = run.get(fader + 0x488);
    if (pointer)
        run.call(0x4f6428, 0, {pointer});
    pointer = run.get(fader + 0x48c);
    if (pointer)
        run.call(0x4f6428, 0, {pointer});
    run.call(0x4ec920, fader);
}
// 0x4d4100. Actor bounds and attached surface.
uint32_t bindSurface(Run &run, uint32_t actor, uint32_t surface) {
    if (!surface)
        return 0;
    uint32_t width = run.get(surface + 0x18);
    uint32_t height = run.get(surface + 0x14);
    if (s32(width) <= 0 || s32(height) <= 0)
        return 0;
    run.put(actor + 0x10, width);
    run.put(actor + 0x24, width);
    run.put(actor + 0x14, height);
    run.put(actor + 0x1c, 0);
    run.put(actor + 0x20, 0);
    run.put(actor + 0x28, height);
    run.put(actor + 0x04, 99);
    run.put(actor + 0x2c, surface);
    run.put(actor + 0x30, 0);
    return 1;
}
// 0x4ee9a0. Surface triples, curl map, optional palette shading and row offsets.
uint32_t initialize(Run &run, uint32_t fader, uint32_t record) {
    Activation activation(run, run.frame, 0x14);
    run.stackPointer = run.frame - 0x18;
    run.put(fader + 0x20, 0);
    if (!record)
        return 0;
    uint32_t destination = run.get(record + 0x04);
    if (!destination)
        destination = run.get(fader + 0x24);
    run.put(fader + 0x38, destination);
    uint32_t source = run.get(record + 0x08);
    if (!source)
        source = run.get(fader + 0x28);
    run.put(fader + 0x3c, source);
    if (!run.get(fader + 0x38) || !run.get(fader + 0x3c))
        return 0;
    uint32_t paper = run.get(record + 0x0c);
    if (!paper)
        paper = source;
    run.put(fader + 0x40, paper);
    run.put(fader + 0x04, 1);
    destination = run.get(fader + 0x38);
    uint32_t height = run.get(destination + 0x14);
    uint32_t width = run.get(destination + 0x18);
    run.put(fader + 0x60, width);
    source = run.get(fader + 0x3c);
    run.put(fader + 0x64, height);
    paper = run.get(fader + 0x40);
    uint32_t sh = run.get(source + 0x14);
    uint32_t sw = run.get(source + 0x18);
    run.put(fader + 0x68, sw);
    run.put(fader + 0x6c, sh);
    uint32_t pw = run.get(paper + 0x18);
    uint32_t ph = run.get(paper + 0x14);
    run.put(fader + 0x70, pw);
    run.put(fader + 0x74, ph);
    if (run.get(fader + 0x60) != sw || run.get(fader + 0x64) != sh || run.get(fader + 0x60) != pw || run.get(fader + 0x64) != ph || run.get(fader + 0x70) != sw || run.get(fader + 0x74) != sh)
        return 0;
    uint32_t mode = run.get(record + 0x14);
    if (mode == 0 || mode >= 4)
        return 0;
    run.put(fader + 0x50, mode);
    run.put(fader + 0x54, run.get(record + 0x18));
    uint32_t radius = run.get(record + 0x10);
    run.put(fader + 0x58, radius);
    if (mode == 1 || mode == 2) {
        uint32_t extent = radiusExtent(run, radius);
        if (run.gets(fader + 0x60) < s32(extent))
            return 0;
    }
    uint32_t remap = run.call(0x4f63ec, 0, {radius * 8});
    run.put(fader + 0x478, remap);
    for (uint32_t i = 0; s32(i) < s32(run.get(fader + 0x58) * 2); ++i) {
        double roundedRadius = double(float(run.gets(fader + 0x58)));
        auto value = state();
        uint64_t radiusBits;
        std::memcpy(&radiusBits, &roundedRadius, 8);
        run.x87_step(CLAW_X87_F64, value, {uint32_t(radiusBits), uint32_t(radiusBits >> 32)});
        arithmetic(run, value, CLAW_X87_SUBR_F64, double(s32(i)));
        arithmetic(run, value, CLAW_X87_DIV_F64, roundedRadius);
        value.popCount = 1;
        value.pushCount = 1;
        value.returned = 0;
        value.eax = 0;
        value.edx = 0;
        run.call_x87_exact(0x4f2400, 0, value);
        arithmetic(run, value, CLAW_X87_MUL_F64, roundedRadius);
        uint32_t offset = convert(run, value);
        run.put(run.get(fader + 0x478) + i * 4, offset);
    }
    run.put(fader + 0x5c, run.get(record + 0x1c));
    if (run.get(run.get(fader + 0x38) + 0xa4) != 8)
        run.put(fader + 0x5c, 0);
    if (run.get(fader + 0x5c)) {
        uint32_t palette = run.get(record + 0x20);
        if (palette) {
            run.put(fader + 0x30, 0);
            palette = run.get(record + 0x20);
            run.put(fader + 0x1c, palette);
        } else {
            uint32_t outgoing = run.stackPointer;
            run.stackPointer = run.frame - 0x20;
            uint32_t access = run.call(0x4f2190, 0, {run.get(record + 0x24), 0});
            run.stackPointer = outgoing;
            if (!access) {
                uint32_t string = run.automatic(-0x18);
                uint32_t outgoing = run.stackPointer;
                run.stackPointer = run.frame - 0x20;
                run.call(0x4f6449, string, {record + 0x24});
                run.stackPointer = run.frame - 0x1c;
                palette = run.call(0x4c7180, fader + 0x04, {run.get(string)});
                run.stackPointer = outgoing;
                run.put(fader + 0x1c, palette);
                if (!palette)
                    run.put(fader + 0x5c, 0);
            } else {
                palette = run.call(0x4c62e0, fader + 0x04, {run.get(run.get(record + 0x28) + 0x0c), 32, 32, 50, 200});
                run.put(fader + 0x1c, palette);
            }
        }
        uint32_t denominator = run.get(fader + 0x58) * 2;
        uint32_t shade = run.call(0x4f63ec, 0, {denominator});
        run.put(fader + 0x48c, shade);
        auto value = state();
        if (s32(denominator) > 0) {
            run.x87_step(CLAW_X87_I32, value, {denominator});
            for (uint32_t i = 0; s32(i) < s32(denominator); ++i) {
                run.x87_step(CLAW_X87_I32, value, {i});
                arithmetic(run, value, CLAW_X87_DIV_F64, double(s32(denominator)));
                arithmetic(run, value, CLAW_X87_MUL_F64, double(run.getf(0x514290)));
                sine(value);
                arithmetic(run, value, CLAW_X87_MUL_F64, run.getd(0x514298));
                uint32_t intensity = convert(run, value);
                run.put8(run.get(fader + 0x48c) + i, uint8_t(16 - intensity));
            }
            run.x87_step(CLAW_X87_POP, value);
        }
    }
    uint32_t rows = run.call(0x4f63ec, 0, {run.get(fader + 0x64) * 4});
    uint32_t nextHeight = run.get(fader + 0x6c);
    run.put(fader + 0x44, rows);
    rows = run.call(0x4f63ec, 0, {nextHeight * 4});
    nextHeight = run.get(fader + 0x74);
    run.put(fader + 0x48, rows);
    rows = run.call(0x4f63ec, 0, {nextHeight * 4});
    run.put(fader + 0x4c, rows);
    for (uint32_t i = 0; s32(i) < run.gets(fader + 0x64); ++i) {
        run.put(run.get(fader + 0x44) + i * 4, run.get(run.get(fader + 0x38) + 0x1c) * i);
        run.put(run.get(fader + 0x48) + i * 4, run.get(run.get(fader + 0x3c) + 0x1c) * i);
        run.put(run.get(fader + 0x4c) + i * 4, run.get(run.get(fader + 0x40) + 0x1c) * i);
    }
    uint32_t maximum = run.get(fader + 0x60);
    if (run.gets(fader + 0x64) > s32(maximum))
        maximum = run.get(fader + 0x64);
    uint32_t scratch = run.call(0x4f63ec, 0, {run.get(run.get(fader + 0x38) + 0xac) * maximum});
    run.put(fader + 0x488, scratch);
    return 1;
}

// Fast row assembly is elected only when scratch cannot change any inputs or
// reloaded fader fields. All other alias arrangements retain the scalar path.
bool curlRow(Run &run, uint32_t fader, uint32_t paper, uint32_t source, uint32_t begin, uint32_t end, uint32_t scratchOffset, uint32_t count, bool remapped, bool shading, uint32_t palette) {
    if (s32(begin) < 0 || s32(end) <= s32(begin))
        return false;
    uint64_t length = uint64_t(end - begin) * count;
    uint64_t ticks = shading && remapped ? uint64_t(end - begin) * 8 : length * (remapped ? 5 : 3);
    if (!rowBudget(run, ticks))
        return false;
    auto fields = rowSpan(run, fader, 0x490);
    if (!fields)
        return false;
    uint64_t output = uint64_t(rowField(fields, 0x488)) + scratchOffset + uint64_t(begin) * count;
    if (output > 0xffffffffu)
        return false;
    auto to = rowSpan(run, uint32_t(output), length);
    if (!to || overlaps(to, length, fields, 0x490))
        return false;
    if (!remapped) {
        uint64_t input = uint64_t(source) + uint64_t(begin) * count;
        if (input > 0xffffffffu)
            return false;
        auto from = rowSpan(run, uint32_t(input), length);
        if (!from)
            return false;
        for (uint64_t i = 0; i < length; ++i)
            to[i] = from[i];
        rowTicks(run, ticks);
        return true;
    }
    uint64_t mapToken = uint64_t(rowField(fields, 0x478)) + uint64_t(begin) * 4;
    if (mapToken > 0xffffffffu)
        return false;
    uint64_t mapLength = uint64_t(end - begin) * 4;
    auto map = rowSpan(run, uint32_t(mapToken), mapLength);
    if (!map || overlaps(to, length, map, mapLength))
        return false;
    uint32_t low = 0xffffffffu;
    uint32_t high = 0;
    for (uint32_t i = 0; i < end - begin; ++i) {
        uint32_t mapped;
        std::memcpy(&mapped, map + uint64_t(i) * 4, 4);
        uint32_t address = paper + mapped * count;
        if (uint64_t(address) + count > 0x100000000ull)
            return false;
        low = std::min(low, address);
        high = std::max(high, address + count - 1);
    }
    uint64_t inputLength = uint64_t(high) - low + 1;
    auto from = rowSpan(run, low, inputLength);
    if (!from || overlaps(to, length, from, inputLength))
        return false;
    uint8_t *shades = nullptr;
    uint8_t *colors = nullptr;
    if (shading) {
        uint64_t shadeToken = uint64_t(rowField(fields, 0x48c)) + begin;
        if (shadeToken > 0xffffffffu)
            return false;
        shades = rowSpan(run, uint32_t(shadeToken), end - begin);
        colors = rowSpan(run, palette, 0x4000);
        if (!shades || !colors || overlaps(to, length, shades, end - begin) || overlaps(to, length, colors, 0x4000))
            return false;
        for (uint32_t i = 0; i < end - begin; ++i) {
            if (shades[i] >= 64)
                return false;
        }
    }
    for (uint32_t i = 0; i < end - begin; ++i) {
        uint32_t mapped;
        std::memcpy(&mapped, map + uint64_t(i) * 4, 4);
        uint32_t address = paper + mapped * count;
        if (shading) {
            to[i] = colors[uint32_t(from[address - low]) * 64 + shades[i]];
        } else {
            for (uint32_t channel = 0; channel < count; ++channel)
                to[uint64_t(i) * count + channel] = from[address - low + channel];
        }
    }
    rowTicks(run, ticks);
    return true;
}
// Pixel assembly shared by the two original curl paths, retaining bytewise alias order.
void curlPixels(Run &run, uint32_t fader, uint32_t paper, uint32_t source, uint32_t begin, uint32_t end, uint32_t scratchOffset, uint32_t bpp, bool remapped, bool shading) {
    uint32_t palette = 0;
    if (shading)
        palette = run.get(run.get(fader + 0x1c) + 0x08);
    if (!shading && bpp != 1 && bpp != 2 && bpp != 3)
        return;
    if (s32(begin) >= s32(end))
        return;
    if (curlRow(run, fader, paper, source, begin, end, scratchOffset, shading ? 1 : bpp, remapped, shading, palette))
        return;
    for (uint32_t i = begin; s32(i) < s32(end); ++i) {
        if (remapped && shading) {
            uint32_t pixel = run.get8(paper + run.get(run.get(fader + 0x478) + i * 4));
            uint32_t shade = run.get8(run.get(fader + 0x48c) + i);
            run.put8(run.get(fader + 0x488) + scratchOffset + i, run.get8(palette + pixel * 64 + shade));
        } else {
            uint32_t count = shading ? 1 : bpp;
            for (uint32_t channel = 0; channel < count; ++channel) {
                uint32_t from = source + i * count + channel;
                if (remapped)
                    from = paper + run.get(run.get(fader + 0x478) + i * 4) * count + channel;
                run.put8(run.get(fader + 0x488) + scratchOffset + i * count + channel, run.get8(from));
            }
        }
    }
}
// 0x4ef010. Partial curl; +0x478 remap, +0x488 scratch, +0x48c shade bytes.
void partial(Run &run, uint32_t fader, uint32_t position, uint32_t delta) {
    uint32_t radius = run.get(fader + 0x58);
    uint32_t diameter = radius * 2;
    if (s32(delta) <= 0)
        return;
    uint32_t arc = radiusExtent(run, radius);
    uint32_t bpp = run.get(run.get(fader + 0x38) + 0xac);
    uint32_t split = position;
    auto reverse = [&]() {
        uint32_t mode = run.get(fader + 0x50);
        return (mode == 1 && run.get(fader + 0x54)) || (mode == 2 && !run.get(fader + 0x54));
    };
    auto forward = [&]() {
        uint32_t mode = run.get(fader + 0x50);
        return (mode == 1 && !run.get(fader + 0x54)) || (mode == 2 && run.get(fader + 0x54));
    };
    if (reverse()) {
        auto value = state();
        run.x87_step(CLAW_X87_I32, value, {diameter});
        arithmetic(run, value, CLAW_X87_DIV_F64, double(s32(arc - radius)));
        arithmetic(run, value, CLAW_X87_MUL_F64, double(s32(run.get(fader + 0x60) - diameter - position)));
        split = diameter - convert(run, value);
    }
    if (forward()) {
        auto value = state();
        run.x87_step(CLAW_X87_I32, value, {diameter});
        arithmetic(run, value, CLAW_X87_DIV_F64, double(s32(arc - radius)));
        arithmetic(run, value, CLAW_X87_MUL_F64, double(s32(position)));
        split = convert(run, value);
    }
    bool reversed = reverse();
    if (!reversed && !forward())
        return;
    uint32_t horizontal = bpp * position;
    for (uint32_t row = 0; s32(row) < run.gets(fader + 0x64); ++row) {
        uint32_t destination = run.get(run.get(fader + 0x44) + row * 4) + horizontal + run.get(fader + 0x47c);
        uint32_t paper = run.get(run.get(fader + 0x4c) + row * 4) + horizontal + run.get(fader + 0x484);
        uint32_t source = run.get(run.get(fader + 0x48) + row * 4) + horizontal + run.get(fader + 0x480);
        bool shading = run.get(fader + 0x5c) != 0;
        curlPixels(run, fader, paper, source, 0, split, 0, bpp, !reversed, shading);
        curlPixels(run, fader, paper, source, split, diameter, 0, bpp, reversed, shading);
        bytes(run, destination, run.get(fader + 0x488), bpp * diameter);
        uint32_t extra = bpp * delta;
        if (!run.get(fader + 0x54)) {
            zero(run, reversed ? destination + bpp * diameter : destination - extra, extra);
        } else {
            uint32_t fromPosition = reversed ? position - delta : position + diameter;
            uint32_t from = fromPosition * bpp + run.get(run.get(fader + 0x48) + row * 4) + run.get(fader + 0x480);
            bytes(run, reversed ? destination - extra : destination + bpp * diameter, from, extra);
        }
    }
}
// 0x4ef7d0. Full curl includes delta pixels alongside the complete mapped curl.
void full(Run &run, uint32_t fader, uint32_t position, uint32_t delta) {
    if (s32(delta) <= 0)
        return;
    uint32_t diameter = run.get(fader + 0x58) * 2;
    uint32_t mode = run.get(fader + 0x50);
    uint32_t bpp = run.get(run.get(fader + 0x38) + 0xac);
    uint32_t offset = mode == 1 ? delta : 0;
    uint32_t side = run.get(fader + 0x488) + (mode == 1 ? 0 : bpp * diameter);
    uint32_t fromBase = (mode == 1 ? position - delta : diameter + position) * bpp + run.get(fader + 0x480);
    if (mode != 1 && mode != 2)
        return;
    uint32_t targetBase = run.get(fader + 0x47c) + (position - offset) * bpp;
    uint32_t paperBase = run.get(fader + 0x484) + (position - offset) * bpp;
    for (uint32_t row = 0; s32(row) < run.gets(fader + 0x64); ++row) {
        uint32_t destination = run.get(run.get(fader + 0x44) + row * 4) + targetBase;
        uint32_t paper = run.get(run.get(fader + 0x4c) + row * 4) + paperBase;
        curlPixels(run, fader, paper, 0, 0, diameter, offset * (run.get(fader + 0x5c) ? 1 : bpp), bpp, true, run.get(fader + 0x5c) != 0);
        if (!run.get(fader + 0x54))
            zero(run, side, bpp * delta);
        else
            bytes(run, side, run.get(run.get(fader + 0x48) + row * 4) + fromBase, bpp * delta);
        bytes(run, destination, run.get(fader + 0x488), bpp * (diameter + delta));
    }
}
// 0x4eecc0. Progress is committed before the first COM unlock callback.
void render(Run &run, uint32_t fader, uint32_t progress) {
    Activation activation(run, run.frame, 0x1c);
    uint32_t pointer = run.call(0x4b9730, run.get(fader + 0x38), {0});
    run.put(fader + 0x47c, pointer);
    pointer = run.call(0x4b9730, run.get(fader + 0x3c), {0});
    uint32_t paper = run.get(fader + 0x40);
    uint32_t source = run.get(fader + 0x3c);
    run.put(fader + 0x480, pointer);
    if (source != paper)
        pointer = run.call(0x4b9730, paper, {0});
    run.put(fader + 0x484, pointer);
    uint32_t radius = run.get(fader + 0x58);
    uint32_t diameter = radius * 2;
    uint32_t arc = radiusExtent(run, radius);
    uint32_t center = 0;
    if (run.get(fader + 0x50) == 3 && run.get(fader + 0x54))
        center = uint32_t(run.gets(fader + 0x60) / 2);
    if (!run.get(fader + 0x54) && !progress) {
        uint32_t pitch = uint32_t(std::min(run.gets(run.get(fader + 0x38) + 0x1c), run.gets(run.get(fader + 0x3c) + 0x1c)));
        for (uint32_t row = 0; s32(row) < run.gets(fader + 0x64); ++row) {
            uint32_t from = run.get(run.get(fader + 0x48) + row * 4) + run.get(fader + 0x480);
            uint32_t to = run.get(run.get(fader + 0x44) + row * 4) + run.get(fader + 0x47c);
            bytes(run, to, from, pitch);
        }
    }
    if (run.get(fader + 0x54)) {
        uint32_t width = run.get(fader + 0x60);
        bool isPartial = center + progress > width - arc - run.get(fader + 0x58);
        uint32_t mode = run.get(fader + 0x50);
        auto draw = [&](uint32_t x) {
            if (isPartial)
                partial(run, fader, x, progress - run.get(fader + 0x20));
            else
                full(run, fader, x, progress - run.get(fader + 0x20));
        };
        if (mode == 1)
            draw(progress);
        else if (mode == 2)
            draw(width - progress - diameter);
        else if (mode == 3) {
            run.put(fader + 0x50, 1);
            draw(uint32_t(s32(width) / 2) + progress);
            uint32_t currentWidth = run.get(fader + 0x60);
            run.put(fader + 0x50, 2);
            uint32_t half = uint32_t(s32(currentWidth) / 2);
            draw((isPartial ? currentWidth - half : half) - progress - diameter);
            run.put(fader + 0x50, 3);
        }
    }
    if (!run.get(fader + 0x54)) {
        bool isFull = center + progress > arc - run.get(fader + 0x58);
        uint32_t mode = run.get(fader + 0x50);
        auto draw = [&](uint32_t x) {
            if (isFull)
                full(run, fader, x, progress - run.get(fader + 0x20));
            else
                partial(run, fader, x, progress - run.get(fader + 0x20));
        };
        if (mode == 1)
            draw(progress);
        else if (mode == 2)
            draw(run.get(fader + 0x60) - progress - diameter);
        else if (mode == 3) {
            run.put(fader + 0x50, 1);
            draw(progress);
            uint32_t width = run.get(fader + 0x60);
            run.put(fader + 0x50, 2);
            draw(width - progress - diameter);
            run.put(fader + 0x50, 3);
        }
    }
    uint32_t destination = run.get(fader + 0x38);
    run.put(fader + 0x20, progress);
    uint32_t interface = run.get(destination + 0x08);
    run.call(run.get(run.get(interface) + 0x80), 0, {interface, 0});
    interface = run.get(run.get(fader + 0x3c) + 0x08);
    run.call(run.get(run.get(interface) + 0x80), 0, {interface, 0});
    paper = run.get(fader + 0x40);
    if (run.get(fader + 0x3c) != paper) {
        interface = run.get(paper + 0x08);
        run.call(run.get(run.get(interface) + 0x80), 0, {interface, 0});
    }
}
uint32_t destinationSurface(Run &run, uint32_t menu) {
    return run.get(run.get(run.get(run.get(menu + 0x0c) + 0x04) + 0x10) + 0x2c);
}
void sound(Run &run, uint32_t depth, uint32_t menu, uint32_t name, uint32_t output) {
    uint32_t manager = run.get(run.get(menu + 0x0c) + 0x28);
    if (run.get(manager + 0x30))
        return;
    run.put(output, 0);
    at(run, depth, 0x4f6286, manager + 0x10, {name, output});
    uint32_t entry = run.get(output);
    if (entry && run.get(0x532c0c))
        at(run, depth, 0x4b45f0, run.get(entry + 0x10), {run.get(0x532c10), 0, 0, 0});
}
// 0x48f500 / 0x48f740 use the same cached paper resource operation.
uint32_t paperSurface(Run &run, uint32_t menu, uint32_t manager) {
    uint32_t paper = run.get(menu + 0x40);
    if (paper)
        return paper;
    uint32_t resource = run.call(0x4b7f00, run.get(menu + 0x08), {0x528e38, 0x504358});
    if (!resource)
        return 0;
    uint32_t data = run.call(0x4b61c0, resource);
    if (!data)
        return 0;
    uint32_t created = run.call(0x4bc520, manager, {data, 2, run.get(resource + 0x14), 0x800, 0xffffffff});
    run.put(menu + 0x40, created);
    run.call(0x4b6230, resource);
    return run.get(menu + 0x40);
}
void configure(Run &run, uint32_t menu, uint32_t record, uint32_t destination, uint32_t palette, uint32_t direction) {
    initRecord(run, record);
    uint32_t temporary = run.get(menu + 0x3c);
    uint32_t paper = run.get(menu + 0x40);
    run.put(record + 0x08, temporary);
    run.put(record + 0x04, destination);
    run.put(record + 0x1c, palette != 0);
    run.put(record + 0x0c, paper);
    run.put(record + 0x10, 40);
    run.put(record + 0x14, 3);
    run.put(record + 0x18, direction);
    run.put(record + 0x20, palette);
}
// 0x48f500. Menu fields +4 application, +8 resources, +0xc services,
// +0x10 faders, +0x3c temporary surface, +0x40 cached paper.
uint32_t paperTransition(Run &run, uint32_t menu, uint32_t duration) {
    Activation activation(run, run.frame, 0x54);
    uint32_t faders = run.get(menu + 0x10);
    if (!faders)
        return 0;
    uint32_t services = run.get(menu + 0x0c);
    uint32_t surfaces = run.get(services + 0x1c);
    if (!surfaces)
        return 0;
    uint32_t destination = destinationSurface(run, menu);
    if (!destination)
        return 0;
    uint32_t height = run.get(destination + 0x14);
    uint32_t width = run.get(destination + 0x18);
    uint32_t output = run.automatic(-0x44);
    run.put(output, height);
    uint32_t temporary = at(run, 0x54, 0x4bc670, surfaces, {width, height, 8, 0x800, 0xffffffff});
    run.put(menu + 0x3c, temporary);
    if (!temporary)
        return 0;
    if (copySurface(run, temporary, destination))
        return 0;
    uint32_t paper = paperSurface(run, menu, surfaces);
    if (!paper)
        return 0;
    if (run.get(paper + 0x18) != width || run.get(paper + 0x14) != height)
        return 0;
    uint32_t palette;
    {
        Activation child(run, run.frame - 0x58, 0x0c);
        palette = rollerPalette(run, run.get(menu + 0x04));
    }
    uint32_t record = run.automatic(-0x38);
    configure(run, menu, record, destination, palette, 0);
    uint32_t fader = at(run, 0x54, 0x4ec050, faders, {0, record});
    if (!fader) {
        at(run, 0x54, 0x4f6584, record + 0x24);
        return 0;
    }
    at(run, 0x54, 0x42d420, run.get(menu + 0x04));
    if (run.get(0x537238)) {
        at(run, 0x54, 0x4b8960, 0, {duration});
        at(run, 0x54, 0x4b97c0, destinationSurface(run, menu), {0});
    } else {
        sound(run, 0x54, menu, 0x52c6d0, output);
        at(run, 0x54, 0x4ec9c0, fader, {duration, 0, 0});
    }
    at(run, 0x54, 0x42d440, run.get(menu + 0x04));
    at(run, 0x54, 0x4ec600, faders, {fader});
    at(run, 0x54, 0x4bc4f0, surfaces, {run.get(menu + 0x3c)});
    run.put(menu + 0x3c, 0);
    at(run, 0x54, 0x4f6584, record + 0x24);
    return 1;
}
// 0x48f740. Screen resource formatting and palette operations precede the unroll.
uint32_t unroll(Run &run, uint32_t menu, const uint32_t *arguments) {
    Activation activation(run, run.frame, 0x98);
    uint32_t faders = run.get(menu + 0x10);
    if (!faders)
        return 0;
    uint32_t services = run.get(menu + 0x0c);
    uint32_t surfaces = run.get(services + 0x1c);
    if (!surfaces)
        return 0;
    uint32_t destination = destinationSurface(run, menu);
    if (!destination)
        return 0;
    uint32_t width = run.get(destination + 0x18);
    uint32_t height = run.get(destination + 0x14);
    uint32_t output = run.automatic(-0x84);
    run.put(output, width);
    run.put(run.automatic(-0x80), height);
    uint32_t name = run.automatic(-0x4c);
    at(run, 0x98, 0x4a3920, 0, {name, 0x528e54, arguments[0]});
    uint32_t resource = at(run, 0x98, 0x4b7dc0, run.get(menu + 0x20), {name, 0x504358});
    if (!resource)
        return 0;
    uint32_t data = at(run, 0x98, 0x4b61c0, resource);
    if (!data)
        return 0;
    uint32_t temporary = at(run, 0x98, 0x4bc520, surfaces, {data, 2, run.get(resource + 0x14), 0x800, 0xffffffff});
    run.put(menu + 0x3c, temporary);
    if (!temporary)
        return 0;
    if (!run.get(menu + 0x2c)) {
        uint32_t screen = virtualAt(run, 0x98, run.get(run.get(menu + 0x0c) + 0x18), 0x30, {resource, 0, 0});
        run.put(menu + 0x2c, screen);
        if (!screen)
            return 0;
    }
    at(run, 0x98, 0x4b6230, resource);
    if (arguments[1])
        at(run, 0x98, 0x4bbf60, run.get(run.get(menu + 0x2c) + 0x10));
    if (arguments[2]) {
        at(run, 0x98, 0x4bb870, run.get(run.get(menu + 0x2c) + 0x10));
        at(run, 0x98, 0x4bb990, run.get(run.get(menu + 0x2c) + 0x10), {0, 0x100, 0, 0, 0, arguments[2]});
        uint32_t platform = run.get(run.get(menu + 0x0c) + 0x04);
        at(run, 0x98, 0x4b97c0, run.get(run.get(platform + 0x14) + 0x2c), {0});
        at(run, 0x98, 0x4b98b0, run.get(run.get(platform + 0x10) + 0x2c), {0});
        at(run, 0x98, 0x4bb8c0, run.get(run.get(menu + 0x2c) + 0x10), {0});
    }
    uint32_t screen = run.get(menu + 0x2c);
    run.put(run.get(run.get(menu + 0x0c) + 0x18) + 0x64, screen);
    virtualAt(run, 0x98, screen, 0x34);
    uint32_t paper = paperSurface(run, menu, surfaces);
    if (!paper)
        return 0;
    if (run.get(paper + 0x18) != width || run.get(paper + 0x14) != height)
        return 0;
    uint32_t palette;
    {
        Activation child(run, run.frame - 0x9c, 0x0c);
        palette = rollerPalette(run, run.get(menu + 0x04));
    }
    uint32_t record = run.automatic(-0x78);
    configure(run, menu, record, destination, palette, 1);
    uint32_t fader = at(run, 0x98, 0x4ec050, faders, {0, record});
    if (!fader) {
        at(run, 0x98, 0x4f6584, record + 0x24);
        return 0;
    }
    at(run, 0x98, 0x42d420, run.get(menu + 0x04));
    if (run.get(0x537238)) {
        at(run, 0x98, 0x4b8960, 0, {arguments[4]});
        services = run.get(menu + 0x0c);
        temporary = run.get(menu + 0x3c);
        uint32_t node = run.get(run.get(services + 0x04) + 0x10);
        if (temporary)
            copySurface(run, run.get(node + 0x2c), temporary);
    } else {
        sound(run, 0x98, menu, arguments[3] ? 0x52c6d8 : 0x528e30, output);
        at(run, 0x98, 0x4ec9c0, fader, {arguments[4], arguments[3], 0});
    }
    at(run, 0x98, 0x42d440, run.get(menu + 0x04));
    at(run, 0x98, 0x4ec600, faders, {fader});
    at(run, 0x98, 0x4bc4f0, surfaces, {run.get(menu + 0x3c)});
    run.put(menu + 0x3c, 0);
    at(run, 0x98, 0x4f6584, record + 0x24);
    return 1;
}
// 0x4efac0. Extent uses signed truncation for split mode.
uint32_t extent(Run &run, uint32_t fader) {
    uint32_t mode = run.get(fader + 0x50);
    if (mode == 1 || mode == 2)
        return run.get(fader + 0x60) - run.get(fader + 0x58) * 2;
    if (mode == 3)
        return uint32_t(s32(run.get(fader + 0x60) - run.get(fader + 0x58) * 4) / 2);
    return 0;
}
int owned(uint32_t function) {
    switch (function) {
    case 0x42a4f0:
    case 0x4c6260:
    case 0x4c96b0:
    case 0x4ecb40:
    case 0x4ee880:
    case 0x4ee8e0:
    case 0x4efac0:
        return 0;
    case 0x48f500:
    case 0x4b9c50:
    case 0x4c7730:
    case 0x4d4100:
    case 0x4ee8c0:
    case 0x4ee9a0:
    case 0x4eecc0:
        return 1;
    case 0x4c7360:
    case 0x4c7850:
    case 0x4ef010:
    case 0x4ef7d0:
        return 2;
    case 0x48f740:
        return 5;
    default:
        return -1;
    }
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    Activation activation(run, run.frame, 0x100);
    switch (function) {
    case 0x42a4f0:
        return rollerPalette(run, receiver);
    case 0x48f500:
        return paperTransition(run, receiver, arguments[0]);
    case 0x48f740:
        return unroll(run, receiver, arguments);
    case 0x4b9c50:
        return copySurface(run, receiver, arguments[0]);
    case 0x4c6260:
        run.put(receiver + 0x00, 1);
        return 1;
    case 0x4c7360:
        return paletteBytes(run, receiver, arguments[0], arguments[1]);
    case 0x4c7730:
        return readStream(run, receiver, arguments[0]);
    case 0x4c7850:
        return tableBytes(run, receiver, arguments[0], arguments[1]);
    case 0x4c96b0:
        return 0;
    case 0x4d4100:
        return bindSurface(run, receiver, arguments[0]);
    case 0x4ecb40:
        return initRecord(run, receiver);
    case 0x4ee880:
        return construct(run, receiver);
    case 0x4ee8c0:
        destroy(run, receiver);
        if (arguments[0] & 1)
            run.call(0x4f6428, 0, {receiver});
        return receiver;
    case 0x4ee8e0:
        destroy(run, receiver);
        return 0;
    case 0x4ee9a0:
        return initialize(run, receiver, arguments[0]);
    case 0x4eecc0:
        render(run, receiver, arguments[0]);
        return 0;
    case 0x4ef010:
        partial(run, receiver, arguments[0], arguments[1]);
        return 0;
    case 0x4ef7d0:
        full(run, receiver, arguments[0], arguments[1]);
        return 0;
    case 0x4efac0:
        return extent(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_menu_paper_transition_entry, owned, body)
