#ifndef CLAW_MENU_GAME_LAUNCH_RUNTIME_H
#define CLAW_MENU_GAME_LAUNCH_RUNTIME_H
#include "ApplicationLevelProgressionRuntime.h"
#include "PlayerStartupRuntime.h"
#include "StateFiveRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Whole application426e30 only full command807e/807f, three stack words
 (handlerWord,command,data),RET12. Common429b70/428c40 and owner construction
 remain frozen ApplicationLevelProgression/PlayerDeathCommands bodies. */
typedef struct ClawMenuGameLaunchContext {
    ClawSceneActorHost scene;
    ClawApplicationLevelProgressionContext *progression;
    ClawSinglePlayerSceneContext *singlePlayer;
    ClawPlayerStartupContext *startup;
    ClawStateFiveContext *menu;
    uint32_t composeProgression, composeSinglePlayer, composeStartup, composeMenu;
    uint32_t maximumOperations, fault;
} ClawMenuGameLaunchContext;
typedef ClawBootyProgressionCall ClawMenuGameLaunchCall;
typedef uint32_t (*ClawMenuGameLaunchDependency)(ClawMenuGameLaunchContext *, const ClawMenuGameLaunchCall *, void *);
/* Additional owned queries42ba10(level),42ba70(level,kind),42bab0(),42bad0().
 Saved-level436e60 is cdecl(owningCStringData)/RET0; complete4cd530 is
 stdcall(pathData,outputByteToken)/RET8, source1524-byte CFile header read.
 The436e60 caller has256-byte output; longer source titles are guarded
 unsafe caller domain, not converted into a successful game launch.
 Borrowed raw application77words, SinglePlayer478words and shared aliases.
 Selected SinglePlayer21-word global profile is exported before each active
 source callback and reimported afterwards, including source new player token,
 reset flags, accumulated time and checkpoint defaults. No host level increment
 or fabricated world-load success is supplied. Physical transports/source leaves
 outside the composed graph stay addressed. Separate coverage/fault/EAX. */
uint32_t claw_menu_game_launch_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                     uint32_t argumentCount, ClawMenuGameLaunchContext *, ClawMenuGameLaunchDependency,
                                     void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
