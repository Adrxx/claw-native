# Original resource archive loading

This module recovers nine complete original v1.0 procedures. It executes the source REZ directory grammar and composes the frozen resource-table, namespace, resource-data and allocator bodies. It does not substitute the editor's empty-resource creator for archive records.

The executable is `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. The disc archive is `Original/claw-disc/files/DATA/CLAW.REZ`, 118,033,115 bytes, SHA-256 `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`. Analysis is private to `work/resource-archive-loading-agent`; no reference implementation supplied the decoder.

## Whole source entries

All entries use the original receiver token. Argument counts below are stack words, excluding the receiver.

| Entry | Arguments | Behavior |
| --- | --- | --- |
| `4b7210` | none | 72-byte controller constructor; 61-byte original procedure |
| `4b72e0` | path, readOnly, create | Whole opener/header/root orchestration; 482 bytes, RET12 |
| `4b6b60` | offset, length | Recursive directory load; 106 bytes, RET8 |
| `4b6ed0` | offset, length | Actual folder/resource record reader; 664 bytes, RET8 |
| `4b7bd0` | path, readOnly, create | FILE open and virtual retry election; RET12 |
| `4b7c40` | none | FILE close and virtual retry election |
| `4b7c80` | none | FILE flush and virtual retry election |
| `4b74d0` | compact | Writer/close-or-compact/owned-tree cleanup; RET4 |
| `4b7250` | none | Whole controller destructor; 143 bytes |

The constructor installs `513578`, whose observed entries are `4b7a90`, `4b7aa0`, `42a680`, and zero. The retry method at virtual `+8` is the real `42a680` zero-return leaf in the default profile. The FILE wrappers re-read the handle around retries. Their physical calls and source-selected retry method remain synchronous callback boundaries.

## Native integration recipe

Use `claw_resource_archive_loading_entry` from `Sources/ResourceArchiveLoadingRuntime.h`. The context points to the frozen `ClawResourceTableConstructionContext`; its scene lookup, byte lookup, allocator and rich dependency callback must all address the same raw heap. Preserve the frozen table/core globals when dispatching composed methods. The module routes its own nine entries and executes the frozen table/namespace/data bodies internally; remaining calls are emitted through the same rich callback.

Allocate exactly 72 bytes for a controller, then call `4b7210`. This is not an all-zero constructor: it preserves raw `+14` and `+18`, clears `+8/+c/+10/+1c/+24/+28/+2c/+30/+34/+38/+3c/+40/+44`, sets `+20=1`, `+4=1`, and installs the vtable. Its meaningful EAX is the receiver. The final destructor does not free the controller allocation.

Supply a caller-owned 168-byte `headerToken` scratch span. This represents the original automatic header local, not a source heap allocation. The source read goes through frozen `4b7ab0`. Its reached `4a7260` fread callback has arguments `[0, 1, 168, FILEhandle]`, `localMask=1`, one mutable 168-byte buffer, and a synchronous before/after buffer lifetime. Seed it explicitly when testing short reads; the unfilled bytes retain their original seed.

Physical calls are `4f1d90` fopen, `4a7840` fseek, `4a7260` fread, `4a7ae0` fclose, and `4a7920` fflush. Modes are the actual literals: `532298` (`rb`), `5324cc` (`r+b`), and `5324d0` (`w+b`). `create && readOnly` returns zero without fopen. Successful open sets controller `+20` from the supplied readOnly word, not a normalized Boolean.

Header words are unaligned. The complete source opener maps these byte offsets to controller fields:

| Header byte offset | Controller offset |
| --- | --- |
| 127 | `+30` |
| 131 | `+10` root-directory offset |
| 135 | `+14` root-directory length |
| 139 | `+18` timestamp |
| 143 | `+1c` |
| 147 | `+28` |
| 151 | `+34` |
| 155 | `+38` |
| 159 | `+3c` |
| 163 | `+40` |
| 167 low byte | `+4` |

The original instruction loads a DWORD at header `+167` and masks to one byte. Only byte 167 affects the output. The native implementation consumes that one byte, avoiding an invented three-byte tail beyond the declared 168-byte input.

The opener allocates a 76-byte root folder, with source empty-name identity `534938`, and stores it at controller `+24`. Non-create arguments to frozen folder `4b6600` are `(controller, 0, emptyName, rootOffset, rootLength, timestamp)`. Create mode instead sets controller `+1c=168/+2c=1`, takes the timestamp from frozen `4b7cc0`, and constructs a zero-offset/zero-length root.

## Actual directory records and ownership

`4b6ed0` sets folder `+10=0` and `+c=FFFFFFFF`, allocates exactly the directory byte length, and reads the whole block. A failed allocation returns zero. A short read frees the block and returns zero. The source parses a raw cursor until it reaches the block end; it does not validate record lengths, string terminators, versions or magic values.

Kind `1` selects a folder record: DWORD offset, length and timestamp after the kind word, followed by a NUL name at byte `+16`. It allocates 76 bytes, calls frozen `4b6600`, and inserts the embedded node at child `+24` into parent map `+3c`.

Every other kind selects a resource record: DWORD offset, length, timestamp, ID, tag and auxiliary count at `+4..+24`, then name at `+28`, metadata NUL string immediately after the name, then auxiliary DWORDs. Empty metadata becomes a null constructor argument. Nonzero auxiliary count elects a temporary `count*4` allocation. The source obtains the type through frozen `4b7170`, allocates 96 bytes, and calls frozen `4b5ff0` with `(folder, name, ID, type, metadata, length, offset, timestamp, auxiliaryCount, auxiliaryPointer)`.

The source inserts the resource's ID node `+48` into type map `+1c`, then its name node `+30` into type map `+24`. It adds the length from resource `+14` to folder `+10` with DWORD wrapping, and tracks the minimum resource offset `+28` in folder `+c`. The original local maximum offset has no final stored output. Temporary auxiliary bytes are freed after constructor/insertion; the directory block is freed after parsing. Constructors retain their own copied names, metadata and auxiliary data according to frozen ResourceData ownership.

Frozen table insertion prepends the actual embedded nodes. Thus archive byte order is the creation order, while bucket iteration follows the source head/next links. Repeated directory loads append neither a canonical sorted table nor an editor duplicate gate: duplicate resource nodes are created and prepended. `4b6b60` uses frozen namespace iteration and recursively visits the resulting child links, continues siblings after a child returns zero, and returns aggregate success. Length zero returns one without dereferencing even a null folder.

## Failure and cleanup semantics

The source opener ignores both the 168-byte read count and the recursive loader's return value. After a successful physical open it returns one even if the deeper directory reads failed. Callers must not interpret that EAX as validated archive boot or a complete namespace. Failed fopen leaves the copied path allocated until source cleanup.

Source path, child and resource allocations contain unchecked follow-up uses. Native missing-span/operation guards reject those unsafe continuations rather than inventing original safe returns. The differential suite measures two stopped original prefixes: failed path allocation before the copy at `4b733e`, and failed child allocation before the invalid node read at `4d5458`. Other malformed-record and allocation failures can likewise fault; this module is not a hardened REZ parser.

Close `4b74d0` calls `4b7550` for writable controllers, ignoring its return, then chooses FILE close or `4b76b0` compaction, captures that result, recursively destroys/frees the root, frees the path, and clears ready `+8`. The writer `4b7550` and compactor `4b76b0` remain meaningful, explicitly unported source services. No source write/compaction success is claimed.

FILE close does not clear controller `+c`. The whole destructor can therefore elect fclose twice: once through ready-controller close and again through the still-nonzero handle. A physical transport must preserve this source ordering and report its actual result; it must not silently clear the handle. The destructor resets the specified fields, `+20=1/+30=1/+4=1`, and vtable, but does not release the controller itself.

## Verification and scope

`Tests/compare_resource_archive_loading_runtime.py` compares **450 whole unchanged-original calls, 6,052 ordered full snapshots and two unsafe prefixes**. It records **1,508 instrumented original `.text` addresses** (`401000..50adb5`) and **1,509 total instrumented addresses**, including service entry records. Each snapshot contains the full 1,048,576-byte raw heap and 274,432-byte mapped globals, ordered callback arguments, allocator liveness/free order, meaningful EAX, and local read-buffer changes. Only the transported 168-byte header scratch's heap representation is normalized; its actual source automatic bytes are checked through the callback buffer. Original instructions execute for the default zero-return retry leaf.

The read-only whole-disc record inventory is **1,384 folders / 13,077 resources**. All retail resource metadata strings and auxiliary counts are empty/zero. The measured corpus covers 53 actual shallow directories: all 14 level roots plus STATES/GAME/CLAW, all 14 PALETTES/WORLDS directories, and ROLLER/CREDITS descendants. Thirty nested graphs exercise full recursive loading/cleanup of the selected ROLLER/CREDITS and palette/world graphs. Whole opener cases consume the actual 168-byte header, root and 17 top-level directory blocks, with deeper FILE reads deliberately returning zero. This is a declared transport-failure profile, not a full 13,077-resource boot measurement.

Generated cases mutate a copied actual ROLLER palette record solely to elect nonempty metadata/auxiliary branches; they are not claimed to be retail records. Other directed cases cover seeded constructor preservation, partial header counts, open/close/flush retries, writable create/cleanup, null FILE handles, directory allocation/short-read/seek failures, repeat loads, and zero-length null recursion.

The private gate passes strict C11, warning-clean C++17, a Swift-imported 16-byte context, and **18 exact controller/class/map/resource allocation ASAN/UBSAN replays**, including live ownership and ordered full-span snapshots. Word-based legacy transport uses declared containing-word capacity for packed byte buffers; class/map allocations remain exact. No native app, device, complete archive startup, filesystem write or PCX acceptance is implied.

Run from the repository root:

```sh
work/test-env/bin/python Tests/compare_resource_archive_loading_runtime.py
work/test-env/bin/python work/resource-archive-loading-agent/checks.py
```

Measured outputs are `work/resource-archive-loading-agent/verification.json`, `verify.log` and `checks.log`.
