#pragma once
#include "PowerupObjectRuntime.h"
#include "LiftThrowRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_ROPE_PRIVATE_BYTES 0x148u
#define CLAW_ROPE_PRIVATE_WORDS 82u
/* Registered AniRope(ID51,literal522bf8), callback403100. Other literal names
   with 'rope' in their image paths can be ordinary scenery, not this logic. */
typedef struct ClawRopeGlobals {
    uint32_t playerToken, tick, stageDelta, ignoreHazards, cheat, pixelScratch;
    uint32_t physicsDefaults[4]; /* live513e10..513e1f; four raw double halves */
} ClawRopeGlobals;
typedef struct ClawRopeContext {
    ClawSceneActorHost scene;
    ClawRopeGlobals *globals;
    /* Borrow frozen41ee60 selector context. Its input token, animation delta,
    powerup globals and complete player physics are canonical shared aliases.
    Required by grab/player paths; ordinary actor methods don't require it. */
    ClawPowerupObjectContext *powerups;
    /* Optional composition of held-target cleanup/bitset421010/420fc0/41c4e0.
    Without it those exact raw calls remain explicit rich dependencies. */
    ClawLiftThrowContext *lift;
    uint32_t composeAnimation, fault;
} ClawRopeContext;
typedef struct ClawRopeCall {
    uint32_t function, receiver, argumentCount, arguments[6];
    const char *name;
} ClawRopeCall;
typedef uint32_t (*ClawRopeDependency)(ClawRopeContext *, const ClawRopeCall *, void *);
/* Copies only pinned physics defaults; preserves caller live global aliases. */
void claw_rope_defaults(ClawRopeGlobals *);
/* Raw full entries:403100 cdecl(actor);4031c0 thiscall(actor);
   4035a0(stateID),403850(unusedNameToken),4038d0(),465450(),
   403ab0()/403ac0() getters,4181c0 cdecl(player,primary,private);
   41ee60 cdecl(player,primary,private,electedRope) composes frozen selector;
   41ce80 cdecl(player) composes frozen CaptainClawHit only for an elected
   rope at player+74(type100/fc26af), using borrowed powerups.items identities.
   Shared4dc870(private) composes frozen raw dispatcher, and shared lifecycle
   methods compose frozenStackedActorLifecycleRuntime. Exact class table534820,
   ID-name array537698 and their CString/raw arenas must be host-addressable for
   state dispatch; original name-pointer identities are never replaced by text.
   Source rope frame/geometry uses immutable522f08 table and modulo120.
   No invented rope duration/pendulum/button election. Geometry domains outside
   original table are bounded fault2 at the reached prefix; they aren't claimed
   normal original behavior. Allocator-null guards preserve reached source writes.
   Also415df0 cdecl(actor), ONLY initial5007: source4181c0 followed by unchanged
   public input epilogue, using live primary/private/source aliases. Other initial
   states return0 untouched. Full player helper composes frozen physics/facing;
   allocation/resources/contact election/physical audio remain explicit services.
   Returns1 completed/covered,0 unsupported/fault; result only meaningful EAX.
   source void methods normalize0. Fault1 missing span/service,2 bounded unsafe
   profile/argcount,3 missing required composition. Clear fault before each call. */
uint32_t claw_rope_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                         ClawRopeContext *, ClawRopeDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
