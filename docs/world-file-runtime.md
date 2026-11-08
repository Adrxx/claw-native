# Original v1.0 world file runtime

`WorldFileRuntime.h/.cpp` recover complete original world load entry `4cb200`, its compressed-header wrapper `4cd660`, file/resource wrappers, world constructor/default state, all three tile-description factories, and world/plane cleanup and deletion. They compose frozen WorldPlaneRuntime, SceneCameraRuntime, CArrayRuntime and SpatialGridRuntime rather than creating a second plane/grid interpretation. File/codec/resource services and actual actor-record creation remain named boundaries.

The source executable is SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. The actual 14-world resource corpus is extracted from REZ SHA-256 `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`. Ghidra evidence is private in `work/world-file-agent/{file,descriptions,wrappers,plane-cleanup-body,world-cleanup,array-destructor,codec}.c`; original instruction bodies remain the oracle. No reference gameplay source is copied. This module does not claim complete game, asset-version identity, Windows file/codec internals, or native UI acceptance.

## C11 contract

`claw_world_file_entry(function,receiver,args,context,dependency,user,&result)` accepts four original argument words plus count. Return 1 means a supported entry completed, including original ordinary return-zero failure paths. Return 0 means unsupported entry or native fault. Meaningful original results are written through result; void incidental EAX is excluded. Initialize `context.fault` and optional CArray context fault to zero. Native faults: 1 missing graph/service; 2 unsafe/unsupported metadata, allocation, or loop bound.

Context supplies raw SceneActorHost token/word lookup, allocation and free. An optional frozen CArrayContext composes actual CArray metadata operations with its caller-owned allocator/CRT profile. Null instead exposes those operations at explicit service boundaries. Its scene host is assigned from the world-file context, while allocator mode/global fields are preserved. `composeSpatial != 0` composes actual frozen `4d1620` grid construction and its original record-call ordering; `4d17e0` actor-record construction remains a service. There is no invented object/no-op gameplay implementation.

`ClawWorldFileCall` preserves original function, receiver, argument count and four arguments. Temporary plane ANSI lookup names are provided as synchronous `name`. Codec output-count and four-word local file objects are provided as mutable `size` and `temporary`; their original stack pointer/receiver identities are normalized to zero. Heap pointers retain raw token identity. Never keep temporary pointers after the callback.

| Entry | Receiver and arguments |
| --- | --- |
| `4cb200` | world; WWD buffer token |
| `4cd660` | receiver ignored; source WWD, destination, capacity |
| `4cb470` | world; ANSI filename token; original open/size/read/load/free/close wrapper |
| `4cb5a0` | world; resource object token; GetData/load/release wrapper |
| `4cace0` | world; parent scene, ID, flags; complete 224-byte constructor stores |
| `4cb180` | world; none; cleanup plus viewport-left INT_MIN |
| `4cb5f0` | world; none; cleanup retaining viewport-left |
| `4cdd30` / `4cdd10` | world; none / deleting flag; complete base/deleting destruction |
| `4cb700` | receiver ignored; raw tile-description record; exact 1/2/3 factory |
| `4d5840`, `4d5c30`, `4d5870` | description; raw record; simple/rectangular/owned-mask loading |
| `4cde00`, `4cde40`, `4cdf10` | description; none; original raw record advance sizes |
| `4d5330`, `4cde70` | description; deleting flag; complete simple/owned-mask deletion |
| `423f00`, `4cde90` | description; none; corresponding base destructors |
| `4d2210`, `4d2230`, `4d0a00` | plane; deleting flag / none / none; exact plane lifecycle |
| `4f58de` | embedded CArray; none; destructor stores and free, including null |

Unknown virtual entries dispatch through the explicit dependency callback. Known original world/description/plane vtable identities resolve without needing to materialize original executable pointers as native function pointers.

## Raw startup graph and defaults

Allocate **56 words / 224 bytes** for the world, 86 words for each plane, and retain the parent's 12-word scene graph. World vtable is `513938`; +38 is `4cb200`, +44 is `4cb5f0`, +4 is deleting destructor `4cdd10`. Parent scene +24 points to this world. Parent +8 is the actor container and +10 the image/resource registry holder. World +5c/+60 hold main plane pointer/index. The scene initializer's world allocation/registration order is owned by SinglePlayerSceneRuntime, not fabricated here.

The complete world constructor assigns vtable, ID +4, flags +8 and parent +c, and constructs three embedded CArrays at +20/+34/+48. It sets viewport-left +10 to INT_MIN, tile defaults +64/+68 to 64, main pointer +5c to zero, main index +60 to FFFFFFFF, and header metadata +ac to zero. All other unwritten fields retain heap seed. The six spatial pairs +b0..dc are exactly 500/250, 1000/1000, 250/125, 1600/1200, 2560/1920 and 768/576. Compose frozen SpatialGridRuntime `4cb040(width,height)` or `4cb0e0(rectToken)` for a valid inclusive viewport before loading a normal scene; the original gameplay profile is 640 by 480.

| World offset | Runtime content |
| --- | --- |
| +10..1c | Inclusive viewport |
| +34..44 | Plane CArray: vtable/data/count/capacity/growBy |
| +48..58 | Tile-description CArray |
| +5c/+60 | Main plane pointer/index; last successfully added flag-1 plane wins |
| +6c..ab | Owned copied world title, including terminator |
| +ac | Original WWD header word at +748 |
| +b0..dc | Six original spatial-size pairs |

The input buffer must remain live through the whole load. Original plane/tile/object source offsets are relative to the decoded WWD base. Successful loading copies tile arrays, rows, plane names, description fields and type-3 byte masks into owned runtime allocations. Actor records are consumed synchronously at the `4d1620`/`4d17e0` seam; a host adapter must copy/materialize their fields and strings before the decoded buffer is freed. Storing that temporary record pointer for later gameplay is invalid original ownership.

Raw tile-description records in actual WWD files can be **unaligned**. This module reads their scalar fields through aligned-span byte access and memcpy, while allocated runtime objects stay aligned. Raw tile arrays consumed by frozen WorldPlaneRuntime retain that module's aligned-word input contract. Resources need readable final word padding for byte lengths not divisible by four. No ARM64 pointers are truncated into raw tokens.

## Whole load and decompression ownership

`4cb200` invokes world virtual +44 cleanup **before validating the input header**. It accepts header-size word +0 when unsigned <=5f4; it does not impose a new exact-size equality. When input flags +8 contain bit 2, it allocates `declaredDecodedBytes + headerSize + 64`, then invokes the complete `4cd660` wrapper with capacity `declaredDecodedBytes + headerSize + 32`.

The compressed wrapper checks source/destination/header/flag/declared count, copies exactly the original header bytes, then calls original zlib uncompress boundary `4d5fe0(destination+header, &count, source+header, declaredDecodedBytes)`. Its output capacity is declared bytes +32, and success requires return zero and resulting count **exactly equal to the current original header +744 word**. The original advertised source count is the declared decoded count, despite the compressed file being shorter. The service must preserve that argument contract; valid zlib streams stop at their end marker. Native buffer bounds/size checks extend original unsafe behavior, not malformed-input equivalence. For a bounded native zlib backend, find the source token's containing owned file allocation and use its actual remaining bytes rather than requiring an oversized lookup of the advertised decoded count. All 14 original valid streams stop before those trailing bytes matter. Feed the original compressed WWD to `4cb200`; a Swift-already-decoded buffer retaining compression bit 2 is not valid input to that path.

The module intentionally exposes the codec as a service, not a claim that system zlib's internal heap is original zlib's heap. The separate `world_file_codec_oracle.py` executes the complete original **zlib 1.0.4** body `4d5fe0`, adapting only its physical calloc/free functions. All 14 real payloads match the declared native/Python zlib output and exact output counts, with leading/trailing guards and spare 32 bytes unchanged. Its 2,597 calloc and 2,597 free events prove that original codec execution completed without leaking its adapted blocks; they do not equate native zlib's internal allocator sequence. Codec corrupt-stream/version/other-library error behavior remains outside corpus parity.

After decompression, `4cb200` copies title, flags, +748 metadata and structural counts/offsets from the **original input header**, not the copied header. It advances each plane record by 160 bytes and calls frozen whole `4cb7b0` add-plane. It then reads the optional tile-description table at header +740 (count at table +8, first record at +32), constructs each description, advances using its actual virtual +24 result, and inserts it into world +48 CArray. There is no low-16/high-16 tile rewriting or guessed description allocation.

A failed plane/description load frees the temporary decompression allocation but retains already inserted runtime objects until subsequent cleanup. Codec and safe top-level allocation failures return zero before later header stores. Successful loading initializes centers, frees the temporary decoded allocation, and returns one. Uncompressed input is used directly and is never freed by `4cb200`; ownership belongs to its file/resource caller.

## Exact initial center propagation

Header +720 and +724 are interpreted as signed 32-bit initial center coordinates. The main plane receives those values via the original float/scaling rule and frozen `4d0a60` clamp. The loader then captures **main plane integer center +84/+88 after clamp** and uses those captured integers for every other plane, with each plane's original +18/+1c scale if flag 1 is clear, followed by another clamp.

This is not scaling the unclamped header coordinates or scaling a UI viewport's top-left. Signed integer conversion uses double intermediates corresponding to the original x87 profile, then float stores; it does not introduce an early float rounding before multiplication. Tests include signed extrema, wrapping plane flags, actual startup centers and the original percentage-to-float factors supplied by frozen WorldPlaneRuntime.

## Tile descriptions and full cleanup

Description kinds 1/2/3 allocate **16/36/24 bytes**, with vtables **513980/5139c8/513a10**. Type 1 copies three words from raw +8 and advances 20 bytes. Type 2 copies eight words from raw +8 and advances 40. Type 3 stores width/height, derives a right-shift count from **height**, compares `1 << shift` to **width**, allocates width×height bytes and copies the raw mask at +16; its advance is width×height+16. The apparent width/height power-check asymmetry is preserved. Constructor fields and unused seed bytes are not replaced by a Swift/reference-format convenience structure.

Simple deleting destructor `4d5330` sets base vtable 50becc and optionally frees the object. Type-3 `4cde70→4cde90` sets its class vtable during destruction, frees and clears the owned mask, then sets base vtable and optionally frees the object. Delete uses low bit only.

World cleanup iterates live plane count, invoking each plane's actual deleting virtual +4, resets plane CArray to size zero, then deletes every tile description and resets that CArray. `4cb180` additionally writes viewport-left INT_MIN; `4cb5f0` does not. Both clear main pointer/index. The full world destructor first installs vtable513938, invokes `4cb180`, destroys embedded arrays in order **+48, +34, +20**, resets ID/flags/parent and base vtable, then deleting wrapper optionally frees the world.

Plane `4d2230` installs plane vtable513d40, deletes dormant grid actors via frozen `4d50e0`, clears/frees the grid via frozen `4d4b00`, frees and clears tiles and rows, destroys image-manager pointer CArray at +9c, then resets ID/flags/parent and base vtable. The original grid pointer field is not helpfully nulled; preserve its dangling value and avoid reusing a destroyed object. Actual actor polymorphic destruction stays at the frozen spatial callback seam. No resource-manager objects are newly claimed to be owned by the plane pointer array.

## File/resource adapter boundaries

`4cb470` preserves ordered local-file construction, open, size, allocate, size again, read, world virtual +38, free file bytes, and local-file destruction. Open/allocation failure still destroys the file object. CFile/CString/Win32 bodies remain explicit `4f72c9`, `4f7448`, `4f774d`, `4f7570`, `4f7369` services with the mutable four-word local object and normalized stack receiver. Read return is ignored by the original wrapper; load result decides success.

`4cb5a0` calls resource GetData `4b61c0`; null returns immediately without release. Non-null data is passed to world virtual +38, then `4b6230` releases it on both success and failure. The record-grid callback is explicit original `4d17e0`, not a registry-name-based invented dispatcher. Native arrays and grids may be composed by context; unresolved alternate polymorphic/resource/scene callbacks remain declared services.

## Validation

Run `work/test-env/bin/python Tests/compare_world_file_runtime.py` and `work/test-env/bin/python Tests/world_file_codec_oracle.py`. The main suite hashes the entire declared **16,777,216-byte raw heap at every ordered event and return**, comparing live/freed object seed, records, decoded headers, tiles, rows, description masks, array metadata and ownership/free order against whole original entries. Only adapted temporary stack identities and void incidental EAX are excluded. Windows CopyRect/SetRect shims are exact memory copies/stores required by frozen camera/spatial bodies; no UI is driven.

All 14 original compressed worlds are whole-call fixtures. The 34,784 complete raw object records are sampled in order at the live record boundary before decoded buffer free; that boundary is declared rather than counted as recovered actor logic. Actual Level 1 also executes the real frozen spatial constructor/record-caller graph, retained reload, then whole world/grid deletion, with actor creation remaining explicit. Directed fixtures cover compressed/uncompressed inputs, missing image lookups, optional array-service mode, signed startup centers, invalid headers/planes/descriptions, decoder failure, top-level allocation failure, file/resource success/failure, 12 seeded complete constructors and deleting flags. Final main-suite evidence: **100 whole original calls, 25,740 ordered full-heap events, 2,486 original-image addresses**, 14 original worlds and all 34,784 raw records. The separate whole original codec suite covers **14 calls, 2,407 original-image addresses, 2,597 calloc and 2,597 free events**. Exact reports are `work/world-file-agent/verification.json` and `codec-verification.json`.

C11 warning-clean compilation and native Swift bridge execution pass. Swift checks exact world defaults and unwritten-word preservation, an unaligned type-3 record copied into an owned mask, and ordered world/description/array destruction. No Xcode, simulator, device or physical OS file/codec/renderer parity is claimed.
