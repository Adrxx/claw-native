# Original resource byte lifetime

`ResourceDataRuntime.h/.cpp` supplies a generic raw-token adapter for the frozen
`AudioPCMTransfer` file acquisition/release/read bodies and recovers the missing
96-byte resource constructor4b5ff0, teardown4b6120 and type getter4b61b0.
PAL, image, ANI, WWD and other callers can compose the same source bodies without
an audio-specific native transport. No resource reference count is invented.

The original input is `Original/claw10/CLAW.EXE`, SHA256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Actual payloads come from the fingerprinted disc REZ SHA256
`b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.
Private original decompilation is in `work/resource-data-agent/core.c` and
`resource.c`. `load.c` confirms the existing135-byte4b7ab0 boundary; its original
analysis log also records a rejected interior4b60c0 address. That interior was
not used as a function or implemented. Folder constructor4b6600 is not owned
or claimed recovered here.

## Stable raw ABI and ownership

`claw_resource_data_entry(function, receiver, args, count, context, dependency,
user, result)` returns1 for recognized completion and puts original EAX in
`result`; unknown/fault returns0. Setcontext.fault0 before each call. Context
borrows `ClawSceneActorHost`, an optional frozen `ClawCArrayContext` allocator,
and a finite native operation guard. The allocator context must already use the
same token heap; this adapter does not overwrite its host or configuration.

The rich scalar dependency carries original function/receiver, count and up to10
argument words. Allocation/free use receiver0 and exact original argument order.
Physical services are4f63ec/4f6428 (or frozen wrapper composition reaching
4a48e0/4a49b0/module-handler services),4a7840(FILE,offset,whence),
4a7260(destination,itemSize,count,FILE), and the current stream's virtual+8
retry/reopen method. No resource bytes, names or addresses are rewritten into
synthetic success. The callbacks may mutate live resource/owner/stream fields.

Lookup requests aligned containing words. Names and optional metadata strings
need their final containing word readable, including physical allocator padding
under the word-only host. Resource views are96bytes, owner folder views76bytes,
and stream views44bytes in tested source profiles. File/resource type is fetched
from the type object referenced atresource+8, retaining its actual integer tag.

| Entry | Arguments / cleanup | Composition |
|---|---|---|
|4b5ff0|10 words, RET40|whole original resource constructor|
|4b6120|none, RET0|whole original resource teardown|
|4b61b0|none, RET0|type object's word0|
|4b61c0|none, RET0|frozen acquire-file body|
|4b6230|none, RET0|frozen release-file body|
|4b7ab0|offset,count,destination, RET12|frozen whole-file read/retry body|

Constructor arguments are ownerFolder,name,resourceID,typeObject,
optionalMetadata,sizeBytes,fileOffset,auxiliaryScalar,auxiliaryWordCount,
optionalAuxiliaryWords. It stores embedded vtables51356c at+30 and513568 at+48;
initially clears embedded owners+44/+5c, then finishes both withself. A null name
preserves originalword0 rather than clearing it. Nonnull strings allocate exact
`strlen+1` and copy their new live contents after allocation. A null metadata
string clears+0c. Optional auxiliary words allocate wrappingcount*4 and copy
word-by-word. Allocation failure preserves the original constructor's nonzero
receiver return; this is not a separate successful-resource admission claim.
Unnamed padding/iterator fields are untouched.

Teardown frees name, metadata, optionally cache, then auxiliary words in source
order. Cache free is skipped when ownerFolder+20 mapped buffer is nonzero; a
null owner permits cache free. It clears words0..11 and embedded owner words+44
and+5c, preserving other96-byte fields. Teardown is originallyvoid: recorded
machine EAX depends on the final optional auxiliary free; it must not acquire a
host boolean meaning. It does not itself free the96-byte object allocation.

## Acquire, retry and release

Acquisition checks ownerFolder+20 before cache or length. A nonzero mapped base
returns wrapping(resourceOffset-ownerBaseOffset+mappedBase), leaves cache intact,
and performs no physical read. A cache atresource+18 is reused. Zero size returns0.
Otherwise it allocates exactlyresource+14 bytes, stores cache before reading,
then reads through the newly loaded ownerFolder+18 stream. A whole-read count
mismatch frees the current live cache and clears it. Allocation failure returns0.

The original read seeks with whence0. Failed seeks call current stream virtual+8;
accepted retry repeats seek using the current stream+0c FILE handle. Successful
seek elects fread(destination,1,fullCount,liveFILE). Partial reads retry the full
count into the same destination without another seek. Rejected retry returns0;
full count returnscount. Count0 touches no stream. The original has no retry
limit; native maximumOperations is a separately declared safety diagnostic.

Release frees only current resource+18 when nonzero, clears it, and returns1.
Repeated release returns1 without another free. It does not unmap owner data.
Physical allocator/FILE lifetime, archive mapping setup, REZ decoding and resource
registration remain explicit. The measured fixture's free transport records
ordered frees and retains storage for complete snapshots; it does not emulate a
physical heap decommit or prove that stale aliases remain usable after free.

## Corrected frozen owner reload

A directed allocator callback changes resource+24 fromOWNER toOWNER2. The prior
frozen `claw_audio_acquire_file` kept its first owner pointer and usedFILE17;
unchanged original4b61fe reloads resource+24 and usedFILE43. Complete heap/events
proved the discrepancy; `owner-reload-before-fix.json` preserves the witness.
The authorized correction in `AudioPCMTransfer.cpp` adds only the owner reload
and null-span diagnostic after allocation, before the file-read call. It changes
no public API. `check-owner-reload.py` verifies the corrected full original call.

## Verification

Run `work/test-env/bin/python Tests/compare_resource_data_runtime.py`,
`work/test-env/bin/python Tests/compare_audio_pcm_transfer.py`, and
`work/resource-data-agent/check-abi.sh`. The final suite passes2572 whole original calls /5566 complete snapshots,
4 matched unchecked-pointer prefixes,113 exact-size ASAN/UBSAN replays,
and216 actual disc profiles (28 WWD histories across14 distinct worlds).
It records321 instrumented addresses,320 within originalPE.text; the count
includes adapted physical-service entries and is not unchanged-body coverage.
Private reports contain actual metadata profiles, sanitizer material and frozen
source hashes.

Normal comparisons execute whole unchanged original constructor, teardown,
getters, acquire/release/read and optional allocator wrappers. Physical CRT,
stdio and retry/reopen services are explicitly adapted with complete pre-call
1MiB heap plus64KiB globals snapshots. Final comparisons include machine EAX,
exact stack cleanup, callback order, allocated sizes, bytes and frees. Profiles
cover seeded raw buffers, retained constructor→load→cache→release→teardown,
mapped/stale cache, zero size/count, allocation failure, seek/read retries,
owner/length/cache callback mutations,216 actual disc payload profiles and all14
worlds. Four null-pointer prefixes are tracked separately from successful
returns; native guards do not convert unchecked original faults into success.

The existing audio suite passes2000 acquire/release pairs,2000 direct reads,
3000 PCM transfers,2000 manager wrappers,2000 sound load/unload pairs,
1500 teardowns, directed callback snapshots and144 real-disc cases. It records
916 instrumented original addresses. These source comparisons and strict
C++/C11/Swift imports plus exact-size ASAN/UBSAN replay do not establish full
archive startup, physical audio/render acceptance or complete game identity.
