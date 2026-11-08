# Original world-plane construction and configuration

`WorldPlaneRuntime.h/.cpp` recover complete original v1.0 plane constructor `4d03b0`, WWD plane loader `4d0450`, tile-size setter `4d0cd0`, and world add-plane wrapper `4cb7b0`. Frozen `SceneCameraRuntime` supplies actual `4d0a60` clamp behavior; the exact small embedded CArray constructor `4f58ab` is composed locally. Ghidra logs verify all entry boundaries without script errors. The oracle pins original EXE SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.

## API and sizes

The C11 API uses `ClawSceneActorHost` stable raw token spans and a rich dependency callback. Heap lookup retains its aligned four-byte-word ABI: name read/write helpers request `(token & ~3,1)` and access the byte at `(token &3)` within that word. The comparison host rejects unaligned lookup requests. Original runtime planes allocate **0x158 bytes /86 words**; 45 words suffice for camera projection alone, but not plane loading. Each WWD plane record contains **0xa0 bytes /40 words**. Input file offsets are added, with wrapping 32-bit arithmetic, to the decoded world-base token; they are not relative to the plane record.

`claw_world_plane_construct(receiver,parent,id,flags,context)` writes only the observed constructor fields. It assigns original vtable `513d40`, parent+`c`, id+`4`, flags+`8`, zero tile/row pointers+`20`/`24`, grid+`b0`=0, factor+`18`/`1c`=1.0, screen-left+`50`=`ffffffff`, and25 words beginning+`f4` (first=100, others0). Its embedded CArray at+`9c` has vtable `5108fc`, and four following words0. It preserves all other bytes and does not allocate.

`claw_world_plane_load(receiver,record,decodedWorldBase,inclusiveViewport,context,dependency,user)` returns original0/1. `claw_world_plane_add(world,record,decodedWorldBase,unused,...)` returns the original plane token or0. Add allocates0x158, constructs with parent=world+`c`, id=current world+`3c`, flags0, loads using viewport world+`10`, inserts at the current array index, and selects the main plane if flags bit1 is set. The original caller supplies a third argument (its viewport address) and the method removes12 stack bytes; the third argument is not read. The wrapper itself supplies world+`10` to the loader.

## Exact record mapping

| Record byte offset /word | Runtime field | Meaning |
| --- | --- | --- |
| `8` /2 | `8` | Flags copied directly, twice at original boundaries |
| `10` /4 | `b4` | NUL-terminated plane name copy |
| `58`,`5c` /22,23 | `38`,`3c` and `68`,`6c` | Declared tile width/height and working geometry |
| `60`,`64` /24,25 | `28`,`2c` | Tile counts width/height |
| `68`,`6c` /26,27 | `10`,`14` | Initial centers, scaled unless flags1 |
| `70`,`74` /28,29 | `94`,`98`, then `18`,`1c` | Signed movement percentages and binary32 factors |
| `78` /30 | `144` | Raw plane parameter/color word |
| `7c` /31 | Image registry/array loop | Number of image-set names |
| `80` /32 | `4d1620` argument1 | Object count |
| `84` /33 | Allocated tile buffer | Input tile-data offset |
| `88` /34 | Image-name scanner | Input image-set-name offset |
| `8c` /35 | `4d1620` argument0 | Input object-record offset; zero skips grid/object setup |
| `90` /36 | `80` | Raw z/order value |

The loader first resolves image-set names through scene+`10` image registry+`10`, then inserts roots into plane+`9c` CArray. Bytes are interpreted as signed. The scanner skips nonzero bytes below`30` and collects bytes `30..7f`; names are not parsed using a generic whitespace splitter. Each lookup produces a resource token through the declared bool/output-pointer adapter. Array index is the original signed low byte of the loop index.

Extents+`30`/`34` are wrapping32 products of counts and tile dimensions. Flags bit`10` changes geometry: the loader searches the first image resource for its first valid nonzero image, then uses image+`10`/`14` dimensions. Without this bit, it uses the WWD dimensions directly. If that resource has no nonzero image, the later setter is skipped, preserving earlier geometry and untouched shift fields.

`4d0cd0` updates extents, working dimensions, offsets, and shift fields. Both shifts+`8c` and+`90` count signed right shifts of **width**, including when height differs. The recovered code preserves this original behavior.

Movement factors use original instructions `fild signed32`, `fmul binary32 [513d70]`, `fstp binary32`. The multiplier's actual bits are `3c23d70a`, or approximately0.009999999776482582. The native implementation performs the product at53-bit precision, then stores binary32. Division by100 is not equivalent for all inputs; directed cases include99,37, signed limits and negative values. All14 supplied retail worlds use percentage pairs50/50,100/100,150/125, where the earlier division conversion happened to produce the same bits.

## Ordering and ownership

The loader copies the supplied screen rectangle before geometry selection. It sets working tile offsets+`60`/`64`=0, copies the name and raw plane fields, and, unless rectangle-left=`80000000`, calculates inclusive width/height `(right-left+1,bottom-top+1)` with wrapped arithmetic and signed halves, then clamps the initially zero centers. It then writes movement factors.

The original loader allocates `countWidth*countHeight*4` bytes and copies every raw tile word into plane+`20`. It separately allocates `countHeight*4` bytes for plane+`24` and fills signed positive-height rows with `row*countWidth`. It does not free prior tile/row allocations when invoked again. These pointers and ownership are preserved rather than borrowing the decoded asset's tile bytes.

Next it converts record centers, applying the factors unless flags1, stores binary32 centers and clamps again. Only then does nonzero object offset invoke `4d1620(plane,decodedBase+objectOffset,objectCount)`. Frozen `SpatialGridRuntime` owns this grid constructor/object-record loop and its deletion/resize services; this module delegates the exact boundary. Actual resource allocation, object loading, and gameplay callbacks remain host responsibilities.

Add inserts through `4f582f(world+34,currentCount,plane)`. This updates raw array fields+`38` and+`3c` under the supplied service contract. Plane insertion follows record order without sorting by z. **The last inserted plane with flags1 wins** world main pointer+`5c` and index+`60`. On loader failure the wrapper calls observed deleting destructor `4d2210(plane,1)`; actual destruction is an explicit service here. Allocation failure leading to the original null dereference is reported as native fault2.

The verified caller `4cb200` first invokes world vtable+`44` cleanup, optionally calls decompression`4cd660`, and calls `4cb7b0` in consecutive160-byte record order. After all planes and tile descriptions load, it overwrites the main center from **world header720/724**, clamps, and propagates the resulting integer center to the other planes. The frozen world-follow `42d5f0` has these camera propagation semantics. A native startup must apply that final world start point after all planes exist; record initial centers alone do not represent completed world startup. The complete `4cb200` cleanup/decompression/tile-description graph is not ported by this bounded module; private caller decompilation records this remaining boundary.

## Explicit host services and bounded faults

`ClawWorldPlaneCall` carries original function, receiver and raw arguments; `4f6286` temporary stack name is adapted as callback text, with its original bool/output pointer represented by the returned resource token. `4f582f` has original `(index,value)` arguments and must implement array state changes. `4d1620` has original `(record,count)` arguments and returns original success. `4d2210` has deleting flag1. Allocations use `scene.allocate`, with exact original requested byte counts and full pre-call snapshots in tests. Frozen camera clamp needs only the same raw heap lookup contract. All spans must remain stable during callbacks and allocation.

The oracle adapts CopyRect to an exact16-byte memory copy; no graphics platform behavior is substituted. Image registry lookup, CArray insertion, grid/object initialization and deleting destructor fixtures are declared finite services. Their arguments and complete pre-call heaps are compared; those fixtures do not prove the actual service bodies. REZ index reading and zlib decompression in the asset helper are explicit input adapters, not claims of recovered original archive/decompression code.

Fault1 reports missing raw spans/services. Fault2 reports native allocation/loop/string bounds. The frozen clamp also reports invalid extents/nonfinite or excessive wrap loops. Unsafe original paths (such as flags10 with no valid first resource, null tile allocation followed by nonempty copy, overflowing strings, overlapping output/input strings, or corrupt unbounded counts) do not receive a safe-normal-return equivalence claim. Constructor/load/add do not reset a preexisting context fault; the host clears it deliberately before a new operation.

## Evidence

Run `work/test-env/bin/python Tests/compare_world_plane_runtime.py`. The optimized portable library builds with `-Wall -Wextra -Werror -ffp-contract=off`; the public header also compiles as C11. Final suite:981 complete original calls,1,819 ordered complete6MiB heap snapshots,657 executed original addresses and854 directed cases. Meaningful EAX returns, exact callee stack cleanup, allocation arguments/tokens, and original FS exception-chain restoration are checked. Preserved seeded bytes are compared across the entire heap, not only known fields.

The suite reads the hash-pinned disc REZ (`b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`), tests **all14 worlds /42 actual plane records /1,886,406 tile words**, and retains the full three-plane world append history. It also checks repeated main-plane replacement without z sorting, invalid-header failure/destructor ordering, changing percentages during image lookup, lookup misses, grid failure, signed image-name scanning, flags10 geometry selection, non-origin inclusive rectangles, sentinel rectangles, extreme percentages, wrapped geometry products and constructor-preserved words. Actual42 source-derived field/factor profiles and verification counts are saved privately under `work/world-plane-agent/`.

This proves the bounded plane bodies within explicit service contracts. It does not establish full original world-resource initialization, tile-description loading, retail graphics or whole-game identity.
