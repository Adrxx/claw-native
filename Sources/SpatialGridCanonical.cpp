#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;
int owned(uint32_t f) {
    switch (f) {
    case 0x4cb040: case 0x4d1620: case 0x4d4b50: case 0x4d4d10: case 0x4f4860: return 2;
    case 0x4cb0e0: case 0x4d4a90: case 0x4d51a0: case 0x4f4630: case 0x4f4680: return 1;
    case 0x4d4890: return 8;
    case 0x4f4490: case 0x4f48a0: return 6;
    case 0x4f46b0: return 5;
    case 0x4d1fd0: case 0x4d2000: case 0x4d2030: case 0x4d2050: case 0x4d4b00: case 0x4d4c40: case 0x4d50e0: case 0x4f45f0: case 0x4f49c0: return 0;
    default: return -1;
    }
}
uint32_t body(Run &run, uint32_t f, uint32_t r, const uint32_t *a);
uint32_t invoke(Run &run, uint32_t f, uint32_t r, std::initializer_list<uint32_t> a = {}) {
    return body(run, f, r, a.begin());
}
uint32_t sar(uint32_t v, uint32_t n) {
    return uint32_t(s32(v) >> (n & 31));
}
uint32_t half(uint32_t v) {
    return uint32_t(s32(v) / 2);
}
ClawX87State xstate() {
    ClawX87State s{};
    s.size = sizeof(s);
    s.version = CLAW_X87_VERSION;
    s.control = 0x023f;
    return s;
}
uint32_t exact(Run &run, ClawX87State &s, uint32_t f, uint32_t pop, uint32_t push) {
    s.popCount = pop;
    s.pushCount = push;
    s.returned = 0;
    s.eax = 0;
    s.edx = 0;
    return run.call_x87_exact(f, 0, s);
}
void f64(Run &run, ClawX87State &s, double v) {
    uint64_t bits;
    std::memcpy(&bits, &v, sizeof(bits));
    run.x87_step(CLAW_X87_F64, s, {uint32_t(bits), uint32_t(bits >> 32)});
}
void defaults(Run &run, uint32_t r) {
    run.put(r + 0xb4, 0xfa);
    run.put(r + 0xc0, 0xfa);
    run.put(r + 0xc4, 0x7d);
    run.put(r + 0xc8, 0x640);
    run.put(r + 0xcc, 0x4b0);
    run.put(r + 0xd0, 0xa00);
    run.put(r + 0xd4, 0x780);
    run.put(r + 0xd8, 0x300);
    run.put(r + 0xdc, 0x240);
}
void event29(Run &run, uint32_t entity) {
    uint32_t logic = run.get(entity + 0x6c);
    run.put(logic + 0x1c, 29);
    run.call(run.get(logic + 0x10), 0, {entity});
}
uint32_t body(Run &run, uint32_t f, uint32_t r, const uint32_t *a) {
    switch (f) {
    // 0x4cb040. World defaults and dimensions.
    case 0x4cb040:
        run.put(r + 0x10, 0);
        run.put(r + 0x14, 0);
        run.put(r + 0x18, a[0] - 1);
        run.put(r + 0x1c, a[1] - 1);
        run.put(r + 0xb8, 1000);
        run.put(r + 0xbc, 1000);
        run.put(r + 0xb0, 500);
        defaults(run, r);
        return 1;
    // 0x4cb0e0. Sequential rectangle copy, allowing aliasing.
    case 0x4cb0e0: {
        run.put(r + 0x10, run.get(a[0]));
        run.put(r + 0x14, run.get(a[0] + 0x4));
        run.put(r + 0x18, run.get(a[0] + 0x8));
        uint32_t bottom = run.get(a[0] + 0xc);
        run.put(r + 0xb0, 500);
        run.put(r + 0x1c, bottom);
        run.put(r + 0xb8, 1000);
        run.put(r + 0xbc, 1000);
        defaults(run, r);
        return 1;
    }
    // 0x4d1620. Plane manager construction and record parsing.
    case 0x4d1620: {
        uint32_t buffer = a[0];
        if (!buffer) return 0;
        uint32_t old = run.get(r + 0xb0);
        if (old) {
            invoke(run, 0x4d4b00, old);
            run.call(0x4f6428, 0, {old});
        }
        uint32_t rectangle = run.automatic(-0x10);
        uint32_t width = run.get(r + 0x30) - 1;
        uint32_t height = run.get(r + 0x34) - 1;
        run.put(rectangle + 0x8, width);
        run.put(rectangle, 0);
        run.put(rectangle + 0x4, 0);
        run.put(rectangle + 0xc, height);
        uint32_t world = run.get(r + 0xc);
        uint32_t container = run.get(world + 0x8);
        if (!container) return 0;
        uint32_t config = run.get(world + 0x24);
        if (!config) return 0;
        uint32_t pairs[6];
        for (uint32_t i = 0; i < 6; ++i) {
            pairs[i] = run.automatic(-0x18 - int32_t(i * 8));
            run.put(pairs[i], run.get(config + 0xb0 + i * 8));
            run.put(pairs[i] + 0x4, run.get(config + 0xb4 + i * 8));
        }
        uint32_t manager = run.call(0x4f63ec, 0, {0x70});
        if (manager) {
            run.put(manager, 0);
            run.put(manager + 0x4, 0);
            run.put(manager + 0x8, 0);
            run.put(manager + 0xc, 0);
        }
        run.put(r + 0xb0, manager);
        if (!invoke(run, 0x4d4890, manager, {container, rectangle, pairs[0], pairs[1], pairs[2], pairs[3], pairs[4], pairs[5]})) {
            old = run.get(r + 0xb0);
            if (old) {
                invoke(run, 0x4d4b00, old);
                run.call(0x4f6428, 0, {old});
            }
            run.put(r + 0xb0, 0);
            return 0;
        }
        for (uint32_t n = 0; s32(n) < s32(a[1]); ++n) {
            uint32_t savedStack = run.stackPointer;
            run.stackPointer = run.automatic(-0x58);
            uint32_t stride = run.call(0x4d17e0, r, {buffer});
            run.stackPointer = savedStack;
            if (!stride) return 0;
            buffer += stride;
        }
        return 1;
    }
    // 0x4d1fd0, 0x4d2000. Exact ordered coordinate conversions.
    case 0x4d1fd0: case 0x4d2000: {
        uint32_t manager = run.get(r + 0xb0);
        if (!manager) return 0;
        auto s = xstate();
        f64(run, s, double(run.getf(r + 0x14)));
        uint32_t y = exact(run, s, 0x4a30e0, 1, 0);
        f64(run, s, double(run.getf(r + 0x10)));
        uint32_t x = exact(run, s, 0x4a30e0, 1, 0);
        return invoke(run, f == 0x4d1fd0 ? 0x4d4b50 : 0x4d4d10, manager, {x, y});
    }
    // 0x4d2030.
    case 0x4d2030: {
        uint32_t manager = run.get(r + 0xb0);
        return manager ? invoke(run, 0x4d4c40, manager) : 0;
    }
    // 0x4d2050. Configuration refresh with manager reloads.
    case 0x4d2050: {
        uint32_t m = run.get(r + 0xb0);
        if (!m) return 0;
        uint32_t c = run.get(run.get(r + 0xc) + 0x24);
        if (!c) return 0;
        uint32_t x = run.get(c + 0xc8);
        uint32_t y = run.get(c + 0xcc);
        uint32_t by = run.get(c + 0xd4);
        uint32_t bx = run.get(c + 0xd0);
        uint32_t cx = run.get(c + 0xd8);
        uint32_t cy = run.get(c + 0xdc);
        run.put(m + 0x10, 0);
        run.put(m + 0x14, 0);
        run.put(m + 0x18, x - 1);
        run.put(m + 0x1c, y - 1);
        run.put(m + 0x40, half(x));
        run.put(m + 0x44, half(y));
        m = run.get(r + 0xb0);
        run.put(m + 0x38, bx - 1);
        run.put(m + 0x3c, by - 1);
        run.put(m + 0x30, 0);
        run.put(m + 0x48, half(bx));
        run.put(m + 0x34, 0);
        run.put(m + 0x4c, half(by));
        m = run.get(r + 0xb0);
        run.put(m + 0x20, 0);
        run.put(m + 0x24, 0);
        run.put(m + 0x28, cx - 1);
        run.put(m + 0x2c, cy - 1);
        run.put(m + 0x50, half(cx));
        run.put(m + 0x54, half(cy));
        m = run.get(r + 0xb0);
        run.put(m + 0x68, 0xffffa932);
        run.put(m + 0x6c, 0xffffa932);
        return 0;
    }
    // 0x4d4890. Allocate and initialize the three grids.
    case 0x4d4890: {
        if (!a[0]) return 0;
        for (uint32_t offset : {0x4u, 0x8u, 0xcu}) {
            uint32_t grid = run.call(0x4f63ec, 0, {0x44});
            if (grid) {
                run.put(grid + 0x4, 0);
                run.put(grid, 0x513db0);
            }
            run.put(r + offset, grid);
        }
        if (!run.get(r + 0x4) || !run.get(r + 0x8) || !run.get(r + 0xc)) return 0;
        for (uint32_t i = 0; i < 3; ++i) {
            uint32_t w = run.get(a[2 + i]);
            uint32_t h = run.get(a[2 + i] + 0x4);
            if (!invoke(run, 0x4f4490, run.get(r + 0x4 + i * 4), {run.get(a[1]), run.get(a[1] + 0x4), run.get(a[1] + 0x8), run.get(a[1] + 0xc), w, h})) return 0;
        }
        run.put(r + 0x10, 0);
        run.put(r + 0x14, 0);
        run.put(r + 0x18, run.get(a[5]) - 1);
        run.put(r + 0x1c, run.get(a[5] + 0x4) - 1);
        run.put(r + 0x40, half(run.get(a[5])));
        uint32_t y = run.get(a[5] + 0x4);
        run.put(r + 0x30, 0);
        run.put(r + 0x34, 0);
        run.put(r + 0x44, half(y));
        run.put(r + 0x38, run.get(a[6]) - 1);
        run.put(r + 0x3c, run.get(a[6] + 0x4) - 1);
        run.put(r + 0x48, half(run.get(a[6])));
        y = run.get(a[6] + 0x4);
        run.put(r + 0x20, 0);
        run.put(r + 0x24, 0);
        run.put(r + 0x4c, half(y));
        run.put(r + 0x28, run.get(a[7]) - 1);
        run.put(r + 0x2c, run.get(a[7] + 0x4) - 1);
        run.put(r + 0x50, half(run.get(a[7])));
        y = run.get(a[7] + 0x4);
        run.put(r, a[0]);
        run.put(r + 0x54, half(y));
        run.icall(0x546d5c, {r + 0x58, run.get(a[1]), run.get(a[1] + 0x4), run.get(a[1] + 0x8), run.get(a[1] + 0xc)});
        run.put(r + 0x68, 0xffffa932);
        run.put(r + 0x6c, 0xffffa932);
        return 1;
    }
    // 0x4d4a90.
    case 0x4d4a90:
        run.call(0x4d4ab0, r);
        if (a[0] & 1) run.call(0x4f6428, 0, {r});
        return r;
    // 0x4d4b00.
    case 0x4d4b00:
        for (uint32_t o : {0x4u, 0x8u, 0xcu}) {
            uint32_t grid = run.get(r + o);
            if (grid) {
                run.vcall(grid, 0x4, {1});
                run.put(r + o, 0);
            }
        }
        return 0;
    // 0x4d4b50.
    case 0x4d4b50: {
        if (run.get(r + 0x68) == a[0] && run.get(r + 0x6c) == a[1]) return 0;
        run.put(r + 0x68, a[0]);
        run.put(r + 0x6c, a[1]);
        uint32_t result = 0;
        for (uint32_t i = 0; i < 3; ++i) {
            uint32_t x = run.get(r + 0x40 + i * 8);
            uint32_t y = run.get(r + 0x44 + i * 8);
            result += invoke(run, 0x4f46b0, run.get(r + 0x4 + i * 4), {a[0] - x, a[1] - y, a[0] + x, a[1] + y, 1});
        }
        return result;
    }
    // 0x4d4c40, 0x4d50e0.
    case 0x4d4c40: case 0x4d50e0: {
        uint32_t result = 0;
        for (uint32_t o : {0x4u, 0x8u, 0xcu}) {
            uint32_t grid = run.get(r + o);
            if (f == 0x4d4c40) result += run.call(0x4d4c70, r, {grid});
            else if (grid) result += run.call(0x4d5120, r, {grid});
        }
        return result;
    }
    // 0x4d4d10. Active list processing; callbacks can change later objects.
    case 0x4d4d10: {
        uint32_t rect[3][4];
        for (uint32_t i = 0; i < 3; ++i) {
            uint32_t x = run.get(r + 0x40 + i * 8);
            uint32_t y = run.get(r + 0x44 + i * 8);
            rect[i][0] = a[0] - x;
            rect[i][1] = a[1] - y;
            rect[i][2] = a[0] + x;
            rect[i][3] = a[1] + y;
        }
        uint32_t list = run.get(r) + 0x10;
        uint32_t node = run.get(list + 0x4);
        uint32_t result = 0;
        while (node) {
            uint32_t entity = run.get(node + 0x8);
            uint32_t next = run.get(node);
            uint32_t flags = run.get(entity + 0x8);
            if ((flags & 0x40) && (s32(a[0]) < s32(run.get(r + 0x58) - 320) || s32(a[0]) > s32(run.get(r + 0x60) + 320) || s32(a[1]) < s32(run.get(r + 0x5c) - 220) || s32(a[1]) > s32(run.get(r + 0x64) + 220))) {
                if (flags & 0x80000) event29(run, entity);
                run.call(0x4f5212, list, {node});
                if (entity) run.vcall(entity, 0x4, {1});
            }
            flags = run.get(entity + 0x8);
            if (!(flags & 2) && (flags & 0x40000)) {
                uint32_t x = run.get(entity + 0x4c);
                uint32_t y = run.get(entity + 0x50);
                if (s32(x) < s32(run.get(r + 0x58))) x = run.get(r + 0x58);
                if (s32(y) < s32(run.get(r + 0x5c))) y = run.get(r + 0x5c);
                if (s32(x) >= s32(run.get(r + 0x60))) x = run.get(r + 0x60);
                if (s32(y) >= s32(run.get(r + 0x64))) y = run.get(r + 0x64);
                run.put(entity + 0x98, x);
                run.put(entity + 0x9c, y);
                flags = run.get(entity + 0x8);
                uint32_t i = (flags & 0x800000) ? 1 : ((flags & 0x1000000) ? 2 : 0);
                uint32_t grid = run.get(r + 0x4 + i * 4);
                if (s32(x) < s32(rect[i][0]) || s32(y) < s32(rect[i][1]) || s32(x) > s32(rect[i][2]) || s32(y) > s32(rect[i][3])) {
                    uint32_t targetList = run.get(r) + 0x10;
                    if (flags & 0x20) {
                        if (flags & 0x80000) event29(run, entity);
                        run.call(0x4f5212, targetList, {node});
                        if (entity) run.vcall(entity, 0x4, {1});
                    } else {
                        if (flags & 0x100000) {
                            uint32_t logic = run.get(entity + 0x6c);
                            uint32_t saved = run.get(logic + 0x1c);
                            run.put(logic + 0x1c, 30);
                            run.call(run.get(logic + 0x10), 0, {entity});
                            if (run.get(logic + 0x1c) == 30) {
                                run.put(logic + 0x1c, saved);
                            }
                        }
                        run.call(0x4f5212, targetList, {node});
                        invoke(run, 0x4f4630, grid, {entity + 0x88});
                    }
                    ++result;
                }
            }
            node = next;
        }
        return result;
    }
    // 0x4d51a0.
    case 0x4d51a0: {
        uint32_t flags = run.get(a[0] + 0x8);
        uint32_t offset = (flags & 0x800000) ? 0x8 : ((flags & 0x1000000) ? 0xc : 0x4);
        invoke(run, 0x4f4630, run.get(r + offset), {a[0] + 0x88});
        return 0;
    }
    // 0x4f4490. Original x87 instruction sequence at the startup control word.
    case 0x4f4490: {
        run.put(r + 0x8, 0);
        run.put(r + 0x28, a[0]);
        run.put(r + 0x2c, a[1]);
        run.put(r + 0x30, a[2]);
        run.put(r + 0x34, a[3]);
        uint32_t left = a[0];
        uint32_t right = a[2];
        uint32_t top = a[1];
        uint32_t bottom = a[3];
        if (s32(right) < s32(left)) std::swap(left, right);
        if (s32(bottom) < s32(top)) std::swap(top, bottom);
        auto s = xstate();
        run.x87_step(CLAW_X87_LN2, s);
        uint32_t width = right - left;
        uint32_t height = bottom - top;
        run.put(r + 0x20, width);
        run.put(r + 0x24, height);
        f64(run, s, run.getd(0x5143f0));
        run.x87_step(CLAW_X87_YL2X, s);
        run.x87_step(CLAW_X87_LN2, s);
        run.x87_step(CLAW_X87_I32, s, {a[4]});
        run.x87_step(CLAW_X87_YL2X, s);
        run.x87_step(CLAW_X87_DIV_ST1, s);
        uint32_t sx = exact(run, s, 0x4a30e0, 1, 0);
        run.x87_step(CLAW_X87_LN2, s);
        run.put(r + 0x14, sx);
        run.x87_step(CLAW_X87_I32, s, {a[5]});
        run.x87_step(CLAW_X87_YL2X, s);
        run.x87_step(CLAW_X87_DIV_ST1, s);
        uint32_t sy = exact(run, s, 0x4a30e0, 1, 0);
        run.x87_step(CLAW_X87_POP, s);
        f64(run, s, run.getd(0x5143f0));
        run.x87_step(CLAW_X87_I32, s, {sx});
        run.put(r + 0x18, sy);
        exact(run, s, 0x4f1b30, 2, 1);
        uint32_t cw = exact(run, s, 0x4a30e0, 1, 0);
        f64(run, s, run.getd(0x5143f0));
        run.x87_step(CLAW_X87_I32, s, {sy});
        run.put(r + 0x38, cw);
        exact(run, s, 0x4f1b30, 2, 1);
        uint32_t ch = exact(run, s, 0x4a30e0, 1, 0);
        uint32_t columns = uint32_t(s32(width) / s32(cw)) + 1;
        run.put(r + 0x3c, ch);
        uint32_t rows = uint32_t(s32(height) / s32(ch)) + 1;
        run.put(r + 0xc, columns);
        run.put(r + 0x10, rows);
        uint32_t count = columns * rows;
        run.put(r + 0x1c, count);
        uint32_t allocation = run.call(0x4f63ec, 0, {count * 8 + 4});
        uint32_t payload = 0;
        if (allocation) {
            payload = allocation + 4;
            run.put(allocation, count);
            run.call(0x4a4590, 0, {payload, 8, count, 0x4f4a90, 0x4c96b0});
        }
        run.put(r + 0x40, payload);
        if (!payload) return 0;
        run.put(r + 0x4, 1);
        return 1;
    }
    // 0x4f45f0.
    case 0x4f45f0:
        if (run.get(r + 0x4)) {
            uint32_t p = run.get(r + 0x40);
            if (p) {
                run.call(0x4a4450, 0, {p, 8, run.get(p - 4), 0x4c96b0});
                run.call(0x4f6428, 0, {p - 4});
            }
            run.put(r + 0x4, 0);
        }
        return 0;
    // 0x4f4630.
    case 0x4f4630: {
        uint32_t node = a[0];
        uint32_t row = sar(run.get(node + 0x14) - run.get(r + 0x2c), run.get(r + 0x18));
        uint32_t col = sar(run.get(node + 0x10) - run.get(r + 0x28), run.get(r + 0x14));
        uint32_t cell = run.get(r + 0x40) + (row * run.get(r + 0xc) + col) * 8;
        run.put(node + 0xc, cell);
        run.call(0x4b5210, cell, {node});
        run.put(r + 0x8, run.get(r + 0x8) + 1);
        return 1;
    }
    // 0x4f4680.
    case 0x4f4680:
        run.call(0x4b5270, run.get(a[0] + 0xc), {a[0]});
        run.put(a[0] + 0xc, 0);
        run.put(r + 0x8, run.get(r + 0x8) - 1);
        return 0;
    // 0x4f46b0. Inclusive clipped query with ordered callbacks.
    case 0x4f46b0: {
        uint32_t l = a[0];
        uint32_t t = a[1];
        uint32_t right = a[2];
        uint32_t b = a[3];
        uint32_t gr = run.get(r + 0x30);
        if (s32(l) > s32(gr)) return 0;
        uint32_t gl = run.get(r + 0x28);
        if (s32(right) < s32(gl)) return 0;
        uint32_t gb = run.get(r + 0x34);
        if (s32(t) > s32(gb)) return 0;
        uint32_t gt = run.get(r + 0x2c);
        if (s32(b) < s32(gt)) return 0;
        if (s32(l) < s32(gl)) l = gl;
        if (s32(right) > s32(gr)) right = gr;
        if (s32(t) < s32(gt)) t = gt;
        if (s32(b) > s32(gb)) b = gb;
        uint32_t sy = run.get(r + 0x18);
        uint32_t sx = run.get(r + 0x14);
        uint32_t minrow = sar(t - gt, sy);
        uint32_t mincol = sar(l - run.get(r + 0x28), sx);
        uint32_t maxrow = sar(b - gt, sy);
        uint32_t maxcol = sar(right - run.get(r + 0x28), sx);
        uint32_t linear = minrow * run.get(r + 0xc) + mincol;
        uint32_t result = 0;
        if (s32(minrow) > s32(maxrow)) return result;
        uint32_t rows = maxrow - minrow + 1;
        do {
            if (s32(mincol) <= s32(maxcol)) {
                uint32_t offset = linear * 8;
                uint32_t columns = maxcol - mincol + 1;
                do {
                    uint32_t node = run.get(run.get(r + 0x40) + offset);
                    while (node) {
                        uint32_t x = run.get(node + 0x10);
                        uint32_t next = run.get(node);
                        if (s32(x) >= s32(l) && s32(run.get(node + 0x14)) >= s32(t) && s32(x) <= s32(right) && s32(run.get(node + 0x14)) <= s32(b)) {
                            if (a[4]) {
                                run.call(0x4b5270, run.get(r + 0x40) + offset, {node});
                                run.put(node + 0xc, 0);
                                run.put(r + 0x8, run.get(r + 0x8) - 1);
                            }
                            run.vcall(r, 0x14, {node});
                            ++result;
                        }
                        node = next;
                    }
                    offset += 8;
                } while (--columns);
            }
            linear += run.get(r + 0xc);
        } while (--rows);
        return result;
    }
    // 0x4f4860.
    case 0x4f4860:
        return invoke(run, 0x4f48a0, r, {a[0], run.get(a[0] + 0x28), run.get(a[0] + 0x2c), run.get(a[0] + 0x30), run.get(a[0] + 0x34), a[1]});
    // 0x4f48a0. Iterator initialization.
    case 0x4f48a0: {
        uint32_t grid = a[0];
        run.put(r + 0x10, a[1]);
        run.put(r + 0x4, grid);
        run.put(r + 0x14, a[2]);
        run.put(r + 0x18, a[3]);
        run.put(r + 0x1c, a[4]);
        run.put(r + 0x40, a[5]);
        if (s32(run.get(r + 0x10)) > s32(run.get(grid + 0x30))) return 0;
        uint32_t left = run.get(grid + 0x28);
        if (s32(run.get(r + 0x18)) < s32(left)) return 0;
        if (s32(run.get(r + 0x14)) > s32(run.get(grid + 0x34))) return 0;
        uint32_t bottom = run.get(r + 0x1c);
        if (s32(bottom) < s32(run.get(grid + 0x2c))) return 0;
        if (s32(run.get(r + 0x10)) < s32(left)) {
            run.put(r + 0x10, left);
        }
        if (s32(run.get(r + 0x18)) > s32(run.get(grid + 0x30))) {
            run.put(r + 0x18, run.get(grid + 0x30));
        }
        if (s32(run.get(r + 0x14)) < s32(run.get(grid + 0x2c))) {
            run.put(r + 0x14, run.get(grid + 0x2c));
        }
        if (s32(bottom) > s32(run.get(grid + 0x34))) {
            run.put(r + 0x1c, run.get(grid + 0x34));
        }
        uint32_t row = sar(run.get(r + 0x14) - run.get(grid + 0x2c), run.get(grid + 0x18));
        run.put(r + 0x24, row);
        run.put(r + 0x20, sar(run.get(r + 0x10) - run.get(grid + 0x28), run.get(grid + 0x14)));
        run.put(r + 0x2c, sar(run.get(r + 0x1c) - run.get(grid + 0x2c), run.get(grid + 0x18)));
        run.put(r + 0x28, sar(run.get(r + 0x18) - run.get(grid + 0x28), run.get(grid + 0x14)));
        uint32_t linear = run.get(grid + 0xc) * row + run.get(r + 0x20);
        run.put(r + 0x38, row);
        run.put(r + 0x34, run.get(r + 0x20));
        run.put(r + 0x3c, linear);
        run.put(r + 0x30, linear);
        run.put(r + 0xc, run.get(run.get(grid + 0x40) + linear * 8));
        return invoke(run, 0x4f49c0, r);
    }
    // 0x4f49c0. Retain the original nonterminating rejection behavior.
    case 0x4f49c0: {
        for (;;) {
            run.put(r + 0x8, run.get(r + 0xc));
            if (!run.get(r + 0xc)) {
                do {
                    if (s32(run.get(r + 0x34)) < s32(run.get(r + 0x28))) {
                        run.put(r + 0x30, run.get(r + 0x30) + 1);
                        run.put(r + 0x34, run.get(r + 0x34) + 1);
                    } else {
                        if (s32(run.get(r + 0x38)) >= s32(run.get(r + 0x2c))) return 0;
                        uint32_t next = run.get(r + 0x3c) + run.get(run.get(r + 0x4) + 0xc);
                        run.put(r + 0x3c, next);
                        run.put(r + 0x30, next);
                        run.put(r + 0x34, run.get(r + 0x20));
                        run.put(r + 0x38, run.get(r + 0x38) + 1);
                    }
                    run.put(r + 0x8, run.get(run.get(run.get(r + 0x4) + 0x40) + run.get(r + 0x30) * 8));
                } while (!run.get(r + 0x8));
            }
            uint32_t node = run.get(r + 0x8);
            if (!node) continue;
            for (;;) {
                run.put(r + 0xc, run.get(node));
                node = run.get(r + 0x8);
                if (s32(run.get(node + 0x10)) >= s32(run.get(r + 0x10)) && s32(run.get(node + 0x14)) >= s32(run.get(r + 0x14)) && s32(run.get(node + 0x10)) <= s32(run.get(r + 0x18)) && s32(run.get(node + 0x14)) <= s32(run.get(r + 0x1c))) {
                    if (run.get(r + 0x40)) {
                        run.call(0x4b5270, run.get(run.get(r + 0x4) + 0x40) + run.get(r + 0x30) * 8, {run.get(r + 0x8)});
                        run.put(run.get(r + 0x8) + 0xc, 0);
                        uint32_t grid = run.get(r + 0x4);
                        run.put(grid + 0x8, run.get(grid + 0x8) - 1);
                    }
                    return run.get(r + 0x8);
                }
                if (!node) break;
            }
        }
    }
    default:
        run.fail(CLAW_FAULT_ABI, f);
    }
}
}
CLAW_MODULE_ENTRY(claw_spatial_grid_canonical_entry, owned, body)
