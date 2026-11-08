#ifndef CLAW_PLAYER_CACHE_APPLICATION_RUNTIME_H
#define CLAW_PLAYER_CACHE_APPLICATION_RUNTIME_H
#include "SaveLoadRuntime.h"
#include "BootyProgressionRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerCacheApplicationContext {
    ClawSceneActorHost scene;
    ClawSaveLoadContext *saveLoad;
    /* Caller-owned projection of source automatic storage,304bytes: three
    registry fields100bytes each then the in/out length DWORD. Also used for
    the change-player listbox's256-byte automatic text. Never retained. */
    uint32_t automaticToken, composeSaveLoad, maximumOperations, fault;
} ClawPlayerCacheApplicationContext;
typedef ClawBootyProgressionCall ClawPlayerCacheApplicationCall;
typedef uint32_t (*ClawPlayerCacheApplicationDependency)(ClawPlayerCacheApplicationContext *,
                                                         const ClawPlayerCacheApplicationCall *, void *);
/* Whole42bf90(record),430ac0(record),42bbb0/bbd0/bbe0/bbf0(),
   42bb00(template,dialogProc),49c090(control,selected,excludePlayer),
   cdecl49b050(dialog)/49b0c0(listbox),stdcall49b730(HWND,message,wParam,lParam).
   Record/source-manager constructors and readers compose frozen SaveFile/Load.
   Registry, HWND/selection, modal message pump, source surface/clock callbacks
   remain exact-address services. Live5371fc(app),537204(input),53725c(difficulty),
   53ebe0/53ebec(dialog retained identities); no private alias defaults.
   Void EAX normalized0. Unknown0;fault1missing,2unchecked,3ABI/guard. */
uint32_t claw_player_cache_application_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                             uint32_t argumentCount, ClawPlayerCacheApplicationContext *,
                                             ClawPlayerCacheApplicationDependency, void *, uint32_t *result);
/* Exact caller instruction span426546..4266e0 within actual425730, not a
   claimed whole function. priorNameToken borrows32-byte source registry name
   already produced earlier by425730. Alloc88/publishapp+60/startupCLAW.USR,
   prior-name selection, migration of User_Name/Location/Email then deletion,
   fallback literalPlayer, actual42bf90/input-binding/difficulty publication.
   *reachedJoin=1 onlywhen source reaches4266e0; startupfailure=0 after exact
   800a/6aa report. Does not run later application/clock/audio/bootstrap footer.
   Scratch automaticToken304bytes must be valid; constructors are not repeated
   over an already existing manager; previous ownership isn't guessed/freed. */
uint32_t claw_player_cache_application_startup_span(uint32_t applicationToken, uint32_t priorNameToken,
                                                    ClawPlayerCacheApplicationContext *,
                                                    ClawPlayerCacheApplicationDependency, void *,
                                                    uint32_t *reachedJoin);
#ifdef __cplusplus
}
#endif
#endif
