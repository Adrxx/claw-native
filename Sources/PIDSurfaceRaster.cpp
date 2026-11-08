#include "PIDSurfaceRaster.h"
#include <cstring>
#include <limits>

namespace {
uint32_t word(const uint8_t *p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}
// Recovered from 0x4babe0: each row starts at its surface pitch; tokens with
// BOTH high bits set consume a following index and repeat low six bits times.
// 0xc0 therefore consumes its index but writes nothing; remaining tokens are
// individual literal indices. Full surface creation/color conversion is external.
bool rows(const uint8_t *pid, size_t end, uint32_t width, uint32_t height, bool keyed, uint8_t *output,
          uint8_t *coverage, size_t stride, size_t &consumed) {
    size_t cursor = 32;
    for (uint32_t y = 0; y < height; ++y) {
        uint32_t x = 0;
        while (x < width) {
            if (cursor >= end)
                return false;
            uint8_t index = pid[cursor++];
            uint32_t count = 1;
            if ((index & 0xc0) == 0xc0) {
                count = index & 0x3f;
                if (cursor >= end)
                    return false;
                index = pid[cursor++];
            }
            if (count > width - x)
                return false;
            if (output && count) {
                std::memset(output + size_t(y) * stride + x, index, count);
                std::memset(coverage + size_t(y) * stride + x, keyed && index == 0 ? 0 : 1, count);
            }
            x += count;
        }
    }
    consumed = cursor;
    return true;
}
} // namespace

uint32_t claw_pid_decode_surface_raster8(const uint8_t *pid, size_t length, uint32_t useColorKey, uint8_t *output,
                                         uint8_t *coverage, size_t capacity, size_t rowStride,
                                         ClawPIDSurfaceRasterInfo *info) {
    if (!pid || !output || !coverage || !info || length < 32)
        return 0;
    const uint32_t flags = word(pid + 4), width = word(pid + 8), height = word(pid + 12);
    if (flags & 0x20 || !width || !height || width > 4096 || height > 4096 || (width & 3))
        return 0;
    if (rowStride < width || rowStride > std::numeric_limits<size_t>::max() / height || capacity < rowStride * height)
        return 0;
    size_t end = length;
    if (flags & 0x80) {
        if (end < 32 + 768)
            return 0;
        end -= 768;
    }
    const bool keyed = (flags & 1) && useColorKey;
    size_t consumed = 0;
    if (!rows(pid, end, width, height, keyed, nullptr, nullptr, rowStride, consumed))
        return 0;
    rows(pid, end, width, height, keyed, output, coverage, rowStride, consumed);
    ClawPIDSurfaceRasterInfo result{};
    result.width = width;
    result.height = height;
    result.offsetX = int32_t(word(pid + 16));
    result.offsetY = int32_t(word(pid + 20));
    result.consumed = consumed;
    result.colorKeyEnabled = keyed;
    *info = result;
    return 1;
}
