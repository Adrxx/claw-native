#ifndef CLAW_PLAYER_MENU_MANAGEMENT_RUNTIME_H
#define CLAW_PLAYER_MENU_MANAGEMENT_RUNTIME_H
#include "PlayerCacheApplicationRuntime.h"
#include "CStringAssignmentRuntime.h"
#include "PlayerStartupRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerMenuManagementContext {
    ClawSceneActorHost scene;
    ClawPlayerCacheApplicationContext *playerCache;
    ClawCStringAssignmentContext *strings;
    ClawPlayerStartupContext *startup;
    /* Caller-owned automatic storage: title128, list text256, CString cells4+4,
    time text64 =456 bytes. Never retained or owned by a player record. */
    uint32_t automaticToken, composeStrings, maximumOperations, fault;
} ClawPlayerMenuManagementContext;
typedef ClawBootyProgressionCall ClawPlayerMenuManagementCall;
typedef uint32_t (*ClawPlayerMenuManagementDependency)(ClawPlayerMenuManagementContext *,
                                                       const ClawPlayerMenuManagementCall *, void *);
/* Complete stdcall49b160/49b630(HWND,message,fullWParam,lParam), RET16;
   cdecl49afd0(listbox),49b3a0/49b470(dialog,listbox),49c860(outCString,timeMs);
   thiscall49aed0(level), RET4; elected426e30(handlerWord,8090,data), RET12.
   Live5371fc,53ebe0/e4/e8/ec and borrowed app/record/list identities are raw.
   Frozen PlayerCache/SaveLoad/SaveFile and optional CString/Startup compose.
   8090 elects actual428c40(app,13,1,1,data); the state13 graphical popup and
   transition remain addressed dependencies, not a fabricated record mutation.
   Ordinary CString ctor/copy/destroy compose existing frozen source entries
   when composeStrings=1; supply strings with allocation/fade, byte transport.
   Format4a3920 and UI546d1c/34/3c/40/44 are explicit synchronous services.
   Unknown0 unchanged; recognized1 complete. VoidEAX normalized0; result
   separate. Fault1 missing service/span,2 unsafe prefix,3 ABI/operation guard. */
uint32_t claw_player_menu_management_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                           uint32_t argumentCount, ClawPlayerMenuManagementContext *,
                                           ClawPlayerMenuManagementDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
