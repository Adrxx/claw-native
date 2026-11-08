#include "PIDBlitter.h"
#include "ClawRuntime.hpp"
#include <algorithm>
#include <limits>

namespace {
uint32_t word(const uint8_t *p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}
struct Run {
    int32_t count;
    bool literal;
    size_t start;
};
struct Stream {
    const uint8_t *pid;
    size_t end, cursor = 32;
    bool next(Run &r) {
        if (cursor >= end)
            return false;
        const uint8_t token = pid[cursor++];
        r.literal = !(token & 128);
        r.count = r.literal ? token : token - 128;
        r.start = cursor;
        if (!r.count || (r.literal && size_t(r.count) > end - cursor))
            return false;
        if (r.literal)
            cursor += r.count;
        return true;
    }
};
struct Writer {
    const uint8_t *pid;
    uint8_t *output;
    uint8_t *coverage;
    size_t capacity, writes = 0, extent = 0;
    bool copy(size_t source, int64_t destination, int32_t count, bool reverse) {
        if (count <= 0)
            return true;
        const int64_t last = destination + (reverse ? -int64_t(count - 1) : count - 1);
        if (destination < 0 || last < 0 || uint64_t(destination) >= capacity || uint64_t(last) >= capacity)
            return false;
        for (int32_t i = 0; i < count; ++i) {
            const size_t offset = size_t(destination + (reverse ? -int64_t(i) : i));
            if (output)
                output[offset] = pid[source + i];
            if (coverage)
                coverage[offset] = 1;
        }
        extent = std::max(extent, size_t(std::max(destination, last)) + 1);
        writes += count;
        return true;
    }
};
bool validStream(const uint8_t *pid, size_t end, int32_t width, int32_t height, size_t start = 32) {
    Stream stream{pid, end, start};
    Run run{};
    for (int32_t y = 0; y < height; ++y) {
        int32_t x = 0;
        while (x < width) {
            if (!stream.next(run) || run.count > width - x)
                return false;
            x += run.count;
        }
    }
    return true;
}
// The loops below retain the original run boundaries. Decoding an ordinary
// rectangle then reflecting it would erase branch-specific overdraw/omissions.
bool blit(const uint8_t *pid, size_t end, int32_t width, const ClawPIDBlitCommand &c, size_t stride, Writer &writer,
          size_t &consumed, size_t start = 32) {
    Stream stream{pid, end, start};
    Run run{};
    int32_t row = 0;
    int32_t x = c.flipX && c.flipY ? int32_t(c.originalSourceRectAddress) : 0;
    while (row < c.source.top) {
        if (!stream.next(run))
            return false;
        x = int32_t(uint32_t(x) + uint32_t(run.count));
        if (x >= width) {
            ++row;
            x = 0;
        }
    }
    int64_t base = int64_t(c.flipY ? c.destination.bottom : c.destination.top) * int64_t(stride) + c.destination.left;
    const int64_t advance = c.flipY ? -int64_t(stride) : int64_t(stride);
    x = c.flipX ? width : 0;
    if (!c.flipX) {
        if (c.source.left == 0) {
            while (row <= c.source.bottom) {
                if (!stream.next(run))
                    return false;
                if (run.literal) {
                    int32_t count = run.count;
                    if (c.source.right != width - 1)
                        count = int32_t(std::max<int64_t>(0, std::min<int64_t>(count, int64_t(c.source.right) - x)));
                    if (!writer.copy(run.start, base + x, count, false))
                        return false;
                }
                x += run.count;
                if (x >= width) {
                    ++row;
                    base += advance;
                    x = 0;
                }
            }
        } else {
            // Original nonzero-left path ignores source.right and excludes bottom.
            while (row < c.source.bottom) {
                if (x < c.source.left) {
                    do {
                        if (!stream.next(run))
                            return false;
                        x += run.count;
                    } while (x < c.source.left);
                    if (x > c.source.left && run.literal) {
                        const int32_t count = x - c.source.left;
                        if (!writer.copy(stream.cursor - count, base, count, false))
                            return false;
                    }
                }
                if (x < width) {
                    if (!stream.next(run))
                        return false;
                    if (run.literal && !writer.copy(run.start, base + x - c.source.left, run.count, false))
                        return false;
                    x += run.count;
                } else {
                    ++row;
                    base += advance;
                    x = 0;
                }
            }
        }
    } else if (c.source.left != 0) {
        // Both mirrored paths ignore right when left is nonzero. The clip is
        // measured against the decreasing width counter, not ordinary source x.
        while (row <= c.source.bottom) {
            if (!stream.next(run))
                return false;
            if (run.literal) {
                const int32_t count = std::max(0, std::min(run.count, x - c.source.left));
                if (!writer.copy(run.start, base + x - c.source.left, count, true))
                    return false;
            }
            x -= run.count;
            if (x < 1) {
                ++row;
                base += advance;
                x = width;
            }
        }
    } else if (c.source.right == width - 1) {
        while (row <= c.source.bottom) {
            if (!stream.next(run))
                return false;
            if (run.literal && !writer.copy(run.start, base + x, run.count, true))
                return false;
            x -= run.count;
            if (x < 1) {
                ++row;
                base += advance;
                x = width;
            }
        }
    } else {
        // 0x4c0450 excludes bottom here; 0x4c0cc0 includes it.
        auto hasRow = [&] {
            return c.flipY ? row <= c.source.bottom : row < c.source.bottom;
        };
        while (hasRow()) {
            bool nextRow = false;
            if (c.source.right < x) {
                do {
                    if (!stream.next(run))
                        return false;
                    x -= run.count;
                } while (c.source.right < x);
                if (x >= 0) {
                    if (run.literal) {
                        const int32_t count = c.source.right - x;
                        if (!writer.copy(stream.cursor - count, base + c.source.right, count, true))
                            return false;
                    }
                } else
                    nextRow = true;
            }
            if (x < 1)
                nextRow = true;
            if (nextRow) {
                ++row;
                base += advance;
                x = width;
            } else {
                if (!stream.next(run))
                    return false;
                if (run.literal && !writer.copy(run.start, base + x, run.count, true))
                    return false;
                x -= run.count;
            }
        }
    }
    consumed = stream.cursor;
    return true;
}
} // namespace

uint32_t claw_pid_blit8(const uint8_t *pid, size_t length, const ClawPIDBlitCommand *command, uint8_t *output,
                        uint8_t *coverage, size_t capacity, size_t rowStride, ClawPIDBlitInfo *info) {
    if (!pid || !command || !output || length < 32 || !(word(pid + 4) & 32))
        return 0;
    const int32_t width = int32_t(word(pid + 8)), height = int32_t(word(pid + 12));
    if (width < 1 || height < 1 || width > 4096 || height > 4096 || !rowStride || rowStride > INT32_MAX ||
        capacity > INT32_MAX)
        return 0;
    const auto &s = command->source;
    // These four bounds are the actual dispatcher predicates. The original
    // does not validate bottom or rectangle ordering; unsafe touches reject below.
    if (s.left < 0 || s.right > width - 1 || s.top < 0 || s.top > height - 1)
        return 0;
    size_t end = length;
    if (word(pid + 4) & 128) {
        if (end < 800)
            return 0;
        end -= 768;
    }
    if (!validStream(pid, end, width, height))
        return 0;
    Writer dry{pid, nullptr, nullptr, capacity};
    size_t consumed = 0;
    if (!blit(pid, end, width, *command, rowStride, dry, consumed))
        return 0;
    Writer actual{pid, output, coverage, capacity};
    blit(pid, end, width, *command, rowStride, actual, consumed);
    if (info)
        *info = ClawPIDBlitInfo{consumed, actual.writes};
    return 1;
}

namespace {
uint32_t checkedAddress(claw::Run &run, uint32_t base, uint32_t count) {
    if (uint64_t(base) + count > uint64_t(UINT32_MAX) + 1)
        run.fail(CLAW_FAULT_MEMORY, base);
    return base;
}
bool overlaps(uint32_t a, size_t n, uint32_t b, size_t m) {
    return uint64_t(a) < uint64_t(b) + m && uint64_t(b) < uint64_t(a) + n;
}
ClawPIDBlitRect readRectangle(claw::Run &run, uint32_t address) {
    ClawPIDBlitRect rectangle;
    std::memcpy(&rectangle, run.span(checkedAddress(run, address, 0x10), 0x10), 0x10);
    return rectangle;
}
int owned(uint32_t function) {
    return function == 0x4c00b0 ? 3 : -1;
}
// 0x4c00b0: pitch is captured before the physical lock; all image and RECT
// state is read after it. Nonaliasing is required because the original reloads
// those fields during literal writes.
uint32_t rawBlit(claw::Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t destination = arguments[0];
    const uint32_t surface = arguments[1];
    const uint32_t source = arguments[2];
    checkedAddress(run, surface, 0x78);
    const int32_t pitch = run.gets(surface + 0x1c);
    const uint32_t pixels = run.call(0x4b9730, surface, {0});
    checkedAddress(run, receiver, 0x25);
    const int32_t width = run.gets(receiver + 0x04);
    const int32_t height = run.gets(receiver + 0x08);
    const uint32_t payload = run.get(receiver + 0x0c);
    const uint32_t length = run.get(receiver + 0x10);
    const uint8_t pixelBytes = run.get8(receiver + 0x24);
    ClawPIDBlitCommand command{};
    command.destination = readRectangle(run, destination);
    command.source = readRectangle(run, source);
    if (pixelBytes != 1 || width < 1 || height < 1 || width > 4096 || height > 4096 ||
        pitch <= 0 || !length || length > 0x02000000 || command.source.left < 0 ||
        command.source.left >= width || command.source.top < 0 || command.source.top >= height ||
        command.source.right > width - 1 || command.source.bottom >= height)
        run.fail(CLAW_FAULT_MEMORY, receiver);
    checkedAddress(run, payload, length);
    const uint32_t dd = run.get(surface + 0x08);
    checkedAddress(run, dd, 0x04);
    const uint32_t vtable = run.get(dd);
    checkedAddress(run, vtable, 0x84);
    {
        const uint8_t *input = run.span(payload, length);
        if (!validStream(input, length, width, height, 0))
            run.fail(CLAW_FAULT_MEMORY, payload);
        Writer dry{input, nullptr, nullptr, UINT32_MAX};
        size_t consumed = 0;
        if (!blit(input, length, width, command, size_t(pitch), dry, consumed, 0))
            run.fail(CLAW_FAULT_MEMORY, pixels);
        if (dry.extent) {
            checkedAddress(run, pixels, uint32_t(dry.extent));
            if (overlaps(pixels, dry.extent, payload, length) ||
                overlaps(pixels, dry.extent, receiver, 0x25) ||
                overlaps(pixels, dry.extent, destination, 0x10) ||
                overlaps(pixels, dry.extent, source, 0x10) ||
                overlaps(pixels, dry.extent, surface, 0x78) ||
                overlaps(pixels, dry.extent, dd, 0x04) ||
                overlaps(pixels, dry.extent, vtable, 0x84))
                run.fail(CLAW_FAULT_MEMORY, pixels);
            uint8_t *output = run.span(pixels, uint32_t(dry.extent));
            Writer actual{input, output, nullptr, dry.extent};
            if (!blit(input, length, width, command, size_t(pitch), actual, consumed, 0))
                run.fail(CLAW_FAULT_MEMORY, pixels);
        }
    }
    const uint32_t currentDD = run.get(surface + 0x08);
    checkedAddress(run, currentDD, 0x04);
    const uint32_t currentVtable = run.get(currentDD);
    checkedAddress(run, currentVtable, 0x84);
    const uint32_t unlock = run.get(currentVtable + 0x80);
    run.call(unlock, 0, {currentDD, 0});
    return 0;
}
uint32_t body(claw::Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    if (function == 0x4c00b0)
        return rawBlit(run, receiver, arguments);
    run.fail(CLAW_FAULT_ABI, function);
}
}
CLAW_MODULE_ENTRY(claw_pid_blitter_entry, owned, body)
