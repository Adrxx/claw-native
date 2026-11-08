#include "AnimationEngine.h"
#include <cstring>

extern "C" uint32_t claw_animation_decode_record(const uint8_t *bytes, uint32_t size, uint32_t resolvedEvent,
                                                 ClawAnimationRecord *record, uint32_t *nameLength) {
    if (!bytes || !record || !nameLength || size < 20)
        return 0;
    auto word = [&](uint32_t offset) {
        return uint32_t(bytes[offset]) | uint32_t(bytes[offset + 1]) << 8;
    };
    auto signedWord = [&](uint32_t offset) {
        const uint32_t value = word(offset);
        return value & 0x8000 ? value | 0xffff0000 : value;
    };
    uint32_t consumed = 20;
    *nameLength = 0;
    const uint32_t flags = word(0);
    if (flags & 2) {
        while (consumed < size && bytes[consumed])
            ++consumed;
        if (consumed == size)
            return 0;
        *nameLength = consumed - 20;
        ++consumed;
    }
    *record = {flags,          signedWord(2),  signedWord(4),  signedWord(6),  signedWord(8),
               signedWord(10), signedWord(12), signedWord(14), signedWord(16), flags & 2 ? resolvedEvent : 0};
    return consumed;
}

// Integer-by-binary32 multiply rounded to the original CRT's 53-bit precision,
// then truncated to signed64, returning its low32 bits. Startup 0x4a7ef0 sets
// precision control to 53 bits; assuming the x87 reset default (64) differs.
static uint32_t scaleDuration(uint32_t duration, float rate) {
    uint32_t bits;
    std::memcpy(&bits, &rate, 4);
    const uint32_t exponent = (bits >> 23) & 255;
    if (exponent == 255)
        return 0; // x87 indefinite int64 low word
    uint64_t significand = bits & 0x7fffff;
    int shift = -149;
    if (exponent) {
        significand |= 0x800000;
        shift = int(exponent) - 150;
    }
    uint64_t magnitude = uint64_t(duration) * significand;
    if (magnitude) {
        const int bitCount = 64 - __builtin_clzll(magnitude);
        if (bitCount > 53) {
            const int discarded = bitCount - 53;
            const uint64_t tailMask = (uint64_t(1) << discarded) - 1;
            const uint64_t tail = magnitude & tailMask;
            uint64_t rounded = magnitude >> discarded;
            const uint64_t halfway = uint64_t(1) << (discarded - 1);
            if (tail > halfway || (tail == halfway && (rounded & 1)))
                ++rounded;
            magnitude = rounded << discarded;
        }
    }
    if (shift >= 0) {
        if (shift >= 63 || magnitude > (uint64_t(1) << 63) >> shift)
            return 0;
        magnitude <<= shift;
    } else {
        magnitude = shift <= -64 ? 0 : magnitude >> -shift;
    }
    if (magnitude > (uint64_t(1) << 63) || (magnitude == (uint64_t(1) << 63) && !(bits >> 31)))
        return 0;
    uint32_t low = uint32_t(magnitude);
    return bits >> 31 ? uint32_t(0) - low : low;
}

extern "C" uint32_t claw_animation_update(ClawAnimationState *s, ClawAnimationActor *a,
                                          const ClawAnimationRecord *records, uint32_t count, const uint32_t *images,
                                          int32_t first, int32_t last, uint32_t delta, uint32_t globalPosition,
                                          ClawAnimationEvent *event) {
    *event = {};
    if (!s->hasSequence)
        return 0xffffffff;
    if (s->remaining) {
        if (!s->timed) {
            --s->remaining;
            return s->previousCode;
        }
        if (delta < s->remaining) {
            s->remaining -= delta;
            return s->previousCode;
        }
        s->remaining = 0;
    }
    s->previousCode = s->code;
    if (s->stopped)
        return s->code;
    // Invalid records are rejected by the native loader. Original dereferences
    // a null record in some malformed-sequence cases; avoid undefined behavior.
    if (!records || s->recordIndex < 0 || uint32_t(s->recordIndex) >= count)
        return 0xffffffff;
    const auto &r = records[s->recordIndex];
    auto image = [&](uint32_t id) -> uint32_t {
        if (!images || int32_t(id) < first || int32_t(id) > last)
            return 0;
        return images[id]; // mirrors original image-ID-indexed array
    };
    auto selectImage = [&](uint32_t id) {
        a->imageID = id;
        a->imageToken = image(id);
    };
    if (images) {
        switch (r.imageCommand) {
        case 1:
            selectImage(a->imageID + 1);
            if (!a->imageToken)
                selectImage(uint32_t(first));
            break;
        case 2:
            selectImage(a->imageID == uint32_t(first) ? uint32_t(last) : a->imageID - 1);
            break;
        case 3:
            selectImage(r.parameter);
            break;
        case 4:
            selectImage(uint32_t(first));
            break;
        case 5:
            selectImage(uint32_t(last));
            break;
        case 6:
            selectImage(a->imageID + r.parameter);
            if (!a->imageToken)
                selectImage(uint32_t(last));
            break;
        case 7:
            selectImage(a->imageID - r.parameter);
            if (!a->imageToken)
                selectImage(uint32_t(first));
            break;
        default:
            break;
        }
    }
    a->moveX = a->moveY = 0;
    switch (r.movementCommand) {
    case 1:
        a->moveX = r.dx;
        a->moveY = r.dy;
        break;
    case 2:
        a->x += a->flags & 2 ? uint32_t(0) - r.dx : r.dx;
        a->y += r.dy;
        break;
    case 3:
        a->x = r.dx;
        a->y = r.dy;
        break;
    default:
        break;
    }
    if (r.event) {
        event->event = r.event;
        event->spatial = (r.flags & 4) ? 1 : 0;
        event->position = event->spatial ? a->x : globalPosition;
        event->dispatched = 1;
    }
    s->remaining = r.duration;
    s->timed = (~r.flags) & 1;
    if (s->rate != 1.0f)
        s->remaining = scaleDuration(s->remaining, s->rate);
    auto at = [&](int32_t index) -> const ClawAnimationRecord * {
        return index >= 0 && uint32_t(index) < count ? records + index : nullptr;
    };
    auto advance = [&]() {
        s->recordIndex = int32_t(uint32_t(s->recordIndex) + 1);
        const auto *next = at(s->recordIndex);
        if (!next) {
            s->recordIndex = 0;
            next = at(0);
        }
        if (next) {
            s->previousCode = s->code;
            s->code = next->code;
        }
    };
    switch (r.controlCommand & 0xffff) {
    case 0:
        if (r.controlCommand != 9)
            advance();
        break;
    case 1:
        if (a->imageID == r.parameter && r.controlCommand != 9)
            advance();
        break;
    case 2:
        if (images && a->imageID == uint32_t(first) && r.controlCommand != 9)
            advance();
        break;
    case 3:
        if (images && a->imageID == uint32_t(last) && r.controlCommand != 9)
            advance();
        break;
    case 4:
        if (images && a->imageID == uint32_t(first) + 1 && r.controlCommand != 9)
            advance();
        break;
    case 5:
        if (images && a->imageID == uint32_t(last) - 1 && r.controlCommand != 9)
            advance();
        break;
    case 6:
        break;
    case 7: {
        s->recordIndex = at(1) ? 1 : 0;
        if (const auto *next = at(s->recordIndex)) {
            s->stopped = 0;
            s->remaining = 0;
            s->previousCode = s->code;
            s->code = next->code;
        }
        break;
    }
    case 8:
        s->recordIndex = 0;
        s->stopped = 0;
        s->rate = 1.0f;
        if (const auto *next = at(0))
            s->code = s->previousCode = next->code;
        break;
    case 9:
        s->stopped = 1;
        break;
    default:
        break;
    }
    return s->remaining ? s->previousCode : s->code;
}
