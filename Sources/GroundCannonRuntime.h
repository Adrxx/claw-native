#ifndef CLAW_GROUND_CANNON_RUNTIME_H
#define CLAW_GROUND_CANNON_RUNTIME_H
#include "GabrielWeaponsRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_GROUND_CANNON_PRIVATE_BYTES 0x7cu
#define CLAW_GROUND_CANNON_PRIVATE_WORDS 31u
typedef ClawGabrielWeaponsContext ClawGroundCannonContext;
typedef ClawGabrielWeaponsCall ClawGroundCannonCall;
typedef ClawGabrielWeaponsDependency ClawGroundCannonDependency;
// GroundCannon registry29/literal522d0c;4493c0 is cdecl(actor),449480
// thiscall(actor),449590 thiscall(state). Private31/VT50dfd4 exactly9words.
// Class537818 HOME override42a680 is a literal RET; inherited534bf8 owns
// HOME/FIRING/VERTFIRING. Retail bootstrap IDs2018/2027/2032 are observed,
// not caller-forced. No-op init leaves primary1000 until an explicit request.
// Public4dc870 is actualcdecl(receiver0,args{private}); ground31 adapter
// composes frozen GenericEnemy tick. CannonBall uses borrowed Bullet context.
// Shared414030/4141f0/4145b0/4145f0/414640/414660/4146b0/414860/4148b0/
//414a60/414b20/414be0 and lifecycle compose frozen GabrielWeapons/Stacked
// bodies. No duplicate common or projectile implementation. Raw registry and
// allocation/creation/resource/audio/collision transports remain explicit.
// Requires source heap-name tokens, initialized class/name tables and live
// shared globals. Completion is distinct from meaningful original EAX.
// Fault1 span/service,2 unchecked source prefix,3 ABI/traversal rejection.
uint32_t claw_ground_cannon_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                  uint32_t argumentCount, ClawGroundCannonContext *, ClawGroundCannonDependency, void *,
                                  uint32_t *result);
uint32_t claw_ground_cannon_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
