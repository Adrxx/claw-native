#ifndef CLAW_ELEMENTAL_PROJECTILE_RUNTIME_H
#define CLAW_ELEMENTAL_PROJECTILE_RUNTIME_H
#include "PlayerProjectileRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_ELEMENTAL_PROJECTILE_PRIVATE_BYTES 0x158u
#define CLAW_ELEMENTAL_PROJECTILE_PRIVATE_WORDS 86u
typedef ClawPlayerProjectileGlobals ClawElementalProjectileGlobals;
typedef ClawPlayerProjectileContext ClawElementalProjectileContext;
typedef ClawPlayerProjectileCall ClawElementalProjectileCall;
typedef ClawPlayerProjectileDependency ClawElementalProjectileDependency;
/* Original registered cdecl410100/4101c0/410280(actor), constructors
   410ec0/411370/411820 thiscall(actor), state dispatch411030/4114e0/411990
   thiscall(state), flight411310/4117c0/411c70() and cleanup411cd0().
   Allocation158bytes/86 words, VTs50b7bc/50b80c/50b844, classes534ba0/
   534a38/534b00. Direct Bullet4107c0 base, not Magic410900. Flare150;
   last154 remains unwritten. Globals/host/Bullet views alias frozen context.
   Inherited source scheduler4dc870 is accepted as cdecl(private):receiver0,
   one argument. Existing non-cdecl inherited private methods retain rawreceiver.
   Own bodies compose frozen shared Projectile/Bullet/ANI/destruction at actual
   calls. Exact creation/resource/audio/physical transport stays rich dependency;
   no immediate Flare startup, invented opacity/TTL/sparkle or mixed ownership.
   Covered completed source returns1; unsupported/fault0; result is original
   meaningful EAX separately. fault1 spans/service,2 unchecked allocation
   prefix,3 ABI/traversal limit. Host supplies source registry/name arrays.
   Only actual86 private words are source-owned; frozen padding stays local. */
uint32_t claw_elemental_projectile_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                         uint32_t argumentCount, ClawElementalProjectileContext *,
                                         ClawElementalProjectileDependency, void *, uint32_t *result);
uint32_t claw_elemental_projectile_private_bytes(uint32_t registeredCallback);
uint32_t claw_elemental_projectile_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
