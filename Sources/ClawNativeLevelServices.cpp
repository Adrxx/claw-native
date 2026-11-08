#include "ClawNativeLevelServices.h"
#include <zlib.h>
#include <cstring>
#include <vector>

uint32_t claw_level_rand(uint32_t *state) {
    *state = *state * 214013u + 2531011u;
    return (*state >> 16) & 0x7fffu;
}

uint32_t claw_level_ctype(uint32_t function, uint32_t value, uint32_t *result) {
    uint32_t mask;
    switch (function) {
    case 0x4b0d30u: mask = 4; break;
    case 0x4b0d60u: mask = 8; break;
    case 0x4b0d90u: mask = 0x157; break;
    default: return 0;
    }
    if (value != 0xffffffffu && value > 127) return 0;
    uint32_t bits = 0;
    if (value >= 65 && value <= 90) bits = 0x101;
    else if (value >= 97 && value <= 122) bits = 0x102;
    else if (value >= 48 && value <= 57) bits = 4;
    else if (value >= 33 && value <= 126) bits = 0x10;
    else if (value == 32) bits = 0x48;
    else if (value >= 9 && value <= 13) bits = 8;
    *result = bits & mask;
    return 1;
}

void claw_level_inflate_rect(uint32_t rect[4], uint32_t left, uint32_t top, uint32_t right, uint32_t bottom) {
    rect[0] -= left; rect[1] -= top; rect[2] += right; rect[3] += bottom;
}

uint32_t claw_level_uncompress(uint8_t *destination, uint32_t capacity, const uint8_t *source,
                               uint32_t available, uint32_t *written) {
    z_stream stream;
    std::memset(&stream, 0, sizeof(stream));
    if (inflateInit(&stream) != Z_OK) return 0xfffffffdu;
    stream.next_in = const_cast<Bytef *>(source); stream.avail_in = available;
    // Decode into private storage: a data error leaves the destination untouched.
    std::vector<uint8_t> output(capacity ? capacity : 1);
    stream.next_out = output.data(); stream.avail_out = capacity;
    int status = Z_OK;
    // Run until the stream ends, the output is full or the input is exhausted.
    while (status == Z_OK && stream.avail_out && stream.avail_in) status = inflate(&stream, Z_NO_FLUSH);
    if (status == Z_OK && stream.avail_in == 0) status = inflate(&stream, Z_NO_FLUSH);
    uint32_t produced = capacity - stream.avail_out;
    inflateEnd(&stream);
    if (status != Z_STREAM_END && status != Z_OK && status != Z_BUF_ERROR) return 0xfffffffdu;
    if (produced) std::memcpy(destination, output.data(), produced);
    *written = produced;
    return status == Z_STREAM_END ? 0 : 0xfffffffbu;
}

uint32_t claw_level_adjacent_sort(uint8_t *base, uint32_t count, ClawLevelCompare compare, void *context,
                                  uint32_t *comparisons, uint32_t *swaps) {
    *comparisons = 0; *swaps = 0;
    for (uint32_t i = 1; i < count; ++i) {
        for (uint32_t j = i; j > 0; --j) {
            uint32_t value = 0;
            if (!compare(context, j - 1, j, &value)) return 0;
            ++*comparisons;
            if (!(value > 0 && value < 0x80000000u)) break;
            uint8_t t = base[j - 1]; base[j - 1] = base[j]; base[j] = t;
            ++*swaps;
        }
    }
    return 1;
}
