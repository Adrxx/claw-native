// Font lookup measurement and clipped text drawing tail
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4df6c0:
        return 0;
    case 0x4df6d0:
        return 1;
    case 0x4df6e0:
        return 1;
    case 0x4df6f0:
        return 5;
    case 0x4df7d0:
        return 9;
    case 0x4dfde0:
        return 2;
    case 0x4dfee0:
        return 1;
    case 0x4dff00:
        return 2;
    case 0x4dff30:
        return 0;
    default:
        return -1;
    }
}

// Guest addresses of stack objects are part of the CString boundary.
struct Frame {
    Run &run;
    uint32_t saved;
    Frame(Run &run, uint32_t entry) : run(run), saved(run.frame) {run.frame = entry;}
    ~Frame() {run.frame = saved;}
};

// 0x4dfee0: return the glyph-pointer SLOT, not its contents.
uint32_t glyphSlot(Run &run, uint32_t font, uint32_t character) {
    return run.get(font + 0x8) + (character & 0xffu) * 4;
}

// 0x4dff00: copy width/height in original order, allowing output aliasing.
uint32_t glyphExtent(Run &run, uint32_t font, uint32_t out, uint32_t character) {
    uint32_t table = run.get(font + 0xc);
    uint32_t slot = table + (character & 0xffu) * 8;
    uint32_t width = run.get(slot);
    run.put(out, width);
    uint32_t height = run.get(slot + 0x4);
    run.put(out + 0x4, height);
    return out;
}

// 0x4dff30: signed count and signed maximum, initially zero.
uint32_t maximumHeight(Run &run, uint32_t font) {
    uint32_t count = run.get(font + 0x4);
    uint32_t maximum = 0;
    if (s32(count) > 0) {
        uint32_t slot = run.get(font + 0xc) + 4;
        do {
            uint32_t height = run.get(slot);
            if (s32(maximum) <= s32(height)) maximum = height;
            slot += 8;
            --count;
        } while (count != 0);
    }
    return maximum;
}

// 0x4dfde0: the by-value CString is destroyed after publishing the result.
uint32_t measureText(Run &run, uint32_t painter, uint32_t out, uint32_t text) {
    run.put(run.automatic(8), text);
    uint32_t width = 0;
    uint32_t height = 0;
    if (run.get(painter) != 0) {
        uint32_t index = 0;
        while (s32(index) < run.gets(text - 8)) {
            uint32_t extent = glyphExtent(run, run.get(painter), run.automatic(-0x24), run.get8(text + index));
            width += run.get(extent);
            extent = glyphExtent(run, run.get(painter), run.automatic(-0x1c), run.get8(text + index));
            if (s32(height) <= run.gets(extent + 0x4)) {
                extent = glyphExtent(run, run.get(painter), run.automatic(-0x14), run.get8(text + index));
                height = run.get(extent + 0x4);
            }
            ++index;
        }
    }
    run.put(out, width);
    run.put(out + 0x4, height);
    run.call(0x4f6584, run.automatic(8));
    return out;
}

uint8_t shrByte(uint8_t value, uint32_t shift) {
    return uint8_t(uint32_t(value) >> (shift & 31));
}
uint8_t shlByte(uint8_t value, uint32_t shift) {
    return uint8_t(uint32_t(value) << (shift & 31));
}

// 0x4df7d0: clipping is in glyph-mask coordinates; destination is independent.
uint32_t drawClippedText(Run &run, uint32_t painter, const uint32_t *arguments) {
    const uint32_t entry = run.frame;
    for (uint32_t index = 0; index < 9; ++index) {
        run.put(entry + 4 + index * 4, arguments[index]);
    }
    const uint32_t text = arguments[0];
    if (run.get(painter) != 0) {
        run.call(0x4f6449, entry - 0xac, {entry + 4});
        {
            Frame frame(run, entry - 0xb4);
            measureText(run, painter, entry - 0x8c, run.get(entry - 0xac));
        }
        run.put(entry - 0x24, run.get(entry - 0x8c));
        run.put(entry - 0x20, run.get(entry - 0x88));
        run.put(entry - 0x2c, 0);
        run.put(entry - 0x28, 0);
        if (run.icall(0x546ce0, {entry + 12, entry + 12, entry - 0x2c}) != 0) {
            if (run.gets(entry + 20) > run.gets(entry - 0x8c)) {
                run.put(entry + 20, run.get(entry - 0x8c));
            }
            if (run.gets(entry + 24) > run.gets(entry - 0x88)) {
                run.put(entry + 24, run.get(entry - 0x88));
            }
            uint32_t surface = run.get(entry + 8);
            uint32_t pixels = run.call(0x4b9730, surface, {0});
            uint32_t pitch = run.get(surface + 0x1c);
            if (pixels != 0) {
                uint32_t destinationX = run.get(entry + 28);
                uint8_t sourceRed = run.get8(painter + 0x4);
                uint8_t sourceGreen = run.get8(painter + 0x5);
                uint8_t sourceBlue = uint8_t(run.get(painter + 0x4) >> 16);
                uint32_t redDestination = run.get(0x54135c);
                uint32_t greenDestination = run.get(0x541360);
                uint8_t red = shrByte(sourceRed, run.get8(0x541368));
                uint8_t green = shrByte(sourceGreen, run.get8(0x54136c));
                uint8_t low = uint8_t(shlByte(red, redDestination) | shlByte(green, greenDestination) |
                                      shrByte(sourceBlue, run.get8(0x541370)));
                uint8_t high = uint8_t(((uint32_t(red) << (redDestination & 31)) >> 8) |
                                       ((uint32_t(green) << (greenDestination & 31)) >> 8));
                uint32_t first = 0;
                uint32_t leftCrop = 0;
                uint32_t left = run.get(entry + 12);
                if (left != 0) {
                    uint32_t sum = 0;
                    uint32_t previous = 0;
                    if (s32(left) > 0) {
                        do {
                            previous = sum;
                            uint32_t extent = glyphExtent(run, run.get(painter), entry - 0x14, run.get8(text + first));
                            sum += run.get(extent);
                            ++first;
                        } while (s32(sum) < s32(left));
                    }
                    --first;
                    leftCrop = left - previous;
                }
                uint32_t last;
                uint32_t rightCrop = 0;
                uint32_t right = run.get(entry + 20);
                if (right == run.get(entry - 0x8c)) {
                    last = run.get(text - 8);
                } else {
                    uint32_t sum = 0;
                    last = 0;
                    if (s32(right) >= 0) {
                        do {
                            uint32_t extent = glyphExtent(run, run.get(painter), entry - 0x1c, run.get8(text + last));
                            sum += run.get(extent);
                            ++last;
                        } while (s32(sum) <= s32(right));
                    }
                    rightCrop = sum - right;
                }
                for (uint32_t index = first; s32(index) < s32(last); ++index) {
                    uint32_t extent = glyphExtent(run, run.get(painter), entry - 0x2c, run.get8(text + index));
                    uint32_t width = run.get(extent);
                    run.put(entry - 0x8c, width);
                    run.put(entry - 0x88, run.get(extent + 0x4));
                    uint32_t limit = width;
                    if (index == last - 1) limit -= rightCrop;
                    uint32_t mask = run.get(glyphSlot(run, run.get(painter), run.get8(text + index)));
                    uint32_t top = run.get(entry + 16);
                    for (uint32_t row = top; s32(row) < run.gets(entry + 24); ++row) {
                        uint32_t destination = pixels + (run.get(entry + 32) + row - top) * pitch + destinationX * 2;
                        for (uint32_t column = leftCrop; s32(column) < s32(limit); ++column) {
                            uint8_t alpha = run.get8(mask + row * width + column);
                            if (alpha != 0) {
                                if (run.get(entry + 36) == 0 || alpha == 255) {
                                    run.put8(destination, low);
                                    run.put8(destination + 0x1, high);
                                } else {
                                    uint16_t old = uint16_t(run.get8(destination)) | uint16_t(uint16_t(run.get8(destination + 0x1)) << 8);
                                    uint32_t inverse = 255u - alpha;
                                    uint32_t redShift = run.get16(0x54135c) & 31;
                                    uint32_t greenShift = run.get16(0x541360) & 31;
                                    uint8_t oldRed = shlByte(uint8_t(uint32_t(old) >> redShift), run.get(0x541368));
                                    uint8_t oldGreen = shlByte(uint8_t(uint32_t(old) >> greenShift), run.get(0x54136c));
                                    uint8_t blendedGreen = uint8_t(uint32_t(sourceGreen) * alpha / 255u + uint32_t(oldGreen) * inverse / 255u);
                                    uint16_t packed = uint16_t(uint32_t(shrByte(blendedGreen, run.get8(0x54136c))) << (run.get(0x541360) & 31));
                                    uint8_t blendedRed = uint8_t(uint32_t(sourceRed) * alpha / 255u + uint32_t(oldRed) * inverse / 255u);
                                    packed = uint16_t(packed | uint16_t(uint32_t(shrByte(blendedRed, run.get8(0x541368))) << (run.get(0x54135c) & 31)));
                                    uint8_t oldBlue = shlByte(uint8_t(old), run.get(0x541370));
                                    uint8_t blendedBlue = uint8_t(uint32_t(oldBlue) * inverse / 255u + uint32_t(sourceBlue) * alpha / 255u);
                                    uint8_t blue = shrByte(blendedBlue, run.get(0x541370));
                                    run.put8(destination, uint8_t(packed) | blue);
                                    run.put8(destination + 0x1, uint8_t(packed >> 8));
                                }
                            }
                            destination += 2;
                        }
                    }
                    destinationX += limit - leftCrop;
                    leftCrop = 0;
                }
                uint32_t com = run.get(run.get(entry + 8) + 0x8);
                run.call(run.get(run.get(com) + 0x80), 0, {com, 0});
            }
        }
    }
    run.call(0x4f6584, entry + 4);
    return 0;
}

// 0x4df6f0: measure first, then enforce the surface's bottom boundary.
uint32_t drawText(Run &run, uint32_t painter, const uint32_t *arguments) {
    const uint32_t entry = run.frame;
    run.put(entry + 4, arguments[0]);
    run.call(0x4f6449, entry - 0x34, {entry + 4});
    {
        Frame frame(run, entry - 0x3c);
        measureText(run, painter, entry - 0x24, run.get(entry - 0x34));
    }
    uint32_t font = run.get(painter);
    if (font != 0) {
        uint32_t surface = arguments[1];
        uint32_t surfaceHeight = run.get(surface + 0x14);
        uint32_t height = maximumHeight(run, font);
        if (s32(height + arguments[3]) <= s32(surfaceHeight)) {
            uint32_t rect = run.call(0x4dfec0, entry - 0x1c, {0, 0, run.get(entry - 0x24), run.get(entry - 0x20)});
            uint32_t left = run.get(rect);
            uint32_t top = run.get(rect + 0x4);
            uint32_t right = run.get(rect + 0x8);
            uint32_t bottom = run.get(rect + 0xc);
            run.call(0x4f6449, entry - 0x54, {entry + 4});
            uint32_t nested[] = {run.get(entry - 0x54), surface, left, top, right, bottom, arguments[2], arguments[3], arguments[4]};
            Frame frame(run, entry - 0x58);
            drawClippedText(run, painter, nested);
        }
    }
    run.call(0x4f6584, entry + 4);
    return 0;
}

uint32_t function_4df6c0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0);
    run.put(receiver + 0x4, 0x00ffffff);
    return 0;
}
uint32_t function_4df6d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver, arguments[0]);
    return 0;
}
uint32_t function_4df6e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x4, arguments[0]);
    return 0;
}
uint32_t function_4df6f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return drawText(run, receiver, arguments);
}
uint32_t function_4df7d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return drawClippedText(run, receiver, arguments);
}
uint32_t function_4dfde0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return measureText(run, receiver, arguments[0], arguments[1]);
}
uint32_t function_4dfee0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return glyphSlot(run, receiver, arguments[0]);
}
uint32_t function_4dff00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return glyphExtent(run, receiver, arguments[0], arguments[1]);
}
uint32_t function_4dff30(Run &run, uint32_t receiver, const uint32_t *) {
    return maximumHeight(run, receiver);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4df6c0:
        return function_4df6c0(run, receiver, arguments);
    case 0x4df6d0:
        return function_4df6d0(run, receiver, arguments);
    case 0x4df6e0:
        return function_4df6e0(run, receiver, arguments);
    case 0x4df6f0:
        return function_4df6f0(run, receiver, arguments);
    case 0x4df7d0:
        return function_4df7d0(run, receiver, arguments);
    case 0x4dfde0:
        return function_4dfde0(run, receiver, arguments);
    case 0x4dfee0:
        return function_4dfee0(run, receiver, arguments);
    case 0x4dff00:
        return function_4dff00(run, receiver, arguments);
    case 0x4dff30:
        return function_4dff30(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_call_closure_text_tail_entry, owned, body)
