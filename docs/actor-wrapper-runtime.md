# Raw actor geometry and resource wrappers

Frozen additive `ActorWrapperRuntime.h/.cpp` from original Captain Claw v1.0 `CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private Ghidra analysis lives in `work/actor-wrapper-agent/ghidra-project`; all six entries were accepted as real boundaries by the hash-checking recovery script. No shared source, header, project or device was modified.

## Source ABI

| Entry | Receiver and stack arguments | Result |
| --- | --- | --- |
|406240|Actor, no args; hit rectangle+128/+12c/+130/+134|Original void|
|406290|Actor, no args; move rectangle+118/+11c/+120/+124|Original void|
|40f6c0|Actor, `(left,top,right,bottom)`, RET16|Original void|
|4209d0|Actor, `(imageID)`, RET4|Original void|
|4061b0|Registry, `(nameToken)`, RET4|Exact dictionary output word|
|4062e0|Embedded wrapper, `(nameToken)`, RET4|Exact dictionary output word|

`claw_actor_wrapper_entry` uses a borrowed live `ClawSceneActorHost`. It returns1 for a recognized call independently of diagnostic fault; result is meaningful only for the two getters. Unknown entry or invalid argument count returns0 untouched. Missing spans/services set fault1 while preserving the reached native prefix; they are not source normal returns.

## Geometry and image behavior

Hit/move wrappers capture actor+174 once. A zero selected-image pointer leaves all rectangle fields unchanged. A nonzero pointer supplies halfWidth+18,halfHeight+1c,offsetX+20,offsetY+24. The wrappers reuse the already frozen `claw_sprite_relative_bounds`4061e0 numeric implementation; that routine is not claimed as a new recovery.

The source writes each scalar separately and reloads the relevant image fields before the following scalar. Native composition therefore invokes the frozen numeric helper over only the required fields at each source store, preserving left→top→right→bottom order. This is observable for image headers aliasing actor rectangles or when a later input/output word is unavailable. No whole-header snapshot or bulk rectangle store replaces those reads. These are relative image bounds; actor position, facing, clipping and padding are not newly applied.

40f6c0 copies four raw words to the move rectangle without validation, normalization or arithmetic.4209d0 captures actor+170 image root. Null root changes neither actor+16c index nor+174 selected image. With a root, the requested signed index is accepted only between signed-inclusive root+64/+68. A valid index reads `*(root+14 + index*4)` from the source **absolute-ID** table, preserving32-bit address wrap, negative-ID profiles and null/gap entries. The source captures that frame pointer before storing index then selected pointer. An out-of-range index is still stored and clears selected pointer. It does not subtract the minimum, choose a fallback frame or recompute rectangles.

## Exact dictionary output transport

4061b0 invokes4f6286 on registry+10.4062e0 follows `wrapper+4 → actor+C → parent+2c → ANIregistry+10`; its receiver is the embedded wrapper, not the actor. Neither adds null checks around this chain.

Both source getters initialize an automatic output word0, call4f6286 `(nameToken,&output)`, ignore its Boolean return and return the resulting output word. Rich `ClawActorWrapperDependency` exposes both independently: function4f6286, exact dictionary receiver, argumentCount2, arguments `(nameToken,0)`, localMask2, and a synchronous writable output pointer initialized0. A callback may return0 and write a nonzero output, or return1 and leave0; the wrappers preserve those distinctions. The automatic pointer must not be retained as game-owned storage.

Without a rich callback, established `SceneActorHost.call` uses its named-lookup contract: function4f6286, dictionary receiver, one name-token argument, returned resolved token. That token becomes the local output. This fallback adapts the existing host ABI, which exposes no dictionary Boolean. Dictionary hashing/storage/resource lifetime and name parsing remain explicit services; tests do not claim the4f6286 internals or failed-resource semantics of an absent dictionary.

For Root's Breakable adapter, route the six leaf addresses directly with the table above. Keg constructor selects9 then1, copies its original move rectangle through40f6c0 and applies406240. Crate applies406290 to its current selected image. Root can use the legacy host resolver or the richer independent output service. All tokens and source allocations retain their existing owner; this module allocates or frees nothing.

## Verification

`work/test-env/bin/python Tests/compare_actor_wrapper_runtime.py` passes1614 whole original calls,218 ordered complete service snapshots and26 stopped original read/store prefixes, covering92 actual instruction addresses. Each snapshot and final comparison preserves the full131072-byte mutable fixture heap. Meaningful getter EAX and original stack cleanup match. Original dictionary internals are adapted with a separately controlled Boolean and output; callbacks mutate actor image fields, rectangles and wrapper/parent registry identities before returning.

Coverage includes500 arbitrary32-bit geometry profiles, image/rectangle aliases, null images, raw setter extrema, signed min/max/reversed image ranges and gaps, wrapped absolute-ID reads, independent dictionary output/Boolean combinations, null/literal names, live callee mutation and the legacy resolver contract. Read faults stop before the relevant original memory access; write faults stop at its actual source instruction before the store. Four additional comparisons execute real unmapped-null exceptions with a valid SEH/TIB adapter. Native safe faults retain the matching heap prefix without inventing source returns.

All25 actual retail Level1 PID headers (17 POWDERKEG,8 CRATES) feed the frozen source geometry setter and real absolute-ID tables, then run three retained selection→hit bounds→move bounds cycles each. Actual file SHA256, header dimensions/hotspots and frame IDs are saved in `work/actor-wrapper-agent/verification.json`. These header tests do not claim pixel decoding or retail enumeration: file transport and image table population are explicit fixtures. Strict C11/C++ and a native ASAN/UBSAN image/gap/getter/alias smoke pass. Parent owns gameplay integration and device verification.
