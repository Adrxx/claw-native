// Level 1 closure: player fade helpers and fade blend
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"
#include <cmath>

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4ec720:
        return 1;
    case 0x4ec900:
        return 1;
    case 0x4ecc30:
        return 0;
    case 0x4ecc60:
        return 0;
    case 0x4ecc90:
        return 1;
    case 0x4eccb0:
        return 0;
    case 0x4ecd00:
        return 1;
    case 0x4ecef0:
        return 0;
    case 0x4ecf10:
        return 1;
    case 0x423f10:
        return 1;
    case 0x4c7650:
        return 0;
    case 0x4c76b0:
        return 1;
    default:
        return -1;
    }
}

constexpr uint32_t OPERATOR_NEW = 0x4f63ec;
constexpr uint32_t OPERATOR_DELETE = 0x4f6428;
constexpr uint32_t FTOL = 0x4a30e0;

// Constants in the program's data: float 0x514208, double 0x514210, double
// 0x514218, float 0x514220, float 0x514224.

uint32_t allocate(Run &run, uint32_t size) {
    return run.call(OPERATOR_NEW, 0, {size});
}

void release(Run &run, uint32_t pointer) {
    run.call(OPERATOR_DELETE, 0, {pointer});
}

// Converts a binary64 value to the extended-precision encoding of an x87 register.
ClawX87Value extended(double value) {
    ClawX87Value result{};
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    uint32_t sign = uint32_t(bits >> 63) << 15;
    uint32_t exponent = uint32_t((bits >> 52) & 0x7ff);
    uint64_t fraction = bits & 0xfffffffffffffull;
    if (exponent == 0x7ff) {
        result.significand = 0x8000000000000000ull | (fraction << 11);
        result.signExponent = sign | 0x7fff;
    } else if (exponent == 0) {
        if (fraction == 0) {
            result.significand = 0;
            result.signExponent = sign;
        } else {
            int shift = 0;
            while (!(fraction & 0x10000000000000ull)) {
                fraction <<= 1;
                ++shift;
            }
            result.significand = fraction << 11;
            result.signExponent = sign | uint32_t(16383 - 1022 - shift);
        }
    } else {
        result.significand = 0x8000000000000000ull | (fraction << 11);
        result.signExponent = sign | (exponent - 1023 + 16383);
    }
    return result;
}

// 0x4a30e0 truncates ST(0) to an integer and pops it; the caller only reads EAX.
// `live` lists the register stack from ST(0) downwards.
uint32_t truncate(Run &run, std::initializer_list<double> live) {
    ClawX87State state{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
    state.count = uint32_t(live.size());
    state.status = ((8u - state.count) & 7u) << 11;
    state.popCount = 1;
    state.pushCount = 0;
    uint32_t index = 0;
    for (double value : live)
        state.slots[index++] = extended(value);
    return run.call_x87_exact(FTOL, 0, state, {});
}

// Calls the Unlock method (vtable +0x80) of a DirectDraw surface interface.
void unlock(Run &run, uint32_t interface) {
    uint32_t table = run.get(interface);
    uint32_t method = run.get(table + 0x80);
    run.call(method, 0, {interface, 0});
}

// Zeroes `count` bytes the way rep stosd then rep stosb do.
void zeroBytes(Run &run, uint32_t address, uint32_t count) {
    uint32_t words = count >> 2;
    for (uint32_t i = 0; i < words; ++i)
        run.put(address + i * 4, 0);
    uint32_t tail = address + words * 4;
    for (uint32_t i = 0; i < (count & 3); ++i)
        run.put8(tail + i, 0);
}

// 0x4ec720. Array object fields: +4 data, +8 size, +0xc capacity, +0x10 grow
// step. Archive flags at +0x14, bit 0 set means loading.
uint32_t function_4ec720(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t array = receiver;
    uint32_t archive = arguments[0];
    uint32_t entry = run.frame;
    uint32_t flags = run.get(archive + 0x14);
    if ((~flags & 1) != 0) {
        uint32_t size = run.get(array + 0x08);
        run.stackPointer = entry - 0x20;
        run.call(0x4fde7f, archive, {size});
    } else {
        run.stackPointer = entry - 0x1c;
        uint32_t count = run.call(0x4fdead, archive, {});
        if (count == 0) {
            uint32_t data = run.get(array + 0x04);
            if (data != 0) {
                run.stackPointer = entry - 0x20;
                release(run, data);
                run.put(array + 0x04, 0);
            }
            run.put(array + 0x0c, 0);
            run.put(array + 0x08, 0);
        } else {
            uint32_t data = run.get(array + 0x04);
            if (data == 0) {
                uint32_t bytes = count * 4;
                run.stackPointer = entry - 0x20;
                uint32_t block = allocate(run, bytes);
                run.put(array + 0x04, block);
                zeroBytes(run, block, bytes);
                run.put(array + 0x0c, count);
                run.put(array + 0x08, count);
            } else {
                uint32_t capacity = run.get(array + 0x0c);
                if (s32(count) <= s32(capacity)) {
                    uint32_t size = run.get(array + 0x08);
                    if (s32(count) > s32(size)) {
                        uint32_t from = data + size * 4;
                        uint32_t words = count - size;
                        for (uint32_t i = 0; i != words; ++i)
                            run.put(from + i * 4, 0);
                    }
                    run.put(array + 0x08, count);
                } else {
                    uint32_t step = run.get(array + 0x10);
                    if (step == 0) {
                        uint32_t size = run.get(array + 0x08);
                        uint32_t bias = uint32_t(s32(size) >> 31) & 7u;
                        step = uint32_t(s32(size + bias) >> 3);
                        if (s32(step) < 4)
                            step = 4;
                        else if (s32(step) > 0x400)
                            step = 0x400;
                    }
                    uint32_t newCapacity = step + capacity;
                    if (!(s32(count) < s32(newCapacity)))
                        newCapacity = count;
                    run.stackPointer = entry - 0x20;
                    uint32_t block = allocate(run, newCapacity * 4);
                    uint32_t size = run.get(array + 0x08);
                    uint32_t source = run.get(array + 0x04);
                    uint32_t bytes = size << 2;
                    uint32_t words = bytes >> 2;
                    for (uint32_t i = 0; i < words; ++i) {
                        uint32_t word = run.get(source + i * 4);
                        run.put(block + i * 4, word);
                    }
                    uint32_t tail = bytes & 3;
                    for (uint32_t i = 0; i < tail; ++i) {
                        uint32_t value = run.get8(source + words * 4 + i);
                        run.put8(block + words * 4 + i, uint8_t(value));
                    }
                    size = run.get(array + 0x08);
                    uint32_t fill = block + size * 4;
                    uint32_t fillCount = count - size;
                    for (uint32_t i = 0; i != fillCount; ++i)
                        run.put(fill + i * 4, 0);
                    uint32_t old = run.get(array + 0x04);
                    run.stackPointer = entry - 0x20;
                    release(run, old);
                    run.put(array + 0x04, block);
                    run.put(array + 0x08, count);
                    run.put(array + 0x0c, newCapacity);
                }
            }
        }
    }
    uint32_t endFlags = run.get(archive + 0x14);
    uint32_t endSize = run.get(array + 0x08);
    uint32_t endData = run.get(array + 0x04);
    run.stackPointer = entry - 0x24;
    if ((~endFlags & 1) != 0)
        run.call(0x4fdcb3, archive, {endData, endSize << 2});
    else
        run.call(0x4fdba5, archive, {endData, endSize * 4});
    return 0;
}

// 0x4ec900. Array destructor body, then delete when bit 0 of the flag is set.
uint32_t function_4ec900(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t entry = run.frame;
    run.stackPointer = entry - 0x08;
    run.call(0x4ec920, receiver, {});
    run.stackPointer = entry - 0x0c;
    if ((arguments[0] & 1) != 0)
        release(run, receiver);
    return receiver;
}

// 0x4ecc30. Array constructor.
uint32_t function_4ecc30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.stackPointer = run.frame - 0x08;
    run.call(0x4ecb30, receiver, {});
    run.put(receiver + 0x00, 4);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x0c, 1);
    return receiver;
}

// 0x4ecc60. Fade constructor. +0x40 and +0x44 list fields, +0x48 flag, +0x50 records.
uint32_t function_4ecc60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.stackPointer = run.frame - 0x08;
    run.call(0x4ec8d0, receiver, {});
    run.put(receiver + 0x00, 0x5141f0);
    run.put(receiver + 0x44, 0);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x48, 1);
    return receiver;
}

void destroyFade(Run &run, uint32_t receiver, uint32_t entry);

// 0x4ecc90. Fade deleting destructor.
uint32_t function_4ecc90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t entry = run.frame;
    destroyFade(run, receiver, entry - 0x08);
    run.stackPointer = entry - 0x0c;
    if ((arguments[0] & 1) != 0)
        release(run, receiver);
    return receiver;
}

void freeRecords(Run &run, uint32_t receiver, uint32_t entry) {
    uint32_t records = run.get(receiver + 0x50);
    if (records != 0) {
        run.stackPointer = entry - 0x08;
        release(run, records);
    }
}

// Body of 0x4eccb0 entered with the return word at `entry`: restores the vtable,
// frees the records, runs the list destructor.
void destroyFade(Run &run, uint32_t receiver, uint32_t entry) {
    run.put(receiver + 0x00, 0x5141f0);
    freeRecords(run, receiver, entry - 0x18);
    run.stackPointer = entry - 0x18;
    run.call(0x4ec920, receiver, {});
}

// 0x4eccb0.
uint32_t function_4eccb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    destroyFade(run, receiver, run.frame);
    return 0;
}

// 0x4ecd00. Sets up the fade from an argument block. Fade fields: +0x1c item,
// +0x24 and +0x28 default destination and source, +0x30 owns item, +0x38 source
// surface, +0x3c destination surface, +0x44 radius, +0x4c scale, +0x50 records
// (16 bytes each), +0x54 and +0x58 centre. Surface: +8 interface, +0x14 height,
// +0x18 width, +0x1c pitch.
uint32_t function_4ecd00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    uint32_t block = arguments[0];
    uint32_t destination = run.get(block + 0x04);
    if (destination == 0)
        destination = run.get(self + 0x24);
    run.put(self + 0x3c, destination);
    uint32_t source = run.get(block + 0x08);
    if (source == 0) {
        uint32_t fallback = run.get(self + 0x28);
        run.put(self + 0x38, fallback);
    } else {
        run.put(self + 0x38, source);
    }
    uint32_t item = run.get(block + 0x14);
    if (item == 0) {
        uint32_t holder = run.get(block + 0x10);
        uint32_t text = run.get(holder + 0x0c);
        run.stackPointer = run.frame - 0x38;
        uint32_t made = run.call(0x4c6bd0, self + 4, {text, 0x10, 0});
        run.put(self + 0x1c, made);
        run.put(self + 0x30, 1);
    } else {
        run.put(self + 0x1c, item);
        run.put(self + 0x30, 0);
    }
    if (run.get(self + 0x1c) == 0)
        return 0;
    uint32_t surface = run.get(self + 0x38);
    int32_t widthInt = run.gets(surface + 0x18);
    float scaleFactor = run.getf(0x514208);
    double scaled = double(widthInt) * double(scaleFactor);
    run.putf(self + 0x4c, float(scaled));
    int32_t width = run.gets(surface + 0x18);
    run.put(self + 0x54, uint32_t(width / 2));
    int32_t height = run.gets(surface + 0x14);
    run.put(self + 0x58, uint32_t(height / 2));
    uint32_t cells = run.get(surface + 0x14);
    cells = cells * run.get(surface + 0x18);
    run.stackPointer = run.frame - 0x30;
    uint32_t records = allocate(run, cells << 4);
    run.put(self + 0x50, records);
    uint32_t halfHeight = run.get(self + 0x58);
    uint32_t halfWidth = run.get(self + 0x54);
    uint32_t squares = halfWidth * halfWidth;
    uint32_t squares2 = halfHeight * halfHeight;
    squares = squares + squares2;
    double root = std::sqrt(double(s32(squares)));
    double reach = root * run.getd(0x514210);
    run.stackPointer = run.frame - 0x2c;
    uint32_t radius = truncate(run, {reach});
    surface = run.get(self + 0x38);
    run.put(self + 0x44, radius);
    if (s32(run.get(surface + 0x14)) <= 0)
        return 1;
    uint32_t row = 0;
    for (;;) {
        uint32_t columns = run.get(surface + 0x18);
        uint32_t column = 0;
        if (s32(columns) > 0) {
            do {
                uint32_t halfW = run.get(self + 0x54);
                uint32_t offsetX = column - halfW;
                uint32_t halfH = run.get(self + 0x58);
                uint32_t offsetY = row - halfH;
                uint32_t flipped = halfH - row;
                uint32_t distance = offsetX * offsetX;
                uint32_t distance2 = offsetY * offsetY;
                distance = distance + distance2;
                double base = double(run.gets(self + 0x44));
                double length = std::sqrt(double(s32(distance)));
                double scaledLength = length * run.getd(0x514210);
                double depth = base - scaledLength;
                depth = depth - run.getd(0x514218);
                float depthStored = float(depth);
                double ratio = depth / double(run.getf(self + 0x4c));
                ratio = ratio - double(run.getf(0x514220));
                double projectedX = double(s32(offsetX)) * ratio;
                float xStored = float(projectedX);
                double projectedY = double(s32(flipped)) * ratio;
                float yStored = float(projectedY);
                run.stackPointer = run.frame - 0x30;
                uint32_t pixels = run.call(0x4b9730, surface, {0});
                uint32_t shade = 0;
                if (pixels != 0) {
                    uint32_t pitch = run.get(surface + 0x1c);
                    uint32_t interface = run.get(surface + 0x08);
                    uint32_t value = run.get8(pixels + pitch * row + column);
                    run.stackPointer = run.frame - 0x34;
                    unlock(run, interface);
                    shade = value;
                }
                uint32_t current = run.get(self + 0x38);
                uint32_t stride = run.get(current + 0x18);
                uint32_t table = run.get(self + 0x50);
                uint32_t record = ((stride * row + column) << 4) + table;
                run.putf(record + 0x00, xStored);
                run.putf(record + 0x04, yStored);
                run.putf(record + 0x08, depthStored);
                run.put(record + 0x0c, shade);
                column = column + 1;
                surface = run.get(self + 0x38);
            } while (s32(column) < s32(run.get(surface + 0x18)));
        }
        surface = run.get(self + 0x38);
        row = row + 1;
        if (!(s32(row) < s32(run.get(surface + 0x14))))
            break;
    }
    return 1;
}

// 0x4ecef0. Frees the record table when there is one.
uint32_t function_4ecef0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    freeRecords(run, receiver, run.frame);
    return 0;
}

// 0x4ecf10. Blends the fade records into the destination surface; the argument
// is an unsigned depth offset.
uint32_t function_4ecf10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    uint32_t offset = arguments[0];
    uint32_t destination = run.get(self + 0x3c);
    uint32_t bufferSize = run.get(destination + 0x18);
    uint32_t entry = run.frame;
    run.stackPointer = entry - 0x20;
    uint32_t buffer = allocate(run, bufferSize);
    destination = run.get(self + 0x3c);
    run.stackPointer = entry - 0x20;
    run.call(0x4b9bd0, destination, {0});
    uint32_t source = run.get(self + 0x38);
    run.stackPointer = entry - 0x20;
    run.call(0x4b9730, source, {0});
    destination = run.get(self + 0x3c);
    run.stackPointer = entry - 0x20;
    uint32_t pixels = run.call(0x4b9730, destination, {0});
    uint32_t item = run.get(self + 0x1c);
    if (run.get(item + 0x08) == 0)
        return 0;
    uint32_t sourceSurface = run.get(self + 0x38);
    uint32_t total = run.get(sourceSurface + 0x14);
    total = total * run.get(sourceSurface + 0x18);
    if (s32(total) > 0) {
        double base = double(offset);
        uint32_t index = 0;
        uint32_t byteOffset = 0;
        do {
            uint32_t table = run.get(self + 0x50);
            uint32_t record = byteOffset + table;
            double depth = double(run.getf(record + 0x08));
            depth = depth - base;
            if (depth > double(run.getf(0x514224))) {
                depth = depth / double(run.getf(self + 0x4c));
                double factor = depth - double(run.getf(0x514220));
                double quotientX = double(run.getf(record + 0x00)) / factor;
                run.stackPointer = entry - 0x24;
                uint32_t stepX = truncate(run, {quotientX, factor, base});
                double quotientY = double(run.getf(record + 0x04)) / factor;
                uint32_t column = stepX + run.get(self + 0x54);
                run.stackPointer = entry - 0x24;
                uint32_t stepY = truncate(run, {quotientY, factor, base});
                uint32_t row = run.get(self + 0x58) - stepY;
                if (s32(column) > 0) {
                    uint32_t target = run.get(self + 0x3c);
                    if (s32(column) < s32(run.get(target + 0x18))) {
                        if (s32(row) > 0) {
                            if (s32(row) < s32(run.get(target + 0x14))) {
                                uint32_t pitch = run.get(target + 0x1c);
                                uint32_t value = run.get8(record + 0x0c);
                                uint32_t position = pitch * row + column;
                                run.put8(position + pixels, uint8_t(value));
                            }
                        }
                    }
                }
            }
            sourceSurface = run.get(self + 0x38);
            index = index + 1;
            byteOffset = byteOffset + 0x10;
            total = run.get(sourceSurface + 0x14);
            total = total * run.get(sourceSurface + 0x18);
        } while (s32(index) < s32(total));
    }
    sourceSurface = run.get(self + 0x38);
    uint32_t sourceInterface = run.get(sourceSurface + 0x08);
    run.stackPointer = entry - 0x28;
    unlock(run, sourceInterface);
    destination = run.get(self + 0x3c);
    uint32_t destinationInterface = run.get(destination + 0x08);
    run.stackPointer = entry - 0x28;
    unlock(run, destinationInterface);
    run.stackPointer = entry - 0x24;
    release(run, buffer);
    return 0;
}

// 0x423f10. Base deleting destructor: sets the base vtable.
uint32_t function_423f10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x00, 0x50becc);
    run.stackPointer = run.frame - 0x0c;
    if ((arguments[0] & 1) != 0)
        release(run, receiver);
    return receiver;
}

void destroyBuffered(Run &run, uint32_t receiver, uint32_t entry) {
    run.put(receiver + 0x00, 0x5136e8);
    uint32_t buffer = run.get(receiver + 0x04);
    if (buffer != 0) {
        run.stackPointer = entry - 0x1c;
        release(run, buffer);
    }
    run.put(receiver + 0x00, 0x50becc);
}

// 0x4c7650. Frees the buffer at +4 and restores the base vtable.
uint32_t function_4c7650(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    destroyBuffered(run, receiver, run.frame);
    return 0;
}

// 0x4c76b0. Deleting destructor over 0x4c7650.
uint32_t function_4c76b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t entry = run.frame;
    destroyBuffered(run, receiver, entry - 0x08);
    run.stackPointer = entry - 0x0c;
    if ((arguments[0] & 1) != 0)
        release(run, receiver);
    return receiver;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4ec720:
        return function_4ec720(run, receiver, arguments);
    case 0x4ec900:
        return function_4ec900(run, receiver, arguments);
    case 0x4ecc30:
        return function_4ecc30(run, receiver, arguments);
    case 0x4ecc60:
        return function_4ecc60(run, receiver, arguments);
    case 0x4ecc90:
        return function_4ecc90(run, receiver, arguments);
    case 0x4eccb0:
        return function_4eccb0(run, receiver, arguments);
    case 0x4ecd00:
        return function_4ecd00(run, receiver, arguments);
    case 0x4ecef0:
        return function_4ecef0(run, receiver, arguments);
    case 0x4ecf10:
        return function_4ecf10(run, receiver, arguments);
    case 0x423f10:
        return function_423f10(run, receiver, arguments);
    case 0x4c7650:
        return function_4c7650(run, receiver, arguments);
    case 0x4c76b0:
        return function_4c76b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_scene_fade_closure_entry, owned, body)
