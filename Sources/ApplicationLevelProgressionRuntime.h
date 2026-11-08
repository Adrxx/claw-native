#ifndef CLAW_APPLICATION_LEVEL_PROGRESSION_RUNTIME_H
#define CLAW_APPLICATION_LEVEL_PROGRESSION_RUNTIME_H
#include "BootyResultsRuntime.h"
#include "BootyStoryRuntime.h"
#include "PlayerDeathCommands.h"
#include "SceneLifecycleRuntime.h"
#include "CArrayRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_APPLICATION_CREDITS_BYTES 0x1b8u
#define CLAW_APPLICATION_SINGLE_PLAYER_BYTES 0x778u
typedef struct ClawApplicationLevelProgressionContext {
    ClawSceneActorHost scene;
    ClawPlayerDeathCommandGlobals *application;
    ClawBootyProgressionContext *progression;
    ClawBootyResultsContext *results;
    ClawBootyStoryContext *story;
    ClawSinglePlayerSceneContext *singlePlayer;
    ClawSpecialCommandContext *special;
    ClawSceneLifecycleContext *lifecycle;
    ClawCArrayContext *arrays;
    uint32_t composeTransitions, composeSinglePlayer, composeBooty, composeLifecycle;
    uint32_t maximumOperations, fault;
} ClawApplicationLevelProgressionContext;
typedef ClawBootyProgressionCall ClawApplicationLevelProgressionCall;
typedef uint32_t (*ClawApplicationLevelProgressionDependency)(ClawApplicationLevelProgressionContext *,
                                                              const ClawApplicationLevelProgressionCall *, void *);
//Whole426e30 elected8021/8036/8075, actualthreewords(handlerWord,command,data).
//The command is compared asfull32bits; no invented LOWORD dispatch. Command
//8021 probesliveownermode2/5/10 then type8,param1,retain0,extra0 withtype5fallback.
//8036 resumeslastretainedownerthrough429ac0.8075 calls429be0: onlymode3,
//clearappCString+C0,try nextlevel withsignedwrap14→1, sourcefailure/gameover.
//Entry428c40 accepts(type,param,retain,extra), requiringcomposeTransitions=1.
//These methods do not imply a successful World load or a complete save pipeline.
//Common428c40 prefix/history/footer composes sharedPlayerDeathCommands helper;
//singleplayer type3 ctor0x778 composes frozenSinglePlayer constructor. Credits
//type8 ctor0x1b8/VT50c174,20slots; creationdoesn'tguess its startupreturn.
//Live rawclock/player/input aliases541328..338,537208/20c,5430c8/c4,
//537e88,532c10,537204/200 mustagreewithborrowed applicationglobals. Other
//contexts retain their own declared aliases; physical transports may mutate them.
//Rich stackpointers normalized0/localMask; no host pointer is cast to uint32.
//Paper-roll source48f500/48f740 and type0 fader are unfinished addressed
//dependencies; type2 SceneFade is not an interchangeable controller.
//Physical file/resource/GDI/audio/window/presentation/moviecodec services stay
//actual address dependencies. Unknown0,fault1 missing span/service,2 reached
//unchecked prefix,3 ABI/guard. Meaningful EAX exposed separately from support.
uint32_t claw_application_level_progression_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                                  uint32_t argumentCount, ClawApplicationLevelProgressionContext *,
                                                  ClawApplicationLevelProgressionDependency, void *, uint32_t *result);
//Source inlined428c40 constructor election for types3/8 only. ExtraWord is
//passedthrough evenwherethese typesignoreit; caller mustuse actualtransition.
uint32_t claw_application_level_progression_construct(uint32_t application, uint32_t type, uint32_t extraWord,
                                                      ClawApplicationLevelProgressionContext *,
                                                      ClawApplicationLevelProgressionDependency, void *,
                                                      uint32_t *result);
uint32_t claw_application_level_progression_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
