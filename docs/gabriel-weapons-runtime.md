# Original Gabriel weapon closure

This additive module recovers the remaining GabrielCannon/GabrielBomb bodies and the source-elected CannonBall. It composes the frozen Gabriel boss/core, PlayerProjectile/Bullet/shared physics, ActorAnimation, ActorWrapper/SpriteGeometry, image binding, and generic actor lifecycle. It does not edit those modules or implement a substitute boss arena.

The oracle requires the original v1.0 EXE SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263` and disc REZ SHA256 `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`. Execute `work/test-env/bin/python Tests/compare_gabriel_weapons_runtime.py`.

## Source inventory and host recipe

| Registered name | Ordinal / callback | Flags | Private bytes / constructor / vtable |
|---|---|---|---|
| GabrielCannon | 70 / `446550` | 0 | `98` / `446a70` / `50df44` |
| GabrielBomb | 72 / `4459d0` | 0 | `198` / `445ef0` / `50ded4` |
| CannonBall | 14 / `414b20` | 0 | `150` / `414be0` / `50ba04` |

All sizes and addresses are hexadecimal. CannonBall is created by both inherited Cannon firing states; it is not a guessed replacement projectile. The all-14-world inventory has exactly one GabrielCannon WWD row: Level8, main plane1, row1293, ID2698, `(43203,5184,1000)`, `LEVEL_GABRIELCANNON`, with render flag2. Gabriel itself is row1511, ID2618, `(43223,5068,2000)`. GabrielBomb has no static WWD row; the boss creates it dynamically. The prior core's adjacent `446ef0` listing is unrelated LevelComplete/menu code and is excluded here.

`claw_gabriel_weapons_entry(function, receiver, arguments, count, context, dependency, user, result)` uses raw32-bit pointer identities. The new header is C11 and imports frozen Gabriel/Bullet context types. Supply:

- `scene.lookup`, returning aligned word spans that respect real allocation sizes, plus original raw class/name tables, vtables, actor/primary/secondary/contact objects, world/plane pointers and resource objects.
- Borrowed `ClawRauxGlobals` with exact tick537210, animationDelta5430c4, audio gate532c0c, overall volume532c10, and manager/player/CBoss aliases. Direct raw cell53774c contains **Gabriel-private**, distinct from generic boss-actor5349dc.
- Borrowed `ClawBulletContext`/`ClawGenericEnemyContext` with the actual source default words and original Projectile state table. Its generic state profile remains caller supplied. Each composition copies the borrowed context before refreshing live receiver identities, so nested CannonBall construction does not overwrite the outer context.
- Enable `composeCore`, `composeProjectiles`, `composeAnimation`, and `composeImages` for native closure. Zero flags retain the exact external address service at the respective boundary. `maximumSteps=0` uses65536. Unknown entries return0 without claiming completion; require `fault==0`. Fault1 is a missing span/service,2 a diagnosed unsafe source prefix,3 an ABI/loop rejection. Meaningful original EAX is separate from native support.

Registered facades are original **cdecl** `(actor)`: receiver0, args[actor]. Constructors are thiscall `(actor)`. Selectors4141f0/445af0/446670 take one captured numeric state. Other specialized entries use private receiver with no arguments. Retarget446130 is frozen core thiscall `(signed relativeX)`. Source4dc870 is cdecl receiver0,args[private]; the module adapts that into the frozen native projectile entry ABI. Generic deleting destructor484d90 takes `(flags)` and preserves the original receiver EAX.

Full captured startup bindings are pinned in `work/gabriel-weapons-agent/registrations.json`, extracted from the unchanged original401000 bootstrap evidence. The resolved closure is:

| Raw class | ID / source name | Function |
|---|---|---|
| 534bf8, inherited Cannon | 2018 LS_HOME | 4145f0 |
| 534bf8 | 2027 LS_FIRING | 4146b0 |
| 534bf8 | 2032 LS_VERTFIRING | 4148b0 |
| 537788, GabrielCannon | 2018 LS_HOME | 446ca0 |
| 537788 | 2081 LS_ROTATE | 446eb0 |
| 537758, GabrielBomb | 2002 LS_EXPLODING | 4463f0 |
| 537758 | 2001 LS_FALLING | 446490 |
| 534910, inherited arching projectile | 2001 LS_FALLING | 4089d0 |
| 538428, Projectile | 2001 LS_FALLING | 4742f0 |

These are captured boot-profile identities, not a claim of full Windows application/arena startup. Preserve actual CString objects/name pointer identities from the registry. Shared FSM captures state before pre and uses that captured ID for dispatch/post. The Cannon/Bomb class selectors remain the frozen core's exact double-query/fallback bodies; Cannon missing state calls actual4a36f0 rather than silently completing.

## Owned bodies and behavior

New whole bodies:414030,4141f0,4145b0,4145f0,414640,414660,4146b0,414860,4148b0,414a60,414b20,414be0,446a70,446c20,446ca0,446d70,446e10,446eb0,445ef0,446340,4463f0,446490,432550,432560. Embedded attack rectangle setter40fe90 is composed as its observed four stores; the original CRect/import transport remains declared in the oracle. Frozen facades4459d0/446550, selectors445af0/446670, retarget446130 and the shared projectile/lifecycle entries are composed, not relifted.

Base Cannon414030 sets actor speeds500/0 only when zero, damage10 when zero, default Z3990 only when zero, dynamic/rendering flags1/40, and offsets50/10/-26/-10. Its mirror helper preserves sentinel rectangles, wraps unary negation, and separately negates positive speed/offsets. Standalone base HOME polls an unsigned elapsed timer and selects a firing state every3000ms. Gabriel's override instead follows live boss fields518 fire request,51c rise request,534 bit0 reset,520 terminal. Reset clears8c/90, clears live boss requests/reset bit, selects imageID1, then enters HOME. It re-reads the raw global alias between original stores/calls.

GabrielCannon's constructor looks up HORZFIRE, VERTIFIRE, RISE, REST; it does **not** choose the existing HOME.ANI. Field48 stays0 from the base, so HOME selects null ANI and reset image1. Its offsets are50/54/-26/-10, with render2 setting X offsets-50/+26. RISE selects LS_ROTATE and speeds0/-500; REST selects LS_ROTATE and speeds-500/0. A fire marker1 creates a real CannonBall with original six creation arguments, invokes its registered callback, writes double velocity from live Cannon speeds and zeroes its vertical gravity. A negative X speed mirrors private and all eligible actor rectangles after creation. The completion flag returns the Cannon to HOME. Vertical fire uses the alternate X/Y offsets; it is not an inferred trajectory.

CannonBall binds exact literals52458c=`LEVEL_CANNONBALL` and524574=`LEVEL_CANNONBALL_FALL`, inherits Bullet physics/FSM, sets D0=40/D4=2, damage10 when zero, and gravityY0. Actual source initial primary limit fields2c/30/34/38 are preserved; the finite creator profile clears them through the frozen generic initializer. Random uninitialized state words are not a valid substitute for that creator profile.

GabrielBomb inherits the source arching projectile, sets a[-50,-50,50,50] attack rectangle, D0=40, damage15 only when zero, actor164|2020, no bounce allowance, timeout10000, CC7, and first-whistle/explosion latches0. FALL and its inherited fall ANI field both reference LEVEL_GABRIELBOMB_FALL. All three whistle fields use **BOMBWHISTLE1**, despite WHISTLE2/3 files existing; no spelling/variation is invented. Explosion sounds use SEXPLOSION1/2/3. RNG is signed `%3`, including directed negative inputs; consume it even when audio is disabled. Falling whistles once, then, only with a live nonterminal boss, updates ANI and compares actual doubleY against signed boss530. Explosion is the actual virtual2c path. It sets actor flag4/D01000000/privateC8=1, selects EXPLODE, and elects one sound. First marker1 clears actor flag80; completed nonlooping ANI sets10000. Boss terminal state makes either update set80 then10000 without the normal ANI work. No guessed screen pulse/fuse is added.

Actor source allocation is exactly0x1b4/109words. Frozen portable snapshot APIs have128-word compatibility storage; the composition creates a128-word **local** actor shadow, imports/exports109words, and flushes that prefix at dependency boundaries. It never requires an enlarged live allocation. Private prefix imports likewise preserve the real38/84/102-word allocations and later Bomb fields.

## Evidence and boundaries

Final oracle: **3,962 normal unchanged-original calls,3,816 ordered full snapshots,3,429 original instruction addresses**, comparing complete512KiB fixture heap plus192KiB raw globals on every boundary and final return. It includes seeded whole constructors/missing resource transport profiles, directed complete states, signed RNG/mirror/sentinel/unsigned clock-wrap cases, real disc ANI/PID histories,16 marker→CannonBall constructions, whole facades/FSM,8 actual Cannon WWD controller/fire/reset histories, explicit generic cleanup/delete, and5 unsafe null allocation/creation prefixes.

The retained collision fixture executes whole original4cbb60 on the original side and frozen native CollisionResponse on the native side, with explicit512×512 empty/solid tile descriptions and actor population0. Four histories assert actual deletion: CannonBall via wall-impact10000, Bomb via source threshold→EXPLODING→marker latch→ANI completion. This finite tile fixture is distinct from the retail Level8 arena's complete collision/residency acceptance.

ASAN/UBSAN passes238 measured source replays and801 ordered full snapshots in each of the ordinary and exact-allocation executables. It replays the measured source comparisons and event patches. A second replay stores actor/private/logic buffers in independent allocations of exactly1b4/98/198/150/174bytes, rejects out-of-allocation spans and compares the same complete heap snapshots. C11, warning-clean C++17, Python and an executed Swift importer/API check pass. Replay counts are recorded in the adjacent private sanitizer logs; replay uses explicitly captured transport outcomes, not a second assertion that physical services are native.

Physical4f63ec/4f6428 allocation/free,4c8da0 named actor/list creation,4c7fa0/4c8060 generic metadata binding, dictionary4f6286 and4dba00/name CString transport, graphics/sound pool4b45f0/animation-event transports, and any elected unsupported common method remain explicit address/receiver/argument services. The source actors and their inherited native bodies are not replaced by terminal-success stubs. Tests compare allocation/creation failure's already-written prefix against the original's fault; native diagnostics do not turn that fault into gameplay success. Arbitrary malformed raw pointers, NaN/invalid physics setup, physical audio/renderer equivalence, full Windows CRT/application startup, actual Gabriel arena/player acceptance and all-level completion are not established by this module.
