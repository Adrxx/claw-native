#include "AudioResourceRuntime.h"
#include <cstring>
namespace {
uint32_t read32(const uint8_t *p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
uint32_t *object(ClawAudioResourceHost h, uint32_t token, uint32_t *fault) {
    uint32_t *p = h.lookup(h.context, token);
    if (!p && fault)
        *fault = 3;
    return p;
}
void report(ClawAudioResourceHost h, uint32_t line, uint32_t result) {
    h.report(h.context, line, result);
}
void baseConstruct(uint32_t *p, uint32_t buffer, uint32_t manager, ClawAudioResourceHost h) {
    p[4] = manager;
    p[0] = 0x513508;
    p[3] = buffer;
    p[5] = 0;
    p[10] = 0;
    if (!buffer)
        return;
    if (h.get(h.context, buffer, 0x20, p + 6))
        report(h, 0x46, 1);
    p[9] = p[6];
    if (h.get(h.context, buffer, 0x1c, p + 7))
        report(h, 0x4a, 1);
    if (h.get(h.context, buffer, 0x18, p + 8))
        report(h, 0x4d, 1);
}
bool insertHead(uint32_t *head, uint32_t *tail, uint32_t token, ClawAudioResourceHost h, uint32_t *fault) {
    if (!token) {
        if (fault)
            *fault = 2;
        return false;
    }
    uint32_t *p = object(h, token, fault);
    if (!p)
        return false;
    p[1] = *head;
    p[2] = 0;
    if (*head) {
        uint32_t *q = object(h, *head - 4, fault);
        if (!q)
            return false;
        q[2] = token + 4;
    } else
        *tail = token + 4;
    *head = token + 4;
    return true;
}
bool moveTail(uint32_t *head, uint32_t *tail, uint32_t token, ClawAudioResourceHost h, uint32_t *fault) {
    if (!token) {
        if (fault)
            *fault = 2;
        return false;
    }
    uint32_t *p = object(h, token, fault);
    if (!p)
        return false;
    if (p[2]) {
        uint32_t *q = object(h, p[2] - 4, fault);
        if (!q)
            return false;
        q[1] = p[1];
    } else
        *head = p[1];
    if (p[1]) {
        uint32_t *q = object(h, p[1] - 4, fault);
        if (!q)
            return false;
        q[2] = p[2];
    } else
        *tail = p[2];
    p[1] = 0;
    p[2] = *tail;
    if (*tail) {
        uint32_t *q = object(h, *tail - 4, fault);
        if (!q)
            return false;
        q[1] = token + 4;
    } else
        *head = token + 4;
    *tail = token + 4;
    return true;
}
} // namespace
extern "C" uint32_t claw_audio_parse_riff(const uint8_t *data, uint32_t bytes, ClawAudioRiffResult *out,
                                          uint32_t *fault) {
    if (fault)
        *fault = 0;
    if (!data || bytes < 12) {
        if (fault)
            *fault = 1;
        return 0;
    }
    if (read32(data) != 0x46464952 || read32(data + 8) != 0x45564157)
        return 0;
    out->formatOffset = 0;
    out->dataOffset = 0;
    uint64_t end = uint32_t(read32(data + 4) + 8u), cursor = 12;
    while (cursor < end) {
        if (cursor + 8 > bytes) {
            if (fault)
                *fault = 1;
            return 0;
        }
        uint32_t name = read32(data + cursor), size = read32(data + cursor + 4);
        cursor += 8;
        if (name == 0x20746d66)
            out->formatOffset = uint32_t(cursor);
        else if (name == 0x61746164) {
            out->dataOffset = uint32_t(cursor);
            out->dataBytes = size;
            return out->formatOffset != 0;
        }
        uint32_t advance = (size + 1u) & ~1u;
        cursor += advance;
    }
    return 0;
}
extern "C" uint32_t claw_audio_create_resource(ClawAudioResourceContext *s, const uint8_t *format, uint32_t dataBytes,
                                               ClawAudioResourceHost h, uint32_t *fault) {
    if (fault)
        *fault = 0;
    if (!dataBytes || !format || !s->deviceAvailable || format[0] != 1 || format[1] != 0)
        return 0;
    uint8_t copied[18];
    std::memcpy(copied, format, 16);
    copied[16] = copied[17] = 0;
    uint32_t buffer = 0;
    if (h.createBuffer(h.context, s->deviceToken, copied, dataBytes, &buffer)) {
        report(h, 0x2d6, 1);
        return 0;
    }
    if (!buffer)
        return 0;
    uint32_t token = h.allocate(h.context, 0x38);
    if (!token) {
        if (fault)
            *fault = 2;
        return 0;
    }
    uint32_t *p = object(h, token, fault);
    if (!p)
        return 0;
    baseConstruct(p, buffer, s->managerToken, h);
    p[12] = p[13] = 0;
    p[4] = s->managerToken;
    p[5] = 0;
    p[0] = 0x51350c;
    p[3] = buffer;
    if (!insertHead(&s->resourceHead, &s->resourceTail, token, h, fault))
        return 0;
    uint32_t rate = read32(format + 8);
    if (!rate) {
        if (fault)
            *fault = 1;
        return 0;
    }
    uint32_t duration = (dataBytes * 1000u) / rate;
    p[11] = dataBytes;
    p[10] = duration;
    return token;
}
extern "C" uint32_t claw_audio_allocate_voice(ClawAudioResourceContext *s, uint32_t poolToken, uint32_t reusable,
                                              ClawAudioResourceHost h, uint32_t *fault) {
    if (fault)
        *fault = 0;
    if (!s->deviceAvailable)
        return 0;
    uint32_t *pool = object(h, poolToken, fault);
    if (!pool)
        return 0;
    uint32_t token = h.allocate(h.context, 0x38);
    if (!token)
        return 0;
    uint32_t *p = object(h, token, fault);
    if (!p)
        return 0;
    baseConstruct(p, pool[3], pool[4], h);
    p[0] = 0x513510;
    p[13] = poolToken;
    p[12] = 1;
    if (h.duplicateBuffer(h.context, s->deviceToken, pool[3], p + 3)) {
        report(h, 0x179, 1);
        return 0;
    }
    if (!insertHead(pool + 12, pool + 13, token, h, fault))
        return 0;
    p[12] = reusable;
    return token;
}
extern "C" uint32_t claw_audio_select_voice(ClawAudioResourceContext *s, uint32_t poolToken, ClawAudioResourceHost h,
                                            uint32_t *fault) {
    if (fault)
        *fault = 0;
    if (!s->deviceAvailable)
        return 0;
    uint32_t *pool = object(h, poolToken, fault);
    if (!pool)
        return 0;
    uint32_t token = pool[12] ? pool[12] - 4 : 0;
    while (token) {
        uint32_t *p = object(h, token, fault);
        if (!p)
            return 0;
        if (p[12]) {
            uint32_t status = 0;
            uint32_t hr = h.get(h.context, p[3], 0x24, &status);
            if (hr)
                report(h, 0x88, 1);
            if (hr || !(status & 1))
                break;
        }
        token = p[1] ? p[1] - 4 : 0;
    }
    if (token) {
        uint32_t *p = object(h, token, fault);
        if (!p)
            return 0;
        if (h.set(h.context, p[3], 0x3c, pool[8]))
            report(h, 0xaf, 1);
        if (h.set(h.context, p[3], 0x40, pool[7]))
            report(h, 0xf6, 1);
        uint32_t hr = h.set(h.context, p[3], 0x44, pool[6]);
        if (hr)
            report(h, 0x12a, hr);
        else
            p[9] = pool[6];
    } else
        token = claw_audio_allocate_voice(s, poolToken, 1, h, fault);
    if (!moveTail(pool + 12, pool + 13, token, h, fault))
        return 0;
    return token;
}
