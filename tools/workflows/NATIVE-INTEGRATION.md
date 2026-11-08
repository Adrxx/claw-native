# Native integration harness

This workflow connects finite admitted source graphs to native physical owners.
A family admission, a joined source comparison, an app build, and playable
acceptance are separate results. The original menu → Level 1 → results objective
remains unfinished.

For wire-object tasks, generate a local scene with
`work/test-env/bin/python -m tools.claw.test_level --source-level 13 --spacing 20 --uncompressed --output work/test-levels/objects.WWD`
(or select repeated `--logic NAME` / `--family ID`; `--list` shows source placements).
Run the original with
`work/test-env/bin/python -m Tests.NativeLevels.test_level_trace --wwd work/test-levels/objects.WWD`.
After a Release build through `scripts/run-mac.sh`, run
`work/test-env/bin/python scripts/check-test-level.py --reuse-original` for the muted
app check, or launch interactively with
`CLAW_LOCAL_TEST_LEVELS=1 scripts/run-mac.sh --mute --test-level "$PWD/work/test-levels/objects.WWD"`.
The Mac-only developer opt-in replaces the first New Game world input in both
hosts; the generator manifest selects the source's real runtime level through
the original New Game command's level argument. Keep its original tiles, palette
and resource aliases. Select one source level per scene; mixing aliases is unsupported.
The original substitutes the loader's WWD input; the app substitutes its decoded
payload at the physical zlib boundary, matching the original compressed payload's
hash. Keep the generated WWD and its adjacent manifest together.
The combined check expects the ten-type default scene; use the original runner
and interactive app flag above for individual family scenes.
Generated WWDs, provenance manifests, original traces and screenshots stay under
ignored `work/test-levels/`. This checks object wiring, not family admission or
unchanged original-level behavior.

## Start with the consumer contract

Before drafting or extending a family, run the advisory planner for the intended
roots, then review its gaps against the original. It reports declared/cached
edges, not a complete verified call graph:

```sh
work/test-env/bin/python -m tools.claw.graph_plan --roots 0x50335e 0x50228f --require-source --out work/coordination/source-graph-plan.json
```

Decide the immediate consumer's ABI, CPU/stack observations, machine EAX for a
semantic void result, callbacks, return sites, exception boundary, and ownership
before sealing cases. Do not automatically require full source context for every
gameplay family. Preserve boundary → blind cases → seal/guard → fresh translator
→ guard → recorded gate, including the existing mutation threshold.

## Elect a finite connection

`ClawNativeCanonicalHost` holds a closed typed source edge table. Each row names
an explicit root, active dispatch owner, original body, CALL metadata,
continuation, target, frame relationship, and operation. Runtime selection checks
the elected root/owner/target/continuation and the operation's CPU/frame/ownership
witnesses. It does not dynamically observe the original CALL instruction address.

`Tests/NativeSourceEdges/validate_edges.py` checks CALL metadata against the
hash-verified original and checks admitted registry signatures. Its negative
probes reject stale signatures, incorrect targets/continuations and ambiguous
rows. Full-stack replay and adversarial controls verify dynamic behavior. A new
operation or frame policy needs original boundary review and independent cases;
adding an admitted address alone never authorizes a connection.

## Reuse the physical owner

A `SourceLocalAllocator(host:provider:)` adapter uses the existing
`ClawNativeMfcMemory` allocation ledger. Requests contain copied CPU/frame/stack
values and an opaque, single-use lease bound to the issuing host, graph, thread
and exact provider. The lease expires when synchronous service returns. Providers
are trusted native implementations, not an extension/plugin interface. They must
consume their request, preserve binding and allocation identities, and implement
the physical operation once. Source CPU mutation remains in the host.

The BossStager prerequisite uses `host.withObjectAllocation(provider: memory)`
around ordinary canonical calls. It elects contact binding `0x4c8060` and
health-meter construction `0x4c8da0`, executes the existing operator-new owner,
and grants its reviewed malloc edge a single-use Memory request. Exhaustion
reaches the original handler lookup and faults if that service is unavailable.
Internal CALL continuations are reviewed metadata for inlined bodies, not
dynamically observed PCs.
Enabled pool playback additionally elects `audio: scene.player.audio` in that
scope. The audio owner and scene share the player's `audioHeap`; no metadata
copy or seeded idle voice is needed. Only genuine loaded pools at `0x4b4430`
and `0x4b42e0` authorize `0x38` bytes at continuation `0x4b4320`. The existing
operator-new body and Memory lease remain the allocation authority. Audio retains
the issuing ledger until its source PCM destructor releases each voice. Buffer
COM output cells use `host.bytes`, including synchronous stack locals, and the
exact `0x4a30e0` x87 service consumes its declared stack result. Run
`scripts/check-boss-stager-audio-transport.sh` for the original playback/list and
teardown comparison plus native ownership controls. This does not attach the
BossStager callback. `scripts/check-boss-stager-transport.sh` checks this
boundary; the BossStager object adapter and its connection check remain separate.

Memory supplies allocation, subsequent ordinary resize/free and final teardown.
Retiring the adapter retains those allocations while Memory remains owned.
Explicit eight-byte alignment supports the sealed factory profile addresses;
the ordinary default remains sixteen bytes. An occupied shared allocation base
is allocation exhaustion: zero reaches the genuine missing throw dependency.
The standalone unit allocator retains its existing safety-fault collision policy.
Neither policy moves or overwrites the occupied allocation.

Reentrant physical service is rejected with a sticky fault, including delegated
lock calls. Manager creation/registration is setup work and rejects while a
service is active. All effect-capable allocation hooks are followed by binding,
fault and applicable allocation-identity checks. An invalid request never grants
an ordinary context-free call in place of a source call.

## Run the shared verification

```sh
scripts/check-native-graph-replay.sh
env CLAW_NATIVE_ASAN=0 CLAW_NATIVE_OPTIMIZE=1 scripts/check-native-graph-replay.sh
```

The runner uses the two existing sealed reference files unchanged. It executes
160 standalone factory profiles, 128 thread-record profiles and the same 160
factory profiles through the shared Memory provider: **448 executions of 288
unique original profiles**. Shared factory allocations also undergo ordinary
resize/free checks against their sealed constructor bytes. Separate native owner
checks cover lifecycle, identity replacement, request authority and callbacks;
these are not additional original instruction paths.

The builder captures private source/header/manifest bytes, validates matching
edge metadata, includes toolchain/SDK/flags and inputs in its cache key, and uses
per-key locking plus atomic publication. It rejects extra compiler flags.
Concurrent edits between edge validation and capture fail with a rerun request.
A certificate identifies the exact compiled bytes, not an atomic repository
snapshot, current family admission proof or device acceptance.

Keep the original factory, thread-record, source-context, canonical-host,
Memory/Locks/TLS and heap adversarial suites available. Run the affected controls
when their shared implementation changes. The common success loop does not
replace them. Root alone regenerates the project and controls app/device checks.

## Parallel work and measurement

For recorded project, graph and startup-prefix checks with freshness-aware
resume, use the [milestone harness](MILESTONE.md). Its lower-level certificates
remain separate from connected gameplay and device acceptance.

With four agent slots, use one coordinator and up to three bounded workers on
disjoint files. Original-only boundary/reference work, a native implementation,
and independent native owner tests can overlap after agreeing the interface.
Across different families, case-author A can overlap translator B; within a
family the cases must be sealed before translation. Use fresh Sol 6.1 low workers
for cases/translations and Astra high for boundaries, harness work and review.

One worker owns a shared host file at a time. Serialize project generation,
manifest admission publication and final integration. Freeze shared inputs before
final review and controls; private build snapshots protect compilation from
unrelated edits but do not make incompatible interfaces coherent. Count actual
heavy child processes, keeping the total near four; use one-job mutation gates
when other work is active.

Wrap commands to retain measured phase duration and CPU usage:

```sh
work/test-env/bin/python -m tools.claw.run_logged --label native-replay --input Sources/ClawNativeCanonicalHost.swift -- scripts/check-native-graph-replay.sh
```

Measure command/build/replay time and concrete integration changes separately.
Model waiting, coordinator effort and overall project speedup are not inferred
from gaps between artifact timestamps. The shared-provider example reuses the
same nine edge rows and comparison loop; new provider ownership semantics still
need implementation and review. A new dependency with a different frame or
result contract still requires an explicit extension.
