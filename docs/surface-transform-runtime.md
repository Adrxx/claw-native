# Original surface vertical flip

`SurfaceTransformRuntime` recovers the whole original `4b99d0` (294 bytes, `4b99d0..4b9af5` inclusive), a thiscall method taking a surface receiver and no stack arguments. Original incidental void EAX is excluded. The source address was confirmed against the hash-pinned v1.0 EXE (`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`) before implementation. Private instruction listing is `work/surface-transform-agent/vertical-flip.asm`.

The requested `4b9e90` was already frozen in PCXImageRuntime: it is the RET16 pixel-depth conversion selector `(data, sourceDepth, palette, direction)`, not vertical flip. It is not duplicated here. Frozen image method `4d2790` elects the newly recovered `4b99d0` when image `+2c` is nonzero. No frozen file is edited.

## Actual byte and lifetime behavior

Surface footprint is 188 bytes. Height `+14` and width `+18` are signed loop values; pitch `+1c` is a byte stride. Height at most one returns immediately, without locking or allocating. Otherwise source calls frozen `4b9730(surface,0)`, then malloc `4f63ec(width)` if locking returned a nonzero pixel pointer. Failed lock does not allocate or unlock. Failed scratch allocation still performs DD Unlock, then returns without free.

After allocation, source captures height and width again, so an allocator callback may change the geometry consumed by the loop. It saves one top row into scratch, copies its opposite bottom row to the top, then copies scratch to the bottom. The loop copies **width bytes**, even when surface pixel depth is 16, 24 or 32. It does not multiply width by pixel size. Middle rows and the portion after width bytes retain their prior contents in ordinary disjoint-stride profiles. Overlapping pitch and aliased scratch preserve sequential byte reads/writes; no memcpy, deduplication or involution is substituted.

Pitch is reread before the first copy, once for the second-copy top/bottom calculations, and again for the third-copy bottom calculation. Height/width and half-height are captured once after allocation. At completion source rereads surface `+8`, resolves its DD VT `+80`, calls stdcall `Unlock(DD,0)` with receiver zero, then frees scratch with `4f6428`. Unlock HRESULT is ignored. DD interface, surface fields and allocator writes are not fabricated.

## Public ABI and joining

`ClawSurfaceTransformContext` is 80 bytes on the current 64-bit C/Swift host. Supply a shared raw `ClawSceneActorHost`, optional exact byte lookup and borrowed `ClawGameImageGlobals`. Word lookup must preserve exact aligned metadata spans; byte lookup must accept exact pixel/scratch spans and aliases. The fallback accesses containing aligned words and therefore requires those complete words. It creates no tail shadow or deferred flush.

With image globals supplied, source lock `4b9730` composes frozen GameImage directly, including DD Lock, surface descriptor/pixel stores, lost-surface restoration election and diagnostics. Without them, the entire lock body remains one exact dependency packet. The facade does not claim the restoration callback `4b9e60` is complete physical restoration: the host should route that elected address to its existing frozen owner.

The rich dependency type uses `ClawGameImageCall`. DD Lock is receiver zero with `(DD,rectangle,surface+0c,1,0)`; physical descriptor writes occur synchronously in the shared raw graph. Unlock is receiver zero with `(DD,0)`. Allocate/free remain their original addressed cdecl packets. Optional stack buffers retain the existing GameImage contract. Native completion returns one and output zero; fault 1 means missing service/span, 2 invalid ABI and 3 operation budget. A span rejection or budget stop is a native safety extension, not a recovered graceful original exit. Unknown function leaves result/fault unchanged.

To join the frozen lifecycle graph, route its elected `4b99d0` packet into `claw_surface_transform_entry` using the same heap, strict byte provider, image globals and DD/allocator identities. No additional surface ownership is introduced.

## Evidence

The final oracle passes **1,245 whole original calls / 5,930 full snapshots / 529 distinct retail-derived dimension pairs / 172 instrumented .text addresses / 174 total instrumented addresses**. Retained ordinary double flips restore every represented initial pixel byte. Strict C11, warnings-as-errors C++17, executed Swift import of the 80-byte context and **31 exact-span ASAN/UBSAN replays** pass. The original oracle compares every byte of a 1 MiB raw arena, source RET stack effect, full callback snapshots, arguments, and allocated/live/freed identities. Ordinary retail profiles derive dimensions directly from actual PID headers; they are dimension/pitch profiles with seeded pixels, not a claim of loading/rendering every retail resource in this suite. No reference-source pixel algorithm is used.

Generated profiles cover zero/negative/single-row heights, widths including zero and odd tails, odd/even heights, padding, four depth fields, allocator-mutated geometry, aliased scratch/pixels/surface unrelated fields, overlapping row strides, ordinary and surface-lost Lock failures, source restore/retry/diagnostic elections, malloc failure and ignored Unlock errors. Declared alias/free endpoints compare source requests; they do not assert that an ordinary allocator would accept freeing a borrowed alias.

Exact-span ASAN/UBSAN replays instrument the new transform source, with exact surface188, DD4, VT132, pixel and scratch allocation lengths, strict byte/word lookup, live/dead transitions, callback-entry whole-span snapshots and full final bytes. Frozen GameImage's borrowed dylib is not freshly instrumented by this gate. Physical DD device behavior, negative-pitch ownership graphs, true concurrent or reentrant byte mutation, and complete pixel-depth conversion remain outside this bounded proof.

Run:

```sh
work/test-env/bin/python Tests/compare_surface_transform_runtime.py
work/test-env/bin/python work/surface-transform-agent/checks.py
```

Only new source/test/doc and private compiler outputs are changed. No native host, shared tests, project, GUI or device actions are part of this handoff.
