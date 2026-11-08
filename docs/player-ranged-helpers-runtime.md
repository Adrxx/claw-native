# Original player ranged helper bodies

`PlayerRangedHelpersRuntime.h/.cpp` recovers four complete original retail v1.0 entries. The executable SHA256 is `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. True entries and calling conventions were checked against standing/duck callers and original instructions, then exported with the pinned Ghidra script in a private project. No shared project or frozen source was edited.

| Entry | Whole bytes | Source behavior |
| --- | --- | --- |
|41c9f0|184|PistolBullet emit; signed facing speed±700, conditional signed-positive pistol decrement, repeat serial, damage8 and GAME_BULLETS binding|
|41cab0|197|MagicBullet emit; conditional signed-positive magic decrement, speed±700, magic type/flag8, damage25, repeat serial, live-facing flip|
|41cb80|220|Dynamite emit; wrapped signed charge/idiv, clamp0..200, unconditional wrapped dynamite decrement, actor158 signed launch-distance, damage15|
|41cc60|532|Marker5 elemental sword emit, selected only by powerup26b8/26b9/26ba; element bit, gated sword sound, magic type/flag8/damage25/repeat/facing|

Every entry is **cdecl(actorToken,primaryToken,playerPrivateToken)** and returns meaningful success0/1. `primaryToken` is present in the original caller packet but is unused in these bodies; directed comparisons pass unmapped values there. It is not an ECX receiver. Private fields are read at their original offsets, including facing0, muzzle54/58, ammo70/74/78, repeatseriale8 and charge100/104/108. These are borrowed player fields, not a new allocated private object.

All named creation calls preserve `(id0,x,y,z,nameToken,flags40000)`. Pistol uses z-1; all other emits use z+1. Position, offset and charge arithmetic wrap in32 bits. Private/actor values reread after creation preserve callback mutation: direction sets the captured speed before the callback, while later magic/elemental flip and repeatserial read current private values. Dynamite's denominator0 becomes1; `INT_MIN/-1` traps in the original before any creation. Native fault2 reports that exact reached prefix. It never fabricates a successful throw.

Marker5 maps26b8→FireBullet522df4/callback410100/bit40000/soundCLAW_FIRESWORD5247b0,26b9→LightningBullet522de4/callback4101c0/bit100000/soundCLAW_LIGHTSWORD5247c0,26ba→IceBullet522dd8/callback410280/bit80000/soundCLAW_ICESWORD5247d0. Other powerup values return0 with no creation. The source writes the element bit **before checking createdToken**. A failed elemental named creation therefore faults at a null receiver; native missing-span fault1 preserves the preceding stores/events. Sound lookup is skipped if live scene sound manager+30 is nonzero. Otherwise the resolved voice plays through4208e0 with the current master volume, reread after lookup. No ammunition is consumed by elemental emission.

## Host API

```
claw_player_ranged_helpers_entry(function, args, 3,
    &context, dependency, user, &originalEAX)
```

Context contains `ClawSceneActorHost`, an8-byte borrowed `ClawPlayerRangedHelpersGlobals{powerup,masterVolume}`, optional creation/image composition flags and diagnostic fault. Raw globals are original534eac and532c10. The owner must maintain these aliases during callbacks; there are no new defaults or clocks. Full C layouts on this host are globals8/context72/call72 bytes. Return1 means supported/completed; inspect fault and use the separate original success scalar. Unknown function returns0. Invalid argument counts are native fault3, not an original gameplay branch.

Rich dependency calls preserve receiver, all arguments and source resource/name literals. Route4c8da0 to the existing scene named creator,4c7970 to image binding,4f6286 to the source dictionary transport and4208e0 to audio. `composeCreation` joins frozen SceneActorRuntime including common actor/primary construction, list insertion and caller flags. Allocation/free forward through the supplied host or exact4f63ec/4f6428 services. `composeImages` joins frozen image binding/default indexed frame lookup; it requires the existing portable128-word actor backing, distinct from the actual1b4-byte actor allocation. Original primary allocation is174 bytes.

Creation flags40000 do not elect an immediate callback. The host attaches the correct component and the ordinary source scene frame later elects its registered callback. Already-frozen downstream Pistol40ff80/private150, Magic410040/private158 and Dynamite43a850/private188 belong to PlayerProjectileRuntime. **Elemental callbacks410100/4101c0/410280 are not in that frozen module; their startup/private sizes/flight must remain explicit until independently recovered.** This module does not guess them or invoke their startup early.

## Proof and boundaries

`Tests/compare_player_ranged_helpers_runtime.py` executes each complete unchanged original body and compares meaningful EAX, the complete256KiB raw heap plus192KiB live globals, and ordered complete snapshots at every retained service boundary. The matrix covers facing, signed/wrapped ammo, zero/signed charge denominators, charge clamp, missing/present resources, named creation failures, callback mutations, unused primary arguments, aliased created actors, raw image-ID gaps and joined real scene creation. Full original scene creator/construction/list instructions execute in the joined profiles. Physical allocator/name dictionary/image transport remain declared profiles.

Ten retained original-disc ANI histories join actual419fd0 duck and41c5a0 standing callbacks with frozen PlayerPoseStates/PlayerAttackInput, actual ActorAnimationRuntime, and the new helpers. DUCKPISTOL,DUCKMAGIC,DUCKPOSTDYNAMITE,DUCKPOWERUPSWIPE and POWERUPSWIPE ANI records elect firing/deduplication/marker5. Pistol repeat/seek uses frozen exact420970, with no duplicated seek body. These caller histories use an explicit grounded movement transport and raw ANI image table transport; they are not a new whole-level collision, raster or gameplay acceptance claim. ANI hashes/record counts/markers are retained in `work/player-ranged-helpers-agent/asset-profile.json`.

Three elemental null-creation prefixes, one signed-idiv exception and four service-cancellation prefixes compare complete reached buffers/events. Windows FS/SEH uses a separate emulated TEB when address0 is unmapped. Normal actor/primary creation is composed; full downstream projectile startup/flight/collision/destruction remains with the frozen projectile owners. Physical audio and elemental gameplay are explicit boundaries.

Final original evidence: **2,188 whole calls,2,927 ordered complete snapshots,1,247 original instruction addresses,10 real ANI histories and8 failure prefixes.** Strict C11 and Swift ASAN raw actor/private/unused-primary/serial/creator callback checks pass. C++ ASAN/UBSAN replays the selected original-paired complete buffers and service mutations; it complements rather than replaces the original instruction suite.

Run:

```
work/test-env/bin/python Tests/compare_player_ranged_helpers_runtime.py
work/test-env/bin/python work/player-ranged-helpers-agent/compile_replay.py
clang -std=c11 -Wall -Wextra -Werror -fsyntax-only -I Sources work/player-ranged-helpers-agent/abi.c
```

Frozen handoff: C++ ASAN/UBSAN **21 complete calls/41 full-state events** passed. Header SHA256 `e89f5a5dc171aeba92ea361f33a680cc930786163175fa923b107d341327a780`; implementation SHA256 `5f9f19bfce8d3919969ce2804fed65e29f86cb72ba3357f251fb88c4cc7b8572`. Parent owns native registration and shared caller integration after this freeze.
