# Native Rat and RatBomb host

The native scene now instantiates all12 actual Level1 Rat WWD records through
WorldObjectRuntime, image/resource binders and RatLogic. The scene also loads
42 actual Officers/Soldiers and458 pickups, plus594 scenery,31 platforms,120 pegs,
81 sound/dialog/ambient records,34 single crates,7 ordinary checkpoints and8 curse records:
1467 represented WWD records. The remaining12 Level1 records are uninstantiated. This is partial integration.

Each actor has stable32-bit token identities and pinned raw buffers. Primary,
secondary and contact logic fields persist in the shared scene heap. Rat private
storage is264 words; RatBomb storage is92 words. Constructors, shared enemy
states, collision queries, scene ordering and interactions use recovered code.
The original runtime renderer-init path selects14-pixel collision steps; the
isolated tile-manager constructor profile retains64. Both profiles are compared
against complete original movement calls, including their scalar return flags.

The state host executes the actual recovered CRT initialization and401000
bootstrap, then resolves mutable class arrays through the recovered registry.
Heap CString name identities remain distinct from original literal identities.
Class lookup uses original inheritance order and preserves absent callbacks.
The native bounded arena retains replaced blocks, so the adapter grows array
bounds once before enumerating all state views. Its allocation policy and
process-exit/metadata ownership remain platform adapters.

Level1, GAME and player resource namespaces resolve original ANI/PID files. Image IDs
have distinct identities across image sets. Each ANI is materialized as a raw
20-byte sequence, record-pointer array and48-byte records. Event lookup resolves
native original PCM resources. Player, Rat and RatBomb animation calls now compose
ActorAnimationRuntime: selection preserves timed mode, current-record identity
persists, null selection preserves unrelated fields, and sound callbacks occur
after image/movement writes and before countdown/control writes. Audio routing
has no gameplay buffer writes; reentrant mutation is an explicit unsupported case.

Rat throwing uses original election and ANI marker, SceneActorRuntime's named
creator, the real RatBomb constructor and activation. Retained flight uses actual
Level1 tile collision, explosion states, deferred list deletion and recovered
actor/logic/private destruction. Static original vtable identities are retained
for virtual destructor selection. Core CRT initialization and registration/removal
now use recovered bodies. The ordinary constructor profile has an empty list;
its temporary bitset destructor performs a real removal call. Frozen generic
constructors are proved for that empty/default32/empty-string profile. Populated
constructor behavior and nonempty bit strings remain outside that frozen scope.

The coordinator independently passes:

- `scripts/check-native-player.sh`: all12 records,180 scene frames, then rendered
  Rat throw election, Bomb activation, flight, explosion and ownership removal.
  Player placement near the Rat is synthetic test setup.
  A separate loaded-scene player chain passes WALK/JUMP/FALL/STAND through the
  raw animation caller while all12 Rats are scheduled.
- ActorResourceBindings:16,371 complete calls, including4,000 contact-binding
  calls and preserved unrelated secondary fields.
- CollisionResponse: full movement return values under14/64 step profiles and
  5,500 horizontal-clear queries, including500 real Level1 cases.
- LogicStateRegistry:1,899 complete operations,4,834 ordered full object/arena
  snapshots and156 atomic-service snapshots across three preserved profiles.
- ActorDestruction:3,610 complete calls and11,742 ordered full heap/ownership
  events, including100 joined scene deletion chains.
- ActorAnimationRuntime:6,500 complete calls and1,324 ordered full heap events;
  48 actual decoded records and2,200 retained real-file steps.
- CoreRegistration:17,805 operations and2,415 full snapshots, plus120 actual
  constructors with1,080 shared-global callback snapshots.

The scene now uses recovered input polling, plain camera creation/follow,
whole tile/image drawing and ordinary spatial residency. Cached Canvas commands
prevent redraws from repeating blink preparation. Rat throw eligibility uses
source draw fields; retained tests still label their synthetic player placement.
RNG uses an explicit laboratory seed; retail startup seeding is pending.
Resource paths, physical graphics and CoreAudio mixing remain native services.

Human/Officer/Soldier/combat/Bullet source and separate native hosts are verified,
and those42 WWD actors are now instantiated by the app. Their ordinary-frame
activation and retained controllers pass ASAN with synthetic visits and
idle-timer seeding; shared48ce40 speech now composes and emits scheduled WAV requests. Loot, ordinary
pickup, Points, Glitter and platform hosts compose. Full combat, particles,
game-over UI, menus/saves/music and all-level gameplay remain.
Scene-owned803a respawn now executes original state23 and retained clock reset;
source fade loops are still pending. Physical iPad acceptance is separate.

SpatialGridRuntime independent comparisons pass5,564 calls/17,835 events/
3,164 addresses. Populated native tests now exercise all12 actual Rats through
camera-range activation and dormant reinsertion, then scene-created RatBomb
flight/collision/explosion/deferred teardown. All linked native source passes
AddressSanitizer, including cached post-free field rereads under scoped physical
retention and immediate logical ownership release. See STATUS.md for current
build/input evidence and the explicit partial-population boundary.

PowderKeg and stacked-child Crate source bridges use the common enemy constructor/
FSM with actual source private sizes260/262 words. Keg subtype sound roots join
the shared state sound-pool view; exact raw resource/bounds wrappers and subtype
virtual identities run over the same scene heap. Stack parents use their
separate19-word destructor, not a generic enemy destructor. All45 child crates
are source-created from22 actual WWD inventories and retain neighbor links.
