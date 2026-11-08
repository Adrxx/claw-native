#ifndef CLAW_SPEECH_ACTOR_H
#define CLAW_SPEECH_ACTOR_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Raw original actor and logic buffers. Pointer words remain opaque tokens.
typedef struct ClawSpeechActor {
    uint32_t actor[128], logic[128];
} ClawSpeechActor;
typedef struct ClawSpeechImage {
    uint32_t token, firstIndex, lastIndex, firstFrameToken;
} ClawSpeechImage;
typedef struct ClawSpeechContext {
    uint32_t actorToken, imageRegistryToken;
    uint32_t registeredActorToken, busy; // Globals 0x53c9a4 / 0x53c9a0.
    uint32_t managerAvailable, speechEnabled, speechVolume, stageDelta;
    uint32_t playerPresent, playerX, playerY, playerHeight, playerLayer, playerLogicState;
    // Immutable metadata for actor+0x184's current resource: sound+0x10's
    // voice pool token and pool+0x28 duration. Refresh after queue replacement.
    uint32_t queuedSoundPoolToken, queuedSoundDuration;
} ClawSpeechContext;
typedef struct ClawSpeechHost {
    void *context;
    // Original registry 0x4f6286; name 0x52c580 is GAME_EXCLAMATION.
    void (*resolveImage)(void *context, uint32_t registryToken, uint32_t nameToken, ClawSpeechImage *out);
    // Original 0x4b45f0 boundary. Return value does not alter this actor.
    uint32_t (*play)(void *context, uint32_t poolToken, uint32_t volume, uint32_t pan, uint32_t pitchPercent,
                     uint32_t looping);
} ClawSpeechHost;
// Entire registered ClawDialogSound callback 0x48c630. Every path returns 1.
// Global registration/busy updates are in context. Actor+0x6c must represent
// its valid logic buffer. Player fields and queued resource metadata are inputs.
uint32_t claw_speech_actor_update(ClawSpeechActor *state, ClawSpeechContext *context, ClawSpeechHost host);
#ifdef __cplusplus
}
#endif
#endif
