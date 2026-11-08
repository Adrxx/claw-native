#ifndef CLAW_SOUND_TRIGGER_LOGIC_RUNTIME_H
#define CLAW_SOUND_TRIGGER_LOGIC_RUNTIME_H
#include "EnemySpeechRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawSoundTriggerArguments {
    uint32_t words[9], count;
} ClawSoundTriggerArguments;
typedef struct ClawSoundTriggerCall {
    uint32_t function, receiver, arguments[9], argumentCount;
    // Original stack pair/rectangle arguments use token0 in arguments;
    // synchronous writable span points to their actual portable values.
    uint32_t *temporary;
    uint32_t temporaryWords;
} ClawSoundTriggerCall;
typedef struct ClawSoundTriggerContext {
    ClawSceneActorHost scene;
    ClawEnemySpeechGlobals *globals;         // Share original manager/player/audio/53720c aliases.
    uint32_t masterVolume;                   //532c10
    uint32_t triggerProfile, ambientProfile; //53c9b4,534810 diagnostics; retained across calls.
    uint32_t composeSpeech;                  //Nonzero invokes frozen48c820 over the same globals/live heap.
    uint32_t fault;                          //1 missing span/service;2 native unsafe metadata;3 bounded iteration/trap.
} ClawSoundTriggerContext;
typedef uint32_t (*ClawSoundTriggerDependency)(ClawSoundTriggerContext *, const ClawSoundTriggerCall *, void *);
// Callback actors are original cdecl(actor): receiver0 and one actor-token arg.
// Helpers preserve original receiver/argument identity; list/voice/platform
// services remain explicit. Source ambient helpers4022f0/402370/402400 and
// update4025c0 are composed inside ambient actors with recovered object bodies.
// Source4f5133 CPtrList constructor is also exposed for the48-byte ambient
// manager caller profile.
// Original meaningful EAX is separate from native completion status. Unknown
// functions return0 without mutating result/context. Initialize fault0.
// Master-volume entries 0x4024e0 (manager) and 0x4026a0 (object) each take one
// word and have semantic void results; +8 remains the object's live percentage.
uint32_t claw_sound_trigger_entry(uint32_t function, uint32_t receiver, ClawSoundTriggerArguments,
                                  ClawSoundTriggerContext *, ClawSoundTriggerDependency, void *, uint32_t *result);
// Verified inline4262c4..4262d7 stores over an already allocated48-byte manager;
// preserves enabled/center words until a separate402240 initializes them.
uint32_t claw_sound_trigger_construct_manager(uint32_t token, ClawSoundTriggerContext *);
#ifdef __cplusplus
}
#endif
#endif
