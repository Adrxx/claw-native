# Original pointer CArray runtime

`CArrayRuntime.h/.cpp` recover original v1.0 pointer CArray constructor `4f58ab`, SetAtGrow `4f582f`, SetSize `4f5915`, and their required allocation/copy graph. Original instruction comparisons pin `Original/claw10/CLAW.EXE` SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private Ghidra logs corroborate observed entry boundaries and contain no script errors.

The arrays embedded at world+`34` and plane+`9c` use these exact routines. SetAtGrow **overwrites an index without shifting other elements**. Its name must not be interpreted as an insertion that moves a suffix.

## Stable host API

`claw_carray_entry(function,receiver,arg0,arg1,arg2,context,dependency,user,result)` returns1 for supported functions. `ClawCArrayContext.scene` is the frozen `ClawSceneActorHost` raw-token heap. Lookups retain the shared aligned four-byte-word ABI. Memory helpers round the requested address down to a word boundary and access its byte offset; no unaligned lookup is required. The dependency carries original function identity, receiver and ordered raw arguments. If no rich dependency is supplied, calls use `scene.call` with the same argument contract.

| Function | Original ABI / arguments |
| --- | --- |
| `4f58ab` | thiscall array, no arguments |
| `4f582f` | thiscall array `(index,value)` |
| `4f5915` | thiscall array `(size,growBy)` |
| `4f63ec` | cdecl `(bytes)` |
| `4f6428` | cdecl `(pointer)` |
| `4a4a20` | cdecl memset `(destination,byte,count)` |
| `4a4a80` | cdecl overlap-safe copy `(destination,source,count)` |
| `4a48e0` | cdecl CRT allocation `(bytes)` |
| `4a4900` | cdecl CRT allocation `(bytes,newMode)` |
| `4a4950` | cdecl CRT physical-allocation selection `(bytes)` |

`result` preserves measured EAX for the represented paths. Constructor returns the array token; SetAtGrow leaves its data pointer in EAX. SetSize and free are void functions originally, so the machine-register result must not gain a new gameplay meaning. Allocation returns a token or0; memory helpers return their destination token. Original callee stack cleanup is separately checked, including the8 bytes removed by SetAtGrow/SetSize.

## Raw header and resizing

The five-word header is `[vtable,data,size,capacity,growBy]`. Constructor writes `5108fc,0,0,0,0` and preserves every surrounding byte.

SetAtGrow compares signed index against signed size. If `index >= size`, it calls SetSize with wrapped `index+1` and growBy=`ffffffff`; it then rereads the data pointer and stores the raw value at wrapped `data+index*4`. It does not check negative indices. Native heap-span diagnostics do not turn this unsafe original behavior into a new valid-index rule.

SetSize updates growBy first if the supplied value differs from`ffffffff`. New size0 calls free even when data is0, then zeros data/capacity/size; it preserves growBy and all other words. With null data and nonzero size, it allocates wrapped `size*4` bytes, stores the returned pointer before memset, zeros those bytes, then sets capacity and size to the requested value.

For nonnull data and signed requested size within capacity, it preserves the pointer and capacity. A larger logical size zeros only the interval from old size to requested size; shrinking does not clear truncated values or release memory. If requested size exceeds capacity, explicit nonzero growBy is used directly. Default growBy0 selects signed `oldSize/8`, clamped to4..1024. New capacity is the signed maximum of wrapped `oldCapacity+growth` and requested size. It allocates `newCapacity*4`, copies `oldSize*4`, clears only `(requestedSize-oldSize)*4` bytes after that copy, frees the old pointer, then commits new pointer/size/capacity. **Spare capacity bytes remain untouched**.

Allocator/free callbacks may mutate headers. The port reloads the original fields at the observed boundaries: capacity is computed before allocation, copied size and old pointer are read after allocation, and final header commit follows free. Tests explicitly exercise mutations during these callbacks. Stable spans are required during every allocation and callback.

`4a4a20` and `4a4a80` are represented by their exact memory effects and return values, using native memset/memmove. Original instructions execute in the oracle over forward/backward overlap, byte alignments, zero lengths, short copies and larger word-copy paths. Wrapped pointer/count cases that leave represented heap storage are native faults rather than normal-return equivalence claims.

## Allocation modes and boundaries

Context `composeAllocator=0` exposes logical allocator `4f63ec(bytes)` and free `4f6428(pointer)` as explicit services. This is suitable for the native token heap's physical allocation policy. No malloc layout or OS heap equivalence is implied.

Mode1 composes actual `4f63ec` while keeping CRT `4a48e0` explicit. It captures original global new-handler identity`510020`, tries allocation, and, after failure, calls module-thread lookup `5022b5` only when its current handler equals the live global. It reads the thread view's handler at+`28`, stops when handler is0 or returns0, and retries when it returns nonzero. Global identity changes are preserved between attempts. `4f6428` delegates the exact `4a49b0(pointer)` boundary, which can route into frozen `CoreRegistration` for the recovered CRT free wrapper.

Mode2 additionally composes actual `4a48e0`→`4a4900`→`4a4950` allocation selection. CRT size0 becomes1. Sizes above`ffffffe0` return0. The CRT newMode parameter is captured per call; failed physical allocation invokes `4ad350(bytes)` and retries only when newMode and that handler's return are nonzero. `4a4950` rounds bytes to16 using wrapping `(bytes+15)&fffffff0`. If rounded size is at most the live small-block threshold, it executes `lock9` (`4a7bc0(9)`), small-block allocation `4ab4c0(roundedSize/16)`, then `unlock9` (`4a7c40(9)`). A nonzero small-block token returns; otherwise it calls the supplied resolved HeapAlloc identity with `(heapHandle,0,roundedSize)`.

`claw_carray_defaults` writes only verified image values: global new handler=`ffffffff`, CRT newMode=0 (`540fe8`), small-block threshold=480 (`5312d4`). It preserves mode, fault, raw host and allocator identities. Heap handle represents`545fc4`; `heapAllocFunction` represents the resolved function identity from original IAT`546960`, not its unresolved image contents. The caller supplies these initialized platform values. Small-block allocator internals, locks, module-thread allocation, both handler bodies, Win32 HeapAlloc and CRT physical free remain explicit service boundaries. Mode2 proves their selection, parameters, ordering and retry control flow, not the platform allocator internals.

## Fault scope

Fault1 means a missing raw span/service. Fault2 reports a null pointer reaching a nonempty memory helper or a native safety bound. Retry loops are bounded at one million attempts; a stopped original infinite allocation loop has no successful-return claim. Unsupported entry functions return0 before mutation. Clear context fault deliberately before each new operation.

The original SetSize has no null-result check before copying/zeroing. The native API preserves mutations preceding that boundary and reports its diagnostic instead of completing unsafe writes. Six dedicated fixtures witness the first actual original store through null and compare the retained host heap/events at that boundary. The oracle's synthetic low page exists for FS exception-chain access; those fixtures interrupt the offending low-page store and do not count it as normal original completion. EAX, normal SP cleanup and FS restoration are asserted for normal returns only. Physical allocator failure/refusal is also tested directly through allocator entrypoints that legitimately return0.

## Joined plane evidence

The private generated C++ bridge routes frozen `WorldPlaneRuntime` dependencies `4f582f` directly into this recovered native CArray. The original oracle executes its real `4f582f`/`4f5915` bodies rather than intercepting them with an array fixture. Across all14 hash-pinned disc worlds,42 consecutive plane additions copy1,886,406 tile words and preserve retained world/resource array state. This adds266 complete pre-call heap snapshots. The original and native constructors, plane loading, growth/copy/free, insertion order, main-plane selection and camera clamp compose correctly within the declared services.

Image registry lookup, grid/object initialization, logical physical allocation and CopyRect remain explicit services in that joined evidence. Source-derived asset reading/decompression comes from the frozen plane input adapter. There is no guessed array growth, shifted insertion, approximated resource playback, or pickup substitute in the joined path.

## Verification

Run `work/test-env/bin/python Tests/compare_carray_runtime.py`. It builds optimized C++ with warnings treated as errors, then compares all6MiB raw heap bytes, five live allocator globals, meaningful/machine EAX, exact SP cleanup, normal FS restoration, callback arguments and ordered complete snapshots. Directed cases cover seeded preserved words, explicit/default/signed growth, overflow capacity selection, zero/release/shrink/regrow, signed index stores, header mutations during allocation/free, allocator retries/refusal/global changes, CRT zero/maximum sizes, small-block success/fallback, byte fill and overlapping copy. There are32 retained array histories with1,568 calls, plus42 retained original plane additions. Four additional complete operations exercise plain `scene.call` fallback with no rich dependency. The combined suite contains2,255 normal-return comparisons and six separately reported unsafe null-access witnesses,2,431 complete callback snapshots,999 executed original addresses and583 directed cases. Final counts are recorded in private `work/carray-agent/verification.json`; joined/fallback counts are also in their separate proof JSON files.

These bounded body and composition checks establish array behavior under explicit allocator/resource contracts. They do not establish native physical heap equivalence, complete retail resource startup, or whole-game identity.
