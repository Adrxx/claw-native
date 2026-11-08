#include "RawTileDescriptionRuntime.h"
#include "TileCollision.h"
#include "WorldFileRuntime.h"
#include <cstring>

namespace {
struct Run {
    ClawSceneActorHost host;
    uint32_t fault = 0;
    uint8_t *span(uint32_t token, uint32_t bytes) {
        if (fault)
            return nullptr;
        uint32_t offset = token & 3u;
        auto *p = host.lookup ? host.lookup(host.context, token & ~3u, (offset + bytes + 3u) / 4u) : nullptr;
        if (!p) {
            fault = 1;
            return nullptr;
        }
        return reinterpret_cast<uint8_t *>(p) + offset;
    }
    uint32_t word(uint32_t token) {
        uint32_t value = 0;
        if (auto *p = span(token, 4))
            std::memcpy(&value, p, 4);
        return value;
    }
    uint32_t byte(uint32_t token) {
        auto *p = span(token, 1);
        return p ? *p : 0;
    }
    void put(uint32_t token, uint32_t value) {
        if (auto *p = span(token, 4))
            std::memcpy(p, &value, 4);
    }
};
int32_t signedWord(uint32_t v) {
    int32_t result;
    std::memcpy(&result, &v, 4);
    return result;
}
const uint32_t rectangleFunctions[] = {0x4d5c80, 0x4d5ce0, 0x4d5e30, 0x4d5e90, 0x4d5d50, 0x4d5dc0, 0x4d5f00, 0x4d5f70};
const uint32_t maskFunctions[] = {0x4d5900, 0x4d5960, 0x4d59b0, 0x4d5a20, 0x4d5a80, 0x4d5af0, 0x4d5b50, 0x4d5bd0};
int indexOf(const uint32_t *functions, uint32_t function) {
    for (int i = 0; i < 8; ++i)
        if (functions[i] == function)
            return i;
    return -1;
}
uint32_t rectangleScan(Run &r, uint32_t t, ClawRawTileArguments a, int method) {
    const bool vertical = (method / 2) & 1, forward = method >= 4, target = method & 1;
    const uint32_t cross = a.words[vertical ? 0 : 1], coordinate = a.words[vertical ? 1 : 0];
    const uint32_t crossLowOffset = vertical ? 0x14 : 0x18, crossHighOffset = vertical ? 0x1c : 0x20;
    if (signedWord(cross) < signedWord(r.word(t + crossLowOffset)))
        return 0;
    if (signedWord(cross) > signedWord(r.word(t + crossHighOffset)))
        return 0;
    const uint32_t lowOffset = vertical ? 0x18 : 0x14, highOffset = vertical ? 0x20 : 0x1c;
    uint32_t candidate, attributeOffset;
    if (!forward) {
        const uint32_t low = r.word(t + lowOffset);
        if (signedWord(coordinate) < signedWord(low))
            return 0;
        const uint32_t high = r.word(t + highOffset);
        if (signedWord(coordinate) > signedWord(high)) {
            candidate = high;
            attributeOffset = 0x10;
        } else if (signedWord(low) > 0) {
            candidate = low - 1;
            attributeOffset = 0xc;
        } else
            return 0;
    } else {
        const uint32_t high = r.word(t + highOffset);
        if (signedWord(coordinate) > signedWord(high))
            return 0;
        const uint32_t low = r.word(t + lowOffset);
        if (signedWord(coordinate) < signedWord(low)) {
            candidate = low;
            attributeOffset = 0x10;
        } else if (signedWord(high) < signedWord(r.word(t + (vertical ? 8 : 4)) - 1)) {
            candidate = high + 1;
            attributeOffset = 0xc;
        } else
            return 0;
    }
    if (target) {
        if (r.word(t + attributeOffset) != a.words[2])
            return 0;
        r.put(a.words[3], candidate);
    } else {
        r.put(a.words[2], candidate);
        // Original reads the selected attribute after the first output store.
        const uint32_t attribute = r.word(t + attributeOffset);
        r.put(a.words[3], attribute);
    }
    return 1;
}
uint32_t maskScan(Run &r, uint32_t t, ClawRawTileArguments a, int method) {
    const bool vertical = (method / 2) & 1, forward = method >= 4, target = method & 1;
    uint32_t index = (a.words[1] << (r.word(t + 0xc) & 31u)) + a.words[0];
    uint32_t coordinate = a.words[vertical ? 1 : 0], base = 0, initial = 0;
    if (!target) {
        base = r.word(t + 0x14);
        initial = r.byte(base + index);
    }
    const uint32_t limit = forward ? r.word(t + (vertical ? 8 : 4)) - 1 : 0;
    if (forward ? signedWord(coordinate) >= signedWord(limit) : signedWord(coordinate) <= 0)
        return 0;
    const uint32_t step = vertical ? r.word(t + 4) : 1;
    if (target)
        base = r.word(t + 0x14);
    for (uint32_t count = 0; !r.fault; ++count) {
        if (count == 1000000) {
            r.fault = 3;
            return 0;
        }
        coordinate += forward ? 1u : uint32_t(-1);
        index += forward ? step : uint32_t(0) - step;
        const uint32_t value = r.byte(base + index);
        if (target ? value == a.words[2] : value != initial) {
            if (target)
                r.put(a.words[3], coordinate);
            else {
                r.put(a.words[2], coordinate);
                // The mask token is reloaded after the coordinate output.
                const uint32_t attribute = r.byte(r.word(t + 0x14) + index);
                r.put(a.words[3], attribute);
            }
            return 1;
        }
        if (forward ? signedWord(coordinate) >= signedWord(limit) : signedWord(coordinate) <= 0)
            return 0;
    }
    return 0;
}
} // namespace

extern "C" uint32_t claw_raw_tile_function(uint32_t vtable, uint32_t slot) {
    if (slot == 0x1c)
        return vtable == 0x513980 ? 0x4bd250 : vtable == 0x5139c8 ? 0x4bd240 : vtable == 0x513a10 ? 0x40af90 : 0;
    if (slot == 0x20)
        return vtable == 0x513980 ? 0x4cddc0 : vtable == 0x5139c8 ? 0x4cde10 : vtable == 0x513a10 ? 0x4cdef0 : 0;
    if (slot == 0x24)
        return vtable == 0x513980 ? 0x4cde00 : vtable == 0x5139c8 ? 0x4cde40 : vtable == 0x513a10 ? 0x4cdf10 : 0;
    if (slot < 0x28 || slot > 0x44 || (slot & 3u))
        return 0;
    const uint32_t index = (slot - 0x28) / 4;
    if (vtable == 0x5139c8)
        return rectangleFunctions[index];
    if (vtable == 0x513a10)
        return maskFunctions[index];
    if (vtable == 0x513980)
        return slot == 0x38 ? 0x4cdde0 : slot == 0x40 ? 0x4cddf0 : 0x4cddd0;
    return 0;
}
extern "C" uint32_t claw_raw_tile_entry(uint32_t function, uint32_t token, ClawRawTileArguments a,
                                        ClawSceneActorHost host, uint32_t *fault, uint32_t *result) {
    Run r{host};
    uint32_t value = 0, expected;
    const int rectangle = indexOf(rectangleFunctions, function), mask = indexOf(maskFunctions, function);
    if (rectangle >= 0 || mask >= 0 || function == 0x4cddd0 || function == 0x4cdde0 || function == 0x4cddf0)
        expected = 4;
    else if (function == 0x4cddc0 || function == 0x4cde10 || function == 0x4cdef0)
        expected = 2;
    else if (function == 0x4bd250 || function == 0x4bd240 || function == 0x40af90 || function == 0x4cde00 ||
             function == 0x4cde40 || function == 0x4cdf10)
        expected = 0;
    else {
        if (fault)
            *fault = 2;
        return 0;
    }
    if (a.count != expected) {
        if (fault)
            *fault = 2;
        return 0;
    }
    if (rectangle >= 0)
        value = rectangleScan(r, token, a, rectangle);
    else if (mask >= 0)
        value = maskScan(r, token, a, mask);
    else
        switch (function) {
        case 0x4bd250:
            value = 1;
            break;
        case 0x4bd240:
            value = 2;
            break;
        case 0x40af90:
            value = 3;
            break;
        case 0x4cddd0:
            break;
        case 0x4cdde0:
            value = r.word(token + 4) - 1;
            break;
        case 0x4cddf0:
            value = r.word(token + 8) - 1;
            break;
        case 0x4cddc0: {
            ClawTileDescription tile{};
            tile.type = 1;
            tile.insideAttribute = r.word(token + 0xc);
            value = claw_tile_attribute(&tile, signedWord(a.words[0]), signedWord(a.words[1]));
            break;
        }
        case 0x4cde10:
            if (signedWord(a.words[0]) >= signedWord(r.word(token + 0x14)) &&
                signedWord(a.words[0]) <= signedWord(r.word(token + 0x1c)) &&
                signedWord(a.words[1]) >= signedWord(r.word(token + 0x18)) &&
                signedWord(a.words[1]) <= signedWord(r.word(token + 0x20)))
                value = r.word(token + 0x10);
            else
                value = r.word(token + 0xc);
            break;
        case 0x4cdef0: {
            const uint32_t index = (a.words[1] << (r.word(token + 0xc) & 31u)) + a.words[0];
            value = r.byte(r.word(token + 0x14) + index);
            break;
        }
        default: {
            ClawWorldFileContext context{};
            context.scene = host;
            ClawWorldFileArguments arguments{};
            if (!claw_world_file_entry(function, token, arguments, &context, nullptr, nullptr, &value))
                r.fault = context.fault ? context.fault : 2;
            break;
        }
        }
    if (fault)
        *fault = r.fault;
    if (result)
        *result = value;
    return r.fault ? 0 : 1;
}
extern "C" uint32_t claw_raw_tile_virtual(uint32_t token, uint32_t slot, ClawRawTileArguments a,
                                          ClawSceneActorHost host, uint32_t *fault, uint32_t *result) {
    Run r{host};
    const uint32_t function = claw_raw_tile_function(r.word(token), slot);
    if (r.fault || !function) {
        if (fault)
            *fault = r.fault ? r.fault : 2;
        return 0;
    }
    return claw_raw_tile_entry(function, token, a, host, fault, result);
}
