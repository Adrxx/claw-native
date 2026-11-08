#ifndef CLAW_APPLICATION_STARTUP_RUNTIME_H
#define CLAW_APPLICATION_STARTUP_RUNTIME_H
#include "SceneStartupCompositionRuntime.h"
#include "ResourceArchiveLoadingRuntime.h"
#include "PlayerCacheApplicationRuntime.h"
#include "PlayerStartupRuntime.h"
#include "PlayerFadeRuntime.h"
#include "LightPaletteRuntime.h"
#include "SoundTriggerLogicRuntime.h"
#include "MusicRuntime.h"
#include "CRTRandomRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_APPLICATION_STARTUP_AUTOMATIC_BYTES 1200u
typedef struct ClawApplicationStartupContext {
    ClawSceneActorHost scene;
    /* Borrowed frozen owners; null elects the exact addressed dependency.
    Copies receive this call's synchronous host, never retained stack hosts. */
    ClawSceneStartupCompositionContext *graphics;
    ClawResourceArchiveLoadingContext *archive;
    ClawPlayerCacheApplicationContext *players;
    ClawPlayerStartupContext *messages;
    ClawPlayerFadeContext *fades;
    ClawLightPaletteContext *light;
    ClawSoundTriggerContext *ambient;
    ClawMusicContext *music;
    ClawCRTRandomContext *random;
    /* Caller-owned source automatic projection,1200bytes; not a source heap
    allocation. name32, command300, userCommand300, logCommand256,
    temporaryCString4, registryLength4, selected-cache304 at offsets
    0,32,332,632,888,892,896 respectively. Never retained or freed. */
    uint32_t automaticToken, maximumOperations, fault;
    /* Opt-in bounded pregraphics source-frame projection: the byte host maps
    logCommand's initialized span (up to300 bytes) onto source E-238, contiguous
    with USER at E-138. The rich5028ec view remains exactly256 bytes.
    Zero preserves the legacy scratch contract. */
    uint32_t pregraphicsSourceFrame;
    /*Optional exact byte spans for ordinary odd-sized archive/path allocations.
   The word host remains authoritative for aligned source DWORD accesses.*/
    void *byteContext;
    uint8_t *(*bytes)(void *, uint32_t token, uint32_t byteCount);
} ClawApplicationStartupContext;
typedef ClawPlayerCacheApplicationCall ClawApplicationStartupCall;
typedef uint32_t (*ClawApplicationStartupDependency)(ClawApplicationStartupContext *,
                                                     const ClawApplicationStartupCall *, void *);
/* Whole original425730(windowOwner,commandLine), thiscall/RET8, VT50bee4+4.
   windowOwner+4 is HWND,+8 is the instance owner (whose+12 is HINSTANCE).
   commandLine is an ordinary readable null-terminated source token, including
   the empty string. Frozen426546..4266e0 is composed, never duplicated.
   Raw globals remain authoritative. Rich services preserve exact identities;
   localMask256 receiver, bits otherwise; buffers in ascending argument order.
   Local4a3990 strstr returns byteOffset+1,0 for absent;4f21e0 mutates its
   local300-byte string.4268b0 writes a local4-byte CString value; its
   incidental returned local address is excluded.
   No window/registry/media/file operation occurs without a dependency.
   Return1 covered/completed, original bootstrap EAX separately (0/1).
   fault1 span/owner/service,2 ABI/domain,3 operation budget. Source C++ SEH
   exceptional unwinding is not transported; ordinary return cleanup is exact.
   See docs/application-startup-runtime.md for owner/transport boundaries. */
uint32_t claw_application_startup_entry(uint32_t function, uint32_t application, const uint32_t *arguments,
                                        uint32_t argumentCount, ClawApplicationStartupContext *,
                                        ClawApplicationStartupDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
