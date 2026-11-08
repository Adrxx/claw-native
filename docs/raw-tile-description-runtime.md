# Original raw tile descriptions

`RawTileDescriptionRuntime.h/.cpp` recovers the complete query portion of the
three original tile-description vtables in the hash-pinned v1.0 executable.
WorldFileRuntime retains construction, mask ownership, destruction and raw
record-advance ownership. The existing flat TileCollision API remains unchanged.
The raw simple-point adapter composes its proven attribute implementation;
rectangle queries preserve the original short-circuit raw field reads rather
than requiring the different flat structure to be present in the heap.

## ABI and original identities

The C11 entry API takes the description's original 32-bit heap token, four raw
argument words plus an exact argument count, and the frozen SceneActorHost.
`claw_raw_tile_virtual` resolves only the owned query slots through verified
original vtable identities. `claw_raw_tile_function` exposes this mapping for
host integration. Unknown vtables/slots/functions remain unsupported.

| Slot | Arguments | Simple `513980` | Rectangle `5139c8` | Mask `513a10` |
|---|---|---|---|---|
| `1c` | none | `4bd250` type1 | `4bd240` type2 | `40af90` type3 |
| `20` | x,y | `4cddc0` | `4cde10` | `4cdef0` |
| `24` | none | `4cde00` advance20 | `4cde40` advance40 | `4cdf10` advance16+width×height |
| `28` | x,y,coordinateOut,attributeOut | `4cddd0` | `4d5c80` left transition | `4d5900` |
| `2c` | x,y,target,coordinateOut | `4cddd0` | `4d5ce0` left target | `4d5960` |
| `30` | x,y,coordinateOut,attributeOut | `4cddd0` | `4d5e30` up transition | `4d59b0` |
| `34` | x,y,target,coordinateOut | `4cddd0` | `4d5e90` up target | `4d5a20` |
| `38` | x,y,coordinateOut,attributeOut | `4cdde0` | `4d5d50` right transition | `4d5a80` |
| `3c` | x,y,target,coordinateOut | `4cddd0` | `4d5dc0` right target | `4d5af0` |
| `40` | x,y,coordinateOut,attributeOut | `4cddf0` | `4d5f00` down transition | `4d5b50` |
| `44` | x,y,target,coordinateOut | `4cddd0` | `4d5f70` down target | `4d5bd0` |

Type1's right/down transition methods return `width−1` / `height−1` in EAX,
without modifying either output. Its other scan methods return0 without
modification. This is the original behavior, even though rectangle and mask
scan success returns1 and writes outputs. The host must retain those distinct
contracts rather than interpreting every nonzero scan result uniformly.

The type1 layout is `[vtable,width,height,attribute]`. Type2 is
`[vtable,width,height,outside,inside,left,top,right,bottom]`. Type3 is
`[vtable,width,height,shift,byteCount,maskToken]`; these are raw contiguous
32-bit words, not the flat ClawTileDescription layout. The heap objects remain
owned by the caller's WorldFile graph and are invalid after its cleanup.

## Exact query behavior

Rectangle membership uses signed inclusive comparisons. Transition scans gate
the orthogonal coordinate by that same rectangle and select its next inside
or outside boundary in the requested direction. On success they write the
coordinate first, then read the selected attribute from the raw descriptor
and write it. A coordinate output aliased to the inside/outside field therefore
changes the later attribute output. Target scans compare the complete32-bit
target before writing the coordinate. Failed scans preserve outputs.

Mask point lookup is exactly `maskToken + (y << (shift &31)) + x`, with wrapping
32-bit arithmetic and a zero-extended byte result. It has no coordinate clamp,
width/height check or malformed-coordinate return0. A byte beyond the nominal
mask can be read if the original surrounding memory is readable.

Mask transition scans read the initial byte before the directional boundary
gate. Target scans have no initial-byte read. Scans advance one coordinate at
a time, stepping the raw index by1 horizontally and width vertically, and
include coordinate0 or dimension−1 as appropriate. They compare bytes against
the cached initial byte or the full32-bit target. A target greater than255
never matches a zero-extended mask byte. On transition success the coordinate
store precedes reloading the mask token and reading the output attribute;
aliasing that token is preserved. Shift masking and width-based vertical
steps are not replaced with inferred square-tile semantics.

The source type3 constructor computes shift from height but verifies
`1 << shift == width`. The tests compose the frozen source constructor:
8×12 and16×17 masks succeed, while4×8 and8×4 fail. This asymmetry is preserved.

## Host and failure profile

Queries use only `SceneActorHost.lookup`; allocator, free, clock and external
call callbacks are unused by the new query bodies. Byte and unaligned output
accesses request aligned word spans and use byte offsets/memcpy internally.
The host must return stable, readable/writable raw spans with the original
byte values and identities. It must not infer a mask's nominal extent as a
substitute for actual surrounding readable bytes.

The native completed/supported result is separate from original EAX.
Fault1 means a missing span, fault2 an unsupported identity or wrong argument
count, and fault3 the one-million-iteration diagnostic cap. These are explicit
native diagnostics for unsafe/unbounded original access, not recovered
ordinary original return values. Stores already completed before a failed
access remain in the raw heap. Frozen record-advance composition uses its
documented span assumptions. Physical allocator identity/address selection is
still a host service, and resource/world/plane/actor lifecycle remains outside
this query module.

## Evidence and verification

The executable SHA256 is
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
The original REZ SHA256 is
`b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.
Private Ghidra decompilation is in
`work/raw-tile-description-agent/queries.c`; its log verifies all25 newly
recovered function boundaries, checked against actual instructions. Record
advance is composed from frozen WorldFile rather than copied.

Run `work/test-env/bin/python Tests/compare_raw_tile_description_runtime.py`.
The suite independently enumerates and decompresses the fingerprinted REZ,
constructs each of all9,336 records through the real original factory and the
frozen native factory, and retains each object through all11 query slots and
deletion. These are8,231 simple and1,105 rectangle records across14 worlds;
there are no type3 records in that actual table set. Type3 comparisons are
separate directed/source-constructor cases, not claimed shipped usage.

Every successful original call compares EAX, exact stack-pop size and the
entire64KiB seeded raw arena against native output. Construction/deletion
events compare ordered allocation/free arguments and whole-arena snapshots.
Only physical4f63ec allocation and4f6428 free are adapted; freed bytes remain
readable for comparison, and allocator implementation equivalence is not
claimed. Original image/global writes are monitored and the full mapped image
is checked unchanged. Coverage includes signed and wrapping fields, targets
outside byte range, unaligned masks/outputs, same output pointers, descriptor
and mask aliases, retained scan/mutation histories and four original unmapped
access/partial-store cases. Exact totals are saved in the private
`verification.json` rather than inferred from tests alone.

Sanitizer replay uses a private standalone C++ executable to avoid the macOS
Python launcher's late AddressSanitizer interceptor initialization. Its corpus
contains complete before/after heaps and EAX/cursor values verified against
the original, including every supported function and aliases/retained cases.
Run `bash work/raw-tile-description-agent/check-sanitizer.sh` after the oracle.
These bounded function comparisons do not establish full-game equivalence or
retail application startup equivalence.

Final verification:149,790 completed original calls;18,792 ordered complete
heap service snapshots;888 original instruction addresses;31 exact stack-pop
profiles;2,996 directed seeded profiles/chains;4 original fault comparisons;
zero original image/global writes. C11 header compilation passed. The
standalone AddressSanitizer/UndefinedBehaviorSanitizer replay passed all262
captured complete-heap calls with no diagnostics. `git diff --check` passed.
