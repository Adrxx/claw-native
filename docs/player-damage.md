# Original player hit, hurt, and hazard death

This unit reconstructs the registered `CaptainClawHit` callback `0x41ce80`,
fall-death entry/update, spike-death entry/update, hurt update, and complete
CaptainClaw `0x415df0` branches for initial states28/31/5004/5005.
It uses the original v1.0 executable SHA256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.

| Original entry | Portable API |
| --- | --- |
| `0x41ce80` | `claw_player_hit` |
| `0x417b00` | `claw_player_enter_fall_death` |
| `0x417c50` | `claw_player_enter_spike_death` |
| `0x41c030` | `claw_player_update_hurt` |
| `0x41c2b0` | `claw_player_update_fall_death` |
| `0x41c440` | `claw_player_update_spike_death` |
| `0x415df0` | `claw_player_dispatch_damage` for initial28/31/5004/5005 |

Evidence is in owned `work/player-damage-agent/`, including decompiler output,
observed hit/death instruction listings, and differential verification logs.
The decompiler rejected two initially considered addresses inside other
functions (`0x417a80` and `0x41c0f0`); no API or recovery relies on those
non-entry addresses. The final verified headless run uses observed function
entry `0x41c030` and has no script errors. Headless exit status alone was not
treated as successful recovery.

## Hit engine boundary and state

`CaptainClawHit` reads its attacker from player actor+`0x74`. If that word is0,
it returns0 with no effects. Otherwise it returns1 after its original type
dispatch, even for types with no applicable action. `ClawPlayerDamageContext`
holds an attacker token and all128 attacker actor words; the snapshot must
correspond to the token at player+`0x74`. The adapter commits resulting attacker
flag changes to the actual attacker object. Bounds-checked C word accessors
avoid indexing imported Swift128-element tuples.

There is **no initial immunity or powerup gate inside this callback**. The
generic hit engine decides whether to invoke it. Registry/object recovery
confirmed CaptainClawHit flags0, ordinal2, and binder `0x4c7fa0 ->0x4c7f20`
creates the player's secondary logic at actor+`0x70`; actor+`0x178/+0x17c`
are sound state, not this hit handler. The generic engine's invocation and
collision-filter/immunity boundary remains unrecovered here. Calling this
portable handler directly must not be presented as a verified replacement
for that engine gate.

Actual hurt state is31, not28. Original main callback initial28 has no update
body and runs only its common epilogue. This is preserved. Fall death uses5004
and spike death5005. Unsupported initial states return0 unchanged as a native
scope guard; this does not describe original behavior for other states.

## Damage and pickups

Enemy type4 inflicts damage unless attacker flag`0x10` is set or the attacker
is the player's carried token private75. Types`0x10`, `0x40` and `0x1000000`
use the projectile damage path. These set invulnerability logic+`0x130` to850,
actor words+`0x48`=33 /+`0x44`=0, issue the original hit sounds with exact RNG
ordering, and remove original filter bits. Enemy filtering clears`0x4`;
projectile filtering clears`0x1000004`. Zero attacker damage becomes1;
negative signed damage does not subtract health. Other side effects still
occur for that negative damage branch, as in the original.

Projectile type`0x40` with attacker+`0xfc`=`0x26bf` instead optionally plays
`CLAW_HIT`, sets configuration+`0x764` to2000 when configuration exists,
and marks the attacker with flag`0x10000`; it does not take health or install
the ordinary850 timer. Other projectiles mark the attacker for destruction,
except type`0x1000000` persists; attacker flag`0x20` invokes its actual virtual
slot+`0x2c` instead of directly marking deletion.

Positive damage subtracts from **actor+`0x10c`**, with 32-bit wrap. This callback
does not mirror that result into private health word18. Health below1 enters
fall death. Otherwise, unless already in31, it cleans up attack/carry state,
selects DAMAGE1/2 using original signed RNG remainder, sets knockback, creates
the impact effect, and chooses original collision mode. Existing hurt31 still
takes health and timer/filter effects but skips restarting hurt animation.

Hit categories also include original pickup behavior: type`0x100` invokes its
external pickup/powerup body; `0x40000` adds actor score+`0xf8`, invokes sound
and inventory bodies, and marks deletion according to `0x473ae0`; `0x10000`
heals up to100 or requests powerup`0x26bc` when its amount exceeds100;
`0x200000` adds health capped100; `0x100000` and `0x800000` add magic/pistol
ammo capped99. Signed caps, wrapping sums, full-health no-collection branch,
and object deletion timing are preserved. Pickup sound/inventory/resource
bodies themselves remain explicit dependencies.

## Hurt and death updates

Hurt31 carries platform deltas, updates animation before movement, and moves
horizontally only for marker1. Displacement uses wrapping32-bit speed×animation
delta, then **unsigned** division by1000 of the direction-adjusted magnitude;
it does not use the physics integrator or stage delta. After collision, airborne
mode4 clears support flag`0x10`. Animation completion cleans up using original
`0x4c8220` restore ordering and returns to standing geometry/timers.

Fall-death entry5004 sets logic+`0x20` to750, selects `CLAW_FALLDEATH` with
immediate update, mode4/zero actor speed/death flags, z8500 with its exact
conditional dirty flag, actor health0, private fall distance16=0, vertical
physics velocity0 and gravity2250. Its optional notice body, game audio/resource
stop, and powerup reset remain explicit original-address callbacks. Spike death
selects `CLAW_SPIKEDEATH`, installs original death/flicker words, optionally
creates the overlay effect, resolves/plays `LEVEL_DEATHTILE`, then requests the
same external resource operations. It does not copy fall entry's z/physics or
logic+`0x20` changes.

Fall updater5004 updates animation and physics, converts the **same Y delta
twice**, advances actor y by the first result, and increments private16 by the
second result plus1. The second conversion retains the first conversion's
fractional remainder; collapsing these calls changes behavior. Once signed
private16 exceeds800 and private6 is0, it completes the death. Spike updater5005
completes only when animation stopped flag is nonzero, frame index0, and the
same guard is0. Completion queries game mode: mode4 skips lives subtraction;
infinite-lives global`0x53722c` then adds1 regardless of mode. Death count
private32 increments with wrapping arithmetic.

Completion calls original `PostMessageA` with these exact fields:

| Field | Value |
| --- | --- |
| hWnd | Window token from original manager+4 owner's+4 |
| message | `0x111` (`WM_COMMAND`) |
| wParam | `0x8006` when resulting signed lives<=0, else`0x803a` |
| lParam | 0 |

It sets private6=1 **after** requesting the message. It does not immediately
assign respawn logic23 or implement game-over UI. Queueing and interpreting the
host command are separate boundaries; native adapters must not silently change
the callback's state/order by processing the queued command synchronously.
Original respawn state23 has its own separately recovered implementation.

## Context and dependencies

Extra context fields represent config token/config+`0x764`, player logic+`0x20`,
infinite-lives global, overlay object's+`0x44/+0xb0`, window token, audio manager
availability and resolved sound pool token. Invulnerability timer and common
bounds/cheats use `ClawPlayerInputContext`. Legacy shared `audioPosition` is
original **overall volume** global`0x532c10`, not positional audio.

Payloads are existing dependency `(entry,a,b,c)`; all omitted original scalar
arguments below are fixed and verified in tests:

| Entry | Payload / adapter boundary |
| --- | --- |
| `0x4a3050` | `(0,0,0)` shared original CRT RNG |
| `0x4061b0`, `0x4f6286` | `(nameAddress,0,0)` resolve audio/sequence token; spike lookup also supplies context.resolvedSoundPoolToken |
| `0x4208e0` | `(soundToken,overallVolume,0)` original pan/pitch/loop all0 |
| `0x4b45f0` | `(voicePoolToken,overallVolume,0)` original pan/pitch/loop all0 |
| `0x4c79e0` | `(sequenceAddress,immediateUpdate,0)` |
| `0x4c82a0` | `(animationDelta,0,0)` return original animation marker |
| `0x4c8220`, `0x420a10` | `(savedSequenceToken,0,0)` original restore variants |
| `0x421010` | `(carriedToken,0x4207a0,1)` |
| `0x420fc0` | `(carriedToken,0,0)` |
| `0x158`, `0x15c` | `(supportToken,0,0)` platform field reads; these are synthetic field operations, not routine addresses |
| `0x4cbb60` | `(x,y,8)` actor movement/collision |
| `0x461a00` | `(x,y,z)` impact object; original remaining args are style1 and current actor, with scene as leading argument |
| `0x461c40` | `(x,y,z)` spike overlay object with scene as leading argument |
| `0x2c` | `(attackerToken,0,0)` synthetic representation of actual attacker's logic virtual slot+`0x2c` |
| `0x10` | `(configurationToken,0,0)` original configuration virtual slot+`0x10`, returns game mode |
| `0x546d50` | `(windowToken,0x111,command)` imported PostMessageA operation; fourth argument0 |
| `0x41ebd0` | `(0,0,0)` original death notice/multiplayer message body |
| `0x4b7aa0` | `(0,0,0)` original game-manager call with argument0 |
| `0x41f990` | `(powerupID,duration,0)` powerup/resource transition |
| `0x41ee60` | `(attackerToken,0,0)` pickup handler, original actor/logic/private are implicit current state |
| `0x41d6f0`, `0x41f850`, `0x473ae0` | `(attackerToken,0,0)` pickup sound/inventory/query;473ae0 return controls deletion |

The common epilogue also calls existing powerup timer`0x41fc30`, weapon-cycle
sound`0x420910`, foot hazard query`0x4cd740`, and recovered spike entry`0x417c50`.
It executes the latter body directly in differential hazard tests. Configuration,
attacker, carrier and support snapshots must refer to their original-profile
tokens. Dependency callbacks may mutate live state; complete callback-entry
snapshot tests verify their ordering.

## Verified original strings

| Address | String |
| --- | --- |
| `0x5246d0` | CLAW_STAND |
| `0x5246e8` | CLAW_FALLDEATH |
| `0x5246f8` | LEVEL_DEATHTILE |
| `0x524708` | CLAW_SPIKEDEATH |
| `0x5247e0` | CLAW_DAMAGE2 |
| `0x5247f0` | CLAW_DAMAGE1 |
| `0x524800` | CLAW_HIT |
| `0x52480c` | CLAW_1110051 |
| `0x52481c` | CLAW_1110050 |
| `0x52482c` | CLAW_1110049 |
| `0x52483c` | CLAW_1110048 |
| `0x52484c` | GAME_HIT4 |
| `0x524858` | GAME_HIT3 |
| `0x524864` | GAME_HIT2 |
| `0x524870` | GAME_HIT1 |

All strings were read from the mapped hash-pinned original image.
Enemy sound paths use4061b0 for both random groups; projectile paths use
4f6286 for HIT4 and the second random group. This resolver distinction,
registry-disable behavior and RNG call ordering are preserved.

## Verification and limits

Run `work/test-env/bin/python Tests/compare_player_damage.py`.
The harness compiles into owned `work/player-damage-agent/` only.
It compares complete portable actor/private/physics/state bytes, all93 original
logic words, complete input/damage contexts, all128 attacker words, global
scratch/input/health/lives fields and ordered external events with complete
actor/private/physics/input/attacker/config snapshots at callback entry.
Each original adapted call validates its receiver and complete real argument
vector. Resource/object/message bodies above remain explicitly adapted.

Chained histories execute the **unmodified original CRT RNG body** and compare
its shared stream after every callback. Only its Windows TLS accessor
`0x4a7dc0` is adapted to a test TLS buffer, and that call is recorded; it is not
silently skipped. Native host RNG uses the original214013/2531011 recurrence.
Directed checks cover hit categories/flags, signed and zero damage, wrapping
health, active hurt/carry state, pickup caps, game mode/infinite lives, once-only
messages, support/flag hazards and common epilogue exclusions.128 cases run the
unmodified original Level1 collision resolver during hurt movement.

This establishes covered callbacks under the documented adapters, not original
hit-engine immunity/filter dispatch, impact/projectile/object lifecycle,
pickup inventory implementation, multiplayer death notices, audio resource
equivalence, Windows command processing/game-over UI or whole-game identity.
