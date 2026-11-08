#ifndef CLAW_AUDIO_RESOURCE_RUNTIME_H
#define CLAW_AUDIO_RESOURCE_RUNTIME_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Raw 0x38-byte pool/voice objects. Tokens identify object bases; intrusive
// list links point to objectToken+4, as in the original. lookup returns 14 words.
typedef struct ClawAudioResourceContext {
    uint32_t managerToken, deviceToken, deviceAvailable;
    uint32_t resourceHead, resourceTail; // Original manager+4/+8 list nodes.
} ClawAudioResourceContext;
typedef struct ClawAudioResourceHost {
    void *context;
    uint32_t *(*lookup)(void *context, uint32_t objectToken);
    uint32_t (*allocate)(void *context, uint32_t bytes);
    // Original DirectSound CreateSoundBuffer (+0xc). format is an 18-byte
    // WAVEFORMATEX copy with cbSize forced to zero; descriptor size20, flags0xe0.
    uint32_t (*createBuffer)(void *context, uint32_t deviceToken, const uint8_t *format, uint32_t dataBytes,
                             uint32_t *outBufferToken);
    // Original DirectSound DuplicateSoundBuffer (+0x14).
    uint32_t (*duplicateBuffer)(void *context, uint32_t deviceToken, uint32_t sourceBufferToken,
                                uint32_t *outBufferToken);
    // Buffer methods: GetFrequency20, GetPan1c, GetVolume18, GetStatus24.
    // May update out even on failure, matching the external service contract.
    uint32_t (*get)(void *context, uint32_t bufferToken, uint32_t method, uint32_t *out);
    // Buffer SetVolume3c, SetPan40, SetFrequency44.
    uint32_t (*set)(void *context, uint32_t bufferToken, uint32_t method, uint32_t value);
    void (*report)(void *context, uint32_t originalLine, uint32_t result);
} ClawAudioResourceHost;
typedef struct ClawAudioRiffResult {
    uint32_t formatOffset, dataOffset, dataBytes;
} ClawAudioRiffResult;
// 0x4b4e30 parser with explicit input bounds. Returns original boolean in its
// readable domain. Fault1 denotes an input read the original does not guard.
uint32_t claw_audio_parse_riff(const uint8_t *data, uint32_t bytes, ClawAudioRiffResult *result, uint32_t *fault);
// Entire 0x4b48b0 creator: PCM tag1 only; metadata duration wraps dataBytes*1000
// before unsigned division by nAvgBytesPerSec. format==NULL is permitted.
// Fault1 division by zero, fault2 null intrusive-list node, fault3 missing token.
// Fault output is a portable diagnostic, not an original successful return.
uint32_t claw_audio_create_resource(ClawAudioResourceContext *state, const uint8_t *format, uint32_t dataBytes,
                                    ClawAudioResourceHost host, uint32_t *fault);
// Entire 0x4b42e0 allocation/duplication, including reusable argument +0x30.
uint32_t claw_audio_allocate_voice(ClawAudioResourceContext *state, uint32_t poolToken, uint32_t reusable,
                                   ClawAudioResourceHost host, uint32_t *fault);
// Entire 0x4b4430 selection and list ordering. No voice-count cap is present.
uint32_t claw_audio_select_voice(ClawAudioResourceContext *state, uint32_t poolToken, ClawAudioResourceHost host,
                                 uint32_t *fault);
#ifdef __cplusplus
}
#endif
#endif
