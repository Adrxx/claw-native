# Original image-controller dictionary and loading composition

This additive module recovers the missing CString/value dictionary storage used by the source image controller. It composes the frozen image registry, resource namespace/data/archive loader, CArray and pooled-block bodies; it does not replace their loading routines or enumerate filenames in Swift.

Evidence uses unchanged `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`, and disc `Original/claw-disc/files/DATA/CLAW.REZ`, SHA-256 `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`. Private analysis is in `work/image-controller-loading-agent`. No reference decoder, filename convention or gameplay implementation supplied these bodies.

## Source boundary inventory

The actual `513b88` image-controller vtable elects `4cff40` at `+48` and `4d0120` at `+4c`. Their whole implementations, recursive group loading, root creation, frame selection and typed image wrappers already belong to frozen `ImageRegistryRuntime`. Source Menu `45ace0` invokes the first with `(IMAGES folder, MENU literal525698, separator523728)`. Source Story `40b860` loads `STATES_BOOTY` (literal523b1c), and invokes it with prefix `BOOTY` (523b14). Menu/Story recovery invokes the same restore slot `+4c`. `45be10/45f940` remain frozen StateFive-owned; they read this dictionary and signed root ranges rather than defining the cache.

The new complete procedures are:

| Entry | Stack words | Source role |
| --- | --- | --- |
| `4f5d5c` (90 bytes) | name, bucketOutputCell | Hash, publish bucket, find association |
| `4f6286` (34 bytes) | name, valueOutputCell | Original BOOL lookup and conditional output store |
| `4f62a8` (98 bytes) | name | Find/create association and return writable value slot |
| `4f5db6` (104 bytes) | name | Unlink matching association and release it |
| `4f615b` (70 bytes) | bucketCount, allocate | Replace bucket table |
| `4f6226` (96 bytes) | none | New/reused pooled association |
| `4f5d33` | association | CString release, free-list insertion and last-item clear |

All use ECX as the original receiver. CString copy/assignment `4f66cc`, destruction `4f6584`, empty-cell getter `4f6433`, exact CRT comparison `4a3810`, and last-item map clear `4f61a1` remain addressed dependencies with existing frozen ownership where available. The module does not duplicate the map constructor `4f6118`, clear/destructor `4f61a1/4f61f3`, iteration `4f5e1e`, image-controller initialization `4cfa60` or cleanup `4cfa80/4d0240`.

## Raw layout and semantics

The dictionary occupies 28 bytes. Its original fields are vtable `+0`, bucket table `+4`, bucket count `+8`, live association count `+c`, free-list head `+10`, pooled-block chain `+14`, and associations per block `+18`. The frozen constructor sets bucket count17 and receives the block size (the source scene supplies10). A bucket table contains one DWORD head per bucket, with no extra fixture header.

Associations occupy16 bytes: next `+0`, saved bucket index `+4`, owning CString data token `+8`, and value `+c`. They are embedded in blocks allocated by frozen `4f5aa8` with `(map+14, map+18, 16)`. They are not individually allocated or freed. Source NewAssoc builds the free list backwards across the block, then pops its first node, increments count, copies the four-byte cell returned by `4f6433`, and zeros the value. It re-reads block size after the allocator/pool callback; retaining the earlier value would lose an observed callback mutation.

Hash is DWORD-wrapped `hash*33 + signExtend(byte)` until NUL, followed by unsigned remainder using the live bucket count. Key comparison uses actual `4a3810`, preserving case sensitivity. `KEY` and `key` are distinct. Bytes80..FF contribute negative signed-char values before wrapping. `4f5d5c` writes the bucket output before reading/traversing bucket heads and before comparison callbacks, including when that output aliases the input key.

Lookup `4f6286` returns one when an association exists even if its value is zero. It writes the output only on success. A missing key leaves the caller's seeded output untouched. This is different from the older shared SceneActorHost convenience convention that returns a resolved token.

Create `4f62a8` initializes the bucket table on demand, obtains a pooled node, stores the previously computed bucket index, assigns the owning CString, re-reads the table/head after assignment, and prepends the node. It returns `node+c`; the caller writes its own payload there. Existing keys return the existing slot without replacing its key or value.

Remove skips name/hash work when the table is null. Otherwise it walks the source chain, unlinks first, calls `4f5d33`, and returns one. FreeAssoc destroys the key before reading the live free-list head, decrements count, inserts the node into the free list, and calls `4f61a1` when the count reaches zero. The frozen clear owns table/block release. No automatic private-image deletion is added to dictionary removal; source registry `4cf230` separately captures its root, removes the name, then invokes root deleting destruction.

Table initialization frees the prior table before clearing `+4`, optionally allocates/zeros `bucketCount*4` wrapped bytes, then writes bucket count. Existing association count/blocks are not repaired or rehashed by this method. Zero buckets and failed allocation can reach original unsafe operations, so it is not a safe arbitrary resize API.

## Stable API and integration

Use `claw_image_controller_loading_entry` in `Sources/ImageControllerLoadingRuntime.h`. The public entry admits the seven owned methods and the recognized frozen methods for each supplied optional composition view. Unknown entries return zero without changing the output. Return one denotes supported completion; original EAX is separate. Void procedures' incidental EAX has no parity claim.

The 104-byte native context contains the shared raw scene host, borrowed `ClawImageRegistryContext`, `ClawResourceNamespaceContext`, `ClawResourceDataContext`, `ClawResourceArchiveLoadingContext`, `ClawCArrayContext`, and `ClawAmbientAudioBackendContext`, plus native limit/fault. All views must use the same heap/global aliases and be initialized with clear fault fields. Rich dependencies preserve ten arguments, two synchronous buffers, and local masks. Array, pool, namespace, data and archive callback addresses compose into their frozen bodies when the corresponding view is present; otherwise remaining reached services are emitted by address. The function inventories are dispatch inventories, not duplicated implementations.

The module temporarily installs its host on borrowed views so frozen ImageRegistry's one-argument convenience lookup resolves through the genuine dictionary. It restores those host views on normal or failed returns, including nested array views. These synchronous views cannot be used concurrently. Their logical contents, fault words and source globals remain live; they are not copied into detached frame snapshots.

For the default image controller, retain the frozen scene's 44-byte allocation at scene `+10`, parent at controller `+c`, and embedded dictionary at controller `+10`. Construct it through existing `4cea10/4f6118`; do not call a second constructor in this module. Supply `registry.arrays` for sparse frame arrays, and both `registry.images` and `registry.imageHost` when composing actual GameImage load bodies. The GameImage host's separate rich physical service ABI remains caller-owned and must retain live scene/graphics/resource aliases. Source-created roots are108 bytes; indexed images are52 bytes. Metadata/ranges and sparse arrays remain ImageRegistry-owned.

Route `4f61a1` and map destructors into frozen SceneLifecycle, `4f6584` into the recovered CString destruction owner, and `4f6433` into the existing empty-cell getter. Raw globals `52e1c8/52e1cc` identify the same source empty string header/data, not new native identities. Owning CString assignment `4f66cc` still requires its exact source/transport implementation; this module does not claim to have recovered that leaf. Physical allocator/CRT thread lookup, FILE and image/surface services remain explicit. Do not retain callback buffer pointers after return.

Calls from the unmodified Menu resolver can now find original name slots and signed min/max metadata. Its returned presentation is still the actual image `+2c`, and other image fields `+30` are populated by existing GameImage/physical source composition. This module invents neither field values nor surface success; the joined oracle uses the existing explicit image-initializer boundary with no presentation pixels or synthetic `+2c` stores.

## Measured verification

The final unchanged-original suite compares **2,145 whole calls, 17,383 ordered full snapshots and three unsafe prefixes**. It compares every byte of a2MiB raw heap and274,432-byte mapped globals, callback arguments, meaningful EAX, file cursor/payload hashes, allocated/live/freed histories and snapshot ordering. Instruction counts are in `work/image-controller-loading-agent/verification.json`, using actual `.text`401000..50adb5 and separate total instrumented count.

Directed profiles cover case, empty/high-byte keys, varied bucket/block sizes, collisions, retained slots, present-null versus absent output, table replacement, allocator callback mutation, removal and key/output aliases. Stopped prefixes are zero-bucket division at4f5d7c, null bucket allocation before4a4a20, and failed association-block allocation before4f6253. Native faults are guard extensions; those prefixes do not claim original safe error returns.

Joined profiles execute original disc directory records through frozen Archive/Table, actual node prepend and frozen Namespace bucket traversal, then frozen ImageRegistry and the new raw dictionary:

| Retail tree | Source registered roots | Physical image-load boundary calls |
| --- | ---: | ---: |
| `STATES_MENU/IMAGES` |20|295|
| `STATES_BOOTY/IMAGES` |52|452|

Duplicate calls preserve the source cache and elect no additional image loads. Restore, true BOOL lookup of every root, name removal/root deletion and REZ graph destruction follow retained histories. These joined profiles do not use a supplied filename/traversal list. FILE reads use actual archive bytes. The physical allocator profile reuses its most recent released block during these joins; source CRT heap address identity is not claimed.

CString assignment/destruction and map clear are declared synchronous transport profiles in this oracle. Their complete boundary heap/liveness effects are compared, but their internal instructions are not counted as recovered by this module. Map clear and CString destruction have independent frozen proof; root must route them to those actual APIs for native source composition. Physical image initialization/restore/deletion is likewise explicit; the registry's typed wrapper and actual resource acquisition/read/release execute, while pixel decoding and physical presentation acceptance are outside this oracle.

Private gates pass strict C11/C++17, Swift import of the104-byte context, and **30 exact-span ASAN/UBSAN source replays**. New dictionary code plus freshly compiled frozen CArray/pool code are instrumented, with exact28-byte maps, bucket arrays and original pooled blocks, live/dead lookup enforcement and original callback snapshots. Packed strings use explicitly declared containing-word padding required by the shared UInt32 lookup ABI. These sanitizer replays cover dictionary bodies, not the joined Menu/Story image graph or physical codec services.

Run from the repository root:

```sh
work/test-env/bin/python Tests/compare_image_controller_loading_runtime.py
work/test-env/bin/python work/image-controller-loading-agent/checks.py
```

The oracle currently links read-only frozen `libImageRegistry.dylib`, `libData.dylib` (Archive), and `libSceneLifecycle.dylib` from their private work directories. Rebuild those using their existing owners' documented gates if absent; this script does not modify frozen sources/work. The new C++ source compiles independently with warnings as errors. No PCX retry, Xcode/device action, shared native edit, full IFC menu acceptance or whole Story frame rendering is implied.
