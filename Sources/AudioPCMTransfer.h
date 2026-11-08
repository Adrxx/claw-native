#ifndef CLAW_AUDIO_PCM_TRANSFER_H
#define CLAW_AUDIO_PCM_TRANSFER_H
#include "AudioResourceRuntime.h"
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawAudioPCMContext {
    ClawAudioResourceContext resource;
    uint32_t fadeHead, fadeTail; // Manager+0xc/+0x10 intrusive fade list.
} ClawAudioPCMContext;
typedef struct ClawAudioPCMLock {
    uint32_t firstToken, firstBytes, secondToken, secondBytes;
} ClawAudioPCMLock;
typedef struct ClawAudioPCMHost {
    ClawAudioResourceHost resource;
    // lookup returns raw words for pool, voice, sound, scene, archive, file and
    // stream objects. lookupBytes supplies a readable/writable contiguous span.
    uint8_t *(*lookupBytes)(void *context, uint32_t byteToken, uint32_t bytes);
    void (*free)(void *context, uint32_t token);
    uint32_t (*seek)(void *context, uint32_t fileHandleToken, uint32_t offset, uint32_t whence);
    uint32_t (*read)(void *context, uint32_t destinationToken, uint32_t itemBytes, uint32_t count,
                     uint32_t fileHandleToken);
    // Original stream vtable+8 retry/reopen service. May replace stream+0xc.
    uint32_t (*retry)(void *context, uint32_t streamToken);
    // DirectSound buffer Lock+0x2c / Unlock+0x4c / IUnknown Release+8.
    uint32_t (*lock)(void *context, uint32_t bufferToken, uint32_t offset, uint32_t bytes, uint32_t flags,
                     ClawAudioPCMLock *out);
    uint32_t (*unlock)(void *context, uint32_t bufferToken, ClawAudioPCMLock regions);
    uint32_t (*release)(void *context, uint32_t bufferToken);
} ClawAudioPCMHost;
// Faults preserve earlier side effects: 1 divide, 2 null list node,
// 3 unresolved object/byte token, 4 unsupported bounded source/lock span.
uint32_t claw_audio_read_file(ClawAudioPCMHost host, uint32_t streamToken, uint32_t offset, uint32_t bytes,
                              uint32_t destinationToken, uint32_t *fault);
uint32_t claw_audio_acquire_file(ClawAudioPCMHost host, uint32_t fileToken,
                                 uint32_t *fault); // 0x4b61c0: archive mapping, cached bytes, or read allocation.
uint32_t claw_audio_release_file(ClawAudioPCMHost host, uint32_t fileToken,
                                 uint32_t *fault); // 0x4b6230: frees only file+0x18 cached allocation.
uint32_t claw_audio_transfer_pcm(ClawAudioPCMContext *state, uint32_t poolToken, uint32_t sourceToken,
                                 uint32_t dataBytes, ClawAudioPCMHost host, uint32_t *fault); // Entire 0x4b44f0.
uint32_t claw_audio_load_pcm(ClawAudioPCMContext *state, uint32_t sourceToken, uint32_t sourceBytes,
                             ClawAudioPCMHost host,
                             uint32_t *fault); // 0x4b4a20 composed with frozen parser/creator.
void claw_audio_destroy_resource(ClawAudioPCMContext *state, uint32_t poolToken, ClawAudioPCMHost host,
                                 uint32_t *fault); // 0x4b4ae0.
uint32_t claw_audio_load_sound(ClawAudioPCMContext *state, uint32_t soundToken, uint32_t fileToken,
                               ClawAudioPCMHost host,
                               uint32_t *fault); // 0x4c8850; scene+0x20 gates manager presence.
void claw_audio_unload_sound(ClawAudioPCMContext *state, uint32_t soundToken, ClawAudioPCMHost host,
                             uint32_t *fault); // 0x4c88b0.
#ifdef __cplusplus
}
#endif
#endif
