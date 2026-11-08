#ifndef CLAW_AUDIO_EVENTS_H
#define CLAW_AUDIO_EVENTS_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t resourceToken, voicePoolToken;
} ClawAudioSound;
typedef struct {
    uint32_t token, disabled;
} ClawAudioRegistry;
typedef struct {
    uint32_t managerAvailable, masterVolume;
    uint32_t defaultReferenceX, sceneWidth;
    uint32_t speechActorPresent, speechLogicPresent, speechBusy;
    uint32_t playerPresent, playerLogicState;
    uint32_t speechRegistryToken, queuedSpeechToken, speechLogicState;
} ClawAudioRouting;
typedef struct {
    uint32_t volume, pan, pitchPercent, looping;
} ClawAudioRequest;
typedef struct {
    void *context;
    void (*resolve)(void *context, uint32_t registryToken, uint32_t nameToken, ClawAudioSound *result);
    uint32_t (*play)(void *context, uint32_t poolToken, ClawAudioRequest request);
} ClawAudioHost;
// 0x4208e0 and 0x420910. Host play boundary corresponds to 0x4b45f0.
uint32_t claw_audio_play_direct(const ClawAudioRouting *routing, const ClawAudioSound *sound, ClawAudioRequest request,
                                ClawAudioHost host);
uint32_t claw_audio_play_name(const ClawAudioRouting *routing, ClawAudioRegistry registry, uint32_t nameToken,
                              ClawAudioHost host);
// 0x4c88e0. Fault 0 means ordinary completion; 1/2 identify original x86
// integer division-by-zero/overflow traps. They have no original return value.
uint32_t claw_audio_play_spatial(const ClawAudioRouting *routing, const ClawAudioSound *sound, uint32_t sourceX,
                                 uint32_t referenceX, uint32_t clampDistance, uint32_t panDistance, ClawAudioHost host,
                                 uint32_t *arithmeticFault);
// 0x48c820 / 0x48c8a0 queue speech; these do not directly play a sound.
uint32_t claw_audio_queue_speech(ClawAudioRouting *routing, uint32_t soundToken, uint32_t force);
uint32_t claw_audio_queue_speech_name(ClawAudioRouting *routing, uint32_t nameToken, uint32_t force,
                                      ClawAudioHost host);

// Portable original voice words. +0xc is buffer token, +0x10 manager token,
// +0x14 playback flags, +0x18 base frequency, +0x24 current frequency.
typedef struct {
    uint32_t words[14];
} ClawAudioVoice;
typedef struct {
    uint32_t token, deviceAvailable;
} ClawAudioPool;
typedef struct {
    void *context;
    // Original 0x4b4430 selection/allocation/list management stays external.
    ClawAudioVoice *(*selectVoice)(void *context, uint32_t poolToken);
    // DirectSound vtable method offsets: volume0x3c, pan0x40, frequency0x44,
    // play0x30. Return HRESULT word; zero is success.
    uint32_t (*directSound)(void *context, uint32_t bufferToken, uint32_t method, uint32_t a, uint32_t b, uint32_t c);
    void (*report)(void *context, uint32_t code, uint32_t result);
} ClawAudioBackend;
// 0x4b45f0 plus recovered parameter setters and play wrapper. Valid table
// domains are volume0..100 and signed pan-100..100. Out-of-domain returns 0
// as a portable extension rather than reading outside the original table.
uint32_t claw_audio_play_pool(ClawAudioPool pool, ClawAudioRequest request, ClawAudioBackend backend);
// Shared finite body; the exported portable API and canonical adapter use
// these same values without a second implementation or link-time game fallback.
static inline int32_t claw_audio_volume_table_value(uint32_t index) {
    static const int32_t volumes[101] = {
    -10000, -6643, -5643, -5058, -4643, -4321, -4058, -3836, -3643, -3473, -3321, -3184, -3058, -2943, -2836,
    -2736,  -2643, -2556, -2473, -2395, -2321, -2251, -2184, -2120, -2058, -2000, -1943, -1888, -1836, -1785,
    -1736,  -1689, -1643, -1599, -1556, -1514, -1473, -1434, -1395, -1358, -1321, -1286, -1251, -1217, -1184,
    -1152,  -1120, -1089, -1058, -1029, -1000, -971,  -943,  -915,  -888,  -862,  -836,  -810,  -785,  -761,
    -736,   -713,  -689,  -666,  -643,  -621,  -599,  -577,  -556,  -535,  -514,  -494,  -473,  -454,  -434,
    -415,   -395,  -377,  -358,  -340,  -321,  -304,  -286,  -268,  -251,  -234,  -217,  -200,  -184,  -168,
    -152,   -136,  -120,  -104,  -89,   -74,   -58,   -43,   -29,   -14,   0};
    return index <= 100 ? volumes[index] : 0;
}
// Original initialized volume table; index0..100 only.
int32_t claw_audio_volume_table(uint32_t index);
#ifdef __cplusplus
}
#endif
#endif
