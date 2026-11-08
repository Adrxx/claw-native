#include "ClawRuntime.hpp"
#include <algorithm>
#include <array>

namespace {
using claw::Run;
using claw::s32;
uint32_t body(Run &run, uint32_t function, uint32_t self, const uint32_t *a);
int owned(uint32_t function) {
    switch (function) {
    case 0x4bc110:
        return 0;
    case 0x4dcc40:
        return 2;
    case 0x4dccb0:
        return 0;
    case 0x4dcd10:
        return 6;
    case 0x4dcdf0:
        return 7;
    case 0x4dce90:
        return 0;
    case 0x4dceb0:
        return 2;
    case 0x4dcf00:
        return 0;
    case 0x4dcf10:
        return 2;
    case 0x4dd020:
        return 1;
    case 0x4dd030:
        return 0;
    case 0x4dd0c0:
        return 0;
    case 0x4dd0d0:
        return 1;
    case 0x4dd0e0:
        return 0;
    case 0x4dd180:
        return 0;
    case 0x4dd1c0:
        return 0;
    case 0x4dd240:
        return 0;
    case 0x4dd270:
        return 1;
    case 0x4dd2c0:
        return 1;
    case 0x4dd420:
        return 0;
    case 0x4dd450:
        return 1;
    case 0x4dd480:
        return 0;
    case 0x4dd490:
        return 1;
    case 0x4dd520:
        return 1;
    case 0x4dd800:
        return 3;
    case 0x4dda50:
        return 0;
    case 0x4ddac0:
        return 0;
    case 0x4ddb40:
        return 0;
    case 0x4ddbc0:
        return 0;
    case 0x4ddc30:
        return 0;
    case 0x4ddce0:
        return 0;
    case 0x4dde80:
        return 0;
    case 0x4ddf70:
        return 0;
    case 0x4de0e0:
        return 4;
    case 0x4de450:
        return 0;
    case 0x4de4d0:
        return 2;
    case 0x4de790:
        return 1;
    case 0x4deb50:
        return 1;
    case 0x4dec60:
        return 1;
    case 0x4dece0:
        return 1;
    case 0x4ded00:
        return 2;
    case 0x4ded20:
        return 1;
    case 0x4ded40:
        return 1;
    case 0x4def70:
        return 0;
    case 0x4df040:
        return 0;
    case 0x4df0e0:
        return 5;
    case 0x4df180:
        return 0;
    case 0x4df200:
        return 1;
    case 0x4df260:
        return 1;
    case 0x4df270:
        return 1;
    case 0x4df2b0:
        return 1;
    case 0x4df460:
        return 1;
    case 0x4df480:
        return 0;
    case 0x4df490:
        return 1;
    case 0x4df620:
        return 1;
    case 0x4df630:
        return 0;
    case 0x4e5b50:
        return 2;
    case 0x4ed050:
        return 0;
    default:
        return -1;
    }
}

// Direct native calls retain the original entry-relative automatic addresses.
struct Frame {
    Run &run;
    uint32_t saved;
    Frame(Run &run, int32_t offset) : run(run), saved(run.frame) {
        run.frame = run.automatic(offset);
    }
    ~Frame() {
        run.frame = saved;
    }
};
uint32_t native(Run &run, int32_t offset, uint32_t function, uint32_t self, std::initializer_list<uint32_t> args = {}) {
    std::array<uint32_t, 16> words{};
    uint32_t index = 0;
    for (uint32_t word : args)
        words[index++] = word;
    Frame frame(run, offset);
    return body(run, function, self, words.data());
}
uint32_t virtualCall(Run &run, int32_t offset, uint32_t self, uint32_t slot, std::initializer_list<uint32_t> args = {}) {
    uint32_t function = run.get(run.get(self) + slot);
    if (owned(function) >= 0)
        return native(run, offset, function, self, args);
    return run.call(function, self, args);
}
uint32_t half(uint32_t value) {
    return uint32_t(s32(value) / 2);
}

// Inline pointer-array growth shared by 0x4dd2c0 and 0x4df2b0.
void resizeAppend(Run &run, uint32_t array, uint32_t old, uint32_t value) {
    // Array +0x4 storage, +0x8 count, +0xc capacity, +0x10 growth.
    uint32_t count = old + 1;
    uint32_t storage = run.get(array + 0x4);
    if (!count) {
        if (storage) {
            run.call(0x4f6428, 0, {storage});
            run.put(array + 0x4, 0);
        }
        run.put(array + 0xc, 0);
        run.put(array + 0x8, 0);
    } else if (!storage) {
        uint32_t bytes = count * 4;
        uint32_t allocated = run.call(0x4f63ec, 0, {bytes});
        run.put(array + 0x4, allocated);
        for (uint32_t i = 0; i < (bytes >> 2); ++i)
            run.put(allocated + i * 4, 0);
        run.put(array + 0xc, count);
        run.put(array + 0x8, count);
    } else {
        uint32_t capacity = run.get(array + 0xc);
        if (s32(count) <= s32(capacity)) {
            if (s32(count) > s32(old)) {
                for (uint32_t i = 0; i < count - old; ++i)
                    run.put(storage + old * 4 + i * 4, 0);
            }
            run.put(array + 0x8, count);
        } else {
            uint32_t growth = run.get(array + 0x10);
            if (!growth) {
                growth = uint32_t(s32(old) / 8);
                if (s32(growth) < 4)
                    growth = 4;
                else if (s32(growth) > 0x400)
                    growth = 0x400;
            }
            uint32_t next = capacity + growth;
            if (s32(count) >= s32(next))
                next = count;
            uint32_t allocated = run.call(0x4f63ec, 0, {next * 4});
            uint32_t bytes = run.get(array + 0x8) * 4;
            uint32_t source = run.get(array + 0x4);
            for (uint32_t i = 0; i < (bytes >> 2); ++i)
                run.put(allocated + i * 4, run.get(source + i * 4));
            uint32_t previous = run.get(array + 0x8);
            for (uint32_t i = 0; i < count - previous; ++i)
                run.put(allocated + previous * 4 + i * 4, 0);
            run.call(0x4f6428, 0, {run.get(array + 0x4)});
            run.put(array + 0x4, allocated);
            run.put(array + 0x8, count);
            run.put(array + 0xc, next);
        }
    }
    run.put(run.get(array + 0x4) + old * 4, value);
}

void dimensions(Run &run, uint32_t self) {
    uint32_t count = run.get(self + 0x8);
    uint32_t width = 0;
    uint32_t height = 0;
    if (s32(count) > 0) {
        uint32_t images = run.get(self + 0x4);
        for (uint32_t i = 0; i < count; ++i) {
            uint32_t image = run.get(images + i * 4);
            uint32_t w = run.get(image + 0x18);
            if (s32(width) <= s32(w))
                width = w;
            uint32_t h = run.get(image + 0x14);
            if (s32(height) <= s32(h))
                height = h;
        }
    }
    run.put(self + 0x5c, width);
    run.put(self + 0x60, height);
}

void archiveRoom(Run &run, uint32_t archive, uint32_t bytes, bool reading) {
    uint32_t cursor = run.get(archive + 0x24);
    uint32_t end = run.get(archive + 0x28);
    if (cursor + bytes > end) {
        if (reading)
            run.call(0x4fddbd, archive, {cursor - end + bytes});
        else
            run.call(0x4fdd43, archive);
    }
}
uint32_t readWord(Run &run, uint32_t archive, uint32_t bytes) {
    archiveRoom(run, archive, bytes, true);
    uint32_t cursor = run.get(archive + 0x24);
    uint32_t value = bytes == 2 ? run.get16(cursor) : run.get(cursor);
    run.put(archive + 0x24, run.get(archive + 0x24) + bytes);
    return value;
}
void writeWord(Run &run, uint32_t archive, uint32_t bytes, uint32_t value) {
    archiveRoom(run, archive, bytes, false);
    uint32_t cursor = run.get(archive + 0x24);
    if (bytes == 2)
        run.put16(cursor, uint16_t(value));
    else
        run.put(cursor, value);
    run.put(archive + 0x24, run.get(archive + 0x24) + bytes);
}

uint32_t body(Run &run, uint32_t function, uint32_t self, const uint32_t *a) {
    switch (function) {
    // 0x4bc110: empty game callback.
    case 0x4bc110:
        return 0;
    // 0x4dd180: controller constructor.
    case 0x4dd180:
        run.put(self + 0x8, 0x513ea8);
        run.put(self + 0xc, 0);
        run.put(self + 0x18, 0);
        run.put(self + 0x14, 0);
        run.put(self + 0x10, 0);
        run.put(self, 0x513e88);
        run.put(self + 0x4, 0);
        run.put(self + 0x1c, 0);
        run.put(self + 0x24, 0);
        run.put(self + 0x20, 0);
        run.put(self + 0x34, 0x190);
        run.put(self + 0x28, 0xffffffff);
        return self;
    // 0x4dd1c0: controller destructor.
    case 0x4dd1c0:
        run.put(self, 0x513e88);
        if (run.get(self + 0x4))
            native(run, -0x18, 0x4dd240, self);
        run.put(self + 0x8, 0x513ea8);
        if (run.get(self + 0xc))
            run.call(0x4f6428, 0, {run.get(self + 0xc)});
        run.put(self + 0x8, 0x50becc);
        return 0;
    // 0x4dd240 and 0x4dd420: owned array reset.
    case 0x4dd240:
    case 0x4dd420:
        if (run.get(self + 0xc)) {
            run.call(0x4f6428, 0, {run.get(self + 0xc)});
            run.put(self + 0xc, 0);
        }
        run.put(self + 0x14, 0);
        run.put(self + 0x10, 0);
        if (function == 0x4dd240)
            run.put(self + 0x4, 0);
        return 0;
    // 0x4dd2c0: raw widget append.
    case 0x4dd2c0:
        if (!a[0])
            return 0;
        resizeAppend(run, self + 0x8, run.get(self + 0x10), a[0]);
        return 1;
    // 0x4dd450: bounds checked widget lookup.
    case 0x4dd450:
        if (s32(a[0]) >= 0 && s32(a[0]) <= s32(run.get(self + 0x10) - 1))
            return run.get(run.get(self + 0xc) + a[0] * 4);
        return 0;
    // 0x4dd480: selected index.
    case 0x4dd480:
        return run.get(self + 0x1c);
    // 0x4dd0c0: current interface node.
    case 0x4dd0c0:
        return run.get(self + 0xf8);
    // 0x4df480: child count.
    case 0x4df480:
        return run.get(self + 0x20);
    // 0x4df630: controller widget count / node parent.
    case 0x4df630:
        return run.get(self + 0x10);
    // 0x4ed050: widget state.
    case 0x4ed050:
        return run.get(self + 0x44);
    // 0x4df260: child lookup.
    case 0x4df260:
        return run.get(run.get(self + 0x1c) + a[0] * 4);
    // 0x4df620: child parent setter.
    case 0x4df620:
        run.put(self + 0x10, a[0]);
        return 0;
    // 0x4df460: copy description CString.
    case 0x4df460:
        run.call(0x4f6449, a[0], {self + 0x14});
        return a[0];
    // 0x4e5b50: affirmative callback, stdcall two words.
    case 0x4e5b50:
        return 1;
    // 0x4dece0: widget extent output.
    case 0x4dece0:
        run.put(a[0], run.get(self + 0x5c));
        run.put(a[0] + 0x4, run.get(self + 0x60));
        return a[0];
    // 0x4ded20: widget position output.
    case 0x4ded20:
        run.put(a[0], run.get(self + 0x54));
        run.put(a[0] + 0x4, run.get(self + 0x58));
        return a[0];
    // 0x4ded00: widget position setter.
    case 0x4ded00:
        run.put(self + 0x54, a[0]);
        run.put(self + 0x58, a[1]);
        return 0;
    // 0x4dec60: select image for the exact state flag precedence.
    case 0x4dec60: {
        uint32_t state = a[0];
        run.put(self + 0x44, state);
        uint32_t index = 0;
        if (state & 0x20) {
            if (!(state & 0x4))
                index = 0x14;
            else
                index = state & 0x10 ? 0x1c : 0x18;
        } else if (state & 0x1) {
            if (state & 0x4)
                index = state & 0x10 ? 0x10 : 0xc;
        } else if (state & 0x2) {
            index = state & 0x10 ? 0x8 : 0x4;
        } else {
            return 0;
        }
        run.put(self + 0x40, run.get(run.get(self + 0x4) + index));
        return 0;
    }
    // 0x4dde80: widget construction.
    case 0x4dde80:
        run.put(self, 0x513ec0);
        run.put(self + 0x4, 0);
        run.put(self + 0x10, 0);
        run.put(self + 0xc, 0);
        run.put(self + 0x8, 0);
        for (uint32_t offset = 0x18; offset <= 0x34; offset += 4)
            run.call(0x4f6439, self + offset);
        run.put(self + 0x54, 0);
        run.put(self + 0x58, 0);
        run.put(self + 0x3c, 0);
        run.put(self + 0x14, 0);
        run.put(self + 0x44, 1);
        run.put(self + 0x38, 0);
        run.put(self + 0x4c, 0);
        run.put(self + 0x50, 0);
        run.put(self + 0x64, 1);
        run.put(self + 0x68, 0x12c);
        return self;
    // 0x4ddf70: widget destruction.
    case 0x4ddf70:
        native(run, -0x20, 0x4de450, self);
        for (uint32_t offset = 0x34; offset >= 0x18; offset -= 4)
            run.call(0x4f6584, self + offset);
        run.put(self, 0x513ec0);
        if (run.get(self + 0x4))
            run.call(0x4f6428, 0, {run.get(self + 0x4)});
        run.put(self, 0x50becc);
        return 0;
    // 0x4def70: interface node construction.
    case 0x4def70: {
        run.call(0x4f6439, self + 0xc);
        run.call(0x4f6439, self + 0x14);
        run.put(self + 0x18, 0x513ee8);
        run.put(self + 0x1c, 0);
        run.put(self + 0x28, 0);
        run.put(self + 0x24, 0);
        run.put(self + 0x20, 0);
        native(run, -0x24, 0x4dde80, self + 0x3c);
        run.put(self, 0x513ed8);
        run.put(self + 0x2c, 0);
        uint32_t temporary = run.automatic(-0x14);
        uint32_t string = run.call(0x4f65f2, temporary, {0x5334f0});
        run.call(0x4f667d, self + 0x14, {string});
        run.call(0x4f6584, temporary);
        run.put(self + 0x38, 9);
        uint32_t buffer = run.call(0x4f63ec, 0, {0x24});
        run.put(self + 0x34, buffer);
        run.put(self + 0x4, 0);
        run.put(self + 0xac, 0);
        run.put(self + 0x10, 0);
        run.put(self + 0x8, 0);
        return self;
    }
    // 0x4df040: interface node destruction.
    case 0x4df040:
        run.put(self, 0x513ed8);
        if (run.get(self + 0x4))
            native(run, -0x20, 0x4df180, self);
        native(run, -0x20, 0x4ddf70, self + 0x3c);
        run.put(self + 0x18, 0x513ee8);
        if (run.get(self + 0x1c))
            run.call(0x4f6428, 0, {run.get(self + 0x1c)});
        run.put(self + 0x18, 0x50becc);
        run.call(0x4f6584, self + 0x14);
        run.call(0x4f6584, self + 0xc);
        return 0;
    // 0x4dcc40: derived interface controller constructor.
    case 0x4dcc40:
        native(run, -0x1c, 0x4dd180, self);
        native(run, -0x1c, 0x4def70, self + 0x48);
        run.put(self + 0x40, a[1]);
        run.put(self + 0x3c, a[0]);
        run.put(self + 0x1c, 0);
        run.put(self + 0xf8, 0);
        run.put(self + 0x44, 0);
        run.put(self, 0x513e68);
        run.put(self + 0xfc, 1);
        return self;
    // 0x4dccb0: derived interface controller destructor.
    case 0x4dccb0:
        run.put(self, 0x513e68);
        native(run, -0x18, 0x4dce90, self);
        native(run, -0x18, 0x4df040, self + 0x48);
        native(run, -0x18, 0x4dd1c0, self);
        return 0;
    // 0x4dce90: tail virtual node release.
    case 0x4dce90:
        if (run.get(self + 0x44)) {
            uint32_t method = run.get(run.get(self + 0x48) + 0x4);
            run.put(self + 0x44, 0);
            if (owned(method) >= 0)
                return native(run, 0, method, self + 0x48);
            return run.call(method, self + 0x48);
        }
        return 0;
    // 0x4df200: recursive identifier search.
    case 0x4df200:
        if (run.get(self + 0x50) == a[0])
            return self;
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x20)); ++i) {
            uint32_t child = run.get(run.get(self + 0x1c) + i * 4);
            uint32_t result = native(run, -0x10, 0x4df200, child, {a[0]});
            if (result)
                return result;
        }
        return 0;
    // 0x4dd020: controller identifier search.
    case 0x4dd020:
        return native(run, -0x8, 0x4df200, self + 0x48, {a[0]});
    // 0x4df270: recursive property propagation.
    case 0x4df270:
        run.put(self + 0xa4, a[0]);
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x20)); ++i)
            native(run, -0x10, 0x4df270, run.get(run.get(self + 0x1c) + i * 4), {a[0]});
        return 0;
    // 0x4dd0d0: propagate property from root.
    case 0x4dd0d0:
        native(run, -0x8, 0x4df270, self + 0x48, {a[0]});
        return 0;
    // 0x4df2b0: node factory, kind zero only; other kinds return untouched local.
    case 0x4df2b0: {
        if (a[0])
            return run.get(run.automatic(-0x10));
        uint32_t child = run.call(0x4f63ec, 0, {0xb0});
        if (child)
            child = native(run, -0x30, 0x4def70, child);
        run.put(run.automatic(-0x10), child);
        uint32_t old = run.get(self + 0x20);
        resizeAppend(run, self + 0x18, old, child);
        native(run, -0x34, 0x4df620, child, {self});
        return run.get(run.automatic(-0x10));
    }
    // 0x4de450: release provider-owned images and array storage.
    case 0x4de450:
        if (!run.get(self + 0x48))
            return 0;
        if (run.get(self + 0x3c)) {
            for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x8)); ++i) {
                uint32_t image = run.get(run.get(self + 0x4) + i * 4);
                if (image) {
                    run.call(0x4bc4f0, run.get(self + 0x48), {image});
                    for (uint32_t j = 0; s32(j) < s32(run.get(self + 0x8)); ++j)
                        run.put(run.get(self + 0x4) + j * 4, 0);
                }
            }
        }
        if (run.get(self + 0x38)) {
            run.call(0x4f6428, 0, {run.get(self + 0x38)});
            run.put(self + 0x38, 0);
        }
        if (run.get(self + 0x4)) {
            run.call(0x4f6428, 0, {run.get(self + 0x4)});
            run.put(self + 0x4, 0);
        }
        run.put(self + 0xc, 0);
        run.put(self + 0x8, 0);
        return 0;
    // 0x4de4d0: replace all references to a state image.
    case 0x4de4d0: {
        if (s32(a[1]) < 0 || s32(a[1]) >= 8)
            return 0;
        uint32_t previous = run.get(run.get(self + 0x4) + a[1] * 4);
        if (run.get(self + 0x3c))
            run.call(0x4bc4f0, run.get(self + 0x48), {previous});
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x8)); ++i) {
            if (run.get(run.get(self + 0x4) + i * 4) == previous)
                run.put(run.get(self + 0x4) + i * 4, a[0]);
        }
        dimensions(run, self);
        return 0;
    }
    // 0x4de0e0: widget images from callback or original provider loader.
    case 0x4de0e0: {
        if (!a[0])
            return 0;
        run.put(self + 0x48, a[0]);
        run.put(self + 0x4c, a[2]);
        run.put(self + 0x50, a[3]);
        run.put(self + 0x3c, a[1] ? 0 : 1);
        uint32_t temporary = run.automatic(-0x14);
        for (uint32_t offset = 0x18; offset <= 0x34; offset += 4) {
            run.call(0x4f6449, temporary, {self + offset});
            if (a[1]) {
                uint32_t image = run.call(a[1], 0, {run.get(temporary)});
                uint32_t old = run.get(self + 0x8);
                run.call(0x4dee30, self, {old + 1, 0xffffffff});
                run.put(run.get(self + 0x4) + old * 4, image);
            } else {
                run.call(0x4de560, self, {run.get(temporary)});
            }
        }
        uint32_t images = run.get(self + 0x4);
        if (!run.get(images) || !run.get(images + 0xc))
            return 0;
        uint32_t bitmap = run.call(0x4f63ec, 0, {run.get(self + 0x8) * 4});
        run.put(self + 0x38, bitmap);
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x8)); ++i)
            run.put(run.get(self + 0x38) + i * 4, 1);
        const uint32_t destinations[] = {0x4, 0x8, 0x10, 0x14, 0x18, 0x1c};
        const uint32_t sources[] = {0xc, 0x4, 0xc, 0, 0xc, 0x18};
        for (uint32_t i = 0; i < 6; ++i) {
            uint32_t storage = run.get(self + 0x4);
            if (!run.get(storage + destinations[i])) {
                run.put(storage + destinations[i], run.get(storage + sources[i]));
                run.put(run.get(self + 0x38) + destinations[i], 0);
            }
        }
        native(run, -0x18, 0x4dec60, self, {1});
        dimensions(run, self);
        return 1;
    }
    // 0x4df0e0: recursive node initialization and optional text creation.
    case 0x4df0e0: {
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x20)); ++i) {
            uint32_t child = run.get(run.get(self + 0x1c) + i * 4);
            if (!virtualCall(run, -0x28, child, 0, {a[0], a[1], a[2], a[3], a[4]}))
                return 0;
        }
        run.put(self + 0xa8, a[0]);
        if (!native(run, -0x24, 0x4de0e0, self + 0x3c, {a[0], a[1], 0, 0}))
            return 0;
        if (a[2]) {
            uint32_t temporary = run.automatic(-0x1c);
            native(run, -0x24, 0x4df460, self, {temporary});
            run.call(0x4de830, self + 0x3c, {run.get(temporary), a[3], a[4]});
        }
        run.put(self + 0x4, 1);
        return 1;
    }
    // 0x4df180: release a node's initialized subtree.
    case 0x4df180:
        native(run, -0x10, 0x4de450, self + 0x3c);
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x20)); ++i) {
            uint32_t child = run.get(run.get(self + 0x1c) + i * 4);
            virtualCall(run, -0x10, child, 0x4);
            child = run.get(run.get(self + 0x1c) + i * 4);
            if (child) {
                native(run, -0x10, 0x4df040, child);
                run.call(0x4f6428, 0, {child});
            }
        }
        if (run.get(self + 0x1c)) {
            run.call(0x4f6428, 0, {run.get(self + 0x1c)});
            run.put(self + 0x1c, 0);
        }
        run.put(self + 0x24, 0);
        run.put(self + 0x20, 0);
        if (run.get(self + 0x34)) {
            run.call(0x4f6428, 0, {run.get(self + 0x34)});
            run.put(self + 0x34, 0);
        }
        run.put(self + 0x4, 0);
        return 0;
    // 0x4deb50: serialize widget strings and identifier.
    case 0x4deb50: {
        uint32_t archive = a[0];
        bool reading = (run.get(archive + 0x14) & 1) != 0;
        for (uint32_t offset = 0x18; offset <= 0x34; offset += 4)
            run.call(reading ? 0x4fd877 : 0x4fd7fd, 0, {archive, self + offset});
        if (reading)
            run.put(self + 0x14, readWord(run, archive, 4));
        else
            writeWord(run, archive, 4, run.get(self + 0x14));
        return 0;
    }
    // 0x4df490: recursive node archive, signed 16-bit child count.
    case 0x4df490: {
        uint32_t archive = a[0];
        if (run.get(archive + 0x14) & 1) {
            run.put(self + 0x2c, readWord(run, archive, 4));
            run.call(0x4fd877, 0, {archive, self + 0x14});
            native(run, -0x18, 0x4deb50, self + 0x3c, {archive});
            uint32_t count = uint32_t(int32_t(int16_t(readWord(run, archive, 2))));
            uint32_t child = archive;
            for (uint32_t i = 0; s32(i) < s32(count); ++i) {
                uint32_t kind = readWord(run, archive, 4);
                if (!kind)
                    child = native(run, -0x18, 0x4df2b0, self, {0});
                virtualCall(run, -0x18, child, 0x8, {archive});
            }
        } else {
            writeWord(run, archive, 4, run.get(self + 0x2c));
            run.call(0x4fd7fd, 0, {archive, self + 0x14});
            native(run, -0x18, 0x4deb50, self + 0x3c, {archive});
            uint32_t count = run.get(self + 0x20);
            writeWord(run, archive, 2, count);
            count = uint32_t(int32_t(int16_t(count)));
            for (uint32_t i = 0; s32(i) < s32(count); ++i) {
                uint32_t child = run.get(run.get(self + 0x1c) + i * 4);
                uint32_t kind = run.call(0x4df250, child);
                writeWord(run, archive, 4, kind);
                child = run.get(run.get(self + 0x1c) + i * 4);
                virtualCall(run, -0x18, child, 0x8, {archive});
            }
        }
        return 0;
    }
    // 0x4dcd10: load from a CFile through an automatic CArchive.
    case 0x4dcd10: {
        uint32_t archive = run.automatic(-0x50);
        run.put(self + 0x38, a[0]);
        uint32_t previousStack = run.stackPointer;
        run.stackPointer = run.automatic(-0x6c);
        run.call(0x4fda33, archive, {a[1], 1, 0x1000, 0});
        run.stackPointer = previousStack;
        virtualCall(run, -0x60, self + 0x48, 0x8, {archive});
        uint32_t initialized = virtualCall(run, -0x70, self + 0x48, 0, {run.get(self + 0x38), a[2], a[3], a[4], a[5]});
        if (!initialized) {
            run.call(0x4fdb0f, archive);
            return 0;
        }
        native(run, -0x5c, 0x4dcf00, self);
        native(run, -0x60, 0x4dd490, self, {0});
        run.put(self + 0x44, 1);
        run.call(0x4fdb0f, archive);
        return 1;
    }
    // 0x4dcdf0: attach a memory file, then invoke the six-word loader.
    case 0x4dcdf0: {
        uint32_t memoryFile = run.automatic(-0x34);
        run.call(0x4ff5f9, memoryFile, {0x400});
        run.call(0x4ff645, memoryFile, {a[1], a[2], 0});
        uint32_t result = native(run, -0x54, 0x4dcd10, self, {a[0], memoryFile, a[3], a[4], a[5], a[6]});
        run.call(0x4ff670, memoryFile);
        run.call(0x4ff682, memoryFile);
        return result;
    }
    // 0x4ded40: centered current-image rectangle, preserving store order.
    case 0x4ded40: {
        uint32_t point = run.automatic(-0x8);
        native(run, -0x18, 0x4dece0, self, {point});
        uint32_t width = run.get(run.get(self + 0x40) + 0x18);
        uint32_t height = run.get(run.get(self + 0x40) + 0x14);
        uint32_t x = half(run.get(point) - width) + run.get(self + 0x54);
        uint32_t y = half(run.get(point + 0x4) - height) + run.get(self + 0x58);
        run.put(a[0] + 0xc, height + y);
        run.put(a[0] + 0x4, y);
        run.put(a[0] + 0x8, width + x);
        run.put(a[0], x);
        return a[0];
    }
    // 0x4de790: draw a centered current image using the original blitter.
    case 0x4de790: {
        if (!run.get(self + 0x64))
            return 0;
        uint32_t extent = run.automatic(-0x28);
        native(run, -0x3c, 0x4dece0, self, {extent});
        uint32_t image = run.get(self + 0x40);
        uint32_t width = run.get(image + 0x18);
        uint32_t height = run.get(image + 0x14);
        uint32_t x = half(run.get(extent) - width) + run.get(self + 0x54);
        uint32_t y = half(run.get(extent + 0x4) - height) + run.get(self + 0x58);
        uint32_t destination = run.automatic(-0x10);
        uint32_t source = run.automatic(-0x20);
        run.put(destination, x);
        run.put(destination + 0x4, y);
        run.put(destination + 0x8, width + x);
        run.put(destination + 0xc, height + y);
        run.put(source + 0x8, run.get(image + 0x18));
        run.put(source + 0xc, run.get(image + 0x14));
        run.put(source, 0);
        run.put(source + 0x4, 0);
        run.call(0x4b9ce0, a[0], {destination, image, source, 0x1008000, 0});
        return 0;
    }
    // 0x4dd490: select by index and notify after resetting widget states.
    case 0x4dd490: {
        if (s32(a[0]) < 0 || s32(a[0]) > s32(run.get(self + 0x10) - 1))
            return 0;
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x10)); ++i) {
            uint32_t widget = native(run, -0x18, 0x4dd450, self, {i});
            uint32_t flags = run.get(widget + 0x44);
            native(run, -0x18, 0x4dec60, widget, {flags & 0x20 ? 0x21u : 1u});
        }
        uint32_t widget = native(run, -0x18, 0x4dd450, self, {a[0]});
        uint32_t flags = run.get(widget + 0x44);
        native(run, -0x18, 0x4dec60, widget, {flags & 0x20 ? 0x35u : 0x15u});
        uint32_t now = run.icall(0x546a24);
        run.put(self + 0x30, now);
        run.put(self + 0x1c, a[0]);
        virtualCall(run, -0x14, self, 0x10);
        return 0;
    }
    // 0x4dd520: select by pointer, choosing index zero when absent.
    case 0x4dd520: {
        uint32_t selected = 0;
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x10)); ++i) {
            uint32_t widget = native(run, -0x18, 0x4dd450, self, {i});
            uint32_t flags = run.get(widget + 0x44);
            native(run, -0x18, 0x4dec60, widget, {flags & 0x20 ? 0x21u : 1u});
            if (run.get(run.get(self + 0xc) + i * 4) == a[0])
                selected = i;
        }
        uint32_t flags = run.get(a[0] + 0x44);
        native(run, -0x18, 0x4dec60, a[0], {flags & 0x20 ? 0x35u : 0x15u});
        uint32_t now = run.icall(0x546a24);
        run.put(self + 0x1c, selected);
        run.put(self + 0x30, now);
        virtualCall(run, -0x14, self, 0x10);
        return 0;
    }
    // 0x4ddce0: press timeout and selected-widget blink.
    case 0x4ddce0: {
        if (!run.get(self + 0x10))
            return 0;
        if (run.get(self + 0x24)) {
            uint32_t widget = native(run, -0x18, 0x4dd450, self, {run.get(self + 0x1c)});
            if (!widget)
                return 0;
            uint32_t duration = run.get(widget + 0x68);
            uint32_t now = run.icall(0x546a24);
            if (duration < now - run.get(self + 0x2c)) {
                run.put(self + 0x24, 0);
                uint32_t flags = run.get(widget + 0x44);
                if (!(flags & 0x20)) {
                    flags = run.get(widget + 0x44);
                    native(run, -0x18, 0x4dec60, widget, {flags & 0x10 ? 0x15u : 5u});
                }
                now = run.icall(0x546a24);
                run.put(self + 0x30, now);
                virtualCall(run, -0x14, self, 0x18);
            }
        }
        uint32_t now = run.icall(0x546a24);
        if (!run.get(self + 0x24) && run.get(self + 0x34) < now - run.get(self + 0x30)) {
            uint32_t widget = native(run, -0x18, 0x4dd450, self, {run.get(self + 0x1c)});
            if (widget) {
                uint32_t flags = run.get(widget + 0x44);
                native(run, -0x18, 0x4dec60, widget, {flags & 0x10 ? flags - 0x10 : flags | 0x10});
                run.put(self + 0x30, now);
            }
        }
        return 0;
    }
    // 0x4dda50 / 0x4ddac0 / 0x4ddb40: directional menu navigation.
    case 0x4dda50:
    case 0x4ddac0:
    case 0x4ddb40: {
        if (function != 0x4dda50)
            native(run, -0x10, 0x4ddce0, self);
        if (run.get(self + 0x24))
            return 0;
        bool forward = function == 0x4ddb40;
        uint32_t selected = run.get(self + 0x1c);
        uint32_t index = forward ? selected + 1 : selected - 1;
        if (!run.get(self + 0x20)) {
            if (forward) {
                if (s32(index) > s32(run.get(self + 0x10) - 1))
                    index = 0;
            } else if (s32(index) < 0) {
                index = run.get(self + 0x10) - 1;
            }
            native(run, -0x14, 0x4dd490, self, {index});
            return 0;
        }
        while (index != selected) {
            if (forward) {
                if (s32(index) > s32(run.get(self + 0x10) - 1))
                    index = 0;
            } else if (s32(index) < 0) {
                index = run.get(self + 0x10) - 1;
            }
            uint32_t widget = native(run, -0x14, 0x4dd450, self, {index});
            if (!(run.get(widget + 0x44) & 0x20)) {
                native(run, -0x14, 0x4dd490, self, {index});
                return 0;
            }
            index += forward ? 1 : uint32_t(-1);
        }
        return 0;
    }
    // 0x4ddbc0: start a timed press and notify.
    case 0x4ddbc0: {
        native(run, -0xc, 0x4ddce0, self);
        if (run.get(self + 0x24))
            return 0;
        uint32_t widget = native(run, -0x10, 0x4dd450, self, {run.get(self + 0x1c)});
        if (widget) {
            uint32_t flags = run.get(widget + 0x44);
            if (!(flags & 0x20)) {
                flags = run.get(widget + 0x44);
                native(run, -0x10, 0x4dec60, widget, {flags & 0x10 ? 0x12u : 2u});
            }
            run.put(self + 0x24, 1);
            run.put(self + 0x28, run.get(self + 0x1c));
            uint32_t now = run.icall(0x546a24);
            run.put(self + 0x2c, now);
        }
        virtualCall(run, -0xc, self, 0x14);
        return 0;
    }
    // 0x4ddc30: cursor press hit testing.
    case 0x4ddc30: {
        native(run, -0x30, 0x4ddce0, self);
        if (run.get(self + 0x24))
            return 0;
        uint32_t point = run.automatic(-0x18);
        uint32_t rectangle = run.automatic(-0x10);
        run.icall(0x546cd0, {point});
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x10)); ++i) {
            uint32_t widget = run.get(run.get(self + 0xc) + i * 4);
            if (!widget)
                continue;
            uint32_t x = run.get(point);
            uint32_t y = run.get(point + 0x4);
            native(run, -0x34, 0x4ded40, widget, {rectangle});
            if (!run.icall(0x546cd4, {rectangle, x, y}))
                continue;
            if (run.get(self + 0x20) && (run.get(widget + 0x44) & 0x20))
                return 0;
            native(run, -0x34, 0x4dd490, self, {i});
            native(run, -0x30, 0x4ddbc0, self);
            return 0;
        }
        return 0;
    }
    // 0x4dd270: update before drawing each nonnull widget.
    case 0x4dd270:
        native(run, -0x10, 0x4ddce0, self);
        if (a[0]) {
            for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x10)); ++i) {
                uint32_t widget = run.get(run.get(self + 0xc) + i * 4);
                if (widget)
                    native(run, -0x14, 0x4de790, widget, {a[0]});
            }
        }
        return 0;
    // 0x4dceb0: enable or disable an identified widget.
    case 0x4dceb0: {
        uint32_t node = native(run, -0x10, 0x4df200, self + 0x48, {a[0]});
        if (node && node + 0x3c) {
            uint32_t flags = run.get(node + 0x80);
            native(run, -0x10, 0x4dec60, node + 0x3c, {a[1] ? (flags | 0x20) - 0x20 : flags | 0x20});
        }
        return 0;
    }
    // 0x4dcf00: activate root menu.
    case 0x4dcf00:
        native(run, -0xc, 0x4dcf10, self, {self + 0x48, 1});
        return 0;
    // 0x4dcf10: populate current menu and center its widgets vertically.
    case 0x4dcf10: {
        if (!a[0])
            return 0;
        run.put(self + 0xf8, a[0]);
        native(run, -0x1c, 0x4dd420, self);
        for (uint32_t i = 0; s32(i) < s32(run.get(run.get(self + 0xf8) + 0x20)); ++i) {
            uint32_t node = run.get(self + 0xf8);
            uint32_t child = run.get(run.get(node + 0x1c) + i * 4);
            native(run, -0x20, 0x4dd2c0, self, {child + 0x3c});
        }
        if (!a[1])
            return 0;
        uint32_t count = run.get(self + 0x10);
        uint32_t total = 0;
        uint32_t point = run.automatic(-0x8);
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t widget = native(run, -0x24, 0x4dd450, self, {i});
            native(run, -0x20, 0x4dece0, widget, {point});
            total += run.get(point + 0x4);
        }
        uint32_t y = count * uint32_t(-10) - half(total) + half(run.get(self + 0x40)) + 10;
        for (uint32_t i = 0; s32(i) < s32(count); ++i) {
            uint32_t widget = native(run, -0x24, 0x4dd450, self, {i});
            native(run, -0x20, 0x4dece0, widget, {point});
            uint32_t x = half(run.get(self + 0x3c)) - half(run.get(point));
            widget = native(run, -0x28, 0x4dd450, self, {i});
            native(run, -0x24, 0x4ded00, widget, {x, y});
            y += 10 + run.get(point + 0x4);
        }
        return 0;
    }
    // 0x4dd030: return to parent menu and select its marked widget.
    case 0x4dd030: {
        uint32_t node = run.get(self + 0xf8);
        if (!node)
            return 0;
        node = run.get(self + 0xf8);
        if (!run.get(node + 0x10))
            return 0;
        node = run.get(self + 0xf8);
        native(run, -0x14, 0x4dcf10, self, {run.get(node + 0x10), 1});
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x10)); ++i) {
            uint32_t widget = native(run, -0x10, 0x4dd450, self, {i});
            if (run.get(widget + 0x44) & 0x4) {
                native(run, -0x10, 0x4dd490, self, {i});
                return 0;
            }
        }
        native(run, -0x10, 0x4dd490, self, {0});
        return 0;
    }
    // 0x4dd0e0: activate selected menu node and dispatch identifier callback.
    case 0x4dd0e0: {
        if (!run.get(self + 0xfc))
            return 0;
        uint32_t widget = native(run, -0x18, 0x4dd450, self, {run.get(self + 0x1c)});
        uint32_t identifier = run.get(widget + 0x14);
        if (!(run.get(widget + 0x44) & 0x20)) {
            uint32_t index = run.get(self + 0x1c);
            uint32_t node = run.get(self + 0xf8);
            uint32_t child = run.get(run.get(node + 0x1c) + index * 4);
            if (s32(run.get(child + 0x20)) > 0) {
                index = run.get(self + 0x1c);
                node = run.get(self + 0xf8);
                child = run.get(run.get(node + 0x1c) + index * 4);
                native(run, -0x1c, 0x4dcf10, self, {child, 1});
                native(run, -0x18, 0x4dd490, self, {0});
            }
        }
        uint32_t method = run.get(run.get(self) + 0x1c);
        uint32_t flags = run.get(widget + 0x44);
        if (owned(method) >= 0)
            native(run, -0x1c, method, self, {identifier, (~flags >> 5) & 1});
        else
            run.call(method, self, {identifier, (~flags >> 5) & 1});
        return 0;
    }
    // 0x4dd800: horizontal or vertical spacing of the current widget list.
    case 0x4dd800: {
        if (a[0] > 1)
            return 0;
        bool vertical = a[0] == 1;
        uint32_t count = run.get(self + 0x10);
        uint32_t lower = s32(a[1]) < s32(a[2]) ? a[1] : a[2];
        uint32_t upper = s32(a[1]) <= s32(a[2]) ? a[2] : a[1];
        if (count == 1) {
            uint32_t widget = native(run, -0x58, 0x4dd450, self, {0});
            uint32_t point = run.automatic(vertical ? -0x40 : -0x20);
            native(run, -0x58, 0x4ded20, widget, {point});
            uint32_t x = vertical ? run.get(point) : lower;
            uint32_t y = vertical ? lower : run.get(point + 0x4);
            native(run, -0x5c, 0x4ded00, widget, {x, y});
            return 0;
        }
        uint32_t total = 0;
        uint32_t extent = run.automatic(vertical ? -0x38 : -0x18);
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x10)); ++i) {
            uint32_t widget = native(run, -0x5c, 0x4dd450, self, {i});
            native(run, -0x58, 0x4dece0, widget, {extent});
            total += run.get(extent + (vertical ? 0x4 : 0));
        }
        count = run.get(self + 0x10);
        uint32_t position = lower;
        uint32_t point = run.automatic(vertical ? -0x30 : -0x10);
        extent = run.automatic(vertical ? -0x28 : -0x8);
        for (uint32_t i = 0; s32(i) < s32(run.get(self + 0x10)); ++i) {
            uint32_t widget = native(run, -0x58, 0x4dd450, self, {i});
            native(run, -0x58, 0x4ded20, widget, {point});
            uint32_t x = vertical ? run.get(point) : position;
            uint32_t y = vertical ? position : run.get(point + 0x4);
            native(run, -0x5c, 0x4ded00, widget, {x, y});
            native(run, -0x58, 0x4dece0, widget, {extent});
            uint32_t spacing = uint32_t(int64_t(s32(upper - total - lower)) / int64_t(s32(count - 1)));
            position += run.get(extent + (vertical ? 0x4 : 0)) + spacing;
        }
        return 0;
    }
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_interface_file_canonical_entry, owned, body)
