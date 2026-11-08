# Original interface-file and menu-widget runtime

`Sources/InterfaceFileRuntime.h/.cpp` recovers the finite **load-mode** IFC tree, borrowed-image initialization, selection/page/input timing, drawing wrapper and teardown graph elected by original StateFive. This is source recovery with declared transports. It is not a claim that the native app starts or presents the retail main menu, or that its pixels match the original.

Evidence uses unchanged instructions from `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Read-only Ghidra analysis is independently cloned in `work/interface-file-agent/`; original assembly verifies whole entry boundaries and return stack cleanup. No existing module, host, project or shared header was changed.

## API and source storage

`claw_interface_file_entry(function, receiver, arguments, count, context, dependency, user, result)` separates completion status, faults and meaningful source EAX. Original void-method register residue has no host meaning. `claw_interface_file_function(vtable, slot)` exposes the observed interface/controller slot identities; raw source vtables/IATs are still required in the token host. Unknown entries return uncovered. Native diagnostics are missing span/service1, unsupported/unsafe/EOF2, ABI/operation limit3. They do not make the original safe.

Storage is **controller256 bytes**, **node176 bytes**, and **component108 bytes**, embedded at node+60. Controller root is embedded at+72, current page+248, ready+68 and tree-navigation enabled+252. Controller pointer array occupies+8..24; selected index+28, disabled-choice skip+32, press latch+36, captured press index+40, press tick+44, blink tick+48 and blink interval+52. Width/height are+60/+64. Untouched fields retain caller seeds.

Node CString name is+12, description+20; children use the five-word pointer array+24, parent is+16, schema+44, nine-word auxiliary allocation+52, initialized+4, graphics+168. Embedded component has eight owning CString cells+24..52, image pointer array at0..16, ID+20, fallback mask pointer+56, ownership+60, current image+64, flags+68, graphics+72, extras+76/+80, position+84/+88, maximum dimensions+92/+96, draw enable+100 and press duration+104.

Raw memory lookup keeps the frozen aligned-word host ABI. Byte access requests an aligned word and accesses only the selected byte. Transport spans may round their token-domain length to words, but the sanitizer backing allocation retains the actual byte allocation, including CString `length+13`. No full-word read past an actual byte span is authorized by rounding.

The context reserves caller-owned automatic aliases: CMemFile40 bytes, CArchive68 bytes and CString scratch4 bytes. They must not overlap live objects, output buffers or input bytes. Source stack receiver/pointer arguments in dependency events are normalized through synchronous buffers: receiver bit256; argument bit `1<<index`; receiver buffer first, followed by argument buffers in ascending order. Complete original file/archive automatic state is compared at every callback and before stack lifetime ends. The internal scratch cell's persisted host address is not an original heap allocation or persistent stack-cell identity.

The optional CArray context composes frozen `CArrayRuntime` SetSize; CString destruction composes frozen `ActorDestruction`4f6584. The reserved `strings` pointer does not add an implicit scene/controller call. Source global empty-string aliases52e1c8/52e1cc and read-only literals must be mapped. Physical allocation/free use exact4f63ec/4f6428 events and source byte lengths.

## Whole entries and loader ABI

| Family | Entries |
| --- | --- |
| Controller constructors/destruction/clear |4dcc40,4dd180,4dccb0,4dd1c0,4dd240,4dce90,4dd420|
| Raw-byte/file loader |4dcdf0,4dcd10|
| Node/component constructors, load serialization, factory, init and cleanup |4def70,4dde80,4df490,4deb50,4df2b0(kind0),4df0e0,4de0e0,4df180,4df040,4de450,4ddf70|
| Lookup, description copy, parent/count, recursive argument |4dd020,4df200,4df460,4df620,4df630,4df480,4df260,4df270,4dd0d0,4dd0c0|
| Root/page/back/layout |4dcf00,4dcf10,4dd030,4dd800|
| Selection/navigation/activation/mouse/time |4dd450,4dd480,4dd490,4dd520,4dda50,4ddb40,4ddac0,4ddbc0,4ddce0,4dd0e0,4ddc30|
| Component flags/enable/image replacement/geometry/drawing |4dec60,4ed050,4dceb0,4de4d0,4dece0,4ded00,4ded20,4ded40,4de790,4dd270|
| Trivial elected callbacks |4bc110,4e5b50(two arguments/RET8)|
| Borrowed memory-file read/seek/GetBufferPtr |4ff79f,4ff822,4ff8a8|

The original **4dcdf0 takes seven stack words, RET28**: graphics manager, bytes, size, image resolver, argument4, argument5, argument6. Its file-object counterpart **4dcd10 takes six words, RET24**: graphics manager, file, resolver, argument3, argument4, argument5. Ghidra omitted a trailing argument; assembly45ae6d..45ae86 establishes three trailing zeros in the actual StateFive caller.

4dcdf0 creates a borrowed CMemFile, attaches bytes without ownership, constructs a load-mode CArchive with4096-byte buffer request, invokes embedded root serialization then initialization, lays out the root page, selects0, publishes ready, closes the archive, detaches the file and destroys its automatic object. Successful EAX1 and failed image initialization EAX0 are compared. Archive direct-buffer reads, length encodings and signed child count preserve source ordering. Load close seeks back unread bytes and sets archive cursor to **end**, not buffer begin.

CLAW.IFC is14249 bytes, SHA256 `e371e28c41aeb8245d33942bb1cb2cbec64c043df63f9968a6873c8e1403c345`; its whole-original tree has133 nodes, root ID10000/Main Page with7 children,1064 image-resolution calls (eight per node). CLAWWITHLOBBY.IFC is14678 bytes, SHA256 `2630c505e243d69e1ce349cde7b7a6e2dd6eff2eeaf087b66443836c6f3377c6`, with138 nodes. Inventory is produced from the original loaded tree, not from an independently inferred IFC parser. Peer `Tests/state_five_interface_profile.json` preserves the CLAW tree capture and213 distinct nonempty image strings for source StateFive resolver comparisons.

## Timing and source quirks

The component constructor sets press duration300 and the base controller sets blink duration400. Both comparisons are strict unsigned elapsed greater-than, preserving tick wrap and multiple GetTickCount calls. Left navigation4dda50 does **not** update expiry first, while4ddac0 and4ddb40 do. Disabled selection modes, page transitions and old-widget callback payload are preserved.

**Actual StateFive later calls4dd0d0(menu,0).** This recursively writes node+164, which aliases embedded component+104, the press-duration field. Consequently the actual caller changes release duration to0: same tick retains the latch, elapsed1 releases. The standalone300-ms tests and a source-caller-style zero-duration history are separate measured profiles.

Current-image rectangles center the current image inside cached maximum dimensions, with signed truncation and wrapping stores. Mouse calls physical GetCursorPos546cd0 (POINT8) and PtInRect546cd4 (RECT16 plus POINT by value).4de790 emits exact4b9ce0 target/destinationRECT/currentImage/sourceRECT/0x1008000/0; no custom GUI drawing is substituted. Owned image clear4de450 clears the entire pointer array after the first nonnull release, so it does not issue one release per slot. Image replacement4de4d0 replaces every old-pointer alias, recomputes maximum dimensions and leaves current-image selection to a later SetMode call.

A failed node allocation can append0 then reach an unchecked parent write. Null CString/mask allocations can also reach unchecked writes. A failed auxiliary36-byte allocation is different: the measured whole loader can still finish, and cleanup checks that pointer. Truncated streams reach source4fe675(3,0); tests compare the prefix at the throw request, not a manufactured empty menu or invented exception unwinding.

## Declared boundaries and limits

Actual StateFive image-name resolver45f940/45be10 and action45fa50 are frozen in `StateFiveRuntime`, not duplicated here. The IFC oracle's default resolver is an explicit cdecl callback receiving an owning CString by value and returning borrowed188-byte surface metadata (30×20); it destroys that incoming copy. Source string ownership, all image array/fallback stores and callback ordering are compared. Separate directed fixtures vary signed dimensions and aliases. These are physical image/metadata profiles, **not proof of whole retail image-controller traversal or pixels**. Parent can compose the real StateFive resolver through the same exact callback ABI. Source PCX factory4be810 remains outside this module even though frozen PCX decode4bebc0 exists.

CFile physical filename/stat4fc139, allocator/CRT transport, image release4bc4f0, Win32 cursor/tick/rectangle services and physical blit4b9ce0 remain addressed callbacks. Non-default no-resolver acquisition4de560 and optional caption4de830 are explicitly delegated, not silent success. Base-controller release4dddc0 is an explicit service if its base vtable elects it; actual StateFive uses derived4dd0e0. Store-mode archive serialization, direct factory nonzero kinds and arbitrary file write/growth are unported diagnostics/services, distinct from the measured retail load-mode graph. All-disabled zero-index navigation may cycle in the original; the host operation limit is a diagnostic, not a recovered successful response.

## Verification

Run `work/test-env/bin/python Tests/compare_interface_file_runtime.py`. The suite compares complete4MiB fixture heap plus192KiB mutable original image/global window, ordered calls and callback snapshots, allocation/free ordering, automatic file/archive states, meaningful EAX and RET/SP for completed calls. It covers both retail hierarchies; every CLAW node/page and nested activation; strict and wrapped timers; disabled/previous/next paths; mouse misses/activation; drawing and signed geometry; distinct image aliases; distribution; repeated cleanup;12 synthetic archive boundaries; mandatory-image failures;9 truncated streams and4 unchecked allocation prefixes, plus the accepted auxiliary-allocation failure.

Final suite passes **4843 paired calls**, including **13 matched unsafe/throw prefixes**, and **44340 complete snapshots**;3533 instrumented addresses/3526 filtered text addresses. Counts and hashes are recorded in `work/interface-file-agent/verified-complete.log` and `frozen-sha256.txt`. The private corpus/replay compiles the unchanged final native source with ASAN/UBSAN and maps controllers/nodes/components/CStrings/image metadata/file/archive to source-sized allocations.26 retained replays/7848 callback snapshots passed, including both complete loaders and teardown. Allocator/free endpoints remain replay transports; callback order and freed identities are compared, rather than claiming a physical Windows allocator or source stack identity. Strict C++17, C11 header and Swift import/typecheck pass. Instrumented-address totals include stops/adapters; filtered text-address totals are reported separately and are not whole-game coverage.
