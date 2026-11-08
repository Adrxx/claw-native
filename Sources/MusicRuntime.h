#ifndef CLAW_MUSIC_RUNTIME_H
#define CLAW_MUSIC_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawMusicGlobals {
    uint32_t midiDriver, resourceOrdinal, instance;
} ClawMusicGlobals;
typedef struct ClawMusicContext {
    ClawSceneActorHost scene;
    uint8_t *(*lookupBytes)(void *context, uint32_t token, uint32_t bytes);
    ClawMusicGlobals *globals; // Original54131c/541320/541324, respectively.
    uint32_t maximumTraversal, fault;
} ClawMusicContext;
typedef struct ClawMusicCall {
    uint32_t function, receiver, argumentCount, arguments[6];
    // 0 raw calls; 1 Lookup(name)->boolean plus output[0] object;
    // 2 GetNextAssoc(position) outputs nextPosition/keyCString/object;
    // 3 temporary CString destructor(value): receiver0, args[0] is string data.
    // Temporary stack pointer transport is normalized, not original heap.
    uint32_t transport, outputCount;
    uint32_t *outputs;
} ClawMusicCall;
typedef uint32_t (*ClawMusicDependency)(ClawMusicContext *, const ClawMusicCall *, void *);
// Source manager11words and XMI resource24words/VT513528. Raw memory XMI load,
// source manager/sequence start/end/pause/resume/restart/volume/clear/shutdown,
// resource delete, and bounded PE resource loader are listed in module docs.
// MSS32 AIL operations retain exact original import-slot identities/arity.
// OS/MFC map/formatter/CString transport remains explicit; no MIDI timer,
// parser, synthesis or output is invented. Initialize fault0. Fault1 span/service,
// 2 ABI/unchecked metadata bound,3 nonadvancing traversal guard (default65536).
uint32_t claw_music_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                          ClawMusicContext *, ClawMusicDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
