#pragma once
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawSpecialCommandGlobals {
    uint32_t managerToken, playerToken, warpX, warpY, audioVolume, fadeBypass;
    uint32_t inputMappingToken, mouseToken, accumulatedTick;
    ClawClockState clock;
    ClawFrameClock stage, animation;
    uint32_t capturedPlayer[78]; /* Original534c80..534db7, copied by415d90. */
    uint32_t displayRankings;    /*525518, live option forwarded by46bbc0.*/
} ClawSpecialCommandGlobals;
typedef struct ClawSpecialCommandContext {
    ClawSceneActorHost scene;
    ClawSpecialCommandGlobals *globals;
    uint32_t fault;
} ClawSpecialCommandContext;
typedef struct ClawSpecialCommandCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    const char *name;
    uint32_t localMask;
    uint32_t *buffer;
    uint32_t bufferWords;
} ClawSpecialCommandCall;
typedef uint32_t (*ClawSpecialCommandDependency)(ClawSpecialCommandContext *, const ClawSpecialCommandCall *, void *);
/*426e30 args(0,command,0), bounded805c/800e/8023;46c630 warp;
 46c900 end-level/map;42abf0 clock/player reset;48feb0/48fda0(steps,duration,flag);
 42d420/42d440 music;46b7b0 teardown;46bbc0 settings cleanup;
 415d90 cdecl(player) capture;46c7b0(player) level stats;
 428c40 only state10 (10,level,retainPrevious,unused);
 40ac20(manager,level,previousMode) Booty initializer,40b120(previousMode) enter;
 4ecc00 five-word fade packet constructor;4ec600(fader) exact list removal.
 Source ready-mode probes are repeated, signed warp coordinates >0. Physical
 fader4ec050/4ec9c0, audio, renderer/presentation, save/file, state5 fallback,
 Booty child virtual/resource services remain exact-address dependencies.
 40b5c0 must route frozen base constructor, never return success without stores.
 localMask identifies automatic pointer argument(s), token normalized0;
 buffer carries its live raw packet. Namedlookup returns resolved token.
 Inputs/global aliases must be shared with scene/camera/powerups/save contexts.
 Clock reads use scene.readClock in exact source order; no synthetic timestep.
 Fault1 missing span,2 failed history allocation,3 unsupported argument profile.
 Entry return1 means recognized, result exposes meaningful source EAX only. */
uint32_t claw_special_command_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                    uint32_t argumentCount, ClawSpecialCommandContext *, ClawSpecialCommandDependency,
                                    void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
