#include "LightPIDBlitter.h"
#include <algorithm>
#include <cstring>
#include <vector>
namespace {
uint32_t word(const uint8_t *p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}
struct Invalid {};
struct Run {
    int32_t count;
    bool literal;
    size_t start;
};
struct Engine {
    const uint8_t *pid;
    size_t end, cursor = 32;
    int32_t width, height;
    const ClawPIDBlitCommand &c;
    const ClawLightPIDBlitState &state;
    const ClawLightPIDBlitTable &table;
    uint8_t *output;
    uint8_t *coverage;
    size_t capacity, stride, writes = 0;
    uint8_t *scratch;
    uint32_t steps = 0;
    void next() {
        if (++steps > 20000000)
            throw Invalid{};
    }
    Run run() {
        next();
        if (cursor >= end)
            throw Invalid{};
        uint8_t b = pid[cursor++];
        Run r{int32_t(b & 128 ? b - 128 : b), !(b & 128), cursor};
        if (!r.count || (r.literal && size_t(r.count) > end - cursor))
            throw Invalid{};
        if (r.literal)
            cursor += r.count;
        return r;
    }
    void range(int64_t at, size_t n) {
        if (at < 0 || uint64_t(at) > capacity || n > capacity - size_t(at))
            throw Invalid{};
    }
    void store(int64_t at, uint8_t v) {
        range(at, 1);
        output[at] = v;
        if (coverage)
            coverage[at] = 1;
        ++writes;
    }
    void pixels(size_t src, int64_t at, int32_t count, int32_t row) {
        if (count <= 0)
            return;
        if (count > 127 || src > end || size_t(count) > end - src)
            throw Invalid{};
        const bool paired = state.renderWord != 0;
        if (paired && !((uint32_t(row) + uint32_t(c.destination.top)) & 1))
            return;
        const int64_t low = c.flipX ? at - count + 1 : at;
        range(low, size_t(count));
        std::memcpy(scratch, output + low, size_t(count));
        for (int32_t i = 0; i < count; ++i) {
            const uint8_t old = scratch[c.flipX ? count - 1 - i : i], source = pid[src + i];
            const uint8_t v = table.data[(uint32_t(old) << 8) + source];
            const int64_t dst = at + (c.flipX ? -int64_t(i) : int64_t(i));
            store(dst, v);
            if (paired)
                store(dst + int64_t(stride), v);
        }
    }
    void blit() {
        int32_t row = 0, x = c.flipX && c.flipY ? int32_t(state.bothTopSkipSeed) : 0;
        while (row < c.source.top) {
            auto r = run();
            x = int32_t(uint32_t(x) + uint32_t(r.count));
            if (x >= width) {
                ++row;
                x = 0;
            }
        }
        int64_t base =
            int64_t(c.flipY ? c.destination.bottom : c.destination.top) * int64_t(stride) + c.destination.left;
        const int64_t delta = c.flipY ? -int64_t(stride) : int64_t(stride);
        x = c.flipX ? width : 0;
        if (!c.flipX) {
            if (c.source.left == 0) {
                while (row <= c.source.bottom) {
                    auto r = run();
                    if (r.literal) {
                        int32_t n = r.count;
                        if (c.source.right != width - 1)
                            n = int32_t(std::max<int64_t>(0, std::min<int64_t>(n, int64_t(c.source.right) - x)));
                        pixels(r.start, base + x, n, row);
                    }
                    x += r.count;
                    if (x >= width) {
                        ++row;
                        base += delta;
                        x = 0;
                    }
                }
            } else {
                while (row < c.source.bottom) {
                    if (x < c.source.left) {
                        Run r{};
                        do {
                            r = run();
                            x += r.count;
                        } while (x < c.source.left);
                        if (x > c.source.left && r.literal) {
                            int32_t n = x - c.source.left;
                            pixels(cursor - n, base, n, row);
                        }
                    }
                    if (x < width) {
                        auto r = run();
                        if (r.literal)
                            pixels(r.start, base + x - c.source.left, r.count, row);
                        x += r.count;
                    } else {
                        ++row;
                        base += delta;
                        x = 0;
                    }
                }
            }
        } else if (c.source.left != 0) {
            while (row <= c.source.bottom) {
                auto r = run();
                if (r.literal)
                    pixels(r.start, base + x - c.source.left, std::max(0, std::min(r.count, x - c.source.left)), row);
                x -= r.count;
                if (x < 1) {
                    ++row;
                    base += delta;
                    x = width;
                }
            }
        } else if (c.source.right == width - 1) {
            while (row <= c.source.bottom) {
                auto r = run();
                if (r.literal)
                    pixels(r.start, base + x, r.count, row);
                x -= r.count;
                if (x < 1) {
                    ++row;
                    base += delta;
                    x = width;
                }
            }
        } else {
            auto hasRow = [&] {
                return c.flipY ? row <= c.source.bottom : row < c.source.bottom;
            };
            while (hasRow()) {
                bool advance = false;
                if (c.source.right < x) {
                    Run r{};
                    do {
                        r = run();
                        x -= r.count;
                    } while (c.source.right < x);
                    if (x >= 0) {
                        if (r.literal) {
                            int32_t n = c.source.right - x;
                            pixels(cursor - n, base + c.source.right, n, row);
                        }
                    } else
                        advance = true;
                }
                if (x < 1)
                    advance = true;
                if (advance) {
                    ++row;
                    base += delta;
                    x = width;
                } else {
                    auto r = run();
                    if (r.literal)
                        pixels(r.start, base + x, r.count, row);
                    x -= r.count;
                }
            }
        }
    }
};
bool valid(const uint8_t *p, size_t end, int32_t w, int32_t h) {
    size_t at = 32;
    for (int32_t y = 0; y < h; ++y) {
        int32_t x = 0;
        while (x < w) {
            if (at >= end)
                return false;
            uint8_t b = p[at++];
            int32_t n = b & 128 ? b - 128 : b;
            if (!n || n > w - x)
                return false;
            if (!(b & 128)) {
                if (size_t(n) > end - at)
                    return false;
                at += n;
            }
            x += n;
        }
    }
    return true;
}
} // namespace
extern "C" uint32_t claw_light_pid_blit8(const uint8_t *pid, size_t length, const ClawPIDBlitCommand *c,
                                         const ClawLightPIDBlitState *state, const ClawLightPIDBlitTable *table,
                                         uint8_t *output, uint8_t *coverage, size_t capacity, size_t stride,
                                         uint8_t *scratch, ClawLightPIDBlitInfo *info) {
    if (!pid || !c || !state || !output || length < 32 || !(word(pid + 4) & 32))
        return 0;
    const int32_t w = int32_t(word(pid + 8)), h = int32_t(word(pid + 12));
    if (w < 1 || h < 1 || w > 4096 || h > 4096 || !stride || stride > INT32_MAX || capacity > INT32_MAX)
        return 0;
    if (c->source.left < 0 || c->source.right > w - 1 || c->source.top < 0 || c->source.top > h - 1)
        return 0;
    if ((state->formatByte & 255) != 1)
        return 0;
    if (state->effectMode == 1) {
        ClawPIDBlitInfo normal{};
        if (!claw_pid_blit8(pid, length, c, output, coverage, capacity, stride, &normal))
            return 0;
        if (info)
            *info = {normal.consumed, normal.writes, 1, 1};
        return 1;
    }
    if ((state->formatByte & 255) != 1 || state->effectMode != 2)
        return 0;
    if (!table) {
        if (info)
            *info = {0, 0, 0, 0};
        return 1;
    }
    if (!scratch || !table->data || !table->words[2] || table->capacity < 65536)
        return 0;
    size_t end = length;
    if (word(pid + 4) & 128) {
        if (end < 800)
            return 0;
        end -= 768;
    }
    if (!valid(pid, end, w, h))
        return 0;
    //Isolated native validation prevents partial stores on unsafe source profiles.
    std::vector<uint8_t> frame(output, output + capacity), mask;
    if (coverage)
        mask.assign(coverage, coverage + capacity);
    uint8_t local[128];
    std::memcpy(local, scratch, 128);
    Engine e{pid,      end,    32, w,    h, *c, *state, *table, frame.data(), coverage ? mask.data() : nullptr,
             capacity, stride, 0,  local};
    try {
        e.blit();
    } catch (Invalid &) {
        return 0;
    }
    std::memcpy(output, frame.data(), capacity);
    if (coverage)
        std::memcpy(coverage, mask.data(), capacity);
    std::memcpy(scratch, local, 128);
    if (info)
        *info = {e.cursor, e.writes, 1, 1};
    return 1;
}
