// Observed Level 1 level object actions batch 1
//
// Native recovery of eleven original functions: two logic-object
// constructors (0x4332f0, 0x44c000) with their shared base initialiser
// (0x44bc60) and tail-initialiser (0x44aaf0), a tile lookup (0x4410f0), a
// ground probe (0x43eab0), a function-table dispatcher (0x44c840) and four
// per-frame actions (0x44d000, 0x44d3c0, 0x44edd0, 0x44ef70).
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4332f0:
        return 1;
    case 0x43eab0:
        return 0;
    case 0x4410f0:
        return 2;
    case 0x44aaf0:
        return 1;
    case 0x44bc60:
        return 1;
    case 0x44c000:
        return 1;
    case 0x44c840:
        return 1;
    case 0x44d000:
        return 1;
    case 0x44d3c0:
        return 1;
    case 0x44edd0:
        return 0;
    case 0x44ef70:
        return 0;
    default:
        return -1;
    }
}

// Import slot of SetRectEmpty.
const uint32_t kSetRectEmptySlot = 0x546cdc;

// Copies a binary64 as two words, both loaded before either is stored.
void copyDouble(Run &run, uint32_t destination, uint32_t source) {
    uint32_t low = run.get(source);
    uint32_t high = run.get(source + 4);
    run.put(destination, low);
    run.put(destination + 4, high);
}

// Low and high 32-bit words of a binary64, as they travel on the stack.
uint32_t lowWord(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    return uint32_t(bits);
}

uint32_t highWord(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    return uint32_t(bits >> 32);
}

// Exact constructor arithmetic. Unsigned 32-bit qword integer loads are
// exactly representable in binary64; all arithmetic still uses x87 steps.
ClawX87State emptyFP() {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    return fp;
}

void loadUnsigned(Run &run, ClawX87State &fp, uint32_t value) {
    double number = double(value);
    run.x87_step(CLAW_X87_F64, fp, {lowWord(number), highWord(number)});
}

void storeFP(Run &run, ClawX87State &fp, uint32_t destination, bool pop = true) {
    uint64_t bits = run.x87_step(pop ? CLAW_X87_STP_F64 : CLAW_X87_ST_F64, fp);
    run.put(destination, uint32_t(bits));
    run.put(destination + 0x4, uint32_t(bits >> 32));
}

void storeExactIntOrConstant(Run &run, ClawX87State &fp, uint32_t destination, uint32_t value, uint32_t zeroSource) {
    if (!value) {
        copyDouble(run, destination, zeroSource);
    } else {
        run.x87_step(CLAW_X87_I32, fp, {value});
        storeFP(run, fp, destination);
    }
}

uint32_t exactCall(Run &run, ClawX87State &fp, uint32_t target, uint32_t receiver, uint32_t pop) {
    fp.popCount = pop;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(target, receiver, fp);
}

void floatOperand(Run &run, ClawX87State &fp, uint32_t operation, uint32_t address) {
    double number = double(run.getf(address));
    run.x87_step(operation, fp, {lowWord(number), highWord(number)});
}

// Address of the first word of a growable bit string whose header is at
// `set`: +0x08 bit count, +0x0c inline word (up to 0x20 bits) or a pointer to
// the words.
uint32_t bitWordAddress(Run &run, uint32_t count, uint32_t set) {
    if (count > 0x20) {
        return run.get(set + 0xc);
    }
    return set + 0xc;
}

// Reads bit `bit` of the bit string at `set`; a bit past the count is 0.
uint32_t bitIsSet(Run &run, uint32_t set, uint32_t bit) {
    uint32_t count = run.get(set + 0x8);
    if (count <= bit) {
        return 0;
    }
    uint32_t address = bitWordAddress(run, count, set);
    uint32_t word = run.get(address);
    return (word >> bit) & 1;
}

// Negates a pair of words and swaps them: a = -b, b = -a.
void negateSwap(Run &run, uint32_t first, uint32_t second) {
    uint32_t a = run.get(first);
    uint32_t b = run.get(second);
    run.put(first, 0 - b);
    run.put(second, 0 - a);
}

// negateSwap of obj+first / obj+second unless obj+first holds the sentinel.
void negateSwapUnlessEmpty(Run &run, uint32_t object, uint32_t first, uint32_t second) {
    uint32_t a = run.get(object + first);
    if (a == 0x80000000) {
        return;
    }
    uint32_t b = run.get(object + second);
    run.put(object + first, 0 - b);
    run.put(object + second, 0 - a);
}

// binary64 equality as the x87 compare tests it: equal or unordered.
bool equalOrUnordered(double a, double b) {
    return !(a < b) && !(a > b);
}

// Whether the player sprite is within 0x32 rows of the object and the
// proximity probe 0x4cda10 succeeds. Reads shared by 0x44d000 and 0x44ef70.
bool playerNear(Run &run, uint32_t self) {
    uint32_t player = run.get(0x537e88);
    uint32_t target = run.get(self + 0x194);
    uint32_t left = run.get(target + 0x4c);
    uint32_t top = run.get(target + 0x50);
    uint32_t playerX = run.get(player + 0x4c);
    uint32_t owner = run.get(self + 0x190);
    uint32_t level = run.get(owner + 0xc);
    uint32_t grid = run.get(level + 0x24);
    uint32_t hit = run.call(0x4cda10, grid, {left, top, playerX, 0x20});
    if (hit == 0) {
        return false;
    }
    uint32_t target2 = run.get(self + 0x194);
    uint32_t player2 = run.get(0x537e88);
    uint32_t targetY = run.get(target2 + 0x50);
    uint32_t playerY = run.get(player2 + 0x50);
    if (s32(playerY) >= s32(targetY + 0x32)) {
        return false;
    }
    if (s32(playerY) <= s32(targetY - 0x32)) {
        return false;
    }
    if (run.get(target2 + 0x38) == 0xffffffff) {
        return false;
    }
    return true;
}

// 0x4410f0 body. Tile id at column x, row y: +0x20 table of ids, +0x24 table
// of row start offsets.
uint32_t tileAt(Run &run, uint32_t map, uint32_t x, uint32_t y) {
    uint32_t rows = run.get(map + 0x24);
    uint32_t ids = run.get(map + 0x20);
    uint32_t rowStart = run.get(rows + y * 4);
    return run.get(ids + (rowStart + x) * 4);
}

// 0x4410f0. thiscall, 2 stack argument(s), returns u32.
uint32_t function_4410f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return tileAt(run, receiver, arguments[0], arguments[1]);
}

// 0x4207f0 on the level grid of the object at `self`: x is the player column
// plus xDelta.
uint32_t probeCell(Run &run, uint32_t self, uint32_t xDelta, uint32_t y) {
    uint32_t owner = run.get(self + 0x128);
    uint32_t level = run.get(owner + 0xc);
    uint32_t grid = run.get(level + 0x24);
    uint32_t actor = run.get(self + 0x12c);
    uint32_t x = run.get(actor + 0x4c) + xDelta;
    return run.call(0x4207f0, grid, {x, y});
}

// True when the probe reports 1, then 2, then 3, trying them in that order.
bool probeSolid(Run &run, uint32_t self, uint32_t xDelta, uint32_t y) {
    if (probeCell(run, self, xDelta, y) == 1) {
        return true;
    }
    if (probeCell(run, self, xDelta, y) == 2) {
        return true;
    }
    if (probeCell(run, self, xDelta, y) == 3) {
        return true;
    }
    return false;
}

// 0x43eab0. thiscall, 0 stack argument(s), returns u32.
// Searches for a ledge: first at the object's own column, then outward to the
// left (through the tile map as well) and to the right.
uint32_t function_43eab0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t owner = run.get(self + 0x128);
    uint32_t row = run.get(owner + 0x124);
    uint32_t base = run.get(owner + 0x50);
    uint32_t y = row + base + 1;
    if (!probeSolid(run, self, 0, y)) {
        return 0;
    }
    y = y - 1;
    if (probeCell(run, self, 0, y) != 0) {
        return 0;
    }
    int32_t offset = -1;
    for (;;) {
        uint32_t owner2 = run.get(self + 0x128);
        uint32_t row2 = run.get(owner2 + 0x124);
        uint32_t base2 = run.get(owner2 + 0x50);
        uint32_t level = run.get(owner2 + 0xc);
        uint32_t savedY = row2 + base2 + 1;
        uint32_t grid = run.get(level + 0x24);
        uint32_t actor = run.get(self + 0x12c);
        uint32_t clampedX = run.get(actor + 0x4c) + uint32_t(offset);
        if (s32(clampedX) < 0) {
            clampedX = 0;
        } else {
            uint32_t tiles = run.get(grid + 0x5c);
            uint32_t width = run.get(tiles + 0x30);
            if (s32(clampedX) >= s32(width)) {
                clampedX = width - 1;
            }
        }
        uint32_t clampedY = savedY;
        if (s32(clampedY) < 0) {
            clampedY = 0;
        } else {
            uint32_t tiles = run.get(grid + 0x5c);
            uint32_t height = run.get(tiles + 0x34);
            if (s32(clampedY) >= s32(height)) {
                clampedY = height - 1;
            }
        }
        uint32_t tiles = run.get(grid + 0x5c);
        uint32_t shiftX = run.get(tiles + 0x8c);
        uint32_t shiftY = run.get(tiles + 0x90);
        uint32_t tileX = uint32_t(s32(clampedX) >> (shiftX & 0x1f));
        uint32_t tileY = uint32_t(s32(clampedY) >> (shiftY & 0x1f));
        uint32_t offsetX = clampedX - (tileX << (shiftX & 0x1f));
        uint32_t offsetY = clampedY - (tileY << (shiftY & 0x1f));
        uint32_t tilesAgain = run.get(grid + 0x5c);
        uint32_t tile = tileAt(run, tilesAgain, tileX, tileY);
        uint32_t result;
        if (tile == 0xeeeeeeee || tile == 0xffffffff) {
            result = 0;
        } else {
            uint32_t objects = run.get(grid + 0x4c);
            uint32_t object = run.get(objects + (tile & 0xffff) * 4);
            result = run.vcall(object, 0x20, {offsetX, offsetY});
        }
        bool blocked = result == 1;
        if (!blocked) {
            blocked = probeCell(run, self, uint32_t(offset), savedY) == 2;
        }
        if (!blocked) {
            blocked = probeCell(run, self, uint32_t(offset), savedY) == 3;
        }
        if (!blocked) {
            break;
        }
        if (probeCell(run, self, uint32_t(offset), savedY - 1) != 0) {
            break;
        }
        offset = offset - 1;
        if (offset <= -0x32) {
            return 0;
        }
    }
    int32_t step = 1;
    for (;;) {
        uint32_t owner3 = run.get(self + 0x128);
        uint32_t base3 = run.get(owner3 + 0x50);
        uint32_t row3 = run.get(owner3 + 0x124);
        uint32_t y3 = base3 + row3 + 1;
        if (!probeSolid(run, self, uint32_t(step), y3)) {
            return 1;
        }
        if (probeCell(run, self, uint32_t(step), y3 - 1) != 0) {
            return 1;
        }
        step = step + 1;
        if (step >= 0x32) {
            return 0;
        }
    }
}

// 0x44aaf0. thiscall, 1 stack argument(s), returns void.
// Gathers nine slot values into the array at +0x2c, counting the non-zero
// ones in +0x28. The count at +0x24 and the slot being tested are re-read
// after every store, as the original does.
void collectSlot(Run &run, uint32_t self) {
    uint32_t index = run.get(self + 0x24);
    uint32_t value = run.get(self + index * 4 + 0x2c);
    run.put(self + 0x24, index + 1);
    if (value != 0) {
        uint32_t count = run.get(self + 0x28);
        run.put(self + 0x28, count + 1);
    }
}

uint32_t function_44aaf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    uint32_t owner = arguments[0];
    run.put(self, owner);
    run.put(self + 0x4, owner);
    uint32_t info = run.get(owner + 0x6c);
    run.put(self + 0x50, owner);
    run.put(self + 0x8, info);
    run.put(self + 0x54, owner);
    uint32_t info2 = run.get(owner + 0x6c);
    run.put(self + 0x58, info2);
    run.put(self + 0x28, 0);
    run.put(self + 0x24, 0);
    uint32_t source = run.get(self + 0x58);
    run.put(self + 0x2c, run.get(source + 0xf0));
    collectSlot(run, self);
    source = run.get(self + 0x58);
    uint32_t index = run.get(self + 0x24);
    run.put(self + index * 4 + 0x2c, run.get(source + 0xf8));
    collectSlot(run, self);
    source = run.get(self + 0x58);
    index = run.get(self + 0x24);
    run.put(self + index * 4 + 0x2c, run.get(source + 0xf4));
    collectSlot(run, self);
    source = run.get(self + 0x58);
    index = run.get(self + 0x24);
    run.put(self + index * 4 + 0x2c, run.get(source + 0xfc));
    collectSlot(run, self);
    source = run.get(self + 0x58);
    index = run.get(self + 0x24);
    run.put(self + index * 4 + 0x2c, run.get(source + 0x100));
    collectSlot(run, self);
    source = run.get(self + 0x58);
    index = run.get(self + 0x24);
    run.put(self + index * 4 + 0x2c, run.get(source + 0x108));
    collectSlot(run, self);
    source = run.get(self + 0x58);
    index = run.get(self + 0x24);
    run.put(self + index * 4 + 0x2c, run.get(source + 0x104));
    collectSlot(run, self);
    source = run.get(self + 0x58);
    index = run.get(self + 0x24);
    run.put(self + index * 4 + 0x2c, run.get(source + 0x10c));
    collectSlot(run, self);
    source = run.get(self + 0x54);
    index = run.get(self + 0x24);
    run.put(self + index * 4 + 0x2c, run.get(source + 0x100));
    collectSlot(run, self);
    run.put(self + 0x68, owner);
    run.put(self + 0x6c, owner);
    uint32_t info3 = run.get(owner + 0x6c);
    run.put(self + 0x70, info3);
    return 0;
}

// 0x44bc60. thiscall, 1 stack argument(s), returns u32.
// Base logic-object constructor; returns the object.
uint32_t function_44bc60(Run &run, uint32_t receiver, const uint32_t *arguments, ClawX87State &fp) {
    uint32_t self = receiver;
    uint32_t owner = arguments[0];
    run.put(self, 0x50b064);
    run.put(self + 0x8, owner);
    run.put(self + 0xc, owner);
    uint32_t info = run.get(owner + 0x6c);
    run.put(self + 0x10, info);
    run.put(self + 0x4, 0);
    run.call(0x4c7fa0, owner, {0x522d54});
    uint32_t owner2 = run.get(self + 0xc);
    run.call(0x4c8060, owner2, {0x522d48});
    run.put(self + 0x14, 0);
    run.put(self + 0x18, 0);
    run.put(self + 0x1c, 0x3e9);
    run.put(self + 0x20, 2);
    run.put(self + 0x68, 0);
    run.put(self + 0x70, 0);
    run.put(self + 0x78, 0);
    run.put(self + 0x50, 0);
    run.put(self + 0x58, 0);
    run.put(self + 0x60, 0);
    run.put(self + 0x38, 0);
    run.put(self + 0x40, 0);
    run.put(self + 0x48, 0);
    run.put(self + 0x28, 0);
    run.put(self + 0x30, 0);
    run.put(self + 0xd0, 0);
    run.put(self + 0xd8, 0);
    run.put(self + 0xe0, 0);
    run.put(self + 0x6c, 0);
    run.put(self + 0x74, 0);
    run.put(self + 0x7c, 0);
    run.put(self + 0x54, 0);
    run.put(self + 0x5c, 0);
    run.put(self + 0x64, 0);
    run.put(self + 0x3c, 0);
    run.put(self + 0x44, 0);
    run.put(self + 0x4c, 0);
    run.put(self + 0x2c, 0);
    run.put(self + 0x34, 0);
    run.put(self + 0xd4, 0);
    run.put(self + 0xdc, 0);
    run.put(self + 0xe4, 0);
    run.put(self + 0xc8, 0);
    copyDouble(run, self + 0x80, 0x513e10);
    copyDouble(run, self + 0x98, 0x513e18);
    copyDouble(run, self + 0x88, 0x513e10);
    copyDouble(run, self + 0xa0, 0x513e18);
    copyDouble(run, self + 0x90, 0x513e10);
    copyDouble(run, self + 0xa8, 0x513e18);
    copyDouble(run, self + 0xe8, 0x513e18);
    copyDouble(run, self + 0xf0, 0x513e18);
    copyDouble(run, self + 0xf8, 0x513e18);
    copyDouble(run, self + 0x100, 0x513e18);
    copyDouble(run, self + 0x108, 0x513e18);
    copyDouble(run, self + 0x110, 0x513e18);
    run.put(self, 0x50b2a4);
    uint32_t info2 = run.get(self + 0x10);
    storeExactIntOrConstant(run, fp, self + 0x80, run.get(info2 + 0x2c), 0x513e10);
    uint32_t info3 = run.get(self + 0x10);
    storeExactIntOrConstant(run, fp, self + 0x88, run.get(info3 + 0x34), 0x513e10);
    uint32_t info4 = run.get(self + 0x10);
    storeExactIntOrConstant(run, fp, self + 0x98, run.get(info4 + 0x30), 0x513e18);
    uint32_t info5 = run.get(self + 0x10);
    storeExactIntOrConstant(run, fp, self + 0xa0, run.get(info5 + 0x38), 0x513e18);
    uint32_t actor = run.get(self + 0xc);
    uint32_t y = run.get(actor + 0x50);
    uint32_t x = run.get(actor + 0x4c);
    uint32_t ticks = run.get(0x537210);
    loadUnsigned(run, fp, ticks);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50e008), run.get(0x50e00c)});
    run.x87_step(CLAW_X87_I32, fp, {run.get(actor + 0x14c)});
    run.x87_step(CLAW_X87_I32, fp, {run.get(actor + 0x148)});
    run.x87_step(CLAW_X87_I32, fp, {x});
    run.put(self + 0x78, 0);
    run.put(self + 0x60, 0);
    run.put(self + 0x38, 0);
    run.put(self + 0x40, 0);
    storeFP(run, fp, self + 0x68);
    run.x87_step(CLAW_X87_I32, fp, {y});
    run.put(self + 0x48, 0);
    run.put(self + 0x30, 0);
    run.put(self + 0x7c, 0);
    run.put(self + 0x64, 0);
    storeFP(run, fp, self + 0x70);
    run.put(self + 0x3c, 0);
    run.put(self + 0x44, 0);
    storeFP(run, fp, self + 0x50);
    run.put(self + 0x4c, 0);
    run.put(self + 0x34, 0);
    storeFP(run, fp, self + 0x58);
    storeFP(run, fp, self + 0x28);
    loadUnsigned(run, fp, run.get(0x513e40));
    storeFP(run, fp, self + 0xe8, false);
    storeFP(run, fp, self + 0xf0, false);
    storeFP(run, fp, self + 0xf8);
    uint32_t actor2 = run.get(self + 0xc);
    run.put(self + 0x120, 0);
    run.put(self + 0x124, 0);
    run.put(actor2 + 0xcc, 7);
    exactCall(run, fp, 0x4dca10, self, 0);
    return self;
}

// 0x4332f0. thiscall, 1 stack argument(s), returns u32.
// Derived logic-object constructor; returns the object.
uint32_t function_4332f0(Run &run, uint32_t receiver, const uint32_t *arguments, ClawX87State &fp) {
    uint32_t self = receiver;
    uint32_t owner = arguments[0];
    run.call(0x4082f0, self, {owner});
    uint32_t sub = self + 0x28;
    run.call(0x4080a0, sub, {});
    run.put(self, 0x50b2a4);
    uint32_t info = run.get(self + 0x10);
    storeExactIntOrConstant(run, fp, self + 0x80, run.get(info + 0x2c), 0x513e10);
    uint32_t info2 = run.get(self + 0x10);
    storeExactIntOrConstant(run, fp, self + 0x88, run.get(info2 + 0x34), 0x513e10);
    uint32_t info3 = run.get(self + 0x10);
    storeExactIntOrConstant(run, fp, self + 0x98, run.get(info3 + 0x30), 0x513e18);
    uint32_t info4 = run.get(self + 0x10);
    storeExactIntOrConstant(run, fp, self + 0xa0, run.get(info4 + 0x38), 0x513e18);
    uint32_t ticks = run.get(0x537210);
    uint32_t actor = run.get(self + 0xc);
    loadUnsigned(run, fp, ticks);
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50c830), run.get(0x50c834)});
    uint64_t scaledBits = run.x87_step(CLAW_X87_STP_F64, fp);
    double scaled;
    std::memcpy(&scaled, &scaledBits, 8);
    double heightB = double(s32(run.get(actor + 0x14c)));
    double widthA = double(s32(run.get(actor + 0x148)));
    double y = double(s32(run.get(actor + 0x50)));
    double x = double(s32(run.get(actor + 0x4c)));
    // 0x408220 takes 22 stack words, first argument lowest.
    run.call(0x408220, sub,
             {lowWord(x), highWord(x), lowWord(y), highWord(y), 0, 0, lowWord(widthA), highWord(widthA),
              lowWord(heightB), highWord(heightB), 0, 0, 0, 0, 0, 0, 0, 0, lowWord(scaled), highWord(scaled), 0, 0});
    // The original builds this binary64 through a stack scratch qword at
    // entry-28; that qword is still there when the bit-string local is
    // constructed over it below.
    uint32_t scratchWord = run.get(0x513e40);
    run.put(run.automatic(-24), 0);
    run.put(run.automatic(-28), scratchWord);
    loadUnsigned(run, fp, scratchWord);
    storeFP(run, fp, sub + 0xc0, false);
    storeFP(run, fp, sub + 0xc8, false);
    storeFP(run, fp, sub + 0xd0);
    run.put(self + 0x120, 0);
    run.put(self + 0x124, 0);
    uint32_t actor2 = run.get(self + 0xc);
    run.put(actor2 + 0xcc, 7);
    exactCall(run, fp, 0x4dca10, self, 0);
    uint32_t tail = self + 0x128;
    run.call(0x408370, tail, {owner});
    run.put(tail + 0x68, owner);
    run.put(tail + 0x6c, owner);
    uint32_t ownerInfo = run.get(owner + 0x6c);
    run.put(tail + 0x70, ownerInfo);
    run.call(0x4f6439, self + 0x1a4, {});
    run.call(0x4f6439, self + 0x1a8, {});
    uint32_t set = self + 0x2f4;
    run.call(0x4dc180, set, {});
    run.put(self + 0x3c8, 0);
    run.put(self + 0x3cc, 0);
    run.put(self + 0x3d0, 0);
    run.put(self + 0x3d4, 0);
    run.put(self + 0x3d8, 0);
    run.put(self + 0x3dc, 0);
    run.put(self + 0x3e0, 0);
    run.put(self + 0x3e4, 0);
    run.put(self + 0x3e8, 0);
    run.put(self + 0x3ec, 0);
    run.put(self + 0x3f0, 0);
    run.put(self + 0x3f4, 0);
    run.put(self + 0x3f8, 0);
    run.put(self + 0x3fc, 0);
    run.put(self, 0x50b16c);
    uint32_t actor3 = run.get(self + 0xc);
    uint32_t flags = run.get(actor3 + 0x8);
    run.put(actor3 + 0x8, flags | 0x80000);
    uint32_t info5 = run.get(self + 0x10);
    uint32_t value = run.get(info5 + 0x168);
    run.put(self + 0x4, value);
    run.put(self + 0x184, 6);
    run.put(self + 0x188, 0);
    run.put(self + 0x288, 0);
    run.put(self + 0x28c, 0x190);
    run.put(self + 0x290, 0x32);
    run.put(self + 0x29c, 0x12c);
    run.put(self + 0x2a0, 0x32);
    run.put(self + 0x2a4, 0xc8);
    run.put(self + 0x2a8, 0x32);
    run.put(self + 0x2ac, 0x64);
    run.put(self + 0x2b0, 0x32);
    uint32_t actor4 = run.get(self + 0xc);
    run.put(self + 0x2e4, run.get(actor4 + 0x108));
    uint32_t actor5 = run.get(self + 0xc);
    run.put(self + 0x2e8, run.get(actor5 + 0x114));
    uint32_t info6 = run.get(self + 0x10);
    run.put(self + 0x2ec, run.get(info6 + 0x68));
    uint32_t info7 = run.get(self + 0x10);
    uint32_t rect = self + 0x210;
    uint32_t value2 = run.get(info7 + 0x68);
    run.put(self + 0x2f0, value2);
    run.put(self + 0x19c, 0xffffffff);
    run.put(self + 0x1a0, 0);
    run.icall(kSetRectEmptySlot, {rect});
    run.icall(kSetRectEmptySlot, {self + 0x220});
    run.icall(kSetRectEmptySlot, {self + 0x230});
    run.icall(kSetRectEmptySlot, {self + 0x240});
    run.icall(kSetRectEmptySlot, {self + 0x250});
    run.icall(kSetRectEmptySlot, {self + 0x260});
    uint32_t local = run.automatic(-28);
    run.call(0x4dbe10, local, {0x534938, 0});
    run.call(0x4dbd60, set, {local});
    run.call(0x4dbcd0, local, {});
    uint32_t info8 = run.get(self + 0x10);
    if (s32(run.get(info8 + 0x64)) > 0) {
        uint32_t count = run.get(set + 0x8);
        if (count <= 2) {
            run.call(0x4dbd20, set, {2});
        } else {
            uint32_t address = bitWordAddress(run, count, set);
            uint32_t word = run.get(address);
            run.put(address, word | 4);
        }
    }
    uint32_t count2 = run.get(set + 0x8);
    if (count2 <= 9) {
        run.call(0x4dbd20, set, {9});
    } else {
        uint32_t address2 = bitWordAddress(run, count2, set);
        uint32_t word2 = run.get(address2);
        run.put(address2, word2 | 0x200);
    }
    run.put(self + 0x2b4, 0);
    run.put(self + 0x2b8, 0);
    run.put(self + 0x2bc, 0);
    run.put(self + 0x2c0, 0);
    run.put(self + 0x2c4, 0);
    run.put(self + 0x2c8, 0);
    run.put(self + 0x1ac, 0);
    run.put(self + 0x2cc, 0);
    run.put(self + 0x2d0, 0);
    run.put(self + 0x308, 0);
    run.put(self + 0x30c, 0);
    run.put(self + 0x310, 0);
    run.put(self + 0x314, 0);
    run.put(self + 0x318, 0);
    run.put(self + 0x31c, 0);
    run.put(self + 0x320, 0);
    run.put(self + 0x32c, 0);
    run.put(self + 0x330, 0);
    run.put(self + 0x334, 0);
    run.put(self + 0x338, 0);
    run.put(self + 0x33c, 0);
    run.put(self + 0x340, 0);
    run.put(self + 0x344, 0);
    run.put(self + 0x348, 0);
    run.put(self + 0x34c, 0);
    run.put(self + 0x350, 0);
    run.put(self + 0x354, 0);
    run.put(self + 0x358, 0);
    run.put(self + 0x35c, 0);
    run.put(self + 0x360, 0);
    run.put(self + 0x364, 0);
    run.put(self + 0x368, 0);
    run.put(self + 0x36c, 0);
    run.put(self + 0x370, 0);
    run.put(self + 0x374, 0);
    run.put(self + 0x378, 0);
    run.put(self + 0x37c, 0);
    run.put(self + 0x380, 0);
    run.put(self + 0x384, 0);
    run.put(self + 0x388, 0);
    uint32_t slot = run.automatic(4);
    uint32_t level = run.get(run.get(self + 0x12c) + 0xc);
    uint32_t classes = run.get(level + 0x28) + 0x10;
    run.put(slot, 0);
    run.call(0x4f6286, classes, {0x5266ec, slot});
    run.put(self + 0x38c, run.get(slot));
    level = run.get(run.get(self + 0x12c) + 0xc);
    classes = run.get(level + 0x28) + 0x10;
    run.put(slot, 0);
    run.call(0x4f6286, classes, {0x524870, slot});
    run.put(self + 0x390, run.get(slot));
    level = run.get(run.get(self + 0x12c) + 0xc);
    classes = run.get(level + 0x28) + 0x10;
    run.put(slot, 0);
    run.call(0x4f6286, classes, {0x524864, slot});
    run.put(self + 0x394, run.get(slot));
    level = run.get(run.get(self + 0x12c) + 0xc);
    classes = run.get(level + 0x28) + 0x10;
    run.put(slot, 0);
    run.call(0x4f6286, classes, {0x524858, slot});
    run.put(self + 0x398, run.get(slot));
    level = run.get(run.get(self + 0x12c) + 0xc);
    classes = run.get(level + 0x28) + 0x10;
    run.put(slot, 0);
    run.call(0x4f6286, classes, {0x52484c, slot});
    run.put(self + 0x39c, run.get(slot));
    level = run.get(run.get(self + 0x12c) + 0xc);
    classes = run.get(level + 0x28) + 0x10;
    run.put(slot, 0);
    run.call(0x4f6286, classes, {0x5266dc, slot});
    uint32_t found = run.get(slot);
    run.put(self + 0x3a0, 0);
    run.put(self + 0x148, found);
    run.put(self + 0x3a4, 0);
    run.put(self + 0x3a8, 0);
    run.put(self + 0x3ac, 0);
    run.put(self + 0x3b0, 0);
    run.put(self + 0x3b4, 0);
    run.put(self + 0x3b8, 0);
    run.put(self + 0x3bc, 0);
    run.put(self + 0x3c0, 0);
    run.put(self + 0x40, 0);
    run.put(self + 0x44, 0x409f4000);
    uint32_t actor6 = run.get(self + 0x12c);
    uint32_t protection = run.get(actor6 + 0x164);
    run.put(actor6 + 0x164, protection & 0xfffffffe);
    uint32_t actor7 = run.get(self + 0x12c);
    if ((run.get(actor7 + 0x40) & 2) != 0) {
        uint32_t target = run.get(tail + 0x4);
        if ((run.get(target + 0x40) & 2) == 0) {
            negateSwap(run, tail + 0x10, tail + 0x18);
            uint32_t targetFlags = run.get(target + 0x40);
            run.put(target + 0x40, targetFlags | 2);
            uint32_t target2 = run.get(tail + 0x4);
            negateSwapUnlessEmpty(run, target2, 0x118, 0x120);
            negateSwapUnlessEmpty(run, target2, 0x128, 0x130);
            negateSwapUnlessEmpty(run, target2, 0x138, 0x140);
        }
    }
    return self;
}

// 0x44c000. thiscall, 1 stack argument(s), returns u32.
// Logic-object constructor built on 0x44bc60; returns the object.
uint32_t function_44c000(Run &run, uint32_t receiver, const uint32_t *arguments, ClawX87State &fp) {
    uint32_t self = receiver;
    uint32_t owner = arguments[0];
    function_44bc60(run, self, arguments, fp);
    uint32_t tail = self + 0x128;
    uint32_t tailArguments[1] = {owner};
    function_44aaf0(run, tail, tailArguments);
    run.call(0x4f6439, self + 0x1a4, {});
    run.call(0x4f6439, self + 0x1a8, {});
    uint32_t set = self + 0x2f4;
    run.call(0x4dc180, set, {});
    run.put(self + 0x3c8, 0);
    run.put(self + 0x3cc, 0);
    run.put(self + 0x3d0, 0);
    run.put(self + 0x3d4, 0);
    run.put(self + 0x3d8, 0);
    run.put(self + 0x3dc, 0);
    run.put(self + 0x3e0, 0);
    run.put(self + 0x3e4, 0);
    run.put(self + 0x3e8, 0);
    run.put(self + 0x3ec, 0);
    run.put(self + 0x3f0, 0);
    run.put(self + 0x3f4, 0);
    run.put(self + 0x3f8, 0);
    run.put(self + 0x3fc, 0);
    run.put(self, 0x50b16c);
    uint32_t actor = run.get(self + 0xc);
    uint32_t flags = run.get(actor + 0x8);
    run.put(actor + 0x8, flags | 0x80000);
    uint32_t info = run.get(self + 0x10);
    uint32_t value = run.get(info + 0x168);
    run.put(self + 0x4, value);
    run.put(self + 0x184, 6);
    run.put(self + 0x188, 0);
    run.put(self + 0x288, 0);
    run.put(self + 0x28c, 0x190);
    run.put(self + 0x290, 0x32);
    run.put(self + 0x29c, 0x12c);
    run.put(self + 0x2a0, 0x32);
    run.put(self + 0x2a4, 0xc8);
    run.put(self + 0x2a8, 0x32);
    run.put(self + 0x2ac, 0x64);
    run.put(self + 0x2b0, 0x32);
    uint32_t actor2 = run.get(self + 0xc);
    run.put(self + 0x2e4, run.get(actor2 + 0x108));
    uint32_t actor3 = run.get(self + 0xc);
    run.put(self + 0x2e8, run.get(actor3 + 0x114));
    uint32_t info2 = run.get(self + 0x10);
    run.put(self + 0x2ec, run.get(info2 + 0x68));
    uint32_t info3 = run.get(self + 0x10);
    uint32_t rect = self + 0x210;
    uint32_t cornerB = self + 0x220;
    uint32_t cornerC = self + 0x230;
    run.put(self + 0x2f0, run.get(info3 + 0x68));
    run.put(self + 0x19c, 0xffffffff);
    run.put(self + 0x1a0, 0);
    run.icall(kSetRectEmptySlot, {rect});
    run.icall(kSetRectEmptySlot, {cornerB});
    run.icall(kSetRectEmptySlot, {cornerC});
    run.icall(kSetRectEmptySlot, {self + 0x240});
    run.icall(kSetRectEmptySlot, {self + 0x250});
    run.icall(kSetRectEmptySlot, {self + 0x260});
    uint32_t local = run.automatic(-28);
    run.call(0x4dbe10, local, {0x534938, 0});
    run.call(0x4dbd60, set, {local});
    run.call(0x4dbcd0, local, {});
    uint32_t info4 = run.get(self + 0x10);
    if (s32(run.get(info4 + 0x64)) > 0) {
        run.call(0x420fc0, set, {2});
    }
    run.call(0x420fc0, set, {9});
    run.put(self + 0x2b4, 0);
    run.put(self + 0x2b8, 0);
    run.put(self + 0x2bc, 0);
    run.put(self + 0x2c0, 0);
    run.put(self + 0x2c4, 0);
    run.put(self + 0x2c8, 0);
    run.put(self + 0x1ac, 0);
    run.put(self + 0x2cc, 0);
    run.put(self + 0x2d0, 0);
    run.put(self + 0x308, 0);
    run.put(self + 0x30c, 0);
    run.put(self + 0x310, 0);
    run.put(self + 0x314, 0);
    run.put(self + 0x318, 0);
    run.put(self + 0x31c, 0);
    run.put(self + 0x320, 0);
    run.put(self + 0x32c, 0);
    run.put(self + 0x330, 0);
    run.put(self + 0x334, 0);
    run.put(self + 0x338, 0);
    run.put(self + 0x33c, 0);
    run.put(self + 0x340, 0);
    run.put(self + 0x344, 0);
    run.put(self + 0x348, 0);
    run.put(self + 0x34c, 0);
    run.put(self + 0x350, 0);
    run.put(self + 0x354, 0);
    run.put(self + 0x358, 0);
    run.put(self + 0x35c, 0);
    run.put(self + 0x360, 0);
    run.put(self + 0x364, 0);
    run.put(self + 0x368, 0);
    run.put(self + 0x36c, 0);
    run.put(self + 0x370, 0);
    run.put(self + 0x374, 0);
    run.put(self + 0x378, 0);
    run.put(self + 0x37c, 0);
    run.put(self + 0x380, 0);
    run.put(self + 0x384, 0);
    run.put(self + 0x388, 0);
    uint32_t text1 = run.call(0x40f780, tail, {0x5266ec});
    run.put(self + 0x38c, text1);
    uint32_t text2 = run.call(0x40f780, tail, {0x524870});
    run.put(self + 0x390, text2);
    uint32_t text3 = run.call(0x40f780, tail, {0x524864});
    run.put(self + 0x394, text3);
    uint32_t text4 = run.call(0x40f780, tail, {0x524858});
    run.put(self + 0x398, text4);
    uint32_t text5 = run.call(0x40f780, tail, {0x52484c});
    run.put(self + 0x39c, text5);
    uint32_t text6 = run.call(0x40f780, tail, {0x5266dc});
    run.put(self + 0x148, text6);
    run.put(self + 0x3a0, 0);
    run.put(self + 0x3a4, 0);
    run.put(self + 0x3a8, 0);
    run.put(self + 0x3ac, 0);
    run.put(self + 0x3b0, 0);
    run.put(self + 0x3b4, 0);
    run.put(self + 0x3b8, 0);
    run.put(self + 0x3bc, 0);
    run.put(self + 0x3c0, 0);
    run.put(self + 0x40, 0);
    run.put(self + 0x44, 0x409f4000);
    uint32_t actor4 = run.get(self + 0x12c);
    uint32_t protection = run.get(actor4 + 0x164);
    run.put(actor4 + 0x164, protection & 0xfffffffe);
    uint32_t actor5 = run.get(self + 0x12c);
    if ((run.get(actor5 + 0x40) & 2) != 0) {
        run.call(0x4357a0, tail, {});
    }
    run.put(self + 0x428, 0);
    run.put(self + 0x42c, 0);
    run.put(self + 0x430, 0);
    run.put(self + 0x434, 0);
    run.put(self + 0x438, 0);
    run.put(self + 0x43c, 0);
    run.put(self + 0x440, 0);
    run.put(self + 0x444, 0);
    run.put(self, 0x50e12c);
    uint32_t actor6 = run.get(self + 0xc);
    uint32_t flags2 = run.get(actor6 + 0x8);
    run.put(actor6 + 0x8, flags2 | 0x80000);
    run.put(self + 0x424, 0);
    run.put(self + 0x448, 0);
    run.put(self + 0x2d0, 0xa);
    run.put(self + 0x408, 0);
    run.put(self + 0x40c, 0);
    run.put(self + 0x414, 0);
    uint32_t level = run.get(run.get(self + 0x12c) + 0xc);
    uint32_t classes = run.get(level + 0x28);
    uint32_t c1 = run.call(0x4061b0, classes, {0x524870});
    run.put(self + 0x41c, c1);
    level = run.get(run.get(self + 0x12c) + 0xc);
    classes = run.get(level + 0x28);
    uint32_t c2 = run.call(0x4061b0, classes, {0x5246f8});
    run.put(self + 0x3a8, c2);
    level = run.get(run.get(self + 0x12c) + 0xc);
    classes = run.get(level + 0x28);
    uint32_t c3 = run.call(0x4061b0, classes, {0x5246f8});
    run.put(self + 0x3ac, c3);
    run.put(self + 0x410, 0);
    run.put(self + 0x40c, 0);
    run.put(self + 0x420, 0);
    level = run.get(run.get(self + 0x12c) + 0xc);
    classes = run.get(level + 0x28);
    uint32_t c4 = run.call(0x4061b0, classes, {0x527d50});
    run.put(self + 0x414, c4);
    level = run.get(run.get(self + 0x12c) + 0xc);
    classes = run.get(level + 0x28);
    uint32_t c5 = run.call(0x4061b0, classes, {0x527d40});
    run.put(self + 0x418, c5);
    level = run.get(run.get(self + 0x12c) + 0xc);
    classes = run.get(level + 0x28);
    uint32_t c6 = run.call(0x4061b0, classes, {0x527d34});
    run.put(self + 0x408, c6);
    run.put(self + 0x44c, 0);
    run.put(self + 0x50, 0);
    run.put(self + 0x54, 0);
    run.put(self + 0x58, 0);
    run.put(self + 0x5c, 0);
    copyDouble(run, self + 0x88, 0x513e10);
    copyDouble(run, self + 0xa0, 0x513e18);
    run.put(self + 0x400, 0x3c);
    run.put(self + 0x404, 0x78);
    run.call(0x420fc0, set, {0});
    run.call(0x420fc0, set, {3});
    run.call(0x420fc0, set, {5});
    run.put(self + 0x124, 8);
    uint32_t actor7 = run.get(self + 0x12c);
    uint32_t flags3 = run.get(actor7 + 0x8);
    run.put(actor7 + 0x8, flags3 | 0x40);
    uint32_t actor8 = run.get(self + 0x12c);
    uint32_t protection2 = run.get(actor8 + 0x164);
    run.put(actor8 + 0x164, protection2 | 0x400);
    uint32_t actor9 = run.get(self + 0x12c);
    run.put(actor9 + 0xd0, 4);
    uint32_t actor10 = run.get(self + 0x12c);
    run.put(actor10 + 0xd4, 0x3001032);
    run.call(0x4296f0, cornerC, {0xffffff77, 0xffffffe5, 0, 0xfffffff9});
    run.call(0x4296f0, self + 0x240, {0xffffff77, 0x14, 0, 0x28});
    uint32_t word0 = run.get(cornerC);
    uint32_t word1 = run.get(cornerC + 0x4);
    uint32_t word2 = run.get(cornerC + 0x8);
    run.put(cornerB, word0);
    uint32_t word3 = run.get(cornerC + 0xc);
    run.put(cornerB + 0x4, word1);
    run.put(cornerB + 0x8, word2);
    run.put(cornerB + 0xc, word3);
    run.call(0x4296f0, rect, {0xffffffff, 0xffffffff, 1, 1});
    uint32_t cornerD = self + 0x250;
    run.call(0x4296f0, cornerD, {0xffffffec, 0xffffffc4, 0x14, 0x33});
    run.call(0x4296f0, self + 0x260, {0xffffffec, 0xfffffff1, 0x14, 0xf});
    run.call(0x40ab80, tail, {0xffffffec, 0xffffffce, 0x14, 0x32});
    run.call(0x40abb0, tail, {cornerD});
    run.put(self + 0x28c, 0x1f4);
    run.put(self + 0x290, 0x28);
    run.put(self + 0x29c, 0xc8);
    run.put(self + 0x2a0, 0x28);
    run.put(self + 0x2a4, 0x96);
    run.put(self + 0x2a8, 0x28);
    run.put(self + 0x2ac, 0x64);
    run.put(self + 0x2b0, 0x28);
    run.put(self + 0x2b4, 0xa);
    run.put(self + 0x2b8, 0xfffffff6);
    run.put(self + 0x294, 0x12c);
    run.put(self + 0x298, 0x28);
    run.put(self + 0x2bc, 0xffffffd3);
    run.put(self + 0x2c0, 0xffffffec);
    run.put(self + 0x2c4, 0x14);
    run.put(self + 0x2c8, 0xfffffff1);
    run.put(self + 0x2e4, 0x32);
    floatOperand(run, fp, CLAW_X87_F64, 0x5262b8);
    floatOperand(run, fp, CLAW_X87_MUL_F64, 0x50e0c0);
    uint32_t speed = exactCall(run, fp, 0x4a30e0, 0, 1);
    if (speed <= 0x63) {
        speed = 0x63;
    }
    run.put(self + 0x2e4, speed);
    uint32_t actor11 = run.get(self + 0xc);
    run.put(actor11 + 0x10c, 10);
    uint32_t actor12 = run.get(self + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(actor12 + 0x10c)});
    floatOperand(run, fp, CLAW_X87_MUL_F64, 0x5262b4);
    uint32_t rounded = exactCall(run, fp, 0x4a30e0, 0, 1);
    run.put(actor12 + 0x10c, rounded);
    uint32_t actor13 = run.get(self + 0xc);
    run.put(actor13 + 0x104, 10);
    uint32_t actor14 = run.get(self + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(actor14 + 0x104)});
    floatOperand(run, fp, CLAW_X87_MUL_F64, 0x5262b0);
    uint32_t rounded2 = exactCall(run, fp, 0x4a30e0, 0, 1);
    run.put(actor14 + 0x104, rounded2);
    return self;
}

// 0x44c840. thiscall, 1 stack argument(s), returns void.
// Looks up the handler for an action index in a function table and runs it,
// falling back to 0x43d490 when the table entry is empty.
uint32_t tableSlot(Run &run, uint32_t index, uint32_t low) {
    bool inRange = s32(index) >= s32(low);
    if (inRange) {
        inRange = s32(index) <= s32(run.get(0x537884));
    }
    if (!inRange) {
        uint32_t found = run.call(0x4db6e0, 0x537878, {index, 0});
        if (found == 0) {
            uint32_t message = run.get(0x544b4c);
            uint32_t code = run.call(0x4db5f0, 0, {});
            uint32_t owner = run.get(0x53787c);
            run.put(0x544b14, code);
            run.call(0x4db4d0, owner, {0x537878, message, 0xc});
            return run.get(0x53788c);
        }
        low = run.get(0x537880);
    }
    uint32_t base = run.get(0x537888);
    uint32_t stride = run.get(0x537890);
    return (index - low) * stride + base;
}

uint32_t function_44c840(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    uint32_t index = arguments[0];
    uint32_t low = run.get(0x537880);
    run.put(0x537898, 0);
    uint32_t slot = tableSlot(run, index, low);
    uint32_t handler = run.get(slot);
    if (handler == 0) {
        run.call(0x43d490, self, {index});
        return 0;
    }
    uint32_t low2 = run.get(0x537880);
    run.put(0x537898, 0);
    uint32_t slot2 = tableSlot(run, index, low2);
    uint32_t target = run.get(slot2);
    run.call(target, self, {});
    return 0;
}

// 0x44d000. thiscall, 1 stack argument(s), returns void.
// Per-state setup after a logic state change; `state` is the state name.
uint32_t function_44d000(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    uint32_t state = arguments[0];
    uint32_t set = self + 0x2f4;
    uint32_t delay;
    if (run.get(0x541334) == 0) {
        delay = run.call(0x44f850, 0, {0x3e8});
    } else {
        delay = 0x1fffffff;
    }
    run.put(self + 0x3c4, delay);
    run.call(0x43e420, self, {});
    uint32_t guarded = bitIsSet(run, set, 9);
    bool clearLow = guarded == 0;
    if (state == 0x52720c) {
        clearLow = true;
    }
    if (state == 0x527204) {
        clearLow = true;
    }
    if (state == 0x527da0) {
        clearLow = true;
    }
    if (state == 0x5234f4) {
        clearLow = true;
    }
    if (state == 0x5271d8) {
        clearLow = true;
    }
    if (state == 0x5271cc) {
        clearLow = true;
    }
    if (state == 0x5271b4) {
        clearLow = true;
    }
    if (!clearLow) {
        uint32_t now = run.get(0x537210);
        uint32_t since = run.get(self + 0x440);
        uint32_t window = run.get(self + 0x444);
        clearLow = (now - since) < window;
    }
    uint32_t actor = run.get(self + 0x12c);
    uint32_t protection = run.get(actor + 0x164);
    if (clearLow) {
        run.put(actor + 0x164, protection & 0xfffffffe);
    } else {
        run.put(actor + 0x164, protection | 1);
    }
    uint32_t boxes = run.get(self + 0xc);
    uint32_t box = boxes + 0x138;
    uint32_t source = self + 0x210;
    uint32_t w0 = run.get(source);
    run.put(box, w0);
    uint32_t w1 = run.get(source + 0x4);
    run.put(box + 0x4, w1);
    uint32_t w2 = run.get(source + 0x8);
    run.put(box + 0x8, w2);
    uint32_t w3 = run.get(source + 0xc);
    run.put(box + 0xc, w3);
    uint32_t actor2 = run.get(self + 0x12c);
    if ((run.get(actor2 + 0x40) & 2) != 0) {
        uint32_t boxes2 = run.get(self + 0xc);
        uint32_t right = run.get(boxes2 + 0x140);
        uint32_t left = run.get(boxes2 + 0x138);
        run.put(boxes2 + 0x138, 0 - right);
        uint32_t boxes3 = run.get(self + 0xc);
        run.put(boxes3 + 0x140, 0 - left);
    }
    uint32_t actor3 = run.get(self + 0x12c);
    uint32_t flipped = run.get(actor3 + 0x40) & 2;
    uint32_t protection2 = run.get(actor3 + 0x164);
    if (flipped != 0) {
        run.put(actor3 + 0x164, protection2 | 2);
    } else {
        run.put(actor3 + 0x164, protection2 & 0xfffffffd);
    }
    bool near = false;
    if (run.get(0x534eac) != 0x26b7) {
        near = playerNear(run, self);
    }
    if (near) {
        if (bitIsSet(run, set, 8) != 0) {
            return 0;
        }
    }
    uint32_t mode = run.get(self + 0x184);
    if ((mode == 5 || mode == 6) && state != 0x5234f4) {
        if (bitIsSet(run, set, 7) == 0) {
            if (s32(run.get(self + 0x20)) >= 2) {
                run.put(self + 0x14, 0x44f840);
            }
            uint32_t count = run.get(set + 0x8);
            if (count <= 7) {
                run.call(0x4dbd20, set, {7});
            } else {
                uint32_t address = bitWordAddress(run, count, set);
                uint32_t word = run.get(address);
                run.put(address, word | 0x80);
            }
        }
    } else {
        uint32_t count2 = run.get(set + 0x8);
        if (count2 > 7) {
            uint32_t address2 = bitWordAddress(run, count2, set);
            uint32_t word2 = run.get(address2);
            run.put(address2, word2 ^ 0x80);
        }
    }
    uint32_t actor4 = run.get(self + 0x12c);
    uint32_t held = run.get(actor4 + 0x8) & 0x10;
    uint32_t carried = run.get(actor4 + 0x80);
    if (held != 0 && carried != 0 && (run.get(carried + 0x164) & 0x8000) != 0) {
        uint32_t carriedState = run.get(carried + 0x6c);
        if (run.get(carriedState + 0x1c) == 5) {
            run.put(carriedState + 0x1c, 0x457);
            return 0;
        }
    }
    uint32_t carried2 = run.get(actor4 + 0x80);
    if (carried2 != 0 && (run.get(carried2 + 0x164) & 0x20000) != 0 && run.get(self + 0x448) != 0) {
        if (s32(run.get(self + 0x20)) >= 2) {
            run.put(self + 0x14, 0x44f6e0);
        }
        return 0;
    }
    if (held != 0) {
        if (carried2 != 0 && (run.get(carried2 + 0x164) & 0x10000) != 0) {
            uint32_t carriedState2 = run.get(carried2 + 0x6c);
            if (run.get(carriedState2 + 0x1c) == 5) {
                run.put(self + 0x448, 1);
                uint32_t actor5 = run.get(self + 0x12c);
                uint32_t carried3 = run.get(actor5 + 0x80);
                uint32_t carriedState3 = run.get(carried3 + 0x6c);
                run.put(carriedState3 + 0x1c, 0x457);
                return 0;
            }
        }
        uint32_t count3 = run.get(set + 0x8);
        if (count3 <= 2) {
            run.call(0x4dbd20, set, {2});
            return 0;
        }
        uint32_t address3 = bitWordAddress(run, count3, set);
        uint32_t word3 = run.get(address3);
        run.put(address3, word3 | 4);
        return 0;
    }
    uint32_t ledge = function_43eab0(run, self, arguments);
    if (ledge != 0) {
        if (bitIsSet(run, set, 2) == 0) {
            if (s32(run.get(self + 0x20)) >= 2) {
                run.put(self + 0x14, 0x44e120);
            }
        }
    }
    return 0;
}

// 0x44d3c0. thiscall, 1 stack argument(s), returns void.
// Runs a pending action and its guard, then rounds the carried object's
// position into integer coordinates.
uint32_t function_44d3c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t pending = run.get(self + 0x14);
    if (pending != 0) {
        uint32_t guard = run.get(self + 0x18);
        if (guard != 0) {
            uint32_t info = run.get(self + 0x10);
            uint32_t infoState = run.get(info + 0x1c);
            uint32_t state = run.get(self + 0x1c);
            if (infoState == state) {
                run.call(guard, self, {});
                run.put(self + 0x18, 0);
            }
        }
        uint32_t action = run.get(self + 0x14);
        run.call(action, self, {});
        run.put(self + 0x14, 0);
        run.put(self + 0x1c, 0x3e9);
    }
    run.vcall(self, 0x24, {});
    uint32_t mover = run.get(self + 0x44c);
    if (mover == 0) {
        return 0;
    }
    if (run.get(mover + 0x1a4) != 0 && run.get(mover + 0x19c) == 0) {
        uint32_t moverFlags = run.get(mover + 0x8);
        run.put(mover + 0x8, moverFlags | 0x10000);
        run.put(self + 0x44c, 0);
        return 0;
    }
    auto fp = emptyFP();
    run.x87_step(CLAW_X87_F64, fp, {run.get(self + 0x68), run.get(self + 0x6c)});
    uint32_t roundedX = exactCall(run, fp, 0x4a30e0, 0, 1);
    run.put(mover + 0x4c, roundedX);
    run.x87_step(CLAW_X87_F64, fp, {run.get(self + 0x70), run.get(self + 0x74)});
    uint32_t roundedY = exactCall(run, fp, 0x4a30e0, 0, 1);
    uint32_t mover2 = run.get(self + 0x44c);
    run.put(mover2 + 0x50, roundedY);
    return 0;
}

// 0x44edd0. thiscall, 0 stack argument(s), returns u32.
// Turns around at the ends of a patrol: faces right at the left end, left at
// the right end, then re-arms the pacing state.
uint32_t function_44edd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t set = self + 0x2f4;
    if (bitIsSet(run, set, 2) != 0) {
        run.vcall(self, 0x48, {});
        return 0;
    }
    run.put(self + 0x50, 0);
    double position = run.getd(self + 0x68);
    double leftEnd = run.getd(self + 0x98);
    if (equalOrUnordered(position, leftEnd)) {
        run.put(self + 0x54, 0xc05e0000);
        uint32_t actor = run.get(self + 0x12c);
        if ((run.get(actor + 0x40) & 2) != 0) {
            negateSwap(run, self + 0x138, self + 0x140);
            uint32_t actorFlags = run.get(actor + 0x40);
            run.put(actor + 0x40, actorFlags & 0xfffffffd);
            uint32_t actor2 = run.get(self + 0x12c);
            negateSwapUnlessEmpty(run, actor2, 0x118, 0x120);
            run.call(0x406150, actor2, {});
            run.call(0x406180, actor2, {});
        }
    } else {
        run.put(self + 0x54, 0x405e0000);
        uint32_t actor3 = run.get(self + 0x12c);
        if ((run.get(actor3 + 0x40) & 2) == 0) {
            negateSwap(run, self + 0x138, self + 0x140);
            uint32_t actorFlags2 = run.get(actor3 + 0x40);
            run.put(actor3 + 0x40, actorFlags2 | 2);
            uint32_t actor4 = run.get(self + 0x12c);
            negateSwapUnlessEmpty(run, actor4, 0x118, 0x120);
            negateSwapUnlessEmpty(run, actor4, 0x128, 0x130);
            run.call(0x406180, actor4, {});
        }
    }
    uint32_t info = run.get(self + 0x10);
    uint32_t savedState = run.get(info + 0x1c);
    run.put(self + 0x24, savedState);
    uint32_t pacing = run.call(0x4dba00, 0x537668, {0x527d78});
    uint32_t info2 = run.get(self + 0x10);
    run.put(info2 + 0x1c, pacing);
    uint32_t actor5 = run.get(self + 0x12c);
    uint32_t channel = run.get(self + 0x34c);
    uint32_t facing = run.get(actor5 + 0x190);
    run.put(self + 0x134, facing);
    run.call(0x4c8220, actor5 + 0x188, {channel});
    return 0;
}

// 0x44ef70. thiscall, 0 stack argument(s), returns u32.
// Patrol update: at either end of the patrol, turn around or drop to the
// idle action by chance; then react to the player in range.
uint32_t function_44ef70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t set = self + 0x2f4;
    uint32_t actorBase = run.get(self + 0x12c);
    uint32_t stamp = run.get(0x5430c4);
    run.call(0x4c82a0, actorBase + 0x188, {stamp});
    double position = run.getd(self + 0x68);
    double rightEnd = run.getd(self + 0x80);
    if (equalOrUnordered(position, rightEnd)) {
        uint32_t roll = run.call(0x4a3050, 0, {});
        int32_t remainder = s32(roll) % 100;
        if (remainder < 0x32) {
            run.vcall(self, 0x48, {});
        } else {
            run.put(self + 0x50, 0);
            run.put(self + 0x54, 0x405e0000);
            uint32_t actor = run.get(self + 0x12c);
            if ((run.get(actor + 0x40) & 2) == 0) {
                negateSwap(run, self + 0x138, self + 0x140);
                uint32_t actorFlags = run.get(actor + 0x40);
                run.put(actor + 0x40, actorFlags | 2);
                uint32_t actor2 = run.get(self + 0x12c);
                negateSwapUnlessEmpty(run, actor2, 0x118, 0x120);
                run.call(0x406150, actor2, {});
                run.call(0x406180, actor2, {});
            }
        }
    }
    double position2 = run.getd(self + 0x68);
    double leftEnd = run.getd(self + 0x98);
    if (equalOrUnordered(position2, leftEnd)) {
        uint32_t roll2 = run.call(0x4a3050, 0, {});
        int32_t remainder2 = s32(roll2) % 100;
        if (remainder2 < 0x32) {
            run.vcall(self, 0x48, {});
        } else {
            run.put(self + 0x50, 0);
            run.put(self + 0x54, 0xc05e0000);
            uint32_t actor3 = run.get(self + 0x12c);
            if ((run.get(actor3 + 0x40) & 2) != 0) {
                negateSwap(run, self + 0x138, self + 0x140);
                uint32_t actorFlags2 = run.get(actor3 + 0x40);
                run.put(actor3 + 0x40, actorFlags2 & 0xfffffffd);
                uint32_t actor4 = run.get(self + 0x12c);
                negateSwapUnlessEmpty(run, actor4, 0x118, 0x120);
                negateSwapUnlessEmpty(run, actor4, 0x128, 0x130);
                run.call(0x406180, actor4, {});
            }
        }
    }
    if (bitIsSet(run, set, 8) == 0) {
        int32_t phase = run.gets(self + 0x184);
        if (phase >= 0 && phase <= 4) {
            run.vcall(self, 0x44, {});
        }
        return 0;
    }
    if (run.get(0x534eac) == 0x26b7) {
        return 0;
    }
    if (playerNear(run, self)) {
        run.vcall(self, 0x44, {});
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4332f0: {
        auto fp = run.x87_entry(function);
        uint32_t value = function_4332f0(run, receiver, arguments, fp);
        run.x87_finish(function, fp);
        return value;
    }
    case 0x43eab0:
        return function_43eab0(run, receiver, arguments);
    case 0x4410f0:
        return function_4410f0(run, receiver, arguments);
    case 0x44aaf0:
        return function_44aaf0(run, receiver, arguments);
    case 0x44bc60: {
        auto fp = run.x87_entry(function);
        uint32_t value = function_44bc60(run, receiver, arguments, fp);
        run.x87_finish(function, fp);
        return value;
    }
    case 0x44c000: {
        auto fp = run.x87_entry(function);
        uint32_t value = function_44c000(run, receiver, arguments, fp);
        run.x87_finish(function, fp);
        return value;
    }
    case 0x44c840:
        return function_44c840(run, receiver, arguments);
    case 0x44d000:
        return function_44d000(run, receiver, arguments);
    case 0x44d3c0:
        return function_44d3c0(run, receiver, arguments);
    case 0x44edd0:
        return function_44edd0(run, receiver, arguments);
    case 0x44ef70:
        return function_44ef70(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}


ClawSourceContract sourceContract(uint32_t function) {
    if (function == 0x44c840)
        return {0x7ff, 0x5ff, 0x472, 0x4};
    return {};
}

bool optionalSource(uint32_t function) {
    return function == 0x44c840;
}

uint32_t sourceCommonFlags(uint32_t value) {
    uint32_t parity = value & 0xff;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    return 0x2u | ((parity & 1) ? 0u : 0x4u) | (value == 0 ? 0x40u : 0u) | (value & 0x80000000u ? 0x80u : 0u);
}

void sourceCompare(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    uint32_t result = left - right;
    cpu.eflags = sourceCommonFlags(result) | (left < right ? 0x1u : 0u) | ((left ^ right ^ result) & 0x10u) | (((left ^ right) & (left ^ result) & 0x80000000u) ? 0x800u : 0u);
}

void sourceAdd(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    uint32_t result = left + right;
    cpu.eflags = sourceCommonFlags(result) | (result < left ? 0x1u : 0u) | ((left ^ right ^ result) & 0x10u) | ((~(left ^ right) & (left ^ result) & 0x80000000u) ? 0x800u : 0u);
}

void sourcePush(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 0x4;
    run.put(cpu.esp, value);
}

ClawSourceContext sourceChild(Run &run, ClawSourceContext &cpu, uint32_t target, uint32_t returnPC) {
    sourcePush(run, cpu, returnPC);
    cpu.eip = target;
    auto child = cpu;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0x472;
    return child;
}

void sourceReturned(ClawSourceContext &cpu, const ClawSourceContext &child) {
    cpu.eax = child.eax;
    cpu.ebx = child.ebx;
    cpu.ecx = child.ecx;
    cpu.edx = child.edx;
    cpu.esi = child.esi;
    cpu.edi = child.edi;
    cpu.ebp = child.ebp;
    cpu.esp = child.esp;
    cpu.eip = child.eip;
    cpu.eflags = child.eflags;
    cpu.fsHead = child.fsHead;
}

// 0x44c840. Source dispatch retains real frames and the void entry's machine EAX.
uint32_t sourceDispatch(Run &run) {
    auto &cpu = run.source();
    sourcePush(run, cpu, cpu.ebp);
    cpu.ebp = cpu.ecx;
    cpu.ecx = run.get(0x537880);
    sourcePush(run, cpu, cpu.esi);
    cpu.esi = run.get(cpu.esp + 0xc);
    sourcePush(run, cpu, cpu.edi);
    sourceCompare(cpu, cpu.esi, cpu.ecx);
    run.put(0x537898, 0);
    if (s32(cpu.esi) < s32(cpu.ecx))
        goto firstGrow;
    sourceCompare(cpu, cpu.esi, run.get(0x537884));
    if (s32(cpu.esi) > s32(run.get(0x537884)))
        goto firstGrow;
    cpu.eax = cpu.esi;
    goto firstSlot;
firstGrow:
    sourcePush(run, cpu, 0);
    sourcePush(run, cpu, cpu.esi);
    cpu.ecx = 0x537878;
    {
        auto child = sourceChild(run, cpu, 0x4db6e0, 0x44c876);
        run.source_call(0x4db6e0, cpu.ecx, 0x44c876, child, {cpu.esi, 0}, 0, 0x8);
        sourceReturned(cpu, child);
    }
    cpu.eflags = sourceCommonFlags(cpu.eax);
    if (!cpu.eax)
        goto firstError;
    cpu.ecx = run.get(0x537880);
    cpu.eax = cpu.esi;
firstSlot:
    cpu.eax -= cpu.ecx;
    cpu.edx = run.get(0x537888);
    cpu.eax *= run.get(0x537890);
    sourceAdd(cpu, cpu.eax, cpu.edx);
    cpu.eax += cpu.edx;
    goto firstCheck;
firstError:
    cpu.edi = run.get(0x544b4c);
    {
        auto child = sourceChild(run, cpu, 0x4db5f0, 0x44c8a0);
        run.source_call(0x4db5f0, 0, 0x44c8a0, child);
        sourceReturned(cpu, child);
    }
    cpu.ecx = run.get(0x53787c);
    sourcePush(run, cpu, 0xc);
    sourcePush(run, cpu, cpu.edi);
    sourcePush(run, cpu, 0x537878);
    run.put(0x544b14, cpu.eax);
    {
        auto child = sourceChild(run, cpu, 0x4db4d0, 0x44c8b8);
        run.source_call(0x4db4d0, cpu.ecx, 0x44c8b8, child, {0x537878, cpu.edi, 0xc}, 0, 0xc);
        sourceReturned(cpu, child);
    }
    cpu.eax = run.get(0x53788c);
    cpu.ecx = run.get(0x537880);
firstCheck:
    sourceCompare(cpu, run.get(cpu.eax), 0);
    if (run.get(cpu.eax) == 0)
        goto fallback;
    sourceCompare(cpu, cpu.esi, cpu.ecx);
    run.put(0x537898, 0);
    if (s32(cpu.esi) < s32(cpu.ecx))
        goto secondGrow;
    sourceCompare(cpu, cpu.esi, run.get(0x537884));
    if (s32(cpu.esi) <= s32(run.get(0x537884)))
        goto secondSlot;
secondGrow:
    sourcePush(run, cpu, 0);
    sourcePush(run, cpu, cpu.esi);
    cpu.ecx = 0x537878;
    {
        auto child = sourceChild(run, cpu, 0x4db6e0, 0x44c8eb);
        run.source_call(0x4db6e0, cpu.ecx, 0x44c8eb, child, {cpu.esi, 0}, 0, 0x8);
        sourceReturned(cpu, child);
    }
    cpu.eflags = sourceCommonFlags(cpu.eax);
    if (!cpu.eax)
        goto secondError;
    cpu.ecx = run.get(0x537880);
secondSlot:
    cpu.esi -= cpu.ecx;
    cpu.eax = run.get(0x537888);
    cpu.esi *= run.get(0x537890);
    sourceAdd(cpu, cpu.esi, cpu.eax);
    cpu.esi += cpu.eax;
    cpu.ecx = cpu.ebp;
    {
        uint32_t target = run.get(cpu.esi);
        auto child = sourceChild(run, cpu, target, 0x44c909);
        run.source_call(target, cpu.ecx, 0x44c909, child);
        sourceReturned(cpu, child);
    }
    goto restore;
secondError:
    cpu.esi = run.get(0x544b4c);
    {
        auto child = sourceChild(run, cpu, 0x4db5f0, 0x44c91a);
        run.source_call(0x4db5f0, 0, 0x44c91a, child);
        sourceReturned(cpu, child);
    }
    cpu.ecx = run.get(0x53787c);
    sourcePush(run, cpu, 0xc);
    sourcePush(run, cpu, cpu.esi);
    sourcePush(run, cpu, 0x537878);
    run.put(0x544b14, cpu.eax);
    {
        auto child = sourceChild(run, cpu, 0x4db4d0, 0x44c932);
        run.source_call(0x4db4d0, cpu.ecx, 0x44c932, child, {0x537878, cpu.esi, 0xc}, 0, 0xc);
        sourceReturned(cpu, child);
    }
    cpu.esi = run.get(0x53788c);
    cpu.ecx = cpu.ebp;
    {
        uint32_t target = run.get(cpu.esi);
        auto child = sourceChild(run, cpu, target, 0x44c93c);
        run.source_call(target, cpu.ecx, 0x44c93c, child);
        sourceReturned(cpu, child);
    }
    goto restore;
fallback:
    sourcePush(run, cpu, cpu.esi);
    cpu.ecx = cpu.ebp;
    {
        auto child = sourceChild(run, cpu, 0x43d490, 0x44c94a);
        run.source_call(0x43d490, cpu.ecx, 0x44c94a, child, {cpu.esi}, 0, 0x4);
        sourceReturned(cpu, child);
    }
restore:
    cpu.edi = run.get(cpu.esp);
    cpu.esp += 0x4;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 0x4;
    cpu.ebp = run.get(cpu.esp);
    cpu.esp += 0x4;
    return cpu.eax;
}

uint32_t sourceBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    if (function == 0x44c840)
        return sourceDispatch(run);
    return body(run, function, receiver, arguments);
}

} // namespace

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_level_one_object_actions_01_entry, owned, sourceContract, optionalSource, body, sourceBody)
