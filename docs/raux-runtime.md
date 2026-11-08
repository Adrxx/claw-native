# Original Raux and CBoss runtime

This module translates the pinned original v1.0 Raux callback and its specialized methods. It does not import a reference game's boss implementation. The original EXE SHA256 is `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`; the disc REZ SHA256 is `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.

## Retail identity and creation

The registered name is `Raux`, ordinal25, literal `0x522d30`, callback `0x47e210`, flags0. Inventory of all fourteen original WWDs finds exactly one Raux: Level2, plane1, row552, offset341778, actor ID4880, `(23970,3947,0)`, images `LEVEL_RAUX`. The exact71 words/four strings and all-world inventory are captured in `work/raux-agent/records.json` and `inventory.json`.

The callback sets primary state1000 **before** allocating `0x478` bytes. It constructs `47e2d0`, invokes virtual slot10, then publishes the private pointer to primary18. State29 invokes cleanup20; state30 invokes method1c;1000 is inert. Other states invoke **cdecl** `4dc870(private)`; its receiver identity is0 and it has one argument, unlike a thiscall method. Callback EAX is1. Null allocation has an original unsafe dereference after the1000 store; native reports a fault after the matching prefix.

`47e2d0` inherits `40e0d0→44c000`, then uses vtable `50f1ac` and clears six additional words460..474. Its first460 bytes are CBoss/Human state, not a separate allocation. The inherited constructor supplies physics and hit/attack bindings. CBoss marks actor flag80000, visual flag2, captures initial actor x/y into private450/454, publishes actor5349dc and clears the gem latch45c. Raux selects `LEVEL_RAUX` and nineteen ANI references, falling back individually to `GAME_NULL`. It sets health100 and damage10 before multiplying by the actual float globals5262b4/5262b0 and truncating. Attack probability derives from5262b8; the unsigned `<100` branch stores99. Negative scales are not silently clamped.

Raux attack rectangle is `[-117,-4,-30,21]`, movement `[-15,-60,15,52]`, hit `[0,-60,20,35]`. The exact wrapper subtracts32 from the actor Y, calls world `4cd800(actor,0)`, sets actor mode1, then enters the registered `LS_STARTUP`. The ground-placement service decides the actual resulting Y; the fixture's declared transport changes Y by3 and is not a claimed retail floor location.

## API and composition

`Sources/RauxRuntime.h` exposes a C11 raw-token entry, a48-byte source-global view, private size and exact45-slot vtable mapping. The host supplies bounds-checked aligned word lookup and rich dependency calls with twelve argument slots and optional source name. Raw fields remain source identities. The native diagnostic is separate from the meaningful original EAX.

The following complete bodies are supported:

| Entry | Body |
|---|---|
|47e210 /47e2d0|Registered wrapper / specialized constructor|
|40e0d0 /40e1b0|CBoss constructor / attack rectangle initialization|
|40e280 /47e8e0|CBoss / Raux class lookup and state dispatch|
|40e560 /47eeb0|Restore captured physics position / scaled health reset|
|40e580 /47f020|Startup update / idle entry|
|40e5b0 /40e660|CBoss cleanup / death wrapper|
|420590|Live player primary state5010|
|47e7f0 /47e810|Deleting private wrapper / destructor order|
|47ece0 /47eef0|Raux pre-update decisions / hit selector|
|47f0c0 /47f160|Idle / home updates|
|47f290 /47f600|Jump-over entry / update|
|47f680 /47f6b0|High / low hit update wrappers|
|405060 /4208b0 /40abf0|Startup entry / hit rectangle / ground wrapper|
|4a07e0|Typed-hit adapter: attacker flag10000 then selfvirtual9c|

Animation and image composition flags run frozen `ActorAnimationRuntime`, `ActorResourceBindings`, `ActorWrapperRuntime` and the image index helper on the same raw buffers. The27-byte typed-hit adapter4a07e0 is additionally verified directly; Raux vtable slots30/34/38 elect it. It marks the supplied attacker for source deletion, then invokes the same receiver's virtual9c (Raux block-low entry440c90). Other inherited bodies use their exact function addresses so a live host can compose frozen HumanEnemy/HumanCombat/GenericEnemy/GenericEnemyStates/Rat mirror bodies. They are not replaced by guessed Raux mechanics. Sound resource532c10 is **overall volume**, not spatial position.

Required source aliases are listed in `ClawRauxGlobals`; raw `53c9c0` is the additional startup gate: only value2 invokes idle slot48. Class registries53c148(Raux),5349b8(CBoss),537878(Human),537638(CEnemy), and name registry537698 must use actual source registration metadata. Full recovered401000 registration gives IDLE2000,HOME2018,HITLOW2024,HITHIGH2025,STARTUP2028,JUMPOVER2029. These are source bootstrap evidence, not an assertion that the full retail WinMain/application startup was executed by these tests. Runtime alias/register rules remain the frozen registry host's responsibility. Raux's class overrides HOME,IDLE,JUMPOVER,HITHIGH,HITLOW; CBoss overrides STARTUP. Out-of-range lookup retains `4db6e0`, diagnostic4db5f0→544b14, `4db4d0`, defaultslot and second lookup ordering.

Boss death first calls Human44e0c0(mode). Only if player signed health>0 does it set player5010 and invoke `40e5c0(boss private)`. **40e5c0 and the gem lifecycle are owned by EndLevelGemRuntime** and are explicit Raux services. They must be composed in the live host; Raux does not synthesize a level transition. Cleanup calls Human44cfd0 before clearing5349dc. Private destruction preserves bitset→CString1a8→CString1a4 order and delegates physical heap release.

## Behavioral details and limits

The pre-update consumes a signed remainder `%3` and may change both stab/block sounds; choice2 preserves the previous block sound. Player facing/stance and relation3/4 gate a second `%100` decision. Distances0..99,100..199,200..499 elect44e620,455350,47f290 only in the source logic mode range. Home uses `%121`, mirrored rectangles and relation-specific attack/approach decisions, then calls Human44da20. Idle uses unsigned elapsed arithmetic and the raw541334 gate before its5-percent pacing decision.

Jump-over performs repeated tile queries, accepting1 then2 then3 followed by the empty tile above; query count/order is observable. TargetX comes from the actual min/max double bounds and source ftol before adding/subtracting20. The solver preserves each x87 operation rounded at the original53-bit precision, source signed-zero Z, square/add evaluation order,0.1 threshold and quarter acceleration branch. Ghidra's display reordered sums algebraically; instruction tracing, not that expression text, determines native evaluation order.

The tests declare physical resource dictionary/name transport, ground/collision/ledge signals, image pixels, audio/speech scheduling, loot/particle creation, registry storage, CString/bitset backing and physical free services. Full joins execute the original Human/Common code while native tests marshal the frozen snapshot APIs back into raw buffers. The empty core-registration profile and temporary stack bitset construction/release are explicit adapters; a real populated core-handler host must compose frozen CoreRegistration/ActorDestruction. Canonical shared API events compare named transport rather than temporary source string pointer arguments; specialized Raux dependency arguments retain their exact raw ABI. No full retail boss arena, all-level gameplay, rendering, menu/outro or full-game identity claim follows from these bounded tests.

## Validation

Run `work/test-env/bin/python Tests/compare_raux_runtime.py`. It compares the complete512KiB heap and192KiB source global span at each return and ordered service boundary, tracks resource/query/random consumption and checks meaningful scalar results. It includes constructor resource misses/scales, all specialized state paths, simultaneous pre/hit conditions, seeded jump math, actual WWD/retail resources and retained full original callbacks using frozen shared bodies. Retained RNG tests execute original4a3050 with only CRT thread lookup adapted; native uses the matching214013/2531011 LCG and compares the seed word. Allocation/null-private unsafe prefixes run with a separate valid TEB and unmapped zero page.

`work/raux-agent/run-sanitizers.sh` replays a private binary corpus of original-matched calls under ASAN/UBSAN, validating ordered complete-buffer service digests and final words. That private corpus includes original PE input and is not a distributable source artifact. C11 header, C++ warning/FP settings, Python syntax and Swift header checks are also run. Final counts are recorded in `work/raux-agent/verification.json` and the worker handoff.

Final verification: **4,105 normal whole calls**, **28,561 ordered complete-buffer events** (including the one service event in three separately measured unsafe prefixes), **5,119 executed original addresses**. Twelve172-frame retail-record histories and five60-frame grounded own-state histories compose the frozen inherited bodies. The real resource profile contains47 original Raux PIDs and22 ANI groups/73 records, including GAME_NULL. ASAN/UBSAN replay passes332 original-matched calls and2,332 ordered service snapshots. C11, C++ warnings/FP, Python syntax and Swift header import checks pass. This freezes the additive Raux files for parent integration; no Mac/iPad UI or retail Level2 arena acceptance is claimed.
