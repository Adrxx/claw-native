# Original sound-trigger and ambient actors

`Sources/SoundTriggerLogicRuntime.h/.cpp` recovers **39 complete bounded original methods**, plus the actual inline ambient-manager constructor stores. It composes the frozen EnemySpeechRuntime queue and speech-actor bodies over shared live raw buffers. Physical audio, generic list allocation/storage, raw resource-name transport and CRT RNG remain explicit services. Original executable SHA-256 is `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`; real REZ SHA-256 is `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.

## Registered callbacks and Level1 scope

These identities come from the frozen original LogicRegistry, not address/name guesses:

| Callback | Original address | Actual Level1 records |
| --- | --- | ---: |
|SoundTrigger|48c1e0|25|
|BigSoundTrigger|48c410|21|
|SmallSoundTrigger|48c430|7|
|HugeSoundTrigger|48c450|0|
|TinySoundTrigger|48c470|0|
|TallSoundTrigger|48c490|0|
|WideSoundTrigger|48c4b0|0|
|ClawDialogSoundTrigger|48c8f0|0|
|ClawDialogBigSoundTrigger|48ca40|1|
|ClawDialogSmallSoundTrigger|48ca60|12|
|ClawDialogHugeSoundTrigger|48ca80|0|
|ClawDialogTinySoundTrigger|48caa0|0|
|ClawDialogTallSoundTrigger|48cac0|0|
|ClawDialogWideSoundTrigger|48cae0|0|
|GlobalAmbientSound|402ca0|4|
|AmbientSound|402cc0|2|
|AmbientPosSound|402e00|0|
|SpotAmbientSound|402e20|9|

The eight present families total **81 of1479 records**. All81 actual records and their raw-byte SHA-256 are captured in private `work/sound-trigger-agent/level1-records.json`. Closely related zero-count wrappers have directed original comparisons, but no Level1 population is attributed to them.

## API and shared aliases

```c
uint32_t claw_sound_trigger_entry(uint32_t function, uint32_t receiver,
    ClawSoundTriggerArguments args, ClawSoundTriggerContext *context,
    ClawSoundTriggerDependency dependency, void *user, uint32_t *originalResult);
uint32_t claw_sound_trigger_construct_manager(uint32_t token,
    ClawSoundTriggerContext *context);
```

The argument struct contains **nine32-bit words and count**. Callback actors preserve their original cdecl ABI: receiver0, one actor-token argument. Helper calls preserve their original receiver and arguments. Function support/completion is separate from meaningful original EAX. Unknown functions do not alter result/context; wrong argument count produces native fault2. Never cast a native pointer into an original token. Host lookup returns live aligned word spans, allocation returns a raw token, and free follows original ordering.

Context references `ClawEnemySpeechGlobals` directly:

| Shared field | Original global |
| --- | --- |
|managerToken|5371fc|
|playerToken|537e88|
|audioManagerToken / nonzero availability|532c0c|
|clawBusy / clawActorToken|53c9a0 /53c9a4|
|enemyBusy / enemyActorToken /speakerToken|53c9a8 /53c9ac /53c9b0|
|stageDelta|53720c|

Context additionally keeps masterVolume532c10, triggerProfile53c9b4, ambientProfile534810, composeSpeech and fault. Preserve diagnostic globals across calls. They record wrapper selection, but rectangle helpers select their actual bounds from **primary+10 callback identity**, not the diagnostic. Nonzero composeSpeech invokes frozen48c820 on those same globals/live heap. Zero explicitly forwards48c820 to the dependency rather than simulating acceptance.

Raw owner/manager/token aliases are supplied by the host. The ordinary application manager+10 gates ambient playback; manager+5c identifies the ambient manager. That object's+0 is the original sound-controller token, and the controller+2c supplies the physical audio collection used by flush/stop services. These are distinct from the global audio availability test. Original53720c stage delta drives repeated ambient timers; animation delta5430c4 and OS time are not substituted.

The dependency event carries function, receiver, up to nine arguments, and optional writable synchronous temporary words. Any actual adapted stack pair/rectangle argument uses token0 and the temporary span instead of exposing a native pointer as an original address. In the recovered ambient graph those stack pairs/rectangles are consumed inside native helper bodies, so no physical dependency owns or retains them.

### Complete helper inventory

In addition to the18 callbacks:

| Entry | Receiver / arguments |
| --- | --- |
|48c4d0 /48cb00|cdecl(actor,primary); source rectangle selection|
|4022f0 /402370|ambient manager / pool, volume, rectangle-or-point, scale, reserved; five-word factory|
|402400|ambient manager / pool, volume, rectangle, scale, onMin, onMax, offMin, offMax, reserved; nine-word repeat factory|
|402610 /402a60|object / pool, volume, baseVolume, rectangle-or-point, scale; initialization|
|4023f0 /4022d0|object / none or deleteBits; body/deleting destructor|
|402720 /402ac0 /402f10|object / centerX,centerY,refresh; rectangle/spot/repeat updates|
|402840 /4028c0|object / percent,delay,stop or play,percent,delay; volume and playback/fade control|
|402240|manager / soundController,baseVolume; initialization|
|402270 /4022a0 /402520 /402570|manager / none; cleanup/clear/stop/refresh|
|4025c0|manager / centerX,centerY; complete ordinary ambient frame update|
|4f5133|embedded CPtrList / grow; complete raw constructor|

The actual factories have an additional unused final parameter that Ghidra's inferred prototype omits:4022f0/402370 pop20 bytes,402400 pops36. These words count in the public ABI. Spot updater402ac0 similarly pops12 bytes even though its third argument is unused. The native entry preserves the observed arity instead of accepting the shorter decompiler prototypes.

## Exact trigger behavior

Initialization sets actor+d0 to04000000 and hides the actor through actor+40 bit1. SoundTrigger flags become `(flags & ~2) |1`; ClawDialog flags OR1. Zero actor+108 becomes99999. Both enter primary state5.

Rectangle helpers overwrite actor+128..134 with centered source bounds: default±64, Big±128, Small±32, Huge±256, Tiny±16, Tall x±32/y±100, Wide x±100/y±32. The callback pointer determines the variant even if a different wrapper is invoked directly. Ordinary SoundTrigger uses these bounds too; the original WWD rectangle is not retained as its active trigger size.

State5 tests **inclusive** signed bounds translated by wrapped actor x/y against the global player's coordinates. SoundTrigger submits4b45f0 only when actor+184 sound and global532c0c are nonzero. It then consumes charges independently of audio success: charge1 marks actor flag10000 for deferred deletion; signed charge>1 decrements; other signed charges retain their value. It captures player's primary+14 private+80 into primary+64 and enters state23.

For SoundTrigger only, chargeFFFFFFFF plus nonnull sound switches to state11 and stores pool+28 duration+100 at primary+20. **The callback does not decrement/check that timer in state11**: its rearm gate is the player leaving the rectangle. In state23, a change in the player's private+80 checkpoint word rearms state5. Nothing here guesses a timer-based replay.

ClawDialog state5 calls original48c820(sound,force0), then consumes charges and enters state23 regardless of the queue result. Charge1 marks deletion; every other charge decrements, including zero and negative values. This differs from SoundTrigger. Absent/busy speech actors and excluded player states therefore can reject the queue while still consuming the trigger. Frozen EnemySpeechRuntime preserves those gates; it does not directly play the sound. The separate48c630 actor schedules voice playback and counts down speech duration.

## Exact ambient behavior and manager creation

AmbientSound initialization sets hidden/invisible bits, sets global-style flag2 only when primary callback is402ca0, and otherwise clears it. It copies the actor+128 rectangle; positive primary+2c or+30 overrides that rectangle with primary+2c/+34/+30/+38. It creates a64-byte ordinary object, or88-byte repeated object when signed actor+11c>0. Positive actor+13c adds the secondary rectangle from actor+138..144. It marks the **actor** for deletion and enters state5; the separately owned ambient object remains in the manager list.

SpotAmbientSound initialization sets `(flags & ~2)|100001`, clears primary+168, creates a72-byte positional object from the actor's x/y and sound pool, and stores that object at primary+168 when successful. State30 stops its sound, clears playing, removes a nonnull list node, runs the object's deleting destructor, then clears primary+168 and resets primary state0. If insertion returned no node, source cancellation clears the reference without inventing object deletion/rollback. Creation failures are ordinary null returns with source actor stores retained.

The bounded manager constructor comes from actual caller **4262c4..4262d7**: allocation size48 is already owned, CPtrList+8 receives grow10, object+0 becomes0 and+4 becomes100. `claw_sound_trigger_construct_manager` performs exactly those stores, preserving enabled/center words until a separate402240 initializes them. CPtrList4f5133 sets vtable51000c, clears offsets4/8/c/10/14, and stores grow+18. The actual preceding caller allocation at4262a5 requests48; subsequent4262dd..4262f3 passes scene+28 sound controller and caller base volume to402240. These are measured caller/inline constructor facts, not execution of the entire426xxx application configuration method.

4025c0 stores center at manager+28/+2c, traverses raw linked list at+c, calls each nonnull object's virtual+4 with centerX,centerY,refresh0, then flushes controller+2c through4b4b80 when nonzero. Each next-node is captured before callback. 402570 sets playing0 and refresh1, reading live manager center for each object. 402520 stops every nonnull sound and clears playing. 402270 stops the audio collection, destroys all list objects, clears the list and resets manager+0. CPtrList storage/free internals remain explicit services.

Ordinary rectangular objects use **strict** interior bounds, plus an optional second rectangle. A global rectangle sentinel INT_MIN bypasses the bounds. Leaving fades to zero with stop1; entering uses a1000ms source fade, while refresh can restart immediately. Positional objects preserve source32-bit absolute-value/square wrapping and signed comparisons before sqrt/ftol, then derive volume and pan and stop outside the source640px checks. Repeated objects preserve on/off range fields, unsigned stage-delta subtraction, RNG call order, wrapped range+1, zero-range bit selection and signed remainder. There is no guessed distance, radius, repeat schedule or source clock.

Physical4b3dc0 receives **initial volume1, pan, pitch0, looping1**, followed by source volume/fade requests. Volume arithmetic wraps32-bit signed products and uses source truncating divisions before clamping. The physical backend must preserve that order; immediately treating the first1 as a looping flag or collapsing the fade would change the boundary sequence.

## Dependency boundaries and resource profile

- **4f51c5**: CPtrList AddTail(manager+8,object), returning node identity. **4f5212** removes a raw node; **4f5172** clears list ownership. Their storage/pool/free implementation is explicitly adapted; this module recovers the list constructor and surrounding gameplay ownership.
- **4b45f0**: ordinary trigger/speech playback with volume,pan,pitch,loop. **4b3dc0**, **4b3e30**, **4b3f40**, **4b3fe0**, **4b4110**: ambient pool/voice play, stop, volume, timed volume/stop and pan. **4b4b80/4b4c10**: collection update/stop. Physical DirectSound, voice/fade allocation and OS timer execution remain explicit; no immediate-play replacement is claimed.
- **4a3050**: original RNG value service. The host must share the source RNG stream; deterministic oracle values are an explicit boundary profile, not new gameplay randomness.
- Physical alloc/free follow raw sizes64/72/88 and original ordering; unnamed seed words remain intact.

The real record fixture composes frozen WorldObjectRuntime with exact rebuilt WWD bytes/hashes and its source field stores. Image/ANI lookup and layer insertion during fixture setup remain declared boundaries; the full original4d17e0 loader was independently proved by its owning module. This suite does not recount those setup calls as new original callback coverage.

Sound binding is the frozen complete **4c7a40** actor auxiliary binder, independently compared here in the original on every record. A declared filesystem namespace transport profile uses LEVEL1/SOUNDS with LEVEL, CLAW/SOUNDS with CLAW, GAME/SOUNDS with GAME and exact directory/leaf names joined by `_`; it supplies dictionary values to the binder. The source sound-registry recursive4ca440 and underlying REZ traversal are not recovered here, so this is an explicit name transport profile, not complete retail resource-loader parity. No aliases or spelling corrections are introduced. Under it,80 records resolve25 distinct WAV files and **LEVEL_AMBIENT_ANGVIL** is missing; **ANVIL** remains a separate exact resource name.

Actual WAV hashes and borrowed pool durations are recorded in verification.json. Duration profile uses the separately recovered AudioResourceRuntime rule `(dataBytes *1000 mod2^32)/nAvgBytesPerSec`; RIFF chunk inspection is format inventory, not new whole original resource-creation proof. Joined speech-expiry tests additionally use an explicit synthetic750ms borrowed pool duration to test exact countdown boundaries.

## Verification and limits

`Tests/compare_sound_trigger_runtime.py` compares **9094 complete original calls**, **10689 ordered snapshots** over every131072-byte raw heap plus all12 shared global words, meaningful results, stack-pop arity, allocator/list/RNG service state, and **1842 original instruction addresses** excluding adapter/unsafe-stop entries. It includes18 registered family profiles, all81 actual WWD histories with648 retained ordinary steps,64 complete inline manager-constructor profiles, actual source sound binding, retained ambient creation/update/refresh/stop/cleanup, and32 trigger→queue→source speech actor→busy→expiry histories.

Directed cases cover callback-pointer rectangles, charge/busy/missing-actor/death-state gates, signed coordinate wrapping, empty/range sentinels, sparse/null list outcomes, safe allocation failure, volume overflow, live callback mutation and source manager center reads. Tests preserve source calls rather than bypassing helper bodies; only the listed physical/transport/list/RNG boundaries are adapted. Pure CopyRect/SetRect original imports are represented by exact word-copy adapters.

Two **unsafe original prefixes** are separate from completed calls: the missing player's private checkpoint pointer after charge side effects, and a synthetic out-of-domain RNG value causing signed division overflow in a repeated factory. The oracle stops before the first unsafe instruction, comparing complete prefix buffers/events. Native fault1/3 are bounded diagnostics, not original successful returns or SEH exception emulation. Fault2 denotes unsupported metadata/argument profiles. Iteration limit1,000,000 is a safety extension. The ordinary original CRT RNG returns15 bits, so the synthetic division-trap profile is not claimed reachable under that normal RNG.

The sanitizer corpus contains **938 callback-free whole-original heap/global replays**, including frozen speech bodies. It rejects any unexpected allocator/voice/list/dependency callback and checks complete output bytes. These replays do not prove the adapted physical/list services. C11 header, optimized warnings-as-errors and diff checks pass.

```sh
work/test-env/bin/python Tests/compare_sound_trigger_runtime.py
work/sound-trigger-agent/check-sanitizer.sh
clang -std=c11 -Wall -Wextra -Werror -I Sources -fsyntax-only work/sound-trigger-agent/header_check.c
```

Private callbacks/helpers/ambient/update/fades/manager/list-constructor Ghidra outputs have checked logs in work/sound-trigger-agent and an independent project. No shared project/module/device was modified. Source scene integration, physical audio acceptance and complete game identity remain separate from this bounded proof.
