#include "NativeIndexedPresentation.h"
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <vector>

void claw_native_indexed_image_dispose(ClawNativeIndexedImage *image) {
    if (!image)
        return;
    std::free(image->rgba);
    *image = {};
}

static uint32_t present(const uint8_t *indices, const uint8_t *coverage, size_t stride, const uint8_t *paletteRGB,
                        uint32_t width, uint32_t height, ClawNativeIndexedImage *result) {
    uint32_t left = width, top = height, right = 0, bottom = 0;
    bool visible = false;
    for (uint32_t y = 0; y < height; ++y) {
        const uint8_t *row = coverage + size_t(y) * stride;
        uint32_t x = 0;
        // Zero groups dominate a viewport containing a small sprite. memcpy
        // permits unaligned rows without aliasing or overreading padding.
        for (; x + 8 <= width; x += 8) {
            uint64_t group;
            std::memcpy(&group, row + x, 8);
            if (!group)
                continue;
            for (uint32_t i = 0; i < 8; ++i)
                if (row[x + i]) {
                    const uint32_t column = x + i;
                    if (column < left)
                        left = column;
                    if (column > right)
                        right = column;
                    if (y < top)
                        top = y;
                    bottom = y;
                    visible = true;
                }
        }
        for (; x < width; ++x)
            if (row[x]) {
                if (x < left)
                    left = x;
                if (x > right)
                    right = x;
                if (y < top)
                    top = y;
                bottom = y;
                visible = true;
            }
    }
    if (!visible) {
        return 0;
    }
    const uint32_t cropWidth = right - left + 1, cropHeight = bottom - top + 1;
    const size_t bytes = size_t(cropWidth) * cropHeight * 4;
    auto *rgba = static_cast<uint8_t *>(std::calloc(bytes, 1));
    if (!rgba) {
        return 0;
    }
    uint8_t colors[256][4];
    for (unsigned i = 0; i < 256; ++i) {
        std::memcpy(colors[i], paletteRGB + i * 3, 3);
        colors[i][3] = 255;
    }
    for (uint32_t y = top; y <= bottom; ++y) {
        const uint8_t *mask = coverage + size_t(y) * stride + left;
        const uint8_t *source = indices + size_t(y) * stride + left;
        uint8_t *destination = rgba + size_t(y - top) * cropWidth * 4;
        for (uint32_t x = 0; x < cropWidth; ++x)
            if (mask[x])
                std::memcpy(destination + size_t(x) * 4, colors[source[x]], 4);
    }
    *result = {rgba, bytes, left, top, cropWidth, cropHeight};
    return 1;
}

uint32_t claw_native_indexed_present8(const uint8_t *pid, size_t length, const ClawPIDBlitCommand *command,
                                      const uint8_t *paletteRGB, size_t paletteLength, uint32_t width, uint32_t height,
                                      ClawNativeIndexedImage *result) {
    if (!result)
        return 0;
    *result = {};
    if (!pid || !command || !paletteRGB || paletteLength != 768 || !width || !height || width > 8192 || height > 8192)
        return 0;
    const size_t stride = (width + 3u) & ~size_t(3);
    const size_t capacity = stride * height;
    auto *indices = static_cast<uint8_t *>(std::calloc(capacity, 1));
    auto *coverage = static_cast<uint8_t *>(std::calloc(capacity, 1));
    if (!indices || !coverage) {
        std::free(indices);
        std::free(coverage);
        return 0;
    }
    if (claw_pid_blit8(pid, length, command, indices, coverage, capacity, stride, nullptr) != 1) {
        std::free(indices);
        std::free(coverage);
        return 0;
    }
    const uint32_t accepted = present(indices, coverage, stride, paletteRGB, width, height, result);
    std::free(indices);
    std::free(coverage);
    return accepted;
}

uint32_t claw_native_indexed_composite8(const uint8_t *pid, size_t length, const ClawPIDBlitCommand *command,
                                        const ClawLightPIDBlitState *state, const ClawLightPIDBlitTable *table,
                                        uint8_t *indices, uint8_t *coverage, size_t capacity, size_t stride,
                                        uint8_t *scratch, size_t scratchCapacity, const uint8_t *paletteRGB,
                                        size_t paletteLength, uint32_t width, uint32_t height,
                                        ClawLightPIDBlitInfo *info, ClawNativeIndexedImage *result) {
    if (!result)
        return 0;
    *result = {};
    if (!width || !height || width > 8192 || height > 8192 || stride < width || capacity < stride * height ||
        !coverage || !indices || !paletteRGB || paletteLength != 768)
        return 0;
    std::memset(coverage, 0, capacity);
    if (claw_effect_pid_blit8(pid, length, command, state, table, indices, coverage, capacity, stride, scratch,
                              scratchCapacity, info) != 1)
        return 0;
    return present(indices, coverage, stride, paletteRGB, width, height, result);
}

uint32_t claw_native_indexed_surface8(const uint8_t *source, size_t sourceCapacity, uint32_t sourceWidth,
                                      uint32_t sourceHeight, const ClawPIDBlitCommand *command, uint32_t keyEnabled,
                                      uint8_t *indices, size_t capacity, size_t stride, uint32_t width,
                                      uint32_t height) {
    if (!source || !indices || !command || stride < width || capacity < stride * height ||
        uint64_t(sourceWidth) * sourceHeight > sourceCapacity)
        return 0;
    const auto &s = command->source, &d = command->destination;
    const int64_t w = int64_t(s.right) - s.left, h = int64_t(s.bottom) - s.top;
    if (s.left < 0 || s.top < 0 || w <= 0 || h <= 0 || s.right > int64_t(sourceWidth) ||
        s.bottom > int64_t(sourceHeight))
        return 0;
    const int64_t x0 = std::max<int64_t>(0, -int64_t(d.left)), y0 = std::max<int64_t>(0, -int64_t(d.top));
    const int64_t x1 = std::min<int64_t>(w, int64_t(width) - d.left),
                  y1 = std::min<int64_t>(h, int64_t(height) - d.top);
    for (int64_t y = y0; y < y1; ++y)
        for (int64_t x = x0; x < x1; ++x) {
            const int64_t sx = s.left + (command->flipX ? w - 1 - x : x), sy = s.top + (command->flipY ? h - 1 - y : y);
            const uint8_t value = source[size_t(sy) * sourceWidth + size_t(sx)];
            if (!keyEnabled || value)
                indices[size_t(int64_t(d.top) + y) * stride + size_t(int64_t(d.left) + x)] = value;
        }
    return 1;
}

uint32_t claw_native_indexed_fill8(const ClawPIDBlitRect *rectangle, uint32_t color, uint8_t *indices, size_t capacity,
                                   size_t stride, uint32_t width, uint32_t height) {
    if (!rectangle || !indices || stride < width || capacity < stride * height)
        return 0;
    const int64_t left = std::max<int64_t>(0, rectangle->left), top = std::max<int64_t>(0, rectangle->top);
    const int64_t right = std::min<int64_t>(width, rectangle->right),
                  bottom = std::min<int64_t>(height, rectangle->bottom);
    if (left >= right || top >= bottom)
        return 1;
    for (int64_t y = top; y < bottom; ++y)
        std::memset(indices + size_t(y) * stride + size_t(left), uint8_t(color), size_t(right - left));
    return 1;
}

uint32_t claw_native_indexed_frame_present8(const uint8_t *indices, size_t capacity, size_t stride,
                                            const uint8_t *paletteRGB, size_t paletteLength, uint32_t width,
                                            uint32_t height, ClawNativeIndexedImage *result) {
    if (!result)
        return 0;
    *result = {};
    if (!indices || !paletteRGB || paletteLength != 768 || !width || !height || width > 8192 || height > 8192 ||
        stride < width || stride > SIZE_MAX / height || capacity < stride * height)
        return 0;
    std::vector<uint8_t> mask(stride * height, 1);
    return present(indices, mask.data(), stride, paletteRGB, width, height, result);
}
