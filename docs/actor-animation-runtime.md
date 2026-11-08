# Original actor animation selection and callers

`Sources/ActorAnimationRuntime.h/.cpp` recover the complete bounded actor-animation caller graph from original v1.0 `CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. The full updater is the frozen `AnimationEngine`; pending-delay behavior composes frozen `AnimationOperations`. No updater or gameplay source port was copied.

## Stable C11 interface and actual caller ABI

`claw_actor_animation_entry(function, receiver, argument0, argument1, globals, ClawSceneActorHost, fault, result)` uses stable raw mutable token spans. Its support result is separate from meaningful original scalar EAX. Selection/restoration void entries do not claim incidental EAX equivalence.

| Function | Actual receiver/arguments | Behavior |
|---|---|---|
| `4c79e0` | actor, name token, eager | Lookup scene+2c manager+10; missing returns0 without selection; found selects ANI and optionally updates using animation delta5430c4; returns1 |
| `4c7a40` | actor, name token | Lookup scene+28 manager+10; found stores actor184 and returns1; missing preserves184 and returns0 |
| `4c8210` | animation | Clear owner+4, sequence+8 and current record+c only |
| `4c8220` | animation, sequence token | Set sequence+8, then valid selection resets fields below; null sequence preserves every other word |
| `4c8260` | animation, clear-delay flag | Reset currently bound sequence; preserve pending delay unless flag nonzero; no sequence preserves all fields |
| `4c82a0` | animation, delta | Full original update through frozen native engine, preserving raw token fields and sound service order |
| `420a10` | actor, sequence token, eager | Select embedded actor+188 animation, optionally update with5430c4; void restoration wrapper |

`4c7a40` is an auxiliary resource binder, not an ANI-selection/postselection routine. `4c8310` is an interior address in the updater, not its function entry; the complete function starts4c82a0.

The raw animation object has11 observed words, normally inside the full128-word actor at188:

| Offset | Raw field |
|---|---|
| 04 | owning actor token |
| 08 | sequence token |
| 0c | current record token |
| 10 | record index |
| 14 | remaining countdown |
| 18 | timed/countdown mode |
| 1c | stopped |
| 20,24 | code, previous code |
| 28 | binary32 rate bits |

Valid selection sets index0, the first record token, countdown0, stopped0, both codes to first-record+1c and rate1.0. It **preserves timed+18**, unrelated actor/animation fields and image state. Reset4c8260 does the same except optional countdown clearing. Binding a null sequence is not animation destruction and does not erase stopped/current-record/rate fields.

Globals supply **animation delta5430c4** and **audio position532c10** separately. Stage delta53720c is not read by these wrappers. Named eager selection reads5430c4 after the resource service, preserving dependency mutation/order. There is no OS clock read in this caller layer.

## Host raw resource layout

A sequence exposes at least20 bytes: sequence+c is its record-pointer-array token, sequence+10 its signed record count. Each record is12 words/48 bytes:

```
[preservedClassWord, flags, imageCommand, controlCommand, movementCommand,
 parameter, duration, code, dx, dy, preservedWord40, resolvedEventToken]
```

The existing frozen portable record is40 bytes and is marshalled from these raw fields. Original pointer identities remain in animation+c and sequence tables. Image manager uses+14 absolute-ID pointer table,+64 minimum,+68 maximum; actor170 supplies the manager. The wrapper does not bind an image set automatically from ANI selection. Actual supplied resource/sequence/image identities belong to the host.

`ClawSceneActorHost.call` named lookup4f6286 returns a resolved resource token rather than the original bool/out-parameter ABI. File loading, namespace/path translation, registry/factory creation and image/ANI allocation remain explicit adapters. Native `ClawActorResources` now materializes the raw20-byte ANI, pointer-array and48-byte record layout. Player/Rat/RatBomb calls compose this module; the standalone playback preview retains its separate adapter. C++ marshalling vectors are temporary native implementation storage, not gameplay heap allocation services.

## Exact event boundary and bounded safety

Original sound dispatch occurs after image and movement writes, and after the pending-delay prefix, but **before** current-record duration, rate conversion, control and next-record stores. The wrapper runs the frozen engine on shadows, exposes only the original actor/image/movement and prefix stores at the sound call, then commits the remaining engine output. The explicit sound calls are `4c88e0` for spatial records and `4208e0` for direct records, receiver=resolved event token, arguments `(position,0,0,0)`.

The separately recovered audio routing has no gameplay actor/ANI/image-table writes. Audio can mutate its own globals/resources. Reentrant mutation of actor, animation, sequence, record pointer table, records or image manager/table is explicitly rejected with fault3 rather than claiming arbitrary callback parity from a batched frozen updater. This is checked and tested as a native scope diagnostic, not simulated original behavior.

Fault1 is a missing span/service; fault2 is unsupported/invalid metadata (including nonpositive record count, incoherent record index/pointer, oversized sequences, invalid image table domain and unsafe absent-manager control paths). These are native safety extensions. Original empty/invalid sequence dereferences are not executed as successful parity cases. Zero **duration** is valid and is never confused with an empty sequence. Finite and nonfinite rate behavior composes the engine's previously verified53-bit CRT arithmetic.

## Verification

From the repository root:

```sh
work/test-env/bin/python Tests/compare_actor_animation_runtime.py
zsh work/actor-animation-agent/check-swift.sh
clang -std=c11 -Wall -Wextra -Werror -I Sources -fsyntax-only work/actor-animation-agent/header-check.c
```

Optimized native code (`-O2 -Wall -Wextra -Werror -ffp-contract=off`) passes **6,500 complete original caller/updater calls**, **1,324 ordered complete pre-service heap snapshots**, and **670 original instruction addresses**. Every call compares the full65,536-byte raw heap, including fullactor128, standalone animation, sequence/pointer/record/image buffers, preserved words and guards; both globals; and meaningful scalar returns. Actual original image helpers, record lookup/control/reset, x87 conversion and updater instructions execute; only registry and sound services are adapted.

Generated/directed coverage includes named missing/found lookup, actor resource binding, null/valid selection, preserved timed fields, eager/deferred calls, remaining countdown boundary values includingUInt32.max, arbitrary nonzero timed/stopped words, optional delay reset, all image/movement/control forms, rates, old/current codes, dependency-side actor/clock writes during named lookup and audio-global writes during sound dispatch. Reentrant gameplay mutation produces explicit fault3 in a separate native-only scope check.

**48 records from10 actual ANI files** are decoded through both frozen native decoding and original4d76e0, then supply **2,200 retained original/native updater steps**, with repeated reset and external rate changes. The files are all5 Level1 Rat sequences, all4 RatBomb sequences and `GAME_NULL`. Rat and RatBomb fixtures use the **actual PID filename ID sets** (15 and23 frames respectively), represented by opaque image tokens. GAME_NULL is exercised on an explicitly supplied Rat image context. BOUNCE and GAME_NULL each contain a valid zero-duration record; THROWSOUTH also includes one. Pixel data/audio playback and asset-version identity are separate concerns.

The optimized Swift raw-heap C bridge passes zero-duration stop-record selection/update, actual image-token propagation, timed-word preservation and null-selection retention. The public header also passes C11 ABI shape checks. No Xcode/device/UI build or run was performed. Detailed assets/counts are saved in `work/actor-animation-agent/verification.json`.

This caller recovery supports native integration of the already verified animation engine. It does not establish full scene scheduling, resource namespace identity or whole-game equivalence by itself.
