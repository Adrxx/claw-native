# Original Katherine boss runtime

The retail v1.0 registry names this boss **Katherine**: ID37, literal `0x522c9c`, cdecl actor callback `0x453d30`, flags0. The source executable is SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. This module is a source-instruction reconstruction, with a raw heap interface. It does not establish whole-game or physical presentation parity.

The original-disc Level4 world contains one Katherine record: plane1, record106, x18586/y1762, image `LEVEL_KATHERINE`, health property200. Its compressed WWD is SHA256 `d6f4117a18972e6b4daf8fcf3abae8971d20a7c87c0b385cb3ed06392d1215fc`. `work/katherine-agent/wwd-records.json` retains the original71 words and four strings. The constructor replaces health with `ftol(100*healthScale)` and damage with `ftol(10*damageScale)`, rather than preserving that health property. It allocates exactly `0x478` bytes,286 words. Words at460/464/468 select Flip1/Flip2/Flip3 ANI;46c/470 are cleared. **474 remains unwritten by the Katherine constructor.** Inherited CBoss prefix is460 bytes. The inherited Human pointer view uses264 words plus20 tail words; retain both derived words beyond that prefix.

## Owned whole bodies

| Address | Source role |
| --- | --- |
|453d30|Registered callback:0→primary1000→allocate/construct→virtual10→publish private;29 cleanup;30 render callback;1000 skip; otherwise generic tick|
|453df0|Full derived constructor1267 bytes; shared CBoss base, ordered images/ANI/sounds, rectangles/scales, initial grounding/startup|
|4542f0 /454310|Scalar deleting wrapper30 bytes and destructor108 bytes; original bitset/CString destruction order, optional free|
|4543e0|Katherine class dispatcher272 bytes; class537980 table lookup/growth/diagnostics, CBoss fallback|
|4547c0|Pre249 bytes; shared Human pre, signed RNG block sound selection, exact name-pointer and facing/distance/armed gates; pending455350|
|4548c0|Hit324 bytes; invulnerability500, raw name-array/pending-CString work, text hit-state gates, block or inherited hurt/damage/particle path|
|454a10|HOME383 bytes; source facing, distance and relation branches, speech selection, rich strike1/strike2 calls or jump/back/patrol|
|454b90 /454c20|Idle entry141/update112 bytes; zero horizontal velocity, source ID/name/ANI, speech and random patrol gates|
|454cb0|Jump1070 bytes; signed random distance, horizontal/foot clearance queries, distinct left inlined/right420dd0 physics, state/flag/ANI/sound order|
|4550e0|Mirror331 bytes; embedded rect unconditionally, actor flags, source rereads, actor rectangles except INT_MIN sentinels|
|455230 /455280|Jump69 bytes and flip-entry73 bytes; animation, grounded velocity reset, source FLIP3 transition|
|4552d0|Flip update123 bytes; stopped/index0 gate, flag clear, random speech, priority2 and HOME virtual|
|455350|Verified5-byte pending tail thunk to self virtual60; no inferred attack body|
|455360 /4553a0|57-byte wrapper ANI select/eager update;37-byte state setter/previous-state publication|
|40f780|44-byte embedded actor sound dictionary getter, preserving BOOL/out lookup transport|

The rejected Ghidra request454970 was inside4548c0, not a function. It has no implementation or recovery claim. Other entry boundaries came from actual original registry, vtable and direct callers. Private analysis is under `work/katherine-agent`; shared Ghidra was not opened.

Full source401000 bootstrap supplies class537980 with LS_JUMP→455230, LS_FLIP3→4552d0, LS_HOME→454a10 and LS_IDLE→454c20. CBoss class5349b8 supplies LS_STARTUP→40e580. ID CString tokens are allocated heap data; matching text does **not** make them equal to original literals. Pre4547c0 compares its incoming token against literal527204/528454/52720c. Tests use the actual full-bootstrap heap tokens and directed literal identities separately.

## Raw integration

`claw_katherine_entry(function,receiver,args,count,context,dependency,user,result)` accepts original receiver identity and stack arguments. Cdecl453d30 uses receiver0/one actor argument. `claw_katherine_function(0x50e2a4,slot)` exposes45 verified vtable entries. The return value is native support/completion; check `context.fault`. Meaningful original EAX is returned separately (callback1, constructors/deleting wrapper private token, getter resource token); source void methods normalize to0.

Context borrows `ClawRauxGlobals` (48 bytes), a live `ClawSceneActorHost`, and optional real ANI/image composition. It adds no clock or RNG defaults. Owner must keep globals synchronized with raw5371fc/537e88/537210/5430c4/534eac/532c0c/532c10/541334/5349dc and scales5262b0/b4/b8. Raw53c9c0 supplies the CBoss startup gate; only actual value2 elects idle. Raw513e20 supplies the left jump threshold. Class arrays537980/5349b8, source name trie537668, ID CString array537698, and pending construction5376b4/b8 remain live addressable spans. Shared strike counter52713c must be exported/imported in inherited strike adapters. Actor/primary/secondary/contact and286 private words share the same live identities.

The rich dependency preserves up to12 arguments, receiver and optional human-readable name. Unknown bodies remain exact address calls. Route44c000/44d000/44c840/44d3c0/44df60/44e0c0/44cfd0 etc to frozen HumanEnemy;44f3c0/44f510 and typed combat to HumanCombat;43ee10/43eee0/43f030 to HumanoidStrikeRuntime; inherited motion/FSM to frozen GenericEnemy/GenericEnemyStates/CommonEnemyEntries/EnemyMotionAux. Route40e5c0 to EndLevelGemRuntime. The module directly composes frozen Raux CBoss methods, the raw common tick dispatcher, ActorWrapper getters/setter, optional ActorAnimationRuntime and image binding. It does not copy those bodies.

Direct tile4cda10/4207f0/4cd800, RNG4a3050, dictionary4f6286, audio4208e0/4b45f0 and speech48ceb0 are exact services. The source left target intentionally preserves x87 operation ordering, negative zero for negated Z and unordered threshold behavior; the right source420dd0 uses the frozen physics retarget. Both paths have complete-buffer original checks. Allocation failure at453d30 leaves primary1000 and reaches an unchecked virtual read. Native missing-span fault stops there; it does not invent recovery or a successful actor.

## Evidence and limits

`Tests/compare_katherine_runtime.py` runs unchanged original executable instructions under Unicorn with retail CRT53-bit precision. Every service event compares the complete1MiB fixture heap plus192KiB live global span, not just selected fields or a digest. Physical Windows SEH uses a distinct TEB in null-pointer tests. Temporary inherited CString/bitset lifetime helpers that are composed internally are consistently normalized; resource dictionary annotations preserve exact names and raw arguments in the specialized graph. The joined inherited model uses frozen Human/Common/Combat/strike APIs and actual class/name tables. This is not a new independent recovery claim for those modules.

The actual Level4 fixture uses source WorldObject loading,384×120 cells and602 original tile descriptions; ground placement, horizontal checks and foot probes execute real original helpers. It binds44 original PID header geometries and19 real ANI groups (18 Katherine plus GAME_NULL), including image-ID gaps and source record/audio tokens. Asset hashes are retained in `work/katherine-agent/asset-profile.json`; filesystem name/enumeration and dictionary bindings remain an explicit transport. It exercises retained constructor/startup/jump/landing/FLIP3/HOME/strike/hurt/fatal-health/death/cleanup/free histories and complete ordinary callbacks with inherited movement/collision. The class-only landing-history source ground election is injected explicitly; separate full-frame histories execute real collision.

CBoss40e660 publishes player5010 before the exact EndLevelGem once-latch creator. In this boss suite, the physical named creator returns a fixture actor and a declared initializer callback; the frozen EndLevelGem creator/retarget is composed and compared. Complete real gem/pickup/restore lifetime is independently proved by EndLevelGemRuntime, and is not claimed anew here. Loot42df90, particle461a00, physical voice/speech, player hit election, and the scene/global command/render loop remain identified services. No physical audio, raster or complete Level4 encounter acceptance is claimed.

`work/katherine-agent/verification.json` holds measured counts. Strict C11 raw layouts are48/72/72 bytes for globals/context/call. Swift ASAN checks raw286-word bounds, resource-free mirror/state callbacks and the retained474 sentinel. C++ ASAN/UBSAN replay checks selected original-paired calls and complete callback snapshots while replaying only declared service outputs/mutations; it does not substitute for the original-instruction suite.

Run:

```
work/test-env/bin/python Tests/compare_katherine_runtime.py
work/test-env/bin/python work/katherine-agent/compile_replay.py
clang -std=c11 -Wall -Wextra -Werror -fsyntax-only -I Sources work/katherine-agent/abi.c
```

Final frozen evidence: **2,266 whole original calls,11,407 ordered complete snapshots,5,779 original instruction addresses**, one actual null-allocation prefix, eight retained class/combat lifetimes and four150-frame ordinary callback histories. C++ ASAN/UBSAN:43 calls/247 complete-state events. C11 and Swift ASAN passed. Header SHA256 `b7488d962f6dc9b496dcbfb114368ae48ed6d2adb90db52b659ff79932bab66f`; implementation SHA256 `6b1a58cd3afe4d151b35f85e836c32a80590b0717f9c5f41d5ef6d6748ebce88`. These files are frozen for parent integration.
