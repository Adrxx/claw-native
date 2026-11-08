# Original SuperPowerup callback

`SuperPowerupRuntime` recovers the complete original v1.0 registered callback
`0x471330` (497 bytes, literal `0x5228a0`, registration ordinal 117/flags 2).
This callback produces an animated health pickup with actor interaction type
`0x200000`. It neither allocates a private object nor starts a player ability
timer. The frozen `ItemPickupRuntime`/`CaptainClawHit` implementation supplies its
health award. No SpecialPowerup/CursePowerup ability ID or duration is reused.

The input executable is `Original/claw10/CLAW.EXE`, SHA256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
The independent Ghidra project, exact boundary log and decompilation are under
`work/super-powerup-agent/`. The source literal's observed references include
registration `0x401abe`; comparisons at `0x46ccb5`/`0x46e51c` do not prove a
dynamic creation path.

## Retail inventory and tested caller profile

The hash-pinned original disc REZ
`b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`
contains **zero SuperPowerup records in all 14 retail WWD worlds** (34,784 total
object records). `work/super-powerup-agent/inventory.py` records each world's
count in `inventory.json`; `records.json` is an empty list. REZ traversal and
WWD decompression/record decoding in this inventory are format fixtures, not a
new source-backed resource loader.

The retained SuperPowerup fixtures therefore declare a valid actor/primary
caller profile, its image/ANI/resource identities, player contact election and
transport services. They do not claim an observed retail SuperPowerup
placement, a complete dynamic creator or full application startup.

All14 positive per-level configurations use frozen source `0x452b00` profile
initialization, whose selected profile's first word equals the level number.
Each is joined to the complete original/frozen loot initializer `0x4719e0`.
The selected profile word is borrowed through
`ClawWorldLootGlobals.configurationWord`, not replaced with a Level1 zero.

## State and field effects

| Original primary state | Complete callback behavior |
| --- | --- |
| 0 | Clear primary+168 sound. If actor+190 is zero, bind `GAME_POWERUP` (`0x52a198`) with eager0. Set actor flag80000 and type200000. Derive the inclusive attack rectangle138..144 from current leaf image geometry. When depth64 is zero, set1000 and the captured flags OR20000. Lazily initialize the global loot table if needed, then match actor image-root170 by token identity. Match index0 maps actor ID to33; other indices remain unchanged. Copy value and sound from the exact table. A miss gives ID0/value100/sound0. If manager5371fc+124 is nonzero, create `PowerupGlitter` (`0x522950`) at x/y and depth+1 with flags40000. Store the returned live actor token or0 in actor+c8. Set captured primary state5. |
| 5 | Execute actor animation `0x4c82a0` using animation delta5430c4. |
| 29 | If actor+c8 is nonzero, OR10000 into that glitter actor's flags. Preserve the retained token. |
| All others | Return1 without further callback writes. |

Source pointer ordering matters: the startup state is written through the
primary token captured at entry, while the sound destination reloads actor+6c
after service calls. Directed service mutations compare that distinction.
The type==1 substitution branch is preserved, although ordinary callback
startup has already set type200000. Source arithmetic wraps at32 bits;
image-derived rectangle right/bottom subtract1.

Frozen `CaptainClawHit` adds item+fc to player health10c with wrapping32-bit
arithmetic, then clamps the signed result to100 when greater than100. It awards
even at full health, emits the exact pickup sound/cache operation, and marks the
item for deletion. Contact election, secondary callback binding and generic
actor destruction remain owned by their frozen modules. State29 only requests
glitter deletion; this module does not physically free either actor.

## API and composition

`Sources/SuperPowerupRuntime.h` is a C11 raw-token API:

* `claw_super_powerup_entry(actor, context, dependency, user, result)` executes
  the entire registered callback. Its completion return is distinct from
  original EAX1.
* `claw_super_powerup_award(item, ...)` checks exact type200000 and delegates to
  frozen `claw_item_pickup_award`. The caller must already bind
  `player.actor+74=itemToken` through actual interaction election.
* Context borrows the existing item/loot/player context and actor animation
  globals; it preserves the shared sound token/tick cache534ec0/534ec4.
* `composeAnimation=1` routes source binding/update through frozen
  `ActorAnimationRuntime`. Otherwise those exact source calls remain rich
  dependencies. Its legacy `audioPosition` field represents overall volume
 532c10, not a position or clock.
* `composeCreation=1` offers frozen `SceneActorRuntime` named creation; otherwise
  a dependency receives the original six creation arguments. The differential
  suite measures the explicit named-creation transport profile, not a joined
  whole-glitter constructor or generic destructor.

The dependency call records function, receiver, argument count, all arguments
and optional literal/resource name. Required source boundaries are animation
bind `0x4c79e0`, update `0x4c82a0`, named actor creation `0x4c8da0`, dictionary
lookup `0x4f6286`, image-root lookup `0x4061b0`, audio pool/play `0x4b45f0` and the
frozen ANI audio boundaries `0x4c88e0`/`0x4208e0`. Source loot initialization
`0x4719e0` executes as a whole original/native body, with named resource services
explicit. Dictionary and image identities are deterministic caller-supplied
transport tokens; they are not guessed filesystem-derived IDs. A null glitter
creation or missing ANI is a normal original path and is measured.

`fault1` denotes missing raw spans/services and `fault2` rejects out-of-bounds
native metadata. For example, native table scanning rejects indices outside
the 66-word image capacity rather than reading adjoining table storage. These
are native safety extensions, not claimed original exception behavior. Raw
spans retain word alignment and the existing `ClawSceneActorHost` ABI.

## Verification

Run `work/test-env/bin/python Tests/compare_super_powerup_runtime.py`.
Final result: **1,666 complete original calls**, **11,388 ordered callback
snapshots**, **2,088 executed original addresses**. Every call compares the
complete 262,144-byte raw heap plus 196,608-byte original global span, preserving
unrelated seeded fields, aliases, clock/cache values and meaningful callback
EAX. Event comparisons include complete-buffer SHA256 snapshots, receiver,
exact arguments and named resource identity.

Coverage includes 700 seeded state/resource/control cases; 90 complete
CaptainClawHit signed-health/audio cases; 14 source per-level lazy loot joins;
24 retained actual resource histories (12 original health PID files, both
glitter gates, `GAME/ANIS/POWERUP.ANI`, real frozen ANI update and PID geometry);
and 116 directed captured-primary, missing-ANI and retained duplicate/new
sound-token/tick cases; 42 additional matched original potion-group histories
across all 14 source level profiles (168 calls); and 2 resource-service type
substitution cases. The exact source potion amounts are 10, 15, 25, copied from
the lazy table rather than overridden with 100. Real resource histories run animation→health award→
state29 cleanup, including explicit repeated hit-election fixtures. Physical
sound, image decompression/pixels and glitter creation are declared services.

Strict C11 header, C++ `-Wall -Wextra -Werror`, and Python compilation pass.
`zsh work/super-powerup-agent/run-sanitizers.sh` passes ASAN/UBSAN on 672 native
callback/award calls with 480 explicit transport calls and a separately labeled
safe missing-span guard. That sanitizer smoke is directed native verification,
not a replay of the entire differential corpus. No full-game identity, retail
SuperPowerup spawn path or source menu behavior is established by this module.
