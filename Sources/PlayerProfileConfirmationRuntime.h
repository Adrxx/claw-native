#ifndef CLAW_PLAYER_PROFILE_CONFIRMATION_RUNTIME_H
#define CLAW_PLAYER_PROFILE_CONFIRMATION_RUNTIME_H
#include "PlayerMenuManagementRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerProfileConfirmationContext {
    ClawSceneActorHost scene;
    ClawPlayerMenuManagementContext *menu;
    ClawSinglePlayerSceneContext *base;
    /* Synchronous caller automatic projection: CString cells0/4/8, POINT12,
    capture RECTs20/36/52 (68 bytes total). No retained host pointer. */
    uint32_t automaticToken, composeBase, composeStrings, maximumOperations, fault;
} ClawPlayerProfileConfirmationContext;
typedef ClawBootyProgressionCall ClawPlayerProfileConfirmationCall;
typedef uint32_t (*ClawPlayerProfileConfirmationDependency)(ClawPlayerProfileConfirmationContext *,
                                                            const ClawPlayerProfileConfirmationCall *, void *);
/* Whole438c40(app,parameter,previousMode),4399d0(popupKind),43a760(),439480(),
   485160() RemoveUserConfirm action,4247c0()/4247e0() OK/cancel,424800() close,
   4299a0() mode13. Receiver is raw owner/CWnd, exact caller cleanup retained.
   Source428c40 remains an addressed controller boundary. Menu/SaveLoad/File,
   source CString and optional40b5c0/48f0d0 base compose frozen modules.
   CWnd graph constructors/load/drawing/resource virtual methods retain exact
   source addresses; never return synthetic menu/native admission success.
   Live5371fc,53ebe0,5375bc/c0/c4,52545c and source previous owner identities
   share the raw heap. Unknown0 unchanged; completion1/EAX separate.
   Fault1 missing span/service,2 unchecked prefix,3 ABI/operation guard. */
uint32_t claw_player_profile_confirmation_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                                uint32_t argumentCount, ClawPlayerProfileConfirmationContext *,
                                                ClawPlayerProfileConfirmationDependency, void *, uint32_t *result);
/* Exact inline state13 constructor body in428c40 after successful380-byte
   allocation. Caller owns allocation/election; base40b5c0 and actual VT50bf94
   fields/stores only. Not a newly invented whole retail function. */
uint32_t claw_player_profile_confirmation_construct(uint32_t ownerToken, uint32_t data,
                                                    ClawPlayerProfileConfirmationContext *,
                                                    ClawPlayerProfileConfirmationDependency, void *, uint32_t *result);
uint32_t claw_player_profile_confirmation_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
