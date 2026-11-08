#ifndef CLAW_AUDIO_MANAGER_LIFECYCLE_RUNTIME_H
#define CLAW_AUDIO_MANAGER_LIFECYCLE_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawAudioManagerLifecycleContext {
    ClawSceneActorHost scene;
    uint32_t maximumTraversal, fault;
} ClawAudioManagerLifecycleContext;
typedef struct ClawAudioManagerLifecycleCall {
    uint32_t function, receiver, argumentCount, arguments[6];
    uint32_t deviceMethod;
    // DirectSoundCreate retains all three original args, including raw
    // manager+14 output token. This points at that same writable host word.
    uint32_t *outputWord;
} ClawAudioManagerLifecycleCall;
typedef uint32_t (*ClawAudioManagerLifecycleDependency)(ClawAudioManagerLifecycleContext *,
                                                        const ClawAudioManagerLifecycleCall *, void *);
// Whole original entries: ctor4b4710(), delete4b4770(flag), dtor4b4790(),
// startup4b47e0(hwnd,cooperativeLevel), shutdown4b4860(), stop4b4b40(),
// pooled duplicate-stop4b4670(),
// global volume-table initialization4b3c80(). Receiver is actual thiscall ECX;
// table initialization ignores it. Manager32words: +14 actual COM device,
// +78 availability word, +7c multimedia timestamp; ctor preserves +14/+7c.
// Host lookup must provide writable original table541178 (101words) for ctor.
// Native support/fault is separate from original result. Only ctor/delete/
// startup have meaningful source EAX; void entries report0. Fault1 span/service,
// 2 ABI,3 bounded traversal limit (zero limit uses65536), not source success.
uint32_t claw_audio_manager_lifecycle_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                            uint32_t argumentCount, ClawAudioManagerLifecycleContext *,
                                            ClawAudioManagerLifecycleDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
