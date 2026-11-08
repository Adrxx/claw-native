// Original compressed PID blitter variants
//
// Eight owned functions: three plain compressed-run blitters (0x4c0450,
// 0x4c0920, 0x4c0cc0), four palette/blend blitters (0x4c1190, 0x4c25b0,
// 0x4c3800, 0x4c4c20) and the mirrored blend helper 0x4c5e80.
//
// Common object fields (self): +0x00 interlace flag, +0x04 width, +0x0c run
// stream, +0x14 blend mode, +0x18 blend operand, +0x1c palette object (its +0x08
// is the 256x256 remap table), +0x24 bytes per pixel (plain blitters only).
// Surface fields (surface): +0x08 DirectDraw surface, +0x1c pitch.
// Origin (first argument): +0x00 x, +0x04 y, +0x0c flipped y.
// Clip (third argument): +0x00 left, +0x04 rows to skip, +0x08 right, +0x0c last row.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4c0450:
        return 3;
    case 0x4c0920:
        return 3;
    case 0x4c0cc0:
        return 3;
    case 0x4c1190:
        return 3;
    case 0x4c25b0:
        return 3;
    case 0x4c3800:
        return 3;
    case 0x4c4c20:
        return 3;
    case 0x4c5e80:
        return 3;
    default:
        return -1;
    }
}

// Global scratch row that the blend variants copy the destination pixels into.
const uint32_t kScratch = 0x542bb0;

// Calls the surface's unlock method (vtable +0x80) with (surface object, 0).
void unlockSurface(Run &run, uint32_t surface) {
    uint32_t object = run.get(surface + 0x08);
    uint32_t method = run.get(run.get(object) + 0x80);
    run.call(method, 0, {object, 0});
}

// True when the absolute value of the row number is odd.
bool oddRow(uint32_t value) {
    uint32_t sign = s32(value) < 0 ? 0xffffffffu : 0u;
    uint32_t magnitude = (value ^ sign) - sign;
    return ((magnitude & 1u) ^ sign) != sign;
}

// Copies count bytes from source into the scratch row, dwords first.
void copyToScratch(Run &run, uint32_t source, uint32_t count) {
    uint32_t from = source;
    uint32_t to = kScratch;
    for (uint32_t words = count >> 2; words != 0; --words) {
        run.put(to, run.get(from));
        from += 4;
        to += 4;
    }
    for (uint32_t tail = count & 3; tail != 0; --tail) {
        run.put8(to, run.get8(from));
        from += 1;
        to += 1;
    }
}

// Blend mode dispatch is skipped when the interlace flag is clear or the mode
// is neither 2 nor 4.
bool plainMode(Run &run, uint32_t self) {
    if (run.get(self) == 0)
        return true;
    uint32_t mode = run.get(self + 0x14);
    return mode != 2 && mode != 4;
}

// Forward (left to right) blend of count pixels at dest from the run bytes at source.
void blendForward(Run &run, uint32_t self, uint32_t dest, uint32_t source, uint32_t count) {
    uint32_t table = run.get(run.get(self + 0x1c) + 0x08);
    switch (run.get(self + 0x14)) {
    case 2:
        copyToScratch(run, dest, count);
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t under = run.get8(kScratch + i);
            uint32_t over = run.get8(source + i);
            run.put8(dest + i, run.get8(table + under * 0x100 + over));
        }
        break;
    case 4:
        copyToScratch(run, dest, count);
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t under = run.get8(kScratch + i);
            run.put8(dest + i, run.get8(under * 0x100 + table + run.get(self + 0x18)));
        }
        break;
    case 8:
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t over = run.get8(source + i);
            run.put8(dest + i, run.get8(over * 0x100 + table + run.get(self + 0x18)));
        }
        break;
    case 0x16:
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            run.put8(dest + i, run.get8(self + 0x18));
        }
        break;
    case 0x32:
        copyToScratch(run, dest, count);
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t under = run.get8(run.get8(kScratch + i) + 0x100 + table);
            uint32_t over = run.get8(run.get8(source + i) + 0x100 + table);
            uint32_t scaled = uint32_t(s32((over - under) * run.get(self + 0x18)) / 0xff);
            run.put8(dest + i, run.get8(scaled + under + table));
        }
        break;
    default:
        break;
    }
}

// Mirrored (right to left) blend; dest is the rightmost pixel. 0x4c5e80.
void blendMirrored(Run &run, uint32_t self, uint32_t dest, uint32_t source, uint32_t count) {
    uint32_t table = run.get(run.get(self + 0x1c) + 0x08);
    switch (run.get(self + 0x14)) {
    case 2:
        copyToScratch(run, dest + 1 - count, count);
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t under = run.get8(kScratch + count - 1 - i);
            uint32_t over = run.get8(source + i);
            run.put8(dest - i, run.get8(over + table + under * 0x100));
        }
        break;
    case 4:
        copyToScratch(run, dest + 1 - count, count);
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t under = run.get8(kScratch + count - 1 - i);
            run.put8(dest - i, run.get8(under * 0x100 + table + run.get(self + 0x18)));
        }
        break;
    case 8:
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t over = run.get8(source + i);
            run.put8(dest - i, run.get8(over * 0x100 + table + run.get(self + 0x18)));
        }
        break;
    case 0x16:
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            run.put8(dest - i, run.get8(self + 0x18));
        }
        break;
    case 0x32:
        copyToScratch(run, dest - 1 - count, count);
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t under = run.get8(run.get8(kScratch + count + 1 - i) + 0x100 + table);
            uint32_t over = run.get8(run.get8(source + i) + 0x100 + table);
            uint32_t scaled = uint32_t(s32((over - under) * run.get(self + 0x18)) / 0xff);
            run.put8(dest - i, run.get8(scaled + under + table));
        }
        break;
    default:
        break;
    }
}

// Forward blend that writes the result to this row and the row at +pitch.
void interlaceForward(Run &run, uint32_t self, uint32_t dest, uint32_t source, uint32_t count,
                      uint32_t pitch) {
    uint32_t table = run.get(run.get(self + 0x1c) + 0x08);
    uint32_t mode = run.get(self + 0x14);
    if (mode == 2) {
        copyToScratch(run, dest, count);
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t under = run.get8(kScratch + i);
            uint32_t over = run.get8(source + i);
            run.put8(dest + i, run.get8(over + table + under * 0x100));
            run.put8(dest + i + pitch, run.get8(over + table + under * 0x100));
        }
    } else if (mode == 4) {
        copyToScratch(run, dest, count);
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t under = run.get8(kScratch + i);
            run.put8(dest + i, run.get8(under * 0x100 + table + run.get(self + 0x18)));
            run.put8(dest + i + pitch, run.get8(under * 0x100 + table + run.get(self + 0x18)));
        }
    }
}

// Mirrored blend that writes the result to this row and the row at +pitch.
// In mode 4 the second row is indexed with the first run byte, never advanced.
void interlaceMirrored(Run &run, uint32_t self, uint32_t dest, uint32_t source, uint32_t count,
                       uint32_t pitch) {
    uint32_t table = run.get(run.get(self + 0x1c) + 0x08);
    uint32_t mode = run.get(self + 0x14);
    if (mode == 2) {
        copyToScratch(run, dest + 1 - count, count);
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t under = run.get8(kScratch + count - 1 - i);
            uint32_t over = run.get8(source + i);
            run.put8(dest - i, run.get8(under * 0x100 + table + over));
            run.put8(dest - i + pitch, run.get8(under * 0x100 + table + over));
        }
    } else if (mode == 4) {
        copyToScratch(run, dest + 1 - count, count);
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t under = run.get8(kScratch + count - 1 - i);
            run.put8(dest - i, run.get8(under * 0x100 + table + run.get(self + 0x18)));
            run.put8(dest - i + pitch, run.get8(under * 0x100 + table + run.get8(source)));
        }
    }
}

uint32_t clampPositive(uint32_t value) {
    return s32(value) < 0 ? 0u : value;
}

// Draws one forward run: plain blend, or the interlaced blend on odd rows.
void drawForward(Run &run, uint32_t self, uint32_t origin, uint32_t pitch, uint32_t row,
                 uint32_t dest, uint32_t source, uint32_t count) {
    if (plainMode(run, self)) {
        blendForward(run, self, dest, source, count);
    } else if (oddRow(row + run.get(origin + 0x04))) {
        interlaceForward(run, self, dest, source, count, pitch);
    }
}

// Draws one mirrored run: plain blend, or the interlaced blend on odd rows.
void drawMirrored(Run &run, uint32_t self, uint32_t origin, uint32_t pitch, uint32_t row,
                  uint32_t dest, uint32_t source, uint32_t count) {
    if (plainMode(run, self)) {
        blendMirrored(run, self, dest, source, count);
    } else if (oddRow(row + run.get(origin + 0x04))) {
        interlaceMirrored(run, self, dest, source, count, pitch);
    }
}

// Copies right to left with source ascending; loops while count != 0.
void runDownNz(Run &run, uint32_t dest, uint32_t source, uint32_t count, uint32_t unit) {
    if (unit == 1) {
        for (; count != 0; --count) {
            run.put8(dest, run.get8(source));
            dest -= 1;
            source += 1;
        }
    } else if (count != 0) {
        do {
            run.put16(dest, run.get16(source));
            source += 2;
            dest -= 2;
            count -= 2;
        } while (0 < s32(count));
    }
}

// Copies right to left with source ascending; loops while count > 0.
void runDownPos(Run &run, uint32_t dest, uint32_t source, uint32_t count, uint32_t unit) {
    if (unit == 1) {
        if (0 < s32(count)) {
            do {
                run.put8(dest, run.get8(source));
                dest -= 1;
                source += 1;
                count -= 1;
            } while (count != 0);
        }
    } else {
        for (; 0 < s32(count); count -= 2) {
            run.put16(dest, run.get16(source));
            source += 2;
            dest -= 2;
        }
    }
}

// 0x4c0450 (normal) and 0x4c0cc0 (flipped). Plain mirrored blit with
// bytes-per-pixel scaling. The flipped copy starts its column counter at the
// clip pointer, starts at the flipped row, walks up, tests the middle loop with
// <= and shrinks the span by the run length only (no pixel scaling).
uint32_t plainMirrored(Run &run, uint32_t self, const uint32_t *arguments, bool flipped) {
    uint32_t origin = arguments[0];
    uint32_t surface = arguments[1];
    uint32_t clip = arguments[2];
    uint32_t pitch = run.get(surface + 0x1c);
    uint32_t base = run.call(0x4b9730, surface, {0});
    uint32_t cursor = 0;
    uint32_t row = 0;
    uint32_t rows = run.get(clip + 0x04);
    uint32_t phase = flipped ? clip : 0;
    if (rows != 0 && 0 < s32(rows)) {
        do {
            uint32_t code = run.get8(cursor + run.get(self + 0x0c));
            if ((code & 0x80) == 0) {
                phase += code;
                cursor += 1 + uint32_t(run.get8(self + 0x24)) * code;
            } else {
                cursor += 1;
                phase += code - 0x80;
            }
            if (s32(run.get(self + 0x04)) <= s32(phase)) {
                row += 1;
                phase = 0;
            }
        } while (s32(row) < s32(rows));
    }
    uint32_t bpp = run.get8(self + 0x24);
    uint32_t startRow = flipped ? run.get(origin + 0x0c) : run.get(origin + 0x04);
    uint32_t line = startRow * pitch + base + run.get(origin) * bpp;
    uint32_t span = 0;
    if (run.get(clip) == 0) {
        span = run.get(self + 0x04);
        if (run.get(clip + 0x08) == span - 1) {
            if (s32(row) <= s32(run.get(clip + 0x0c))) {
                do {
                    uint32_t code = run.get8(cursor + run.get(self + 0x0c));
                    uint32_t step = 0;
                    if ((code & 0x80) == 0) {
                        uint32_t source = cursor + run.get(self + 0x0c) + 1;
                        uint32_t count = code * bpp;
                        uint32_t dest = span * bpp + line;
                        runDownNz(run, dest, source, count, bpp);
                        uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                        bpp = run.get8(self + 0x24);
                        step = 0 - length;
                        cursor += 1 + bpp * length;
                    } else {
                        step = 0x80 - code;
                        cursor += 1;
                    }
                    span += step;
                    if (s32(span) < 1) {
                        row += 1;
                        line = flipped ? line - pitch : line + pitch;
                        span = run.get(self + 0x04);
                    }
                } while (s32(row) <= s32(run.get(clip + 0x0c)));
            }
        } else {
            bool more = flipped ? s32(row) <= s32(run.get(clip + 0x0c)) : s32(row) < s32(run.get(clip + 0x0c));
            if (more) {
                do {
                    uint32_t clipRight = run.get(clip + 0x08);
                    bool newRow = false;
                    if (s32(clipRight) < s32(span)) {
                        bool literal = false;
                        do {
                            uint32_t code = run.get8(cursor + run.get(self + 0x0c));
                            literal = (code & 0x80) == 0;
                            uint32_t step = 0;
                            if (literal) {
                                step = 0 - code;
                                cursor += 1 + code * uint32_t(run.get8(self + 0x24));
                            } else {
                                step = 0x80 - code;
                                cursor += 1;
                            }
                            span += step;
                        } while (s32(clipRight) < s32(span));
                        if (-1 < s32(span)) {
                            if (literal) {
                                uint32_t unit = run.get8(self + 0x24);
                                uint32_t count = (clipRight - span) * unit;
                                uint32_t source = (run.get(self + 0x0c) + cursor) - count;
                                uint32_t dest = clipRight * unit + line;
                                runDownPos(run, dest, source, count, unit);
                            }
                        } else {
                            newRow = true;
                        }
                    }
                    if (!newRow && s32(span) < 1)
                        newRow = true;
                    if (newRow) {
                        row += 1;
                        line = flipped ? line - pitch : line + pitch;
                        span = run.get(self + 0x04);
                    } else {
                        uint32_t code = run.get8(cursor + run.get(self + 0x0c));
                        if ((code & 0x80) == 0) {
                            uint32_t unit = run.get8(self + 0x24);
                            uint32_t count = code * unit;
                            uint32_t source = cursor + run.get(self + 0x0c) + 1;
                            uint32_t dest = span * unit + line;
                            runDownNz(run, dest, source, count, unit);
                            uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                            uint32_t scaled = length * uint32_t(run.get8(self + 0x24));
                            span -= flipped ? length : scaled;
                            cursor += 1 + scaled;
                        } else {
                            span += 0x80 - code;
                            cursor += 1;
                        }
                    }
                } while (flipped ? s32(row) <= s32(run.get(clip + 0x0c)) : s32(row) < s32(run.get(clip + 0x0c)));
            }
        }
    } else {
        span = run.get(self + 0x04);
        if (s32(row) <= s32(run.get(clip + 0x0c))) {
            do {
                uint32_t pointer = run.get(self + 0x0c) + cursor;
                uint32_t code = run.get8(pointer);
                uint32_t step = 0;
                if ((code & 0x80) == 0) {
                    uint32_t clipLeft = run.get(clip);
                    if (s32(clipLeft) < s32(span - code)) {
                        uint32_t count = bpp * code;
                        uint32_t source = pointer + 1;
                        uint32_t dest = (span - clipLeft) * bpp + line;
                        runDownNz(run, dest, source, count, bpp);
                    } else {
                        uint32_t scaled = (span - clipLeft) * bpp;
                        uint32_t count = clampPositive(scaled);
                        uint32_t source = pointer + 1;
                        uint32_t dest = scaled + line;
                        runDownPos(run, dest, source, count, bpp);
                    }
                    uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                    bpp = run.get8(self + 0x24);
                    step = 0 - length;
                    cursor += 1 + bpp * length;
                } else {
                    step = 0x80 - code;
                    cursor += 1;
                }
                span += step;
                if (s32(span) < 1) {
                    row += 1;
                    line = flipped ? line - pitch : line + pitch;
                    span = run.get(self + 0x04);
                }
            } while (s32(row) <= s32(run.get(clip + 0x0c)));
        }
    }
    unlockSurface(run, surface);
    return 0;
}

// 0x4c0920. Plain forward blit, flipped (starts at the flipped row, walks up).
uint32_t plainForward(Run &run, uint32_t self, const uint32_t *arguments) {
    uint32_t origin = arguments[0];
    uint32_t surface = arguments[1];
    uint32_t clip = arguments[2];
    uint32_t phase = 0;
    uint32_t pitch = run.get(surface + 0x1c);
    uint32_t base = run.call(0x4b9730, surface, {0});
    uint32_t cursor = 0;
    uint32_t row = 0;
    uint32_t rows = run.get(clip + 0x04);
    if (rows != 0 && 0 < s32(rows)) {
        do {
            uint32_t code = run.get8(cursor + run.get(self + 0x0c));
            if ((code & 0x80) == 0) {
                phase += code;
                cursor += 1 + uint32_t(run.get8(self + 0x24)) * code;
            } else {
                cursor += 1;
                phase += code - 0x80;
            }
            if (s32(run.get(self + 0x04)) <= s32(phase)) {
                row += 1;
                phase = 0;
            }
        } while (s32(row) < s32(rows));
    }
    uint32_t bpp = run.get8(self + 0x24);
    uint32_t line = run.get(origin + 0x0c) * pitch + base + run.get(origin) * bpp;
    uint32_t col = 0;
    if (run.get(clip) == 0) {
        if (run.get(clip + 0x08) == run.get(self + 0x04) - 1) {
            if (s32(row) <= s32(run.get(clip + 0x0c))) {
                do {
                    uint32_t pointer = cursor + run.get(self + 0x0c);
                    uint32_t code = run.get8(pointer);
                    if ((code & 0x80) == 0) {
                        uint32_t dest = line + col * bpp;
                        for (uint32_t n = code * bpp; n != 0; --n) {
                            pointer += 1;
                            run.put8(dest, run.get8(pointer));
                            dest += 1;
                        }
                        uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                        bpp = run.get8(self + 0x24);
                        col += length;
                        cursor += 1 + bpp * length;
                    } else {
                        cursor += 1;
                        col += code - 0x80;
                    }
                    if (s32(run.get(self + 0x04)) <= s32(col)) {
                        row += 1;
                        line -= pitch;
                        col = 0;
                    }
                } while (s32(row) <= s32(run.get(clip + 0x0c)));
            }
        } else if (s32(row) <= s32(run.get(clip + 0x0c))) {
            do {
                uint32_t pointer = run.get(self + 0x0c) + cursor;
                uint32_t code = run.get8(pointer);
                if ((code & 0x80) == 0) {
                    if (s32(col + code) < s32(run.get(clip + 0x08))) {
                        uint32_t dest = line + col * bpp;
                        for (uint32_t n = bpp * code; n != 0; --n) {
                            pointer += 1;
                            run.put8(dest, run.get8(pointer));
                            dest += 1;
                        }
                    } else {
                        uint32_t count = (run.get(clip + 0x08) - col) * bpp;
                        count = clampPositive(count);
                        uint32_t dest = line + col * bpp;
                        if (0 < s32(count)) {
                            do {
                                pointer += 1;
                                run.put8(dest, run.get8(pointer));
                                dest += 1;
                                count -= 1;
                            } while (count != 0);
                        }
                    }
                    uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                    bpp = run.get8(self + 0x24);
                    col += length;
                    cursor += 1 + bpp * length;
                } else {
                    cursor += 1;
                    col += code - 0x80;
                }
                if (s32(run.get(self + 0x04)) <= s32(col)) {
                    row += 1;
                    line -= pitch;
                    col = 0;
                }
            } while (s32(row) <= s32(run.get(clip + 0x0c)));
        }
    } else if (s32(row) < s32(run.get(clip + 0x0c))) {
        do {
            uint32_t clipLeft = run.get(clip);
            if (s32(col) < s32(clipLeft)) {
                bool literal = false;
                do {
                    uint32_t code = run.get8(cursor + run.get(self + 0x0c));
                    literal = (code & 0x80) == 0;
                    if (literal) {
                        col += code;
                        cursor += 1 + code * uint32_t(run.get8(self + 0x24));
                    } else {
                        cursor += 1;
                        col += code - 0x80;
                    }
                } while (s32(col) < s32(clipLeft));
                if (s32(clipLeft) < s32(col) && literal) {
                    uint32_t count = (col - clipLeft) * uint32_t(run.get8(self + 0x24));
                    uint32_t source = (cursor - count) + run.get(self + 0x0c);
                    uint32_t dest = line;
                    if (0 < s32(count)) {
                        do {
                            run.put8(dest, run.get8(source));
                            source += 1;
                            count -= 1;
                            dest += 1;
                        } while (count != 0);
                    }
                }
            }
            if (s32(col) < s32(run.get(self + 0x04))) {
                uint32_t pointer = cursor + run.get(self + 0x0c);
                uint32_t code = run.get8(pointer);
                if ((code & 0x80) == 0) {
                    uint32_t dest = line + (col - run.get(clip)) * uint32_t(run.get8(self + 0x24));
                    for (uint32_t n = code * uint32_t(run.get8(self + 0x24)); n != 0; --n) {
                        pointer += 1;
                        run.put8(dest, run.get8(pointer));
                        dest += 1;
                    }
                    uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                    col += length;
                    cursor += 1 + length * uint32_t(run.get8(self + 0x24));
                } else {
                    cursor += 1;
                    col += code - 0x80;
                }
            } else {
                row += 1;
                line -= pitch;
                col = 0;
            }
        } while (s32(row) < s32(run.get(clip + 0x0c)));
    }
    unlockSurface(run, surface);
    return 0;
}

// 0x4c1190 (normal) and 0x4c3800 (flipped). Forward blend blit through the
// palette object. The flipped copy starts at the flipped row and walks up.
uint32_t blitForward(Run &run, uint32_t self, const uint32_t *arguments, bool flipped) {
    uint32_t origin = arguments[0];
    uint32_t surface = arguments[1];
    uint32_t clip = arguments[2];
    if (run.get(self + 0x1c) == 0)
        return 0;
    uint32_t pitch = run.get(surface + 0x1c);
    uint32_t base = run.call(0x4b9730, surface, {0});
    uint32_t phase = 0;
    uint32_t cursor = 0;
    uint32_t row = 0;
    uint32_t rows = run.get(clip + 0x04);
    if (rows != 0 && 0 < s32(rows)) {
        do {
            uint32_t code = run.get8(cursor + run.get(self + 0x0c));
            if ((code & 0x80) == 0) {
                phase += code;
                cursor += 1 + code;
            } else {
                cursor += 1;
                phase += code - 0x80;
            }
            if (s32(run.get(self + 0x04)) <= s32(phase)) {
                row += 1;
                phase = 0;
            }
        } while (s32(row) < s32(rows));
    }
    uint32_t startRow = flipped ? run.get(origin + 0x0c) : run.get(origin + 0x04);
    uint32_t line = base + pitch * startRow + run.get(origin);
    uint32_t col = 0;
    if (run.get(clip) == 0) {
        if (run.get(clip + 0x08) == run.get(self + 0x04) - 1) {
            if (s32(row) <= s32(run.get(clip + 0x0c))) {
                do {
                    uint32_t pointer = cursor + run.get(self + 0x0c);
                    uint32_t code = run.get8(pointer);
                    if ((code & 0x80) == 0) {
                        drawForward(run, self, origin, pitch, row, col + line, pointer + 1, code);
                        uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                        col += length;
                        cursor += 1 + length;
                    } else {
                        cursor += 1;
                        col += code - 0x80;
                    }
                    if (s32(run.get(self + 0x04)) <= s32(col)) {
                        row += 1;
                        line = flipped ? line - pitch : line + pitch;
                        col = 0;
                    }
                } while (s32(row) <= s32(run.get(clip + 0x0c)));
            }
        } else if (s32(row) <= s32(run.get(clip + 0x0c))) {
            do {
                uint32_t pointer = cursor + run.get(self + 0x0c);
                uint32_t code = run.get8(pointer);
                if ((code & 0x80) == 0) {
                    uint32_t clipRight = run.get(clip + 0x08);
                    if (s32(col + code) < s32(clipRight)) {
                        drawForward(run, self, origin, pitch, row, col + line, pointer + 1, code);
                    } else {
                        uint32_t count = clampPositive(clipRight - col);
                        drawForward(run, self, origin, pitch, row, col + line, pointer + 1, count);
                    }
                    uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                    col += length;
                    cursor += 1 + length;
                } else {
                    cursor += 1;
                    col += code - 0x80;
                }
                if (s32(run.get(self + 0x04)) <= s32(col)) {
                    row += 1;
                    line = flipped ? line - pitch : line + pitch;
                    col = 0;
                }
            } while (s32(row) <= s32(run.get(clip + 0x0c)));
        }
    } else if (s32(row) < s32(run.get(clip + 0x0c))) {
        do {
            uint32_t clipLeft = run.get(clip);
            if (s32(col) < s32(clipLeft)) {
                bool literal = false;
                do {
                    uint32_t code = run.get8(cursor + run.get(self + 0x0c));
                    literal = (code & 0x80) == 0;
                    if (literal) {
                        col += code;
                        cursor += 1 + code;
                    } else {
                        cursor += 1;
                        col += code - 0x80;
                    }
                } while (s32(col) < s32(clipLeft));
                if (s32(clipLeft) < s32(col) && literal) {
                    uint32_t source = (cursor - col) + clipLeft + run.get(self + 0x0c);
                    drawForward(run, self, origin, pitch, row, line, source, col - clipLeft);
                }
            }
            if (s32(col) < s32(run.get(self + 0x04))) {
                uint32_t pointer = cursor + run.get(self + 0x0c);
                uint32_t code = run.get8(pointer);
                if ((code & 0x80) == 0) {
                    uint32_t dest = (col - run.get(clip)) + line;
                    drawForward(run, self, origin, pitch, row, dest, pointer + 1, code);
                    uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                    col += length;
                    cursor += 1 + length;
                } else {
                    cursor += 1;
                    col += code - 0x80;
                }
            } else {
                row += 1;
                line = flipped ? line - pitch : line + pitch;
                col = 0;
            }
        } while (s32(row) < s32(run.get(clip + 0x0c)));
    }
    unlockSurface(run, surface);
    return 0;
}

// 0x4c25b0 (normal) and 0x4c4c20 (flipped). Mirrored blend blit. The flipped
// copy starts at the flipped row, walks up and tests the middle loop with <=.
uint32_t blitMirrored(Run &run, uint32_t self, const uint32_t *arguments, bool flipped) {
    uint32_t origin = arguments[0];
    uint32_t surface = arguments[1];
    uint32_t clip = arguments[2];
    if (run.get(self + 0x1c) == 0)
        return 0;
    uint32_t pitch = run.get(surface + 0x1c);
    uint32_t base = run.call(0x4b9730, surface, {0});
    uint32_t phase = 0;
    uint32_t cursor = 0;
    uint32_t row = 0;
    uint32_t rows = run.get(clip + 0x04);
    if (rows != 0 && 0 < s32(rows)) {
        do {
            uint32_t code = run.get8(cursor + run.get(self + 0x0c));
            if ((code & 0x80) == 0) {
                phase += code;
                cursor += 1 + code;
            } else {
                cursor += 1;
                phase += code - 0x80;
            }
            if (s32(run.get(self + 0x04)) <= s32(phase)) {
                row += 1;
                phase = 0;
            }
        } while (s32(row) < s32(rows));
    }
    uint32_t startRow = flipped ? run.get(origin + 0x0c) : run.get(origin + 0x04);
    uint32_t line = base + pitch * startRow + run.get(origin);
    uint32_t span = 0;
    if (run.get(clip) == 0) {
        span = run.get(self + 0x04);
        if (run.get(clip + 0x08) == span - 1) {
            if (s32(row) <= s32(run.get(clip + 0x0c))) {
                do {
                    uint32_t pointer = cursor + run.get(self + 0x0c);
                    uint32_t code = run.get8(pointer);
                    uint32_t step = 0;
                    if ((code & 0x80) == 0) {
                        drawMirrored(run, self, origin, pitch, row, span + line, pointer + 1, code);
                        uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                        step = 0 - length;
                        cursor += 1 + length;
                    } else {
                        step = 0x80 - code;
                        cursor += 1;
                    }
                    span += step;
                    if (s32(span) < 1) {
                        span = run.get(self + 0x04);
                        row += 1;
                        line = flipped ? line - pitch : line + pitch;
                    }
                } while (s32(row) <= s32(run.get(clip + 0x0c)));
            }
        } else {
            bool more = flipped ? s32(row) <= s32(run.get(clip + 0x0c)) : s32(row) < s32(run.get(clip + 0x0c));
            if (more) {
                do {
                    uint32_t clipRight = run.get(clip + 0x08);
                    if (s32(clipRight) < s32(span)) {
                        bool literal = false;
                        do {
                            uint32_t code = run.get8(cursor + run.get(self + 0x0c));
                            literal = (code & 0x80) == 0;
                            uint32_t step = 0;
                            if (literal) {
                                step = 0 - code;
                                cursor += 1 + code;
                            } else {
                                step = 0x80 - code;
                                cursor += 1;
                            }
                            span += step;
                        } while (s32(clipRight) < s32(span));
                        if (-1 < s32(span) && literal) {
                            uint32_t count = clipRight - span;
                            uint32_t source = ((span + cursor) - clipRight) + run.get(self + 0x0c);
                            drawMirrored(run, self, origin, pitch, row, line + clipRight, source, count);
                        }
                    }
                    if (s32(span) < 1) {
                        row += 1;
                        line = flipped ? line - pitch : line + pitch;
                        span = run.get(self + 0x04);
                    } else {
                        uint32_t code = run.get8(cursor + run.get(self + 0x0c));
                        uint32_t pointer = cursor + run.get(self + 0x0c);
                        if ((code & 0x80) == 0) {
                            drawMirrored(run, self, origin, pitch, row, span + line, pointer + 1, code);
                            uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                            span -= length;
                            cursor += 1 + length;
                        } else {
                            span += 0x80 - code;
                            cursor += 1;
                        }
                    }
                } while (flipped ? s32(row) <= s32(run.get(clip + 0x0c)) : s32(row) < s32(run.get(clip + 0x0c)));
            }
        }
    } else {
        span = run.get(self + 0x04);
        if (s32(row) <= s32(run.get(clip + 0x0c))) {
            do {
                uint32_t pointer = cursor + run.get(self + 0x0c);
                uint32_t code = run.get8(pointer);
                uint32_t step = 0;
                if ((code & 0x80) == 0) {
                    uint32_t clipLeft = run.get(clip);
                    if (s32(clipLeft) < s32(span - code)) {
                        drawMirrored(run, self, origin, pitch, row, (span + line) - clipLeft, pointer + 1, code);
                    } else {
                        uint32_t count = clampPositive(span - clipLeft);
                        drawMirrored(run, self, origin, pitch, row, (span + line) - clipLeft, pointer + 1, count);
                    }
                    uint32_t length = run.get8(cursor + run.get(self + 0x0c));
                    step = 0 - length;
                    cursor += 1 + length;
                } else {
                    step = 0x80 - code;
                    cursor += 1;
                }
                span += step;
                if (s32(span) < 1) {
                    span = run.get(self + 0x04);
                    row += 1;
                    line = flipped ? line - pitch : line + pitch;
                }
            } while (s32(row) <= s32(run.get(clip + 0x0c)));
        }
    }
    unlockSurface(run, surface);
    return 0;
}

// 0x4c0450.
uint32_t function_4c0450(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return plainMirrored(run, receiver, arguments, false);
}

// 0x4c0920.
uint32_t function_4c0920(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return plainForward(run, receiver, arguments);
}

// 0x4c0cc0.
uint32_t function_4c0cc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return plainMirrored(run, receiver, arguments, true);
}

// 0x4c1190.
uint32_t function_4c1190(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return blitForward(run, receiver, arguments, false);
}

// 0x4c25b0.
uint32_t function_4c25b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return blitMirrored(run, receiver, arguments, false);
}

// 0x4c3800.
uint32_t function_4c3800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return blitForward(run, receiver, arguments, true);
}

// 0x4c4c20.
uint32_t function_4c4c20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return blitMirrored(run, receiver, arguments, true);
}

// 0x4c5e80. Mirrored blend of count pixels; arguments are dest, source, count.
uint32_t function_4c5e80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    blendMirrored(run, receiver, arguments[0], arguments[1], arguments[2]);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4c0450:
        return function_4c0450(run, receiver, arguments);
    case 0x4c0920:
        return function_4c0920(run, receiver, arguments);
    case 0x4c0cc0:
        return function_4c0cc0(run, receiver, arguments);
    case 0x4c1190:
        return function_4c1190(run, receiver, arguments);
    case 0x4c25b0:
        return function_4c25b0(run, receiver, arguments);
    case 0x4c3800:
        return function_4c3800(run, receiver, arguments);
    case 0x4c4c20:
        return function_4c4c20(run, receiver, arguments);
    case 0x4c5e80:
        return function_4c5e80(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_pid_blitter_variants_entry, owned, body)
