#include "PIDRaster.h"

static uint32_t read32(const uint8_t *p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}
static int32_t signed32(uint32_t value) {
    return value < 0x80000000u ? int32_t(value) : int32_t(int64_t(value) - 0x100000000LL);
}

extern "C" uint32_t claw_pid_decode_raster8(const uint8_t *pid, size_t length, uint8_t *output, uint8_t *coverage,
                                            size_t capacity, size_t stride, ClawPIDRasterInfo *info) {
    if (!pid || !output || !coverage || !info || length < 32)
        return 0;
    const uint32_t flags = read32(pid + 4), w = read32(pid + 8), h = read32(pid + 12);
    if (!(flags & 0x20u) || !w || !h || w > 4096 || h > 4096 || stride < w)
        return 0;
    if (stride && size_t(h) > SIZE_MAX / stride)
        return 0;
    if (capacity < stride * size_t(h))
        return 0;
    size_t limit = length;
    if (flags & 0x80u) {
        if (length < 32 + 768)
            return 0;
        limit -= 768;
    }
    // Original valid-data row grammar: high-bit tokens skip token-128 pixels,
    // low-bit tokens copy exactly token palette indices. Row ends at width.
    size_t position = 32;
    for (uint32_t y = 0; y < h; ++y) {
        uint32_t x = 0;
        while (x < w) {
            if (position >= limit)
                return 0;
            const uint8_t token = pid[position++];
            const uint32_t count = token & 0x7fu;
            if (!count || count > w - x)
                return 0;
            if (!(token & 0x80u)) {
                if (count > limit - position)
                    return 0;
                position += count;
            }
            x += count;
        }
    }
    const size_t consumed = position;
    position = 32;
    for (uint32_t y = 0; y < h; ++y) {
        uint32_t x = 0;
        while (x < w) {
            const uint8_t token = pid[position++];
            const uint32_t count = token & 0x7fu;
            for (uint32_t i = 0; i < count; ++i) {
                const size_t target = size_t(y) * stride + x + i;
                const bool literal = !(token & 0x80u);
                output[target] = literal ? pid[position + i] : 0;
                coverage[target] = literal ? 1 : 0;
            }
            if (!(token & 0x80u))
                position += count;
            x += count;
        }
    }
    *info = {w, h, signed32(read32(pid + 16)), signed32(read32(pid + 20)), consumed};
    return 1;
}
