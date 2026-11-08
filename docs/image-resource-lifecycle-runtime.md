# Source image resource lifecycle

`ImageResourceLifecycleRuntime` closes the bounded original image-controller load, cache, restore, remove and clear graph. It adds eight original bodies and composes frozen dictionary, CString, REZ, image, pixel and surface owners. It is not an independent image parser or a claim of complete DirectDraw behavior.

The executable is original v1.0 `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Retail archive SHA256 is `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`. Private disassembly/decompilation is under `work/image-resource-lifecycle-agent/`; source bodies are checked against unchanged executable instructions.

## New bodies and source behavior

| Entry | Arguments after receiver | Recovered behavior |
| --- | --- | --- |
| `4d2540` | width, height, key-enabled | Blank image initialization through source `4bc670`; dimensions, halves, kind and origin stores. This is not the file loader. |
| `4d26c0` | none | Image cleanup: zeros dimensions, destroys surface, rereads and frees compressed ownership, then zeros the corresponding pointers. |
| `4ce900` | none | Base image destructor: restores source VT, cleanup, resets identity/owner fields, then base VT. |
| `4ce8e0` | flags | Deleting wrapper: destructor, conditional free on low flag bit, returns original receiver. |
| `4bfc20` | none | Compressed object cleanup: frees payload `+0c`, then rereads/frees auxiliary `+20`; does not clear either field. |
| `4d27a0` | resource, key-enabled | Whole resource restore decision, in-place reload or typed recreate, including original resource ownership distinction. |
| `4d2790` | unused | Calls source `4b99d0(surface)` when present. That vertical pixel-flip body remains an explicit dependency. |
| `4bf680` | graphics, data, length, key | Whole surface PID reload wrapper: numeric/palette gates, source embedded-palette byte stores, source decoder/converter election, temporary allocation and cleanup. Pixel loops compose frozen owners. |

`4bf680` requires width divisible by four and matching surface dimensions. Embedded palette flag `80` requires length greater than 768; it copies trailing RGB triplets into `5423b0` as three bytes followed by a zero reserved byte, in original byte-store order. Eight-bit decoding elects `4babe0`; other depths elect temporary allocation, `4bef50`, then `4b9e90`. Optional key flag elects `4b9990`. Isolated 16/24/32-bit tests verify the wrapper with declared decoder/converter services, not those complete pixel bodies.

No new CString implementation is added. The tiny `4f6433` empty-string getter already belongs to frozen `PlayerFadeBlendRuntime`; composition uses its API. Frozen `CStringAssignmentRuntime` handles exact byte tails. Frozen `ActorDestruction` handles `4f6584`, and frozen `SceneLifecycle` handles dictionary/controller clear.

## Native joining recipe

The C11 context is 120 bytes on the current 64-bit host. `claw_image_resource_lifecycle_entry` accepts a source function, raw receiver, argument words, borrowed context and synchronous rich dependency callback. Return one means a covered completed call; meaningful original EAX is a separate output. Faults 1/2/3 denote missing transport/span, unsafe ABI/domain and operation budget respectively. These are native diagnostics, not invented original error returns. Unknown public entries return zero without modifying the output.

1. Keep a single raw token heap with exact live ownership: controller 44 bytes, image 52, scene 60, graphics 2180, surface 188, compressed object 40, borrowed REZ resource 96. An image `+0c` points to scene; scene `+1c` points to graphics; image `+2c` owns its surface and `+30` owns its compressed representation. Initialize the controller and resource graph through their frozen constructors. No synthetic surface/image success is required.
2. Supply borrowed loading context with frozen Registry, Namespace, ResourceData, Archive, CArray and pool views. Supply image globals, SceneDisplay, Story, PCX, SurfaceBlit, CStringAssignment and SceneLifecycle views when their bodies are reached. All contexts use the same heap and synchronous allocator identity; set their fault fields to zero before a new history. Do not concurrently borrow these contexts. The facade temporarily redirects borrowed scene hosts and disables Registry's shortcut image dispatcher, then restores those references on return, including failure.
3. Pass the strict word lookup directly through this facade. Supply CStringAssignment's strict byte provider and its existing lifecycle/allocation/array contexts. This module creates no containing-word shadow or late flush; it leaves `byteContext/bytes` untouched. An outer padded word view must not falsely claim that an exact CString tail is a writable complete word. Resource/table byte adapters retain their own distinct contracts.
4. Materialize live globals `54316c` (load flags), `543170` (key), `5430b0..bc` (effects) and `5427b0` (embedded palette) in the same raw graph. The facade synchronizes frozen GameImage's view before calls and at dependency boundaries; the raw aliases remain authoritative. Whole clear uses the source reset of `54316c`.
5. Surface `+8` is the real DirectDraw interface token, preserved across text, copy, Flip, restore and cleanup. `4d27a0` elects interface VT `+60` IsLost and `+6c` Restore with receiver zero and interface token as argument zero. Supply exact HRESULTs and synchronous DD descriptor/local buffers. Physical DD allocation, locking, pitch, pixels, release and COM refcounts remain transport responsibilities. Do not replace the interface with a separate text-only identity.
6. `4d27a0` returns one for absent or intact surfaces. Nonzero Restore HRESULT elects virtual image cleanup and typed initializer `4d2380`, whose source resource release is composed. Zero Restore HRESULT elects in-place resource type/acquire and `4b95b0`; this branch does **not** release the acquired resource and uses raw `543170`, not the caller's key argument. A zero resource size after acquisition returns zero while retaining its cached payload. Preserve that lifetime until original resource destruction.
7. Registered surface `+b4` restoration callback is caller supplied. Frozen `4b9e60` invokes it as cdecl(surface); ordinary observed factory construction initializes this field to zero. No registration installer was found in this bounded graph, so no native reload callback is invented.

Rich callback packets retain local masks and up to two synchronous borrowed buffers. CopyRect and color-key locals are normalized explicitly; arbitrary physical writes must be performed in the shared raw graph during the callback, before source execution resumes.

## Verification and limits

The isolated suite passes **527 completed whole original calls plus one matched unsafe prefix**, with **1,485 full snapshots**, 381 instrumented `.text` addresses and 383 total instrumented addresses. It compares the full 2 MiB heap, `510000..553000` globals, meaningful EAX/RET stack effect, callback ordering and live/free identities. Profiles include callback-mutated surface/compressed pointers, duplicate aliased free requests, absent images, all restore branches, resource types, zero payload/size, blank geometry, depth/palette/length gates and overlapping embedded palette bytes. Bare compressed duplicate frees are normalized transport observations, not a claim that an ordinary allocator accepts them. The null-DD source prefix stops before the first invalid dereference at `4d27da`; native rejection is not original graceful behavior.

The joined retail suite passes **52 whole original calls / 2,239 full snapshots / 3,700 instrumented `.text` addresses / 3,711 total addresses**. Four complete source groups contain 42 frames:

| Retail resource group | Frames | Format |
| --- | ---: | --- |
| `STATES/MENU/IMAGES/SPARKLE` |8|uncompressed PID|
| `STATES/MENU/IMAGES/CURSOR` |19|PCX|
| `STATES/BOOTY/IMAGES/SCORENUMBERS` |10|compressed PID|
| `STATES/BOOTY/IMAGES/SYMBOLS` |5|compressed PID|

Each retained history constructs the real directory/resource graph, loads through the original image controller, duplicates the cache request, restores intact, reloads in place, recreates after failed Restore, removes by source name, reloads after removal, clears the whole controller, repeats clear and destroys the resource folder. Original CString/map/array/resource/image/codec bodies execute rather than initializer-success fixtures. Physical FILE reads use actual immutable REZ bytes; the test's directory selector merely chooses original records. Original pixels and every represented physical buffer byte participate in the full heap comparisons. Physical DD backing declares aligned pitch times `(height+1)` capacity: the extra row is a host transport profile, not a recovered OS allocation promise. Eight-bit DD transport and source graphics constructor are verified here; whole physical display startup and other pixel depths are outside this joined proof.

Strict C11, warnings-as-errors C++17, executed Swift import (120-byte context), and **21 exact-size ASAN/UBSAN replays** pass. These replays instrument the new lifecycle source and freshly compiled PCXCreation, preserve original callback snapshots and live/dead lookup enforcement, and use exact image/surface/compressed/resource/PID spans. Frozen dylib implementations and the entire joined retail graph are not freshly sanitizer-instrumented by this gate. Pixel parity belongs to the existing frozen pixel owners and root's separate native tests; this module's additional evidence closes their caller ownership/order graph.

Run from the repository root:

```sh
work/test-env/bin/python Tests/compare_image_resource_lifecycle_runtime.py
work/test-env/bin/python Tests/compare_image_resource_lifecycle_join.py
work/test-env/bin/python Tests/check_image_resource_lifecycle_asan.py
```

These scripts compile only private artifacts and read frozen owners' dylibs. Source physical BMP reload, `4b99d0` vertical flip, physical COM/device success, registered callback installation and full-menu rendering acceptance remain explicit boundaries. No native host, Xcode project, shared source or device was changed.
