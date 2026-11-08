# Original resource table construction

`ResourceTableConstructionRuntime` recovers the finite original folder/type/hash-table construction and destruction graph. It composes frozen `ResourceNamespaceRuntime` lookup/iteration, `ResourceDataRuntime` resource construction/lifetime, `AmbientAudioBackendRuntime` intrusive-list insertion/removal, and optional `CArrayRuntime` allocator wrappers. No REZ parser or filesystem implementation is substituted for the source archive loader.

The original executable is `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Procedure starts and RET arities were checked against mapped PE instructions before private Ghidra recovery in `work/resource-table-construction-agent/tables.c/.log`.

## Entries and ABI

| Entry | Original interface | Span/behavior |
| --- | --- | --- |
| `4b6600` | folder, six words, RET24 |76-byte constructor |
| `4b64b0` | type, `(tag)`, RET4 |44-byte constructor |
| `4d53a0` | map, `(bucketCount)`, RET4 |8-byte header, allocation `4+16*N` |
| `4d5410` | bucket, no args |16-byte bucket initializer |
| `4d5420` | map, no args |bucket-array destruction/free |
| `4d5450` / `4d5490` | map, `(iterator)`, RET4 |source virtual hash insert / unlink |
| `4b69a0` | folder, `(name)`, RET4 |create a child, reject existing name |
| `4b7170` | folder, `(typeTag)`, RET4 |find or create a type |
| `4b6a60` | folder, `(resourceID,name,typeTag)`, RET12 |create empty resource; reject existing ID/name |
| `4b8070` | ID map, `(ID)`, RET4 |ID-chain lookup |
| `4b7f40/4b8050/4b80c0/4b8130` | embedded iterator, no args |name/ID/type/folder hash wrappers |
| `4b7cc0` | source receiver, no args |whole timestamp wrapper |
| `4b6530` / `4b66d0` | type / folder, no args |whole resource / recursive folder cleanup |

All17 exposed entries have separate supported/completed and meaningful-EAX outputs. Void incidental EAX is not given new semantics. Unknown entries leave result unchanged. Native diagnostics preserve reached prefixes: fault1 missing span/service,2 unchecked domain,3 operation limit,4 arity. A zero maximum permits one million operations; this is a safety bound, not an original field or success path.

The C11 context uses the existing raw `ClawSceneActorHost`, optional caller-owned frozen allocator, and an optional exact byte-span callback for this module's folder-name reads/copies. Frozen namespace/resource modules still use containing-word string access; their hosts must expose physical string padding honestly. Do not hide missing allocation capacity. Rich dependencies accept ten arguments, synchronous local buffers and a local-argument mask.

`4b7cc0` **is not a stream position getter**. Source `push ecx; lea eax,[esp]; push eax; call4a3b10` supplies CRT `time` with a four-byte local initialized to the source ECX value. The native callback uses function`4a3b10`, receiver0, one argument0, localMask1 and one mutable four-byte buffer. Return the physical timestamp and write the local as the actual transport does; do not replace it with game elapsed time or an independent RNG identity. Creator callers reread their controller alias after this callback.

## Exact graph recipe

All offsets are hexadecimal bytes. Folder constructor arguments are `(controller,parent,name,arg3,arg4,arg5)`; source stores controller+18,parent+1c,arg3+4,arg4+8,arg5+14. Archive-call instruction evidence gives offset/length/time in those latter fields, but this module does not execute the archive reader.

| Object | Original raw fields |
| --- | --- |
| Folder76 | name+0; embedded iterator+24, vtable`513574`, self value+38; child-name map+3c,count5; type map+44,count9 |
| Type44 | tag+0; embedded iterator+4,vtable`513570`,self value+18; ID map+1c,count19; name map+24,count19 |
| Resource96 | frozen constructor supplies name iterator+30,VT`51356c`,self+44; ID iterator+48,VT`513568`,self+5c |
| Map8 | bucket count+0; table pointer+4 |
| Bucket16 | source preserves words0/1; initializer zeros head+8 and tail+c |
| Embedded iterator24 | virtual table+0,next+4,previous+8,map owner+c,bucket index+10,value+14 |

Map construction first writes map.count, allocates **`4+16*N`**, writes count at allocation+0, initializes the buckets, then stores map.table=`allocation+4`. A null allocation leaves the nonzero count and table0. Do not allocate only`16*N`, omit the prefix, zero preserved bucket words, or create separate24-byte nodes for the embedded class iterators.

Insertion calls the actual iterator vtable slot0 before storing map owner/bucket index. It then composes original`4b5210` on the bucket's head/tail pair. That routine **prepends**, so creation order reverses within a collision bucket. The previous namespace module's disc-order fixture was a declared transport profile, not original construction evidence. Actual archive order is still a separate question.

Folder/type/resource hash wrappers compose the frozen unsigned length%5,tag%9,ID%19 and name-length%19 helpers. Resources are inserted into **both** distinct embedded iterators. Source duplicate admission is case-insensitive name within a type and exact unsigned resource ID within its ID map. Different types remain independent. The child creator updates controller+38 maximum name length; resource creator updates controller+3c, after rereading the controller pointer. Those fields are caller-owned startup inputs in the finite fixtures.

## Ownership and failure behavior

Folder constructor zeros only source-owned fields, preserving unnamed iterator words until insertion. It copies a mandatory nonnull name, including the terminator, with source dword-then-byte forward copy order; allocator callbacks may change the original name before its second length scan. Null name-allocation still returns the receiver with name0. Type constructor similarly preserves unrelated embedded words before insertion. No guessed all-zero class initialization is added.

Type cleanup captures the next iterator before unlinking. It removes all ID nodes first without freeing resources, then walks the name map, unlinks each node, composes whole frozen resource cleanup and frees each resource. It clears tag/self, destroys name buckets, then ID buckets. Folder cleanup removes and destroys types first, then recursively removes/destroys/frees children, frees its name and optional+20 buffer, clears the exact source fields and destroys type then child buckets. The root folder allocation itself remains caller-owned.

Map destructor frees allocation=`table-4` **without clearing map.table or map.count**. Embedded iterator metadata is not sanitized or separately freed. A second destruction can therefore elect stale storage/free identities. The raw oracle's allocator transport retains freed bytes for observation; that does not make physical double-free or stale-pointer use safe.

Missing type allocation in resource creation is not a clean return: the original continues into ID-map lookup through the null type. Null insertion/removal arguments likewise reach unchecked reads. The suite stops those exact source prefixes and checks earlier side effects; native missing-span rejection is not represented as an original success or error return.

## Archive boundary

The recovered creator`4b6a60` constructs an **empty** resource with the actual source zero payload fields and timestamp. It is not an archive-record decoder. Retail names/tags/IDs are test inputs to those creation calls; payload offsets, byte lengths and archive-loaded ownership require the archive loader's real caller graph.

Instruction evidence locates separate `4b6ed0` directory loading: allocation/read of directory bytes through`4b7ab0`, folder construction at`4b6fb8`, resource construction at`4b70d0`, and insertion at`4b6fd4/4b70ee/4b70fa`. Archive/controller opening starts`4b72e0`; its root folder constructors are called at`4b73b2/4b747f`, followed by`4b6b60`. Those larger reader/open/dispatch/format/failure bodies are **not recovered here**. Controller constructor`4b7210` is also outside this module; no all-zero controller startup or full retail boot order is claimed.

Physical CRT allocator/time, nonnormal CRT locale handling, original exception/unwind machinery and broader archive/stdio transport remain explicit. The finite map constructor specializes the actual pure bucket constructor/vector loop; teardown specializes the actual no-op bucket destruction loop. It does not export a generic replacement for every compiler array/exception helper.

## Verification

Run, sequentially from the repository root:

```
work/test-env/bin/python Tests/compare_resource_table_construction_runtime.py
work/test-env/bin/python work/resource-table-construction-agent/checks.py
```

The oracle executes the unchanged original and compares full1MiB heap,274,432 bytes of mapped globals, meaningful returns, RET arity, source allocation/free/live histories and ordered complete callback snapshots. Coverage includes exact bucket header/preserved words, retained tree construction and collision order, type reuse, duplicate names/IDs, null allocation paths, name/controller mutation at allocator/time boundaries, virtual hash callback ordering, three unsafe prefixes, real allocator wrapper composition, and170 retail names/tags/IDs spanning all14 levels plus GAME/CLAW/ROLLER/CREDITS. The metadata parser is explicitly a read-only format adapter, not original REZ boot.

The strict replay corpus uses exact76/44/96-byte classes,8-byte headers,`4+16*N` allocations, embedded nodes and live ownership. String allocations expose declared containing-word physical padding because frozen readers use that ABI. It checks source snapshots at every dependency and rejects access to not-yet-allocated/freed blocks. Final counts and gate status are recorded below and in private `verification.json`, `verify.log` and `checks.log`.

Final frozen evidence: **1,827 paired whole original calls,11,748 ordered full snapshot pairs,3 unsafe prefixes,1,172 instrumented original `.text` addresses and1,173 total instrumented addresses**. Snapshot count includes terminal whole-call states and addressed callback states. The final corpus contains **32 original-verified exact-class/map/embedded-node ASAN/UBSAN replays**, with live allocation checks and complete exposed-span comparisons at every callee boundary. C11, C++17 warnings-as-errors and Swift C11 import (80-byte native context) pass. All170 retail metadata profiles are recorded in `verification.json`; the exact original method inputs, allocation/lifetime histories and failure outcomes are checked, but retail archive-loading semantics and physical stdio/device acceptance remain outside the result.
# Root acceptance

Root independently reran the original comparison and strict/sanitizer checks,
both exiting0:1827 whole calls/11748 ordered snapshots/three unsafe prefixes,
170 metadata profiles and32 exact-span sanitizer histories. This family remains
source-only. Full REZ archive decoding and native boot are separate pending work.

