#include "AudioPCMTransfer.h"
#include <cstring>
namespace {
uint32_t *words(ClawAudioPCMHost h, uint32_t token, uint32_t *fault) {
    uint32_t *p = h.resource.lookup(h.resource.context, token);
    if (!p && fault)
        *fault = 3;
    return p;
}
bool failed(const uint32_t *fault) {
    return fault && *fault;
}
uint8_t *bytes(ClawAudioPCMHost h, uint32_t token, uint32_t size, uint32_t *fault) {
    uint8_t *p = h.lookupBytes(h.resource.context, token, size);
    if (!p && fault)
        *fault = 3;
    return p;
}
bool removeNode(uint32_t *head, uint32_t *tail, uint32_t token, ClawAudioPCMHost h, uint32_t *fault) {
    if (!token) {
        if (fault)
            *fault = 2;
        return false;
    }
    uint32_t *p = words(h, token, fault);
    if (!p)
        return false;
    if (p[2]) {
        uint32_t *q = words(h, p[2] - 4, fault);
        if (!q)
            return false;
        q[1] = p[1];
    } else
        *head = p[1];
    if (p[1]) {
        uint32_t *q = words(h, p[1] - 4, fault);
        if (!q)
            return false;
        q[2] = p[2];
    } else
        *tail = p[2];
    return true;
}
} // namespace
extern "C" uint32_t claw_audio_read_file(ClawAudioPCMHost h, uint32_t stream, uint32_t offset, uint32_t count,
                                         uint32_t destination, uint32_t *fault) {
    if (fault)
        *fault = 0;
    if (!count)
        return 0;
    uint32_t *s = words(h, stream, fault);
    if (!s)
        return 0;
    while (h.seek(h.resource.context, s[3], offset, 0)) {
        if (!h.retry(h.resource.context, stream))
            return 0;
    }
    uint32_t read = h.read(h.resource.context, destination, 1, count, s[3]);
    if (read == count)
        return read;
    while (h.retry(h.resource.context, stream)) {
        read = h.read(h.resource.context, destination, 1, count, s[3]);
        if (read == count)
            return read;
    }
    return 0;
}
extern "C" uint32_t claw_audio_acquire_file(ClawAudioPCMHost h, uint32_t token, uint32_t *fault) {
    if (fault)
        *fault = 0;
    uint32_t *f = words(h, token, fault);
    if (!f)
        return 0;
    uint32_t *archive = words(h, f[9], fault);
    if (!archive)
        return 0;
    if (archive[8])
        return f[10] - archive[3] + archive[8];
    if (f[6])
        return f[6];
    if (!f[5])
        return 0;
    f[6] = h.resource.allocate(h.resource.context, f[5]);
    if (!f[6])
        return 0;
    // Original4b61fe reloads the owner after the allocator callback.
    archive = words(h, f[9], fault);
    if (!archive)
        return 0;
    uint32_t read = claw_audio_read_file(h, archive[6], f[10], f[5], f[6], fault);
    if (failed(fault))
        return 0;
    if (read != f[5]) {
        h.free(h.resource.context, f[6]);
        f[6] = 0;
    }
    return f[6];
}
extern "C" uint32_t claw_audio_release_file(ClawAudioPCMHost h, uint32_t token, uint32_t *fault) {
    if (fault)
        *fault = 0;
    uint32_t *f = words(h, token, fault);
    if (!f)
        return 0;
    if (f[6]) {
        h.free(h.resource.context, f[6]);
        f[6] = 0;
    }
    return 1;
}
extern "C" uint32_t claw_audio_transfer_pcm(ClawAudioPCMContext *s, uint32_t pool, uint32_t source, uint32_t dataBytes,
                                            ClawAudioPCMHost h, uint32_t *fault) {
    if (fault)
        *fault = 0;
    if (!s->resource.deviceAvailable)
        return 0;
    uint32_t *p = words(h, pool, fault);
    if (!p)
        return 0;
    ClawAudioPCMLock regions{};
    if (h.lock(h.resource.context, p[3], 0, dataBytes, 1, &regions)) {
        h.resource.report(h.resource.context, 0x200, 1);
        return 0;
    }
    uint64_t total = uint64_t(regions.firstBytes) + regions.secondBytes;
    if (total > dataBytes) {
        if (fault)
            *fault = 4;
        return 0;
    }
    uint8_t *input = nullptr;
    if (total) {
        input = bytes(h, source, uint32_t(total), fault);
        if (!input)
            return 0;
    }
    if (regions.firstBytes) {
        uint8_t *out = bytes(h, regions.firstToken, regions.firstBytes, fault);
        if (!out)
            return 0;
        std::memcpy(out, input, regions.firstBytes);
    }
    if (regions.secondBytes) {
        uint8_t *out = bytes(h, regions.secondToken, regions.secondBytes, fault);
        if (!out)
            return 0;
        std::memcpy(out, input + regions.firstBytes, regions.secondBytes);
    }
    if (h.unlock(h.resource.context, p[3], regions)) {
        h.resource.report(h.resource.context, 0x213, 1);
        return 0;
    }
    return 1;
}
extern "C" void claw_audio_destroy_resource(ClawAudioPCMContext *s, uint32_t token, ClawAudioPCMHost h,
                                            uint32_t *fault) {
    if (fault)
        *fault = 0;
    if (!s->resource.deviceAvailable)
        return;
    uint32_t fade = s->fadeHead ? s->fadeHead - 4 : 0;
    while (fade) {
        uint32_t *p = words(h, fade, fault);
        if (!p)
            return;
        uint32_t next = p[1] ? p[1] - 4 : 0;
        if (p[4] == token) {
            if (!removeNode(&s->fadeHead, &s->fadeTail, fade, h, fault))
                return;
            p[0] = 0x513518;
            h.free(h.resource.context, fade);
        }
        fade = next;
    }
    uint32_t *pool = words(h, token, fault);
    if (!pool)
        return;
    h.release(h.resource.context, pool[3]);
    pool[3] = 0;
    if (!removeNode(&s->resource.resourceHead, &s->resource.resourceTail, token, h, fault))
        return;
    pool[0] = 0x51350c;
    while (pool[12]) {
        uint32_t voice = pool[12] - 4;
        uint32_t *p = words(h, voice, fault);
        if (!p)
            return;
        h.release(h.resource.context, p[3]);
        p[3] = 0;
        if (!removeNode(pool + 12, pool + 13, voice, h, fault))
            return;
        p[0] = 0x513508;
        h.free(h.resource.context, voice);
    }
    pool[0] = 0x513508;
    h.free(h.resource.context, token);
}
extern "C" uint32_t claw_audio_load_pcm(ClawAudioPCMContext *s, uint32_t source, uint32_t sourceBytes,
                                        ClawAudioPCMHost h, uint32_t *fault) {
    if (fault)
        *fault = 0;
    if (!source || !s->resource.deviceAvailable)
        return 0;
    uint8_t *input = bytes(h, source, sourceBytes, fault);
    if (!input)
        return 0;
    ClawAudioRiffResult parsed{};
    if (!claw_audio_parse_riff(input, sourceBytes, &parsed, fault))
        return 0;
    if (parsed.formatOffset > sourceBytes || sourceBytes - parsed.formatOffset < 18 ||
        parsed.dataOffset > sourceBytes || parsed.dataBytes > sourceBytes - parsed.dataOffset) {
        if (fault)
            *fault = 4;
        return 0;
    }
    uint32_t pool =
        claw_audio_create_resource(&s->resource, input + parsed.formatOffset, parsed.dataBytes, h.resource, fault);
    if (!pool || failed(fault))
        return 0;
    if (!claw_audio_transfer_pcm(s, pool, source + parsed.dataOffset, parsed.dataBytes, h, fault)) {
        if (!failed(fault))
            claw_audio_destroy_resource(s, pool, h, fault);
        return 0;
    }
    return pool;
}
extern "C" uint32_t claw_audio_load_sound(ClawAudioPCMContext *s, uint32_t sound, uint32_t file, ClawAudioPCMHost h,
                                          uint32_t *fault) {
    if (fault)
        *fault = 0;
    uint32_t input = claw_audio_acquire_file(h, file, fault);
    if (!input || failed(fault))
        return 0;
    uint32_t *p = words(h, sound, fault);
    if (!p)
        return 0;
    uint32_t *scene = words(h, p[3], fault);
    if (!scene)
        return 0;
    if (!scene[8]) {
        claw_audio_release_file(h, file, fault);
        return 0;
    }
    uint32_t *f = words(h, file, fault);
    if (!f)
        return 0;
    uint32_t pool = claw_audio_load_pcm(s, input, f[5], h, fault);
    if (failed(fault))
        return 0;
    p[4] = pool;
    claw_audio_release_file(h, file, fault);
    return pool != 0;
}
extern "C" void claw_audio_unload_sound(ClawAudioPCMContext *s, uint32_t sound, ClawAudioPCMHost h, uint32_t *fault) {
    if (fault)
        *fault = 0;
    uint32_t *p = words(h, sound, fault);
    if (!p || !p[4])
        return;
    uint32_t *scene = words(h, p[3], fault);
    if (!scene || !scene[8])
        return;
    claw_audio_destroy_resource(s, p[4], h, fault);
    if (failed(fault))
        return;
    p[4] = 0;
}
