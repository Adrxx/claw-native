#ifndef CLAW_AMBIENT_AUDIO_BACKEND_RUNTIME_H
#define CLAW_AMBIENT_AUDIO_BACKEND_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawAmbientAudioBackendContext {
    ClawSceneActorHost scene;
    // Native bounded traversal guard. Zero uses65536; not an original field.
    uint32_t maximumTraversal, fault;
} ClawAmbientAudioBackendContext;
typedef struct ClawAmbientAudioBackendCall {
    uint32_t function, receiver, argumentCount, arguments[6];
    // Zero for ordinary source services. DirectSound COM calls retain original
    // interface token as arguments[0], receiver0, and actual vtable identity.
    // The original stack output-pointer transport is represented by outputWord
    // for GetVolume/GetStatus; it is omitted from logical argumentCount.
    uint32_t bufferMethod;
    uint32_t *outputWord;
} ClawAmbientAudioBackendCall;
typedef uint32_t (*ClawAmbientAudioBackendDependency)(ClawAmbientAudioBackendContext *,
                                                      const ClawAmbientAudioBackendCall *, void *);
// Raw actor-independent voice/resource14words. voice+c DirectSound interface,
// +10 manager; manager+78 device gate,+c/+10 fade list,+7c clock. Fades10words;
// CPtrList7words with12byte nodes and original pooled block ownership.
// Actual source stack args; receiver=thiscall ECX, or0 for cdecl helper entries.
// Output is native support/completion, with meaningful source EAX in result.
// fault1 missing span/service,2 invalid ABI/unchecked table/division domain,
//3 runaway/nonadvancing source list. Faults are extensions, not source success.
uint32_t claw_ambient_audio_backend_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                          uint32_t argumentCount, ClawAmbientAudioBackendContext *,
                                          ClawAmbientAudioBackendDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
